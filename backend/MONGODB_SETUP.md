# MongoDB Atlas Setup Guide

This guide will help you set up MongoDB Atlas for the Repair Assistant application.

## Step 1: Create MongoDB Atlas Account

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Click "Try Free" or "Sign In"
3. Create an account or sign in with Google/GitHub

## Step 2: Create a Cluster

1. After logging in, click "Build a Database"
2. Choose **M0 FREE** tier (perfect for development)
3. Select a cloud provider and region (choose one closest to you)
4. Name your cluster (e.g., "repair-assistant-cluster")
5. Click "Create"

## Step 3: Create Database User

1. In the Security section, click "Database Access"
2. Click "Add New Database User"
3. Choose "Password" authentication
4. Set username and password (save these securely!)
5. Set user privileges to "Read and write to any database"
6. Click "Add User"

## Step 4: Configure Network Access

1. In the Security section, click "Network Access"
2. Click "Add IP Address"
3. For development, click "Allow Access from Anywhere" (0.0.0.0/0)
   - **Note**: For production, restrict to specific IP addresses
4. Click "Confirm"

## Step 5: Get Connection String

1. Go to "Database" in the left sidebar
2. Click "Connect" on your cluster
3. Choose "Connect your application"
4. Select "Python" as driver and version "3.12 or later"
5. Copy the connection string (looks like: `mongodb+srv://username:<password>@cluster.xxxxx.mongodb.net/`)
6. Replace `<password>` with your actual database user password
7. Add the database name at the end: `mongodb+srv://username:password@cluster.xxxxx.mongodb.net/repair_assistant`

## Step 6: Update Environment Variables

Add to your `.env` file:

```bash
# MongoDB Configuration
MONGODB_URL=mongodb+srv://username:password@cluster.xxxxx.mongodb.net/repair_assistant
MONGODB_DATABASE=repair_assistant

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production

# Optional: Bypass auth for development
BYPASS_AUTH=false
```

**Important**: Generate a secure JWT secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Database Schema

The application will automatically create these collections with indexes on startup:

### Collections

#### `users`
- Stores user accounts with hashed passwords
- Indexes: `email` (unique)

#### `conversations`
- Stores chat messages and conversation history
- Indexes: `user_id`, `thread_id`, `created_at`, compound index on `(thread_id, created_at)`

#### `user_usage`
- Tracks token usage per user
- Indexes: `user_id` (unique)

#### `refresh_tokens`
- Stores refresh tokens for authentication
- Indexes: `token` (unique), `user_id`, `expires_at` (TTL index for auto-deletion)

## Verification

After setup, start your application:

```bash
cd /home/lelo/projects/Repair_fix_AI_assistance
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
✅ MongoDB indexes initialized successfully
✅ Application started successfully
```

Check the health endpoint:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "auth_mode": "production",
  "database": "MongoDB Atlas",
  "mongodb_status": "configured"
}
```

## Troubleshooting

### Connection Issues

**Error**: `ServerSelectionTimeoutError`
- Check your IP address is whitelisted in Network Access
- Verify connection string is correct
- Ensure password doesn't contain special characters (or URL-encode them)

**Error**: `Authentication failed`
- Verify database user credentials
- Check username and password in connection string

### Index Creation Issues

**Error**: `Index already exists with different options`
- Drop the existing indexes in MongoDB Atlas dashboard
- Restart the application

## MongoDB Atlas Dashboard

Access your data:
1. Go to MongoDB Atlas dashboard
2. Click "Browse Collections"
3. View your `repair_assistant` database
4. Explore collections: `users`, `conversations`, `user_usage`, `refresh_tokens`

## Security Best Practices

1. **Never commit `.env` file** - It contains sensitive credentials
2. **Use strong JWT secret** - Generate with `secrets.token_urlsafe(32)`
3. **Restrict network access** - In production, whitelist specific IPs only
4. **Rotate credentials** - Change passwords and secrets regularly
5. **Enable MongoDB Atlas alerts** - Get notified of unusual activity
