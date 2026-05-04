"""
TTS Tool — edge-tts with gTTS fallback.
Uses a simplified VOICE_MAP for reliable neural voice assignment.
"""
from mcp.base_tool import BaseTool
from shared.config import OUTPUTS_DIR
from typing import Any, Dict
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

# Simplified, reliable voice map — all stable Microsoft Neural voices
VOICE_MAP = {
    "narrator":   "en-US-GuyNeural",      # deep, clear narrator
    "male":       "en-GB-RyanNeural",      # British male
    "female":     "en-US-JennyNeural",     # warm female
    "default":    "en-US-AriaNeural",      # expressive female default
}


def match_voice(voice_description: str) -> str:
    """Match a character's voice_description to an edge-tts voice name."""
    desc = voice_description.lower()
    if "narrator" in desc or "narrat" in desc:
        return VOICE_MAP["narrator"]
    if any(w in desc for w in ["male", "man", "boy", "deep", "baritone"]):
        return VOICE_MAP["male"]
    if any(w in desc for w in ["female", "woman", "girl", "soft"]):
        return VOICE_MAP["female"]
    return VOICE_MAP["default"]


def _ms_to_srt(ms: int) -> str:
    """Convert milliseconds to SRT timestamp."""
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _generate_estimated_srt(text: str, duration_ms: int, srt_path: str):
    """Generate estimated word-level SRT from text and total audio duration."""
    words = text.split()
    if not words:
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("")
        return

    ms_per_word = duration_ms / len(words) if words else 0
    entries = []
    chunk_size = 4
    for i in range(0, len(words), chunk_size):
        chunk = words[i:i + chunk_size]
        start_ms = int(i * ms_per_word)
        end_ms = int(min((i + len(chunk)) * ms_per_word, duration_ms))
        entries.append((len(entries) + 1, start_ms, end_ms, " ".join(chunk)))

    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, start, end, text_chunk in entries:
            f.write(f"{idx}\n")
            f.write(f"{_ms_to_srt(start)} --> {_ms_to_srt(end)}\n")
            f.write(f"{text_chunk}\n\n")


class TTSTool(BaseTool):
    name = "tts"
    description = "Synthesize speech from text. Tries edge-tts first, falls back to gTTS."

    async def execute(self, text: str, voice: str = "en-US-AriaNeural",
                      output_dir: str = "", file_prefix: str = "line",
                      **kwargs) -> Dict[str, Any]:
        """Generate TTS audio + SRT subtitle file."""
        if not output_dir:
            output_dir = str(OUTPUTS_DIR / "audio")
        os.makedirs(output_dir, exist_ok=True)

        audio_path = os.path.join(output_dir, f"{file_prefix}.mp3")
        srt_path = os.path.join(output_dir, f"{file_prefix}.srt")

        # Strategy 1: edge-tts (best quality, word-level timestamps)
        try:
            result = await self._try_edge_tts(text, voice, audio_path, srt_path)
            if result:
                return result
        except Exception as e:
            logger.warning(f"edge-tts failed: {e}")

        # Strategy 2: gTTS fallback
        try:
            result = await self._try_gtts(text, audio_path, srt_path)
            if result:
                return result
        except Exception as e:
            logger.error(f"gTTS also failed: {e}")
            raise RuntimeError(f"All TTS engines failed for: {text[:50]}...")

    async def _try_edge_tts(self, text: str, voice: str, audio_path: str, srt_path: str) -> Dict:
        """Try edge-tts with retry. Returns result dict or None on failure."""
        import edge_tts

        for attempt in range(2):
            try:
                communicate = edge_tts.Communicate(text, voice)
                submaker = edge_tts.SubMaker()

                with open(audio_path, "wb") as audio_file:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_file.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            submaker.create_sub(
                                chunk["offset"], chunk["duration"], chunk["text"]
                            )

                if os.path.getsize(audio_path) < 100:
                    raise RuntimeError("edge-tts produced empty audio")

                srt_content = submaker.generate_subs()
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(srt_content)

                from pydub import AudioSegment as PydubSegment
                audio = PydubSegment.from_mp3(audio_path)
                duration_ms = len(audio)

                logger.info(f"edge-tts OK: {audio_path} ({duration_ms}ms)")
                return {
                    "success": True,
                    "audio_file": audio_path,
                    "srt_file": srt_path,
                    "duration_ms": duration_ms,
                    "engine": "edge-tts",
                }
            except Exception as e:
                logger.warning(f"edge-tts attempt {attempt+1} failed: {e}")
                if attempt < 1:
                    await asyncio.sleep(2)
        return None

    async def _try_gtts(self, text: str, audio_path: str, srt_path: str) -> Dict:
        """Fallback to gTTS. No word timestamps — uses estimated SRT."""
        from gtts import gTTS
        from pydub import AudioSegment as PydubSegment

        logger.info("Falling back to gTTS...")

        def _do_gtts():
            tts = gTTS(text=text, lang="en", slow=False)
            tts.save(audio_path)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _do_gtts)

        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 100:
            raise RuntimeError("gTTS produced empty audio")

        audio = PydubSegment.from_mp3(audio_path)
        duration_ms = len(audio)
        _generate_estimated_srt(text, duration_ms, srt_path)

        logger.info(f"gTTS OK: {audio_path} ({duration_ms}ms, estimated SRT)")
        return {
            "success": True,
            "audio_file": audio_path,
            "srt_file": srt_path,
            "duration_ms": duration_ms,
            "engine": "gtts",
        }
