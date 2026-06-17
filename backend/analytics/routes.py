from fastapi import APIRouter, Depends, HTTPException
from backend.auth.dependencies import get_current_user
from backend.postgres_client import get_db_connection
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/usage")
async def get_user_usage(user=Depends(get_current_user)):
    """Get token usage for current user from Postgres"""
    user_id = user.id
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT input_tokens, output_tokens FROM user_usage WHERE user_id = %s",
            (user_id,)
        )
        records = cur.fetchall()
        
        total_input_tokens = 0
        total_output_tokens = 0
        
        for record in records:
            total_input_tokens += record.get("input_tokens", 0)
            total_output_tokens += record.get("output_tokens", 0)
        
        total_tokens = total_input_tokens + total_output_tokens
        
        return {
            "total_tokens": total_tokens,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "request_count": len(records)
        }
    except Exception as e:
        logger.error(f"Error fetching usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch usage data")
    finally:
        if conn:
            conn.close()
