# TranscribeTalk Architecture Documentation

**Version 2.0 - Agentic Architecture Implementation**  
**Status:** Production Ready with Agentic Capabilities  
**Last Updated:** January 2025

This document serves as the definitive architectural reference for TranscribeTalk, a sophisticated CLI application that combines voice-to-voice AI conversations with agentic tool-calling capabilities.

---

## 1. Executive Summary

TranscribeTalk has evolved from a simple voice-to-voice application into a comprehensive conversational AI agent system. The architecture follows an event-driven, modular design inspired by production systems like `gemini-cli`, enabling sophisticated human-AI interactions with tool integration.

### Core Capabilities

- **Voice-to-Voice Conversations**: Seamless speech-to-text, AI processing, and text-to-speech
- **Agentic Tool Integration**: AI can interact with the local environment through structured tools
- **Event-Driven Architecture**: Modular, async-first design for scalability and maintainability
- **Production-Ready Safety**: Comprehensive error handling, timeouts, and user confirmations
- **Long-Term Memory**: Persistent context management across conversations
- **Advanced Hardening**: Loop detection, chat compression, and performance optimization

---

## 2. High-Level Architecture

### 2.1 Architectural Pattern

The system follows a **layered, event-driven architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Interface Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Interactive UI  │  │  One-Shot Mode  │  │ Config Manager  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │     Agent       │  │      Turn       │  │ Event System    │ │
│  │  (Coordinator)  │  │  (Interaction)  │  │ (Communication) │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Voice I/O      │  │   AI Services   │  │ Tool Management │ │
│  │ (Audio/TTS)     │  │ (LLM/Context)   │  │ (Discovery/Exec)│ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                     Infrastructure Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Configuration   │  │    Utilities    │  │    External     │ │
│  │   Management    │  │   & Helpers     │  │   APIs/Tools    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Overview

```
User Voice Input → Audio Recording → Speech-to-Text →
Agent Orchestration → AI Processing ↔ Tool Execution →
Text-to-Speech → Audio Playback → User
                     ↕
             Conversation History & Memory
```

---

## 3. Directory Structure

```
transcribe-talk/
├── README.md                     # Project overview and usage
├── ARCHITECTURE.md               # This document
├── AGENT.md                      # Agentic features documentation
├── SUMMARY.md                    # Implementation summary
├── GEMINICLI.md                 # Architecture inspiration
├── pyproject.toml               # Project configuration and dependencies
├── requirements.txt             # Pinned dependencies
├── .env.example                 # Environment variable template
├── src/transcribe_talk/         # Main application package
│   ├── __init__.py             # Package initialization
│   ├── cli.py                  # CLI entry point and commands (822 lines)
│   ├── audio/                  # Voice I/O layer
│   │   ├── __init__.py
│   │   ├── recorder.py         # Audio recording functionality
│   │   └── player.py           # Audio playback with format support
│   ├── ai/                     # AI services and orchestration
│   │   ├── __init__.py         # AI module exports (30 lines)
│   │   ├── agent.py            # Central orchestrator (427 lines)
│   │   ├── turn.py             # Interaction cycle manager (388 lines)
│   │   ├── events.py           # Event system definitions (108 lines)
│   │   ├── chat_service.py     # OpenAI API interface (319 lines)
│   │   ├── history.py          # Conversation management (364 lines)
│   │   ├── prompt_engine.py    # Context assembly (296 lines)
│   │   ├── tool_scheduler.py   # Tool execution manager (395 lines)
│   │   ├── loop_detector.py    # Infinite loop prevention (209 lines)
│   │   ├── chat_compressor.py  # Memory management (234 lines)
│   │   ├── transcriber.py      # Speech-to-text service (170 lines)
│   │   ├── tts.py              # Text-to-speech service (388 lines)
│   │   ├── chat.py             # Additional chat utilities (361 lines)
│   │   └── ai_legacy/          # Preserved legacy implementations
│   │       ├── __init__.py
│   │       ├── chat.py         # Original chat implementation
│   │       └── transcriber.py  # Original transcriber
│   ├── tools/                  # Tool system
│   │   ├── __init__.py         # Tool module exports (23 lines)
│   │   ├── tool_registry.py    # Tool discovery and registration (282 lines)
│   │   ├── file_system.py      # File system tools (339 lines)
│   │   └── memory.py           # Memory management tools (201 lines)
│   ├── config/                 # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py         # Pydantic-based configuration
│   └── utils/                  # Shared utilities
│       ├── __init__.py
│       └── helpers.py          # Common utility functions
└── tests/                      # Test infrastructure
    └── implementation_verification/  # Phase-based verification tests
        ├── README.md           # Test documentation
        ├── test_phase1.py      # Foundational architecture tests
        ├── test_phase2.py      # MVP agentic loop tests
        ├── test_phase3.py      # Expanded capabilities tests
        └── test_phase4_simple.py  # Advanced hardening tests
```

