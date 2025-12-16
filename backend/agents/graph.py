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

# Model configured for streaming
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=GEMINI_API_KEY,
    streaming=True
)


# ==================== NODE 1: NORMALIZE INPUT ====================
async def normalize_input(state: AgentState) -> AgentState:
    """Extract and normalize user input from messages."""
    messages = state["messages"]
    
    # Find the last user message
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_query = msg.content
            return {
                "user_query": user_query,
                "normalized_query": user_query.lower().strip()
            }
    
    # No user message found
    return {
        "user_query": "",
        "normalized_query": "",
        "messages": [AIMessage(content="Please ask a repair question.")]
    }


# ==================== NODE 2: IFIXIT SEARCH ====================
async def ifixit_search(state: AgentState) -> AgentState:
    """Search iFixit for device and guides."""
    user_query = state.get("user_query", "")
    normalized_query = state.get("normalized_query", "")
    
    if not user_query:
        return {"ifixit_results": [], "ifixit_found": False}
    
    ifixit_results = []
    device_title = None
    
    # Step 1: Find device/guides
    try:
        device_result = find_device.invoke({"query": user_query})
        ifixit_results.append({"type": "device_search", "content": device_result})
        
        # Extract device title for further queries
        device_title = _extract_device_title(device_result)
    except Exception as e:
        ifixit_results.append({"type": "error", "content": f"Device search error: {str(e)}"})
    
    # Step 2: List guides for the device
    if device_title:
        try:
            guides_result = list_guides.invoke({"device_title": device_title})
            ifixit_results.append({"type": "guides_list", "content": guides_result})
            
            # Step 3: Get specific guide details if relevant
            guide_id = _extract_guide_id(guides_result, normalized_query)
            if guide_id:
                try:
                    guide_detail = get_guide.invoke({"guide_id": guide_id})
                    ifixit_results.append({"type": "guide_detail", "content": guide_detail})
                except Exception as e:
                    ifixit_results.append({"type": "error", "content": f"Guide detail error: {str(e)}"})
        except Exception as e:
            ifixit_results.append({"type": "error", "content": f"Guides list error: {str(e)}"})
    
    return {
        "ifixit_results": ifixit_results,
        "device_title": device_title
    }


# ==================== NODE 3: ROUTE RESULTS ====================
async def route_results(state: AgentState) -> AgentState:
    """Determine if iFixit found useful results."""
    ifixit_results = state.get("ifixit_results", [])
    
    # Check if we got useful results
    for result in ifixit_results:
        content = result.get("content", "").lower()
        
        # Check for positive indicators
        has_useful_result = (
            (("found devices:" in content or "found guides:" in content) and "-" in result.get("content", "")) or
            ("[guide]" in content and "url:" in content) or
            ("ifixit.com" in content and "url:" in content)
        ) and (
            "no results found" not in content and
            "no devices found" not in content and
            result.get("type") != "error"
        )
        
        if has_useful_result:
            return {"ifixit_found": True}
    
    return {"ifixit_found": False}


# ==================== NODE 4: WEB SEARCH FALLBACK ====================
async def web_search_fallback(state: AgentState) -> AgentState:
    """Search web only if iFixit found nothing."""
    ifixit_found = state.get("ifixit_found", False)
    user_query = state.get("user_query", "")
    
    if ifixit_found or not user_query:
        return {"web_results": []}
    
    # iFixit found nothing, search web
    try:
        web_result = web_search.invoke({"query": user_query})
        return {"web_results": [{"type": "web_search", "content": web_result}]}
    except Exception as e:
        return {"web_results": [{"type": "error", "content": f"Web search error: {str(e)}"}]}


# ==================== NODE 5: MANAGE CONTEXT ====================
async def manage_context(state: AgentState) -> AgentState:
    """Combine all results into structured context."""
    ifixit_results = state.get("ifixit_results", [])
    web_results = state.get("web_results", [])
    ifixit_found = state.get("ifixit_found", False)
    
    # Build combined context
    context_parts = []
    
    # Add iFixit results
    for result in ifixit_results:
        result_type = result.get("type", "unknown")
        content = result.get("content", "")
        
        if result_type == "device_search":
            context_parts.append(f"iFixit Search:\n{content}")
        elif result_type == "guides_list":
            context_parts.append(f"Available Guides:\n{content}")
        elif result_type == "guide_detail":
            context_parts.append(f"Guide Details:\n{content}")
        elif result_type == "error" and not ifixit_found:
            context_parts.append(f"Note: {content}")
    
    # Add web results only if iFixit found nothing
    if not ifixit_found:
        for result in web_results:
            content = result.get("content", "")
            context_parts.append(f"Web Search (unofficial sources):\n{content}")
    
    combined_context = "\n\n".join(context_parts)
    
    return {
        "combined_context": combined_context,
        "has_results": len(context_parts) > 0
    }


# ==================== NODE 6: FORMAT MARKDOWN ====================
async def format_markdown(state: AgentState) -> AgentState:
    """Use LLM to format results into friendly markdown."""
    user_query = state.get("user_query", "")
    combined_context = state.get("combined_context", "")
    has_results = state.get("has_results", False)
    
    if not has_results:
        return {
            "formatted_response": "I couldn't find any information about that. Could you try rephrasing your question?",
            "prompt_tokens": 0
        }
    
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
    format_prompt = state.get("format_prompt", "")
    
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
    
    if formatted_response:
        return {"messages": [AIMessage(content=formatted_response)]}
    
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
                time.sleep(delay)
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

# Add all nodes
graph.add_node("normalize_input", normalize_input)
graph.add_node("ifixit_search", ifixit_search)
graph.add_node("route_results", route_results)
graph.add_node("web_search_fallback", web_search_fallback)
graph.add_node("manage_context", manage_context)
graph.add_node("format_markdown", format_markdown)
graph.add_node("stream_response", stream_response)
graph.add_node("usage_analytics", usage_analytics)
graph.add_node("checkpoint_save", checkpoint_save)

# Build the flow
graph.set_entry_point("normalize_input")
graph.add_edge("normalize_input", "ifixit_search")
graph.add_edge("ifixit_search", "route_results")
graph.add_edge("route_results", "web_search_fallback")
graph.add_edge("web_search_fallback", "manage_context")
graph.add_edge("manage_context", "format_markdown")
graph.add_edge("format_markdown", "stream_response")
graph.add_edge("stream_response", "usage_analytics")
graph.add_edge("usage_analytics", "checkpoint_save")
graph.add_edge("checkpoint_save", END)

# Compile with memory checkpointer
memory = MemorySaver()
app_graph = graph.compile(checkpointer=memory)
