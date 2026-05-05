"""
Edit Executor — executes planned edits by calling MCP tools.
After modifying images/audio, always re-renders the video.
"""
from shared.schemas.pipeline import PipelineState
from shared.schemas.edit import EditIntent
from mcp.tools.vision_tools.image_edit_tool import ImageEditTool
from agents.audio_agent.agent import generate_audio
from agents.video_agent.agent import generate_video
from typing import Dict
import os
import logging

logger = logging.getLogger(__name__)

image_editor = ImageEditTool()


async def execute_edit(state: PipelineState, intent: EditIntent,
                       plan: dict, session_id: str = "default") -> PipelineState:
    """Execute an edit based on the plan. Always re-renders video after changes."""
    phases = plan["phases_to_rerun"]
    edit_session = f"{session_id}_v{state.version + 1}"
    did_modify = False

    # ── Phase 1: Script changes ──
    if "phase1" in phases:
        logger.info(f"Phase 1 re-run requested for: {intent.intent}")
        # For now, log — full script regeneration would require LLM call
        # In production, you'd modify the story object based on intent

    # ── Apply image filters (darken, brighten, grayscale, etc.) ──
    if intent.target == "video_frame":
        filter_name = intent.parameters.get("filter", "darken")

        # Map common intents to filter names
        filter_map = {
            "apply_filter": filter_name,
            "change_lighting": "darken" if "dark" in intent.parameters.get("filter", "") else "brighten",
        }
        actual_filter = filter_map.get(intent.intent, filter_name)

        scope = intent.scope
        modified_count = 0

        for scene_id, img_path in list(state.scene_images.items()):
            if scope == "all" or scope == f"scene:{scene_id}" or scope.startswith("scene:") and scene_id in scope:
                output_path = img_path.replace(".png", f"_{actual_filter}.png")
                result = await image_editor.execute(
                    image_path=img_path, filter_name=actual_filter, output_path=output_path
                )
                if result["success"]:
                    state.scene_images[scene_id] = result["image_path"]
                    modified_count += 1
                    did_modify = True
                    logger.info(f"Applied '{actual_filter}' to {scene_id}")

        if modified_count == 0:
            logger.warning(f"No scenes matched scope '{scope}' for filter '{actual_filter}'")

    # ── Phase 2: Audio re-generation ──
    if "phase2" in phases:
        logger.info("Re-running Phase 2 (audio)")
        manifest = await generate_audio(state.story, session_id=edit_session)
        state.timing_manifest = manifest
        did_modify = True

    # ── Phase 3: Video re-render (always after any visual/audio change) ──
    if "phase3" in phases or did_modify:
        logger.info("Re-running Phase 3 (video re-render)")
        await generate_video(state, session_id=edit_session)
        did_modify = True

    if not did_modify:
        logger.warning(f"Edit '{intent.intent}' on '{intent.target}' did not produce changes")

    state.version += 1
    return state
