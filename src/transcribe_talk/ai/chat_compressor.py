"""
Chat compression service for managing long conversations.

This module provides functionality to compress/summarize long conversation
histories to stay within token limits while preserving important context.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .history import ConversationHistory, Message, MessageRole
from .chat_service import ChatService

logger = logging.getLogger(__name__)


class ChatCompressor:
    """
    Compresses long conversations by summarizing older messages.
    
    This helps maintain context while staying within token limits
    for very long conversations.
    """
    
    def __init__(
        self,
        chat_service: ChatService,
        compression_threshold: int = 6000,
        target_size: int = 3000,
        preserve_recent: int = 10
    ):
        """
        Initialize the chat compressor.
        
        Args:
            chat_service: ChatService for generating summaries
            compression_threshold: Token count that triggers compression
            target_size: Target token count after compression
            preserve_recent: Number of recent messages to always preserve
        """
        self.chat_service = chat_service
        self.compression_threshold = compression_threshold
        self.target_size = target_size
        self.preserve_recent = preserve_recent
        
        logger.info(
            f"ChatCompressor initialized: threshold={compression_threshold}, "
            f"target={target_size}, preserve_recent={preserve_recent}"
        )
    
    async def should_compress(self, history: ConversationHistory) -> bool:
        """
        Check if compression is needed.
        
        Args:
            history: The conversation history
            
        Returns:
            True if compression should be performed
        """
        total_tokens = sum(msg.token_estimate() for msg in history.messages)
        return total_tokens > self.compression_threshold
    
    async def compress_history(
        self, 
        history: ConversationHistory
    ) -> Tuple[ConversationHistory, str]:
        """
        Compress the conversation history.
        
        Args:
            history: The conversation history to compress
            
        Returns:
            Tuple of (new compressed history, summary of compressed content)
        """
        messages = history.messages
        
        if len(messages) <= self.preserve_recent:
            logger.info("Not enough messages to compress")
            return history, ""
        
        # Split messages into parts
        recent_messages = messages[-self.preserve_recent:]
        older_messages = messages[:-self.preserve_recent]
        
        # Check if we need to compress
        older_tokens = sum(msg.token_estimate() for msg in older_messages)
        if older_tokens < 1000:  # Not worth compressing
            logger.info("Older messages too small to compress")
            return history, ""
        
        try:
            # Generate summary of older messages
            summary = await self._generate_summary(older_messages)
            
            # Create new history with compressed content
            new_history = ConversationHistory(
                max_messages=history.max_messages,
                max_tokens=history.max_tokens
            )
            
            # Add system message with summary
            summary_message = Message(
                role=MessageRole.SYSTEM,
                content=f"Previous conversation summary:\n{summary}",
                timestamp=older_messages[0].timestamp
            )
            new_history.add_message(summary_message)
            
            # Add preserved recent messages
            for msg in recent_messages:
                new_history.messages.append(msg)
            
            # Calculate compression ratio
            old_tokens = sum(msg.token_estimate() for msg in messages)
            new_tokens = sum(msg.token_estimate() for msg in new_history.messages)
            compression_ratio = 1 - (new_tokens / old_tokens)
            
            logger.info(
                f"Compressed history: {len(messages)} -> {len(new_history.messages)} messages, "
                f"{old_tokens} -> {new_tokens} tokens ({compression_ratio:.1%} reduction)"
            )
            
            return new_history, summary
            
        except Exception as e:
            logger.error(f"Failed to compress history: {e}")
            return history, ""
    
    async def _generate_summary(self, messages: List[Message]) -> str:
        """
        Generate a summary of the messages.
        
        Args:
            messages: Messages to summarize
            
        Returns:
            Summary text
        """
        # Prepare the summarization prompt
        conversation_text = self._format_messages_for_summary(messages)
        
        summary_prompt = f"""Please provide a concise summary of the following conversation.
Focus on:
1. Key topics discussed
2. Important decisions or conclusions
3. Any user preferences or context that should be remembered
4. Tool usage patterns or results

Keep the summary under 500 words.

Conversation:
{conversation_text}

Summary:"""
        
        # Use chat service to generate summary
        summary_messages = [
            {"role": "system", "content": "You are a helpful assistant that creates concise conversation summaries."},
            {"role": "user", "content": summary_prompt}
        ]
        
        response = await self.chat_service.send_message_async(
            messages=summary_messages,
            temperature=0.3,
            max_tokens=600
        )
        
        return response.content.strip()
    
    def _format_messages_for_summary(self, messages: List[Message]) -> str:
        """
        Format messages for summarization.
        
        Args:
            messages: Messages to format
            
        Returns:
            Formatted text
        """
        lines = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                continue  # Skip system messages
            
            role = msg.role.value.capitalize()
            content = msg.content
            
            # Truncate very long messages
            if len(content) > 500:
                content = content[:500] + "..."
            
            lines.append(f"{role}: {content}")
        
        return "\n\n".join(lines)
    
    def get_compression_stats(self, history: ConversationHistory) -> Dict[str, Any]:
        """
        Get statistics about potential compression.
        
        Args:
            history: The conversation history
            
        Returns:
            Dictionary with compression statistics
        """
        messages = history.messages
        total_tokens = sum(msg.token_estimate() for msg in messages)
        
        if len(messages) <= self.preserve_recent:
            return {
                "can_compress": False,
                "reason": "Not enough messages",
                "total_messages": len(messages),
                "total_tokens": total_tokens
            }
        
        older_messages = messages[:-self.preserve_recent]
        older_tokens = sum(msg.token_estimate() for msg in older_messages)
        recent_tokens = sum(msg.token_estimate() for msg in messages[-self.preserve_recent:])
        
        return {
            "can_compress": total_tokens > self.compression_threshold,
            "total_messages": len(messages),
            "total_tokens": total_tokens,
            "older_messages": len(older_messages),
            "older_tokens": older_tokens,
            "recent_messages": self.preserve_recent,
            "recent_tokens": recent_tokens,
            "estimated_reduction": older_tokens - 500  # Rough estimate
        }