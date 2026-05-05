"""
BGM Tool — selects royalty-free background music by scene mood.
Auto-downloads from YouTube (no-copyright sources) on first run if file not found.
Download runs in a thread with a 60s timeout so it never blocks the pipeline.
Falls back to silence if download fails or times out.
"""
from mcp.base_tool import BaseTool
from shared.config import BGM_DIR, OUTPUTS_DIR
from typing import Any, Dict
from pathlib import Path
import asyncio
import os
import logging

logger = logging.getLogger(__name__)

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

BGM_SOURCES = {
    "happy_upbeat":    "https://www.youtube.com/watch?v=8fbfVdEz7Lk",
    "sad_melancholic": "https://www.youtube.com/watch?v=JUPoUnqDArk",
    "tense_suspense":  "https://www.youtube.com/watch?v=Pgbs1EQLV7w",
    "epic_adventure":  "https://www.youtube.com/watch?v=Wz-ZZD711Oc",
    "calm_peaceful":   "https://www.youtube.com/watch?v=yhFccHgf_FQ",
    "mysterious_dark": "https://www.youtube.com/watch?v=hm0-ZTLRWEo",
}

# Download timeout in seconds — prevents blocking the pipeline
_DOWNLOAD_TIMEOUT = 60


def _download_bgm_sync(stem: str, bgm_dir: str) -> str | None:
    """Synchronous yt-dlp download — run in a thread via asyncio executor."""
    try:
        import yt_dlp
    except ImportError:
        logger.warning("[BGM] yt-dlp not installed. Skipping BGM.")
        return None

    bgm_path = Path(bgm_dir) / f"{stem}.mp3"
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
        # Limit to first 3 minutes only — saves download time
        "postprocessor_args": ["-t", "180"],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([BGM_SOURCES[stem]])
        if bgm_path.exists() and bgm_path.stat().st_size > 1000:
            logger.info(f"[BGM] '{stem}.mp3' downloaded OK ({bgm_path.stat().st_size // 1024} KB)")
            return str(bgm_path)
        logger.warning(f"[BGM] Download completed but file missing at {bgm_path}")
        return None
    except Exception as e:
        logger.warning(f"[BGM] Download failed for '{stem}': {e}")
        return None


async def _ensure_bgm_async(bgm_filename: str, bgm_dir: str) -> str | None:
    """Return path to BGM file. Downloads asynchronously with timeout if missing."""
    bgm_path = Path(bgm_dir) / bgm_filename
    if bgm_path.exists() and bgm_path.stat().st_size > 1000:
        return str(bgm_path)

    stem = Path(bgm_filename).stem
    if stem not in BGM_SOURCES:
        logger.warning(f"[BGM] No source for '{bgm_filename}'. Skipping.")
        return None

    Path(bgm_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"[BGM] '{bgm_filename}' not cached — downloading (timeout={_DOWNLOAD_TIMEOUT}s)...")

    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _download_bgm_sync, stem, bgm_dir),
            timeout=_DOWNLOAD_TIMEOUT
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"[BGM] Download timed out after {_DOWNLOAD_TIMEOUT}s. Continuing without BGM.")
        return None
    except Exception as e:
        logger.warning(f"[BGM] Async download error: {e}. Continuing without BGM.")
        return None


class BGMTool(BaseTool):
    name = "bgm_selector"
    description = "Select background music by scene mood. Auto-downloads with 60s timeout."

    async def execute(self, mood: str, **kwargs) -> Dict[str, Any]:
        """Select BGM for the given mood, downloading if not cached."""
        mood_lower = mood.lower().strip()
        bgm_file = MOOD_BGM_MAP.get(mood_lower, "calm_peaceful.mp3")
        bgm_path = await _ensure_bgm_async(bgm_file, str(BGM_DIR))

        if bgm_path:
            logger.info(f"BGM selected: {bgm_file} (mood='{mood}')")
            return {"success": True, "bgm_file": bgm_path, "mood": mood}
        else:
            logger.warning(f"BGM unavailable for mood '{mood}'. Continuing without BGM.")
            return {"success": True, "bgm_file": None, "mood": mood, "note": "No BGM — silence"}
