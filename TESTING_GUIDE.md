# Testing Guide - ChatGPT-like Session Management

## Quick Start

### 1. Start Backend
```bash
cd /home/lelo/projects/Repair_fix_AI_assistance
source venv/bin/activate
cd backend
python main.py
```

Backend runs on: `http://localhost:8000`

### 2. Start Frontend
```bash
cd /home/lelo/projects/Repair_fix_AI_assistance/frontend
pnpm install
pnpm dev
```

Frontend runs on: `http://localhost:5173`

## Test Scenarios

### ✅ Scenario 1: New Chat Session
**Steps:**
1. Open app, login
2. Click "New chat" button
3. Send message: "How do I fix my iPhone 13 screen?"
4. Verify:
   - Message appears immediately
   - Response streams token-by-token
   - Session appears in sidebar with title
   - Session shows at TOP of list

**Expected Backend Logs:**
```
INFO: /chat/stream called user_id=<uuid> thread_id=thread-<uuid> msg='How do I fix my iPhone 13 screen?'
```

**Expected Database:**
```sql
SELECT * FROM conversations WHERE thread_id = 'thread-<uuid>';
-- Should show 2 rows: user message + assistant response
```

---

### ✅ Scenario 2: Continue Existing Chat
**Steps:**
1. With active session open (from Scenario 1)
2. Send another message: "What tools do I need?"
3. Verify:
   - Previous messages still visible
   - New message appends to conversation
   - Session stays at top of sidebar
   - Preview updates with latest message

**Expected:**
- Same `thread_id` used for all messages
- Message history grows (4 messages total now)

---

### ✅ Scenario 3: Switch Between Sessions
**Steps:**
1. Click "New chat"
2. Send message: "How do I repair PlayStation 5?"
3. Note: Now have 2 sessions in sidebar
4. Click on first session (iPhone repair)
5. Verify:
   - Messages switch to iPhone conversation
   - Correct thread_id highlighted in sidebar
6. Click second session (PS5 repair)
7. Verify:
   - Messages switch to PS5 conversation

**Expected:**
- Each session loads correct message history
- No mixing of messages between sessions
- Active session highlighted with `bg-chat-hover`

---

### ✅ Scenario 4: Persistence After Refresh
**Steps:**
1. With multiple active sessions
2. Refresh browser (F5 or Cmd+R)
3. Verify:
   - All sessions appear in sidebar
   - No messages displayed initially (empty state)
4. Click a session
5. Verify:
   - Full message history loads
   - Correct thread_id selected

**Expected:**
- GET /chat/sessions returns all sessions
- GET /chat/history?thread_id=X returns messages

---

### ✅ Scenario 5: Logout and Login
**Steps:**
1. With active sessions, click "Log out"
2. Login again with same credentials
3. Verify:
   - All sessions still in sidebar
   - Can click and load any session
   - Can continue conversations

**Expected:**
- JWT token cleared and re-issued
- Sessions persist in database
- User ID matches, can access all threads

---

### ✅ Scenario 6: Multiple Tabs
**Steps:**
1. Open app in Tab 1, create session A
2. Open app in Tab 2 (same user)
3. Create session B in Tab 2
4. Switch to Tab 1, check sidebar
5. Click "New chat" to refresh sessions
6. Verify:
   - Session B appears in Tab 1 sidebar
   - Both tabs see all sessions

**Expected:**
- Sessions shared across tabs (same user)
- Each tab independent state
- Backend single source of truth

---

### ✅ Scenario 7: Clear All History
**Steps:**
1. With multiple sessions
2. Click "Clear conversations"
3. Confirm prompt
4. Verify:
   - All sessions removed from sidebar
   - Messages cleared
   - Empty state shown
5. Send new message
6. Verify:
   - New session created

**Expected:**
```
DELETE /chat/history
→ Deletes ALL rows for user_id
→ Sessions list becomes empty
```

---

### ✅ Scenario 8: Session Ordering
**Steps:**
1. Create 3 sessions: A, B, C (in that order)
2. Verify sidebar order: C, B, A (newest first)
3. Click session A (oldest)
4. Send new message in A
5. Verify:
   - Session A moves to top
   - Order now: A, C, B

**Expected:**
- GET /chat/sessions returns sorted by timestamp DESC
- Frontend displays in received order
- Updates move session to top

---

### ✅ Scenario 9: Long Conversations
**Steps:**
1. Create new session
2. Send 20+ messages back and forth
3. Verify:
   - All messages load when clicking session
   - Scrolling works smoothly
   - No performance issues
