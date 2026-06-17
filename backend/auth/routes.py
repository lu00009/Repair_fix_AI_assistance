from fastapi import APIRouter, HTTPException, Depends
from auth.models import UserSignUp, UserLogin, TokenResponse, RefreshTokenRequest
from auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    verify_password,
    decode_token
)
from services.user_service import create_user, find_user_by_email, find_user_by_id
from postgres_client import get_db_connection
from auth.dependencies import get_current_user
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/signup", response_model=TokenResponse)
async def signup(user: UserSignUp):
    """
    Register a new user account.
    
    Args:
        user: User signup data (email and password)
        
    Returns:
        Access token, refresh token, and user info
        
    Raises:
        HTTPException: If user already exists or registration fails
    """
    try:
        # Create user in database
        user_doc = await create_user(user.email, user.password)
        
        # Generate tokens
        user_id = str(user_doc["id"])
        access_token = create_access_token(data={"sub": user_id, "email": user.email})
        refresh_token = create_refresh_token(data={"sub": user_id, "email": user.email})
        
        # Store refresh token in database (Postgres)
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO refresh_tokens (token, user_id, expires_at) VALUES (%s, %s, %s)",
                (refresh_token, user_id, datetime.utcnow() + timedelta(days=7))
            )
            conn.commit()
        finally:
            if conn:
                conn.close()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={
                "id": user_id,
                "email": user.email
            },
            message="User registered successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    """
    Login with email and password.
    
    Args:
        user: User login credentials
        
    Returns:
        Access token, refresh token, and user info
        
    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        # Find user by email
        user_doc = await find_user_by_email(user.email)
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify password
        if not verify_password(user.password, user_doc["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Generate tokens
        user_id = str(user_doc["id"])
        access_token = create_access_token(data={"sub": user_id, "email": user_doc["email"]})
        refresh_token = create_refresh_token(data={"sub": user_id, "email": user_doc["email"]})
        
        # Store refresh token in database (Postgres)
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO refresh_tokens (token, user_id, expires_at) VALUES (%s, %s, %s)",
                (refresh_token, user_id, datetime.utcnow() + timedelta(days=7))
            )
            conn.commit()
        finally:
            if conn:
                conn.close()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={
                "id": user_id,
                "email": user_doc["email"]
            },
            message="Login successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")


@router.get("/me")
async def me(user=Depends(get_current_user)):
    """
    Get current user information from JWT token.
    
    Args:
        user: Current authenticated user from dependency
        
    Returns:
        User information
    """
    return {
        "id": user.id,
        "email": user.email
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh an expired access token using a refresh token.
    
    Args:
        request: Refresh token request
        
    Returns:
        New access token and refresh token
        
    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    try:
        # Decode refresh token
        payload = decode_token(request.refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Check if token exists in database (Postgres)
        conn = None
        user_id = payload.get("sub")
        email = payload.get("email")
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM refresh_tokens WHERE token = %s AND user_id = %s",
                (request.refresh_token, user_id)
            )
            token_row = cur.fetchone()
            if not token_row:
                raise HTTPException(status_code=401, detail="Refresh token not found or revoked")
            
            # Generate new tokens
            new_access_token = create_access_token(data={"sub": user_id, "email": email})
            new_refresh_token = create_refresh_token(data={"sub": user_id, "email": email})
            
            # Delete old refresh token and store new one
            cur.execute("DELETE FROM refresh_tokens WHERE token = %s", (request.refresh_token,))
            cur.execute(
                "INSERT INTO refresh_tokens (token, user_id, expires_at) VALUES (%s, %s, %s)",
                (new_refresh_token, user_id, datetime.utcnow() + timedelta(days=7))
            )
            conn.commit()
            
            return TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                user={
                    "id": user_id,
                    "email": email
                },
                message="Token refreshed successfully"
            )
        finally:
            if conn:
                conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")


@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    """
    Logout user by revoking their refresh tokens.
    
    Args:
        user: Current authenticated user
        
    Returns:
        Success message
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Delete all refresh tokens for this user
        cur.execute("DELETE FROM refresh_tokens WHERE user_id = %s", (user.id,))
        conn.commit()
        return {
            "message": "Logged out successfully"
        }
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")
    finally:
        if conn:
            conn.close()

