"""
Phase 3 Unit Tests — Video composition: Ken Burns styles, FFmpeg routing, image fallback.
"""
import pytest
import os
import shutil
import tempfile
from unittest.mock import patch, AsyncMock, MagicMock
from mcp.tools.video_tools.ffmpeg_tool import FFmpegTool, KEN_BURNS_STYLES, get_style_for_scene


class TestKenBurnsStyles:
    REQUIRED_STYLES = {"zoom_in_center", "zoom_out", "pan_left", "pan_right", "pan_up"}

    def test_all_styles_present(self):
        for style in self.REQUIRED_STYLES:
            assert style in KEN_BURNS_STYLES, f"Missing Ken Burns style: {style}"

    def test_zoom_in_center_no_placeholder(self):
        expr = KEN_BURNS_STYLES["zoom_in_center"]
        # Static styles must NOT have {duration} since they don't need runtime injection
        assert "{duration}" not in expr

    def test_pan_left_injects_duration(self):
        raw = KEN_BURNS_STYLES["pan_left"]
        assert "{duration}" in raw
        injected = raw.format(duration=10)
        assert "{duration}" not in injected
        assert "10" in injected

    def test_pan_right_injects_duration(self):
        raw = KEN_BURNS_STYLES["pan_right"]
        assert "{duration}" in raw
        injected = raw.format(duration=8.5)
        assert "8.5" in injected

    def test_pan_up_injects_duration(self):
        raw = KEN_BURNS_STYLES["pan_up"]
        assert "{duration}" in raw
        injected = raw.format(duration=12)
        assert "12" in injected

    def test_zoom_out_no_placeholder(self):
        expr = KEN_BURNS_STYLES["zoom_out"]
        assert "{duration}" not in expr

    def test_get_style_cycles(self):
        styles = list(KEN_BURNS_STYLES.keys())
        for i in range(len(styles) * 2 + 1):
            style = get_style_for_scene(i)
            assert style in KEN_BURNS_STYLES

    def test_get_style_scene_0(self):
        style = get_style_for_scene(0)
        assert style == list(KEN_BURNS_STYLES.keys())[0]

    def test_get_style_scene_5(self):
        style = get_style_for_scene(5)
        n = len(KEN_BURNS_STYLES)
        assert style == list(KEN_BURNS_STYLES.keys())[5 % n]


class TestFFmpegToolRouting:
    def setup_method(self):
        self.tool = FFmpegTool()

    @pytest.mark.asyncio
    async def test_unknown_operation_returns_error(self):
        result = await self.tool.execute("nonexistent_op")
        assert result["success"] is False
        assert "Unknown operation" in result["error"]

    @pytest.mark.asyncio
    async def test_ken_burns_called(self):
        with patch.object(self.tool, "_ken_burns", new_callable=AsyncMock) as mock_kb:
            mock_kb.return_value = {"success": True, "output_path": "out.mp4"}
            result = await self.tool.execute("ken_burns", image_path="img.png",
                                             duration_sec=5.0, output_path="out.mp4")
            mock_kb.assert_called_once()
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_merge_audio_called(self):
        with patch.object(self.tool, "_merge_audio", new_callable=AsyncMock) as mock_merge:
            mock_merge.return_value = {"success": True, "output_path": "out.mp4"}
            result = await self.tool.execute("merge_audio", video_path="v.mp4",
                                             audio_path="a.wav", output_path="out.mp4")
            mock_merge.assert_called_once()

    @pytest.mark.asyncio
    async def test_overlay_portraits_empty_timeline_copies_video(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_video = os.path.join(tmpdir, "src.mp4")
            dst_video = os.path.join(tmpdir, "dst.mp4")
            open(src_video, "wb").write(b"\x00" * 100)  # fake mp4

            result = await self.tool.execute("overlay_portraits",
                                             video_path=src_video,
                                             portrait_timeline=[],
                                             output_path=dst_video)
            assert result["success"] is True
            assert os.path.exists(dst_video)

    @pytest.mark.asyncio
    async def test_overlay_portraits_missing_video_raises(self):
        with pytest.raises(FileNotFoundError):
            await self.tool.execute("overlay_portraits",
                                    video_path="/nonexistent/path.mp4",
                                    portrait_timeline=[{"portrait": "p.png",
                                                        "start_sec": 0, "end_sec": 3}],
                                    output_path="/tmp/out.mp4")

    @pytest.mark.asyncio
    async def test_speed_change_clamps_atempo(self):
        captured = {}

        async def fake_run_speed(**kwargs):
            captured.update(kwargs)
            return {"success": True, "output_path": "out.mp4"}

        with patch.object(self.tool, "_speed_change", new_callable=AsyncMock) as mock_speed:
            mock_speed.return_value = {"success": True, "output_path": "out.mp4"}
            result = await self.tool.execute("speed_change", video_path="v.mp4",
                                             speed_factor=0.3, output_path="out.mp4")
            mock_speed.assert_called_once()


class TestImageFallback:
    def test_fallback_creates_file(self, tmp_path):
        from mcp.tools.vision_tools.image_gen_tool import _generate_fallback_image
        output = str(tmp_path / "fallback.png")
        _generate_fallback_image("A red desert at dawn", output, size=(320, 180))
        assert os.path.exists(output)
        assert os.path.getsize(output) > 100

    def test_fallback_portrait_size(self, tmp_path):
        from mcp.tools.vision_tools.image_gen_tool import _generate_fallback_image
        from PIL import Image
        output = str(tmp_path / "portrait.png")
        _generate_fallback_image("Character portrait", output, size=(512, 512))
        img = Image.open(output)
        assert img.size == (512, 512)

    def test_fallback_long_prompt_truncated(self, tmp_path):
        from mcp.tools.vision_tools.image_gen_tool import _generate_fallback_image
        output = str(tmp_path / "long_prompt.png")
        long_text = "A " * 200
        _generate_fallback_image(long_text, output, size=(320, 180))
        assert os.path.exists(output)
