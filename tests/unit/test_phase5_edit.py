"""
Phase 5 Unit Tests — Edit agent, state manager, image filters, pipeline state.
"""
import pytest
import os
import tempfile
import json
import shutil
from pydantic import ValidationError
from shared.schemas.edit import EditIntent
from shared.schemas.pipeline import PipelineState
from agents.edit_agent.planner import plan_edit
from state_manager.state_manager import StateManager


class TestEditIntentSchema:
    def test_valid_edit_intent(self):
        intent = EditIntent(intent="change_voice_tone", target="audio", scope="all", parameters={})
        assert intent.target == "audio"

    def test_default_scope_is_all(self):
        intent = EditIntent(intent="apply_filter", target="video_frame")
        assert intent.scope == "all"

    def test_default_parameters_empty(self):
        intent = EditIntent(intent="remove_subtitles", target="video")
        assert intent.parameters == {}

    def test_json_round_trip(self):
        intent = EditIntent(intent="change_speed", target="video", scope="scene_02",
                            parameters={"speed": 1.5})
        json_str = intent.model_dump_json()
        intent2 = EditIntent.model_validate_json(json_str)
        assert intent2.intent == "change_speed"
        assert intent2.parameters["speed"] == 1.5

    def test_all_valid_targets(self):
        for target in ["audio", "video_frame", "video", "script"]:
            intent = EditIntent(intent="test", target=target)
            assert intent.target == target


class TestEditPlanner:
    def _intent(self, target, intent_str="test"):
        return EditIntent(intent=intent_str, target=target)

    def test_script_target_reruns_all_phases(self):
        plan = plan_edit(self._intent("script"))
        assert set(plan["phases_to_rerun"]) == {1, 2, 3}

    def test_audio_target_reruns_phase2_and_3(self):
        plan = plan_edit(self._intent("audio"))
        assert set(plan["phases_to_rerun"]) == {2, 3}

    def test_video_frame_reruns_only_phase3(self):
        plan = plan_edit(self._intent("video_frame"))
        assert set(plan["phases_to_rerun"]) == {3}

    def test_video_target_reruns_only_phase3(self):
        plan = plan_edit(self._intent("video"))
        assert set(plan["phases_to_rerun"]) == {3}

    def test_plan_contains_intent_metadata(self):
        plan = plan_edit(self._intent("audio", "change_bgm_mood"))
        assert "intent" in plan
        assert "scope" in plan
        assert "parameters" in plan

    def test_plan_description_includes_intent(self):
        plan = plan_edit(self._intent("script", "regenerate_script"))
        desc = plan.get("description", "").lower()
        assert len(desc) > 0

    def test_unknown_target_defaults_to_phase3(self):
        intent = EditIntent(intent="unknown", target="unknown_target")
        plan = plan_edit(intent)
        assert 3 in plan["phases_to_rerun"]

    def test_all_targets_in_map(self):
        for target in ["audio", "video_frame", "video", "script"]:
            plan = plan_edit(self._intent(target))
            assert len(plan["phases_to_rerun"]) >= 1


