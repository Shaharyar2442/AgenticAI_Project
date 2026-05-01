"""Logger Tool — structured logging for pipeline phases."""
from mcp.base_tool import BaseTool
from typing import Any, Dict
import logging

class LoggerTool(BaseTool):
    name = "logger"
    description = "Log structured messages for pipeline monitoring."

    async def execute(self, message: str, level: str = "info", phase: str = "", **kwargs) -> Dict[str, Any]:
        logger = logging.getLogger(f"pipeline.{phase}" if phase else "pipeline")
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(message)
        return {"success": True, "logged": message}
