from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
import time
import json
import re

from backend.agents.state import AgentState
from backend.agents.tools_ifixit import find_device, list_guides, get_guide
from backend.agents.tools_search import web_search
from backend.core.config import GEMINI_API_KEY
from backend.models.usage import track_token_usage
import logging
from backend.agents.nodes.normalize_query import normalize_query_node
from backend.agents.nodes.search_device import search_device_node
from backend.agents.nodes.list_guides import list_guides_node
from backend.agents.nodes.select_guide import select_guide_node
from backend.agents.nodes.fetch_guide import fetch_guide_node
from backend.agents.nodes.fallback_search import fallback_search_node

# Model configured for streaming
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=GEMINI_API_KEY,
    streaming=True
)
import logging
import os

from .utils import debug_print

logger = logging.getLogger(__name__)


# Node 1..6 are provided as separate modules under backend.agents.nodes
# and are imported above. They replace the previous inline implementations.


# The ifixit-specific workflow is now split into modular nodes under
# `backend.agents.nodes`. The graph below wires them together.



# ==================== NODE 3: ROUTE RESULTS ====================
async def route_results(state: AgentState) -> AgentState:
    """Determine if iFixit found useful results by checking state keys."""
    debug_print("DEBUG: Entering route_results")
    # If an earlier node already flagged iFixit as found, trust it.
    if state.get("ifixit_found"):
        return {"ifixit_found": True}

    # Check for presence of structured results in specific keys
    repair_steps = state.get("repair_steps")
    available_guides = state.get("available_guides")
    selected_device = state.get("selected_device")

    if repair_steps and isinstance(repair_steps, dict) and repair_steps.get("steps"):
        return {"ifixit_found": True}
    
    if available_guides and isinstance(available_guides, list) and len(available_guides) > 0:
        return {"ifixit_found": True}
    
    if selected_device and isinstance(selected_device, dict) and selected_device.get("title"):
        return {"ifixit_found": True}

    # Fallback to checking the legacy ifixit_results list if present
    ifixit_results = state.get("ifixit_results", [])
    for result in ifixit_results:
        rtype = result.get("type", "").lower()
        raw_content = result.get("content", "")
        content = raw_content.lower()

        if result.get("type") == "error":
            continue

        if any(neg in content for neg in ["no results found", "not found", "status: not found"]):
            continue

        if rtype in ["guide_detail", "guides_list", "device_search"] and content.strip():
            return {"ifixit_found": True}

    return {"ifixit_found": False}


# ==================== NODE 4: WEB SEARCH FALLBACK ====================
async def web_search_fallback(state: AgentState) -> AgentState:
    """Search web only if iFixit found nothing.
    
    DISABLED: Per user requirements, we only use iFixit results.
    """
    return {"web_results": []}


# ==================== NODE 5: MANAGE CONTEXT ====================
async def manage_context(state: AgentState) -> AgentState:
    """Combine all results into structured context."""
    debug_print("DEBUG: Entering manage_context")
    ifixit_results = state.get("ifixit_results", [])
    web_results = state.get("web_results", [])
    ifixit_found = state.get("ifixit_found", False)
    
    # State-based results
    repair_steps = state.get("repair_steps")
    available_guides = state.get("available_guides")
    selected_device = state.get("selected_device")

    # Build combined context
    context_parts = []
    step_image = None
    
    # Add structured state results first
    if selected_device:
        title = selected_device.get("title", "Unknown Device")
        url = selected_device.get("url", "")
        context_parts.append(f"iFixit Search Found Device: {title} (URL: {url})")

    if available_guides:
        guides_text = "\n".join([f"- [{g.get('guideid')}] {g.get('title')} (Difficulty: {g.get('difficulty')})" for g in available_guides[:10]])
        context_parts.append(f"Available iFixit Guides:\n{guides_text}")

    if repair_steps:
        steps_text = []
        for idx, s in enumerate(repair_steps.get("steps", []), 1):
            txt = s.get("text", "").strip()
            imgs = s.get("images") or []
            img_md = f" ![{idx}]({imgs[0]})" if imgs and isinstance(imgs, list) else ""
            steps_text.append(f"Step {idx}: {txt}{img_md}")
            if not step_image and imgs:
                step_image = imgs[0] if isinstance(imgs, list) else imgs
        
        context_parts.append(f"Guide Details ({repair_steps.get('title')}):\n" + "\n".join(steps_text))

    # Fallback to legacy ifixit_results list
    for result in ifixit_results:
        content = result.get("content", "")
        context_parts.append(f"iFixit {result.get('type')}:\n{content}")
    
    combined_context = "\n\n".join(context_parts)
    
    debug_print(f"DEBUG: manage_context finished. context_parts: {len(context_parts)}, ifixit_found: {ifixit_found}, has_results: {len(context_parts) > 0 or ifixit_found}")
    return {
        "combined_context": combined_context,
        "has_results": len(context_parts) > 0 or ifixit_found,
        "step_image": step_image,
        "step_images": state.get('step_images') if state.get('step_images') else []
    }


