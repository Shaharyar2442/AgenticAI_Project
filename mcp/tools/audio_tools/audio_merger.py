"""
Audio Merger Tool — merges dialogue lines + BGM into per-scene audio.
Produces combined audio file and timing metadata.
"""
from mcp.base_tool import BaseTool
from typing import Any, Dict, List
from pydub import AudioSegment
import os
import logging

logger = logging.getLogger(__name__)

DIALOGUE_GAP_MS = 400  # Gap between dialogue lines
BGM_VOLUME_REDUCTION = -18  # dB reduction for BGM under dialogue


class AudioMergerTool(BaseTool):
    name = "audio_merger"
    description = "Merge multiple dialogue audio files and optional BGM into a single scene audio track."

    async def execute(self, audio_files: List[str], bgm_file: str = None,
                      output_path: str = "", **kwargs) -> Dict[str, Any]:
        """
        Merge audio files sequentially with gaps, overlay BGM.
        Returns: {combined_file, duration_ms, segment_timings}
        """
        if not audio_files:
            return {"success": False, "error": "No audio files provided"}

        combined = AudioSegment.empty()
        segment_timings = []
        gap = AudioSegment.silent(duration=DIALOGUE_GAP_MS)

        for i, audio_path in enumerate(audio_files):
            if not os.path.exists(audio_path):
                logger.warning(f"Audio file not found: {audio_path}, using silence")
                segment = AudioSegment.silent(duration=2000)
            else:
                segment = AudioSegment.from_mp3(audio_path)

            start_ms = len(combined)
            combined += segment
            end_ms = len(combined)

            segment_timings.append({
                "index": i,
                "audio_file": audio_path,
                "start_ms": start_ms,
                "end_ms": end_ms,
            })

            # Add gap between lines (not after last)
            if i < len(audio_files) - 1:
                combined += gap

        # Overlay BGM if available
        if bgm_file and os.path.exists(bgm_file):
            try:
                bgm = AudioSegment.from_mp3(bgm_file)
                # Loop BGM to match dialogue length
                while len(bgm) < len(combined):
                    bgm += bgm
                bgm = bgm[:len(combined)]
                bgm = bgm + BGM_VOLUME_REDUCTION  # Reduce volume
                combined = combined.overlay(bgm)
                logger.info(f"BGM overlaid at {BGM_VOLUME_REDUCTION}dB")
            except Exception as e:
                logger.warning(f"Failed to overlay BGM: {e}")

        # Export
        combined.export(output_path, format="mp3")
        duration_ms = len(combined)

        logger.info(f"Merged {len(audio_files)} audio files -> {output_path} ({duration_ms}ms)")
        return {
            "success": True,
            "combined_file": output_path,
            "duration_ms": duration_ms,
            "segment_timings": segment_timings,
        }
