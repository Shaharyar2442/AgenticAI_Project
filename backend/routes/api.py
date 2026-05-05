"""
API Routes — two-stage generate, accept/regen characters, edit, revert, versions.
All version history is session-scoped.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from agents.orchestrator.workflow import generate_story_and_characters, continue_pipeline
from agents.edit_agent.agent import handle_edit
from state_manager.state_manager import StateManager
from shared.schemas.pipeline import PipelineState
from shared.config import OUTPUTS_DIR
from backend.services.session import sessions
from typing import Optional
import logging, os, random

logger = logging.getLogger(__name__)
router = APIRouter()
state_mgr = StateManager()


def _make_url(abs_path: str) -> Optional[str]:
    if not abs_path: return None
    norm = abs_path.replace("\\", "/")
    outputs_norm = str(OUTPUTS_DIR).replace("\\", "/")
    if outputs_norm in norm:
        return f"/outputs/{norm.split(outputs_norm)[-1].lstrip('/')}"
    if "outputs/" in norm:
        return f"/outputs/{norm.split('outputs/')[-1]}"
    return None

def _make_urls(d: dict) -> dict:
    return {k: _make_url(v) for k, v in d.items() if _make_url(v)}


class GenerateRequest(BaseModel):
    prompt: str
    session_id: str = "default"

class ContinueRequest(BaseModel):
    session_id: str = "default"

class EditRequest(BaseModel):
    query: str
    session_id: str = "default"

class RevertRequest(BaseModel):
    session_id: str = "default"


# ── Stage 1: Story + Portraits (pauses for review) ──

@router.post("/generate")
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    session_id = req.session_id
    sessions[session_id] = {"status": "starting", "progress": []}

    async def _run():
        try:
            async def progress_cb(msg):
                sessions[session_id]["progress"].append(msg)
                sessions[session_id]["status"] = msg.get("status", "running")
                from backend.websocket.handler import broadcast
                await broadcast(session_id, msg)

            state = await generate_story_and_characters(req.prompt, session_id, progress_cb)
            sessions[session_id]["state"] = state.model_dump()
            sessions[session_id]["status"] = "characters_ready"
        except Exception as e:
            sessions[session_id]["status"] = "error"
            sessions[session_id]["error"] = str(e)
            logger.error(f"Stage 1 error: {e}")

    background_tasks.add_task(_run)
    return {"session_id": session_id, "status": "started"}


# ── Stage 2: Continue after character approval ──

@router.post("/continue")
async def continue_gen(req: ContinueRequest, background_tasks: BackgroundTasks):
    session_id = req.session_id
    if session_id not in sessions or "state" not in sessions[session_id]:
        raise HTTPException(400, "No story generated yet")

    state = PipelineState(**sessions[session_id]["state"])
    sessions[session_id]["status"] = "running"

    async def _run():
        try:
            async def progress_cb(msg):
                sessions[session_id]["progress"].append(msg)
                sessions[session_id]["status"] = msg.get("status", "running")
                from backend.websocket.handler import broadcast
                await broadcast(session_id, msg)

            updated = await continue_pipeline(state, session_id, progress_cb)
            sessions[session_id]["state"] = updated.model_dump()
            sessions[session_id]["status"] = "complete"
        except Exception as e:
            sessions[session_id]["status"] = "error"
            sessions[session_id]["error"] = str(e)
            logger.error(f"Stage 2 error: {e}")

    background_tasks.add_task(_run)
    return {"session_id": session_id, "status": "continuing"}


# ── Status ──

@router.get("/status/{session_id}")
async def get_status(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    session = dict(sessions[session_id])
    if session.get("state"):
        s = session["state"]
        if s.get("final_video_path"):
            session["video_url"] = _make_url(s["final_video_path"])
        if s.get("character_portraits"):
            session["portrait_urls"] = _make_urls(s["character_portraits"])
        if s.get("scene_images"):
            session["scene_image_urls"] = _make_urls(s["scene_images"])
    return session


# ── Regenerate single character portrait ──

@router.post("/regenerate-character/{session_id}/{char_id}")
async def regenerate_character(session_id: str, char_id: str):
    """Regenerate a character portrait (synchronous for immediate feedback)."""
    if session_id not in sessions or "state" not in sessions[session_id]:
        raise HTTPException(400, "No active generation")

    state_data = sessions[session_id]["state"]
    story = state_data.get("story")
    if not story:
        raise HTTPException(400, "No story yet")

    char = next((c for c in story.get("characters", []) if c["id"] == char_id), None)
    if not char:
        raise HTTPException(404, f"Character {char_id} not found")

    from mcp.tools.vision_tools.image_gen_tool import ImageGenTool
    gen = ImageGenTool()
    img_dir = str(OUTPUTS_DIR / "images" / session_id)
    os.makedirs(img_dir, exist_ok=True)

    result = await gen.execute(
        prompt=char["visual_description"],
        output_path=os.path.join(img_dir, f"{char_id}_portrait.png"),
        image_type="portrait",
        seed=random.randint(1, 9999)
    )
    if "character_portraits" not in state_data:
        state_data["character_portraits"] = {}
    state_data["character_portraits"][char_id] = result["image_path"]
    sessions[session_id]["state"] = state_data

    return {
        "status": "regenerated",
        "char_id": char_id,
        "portrait_url": _make_url(result["image_path"]),
    }


# ── Edit ──

@router.post("/edit")
async def edit(req: EditRequest, background_tasks: BackgroundTasks):
    session_id = req.session_id
    if session_id not in sessions or "state" not in sessions[session_id]:
        raise HTTPException(400, "No active generation to edit")

    state = PipelineState(**sessions[session_id]["state"])

    async def _edit():
        try:
            sessions[session_id]["status"] = "editing"
            from backend.websocket.handler import broadcast
            await broadcast(session_id, {"phase": "edit", "message": f"Processing: {req.query}", "status": "running"})
            updated = await handle_edit(req.query, state, session_id)
            sessions[session_id]["state"] = updated.model_dump()
            sessions[session_id]["status"] = "complete"
            await broadcast(session_id, {"phase": "edit", "message": "Edit complete", "status": "complete"})
        except Exception as e:
            sessions[session_id]["status"] = "error"
            sessions[session_id]["error"] = str(e)
            logger.error(f"Edit error: {e}")

    background_tasks.add_task(_edit)
    return {"session_id": session_id, "status": "editing"}


# ── Versions (session-scoped) ──

@router.get("/versions/{session_id}")
async def get_versions(session_id: str):
    try:
        versions = state_mgr.history(session_id=session_id)
        return {"versions": versions}
    except Exception as e:
        logger.warning(f"Could not load versions: {e}")
        return {"versions": []}


@router.post("/revert/{version}")
async def revert(version: int, req: RevertRequest):
    try:
        state_json = state_mgr.revert(version, session_id=req.session_id)
        sessions[req.session_id] = {
            "status": "complete",
            "state": state_json,
            "progress": [{"phase": "revert", "message": f"Reverted to v{version}"}]
        }
        return {"status": "reverted", "version": version}
    except KeyError:
        raise HTTPException(404, f"Version {version} not found")