---

## 4. Core Components

### 4.1 Orchestration Layer

#### Agent (`ai/agent.py`)

**Role:** Central coordinator and conversation orchestrator

**Responsibilities:**

- Initialize and manage all core components (ChatService, PromptEngine, ToolScheduler, etc.)
- Orchestrate the agentic conversation loop
- Enforce safety limits (max turns, tool calls, timeouts)
- Manage conversation state and lifecycle
- Handle chat compression for long conversations

**Key Features:**

- Event-driven async architecture
- Comprehensive telemetry and logging
- Safety guardrails with configurable limits
- Automatic chat compression when token limits approached
- Support for both interactive and automated modes

#### Turn (`ai/turn.py`)

**Role:** Manages individual interaction cycles with the LLM

**Responsibilities:**

- Process streaming responses from OpenAI API
- Generate structured events (Content, ToolRequest, Finished, Error)
- Handle token usage tracking with OpenAI's streaming API
- Integrate with loop detection for safety
- Manage interaction state and telemetry

**Key Features:**

- Async streaming response processing
- Comprehensive event generation
- Token usage tracking with `stream_options={"include_usage": True}`
- Loop detection integration
- Debug response collection

#### Event System (`ai/events.py`)

**Role:** Structured communication between components

**Event Types:**

- `ContentEvent`: Text content from AI responses
- `ThoughtEvent`: AI reasoning information
- `ToolCallRequestEvent`: Tool execution requests
- `FunctionResponseEvent`: Tool execution results
- `FinishedEvent`: Interaction completion
- `ErrorEvent`: Error conditions
- `DebugEvent`: Development and debugging information

### 4.2 AI Services Layer

#### ChatService (`ai/chat_service.py`)

**Role:** OpenAI API interface and communication manager

**Responsibilities:**

- Manage OpenAI API connections and authentication
- Support both streaming and non-streaming modes
- Implement retry logic for transient errors
- Track token usage and API costs
- Handle API-level error conditions

**Key Features:**

- Async and sync API support
- Comprehensive telemetry tracking
- Token usage monitoring with streaming support
- Retry mechanisms with exponential backoff
- Cost estimation and budget tracking

#### PromptEngine (`ai/prompt_engine.py`)

**Role:** Context assembly and prompt generation

**Responsibilities:**

- Build system prompts with environmental context
- Load and integrate long-term memory from CONTEXT.md
- Assemble conversation context for AI
- Manage prompt templates and formatting

**Key Features:**

- Dynamic context integration
- Long-term memory loading
- Environmental context (OS, workspace info)
- Customizable prompt templates

#### ConversationHistory (`ai/history.py`)

**Role:** Conversation state and message management

**Responsibilities:**

- Maintain ordered conversation messages
- Format messages for OpenAI API compatibility
- Manage conversation limits (message count, token count)
- Support conversation import/export
- Handle different message roles (system, user, assistant, tool)

**Key Features:**

- Automatic token counting and limits
- Message role management
- API format conversion
- Conversation summarization support

### 4.3 Tool Management Layer

#### ToolRegistry (`tools/tool_registry.py`)

**Role:** Tool discovery, registration, and schema generation

**Responsibilities:**

- Register tool implementations with metadata
- Generate OpenAI function schemas from Python signatures
- Provide tool lookup and categorization
- Manage tool metadata (timeouts, confirmations, categories)

**Key Features:**

- Automatic schema generation from Python functions
- Tool categorization (FILE_SYSTEM, MEMORY, WEB, etc.)
- Metadata-driven configuration
- Type-safe parameter handling

#### ToolScheduler (`ai/tool_scheduler.py`)

**Role:** Tool execution lifecycle management

**Responsibilities:**

- Validate and execute tool call requests
- Manage approval workflows (NEVER, SMART, ALWAYS)
- Enforce timeouts and safety limits
- Handle concurrent tool execution
- Format results for AI consumption

**Key Features:**

- Multi-mode approval system
- Concurrent execution with thread pools
- Comprehensive timeout handling
- Dry-run simulation support
- Detailed execution telemetry

#### Available Tools

**File System Tools** (`tools/file_system.py`):

- `list_directory`: Directory content listing with formatting
- `read_file`: Text file reading with preview mode for large files
- `write_file`: File creation/modification with safety checks

**Memory Tools** (`tools/memory.py`):

- `save_memory`: Save categorized information to CONTEXT.md
- `read_memory`: Retrieve memories with filtering options

