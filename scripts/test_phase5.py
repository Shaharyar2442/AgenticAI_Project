"""
Test Phase 5 — Edit Agent + State Manager.
Tests intent classification, edit planning, and state versioning.
Usage: python scripts/test_phase5.py
"""
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    from agents.edit_agent.intent_classifier import classify_intent
    from agents.edit_agent.planner import plan_edit
    from state_manager.state_manager import StateManager

    print(f"{'='*60}")
    print(f"  PHASE 5: EDIT AGENT + STATE MANAGER TEST")
    print(f"{'='*60}")

    # ---- Part A: Intent Classification ----
    print(f"\n--- Part A: Intent Classification ---\n")
    test_queries = [
        "Make scene 2 darker",
        "Change the narrator's voice to a whisper",
        "Add epic background music to scene 1",
        "Remove all subtitles",
        "Speed up the last scene",
        "Change the setting to underwater",
        "Make the video black and white",
        "Regenerate the entire script",
        "Add a sad tone to the music",
        "Make the narrator speak faster",
        "Add a fade-in transition to scene 1",
        "Change the protagonist's hair to red",
    ]

    results = []
    for i, query in enumerate(test_queries, 1):
        print(f"  [{i:2d}/12] \"{query}\"")
        start = time.time()
        intent = await classify_intent(query)
        elapsed = time.time() - start
        plan = plan_edit(intent)
        print(f"         -> target={intent.target:12s} intent={intent.intent:25s} "
              f"scope={intent.scope:10s} phases={plan['phases_to_rerun']} ({elapsed:.1f}s)")
        results.append({
            "query": query,
            "target": intent.target,
            "intent": intent.intent,
            "scope": intent.scope,
            "phases": plan["phases_to_rerun"],
        })

    # ---- Part B: State Manager ----
    print(f"\n--- Part B: State Manager ---\n")

    sm = StateManager()

    # Save versions
    print(f"  Saving 3 test versions...")
    sm.snapshot(1, {"status": "phase1_done", "title": "Original generation"}, [],)
    print(f"    v1 saved (original)")
    sm.snapshot(2, {"status": "complete", "title": "After edit: darken scene 2"}, [],)
    print(f"    v2 saved (after edit)")
    sm.snapshot(3, {"status": "complete", "title": "After edit: add BGM"}, [],)
    print(f"    v3 saved (after BGM)")

    # List history
    history = sm.history()
    print(f"\n  Version history ({len(history)} entries):")
    for v in history:
        print(f"    v{v['version']}: {v['created_at']} - {v['description']}")

    # Diff
    diff = sm.get_diff(1, 3)
    print(f"\n  Diff v1 -> v3:")
    for change in diff.get("changes", []):
        print(f"    {change['field']}: \"{change['old_summary']}\" -> \"{change['new_summary']}\"")

    # Revert
    reverted = sm.revert(1)
    print(f"\n  Reverted to v1: {reverted}")

    # Latest
    latest = sm.get_latest()
    print(f"  Latest version number: {latest}")

    # Save results
    os.makedirs("data/temp", exist_ok=True)
    out = "data/temp/test_edit_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved classification results -> {out}")

    print(f"\n{'='*60}")
    print(f"  Phase 5 tests complete!")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
