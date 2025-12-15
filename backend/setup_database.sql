-- SQL script to create required Supabase tables for token tracking and conversation history

-- Table for tracking user token usage
CREATE TABLE IF NOT EXISTS user_usage (
    user_id TEXT PRIMARY KEY,
    total_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_usage_user_id ON user_usage(user_id);

-- Table for storing conversation history
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_conversations_thread_id ON conversations(thread_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);

-- Optional: Add RLS (Row Level Security) policies if needed
-- ALTER TABLE user_usage ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Optional: Create policy to allow users to see only their own data
-- CREATE POLICY "Users can view own usage" ON user_usage
--     FOR SELECT USING (auth.uid()::text = user_id);

-- CREATE POLICY "Users can view own conversations" ON conversations
--     FOR SELECT USING (auth.uid()::text = user_id);
