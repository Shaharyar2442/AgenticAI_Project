"""
Edit intent schemas — Phase 5 classification models.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class EditIntent(BaseModel):
    """Structured output from the edit intent classification agent."""
    intent: str = Field(..., description="e.g. 'change_voice_tone', 'apply_filter', 'add_bgm'")
    target: str = Field(..., description="One of: 'audio', 'video_frame', 'video', 'script'")
    scope: str = Field(
        default="all",
        description="e.g. 'character:Narrator', 'scene:scene_02', 'all'"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extra params, e.g. {'tone': 'whispered', 'filter': 'darken'}"
    )
