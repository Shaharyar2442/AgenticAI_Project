"""
TTS Tool — edge-tts with gTTS fallback.
Expanded voice map for distinct character voices.
"""
from mcp.base_tool import BaseTool
from shared.config import OUTPUTS_DIR
from typing import Any, Dict
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

# Expanded voice map — each character gets a truly distinct voice
VOICE_MAP = {
    # Narrator voices
    "narrator_male":   "en-US-GuyNeural",
    "narrator_female": "en-US-AriaNeural",
    # Male voices — different accents/tones
    "male_1": "en-US-ChristopherNeural",   # deep American male
    "male_2": "en-GB-RyanNeural",          # British male
    "male_3": "en-AU-WilliamNeural",       # Australian male
    "male_4": "en-IN-PrabhatNeural",       # Indian male
    # Female voices — different accents/tones
    "female_1": "en-US-JennyNeural",       # warm American female
    "female_2": "en-GB-SoniaNeural",       # British female
    "female_3": "en-AU-NatashaNeural",     # Australian female
    "female_4": "en-US-MichelleNeural",    # clear American female
    # Child / young
    "child_male": "en-US-GuyNeural",
    "child_female": "en-US-AnaNeural",
    # Default
    "default": "en-US-AriaNeural",
}

# Male voices — different accents/ages
_MALE_POOL = [
    "en-US-ChristopherNeural",   # deep American male
    "en-GB-RyanNeural",          # British male
    "en-AU-WilliamNeural",       # Australian male
    "en-IN-PrabhatNeural",       # Indian male
]
# Female voices — different accents/ages
_FEMALE_POOL = [
    "en-US-JennyNeural",         # warm American female
    "en-GB-SoniaNeural",         # British female
    "en-AU-NatashaNeural",       # Australian female
    "en-US-MichelleNeural",      # clear American female
]


def match_voice(voice_description: str, character_id: str = "",
                gender: str = "", char_index: int = 0) -> str:
    """Map a character to an edge-tts voice.
    
    gender must be pre-resolved by the caller (e.g. via _infer_gender in audio_agent).
    char_index drives stateless round-robin within each gender pool.
    """
    g = gender.lower().strip()

    # --- Primary: use caller-resolved gender ---
    if g == "male":
        voice = _MALE_POOL[char_index % len(_MALE_POOL)]
        logger.info(f"  [voice] {character_id} → MALE pool[{char_index}] = {voice}")
        return voice
    if g == "female":
        voice = _FEMALE_POOL[char_index % len(_FEMALE_POOL)]
        logger.info(f"  [voice] {character_id} → FEMALE pool[{char_index}] = {voice}")
        return voice

    # --- Narrator check ---
    desc = voice_description.lower()
    if "narrator" in desc:
        return VOICE_MAP["narrator_male"]

    # --- Child check ---
    if any(w in desc for w in ["child", "kid", "young boy"]):
        return VOICE_MAP["child_male"]
    if any(w in desc for w in ["young girl", "child girl"]):
        return VOICE_MAP["child_female"]

    # --- Final fallback: odd char index = male, even = female ---
    num = int("".join(filter(str.isdigit, character_id)) or "1")
    if num % 2 == 1:
        voice = _MALE_POOL[char_index % len(_MALE_POOL)]
        logger.info(f"  [voice] {character_id} → fallback MALE pool[{char_index}] = {voice}")
        return voice
    voice = _FEMALE_POOL[char_index % len(_FEMALE_POOL)]
    logger.info(f"  [voice] {character_id} → fallback FEMALE pool[{char_index}] = {voice}")
    return voice


# gTTS accent fallback — different tlds produce different accents
GTTS_ACCENTS = ["com", "co.uk", "com.au", "co.in", "ca"]
_gtts_accent_idx = 0


def _get_gtts_accent() -> str:
    """Round-robin through gTTS accents for variety."""
    global _gtts_accent_idx
    accent = GTTS_ACCENTS[_gtts_accent_idx % len(GTTS_ACCENTS)]
    _gtts_accent_idx += 1
    return accent



