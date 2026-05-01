"""File Tool — file system operations."""
from mcp.base_tool import BaseTool
from typing import Any, Dict
import os, json, shutil, logging

logger = logging.getLogger(__name__)

class FileTool(BaseTool):
    name = "file_manager"
    description = "File operations: read/write JSON, copy, list directory."

    async def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        ops = {"write_json": self._write_json, "read_json": self._read_json,
               "copy": self._copy, "ensure_dir": self._ensure_dir}
        if operation not in ops:
            return {"success": False, "error": f"Unknown op: {operation}"}
        return await ops[operation](**kwargs)

    async def _write_json(self, path: str, data: dict, **kw) -> Dict:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return {"success": True, "path": path}

    async def _read_json(self, path: str, **kw) -> Dict:
        with open(path, "r") as f:
            return {"success": True, "data": json.load(f)}

    async def _copy(self, src: str, dst: str, **kw) -> Dict:
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.copy2(src, dst)
        return {"success": True}

    async def _ensure_dir(self, path: str, **kw) -> Dict:
        os.makedirs(path, exist_ok=True)
        return {"success": True}
