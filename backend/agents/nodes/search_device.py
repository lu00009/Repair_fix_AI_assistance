"""
Node 2: Search Device

Searches iFixit API for the device based on normalized query.
"""

from typing import TYPE_CHECKING
import logging

from ..utils import debug_print

logger = logging.getLogger(__name__)


async def search_device_node(state: "AgentState") -> "AgentState":
    """
    Search for device on iFixit.
    
    Uses ONLY the immutable ifixit_device name (no symptoms/issues).
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with selected_device
    """
    from ..ifixit_tools import get_ifixit_tools
    
    # Ensure tool_status exists
    state.setdefault("tool_status", [])
    state["tool_status"].append("Searching iFixit for device...")
    
    # CRITICAL: Use only the canonical device name for iFixit API
    # Per rules, prefer `state['user_query']`, fall back to legacy fields.
    device_name = state.get("user_query") or state.get("normalized_query") or state.get("ifixit_device") or state.get("query")
    
    if not device_name:
        logger.error("No user_query in state - normalization failed")
        state["selected_device"] = None
        state["ifixit_found"] = False
        state.setdefault("tool_status", []).append("Error: Missing user query")
        # Indicate missing data so pipeline can trigger fallback
        state["error"] = "Missing user query"
        return state
    
    # Clean device name by stripping common repair keywords that iFixit search fails on
    cleaned_name = device_name
    import re
    cleaned_name = re.sub(r"\b(back|panel|replacement|disassembly|battery|fan|replace|repair|screen|display|lcd|glass)\b", "", device_name, flags=re.I).strip()
    if cleaned_name:
        device_name = cleaned_name
        debug_print(f"DEBUG: Cleaned device name for search: {device_name}")
        logger.info(f"Cleaned device name for search: {device_name}")
    
    debug_print(f"DEBUG: Starting search_device_node for {device_name}")
    ifixit = get_ifixit_tools()
    result = await ifixit.search_devices(device_name)
    debug_print(f"DEBUG: search_devices result found: {bool(result and result.get('devices'))}")
    
    if result and result.get("devices"):
        # Select the first (most relevant) device
        state["selected_device"] = result["devices"][0]
        state["tool_status"].append(f"Found device: {state['selected_device']['title']}")
        logger.info(f"Device found: {state['selected_device']['title']}")
    else:
        state["selected_device"] = None
        state["tool_status"].append("No device found on iFixit")
        logger.warning(f"No device found for: {device_name}")
    
    return state
