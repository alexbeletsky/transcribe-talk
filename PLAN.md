# TranscribeTalk Refactoring Plan: Jupyter → CLI

## 🎯 Project Overview

**Goal**: Transform the current Jupyter notebook prototype into a professional CLI application that provides better development experience, maintainability, and user interaction.

**Current State**: Modular CLI application with audio recording/playback, Whisper transcription, AI chat, and TTS features fully implemented
**Target State**: Production-ready CLI application with packaging and documentation; testing infrastructure deferred to a future phase

---

## 📋 Phase 1: Core Infrastructure Setup

### 1.1 Project Structure & Packaging

- [x] Create modern Python project structure with `src/` layout
- [x] Set up `pyproject.toml` for modern Python packaging
- [x] Create `requirements.txt` with pinned dependencies
- [x] Initialize proper `.gitignore` for Python projects
- [x] Create `.env.example` template for configuration

### 1.2 Environment & Configuration

- [ ] Implement `src/transcribe_talk/config/settings.py` for configuration management
- [ ] Add support for `.env` file loading with `python-dotenv`
- [ ] Create configuration validation and default values
- [ ] Move hardcoded API keys to environment variables
- [ ] Add configuration for audio settings, model choices, etc.

### 1.3 Basic CLI Framework

- [ ] Create `src/transcribe_talk/cli.py` as main entry point
- [ ] Implement argument parsing with `argparse` or `click`
- [ ] Add basic command structure: interactive, one-shot, config modes
- [ ] Set up logging system with different levels
- [ ] Create basic error handling framework

**Deliverable**: Working CLI skeleton that can be executed but doesn't do audio processing yet

---

## 📋 Phase 2: Core Module Migration

### 2.1 Audio Module (`src/transcribe_talk/audio/`)

- [x] Create `recorder.py` - Extract recording functionality from notebook
  - [ ] Implement threaded recording with start/stop controls
  - [ ] Add audio validation and format handling
  - [ ] Implement configurable sample rates and audio settings
- [x] Create `player.py` - Audio playback functionality
  - [ ] Cross-platform audio playback
  - [ ] Volume control and playback status
- [x] Add proper error handling for audio device issues

### 2.2 AI Services Module (`src/transcribe_talk/ai/`)

- [x] Create `transcriber.py` - Whisper integration
  - [x] Extract Whisper model loading and transcription
  - [x] Add model selection (base, small, medium, large)
  - [x] Implement caching for model loading
  - [x] Add language detection and multilingual support
- [x] Create `chat.py` - OpenAI integration
  - [x] Extract OpenAI client setup and conversation handling
  - [x] Add conversation memory and context management
  - [x] Implement configurable response length and temperature
  - [x] Add support for different models (GPT-4, GPT-3.5, etc.)
- [x] Create `tts.py` - ElevenLabs integration
  - [x] Extract TTS functionality with voice selection
  - [x] Add voice switching capabilities
  - [x] Implement audio format options
  - [ ] Add speech speed and stability controls

### 2.3 Utilities Module (`src/transcribe_talk/utils/`)

- [x] Create `helpers.py` for shared utilities
  - [x] File handling and temporary file management
  - [x] Audio format conversion utilities
  - [x] Text processing and formatting
  - [x] Progress indicators and status display

**Deliverable**: Modular codebase with separated concerns, all original functionality preserved

---

## 📋 Phase 3: Enhanced CLI Experience

### 3.1 Interactive Mode Implementation

- [x] Create keyboard-driven interface for recording control
  - [ ] Implement real-time key detection (without Enter requirement)
  - [ ] Add visual indicators for recording status
  - [x] Create help system and command reference
- [x] Add conversation flow management
  - [x] Conversation history display
  - [x] Context preservation between interactions
  - [ ] Session management and persistence
- [x] Implement user feedback systems
  - [x] Progress bars for long operations
  - [x] Status messages and error feedback
  - [ ] Audio level indicators during recording

### 3.2 One-Shot Mode

- [x] Implement single interaction mode for automation
- [x] Add command-line input options
- [x] Create output formatting options (JSON, text, etc.)
- [ ] Add batch processing capabilities

### 3.3 Configuration Management

- [x] Create `--config` command for settings management
- [ ] Implement configuration viewing and editing
- [ ] Add voice testing and model selection tools
- [x] Create configuration validation and health checks

**Deliverable**: Fully functional CLI with professional user experience

---

### 4 Error Handling & Robustness

- [x] Comprehensive exception handling for all external services
- [x] Network error handling and retry logic
- [x] Audio device error handling and fallbacks
- [x] Graceful degradation when services are unavailable
- [x] User-friendly error messages and suggestions

### 5 Documentation & Distribution

- [x] Create comprehensive `README.md` with installation and usage
- [x] Add inline documentation and type hints
- [x] Create example configurations and use cases
- [x] Set up packaging for pip distribution
- [ ] Add GitHub Actions for CI/CD (optional)

**Deliverable**: Production-ready CLI application with robust error handling and documentation. Testing infrastructure deferred to a future phase

---

## 🔧 Technical Specifications

### Dependencies Management

```toml
# pyproject.toml core dependencies
[project.dependencies]
openai-whisper = "^20231117"
openai = "^1.0.0"
elevenlabs = "^0.2.0"
sounddevice = "^0.4.0"
numpy = "^1.24.0"
scipy = "^1.11.0"
python-dotenv = "^1.0.0"
click = "^8.1.0"  # or argparse for CLI
rich = "^13.0.0"  # for beautiful CLI output
```

### Project Structure

```
transcribe-talk/
├── src/transcribe_talk/
│   ├── __init__.py
│   ├── cli.py                 # Main CLI entry point
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── recorder.py        # Recording functionality
│   │   └── player.py          # Playback functionality
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── transcriber.py     # Whisper integration
│   │   ├── chat.py            # OpenAI integration
│   │   └── tts.py             # ElevenLabs integration
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py        # Configuration management
│   └── utils/
│       ├── __init__.py
│       └── helpers.py         # Shared utilities
├── tests/
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
└── PLAN.md (this file)
```

### CLI Interface Design

```bash
# Installation
pip install transcribe-talk

# Basic usage
transcribe-talk                    # Interactive mode
transcribe-talk --once            # One-shot mode
transcribe-talk --config          # Configuration management
transcribe-talk --help            # Help and usage info

# Advanced options
transcribe-talk --model large      # Use specific Whisper model
transcribe-talk --voice <voice-id> # Use specific TTS voice
transcribe-talk --tokens 200      # Set response length
transcribe-talk --output json     # Output format for one-shot mode
```

---

## 🚦 Success Criteria

### Phase 1 Complete When:

- [ ] CLI can be executed and shows help/version info
- [ ] Configuration system loads from `.env` file
- [ ] Basic logging and error handling works
- [ ] Project structure is established

### Phase 2 Complete When:

- [ ] All original notebook functionality is preserved
- [ ] Audio recording and playback work from CLI
- [ ] AI services (Whisper, OpenAI, ElevenLabs) are integrated
- [ ] No hardcoded API keys remain

### Phase 3 Complete When:

- [ ] Interactive mode provides smooth user experience
- [ ] Conversation history and context work properly
- [ ] Configuration can be managed through CLI
- [ ] One-shot mode works for automation

---

**Note**: This plan is a living document. We'll update it as we progress and encounter new requirements or challenges during the refactoring process.
