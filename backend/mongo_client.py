import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "repair_assistant")

if not MONGODB_URL:
    raise RuntimeError("Missing MONGODB_URL in environment variables")

# Async client for FastAPI async operations
async_client = AsyncIOMotorClient(MONGODB_URL)
async_db = async_client[DATABASE_NAME]

# Sync client for non-async operations (if needed)
sync_client = MongoClient(MONGODB_URL)
sync_db = sync_client[DATABASE_NAME]

# Collection references
users_collection = async_db["users"]
conversations_collection = async_db["conversations"]
user_usage_collection = async_db["user_usage"]
refresh_tokens_collection = async_db["refresh_tokens"]


async def init_db():
    """
    Initialize database indexes for optimal performance.
    This should be called on application startup.
    """
    # Users collection indexes
    await users_collection.create_index("email", unique=True)
    
    # Conversations collection indexes
    await conversations_collection.create_index("user_id")
    await conversations_collection.create_index("thread_id")
    await conversations_collection.create_index("created_at")
    await conversations_collection.create_index([("thread_id", 1), ("created_at", 1)])
    
    # User usage collection indexes
    await user_usage_collection.create_index("user_id", unique=True)
    
    # Refresh tokens collection indexes
    await refresh_tokens_collection.create_index("token", unique=True)
    await refresh_tokens_collection.create_index("user_id")
    await refresh_tokens_collection.create_index("expires_at", expireAfterSeconds=0)  # TTL index
    
    print("✅ MongoDB indexes initialized successfully")


async def close_db():
    """Close database connections."""
    async_client.close()
    sync_client.close()
