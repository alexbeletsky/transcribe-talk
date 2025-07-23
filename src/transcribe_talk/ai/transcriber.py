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
        
        logger.info(f"Whisper transcriber initialized with model: {self.model_name}")
    
    @property
    def model(self) -> whisper.Whisper:
        """
        Get the loaded Whisper model, loading it if necessary.
        
        Returns:
            whisper.Whisper: Loaded Whisper model
        """
        if self._model is None:
            self._load_model()
        return self._model
    
    def _load_model(self) -> None:
        """Load the Whisper model."""
        logger.info(f"Loading Whisper model: {self.model_name}")
        
        try:
            self._model = whisper.load_model(self.model_name)
            logger.info(f"Whisper model '{self.model_name}' loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model '{self.model_name}': {e}")
            raise
    
    def transcribe_array(
        self, 
        audio_data: np.ndarray, 
        language: Optional[str] = None,
        sample_rate: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Transcribe audio from a numpy array.
        
        Args:
            audio_data: Audio data as numpy array
            language: Optional language code (e.g., 'en', 'es'). If None, auto-detect
            sample_rate: Sample rate of audio data. If None, uses config default
            
        Returns:
            dict: Transcription result with 'text' and 'language' keys
        """
        if sample_rate is None:
            sample_rate = self.audio_config.sample_rate
        
        logger.info(f"Transcribing audio array: {len(audio_data)} samples at {sample_rate}Hz")
        
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            try:
                # Ensure correct data format for scipy.io.wavfile
                if audio_data.dtype != np.int16:
                    # Convert to int16 if needed
                    if audio_data.dtype == np.float32:
                        audio_data = (audio_data * 32767).astype(np.int16)
                    elif audio_data.dtype == np.float64:
                        audio_data = (audio_data * 32767).astype(np.int16)
                    else:
                        audio_data = audio_data.astype(np.int16)
                
                # Ensure mono audio for Whisper
                if audio_data.ndim > 1:
                    audio_data = audio_data.flatten()
                
                # Save to temporary WAV file
                scipy.io.wavfile.write(str(temp_path), sample_rate, audio_data)
                
                # Transcribe the file
                return self.transcribe_file(temp_path, language)
                
            finally:
                # Clean up temporary file
                if temp_path.exists():
                    temp_path.unlink()
                    
        except Exception as e:
            logger.error(f"Error transcribing audio array: {e}")
            raise
    
    def transcribe_file(self, file_path: Union[str, Path], language: Optional[str] = None) -> Dict[str, str]:
        """
        Transcribe audio from a file.
        
        Args:
            file_path: Path to audio file
            language: Optional language code. If None, auto-detect
            
        Returns:
            dict: Transcription result with 'text' and 'language' keys
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        logger.info(f"Transcribing audio file: {file_path}")
        
        try:
            # Prepare transcription options
            options = {}
            if language:
                options['language'] = language
            
            # Transcribe using Whisper
            result = self.model.transcribe(str(file_path), **options)
            
            # Extract text and detected language
            transcribed_text = result.get("text", "").strip()
            detected_language = result.get("language", "unknown")
            
            logger.info(f"Transcription completed: {len(transcribed_text)} characters, language: {detected_language}")
            logger.debug(f"Transcribed text: {transcribed_text}")
            
            return {
                "text": transcribed_text,
                "language": detected_language,
                "segments": result.get("segments", []),
            }
            
        except Exception as e:
            logger.error(f"Error transcribing file {file_path}: {e}")
            raise
    
    def transcribe_with_timestamps(
        self, 
        audio_input: Union[np.ndarray, str, Path],
        language: Optional[str] = None
    ) -> Dict:
        """
        Transcribe audio with word-level timestamps.
        
        Args:
            audio_input: Audio data (array) or file path
            language: Optional language code
            
        Returns:
            dict: Detailed transcription result with timestamps
        """
        logger.info("Transcribing with word-level timestamps")
        
        try:
            if isinstance(audio_input, np.ndarray):
                # Convert array to temporary file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                
                try:
                    # Save array to WAV file
                    if audio_input.dtype != np.int16:
                        if audio_input.dtype == np.float32:
                            audio_input = (audio_input * 32767).astype(np.int16)
                        else:
                            audio_input = audio_input.astype(np.int16)
                    
                    scipy.io.wavfile.write(str(temp_path), self.audio_config.sample_rate, audio_input)
                    file_path = temp_path
                    
                finally:
                    cleanup_temp = True
            else:
                file_path = Path(audio_input)
                cleanup_temp = False
            
            try:
                # Transcribe with word_timestamps enabled
                options = {"word_timestamps": True}
                if language:
                    options["language"] = language
                
                result = self.model.transcribe(str(file_path), **options)
                
                logger.info(f"Timestamp transcription completed: {len(result.get('segments', []))} segments")
                return result
                
            finally:
                if cleanup_temp and temp_path.exists():
                    temp_path.unlink()
                    
        except Exception as e:
            logger.error(f"Error transcribing with timestamps: {e}")
            raise
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get supported languages for Whisper.
        
        Returns:
            dict: Language codes and names
        """
        try:
            return whisper.tokenizer.LANGUAGES
        except Exception as e:
            logger.error(f"Error getting supported languages: {e}")
            return {}
    
    def detect_language(self, audio_input: Union[np.ndarray, str, Path]) -> str:
        """
        Detect the language of audio input.
        
        Args:
            audio_input: Audio data (array) or file path
            
        Returns:
            str: Detected language code
        """
        logger.info("Detecting audio language")
        
        try:
            if isinstance(audio_input, np.ndarray):
                # Use transcribe_array to get language
                result = self.transcribe_array(audio_input)
                return result.get("language", "unknown")
            else:
                # Use transcribe_file to get language
                result = self.transcribe_file(audio_input)
                return result.get("language", "unknown")
                
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return "unknown"
    
    def change_model(self, model_name: str) -> None:
        """
        Change the Whisper model.
        
        Args:
            model_name: New model name (tiny, base, small, medium, large)
        """
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if model_name not in valid_models:
            raise ValueError(f"Invalid model name. Must be one of: {valid_models}")
        
        if model_name != self.model_name:
            logger.info(f"Changing Whisper model from {self.model_name} to {model_name}")
            self.model_name = model_name
            self.whisper_config.model = model_name
            self._model = None  # Force reload on next use
    
    def test_transcription(self) -> bool:
        """
        Test transcription functionality with a silent audio clip.
        
        Returns:
            bool: True if test was successful
        """
        try:
            logger.info("Testing Whisper transcription...")
            
            # Create a short silent audio clip for testing
            duration = 1.0  # 1 second
            sample_rate = self.audio_config.sample_rate
            test_audio = np.zeros(int(duration * sample_rate), dtype=np.int16)
            
            # Transcribe the silent audio
            result = self.transcribe_array(test_audio)
            
            # Silent audio should return empty or minimal text
            logger.info(f"Test transcription result: '{result.get('text', '')}'")
            logger.info("Whisper transcription test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Whisper transcription test failed: {e}")
            return False


def get_available_models() -> list:
    """
    Get list of available Whisper models.
    
    Returns:
        list: Available model names
    """
    return ["tiny", "base", "small", "medium", "large"]


def estimate_model_size(model_name: str) -> str:
    """
    Estimate the download size of a Whisper model.
    
    Args:
        model_name: Model name
        
    Returns:
        str: Estimated size description
    """
    sizes = {
        "tiny": "~39 MB",
        "base": "~74 MB", 
        "small": "~244 MB",
        "medium": "~769 MB",
        "large": "~1550 MB"
    }
    return sizes.get(model_name, "Unknown size") 