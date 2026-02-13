"""
Node 4: Select Guide

Logic-only node that selects the most relevant guide based on user intent.
No LLM generation - uses simple keyword matching.
"""

from typing import TYPE_CHECKING
import logging

from ..utils import debug_print

logger = logging.getLogger(__name__)


async def select_guide_node(state: "AgentState") -> "AgentState":
    """
    Select the most relevant guide based on user intent.
    
    Logic-only node - matches user query to guide title/subject.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with selected_guide
    """
    state.setdefault("tool_status", [])
    state["tool_status"].append("Selecting most relevant guide...")
    
    guides = state.get("available_guides") or []
    # Prefer original query for keyword matching to catch symptoms like 'disc drive'
    canonical_query = (state.get("query") or state.get("user_query") or state.get("normalized_query") or "").lower()
    debug_print(f"DEBUG: select_guide_node with {len(guides)} guides. Query: {canonical_query}")
    
    # Simple relevance scoring
    best_guide = None
    best_score = 0
    
    # Check if guides list is valid
    if not guides:
        state["selected_guide"] = None
        state.setdefault("tool_status", []).append("No guides available to select from")
        logger.warning("No guides available in state")
        state["ifixit_found"] = False
        return state
    
    # Synonym mapping for common parts
    synonyms = {
        "disc": ["optical", "drive", "disk", "dvd", "cd", "disk"],
        "drive": ["optical", "disc", "disk", "dvd", "cd"],
        "screen": ["display", "lcd", "glass", "digitizer", "panel"],
        "display": ["screen", "lcd", "glass", "digitizer", "panel"],
        "battery": ["power", "cell"],
        "power": ["battery", "supply", "psu", "adapter"],
        "fan": ["cooler", "cooling", "thermal", "overheating"],
        "overheat": ["fan", "cooler", "thermal", "paste"],
    }

    for guide in guides:
        score = 0
        title_lower = guide["title"].lower()
        subject_lower = guide.get("subject", "").lower()
        
        # Check for keyword matches
        query_words = canonical_query.split()
        for word in query_words:
            if len(word) < 3: continue
            
            # Direct match
            if word in title_lower:
                score += 3
            if word in subject_lower:
                score += 1

            # Synonym match
            if word in synonyms:
                for syn in synonyms[word]:
                    if syn in title_lower:
                        score += 2
                    if syn in subject_lower:
                        score += 1
        
        if score > best_score:
            best_score = score
            best_guide = guide
            debug_print(f"DEBUG: New best guide: {guide['title']} with score {score}")
    
    # If no good match, select first repair guide
    if best_guide is None and guides:
        best_guide = guides[0]
    
    state["selected_guide"] = best_guide
    
    if best_guide:
        state["tool_status"].append(f"Selected: {best_guide['title']}")
        logger.info(f"Selected guide: {best_guide['title']}")
    else:
        state["tool_status"].append("No suitable guide found")
        logger.warning("No guide could be selected")
    
    return state
