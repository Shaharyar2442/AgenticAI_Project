import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # Fix OpenMP conflict (SadTalker + PyTorch)

import asyncio
import argparse
from agents.orchestrator.workflow import run_pipeline
import logging

# Set logging level if needed
logging.basicConfig(level=logging.WARNING)

async def main():
    parser = argparse.ArgumentParser(description="Run Agentic AI Video Pipeline directly from CLI.")
    parser.add_argument("prompt", type=str, help="The natural language prompt for the story")
    parser.add_argument("--session", type=str, default="cli_test", help="Session ID (folder name)")
    args = parser.parse_args()

    async def progress_cb(msg):
        # Print progress clearly to the terminal
        phase = msg.get('phase', '---').upper()
        message = msg.get('message', '')
        print(f"[{phase}] {message}")

    print(f"\n==================================================")
    print(f"Starting Agentic AI Pipeline: '{args.prompt}'")
    print(f"Session ID: {args.session}")
    print(f"==================================================\n")
    
    try:
        state = await run_pipeline(args.prompt, args.session, progress_cb)
        print(f"\n==================================================")
        print(f"✅ PIPELINE FINISHED SUCCESSFULLY!")
        print(f"🎬 Final Video Path: {state.final_video_path}")
        print(f"==================================================\n")
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
