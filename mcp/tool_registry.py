"""
MCP Tool Registry — register and discover tools by name.
Agents request tools from the registry rather than importing them directly.
"""
from typing import Dict, Optional, List
from mcp.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all MCP tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting.")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name. Returns None if not found."""
        return self._tools.get(name)

    def get_or_raise(self, name: str) -> BaseTool:
        """Get a tool by name. Raises KeyError if not found."""
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(self._tools.keys())
            raise KeyError(f"Tool '{name}' not found. Available: [{available}]")
        return tool

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_all(self) -> Dict[str, BaseTool]:
        """Get all registered tools."""
        return dict(self._tools)

    def get_langchain_tools(self) -> list:
        """Convert all registered tools to LangChain tool format."""
        return [tool.to_langchain_tool() for tool in self._tools.values()]


# Global singleton registry
registry = ToolRegistry()
