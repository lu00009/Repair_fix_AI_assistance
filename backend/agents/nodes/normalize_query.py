"""
Node 1: Normalize Query

Converts casual user language to canonical device names for better search results.
Example: "my ps5 fan is loud" -> "PlayStation 5 fan noise"
"""

from typing import TYPE_CHECKING
from langchain_core.messages import HumanMessage
import logging

if TYPE_CHECKING:
    from ..agent import AgentState

logger = logging.getLogger(__name__)


async def normalize_query_node(state: "AgentState") -> "AgentState":
    """
    Normalize user query for better device matching.
    
    Extracts ONLY the canonical device name (no symptoms/issues).
    This device name is IMMUTABLE and used for ALL iFixit API calls.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with ifixit_device (immutable device name)
    """
    from ..agent import get_llm

    # Ensure tool_status list exists to avoid KeyError when running in server
    state.setdefault("tool_status", [])
    state["tool_status"].append("Normalizing query...")

    llm = get_llm()

    # Determine the user query robustly from possible state fields
    query_val = state.get("query") or state.get("user_query")
    if not query_val:
        # Try to extract the last human message from `messages`
        msgs = state.get("messages") or []
        for m in reversed(msgs):
            # prefer objects with .content
            if hasattr(m, "content") and getattr(m, "content"):
                query_val = getattr(m, "content")
                break
            # fallback to string representation
            if isinstance(m, str) and m.strip():
                query_val = m
                break
    if not query_val:
        query_val = ""
    # Ensure canonical state key exists for downstream nodes
    state.setdefault("query", query_val)

    prompt = f"""Extract ONLY the device model/name from this repair query.

Query: {query_val}

CRITICAL RULES:
- Extract ONLY the device name (no symptoms, issues, or problems)
- For laptops, prefer series name over specific model numbers
- Never include words like "Troubleshooting", "Repair", "Won't Work", etc.
- Output must be a clean device category name only

Examples:
- "my ps5 fan is loud" -> "PlayStation 5"
- "iphone 12 battery dying fast" -> "iPhone 12"
- "HP Spectre x360 is slow" -> "HP Spectre x360"
- "dell xps 15 screen flickering" -> "Dell XPS 15"
- "macbook pro 2020 won't turn on" -> "MacBook Pro 2020"

Output ONLY the device name (nothing else):"""
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    device_name = response.content.strip()
    
    # Store canonical query for downstream nodes per STATE HANDLING RULES
    # The canonical field is `user_query` and must contain the normalized device name
    state["user_query"] = device_name
    # Also keep legacy fields for backward compatibility
    state["ifixit_device"] = device_name
    state["normalized_query"] = device_name
    
    state["tool_status"].append(f"Device: {device_name}")

    logger.info(f"Extracted device name: '{device_name}' from query: '{query_val}'")
    
    return state
