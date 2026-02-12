from typing import List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from backend.services.conversation_service import (
    get_conversation_history,
    save_message,
    get_conversation_count as get_count,
    get_user_sessions as get_sessions
)


async def get_or_create_conversation_history(user_id: str, thread_id: str) -> List[BaseMessage]:
    """
    Retrieve conversation history for a user's thread from MongoDB.
    
    Args:
        user_id: The user's unique identifier
        thread_id: The conversation thread identifier (e.g., "user-{user_id}")
        
    Returns:
        List of messages in the conversation history
    """
    try:
        # Query conversation history from MongoDB
        messages_data = await get_conversation_history(user_id, thread_id)
        
        if not messages_data:
            return []
        
        # Convert stored messages to LangChain format
        messages = []
        for record in messages_data:
            role = record.get("role")
            content = record.get("content")
            
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        
        return messages
        
    except Exception as e:
        print(f"Error retrieving conversation history: {e}")
        return []


async def save_message_to_history(
    user_id: str,
    thread_id: str,
    role: str,
    content: str,
    step_image: Optional[str] = None
) -> None:
    """
    Save a message to the conversation history in MongoDB.
    
    Args:
        user_id: The user's unique identifier
        thread_id: The conversation thread identifier
        role: Message role ("user" or "assistant")
        content: Message content
        step_image: Optional image URL for repair steps
    """
    try:
        await save_message(user_id, thread_id, role, content, step_image)
    except Exception as e:
        print(f"Error saving message to history: {e}")


async def get_conversation_count_wrapper(user_id: str, thread_id: str) -> int:
    """
    Get the number of messages in a conversation thread.
    
    Args:
        user_id: The user's unique identifier
        thread_id: The conversation thread identifier
        
    Returns:
        Number of messages in the thread
    """
    try:
        return await get_count(user_id, thread_id)
    except Exception as e:
        print(f"Error getting conversation count: {e}")
        return 0


async def get_user_sessions_wrapper(user_id: str):
    """
    Get all chat sessions for a user with title and preview.
    Groups conversations by thread_id and returns summary info.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        List of session dictionaries with id, title, preview, timestamp
    """
    try:
        sessions = await get_sessions(user_id)
        # Convert datetime objects to ISO strings for JSON serialization
        for session in sessions:
            if session.get("timestamp"):
                session["timestamp"] = session["timestamp"].isoformat()
        return sessions
    except Exception as e:
        print(f"Error getting user sessions: {e}")
        return []

