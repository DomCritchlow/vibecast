"""OpenAI GPT-Image artwork provider."""

import base64
from typing import Optional

from openai import OpenAI

from .base import ArtworkProvider


class OpenAIArtworkProvider(ArtworkProvider):
    """Generate artwork using OpenAI's GPT-Image-1.5 API.
    
    GPT-Image-1.5 (December 2025) is OpenAI's latest image generation model,
    offering faster generation and better prompt following than DALL-E 3.
    
    Configuration in config.yaml:
        artwork:
          provider: "openai"
          size: 1024
          quality: "medium"  # low, medium, or high
    """
    
    # GPT-Image-1.5 supported sizes (square, landscape, portrait)
    VALID_SIZES = [1024, 1536, 1792]
    
    # Quality options for GPT-Image-1.5
    # low: ~$0.009/image, medium: ~$0.035/image, high: ~$0.133/image (1024x1024)
    VALID_QUALITIES = ["low", "medium", "high"]
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # Get settings
        self.size = self._validate_size(self.artwork_config.get("size", 1024))
        self.quality = self._validate_quality(self.artwork_config.get("quality", "medium"))
        self.timeout = self.artwork_config.get("timeout_seconds", 60)
        
        # Create client
        self.client = OpenAI()
    
    def _validate_size(self, size: int) -> int:
        """Validate and normalize size for GPT-Image-1.5."""
        if size not in self.VALID_SIZES:
            print(f"Warning: Size {size} not supported, using 1024")
            return 1024
        return size
    
    def _validate_quality(self, quality: str) -> str:
        """Validate quality setting."""
        if quality not in self.VALID_QUALITIES:
            # Map old DALL-E 3 quality names to new ones
            if quality == "standard":
                return "medium"
            elif quality == "hd":
                return "high"
            print(f"Warning: Invalid quality '{quality}', using 'medium'")
            return "medium"
        return quality
    
    @property
    def name(self) -> str:
        return "OpenAI GPT-Image-1.5"
    
    @property
    def supports_seed(self) -> bool:
        # GPT-Image models don't support seeds for reproducibility
        return False
    
    @property
    def supports_negative_prompt(self) -> bool:
        # Include "avoid" instructions in the main prompt
        return False
    
    def generate(
        self,
        prompt: str,
        size: int = 1024,
        format: str = "png",
        seed: Optional[int] = None,
        negative_prompt: Optional[str] = None,
    ) -> bytes:
        """Generate an image using GPT-Image-1.5.
        
        Args:
            prompt: The image generation prompt.
            size: Image size (1024 for square).
            format: Output format (png).
            seed: Ignored - GPT-Image doesn't support seeds.
            negative_prompt: Ignored - include in main prompt instead.
        
        Returns:
            Raw PNG image bytes.
        """
        # Build size string for API (square format)
        size_str = f"{size}x{size}"
        
        # Generate with GPT-Image-1.5
        response = self.client.images.generate(
            model="gpt-image-1.5",
            prompt=prompt,
            size=size_str,
            quality=self.quality,
            n=1,
            response_format="b64_json",  # Get base64 encoded image
        )
        
        # Extract image data
        image_data = response.data[0]
        
        # Log if the model revised the prompt
        if hasattr(image_data, 'revised_prompt') and image_data.revised_prompt:
            revised = image_data.revised_prompt
            if revised != prompt:
                print(f"  Note: GPT-Image revised the prompt")
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_data.b64_json)
        
        return image_bytes
