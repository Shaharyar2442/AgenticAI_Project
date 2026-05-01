"""
BGM Tool — selects royalty-free background music by scene mood.
Falls back to silence if no BGM files are available.
"""
from mcp.base_tool import BaseTool
from shared.config import BGM_DIR, OUTPUTS_DIR
from typing import Any, Dict
import os
import logging

logger = logging.getLogger(__name__)

# Mood -> BGM filename mapping
MOOD_BGM_MAP = {
    "happy": "happy_upbeat.mp3",
    "sad": "sad_melancholic.mp3",
    "melancholic": "sad_melancholic.mp3",
    "tense": "tense_suspense.mp3",
    "suspense": "tense_suspense.mp3",
    "epic": "epic_adventure.mp3",
    "adventure": "epic_adventure.mp3",
    "calm": "calm_peaceful.mp3",
    "peaceful": "calm_peaceful.mp3",
    "mysterious": "mysterious_dark.mp3",
    "dark": "mysterious_dark.mp3",
}


class BGMTool(BaseTool):
    name = "bgm_selector"
    description = "Select background music track based on scene mood."

    async def execute(self, mood: str, **kwargs) -> Dict[str, Any]:
        """Select a BGM file for the given mood."""
        mood_lower = mood.lower().strip()
        bgm_file = MOOD_BGM_MAP.get(mood_lower, "calm_peaceful.mp3")
        bgm_path = os.path.join(str(BGM_DIR), bgm_file)

        if os.path.exists(bgm_path):
            logger.info(f"BGM selected: {bgm_file} for mood '{mood}'")
            return {"success": True, "bgm_file": bgm_path, "mood": mood}
        else:
            logger.warning(f"BGM file not found: {bgm_path}. Using no BGM.")
            return {"success": True, "bgm_file": None, "mood": mood, "note": "No BGM file available"}
