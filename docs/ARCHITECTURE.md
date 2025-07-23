# TranscribeTalk Architecture Documentation

This document serves as a comprehensive reference of the current architecture of the TranscribeTalk CLI application. It outlines project structure, core modules, configuration, dependencies, design patterns, and conventions to guide future architectural decisions.

---

## 1. Project Overview

TranscribeTalk is a modular Python CLI application enabling voice-to-voice AI conversations.

Key capabilities:

- **Audio Recording**: Capture live microphone input
- **Speech-to-Text**: Transcribe audio using OpenAI Whisper
- **AI Processing**: Generate natural language responses via OpenAI GPT models
- **Text-to-Speech**: Synthesize AI responses with ElevenLabs TTS
- **Interactive CLI**: User-friendly terminal interface using Click and Rich
- **Configuration Management**: Pydantic-based settings with `.env` support

Current state: All core features implemented and packaged; testing infrastructure deferred.

---

## 2. Directory Structure

```
/ (project root)
├── ARCHITECTURE.md       # This document
├── PLAN.md               # Refactoring plan and status
├── README.md             # Usage and setup guide
├── pyproject.toml        # Packaging and dependencies
├── requirements.txt      # Pinned dependencies
├── .env.example          # Sample environment variables
├── src/transcribe_talk/  # Main application package
│   ├── cli.py            # CLI entry point and commands
│   ├── audio/            # Audio recording and playback
│   │   ├── recorder.py   # AudioRecorder class
│   │   └── player.py     # AudioPlayer class
│   ├── ai/               # AI service integrations
│   │   ├── transcriber.py# WhisperTranscriber class
│   │   ├── chat.py       # OpenAIChat class and memory
│   │   └── tts.py        # ElevenLabsTTS class
│   ├── config/           # Configuration management
│   │   └── settings.py   # Pydantic Settings and env loader
│   └── utils/            # Shared utility functions
│       └── helpers.py    # Temp files, spinners, formatting
└── tests/                # (To be added) test suite
```

---

## 3. Core Modules

### 3.1 Configuration (`config/settings.py`)

- Uses **Pydantic** `BaseModel` for each sub-configuration:
  - `AudioConfig`, `WhisperConfig`, `OpenAIConfig`, `ElevenLabsConfig`, `LoggingConfig`
- **Global Settings**:
  - `Settings` model nesting sub-configs and `debug` flag
  - `load_settings()` reads `.env` via `python-dotenv`, environment variables, and validates
  - `get_settings()` caches a singleton instance
- **Validation Rules** enforce formats (e.g. API key prefixes, temperature range)
- Environment variables support nested keys via `env_nested_delimiter='__'`

### 3.2 CLI (`cli.py`)

- **Click**-based commands and subcommands:
  - Default (no subcommand): Interactive mode
  - `interactive`: same as default
  - `once`: one-shot processing of file or live recording
  - `config show` / `config validate`
- **Logging & Output**:
  - `rich` for console panels, spinners, colored messages
  - `RichHandler` for formatted log output
- **Error Handling**:
  - Decorator `@handle_exceptions` wraps commands for graceful exit
  - Supports `KeyboardInterrupt` and generic exceptions
- **Command Options** configure models, voice, tokens, log level, debug

### 3.3 Audio Module (`audio/recorder.py` & `player.py`)

- **AudioRecorder**:
  - Threaded recording via `sounddevice.InputStream`
  - Buffering of audio frames, start/stop controls
  - Fixed-duration recording for testing
  - `save_audio_to_file()` for WAV file output
  - Context manager and cleanup logic
- **AudioPlayer**:
  - Play `numpy.ndarray` buffers via `sounddevice.play()`
  - Support WAV and other formats (`scipy.io.wavfile.read` fallback)
  - Binary data playback with temporary files
  - ElevenLabs native `play()` integration

### 3.4 AI Services Module (`ai/transcriber.py`, `ai/chat.py`, `ai/tts.py`)

- **WhisperTranscriber**:
  - Lazily loads Whisper model via `whisper.load_model(model_name)`
  - Transcription from arrays or files, with optional language hints
  - Supports timestamped transcription
  - Model caching and switchable models (tiny → large)
- **OpenAIChat**:
  - Uses `openai.OpenAI(api_key)` client for chat completions
  - `ConversationMemory` for context (max messages, system prompt)
  - Both streaming and non-streaming chat
  - Parameter adjustments for `max_tokens`, `temperature`
  - Token usage logging
- **ElevenLabsTTS**:
  - `elevenlabs.client.ElevenLabs(api_key)` for TTS
  - Synthesize text to bytes (sync and streaming)
  - Voice and model management, format configuration
  - Error handling and retry logic

### 3.5 Utilities (`utils/helpers.py`)

- **TempFileManager** and `temp_audio_file()` for robust temp file handling
- Audio array save/load, format validation (`save_audio_array`, `load_audio_array`)
- Text and file metadata formatting (`format_duration`, `format_file_size`, `truncate_text`)
- `progress_spinner()` for consistent Rich progress UX
- Retry decorator for transient failures
- Filesystem helpers (`ensure_directory`, `safe_filename`)

---

## 4. Logging & Error Handling

- Centralized `setup_logging()` configures root logger and Rich handler
- Warning suppression for known benign warnings (e.g. FP16 on CPU)
- Decorator-based exception handling ensures:
  - Clean shutdown on `Ctrl+C`
  - Helpful error messages with guidance
- Each module logs key events at `INFO`/`DEBUG` levels

---

## 5. Dependencies & Tech Stack

- **Python** ≥3.8 with strict typing and Pydantic
- **Audio**: `sounddevice`, `numpy`, `scipy`
- **AI**:
  - `openai-whisper` for transcription
  - `openai` for chat completions
  - `elevenlabs` for TTS
- **CLI & UX**: `click`, `rich`
- **Config**: `pydantic`, `python-dotenv`

Package management via **Poetry**/Hatchling or `requirements.txt`.

---

## 6. Design Patterns & Conventions

- **Dependency Injection**: Inject `config` objects into service classes
- **Lazy Loading & Caching**: Whisper model loaded on demand and cached
- **Context Managers**: Resource cleanup for audio streams and temp files
- **Separation of Concerns**: Clear module boundaries (CLI, audio, AI, config, utils)
- **Single Responsibility**: Each class handles one domain (Recorder, Player, Transcriber, Chat, TTS)
- **Extensibility**: Easily add new AI/Audio providers by following interface patterns
- **Configuration as Code**: All behavior controlled via Pydantic models and env vars

---

## 7. Packaging & Distribution

- Entry point defined in `pyproject.toml` under `project.scripts`
- Build with `pip install -e .` or `poetry install`
- Future CI/CD pipelines will publish to PyPI

---

## 8. Future Considerations

- **Testing Suite**: Full pytest integration with mocks
- **CI/CD**: Automated lint, typecheck, test, and publish workflows
- **Monitoring & Telemetry**: Optional usage analytics for API calls
- **Plugin Architecture**: Support alternative backends (Google/TensorFlow, AWS Polly)
- **Platform Support**: Ensure cross-platform compatibility on Windows and Linux

---

_End of Architecture Documentation_
