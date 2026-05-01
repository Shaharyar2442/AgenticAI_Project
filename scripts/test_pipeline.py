"""
Manual Pipeline Test — runs each phase step-by-step with visible output.
Usage: python scripts/test_pipeline.py

This script tests the entire pipeline on the terminal so you can see
every intermediate output without needing the frontend.
"""
import asyncio
import json
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging to see everything
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("test_pipeline")


def divider(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_json(data, max_lines=30):
    """Pretty-print JSON, truncated."""
    text = json.dumps(data, indent=2, default=str)
    lines = text.split("\n")
    for line in lines[:max_lines]:
        print(f"  {line}")
    if len(lines) > max_lines:
        print(f"  ... ({len(lines) - max_lines} more lines)")


async def test_phase1():
    """Phase 1: Story Generation"""
    divider("PHASE 1: STORY GENERATION")

    from agents.story_agent.agent import generate_story

    prompt = "A young astronaut discovers a hidden ocean on Mars"
    print(f"  Prompt: {prompt}")
    print(f"  Calling LLM for structured story output...\n")

    start = time.time()
    story = await generate_story(prompt)
    elapsed = time.time() - start

    print(f"\n  [RESULT] Story generated in {elapsed:.1f}s")
    print(f"  Title:    {story.title}")
    print(f"  Genre:    {story.genre}")
    print(f"  Synopsis: {story.synopsis}")
    print(f"  Characters: {len(story.characters)}")
    for c in story.characters:
        print(f"    - {c.id}: {c.name} ({c.role}) | voice: {c.voice_description}")
    print(f"  Scenes: {len(story.scenes)}")
    for s in story.scenes:
        print(f"    - {s.scene_id}: {s.title} [mood: {s.mood}]")
        print(f"      Setting: {s.setting[:80]}...")
        print(f"      Dialogue: {len(s.dialogue)} lines")
        if s.narration:
            print(f"      Narration: {s.narration[:80]}...")

    # Save to file
    story_path = "data/temp/test_story.json"
    os.makedirs("data/temp", exist_ok=True)
    with open(story_path, "w") as f:
        json.dump(story.model_dump(), f, indent=2)
    print(f"\n  [SAVED] Story JSON -> {story_path}")

    return story


async def test_phase2(story):
    """Phase 2: Audio Generation"""
    divider("PHASE 2: AUDIO GENERATION")

    from agents.audio_agent.agent import generate_audio
    from mcp.tools.audio_tools.tts_tool import match_voice

    # Show voice assignments
    print("  Voice assignments:")
    for c in story.characters:
        voice = match_voice(c.voice_description)
        print(f"    {c.id} ({c.name}): {c.voice_description} -> {voice}")

    print(f"\n  Generating TTS for {len(story.scenes)} scenes...\n")

    start = time.time()
    manifest = await generate_audio(story, session_id="test")
    elapsed = time.time() - start

    print(f"\n  [RESULT] Audio generated in {elapsed:.1f}s")
    print(f"  Total duration: {manifest.total_duration_ms}ms ({manifest.total_duration_ms/1000:.1f}s)")
    print(f"  Segments: {len(manifest.segments)}")
    print(f"  Scene timings:")
    for st in manifest.scene_durations:
        print(f"    - {st.scene_id}: {st.measured_duration_ms}ms ({st.measured_duration_ms/1000:.1f}s)")
        print(f"      Audio: {st.audio_file}")
        print(f"      SRT:   {st.srt_file}")
        # Check files exist
        audio_exists = os.path.exists(st.audio_file)
        srt_exists = os.path.exists(st.srt_file)
        print(f"      Files exist: audio={audio_exists}, srt={srt_exists}")

    # Show segment details
    print(f"\n  Segment breakdown:")
    for seg in manifest.segments:
        print(f"    [{seg.scene_id}] {seg.type:10s} char={seg.character_id or 'N/A':8s} "
              f"{seg.start_ms:6d}ms - {seg.end_ms:6d}ms  {seg.audio_file.split(os.sep)[-1]}")

    # Save manifest
    manifest_path = "data/temp/test_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest.model_dump(), f, indent=2)
    print(f"\n  [SAVED] Timing manifest -> {manifest_path}")

    return manifest


async def test_phase3(story, manifest):
    """Phase 3: Video Generation"""
    divider("PHASE 3: VIDEO GENERATION")

    from shared.schemas.pipeline import PipelineState
    from mcp.tools.vision_tools.image_gen_tool import ImageGenTool
    from mcp.tools.video_tools.ffmpeg_tool import FFmpegTool, get_style_for_scene
    from mcp.tools.video_tools.compositor_tool import CompositorTool
    from shared.config import OUTPUTS_DIR, TEMP_DIR
    from agents.video_agent.agent import _build_portrait_timeline

    image_gen = ImageGenTool()
    ffmpeg = FFmpegTool()
    compositor = CompositorTool()

    session_id = "test"
    img_dir = str(OUTPUTS_DIR / "images" / session_id)
    vid_dir = str(OUTPUTS_DIR / "video" / session_id)
    temp_dir = str(TEMP_DIR / session_id)
    for d in [img_dir, vid_dir, temp_dir]:
        os.makedirs(d, exist_ok=True)

    state = PipelineState(
        user_prompt="test",
        story=story,
        timing_manifest=manifest,
    )

    # Step 3a: Generate character portraits
    print("  Step 3a: Generating character portraits...")
    char_portraits = {}
    for char in story.characters:
        out_path = os.path.join(img_dir, f"{char.id}_portrait.png")
        print(f"    Generating portrait: {char.name} ({char.visual_description[:50]}...)")
        result = await image_gen.execute(
            prompt=char.visual_description,
            output_path=out_path,
            image_type="portrait", seed=42
        )
        char_portraits[char.id] = result["image_path"]
        size_kb = os.path.getsize(result["image_path"]) / 1024
        print(f"      -> {result['image_path']} ({size_kb:.0f} KB, source: {result['source']})")
    state.character_portraits = char_portraits

    # Step 3b: Generate scene images
    print(f"\n  Step 3b: Generating scene background images...")
    scene_images = {}
    for i, scene in enumerate(story.scenes):
        out_path = os.path.join(img_dir, f"{scene.scene_id}.png")
        print(f"    Generating scene: {scene.title} ({scene.visual_prompt[:50]}...)")
        result = await image_gen.execute(
            prompt=scene.visual_prompt,
            output_path=out_path,
            image_type="scene", seed=42 + i
        )
        scene_images[scene.scene_id] = result["image_path"]
        size_kb = os.path.getsize(result["image_path"]) / 1024
        print(f"      -> {result['image_path']} ({size_kb:.0f} KB, source: {result['source']})")
    state.scene_images = scene_images

    # Step 3c: Render each scene (Ken Burns + portraits + audio + subtitles)
    print(f"\n  Step 3c: Rendering scene clips...")
    scene_clips = []
    for i, scene_timing in enumerate(manifest.scene_durations):
        sid = scene_timing.scene_id
        duration_sec = scene_timing.measured_duration_ms / 1000.0
        style = get_style_for_scene(i, story.scenes[i].mood if i < len(story.scenes) else "")

        kb_path = os.path.join(temp_dir, f"kb_{sid}.mp4")
        chars_path = os.path.join(temp_dir, f"chars_{sid}.mp4")
        av_path = os.path.join(temp_dir, f"av_{sid}.mp4")
        final_path = os.path.join(vid_dir, f"{sid}_final.mp4")

        print(f"\n    Scene: {sid} ({duration_sec:.1f}s, style: {style})")

        # Ken Burns
        print(f"      [1/4] Ken Burns animation...")
        start = time.time()
        await ffmpeg.execute("ken_burns", image_path=scene_images[sid],
                            duration_sec=duration_sec, output_path=kb_path, style=style)
        print(f"            Done ({time.time()-start:.1f}s) -> {kb_path}")

        # Portrait overlays
        timeline = _build_portrait_timeline(sid, manifest.segments, char_portraits)
        print(f"      [2/4] Portrait overlays ({len(timeline)} characters)...")
        start = time.time()
        await ffmpeg.execute("overlay_portraits", video_path=kb_path,
                            portrait_timeline=timeline, output_path=chars_path)
        print(f"            Done ({time.time()-start:.1f}s)")

        # Audio merge
        print(f"      [3/4] Merging audio...")
        start = time.time()
        await ffmpeg.execute("merge_audio", video_path=chars_path,
                            audio_path=scene_timing.audio_file, output_path=av_path)
        print(f"            Done ({time.time()-start:.1f}s)")

        # Subtitle burn
        if os.path.exists(scene_timing.srt_file):
            print(f"      [4/4] Burning subtitles...")
            start = time.time()
            await ffmpeg.execute("burn_subtitles", video_path=av_path,
                                srt_path=scene_timing.srt_file, output_path=final_path)
            print(f"            Done ({time.time()-start:.1f}s)")
        else:
            import shutil
            shutil.copy(av_path, final_path)
            print(f"      [4/4] No SRT file, skipped subtitles")

        scene_clips.append(final_path)
        size_mb = os.path.getsize(final_path) / (1024 * 1024)
        print(f"      COMPLETE -> {final_path} ({size_mb:.1f} MB)")

    # Step 3d: Concatenate all scenes
    print(f"\n  Step 3d: Compositing final video ({len(scene_clips)} scenes)...")
    final_output = os.path.join(vid_dir, "final_output.mp4")
    start = time.time()
    await compositor.execute(scene_clip_paths=scene_clips, output_path=final_output)
    elapsed = time.time() - start
    size_mb = os.path.getsize(final_output) / (1024 * 1024)
    print(f"    FINAL VIDEO: {final_output} ({size_mb:.1f} MB, composed in {elapsed:.1f}s)")

    state.final_video_path = final_output
    return state


async def test_phase5_edit(state):
    """Phase 5: Edit Agent"""
    divider("PHASE 5: EDIT AGENT TEST")

    from agents.edit_agent.intent_classifier import classify_intent
    from agents.edit_agent.planner import plan_edit

    test_queries = [
        "Make scene 2 darker",
        "Change the narrator's voice to a whisper",
        "Add epic background music",
        "Make the video black and white",
        "Speed up the last scene",
    ]

    print("  Testing edit intent classification:\n")
    for query in test_queries:
        intent = await classify_intent(query)
        plan = plan_edit(intent)
        print(f"  Query:  \"{query}\"")
        print(f"  Intent: {intent.intent}")
        print(f"  Target: {intent.target}")
        print(f"  Scope:  {intent.scope}")
        print(f"  Phases: {plan['phases_to_rerun']}")
        print()


async def test_state_manager():
    """Test state versioning"""
    divider("STATE MANAGER TEST")

    from state_manager.state_manager import StateManager

    sm = StateManager()

    # Save test versions
    sm.snapshot(1, {"status": "phase1_done", "title": "Original"}, [])
    sm.snapshot(2, {"status": "phase2_done", "title": "After audio"}, [])
    sm.snapshot(3, {"status": "complete", "title": "Final"}, [])

    print("  Saved 3 test versions")

    # List history
    history = sm.history()
    print(f"  Version history ({len(history)} entries):")
    for v in history:
        print(f"    v{v['version']}: {v['created_at']}")

    # Diff
    diff = sm.get_diff(1, 3)
    print(f"\n  Diff v1 -> v3:")
    for change in diff.get("changes", []):
        print(f"    {change['field']}: {change['old_summary']} -> {change['new_summary']}")

    # Revert
    reverted = sm.revert(1)
    print(f"\n  Reverted to v1: status={reverted['status']}, title={reverted['title']}")


async def main():
    divider("AI VIDEO GENERATION PIPELINE - MANUAL TEST")
    print("  This script runs each phase step-by-step.")
    print("  All outputs are saved to data/outputs/ and data/temp/")
    total_start = time.time()

    # Phase 1: Story
    story = await test_phase1()

    # Phase 2: Audio
    manifest = await test_phase2(story)

    # Phase 3: Video
    state = await test_phase3(story, manifest)

    # Phase 5: Edit classification
    await test_phase5_edit(state)

    # State Manager
    await test_state_manager()

    # Summary
    divider("ALL TESTS COMPLETE")
    total_elapsed = time.time() - total_start
    print(f"  Total time: {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")
    print(f"  Final video: {state.final_video_path}")
    print(f"\n  Output directories:")
    print(f"    data/outputs/audio/test/   - TTS audio + SRT files")
    print(f"    data/outputs/images/test/  - Scene images + portraits")
    print(f"    data/outputs/video/test/   - Scene clips + final video")
    print(f"    data/temp/                 - Intermediate files + JSON")


if __name__ == "__main__":
    asyncio.run(main())
