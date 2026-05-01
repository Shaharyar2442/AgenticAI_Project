"""
Edit Agent — classifies, plans, and executes edits on pipeline state.
"""
from shared.schemas.pipeline import PipelineState
from agents.edit_agent.intent_classifier import classify_intent
from agents.edit_agent.planner import plan_edit
from agents.edit_agent.executor import execute_edit
from state_manager.state_manager import StateManager
import logging

logger = logging.getLogger(__name__)
state_mgr = StateManager()


async def handle_edit(query: str, state: PipelineState, session_id: str = "default") -> PipelineState:
    """Full edit flow: classify -> plan -> snapshot -> execute."""

    # 1. Classify intent
    intent = await classify_intent(query)
    logger.info(f"Edit intent: {intent.target}/{intent.intent}")

    # 2. Plan which phases to re-run
    plan = plan_edit(intent)
    logger.info(f"Edit plan: {plan['phases_to_rerun']}")

    # 3. Snapshot current state before edit
    asset_paths = list(state.scene_images.values()) + list(state.character_portraits.values())
    if state.final_video_path:
        asset_paths.append(state.final_video_path)
    state_mgr.snapshot(state.version, state.model_dump(), asset_paths)

    # 4. Execute the edit
    updated_state = await execute_edit(state, intent, plan, session_id)

    # 5. Snapshot new state
    new_assets = list(updated_state.scene_images.values()) + list(updated_state.character_portraits.values())
    if updated_state.final_video_path:
        new_assets.append(updated_state.final_video_path)
    state_mgr.snapshot(updated_state.version, updated_state.model_dump(), new_assets,)

    return updated_state