# ==================== NODE 6: FORMAT MARKDOWN ====================
async def format_markdown(state: AgentState) -> AgentState:
    """Use LLM to format results into friendly markdown and include image if available."""
    user_query = state.get("user_query", "")
    combined_context = state.get("combined_context", "")
    has_results = state.get("has_results", False)
    repair = state.get("repair_steps")
    debug_print(f"DEBUG: Entering format_markdown. has_results: {has_results}, repair_steps present: {bool(repair and repair.get('steps'))}")
    
    if not has_results:
        return {
            "formatted_response": "I couldn't find any information about that. Could you try rephrasing your question?",
            "prompt_tokens": 0
        }

    # If we have structured repair steps present in state (from fetch_guide),
    # build a deterministic Markdown response matching the requested format
    repair = state.get("repair_steps")
    if repair and isinstance(repair, dict) and repair.get("steps"):
        title = repair.get("title", "Repair Guide")
        try:
            logger.info("format_markdown: using structured repair_steps (title=%s steps=%d)", title, len(repair.get('steps', [])))
        except Exception:
            pass
        # Remove specific model-number-like tokens (all caps/digits) if they are 5+ chars
        # but avoid removing common words like 'iPhone'
        title_clean = re.sub(r"\b[A-Z0-9]{5,}\b", "", title).strip()
        # collapse multiple spaces
        title_clean = re.sub(r"\s+", " ", title_clean)

        lines = []
        lines.append(f"## {title_clean}")
        lines.append("")
        steps = repair.get("steps", [])
        for idx, s in enumerate(steps, start=1):
            lines.append(f"### Step {idx}")
            text = (s.get("text") or "").strip()
            if text:
                # Use first paragraph
                first = text.split("\n\n")[0].strip()
                lines.append(first)
                lines.append("")
            
            # include images for this step using proper markdown syntax
            images = s.get("images") or []
            if isinstance(images, list):
                for im_idx, im in enumerate(images, start=1):
                    lines.append(f"![Step {idx} Image {im_idx}]({im})")
                    lines.append("")
            elif isinstance(images, str) and images:
                lines.append(f"![Step {idx} Image]({images})")
                lines.append("")

        tools = repair.get("tools", []) or []
        if tools:
            lines.append("### Tools Required")
            for t in tools:
                lines.append(f"- {t}")
            lines.append("")

        lines.append("What else can I help you with?")

        formatted = "\n".join(lines)
        return {"formatted_response": formatted, "prompt_tokens": 0}

    # Fallback to LLM formatting when no structured repair_steps present
    format_prompt = f"""You are a friendly, helpful repair assistant - like ChatGPT but specialized in device repairs. Your personality is warm, encouraging, and empathetic.

User asked: {user_query}

Tool Results:
{combined_context}

Instructions for your response:
1. START with empathy and acknowledgment of their problem (e.g., "Oh no, that's frustrating!" or "I can definitely help with that!")
2. Be conversational and natural - use contractions, casual language, and show personality
3. If iFixit has official guides, present them enthusiastically as the best solution
4. If only web results exist, acknowledge iFixit doesn't have a guide YET but you found helpful community tips
5. Format clearly with:
   - Friendly headings (not just "Step 1")
   - Bullet points for lists
   - Bold for important points
   - Emojis occasionally (💡 for tips, 🔧 for tools, ⚠️ for warnings)
6. Include "Pro Tips" or "What to try first" sections when relevant
7. End with "What else can I help with?" or offer next steps
8. If showing repair steps with images, format like: "**Step 1:** [instruction]" with image links
9. Keep tone positive and encouraging - repair is empowering!

Be helpful, friendly, and conversational like you're a knowledgeable friend helping them out:"""

    # Estimate prompt tokens
    prompt_tokens = len(format_prompt) // 4

    return {
        "format_prompt": format_prompt,
        "prompt_tokens": prompt_tokens
    }


# ==================== NODE 7: STREAM RESPONSE ====================
async def stream_response(state: AgentState) -> AgentState:
    """Stream the formatted response token-by-token."""
    formatted_response = state.get("formatted_response", "")
    format_prompt = state.get("format_prompt", "")
    debug_print(f"DEBUG: Entering stream_response. formatted_response len: {len(formatted_response)}, format_prompt len: {len(format_prompt)}")
    
    if formatted_response and (not format_prompt):
        debug_print("DEBUG: Already formatted, returning result directly")
        return {"formatted_response": formatted_response, "completion_tokens": 0}

    if not format_prompt:
        return {
            "formatted_response": "Unable to format response.",
            "completion_tokens": 0
        }
    
    try:
        # Stream response with retry logic
        full_response = ""
        async for chunk in _stream_with_retry([HumanMessage(content=format_prompt)]):
            if chunk.content:
                full_response += chunk.content
        
        # Estimate completion tokens
        completion_tokens = len(full_response) // 4
        
        return {
            "formatted_response": full_response,
            "completion_tokens": completion_tokens
        }
    except Exception as e:
        combined_context = state.get("combined_context", "")
        return {
            "formatted_response": f"Error formatting response: {str(e)}\n\nRaw results:\n{combined_context}",
            "completion_tokens": 0
        }


