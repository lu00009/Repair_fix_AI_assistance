from typing import Optional
from backend.services.usage_service import (
    track_token_usage as track_usage,
    get_user_token_usage as get_usage
)


async def track_token_usage(user_id: str, tokens_used: int) -> None:
    """
    Track token usage for a user by updating the user_usage collection in MongoDB.
    
    Args:
        user_id: The user's unique identifier
        tokens_used: Number of tokens consumed in the LLM call
    """
    await track_usage(user_id, tokens_used)


async def get_user_token_usage(user_id: str) -> int:
    """
    Get the total token usage for a user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        Total tokens used by the user
    """
    return await get_usage(user_id)

