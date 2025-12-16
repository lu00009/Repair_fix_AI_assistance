# ChatGPT-like Session Architecture

## Overview

This application implements a production-ready, scalable ChatGPT-like chatbot with persistent multi-session support. Each conversation is isolated with unique thread IDs, and users can switch between conversations seamlessly.

## Core Features

### ✅ Multiple Chat Sessions
- Each conversation has a unique `thread_id` (format: `thread-<uuid>`)
- Users can maintain unlimited concurrent conversations
- Sessions are isolated and don't interfere with each other

### ✅ Persistent Storage
- All messages stored in Supabase `conversations` table
- Survives page refresh, tab close, and logout
- Messages include: `user_id`, `thread_id`, `role`, `content`, `created_at`

### ✅ Session Management
- **New Chat**: Creates new session with unique thread_id
- **Session List**: Sidebar shows all user sessions, sorted by most recent
- **Session Switching**: Click any session to load its complete message history
- **Session Preview**: Shows title (first user message) and last message preview

### ✅ Real-time Streaming
- Server-Sent Events (SSE) for token-by-token streaming
- Tool execution status updates
- Thread ID returned in completion event

### ✅ Production-Ready
- User authentication with JWT tokens
- Thread ownership verification (users can only access their own threads)
- Optimistic UI updates for instant feedback
- Clean architecture with separation of concerns

## Architecture

### Backend (`/backend`)

#### Thread Management
```python
# New conversation - backend generates unique ID
thread_id = request.thread_id or f"thread-{uuid.uuid4()}"

# Existing conversation - frontend sends thread_id
thread_id = request.thread_id  # e.g., "thread-abc123"
```

#### API Endpoints

##### `POST /chat/stream`
**Streaming chat with session support**
```json
{
  "message": "How do I fix my iPhone?",
  "thread_id": "thread-abc123"  // Optional: omit for new chats
}
```

**SSE Response:**
```
data: {"type": "status", "content": "Searching iFixit..."}
data: {"type": "token", "content": "To"}
data: {"type": "token", "content": " fix"}
data: {"type": "done", "thread_id": "thread-abc123"}
```

##### `GET /chat/history?thread_id=<id>`
**Load specific session messages**
```json
{
  "thread_id": "thread-abc123",
  "message_count": 10,
  "messages": [
    {
      "role": "user",
      "content": "How do I fix my iPhone?",
      "timestamp": "2025-12-16T10:30:00Z"
    },
    {
      "role": "assistant", 
      "content": "I'll help you with that...",
      "timestamp": "2025-12-16T10:30:15Z"
    }
  ]
}
```

##### `GET /chat/sessions`
**List all user sessions**
```json
{
  "sessions": [
    {
      "id": "thread-abc123",
      "title": "How do I fix my iPhone?",
      "preview": "I'll help you with that. First, identify...",
      "timestamp": "2025-12-16T10:30:15Z",
      "message_count": 10
    }
  ]
}
```

##### `DELETE /chat/history?thread_id=<id>`
**Clear specific session or all sessions**
- With `thread_id`: Deletes specific conversation
- Without `thread_id`: Deletes ALL user conversations

#### Data Model

**`conversations` table:**
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversations_user_thread 
ON conversations(user_id, thread_id, created_at);
```

### Frontend (`/frontend`)

#### State Management
```typescript
interface ChatSession {
  id: string;           // thread_id
  title: string;        // First 50 chars of first user message
  preview: string;      // Last 60 chars of last message
  timestamp: string;    // ISO timestamp of last message
  message_count: number;
}

