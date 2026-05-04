"""
Phase 1 Unit Tests — Story & Script Generation schemas (offline, no API needed).
"""
import pytest
from pydantic import ValidationError
from shared.schemas.story import Character, DialogueLine, Scene, StoryOutput


class TestCharacterSchema:
    def test_valid_character(self):
        char = Character(
            id="char_01", name="Alex", role="protagonist",
            voice_description="deep male narrator",
            visual_description="tall man in a blue coat",
            personality="brave and curious",
        )
        assert char.id == "char_01"
        assert char.name == "Alex"

    def test_character_missing_required_fields(self):
        with pytest.raises(ValidationError):
            Character(name="Alex")  # missing id, role, etc.

    def test_character_valid_roles(self):
        for role in ["protagonist", "antagonist", "supporting", "narrator"]:
            char = Character(
                id="c1", name="X", role=role,
                voice_description="v", visual_description="v", personality="p"
            )
            assert char.role == role

    def test_character_voice_id_default(self):
        char = Character(
            id="c1", name="X", role="narrator",
            voice_description="calm", visual_description="old man", personality="wise"
        )
        assert char.voice_id is None or isinstance(char.voice_id, str)


class TestDialogueLineSchema:
    def test_valid_dialogue_line(self):
        line = DialogueLine(character_id="char_01", text="Hello world.")
        assert line.character_id == "char_01"
        assert line.text == "Hello world."

    def test_dialogue_with_emotion(self):
        line = DialogueLine(character_id="char_01", text="Run!", emotion="fear")
        assert line.emotion == "fear"

    def test_dialogue_missing_required(self):
        with pytest.raises(ValidationError):
            DialogueLine(character_id="char_01")  # missing text


class TestSceneSchema:
    def test_valid_scene(self):
        scene = Scene(
            scene_id="scene_01", setting="Mars surface",
            mood="mysterious", visual_prompt="vast red desert",
            duration_hint=15,
        )
        assert scene.scene_id == "scene_01"

    def test_scene_with_dialogue(self):
        line = DialogueLine(character_id="c1", text="We made it.")
        scene = Scene(
            scene_id="scene_02", setting="Moon base",
            mood="epic", visual_prompt="silver dome",
            duration_hint=10, dialogue=[line],
        )
        assert len(scene.dialogue) == 1

    def test_scene_no_duration_field(self):
        scene = Scene(
            scene_id="s1", setting="Earth", mood="calm",
            visual_prompt="green meadow",
        )
        assert scene.duration_hint is None or isinstance(scene.duration_hint, (int, float))

    def test_scene_valid_moods(self):
        for mood in ["mysterious", "epic", "calm", "tense", "happy", "sad"]:
            scene = Scene(scene_id="s1", setting="X", mood=mood, visual_prompt="X")
            assert scene.mood == mood

    def test_scene_narration_optional(self):
        scene = Scene(scene_id="s1", setting="X", mood="calm", visual_prompt="X")
        assert scene.narration is None or isinstance(scene.narration, str)


class TestStoryOutputSchema:
    def _make_story(self):
        char = Character(
            id="char_01", name="Zara", role="protagonist",
            voice_description="young female hopeful",
            visual_description="astronaut auburn hair",
            personality="brave"
        )
        scene = Scene(
            scene_id="scene_01", setting="Mars", mood="mysterious",
            visual_prompt="red desert at dawn", duration_hint=15
        )
        return StoryOutput(title="Ocean of Stars", characters=[char], scenes=[scene])

    def test_full_story_output(self):
        story = self._make_story()
        assert story.title == "Ocean of Stars"
        assert len(story.characters) == 1
        assert len(story.scenes) == 1

    def test_story_json_serializable(self):
        story = self._make_story()
        data = story.model_dump()
        assert isinstance(data, dict)
        assert "title" in data
        assert "characters" in data
        assert "scenes" in data

    def test_story_json_round_trip(self):
        story = self._make_story()
        json_str = story.model_dump_json()
        story2 = StoryOutput.model_validate_json(json_str)
        assert story2.title == story.title

    def test_scene_ids_unique(self):
        story = self._make_story()
        ids = [s.scene_id for s in story.scenes]
        assert len(ids) == len(set(ids))

    def test_character_ids_unique(self):
        story = self._make_story()
        ids = [c.id for c in story.characters]
        assert len(ids) == len(set(ids))
