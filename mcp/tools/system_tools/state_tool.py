"""State Tool — MCP wrapper for state_manager operations."""
from mcp.base_tool import BaseTool
from typing import Any, Dict
import logging
logger = logging.getLogger(__name__)

class StateTool(BaseTool):
    name = "state_manager_tool"
    description = "Snapshot, revert, and query state versions."

    def __init__(self):
        from state_manager.state_manager import StateManager
        self.sm = StateManager()

    async def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        ops = {"snapshot": self._snapshot, "revert": self._revert, "history": self._history}
        if operation not in ops:
            return {"success": False, "error": f"Unknown op: {operation}"}
        return await ops[operation](**kwargs)

    async def _snapshot(self, version: int, state_json: dict, asset_paths: list = None, **kw) -> Dict:
        self.sm.snapshot(version, state_json, asset_paths or [])
        return {"success": True, "version": version}

    async def _revert(self, version: int, **kw) -> Dict:
        state = self.sm.revert(version)
        return {"success": True, "state": state, "version": version}

    async def _history(self, **kw) -> Dict:
        h = self.sm.history()
        return {"success": True, "versions": h}
