"""OpenAI GPT-Image artwork provider."""

import base64
import logging

from openai import OpenAI

from .base import ArtworkProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-image-2"


class OpenAIArtworkProvider(ArtworkProvider):
    """Generate artwork using OpenAI's GPT-Image API.

    Defaults to gpt-image-2 (April 2026), which reasons about composition
    before generating and renders text far more reliably than earlier models.

    Configuration in config.yaml:
        artwork:
          provider: "openai"
          openai:
            model: "gpt-image-2"
          size: 1024
          quality: "medium"  # low, medium, or high
    """

    VALID_SIZES = [1024, 1536, 1792]
    VALID_QUALITIES = ["low", "medium", "high"]

    def __init__(self, config: dict):
        super().__init__(config)

        self.model = (self.artwork_config.get("openai") or {}).get("model", DEFAULT_MODEL)
        self.size = self._validate_size(self.artwork_config.get("size", 1024))
        self.quality = self._validate_quality(self.artwork_config.get("quality", "medium"))
        self.timeout = self.artwork_config.get("timeout_seconds", 120)

        self.client = OpenAI()

    def _validate_size(self, size: int) -> int:
        if size not in self.VALID_SIZES:
            logger.warning("Size %s not supported, using 1024", size)
            return 1024
        return size

    def _validate_quality(self, quality: str) -> str:
        if quality not in self.VALID_QUALITIES:
            # Map legacy DALL-E quality names to current ones
            if quality == "standard":
                return "medium"
            if quality == "hd":
                return "high"
            logger.warning("Invalid quality '%s', using 'medium'", quality)
            return "medium"
        return quality

    @property
    def name(self) -> str:
        return f"OpenAI {self.model}"

    @property
    def supports_seed(self) -> bool:
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
        seed: int | None = None,
        negative_prompt: str | None = None,
    ) -> bytes:
        """Generate an image and return raw bytes.

        seed and negative_prompt are accepted for interface compatibility
        but ignored — GPT-Image models support neither.
        """
        output_format = format if format in ["png", "jpeg", "webp"] else "png"

        response = self.client.with_options(timeout=self.timeout).images.generate(
            model=self.model,
            prompt=prompt,
            size=f"{size}x{size}",
            quality=self.quality,
            n=1,
            output_format=output_format,
        )

        return base64.b64decode(response.data[0].b64_json)
