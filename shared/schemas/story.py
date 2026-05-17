"""
Story & Script schemas — Phase 1 output contract.
All downstream phases consume these models.
"""
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
import re


# Gender keyword sets — same as audio_agent._MALE_WORDS / _FEMALE_WORDS
_MALE_W = {
    "male","man","boy","deep","baritone","bass","gruff","husky",
    "tenor","masculine","gentleman","sir","he","him","his",
    "beard","mustache","moustache","father","brother","son",
    "king","lord",
}
_FEMALE_W = {
    "female","woman","girl","soprano","alto","bright","gentle",
    "soft","lady","feminine","she","her","hers",
    "mother","sister","daughter","queen","maiden","princess",
}


def _tok(text: str) -> set:
    return set(re.split(r"[\s,\-_;/\.]+", text.lower()))


class Character(BaseModel):
    """A character in the story with voice and visual attributes."""
    id: str = Field(..., description="Unique ID, e.g. 'char_01'")
    name: str = Field(..., description="Character display name")
    role: str = Field(..., description="protagonist, antagonist, narrator, supporting")
    gender: str = Field(default="", description="Character gender: male, female, or neutral — used for voice assignment")
    voice_description: str = Field(..., description="e.g. 'deep, authoritative male voice'")
    voice_id: str = Field(default="", description="edge-tts voice name, filled by Phase 2")
    visual_description: str = Field(..., description="Physical appearance for image generation")

    @model_validator(mode="after")
    def auto_infer_gender(self) -> "Character":
        """If gender wasn't set by the LLM, infer it from voice/visual descriptions."""
        if self.gender.lower().strip() not in ("male", "female", "neutral", "m", "f"):
            combined = _tok(self.voice_description + " " + self.visual_description)
            is_m = bool(combined & _MALE_W)
            is_f = bool(combined & _FEMALE_W)
            if is_m and not is_f:
                self.gender = "male"
            elif is_f and not is_m:
                self.gender = "female"
            else:
                # Final fallback: use char id parity (odd=male, even=female)
                num = int(''.join(filter(str.isdigit, self.id)) or '1')
                self.gender = "male" if num % 2 == 1 else "female"
        return self


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
