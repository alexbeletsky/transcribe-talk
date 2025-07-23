"""
Text-to-speech synthesis using ElevenLabs.

This module provides TTS capabilities for TranscribeTalk:
- ElevenLabs API client management
- Voice selection and management
- Audio format configuration
- Streaming and non-streaming synthesis
- Voice cloning support (if available)
"""

import logging
from typing import Dict, List, Optional, Union, Iterator

from elevenlabs.client import ElevenLabs

from ..config.settings import ElevenLabsConfig

logger = logging.getLogger(__name__)


class ElevenLabsTTS:
    """
    ElevenLabs text-to-speech synthesizer.
    
    Features:
    - Multiple voice options
    - Configurable audio formats
    - Streaming and non-streaming synthesis
    - Voice settings customization
    - Error handling and retry logic
    """
    
    def __init__(self, config: ElevenLabsConfig):
        """
        Initialize the ElevenLabs TTS client.
        
        Args:
            config: ElevenLabs configuration settings
        """
        self.config = config
        self.client = ElevenLabs(api_key=config.api_key)
        
        logger.info(f"ElevenLabs TTS initialized with voice: {config.voice_id}")
        logger.info(f"Using model: {config.model_id}, format: {config.output_format}")
    
    def synthesize(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        output_format: Optional[str] = None
    ) -> bytes:
        """
        Synthesize text to speech.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use. If None, uses config default
            model_id: Model ID to use. If None, uses config default
            output_format: Output format. If None, uses config default
            
        Returns:
            bytes: Audio data
        """
        # Use config defaults if not specified
        voice_id = voice_id or self.config.voice_id
        model_id = model_id or self.config.model_id
        output_format = output_format or self.config.output_format
        
        logger.info(f"Synthesizing text: {len(text)} characters")
        logger.debug(f"Text to synthesize: {text}")
        
        try:
            # Make TTS API call
            audio_data = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                output_format=output_format,
            )
            
            # Convert generator to bytes if needed
            if isinstance(audio_data, Iterator):
                audio_bytes = b''.join(audio_data)
            else:
                audio_bytes = audio_data
            
            logger.info(f"TTS synthesis completed: {len(audio_bytes)} bytes")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Error in TTS synthesis: {e}")
            raise
    
    def synthesize_streaming(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        output_format: Optional[str] = None
    ) -> Iterator[bytes]:
        """
        Synthesize text to speech with streaming output.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use. If None, uses config default
            model_id: Model ID to use. If None, uses config default
            output_format: Output format. If None, uses config default
            
        Yields:
            bytes: Audio data chunks
        """
        # Use config defaults if not specified
        voice_id = voice_id or self.config.voice_id
        model_id = model_id or self.config.model_id
        output_format = output_format or self.config.output_format
        
        logger.info(f"Starting streaming TTS synthesis: {len(text)} characters")
        
        try:
            # Make streaming TTS API call
            audio_stream = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                output_format=output_format,
                stream=True,
            )
            
            # Yield audio chunks
            total_bytes = 0
            for chunk in audio_stream:
                total_bytes += len(chunk)
                yield chunk
            
            logger.info(f"Streaming TTS synthesis completed: {total_bytes} bytes")
            
        except Exception as e:
            logger.error(f"Error in streaming TTS synthesis: {e}")
            raise
    
    def get_available_voices(self) -> List[Dict]:
        """
        Get list of available voices.
        
        Returns:
            list: List of voice information dictionaries
        """
        try:
            logger.info("Fetching available voices...")
            
            voices = self.client.voices.get_all()
            voice_list = []
            
            for voice in voices.voices:
                voice_info = {
                    'voice_id': voice.voice_id,
                    'name': voice.name,
                    'category': getattr(voice, 'category', 'Unknown'),
                    'description': getattr(voice, 'description', ''),
                    'preview_url': getattr(voice, 'preview_url', ''),
                    'labels': getattr(voice, 'labels', {}),
                }
                voice_list.append(voice_info)
            
            logger.info(f"Found {len(voice_list)} available voices")
            return voice_list
            
        except Exception as e:
            logger.error(f"Error fetching voices: {e}")
            return []
    
    def get_voice_info(self, voice_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific voice.
        
        Args:
            voice_id: Voice ID to query
            
        Returns:
            dict: Voice information or None if not found
        """
        try:
            logger.info(f"Fetching voice info for: {voice_id}")
            
            voice = self.client.voices.get(voice_id)
            
            voice_info = {
                'voice_id': voice.voice_id,
                'name': voice.name,
                'category': getattr(voice, 'category', 'Unknown'),
                'description': getattr(voice, 'description', ''),
                'preview_url': getattr(voice, 'preview_url', ''),
                'labels': getattr(voice, 'labels', {}),
                'settings': getattr(voice, 'settings', {}),
            }
            
            return voice_info
            
        except Exception as e:
            logger.error(f"Error fetching voice info for {voice_id}: {e}")
            return None
    
    def change_voice(self, voice_id: str) -> bool:
        """
        Change the default voice.
        
        Args:
            voice_id: New voice ID to use
            
        Returns:
            bool: True if voice change was successful
        """
        try:
            # Verify voice exists
            voice_info = self.get_voice_info(voice_id)
            if voice_info is None:
                logger.error(f"Voice {voice_id} not found")
                return False
            
            # Update configuration
            self.config.voice_id = voice_id
            logger.info(f"Changed default voice to: {voice_info['name']} ({voice_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error changing voice to {voice_id}: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available TTS models.
        
        Returns:
            list: Available model IDs
        """
        try:
            logger.info("Fetching available models...")
            
            models = self.client.models.get_all()
            model_list = [model.model_id for model in models]
            
            logger.info(f"Found {len(model_list)} available models")
            return model_list
            
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            # Return common known models as fallback
            return [
                "eleven_multilingual_v2",
                "eleven_multilingual_v1", 
                "eleven_monolingual_v1",
                "eleven_turbo_v2",
            ]
    
    def change_model(self, model_id: str) -> None:
        """
        Change the TTS model.
        
        Args:
            model_id: New model ID to use
        """
        logger.info(f"Changing TTS model from {self.config.model_id} to {model_id}")
        self.config.model_id = model_id
    
    def change_output_format(self, output_format: str) -> None:
        """
        Change the audio output format.
        
        Args:
            output_format: New output format (e.g., "mp3_44100_128", "wav")
        """
        logger.info(f"Changing output format from {self.config.output_format} to {output_format}")
        self.config.output_format = output_format
    
    def test_synthesis(self, test_text: str = "Hello, this is a test of the text to speech system.") -> bool:
        """
        Test TTS synthesis functionality.
        
        Args:
            test_text: Text to use for testing
            
        Returns:
            bool: True if test was successful
        """
        try:
            logger.info("Testing TTS synthesis...")
            
            # Synthesize test text
            audio_data = self.synthesize(test_text)
            
            if audio_data and len(audio_data) > 0:
                logger.info(f"TTS synthesis test successful: {len(audio_data)} bytes generated")
                return True
            else:
                logger.error("TTS synthesis test failed: no audio data generated")
                return False
                
        except Exception as e:
            logger.error(f"TTS synthesis test failed: {e}")
            return False
    
    def get_usage_info(self) -> Optional[Dict]:
        """
        Get API usage information (if available).
        
        Returns:
            dict: Usage information or None if not available
        """
        try:
            logger.info("Fetching usage information...")
            
            # Note: ElevenLabs API usage endpoint may vary
            # This is a placeholder for usage information
            usage_info = {
                'status': 'Available',
                'message': 'Usage information not implemented in this version'
            }
            
            return usage_info
            
        except Exception as e:
            logger.error(f"Error fetching usage info: {e}")
            return None


def get_popular_voices() -> List[Dict[str, str]]:
    """
    Get a list of popular ElevenLabs voices with their IDs.
    
    Returns:
        list: Popular voice information
    """
    return [
        {
            'voice_id': 'wyWA56cQNU2KqUW4eCsI',
            'name': 'Adam',
            'description': 'Deep, authoritative male voice',
            'category': 'Generated'
        },
        {
            'voice_id': 'EXAVITQu4vr4xnSDxMaL',
            'name': 'Bella',
            'description': 'Young, warm female voice',
            'category': 'Generated'
        },
        {
            'voice_id': 'ErXwobaYiN019PkySvjV',
            'name': 'Antoni',
            'description': 'Well-rounded male voice',
            'category': 'Generated'
        },
        {
            'voice_id': 'VR6AewLTigWG4xSOukaG',
            'name': 'Arnold',
            'description': 'Confident, strong male voice',
            'category': 'Generated'
        },
        {
            'voice_id': 'pNInz6obpgDQGcFmaJgB',
            'name': 'Adam (clone)',
            'description': 'Professional male voice',
            'category': 'Professional'
        }
    ]


def get_supported_formats() -> List[str]:
    """
    Get list of supported audio output formats.
    
    Returns:
        list: Supported format strings
    """
    return [
        "mp3_44100_32",
        "mp3_44100_64", 
        "mp3_44100_96",
        "mp3_44100_128",
        "mp3_44100_192",
        "pcm_16000",
        "pcm_22050",
        "pcm_24000",
        "pcm_44100",
        "ulaw_8000"
    ] 