import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NEON_URL = os.getenv("NEON_URL")

def get_db_connection():
    """Create a new PostgreSQL connection."""
    try:
        conn = psycopg2.connect(NEON_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to Neon: {e}")
        raise

def init_postgres():
    """Initialize Postgres database by creating necessary tables."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create refresh_tokens table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id SERIAL PRIMARY KEY,
                token TEXT NOT NULL,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                expires_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create user_usage table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_usage (
                id SERIAL PRIMARY KEY,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create conversations table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                step_image TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Add index for thread_id
        cur.execute("CREATE INDEX IF NOT EXISTS idx_conversations_thread_id ON conversations(thread_id);")

        # Create a mock dev user if BYPASS_AUTH is enabled to satisfy foreign key constraints
        if os.getenv("BYPASS_AUTH", "false").lower() == "true":
            dev_user_id = "00000000-0000-0000-0000-000000000000"
            cur.execute("SELECT id FROM users WHERE id = %s", (dev_user_id,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
                    (dev_user_id, "dev@example.com", "bypass-mock")
                )
                logger.info("Created mock dev user for bypass mode")

        conn.commit()
        logger.info("✅ Postgres tables initialized successfully")
        cur.close()
    except Exception as e:
        logger.error(f"Error initializing Postgres: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def close_db_connection(conn):
    """Close the database connection."""
    if conn:
        conn.close()
