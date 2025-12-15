import httpx
from langchain_core.tools import tool
from typing import Union

IFIXIT_BASE = "https://www.ifixit.com/api/2.0"

@tool
def find_device(query: str) -> str:
    """
    Find device name from user text using iFixit API.
    Endpoint: GET https://www.ifixit.com/api/2.0/search/{QUERY}?filter=device
    Converts user text like 'my ps5 broke' into database key like 'PlayStation 5'.
    """
    try:
        url = f"{IFIXIT_BASE}/search/{query}?filter=device"
        response = httpx.get(url, timeout=10.0)
        
        if response.status_code != 200:
            return f"Error: iFixit API returned status {response.status_code}"
        
        data = response.json()
        return _cleanup_search_results(data)
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


def _cleanup_search_results(raw: dict) -> str:
    """
    CLEANUP FUNCTION: Strip metadata from search results.
    Returns only device names and IDs to save tokens.
    """
    if not raw.get("results"):
        return "No devices found. Try a different search term."
    
    results = raw.get("results", [])[:5]  # Limit to top 5 results
    cleaned = []
    
    for item in results:
        device_name = item.get("title", "Unknown")
        device_url = item.get("url", "")
        cleaned.append(f"- {device_name} (URL: {device_url})")
    
    return "Found devices:\n" + "\n".join(cleaned)


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
