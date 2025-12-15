import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in environment.")

# Supabase Python client expects the project URL (https://<ref>.supabase.co) and an anon/service key
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