### 4.4 Safety & Robustness Layer

#### LoopDetector (`ai/loop_detector.py`)

**Role:** Infinite loop prevention

**Responsibilities:**

- Track tool call patterns within time windows
- Detect repetitive tool calls with identical arguments
- Provide statistics and reporting
- Break loops automatically with error reporting

#### ChatCompressor (`ai/chat_compressor.py`)

**Role:** Long conversation management

**Responsibilities:**

- Monitor conversation token usage
- Compress long conversations using AI summarization
- Preserve recent messages while summarizing older content
- Maintain conversation quality while reducing token usage

### 4.5 Voice I/O Layer

#### AudioRecorder (`audio/recorder.py`)

**Role:** Voice input capture

**Features:**

- Multi-threaded recording with sounddevice
- Configurable sample rates and audio settings
- Real-time audio buffering
- Context manager support for cleanup

#### AudioPlayer (`audio/player.py`)

**Role:** Audio output and TTS playback

**Features:**

- Multiple audio format support (WAV, MP3)
- Integration with ElevenLabs TTS output
- Cross-platform compatibility
- Enhanced audio library support (soundfile, librosa)

#### WhisperTranscriber (`ai/transcriber.py`)

**Role:** Speech-to-text conversion

**Features:**

- OpenAI Whisper integration
- Multiple model sizes (tiny → large)
- Model caching for performance
- Language detection and multilingual support

#### ElevenLabsTTS (`ai/tts.py`)

**Role:** Text-to-speech synthesis

**Features:**

- ElevenLabs API integration
- Voice selection and management
- Multiple audio formats
- Streaming and non-streaming synthesis

---

## 5. Configuration Architecture

### 5.1 Configuration System (`config/settings.py`)

Uses **Pydantic** models for type-safe configuration:

```python
class Settings(BaseModel):
    openai: OpenAIConfig
    elevenlabs: ElevenLabsConfig
    whisper: WhisperConfig
    audio: AudioConfig
    logging: LoggingConfig
    debug: bool = False
```

### 5.2 Environment Variables

| Variable             | Description                   | Default                |
| -------------------- | ----------------------------- | ---------------------- |
| `OPENAI_API_KEY`     | OpenAI API key (required)     | -                      |
| `ELEVENLABS_API_KEY` | ElevenLabs API key (required) | -                      |
| `WHISPER_MODEL`      | Whisper model size            | `base`                 |
| `OPENAI_MODEL`       | OpenAI model                  | `gpt-4o-mini`          |
| `OPENAI_MAX_TOKENS`  | Max response tokens           | `200`                  |
| `TTS_VOICE_ID`       | ElevenLabs voice ID           | `wyWA56cQNU2KqUW4eCsI` |
| `AUDIO_SAMPLE_RATE`  | Audio sample rate             | `16000`                |

---

## 6. CLI Interface

### 6.1 Command Structure

```bash
transcribe-talk [OPTIONS] COMMAND [ARGS]...

Commands:
  interactive    # Default mode - voice conversation
  once          # One-shot processing
  config        # Configuration management

Global Options:
  --debug                    # Enable debug mode
  --log-level LEVEL         # Set logging level
  --model MODEL             # Whisper model selection
  --voice VOICE_ID          # ElevenLabs voice
  --tokens INTEGER          # Max AI response tokens
  --auto-confirm, -y        # Auto-confirm tool executions
  --dry-run                 # Simulate tool executions
```

### 6.2 Interactive Session (`InteractiveSession` class)

**Features:**

- Voice recording with visual feedback
- Real-time transcription display
- Streaming AI responses
- Tool execution with confirmation flows
- Conversation history management
- Graceful shutdown handling

---

## 7. Dependencies & Technology Stack

### 7.1 Core Dependencies

```python
# AI & ML
openai-whisper==20231117      # Speech-to-text
openai==1.12.0               # LLM API
elevenlabs==0.2.26           # Text-to-speech

# Audio Processing
sounddevice==0.4.6           # Audio I/O
numpy==1.24.3                # Numerical computing
scipy==1.11.4                # Scientific computing

# Framework & UI
click==8.1.7                 # CLI framework
rich==13.7.0                 # Terminal UI
pydantic==2.5.3              # Configuration validation

# Async & Utils
aiofiles==23.2.1             # Async file operations
python-dotenv==1.0.0         # Environment management
```

### 7.2 Development Dependencies

```python
pytest==7.4.4               # Testing framework
pytest-asyncio==0.21.1      # Async testing
black==23.12.1               # Code formatting
mypy==1.8.0                  # Type checking
```

---

## 8. Design Patterns & Principles

### 8.1 Architectural Patterns

