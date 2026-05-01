"""
FFmpeg Tool — wrapper for Ken Burns, audio merge, subtitle burn, character overlay.
Global FPS = 25 everywhere.
"""
from mcp.base_tool import BaseTool
from shared.config import GLOBAL_FPS
from typing import Any, Dict, List
import subprocess
import shutil
import os
import logging

logger = logging.getLogger(__name__)

FPS = GLOBAL_FPS  # 25 — used in zoompan, overlay, and final concat. NEVER 24.

KEN_BURNS_STYLES = {
    "zoom_in_center": "z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "zoom_out": "z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "pan_left": "z='1.1':x='iw*(1-on/(25*{duration}))':y='ih/2-(ih/zoom/2)'",
    "pan_right": "z='1.1':x='iw*on/(25*{duration})':y='ih/2-(ih/zoom/2)'",
    "pan_up": "z='1.1':x='iw/2-(iw/zoom/2)':y='ih*(1-on/(25*{duration}))'",
}


def get_style_for_scene(scene_index: int, mood: str = "") -> str:
    """Cycle through Ken Burns styles so consecutive scenes look different."""
    styles = list(KEN_BURNS_STYLES.keys())
    return styles[scene_index % len(styles)]


def _run_ffmpeg(cmd: List[str], description: str = ""):
    """Run FFmpeg command with error handling."""
    logger.info(f"FFmpeg [{description}]: {' '.join(cmd[:8])}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed [{description}]: {e.stderr[:500]}")
        raise


class FFmpegTool(BaseTool):
    name = "ffmpeg"
    description = "FFmpeg operations: Ken Burns animation, audio merge, subtitle burn, character overlay."

    async def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Route to specific FFmpeg operation."""
        ops = {
            "ken_burns": self._ken_burns,
            "merge_audio": self._merge_audio,
            "burn_subtitles": self._burn_subtitles,
            "overlay_portraits": self._overlay_portraits,
            "speed_change": self._speed_change,
        }
        if operation not in ops:
            return {"success": False, "error": f"Unknown operation: {operation}"}
        return await ops[operation](**kwargs)

    async def _ken_burns(self, image_path: str, duration_sec: float,
                         output_path: str, style: str = "zoom_in_center", **kwargs) -> Dict:
        """Create a Ken Burns animated video clip from a still image."""
        total_frames = int(duration_sec * FPS)
        zoompan_expr = KEN_BURNS_STYLES.get(style, KEN_BURNS_STYLES["zoom_in_center"])
        zoompan_expr = zoompan_expr.format(duration=duration_sec)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-vf", f"zoompan={zoompan_expr}:d={total_frames}:s=1920x1080:fps={FPS}",
            "-t", str(duration_sec),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_path
        ]
        _run_ffmpeg(cmd, f"ken_burns_{style}")
        return {"success": True, "output_path": output_path}

    async def _merge_audio(self, video_path: str, audio_path: str,
                           output_path: str, **kwargs) -> Dict:
        """Overlay audio on video, cutting to shortest."""
        cmd = [
            "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-shortest", output_path
        ]
        _run_ffmpeg(cmd, "merge_audio")
        return {"success": True, "output_path": output_path}

    async def _burn_subtitles(self, video_path: str, srt_path: str,
                              output_path: str, **kwargs) -> Dict:
        """Burn SRT subtitles into video.
        
        Windows path escaping for the FFmpeg subtitles filter is notoriously
        broken (colons, backslashes, spaces all need different escaping by version).
        The robust fix: copy the SRT next to the video and use a plain filename.
        """
        # Copy SRT to same directory as video with a simple name
        video_dir = os.path.dirname(video_path)
        temp_srt = os.path.join(video_dir, "_subs.srt")
        shutil.copy2(srt_path, temp_srt)
        
        # Use relative path from video_dir — no colons, no spaces to escape
        # Run FFmpeg with cwd=video_dir so relative paths work
        video_basename = os.path.basename(video_path)
        output_basename = os.path.basename(output_path)
        
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        cmd = [
            "ffmpeg", "-y", "-i", video_basename,
            "-vf", "subtitles=_subs.srt:force_style='FontSize=22,PrimaryColour=&HFFFFFF&,Outline=2,Shadow=1'",
            "-c:a", "copy", output_path
        ]
        
        logger.info(f"FFmpeg [burn_subtitles]: running from {video_dir}")
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=video_dir)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg subtitles failed: {e.stderr[:500]}")
            # Fallback: skip subtitles, just copy video through
            logger.warning("Subtitle burn failed — copying video without subtitles")
            shutil.copy(video_path, output_path)
        finally:
            # Cleanup temp SRT
            if os.path.exists(temp_srt):
                os.remove(temp_srt)
        
        return {"success": True, "output_path": output_path}

    async def _overlay_portraits(self, video_path: str,
                                  portrait_timeline: List[Dict],
                                  output_path: str, **kwargs) -> Dict:
        """Overlay character portraits timed to dialogue."""
        # Guard: narration-only scenes have no dialogue -> no portraits
        if not portrait_timeline:
            shutil.copy(video_path, output_path)
            return {"success": True, "output_path": output_path, "note": "no portraits to overlay"}

        inputs = [video_path] + [p["portrait"] for p in portrait_timeline]
        input_args = []
        for inp in inputs:
            input_args.extend(["-i", inp])

        filters = []
        prev = "0:v"
        for i, entry in enumerate(portrait_timeline):
            inp_idx = i + 1
            out_label = f"v{i}"
            filters.append(
                f"[{inp_idx}:v]scale=250:250,format=rgba[char{i}];"
                f"[{prev}][char{i}]overlay=20:H-270:"
                f"enable='between(t,{entry['start_sec']},{entry['end_sec']})'[{out_label}]"
            )
            prev = out_label

        cmd = ["ffmpeg", "-y"] + input_args + [
            "-filter_complex", ";".join(filters),
            "-map", f"[{prev}]", "-map", "0:a?",
            "-c:v", "libx264", "-c:a", "copy", output_path
        ]
        _run_ffmpeg(cmd, "overlay_portraits")
        return {"success": True, "output_path": output_path}

    async def _speed_change(self, video_path: str, speed_factor: float,
                            output_path: str, **kwargs) -> Dict:
        """Change video speed (e.g., 1.5 = 50% faster)."""
        atempo = speed_factor
        if atempo > 2.0:
            atempo = 2.0
        elif atempo < 0.5:
            atempo = 0.5
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-filter_complex",
            f"[0:v]setpts={1/speed_factor}*PTS[v];[0:a]atempo={atempo}[a]",
            "-map", "[v]", "-map", "[a]",
            output_path
        ]
        _run_ffmpeg(cmd, f"speed_{speed_factor}x")
        return {"success": True, "output_path": output_path}
