from typing import List, Optional
from datetime import datetime
from backend.mongo_client import conversations_collection


async def save_message(
    user_id: str,
    thread_id: str,
    role: str,
    content: str,
    step_image: Optional[str] = None
) -> dict:
    """
    Save a message to the conversations collection.
    
    Args:
        user_id: User's unique identifier
        thread_id: Conversation thread identifier
        role: Message role ("user" or "assistant")
        content: Message content
        step_image: Optional image URL for repair steps
        
    Returns:
        Inserted message document
    """
    message_doc = {
        "user_id": user_id,
        "thread_id": thread_id,
        "role": role,
        "content": content,
        "created_at": datetime.utcnow()
    }
    
    if step_image:
        message_doc["step_image"] = step_image
    
    result = await conversations_collection.insert_one(message_doc)
    message_doc["_id"] = result.inserted_id
    return message_doc


async def get_conversation_history(user_id: str, thread_id: str) -> List[dict]:
    """
    Retrieve conversation history for a specific thread.
    
    Args:
        user_id: User's unique identifier
        thread_id: Conversation thread identifier
        
    Returns:
        List of message documents ordered by creation time
    """
    cursor = conversations_collection.find(
        {"thread_id": thread_id, "user_id": user_id}
    ).sort("created_at", 1)
    
    messages = await cursor.to_list(length=None)
    return messages


async def get_conversation_count(user_id: str, thread_id: str) -> int:
    """
    Get the number of messages in a conversation thread.
    
    Args:
        user_id: User's unique identifier
        thread_id: Conversation thread identifier
        
    Returns:
        Number of messages in the thread
    """
    count = await conversations_collection.count_documents(
        {"thread_id": thread_id, "user_id": user_id}
    )
    return count


async def get_user_sessions(user_id: str) -> List[dict]:
    """
    Get all chat sessions for a user with title and preview.
    Groups conversations by thread_id and returns summary info.
    
    Args:
        user_id: User's unique identifier
        
    Returns:
        List of session dictionaries with id, title, preview, timestamp
    """
    # Get all messages for this user
    cursor = conversations_collection.find(
        {"user_id": user_id}
    ).sort("created_at", 1)
    
    messages = await cursor.to_list(length=None)
    
    if not messages:
        return []
    
    # Group by thread_id
    threads = {}
    for msg in messages:
        thread_id = msg.get("thread_id")
        if thread_id not in threads:
            threads[thread_id] = []
        threads[thread_id].append(msg)
    
    # Create session summaries
    sessions = []
    for thread_id, thread_messages in threads.items():
        if not thread_messages:
            continue
        
        # Get first user message as title
        first_user_msg = next((m for m in thread_messages if m.get("role") == "user"), None)
        if not first_user_msg:
            continue
        
        title = first_user_msg.get("content", "Untitled Chat")[:50]
        if len(first_user_msg.get("content", "")) > 50:
            title += "..."
        
        # Get last message as preview
        last_msg = thread_messages[-1]
        preview = last_msg.get("content", "")[:60]
        if len(last_msg.get("content", "")) > 60:
            preview += "..."
        
        # Choose a thumbnail from messages
        thumbnail = None
        for m in thread_messages:
            if m.get("role") == "assistant" and m.get("step_image"):
                thumbnail = m.get("step_image")
                break
        if not thumbnail:
            thumbnail = last_msg.get("step_image")
        
        sessions.append({
            "id": thread_id,
            "title": title,
            "preview": preview,
            "timestamp": last_msg.get("created_at"),
            "message_count": len(thread_messages),
            "thumbnail": thumbnail
        })
    
    # Sort by most recent first
    sessions.sort(key=lambda s: s["timestamp"], reverse=True)
    return sessions


async def delete_conversation(user_id: str, thread_id: Optional[str] = None) -> int:
    """
    Delete conversation(s) for a user.
    
    Args:
        user_id: User's unique identifier
        thread_id: Optional specific thread to delete. If None, deletes all user conversations.
        
    Returns:
        Number of messages deleted
    """
    if thread_id:
        result = await conversations_collection.delete_many(
            {"thread_id": thread_id, "user_id": user_id}
        )
    else:
        result = await conversations_collection.delete_many(
            {"user_id": user_id}
        )
    
    return result.deleted_count
