from fastapi import APIRouter, Depends
from backend.auth.dependencies import get_current_user
from backend.supabase_client import supabase

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/usage")
async def get_user_usage(user=Depends(get_current_user)):
    """Get token usage for current user"""
    user_id = user.id
    
    # Get total token usage
    result = supabase.table("user_usage").select("*").eq("user_id", user_id).execute()
    
    total_input_tokens = 0
    total_output_tokens = 0
    
    for record in result.data:
        total_input_tokens += record.get("input_tokens", 0)
        total_output_tokens += record.get("output_tokens", 0)
    
    total_tokens = total_input_tokens + total_output_tokens
    
    return {
        "total_tokens": total_tokens,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "request_count": len(result.data)
    }