def _ms_to_srt(ms: int) -> str:
    h = ms // 3600000; ms %= 3600000
    m = ms // 60000; ms %= 60000
    s = ms // 1000; ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _generate_estimated_srt(text: str, duration_ms: int, srt_path: str):
    words = text.split()
    if not words:
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("")
        return
    ms_per_word = duration_ms / len(words)
    entries = []
    chunk_size = 4
    for i in range(0, len(words), chunk_size):
        chunk = words[i:i + chunk_size]
        start_ms = int(i * ms_per_word)
        end_ms = int(min((i + len(chunk)) * ms_per_word, duration_ms))
        entries.append((len(entries) + 1, start_ms, end_ms, " ".join(chunk)))
    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, start, end, text_chunk in entries:
            f.write(f"{idx}\n{_ms_to_srt(start)} --> {_ms_to_srt(end)}\n{text_chunk}\n\n")


class TTSTool(BaseTool):
    name = "tts"
    description = "Synthesize speech from text. Tries edge-tts first, falls back to gTTS."

    async def execute(self, text: str, voice: str = "en-US-AriaNeural",
                      output_dir: str = "", file_prefix: str = "line",
                      **kwargs) -> Dict[str, Any]:
        if not output_dir:
            output_dir = str(OUTPUTS_DIR / "audio")
        os.makedirs(output_dir, exist_ok=True)
        audio_path = os.path.join(output_dir, f"{file_prefix}.mp3")
        srt_path = os.path.join(output_dir, f"{file_prefix}.srt")

        # Strategy 1: edge-tts
        try:
            result = await self._try_edge_tts(text, voice, audio_path, srt_path)
            if result:
                return result
        except Exception as e:
            logger.warning(f"edge-tts failed: {e}")

        # Strategy 2: gTTS with varied accents
        try:
            result = await self._try_gtts(text, voice, audio_path, srt_path)
            if result:
                return result
        except Exception as e:
            logger.error(f"gTTS also failed: {e}")
            raise RuntimeError(f"All TTS engines failed for: {text[:50]}...")

    async def _try_edge_tts(self, text, voice, audio_path, srt_path):
        import edge_tts
        for attempt in range(2):
            try:
                communicate = edge_tts.Communicate(text, voice)
                submaker = edge_tts.SubMaker()
                with open(audio_path, "wb") as f:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            submaker.create_sub(chunk["offset"], chunk["duration"], chunk["text"])
                if os.path.getsize(audio_path) < 100:
                    raise RuntimeError("empty audio")
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(submaker.generate_subs())
                from pydub import AudioSegment as AS
                duration_ms = len(AS.from_mp3(audio_path))
                logger.info(f"edge-tts OK: {voice} -> {audio_path} ({duration_ms}ms)")
                return {"success": True, "audio_file": audio_path, "srt_file": srt_path,
                        "duration_ms": duration_ms, "engine": "edge-tts"}
            except Exception as e:
                logger.warning(f"edge-tts attempt {attempt+1} failed: {e}")
                if attempt < 1: await asyncio.sleep(2)
        return None

    async def _try_gtts(self, text, voice, audio_path, srt_path):
        from gtts import gTTS
        from pydub import AudioSegment as AS

        # Use different accents for variety when edge-tts fails
        accent = _get_gtts_accent()
        logger.info(f"gTTS fallback with accent tld={accent}")

        def _do():
            tts_obj = gTTS(text=text, lang="en", tld=accent, slow=False)
            tts_obj.save(audio_path)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _do)

        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 100:
            raise RuntimeError("gTTS empty audio")

        duration_ms = len(AS.from_mp3(audio_path))
        _generate_estimated_srt(text, duration_ms, srt_path)
        logger.info(f"gTTS OK: tld={accent} -> {audio_path} ({duration_ms}ms)")
        return {"success": True, "audio_file": audio_path, "srt_file": srt_path,
                "duration_ms": duration_ms, "engine": "gtts"}
