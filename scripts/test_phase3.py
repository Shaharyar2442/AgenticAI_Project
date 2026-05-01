"""
Test Phase 3 only — Video Generation.
Loads story + manifest from Phase 1 & 2 outputs.
Usage: python scripts/test_phase3.py
"""
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    from shared.schemas.story import StoryOutput
    from shared.schemas.audio import TimingManifest
    from shared.schemas.pipeline import PipelineState
    from agents.video_agent.agent import generate_video

    # Load from previous phases
    story_path = "data/temp/test_story.json"
    manifest_path = "data/temp/test_manifest.json"

    for path, name in [(story_path, "story"), (manifest_path, "manifest")]:
        if not os.path.exists(path):
            print(f"[ERROR] No {name} found at {path}")
            print(f"  Run previous phases first:")
            print(f"    python scripts/test_phase1.py")
            print(f"    python scripts/test_phase2.py")
            return

    with open(story_path) as f:
        story = StoryOutput(**json.load(f))
    with open(manifest_path) as f:
        manifest = TimingManifest(**json.load(f))

    print(f"[Phase 3] Loaded story: '{story.title}' + timing manifest")
    print(f"  {len(story.scenes)} scenes, total audio: {manifest.total_duration_ms}ms")

    state = PipelineState(
        user_prompt="test",
        story=story,
        timing_manifest=manifest,
    )

    print(f"\n  Generating images + compositing video...")
    print(f"  This may take several minutes (image downloads + FFmpeg encoding)\n")

    start = time.time()
    final_path = await generate_video(state, session_id="test")
    elapsed = time.time() - start

    print(f"\n{'='*60}")
    print(f"  Video generation complete in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"{'='*60}")

    # Show all generated assets
    print(f"\n  Character portraits:")
    for cid, path in state.character_portraits.items():
        size = os.path.getsize(path) / 1024 if os.path.exists(path) else 0
        print(f"    {cid}: {os.path.basename(path)} ({size:.0f} KB)")

    print(f"\n  Scene images:")
    for sid, path in state.scene_images.items():
        size = os.path.getsize(path) / 1024 if os.path.exists(path) else 0
        print(f"    {sid}: {os.path.basename(path)} ({size:.0f} KB)")

    print(f"\n  Scene clips:")
    for sid, path in state.scene_videos.items():
        size = os.path.getsize(path) / (1024*1024) if os.path.exists(path) else 0
        print(f"    {sid}: {os.path.basename(path)} ({size:.1f} MB)")

    if state.final_video_path and os.path.exists(state.final_video_path):
        size = os.path.getsize(state.final_video_path) / (1024*1024)
        print(f"\n  FINAL VIDEO: {state.final_video_path} ({size:.1f} MB)")
        print(f"  Open it with: start {state.final_video_path}")
    else:
        print(f"\n  [ERROR] Final video not found!")

    # Save state
    out = "data/temp/test_state.json"
    with open(out, "w") as f:
        json.dump(state.model_dump(), f, indent=2)
    print(f"\n  Saved complete state -> {out}")
    print(f"  Next: python scripts/test_phase5.py")

if __name__ == "__main__":
    asyncio.run(main())
