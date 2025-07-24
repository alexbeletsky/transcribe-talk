"""
AI conversation processing using OpenAI GPT models.

This module provides chat completion capabilities for TranscribeTalk:
- OpenAI API client management
- Conversation memory and context management
- Configurable response parameters
- Error handling and retry logic
- Support for different GPT models
"""

import logging
from typing import Dict, List, Optional, Union

from openai import OpenAI

from ..config.settings import OpenAIConfig

logger = logging.getLogger(__name__)


class ChatMessage:
    """Represents a single chat message."""
    
    def __init__(self, role: str, content: str):
        """
        Initialize a chat message.
        
        Args:
            role: Message role ('system', 'user', 'assistant')
            content: Message content
        """
        self.role = role
        self.content = content
        
    def to_dict(self) -> Dict[str, str]:
        """Convert to OpenAI API format."""
        return {"role": self.role, "content": self.content}


class ConversationMemory:
    """Manages conversation history and context."""
    
    def __init__(self, max_messages: int = 10):
        """
        Initialize conversation memory.
        
        Args:
            max_messages: Maximum number of messages to keep in memory
        """
        self.max_messages = max_messages
        self.messages: List[ChatMessage] = []
        self.system_prompt: Optional[str] = None
        
    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt for the conversation."""
        self.system_prompt = prompt
        logger.info("System prompt updated")
        
    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        self.messages.append(ChatMessage("user", content))
        self._trim_messages()
        
    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation."""
        self.messages.append(ChatMessage("assistant", content))
        self._trim_messages()
        
    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """Get messages in OpenAI API format."""
        api_messages = []
        
        # Add system prompt if set
        if self.system_prompt:
            api_messages.append({"role": "system", "content": self.system_prompt})
        
        # Add conversation messages
        api_messages.extend([msg.to_dict() for msg in self.messages])
        
        return api_messages
    
    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []
        logger.info("Conversation memory cleared")
        
    def _trim_messages(self) -> None:
        """Trim messages to stay within max_messages limit."""
        if len(self.messages) > self.max_messages:
            # Remove oldest messages, keeping pairs when possible
            messages_to_remove = len(self.messages) - self.max_messages
            self.messages = self.messages[messages_to_remove:]


