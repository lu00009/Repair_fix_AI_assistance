import httpx
from langchain_core.tools import tool
from typing import Union

IFIXIT_BASE = "https://www.ifixit.com/api/2.0"

@tool
def find_device(query: str) -> str:
    """
    Find device name or guides from user text using iFixit API.
    Searches without filter if query looks like a how-to question.
    Endpoint: GET https://www.ifixit.com/api/2.0/search/{QUERY}
    Converts user text like 'my ps5 broke' into database key or returns relevant guides.
    """
    try:
        # Check if query is a how-to/guide question (not device-specific)
        query_lower = query.lower()
        is_howto_query = any(word in query_lower for word in [
            'how to', 'how do i', 'start up', 'boot', 'recovery mode', 
            'safe mode', 'reset', 'restore', 'install', 'setup'
        ])
        
        # Use no filter for how-to queries, device filter for device queries
        filter_param = "" if is_howto_query else "?filter=device"
        url = f"{IFIXIT_BASE}/search/{query}{filter_param}"
        response = httpx.get(url, timeout=10.0)
        
        if response.status_code != 200:
            return f"Error: iFixit API returned status {response.status_code}"
        
        data = response.json()
        return _cleanup_search_results(data, is_guide_search=is_howto_query)
    except Exception as e:
        return f"Error searching iFixit: {str(e)}"

@tool
def list_guides(device_title: str) -> str:
    """
    List available repair guides for a device.
    Endpoint: GET https://www.ifixit.com/api/2.0/wikis/CATEGORY/{DEVICE_TITLE}
    Returns all repair topics (Fan, Drive, Motherboard) for the device.
    """
    try:
        url = f"{IFIXIT_BASE}/wikis/CATEGORY/{device_title}"
        response = httpx.get(url, timeout=10.0)
        
        if response.status_code == 404:
            return "Status: Not Found - No guides available for this device"
        
        if response.status_code != 200:
            return f"Error: iFixit API returned status {response.status_code}"
        
        data = response.json()
        return _cleanup_guides_list(data)
    except Exception as e:
        return f"Error fetching guides: {str(e)}"

@tool
def get_guide(guide_id: int) -> str:
    """
    Get detailed repair steps for a specific guide.
    Endpoint: GET https://www.ifixit.com/api/2.0/guides/{GUIDE_ID}
    Returns step-by-step instructions with text and image URLs.
    """
    try:
        url = f"{IFIXIT_BASE}/guides/{guide_id}"
        response = httpx.get(url, timeout=10.0)
        
        if response.status_code == 404:
            return "Status: Not Found - Guide does not exist"
        
        if response.status_code != 200:
            return f"Error: iFixit API returned status {response.status_code}"
        
        data = response.json()
        return _cleanup_guide_details(data)
    except Exception as e:
        return f"Error fetching guide: {str(e)}"


def _cleanup_search_results(raw: dict, is_guide_search: bool = False) -> str:
    """
    CLEANUP FUNCTION: Strip metadata from search results.
    Returns device names or guide titles with URLs to save tokens.
    """
    if not raw.get("results"):
        return "No results found. Try a different search term."
    
    results = raw.get("results", [])[:5]  # Limit to top 5 results
    cleaned = []
    
    for item in results:
        title = item.get("title", "Unknown")
        url = item.get("url", "")
        item_type = item.get("dataType", "")  # Can be "device", "guide", etc.
        
        # For guide searches, indicate if it's a guide
        if is_guide_search and item_type == "guide":
            cleaned.append(f"- [GUIDE] {title} (URL: {url})")
        else:
            cleaned.append(f"- {title} (URL: {url})")
    
    header = "Found guides:\n" if is_guide_search else "Found devices:\n"
    return header + "\n".join(cleaned)


def _cleanup_guides_list(raw: dict) -> str:
    """
    CLEANUP FUNCTION: Strip metadata from guides list.
    Returns only guide titles and IDs to save tokens.
    """
    guides = raw.get("guides", [])
    
    if not guides:
        return "No repair guides found for this device."
    
    cleaned = []
    for guide in guides[:10]:  # Limit to 10 guides
        title = guide.get("title", "Unknown")
        guide_id = guide.get("guideid", "N/A")
        difficulty = guide.get("difficulty", "Unknown")
        cleaned.append(f"- [{guide_id}] {title} (Difficulty: {difficulty})")
    
    return "Available repair guides:\n" + "\n".join(cleaned)


def _cleanup_guide_details(raw: dict) -> str:
    """
    CLEANUP FUNCTION: Strip metadata from guide details.
    Returns only text instructions and image URLs to save tokens.
    Removes: IDs, revisions, author info, metadata.
    """
    title = raw.get("title", "Unknown Guide")
    introduction = raw.get("introduction", "")
    difficulty = raw.get("difficulty", "Unknown")
    time_required = raw.get("time_required", "Unknown")
    
    result = f"**{title}**\n"
    result += f"Difficulty: {difficulty} | Time: {time_required}\n\n"
    
    if introduction:
        result += f"Introduction: {introduction}\n\n"
    
    # Extract steps (text and images only)
    steps = raw.get("steps", [])
    if not steps:
        return result + "No steps available."
    
    result += "**Repair Steps:**\n\n"
    
    for idx, step in enumerate(steps, 1):
        step_title = step.get("title", f"Step {idx}")
        result += f"**Step {idx}: {step_title}**\n"
        
        # Get step text lines
        lines = step.get("lines", [])
        for line in lines:
            text = line.get("text", "")
            if text:
                result += f"- {text}\n"
        
        # Get step images (only URLs, no metadata)
        media = step.get("media", {})
        if media.get("type") == "image":
            image_url = media.get("data", {}).get("standard", "")
            if image_url:
                # Render as Markdown image so the frontend displays it inline
                result += f"  ![Step {idx} image]({image_url})\n"
        
        result += "\n"
    
    # Extract tools needed
    tools = raw.get("tools", [])
    if tools:
        result += "**Tools Required:**\n"
        for tool in tools:
            tool_name = tool.get("text", "Unknown tool")
            result += f"- {tool_name}\n"
    
    return result
