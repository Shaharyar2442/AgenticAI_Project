"""
State Manager — session-scoped versioned state management.
"""
from state_manager.storage import save_version, load_version, list_versions, get_latest_version
from state_manager.snapshot import create_snapshot, restore_snapshot
from state_manager.history import get_history, get_diff
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class StateManager:
    """Central interface for state versioning, snapshots, and history."""

    def snapshot(self, version: int, state_json: dict, asset_paths: list = None,
                 session_id: str = "default", description: str = "") -> None:
        save_version(version, state_json, asset_paths or [], description=description, session_id=session_id)
        create_snapshot(version, state_json, asset_paths or [])
        logger.info(f"State snapshot saved: v{version} (session={session_id})")

    def revert(self, version: int, session_id: str = "default") -> dict:
        state = load_version(version, session_id=session_id)
        logger.info(f"State reverted to v{version} (session={session_id})")
        return state

    def history(self, session_id: str = "default") -> List[Dict]:
        return list_versions(session_id=session_id)

    def get_diff(self, v_old: int, v_new: int) -> Dict:
        return get_diff(v_old, v_new)

    def get_latest(self, session_id: str = "default") -> int:
        return get_latest_version(session_id=session_id)
