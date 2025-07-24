"""
Chat Service - Manages LLM interactions.

This module provides the ChatService class which is responsible for:
- Interacting with the OpenAI chat completions API
- Supporting streaming responses
- Retry logic for transient errors
- Telemetry and token usage tracking
"""

import asyncio
import logging
from typing import AsyncIterator, Dict, List, Optional, Any, Union
from datetime import datetime
import json

from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletionChunk, ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage

from ..config.settings import OpenAIConfig

logger = logging.getLogger(__name__)


class ChatServiceError(Exception):
    """Base exception for ChatService errors."""
    pass


class APIError(ChatServiceError):
    """Error from the OpenAI API."""
    def __init__(self, message: str, status_code: Optional[int] = None, retry_after: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class ChatService:
    """
    Manages interactions with the OpenAI Chat API.
    
    Features:
    - Async/sync API support
    - Streaming responses
    - Automatic retry with exponential backoff
    - Token usage tracking
    - Request/response telemetry
    """
    
    def __init__(self, config: OpenAIConfig):
        """
        Initialize the ChatService.
        
        Args:
            config: OpenAI configuration
        """
        self.config = config
        self._async_client: Optional[AsyncOpenAI] = None
        self._sync_client: Optional[OpenAI] = None
        
        # Telemetry
        self._request_count = 0
        self._total_tokens_used = 0
        self._total_cost = 0.0
        
        logger.info(f"ChatService initialized with model: {config.model}")
    
    @property
    def async_client(self) -> AsyncOpenAI:
        """Get or create async OpenAI client."""
        if self._async_client is None:
            self._async_client = AsyncOpenAI(
                api_key=self.config.api_key,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )
        return self._async_client
    
    @property
    def sync_client(self) -> OpenAI:
        """Get or create sync OpenAI client."""
        if self._sync_client is None:
            self._sync_client = OpenAI(
                api_key=self.config.api_key,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )
        return self._sync_client
    
    async def send_message_async(
        self,
        messages: List[Dict[str, Any]],
        functions: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = True
    ) -> Union[AsyncIterator[ChatCompletionChunk], ChatCompletion]:
        """
        Send a message to the OpenAI API asynchronously.
        
        Args:
            messages: List of message dictionaries
            functions: Optional list of function schemas
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            stream: Whether to stream the response
            
        Returns:
            AsyncIterator of chunks if streaming, complete response otherwise
        """
        self._request_count += 1
        start_time = datetime.now()
        
        # Build request parameters
        params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": stream
        }
        
        # Add stream options to include usage data if streaming
        if stream:
            params["stream_options"] = {"include_usage": True}
        
        # Add functions if provided
        if functions:
            params["tools"] = [{"type": "function", "function": f} for f in functions]
            params["tool_choice"] = "auto"
        
        try:
            logger.debug(f"Sending request to OpenAI API (stream={stream})")
            
            if stream:
                # Return streaming response
                response = await self.async_client.chat.completions.create(**params)
                return self._wrap_stream(response, start_time)
            else:
                # Return complete response
                response = await self.async_client.chat.completions.create(**params)
                self._track_usage(response, start_time)
                return response
                
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise APIError(str(e))
    
    def send_message_sync(
        self,
        messages: List[Dict[str, Any]],
        functions: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[ChatCompletion, Any]:
        """
        Send a message to the OpenAI API synchronously.
        
        Args:
            messages: List of message dictionaries
            functions: Optional list of function schemas
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            stream: Whether to stream the response
            
        Returns:
            Complete response or stream
        """
        self._request_count += 1
        start_time = datetime.now()
        
        # Build request parameters
        params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": stream
        }
        
        # Add stream options to include usage data if streaming
        if stream:
            params["stream_options"] = {"include_usage": True}
        
        # Add functions if provided
        if functions:
            params["tools"] = [{"type": "function", "function": f} for f in functions]
            params["tool_choice"] = "auto"
        
        try:
            logger.debug(f"Sending sync request to OpenAI API (stream={stream})")
            response = self.sync_client.chat.completions.create(**params)
            
            if not stream:
                self._track_usage(response, start_time)
            
            return response
                
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise APIError(str(e))
    
    async def _wrap_stream(
        self,
        stream: AsyncIterator[ChatCompletionChunk],
        start_time: datetime
    ) -> AsyncIterator[ChatCompletionChunk]:
        """
        Wrap the stream to track usage and handle errors.
        
        Args:
            stream: The original stream
            start_time: Request start time
            
        Yields:
            ChatCompletionChunk objects
        """
        total_tokens = 0
        
        try:
            async for chunk in stream:
                # Track tokens if available
                if chunk.usage:
                    total_tokens = chunk.usage.total_tokens
                
                yield chunk
                
        except Exception as e:
            logger.error(f"Stream error: {e}")
            raise APIError(str(e))
        
        finally:
            # Log completion
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Stream completed in {duration:.2f}s, tokens: {total_tokens}")
            
            # Update telemetry
            self._total_tokens_used += total_tokens
    
    def _track_usage(self, response: ChatCompletion, start_time: datetime) -> None:
        """
        Track token usage and costs.
        
        Args:
            response: The API response
            start_time: Request start time
        """
        duration = (datetime.now() - start_time).total_seconds()
        
        if response.usage:
            tokens = response.usage.total_tokens
            self._total_tokens_used += tokens
            
            # Estimate cost (simplified)
            cost = self._estimate_cost(
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )
            self._total_cost += cost
            
            logger.info(
                f"Request completed in {duration:.2f}s, "
                f"tokens: {tokens}, cost: ${cost:.4f}"
            )
    
    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate the cost of a request.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            
        Returns:
            Estimated cost in USD
        """
        # Simplified cost calculation (update based on current pricing)
        model_costs = {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-turbo-preview": {"prompt": 0.01, "completion": 0.03},
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006}
        }
        
        # Default to gpt-3.5-turbo pricing if model not found
        costs = model_costs.get(self.config.model, model_costs["gpt-3.5-turbo"])
        
        prompt_cost = (prompt_tokens / 1000) * costs["prompt"]
        completion_cost = (completion_tokens / 1000) * costs["completion"]
        
        return prompt_cost + completion_cost
    
    def get_telemetry(self) -> Dict[str, Any]:
        """
        Get telemetry data.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "request_count": self._request_count,
            "total_tokens_used": self._total_tokens_used,
            "total_cost": round(self._total_cost, 4),
            "model": self.config.model,
            "average_tokens_per_request": (
                self._total_tokens_used // self._request_count 
                if self._request_count > 0 else 0
            )
        }
    
    def reset_telemetry(self) -> None:
        """Reset telemetry counters."""
        self._request_count = 0
        self._total_tokens_used = 0
        self._total_cost = 0.0
        logger.info("ChatService telemetry reset")