- **Event-Driven Architecture**: Decoupled communication via structured events
- **Layered Architecture**: Clear separation of concerns across layers
- **Dependency Injection**: Configuration and service injection
- **Template Method**: Standardized tool execution patterns
- **Observer Pattern**: Event-based communication

### 8.2 Design Principles

- **Single Responsibility**: Each component has one clear purpose
- **Open/Closed**: Extensible design for new tools and services
- **Dependency Inversion**: High-level modules don't depend on low-level details
- **Interface Segregation**: Minimal, focused interfaces
- **Async-First**: Non-blocking operations throughout

### 8.3 Safety Principles

- **Fail-Safe Defaults**: Conservative defaults for all operations
- **User Confirmation**: Required for potentially destructive operations
- **Timeout Protection**: All operations have configurable timeouts
- **Resource Limits**: Conversation and tool execution limits
- **Error Recovery**: Graceful handling of all error conditions

---

## 9. Performance & Scalability

### 9.1 Performance Optimizations

- **Async/Await**: Non-blocking I/O throughout the system
- **Streaming Responses**: Real-time AI response processing
- **Model Caching**: Whisper model loading optimization
- **Token Management**: Efficient conversation compression
- **Concurrent Tool Execution**: Parallel tool processing

### 9.2 Resource Management

- **Memory Limits**: Automatic conversation compression at 6000 tokens
- **File Size Limits**: 10MB maximum for file reading operations
- **Timeout Management**: 30-second default tool timeouts
- **Connection Pooling**: Efficient API connection management

---

## 10. Testing Strategy

### 10.1 Test Architecture

Tests are organized by implementation phases:

- **Phase 1**: Foundational architecture verification
- **Phase 2**: MVP agentic loop testing
- **Phase 3**: Expanded capabilities validation
- **Phase 4**: Advanced hardening verification

### 10.2 Test Coverage

- Component initialization and integration
- Event flow and communication
- Tool registration and execution
- Safety mechanism validation
- Error handling and recovery

---

## 11. Security Considerations

### 11.1 File System Security

- **Workspace Boundaries**: Tools restricted to current workspace by default
- **Path Validation**: Prevention of directory traversal attacks
- **File Size Limits**: Protection against resource exhaustion
- **Permission Checks**: Proper handling of file system permissions

### 11.2 API Security

- **API Key Management**: Secure storage and handling of credentials
- **Rate Limiting**: Respect for API provider limits
- **Error Information**: Careful handling of sensitive error details
- **Request Validation**: Input sanitization for all API calls

---

## 12. Monitoring & Observability

### 12.1 Logging Architecture

- **Structured Logging**: Rich console output with detailed information
- **Level-Based**: DEBUG, INFO, WARNING, ERROR, CRITICAL levels
- **Component Identification**: Clear source identification for all logs
- **Performance Metrics**: Request timing and token usage tracking

### 12.2 Telemetry

- **Conversation Metrics**: Turn count, token usage, cost estimation
- **Tool Metrics**: Execution count, success rate, timing
- **Error Tracking**: Comprehensive error categorization and reporting
- **Performance Monitoring**: API response times and system resource usage

---

## 13. Future Architecture Considerations

### 13.1 Planned Enhancements

- **Plugin Architecture**: Dynamic tool loading and management
- **Multi-Modal Support**: Image, video, and document processing
- **Distributed Processing**: Multi-agent coordination
- **Advanced Memory**: Vector-based semantic memory search
- **Custom Models**: Support for local and custom LLM models

### 13.2 Extensibility Points

- **Tool Framework**: Easy addition of new tool categories
- **Service Providers**: Pluggable AI service implementations
- **Event System**: Extensible event types and handlers
- **Configuration**: Modular configuration system
- **Storage Backends**: Alternative conversation persistence options

---

## 14. Migration & Compatibility

### 14.1 Legacy Support

- **Backward Compatibility**: All original voice-to-voice features preserved
- **Legacy Module Preservation**: Original implementations maintained in `ai_legacy/`
- **Configuration Migration**: Smooth transition path for existing configurations
- **Feature Flags**: Gradual rollout of new capabilities

### 14.2 Upgrade Path

The architecture supports incremental upgrades:

1. **Foundation**: Core event-driven architecture
2. **Tools**: Progressive tool addition and enhancement
3. **Advanced Features**: Loop detection, chat compression, memory management
4. **Future Enhancements**: Plugin system, distributed processing

---

**Document Version:** 2.0  
**Architecture Status:** Production Ready  
**Implementation Completeness:** All 4 phases complete  
**Last Verification:** January 2025

This architecture documentation reflects the current production-ready state of TranscribeTalk with comprehensive agentic capabilities, robust safety mechanisms, and production-grade reliability.
