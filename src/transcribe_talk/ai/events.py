"""
Event definitions for the agentic architecture.

This module defines the event types that are yielded by the Turn class
during conversation processing.
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class EventType(Enum):
    """Types of events that can occur during a turn."""
    CONTENT = "content"
    THOUGHT = "thought"
    TOOL_CALL_REQUEST = "tool_call_request"
    FUNCTION_RESPONSE = "function_response"
    FINISHED = "finished"
    ERROR = "error"
    DEBUG = "debug"


@dataclass
class BaseEvent:
    """Base class for all events."""
    type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentEvent(BaseEvent):
    """Event for text content from the model."""
    type: EventType = field(default=EventType.CONTENT, init=False)
    content: str = ""
    is_partial: bool = True  # Whether this is a partial chunk or complete


@dataclass
class ThoughtEvent(BaseEvent):
    """Event for model reasoning/thought content."""
    type: EventType = field(default=EventType.THOUGHT, init=False)
    thought: str = ""
    
    
@dataclass 
class ToolCallInfo:
    """Information about a tool call request."""
    id: str
    name: str
    arguments: Dict[str, Any]
    

@dataclass
class ToolCallRequestEvent(BaseEvent):
    """Event for tool call requests from the model."""
    type: EventType = field(default=EventType.TOOL_CALL_REQUEST, init=False)
    tool_calls: List[ToolCallInfo] = field(default_factory=list)
    

@dataclass
class FunctionResponseEvent(BaseEvent):
    """Event for tool execution results."""
    type: EventType = field(default=EventType.FUNCTION_RESPONSE, init=False)
    tool_call_id: str = ""
    result: str = ""
    success: bool = True
    error_message: Optional[str] = None
    

@dataclass
class FinishedEvent(BaseEvent):
    """Event indicating the turn has completed."""
    type: EventType = field(default=EventType.FINISHED, init=False)
    has_tool_calls: bool = False
    finish_reason: str = "stop"
    usage: Optional[Dict[str, int]] = None  # Token usage stats
    

@dataclass
class ErrorEvent(BaseEvent):
    """Event for errors during turn processing."""
    type: EventType = field(default=EventType.ERROR, init=False)
    error_type: str = ""
    error_message: str = ""
    recoverable: bool = True
    

@dataclass
class DebugEvent(BaseEvent):
    """Event for debug information."""
    type: EventType = field(default=EventType.DEBUG, init=False)
    message: str = ""
    data: Optional[Any] = None


# Type alias for all event types
TurnEvent = Union[
    ContentEvent,
    ThoughtEvent,
    ToolCallRequestEvent,
    FunctionResponseEvent,
    FinishedEvent,
    ErrorEvent,
    DebugEvent
]