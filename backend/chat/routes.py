from fastapi import APIRouter, Depends, Body
import logging
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from backend.agents.graph import app_graph
from backend.auth.dependencies import get_current_user
from backend.chat.service import get_or_create_conversation_history
from pydantic import BaseModel
import json
import uuid
from typing import AsyncGenerator, Optional

    
router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    thread_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "How do I fix my iPhone 13 screen?",
                "thread_id": "thread-abc123"
            }
        }

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, user=Depends(get_current_user)):
    """
    Streaming chat endpoint with session management and tool execution status.
    
    Streams:
    - Tool execution status (e.g., "Searching iFixit...")
    - LLM response token-by-token
    - Final completion message
    
    Messages are persisted to conversations table for session continuity.
    """
    from backend.chat.service import save_message_to_history
    
    user_id = user.id
    # Use provided thread_id or generate new one for new conversations
    thread_id = request.thread_id or f"thread-{uuid.uuid4()}"
    try:
        logger.info(f"/chat/stream called user_id={user_id} thread_id={thread_id} msg='{request.message[:80]}'")
    except Exception:
        pass
    
    # Save user message to conversation history
    save_message_to_history(user_id, thread_id, "user", request.message)
    
    async def generate() -> AsyncGenerator[str, None]:
        assistant_response = ""
        try:
            # Get conversation history
            conversation_history = get_or_create_conversation_history(user_id, thread_id)
            
            # Prepare inputs
            inputs = {
                "messages": conversation_history,
                "user_id": user_id
            }
            
            config = {"configurable": {"thread_id": thread_id}}
            
            # Stream events from the graph
            async for event in app_graph.astream_events(inputs, config, version="v1"):
                event_type = event.get("event")
                
                # Tool start event - show brief status
                if event_type == "on_tool_start":
                    tool_name = event.get("name", "tool")
                    status_msg = _get_tool_status_message(tool_name)
                    yield f"data: {json.dumps({'type': 'status', 'content': status_msg})}\n\n"
                
                # LLM token streaming
                elif event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        # Normalize content (Gemini may return structured blocks)
                        normalized = _normalize_content(chunk.content)
                        if normalized:
                            assistant_response += normalized
                            yield f"data: {json.dumps({'type': 'token', 'content': normalized})}\n\n"
                
                # Final message
                elif event_type == "on_chain_end":
                    output = event.get("data", {}).get("output")
                    if output and isinstance(output, dict):
                        messages = output.get("messages", [])
                        if messages:
                            last_message = messages[-1]
                            if isinstance(last_message, AIMessage):
                                # If we didn't capture response via streaming, get it from final message
                                if not assistant_response:
                                    assistant_response = _normalize_content(last_message.content)
                                
                                # Save assistant response to conversation history
                                save_message_to_history(user_id, thread_id, "assistant", assistant_response)
                                
                                yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id})}\n\n"
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
    
    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


def _get_tool_status_message(tool_name: str) -> str:
    """Get friendly status message for tool execution."""
    status_messages = {
        "find_device": "🔍 Searching iFixit...",
        "list_guides": "📋 Loading guides...",
        "get_guide": "📖 Getting repair steps...",
        "web_search": "🌐 Searching online..."
    }
    return status_messages.get(tool_name, f"Working on it...")


def _normalize_content(content) -> str:
    """Normalize LLM message content to plain string.
    Handles providers that return structured blocks (e.g., [{"type":"text","text":"..."}]).
    """
    try:
        if isinstance(content, str):
            return content
        # List of blocks
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    # Common keys: text, content
                    if "text" in block and isinstance(block["text"], str):
                        parts.append(block["text"])
                    elif "content" in block and isinstance(block["content"], str):
                        parts.append(block["content"])
                    else:
                        parts.append(str(block))
                else:
                    parts.append(str(block))
            return "".join(parts)
        # Fallback
        return str(content)
    except Exception:
        return str(content)


@router.get("/chat/history")
def get_chat_history(
    thread_id: Optional[str] = None,
    limit: int = 50,
    user=Depends(get_current_user)
):
    """
    Get conversation history for a specific thread.
    
    Args:
        thread_id: Thread identifier to fetch messages for
        limit: Maximum number of messages to return (default: 50)
    
    Returns:
        List of messages with role, content, and timestamp
    """
    from backend.supabase_client import supabase
    
    user_id = user.id
    
    # If no thread_id provided, return empty
    if not thread_id:
        return {
            "thread_id": None,
            "message_count": 0,
            "messages": []
        }
    
    try:
        # Verify thread belongs to user
        result = supabase.table("conversations").select("*").eq(
            "thread_id", thread_id
        ).eq("user_id", user_id).order("created_at", desc=False).limit(limit).execute()
        
        messages = []
        for record in result.data:
            messages.append({
                "role": record.get("role"),
                "content": record.get("content"),
                "timestamp": record.get("created_at")
            })
        
        return {
            "thread_id": thread_id,
            "message_count": len(messages),
            "messages": messages
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve history: {str(e)}",
            "messages": []
        }


@router.delete("/chat/history")
def clear_chat_history(
    thread_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    """
    Clear conversation history for a specific thread or all user threads.
    
    Args:
        thread_id: Optional thread to clear. If None, clears ALL conversations.
    """
    from backend.supabase_client import supabase
    
    user_id = user.id
    
    try:
        if thread_id:
            # Clear specific thread (verify ownership)
            supabase.table("conversations").delete().eq(
                "thread_id", thread_id
            ).eq("user_id", user_id).execute()
        else:
            # Clear all user's conversations
            supabase.table("conversations").delete().eq("user_id", user_id).execute()
        
        return {
            "success": True,
            "message": "Chat history cleared successfully",
            "thread_id": thread_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to clear history: {str(e)}"
        }


@router.get("/chat/sessions")
def get_sessions_endpoint(user=Depends(get_current_user)):
    """
    Get all chat sessions for the current user.
    Returns a list of sessions with title, preview, and metadata.
    """
    from backend.chat.service import get_user_sessions as get_sessions_service
    
    user_id = user.id
    
    try:
        sessions = get_sessions_service(user_id)
        return {
            "sessions": sessions
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve sessions: {str(e)}",
            "sessions": []
        }
