"""AI module for TranscribeTalk."""

from .agent import Agent, AgentConfig
from .chat_service import ChatService
from .history import ConversationHistory, Message, MessageRole
from .prompt_engine import PromptEngine
from .tool_scheduler import ToolScheduler, ApprovalMode
from .transcriber import WhisperTranscriber
from .tts import ElevenLabsTTS
from .turn import Turn, SyncTurn
from .loop_detector import LoopDetector
from .chat_compressor import ChatCompressor
from .events import (
    TurnEvent, ContentEvent, ThoughtEvent, ToolCallRequestEvent,
    FunctionResponseEvent, FinishedEvent, ErrorEvent, DebugEvent,
    EventType, ToolCallInfo
)

__all__ = [
    # Core components
    "Agent", "AgentConfig", "ChatService", "ConversationHistory", "Message",
    "MessageRole", "PromptEngine", "ToolScheduler", "ApprovalMode", "Turn",
    "SyncTurn", "LoopDetector", "ChatCompressor",
    # Services
    "WhisperTranscriber", "ElevenLabsTTS",
    # Events
    "TurnEvent", "ContentEvent", "ThoughtEvent", "ToolCallRequestEvent",
    "FunctionResponseEvent", "FinishedEvent", "ErrorEvent", "DebugEvent",
    "EventType", "ToolCallInfo"
]