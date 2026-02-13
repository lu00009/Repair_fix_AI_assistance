from types import SimpleNamespace
import re
import asyncio
from typing import Any, List

from langchain_core.messages import HumanMessage


from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

import logging
import time

logger = logging.getLogger(__name__)

class _GeminiLLM:
    def __init__(self):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            google_api_key=GEMINI_API_KEY
        )
    
    async def ainvoke(self, messages: List[Any]) -> Any:
        try:
            # First attempt with Gemini
            return await self.model.ainvoke(messages)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                logger.warning(f"Gemini Rate Limit (429) hit. Falling back to heuristic normalization. Error: {e}")
                
                # Heuristic Fallback
                prompt_content = ""
                if messages:
                    msg = messages[0]
                    prompt_content = msg.content if hasattr(msg, "content") else str(msg)
                
                device_name = self._heuristic_normalize(prompt_content)
                return SimpleNamespace(content=device_name)
            
            logger.error(f"Error in Gemini ainvoke: {e}")
            raise e

    def _heuristic_normalize(self, prompt: str) -> str:
        """Heuristic device name extraction used as fallback when LLM is unavailable."""
        # Extract the Query: line if present
        m = re.search(r"Query:\s*(.+)", prompt)
        q = m.group(1).strip() if m else prompt.strip()

        # Heuristic: attempt to capture brand+model phrases
        brands = [
            'lenovo', 'dell', 'hp', 'acer', 'asus', 'apple', 'macbook', 'iphone', 'ipad', 'samsung',
            'google', 'xiaomi', 'sony', 'microsoft', 'toshiba', 'lg', 'realme', 'playstation', 'ps[45]', 'xbox', 'nintendo'
        ]
        brand_pattern = r"(" + r"|".join(brands) + r")[\w\s\-0-9]{0,60}"
        bm = re.search(brand_pattern, q, flags=re.I)
        if bm:
            device_candidate = bm.group(0).strip()
            # cleanup trailing words like 'repair', 'replacement', etc.
            # remove common repair/part keywords and trailing filler
            device_candidate = re.sub(r"\b(repair|replacement|disassembly|fix|troubleshooting|screen|battery|fan|display|lcd|glass|disc drive|disk drive|joy-con|controller)\b.*$", "", device_candidate, flags=re.I).strip()
            if device_candidate:
                q = device_candidate

        # Heuristic cleanup: remove common repair/issue words and conversational filler
        q_clean = re.sub(r"\b(my|the|is|are|a|an|back|panel|replacement|disassembly|battery|fan|replace|repair|troubleshoot|troubleshooting|won't work|won't|not working|working|faulty|broken|fix|screen|display|lcd|glass|disc drive|disk drive|joy-con|controller)\b", "", q, flags=re.I)
        q_clean = re.sub(r"\s+"," ", q_clean).strip()

        # Prefer a short device name: take up to first 4 words
        parts = q_clean.split()
        device = " ".join(parts[:4]) if parts else q

        # Special case: normalize PS5 to PlayStation 5 for better iFixit matching
        if re.search(r"\bps5\b", device, flags=re.I):
            device = "PlayStation 5"
        elif re.search(r"\bps4\b", device, flags=re.I):
            device = "PlayStation 4"

        # Capitalize words in a reasonable way
        return device.title()

_llm_singleton = None

def get_llm() -> Any:
    """Return the Gemini LLM for normalization and other tasks."""
    global _llm_singleton
    if _llm_singleton is None:
        if GEMINI_API_KEY:
            _llm_singleton = _GeminiLLM()
        else:
            class _FallbackLLM:
                async def ainvoke(self, messages):
                    return SimpleNamespace(content="Unknown Device")
            _llm_singleton = _FallbackLLM()
    return _llm_singleton
