"""
Audio recording functionality for TranscribeTalk.

This module provides advanced audio recording capabilities including:
- Streaming audio recording with real-time callbacks
- Start/stop controls for variable-length recordings
- Threading support for non-blocking operation
- Audio buffering and concatenation
- Proper resource cleanup and error handling
"""

import logging
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import scipy.io.wavfile
import sounddevice as sd

from ..config.settings import AudioConfig

logger = logging.getLogger(__name__)


class AudioRecorder:
    """
    Advanced audio recorder with streaming capabilities.
    
    Features:
    - Variable-length recording with start/stop controls
    - Real-time audio streaming with callbacks
    - Threading for non-blocking operation
    - Configurable audio parameters
    - Automatic cleanup of resources
    """
    
    def __init__(self, config: AudioConfig):
        """
        Initialize the audio recorder.
        
        Args:
            config: Audio configuration settings
        """
        self.config = config
        self.sample_rate = config.sample_rate
        self.channels = config.channels
        self.frame_size = int(self.sample_rate * config.frame_ms / 1000)
        
        # Recording state
        self._stream: Optional[sd.InputStream] = None
        self._buffer: list = []
        self._stop_requested = False
        self._recording_thread: Optional[threading.Thread] = None
        self._is_recording = False
        
        logger.info(f"Audio recorder initialized: {self.sample_rate}Hz, {self.channels} channel(s)")
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording
    
    def start_recording(self) -> None:
        """
        Start audio recording in a separate thread.
        
        Raises:
            RuntimeError: If already recording
        """
        if self._is_recording:
            raise RuntimeError("Recording is already in progress")
        
        logger.info("Starting audio recording...")
        self._stop_requested = False
        self._buffer = []
        self._is_recording = True
        
        # Start recording in separate thread
        self._recording_thread = threading.Thread(
            target=self._record_audio_stream,
            daemon=True
        )
        self._recording_thread.start()
    
    def stop_recording(self) -> np.ndarray:
        """
        Stop audio recording and return the captured audio data.
        
        Returns:
            numpy.ndarray: Captured audio data as int16 array
            
        Raises:
            RuntimeError: If not currently recording
        """
        if not self._is_recording:
            raise RuntimeError("No recording in progress")
        
        logger.info("Stopping audio recording...")
        self._stop_requested = True
        
        # Wait for recording thread to finish
        if self._recording_thread:
            self._recording_thread.join(timeout=5.0)
            if self._recording_thread.is_alive():
                logger.warning("Recording thread did not stop within timeout")
        
        self._is_recording = False
        
        # Concatenate all audio chunks
        if not self._buffer:
            logger.warning("No audio data captured")
            return np.array([], dtype=np.int16)
        
        audio_data = np.concatenate(self._buffer, axis=0)
        logger.info(f"Recording stopped. Captured {len(audio_data)} samples ({len(audio_data) / self.sample_rate:.2f}s)")
        
        return audio_data
    
    def record_fixed_duration(self, duration_seconds: float) -> np.ndarray:
        """
        Record audio for a fixed duration (blocking operation).
        
        Args:
            duration_seconds: Duration to record in seconds
            
        Returns:
            numpy.ndarray: Captured audio data as int16 array
        """
        logger.info(f"Recording for {duration_seconds} seconds...")
        
        # Calculate number of samples
        num_samples = int(duration_seconds * self.sample_rate)
        
        # Record audio (blocking)
        audio_data = sd.rec(
            frames=num_samples,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='int16'
        )
        sd.wait()  # Wait for recording to complete
        
        logger.info(f"Fixed duration recording completed: {len(audio_data)} samples")
        return audio_data.flatten() if self.channels == 1 else audio_data
    
    def save_audio_to_file(self, audio_data: np.ndarray, file_path: Optional[Path] = None) -> Path:
        """
        Save audio data to a WAV file.
        
        Args:
            audio_data: Audio data to save
            file_path: Optional file path. If None, creates a temporary file
            
        Returns:
            Path: Path to the saved audio file
        """
        if file_path is None:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            file_path = Path(temp_file.name)
            temp_file.close()
        
        # Ensure audio_data has correct shape for mono recording
        if self.channels == 1 and audio_data.ndim > 1:
            audio_data = audio_data.flatten()
        
        # Save to WAV file
        scipy.io.wavfile.write(str(file_path), self.sample_rate, audio_data)
        logger.info(f"Audio saved to: {file_path}")
        
        return file_path
    
    def _record_audio_stream(self) -> None:
        """
        Internal method to handle streaming audio recording.
        
        This runs in a separate thread and captures audio until stop is requested.
        """
        def audio_callback(indata, frames, time_info, status):
            """Callback function for audio stream."""
            if status:
                logger.warning(f"Audio stream status: {status}")
            
            # Add audio data to buffer
            self._buffer.append(indata.copy())
            
            # Check if stop was requested
            if self._stop_requested:
                raise sd.CallbackStop()
        
        try:
            # Create and start audio stream
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                blocksize=self.frame_size,
                callback=audio_callback
            )
            
            with self._stream:
                logger.debug("Audio stream started")
                
                # Keep stream active until stop is requested
                while not self._stop_requested:
                    time.sleep(0.1)
                    
        except sd.CallbackStop:
            logger.debug("Audio recording stopped via callback")
        except Exception as e:
            logger.error(f"Error during audio recording: {e}")
        finally:
            self._stream = None
            logger.debug("Audio stream closed")
    
    def cleanup(self) -> None:
        """Clean up resources and stop any active recording."""
        if self._is_recording:
            try:
                self.stop_recording()
            except Exception as e:
                logger.error(f"Error stopping recording during cleanup: {e}")
        
        if self._stream:
            try:
                self._stream.close()
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()


def get_audio_devices() -> dict:
    """
    Get information about available audio devices.
    
    Returns:
        dict: Dictionary with input and output device information
    """
    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        
        return {
            'devices': devices,
            'hostapis': hostapis,
            'default_input': sd.default.device[0] if sd.default.device else None,
            'default_output': sd.default.device[1] if sd.default.device else None,
        }
    except Exception as e:
        logger.error(f"Error querying audio devices: {e}")
        return {}


def test_audio_recording(config: AudioConfig, duration: float = 2.0) -> bool:
    """
    Test audio recording functionality.
    
    Args:
        config: Audio configuration
        duration: Test recording duration in seconds
        
    Returns:
        bool: True if test was successful
    """
    try:
        with AudioRecorder(config) as recorder:
            logger.info(f"Testing audio recording for {duration} seconds...")
            audio_data = recorder.record_fixed_duration(duration)
            
            if len(audio_data) > 0:
                logger.info("Audio recording test successful")
                return True
            else:
                logger.error("Audio recording test failed: no data captured")
                return False
                
    except Exception as e:
        logger.error(f"Audio recording test failed: {e}")
        return False 