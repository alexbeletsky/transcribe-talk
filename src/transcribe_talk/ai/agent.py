"""
Agent module for TranscribeTalk.

The Agent is the central orchestrator that manages:
- Managing all core components (PromptEngine, ChatService, Turn, ToolScheduler, ConversationHistory)
- Orchestrating the conversation flow
- Handling tool execution requests
- Managing conversation state and history
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, AsyncIterator, Callable
from datetime import datetime
from pathlib import Path

from .chat_service import ChatService
from .prompt_engine import PromptEngine
from .history import ConversationHistory, MessageRole
from .tool_scheduler import ToolScheduler, ApprovalMode
from .turn import Turn, SyncTurn
from .loop_detector import LoopDetector
from .chat_compressor import ChatCompressor
from .events import (
    TurnEvent, ContentEvent, ToolCallRequestEvent, FunctionResponseEvent,
    FinishedEvent, ErrorEvent, EventType
)
from ..tools import ToolRegistry, get_global_registry
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class AgentConfig:
    """Configuration for the Agent."""
    
    def __init__(
        self,
        max_turns: int = 10,
        max_tool_calls_per_turn: int = 5,
        max_total_tool_calls: int = 20,
        auto_confirm: bool = False,
        debug: bool = False,
        dry_run: bool = False
    ):
        """
        Initialize agent configuration.
        
        Args:
            max_turns: Maximum conversation turns allowed
            max_tool_calls_per_turn: Maximum tool calls per turn
            max_total_tool_calls: Maximum total tool calls in conversation
            auto_confirm: Whether to auto-confirm tool executions
            debug: Whether to enable debug mode
            dry_run: Whether to simulate tool executions
        """
        self.max_turns = max_turns
        self.max_tool_calls_per_turn = max_tool_calls_per_turn
        self.max_total_tool_calls = max_total_tool_calls
        self.auto_confirm = auto_confirm
        self.debug = debug
        self.dry_run = dry_run


class Agent:
    """
    Central orchestrator for agentic conversations.
    
    This class coordinates all components to enable:
    - Voice-to-voice conversations
    - Tool-augmented AI interactions
    - Safety limits and error handling
    - Conversation state management
    """
    
    def __init__(
        self,
        settings: Settings,
        tool_registry: Optional[ToolRegistry] = None,
        config: Optional[AgentConfig] = None
    ):
        """
        Initialize the Agent.
        
        Args:
            settings: Application settings
            tool_registry: Optional tool registry
            config: Agent configuration
        """
        self.settings = settings
        self.config = config or AgentConfig()
        
        # Initialize core components
        self.chat_service = ChatService(settings.openai)
        self.prompt_engine = PromptEngine(Path.cwd())
        self.conversation_history = ConversationHistory(
            max_messages=100,
            max_tokens=8000
        )
        
        # Initialize chat compressor
        self.chat_compressor = ChatCompressor(
            chat_service=self.chat_service,
            compression_threshold=6000,
            preserve_recent=10
        )
        
        # Tool-related components
        self.tool_registry = tool_registry
        if tool_registry:
            approval_mode = ApprovalMode.NEVER if self.config.auto_confirm else ApprovalMode.SMART
            self.tool_scheduler = ToolScheduler(
                tool_registry=tool_registry,
                approval_mode=approval_mode,
                dry_run=self.config.dry_run
            )
            # Initialize loop detector for tool calls
            self.loop_detector = LoopDetector(
                max_repetitions=3,
                time_window=60
            )
        else:
            self.tool_scheduler = None
            self.loop_detector = None
        
        # State tracking
        self._turn_count = 0
        self._total_tool_calls = 0
        self._conversation_active = False
        
        logger.info("Agent initialized")
    
    async def execute_turn(
        self,
        user_input: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[TurnEvent]:
        """
        Execute a single conversation turn.
        
        Args:
            user_input: User's input text
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Yields:
            TurnEvent objects describing the turn progress
        """
        self._turn_count += 1
        
        # Check turn limit
        if self._turn_count > self.config.max_turns:
            yield ErrorEvent(
                error_type="TurnLimitExceeded",
                error_message=f"Maximum turns ({self.config.max_turns}) exceeded",
                recoverable=False
            )
            return
        
        # Add user message
        self.conversation_history.add_user_message(user_input)
        
        # Check if we need to compress the conversation
        if await self.chat_compressor.should_compress(self.conversation_history):
            logger.info("Compressing conversation history...")
            compressed_history, summary = await self.chat_compressor.compress_history(
                self.conversation_history
            )
            if summary:
                self.conversation_history = compressed_history
                logger.info(f"Conversation compressed. Summary: {summary[:100]}...")
        
        # Set system prompt if first turn or after compression
        if self._turn_count == 1 or len(self.conversation_history.messages) <= 2:
            system_prompt = self.prompt_engine.build_system_prompt()
            self.conversation_history.set_system_prompt(system_prompt)
        
        # Prepare messages for API
        messages = self.conversation_history.get_messages_for_api()
        
        # Create turn with tool support if available
        turn = Turn(
            chat_service=self.chat_service,
            tool_registry=self.tool_registry,
            loop_detector=self.loop_detector,
            debug=self.config.debug
        )
        
        # Process turn events
        tool_calls = []
        accumulated_content = ""
        
        async for event in turn.run(messages, temperature, max_tokens):
            # Yield most events directly
            if event.type in [EventType.CONTENT, EventType.THOUGHT, EventType.DEBUG]:
                if event.type == EventType.CONTENT:
                    accumulated_content += event.content
                yield event
            
            # Collect tool calls
            elif event.type == EventType.TOOL_CALL_REQUEST:
                tool_calls.extend(event.tool_calls)
            
            # Handle finished event
            elif event.type == EventType.FINISHED:
                # Add assistant message to history
                if accumulated_content or tool_calls:
                    tool_calls_data = None
                    if tool_calls:
                        tool_calls_data = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": tc.arguments
                                }
                            }
                            for tc in tool_calls
                        ]
                    
                    self.conversation_history.add_assistant_message(
                        content=accumulated_content,
                        tool_calls=tool_calls_data
                    )
                
                # Execute tool calls if any
                if tool_calls and self.tool_scheduler:
                    # Check tool call limits
                    if len(tool_calls) > self.config.max_tool_calls_per_turn:
                        yield ErrorEvent(
                            error_type="ToolCallLimitExceeded",
                            error_message=f"Too many tool calls in one turn (limit: {self.config.max_tool_calls_per_turn})",
                            recoverable=True
                        )
                        tool_calls = tool_calls[:self.config.max_tool_calls_per_turn]
                    
                    self._total_tool_calls += len(tool_calls)
                    if self._total_tool_calls > self.config.max_total_tool_calls:
                        yield ErrorEvent(
                            error_type="TotalToolCallLimitExceeded",
                            error_message=f"Total tool call limit exceeded ({self.config.max_total_tool_calls})",
                            recoverable=False
                        )
                        return
                    
                    # Execute tools
                    interactive = not self.config.auto_confirm
                    responses = await self.tool_scheduler.execute_tool_calls(
                        tool_calls,
                        interactive=interactive
                    )
                    
                    # Add tool responses to history and yield events
                    for response in responses:
                        self.conversation_history.add_tool_response(
                            tool_call_id=response.tool_call_id,
                            content=response.result if response.success else f"Error: {response.error_message}",
                            metadata={"success": response.success}
                        )
                        yield response
                    
                    # If we had tool calls, we need another turn
                    if responses:
                        # Recursive call for next turn
                        async for event in self._continue_after_tools():
                            yield event
                        return
                
                # Otherwise, we're done
                yield event
            
            # Handle errors
            elif event.type == EventType.ERROR:
                yield event
                if not event.recoverable:
                    return
    
    async def _continue_after_tools(self) -> AsyncIterator[TurnEvent]:
        """
        Continue the conversation after tool execution.
        
        Yields:
            TurnEvent objects
        """
        # Prepare messages including tool responses
        messages = self.conversation_history.get_messages_for_api()
        
        # Create continuation turn
        turn = Turn(
            chat_service=self.chat_service,
            tool_registry=self.tool_registry,
            loop_detector=self.loop_detector,
            debug=self.config.debug
        )
        
        # Process continuation
        accumulated_content = ""
        
        async for event in turn.run(messages):
            if event.type == EventType.CONTENT:
                accumulated_content += event.content
            yield event
            
            if event.type == EventType.FINISHED:
                # Add final assistant message
                if accumulated_content:
                    self.conversation_history.add_assistant_message(
                        content=accumulated_content
                    )
    
    def execute_turn_sync(
        self,
        user_input: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> List[TurnEvent]:
        """
        Synchronous version of execute_turn.
        
        Args:
            user_input: User's input text
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Returns:
            List of TurnEvent objects
        """
        # Run async version in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            events = []
            async def collect_events():
                async for event in self.execute_turn(user_input, temperature, max_tokens):
                    events.append(event)
            
            loop.run_until_complete(collect_events())
            return events
        finally:
            loop.close()
    
    def start_conversation(self) -> None:
        """Start a new conversation."""
        self._conversation_active = True
        self._turn_count = 0
        self._total_tool_calls = 0
        self.conversation_history.clear()
        if self.tool_scheduler:
            self.tool_scheduler.clear_history()
        logger.info("New conversation started")
    
    def end_conversation(self) -> Dict[str, Any]:
        """
        End the current conversation and return summary.
        
        Returns:
            Conversation summary
        """
        self._conversation_active = False
        
        summary = {
            "turn_count": self._turn_count,
            "total_tool_calls": self._total_tool_calls,
            "conversation_summary": self.conversation_history.get_summary(),
            "chat_telemetry": self.chat_service.get_telemetry()
        }
        
        if self.tool_scheduler:
            summary["tool_summary"] = self.tool_scheduler.get_tool_call_summary()
        
        logger.info("Conversation ended")
        return summary
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the full conversation history.
        
        Returns:
            List of message dictionaries
        """
        return self.conversation_history.export_conversation()
    
    def save_conversation(self, filepath: Path) -> None:
        """
        Save the conversation to a file.
        
        Args:
            filepath: Path to save the conversation
        """
        import json
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.end_conversation(),
            "messages": self.get_conversation_history()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Conversation saved to {filepath}")
    
    def load_conversation(self, filepath: Path) -> None:
        """
        Load a conversation from a file.
        
        Args:
            filepath: Path to load the conversation from
        """
        import json
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Import messages
        if "messages" in data:
            self.conversation_history.import_conversation(data["messages"])
        
        # Restore state
        if "summary" in data:
            self._turn_count = data["summary"].get("turn_count", 0)
            self._total_tool_calls = data["summary"].get("total_tool_calls", 0)
        
        logger.info(f"Conversation loaded from {filepath}")