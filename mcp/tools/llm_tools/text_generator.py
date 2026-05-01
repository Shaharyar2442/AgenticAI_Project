"""
Text Generator Tool — wraps LLM calls (Gemini Flash / Groq fallback).
"""
from mcp.base_tool import BaseTool
from shared.config import GOOGLE_API_KEY, GROQ_API_KEY, GEMINI_MODEL, GROQ_MODEL
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TextGeneratorTool(BaseTool):
    name = "text_generator"
    description = "Generate text using LLM. Supports free-form and structured JSON output."

    async def execute(self, prompt: str, system_prompt: str = "", **kwargs) -> Dict[str, Any]:
        """Generate text from an LLM. Tries Gemini first, falls back to Groq."""
        try:
            return await self._try_gemini(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Gemini failed ({e}), falling back to Groq")
            try:
                return await self._try_groq(prompt, system_prompt)
            except Exception as e2:
                logger.error(f"Both LLMs failed. Gemini: {e}, Groq: {e2}")
                return {"success": False, "error": f"All LLMs failed: {e2}"}

    async def _try_gemini(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.8,
        )
        messages = []
        if system_prompt:
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
        else:
            from langchain_core.messages import HumanMessage
            messages = [HumanMessage(content=prompt)]
        result = await llm.ainvoke(messages)
        return {"success": True, "content": result.content}

    async def _try_groq(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model=GROQ_MODEL,
            api_key=GROQ_API_KEY,
            temperature=0.8,
        )
        messages = []
        if system_prompt:
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
        else:
            from langchain_core.messages import HumanMessage
            messages = [HumanMessage(content=prompt)]
        result = await llm.ainvoke(messages)
        return {"success": True, "content": result.content}
