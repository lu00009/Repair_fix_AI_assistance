from typing import Optional
from datetime import datetime
from backend.mongo_client import user_usage_collection


async def track_token_usage(user_id: str, tokens_used: int) -> None:
    """
    Track token usage for a user by updating the user_usage collection.
    Uses upsert to create or update the user's token count.
    
    Args:
        user_id: User's unique identifier
        tokens_used: Number of tokens consumed in the LLM call
    """
    try:
        # Get existing usage
        existing = await user_usage_collection.find_one({"user_id": user_id})
        
        if existing:
            # Update existing record
            new_total = existing.get("total_tokens", 0) + tokens_used
            await user_usage_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "total_tokens": new_total,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        else:
            # Create new record
            await user_usage_collection.insert_one({
                "user_id": user_id,
                "total_tokens": tokens_used,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
    except Exception as e:
        print(f"Error tracking token usage: {e}")
        # Don't fail the request if tracking fails


async def get_user_token_usage(user_id: str) -> int:
    """
    Get the total token usage for a user.
    
    Args:
        user_id: User's unique identifier
        
    Returns:
        Total tokens used by the user
    """
    try:
        usage = await user_usage_collection.find_one({"user_id": user_id})
        if usage:
            return usage.get("total_tokens", 0)
        return 0
    except Exception as e:
        print(f"Error getting token usage: {e}")
        return 0


async def increment_token_usage(user_id: str, tokens: int) -> bool:
    """
    Increment token usage using MongoDB's atomic increment operation.
    
    Args:
        user_id: User's unique identifier
        tokens: Number of tokens to add
        
    Returns:
        True if successful, False otherwise
    """
    try:
        result = await user_usage_collection.update_one(
            {"user_id": user_id},
            {
                "$inc": {"total_tokens": tokens},
                "$set": {"updated_at": datetime.utcnow()},
                "$setOnInsert": {
                    "user_id": user_id,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        print(f"Error incrementing token usage: {e}")
        return False
