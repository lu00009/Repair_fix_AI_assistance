"""
Node 5: Fetch Guide

Fetches detailed repair guide with step-by-step instructions and images.
"""

from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ..agent import AgentState

logger = logging.getLogger(__name__)


async def fetch_guide_node(state: "AgentState") -> "AgentState":
    """
    Fetch detailed repair guide with steps and images.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with repair_steps
    """
    from ..ifixit_tools import get_ifixit_tools
    
    state.setdefault("tool_status", [])
    state["tool_status"].append("Fetching repair instructions...")
    
    # Check if a guide was selected
    selected_guide = state.get("selected_guide")
    if not selected_guide or not isinstance(selected_guide, dict) or not selected_guide.get("guideid"):
        state["repair_steps"] = None
        state.setdefault("tool_status", []).append("No guide selected to fetch")
        logger.warning("Cannot fetch guide - no guide selected")
        state["ifixit_found"] = False
        return state
    
    ifixit = get_ifixit_tools()
    guide_id = selected_guide["guideid"]
    result = await ifixit.fetch_repair_guide(guide_id)
    
    # Validate and CLEANUP result according to CLEANUP FUNCTION rules
    if result and result.get("found"):
        # Only return required fields: title, steps (text + images), tools
        cleaned = {
            "title": result.get("title"),
            "steps": [],
            "tools": result.get("tools") or []
        }
        for s in result.get("steps", []) or []:
            cleaned_step = {
                "text": s.get("text") or "",
                "images": s.get("images") or []
            }
            cleaned["steps"].append(cleaned_step)

        state["repair_steps"] = cleaned
        state.setdefault("tool_status", []).append(f"Retrieved {len(cleaned.get('steps', []))} repair steps")
        logger.info(f"Fetched guide {guide_id} with {len(cleaned.get('steps', []))} steps")
    else:
        state["repair_steps"] = None
        state.setdefault("tool_status", []).append("Failed to fetch repair guide")
        logger.error(f"Failed to fetch guide {guide_id}")
        state["ifixit_found"] = False
    
    return state
