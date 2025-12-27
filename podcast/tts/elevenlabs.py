"""ElevenLabs TTS provider.

ElevenLabs offers high-quality, natural-sounding TTS with:
- Custom voice cloning
- Multiple pre-made voices
- Emotional control
- Multiple languages

To use this provider:
1. Sign up at https://elevenlabs.io
2. Get your API key from the dashboard
3. Set ELEVENLABS_API_KEY environment variable
4. Configure in config.yaml:
   
   tts:
     provider: "elevenlabs"
     elevenlabs:
       voice_id: "your-voice-id"  # or use a preset
       model_id: "eleven_multilingual_v2"
       stability: 0.5
       similarity_boost: 0.75

Note: ElevenLabs is NOT currently enabled. To enable:
1. Install: pip install elevenlabs
2. Set your API key
3. Change tts.provider to "elevenlabs" in config.yaml
"""

import os
from typing import List, Optional

from .base import TTSProvider


class ElevenLabsTTSProvider(TTSProvider):
    """Text-to-speech using ElevenLabs API.
    
    Features:
    - High-quality, natural voices
    - Voice cloning capability
    - Emotional range control
    - Multi-language support
    
    Configuration in config.yaml:
        tts:
          provider: "elevenlabs"
          elevenlabs:
            voice_id: "21m00Tcm4TlvDq8ikWAM"  # Rachel (default)
            model_id: "eleven_multilingual_v2"
            stability: 0.5
            similarity_boost: 0.75
            format: "mp3_44100_128"
    """
    
    # Default voices available to all accounts
    PRESET_VOICES = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",
        "drew": "29vD33N1CtxCmqQRPOHJ",
        "clyde": "2EiwWnXFnvU5JabPnv8n",
        "paul": "5Q0t7uMcjvnagumLfvZi",
        "domi": "AZnzlk1XvdvUeBnXmlld",
        "dave": "CYw3kZ02Hs0563khs1Fj",
        "fin": "D38z5RcWu1voky8WS1ja",
        "sarah": "EXAVITQu4vr4xnSDxMaL",
        "antoni": "ErXwobaYiN019PkySvjV",
        "thomas": "GBv7mTt0atIp3Br8iCZE",
        "charlie": "IKne3meq5aSn9XLyUdCD",
        "emily": "LcfcDJNUP1GQjkzn1xUU",
        "elli": "MF3mGyEYCl7XYWbV9V6O",
        "callum": "N2lVS1w4EtoT3dr4eOWO",
        "patrick": "ODq5zmih8GrVes37Dizd",
        "harry": "SOYHLrjzK2X1ezoPC6cr",
        "liam": "TX3LPaxmHKxFdv7VOQHJ",
        "dorothy": "ThT5KcBeYPX3keUQqHPh",
        "josh": "TxGEqnHWrfWFTfGW9XjX",
        "arnold": "VR6AewLTigWG4xSOukaG",
        "charlotte": "XB0fDUnXU5powFXDhCwa",
        "alice": "Xb7hH8MSUJpSbSDYk0k2",
        "matilda": "XrExE9yKIg1WjnnlVkGX",
        "matthew": "Yko7PKHZNXotIFUBG7I9",
        "james": "ZQe5CZNOzWyzPSCn5a3c",
        "joseph": "Zlb1dXrM653N07WRdFW3",
        "jeremy": "bVMeCyTHy58xNoL34h3p",
        "nicole": "piTKgcLEGmPE4e6mEKli",
        "bill": "pqHfZKP75CvOlQylNhV4",
        "jessie": "t0jbNlBVZ17f02VDIeMI",
        "adam": "pNInz6obpgDQGcFmaJgB",
        "sam": "yoZ06aMxZJJ28mfd3POQ",
    }
    
    # Models available
    MODELS = {
        "eleven_multilingual_v2": "Best quality, multilingual",
        "eleven_turbo_v2_5": "Low latency, good quality",
        "eleven_monolingual_v1": "Legacy English model",
    }
    
    # Character limit per request
    MAX_CHARS = 5000
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # Check if elevenlabs is installed
        self._client = None
        self._available = self._check_availability()
        
        if not self._available:
            return
        
        self.elevenlabs_config = self.tts_config.get("elevenlabs", {})
        
        # Get settings
        self.voice_id = self._resolve_voice_id(
            self.elevenlabs_config.get("voice_id", "rachel")
        )
        self.model_id = self.elevenlabs_config.get(
            "model_id", "eleven_multilingual_v2"
        )
        self.stability = self.elevenlabs_config.get("stability", 0.5)
        self.similarity_boost = self.elevenlabs_config.get("similarity_boost", 0.75)
        self.output_format = self.elevenlabs_config.get("format", "mp3_44100_128")
    
    def _check_availability(self) -> bool:
        """Check if ElevenLabs is properly configured."""
        # Check for API key
        if not os.environ.get("ELEVENLABS_API_KEY"):
            return False
        
        # Check if library is installed
        try:
            from elevenlabs import ElevenLabs
            self._client = ElevenLabs()
            return True
        except ImportError:
            return False
        except Exception as e:
            print(f"Warning: ElevenLabs init failed: {e}")
            return False
    
    def _resolve_voice_id(self, voice: str) -> str:
        """Resolve voice name to ID if using a preset."""
        if voice.lower() in self.PRESET_VOICES:
            return self.PRESET_VOICES[voice.lower()]
        return voice
    
    @property
    def name(self) -> str:
        return "ElevenLabs TTS"
    
    @property
    def max_chars(self) -> int:
        return self.MAX_CHARS
    
    @property
    def supported_formats(self) -> List[str]:
        return ["mp3_44100_128", "mp3_44100_192", "pcm_16000", "pcm_22050", "pcm_24000"]
    
    def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio using ElevenLabs.
        
        Raises:
            RuntimeError: If ElevenLabs is not available.
        """
        if not self._available:
            raise RuntimeError(
                "ElevenLabs is not available. Make sure you have:\n"
                "1. Installed: pip install elevenlabs\n"
                "2. Set ELEVENLABS_API_KEY environment variable\n"
                "3. Selected provider: 'elevenlabs' in tts.provider config"
            )
        
        from elevenlabs import VoiceSettings
        
        chunks = self.chunk_text(text)
        
        if len(chunks) > 1:
            print(f"  Text is {len(text)} chars, splitting into {len(chunks)} chunks")
        
        audio_parts = []
        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                print(f"  Synthesizing chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")
            
            response = self._client.text_to_speech.convert(
                voice_id=self.voice_id,
                model_id=self.model_id,
                text=chunk,
                output_format=self.output_format,
                voice_settings=VoiceSettings(
                    stability=self.stability,
                    similarity_boost=self.similarity_boost,
                ),
            )
            
            # Response is a generator of bytes
            audio_bytes = b''.join(response)
            audio_parts.append(audio_bytes)
        
        return b''.join(audio_parts)


def get_voice_description(voice: str) -> Optional[str]:
    """Get a description for an ElevenLabs voice."""
    descriptions = {
        "rachel": "Young, warm American female - conversational and engaging",
        "drew": "Middle-aged American male - clear and professional",
        "sarah": "Young British female - soft and articulate",
        "adam": "Deep American male - authoritative and calm",
        "emily": "Young American female - bright and enthusiastic",
        "josh": "Young American male - friendly and upbeat",
        "charlotte": "British female - warm and reassuring",
        "matilda": "Australian female - clear and professional",
        "matthew": "British male - warm and engaging",
    }
    return descriptions.get(voice.lower())


