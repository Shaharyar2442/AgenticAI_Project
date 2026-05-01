"""
MCP Tool Executor — executes tools dynamically by name via the registry.
"""
from typing import Any, Dict
from mcp.tool_registry import registry
import logging

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes registered MCP tools by name."""

    async def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name with the given arguments."""
        tool = registry.get_or_raise(tool_name)
        logger.info(f"Executing tool: {tool_name} with args: {list(kwargs.keys())}")
        try:
            result = await tool.execute(**kwargs)
            logger.info(f"Tool {tool_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"success": False, "error": str(e)}


# Global executor instance
executor = ToolExecutor()
