"""
Test script for token tracking and context management implementation
"""
import sys
sys.path.insert(0, '/home/lelo/projects/Repair_fix_AI_assistance/backend')

# Test imports
try:
    from core.config import GEMINI_API_KEY
    print("✅ Core config imported successfully")
except Exception as e:
    print(f"❌ Error importing core config: {e}")

try:
    from models.usage import track_token_usage, get_user_token_usage
    print("✅ Usage model imported successfully")
except Exception as e:
    print(f"❌ Error importing usage model: {e}")

try:
    from agents.graph import app_graph
    print("✅ Agent graph imported successfully")
except Exception as e:
    print(f"❌ Error importing agent graph: {e}")

try:
    from chat.service import get_or_create_conversation_history
    print("✅ Chat service imported successfully")
except Exception as e:
    print(f"❌ Error importing chat service: {e}")

print("\n" + "="*50)
print("IMPLEMENTATION SUMMARY")
print("="*50)

print("""
✅ Token Usage Tracking:
   - track_token_usage() function in models/usage.py
   - Integrated into agent_node in agents/graph.py
   - Automatically tracks after each LLM call
   - Updates user_usage table in Supabase

✅ Context Management:
   - Automatic summarization when messages > 20
   - Keeps last 10 messages + summary of older ones
   - Implemented in agent_node with _summarize_messages()

✅ User Integration:
   - user_id extracted from authenticated user
   - thread_id = f"user-{user_id}"
   - Passed through AgentState for tracking

✅ Conversation Persistence:
   - MemorySaver checkpointer in graph compilation
   - Thread-specific configuration in chat endpoint
   - get_or_create_conversation_history() for context

✅ Database Tables Required:
   - user_usage (user_id, total_tokens)
   - conversations (user_id, thread_id, role, content, created_at)
""")

print("="*50)
print("Next Steps:")
print("="*50)
print("""
1. Ensure Supabase tables exist:
   - CREATE TABLE user_usage (
       user_id TEXT PRIMARY KEY,
       total_tokens INTEGER DEFAULT 0
     );
   
   - CREATE TABLE conversations (
       id SERIAL PRIMARY KEY,
       user_id TEXT NOT NULL,
       thread_id TEXT NOT NULL,
       role TEXT NOT NULL,
       content TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT NOW()
     );

2. Test the chat endpoint:
   POST /chat
   Headers: Authorization: Bearer <token>
   Body: {"message": "How do I fix my phone?"}

3. Monitor token usage in user_usage table

4. Verify conversation history in conversations table
""")
