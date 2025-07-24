"""
Speech-to-text transcription using OpenAI Whisper.

This module provides transcription capabilities for TranscribeTalk:
- Whisper model loading and management
- Audio transcription from files and numpy arrays
- Model caching for performance
- Configurable model selection
- Language detection and multilingual support
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np
import scipy.io.wavfile
import whisper

from ..config.settings import WhisperConfig, AudioConfig

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    OpenAI Whisper speech-to-text transcriber.
    
    Features:
    - Multiple model sizes (tiny, base, small, medium, large)
    - Model caching for performance
    - Audio format conversion
    - Language detection
    - Multilingual support
    """
    
    def __init__(self, whisper_config: WhisperConfig, audio_config: AudioConfig):
        """
        Initialize the Whisper transcriber.
        
        Args:
            whisper_config: Whisper model configuration
            audio_config: Audio configuration for format conversion
        """
        self.whisper_config = whisper_config
        self.audio_config = audio_config
        self.model_name = whisper_config.model
        self._model = None
        
        logger.info(f"WhisperTranscriber initialized with model: {self.model_name}")
    
    @property
    def model(self) -> whisper.Whisper:
        """Lazy load and cache the Whisper model."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self._model = whisper.load_model(self.model_name)
            logger.info(f"Whisper model loaded successfully")
        return self._model
    
    def transcribe_file(self, audio_path: Union[str, Path]) -> Dict[str, any]:
        """
        Transcribe audio from a file.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Transcription result dictionary
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing file: {audio_path}")
        
        # Transcribe with Whisper
        result = self.model.transcribe(
            str(audio_path),
            language=self.whisper_config.language,
            task=self.whisper_config.task,
            temperature=self.whisper_config.temperature,
            initial_prompt=self.whisper_config.initial_prompt
        )
        
        logger.info(f"Transcription completed: {len(result['text'])} characters")
        return result
    
    def transcribe_array(self, audio_array: np.ndarray) -> Dict[str, any]:
        """
        Transcribe audio from a numpy array.
        
        Args:
            audio_array: Audio data as numpy array
            
        Returns:
            Transcription result dictionary
        """
        if len(audio_array) == 0:
            return {"text": "", "segments": [], "language": "en"}
        
        # Save to temporary file (Whisper needs a file)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
            # Ensure audio is in the correct format
            if audio_array.dtype != np.int16:
                # Convert to int16
                if audio_array.dtype == np.float32 or audio_array.dtype == np.float64:
                    audio_array = (audio_array * 32767).astype(np.int16)
                else:
                    audio_array = audio_array.astype(np.int16)
            
            # Write WAV file
            scipy.io.wavfile.write(
                tmp_path,
                self.audio_config.sample_rate,
                audio_array
            )
            
            try:
                # Transcribe the temporary file
                result = self.transcribe_file(tmp_path)
                return result
            finally:
                # Clean up temporary file
                tmp_path.unlink(missing_ok=True)
    
    def detect_language(self, audio_path: Union[str, Path]) -> str:
        """
        Detect the language of an audio file.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Detected language code (e.g., 'en', 'es', 'fr')
        """
        audio_path = Path(audio_path)
        
        # Load audio and detect language
        audio = whisper.load_audio(str(audio_path))
        audio = whisper.pad_or_trim(audio)
        
        # Make log-Mel spectrogram
        mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
        
        # Detect the spoken language
        _, probs = self.model.detect_language(mel)
        detected_language = max(probs, key=probs.get)
        
        logger.info(f"Detected language: {detected_language} (confidence: {probs[detected_language]:.2f})")
        return detected_language
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get a dictionary of supported languages.
        
        Returns:
            Dictionary mapping language codes to language names
        """
        return whisper.tokenizer.LANGUAGES
    
    def unload_model(self) -> None:
        """Unload the model from memory."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Whisper model unloaded") 