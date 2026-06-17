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
import traceback
import re

    
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
    import asyncio
    
    user_id = user.id
    # Use provided thread_id or generate new one for new conversations
    thread_id = request.thread_id or f"thread-{uuid.uuid4()}"
    try:
        logger.info(f"/chat/stream called user_id={user_id} thread_id={thread_id} msg='{request.message[:80]}'")
    except Exception:
        pass
    
    # Save user message to conversation history
    await save_message_to_history(user_id, thread_id, "user", request.message)
    
    async def generate() -> AsyncGenerator[str, None]:
        assistant_response = ""
        pending_done_payload = None
        
        # Emit thread_id immediately so frontend can associate the session
        yield f"data: {json.dumps({'type': 'thread_id', 'thread_id': thread_id})}\n\n"
        # For progressive step image emission
        emitted_step_images = set()
        collected_step_images = []  # list of dicts {step:int, url:str}
        step_images_metadata = []
        current_step = 0
        # Buffer for line-by-line streaming
        line_buffer = ""
        
        try:
            # Get conversation history
            conversation_history = await get_or_create_conversation_history(user_id, thread_id)
            # Ensure the current user message is included in the conversation history
            try:
                if not conversation_history:
                    conversation_history = [HumanMessage(content=request.message)]
                else:
                    # If the last saved message isn't the current user message, append it
                    try:
                        last = conversation_history[-1]
                        last_content = last.content if hasattr(last, 'content') else str(last)
                    except Exception:
                        last_content = None
                    if last_content != (request.message or ""):
                        conversation_history.append(HumanMessage(content=request.message))
            except Exception:
                # If any of this fails, fall back to using the request message alone
                conversation_history = [HumanMessage(content=request.message)]
            
            # Prepare inputs
            inputs = {
                "messages": conversation_history,
                "user_id": user_id
            }

            # Lightweight debug logging to help diagnose mismatch between
            # local pipeline output and running server stream.
            try:
                logger.debug("chat_stream inputs: user_id=%s thread_id=%s messages=%d",
                             user_id, thread_id, len(conversation_history or []))
            except Exception:
                pass
            
            config = {"configurable": {"thread_id": thread_id}}
            
            # Stream events from the graph
            async for event in app_graph.astream_events(inputs, config, version="v1"):
                event_type = event.get("event")
                
                # Tool start event - show brief status
                if event_type == "on_tool_start":
                    tool_name = event.get("name", "tool")
                    status_msg = _get_tool_status_message(tool_name)
                    yield f"data: {json.dumps({'type': 'status', 'content': status_msg})}\n\n"

                # Tool finished / returned a result - emit any step images immediately
                elif event_type in ("on_tool_end", "on_tool_result", "on_tool_output"):
                    # Try to find tool result in event payload
                    data = event.get('data', {}) or {}
                    # possible fields where tool output may live
                    tool_result = data.get('result') or data.get('output') or data.get('tool_result') or data.get('content')
                    if tool_result:
                        # If result is structured (list/dict), try to extract step images
                        try:
                            if isinstance(tool_result, (list, dict)):
                                text_blob = json.dumps(tool_result)
                            else:
                                text_blob = str(tool_result)
                        except Exception:
                            text_blob = str(tool_result)

                        # Look for STEP_IMAGES metadata comment
                        for m in re.finditer(r'<!--\s*STEP_IMAGES:\s*(\[.*?\])\s*-->', text_blob, re.IGNORECASE | re.DOTALL):
                            try:
                                imgs = json.loads(m.group(1))
                                for entry in imgs:
                                    s = int(entry.get('step')) if entry.get('step') is not None else None
                                    u = entry.get('url')
                                    if s and u and s not in emitted_step_images:
                                        emitted_step_images.add(s)
                                        collected_step_images.append({'step': s, 'url': u})
                                        yield f"data: {json.dumps({'type': 'step_image', 'step': s, 'url': u})}\n\n"
                            except Exception:
                                pass

                        # Also search for inline markdown image patterns and emit them
                        for pm in re.finditer(r'!\[[^\]]*Step\s*(\d+)[^\]]*\]\((https?://[^)]+)\)', text_blob, re.IGNORECASE):
                            try:
                                step_num = int(pm.group(1))
                                url = pm.group(2)
                                if step_num not in emitted_step_images:
                                    emitted_step_images.add(step_num)
                                    collected_step_images.append({'step': step_num, 'url': url})
                                    yield f"data: {json.dumps({'type': 'step_image', 'step': step_num, 'url': url})}\n\n"
                            except Exception:
                                pass
                
                # LLM token streaming
                elif event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        # Normalize content (Gemini may return structured blocks)
                        normalized = _normalize_content(chunk.content)
                        if normalized:
                            assistant_response += normalized
                            # Use a small buffer to accumulate partial chunks so we only emit
                            # whole "words" to the client. A word is defined here as either
                            # a run of whitespace or a non-space token plus optional trailing space.
                            if 'word_buffer' not in locals():
                                word_buffer = ""
                            word_buffer += normalized

                            # Emit word-by-word SSE events
                            while True:
                                wm = re.match(r'^(\s+|\S+\s*)', word_buffer)
                                if not wm:
                                    break
                                token = wm.group(1)
                                word_buffer = word_buffer[len(token):]
                                yield f"data: {json.dumps({'type': 'word', 'content': token})}\n\n"

                            # Detect step headings as they stream (e.g., **Step 1: ...)**
                            try:
                                for m in re.finditer(r'\*\*Step\s+(\d+)', assistant_response, re.IGNORECASE):
                                    step_num = int(m.group(1))
                                    # If we haven't emitted an image event for this step, try to find its image
                                    if step_num not in emitted_step_images:
                                        # look for markdown image for this step in the accumulated response
                                        pattern = rf'!\[.*?Step\s*{step_num}.*?\]\((https?://[^)]+)\)'
                                        pm = re.search(pattern, assistant_response, re.IGNORECASE)
                                        url = None
                                        if pm:
                                            url = pm.group(1)
                                        else:
                                            # fallback: any image after the step heading
                                            heading_pos = m.end()
                                            snippet = assistant_response[heading_pos:heading_pos+500]
                                            anym = re.search(r'!\[[^\]]*\]\((https?://[^)]+)\)', snippet)
                                            if anym:
                                                url = anym.group(1)

                                        if url:
                                            emitted_step_images.add(step_num)
                                            collected_step_images.append({"step": step_num, "url": url})
                                            # Emit a step_image SSE event
                                            yield f"data: {json.dumps({'type': 'step_image', 'step': step_num, 'url': url})}\n\n"
                            except Exception:
                                # don't let step detection break streaming
                                pass

                            # Check if we've reached a new step boundary and stream its image
                            step_match = re.search(r'\*\*Step\s+(\d+)', assistant_response)
                            if step_match:
                                step_num = int(step_match.group(1))
                                if step_num > current_step:
                                    current_step = step_num
                                    # Try to find the image for this step in the response
                                    step_img_match = re.search(
                                        rf'\*\*Step\s+{step_num}[^!]*!\[Step\s+{step_num}[^\]]*\]\(([^)]+)\)',
                                        assistant_response,
                                        re.DOTALL
                                    )
                                    if step_img_match:
                                        img_url = step_img_match.group(1)
                                        # Stream the step image immediately
                                        yield f"data: {json.dumps({'type': 'step_image', 'step': step_num, 'url': img_url})}\n\n"
                                        step_images_metadata.append({"step": step_num, "url": img_url})
                
                # Final message
                elif event_type == "on_chain_end":
                    output = event.get("data", {}).get("output")
                    try:
                        logger.debug("on_chain_end event output keys: %s", list(output.keys()) if isinstance(output, dict) else type(output))
                    except Exception:
                        pass
                    if output and isinstance(output, dict):
                        messages = output.get("messages", [])
                        step_image = output.get("step_image")
                        # Log whether the graph/tool returned structured repair data
                        try:
                            has_repair_steps = bool(output.get('repair_steps'))
                        except Exception:
                            has_repair_steps = False
                        try:
                            has_formatted = bool(output.get('formatted_response') or output.get('formatted'))
                        except Exception:
                            has_formatted = False
                        logger.info("on_chain_end: has_repair_steps=%s has_formatted=%s step_image=%s",
                                    has_repair_steps, has_formatted, bool(step_image))
                        if messages:
                            last_message = messages[-1]
                            if isinstance(last_message, AIMessage):
                                # If we didn't capture response via streaming, get it from final message
                                if not assistant_response:
                                    assistant_response = _normalize_content(last_message.content)

                                # Prefer structured step_images returned by the graph/tool output
                                step_images_metadata = []
                                try:
                                    if output.get('step_images'):
                                        step_images_metadata = output.get('step_images') or []
                                    else:
                                        # Fallback: Extract step images metadata if present in HTML comment
                                        metadata_match = re.search(r'<!-- STEP_IMAGES: (\[.*?\]) -->', assistant_response)
                                        if metadata_match:
                                            try:
                                                step_images_metadata = json.loads(metadata_match.group(1))
                                            except:
                                                step_images_metadata = []
                                except Exception:
                                    step_images_metadata = []

                                # Save assistant response to conversation history (persist step image if available)
                                await save_message_to_history(user_id, thread_id, "assistant", assistant_response, step_image)
                                # Prepare done payload but delay sending until graph finishes so we include the final step_image
                                # Include a structured JSON payload so the frontend can render text and image separately
                                structured = {
                                    "text": assistant_response,
                                    "step_image": step_image,
                                    "step_images": step_images_metadata
                                }
                                pending_done_payload = {
                                    'type': 'done',
                                    'thread_id': thread_id,
                                    'step_image': step_image,
                                    'step_images': step_images_metadata,
                                    'message': assistant_response,
                                    'structured': structured
                                }
            
            # Send any remaining buffered content
            if line_buffer:
                yield f"data: {json.dumps({'type': 'line', 'content': line_buffer})}\n\n"
            
            # After the graph finished emitting events, try to extract final step images metadata from the assistant response if present
            try:
                m = re.search(r'<!--\s*STEP_IMAGES:\s*(\[.*?\])\s*-->', assistant_response, re.IGNORECASE | re.DOTALL)
                if m:
                    try:
                        parsed_meta = json.loads(m.group(1))
                        # parsed_meta expected to be list of {step, url}
                        for entry in parsed_meta:
                            s = int(entry.get('step')) if entry.get('step') is not None else None
                            u = entry.get('url')
                            if s and u and s not in emitted_step_images:
                                emitted_step_images.add(s)
                                collected_step_images.append({"step": s, "url": u})
                                yield f"data: {json.dumps({'type': 'step_image', 'step': s, 'url': u})}\n\n"
                    except Exception:
                        pass
            except Exception:
                pass

            if pending_done_payload is not None:
                # include collected step images in final payload
                pending_done_payload['step_images'] = collected_step_images
                # also include in structured if present
                if isinstance(pending_done_payload.get('structured'), dict):
                    pending_done_payload['structured']['step_images'] = collected_step_images
                yield f"data: {json.dumps(pending_done_payload)}\n\n"

        except Exception as e:
            # Include traceback so clients receive useful diagnostic text
            tb = traceback.format_exc()
            error_msg = tb or f"Error: {str(e)}"
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
        "search_devices": "🔍 Searching iFixit...",
        "list_guides": "📋 Loading guides...",
        "fetch_repair_guide": "📖 Getting repair steps...",
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
async def get_chat_history(
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
    from backend.services.conversation_service import get_conversation_history
    
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
        result = await get_conversation_history(user_id, thread_id)
        
        messages = []
        for record in result[:limit] if result else []:
            messages.append({
                "role": record.get("role"),
                "content": record.get("content"),
                "timestamp": record.get("created_at"),
                "step_image": record.get("step_image")
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
async def clear_chat_history(
    thread_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    """
    Clear conversation history for a specific thread or all user threads.
    
    Args:
        thread_id: Optional thread to clear. If None, clears ALL conversations.
    """
    from backend.services.conversation_service import delete_conversation
    
    user_id = user.id
    
    try:
        # Delete conversation(s) using MongoDB service
        deleted_count = await delete_conversation(user_id, thread_id)
        
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
async def get_sessions_endpoint(user=Depends(get_current_user)):
    """
    Get all chat sessions for the current user.
    Returns a list of sessions with title, preview, and metadata.
    """
    from backend.chat.service import get_user_sessions_wrapper as get_sessions_service
    
    user_id = user.id
    
    try:
        sessions = await get_sessions_service(user_id)
        return {
            "sessions": sessions
        }
    except Exception as e:
        return {
            "error": f"Failed to retrieve sessions: {str(e)}",
            "sessions": []
        }
