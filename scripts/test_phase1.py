"""
Test Phase 1 only — Story Generation.
Usage: python scripts/test_phase1.py
"""
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    from agents.story_agent.agent import generate_story

    prompt = "A young astronaut discovers a hidden ocean on Mars"
    print(f"[Phase 1] Generating story for: '{prompt}'")
    print(f"  Using LLM to create structured story...\n")

    start = time.time()
    story = await generate_story(prompt)
    elapsed = time.time() - start

    print(f"\n{'='*60}")
    print(f"  Title:      {story.title}")
    print(f"  Genre:      {story.genre}")
    print(f"  Synopsis:   {story.synopsis}")
    print(f"  Time:       {elapsed:.1f}s")
    print(f"{'='*60}")

    print(f"\n  Characters ({len(story.characters)}):")
    for c in story.characters:
        print(f"    {c.id}: {c.name} ({c.role})")
        print(f"      Voice: {c.voice_description}")
        print(f"      Look:  {c.visual_description[:80]}...")

    print(f"\n  Scenes ({len(story.scenes)}):")
    for s in story.scenes:
        print(f"    {s.scene_id}: {s.title}")
        print(f"      Mood: {s.mood} | Setting: {s.setting[:60]}...")
        for d in s.dialogue:
            print(f"      [{d.character_id}] ({d.emotion}) \"{d.text}\"")
        if s.narration:
            print(f"      [narration] \"{s.narration[:80]}...\"")

    os.makedirs("data/temp", exist_ok=True)
    out = "data/temp/test_story.json"
    with open(out, "w") as f:
        json.dump(story.model_dump(), f, indent=2)
    print(f"\n  Saved -> {out}")
    print(f"  Next: python scripts/test_phase2.py")

if __name__ == "__main__":
    asyncio.run(main())
