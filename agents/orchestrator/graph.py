"""
Orchestrator Graph — LangGraph state graph wiring all agents together.
"""
from langgraph.graph import StateGraph, END
from agents.orchestrator.state import OrchestratorState
from agents.story_agent.agent import generate_story
from agents.audio_agent.agent import generate_audio
from agents.video_agent.agent import generate_video
from shared.schemas.pipeline import PipelineState
import logging

logger = logging.getLogger(__name__)


async def story_node(state: OrchestratorState) -> OrchestratorState:
    """Phase 1: Generate story."""
    state["current_phase"] = "phase1"
    state["progress_messages"].append("Generating story...")
    story = await generate_story(state["user_prompt"])
    state["story_json"] = story.model_dump()
    state["status"] = "phase1_done"
    state["progress_messages"].append(f"Story '{story.title}' generated")
    return state


async def audio_node(state: OrchestratorState) -> OrchestratorState:
    """Phase 2: Generate audio."""
    state["current_phase"] = "phase2"
    state["progress_messages"].append("Generating audio...")
    from shared.schemas.story import StoryOutput
    story = StoryOutput(**state["story_json"])
    manifest = await generate_audio(story, state["session_id"])
    state["timing_manifest_json"] = manifest.model_dump()
    state["status"] = "phase2_done"
    state["progress_messages"].append(f"Audio generated: {manifest.total_duration_ms}ms")
    return state


async def video_node(state: OrchestratorState) -> OrchestratorState:
    """Phase 3: Generate video."""
    state["current_phase"] = "phase3"
    state["progress_messages"].append("Compositing video...")
    from shared.schemas.story import StoryOutput
    from shared.schemas.audio import TimingManifest
    pipeline_state = PipelineState(
        user_prompt=state["user_prompt"],
        story=StoryOutput(**state["story_json"]),
        timing_manifest=TimingManifest(**state["timing_manifest_json"]),
    )
    final_path = await generate_video(pipeline_state, state["session_id"])
    state["final_video_path"] = final_path
    state["scene_images"] = pipeline_state.scene_images
    state["character_portraits"] = pipeline_state.character_portraits
    state["scene_videos"] = pipeline_state.scene_videos
    state["status"] = "complete"
    state["progress_messages"].append(f"Video complete: {final_path}")
    return state


def build_graph() -> StateGraph:
    """Build the LangGraph state graph."""
    graph = StateGraph(OrchestratorState)
    graph.add_node("story", story_node)
    graph.add_node("audio", audio_node)
    graph.add_node("video", video_node)
    graph.add_edge("story", "audio")
    graph.add_edge("audio", "video")
    graph.add_edge("video", END)
    graph.set_entry_point("story")
    return graph
