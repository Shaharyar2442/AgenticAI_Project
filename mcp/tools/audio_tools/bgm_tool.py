"""
BGM Tool — selects royalty-free background music by scene mood.
Auto-downloads from YouTube (no-copyright sources) on first run if file not found.
Falls back to silence if download fails.
"""
from mcp.base_tool import BaseTool
from shared.config import BGM_DIR, OUTPUTS_DIR
from typing import Any, Dict
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

# Mood -> BGM filename mapping
MOOD_BGM_MAP = {
    "happy":       "happy_upbeat.mp3",
    "sad":         "sad_melancholic.mp3",
    "melancholic": "sad_melancholic.mp3",
    "tense":       "tense_suspense.mp3",
    "suspense":    "tense_suspense.mp3",
    "epic":        "epic_adventure.mp3",
    "adventure":   "epic_adventure.mp3",
    "calm":        "calm_peaceful.mp3",
    "peaceful":    "calm_peaceful.mp3",
    "mysterious":  "mysterious_dark.mp3",
    "dark":        "mysterious_dark.mp3",
}

# No-copyright YouTube sources — verified working
BGM_SOURCES = {
    "happy_upbeat":    "https://www.youtube.com/watch?v=5qap5aO4i9A",
    "sad_melancholic": "https://www.youtube.com/watch?v=B4BXGTNF9jU",
    "tense_suspense":  "https://www.youtube.com/watch?v=EqPtz5qN7HM",
    "epic_adventure":  "https://www.youtube.com/watch?v=hHW1oY26kxQ",
    "calm_peaceful":   "https://www.youtube.com/watch?v=2OEL4P1Rz04",
    "mysterious_dark": "https://www.youtube.com/watch?v=ukgNzLwkd9Y",
}


def _ensure_bgm(bgm_filename: str, bgm_dir: str) -> str | None:
    """
    Return path to BGM file. If missing, auto-download from YouTube.
    Returns None if download fails or mood has no source.
    """
    bgm_path = Path(bgm_dir) / bgm_filename
    if bgm_path.exists():
        return str(bgm_path)

    stem = Path(bgm_filename).stem
    if stem not in BGM_SOURCES:
        logger.warning(f"No download source for BGM '{bgm_filename}'. Skipping BGM.")
        return None

    Path(bgm_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"[BGM] '{bgm_filename}' not found. Auto-downloading...")

    try:
        import yt_dlp
    except ImportError:
        logger.warning("[BGM] yt-dlp not installed. Run: pip install yt-dlp. Skipping BGM.")
        return None

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(Path(bgm_dir) / f"{stem}.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([BGM_SOURCES[stem]])
        if bgm_path.exists():
            logger.info(f"[BGM] '{bgm_filename}' downloaded successfully.")
            return str(bgm_path)
        else:
            logger.warning(f"[BGM] Download completed but file not found at {bgm_path}. Skipping BGM.")
            return None
    except Exception as e:
        logger.warning(f"[BGM] Download failed for '{bgm_filename}': {e}. Skipping BGM.")
        return None


class BGMTool(BaseTool):
    name = "bgm_selector"
    description = "Select background music track based on scene mood. Auto-downloads if not cached."

    async def execute(self, mood: str, **kwargs) -> Dict[str, Any]:
        """Select a BGM file for the given mood, auto-downloading if necessary."""
        mood_lower = mood.lower().strip()
        bgm_file = MOOD_BGM_MAP.get(mood_lower, "calm_peaceful.mp3")
        bgm_path = _ensure_bgm(bgm_file, str(BGM_DIR))

        if bgm_path:
            logger.info(f"BGM selected: {bgm_file} for mood '{mood}'")
            return {"success": True, "bgm_file": bgm_path, "mood": mood}
        else:
            logger.warning(f"BGM unavailable for mood '{mood}'. Continuing without BGM.")
            return {"success": True, "bgm_file": None, "mood": mood, "note": "No BGM available"}
