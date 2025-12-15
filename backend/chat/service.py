from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from backend.supabase_client import supabase


def get_or_create_conversation_history(user_id: str, thread_id: str) -> List[BaseMessage]:
    """
    Retrieve conversation history for a user's thread from Supabase.
    
    Args:
        user_id: The user's unique identifier
        thread_id: The conversation thread identifier (e.g., "user-{user_id}")
        
    Returns:
        List of messages in the conversation history
    """
    try:
        # Query conversation history from Supabase
        result = supabase.table("conversations").select("*").eq(
            "thread_id", thread_id
        ).order("created_at", desc=False).execute()
        
        if not result.data:
            return []
        
        # Convert stored messages to LangChain format
        messages = []
        for record in result.data:
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


def save_message_to_history(user_id: str, thread_id: str, role: str, content: str) -> None:
    """
    Save a message to the conversation history in Supabase.
    
    Args:
        user_id: The user's unique identifier
        thread_id: The conversation thread identifier
        role: Message role ("user" or "assistant")
        content: Message content
    """
    try:
        supabase.table("conversations").insert({
            "user_id": user_id,
            "thread_id": thread_id,
            "role": role,
            "content": content
        }).execute()
    except Exception as e:
        print(f"Error saving message to history: {e}")


def get_conversation_count(user_id: str, thread_id: str) -> int:
    """
    Get the number of messages in a conversation thread.
    
    Args:
        user_id: The user's unique identifier
        thread_id: The conversation thread identifier
        
    Returns:
        Number of messages in the thread
    """
    try:
        result = supabase.table("conversations").select(
            "id", count="exact"
        ).eq("thread_id", thread_id).execute()
        
        return result.count if result.count else 0
        
    except Exception as e:
        print(f"Error getting conversation count: {e}")
        return 0
