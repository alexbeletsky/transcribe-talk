"""
Shared utilities for TranscribeTalk.

This module provides common utility functions used across the application:
- Temporary file management
- Audio format conversion
- Text processing and formatting  
- File I/O helpers
"""

import logging
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Union

import numpy as np
import scipy.io.wavfile

logger = logging.getLogger(__name__)


class TempFileManager:
    """
    Context manager for temporary file handling.
    
    Ensures proper cleanup of temporary files even if exceptions occur.
    """
    
    def __init__(self, suffix: str = ".wav", prefix: str = "transcribe_talk_"):
        """
        Initialize temporary file manager.
        
        Args:
            suffix: File suffix/extension
            prefix: File prefix
        """
        self.suffix = suffix
        self.prefix = prefix
        self.temp_files = []
    
    def create_temp_file(self, suffix: Optional[str] = None) -> Path:
        """
        Create a new temporary file.
        
        Args:
            suffix: File suffix. If None, uses instance default
            
        Returns:
            Path: Path to temporary file
        """
        suffix = suffix or self.suffix
        
        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix,
            prefix=self.prefix,
            delete=False
        )
        temp_path = Path(temp_file.name)
        temp_file.close()
        
        self.temp_files.append(temp_path)
        logger.debug(f"Created temporary file: {temp_path}")
        
        return temp_path
    
    def cleanup(self) -> None:
        """Clean up all managed temporary files."""
        for temp_path in self.temp_files:
            try:
                if temp_path.exists():
                    temp_path.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_path}: {e}")
        
        self.temp_files.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()


@contextmanager
def temp_audio_file(
    audio_data: np.ndarray, 
    sample_rate: int,
    suffix: str = ".wav"
) -> Generator[Path, None, None]:
    """
    Context manager for temporary audio files.
    
    Args:
        audio_data: Audio data to save
        sample_rate: Audio sample rate
        suffix: File suffix
        
    Yields:
        Path: Path to temporary audio file
    """
    with TempFileManager(suffix=suffix) as manager:
        temp_path = manager.create_temp_file()
        
        try:
            # Save audio data to temporary file
            save_audio_array(audio_data, temp_path, sample_rate)
            yield temp_path
        except Exception as e:
            logger.error(f"Error with temporary audio file: {e}")
            raise


def save_audio_array(
    audio_data: np.ndarray, 
    file_path: Union[str, Path], 
    sample_rate: int
) -> None:
    """
    Save audio array to file.
    
    Args:
        audio_data: Audio data to save
        file_path: Output file path
        sample_rate: Audio sample rate
    """
    file_path = Path(file_path)
    
    try:
        # Ensure correct data format
        if audio_data.dtype != np.int16:
            if audio_data.dtype == np.float32:
                # Convert float32 to int16
                audio_data = (audio_data * 32767).astype(np.int16)
            elif audio_data.dtype == np.float64:
                # Convert float64 to int16
                audio_data = (audio_data * 32767).astype(np.int16)
            else:
                audio_data = audio_data.astype(np.int16)
        
        # Ensure mono audio if multi-dimensional
        if audio_data.ndim > 1:
            audio_data = audio_data.flatten()
        
        # Save to WAV file
        scipy.io.wavfile.write(str(file_path), sample_rate, audio_data)
        logger.debug(f"Audio saved to: {file_path}")
        
    except Exception as e:
        logger.error(f"Error saving audio to {file_path}: {e}")
        raise


