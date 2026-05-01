"""
Orchestrator State — TypedDict for LangGraph state management.
"""
from typing import TypedDict, Optional, List, Dict, Any


class OrchestratorState(TypedDict):
    """State flowing through the orchestrator graph."""
    user_prompt: str
    session_id: str
    current_phase: str
    status: str
    error: Optional[str]
    story_json: Optional[Dict[str, Any]]
    timing_manifest_json: Optional[Dict[str, Any]]
    scene_images: Dict[str, str]
    character_portraits: Dict[str, str]
    scene_videos: Dict[str, str]
    final_video_path: Optional[str]
    version: int
    progress_messages: List[str]
