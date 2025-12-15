# Chat Session Management - Quick Reference

## 🎯 Session Management Features

All chat endpoints now include automatic session management with conversation persistence.

### How It Works

1. **Automatic Message Saving**: Every user message and assistant response is saved to the `conversations` table
2. **Thread-Based Sessions**: Each user has a unique thread: `thread_id = f"user-{user_id}"`
3. **Conversation Continuity**: Messages are retrieved on each request to maintain context
4. **Token Tracking**: All LLM calls automatically track token usage per user

---

## 📡 Available Endpoints

### 1. **POST /chat**
Standard chat with session persistence

**Request:**
```json
{
  "message": "How do I fix my iPhone screen?"
}
```

**Response:**
```json
{
  "response": "To fix your iPhone screen...",
  "thread_id": "user-abc123"
}
```

**What happens:**
1. ✅ User message saved to database
2. ✅ Conversation history loaded
3. ✅ LLM processes with full context
4. ✅ Assistant response saved to database
5. ✅ Token usage tracked

---

### 2. **POST /chat/stream**
Streaming chat with session persistence

**Request:**
```json
{
  "message": "How do I fix my iPhone screen?"
}
```

**Stream Events:**
```
data: {"type": "status", "content": "🔍 Searching iFixit..."}
data: {"type": "token", "content": "To"}
data: {"type": "token", "content": " fix"}
data: {"type": "done", "thread_id": "user-abc123"}
```

**What happens:**
1. ✅ User message saved to database
2. ✅ Conversation history loaded
3. ✅ LLM streams response token-by-token
4. ✅ Complete response saved to database
5. ✅ Token usage tracked

---

### 3. **GET /chat/history**
View conversation history

**Request:**
```
GET /chat/history?limit=50
```

**Response:**
```json
{
  "thread_id": "user-abc123",
  "message_count": 12,
  "messages": [
    {
      "role": "user",
      "content": "How do I fix my phone?",
      "timestamp": "2025-12-15T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "I can help you with that...",
      "timestamp": "2025-12-15T10:00:05Z"
    }
  ]
}
```

---

### 4. **DELETE /chat/history**
Clear conversation history

**Request:**
```
DELETE /chat/history
```

**Response:**
```json
{
  "success": true,
  "message": "Chat history cleared successfully",
  "thread_id": "user-abc123"
}
```

**Use cases:**
- Start fresh conversation
- Reset context
- Clear sensitive data

---

### 5. **GET /chat/sessions**
Get session statistics

**Request:**
```
GET /chat/sessions
```

**Response:**
```json
{
  "user_id": "abc123",
  "thread_id": "user-abc123",
  "total_messages": 45,
  "total_tokens_used": 12500,
  "session_start": "2025-12-01T08:00:00Z",
  "last_activity": "2025-12-15T14:30:00Z"
}
```

---

## 🔄 Session Flow Example

### Conversation Flow:
```
1. User: "My PS5 broke"
   → Saved to DB as ("user", "My PS5 broke")
   
2. System loads history:
   → Returns all previous messages for context
   
3. LLM processes:
   → Uses full conversation history
   → Searches iFixit
   → Generates response
   
4. Assistant: "I found repair guides..."
   → Saved to DB as ("assistant", "I found repair guides...")
   
5. Token usage tracked:
   → Updates user_usage table
   → Tracks cumulative tokens
```

---

## 💾 Database Schema

### conversations table
```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### user_usage table
```sql
CREATE TABLE user_usage (
    user_id TEXT PRIMARY KEY,
    total_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔍 Querying Sessions

### View all user conversations
```sql
SELECT * FROM conversations 
WHERE thread_id = 'user-abc123' 
ORDER BY created_at DESC;
```

### Count messages per user
```sql
SELECT user_id, COUNT(*) as message_count 
FROM conversations 
GROUP BY user_id 
ORDER BY message_count DESC;
```

### Get active sessions (last 24 hours)
```sql
SELECT DISTINCT user_id, thread_id, MAX(created_at) as last_active
FROM conversations 
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY user_id, thread_id
ORDER BY last_active DESC;
```

### Token usage leaderboard
```sql
SELECT user_id, total_tokens 
FROM user_usage 
ORDER BY total_tokens DESC 
LIMIT 10;
```

---

## 🎨 Frontend Integration

### React Example (Non-streaming)
```javascript
const sendMessage = async (message) => {
  const response = await fetch('/chat', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message })
  });
  
  const data = await response.json();
  console.log(data.response);
  console.log('Thread:', data.thread_id);
};
```

### React Example (Streaming)
```javascript
const sendMessageStream = async (message) => {
  const response = await fetch('/chat/stream', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message })
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const text = decoder.decode(value);
    const lines = text.split('\\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        
        if (data.type === 'status') {
          setStatus(data.content);
        } else if (data.type === 'token') {
          appendToken(data.content);
        } else if (data.type === 'done') {
          console.log('Thread:', data.thread_id);
        }
      }
    }
  }
};
```

### Get History
```javascript
const getHistory = async () => {
  const response = await fetch('/chat/history?limit=50', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  setMessages(data.messages);
};
```

### Clear History
```javascript
const clearHistory = async () => {
  const response = await fetch('/chat/history', {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  if (data.success) {
    setMessages([]);
  }
};
```

---

## ✅ Session Management Benefits

1. **Conversation Continuity**: Users can return and continue previous conversations
2. **Context Awareness**: LLM has full conversation history for better responses
3. **Analytics**: Track user engagement and token usage
4. **Debugging**: Review conversation logs for issues
5. **User Experience**: Seamless multi-turn conversations

---

## 🔐 Security Notes

- All endpoints require authentication (`Depends(get_current_user)`)
- Users can only access their own conversations
- Thread IDs are user-specific: `f"user-{user_id}"`
- Consider adding RLS (Row Level Security) in Supabase

---

## 📊 Monitoring

### Check active sessions
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/chat/sessions
```

### View recent conversations
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/chat/history?limit=10
```

---

## 🎉 Complete Feature Set

✅ **Session Persistence**: Messages saved automatically  
✅ **Context Management**: Full conversation history loaded  
✅ **Token Tracking**: Usage tracked per user  
✅ **History Viewing**: Get past conversations  
✅ **Session Clearing**: Reset conversations  
✅ **Session Stats**: View usage analytics  
✅ **Streaming Support**: Token-by-token with sessions  
✅ **Tool Integration**: iFixit + Web Search with context  

**Your chat is now fully session-aware! 🚀**
