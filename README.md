# TranscribeTalk

A CLI application for voice-to-voice AI conversations using speech-to-text, AI processing, and text-to-speech.

## 🎯 Overview

TranscribeTalk transforms your voice into AI conversations by:

1. **Recording** your voice using your microphone
2. **Transcribing** speech to text using OpenAI Whisper
3. **Processing** with AI using OpenAI GPT models
4. **Speaking** the response using ElevenLabs TTS

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/transcribetalk/transcribe-talk.git
cd transcribe-talk

# Install in development mode
pip install -e .
```

### Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:

```bash
# Get your API keys from:
# OpenAI: https://platform.openai.com/api-keys
# ElevenLabs: https://elevenlabs.io/
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

3. Validate your configuration:

```bash
transcribe-talk config validate
```

### Usage

```bash
# Interactive mode (default)
transcribe-talk

# One-shot mode
transcribe-talk once

# Show configuration
transcribe-talk config show

# Get help
transcribe-talk --help
```

## 📋 Features

### Interactive Mode

- Continuous voice conversations
- Real-time speech-to-text
- AI-powered responses
- Text-to-speech playback

### One-Shot Mode

- Process single audio files
- Batch processing support
- Multiple output formats (text, JSON)

### Configuration Management

- Environment-based configuration
- API key validation
- Model selection (Whisper, OpenAI, TTS)
- Audio settings customization

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

## 🏗️ Development

### Project Structure

```
transcribe-talk/
├── src/transcribe_talk/
│   ├── cli.py                 # Main CLI entry point
│   ├── audio/                 # Audio recording/playback
│   ├── ai/                    # AI services (Whisper, OpenAI, TTS)
│   ├── config/                # Configuration management
│   └── utils/                 # Shared utilities
├── tests/                     # Test suite
├── pyproject.toml            # Project configuration
├── requirements.txt          # Dependencies
└── README.md                # This file
```

### Development Setup

```bash
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

## 📦 Dependencies

### Core Dependencies

- `openai-whisper` - Speech-to-text transcription
- `openai` - AI conversation processing
- `elevenlabs` - Text-to-speech synthesis
- `sounddevice` - Audio recording
- `click` - CLI framework
- `rich` - Beautiful terminal output
- `pydantic` - Configuration validation

### Development Dependencies

- `pytest` - Testing framework
- `black` - Code formatting
- `isort` - Import sorting
- `mypy` - Type checking

## 🚦 Status

**Phase 1 Complete** ✅

- [x] Project structure and packaging
- [x] Configuration management
- [x] Basic CLI framework
- [x] Logging and error handling

**Phase 2 In Progress** 🔄

- [ ] Audio module migration
- [ ] AI services integration
- [ ] Core functionality implementation

**Phase 3 Planned** 📋

- [ ] Enhanced CLI experience
- [ ] Interactive mode implementation
- [ ] One-shot mode implementation

**Phase 4 Planned** 📋

- [ ] Testing infrastructure
- [ ] Documentation completion
- [ ] Distribution packaging

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
