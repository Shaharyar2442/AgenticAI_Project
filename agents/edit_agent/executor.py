"""
Edit Executor — executes planned edits by calling MCP tools.
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
    """Execute an edit based on the plan."""
    phases = plan["phases_to_rerun"]

    if "phase1" in phases:
        # Script change: regenerate story (for now, log and skip)
        logger.info(f"Phase 1 re-run requested for: {intent.intent}")
        # In a full implementation, would modify story based on intent
        # For edits like "change_setting", modify the specific scene and regenerate

    if intent.target == "video_frame" and intent.intent == "apply_filter":
        # Apply filter to scene images
        filter_name = intent.parameters.get("filter", "darken")
        scope = intent.scope

        for scene_id, img_path in state.scene_images.items():
            if scope == "all" or scope == f"scene:{scene_id}":
                output_path = img_path.replace(".png", f"_{filter_name}.png")
                result = await image_editor.execute(
                    image_path=img_path, filter_name=filter_name, output_path=output_path
                )
                if result["success"]:
                    state.scene_images[scene_id] = result["image_path"]

    if "phase2" in phases:
        logger.info("Re-running Phase 2 (audio)")
        manifest = await generate_audio(state.story, session_id=f"{session_id}_edit")
        state.timing_manifest = manifest

    if "phase3" in phases:
        logger.info("Re-running Phase 3 (video)")
        await generate_video(state, session_id=f"{session_id}_edit")

    state.version += 1
    return state
