"""
Node 6: Fallback Web Search

Fallback node that searches the web when iFixit doesn't have results.
Only executed if device not found, no guides available, or no guide selected.
"""

from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ..agent import AgentState

logger = logging.getLogger(__name__)


async def fallback_search_node(state: "AgentState") -> "AgentState":
    """
    Fallback web search (only if iFixit fails).
    
    DISABLED: Per user requirements, we only use iFixit results.
    """
    state.setdefault("tool_status", [])
    state["tool_status"].append("Search only limited to iFixit (web fallback disabled)")
    logger.info("Skipping web search fallback as only iFixit is allowed.")
    state["repair_steps"] = None
    return state
