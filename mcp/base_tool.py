"""
MCP Base Tool — abstract interface for all tools in the system.
Every tool (LLM, TTS, image gen, FFmpeg, etc.) extends this class.

CAUTION: to_langchain_tool() uses `coroutine=` NOT `func=` for async tools.
Using func= silently returns <coroutine object> instead of the actual result.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ToolInput(BaseModel):
    """Base class for tool input schemas. Override in subclasses."""
    pass


class ToolOutput(BaseModel):
    """Standard tool output wrapper."""
    success: bool = True
    data: Dict[str, Any] = {}
    error: Optional[str] = None


class BaseTool(ABC):
    """Abstract base for all MCP tools."""
    name: str = "base_tool"
    description: str = "Base tool"

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool. Must be implemented by all subclasses."""
        pass

    def to_langchain_tool(self):
        """Convert to LangChain-compatible tool for agent use.

        IMPORTANT: We pass coroutine=self.execute (NOT func=self.execute).
        from_function(func=async_fn) silently returns the coroutine object
        instead of awaiting it — a maddening silent bug.
        """
        from langchain_core.tools import StructuredTool
        return StructuredTool.from_function(
            coroutine=self.execute,   # async path
            func=None,                # required when using coroutine
            name=self.name,
            description=self.description
        )

    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}'>"
