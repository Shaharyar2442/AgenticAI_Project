"""
Edit Intent Classifier Tests — 12 query types (spec requires ≥10).
"""
import pytest
from agents.edit_agent.intent_classifier import classify_intent

TEST_CASES = [
    # (user_query, expected_target, expected_intent)
    ("Change the narrator's voice to a whisper",     "audio",       "change_voice_tone"),
    ("Make scene 2 darker",                          "video_frame", "apply_filter"),
    ("Add epic background music to scene 3",         "audio",       "add_bgm"),
    ("Remove all subtitles",                         "video",       "remove_subtitles"),
    ("Speed up the last scene",                      "video",       "change_speed"),
    ("Change the protagonist's hair to red",         "video_frame", "regenerate_character"),
    ("Regenerate the entire script",                 "script",      "regenerate_script"),
    ("Make the video black and white",               "video_frame", "apply_filter"),
    ("Add a sad tone to the music",                  "audio",       "change_bgm_mood"),
    ("Change the setting to underwater",             "script",      "change_setting"),
    ("Make the narrator speak faster",               "audio",       "change_speech_rate"),
    ("Add a fade-in transition to scene 1",          "video",       "add_transition"),
]


@pytest.mark.parametrize("query,expected_target,expected_intent", TEST_CASES)
@pytest.mark.asyncio
async def test_intent_classification(query, expected_target, expected_intent):
    """Test that edit queries are classified to correct target and intent."""
    result = await classify_intent(query)
    assert result.target == expected_target, (
        f"Query '{query}' -> target '{result.target}', expected '{expected_target}'"
    )
    assert result.intent == expected_intent, (
        f"Query '{query}' -> intent '{result.intent}', expected '{expected_intent}'"
    )
