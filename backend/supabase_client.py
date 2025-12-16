import os
from supabase import create_client, Client, ClientOptions
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in environment.")

# Supabase client with extended token expiration using ClientOptions
options = ClientOptions(
    auto_refresh_token=True,  # Auto-refresh tokens before expiry
    persist_session=True,      # Persist session across requests
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY, options)
