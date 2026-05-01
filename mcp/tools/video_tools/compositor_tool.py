"""
Compositor Tool — assembles scene clips into final video using MoviePy.
"""
from mcp.base_tool import BaseTool
from shared.config import GLOBAL_FPS
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


class CompositorTool(BaseTool):
    name = "compositor"
    description = "Concatenate scene clips into the final output video."

    async def execute(self, scene_clip_paths: List[str],
                      output_path: str, **kwargs) -> Dict[str, Any]:
        """Concatenate scene clips into final video."""
        from moviepy.editor import VideoFileClip, concatenate_videoclips

        if not scene_clip_paths:
            return {"success": False, "error": "No scene clips provided"}

        clips = []
        for path in scene_clip_paths:
            try:
                clips.append(VideoFileClip(path))
            except Exception as e:
                logger.error(f"Failed to load clip {path}: {e}")
                continue

        if not clips:
            return {"success": False, "error": "All clips failed to load"}

        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(output_path, fps=GLOBAL_FPS, codec="libx264",
                              audio_codec="aac", logger=None)

        for c in clips:
            c.close()

        logger.info(f"Final video: {output_path} ({len(scene_clip_paths)} scenes)")
        return {"success": True, "output_path": output_path, "num_scenes": len(scene_clip_paths)}
