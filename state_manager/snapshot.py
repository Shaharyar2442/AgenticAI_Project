"""
Snapshot — creates versioned snapshots of state + assets.
"""
import shutil, os, json
from shared.config import STATE_VERSIONS_DIR
import logging

logger = logging.getLogger(__name__)


def create_snapshot(version: int, state_json: dict, asset_paths: list) -> str:
    """Copy all asset files to a versioned directory and save state."""
    version_dir = str(STATE_VERSIONS_DIR / f"v{version}")
    assets_dir = os.path.join(version_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Copy assets
    copied = []
    for path in asset_paths:
        if os.path.exists(path):
            dst = os.path.join(assets_dir, os.path.basename(path))
            shutil.copy2(path, dst)
            copied.append(dst)

    # Save state JSON
    state_path = os.path.join(version_dir, "state.json")
    with open(state_path, "w") as f:
        json.dump(state_json, f, indent=2, default=str)

    logger.info(f"Snapshot v{version}: {len(copied)} assets, state.json")
    return version_dir


def restore_snapshot(version: int) -> dict:
    """Load state from a versioned snapshot."""
    version_dir = str(STATE_VERSIONS_DIR / f"v{version}")
    state_path = os.path.join(version_dir, "state.json")
    if not os.path.exists(state_path):
        raise FileNotFoundError(f"Snapshot v{version} not found")
    with open(state_path, "r") as f:
        return json.load(f)
