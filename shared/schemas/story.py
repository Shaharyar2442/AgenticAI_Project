"""
Story & Script schemas — Phase 1 output contract.
All downstream phases consume these models.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class Character(BaseModel):
    """A character in the story with voice and visual attributes."""
    id: str = Field(..., description="Unique ID, e.g. 'char_01'")
    name: str = Field(..., description="Character display name")
    role: str = Field(..., description="protagonist, antagonist, narrator, supporting")
    voice_description: str = Field(..., description="e.g. 'deep, authoritative male voice'")
    voice_id: str = Field(default="", description="edge-tts voice name, filled by Phase 2")
    visual_description: str = Field(..., description="Physical appearance for image generation")


class DialogueLine(BaseModel):
    """A single line of dialogue spoken by a character."""
    character_id: str = Field(..., description="References Character.id")
    text: str = Field(..., description="The spoken dialogue text")
    emotion: str = Field(default="neutral", description="happy, sad, angry, whispered, etc.")


class Scene(BaseModel):
    """A scene in the story. Duration is NEVER set here — it comes from TimingManifest."""
    scene_id: str = Field(..., description="Unique ID, e.g. 'scene_01'")
    title: str = Field(..., description="Short scene title")
    setting: str = Field(..., description="Description of the scene's physical environment")
    visual_prompt: str = Field(..., description="Detailed prompt for image generation")
    mood: str = Field(..., description="happy, tense, melancholic, epic, mysterious, calm")
    dialogue: List[DialogueLine] = Field(default_factory=list)
    narration: Optional[str] = Field(default=None, description="Optional narrator text for this scene")
    # NOTE: No duration field. Duration is NEVER guessed.
    # The authoritative duration lives in TimingManifest.scene_durations,
    # set by Phase 2 after measuring actual audio output.


class StoryOutput(BaseModel):
    """Complete output from Phase 1 — consumed by all downstream phases."""
    title: str
    genre: str
    synopsis: str
    characters: List[Character]
    scenes: List[Scene]
