"""
Orchestrator Workflow — two-stage pipeline with character approval gate.

Stage 1: generate_story_and_characters() → Story + Portraits → frontend shows to user
Stage 2: continue_pipeline() → Audio + Video → user called this after accepting characters
"""
from shared.schemas.pipeline import PipelineState
from agents.story_agent.agent import generate_story
from agents.audio_agent.agent import generate_audio
from agents.video_agent.agent import generate_video
from mcp.tools.vision_tools.image_gen_tool import ImageGenTool
from state_manager.state_manager import StateManager
from shared.config import OUTPUTS_DIR
from typing import Callable, Optional
import os
import logging

logger = logging.getLogger(__name__)
state_mgr = StateManager()
image_gen = ImageGenTool()


async def generate_story_and_characters(
    user_prompt: str,
    session_id: str = "default",
    progress_callback: Optional[Callable] = None
) -> PipelineState:
    """Stage 1: Generate story + character portraits. Pauses for user review."""

    state = PipelineState(user_prompt=user_prompt)

    async def report(msg, phase="", status="running", **extra):
        logger.info(f"[{phase}] {msg}")
        if progress_callback:
            payload = {"phase": phase, "message": msg, "status": status}
            payload.update(extra)
            await progress_callback(payload)

    # Phase 1: Story
    await report("Connecting to LLM for story generation...", "phase1")
    try:
        story = await generate_story(user_prompt)
        state.story = story
        state.status = "phase1_done"

        await report(
            f"Story '{story.title}' generated: {len(story.scenes)} scenes, {len(story.characters)} characters",
            "phase1", status="complete",
            story_data={
                "title": story.title, "genre": story.genre, "synopsis": story.synopsis,
                "characters": [c.model_dump() for c in story.characters],
                "scenes": [{"scene_id": s.scene_id, "title": s.title, "mood": s.mood,
                            "setting": s.setting, "dialogue_count": len(s.dialogue)} for s in story.scenes],
            }
        )
    except Exception as e:
        state.status = "phase1_failed"
        await report(f"Story generation failed: {e}", "phase1", status="error")
        raise

    # Generate character portraits
    await report("Generating character portraits...", "portraits")
    img_dir = str(OUTPUTS_DIR / "images" / session_id)
    os.makedirs(img_dir, exist_ok=True)

    char_portraits = {}
    for char in story.characters:
        result = await image_gen.execute(
            prompt=char.visual_description,
            output_path=os.path.join(img_dir, f"{char.id}_portrait.png"),
            image_type="portrait", seed=42
        )
        char_portraits[char.id] = result["image_path"]
        await report(f"Portrait generated: {char.name}", "portraits")
    state.character_portraits = char_portraits

    await report("Characters ready for review", "portraits", status="characters_ready")
    return state


async def continue_pipeline(
    state: PipelineState,
    session_id: str = "default",
    progress_callback: Optional[Callable] = None
) -> PipelineState:
    """Stage 2: Audio + Video generation. Called after user accepts characters."""

    async def report(msg, phase="", status="running", **extra):
        logger.info(f"[{phase}] {msg}")
        if progress_callback:
            payload = {"phase": phase, "message": msg, "status": status}
            payload.update(extra)
            await progress_callback(payload)

    story = state.story
    if not story:
        raise ValueError("No story in state — run Stage 1 first")

    # Phase 2: Audio
    await report("Assigning voices and synthesizing TTS audio...", "phase2")
    try:
        manifest = await generate_audio(story, session_id)
        state.timing_manifest = manifest
        state.status = "phase2_done"
        await report(
            f"Audio generated: {manifest.total_duration_ms}ms total",
            "phase2", status="complete",
            audio_data={
                "total_duration_ms": manifest.total_duration_ms,
                "scene_durations": [{"scene_id": st.scene_id, "duration_ms": st.measured_duration_ms}
                                    for st in manifest.scene_durations],
                "segment_count": len(manifest.segments),
            }
        )
    except Exception as e:
        state.status = "phase2_failed"
        await report(f"Audio generation failed: {e}", "phase2", status="error")
        raise

    # Phase 3: Video
    await report("Generating scene images and compositing video...", "phase3")
    try:
        final_path = await generate_video(state, session_id)
        state.status = "complete"
        all_assets = list(state.scene_images.values()) + list(state.character_portraits.values()) + [final_path]
        state_mgr.snapshot(state.version, state.model_dump(), all_assets,
                          session_id=session_id, description="Initial generation")
        await report(f"Video complete: {final_path}", "phase3", status="complete")
    except Exception as e:
        state.status = "phase3_failed"
        await report(f"Video generation failed: {e}", "phase3", status="error")
        raise

    await report("Pipeline complete!", "done", status="complete")
    return state
