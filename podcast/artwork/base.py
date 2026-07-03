"""Base class and types for artwork generation providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ArtBrief:
    """Art direction brief generated from episode content.

    Attributes:
        mood_adjectives: 2-3 words describing the emotional tone.
        single_scene_metaphor: ONE clear scene description (not a collage).
        secondary_detail: Exactly one small symbolic detail.
        accent_color: Selected color from the palette.
    """

    mood_adjectives: list[str]
    single_scene_metaphor: str
    secondary_detail: str
    accent_color: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "mood_adjectives": self.mood_adjectives,
            "single_scene_metaphor": self.single_scene_metaphor,
            "secondary_detail": self.secondary_detail,
            "accent_color": self.accent_color,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtBrief":
        """Create from dictionary."""
        return cls(
            mood_adjectives=data.get("mood_adjectives", []),
            single_scene_metaphor=data.get("single_scene_metaphor", ""),
            secondary_detail=data.get("secondary_detail", ""),
            accent_color=data.get("accent_color", ""),
        )


@dataclass
class ArtworkResult:
    """Result from artwork generation.

    Attributes:
        image_bytes: Raw image data (PNG).
        artwork_url: Public URL after upload to R2.
        prompt: The full prompt used for generation.
        negative_prompt: Negative prompt if supported.
        brief: The art brief used to generate the prompt.
        metadata: Additional metadata for debugging/reproducibility.
    """

    image_bytes: bytes
    artwork_url: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    brief: ArtBrief | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ArtworkProvider(ABC):
    """Abstract base class for artwork generation providers.

    Implement this class to add new image generation services.

    Example:
        class StableDiffusionProvider(ArtworkProvider):
            def generate(self, prompt, size, format, seed) -> bytes:
                # Call Stable Diffusion API
                return image_bytes
    """

    def __init__(self, config: dict):
        """Initialize the provider with configuration.

        Args:
            config: Full configuration dictionary.
        """
        self.config = config
        self.artwork_config = config.get("artwork", {})

    @abstractmethod
    def generate(
        self,
        prompt: str,
        size: int = 1024,
        format: str = "png",
        seed: int | None = None,
        negative_prompt: str | None = None,
    ) -> bytes:
        """Generate an image from a prompt.

        Args:
            prompt: The image generation prompt.
            size: Image size (square).
            format: Output format (png, jpg).
            seed: Random seed for reproducibility (if supported).
            negative_prompt: Things to avoid (if supported).

        Returns:
            Raw image bytes.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this provider."""
        pass

    @property
    def supports_seed(self) -> bool:
        """Whether this provider supports deterministic seeds."""
        return False

    @property
    def supports_negative_prompt(self) -> bool:
        """Whether this provider supports negative prompts."""
        return False
