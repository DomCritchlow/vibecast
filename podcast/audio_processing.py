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
        "fable_light": {
            "description": "Ultra-light processing for fable voice - removes rumble, minimal intervention",
            "filters": [
                "highpass=f=90",  # Cut rumble/low-end artifacts
                "equalizer=f=480:width_type=o:width=2.5:g=-1.2",  # Very light tin-can reduction
                "equalizer=f=7000:width_type=o:width=2.5:g=-1",  # Very gentle de-ess
                "loudnorm=I=-16:TP=-1.5:LRA=16",  # Normalize only, preserve maximum dynamics
            ],
        },
        "clarity": {
            "description": "Remove tin-can sound - for older tts-1 model",
            "filters": [
                "highpass=f=90",
                "equalizer=f=500:width_type=o:width=1.5:g=-4",
                "equalizer=f=3000:width_type=o:width=2:g=6",
                "equalizer=f=10000:width_type=h:width=5000:g=2",
                "compand",
                "loudnorm",
            ],
        },
        "podcast": {
            "description": "Full professional podcast processing chain",
            "filters": [
                "highpass=f=100",
                "equalizer=f=200:width_type=h:width=100:g=2",
                "equalizer=f=3000:width_type=h:width=2000:g=5",
                "equalizer=f=8000:width_type=h:width=4000:g=3",
                "compand=attacks=0.1:decays=0.4:points=-80/-900|-50/-20|-30/-10|-20/-8|-10/-6|0/-4|20/-4:soft-knee=6:gain=3:volume=-90:delay=0.05",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
            ],
        },
    }
    
    def __init__(self, preset: str = "fable_light"):
        """Initialize audio processor.
        
        Args:
            preset: Processing preset name (none, fable_light, clarity, podcast)
        """
        self.preset = preset.lower()
        if self.preset not in self.PRESETS:
            print(f"Warning: Unknown preset '{preset}', using 'fable_light'")
            self.preset = "fable_light"
        
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
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
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
            
            # Run ffmpeg with 192k output
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-af", filter_chain,
                "-b:a", "192k",  # High-quality MP3 output
                "-y",
                final_output,
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
            )
            
            if result.returncode != 0:
                print(f"Warning: ffmpeg processing failed")
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
    preset: str = "fable_light",
    output_path: Optional[str] = None,
) -> bytes:
    """Convenience function to enhance audio.
    
    Args:
        audio_bytes: Input audio data (MP3)
        preset: Processing preset (none, fable_light, clarity, podcast)
        output_path: Optional path to save output
        
    Returns:
        Enhanced audio bytes (MP3)
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

