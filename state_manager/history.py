"""
History — version history with diff summaries.
"""
from state_manager.storage import list_versions, load_version
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def get_history() -> List[Dict]:
    """Get all version entries with metadata."""
    return list_versions()


def get_diff(v_old: int, v_new: int) -> Dict:
    """Compare two versions and return a summary of changes."""
    try:
        old_state = load_version(v_old)
        new_state = load_version(v_new)
    except KeyError as e:
        return {"error": str(e)}

    changes = []
    for key in set(list(old_state.keys()) + list(new_state.keys())):
        old_val = old_state.get(key)
        new_val = new_state.get(key)
        if old_val != new_val:
            changes.append({
                "field": key,
                "old_summary": _summarize(old_val),
                "new_summary": _summarize(new_val),
            })
    return {"v_old": v_old, "v_new": v_new, "changes": changes}


def _summarize(value) -> str:
    if value is None:
        return "None"
    if isinstance(value, str):
        return value[:100] + "..." if len(value) > 100 else value
    if isinstance(value, dict):
        return f"dict({len(value)} keys)"
    if isinstance(value, list):
        return f"list({len(value)} items)"
    return str(value)[:100]
