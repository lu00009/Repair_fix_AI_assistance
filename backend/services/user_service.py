from typing import Optional
from datetime import datetime
from postgres_client import get_db_connection
from auth.jwt_utils import hash_password
import logging

logger = logging.getLogger(__name__)

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
    # Hash password
    password_hash = hash_password(password)
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert into database
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email, created_at, updated_at",
            (email, password_hash)
        )
        user_row = cur.fetchone()
        conn.commit()
        
        # Return user as dict
        return dict(user_row)
        
    except Exception as e:
        if conn:
            conn.rollback()
        if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
            raise ValueError("User with this email already exists")
        logger.error(f"Error creating user: {e}")
        raise
    finally:
        if conn:
            conn.close()


async def find_user_by_email(email: str) -> Optional[dict]:
    """
    Find a user by email address.
    
    Args:
        email: User's email address
        
    Returns:
        User document if found, None otherwise
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, email, password_hash, created_at, updated_at FROM users WHERE email = %s", (email,))
        user_row = cur.fetchone()
        return dict(user_row) if user_row else None
    except Exception as e:
        logger.error(f"Error finding user by email: {e}")
        return None
    finally:
        if conn:
            conn.close()


async def find_user_by_id(user_id: str) -> Optional[dict]:
    """
    Find a user by their ID.
    
    Args:
        user_id: User's unique identifier
        
    Returns:
        User document if found, None otherwise
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, email, created_at, updated_at FROM users WHERE id = %s", (user_id,))
        user_row = cur.fetchone()
        return dict(user_row) if user_row else None
    except Exception as e:
        logger.error(f"Error finding user by ID: {e}")
        return None
    finally:
        if conn:
            conn.close()


async def update_user(user_id: str, update_data: dict) -> bool:
    """
    Update user information.
    
    Args:
        user_id: User's unique identifier
        update_data: Dictionary of fields to update
        
    Returns:
        True if update successful, False otherwise
    """
    if not update_data:
        return False
        
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Prepare SET clause
        fields = []
        values = []
        for key, value in update_data.items():
            fields.append(f"{key} = %s")
            values.append(value)
        
        fields.append("updated_at = %s")
        values.append(datetime.utcnow())
        values.append(user_id)
        
        set_clause = ", ".join(fields)
        query = f"UPDATE users SET {set_clause} WHERE id = %s"
        
        cur.execute(query, tuple(values))
        updated = cur.rowcount > 0
        conn.commit()
        return updated
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error updating user: {e}")
        return False
    finally:
        if conn:
            conn.close()


async def user_exists(email: str) -> bool:
    """
    Check if a user exists by email.
    
    Args:
        email: User's email address
        
    Returns:
        True if user exists, False otherwise
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT EXISTS(SELECT 1 FROM users WHERE email = %s)", (email,))
        exists = cur.fetchone()['exists']
        return exists
    except Exception as e:
        logger.error(f"Error checking user existence: {e}")
        return False
    finally:
        if conn:
            conn.close()
