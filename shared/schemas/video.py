"""
Video schemas — Phase 3 configuration models.
"""
from pydantic import BaseModel, Field
from typing import Optional


class VideoScene(BaseModel):
    """Configuration for rendering a single scene's video clip."""
    scene_id: str
    image_path: str = Field(..., description="Path to generated scene background image")
    ken_burns_style: str = Field(default="zoom_in_center", description="zoompan style key")
    duration_sec: float = Field(..., description="Derived from SceneTiming.measured_duration_ms / 1000")
    output_path: str = Field(default="", description="Path where the final scene clip is written")


class PortraitOverlay(BaseModel):
    """Timing for a character portrait overlay on the video."""
    portrait_path: str = Field(..., description="Path to character portrait image")
    start_sec: float
    end_sec: float
    character_id: str


class CompositionConfig(BaseModel):
    """Global settings for the final video composition."""
    fps: int = Field(default=25, description="Global FPS — must be 25 everywhere")
    resolution: str = Field(default="1920x1080")
    codec: str = Field(default="libx264")
    subtitle_font_size: int = Field(default=22)
    subtitle_color: str = Field(default="&HFFFFFF&")
    transition_duration_sec: float = Field(default=0.5, description="Cross-dissolve between scenes")
