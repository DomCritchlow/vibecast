"""Audio post-processing for podcast episodes.

This module provides audio enhancement filters to improve TTS output quality:
- Remove "tin can" resonances
- Add warmth and presence
- Professional broadcast sound
- Loudness normalization

Uses ffmpeg for processing. Requires ffmpeg to be installed.
"""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional


class AudioProcessor:
    """Post-process audio files with professional quality filters."""
    
    PRESETS = {
        "none": {
            "description": "No processing (original TTS output)",
            "filters": None,
        },
        "clarity": {
            "description": "Remove tin-can sound, boost vocal clarity",
            "filters": [
                "highpass=f=90",  # Remove low rumble
                "equalizer=f=500:width_type=o:width=1.5:g=-4",  # Cut resonant "tin can" freq
                "equalizer=f=3000:width_type=o:width=2:g=6",  # Boost presence
                "equalizer=f=10000:width_type=h:width=5000:g=2",  # Smooth highs
                "compand",  # Light compression
                "loudnorm",  # Normalize loudness
            ],
        },
        "warm": {
            "description": "Warm, full sound with bass boost",
            "filters": [
                "highpass=f=80",  # Gentle high-pass
                "bass=g=3",  # Boost bass
                "treble=g=2",  # Enhance treble
                "loudnorm",  # Normalize
            ],
        },
        "broadcast": {
            "description": "Professional radio/broadcast quality",
            "filters": [
                "highpass=f=80",
                "equalizer=f=3000:width_type=h:width=2000:g=4",  # Presence boost
                "compand=attacks=0.3:decays=0.8:points=-80/-900|-45/-15|-27/-9|0/-7|20/-7:soft-knee=6:gain=5:volume=-90:delay=0.1",
                "loudnorm",
            ],
        },
        "podcast": {
            "description": "Full professional podcast processing chain",
            "filters": [
                "highpass=f=100",  # Clean low-end
                "equalizer=f=200:width_type=h:width=100:g=2",  # Warmth
                "equalizer=f=3000:width_type=h:width=2000:g=5",  # Presence
                "equalizer=f=8000:width_type=h:width=4000:g=3",  # Air/clarity
                "compand=attacks=0.1:decays=0.4:points=-80/-900|-50/-20|-30/-10|-20/-8|-10/-6|0/-4|20/-4:soft-knee=6:gain=3:volume=-90:delay=0.05",
                "loudnorm=I=-16:TP=-1.5:LRA=11",  # Podcast loudness standard
            ],
        },
        "natural": {
            "description": "Minimal processing - preserves voice character (great for gpt-4o-mini-tts)",
            "filters": [
                "highpass=f=70",  # Very gentle high-pass
                "equalizer=f=200:width_type=h:width=100:g=1",  # Subtle warmth
                "loudnorm=I=-16:TP=-1.5:LRA=15",  # Normalize but preserve wide dynamics
            ],
        },
        "storyteller": {
            "description": "Optimized for expressive voices like fable - preserves dynamics and emotion",
            "filters": [
                "highpass=f=75",  # Clean but not aggressive
                "equalizer=f=180:width_type=h:width=120:g=2",  # Gentle warmth
                "equalizer=f=3200:width_type=o:width=1.8:g=3",  # Moderate presence (not too hot)
                "equalizer=f=7500:width_type=h:width=3500:g=1",  # Subtle air
                "compand=attacks=0.3:decays=0.7:points=-80/-900|-45/-18|-30/-12|-20/-9|-10/-6|0/-3|20/-3:soft-knee=8:gain=2:volume=-90:delay=0.08",  # Light compression, preserve expression
                "loudnorm=I=-16:TP=-1.5:LRA=13",  # Standard loudness but more dynamic range
            ],
        },
        "crisp": {
            "description": "Clean and clear - minimal warmth, maximum intelligibility",
            "filters": [
                "highpass=f=85",  # Clean low-end
                "equalizer=f=3500:width_type=o:width=2:g=4",  # Strong presence
                "equalizer=f=8000:width_type=h:width=4000:g=2",  # Add sparkle
                "compand=attacks=0.2:decays=0.5:points=-80/-900|-45/-16|-25/-10|-15/-7|-5/-3|0/-2|20/-2:soft-knee=6:gain=2:volume=-90:delay=0.05",  # Moderate compression
                "loudnorm=I=-16:TP=-1.5:LRA=12",  # Standard loudness
            ],
        },
    }
    
    def __init__(self, preset: str = "clarity"):
        """Initialize audio processor.
        
        Args:
            preset: Processing preset name (none, clarity, warm, broadcast, podcast)
        """
        self.preset = preset.lower()
        if self.preset not in self.PRESETS:
            print(f"Warning: Unknown preset '{preset}', using 'clarity'")
            self.preset = "clarity"
        
        self.ffmpeg_available = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True
            else:
                print("Warning: ffmpeg not working properly. Audio processing disabled.")
                return False
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Warning: ffmpeg not found. Audio processing disabled.")
            return False
    
    def process(self, audio_bytes: bytes, output_path: Optional[str] = None) -> bytes:
        """Process audio with selected preset.
        
        Args:
            audio_bytes: Input audio data (MP3)
            output_path: Optional path to save processed audio
            
        Returns:
            Processed audio bytes (MP3)
        """
        # Skip processing if ffmpeg not available or preset is "none"
        if not self.ffmpeg_available or self.preset == "none":
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
            return audio_bytes
        
        preset_config = self.PRESETS[self.preset]
        filters = preset_config["filters"]
        
        if not filters:
            return audio_bytes
        
        # Create temp files
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as input_file:
            input_file.write(audio_bytes)
            input_path = input_file.name
        
        try:
            # Determine output path
            if output_path:
                final_output = output_path
            else:
                output_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                final_output = output_file.name
                output_file.close()
            
            # Build filter chain
            filter_chain = ",".join(filters)
            
            # Run ffmpeg
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-af", filter_chain,
                "-y",  # Overwrite output
                final_output,
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
            )
            
            if result.returncode != 0:
                print(f"Warning: ffmpeg processing failed: {result.stderr.decode()}")
                return audio_bytes
            
            # Read processed audio
            with open(final_output, "rb") as f:
                processed_bytes = f.read()
            
            # Clean up temp files
            os.unlink(input_path)
            if not output_path:
                os.unlink(final_output)
            
            return processed_bytes
            
        except Exception as e:
            print(f"Warning: Audio processing failed: {e}")
            # Clean up
            if os.path.exists(input_path):
                os.unlink(input_path)
            return audio_bytes
    
    def process_file(self, input_path: str, output_path: str) -> bool:
        """Process an audio file.
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save processed audio
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(input_path, "rb") as f:
                audio_bytes = f.read()
            
            processed = self.process(audio_bytes, output_path)
            return len(processed) > 0
            
        except Exception as e:
            print(f"Error processing file: {e}")
            return False
    
    @classmethod
    def list_presets(cls) -> dict:
        """List all available presets with descriptions."""
        return {
            name: config["description"]
            for name, config in cls.PRESETS.items()
        }


def enhance_audio(
    audio_bytes: bytes,
    preset: str = "clarity",
    output_path: Optional[str] = None,
) -> bytes:
    """Convenience function to enhance audio.
    
    Args:
        audio_bytes: Input audio data
        preset: Processing preset (none, clarity, warm, broadcast, podcast)
        output_path: Optional path to save output
        
    Returns:
        Enhanced audio bytes
    """
    processor = AudioProcessor(preset=preset)
    return processor.process(audio_bytes, output_path)


if __name__ == "__main__":
    # Demo/test
    print("🎙️  Audio Processing Presets")
    print("=" * 50)
    for name, desc in AudioProcessor.list_presets().items():
        print(f"  {name:12s} - {desc}")
    print()
    print("Usage:")
    print("  from podcast.audio_processing import enhance_audio")
    print("  enhanced = enhance_audio(audio_bytes, preset='clarity')")

