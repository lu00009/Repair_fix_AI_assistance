from typing import Optional
from backend.supabase_client import supabase


def track_token_usage(user_id: str, tokens_used: int) -> None:
    """
    Track token usage for a user by updating the user_usage table in Supabase.
    
    Args:
        user_id: The user's unique identifier
        tokens_used: Number of tokens consumed in the LLM call
    """
    try:
        # First, try to get existing usage
        result = supabase.table("user_usage").select("total_tokens").eq("user_id", user_id).execute()
        
        if result.data:
            # User exists, update total
            existing_tokens = result.data[0].get("total_tokens", 0)
            new_total = existing_tokens + tokens_used
        else:
            # New user, set initial total
            new_total = tokens_used
        
        # Upsert the data
        supabase.table("user_usage").upsert({
            "user_id": user_id,
            "total_tokens": new_total
        }).execute()
        
    except Exception as e:
        print(f"Error tracking token usage: {e}")
        # Don't fail the request if tracking fails


def get_user_token_usage(user_id: str) -> int:
    """
    Get the total token usage for a user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        Total tokens used by the user
    """
    try:
        result = supabase.table("user_usage").select("total_tokens").eq("user_id", user_id).execute()
        
        if result.data:
            return result.data[0].get("total_tokens", 0)
        return 0
        
    except Exception as e:
        print(f"Error getting token usage: {e}")
        return 0
