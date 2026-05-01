"""
Subtitle Tool — generates and manages SRT subtitle files.
"""
from mcp.base_tool import BaseTool
from typing import Any, Dict, List
import os
import logging

logger = logging.getLogger(__name__)


class SubtitleTool(BaseTool):
    name = "subtitle_manager"
    description = "Merge multiple SRT files or generate combined subtitles with offset timing."

    async def execute(self, srt_files: List[Dict],
                      output_path: str, **kwargs) -> Dict[str, Any]:
        """
        Merge multiple SRT files with time offsets.
        srt_files: [{"path": "line.srt", "offset_ms": 0}, ...]
        """
        merged_entries = []
        counter = 1

        for srt_info in srt_files:
            path = srt_info["path"]
            offset_ms = srt_info.get("offset_ms", 0)

            if not os.path.exists(path):
                continue

            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                continue

            # Parse SRT entries and apply offset
            blocks = content.split("\n\n")
            for block in blocks:
                lines = block.strip().split("\n")
                if len(lines) >= 3:
                    # Parse timing line
                    timing = lines[1]
                    text = " ".join(lines[2:])

                    # Apply offset to timing
                    try:
                        start_str, end_str = timing.split(" --> ")
                        start_ms = _srt_to_ms(start_str.strip()) + offset_ms
                        end_ms = _srt_to_ms(end_str.strip()) + offset_ms

                        merged_entries.append({
                            "index": counter,
                            "start_ms": start_ms,
                            "end_ms": end_ms,
                            "text": text,
                        })
                        counter += 1
                    except Exception:
                        continue

        # Write merged SRT
        with open(output_path, "w", encoding="utf-8") as f:
            for entry in merged_entries:
                f.write(f"{entry['index']}\n")
                f.write(f"{_ms_to_srt(entry['start_ms'])} --> {_ms_to_srt(entry['end_ms'])}\n")
                f.write(f"{entry['text']}\n\n")

        logger.info(f"Merged {len(merged_entries)} subtitle entries -> {output_path}")
        return {"success": True, "srt_path": output_path, "entry_count": len(merged_entries)}


def _srt_to_ms(time_str: str) -> int:
    """Convert SRT timestamp (HH:MM:SS,mmm) to milliseconds."""
    time_str = time_str.replace(",", ".")
    parts = time_str.split(":")
    h, m = int(parts[0]), int(parts[1])
    s_parts = parts[2].split(".")
    s = int(s_parts[0])
    ms = int(s_parts[1]) if len(s_parts) > 1 else 0
    return h * 3600000 + m * 60000 + s * 1000 + ms


def _ms_to_srt(ms: int) -> str:
    """Convert milliseconds to SRT timestamp format."""
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
