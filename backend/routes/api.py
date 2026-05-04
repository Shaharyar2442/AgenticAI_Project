"""
API Routes — generate, edit, revert, versions.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from agents.orchestrator.workflow import run_pipeline
from agents.edit_agent.agent import handle_edit
from state_manager.state_manager import StateManager
from shared.schemas.pipeline import PipelineState
from shared.config import OUTPUTS_DIR
from backend.services.session import sessions
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()
state_mgr = StateManager()


def _make_video_url(abs_path: str) -> Optional[str]:
    """Convert an absolute Windows video path to a URL-safe relative path.
    
    e.g.  D:\\...\\data\\outputs\\video\\session_X\\final_output.mp4
          -> /outputs/video/session_X/final_output.mp4
    """
    if not abs_path:
        return None
    # Normalise separators
    norm = abs_path.replace("\\", "/")
    outputs_norm = str(OUTPUTS_DIR).replace("\\", "/")
    # Strip everything up to and including the outputs dir
    if outputs_norm in norm:
        rel = norm.split(outputs_norm)[-1].lstrip("/")
        return f"/outputs/{rel}"
    # Fallback: try splitting on 'outputs/'
    if "outputs/" in norm:
        rel = norm.split("outputs/")[-1]
        return f"/outputs/{rel}"
    return None


class GenerateRequest(BaseModel):
    prompt: str
    session_id: str = "default"

class EditRequest(BaseModel):
    query: str
    session_id: str = "default"

class RevertRequest(BaseModel):
    session_id: str = "default"


@router.post("/generate")
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    """Start video generation pipeline."""
    session_id = req.session_id
    sessions[session_id] = {"status": "starting", "progress": []}

    async def _run():
        try:
            async def progress_cb(msg):
                sessions[session_id]["progress"].append(msg)
                sessions[session_id]["status"] = msg.get("status", "running")
                # Broadcast to WebSocket if connected
                from backend.websocket.handler import broadcast
                await broadcast(session_id, msg)

            state = await run_pipeline(req.prompt, session_id, progress_cb)
            sessions[session_id]["state"] = state.model_dump()
            sessions[session_id]["status"] = "complete"
        except Exception as e:
            sessions[session_id]["status"] = "error"
            sessions[session_id]["error"] = str(e)
            logger.error(f"Pipeline error: {e}")

    background_tasks.add_task(_run)
    return {"session_id": session_id, "status": "started"}


@router.get("/status/{session_id}")
async def get_status(session_id: str):
    """Get pipeline status — returns state with a URL-safe video_url field."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = dict(sessions[session_id])  # shallow copy

    # Inject a clean video_url alongside the raw path so the frontend
    # doesn't need to do any path manipulation
    if session.get("state") and session["state"].get("final_video_path"):
        raw_path = session["state"]["final_video_path"]
        session["video_url"] = _make_video_url(raw_path)

    return session


@router.post("/edit")
async def edit(req: EditRequest, background_tasks: BackgroundTasks):
    """Apply an edit to the current pipeline state."""
    session_id = req.session_id
    if session_id not in sessions or "state" not in sessions[session_id]:
        raise HTTPException(400, "No active generation to edit")

    state = PipelineState(**sessions[session_id]["state"])

    async def _edit():
        try:
            sessions[session_id]["status"] = "editing"
            from backend.websocket.handler import broadcast
            await broadcast(session_id, {"phase": "edit", "message": f"Processing: {req.query}"})
            updated = await handle_edit(req.query, state, session_id)
            sessions[session_id]["state"] = updated.model_dump()
            sessions[session_id]["status"] = "complete"
            await broadcast(session_id, {"phase": "edit", "message": "Edit complete", "status": "complete"})
        except Exception as e:
            sessions[session_id]["status"] = "error"
            sessions[session_id]["error"] = str(e)

    background_tasks.add_task(_edit)
    return {"session_id": session_id, "status": "editing"}


@router.get("/versions/{session_id}")
async def get_versions(session_id: str):
    """Get version history for a session."""
    try:
        versions = state_mgr.history()  # returns [{version, created_at, description}, ...]
        return {"versions": versions}
    except Exception as e:
        logger.warning(f"Could not load versions: {e}")
        return {"versions": []}



@router.post("/revert/{version}")
async def revert(version: int, req: RevertRequest):
    """Revert to a specific version."""
    try:
        state_json = state_mgr.revert(version)
        sessions[req.session_id] = {
            "status": "complete",
            "state": state_json,
            "progress": [{"phase": "revert", "message": f"Reverted to v{version}"}]
        }
        return {"status": "reverted", "version": version}
    except KeyError:
        raise HTTPException(404, f"Version {version} not found")
