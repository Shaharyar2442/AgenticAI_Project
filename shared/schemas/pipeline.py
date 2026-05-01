"""
PipelineState — the master state object passed through the entire pipeline.
Every phase reads from and writes to this object.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict
from shared.schemas.story import StoryOutput
from shared.schemas.audio import TimingManifest


class PipelineState(BaseModel):
    """Master state object. Versioned and snapshotted by state_manager."""
    version: int = Field(default=1, description="Auto-incremented on each pipeline run or edit")
    user_prompt: str = Field(..., description="The original user prompt")
    story: Optional[StoryOutput] = None
    timing_manifest: Optional[TimingManifest] = None

    # Key format convention: use the exact `id` field from the corresponding model.
    # scene_id format: "scene_01", "scene_02", etc.
    # character.id format: "char_01", "char_02", etc.
    # A key format mismatch between Phase 1 output and Phase 3 lookup will produce KeyError.
    scene_images: Dict[str, str] = Field(
        default_factory=dict,
        description="scene_id -> absolute file path to scene background image"
    )
    character_portraits: Dict[str, str] = Field(
        default_factory=dict,
        description="character.id -> absolute file path to character portrait image"
    )
    scene_videos: Dict[str, str] = Field(
        default_factory=dict,
        description="scene_id -> absolute file path to rendered scene clip"
    )
    final_video_path: Optional[str] = Field(
        default=None,
        description="Path to the final composited MP4"
    )
    status: str = Field(
        default="initialized",
        description="initialized, phase1_done, phase2_done, phase3_done, complete"
    )
