"""
Compositor Tool — assembles scene clips into final video using FFmpeg concat.
Uses -movflags +faststart so the browser can stream the video immediately
without waiting for the full file to download.
"""
from mcp.base_tool import BaseTool
from shared.config import GLOBAL_FPS
from typing import Any, Dict, List
import subprocess
import tempfile
import os
import logging

logger = logging.getLogger(__name__)


class CompositorTool(BaseTool):
    name = "compositor"
    description = "Concatenate scene clips into the final output video with web-streaming support."

    async def execute(self, scene_clip_paths: List[str],
                      output_path: str, **kwargs) -> Dict[str, Any]:
        """Concatenate scene clips into final video using FFmpeg concat demuxer.

        All input clips must share the same codec / resolution (they do — all go
        through the same FFmpeg ken_burns + overlay pipeline).  The concat
        demuxer is stream-copy fast and frame-perfect.  -movflags +faststart
        writes the moov atom at the front of the file so browsers can begin
        playback before the download is complete.
        """
        if not scene_clip_paths:
            return {"success": False, "error": "No scene clips provided"}

        # Filter out missing files
        valid_clips = [p for p in scene_clip_paths if os.path.exists(p)]
        if not valid_clips:
            return {"success": False, "error": "All provided clip paths are missing"}

        if len(valid_clips) < len(scene_clip_paths):
            logger.warning(f"Compositor: {len(scene_clip_paths) - len(valid_clips)} clips missing, continuing with {len(valid_clips)}")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Write the FFmpeg concat list to a temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            for path in valid_clips:
                # FFmpeg concat list requires forward slashes and single quotes
                safe_path = path.replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
            concat_file = f.name

        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                # Re-encode to ensure consistent stream parameters across clips
                "-c:v", "libx264", "-preset", "fast",
                "-crf", "22",
                "-pix_fmt", "yuv420p",
                "-r", str(GLOBAL_FPS),
                "-c:a", "aac", "-b:a", "192k",
                # Critical for web streaming — moov atom at file start
                "-movflags", "+faststart",
                output_path,
            ]
            logger.info(f"Compositor: concatenating {len(valid_clips)} clips → {output_path}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Compositor: FFmpeg completed successfully")

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg concat failed: {e.stderr[-2000:]}")
            raise
        finally:
            if os.path.exists(concat_file):
                os.unlink(concat_file)

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"Final video: {output_path} ({file_size_mb:.1f} MB, {len(valid_clips)} scenes)")
        return {
            "success": True,
            "output_path": output_path,
            "num_scenes": len(valid_clips),
            "file_size_mb": round(file_size_mb, 2),
        }
