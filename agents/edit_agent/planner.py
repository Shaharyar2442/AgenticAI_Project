"""
Edit Planner — decides which pipeline phases need re-running based on intent.
"""
from shared.schemas.edit import EditIntent
import logging

logger = logging.getLogger(__name__)

# Map intent targets to the phases that need to be re-run
TARGET_PHASE_MAP = {
    "script": ["phase1", "phase2", "phase3"],   # Script change -> re-run everything
    "audio": ["phase2", "phase3"],                # Audio change -> re-run audio + video
    "video_frame": ["phase3"],                    # Image filter -> re-run video only
    "video": ["phase3"],                          # Video edit -> re-run video only
}


def plan_edit(intent: EditIntent) -> dict:
    """Determine which phases to re-run and what modifications to apply."""
    phases = TARGET_PHASE_MAP.get(intent.target, ["phase3"])

    plan = {
        "phases_to_rerun": phases,
        "intent": intent.intent,
        "target": intent.target,
        "scope": intent.scope,
        "parameters": intent.parameters,
        "description": f"Edit: {intent.intent} on {intent.target} (scope: {intent.scope})",
    }

    logger.info(f"Edit plan: re-run {phases} for {intent.intent}")
    return plan
