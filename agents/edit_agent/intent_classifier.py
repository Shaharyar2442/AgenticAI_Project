"""
Intent Classifier — uses LLM to classify edit queries into structured EditIntent.
"""
from shared.schemas.edit import EditIntent
from shared.config import GOOGLE_API_KEY, GROQ_API_KEY, GEMINI_MODEL, GROQ_MODEL
import json
import logging

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are an AI edit intent classifier for an animated video generation system.

Given a user's edit request, classify it into a structured intent.

Available targets: "audio", "video_frame", "video", "script"
Available intents:
- audio: change_voice_tone, add_bgm, change_bgm_mood, change_speech_rate, remove_bgm
- video_frame: apply_filter, regenerate_character, change_lighting
- video: remove_subtitles, add_transition, change_speed, add_subtitles
- script: change_setting, regenerate_script, change_dialogue, add_scene, remove_scene

Scope format: "all", "scene:scene_01", "character:char_01"

User request: "{query}"

Respond with ONLY valid JSON:
{{"intent": "...", "target": "...", "scope": "...", "parameters": {{}}}}"""


async def classify_intent(query: str) -> EditIntent:
    """Classify an edit query into a structured EditIntent."""
    prompt = CLASSIFICATION_PROMPT.format(query=query)

    # Try Gemini
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage
        llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GOOGLE_API_KEY, temperature=0.1)
        structured = llm.with_structured_output(EditIntent)
        result = await structured.ainvoke([HumanMessage(content=prompt)])
        logger.info(f"Classified: '{query}' -> {result.target}/{result.intent}")
        return result
    except Exception as e:
        logger.warning(f"Gemini classification failed: {e}")

    # Groq fallback
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage
        llm = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0.1)
        result = await llm.ainvoke([HumanMessage(content=prompt)])
        content = result.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
        parsed = EditIntent.model_validate_json(content.strip())
        logger.info(f"Classified (Groq): '{query}' -> {parsed.target}/{parsed.intent}")
        return parsed
    except Exception as e2:
        logger.error(f"Classification failed: {e2}")
        # Default fallback
        return EditIntent(intent="unknown", target="script", scope="all")