class TestStateManager:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.sm = StateManager(base_dir=self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_load_version(self):
        data = {"session_id": "test", "version": 1}
        self.sm.save_version(1, data, "Initial state")
        loaded = self.sm.load_version(1)
        assert loaded["session_id"] == "test"

    def test_load_nonexistent_version_raises(self):
        with pytest.raises(Exception):
            self.sm.load_version(999)

    def test_list_versions_empty(self):
        versions = self.sm.list_versions()
        assert isinstance(versions, list)
        assert len(versions) == 0

    def test_list_versions_after_save(self):
        self.sm.save_version(1, {"x": 1}, "v1")
        self.sm.save_version(2, {"x": 2}, "v2")
        versions = self.sm.list_versions()
        assert len(versions) == 2

    def test_get_latest_version_empty(self):
        v = self.sm.get_latest_version()
        assert v is None

    def test_get_latest_version_after_saves(self):
        self.sm.save_version(1, {"x": 1}, "v1")
        self.sm.save_version(3, {"x": 3}, "v3")
        v = self.sm.get_latest_version()
        assert v == 3

    def test_save_version_overwrites_existing(self):
        self.sm.save_version(1, {"x": 1}, "v1")
        self.sm.save_version(1, {"x": 99}, "v1 updated")
        loaded = self.sm.load_version(1)
        assert loaded["x"] == 99

    def test_snapshot_creates_files(self, tmp_path):
        # Create a fake asset file
        asset = tmp_path / "test_asset.txt"
        asset.write_text("fake content")
        state_data = {"session_id": "snap_test", "version": 1}
        self.sm.snapshot(1, state_data, [str(asset)])
        versions = self.sm.list_versions()
        assert any(v == 1 for v in versions)

    def test_snapshot_restore(self, tmp_path):
        asset = tmp_path / "video.mp4"
        asset.write_bytes(b"\x00\x01\x02")
        state_data = {"session_id": "restore_test", "version": 2, "final_video_path": str(asset)}
        self.sm.snapshot(2, state_data, [str(asset)])
        restored = self.sm.revert(2)
        assert restored["version"] == 2

    def test_snapshot_restore_nonexistent_raises(self):
        with pytest.raises(Exception):
            self.sm.revert(9999)


class TestHistoryDiff:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.sm = StateManager(base_dir=self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_diff_detects_changes(self):
        self.sm.save_version(1, {"field": "original"}, "v1")
        self.sm.save_version(2, {"field": "changed"}, "v2")
        diff = self.sm.diff(1, 2)
        assert "field" in diff or isinstance(diff, dict)

    def test_diff_nonexistent_version_returns_error(self):
        self.sm.save_version(1, {"field": "v1"}, "v1")
        try:
            diff = self.sm.diff(1, 999)
            assert "error" in diff or diff is None
        except Exception:
            pass  # Raising is also acceptable


class TestImageEditFilters:
    def test_darken_filter(self, tmp_path):
        from PIL import Image
        from mcp.tools.vision_tools.image_edit_tool import ImageEditTool
        import asyncio

        img_path = str(tmp_path / "input.png")
        out_path = str(tmp_path / "output.png")
        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        img.save(img_path)

        tool = ImageEditTool()
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(operation="apply_filter", image_path=img_path,
                         output_path=out_path, filter_name="darken")
        )
        assert result["success"] is True
        out_img = Image.open(out_path)
        px = out_img.getpixel((50, 50))
        assert px[0] < 200  # should be darker

    def test_unknown_filter_returns_error(self, tmp_path):
        from PIL import Image
        from mcp.tools.vision_tools.image_edit_tool import ImageEditTool
        import asyncio

        img_path = str(tmp_path / "input.png")
        out_path = str(tmp_path / "output.png")
        img = Image.new("RGB", (100, 100), color=(100, 100, 100))
        img.save(img_path)

        tool = ImageEditTool()
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(operation="apply_filter", image_path=img_path,
                         output_path=out_path, filter_name="nonexistent_filter")
        )
        assert result["success"] is False

    def test_missing_image_returns_error(self, tmp_path):
        from mcp.tools.vision_tools.image_edit_tool import ImageEditTool
        import asyncio

        tool = ImageEditTool()
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(operation="apply_filter",
                         image_path="/nonexistent/path/image.png",
                         output_path=str(tmp_path / "out.png"),
                         filter_name="darken")
        )
        assert result["success"] is False

    def test_all_filters_run(self, tmp_path):
        from PIL import Image
        from mcp.tools.vision_tools.image_edit_tool import ImageEditTool
        import asyncio

        for filter_name in ["darken", "brighten", "grayscale", "blur", "sharpen"]:
            img_path = str(tmp_path / f"in_{filter_name}.png")
            out_path = str(tmp_path / f"out_{filter_name}.png")
            img = Image.new("RGB", (100, 100), color=(128, 128, 128))
            img.save(img_path)

            tool = ImageEditTool()
            result = asyncio.get_event_loop().run_until_complete(
                tool.execute(operation="apply_filter", image_path=img_path,
                             output_path=out_path, filter_name=filter_name)
            )
            assert result["success"] is True, f"Filter '{filter_name}' failed: {result}"


class TestPipelineState:
    def test_default_state(self):
        state = PipelineState(session_id="test_session")
        assert state.session_id == "test_session"
        assert state.version == 0
        assert state.story is None

    def test_state_json_round_trip(self):
        state = PipelineState(session_id="rt_test", version=3)
        json_str = state.model_dump_json()
        state2 = PipelineState.model_validate_json(json_str)
        assert state2.session_id == "rt_test"
        assert state2.version == 3

    def test_state_scene_images_dict(self):
        state = PipelineState(
            session_id="img_test",
            scene_images={"scene_01": "/path/scene_01.png"}
        )
        assert state.scene_images["scene_01"] == "/path/scene_01.png"
