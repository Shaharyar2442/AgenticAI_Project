"""
Story Agent — LangGraph agent that generates a structured story from a user prompt.
Uses the JSON structurer tool to enforce StoryOutput schema.
"""
from shared.schemas.story import StoryOutput
from shared.config import GOOGLE_API_KEY, GROQ_API_KEY, GEMINI_MODEL, GROQ_MODEL
from agents.story_agent.planner import SYSTEM_PROMPT, STORY_GENERATION_PROMPT
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


async def generate_story(user_prompt: str) -> StoryOutput:
    """Generate a complete story from a user prompt using structured LLM output."""
    prompt = STORY_GENERATION_PROMPT.format(user_prompt=user_prompt)

    # Try Gemini first with structured output
    try:
        logger.info("Trying Gemini for story generation...")
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.8,
        )
        structured_llm = llm.with_structured_output(StoryOutput)
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]
        result = await structured_llm.ainvoke(messages)
        logger.info(f"Story generated: '{result.title}' with {len(result.scenes)} scenes")
        return result

    except Exception as e:
        logger.warning(f"Gemini failed ({e}), trying Groq fallback...")

    # Groq fallback with prompt-based JSON
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage, HumanMessage
        import json

        schema_json = json.dumps(StoryOutput.model_json_schema(), indent=2)
        json_prompt = (
            f"{prompt}\n\n"
            f"You MUST respond with valid JSON matching this exact schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Respond with ONLY the JSON object, no markdown fences, no explanation."
        )

        llm = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0.8)
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=json_prompt)]
        response = await llm.ainvoke(messages)

        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]

        result = StoryOutput.model_validate_json(content.strip())
        logger.info(f"Story generated (Groq): '{result.title}' with {len(result.scenes)} scenes")
        return result

    except Exception as e2:
        logger.error(f"Both LLMs failed for story generation: {e2}")
        raise RuntimeError(f"Story generation failed: {e2}")
