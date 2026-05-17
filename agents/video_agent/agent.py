"""
Video Agent — generates images, applies Ken Burns, overlays portraits,
merges audio, burns subtitles, and composites final video.
"""
from shared.schemas.story import StoryOutput
from shared.schemas.audio import TimingManifest
from shared.schemas.pipeline import PipelineState
from mcp.tools.vision_tools.image_gen_tool import ImageGenTool
from mcp.tools.video_tools.ffmpeg_tool import FFmpegTool, get_style_for_scene
from mcp.tools.video_tools.compositor_tool import CompositorTool
from shared.config import OUTPUTS_DIR, TEMP_DIR
from typing import Dict, List
import os
import logging

logger = logging.getLogger(__name__)

image_gen = ImageGenTool()
ffmpeg = FFmpegTool()
compositor = CompositorTool()


def _build_portrait_timeline(
    scene_id: str, segments, character_portraits: Dict[str, str],
    char_names: Dict[str, str] = None
) -> List[Dict]:
    """Build portrait overlay timeline from audio segments."""
    char_names = char_names or {}
    timeline = []
    for seg in segments:
        if seg.scene_id != scene_id or seg.type != "dialogue" or not seg.character_id:
            continue
        portrait = character_portraits.get(seg.character_id)
        if portrait and os.path.exists(portrait):
            timeline.append({
                "portrait": portrait,
                "start_sec": seg.start_ms / 1000.0,
                "end_sec": seg.end_ms / 1000.0,
                "character_id": seg.character_id,
                "character_name": char_names.get(seg.character_id, ""),
            })
    return timeline


async def generate_video(state: PipelineState, session_id: str = "default") -> str:
    """Generate the complete video from story + timing manifest."""
    story = state.story
    manifest = state.timing_manifest
    if not story or not manifest:
        raise ValueError("Story and timing manifest required")

    img_dir = str(OUTPUTS_DIR / "images" / session_id)
    vid_dir = str(OUTPUTS_DIR / "video" / session_id)
    temp_dir = str(TEMP_DIR / session_id)
    for d in [img_dir, vid_dir, temp_dir]:
        os.makedirs(d, exist_ok=True)

    # Step 1: Character portraits — reuse existing if already on disk
    char_names: Dict[str, str] = {c.id: c.name for c in story.characters}
    existing_portraits = state.character_portraits or {}
    char_portraits: Dict[str, str] = {}
    for char in story.characters:
        existing = existing_portraits.get(char.id)
        if existing and os.path.exists(existing):
            char_portraits[char.id] = existing
            logger.info(f"Reusing existing portrait for {char.name}: {existing}")
            continue
        result = await image_gen.execute(
            prompt=char.visual_description,
            output_path=os.path.join(img_dir, f"{char.id}_portrait.png"),
            image_type="portrait", seed=42
        )
        char_portraits[char.id] = result["image_path"]
        logger.info(f"Generated new portrait for {char.name}")
    state.character_portraits = char_portraits
    logger.info(f"Portraits ready: {len(char_portraits)} total")

    # Step 2: Scene images — reuse existing if already on disk
    existing_scenes = state.scene_images or {}
    scene_images: Dict[str, str] = {}
    for i, scene in enumerate(story.scenes):
        existing = existing_scenes.get(scene.scene_id)
        if existing and os.path.exists(existing):
            scene_images[scene.scene_id] = existing
            logger.info(f"Reusing existing image for {scene.scene_id}: {existing}")
            continue
        result = await image_gen.execute(
            prompt=scene.visual_prompt,
            output_path=os.path.join(img_dir, f"{scene.scene_id}.png"),
            image_type="scene", seed=42 + i
        )
        scene_images[scene.scene_id] = result["image_path"]
        logger.info(f"Generated new scene image for {scene.scene_id}")
    state.scene_images = scene_images
    logger.info(f"Scene images ready: {len(scene_images)} total")

    # Step 3: Render each scene
    scene_clips = []
    for i, scene_timing in enumerate(manifest.scene_durations):
        sid = scene_timing.scene_id
        duration_sec = scene_timing.measured_duration_ms / 1000.0
        style = get_style_for_scene(i, story.scenes[i].mood if i < len(story.scenes) else "")

        kb_path = os.path.join(temp_dir, f"kb_{sid}.mp4")
        chars_path = os.path.join(temp_dir, f"chars_{sid}.mp4")
        av_path = os.path.join(temp_dir, f"av_{sid}.mp4")
        final_path = os.path.join(vid_dir, f"{sid}_final.mp4")

        # 3a: Ken Burns
        await ffmpeg.execute("ken_burns", image_path=scene_images[sid],
                            duration_sec=duration_sec, output_path=kb_path, style=style)

        # 3b: Character portrait overlays with name labels
        timeline = _build_portrait_timeline(sid, manifest.segments, char_portraits, char_names)
        await ffmpeg.execute("overlay_portraits", video_path=kb_path,
                            portrait_timeline=timeline, output_path=chars_path)

        # 3c: Merge audio
        await ffmpeg.execute("merge_audio", video_path=chars_path,
                            audio_path=scene_timing.audio_file, output_path=av_path)

        # 3d: Burn subtitles
        if os.path.exists(scene_timing.srt_file):
            await ffmpeg.execute("burn_subtitles", video_path=av_path,
                                srt_path=scene_timing.srt_file, output_path=final_path)
        else:
            import shutil
            shutil.copy(av_path, final_path)

        scene_clips.append(final_path)
        state.scene_videos[sid] = final_path
        logger.info(f"Scene {sid} rendered: {duration_sec:.1f}s, style={style}")

    # Step 4: Compose final video
    final_output = os.path.join(vid_dir, "final_output.mp4")
    await compositor.execute(scene_clip_paths=scene_clips, output_path=final_output)

    state.final_video_path = final_output
    logger.info(f"Final video: {final_output}")
    return final_output
