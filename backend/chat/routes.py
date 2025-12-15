from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from backend.agents.graph import app_graph
from backend.auth.dependencies import get_current_user
from backend.chat.service import get_or_create_conversation_history
from pydantic import BaseModel
import json
from typing import AsyncGenerator

    
router = APIRouter()

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "How do I fix my iPhone 13 screen?"
            }
        }

@router.post("/chat")
def chat(request: ChatRequest, user=Depends(get_current_user)):
    """
    Non-streaming chat endpoint with session management.
    
    Each user gets their own conversation thread identified by thread_id.
    Token usage is tracked per user in the user_usage table.
    Messages are persisted to conversations table for session continuity.
    """
    from backend.chat.service import save_message_to_history
    
    # Extract user_id for analytics and persistence
    user_id = user.id
    thread_id = f"user-{user_id}"
    
    # Save user message to conversation history
    save_message_to_history(user_id, thread_id, "user", request.message)
    
    # Get conversation history for context
    conversation_history = get_or_create_conversation_history(user_id, thread_id)
    
    # Prepare inputs with user context
    inputs = {
        "messages": conversation_history,
        "user_id": user_id  # Pass user_id for token tracking
    }
    
    # Invoke graph with thread-specific configuration
    config = {"configurable": {"thread_id": thread_id}}
    result = app_graph.invoke(inputs, config)
    
    # Get assistant response and normalize to plain text
    raw_content = result["messages"][-1].content
    assistant_response = _normalize_content(raw_content)
    
    # Save assistant response to conversation history
    save_message_to_history(user_id, thread_id, "assistant", assistant_response)
    
    return {
        "response": assistant_response,
        "thread_id": thread_id
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
    thread_id = f"user-{user_id}"
    
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
                
                # Tool start event
                if event_type == "on_tool_start":
                    tool_name = event.get("name", "tool")
                    status_msg = _get_tool_status_message(tool_name)
                    yield f"data: {json.dumps({'type': 'status', 'content': status_msg})}\\n\\n"
                
                # Tool end event
                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "tool")
                    yield f"data: {json.dumps({'type': 'status', 'content': f'✓ {tool_name} completed'})}\\n\\n"
                
                # LLM token streaming
                elif event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        # Normalize content (Gemini may return structured blocks)
                        normalized = _normalize_content(chunk.content)
                        if normalized:
                            assistant_response += normalized
                            yield f"data: {json.dumps({'type': 'token', 'content': normalized})}\\n\\n"
                
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
                                
                                yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id})}\\n\\n"
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\\n\\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


def _get_tool_status_message(tool_name: str) -> str:
    """Get friendly status message for tool execution."""
    status_messages = {
        "find_device": "🔍 Searching iFixit for device...",
        "list_guides": "📋 Loading repair guides...",
        "get_guide": "📖 Fetching repair instructions...",
        "web_search": "🌐 Searching the web for information..."
    }
    return status_messages.get(tool_name, f"⚙️ Running {tool_name}...")


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
def get_chat_history(user=Depends(get_current_user), limit: int = 50):
    """
    Get conversation history for the current user.
    
    Args:
        limit: Maximum number of messages to return (default: 50)
    
    Returns:
        List of messages with role, content, and timestamp
    """
    from backend.supabase_client import supabase
    
    user_id = user.id
    thread_id = f"user-{user_id}"
    
    try:
        result = supabase.table("conversations").select("*").eq(
            "thread_id", thread_id
        ).order("created_at", desc=False).limit(limit).execute()
        
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
def clear_chat_history(user=Depends(get_current_user)):
    """
    Clear conversation history for the current user.
    
    This will delete all messages from the current session/thread.
    """
    from backend.supabase_client import supabase
    
    user_id = user.id
    thread_id = f"user-{user_id}"
    
    try:
        # Delete all messages for this thread
        supabase.table("conversations").delete().eq("thread_id", thread_id).execute()
        
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
def get_user_sessions(user=Depends(get_current_user)):
    """
    Get session statistics for the current user.
    
    Returns:
        - Total messages sent
        - Total tokens used
        - Session start date
        - Last activity timestamp
    """
    from backend.supabase_client import supabase
    from backend.models.usage import get_user_token_usage
    from backend.chat.service import get_conversation_count
    
    user_id = user.id
    thread_id = f"user-{user_id}"
    
    try:
        # Get message count
        message_count = get_conversation_count(user_id, thread_id)
        
        # Get token usage
        total_tokens = get_user_token_usage(user_id)
        
        # Get first and last message timestamps
        first_msg = supabase.table("conversations").select("created_at").eq(
            "thread_id", thread_id
        ).order("created_at", desc=False).limit(1).execute()
        
        last_msg = supabase.table("conversations").select("created_at").eq(
            "thread_id", thread_id
        ).order("created_at", desc=True).limit(1).execute()
        
        session_start = first_msg.data[0]["created_at"] if first_msg.data else None
        last_activity = last_msg.data[0]["created_at"] if last_msg.data else None
        
        return {
            "user_id": user_id,
            "thread_id": thread_id,
            "total_messages": message_count,
            "total_tokens_used": total_tokens,
            "session_start": session_start,
            "last_activity": last_activity
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve session info: {str(e)}"
        }
