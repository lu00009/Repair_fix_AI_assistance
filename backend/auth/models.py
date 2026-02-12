from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserSignUp(BaseModel):
    """User registration request model."""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class UserLogin(BaseModel):
    """User login request model."""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
    message: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


class UserInDB(BaseModel):
    """User model as stored in MongoDB."""
    id: str
    email: str
    password_hash: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "password_hash": "$2b$12$...",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }


class UserResponse(BaseModel):
    """User response model (without sensitive data)."""
    id: str
    email: str
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "created_at": "2024-01-01T00:00:00"
            }
        }
