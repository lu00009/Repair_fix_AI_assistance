from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.auth.jwt_utils import decode_token
from backend.services.user_service import find_user_by_id
import os
from typing import Optional

# Security scheme for Bearer token
security = HTTPBearer(auto_error=False)


class MockUser:
    """Mock user for development/testing without authentication."""
    def __init__(self):
        self.id = "00000000-0000-0000-0000-000000000000"
        self.email = "dev@example.com"


class AuthenticatedUser:
    """Authenticated user from JWT token."""
    def __init__(self, user_id: str, email: str):
        self.id = user_id
        self.email = email


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthenticatedUser:
    """
    Get current user from JWT authorization token.
    In development mode (BYPASS_AUTH=true), returns a mock user.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Authenticated user object
        
    Raises:
        HTTPException: If token is invalid or missing
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
        
        # Decode and validate JWT token
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token. Please login again."
            )
        
        # Extract user info from token
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload"
            )
        
        # Verify user exists in database
        user_doc = await find_user_by_id(user_id)
        if not user_doc:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )
        
        return AuthenticatedUser(user_id=user_id, email=email)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )

