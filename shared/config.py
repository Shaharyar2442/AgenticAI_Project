"""
Central configuration — loads from .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------- Paths ----------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUTS_DIR = DATA_DIR / "outputs"
TEMP_DIR = DATA_DIR / "temp"
STATE_VERSIONS_DIR = DATA_DIR / "state_versions"
BGM_DIR = PROJECT_ROOT / "assets" / "bgm"

# Ensure dirs exist
for d in [OUTPUTS_DIR, TEMP_DIR, STATE_VERSIONS_DIR, OUTPUTS_DIR / "audio", OUTPUTS_DIR / "images", OUTPUTS_DIR / "video"]:
    d.mkdir(parents=True, exist_ok=True)

# ---------- API Keys ----------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ---------- LLM Config ----------
GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ---------- TTS Config ----------
DEFAULT_VOICE = "en-US-AriaNeural"

# ---------- Video Config ----------
GLOBAL_FPS = 25  # Must be 25 everywhere — zoompan, overlay, and final concat
VIDEO_RESOLUTION = "1920x1080"
VIDEO_CODEC = "libx264"

# ---------- Pollinations Config ----------
POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt"
IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080
PORTRAIT_SIZE = 512
MAX_IMAGE_RETRIES = 3
