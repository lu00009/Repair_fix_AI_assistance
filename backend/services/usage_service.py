from typing import Optional
from datetime import datetime
from postgres_client import get_db_connection
import logging

logger = logging.getLogger(__name__)

async def track_token_usage(user_id: str, tokens_used: int) -> None:
    """
    Track token usage for a user by updating the user_usage table.
    
    Args:
        user_id: User's unique identifier
        tokens_used: Number of tokens consumed in the LLM call
    """
    await increment_token_usage(user_id, tokens_used)


async def get_user_token_usage(user_id: str) -> int:
    """
    Get the total token usage for a user.
    
    Args:
        user_id: User's unique identifier
        
    Returns:
        Total tokens used by the user
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT SUM(input_tokens + output_tokens) as total FROM user_usage WHERE user_id = %s",
            (user_id,)
        )
        row = cur.fetchone()
        return int(row["total"]) if row and row["total"] else 0
    except Exception as e:
        logger.error(f"Error getting token usage: {e}")
        return 0
    finally:
        if conn:
            conn.close()


async def increment_token_usage(user_id: str, tokens: int) -> bool:
    """
    Increment token usage in Postgres.
    
    Args:
        user_id: User's unique identifier
        tokens: Number of tokens to add
        
    Returns:
        True if successful, False otherwise
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # In this simplified model, we track tokens as input_tokens unless specified otherwise.
        # But for maintenance, we'll just add to input_tokens or maybe we should have a more refined model.
        # Given the previous MongoDB structure only had 'total_tokens', I'll just add to input_tokens.
        
        cur.execute(
            "INSERT INTO user_usage (user_id, input_tokens) VALUES (%s, %s)",
            (user_id, tokens)
        )
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error incrementing token usage: {e}")
        return False
    finally:
        if conn:
            conn.close()
