"""
Node 3: List Guides

Retrieves all available repair guides for the selected device.
"""

from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ..agent import AgentState

logger = logging.getLogger(__name__)


async def list_guides_node(state: "AgentState") -> "AgentState":
    """
    List available repair guides for the device.
    
    Uses ONLY the canonical device name from selected_device.
    NEVER passes guide titles or troubleshooting phrases to iFixit API.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with available_guides
    """
    from ..ifixit_tools import get_ifixit_tools
    
    state.setdefault("tool_status", [])
    state["tool_status"].append("Fetching available repair guides...")
    
    # Check if we have a selected device
    if not state.get("selected_device"):
        state["available_guides"] = None
        state.setdefault("tool_status", []).append("No device selected")
        logger.warning("No device selected for listing guides")
        state["ifixit_found"] = False
        # Early return to allow fallback
        return state
    
    ifixit = get_ifixit_tools()
    device_title = (state.get("selected_device") or {}).get("title")
    
    if not device_title:
        state["available_guides"] = None
        state.setdefault("tool_status", []).append("Device has no title")
        logger.warning("Selected device has no title")
        state["ifixit_found"] = False
        return state
    
    # CRITICAL: Clean device title to remove any guide-like suffixes
    # iFixit category API only accepts device names, not guide titles
    cleaned_title = device_title
    for invalid_suffix in [
        " Troubleshooting", " Repair", " Replacement", " Disassembly",
        " Teardown", " Won't Work", " Not Working", " Doesn't Work"
    ]:
        if cleaned_title.endswith(invalid_suffix):
            cleaned_title = cleaned_title.replace(invalid_suffix, "")
            logger.info(f"Cleaned device title: '{device_title}' -> '{cleaned_title}'")
    
    result = await ifixit.list_guides(cleaned_title)
    
    if result and result.get("guides"):
        state["available_guides"] = result["guides"]
        state["tool_status"].append(f"Found {len(result['guides'])} repair guides")
        logger.info(f"Found {len(result['guides'])} guides for {cleaned_title}")
    else:
        state["available_guides"] = None
        state["tool_status"].append("No repair guides available")
        logger.warning(f"No guides found for: {cleaned_title}")
    
    return state
