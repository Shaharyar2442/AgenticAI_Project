"""
Audio schemas — Phase 2 output contract.
TimingManifest.scene_durations is THE source of truth for video clip durations.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class WordTimestamp(BaseModel):
    """A single word with its timing from edge-tts WordBoundary events."""
    word: str
    start_ms: int
    end_ms: int


class AudioSegment(BaseModel):
    """A single audio segment (one dialogue line, narration chunk, or BGM track)."""
    scene_id: str
    audio_file: str = Field(..., description="Absolute path to .mp3 file")
    type: str = Field(..., description="'dialogue', 'narration', or 'bgm'")
    character_id: Optional[str] = Field(default=None, description="References Character.id for dialogue")
    start_ms: int = Field(..., description="Start time within the scene in milliseconds")
    end_ms: int = Field(..., description="End time within the scene in milliseconds")
    word_timestamps: List[WordTimestamp] = Field(default_factory=list)


class SceneTiming(BaseModel):
    """Measured (not estimated) timing for one scene.
    Phase 3 reads ONLY this to determine video clip duration.
    """
    scene_id: str
    measured_duration_ms: int = Field(..., description="THE source of truth for Phase 3 video clip duration")
    audio_file: str = Field(..., description="Combined scene audio (all dialogue + narration merged)")
    srt_file: str = Field(..., description="Word-synced .srt subtitle file path")


class TimingManifest(BaseModel):
    """Complete audio timing output from Phase 2."""
    segments: List[AudioSegment] = Field(..., description="Per-line audio segment detail")
    scene_durations: List[SceneTiming] = Field(..., description="Per-scene measured durations — Phase 3 reads ONLY this")
    total_duration_ms: int
