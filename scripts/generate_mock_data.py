"""
Generate mock PipelineState JSON for development/testing.
Run: python -m scripts.generate_mock_data
Outputs: data/temp/mock_state.json
"""
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.schemas.story import Character, DialogueLine, Scene, StoryOutput
from shared.schemas.pipeline import PipelineState


def generate():
    characters = [
        Character(
            id="char_01", name="Narrator", role="narrator",
            voice_description="calm, authoritative male voice",
            voice_id="en-US-GuyNeural",
            visual_description="wise old man with gray beard, kind blue eyes, wearing a dark robe"
        ),
        Character(
            id="char_02", name="Zara", role="protagonist",
            voice_description="young, enthusiastic female voice",
            voice_id="en-US-JennyNeural",
            visual_description="young woman with short dark hair, brown eyes, wearing a red spacesuit"
        ),
        Character(
            id="char_03", name="Commander Chen", role="supporting",
            voice_description="deep, authoritative male voice",
            voice_id="en-US-DavisNeural",
            visual_description="middle-aged man with silver temples, stern face, blue uniform"
        ),
    ]

    scenes = [
        Scene(
            scene_id="scene_01", title="The Discovery",
            setting="The rust-red surface of Mars under a violet sky at sunset",
            visual_prompt="Astronaut standing on Mars surface, red desert, violet sky, distant mountains, sunset lighting, cinematic wide shot",
            mood="mysterious",
            dialogue=[
                DialogueLine(character_id="char_01", text="The year was 2157. Humanity had long given up on finding water on Mars.", emotion="neutral"),
                DialogueLine(character_id="char_02", text="Wait... these readings can't be right. The scanner shows liquid water beneath us.", emotion="surprised"),
                DialogueLine(character_id="char_03", text="Zara, we've seen false positives before. Don't get your hopes up.", emotion="skeptical"),
            ],
            narration="A vast Martian landscape stretches before us, bathed in the golden light of a distant sunset."
        ),
        Scene(
            scene_id="scene_02", title="The Descent",
            setting="A narrow cave entrance leading deep underground on Mars",
            visual_prompt="Dark cave entrance on Mars surface, red rock formations, astronaut with flashlight, dramatic shadows, suspenseful atmosphere",
            mood="tense",
            dialogue=[
                DialogueLine(character_id="char_02", text="I'm going in. The signal is getting stronger.", emotion="determined"),
                DialogueLine(character_id="char_03", text="That's not protocol, Zara. We should wait for backup.", emotion="worried"),
                DialogueLine(character_id="char_02", text="Some discoveries can't wait, Commander.", emotion="confident"),
            ]
        ),
        Scene(
            scene_id="scene_03", title="The Hidden Ocean",
            setting="A massive underground cavern filled with glowing blue water",
            visual_prompt="Underground cavern on Mars, bioluminescent blue ocean, crystal formations on ceiling, astronaut silhouette, magical ethereal lighting",
            mood="epic",
            dialogue=[
                DialogueLine(character_id="char_02", text="An entire ocean... hidden beneath the surface all along.", emotion="awe"),
                DialogueLine(character_id="char_01", text="And with it, the answer to humanity's greatest question. We are not alone.", emotion="profound"),
                DialogueLine(character_id="char_03", text="This changes everything we thought we knew about Mars.", emotion="amazed"),
            ],
            narration="Before them lay an ocean of impossible beauty, glowing with bioluminescent life that had thrived in silence for millennia."
        ),
    ]

    story = StoryOutput(
        title="The Hidden Ocean of Mars",
        genre="sci-fi",
        synopsis="A young astronaut named Zara discovers an ancient ocean hidden beneath the Martian surface, proving that life exists beyond Earth.",
        characters=characters,
        scenes=scenes
    )

    state = PipelineState(
        user_prompt="A young astronaut discovers a hidden ocean on Mars",
        story=story,
        status="phase1_done"
    )

    os.makedirs("data/temp", exist_ok=True)
    output_path = "data/temp/mock_state.json"
    with open(output_path, "w") as f:
        json.dump(state.model_dump(), f, indent=2)
    print(f"[OK] Mock state written to {output_path}")
    print(f"   Story: '{story.title}'")
    print(f"   Scenes: {len(story.scenes)}")
    print(f"   Characters: {len(story.characters)}")


if __name__ == "__main__":
    generate()