4. Switch to another session and back
5. Verify:
   - Full history still loads

**Expected:**
- Pagination limit: 50 messages by default
- Can increase with `?limit=100`
- Frontend scrolls to bottom on load

---

### ✅ Scenario 10: Concurrent Sessions
**Steps:**
1. Open session A
2. Start typing message (don't send)
3. Click session B
4. Verify:
   - Unsent message discarded (expected)
   - Session B loads correctly
5. Send message in session B
6. Click back to session A
7. Verify:
   - Session A unchanged

**Expected:**
- Input cleared on session switch
- No message leakage between sessions

---

## API Testing with curl

### Create New Chat
```bash
TOKEN="your_jwt_token"

curl -X POST http://localhost:8000/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I fix my iPhone?"}' \
  --no-buffer
```

### Continue Existing Chat
```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What tools do I need?", "thread_id": "thread-abc123"}' \
  --no-buffer
```

### Get Sessions
```bash
curl http://localhost:8000/chat/sessions \
  -H "Authorization: Bearer $TOKEN"
```

### Get Session History
```bash
curl "http://localhost:8000/chat/history?thread_id=thread-abc123" \
  -H "Authorization: Bearer $TOKEN"
```

### Clear All History
```bash
curl -X DELETE http://localhost:8000/chat/history \
  -H "Authorization: Bearer $TOKEN"
```

---

## Database Verification

### Check Sessions
```sql
SELECT 
  thread_id,
  COUNT(*) as message_count,
  MIN(created_at) as started_at,
  MAX(created_at) as last_message_at
FROM conversations
WHERE user_id = '<user_uuid>'
GROUP BY thread_id
ORDER BY last_message_at DESC;
```

### Check Messages
```sql
SELECT 
  thread_id,
  role,
  LEFT(content, 50) as preview,
  created_at
FROM conversations
WHERE user_id = '<user_uuid>'
  AND thread_id = 'thread-abc123'
ORDER BY created_at ASC;
```

### Verify Isolation
```sql
-- Should return 0 (users can't see each other's threads)
SELECT COUNT(*)
FROM conversations
WHERE thread_id = 'thread-abc123'
  AND user_id != '<owner_user_id>';
```

---

## Common Issues & Fixes

### Issue: Sessions not appearing in sidebar
**Check:**
- Backend logs for errors
- Network tab: GET /chat/sessions returns 200?
- Response contains sessions array?
- Frontend console errors?

**Fix:**
- Verify Supabase connection
- Check user_id matches in database
- Ensure JWT token valid

---

### Issue: Session click doesn't load messages
**Check:**
- Network tab: GET /chat/history?thread_id=X returns 200?
- Messages array in response?
- Thread belongs to logged-in user?

**Fix:**
- Verify thread_id matches in database
- Check ownership (user_id)
- Look for frontend console errors

---

### Issue: New messages create multiple sessions
**Check:**
- Backend returns thread_id in SSE 'done' event?
- Frontend captures receivedThreadId correctly?
- currentThreadId state persists?

**Fix:**
- Ensure frontend sends thread_id on subsequent messages
- Check for state reset bugs

---

### Issue: Sessions not ordered correctly
**Check:**
- Backend GET /chat/sessions query has ORDER BY?
- Frontend respects order from API?

**Fix:**
```python
# Backend service.py
sessions.sort(key=lambda s: s["timestamp"], reverse=True)
```

---

## Performance Benchmarks

**Expected Response Times:**
- GET /chat/sessions: < 100ms
- GET /chat/history: < 200ms
- POST /chat/stream (first token): < 2s
- Session switch: < 300ms

**Database Queries:**
- Should use indexes
- No full table scans
- EXPLAIN ANALYZE if slow

---

## Debug Mode

### Enable Detailed Logging

**Backend:**
```python
# In backend/chat/routes.py
logger.setLevel(logging.DEBUG)
```

**Frontend:**
```typescript
// In api.ts
console.log('SSE event:', parsed);
```

### Monitor SSE Stream
Open Chrome DevTools → Network → Filter: stream
- Should see chunks arriving
- Check for connection drops
- Verify 'done' event received

---

## Success Criteria

✅ Can create unlimited sessions  
✅ Each session isolated with unique thread_id  
✅ Sessions persist after refresh/logout  
✅ Can switch between sessions instantly  
✅ Messages load correctly per session  
✅ Newest sessions appear first  
✅ Optimistic UI updates work  
✅ No race conditions or message mixing  
✅ Authentication enforced  
✅ Performance meets benchmarks  

---

**Last Updated:** December 16, 2025
