# TranscribeTalk Refactoring Plan: Jupyter → CLI

## 🎯 Project Overview

**Goal**: Transform the current Jupyter notebook prototype into a professional CLI application that provides better development experience, maintainability, and user interaction.

**Current State**: Single `TranscribeTalk.ipynb` file with hardcoded API keys and basic UI
**Target State**: Modular Python CLI application with proper configuration, error handling, and professional interface

---

## 📋 Phase 1: Core Infrastructure Setup

### 1.1 Project Structure & Packaging

- [ ] Create modern Python project structure with `src/` layout
- [ ] Set up `pyproject.toml` for modern Python packaging
- [ ] Create `requirements.txt` with pinned dependencies
- [ ] Initialize proper `.gitignore` for Python projects
- [ ] Create `.env.example` template for configuration

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

- [ ] Create `recorder.py` - Extract recording functionality from notebook
  - [ ] Implement threaded recording with start/stop controls
  - [ ] Add audio validation and format handling
  - [ ] Implement configurable sample rates and audio settings
- [ ] Create `player.py` - Audio playback functionality
  - [ ] Cross-platform audio playback
  - [ ] Volume control and playback status
- [ ] Add proper error handling for audio device issues

### 2.2 AI Services Module (`src/transcribe_talk/ai/`)

- [ ] Create `transcriber.py` - Whisper integration
  - [ ] Extract Whisper model loading and transcription
  - [ ] Add model selection (base, small, medium, large)
  - [ ] Implement caching for model loading
  - [ ] Add language detection and multilingual support
- [ ] Create `chat.py` - OpenAI integration
  - [ ] Extract OpenAI client setup and conversation handling
  - [ ] Add conversation memory and context management
  - [ ] Implement configurable response length and temperature
  - [ ] Add support for different models (GPT-4, GPT-3.5, etc.)
- [ ] Create `tts.py` - ElevenLabs integration
  - [ ] Extract TTS functionality with voice selection
  - [ ] Add voice switching capabilities
  - [ ] Implement audio format options
  - [ ] Add speech speed and stability controls

### 2.3 Utilities Module (`src/transcribe_talk/utils/`)

- [ ] Create `helpers.py` for shared utilities
  - [ ] File handling and temporary file management
  - [ ] Audio format conversion utilities
  - [ ] Text processing and formatting
  - [ ] Progress indicators and status display

**Deliverable**: Modular codebase with separated concerns, all original functionality preserved

---

## 📋 Phase 3: Enhanced CLI Experience

### 3.1 Interactive Mode Implementation

- [ ] Create keyboard-driven interface for recording control
  - [ ] Implement real-time key detection (without Enter requirement)
  - [ ] Add visual indicators for recording status
  - [ ] Create help system and command reference
- [ ] Add conversation flow management
  - [ ] Conversation history display
  - [ ] Context preservation between interactions
  - [ ] Session management and persistence
- [ ] Implement user feedback systems
  - [ ] Progress bars for long operations
  - [ ] Status messages and error feedback
  - [ ] Audio level indicators during recording

### 3.2 One-Shot Mode

- [ ] Implement single interaction mode for automation
- [ ] Add command-line input options
- [ ] Create output formatting options (JSON, text, etc.)
- [ ] Add batch processing capabilities

### 3.3 Configuration Management

- [ ] Create `--config` command for settings management
- [ ] Implement configuration viewing and editing
- [ ] Add voice testing and model selection tools
- [ ] Create configuration validation and health checks

**Deliverable**: Fully functional CLI with professional user experience

---

## 📋 Phase 4: Quality & Distribution

### 4.1 Testing Infrastructure

- [ ] Set up `tests/` directory with pytest
- [ ] Create unit tests for each module:
  - [ ] `test_audio.py` - Audio recording/playback tests
  - [ ] `test_ai.py` - AI service integration tests (with mocking)
  - [ ] `test_cli.py` - CLI interface and argument parsing tests
  - [ ] `test_config.py` - Configuration management tests
- [ ] Add integration tests for full workflow
- [ ] Create mock services for testing without API calls

### 4.2 Error Handling & Robustness

- [ ] Comprehensive exception handling for all external services
- [ ] Network error handling and retry logic
- [ ] Audio device error handling and fallbacks
- [ ] Graceful degradation when services are unavailable
- [ ] User-friendly error messages and suggestions

### 4.3 Documentation & Distribution

- [ ] Create comprehensive `README.md` with installation and usage
- [ ] Add inline documentation and type hints
- [ ] Create example configurations and use cases
- [ ] Set up packaging for pip distribution
- [ ] Add GitHub Actions for CI/CD (optional)

**Deliverable**: Production-ready CLI application with proper testing and documentation

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

### Phase 4 Complete When:

- [ ] Test suite covers major functionality
- [ ] Error handling is comprehensive and user-friendly
- [ ] Documentation is complete and clear
- [ ] Application can be distributed and installed easily

---

## 🎯 Next Steps

1. **Start with Phase 1.1** - Create basic project structure
2. **Test early and often** - Ensure each phase builds on working foundation
3. **Preserve functionality** - Keep original notebook as reference during migration
4. **Incremental approach** - Each phase should result in working application
5. **Documentation** - Update this plan as we learn and adapt

---

**Note**: This plan is a living document. We'll update it as we progress and encounter new requirements or challenges during the refactoring process.
