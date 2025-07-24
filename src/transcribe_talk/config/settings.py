"""
Configuration management for TranscribeTalk.

This module handles all configuration loading, validation, and defaults
for the TranscribeTalk application.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


class AudioConfig(BaseModel):
    """Audio recording and playback configuration."""
    
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")
    frame_ms: int = Field(default=30, description="Frame size in milliseconds")
    
    @validator('sample_rate')
    def validate_sample_rate(cls, v):
        if v not in [8000, 16000, 22050, 44100, 48000]:
            raise ValueError('Sample rate must be one of: 8000, 16000, 22050, 44100, 48000')
        return v
    
    @validator('channels')
    def validate_channels(cls, v):
        if v not in [1, 2]:
            raise ValueError('Channels must be 1 (mono) or 2 (stereo)')
        return v


class WhisperConfig(BaseModel):
    """Whisper speech-to-text configuration."""
    
    model: str = Field(default="base", description="Whisper model to use")
    language: Optional[str] = Field(default=None, description="Language code (e.g., 'en', 'es'). None for auto-detect")
    task: str = Field(default="transcribe", description="Task to perform: 'transcribe' or 'translate'")
    temperature: float = Field(default=0.0, description="Temperature for sampling")
    initial_prompt: Optional[str] = Field(default=None, description="Initial prompt to condition the model")
    
    @validator('model')
    def validate_model(cls, v):
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if v not in valid_models:
            raise ValueError(f'Model must be one of: {", ".join(valid_models)}')
        return v
    
    @validator('task')
    def validate_task(cls, v):
        if v not in ["transcribe", "translate"]:
            raise ValueError("Task must be 'transcribe' or 'translate'")
        return v


class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""
    
    api_key: str = Field(..., description="OpenAI API key")
    model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    max_tokens: int = Field(default=200, description="Maximum tokens in response")
    temperature: float = Field(default=0.7, description="Response creativity (0.0-1.0)")
    timeout: float = Field(default=60.0, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not v or v == "your_openai_api_key_here":
            raise ValueError("OpenAI API key is required")
        if not v.startswith("sk-"):
            raise ValueError("OpenAI API key must start with 'sk-'")
        return v
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        return v


class ElevenLabsConfig(BaseModel):
    """ElevenLabs TTS configuration."""
    
    api_key: str = Field(..., description="ElevenLabs API key")
    voice_id: str = Field(default="wyWA56cQNU2KqUW4eCsI", description="TTS voice ID")
    model_id: str = Field(default="eleven_multilingual_v2", description="TTS model ID")
    output_format: str = Field(default="mp3_44100_128", description="Audio output format")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not v or v == "your_elevenlabs_api_key_here":
            raise ValueError("ElevenLabs API key is required")
        if not v.startswith("sk_"):
            raise ValueError("ElevenLabs API key must start with 'sk_'")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Logging level")
    file: Optional[str] = Field(default=None, description="Log file path")
    
    @validator('level')
    def validate_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {", ".join(valid_levels)}')
        return v.upper()


class Settings(BaseModel):
    """Main application settings."""
    
    # Sub-configurations
    audio: AudioConfig = Field(default_factory=AudioConfig)
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    openai: OpenAIConfig
    elevenlabs: ElevenLabsConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Development settings
    debug: bool = Field(default=False, description="Enable debug mode")
    
    class Config:
        env_nested_delimiter = '__'
        env_file = '.env'
        env_file_encoding = 'utf-8'


def load_settings() -> Settings:
    """
    Load application settings from environment variables and .env file.
    
    Returns:
        Settings: Validated application settings
        
    Raises:
        ValueError: If required configuration is missing or invalid
    """
    # Load .env file if it exists
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
    
    # Extract API keys from environment
    openai_api_key = os.getenv('OPENAI_API_KEY', '')
    elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY', '')
    
    # Create sub-configurations
    openai_config = OpenAIConfig(
        api_key=openai_api_key,
        model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '200')),
        temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
    )
    
    elevenlabs_config = ElevenLabsConfig(
        api_key=elevenlabs_api_key,
        voice_id=os.getenv('TTS_VOICE_ID', 'wyWA56cQNU2KqUW4eCsI'),
        model_id=os.getenv('TTS_MODEL_ID', 'eleven_multilingual_v2'),
        output_format=os.getenv('TTS_OUTPUT_FORMAT', 'mp3_44100_128'),
    )
    
    # Create and return settings
    return Settings(
        openai=openai_config,
        elevenlabs=elevenlabs_config,
        debug=os.getenv('DEBUG', 'false').lower() == 'true',
    )


# Global settings instance - will be loaded when needed
_settings = None

def get_settings() -> Settings:
    """Get the global settings instance, loading if necessary."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings 