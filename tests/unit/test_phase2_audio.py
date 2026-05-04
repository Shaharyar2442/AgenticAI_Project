"""
Phase 2 Unit Tests — Audio Generation schemas, voice matching, SRT generation, BGM tool.
"""
import pytest
import os
import tempfile
from pydantic import ValidationError
from shared.schemas.audio import AudioSegment, SceneTiming, TimingManifest
from mcp.tools.audio_tools.tts_tool import TTSTool, match_voice, _ms_to_srt, _generate_estimated_srt
from mcp.tools.audio_tools.bgm_tool import BGMTool


class TestAudioSchemas:
    def test_valid_audio_segment(self):
        seg = AudioSegment(
            scene_id="s1", character_id="c1",
            audio_file="path/to/file.wav",
            start_ms=0, end_ms=5000, type="dialogue"
        )
        assert seg.type == "dialogue"
        assert seg.end_ms == 5000

    def test_narration_segment_no_character(self):
        seg = AudioSegment(
            scene_id="s1", character_id=None,
            audio_file="narration.wav",
            start_ms=0, end_ms=3000, type="narration"
        )
        assert seg.character_id is None

    def test_bgm_segment(self):
        seg = AudioSegment(
            scene_id="s1", character_id=None,
            audio_file="bgm.mp3",
            start_ms=0, end_ms=15000, type="bgm"
        )
        assert seg.type == "bgm"

    def test_scene_timing(self):
        seg = AudioSegment(scene_id="s1", character_id="c1",
                           audio_file="f.wav", start_ms=0, end_ms=3000, type="dialogue")
        timing = SceneTiming(scene_id="s1", segments=[seg], total_duration_ms=3000)
        assert timing.total_duration_ms == 3000

    def test_timing_manifest_round_trip(self):
        seg = AudioSegment(scene_id="s1", character_id="c1",
                           audio_file="f.wav", start_ms=0, end_ms=3000, type="dialogue")
        timing = SceneTiming(scene_id="s1", segments=[seg], total_duration_ms=3000)
        manifest = TimingManifest(scenes=[timing], total_pipeline_duration_ms=3000)
        json_str = manifest.model_dump_json()
        manifest2 = TimingManifest.model_validate_json(json_str)
        assert len(manifest2.scenes) == 1

    def test_word_timestamp(self):
        from shared.schemas.audio import WordTimestamp
        wt = WordTimestamp(word="hello", start_ms=0, end_ms=400)
        assert wt.word == "hello"


class TestVoiceMatching:
    def test_deep_male(self):
        voice = match_voice("deep baritone voice")
        assert "Neural" in voice

    def test_female_narrator(self):
        voice = match_voice("female narrator")
        assert "Neural" in voice

    def test_young_male(self):
        voice = match_voice("young male protagonist")
        assert "Neural" in voice

    def test_old_female(self):
        voice = match_voice("old woman, wise and gentle")
        assert "Neural" in voice

    def test_unknown_description_defaults(self):
        voice = match_voice("mysterious unknown entity")
        assert voice is not None
        assert "Neural" in voice

    def test_female_fallback(self):
        voice = match_voice("woman with a kind voice")
        assert "Neural" in voice

    def test_narrator_keyword(self):
        voice = match_voice("narrator, calm and measured")
        assert "Neural" in voice


class TestSRTGeneration:
    def test_ms_to_srt_zero(self):
        assert _ms_to_srt(0) == "00:00:00,000"

    def test_ms_to_srt_one_hour(self):
        assert _ms_to_srt(3600000) == "01:00:00,000"

    def test_ms_to_srt_one_minute_thirty(self):
        assert _ms_to_srt(90500) == "00:01:30,500"

    def test_srt_file_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            srt_path = os.path.join(tmpdir, "test.srt")
            _generate_estimated_srt("Hello world this is a test", 5000, srt_path)
            assert os.path.exists(srt_path)

    def test_srt_empty_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            srt_path = os.path.join(tmpdir, "empty.srt")
            _generate_estimated_srt("", 3000, srt_path)
            assert os.path.exists(srt_path)

    def test_srt_chunk_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            srt_path = os.path.join(tmpdir, "chunks.srt")
            text = " ".join([f"word{i}" for i in range(16)])  # 16 words -> 4 chunks of 4
            _generate_estimated_srt(text, 8000, srt_path)
            content = open(srt_path).read()
            assert "1\n" in content


class TestBGMTool:
    def test_bgm_file_exists_returns_path(self, tmp_path):
        bgm_file = tmp_path / "calm_peaceful.mp3"
        bgm_file.write_bytes(b"fake audio data")

        import mcp.tools.audio_tools.bgm_tool as bgm_mod
        original = bgm_mod.BGM_DIR

        try:
            import pathlib
            bgm_mod.BGM_DIR = tmp_path
            from shared import config as cfg_mod
            cfg_mod.BGM_DIR = tmp_path

            tool = BGMTool()
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(tool.execute("calm"))
            assert result["success"] is True
        finally:
            bgm_mod.BGM_DIR = original

    def test_bgm_unknown_mood_returns_none(self, tmp_path):
        import mcp.tools.audio_tools.bgm_tool as bgm_mod
        from shared import config as cfg_mod
        original = cfg_mod.BGM_DIR
        cfg_mod.BGM_DIR = tmp_path
        try:
            import asyncio
            tool = BGMTool()
            result = asyncio.get_event_loop().run_until_complete(tool.execute("unknownmood"))
            assert result["success"] is True
            assert result["bgm_file"] is None
        finally:
            cfg_mod.BGM_DIR = original

    def test_bgm_tool_execute_with_existing_file(self, tmp_path):
        import mcp.tools.audio_tools.bgm_tool as bgm_mod
        from shared import config as cfg_mod

        bgm_file = tmp_path / "happy_upbeat.mp3"
        bgm_file.write_bytes(b"fake audio data")
        original = cfg_mod.BGM_DIR
        cfg_mod.BGM_DIR = tmp_path
        try:
            import asyncio
            tool = BGMTool()
            result = asyncio.get_event_loop().run_until_complete(tool.execute("happy"))
            assert result["success"] is True
            assert "happy_upbeat.mp3" in (result.get("bgm_file") or "")
        finally:
            cfg_mod.BGM_DIR = original
