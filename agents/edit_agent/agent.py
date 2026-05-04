"""
Edit Agent — LangGraph implementation that classifies, plans, and executes edits on pipeline state.
Uses MemorySaver for cross-session reasoning state persistence.
"""
from typing import TypedDict, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from shared.schemas.pipeline import PipelineState
from shared.schemas.edit import EditIntent
from agents.edit_agent.intent_classifier import classify_intent
from agents.edit_agent.planner import plan_edit
from agents.edit_agent.executor import execute_edit
from state_manager.state_manager import StateManager
import logging

logger = logging.getLogger(__name__)
state_mgr = StateManager()

class EditAgentState(TypedDict):
    """The graph state for the edit agent."""
    query: str
    session_id: str
    pipeline_state: PipelineState
    intent: Optional[EditIntent]
    plan: Optional[Dict[str, Any]]
    updated_state: Optional[PipelineState]

# --- Nodes ---

async def classify_node(state: EditAgentState) -> EditAgentState:
    logger.info(f"[EditGraph] Classifying intent for query: '{state['query']}'")
    intent = await classify_intent(state["query"])
    return {"intent": intent}

def plan_node(state: EditAgentState) -> EditAgentState:
    logger.info(f"[EditGraph] Planning edit for intent: {state['intent'].intent}")
    plan = plan_edit(state["intent"])
    return {"plan": plan}

async def execute_node(state: EditAgentState) -> EditAgentState:
    logger.info(f"[EditGraph] Executing edit plan...")
    pipeline_state = state["pipeline_state"]
    intent = state["intent"]
    plan = state["plan"]
    session_id = state["session_id"]

    # Pre-edit snapshot
    asset_paths = list(pipeline_state.scene_images.values()) + list(pipeline_state.character_portraits.values())
    if pipeline_state.final_video_path:
        asset_paths.append(pipeline_state.final_video_path)
    state_mgr.snapshot(pipeline_state.version, pipeline_state.model_dump(), asset_paths)

    # Execute
    updated_state = await execute_edit(pipeline_state, intent, plan, session_id)

    # Post-edit snapshot
    new_assets = list(updated_state.scene_images.values()) + list(updated_state.character_portraits.values())
    if updated_state.final_video_path:
        new_assets.append(updated_state.final_video_path)
    state_mgr.snapshot(updated_state.version, updated_state.model_dump(), new_assets)

    return {"updated_state": updated_state}

# --- Graph Construction ---

builder = StateGraph(EditAgentState)
builder.add_node("classify", classify_node)
builder.add_node("plan", plan_node)
builder.add_node("execute", execute_node)

builder.set_entry_point("classify")
builder.add_edge("classify", "plan")
builder.add_edge("plan", "execute")
builder.add_edge("execute", END)

# Compile with checkpointer
memory = MemorySaver()
edit_app = builder.compile(checkpointer=memory)

# --- Wrapper for Backward Compatibility ---

async def handle_edit(query: str, state: PipelineState, session_id: str = "default") -> PipelineState:
    """Entry point compatible with the existing api.py routing."""
    initial_state = {
        "query": query,
        "session_id": session_id,
        "pipeline_state": state,
        "intent": None,
        "plan": None,
        "updated_state": None,
    }

    config = {"configurable": {"thread_id": session_id}}

    logger.info(f"Invoking LangGraph Edit Agent for session {session_id}")
    final_graph_state = await edit_app.ainvoke(initial_state, config=config)

    return final_graph_state["updated_state"]