const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
const [sessions, setSessions] = useState<ChatSession[]>([]);
const [messages, setMessages] = useState<Message[]>([]);
```

#### User Flows

**1. New Chat**
```
User clicks "New chat"
→ setCurrentThreadId(null)
→ setMessages([])
→ User sends message
→ Backend generates thread_id
→ Frontend receives thread_id in SSE 'done' event
→ setCurrentThreadId(receivedThreadId)
→ Session added to sidebar (optimistic + backend sync)
```

**2. Continue Existing Chat**
```
User has currentThreadId set
→ User sends message
→ Frontend includes thread_id in request
→ Backend appends to existing thread
→ Session updated in sidebar (moved to top)
```

**3. Switch Session**
```
User clicks session in sidebar
→ handleSessionClick(sessionId)
→ GET /chat/history?thread_id={sessionId}
→ setMessages(history)
→ setCurrentThreadId(sessionId)
→ Messages displayed
```

**4. Page Refresh / Reopen**
```
User refreshes or reopens app
→ Sidebar loads all sessions
→ No messages displayed (empty state)
→ User clicks session to restore conversation
```

## Session Persistence

### Survives
✅ Page refresh  
✅ Tab close  
✅ Browser restart  
✅ Logout/login  
✅ Multiple devices (same user account)  

### How It Works
1. **Storage**: All messages persisted to Supabase immediately
2. **Session List**: Fetched on mount from `/chat/sessions`
3. **Message History**: Loaded on-demand when user clicks session
4. **Authentication**: JWT token stored in localStorage

## Security

### Authentication
- JWT tokens with expiration
- Auto-logout on 401 responses
- Token sent in `Authorization: Bearer` header

### Authorization
- Thread ownership verified on all endpoints
- Users can only:
  - Read their own threads
  - Write to their own threads
  - Delete their own threads

### SQL Queries
```python
# Always verify user_id matches
result = supabase.table("conversations").select("*").eq(
    "thread_id", thread_id
).eq("user_id", user_id).execute()
```

## Scalability Considerations

### Database
- Indexed on `(user_id, thread_id, created_at)` for fast queries
- Pagination support with `limit` parameter
- Efficient sorting by timestamp (DESC for session list)

### Backend
- Stateless FastAPI server (horizontal scaling ready)
- SSE streaming reduces memory footprint
- LangGraph checkpointing for conversation memory

### Frontend
- Lazy loading: Messages loaded only when session clicked
- Optimistic UI updates for instant feedback
- Session list cached in React state

## Monitoring & Debugging

### Backend Logging
```python
logger.info(f"/chat/stream called user_id={user_id} thread_id={thread_id} msg='{request.message[:80]}'")
```

### Frontend Debugging
```typescript
console.error('Failed to load session:', error);
console.error('Failed to load sessions:', error);
```

### Health Checks
- Monitor Supabase connection
- Track SSE connection failures
- Log authentication errors

## Testing Checklist

- [ ] Create new chat → generates unique thread_id
- [ ] Send messages → persist to database
- [ ] Switch between sessions → loads correct messages
- [ ] Page refresh → sessions persist
- [ ] Logout/login → sessions persist
- [ ] Multiple tabs → isolated sessions
- [ ] Clear history → removes all sessions
- [ ] Session list sorted → newest first
- [ ] Long conversations → pagination works
- [ ] Concurrent messages → no race conditions

## Migration from Single Thread

**Before:**
```python
thread_id = f"user-{user_id}"  # All conversations shared same thread
```

**After:**
```python
thread_id = request.thread_id or f"thread-{uuid.uuid4()}"  # Unique per conversation
```

**Database Migration:**
```sql
-- Optional: Migrate existing data if needed
UPDATE conversations 
SET thread_id = 'thread-legacy-' || user_id 
WHERE thread_id LIKE 'user-%';
```

## Known Limitations

1. **Session Titles**: Generated from first message, not editable
2. **Session Deletion**: Individual session deletion not yet implemented (use clear all)
3. **Message Editing**: Not supported (messages are immutable)
4. **Session Search**: No full-text search across sessions yet

## Future Enhancements

- [ ] Session renaming
- [ ] Individual session deletion with confirmation
- [ ] Session folders/categories
- [ ] Full-text search across all sessions
- [ ] Export session as JSON/Markdown
- [ ] Share session (read-only link)
- [ ] Session analytics (message count, tokens used)
- [ ] Message reactions/bookmarks
- [ ] Conversation branching

---

**Last Updated:** December 16, 2025  
**Version:** 1.0  
**Status:** Production Ready ✅