# ==================== NODE 8: USAGE ANALYTICS ====================
async def usage_analytics(state: AgentState) -> AgentState:
    """Track token usage for analytics."""
    user_id = state.get("user_id")
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)
    total_tokens = prompt_tokens + completion_tokens
    
    if user_id and total_tokens > 0:
        try:
            track_token_usage(user_id, total_tokens)
        except Exception as e:
            print(f"Failed to track usage: {str(e)}")
    
    return {"total_tokens": total_tokens}


# ==================== NODE 9: CHECKPOINT SAVE ====================
async def checkpoint_save(state: AgentState) -> AgentState:
    """Save final response to messages for conversation persistence."""
    formatted_response = state.get("formatted_response", "")
    step_image = state.get("step_image")
    
    if formatted_response:
        # Return messages and include step_image separately so callers (routes) can access it
        return {"messages": [AIMessage(content=formatted_response)], "step_image": step_image, "step_images": state.get('step_images', [])}
    
    return {"messages": [AIMessage(content="Sorry, I couldn't process that request.")]} 


# ==================== HELPER FUNCTIONS ====================
async def _stream_with_retry(messages, max_retries: int = 3, base_delay: float = 2.0):
    """Stream from Gemini with exponential backoff on 429 errors."""
    attempt = 0
    while True:
        try:
            async for chunk in model.astream(messages):
                if chunk.content:
                    yield chunk
            return
        except ChatGoogleGenerativeAIError as e:
            msg = str(e)
            if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                if attempt >= max_retries:
                    raise
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
                attempt += 1
                continue
            raise


def _extract_device_title(device_result: str) -> str:
    """Extract device title from iFixit device search result."""
    try:
        match = re.search(r'-\s*([^(]+)\s*\(URL:', device_result)
        if match:
            return match.group(1).strip()
        
        match = re.search(r'Device:\s*([^\n]+)', device_result)
        if match:
            return match.group(1).strip()
        
        if device_result.startswith('{') or device_result.startswith('['):
            data = json.loads(device_result)
            if isinstance(data, dict):
                return data.get('title', data.get('name', ''))
            elif isinstance(data, list) and len(data) > 0:
                return data[0].get('title', data[0].get('name', ''))
    except Exception:
        pass
    return ""


def _extract_guide_id(guides_result: str, user_query: str) -> str:
    """Extract the most relevant guide ID based on user query."""
    try:
        id_matches = re.findall(r'\[(\d+)\]', guides_result)
        
        if not id_matches:
            id_matches = re.findall(r'(?:ID|id):\s*(\d+)', guides_result)
        
        if id_matches:
            # Prioritize based on keywords
            if any(word in user_query for word in ['disc', 'drive', 'disk', 'dvd', 'cd', 'blu']):
                for match in re.finditer(r'\[(\d+)\][^\n]*(disc|drive|disk)', guides_result, re.IGNORECASE):
                    return match.group(1)
            
            if any(word in user_query for word in ['screen', 'display', 'lcd', 'glass']):
                for match in re.finditer(r'\[(\d+)\][^\n]*(screen|display|lcd)', guides_result, re.IGNORECASE):
                    return match.group(1)
            
            if 'batter' in user_query:
                for match in re.finditer(r'\[(\d+)\][^\n]*batter', guides_result, re.IGNORECASE):
                    return match.group(1)
            
            return id_matches[0]
    except Exception:
        pass
    return ""


# ==================== GRAPH CONSTRUCTION ====================
graph = StateGraph(AgentState)

# Add nodes: normalize -> search -> list -> select -> fetch -> route/format
graph.add_node("normalize_query", normalize_query_node)
graph.add_node("search_device", search_device_node)
graph.add_node("list_guides", list_guides_node)
graph.add_node("select_guide", select_guide_node)
graph.add_node("fetch_guide", fetch_guide_node)

# Keep the existing routing/formatting nodes
graph.add_node("route_results", route_results)
graph.add_node("web_search_fallback", web_search_fallback)
graph.add_node("fallback_search", fallback_search_node)
graph.add_node("manage_context", manage_context)
graph.add_node("format_markdown", format_markdown)
graph.add_node("stream_response", stream_response)
graph.add_node("usage_analytics", usage_analytics)
graph.add_node("checkpoint_save", checkpoint_save)

# Build the flow
graph.set_entry_point("normalize_query")
graph.add_edge("normalize_query", "search_device")
graph.add_edge("search_device", "list_guides")
graph.add_edge("list_guides", "select_guide")
graph.add_edge("select_guide", "fetch_guide")

# After fetching, route results to decide next steps
graph.add_edge("fetch_guide", "route_results")
graph.add_edge("route_results", "manage_context")

graph.add_edge("manage_context", "format_markdown")
graph.add_edge("format_markdown", "stream_response")
graph.add_edge("stream_response", "usage_analytics")
graph.add_edge("usage_analytics", "checkpoint_save")
graph.add_edge("checkpoint_save", END)

# Compile with memory checkpointer
memory = MemorySaver()
app_graph = graph.compile(checkpointer=memory)
