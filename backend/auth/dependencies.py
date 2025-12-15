from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.supabase_client import supabase
import os
from typing import Optional

# Security scheme for Bearer token
security = HTTPBearer(auto_error=False)

class MockUser:
    """Mock user for development/testing without authentication."""
    def __init__(self):
        self.id = "dev-user-123"
        self.email = "dev@example.com"

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Get current user from authorization token.
    In development mode (BYPASS_AUTH=true), returns a mock user.
    """
    # Development bypass
    if os.getenv("BYPASS_AUTH", "false").lower() == "true":
        return MockUser()
    
    # Production authentication
    if not credentials:
        raise HTTPException(
            status_code=401, 
            detail="Authorization header required. Use format: 'Bearer YOUR_TOKEN'"
        )
    
    try:
        # Get token from credentials
        token = credentials.credentials
        
        response = supabase.auth.get_user(token)
        
        if not response or not response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token. Please login again."
            )
        
        return response.user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )
