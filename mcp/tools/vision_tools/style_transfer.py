"""
Style Transfer Tool — ensures visual consistency across scenes.
Adds consistent style suffixes and seed management.
"""
from mcp.base_tool import BaseTool
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


class StyleTransferTool(BaseTool):
    name = "style_transfer"
    description = "Manage visual style consistency across generated images."

    async def execute(self, base_prompt: str, scene_index: int = 0,
                      style: str = "digital illustration", **kwargs) -> Dict[str, Any]:
        """Generate a style-consistent prompt with deterministic seed."""
        style_suffix = f", {style}, cinematic lighting, consistent art style, high detail"
        styled_prompt = f"{base_prompt}{style_suffix}"
        seed = 42 + scene_index  # Deterministic but varied per scene

        return {
            "success": True,
            "styled_prompt": styled_prompt,
            "seed": seed,
            "style": style,
        }
