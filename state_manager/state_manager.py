"""
State Manager — main interface for versioned state management.
"""
from state_manager.storage import save_version, load_version, list_versions, get_latest_version
from state_manager.snapshot import create_snapshot, restore_snapshot
from state_manager.history import get_history, get_diff
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class StateManager:
    """Central interface for state versioning, snapshots, and history."""

    def snapshot(self, version: int, state_json: dict, asset_paths: list = None) -> None:
        """Save state + copy assets into a versioned snapshot."""
        save_version(version, state_json, asset_paths or [])
        create_snapshot(version, state_json, asset_paths or [])
        logger.info(f"State snapshot saved: v{version}")

    def revert(self, version: int) -> dict:
        """Restore state from a specific version."""
        state = load_version(version)
        logger.info(f"State reverted to v{version}")
        return state

    def history(self) -> List[Dict]:
        """Get version history."""
        return get_history()

    def get_diff(self, v_old: int, v_new: int) -> Dict:
        """Compare two versions."""
        return get_diff(v_old, v_new)

    def get_latest(self) -> int:
        """Get latest version number."""
        return get_latest_version()
