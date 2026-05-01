"""
Test Phase 2 only — Audio Generation.
Loads story from Phase 1 output.
Usage: python scripts/test_phase2.py
"""
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    from shared.schemas.story import StoryOutput
    from agents.audio_agent.agent import generate_audio
    from mcp.tools.audio_tools.tts_tool import match_voice

    # Load story from Phase 1
    story_path = "data/temp/test_story.json"
    if not os.path.exists(story_path):
        print(f"[ERROR] No story found at {story_path}")
        print(f"  Run Phase 1 first: python scripts/test_phase1.py")
        return

    with open(story_path) as f:
        story = StoryOutput(**json.load(f))
    print(f"[Phase 2] Loaded story: '{story.title}' ({len(story.scenes)} scenes)")

    # Show voice assignments
    print(f"\n  Voice assignments:")
    for c in story.characters:
        voice = match_voice(c.voice_description)
        print(f"    {c.id} ({c.name}): \"{c.voice_description}\" -> {voice}")

    # Count total lines
    total_lines = sum(len(s.dialogue) + (1 if s.narration else 0) for s in story.scenes)
    print(f"\n  Total audio lines to generate: {total_lines}")
    print(f"  Generating TTS audio...\n")

    start = time.time()
    manifest = await generate_audio(story, session_id="test")
    elapsed = time.time() - start

    print(f"\n{'='*60}")
    print(f"  Audio generation complete in {elapsed:.1f}s")
    print(f"  Total duration: {manifest.total_duration_ms}ms ({manifest.total_duration_ms/1000:.1f}s)")
    print(f"{'='*60}")

    print(f"\n  Per-scene breakdown:")
    for st in manifest.scene_durations:
        exists = os.path.exists(st.audio_file)
        size_kb = os.path.getsize(st.audio_file) / 1024 if exists else 0
        print(f"    {st.scene_id}: {st.measured_duration_ms}ms -> {st.audio_file.split(os.sep)[-1]} ({size_kb:.0f} KB)")

    print(f"\n  All segments ({len(manifest.segments)}):")
    for seg in manifest.segments:
        print(f"    [{seg.scene_id}] {seg.type:10s} {seg.character_id or 'N/A':8s} "
              f"{seg.start_ms:6d}-{seg.end_ms:6d}ms  {os.path.basename(seg.audio_file)}")

    # List generated files
    audio_dir = "data/outputs/audio/test"
    if os.path.exists(audio_dir):
        files = os.listdir(audio_dir)
        print(f"\n  Generated files in {audio_dir}/ ({len(files)} files):")
        for f in sorted(files):
            size = os.path.getsize(os.path.join(audio_dir, f))
            print(f"    {f:40s} {size/1024:6.0f} KB")

    # Save manifest
    out = "data/temp/test_manifest.json"
    with open(out, "w") as f:
        json.dump(manifest.model_dump(), f, indent=2)
    print(f"\n  Saved -> {out}")
    print(f"  Next: python scripts/test_phase3.py")

if __name__ == "__main__":
    asyncio.run(main())