def load_audio_array(file_path: Union[str, Path]) -> tuple[np.ndarray, int]:
    """
    Load audio array from file.
    
    Args:
        file_path: Input file path
        
    Returns:
        tuple: (audio_data, sample_rate)
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    
    try:
        # Load audio file
        sample_rate, audio_data = scipy.io.wavfile.read(str(file_path))
        
        # Ensure mono audio
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)
        
        logger.debug(f"Audio loaded from: {file_path}")
        return audio_data, sample_rate
        
    except Exception as e:
        logger.error(f"Error loading audio from {file_path}: {e}")
        raise


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        str: Formatted duration (e.g., "1m 23s", "45s")
    """
    if seconds < 0:
        return "0s"
    
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.1f}s"
    
    hours = int(minutes // 60)
    remaining_minutes = minutes % 60
    
    return f"{hours}h {remaining_minutes}m {remaining_seconds:.1f}s"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size (e.g., "1.2 MB", "345 KB")
    """
    if size_bytes == 0:
        return "0 B"
    
    # Define size units
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    truncate_length = max_length - len(suffix)
    if truncate_length <= 0:
        return suffix[:max_length]
    
    return text[:truncate_length] + suffix


def validate_audio_format(audio_data: np.ndarray, sample_rate: int) -> bool:
    """
    Validate audio data format and parameters.
    
    Args:
        audio_data: Audio data to validate
        sample_rate: Sample rate to validate
        
    Returns:
        bool: True if audio format is valid
    """
    try:
        # Check if audio_data is a numpy array
        if not isinstance(audio_data, np.ndarray):
            return False
        
        # Check if audio data is not empty
        if audio_data.size == 0:
            return False
        
        # Check sample rate range
        if not (8000 <= sample_rate <= 48000):
            return False
        
        # Check data type
        if audio_data.dtype not in [np.int16, np.int32, np.float32, np.float64]:
            return False
        
        # Check for NaN or infinite values
        if np.any(np.isnan(audio_data)) or np.any(np.isinf(audio_data)):
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating audio format: {e}")
        return False


def normalize_audio(audio_data: np.ndarray, target_type: type = np.int16) -> np.ndarray:
    """
    Normalize audio data to target type.
    
    Args:
        audio_data: Input audio data
        target_type: Target numpy data type
        
    Returns:
        np.ndarray: Normalized audio data
    """
    try:
        if target_type == np.int16:
            if audio_data.dtype == np.float32:
                # Convert float32 to int16
                return (audio_data * 32767).astype(np.int16)
            elif audio_data.dtype == np.float64:
                # Convert float64 to int16
                return (audio_data * 32767).astype(np.int16)
            elif audio_data.dtype == np.int32:
                # Convert int32 to int16
                return (audio_data // 65536).astype(np.int16)
            else:
                return audio_data.astype(np.int16)
                
        elif target_type == np.float32:
            if audio_data.dtype == np.int16:
                # Convert int16 to float32
                return audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.int32:
                # Convert int32 to float32
                return audio_data.astype(np.float32) / 2147483648.0
            else:
                return audio_data.astype(np.float32)
        
        # Default: just convert type
        return audio_data.astype(target_type)
        
    except Exception as e:
        logger.error(f"Error normalizing audio: {e}")
        return audio_data


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path: Path object for the directory
    """
    path = Path(path)
    
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        raise


def safe_filename(filename: str, max_length: int = 255) -> str:
    """
    Create a safe filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        str: Safe filename
    """
    # Characters to remove or replace
    invalid_chars = '<>:"/\\|?*'
    
    # Replace invalid characters with underscores
    safe_name = filename
    for char in invalid_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Remove control characters
    safe_name = ''.join(char for char in safe_name if ord(char) >= 32)
    
    # Truncate if too long
    if len(safe_name) > max_length:
        name_part, ext_part = os.path.splitext(safe_name)
        max_name_length = max_length - len(ext_part)
        safe_name = name_part[:max_name_length] + ext_part
    
    # Ensure it's not empty
    if not safe_name or safe_name.isspace():
        safe_name = "unnamed_file"
    
    return safe_name


def retry_on_exception(
    func, 
    max_retries: int = 3, 
    delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """
    Retry function on exception with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff_factor: Multiplier for delay on each retry
        
    Returns:
        Result of successful function call
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                time.sleep(current_delay)
                current_delay *= backoff_factor
            else:
                logger.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
    
    raise last_exception 