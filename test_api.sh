#!/bin/bash

# ==================================================================
# REPAIR ASSISTANT API - TEST SCRIPT
# ==================================================================

echo "🔧 Repair Assistant API - Quick Test"
echo "======================================"
echo ""

# Server URL
API_URL="http://localhost:8000"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ==================================================================
# 1. HEALTH CHECK
# ==================================================================
echo -e "${YELLOW}1. Testing Health Endpoint (No Auth)${NC}"
echo "GET $API_URL/health"
curl -s $API_URL/health | python3 -m json.tool 2>/dev/null || echo "Server not responding"
echo ""
echo ""

# ==================================================================
# 2. ROOT ENDPOINT
# ==================================================================
echo -e "${YELLOW}2. Testing Root Endpoint (No Auth)${NC}"
echo "GET $API_URL/"
curl -s $API_URL/ | python3 -m json.tool 2>/dev/null || echo "Server not responding"
echo ""
echo ""

# ==================================================================
# 3. CHAT ENDPOINT - WITHOUT AUTH (if BYPASS_AUTH=true)
# ==================================================================
echo -e "${YELLOW}3. Testing Chat WITHOUT Authentication${NC}"
echo "POST $API_URL/chat"
echo "This will work if BYPASS_AUTH=true in .env"
echo ""

curl -X POST $API_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I fix my iPhone 13 screen?"}' \
  2>/dev/null | python3 -m json.tool || echo -e "${RED}Failed - Auth required or server error${NC}"

echo ""
echo ""

# ==================================================================
# 4. CHAT ENDPOINT - WITH AUTH TOKEN
# ==================================================================
echo -e "${YELLOW}4. Testing Chat WITH Authentication${NC}"
echo "POST $API_URL/chat"
echo ""

# Try to read token from environment or prompt
if [ -z "$AUTH_TOKEN" ]; then
    echo -e "${RED}No AUTH_TOKEN set${NC}"
    echo "To test with auth:"
    echo "  1. Login first: curl -X POST $API_URL/login -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\",\"password\":\"password\"}'"
    echo "  2. Copy the access_token"
    echo "  3. Run: AUTH_TOKEN='your_token' ./test_api.sh"
else
    curl -X POST $API_URL/chat \
      -H "Authorization: Bearer $AUTH_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"message": "How do I fix my iPhone 13 screen?"}' \
      2>/dev/null | python3 -m json.tool || echo -e "${RED}Auth token invalid or server error${NC}"
fi

echo ""
echo ""

# ==================================================================
# INSTRUCTIONS
# ==================================================================
echo "======================================"
echo -e "${GREEN}✅ Testing Complete!${NC}"
echo ""
echo "To enable testing without authentication:"
echo "  1. Add to .env file: BYPASS_AUTH=true"
echo "  2. Restart server: ./start_server.sh"
echo "  3. Run this script again"
echo ""
echo "To test with real authentication:"
echo "  1. Ensure BYPASS_AUTH is not set (or =false)"
echo "  2. Login to get token:"
echo "     curl -X POST $API_URL/login \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"email\":\"test@example.com\",\"password\":\"password\"}'"
echo "  3. Use the access_token in requests"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo "======================================"
