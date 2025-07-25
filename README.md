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
- **Text-to-speech** playback of responses
- **Text input** option for accessibility
- **Conversation management** (clear history, help)
- **Beautiful terminal interface** with Rich

#### One-Shot Mode Features

- **File processing** or live recording
- **Batch processing** capabilities
- **Multiple output formats** (text, JSON)
- **Optional TTS** (can be disabled with `--no-tts`)
- **Automation friendly** for scripts and workflows

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

**Phase 2 Complete** ✅

- [x] Audio module migration
- [x] AI services integration
- [x] Core functionality implementation
- [x] Interactive mode implementation
- [x] One-shot mode implementation

**Phase 3 Complete** ✅

- [x] Enhanced CLI experience
- [x] Full voice-to-voice conversation workflow
- [x] Professional user interface with Rich

**Phase 4 Planned** 📋

- [ ] Testing infrastructure
- [ ] Documentation completion
- [ ] Distribution packaging

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
