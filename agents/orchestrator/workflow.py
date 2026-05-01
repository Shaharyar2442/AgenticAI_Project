"""
Orchestrator Workflow — sequential pipeline execution with progress callbacks.
"""
from shared.schemas.pipeline import PipelineState
from agents.story_agent.agent import generate_story
from agents.audio_agent.agent import generate_audio
from agents.video_agent.agent import generate_video
from state_manager.state_manager import StateManager
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)
state_mgr = StateManager()


async def run_pipeline(
    user_prompt: str,
    session_id: str = "default",
    progress_callback: Optional[Callable] = None
) -> PipelineState:
    """Run the full generation pipeline: Story -> Audio -> Video."""

    state = PipelineState(user_prompt=user_prompt)

    async def report(msg: str, phase: str = ""):
        logger.info(f"[{phase}] {msg}")
        if progress_callback:
            await progress_callback({"phase": phase, "message": msg, "status": "running"})

    # Phase 1: Story Generation
    await report("Generating story and characters...", "phase1")
    try:
        story = await generate_story(user_prompt)
        state.story = story
        state.status = "phase1_done"
        state_mgr.snapshot(1, state.model_dump(), [])
        await report(f"Story '{story.title}' generated: {len(story.scenes)} scenes, {len(story.characters)} characters", "phase1")
    except Exception as e:
        state.status = "phase1_failed"
        await report(f"Story generation failed: {e}", "phase1")
        raise

    # Phase 2: Audio Generation
    await report("Generating audio and timing manifest...", "phase2")
    try:
        manifest = await generate_audio(story, session_id)
        state.timing_manifest = manifest
        state.status = "phase2_done"
        state_mgr.snapshot(2, state.model_dump(), [])
        await report(f"Audio generated: {manifest.total_duration_ms}ms total", "phase2")
    except Exception as e:
        state.status = "phase2_failed"
        await report(f"Audio generation failed: {e}", "phase2")
        raise

    # Phase 3: Video Generation
    await report("Generating images and compositing video...", "phase3")
    try:
        final_path = await generate_video(state, session_id)
        state.status = "complete"
        all_assets = (list(state.scene_images.values()) +
                     list(state.character_portraits.values()) +
                     [final_path])
        state_mgr.snapshot(3, state.model_dump(), all_assets)
        await report(f"Video complete: {final_path}", "phase3")
    except Exception as e:
        state.status = "phase3_failed"
        await report(f"Video generation failed: {e}", "phase3")
        raise

    await report("Pipeline complete!", "done")
    return state
