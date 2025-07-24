"""
Conversation History Manager.

This module provides the ConversationHistory class which is responsible for:
- Maintaining an ordered list of messages across system, user, assistant, and tool roles
- Formatting messages for ChatService
- Supporting context summarization for token management
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """Valid message roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """Represents a single message in the conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Tool-specific fields
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to OpenAI API format."""
        result = {
            "role": self.role.value,
            "content": self.content
        }
        
        # Add tool-specific fields if present
        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id
            
        if self.tool_calls is not None:
            result["tool_calls"] = self.tool_calls
            
        return result
    
    def token_estimate(self) -> int:
        """
        Rough estimate of token count for this message.
        
        Returns:
            Estimated number of tokens
        """
        # Rough approximation: 1 token ≈ 4 characters
        char_count = len(self.content)
        
        # Add overhead for role and formatting
        char_count += len(self.role.value) + 10
        
        # Add tool call overhead if present
        if self.tool_calls:
            char_count += len(json.dumps(self.tool_calls))
            
        return max(1, char_count // 4)


class ConversationHistory:
    """
    Manages conversation history and context.
    
    This class is responsible for:
    - Maintaining conversation state
    - Formatting messages for the AI model
    - Managing context window limits
    - Supporting conversation summarization
    """
    
    def __init__(self, max_messages: int = 100, max_tokens: int = 8000):
        """
        Initialize conversation history.
        
        Args:
            max_messages: Maximum number of messages to keep
            max_tokens: Maximum estimated tokens to keep in context
        """
        self._messages: List[Message] = []
        self._max_messages = max_messages
        self._max_tokens = max_tokens
        self._system_prompt: Optional[Message] = None
        
        logger.info(f"ConversationHistory initialized (max_messages={max_messages}, max_tokens={max_tokens})")
    
    def set_system_prompt(self, prompt: str) -> None:
        """
        Set the system prompt for the conversation.
        
        Args:
            prompt: System prompt text
        """
        self._system_prompt = Message(
            role=MessageRole.SYSTEM,
            content=prompt,
            metadata={"type": "system_prompt"}
        )
        logger.debug("System prompt updated")
    
    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """
        Add a user message to the history.
        
        Args:
            content: Message content
            metadata: Optional metadata
            
        Returns:
            The created message
        """
        message = Message(
            role=MessageRole.USER,
            content=content,
            metadata=metadata or {}
        )
        self._add_message(message)
        return message
    
    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Add an assistant message to the history.
        
        Args:
            content: Message content
            tool_calls: Optional tool calls made by the assistant
            metadata: Optional metadata
            
        Returns:
            The created message
        """
        message = Message(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls,
            metadata=metadata or {}
        )
        self._add_message(message)
        return message
    
    def add_tool_response(
        self,
        tool_call_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Add a tool response message to the history.
        
        Args:
            tool_call_id: ID of the tool call this responds to
            content: Tool response content
            metadata: Optional metadata
            
        Returns:
            The created message
        """
        message = Message(
            role=MessageRole.TOOL,
            content=content,
            tool_call_id=tool_call_id,
            metadata=metadata or {}
        )
        self._add_message(message)
        return message
    
    def _add_message(self, message: Message) -> None:
        """
        Add a message to the history with overflow management.
        
        Args:
            message: Message to add
        """
        self._messages.append(message)
        
        # Enforce message limit
        if len(self._messages) > self._max_messages:
            # Keep the most recent messages
            overflow = len(self._messages) - self._max_messages
            self._messages = self._messages[overflow:]
            logger.debug(f"Trimmed {overflow} old messages")
        
        # Check token limit
        self._enforce_token_limit()
        
        logger.debug(f"Added {message.role.value} message, total messages: {len(self._messages)}")
    
    def _enforce_token_limit(self) -> None:
        """Enforce the token limit by removing old messages if necessary."""
        total_tokens = self._estimate_total_tokens()
        
        if total_tokens <= self._max_tokens:
            return
        
        # Remove messages from the beginning until under limit
        removed_count = 0
        while self._messages and self._estimate_total_tokens() > self._max_tokens:
            self._messages.pop(0)
            removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} messages to stay under token limit")
    
    def _estimate_total_tokens(self) -> int:
        """
        Estimate total token count for all messages.
        
        Returns:
            Estimated total tokens
        """
        total = 0
        
        # Include system prompt
        if self._system_prompt:
            total += self._system_prompt.token_estimate()
        
        # Include all messages
        for message in self._messages:
            total += message.token_estimate()
        
        return total
    
    def get_messages_for_api(self, include_system: bool = True) -> List[Dict[str, Any]]:
        """
        Get messages formatted for OpenAI API.
        
        Args:
            include_system: Whether to include the system prompt
            
        Returns:
            List of message dictionaries
        """
        messages = []
        
        # Add system prompt if requested and available
        if include_system and self._system_prompt:
            messages.append(self._system_prompt.to_dict())
        
        # Add conversation messages
        for message in self._messages:
            messages.append(message.to_dict())
        
        return messages
    
    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """
        Get the most recent messages.
        
        Args:
            count: Number of messages to retrieve
            
        Returns:
            List of recent messages
        """
        return self._messages[-count:] if self._messages else []
    
    def clear(self) -> None:
        """Clear all conversation history except system prompt."""
        self._messages.clear()
        logger.info("Conversation history cleared")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation state.
        
        Returns:
            Dictionary with conversation statistics
        """
        message_counts = {role: 0 for role in MessageRole}
        for message in self._messages:
            message_counts[message.role] += 1
        
        return {
            "total_messages": len(self._messages),
            "message_counts": {role.value: count for role, count in message_counts.items()},
            "estimated_tokens": self._estimate_total_tokens(),
            "has_system_prompt": self._system_prompt is not None,
            "oldest_message": self._messages[0].timestamp.isoformat() if self._messages else None,
            "newest_message": self._messages[-1].timestamp.isoformat() if self._messages else None
        }
    
    def export_conversation(self) -> List[Dict[str, Any]]:
        """
        Export the full conversation for saving or analysis.
        
        Returns:
            List of message dictionaries with full metadata
        """
        messages = []
        
        if self._system_prompt:
            msg_dict = self._system_prompt.to_dict()
            msg_dict["timestamp"] = self._system_prompt.timestamp.isoformat()
            msg_dict["metadata"] = self._system_prompt.metadata
            messages.append(msg_dict)
        
        for message in self._messages:
            msg_dict = message.to_dict()
            msg_dict["timestamp"] = message.timestamp.isoformat()
            msg_dict["metadata"] = message.metadata
            messages.append(msg_dict)
        
        return messages
    
    def import_conversation(self, messages: List[Dict[str, Any]]) -> None:
        """
        Import a conversation from exported format.
        
        Args:
            messages: List of message dictionaries
        """
        self.clear()
        
        for msg_dict in messages:
            role = MessageRole(msg_dict["role"])
            
            # Handle system prompt separately
            if role == MessageRole.SYSTEM:
                self.set_system_prompt(msg_dict["content"])
                continue
            
            # Create message object
            message = Message(
                role=role,
                content=msg_dict["content"],
                timestamp=datetime.fromisoformat(msg_dict.get("timestamp", datetime.now().isoformat())),
                metadata=msg_dict.get("metadata", {}),
                tool_call_id=msg_dict.get("tool_call_id"),
                tool_calls=msg_dict.get("tool_calls")
            )
            
            self._messages.append(message)
        
        logger.info(f"Imported conversation with {len(self._messages)} messages")