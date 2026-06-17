from typing import List, Optional
from datetime import datetime
from postgres_client import get_db_connection
import logging

logger = logging.getLogger(__name__)

async def save_message(
    user_id: str,
    thread_id: str,
    role: str,
    content: str,
    step_image: Optional[str] = None
) -> dict:
    """
    Save a message to the conversations table.
    
    Args:
        user_id: User's unique identifier
        thread_id: Conversation thread identifier
        role: Message role ("user" or "assistant")
        content: Message content
        step_image: Optional image URL for repair steps
        
    Returns:
        Inserted message document as dict
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO conversations (user_id, thread_id, role, content, step_image) VALUES (%s, %s, %s, %s, %s) RETURNING id, user_id, thread_id, role, content, step_image, created_at",
            (user_id, thread_id, role, content, step_image)
        )
        row = cur.fetchone()
        conn.commit()
        return dict(row)
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error saving message: {e}")
        raise
    finally:
        if conn:
            conn.close()


async def get_conversation_history(user_id: str, thread_id: str) -> List[dict]:
    """
    Retrieve conversation history for a specific thread.
    
    Args:
        user_id: User's unique identifier
        thread_id: Conversation thread identifier
        
    Returns:
        List of message documents ordered by creation time
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, user_id, thread_id, role, content, step_image, created_at FROM conversations WHERE thread_id = %s AND user_id = %s ORDER BY created_at ASC",
            (thread_id, user_id)
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return []
    finally:
        if conn:
            conn.close()


async def get_conversation_count(user_id: str, thread_id: str) -> int:
    """
    Get the number of messages in a conversation thread.
    
    Args:
        user_id: User's unique identifier
        thread_id: Conversation thread identifier
        
    Returns:
        Number of messages in the thread
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM conversations WHERE thread_id = %s AND user_id = %s",
            (thread_id, user_id)
        )
        count = cur.fetchone()['count']
        return count
    except Exception as e:
        logger.error(f"Error getting conversation count: {e}")
        return 0
    finally:
        if conn:
            conn.close()


async def get_user_sessions(user_id: str) -> List[dict]:
    """
    Get all chat sessions for a user with title and preview.
    Groups conversations by thread_id and returns summary info.
    
    Args:
        user_id: User's unique identifier
        
    Returns:
        List of session dictionaries with id, title, preview, timestamp
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # This query gets the first user message (title), the last message (timestamp/preview), 
        # and checking for any assistant message with a step_image (thumbnail)
        # However, for simplicity and compatibility with the previous logic, we'll fetch all and group in Python
        # or use a more complex SQL query. Let's fetch all messages for the user.
        
        cur.execute(
            "SELECT id, user_id, thread_id, role, content, step_image, created_at FROM conversations WHERE user_id = %s ORDER BY created_at ASC",
            (user_id,)
        )
        messages = [dict(row) for row in cur.fetchall()]
        
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
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        return []
    finally:
        if conn:
            conn.close()


async def delete_conversation(user_id: str, thread_id: Optional[str] = None) -> int:
    """
    Delete conversation(s) for a user.
    
    Args:
        user_id: User's unique identifier
        thread_id: Optional specific thread to delete. If None, deletes all user conversations.
        
    Returns:
        Number of messages deleted
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if thread_id:
            cur.execute(
                "DELETE FROM conversations WHERE thread_id = %s AND user_id = %s",
                (thread_id, user_id)
            )
        else:
            cur.execute(
                "DELETE FROM conversations WHERE user_id = %s",
                (user_id,)
            )
        
        deleted_count = cur.rowcount
        conn.commit()
        return deleted_count
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting conversation: {e}")
        return 0
    finally:
        if conn:
            conn.close()
