# 🎬 AgenticAI — AI-Powered Animated Video Generation System
> From Prompt to Polished Short Film — End-to-End with LLM Agents

**Course:** Agentic AI | **FAST NUCES Islamabad** | **Semester Project 2026**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://langchain-ai.github.io/langgraph/)
[![Tests](https://img.shields.io/badge/Tests-101%20passing-brightgreen)](tests/)

---

## 📌 Project Overview

This system accepts a single natural-language prompt and autonomously produces a complete short animated video — including story, dialogue, character voices, visual scenes, and final composited output — with **zero manual creative intervention**.

The pipeline is orchestrated by LLM agents across **5 phases**, each independently testable and modular:

| Phase | Description | Grade Weight |
|---|---|---|
| Phase 1 | Story & Script Generation (LangGraph + Gemini) | 15% |
| Phase 2 | Audio Generation (edge-TTS + BGM auto-download) | 15% |
| Phase 3 | Video Composition (Pollinations.ai + FFmpeg + SadTalker) | 20% |
| Phase 4 | Full-Stack Web Interface (FastAPI + React + WebSocket) | 10% |
| Phase 5 | Intelligent Edit Agent + Undo System (LangGraph + SQLite) | 20% |

---

## 🏗️ System Architecture

```
User Prompt
    │
    ▼
┌─────────────────────────────────────────────┐
│           Phase 1 — Story Agent              │
│  LLM → StoryOutput { scenes[], characters[] }│
└─────────────────────┬───────────────────────┘
                      │  StoryOutput JSON
                      ▼
┌─────────────────────────────────────────────┐
│           Phase 2 — Audio Agent              │
│  TTS per character + BGM → TimingManifest    │
└─────────────────────┬───────────────────────┘
                      │  TimingManifest + .wav files
                      ▼
┌─────────────────────────────────────────────┐
│           Phase 3 — Video Agent              │
│  Image Gen + Ken Burns + LipSync → MP4       │
└─────────────────────┬───────────────────────┘
                      │  final_output.mp4
                      ▼
┌─────────────────────────────────────────────┐
│    Phase 4 — FastAPI Backend + React UI      │
│  WebSocket progress + Video preview + Edit   │
└─────────────────────┬───────────────────────┘
                      │  Edit queries
                      ▼
┌─────────────────────────────────────────────┐
│    Phase 5 — LangGraph Edit Agent            │
│  Classify → Plan → Execute → Snapshot        │
│  MemorySaver checkpointer for multi-turn     │
└─────────────────────────────────────────────┘
```

All phases communicate through a **shared `PipelineState` object** — a central Pydantic model passed forward, updated, and versioned by each phase.

---

## 🧰 Technology Stack

| Layer | Technology | Why Chosen |
|---|---|---|
| LLM / Agents | Google Gemini 2.0 Flash + LangGraph | Fast, free tier, structured output |
| LLM Fallback | Groq (LLaMA 3 8B) | Low-latency fallback when Gemini is slow |
| TTS | edge-tts (Microsoft Neural voices) | Free, high-quality, no API key needed |
| BGM | yt-dlp (royalty-free YouTube) | Auto-downloads on demand, no manual setup |
| Image Generation | Pollinations.ai | Free, no API key, stable REST API |
| Lip Sync | SadTalker | Open-source, runs locally |
| Video Composition | FFmpeg + MoviePy 1.0.3 | Industry standard, full control |
| Backend | FastAPI + Uvicorn | Async, WebSocket support |
| Frontend | React + Vite | Fast HMR, modern tooling |
| State Store | SQLite (append-only log) | Simple, portable, no server needed |
| Schema Validation | Pydantic v2 | Strict JSON schema enforcement |
| Agent Graph | LangGraph StateGraph | Multi-node, checkpointed edit agent |
| Testing | pytest + pytest-asyncio | 101 tests across all 5 phases |

---

## ⚙️ Prerequisites

Before starting, ensure you have:

| Tool | Version | Check Command |
|---|---|---|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| FFmpeg | Any recent | `ffmpeg -version` |
| Git | Any | `git --version` |

> **FFmpeg must be on your system PATH.** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add the `bin/` folder to PATH.

---

## 🚀 Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/Shaharyar2442/AgenticAI_Project.git
cd AgenticAI_Project
```

### 2. Create and activate virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
pip install moviepy==1.0.3   # must be exactly this version (v2 has breaking API changes)
pip install facexlib yacs yt-dlp
```

### 4. Configure environment variables
```bash
# Copy the template
cp .env.example .env
```

Then open `.env` and fill in your keys:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
GEMINI_MODEL=gemini-2.0-flash
GROQ_MODEL=llama3-8b-8192
SADTALKER_PATH=./SadTalker
```

- 🔑 **Gemini API key** (free): https://aistudio.google.com/
- 🔑 **Groq API key** (free): https://console.groq.com/

### 5. Install frontend dependencies
```bash
cd frontend
npm install
cd ..
```

### 6. SadTalker setup (optional — enables lip sync)
If you skip this, the pipeline still works using **static portrait fallback**.
```bash
git clone https://github.com/OpenTalker/SadTalker.git
cd SadTalker
pip install -r requirements.txt
# Download model checkpoints per SadTalker README
cd ..
```

> **Windows fix already applied:** `KMP_DUPLICATE_LIB_OK=TRUE` is set at the top of `run_cli.py`, so you don't need to set it manually.

---

## ▶️ Running the Application

### Option A — CLI (Recommended for testing)
```bash
python run_cli.py "A young astronaut discovers a hidden ocean on Mars"
```

With a custom session name:
```bash
python run_cli.py "Two rival chefs compete in a haunted restaurant" --session my_session
```

Output video saved to:
```
data/outputs/video/<session_id>/final_output.mp4
```

### Option B — Full Web Application

**Terminal 1 — Backend:**
```bash
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open browser at: **http://localhost:3000**

---

## 🗂️ Shared JSON Schema

All phases communicate through a single shared `PipelineState` object defined in `shared/schemas/pipeline.py`. This is the central data contract — every phase reads from it and writes back to it.

```json
{
  "session_id": "cli_test",
  "version": 3,
  "story": {
    "title": "Ocean of Stars",
    "characters": [
      { "id": "char_01", "name": "Zara", "role": "protagonist",
        "voice_description": "young female, hopeful",
        "visual_description": "astronaut with auburn hair" }
    ],
    "scenes": [
      { "scene_id": "scene_01", "setting": "Mars surface at dawn",
        "mood": "mysterious", "visual_prompt": "vast red desert...",
        "dialogue": [], "duration_hint": 15 }
    ]
  },
  "timing_manifest": {
    "segments": [
      { "scene_id": "scene_01", "character_id": "char_01",
        "audio_file": "data/outputs/audio/cli_test/scene_01_char_01_0.wav",
        "start_ms": 0, "end_ms": 4200, "type": "dialogue" }
    ]
  },
  "scene_images": { "scene_01": "data/outputs/images/cli_test/scene_01.png" },
  "character_portraits": { "char_01": "data/outputs/images/cli_test/char_01_portrait.png" },
  "final_video_path": "data/outputs/video/cli_test/final_output.mp4"
}
```

---

## 🎨 Pipeline Phases — Detailed

### Phase 1 — Story & Script Generation
- **Input:** Free-text natural language prompt
- **Process:** LangGraph agent → Gemini LLM → structured JSON story with narrative arc (intro → conflict → climax → resolution)
- **Output:** `StoryOutput` Pydantic model — validated JSON with scenes, characters, dialogue
- **Fallback:** Groq (LLaMA 3) if Gemini fails
- **Guarantees:** Min 3 scenes, min 2 characters, unique IDs, schema validation

### Phase 2 — Audio Generation
- **Input:** `StoryOutput` from Phase 1
- **Process:**
  - TTS synthesis via `edge-tts` using character-specific Microsoft Neural voices
  - Voice matched to character personality (deep male, young female, narrator, etc.)
  - BGM selected by scene mood → auto-downloaded via `yt-dlp` if not cached
  - SRT subtitle file generated per scene
- **Output:** `.wav` files per dialogue line + `TimingManifest` Pydantic model

### Phase 3 — Video Composition
- **Input:** `StoryOutput` + `TimingManifest` from Phase 2
- **Process:**
  - Scene background images generated via Pollinations.ai (1920×1080)
  - Character portrait images generated (512×512)
  - Ken Burns animation (zoom-in, zoom-out, pan-left, pan-right, pan-up) via FFmpeg
  - SadTalker lip sync per dialogue segment (with static portrait fallback)
  - Character overlaid on background during dialogue time windows
  - Audio merged, subtitles burned (Arial font forced on Windows)
  - All scenes concatenated via MoviePy
- **Output:** `final_output.mp4`

### Phase 4 — Web Interface
- **Backend:** FastAPI with 5 REST endpoints + 1 WebSocket endpoint
- **Frontend:** React + Vite with prompt input, live progress indicator, video player, edit input, version history panel
- **Real-time:** WebSocket broadcasts per-phase progress as it happens

### Phase 5 — Intelligent Edit Agent (LangGraph)
- **Architecture:** LangGraph `StateGraph` with 3 nodes: classify → plan → execute
- **Checkpointer:** `MemorySaver` for per-session reasoning state persistence
- **Intent classification:** LLM classifies free-text query into structured `EditIntent`
- **Targeted re-runs:** Only affected phases are re-run (e.g., audio change = re-run Phase 2+3 only)
- **Versioning:** SQLite append-only log — every state snapshot is permanently preserved
- **Undo:** Full revert to any previous version including asset files

---

## ✏️ Edit Agent — Supported Commands (12 Types Tested)

| Example Query | Target | Intent | Action |
|---|---|---|---|
| "Change voice tone to whisper" | audio | change_voice_tone | Re-run TTS with tone parameter |
| "Make scene 2 darker" | video_frame | change_lighting | Apply lighting filter |
| "Add epic background music" | audio | add_bgm | Overlay new BGM track |
| "Remove all subtitles" | video | remove_subtitles | Recompose without subtitle burn |
| "Speed up the last scene" | video | change_speed | Adjust FFmpeg atempo |
| "Change character hair to red" | video_frame | regenerate_character | Re-generate character portrait |
| "Regenerate the entire script" | script | regenerate_script | Re-invoke Phase 1 |
| "Make it black and white" | video_frame | apply_filter | OpenCV grayscale filter |
| "Add sad tone to the music" | audio | change_bgm_mood | Swap BGM track by mood |
| "Change the setting to underwater" | script | change_setting | Re-run story with new setting |
| "Make the narrator speak faster" | audio | change_speech_rate | Adjust TTS rate parameter |
| "Add a fade-in transition to scene 1" | video | add_transition | FFmpeg transition parameter |

---

## 🧪 Running Tests

### Unit tests (all phases — offline, no API key needed):
```bash
python -m pytest tests/unit/ -v --timeout=30
```

### Edit intent classifier tests (requires Gemini API key):
```bash
python -m pytest agents/edit_agent/tests/ -v --timeout=60
```

### All tests together:
```bash
python -m pytest tests/unit/ agents/edit_agent/tests/ -v --timeout=60
```

### Expected results:
```
Phase 1 — Story schemas        : 17 tests  ✅
Phase 2 — Audio, TTS, BGM, SRT : 21 tests  ✅
Phase 3 — Ken Burns, FFmpeg    : 18 tests  ✅
Phase 5 — Edit, State, Filters : 32 tests  ✅
Intent classifier (12 queries) : 12 tests  ✅
─────────────────────────────────────────
Total                          : 101 passed, 0 failed
```

---

## 📁 Project Structure

```
AgenticAI_Project/
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
├── .gitignore                    # Excludes .env, data/, __pycache__, etc.
├── run_cli.py                    # CLI entry point (KMP fix applied here)
│
├── shared/
│   ├── schemas/
│   │   ├── story.py              # Character, Scene, DialogueLine, StoryOutput
│   │   ├── audio.py              # AudioSegment, SceneTiming, TimingManifest
│   │   ├── video.py              # VideoScene, CompositionConfig
│   │   ├── edit.py               # EditIntent (intent, target, scope, parameters)
│   │   └── pipeline.py           # PipelineState — master shared state
│   └── config.py                 # Central config loaded from .env
│
├── mcp/                          # MCP Tool Abstraction Layer
│   ├── base_tool.py              # BaseTool abstract class
│   ├── tool_registry.py          # Tool registration & discovery
│   ├── tool_executor.py          # Dynamic tool execution
│   └── tools/
│       ├── llm_tools/            # text_generator, json_structurer
│       ├── audio_tools/          # tts_tool, bgm_tool, audio_merger
│       ├── vision_tools/         # image_gen_tool, image_edit_tool, style_transfer
│       ├── video_tools/          # ffmpeg_tool, compositor_tool, subtitle_tool
│       └── system_tools/         # file_tool, state_tool, logger_tool
│
├── agents/
│   ├── orchestrator/             # LangGraph workflow — chains all phases
│   ├── story_agent/              # Phase 1 — LLM story generation
│   ├── audio_agent/              # Phase 2 — TTS + BGM synthesis
│   ├── video_agent/              # Phase 3 — Image gen + FFmpeg composition
│   └── edit_agent/               # Phase 5 — LangGraph edit StateGraph
│       ├── agent.py              # StateGraph: classify→plan→execute
│       ├── intent_classifier.py  # LLM-based intent classifier
│       ├── planner.py            # Maps intents to phases to re-run
│       ├── executor.py           # Executes edits via MCP tools
│       └── tests/
│           └── test_intent_classifier.py  # 12 parametrized edit queries
│
├── backend/
│   ├── app.py                    # FastAPI application
│   ├── routes/api.py             # REST endpoints
│   ├── services/session.py       # In-memory session store
│   └── websocket/handler.py      # WebSocket progress broadcaster
│
├── frontend/
│   ├── package.json
│   └── src/
│       ├── App.jsx               # Main React UI
│       └── index.css
│
├── state_manager/
│   ├── storage.py                # SQLite append-only version log
│   ├── snapshot.py               # Asset snapshot & file restore
│   ├── history.py                # Version diff summaries
│   └── state_manager.py          # Unified facade
│
├── tests/
│   ├── conftest.py               # KMP fix + project root import
│   └── unit/
│       ├── test_phase1_story.py  # 17 schema tests
│       ├── test_phase2_audio.py  # 21 audio, TTS, BGM, SRT tests
│       ├── test_phase3_video.py  # 18 Ken Burns, FFmpeg, fallback tests
│       ├── test_phase4_backend.py # FastAPI endpoint tests
│       └── test_phase5_edit.py   # 32 edit agent & state tests
│
└── assets/
    └── bgm/                      # BGM auto-downloaded at runtime via yt-dlp
```

---

## 🔑 API Endpoints

| Method | Endpoint | Request Body | Description |
|---|---|---|---|
| `POST` | `/api/generate` | `{ "prompt": "..." }` | Start full pipeline |
| `GET` | `/api/status/{session_id}` | — | Poll pipeline status |
| `POST` | `/api/edit` | `{ "session_id": "...", "query": "..." }` | Apply edit command |
| `GET` | `/api/versions/{session_id}` | — | List all state versions |
| `POST` | `/api/revert/{version}` | `{ "session_id": "..." }` | Revert to version |
| `WS` | `/ws/progress/{session_id}` | — | Real-time progress stream |

---

## ⚠️ Known Issues & Workarounds

| Issue | Root Cause | Workaround Applied |
|---|---|---|
| SadTalker OpenMP crash on Windows | PyTorch + SadTalker both load libiomp5 | `KMP_DUPLICATE_LIB_OK=TRUE` set at top of `run_cli.py` |
| FFmpeg subtitle font failure on Windows | System font-lookup fails for non-system fonts | `FontName=Arial` forced in `force_style` FFmpeg filter |
| moviepy v2 breaking API changes | v2 renamed core APIs | Pinned to `moviepy==1.0.3` in requirements |
| numpy `VisibleDeprecationWarning` in SadTalker | SadTalker not updated for numpy 2.x | Replaced with `DeprecationWarning` in `preprocess.py` |
| BGM files missing on first run | Files not committed to repo (too large) | `BGMTool` auto-downloads via `yt-dlp` on first run |
| Pollinations.ai network timeouts | Free API under load | 5 retries with exponential backoff + 120s timeout |
| `between()` FFmpeg parsing on Windows | Single-quote shell escaping issues | Replaced with `gte(t,x)*lte(t,y)` math expression |
| FFmpeg overlay using `H` variable | Not a valid FFmpeg overlay variable | Replaced with `main_h` everywhere |

---

## 🔄 State Versioning — How It Works

```
Initial Pipeline Run      │  Edit #1                │  Edit #2
─────────────────────     │  ───────────────────     │  ──────────────
Phase 1 → snapshot(v1)    │  pre-edit snapshot(v3)   │  pre-edit snapshot(v5)
Phase 2 → snapshot(v2)    │  execute edit            │  execute edit
Phase 3 → snapshot(v3)    │  post-edit snapshot(v4)  │  post-edit snapshot(v6)
```

- **Undo v1:** `/api/revert/1` — restores Phase 1 story JSON + all assets
- **Undo v3:** `/api/revert/3` — restores original video before any edits
- No version is ever deleted — fully append-only SQLite log

---

## 👥 Team Contributions

| Member | Primary Phase | Key Responsibilities |
|---|---|---|
| Member 1 | Phase 1 + 2 | Story agent, prompt engineering, Pydantic schemas, TTS, BGM, timing manifest |
| Member 2 | Phase 3 | Pollinations.ai image gen, FFmpeg Ken Burns, A/V sync, MP4 composition |
| Member 3 | Phase 4 + 5 | FastAPI backend, React frontend, WebSocket, LangGraph edit agent, undo system |
| Member 4 | Phase 5 | OpenCV image filters, FFmpeg editing tools, SQLite version management |

All members jointly contributed to: shared JSON schema design, integration testing, and the final presentation.

---

## 📄 License

This project is developed for academic purposes at **FAST NUCES Islamabad** as part of the Agentic AI course (Spring 2026). Not for commercial use.