# 🚀 Quick Start Guide

## ✅ Server is Running!

**URL:** http://localhost:8000  
**API Docs:** http://localhost:8000/docs

---

## 🔓 TESTING WITHOUT AUTHENTICATION

### Quick Start (Development Mode)
Add to `.env`:
```bash
BYPASS_AUTH=true
```

Then test immediately:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I fix my iPhone screen?"}'
```

**No authorization header needed!**

---

## 🎯 How to Start the Server

From the project root directory:
```bash
./start_server.sh
```

Or manually:
```bash
cd /home/lelo/projects/Repair_fix_AI_assistance
source venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

⚠️ **Important:** Always run from the project root, NOT from the backend directory!

---

## 📡 Available Endpoints

### 1. **Standard Chat** (No Streaming)
```bash
POST /chat
Headers: Authorization: Bearer <token>
Body: {"message": "How do I fix my iPhone screen?"}
```

### 2. **Streaming Chat** (Token-by-token + Tool Status)
```bash
POST /chat/stream
Headers: Authorization: Bearer <token>
Body: {"message": "How do I fix my iPhone screen?"}
```

### 3. **Authentication**
```bash
POST /signup - Create new account
POST /login - Get access token
```

---

## 🧪 Test the Implementation

### Test iFixit Tools (Python)
```python
# Run from project root
cd /home/lelo/projects/Repair_fix_AI_assistance
source venv/bin/activate
python3

# In Python shell:
from backend.agents.tools_ifixit import find_device, list_guides, get_guide

# Find a device
result = find_device.invoke({"query": "iPhone 13"})
print(result)

# List repair guides
result = list_guides.invoke({"device_title": "iPhone 13"})
print(result)

# Get specific guide details
result = get_guide.invoke({"guide_id": 126317})
print(result)
```

### Test Streaming (curl)
```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I fix my PS5?"}' \
  --no-buffer
```

---

## ✅ Implementation Complete

### iFixit API Integration
- ✅ **Endpoint 1:** `find_device()` - Search devices
- ✅ **Endpoint 2:** `list_guides()` - List repair guides
- ✅ **Endpoint 3:** `get_guide()` - Get repair instructions
- ✅ **Cleanup Functions:** Strip metadata, keep only text + images

### Fallback Web Search
- ✅ **Tavily API** (if `TAVILY_API_KEY` set)
- ✅ **DuckDuckGo API** (automatic fallback)
- ✅ Auto-triggers on iFixit "Not Found"

### Streaming
- ✅ **Token-by-token** LLM response
- ✅ **Tool execution status** (🔍 Searching, 📋 Loading, etc.)
- ✅ **Server-Sent Events** (SSE) format

### Token Tracking & Context Management
- ✅ **Automatic token tracking** per user
- ✅ **Context summarization** at 20+ messages
- ✅ **User-specific threads** with conversation history
- ✅ **Supabase persistence** (user_usage, conversations tables)

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app entry point |
| `backend/agents/graph.py` | LangGraph agent with token tracking |
| `backend/agents/tools_ifixit.py` | iFixit API tools with cleanup |
| `backend/agents/tools_search.py` | Fallback web search |
| `backend/chat/routes.py` | Chat endpoints (standard + streaming) |
| `backend/models/usage.py` | Token usage tracking |
| `backend/setup_database.sql` | Database schema |
| `start_server.sh` | Server startup script |

---

## 🔧 Configuration

### Required Environment Variables (.env)
```bash
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
```

### Optional
```bash
TAVILY_API_KEY=your_tavily_key  # For better web search
```

---

## 📊 Database Setup

Run in Supabase SQL Editor:
```sql
-- See backend/setup_database.sql for complete schema

CREATE TABLE user_usage (
    user_id TEXT PRIMARY KEY,
    total_tokens INTEGER DEFAULT 0
);

CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'backend'"
**Fix:** Run uvicorn from project root, not backend directory
```bash
cd /home/lelo/projects/Repair_fix_AI_assistance
./start_server.sh
```

### Server won't start
```bash
# Kill existing processes
pkill -f uvicorn

# Check if port 8000 is in use
lsof -i :8000

# Start fresh
./start_server.sh
```

### Import errors
```bash
# Reinstall dependencies
source venv/bin/activate
pip install -r backend/requirements.txt
```

---

## 📚 Documentation

- **Complete Implementation:** `backend/IMPLEMENTATION.md`
- **iFixit & Streaming:** `backend/IFIXIT_STREAMING_DOCS.md`
- **Quick Start:** `QUICKSTART.md` (this file)

---

## 🎉 Ready to Go!

Your Repair Assistant API is now fully functional with:
- iFixit API integration with cleanup functions
- Fallback web search (Tavily/DuckDuckGo)
- Token-by-token streaming with tool status
- Automatic token tracking
- Context management with summarization
- User-specific conversation threads

**Start fixing things! 🔧**
