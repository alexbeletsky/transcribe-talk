# TranscribeTalk

A CLI application for voice-to-voice AI conversations using speech-to-text, AI processing, and text-to-speech, now enhanced with agentic capabilities.

## 🎯 Overview

TranscribeTalk transforms your voice into AI conversations by:

1. **Recording** your voice using your microphone
2. **Transcribing** speech to text using OpenAI Whisper
3. **Processing** with AI using OpenAI GPT models (with tool-calling capabilities)
4. **Speaking** the response using ElevenLabs TTS

### New Agentic Features (Phase 1 & 2 Complete)

TranscribeTalk now includes a foundational agentic architecture inspired by `gemini-cli`:

- **Event-driven architecture** with structured events for better separation of concerns
- **Tool integration framework** for extending AI capabilities with local environment interactions
- **Async/await support** for improved performance and responsiveness
- **Modular design** with clear separation between voice I/O, AI services, and tool management
- **First tool implemented**: `list_directory` for file system exploration
- **Safety features**: Tool approval, timeouts, and execution limits
- **Dry-run mode**: Test tool interactions without actual execution

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/transcribetalk/transcribe-talk.git
cd transcribe-talk

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
# .venv\Scripts\activate  # On Windows

# Install in development mode
pip install -e .
```

### Configuration

1. Create and configure your environment file:

```bash
# Create .env file
touch .env

# Edit .env and add your API keys:
# Get your API keys from:
# OpenAI: https://platform.openai.com/api-keys
# ElevenLabs: https://elevenlabs.io/

cat > .env << 'EOF'
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
EOF
```

3. Validate your configuration:

```bash
transcribe-talk config validate
```

### Usage

```bash
# Interactive mode (default) - Just run without any commands
transcribe-talk

# Interactive mode with options
transcribe-talk --model large --voice <voice-id> --tokens 300

# Interactive mode with auto-confirm (unattended mode)
transcribe-talk --auto-confirm

# Dry-run mode - simulate tool execution
transcribe-talk --dry-run

# One-shot mode - Process single audio file or recording
transcribe-talk once

# One-shot with file input
transcribe-talk once --input audio.wav --output result.txt

# Show configuration
transcribe-talk config show

# Validate configuration
transcribe-talk config validate

# Get help
transcribe-talk --help
```

#### Interactive Mode Features

- **Voice recording** with start/stop controls
- **Real-time transcription** using Whisper
- **AI conversation** with memory and context
- **Tool-augmented responses** (e.g., "What files are in this directory?")
- **Text-to-speech** playback of responses
- **Text input** option for accessibility
- **Conversation management** (clear history, help)
- **Beautiful terminal interface** with Rich

#### Tool Capabilities

Currently available tools:
- **list_directory** - List contents of directories with formatting

Example queries that trigger tool use:
- "What files are in the current directory?"
- "Show me what's in the src folder"
- "List all Python files here"

#### One-Shot Mode Features

- **File processing** or live recording
- **Batch processing** capabilities
- **Multiple output formats** (text, JSON)
- **Optional TTS** (can be disabled with `--no-tts`)
- **Automation friendly** for scripts and workflows

## 📋 Architecture

### New Agentic Architecture (Phase 1)

The application now features a modular, event-driven architecture:

```
TranscribeTalk Agentic Architecture
├── Voice I/O Layer
│   ├── AudioRecorder     # Captures voice input
│   └── AudioPlayer       # Plays TTS output
├── AI Services Layer
│   ├── Agent            # Orchestrates conversation flow
│   ├── Turn             # Manages single interaction cycles
│   ├── ChatService      # Handles OpenAI API communication
│   ├── PromptEngine     # Assembles context for AI
│   ├── Transcriber      # Converts speech to text
│   └── TTS              # Converts text to speech
├── Tool Management Layer
│   ├── ToolRegistry     # Discovers and registers tools
│   └── ToolScheduler    # Executes tool calls safely
└── State Management
    └── ConversationHistory  # Maintains conversation context