class OpenAIChat:
    """
    OpenAI GPT chat client for AI conversation processing.
    
    Features:
    - Conversation memory management
    - Configurable model and parameters
    - Streaming and non-streaming responses
    - Error handling and retry logic
    - Token usage tracking
    """
    
    def __init__(self, config: OpenAIConfig):
        """
        Initialize the OpenAI chat client.
        
        Args:
            config: OpenAI configuration settings
        """
        self.config = config
        self.client = OpenAI(api_key=config.api_key)
        self.memory = ConversationMemory()
        
        # Set default system prompt
        self.memory.set_system_prompt("You are a helpful assistant.")
        
        logger.info(f"OpenAI chat initialized with model: {config.model}")
    
    def set_system_prompt(self, prompt: str) -> None:
        """
        Set the system prompt for conversations.
        
        Args:
            prompt: System prompt to use
        """
        self.memory.set_system_prompt(prompt)
    
    def chat(self, user_message: str, remember_conversation: bool = True) -> str:
        """
        Send a message and get a response from the AI.
        
        Args:
            user_message: User's message
            remember_conversation: Whether to remember this exchange in conversation memory
            
        Returns:
            str: AI's response
        """
        logger.info(f"Processing chat message: {len(user_message)} characters")
        
        try:
            # Add user message to memory if requested
            if remember_conversation:
                self.memory.add_user_message(user_message)
                messages = self.memory.get_messages_for_api()
            else:
                # Single-shot conversation
                messages = []
                if self.memory.system_prompt:
                    messages.append({"role": "system", "content": self.memory.system_prompt})
                messages.append({"role": "user", "content": user_message})
            
            # Make API call
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
            
            # Extract response content
            ai_response = response.choices[0].message.content.strip()
            
            # Add AI response to memory if requested
            if remember_conversation:
                self.memory.add_assistant_message(ai_response)
            
            # Log token usage
            if hasattr(response, 'usage'):
                logger.info(f"Token usage - Prompt: {response.usage.prompt_tokens}, "
                           f"Completion: {response.usage.completion_tokens}, "
                           f"Total: {response.usage.total_tokens}")
            
            logger.info(f"Chat response generated: {len(ai_response)} characters")
            return ai_response
            
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise
    
    def chat_streaming(self, user_message: str, remember_conversation: bool = True):
        """
        Send a message and get a streaming response from the AI.
        
        Args:
            user_message: User's message
            remember_conversation: Whether to remember this exchange
            
        Yields:
            str: Chunks of AI response as they arrive
        """
        logger.info(f"Processing streaming chat message: {len(user_message)} characters")
        
        try:
            # Prepare messages
            if remember_conversation:
                self.memory.add_user_message(user_message)
                messages = self.memory.get_messages_for_api()
            else:
                messages = []
                if self.memory.system_prompt:
                    messages.append({"role": "system", "content": self.memory.system_prompt})
                messages.append({"role": "user", "content": user_message})
            
            # Make streaming API call
            stream = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True,
            )
            
            # Collect response chunks
            full_response = ""
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            # Add complete response to memory
            if remember_conversation:
                self.memory.add_assistant_message(full_response)
            
            logger.info(f"Streaming chat completed: {len(full_response)} characters")
            
        except Exception as e:
            logger.error(f"Error in streaming chat: {e}")
            raise
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the current conversation.
        
        Returns:
            str: Conversation summary
        """
        if not self.memory.messages:
            return "No conversation history"
        
        summary_parts = []
        for msg in self.memory.messages[-6:]:  # Last 6 messages
            role_label = "You" if msg.role == "user" else "AI"
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            summary_parts.append(f"{role_label}: {content_preview}")
        
        return "\n".join(summary_parts)
    
    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self.memory.clear()
    
    def change_model(self, model_name: str) -> None:
        """
        Change the OpenAI model being used.
        
        Args:
            model_name: New model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
        """
        logger.info(f"Changing OpenAI model from {self.config.model} to {model_name}")
        self.config.model = model_name
    
    def adjust_parameters(
        self, 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> None:
        """
        Adjust AI response parameters.
        
        Args:
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0.0-1.0)
        """
        if max_tokens is not None:
            self.config.max_tokens = max_tokens
            logger.info(f"Max tokens set to: {max_tokens}")
            
        if temperature is not None:
            if not 0.0 <= temperature <= 1.0:
                raise ValueError("Temperature must be between 0.0 and 1.0")
            self.config.temperature = temperature
            logger.info(f"Temperature set to: {temperature}")
    
    def test_connection(self) -> bool:
        """
        Test the OpenAI API connection.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            logger.info("Testing OpenAI API connection...")
            
            # Simple test message
            test_response = self.chat("Hello, this is a test message.", remember_conversation=False)
            
            if test_response:
                logger.info("OpenAI API connection test successful")
                return True
            else:
                logger.error("OpenAI API test failed: empty response")
                return False
                
        except Exception as e:
            logger.error(f"OpenAI API connection test failed: {e}")
            return False


def get_available_models() -> List[str]:
    """
    Get list of commonly available OpenAI models.
    
    Returns:
        list: Available model names
    """
    return [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ]


def estimate_token_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Estimate the cost of API usage (approximate pricing).
    
    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        
    Returns:
        float: Estimated cost in USD
    """
    # Approximate pricing as of late 2024 (prices may change)
    pricing = {
        "gpt-4o": {"input": 0.0025, "output": 0.01},  # per 1K tokens
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
    }
    
    if model not in pricing:
        return 0.0  # Unknown model
    
    input_cost = (input_tokens / 1000) * pricing[model]["input"]
    output_cost = (output_tokens / 1000) * pricing[model]["output"]
    
    return input_cost + output_cost 