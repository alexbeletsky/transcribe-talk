"""
Audio playback functionality for TranscribeTalk.

This module provides audio playback capabilities:
- Play numpy arrays directly
- Play audio files (WAV, MP3, etc.)
- Play binary audio data
- Handle different audio formats
- Integration with sounddevice for low-latency playback
"""

import io
import logging
import tempfile
from pathlib import Path
from typing import Optional, Union

import numpy as np
import scipy.io.wavfile
import sounddevice as sd

from ..config.settings import AudioConfig

logger = logging.getLogger(__name__)


class AudioPlayer:
    """
    Cross-platform audio player for various audio sources.
    
    Supports playing:
    - NumPy arrays (recorded audio data)
    - Audio files (WAV, MP3, etc.)
    - Binary audio data (TTS responses)
    """
    
    def __init__(self, config: AudioConfig):
        """
        Initialize the audio player.
        
        Args:
            config: Audio configuration settings
        """
        self.config = config
        self.sample_rate = config.sample_rate
        self.channels = config.channels
        
        logger.info(f"Audio player initialized: {self.sample_rate}Hz, {self.channels} channel(s)")
    
    def play_array(self, audio_data: np.ndarray, sample_rate: Optional[int] = None) -> None:
        """
        Play audio from a numpy array.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate. If None, uses config default
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        logger.info(f"Playing audio array: {len(audio_data)} samples at {sample_rate}Hz")
        
        try:
            # Ensure correct data type
            if audio_data.dtype != np.float32:
                # Convert to float32 and normalize if needed
                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768.0
                elif audio_data.dtype == np.int32:
                    audio_data = audio_data.astype(np.float32) / 2147483648.0
                else:
                    audio_data = audio_data.astype(np.float32)
            
            # Ensure correct shape for mono/stereo
            if self.channels == 1 and audio_data.ndim > 1:
                audio_data = audio_data.flatten()
            
            # Play audio (blocking)
            sd.play(audio_data, samplerate=sample_rate)
            sd.wait()  # Wait for playback to complete
            
            logger.info("Audio playback completed")
            
        except Exception as e:
            logger.error(f"Error playing audio array: {e}")
            raise
    
    def play_file(self, file_path: Union[str, Path]) -> None:
        """
        Play audio from a file.
        
        Args:
            file_path: Path to audio file
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        logger.info(f"Playing audio file: {file_path}")
        
        try:
            if file_path.suffix.lower() == '.wav':
                # Handle WAV files
                sample_rate, audio_data = scipy.io.wavfile.read(str(file_path))
                self.play_array(audio_data, sample_rate)
            else:
                # For other formats, try to use sounddevice directly
                # Note: This requires libsndfile with appropriate codec support
                audio_data, sample_rate = sd.read(str(file_path))
                self.play_array(audio_data, sample_rate)
                
        except Exception as e:
            logger.error(f"Error playing audio file {file_path}: {e}")
            raise
    
    def play_binary_data(self, audio_bytes: bytes, audio_format: str = "mp3") -> None:
        """
        Play audio from binary data (e.g., TTS response).
        
        Args:
            audio_bytes: Binary audio data
            audio_format: Audio format ("mp3", "wav", etc.)
        """
        logger.info(f"Playing binary audio data: {len(audio_bytes)} bytes, format: {audio_format}")
        
        try:
            # Create temporary file for binary data
            with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = Path(temp_file.name)
            
            try:
                # Play the temporary file
                self.play_file(temp_path)
            finally:
                # Clean up temporary file
                if temp_path.exists():
                    temp_path.unlink()
                    
        except Exception as e:
            logger.error(f"Error playing binary audio data: {e}")
            raise
    
    def play_with_elevenlabs(self, audio_bytes: bytes) -> None:
        """
        Play audio bytes directly from ElevenLabs TTS.
        
        ElevenLabs returns audio in MP3 format by default.
        
        Args:
            audio_bytes: MP3 audio data as bytes
        """
        self.play_binary_data(audio_bytes, audio_format="mp3")
    
    def play(self, audio_data: Union[bytes, np.ndarray]) -> None:
        """
        Generic play method that handles different audio formats.
        
        Args:
            audio_data: Audio data as bytes (MP3) or numpy array (raw PCM)
        """
        if isinstance(audio_data, bytes):
            # Assume bytes are MP3 from TTS
            self.play_binary_data(audio_data, audio_format="mp3")
        elif isinstance(audio_data, np.ndarray):
            # Play raw PCM array
            self.play_array(audio_data)
        else:
            raise ValueError(f"Unsupported audio data type: {type(audio_data)}")
    
    def test_playback(self, duration: float = 1.0, frequency: float = 440.0) -> bool:
        """
        Test audio playback with a generated tone.
        
        Args:
            duration: Duration of test tone in seconds
            frequency: Frequency of test tone in Hz
            
        Returns:
            bool: True if test was successful
        """
        try:
            logger.info(f"Testing audio playback with {frequency}Hz tone for {duration}s")
            
            # Generate test tone
            t = np.linspace(0, duration, int(self.sample_rate * duration), False)
            test_audio = 0.3 * np.sin(2 * np.pi * frequency * t)
            
            # Play test tone
            self.play_array(test_audio)
            
            logger.info("Audio playback test successful")
            return True
            
        except Exception as e:
            logger.error(f"Audio playback test failed: {e}")
            return False


def get_audio_output_devices() -> dict:
    """
    Get information about available audio output devices.
    
    Returns:
        dict: Dictionary with output device information
    """
    try:
        devices = sd.query_devices()
        output_devices = [dev for dev in devices if dev['max_output_channels'] > 0]
        
        return {
            'output_devices': output_devices,
            'default_output': sd.default.device[1] if sd.default.device else None,
        }
    except Exception as e:
        logger.error(f"Error querying audio output devices: {e}")
        return {}


def set_audio_device(device_id: Optional[int] = None) -> None:
    """
    Set the default audio output device.
    
    Args:
        device_id: Device ID to use. If None, uses system default
    """
    try:
        if device_id is not None:
            sd.default.device[1] = device_id
            logger.info(f"Set audio output device to: {device_id}")
        else:
            # Reset to system default
            sd.default.device[1] = None
            logger.info("Reset audio output device to system default")
            
    except Exception as e:
        logger.error(f"Error setting audio device: {e}")
        raise 