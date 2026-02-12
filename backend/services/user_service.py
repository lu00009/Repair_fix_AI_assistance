from typing import Optional
from datetime import datetime
from bson import ObjectId
from backend.mongo_client import users_collection
from backend.auth.jwt_utils import hash_password


async def create_user(email: str, password: str) -> dict:
    """
    Create a new user in the database.
    
    Args:
        email: User's email address
        password: Plain text password (will be hashed)
        
    Returns:
        Created user document
        
    Raises:
        ValueError: If user with email already exists
    """
    # Check if user already exists
    existing_user = await find_user_by_email(email)
    if existing_user:
        raise ValueError("User with this email already exists")
    
    # Hash password
    password_hash = hash_password(password)
    
    # Create user document
    user_doc = {
        "email": email,
        "password_hash": password_hash,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Insert into database
    result = await users_collection.insert_one(user_doc)
    
    # Return user with ID
    user_doc["_id"] = result.inserted_id
    return user_doc


async def find_user_by_email(email: str) -> Optional[dict]:
    """
    Find a user by email address.
    
    Args:
        email: User's email address
        
    Returns:
        User document if found, None otherwise
    """
    user = await users_collection.find_one({"email": email})
    return user


async def find_user_by_id(user_id: str) -> Optional[dict]:
    """
    Find a user by their ID.
    
    Args:
        user_id: User's unique identifier
        
    Returns:
        User document if found, None otherwise
    """
    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        return user
    except Exception:
        return None


async def update_user(user_id: str, update_data: dict) -> bool:
    """
    Update user information.
    
    Args:
        user_id: User's unique identifier
        update_data: Dictionary of fields to update
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        update_data["updated_at"] = datetime.utcnow()
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    except Exception:
        return False


async def user_exists(email: str) -> bool:
    """
    Check if a user exists by email.
    
    Args:
        email: User's email address
        
    Returns:
        True if user exists, False otherwise
    """
    count = await users_collection.count_documents({"email": email})
    return count > 0
