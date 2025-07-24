"""
Loop detection service for preventing infinite tool call loops.

This module provides functionality to detect when the same tool
is being called repeatedly with the same arguments, which could
indicate an infinite loop.
"""

import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ToolCallRecord:
    """Record of a tool call for loop detection."""
    tool_name: str
    arguments_hash: str
    timestamp: datetime
    count: int = 1
    
    def increment(self):
        """Increment the count and update timestamp."""
        self.count += 1
        self.timestamp = datetime.now()


class LoopDetector:
    """
    Detects potential infinite loops in tool calls.
    
    A loop is detected when:
    1. The same tool is called with the same arguments
    2. More than `max_repetitions` times
    3. Within `time_window` seconds
    """
    
    def __init__(
        self,
        max_repetitions: int = 3,
        time_window: int = 60,
        strict_mode: bool = False
    ):
        """
        Initialize the loop detector.
        
        Args:
            max_repetitions: Maximum allowed repetitions before loop is detected
            time_window: Time window in seconds to consider for loop detection
            strict_mode: If True, any repetition is considered a loop
        """
        self.max_repetitions = max_repetitions if not strict_mode else 1
        self.time_window = timedelta(seconds=time_window)
        self.strict_mode = strict_mode
        
        # Track tool calls: key = (tool_name, args_hash), value = ToolCallRecord
        self._call_history: Dict[Tuple[str, str], ToolCallRecord] = {}
        
        # Track all calls for reporting
        self._all_calls: List[Tuple[str, Dict[str, Any], datetime]] = []
        
        logger.info(
            f"LoopDetector initialized: max_repetitions={self.max_repetitions}, "
            f"time_window={time_window}s, strict_mode={strict_mode}"
        )
    
    def check_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """
        Check if a tool call would create a loop.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Arguments passed to the tool
            
        Returns:
            True if this call would create a loop, False otherwise
        """
        # Store the call for history
        self._all_calls.append((tool_name, arguments.copy(), datetime.now()))
        
        # Create a stable hash of the arguments
        args_hash = self._hash_arguments(arguments)
        key = (tool_name, args_hash)
        
        now = datetime.now()
        
        # Clean up old entries outside the time window
        self._cleanup_old_entries(now)
        
        # Check if we've seen this call before
        if key in self._call_history:
            record = self._call_history[key]
            
            # Check if it's within the time window
            if now - record.timestamp <= self.time_window:
                record.increment()
                
                if record.count > self.max_repetitions:
                    logger.warning(
                        f"Loop detected: {tool_name} called {record.count} times "
                        f"with same arguments within {self.time_window.seconds}s"
                    )
                    return True
            else:
                # Outside time window, reset the count
                record.count = 1
                record.timestamp = now
        else:
            # First time seeing this call
            self._call_history[key] = ToolCallRecord(
                tool_name=tool_name,
                arguments_hash=args_hash,
                timestamp=now
            )
        
        return False
    
    def _hash_arguments(self, arguments: Dict[str, Any]) -> str:
        """
        Create a stable hash of the arguments.
        
        Args:
            arguments: Tool arguments
            
        Returns:
            Stable hash string
        """
        # Sort keys for consistent ordering
        sorted_args = json.dumps(arguments, sort_keys=True)
        return str(hash(sorted_args))
    
    def _cleanup_old_entries(self, current_time: datetime):
        """
        Remove entries outside the time window.
        
        Args:
            current_time: Current timestamp
        """
        keys_to_remove = []
        
        for key, record in self._call_history.items():
            if current_time - record.timestamp > self.time_window:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._call_history[key]
    
    def get_call_summary(self) -> str:
        """
        Get a summary of recent tool calls.
        
        Returns:
            Human-readable summary of tool calls
        """
        if not self._call_history:
            return "No repeated tool calls detected."
        
        lines = ["Recent repeated tool calls:"]
        
        for (tool_name, _), record in self._call_history.items():
            if record.count > 1:
                lines.append(
                    f"  - {tool_name}: {record.count} calls "
                    f"(last at {record.timestamp.strftime('%H:%M:%S')})"
                )
        
        return "\n".join(lines)
    
    def get_full_history(self) -> List[Tuple[str, Dict[str, Any], datetime]]:
        """
        Get the full history of all tool calls.
        
        Returns:
            List of (tool_name, arguments, timestamp) tuples
        """
        return self._all_calls.copy()
    
    def reset(self):
        """Reset the loop detector state."""
        self._call_history.clear()
        self._all_calls.clear()
        logger.info("LoopDetector state reset")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about tool calls.
        
        Returns:
            Dictionary with statistics
        """
        total_calls = len(self._all_calls)
        unique_calls = len(set((name, self._hash_arguments(args)) 
                              for name, args, _ in self._all_calls))
        
        tool_counts = {}
        for name, _, _ in self._all_calls:
            tool_counts[name] = tool_counts.get(name, 0) + 1
        
        return {
            "total_calls": total_calls,
            "unique_calls": unique_calls,
            "repeated_calls": total_calls - unique_calls,
            "tool_counts": tool_counts,
            "active_tracking": len(self._call_history)
        }