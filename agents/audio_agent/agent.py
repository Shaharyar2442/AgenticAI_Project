"""
Audio Agent — generates TTS audio for all dialogue, merges with BGM,
produces TimingManifest with measured durations.
"""
from shared.schemas.story import StoryOutput
from shared.schemas.audio import AudioSegment, SceneTiming, TimingManifest
from mcp.tools.audio_tools.tts_tool import TTSTool, match_voice
from mcp.tools.audio_tools.bgm_tool import BGMTool
from mcp.tools.audio_tools.audio_merger import AudioMergerTool
from mcp.tools.video_tools.subtitle_tool import SubtitleTool
from shared.config import OUTPUTS_DIR
from typing import Dict
import os
import re
import logging

logger = logging.getLogger(__name__)

tts = TTSTool()
bgm_selector = BGMTool()
merger = AudioMergerTool()
subtitle_mgr = SubtitleTool()

# ── Gender keyword sets (whole-word matching) ─────────────────────────────────
_MALE_WORDS = {
    "male", "man", "boy", "deep", "baritone", "bass", "gruff", "husky",
    "tenor", "masculine", "gentleman", "sir", "he", "him", "his",
    "beard", "mustache", "moustache", "father", "brother", "son",
    "king", "lord",
}
_FEMALE_WORDS = {
    "female", "woman", "girl", "soprano", "alto", "bright", "gentle",
    "soft", "lady", "feminine", "she", "her", "hers",
    "mother", "sister", "daughter", "queen", "maiden", "princess",
}


def _tokens(text: str) -> set:
    """Split text into lowercase word tokens (handles hyphens, commas, etc.)."""
    return set(re.split(r"[\s,\-_;/\.]+", text.lower()))


def _infer_gender(char) -> str:
    """Multi-signal gender inference.
    
    Checks in order:
    1. Explicit 'gender' field set by LLM
    2. Whole-word matching in voice_description  (avoids 'male' in 'female' bug)
    3. Whole-word matching in visual_description
    4. Role-based heuristic
    Returns 'male', 'female', or 'neutral'.
    """
    # 1 ── explicit gender field
    g = getattr(char, "gender", "").lower().strip()
    if g in ("male", "m", "man", "boy"):
        return "male"
    if g in ("female", "f", "woman", "girl"):
        return "female"

    # 2 ── voice description (whole words only!)
    vd = _tokens(char.voice_description)
    vm = bool(vd & _MALE_WORDS)
    vf = bool(vd & _FEMALE_WORDS)
    if vm and not vf:
        return "male"
    if vf and not vm:
        return "female"

    # 3 ── visual description
    vis = _tokens(char.visual_description)
    visM = bool(vis & _MALE_WORDS)
    visF = bool(vis & _FEMALE_WORDS)
    if visM and not visF:
        return "male"
    if visF and not visM:
        return "female"

    # 4 ── role heuristic
    if "narrator" in char.role.lower():
        return "neutral"

    return "neutral"


async def generate_audio(story: StoryOutput, session_id: str = "default") -> TimingManifest:
    """Generate all audio for a story and produce a TimingManifest."""
    audio_dir = str(OUTPUTS_DIR / "audio" / session_id)
    os.makedirs(audio_dir, exist_ok=True)

    # Build voice map: character_id → edge-tts voice name
    voice_map: Dict[str, str] = {}
    for i, char in enumerate(story.characters):
        if char.voice_id:
            voice_map[char.id] = char.voice_id
        else:
            gender = _infer_gender(char)
            assigned = match_voice(
                char.voice_description,
                character_id=char.id,
                gender=gender,
                char_index=i,
            )
            voice_map[char.id] = assigned
            logger.info(f"[VoiceMap] {char.name} ({char.id}): "
                        f"gender_field={char.gender!r} → inferred={gender!r} → voice={assigned}")

    logger.info(f"Final voice map: {voice_map}")

    all_segments = []
    scene_durations = []

    for scene in story.scenes:
        scene_audio_files = []
        scene_srt_files = []
        scene_segments = []
        cumulative_ms = 0

        # Generate narration first if present
        if scene.narration:
            narrator_voice = voice_map.get("char_01", "en-US-GuyNeural")
            prefix = f"{scene.scene_id}_narration"
            result = await tts.execute(
                text=scene.narration, voice=narrator_voice,
                output_dir=audio_dir, file_prefix=prefix
            )
            duration_ms = result["duration_ms"]
            seg = AudioSegment(
                scene_id=scene.scene_id, audio_file=result["audio_file"],
                type="narration", character_id="char_01",
                start_ms=cumulative_ms, end_ms=cumulative_ms + duration_ms
            )
            all_segments.append(seg)
            scene_segments.append(seg)
            scene_audio_files.append(result["audio_file"])
            scene_srt_files.append({"path": result["srt_file"], "offset_ms": cumulative_ms})
            cumulative_ms += duration_ms + 400  # gap

        # Generate dialogue lines
        for i, line in enumerate(scene.dialogue):
            voice = voice_map.get(line.character_id, "en-US-GuyNeural")
            prefix = f"{scene.scene_id}_line_{i:02d}"
            result = await tts.execute(
                text=line.text, voice=voice,
                output_dir=audio_dir, file_prefix=prefix
            )
            duration_ms = result["duration_ms"]
            seg = AudioSegment(
                scene_id=scene.scene_id, audio_file=result["audio_file"],
                type="dialogue", character_id=line.character_id,
                start_ms=cumulative_ms, end_ms=cumulative_ms + duration_ms
            )
            all_segments.append(seg)
            scene_segments.append(seg)
            scene_audio_files.append(result["audio_file"])
            scene_srt_files.append({"path": result["srt_file"], "offset_ms": cumulative_ms})
            cumulative_ms += duration_ms + 400

        # Merge scene audio
        combined_path = os.path.join(audio_dir, f"{scene.scene_id}_combined.mp3")
        bgm_result = await bgm_selector.execute(mood=scene.mood)
        merge_result = await merger.execute(
            audio_files=scene_audio_files,
            bgm_file=bgm_result.get("bgm_file"),
            output_path=combined_path
        )

        # Merge SRT files
        combined_srt = os.path.join(audio_dir, f"{scene.scene_id}_combined.srt")
        await subtitle_mgr.execute(srt_files=scene_srt_files, output_path=combined_srt)

        measured_duration = merge_result["duration_ms"]
        scene_durations.append(SceneTiming(
            scene_id=scene.scene_id,
            measured_duration_ms=measured_duration,
            audio_file=combined_path,
            srt_file=combined_srt
        ))
        logger.info(f"Scene {scene.scene_id}: {measured_duration}ms, {len(scene_segments)} segments")

    total_ms = sum(st.measured_duration_ms for st in scene_durations)
    manifest = TimingManifest(
        segments=all_segments, scene_durations=scene_durations, total_duration_ms=total_ms
    )
    logger.info(f"Audio generation complete: {len(scene_durations)} scenes, {total_ms}ms total")
    return manifest