```

### Project Structure

```
transcribe-talk/
├── src/transcribe_talk/
│   ├── cli.py                 # Main CLI entry point (refactored)
│   ├── audio/                 # Audio recording/playback
│   ├── ai/                    # AI services
│   │   ├── ai_legacy/         # Legacy modules (preserved)
│   │   ├── agent.py           # Agent orchestrator
│   │   ├── chat_service.py    # OpenAI API interface
│   │   ├── events.py          # Event definitions
│   │   ├── history.py         # Conversation history
│   │   ├── prompt_engine.py   # Context assembly
│   │   ├── tool_scheduler.py  # Tool execution
│   │   ├── transcriber.py     # Speech-to-text
│   │   ├── tts.py            # Text-to-speech
│   │   └── turn.py           # Turn management
│   ├── tools/                 # Tool infrastructure
│   │   └── tool_registry.py   # Tool discovery
│   ├── config/                # Configuration management
│   └── utils/                 # Shared utilities
├── tests/                     # Test suite
├── pyproject.toml            # Project configuration
├── requirements.txt          # Dependencies
├── AGENT.md                  # Agentic architecture documentation
├── GEMINICLI.md             # Architecture inspiration
└── README.md                # This file
```

### Development Setup

```bash
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
# .venv\Scripts\activate  # Windows

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

## 🔧 Configuration

### Environment Variables

| Variable             | Description                   | Default                |
| -------------------- | ----------------------------- | ---------------------- |
| `OPENAI_API_KEY`     | OpenAI API key (required)     | -                      |
| `ELEVENLABS_API_KEY` | ElevenLabs API key (required) | -                      |
| `WHISPER_MODEL`      | Whisper model size            | `base`                 |
| `AUDIO_SAMPLE_RATE`  | Audio sample rate             | `16000`                |
| `OPENAI_MODEL`       | OpenAI model                  | `gpt-4o-mini`          |
| `OPENAI_MAX_TOKENS`  | Max response tokens           | `200`                  |
| `TTS_VOICE_ID`       | ElevenLabs voice ID           | `wyWA56cQNU2KqUW4eCsI` |

### Command Line Options

```bash
# Interactive mode options
transcribe-talk --model large --voice <voice-id> --tokens 300

# One-shot mode options
transcribe-talk once --input audio.wav --output result.txt --format json

# Logging options
transcribe-talk --log-level DEBUG --log-file transcribe.log
```

## 📦 Dependencies

### Core Dependencies

- `openai-whisper` - Speech-to-text transcription
- `openai` - AI conversation processing with tool support
- `elevenlabs` - Text-to-speech synthesis
- `sounddevice` - Audio recording
- `click` - CLI framework
- `rich` - Beautiful terminal output
- `pydantic` - Configuration validation
- `aiofiles` - Async file operations

### Development Dependencies

- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `black` - Code formatting
- `isort` - Import sorting
- `mypy` - Type checking

## 🚦 Development Status

**Phase 1 Complete** ✅ (Foundational Architecture)

- [x] Event-driven architecture with Turn/Agent pattern
- [x] Tool integration framework
- [x] Async/await support throughout
- [x] Legacy code preservation in ai_legacy/
- [x] Refactored CLI with Agent integration
- [x] Type safety with comprehensive hints
- [x] Modular design with clear separation of concerns

**Phase 2 Complete** ✅ (MVP Agentic Loop)

- [x] First tool implementation (list_directory)
- [x] Tool confirmation flow (--auto-confirm)
- [x] Dry-run mode (--dry-run)
- [x] Safety guardrails (timeouts, retry logic)
- [x] Telemetry and logging enhancements
- [x] Basic testing framework
- [x] End-to-end tool execution flow

**Phase 3 Planned** 📋 (Expanding Capabilities)

- [ ] Additional tools (read_file, write_file)
- [ ] Long-term memory with CONTEXT.md
- [ ] Memory management tools
- [ ] Enhanced prompt engineering

**Phase 4 Planned** 📋 (Advanced Hardening)

- [ ] Loop detection and prevention
- [ ] Chat compression for long conversations
- [ ] Advanced error recovery
- [ ] Performance optimizations

## 🔧 Troubleshooting

### Common Issues

**Python 3.13 Compatibility Issues:**

```bash
# If you encounter dependency installation errors, try:
pip cache purge
pip install --upgrade pip
pip install -e .
```

**Virtual Environment Issues:**

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Verify activation
which python  # Should show .venv/bin/python
```

**Configuration Validation Errors:**

```bash
# Check if .env file exists and has correct format
cat .env

# Ensure API keys are properly set
transcribe-talk config validate
```

**Import Errors After Update:**

```bash
# Reinstall in development mode
pip install -e .

# Clear Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI](https://openai.com/) for Whisper and GPT models
- [ElevenLabs](https://elevenlabs.io/) for text-to-speech
- [Click](https://click.palletsprojects.com/) for CLI framework
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- [gemini-cli](https://github.com/google/gemini-cli) for architectural inspiration
