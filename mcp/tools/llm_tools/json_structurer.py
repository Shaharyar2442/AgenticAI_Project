"""
JSON Structurer Tool — forces LLM output into a Pydantic schema.
Uses Gemini's native JSON mode or falls back to prompt-based extraction.
"""
from mcp.base_tool import BaseTool
from shared.config import GOOGLE_API_KEY, GROQ_API_KEY, GEMINI_MODEL, GROQ_MODEL
from typing import Any, Dict, Type
from pydantic import BaseModel
import json
import logging

logger = logging.getLogger(__name__)


class JsonStructurerTool(BaseTool):
    name = "json_structurer"
    description = "Generate structured JSON output from LLM enforced by a Pydantic schema."

    async def execute(self, prompt: str, schema_class: Type[BaseModel],
                      system_prompt: str = "", **kwargs) -> Dict[str, Any]:
        """Generate JSON output conforming to the given Pydantic schema."""
        try:
            return await self._try_gemini_structured(prompt, schema_class, system_prompt)
        except Exception as e:
            logger.warning(f"Gemini structured output failed ({e}), trying Groq with prompt-based JSON")
            try:
                return await self._try_groq_json(prompt, schema_class, system_prompt)
            except Exception as e2:
                return {"success": False, "error": str(e2)}

    async def _try_gemini_structured(self, prompt: str, schema_class: Type[BaseModel],
                                      system_prompt: str) -> Dict[str, Any]:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.8,
        )
        structured_llm = llm.with_structured_output(schema_class)
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        result = await structured_llm.ainvoke(messages)
        return {"success": True, "data": result.model_dump(), "parsed": result}

    async def _try_groq_json(self, prompt: str, schema_class: Type[BaseModel],
                              system_prompt: str) -> Dict[str, Any]:
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage, HumanMessage

        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        json_prompt = (
            f"{prompt}\n\n"
            f"You MUST respond with valid JSON matching this schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Respond with ONLY the JSON, no markdown, no explanation."
        )

        llm = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0.8)
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=json_prompt))

        result = await llm.ainvoke(messages)
        content = result.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
        parsed = schema_class.model_validate_json(content)
        return {"success": True, "data": parsed.model_dump(), "parsed": parsed}
