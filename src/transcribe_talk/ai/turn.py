"""
Turn - Event generator for conversation interactions.

This module provides the Turn class which encapsulates the logic for processing
a single request to the LLM and handling its streamed response.
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Dict, List, Optional, Any, Union
from datetime import datetime

from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import ChoiceDelta, ChoiceDeltaToolCall

from .chat_service import ChatService
from .events import (
    TurnEvent, ContentEvent, ThoughtEvent, ToolCallRequestEvent,
    FinishedEvent, ErrorEvent, DebugEvent, ToolCallInfo
)
from ..tools import ToolRegistry

logger = logging.getLogger(__name__)


class Turn:
    """
    Encapsulates a single interaction cycle with the LLM.
    
    This class:
    - Sends messages to ChatService
    - Processes the streamed response
    - Yields structured events describing what's happening
    - Does NOT execute tools (that's handled by ToolScheduler)
    """
    
    def __init__(
        self,
        chat_service: ChatService,
        tool_registry: Optional[ToolRegistry] = None,
        debug: bool = False
    ):
        """
        Initialize a Turn.
        
        Args:
            chat_service: The ChatService instance
            tool_registry: Optional ToolRegistry for function schemas
            debug: Whether to emit debug events
        """
        self.chat_service = chat_service
        self.tool_registry = tool_registry
        self.debug = debug
        
        # State tracking
        self.accumulated_content = ""
        self.accumulated_tool_calls: Dict[int, Dict[str, Any]] = {}
        self.debug_responses: List[Any] = []
        
    async def run(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[TurnEvent]:
        """
        Execute the turn and yield events.
        
        Args:
            messages: Conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Yields:
            TurnEvent objects
        """
        try:
            # Get function schemas if tool registry provided
            functions = None
            if self.tool_registry:
                functions = self.tool_registry.get_all_schemas()
                if self.debug and functions:
                    yield DebugEvent(
                        message=f"Available tools: {[f['name'] for f in functions]}"
                    )
            
            # Send to ChatService
            stream = await self.chat_service.send_message_async(
                messages=messages,
                functions=functions,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            # Process the stream
            finish_reason = None
            usage = None
            
            async for chunk in stream:
                if self.debug:
                    self.debug_responses.append(chunk)
                
                # Process each choice in the chunk
                for choice in chunk.choices:
                    delta = choice.delta
                    
                    # Handle content
                    if delta.content is not None:
                        self.accumulated_content += delta.content
                        yield ContentEvent(
                            content=delta.content,
                            is_partial=True
                        )
                    
                    # Handle tool calls
                    if delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            yield await self._process_tool_call_delta(tool_call_delta)
                    
                    # Track finish reason
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
                
                # Track usage if available
                if chunk.usage:
                    usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens
                    }
            
            # Yield final content if any accumulated
            if self.accumulated_content and not self.accumulated_tool_calls:
                yield ContentEvent(
                    content=self.accumulated_content,
                    is_partial=False
                )
            
            # Yield tool call requests if any
            if self.accumulated_tool_calls:
                tool_calls = []
                for tool_data in self.accumulated_tool_calls.values():
                    if tool_data.get("id") and tool_data.get("function", {}).get("name"):
                        try:
                            arguments = json.loads(
                                tool_data.get("function", {}).get("arguments", "{}")
                            )
                            tool_calls.append(ToolCallInfo(
                                id=tool_data["id"],
                                name=tool_data["function"]["name"],
                                arguments=arguments
                            ))
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse tool arguments: {e}")
                            yield ErrorEvent(
                                error_type="ToolArgumentParseError",
                                error_message=str(e),
                                recoverable=True
                            )
                
                if tool_calls:
                    yield ToolCallRequestEvent(tool_calls=tool_calls)
            
            # Yield finished event
            yield FinishedEvent(
                has_tool_calls=bool(self.accumulated_tool_calls),
                finish_reason=finish_reason or "stop",
                usage=usage
            )
            
        except Exception as e:
            logger.error(f"Turn error: {e}")
            yield ErrorEvent(
                error_type=type(e).__name__,
                error_message=str(e),
                recoverable=False
            )
    
    async def _process_tool_call_delta(
        self,
        tool_call_delta: ChoiceDeltaToolCall
    ) -> Optional[TurnEvent]:
        """
        Process a tool call delta from the stream.
        
        Args:
            tool_call_delta: Tool call delta from OpenAI
            
        Returns:
            Optional debug event
        """
        index = tool_call_delta.index
        
        # Initialize tool call if needed
        if index not in self.accumulated_tool_calls:
            self.accumulated_tool_calls[index] = {
                "id": None,
                "type": None,
                "function": {
                    "name": None,
                    "arguments": ""
                }
            }
        
        tool_data = self.accumulated_tool_calls[index]
        
        # Update fields
        if tool_call_delta.id:
            tool_data["id"] = tool_call_delta.id
            
        if tool_call_delta.type:
            tool_data["type"] = tool_call_delta.type
            
        if tool_call_delta.function:
            if tool_call_delta.function.name:
                tool_data["function"]["name"] = tool_call_delta.function.name
                
            if tool_call_delta.function.arguments:
                tool_data["function"]["arguments"] += tool_call_delta.function.arguments
        
        # Emit debug event if enabled
        if self.debug:
            return DebugEvent(
                message=f"Tool call delta: index={index}, name={tool_data['function']['name']}",
                data=tool_data
            )
        
        return None
    
    def reset(self) -> None:
        """Reset the turn state for reuse."""
        self.accumulated_content = ""
        self.accumulated_tool_calls.clear()
        self.debug_responses.clear()


class SyncTurn:
    """
    Synchronous version of Turn for non-async contexts.
    
    This is a simplified version that doesn't support streaming.
    """
    
    def __init__(
        self,
        chat_service: ChatService,
        tool_registry: Optional[ToolRegistry] = None
    ):
        """
        Initialize a synchronous Turn.
        
        Args:
            chat_service: The ChatService instance
            tool_registry: Optional ToolRegistry for function schemas
        """
        self.chat_service = chat_service
        self.tool_registry = tool_registry
    
    def run(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> List[TurnEvent]:
        """
        Execute the turn synchronously and return events.
        
        Args:
            messages: Conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Returns:
            List of TurnEvent objects
        """
        events = []
        
        try:
            # Get function schemas if tool registry provided
            functions = None
            if self.tool_registry:
                functions = self.tool_registry.get_all_schemas()
            
            # Send to ChatService (non-streaming)
            response = self.chat_service.send_message_sync(
                messages=messages,
                functions=functions,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            # Process the response
            choice = response.choices[0]
            message = choice.message
            
            # Handle content
            if message.content:
                events.append(ContentEvent(
                    content=message.content,
                    is_partial=False
                ))
            
            # Handle tool calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_calls = []
                for tool_call in message.tool_calls:
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        tool_calls.append(ToolCallInfo(
                            id=tool_call.id,
                            name=tool_call.function.name,
                            arguments=arguments
                        ))
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse tool arguments: {e}")
                        events.append(ErrorEvent(
                            error_type="ToolArgumentParseError",
                            error_message=str(e),
                            recoverable=True
                        ))
                
                if tool_calls:
                    events.append(ToolCallRequestEvent(tool_calls=tool_calls))
            
            # Add usage info
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
            # Add finished event
            events.append(FinishedEvent(
                has_tool_calls=bool(hasattr(message, 'tool_calls') and message.tool_calls),
                finish_reason=choice.finish_reason or "stop",
                usage=usage
            ))
            
        except Exception as e:
            logger.error(f"SyncTurn error: {e}")
            events.append(ErrorEvent(
                error_type=type(e).__name__,
                error_message=str(e),
                recoverable=False
            ))
        
        return events