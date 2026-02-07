#!/bin/bash

# Simple Curl Tests for Users Endpoints
# Tests core functionality without complex timing

set +e

BASE_URL="http://localhost:8000/api/v1"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local expected_status="$5"
    
    echo -ne "${YELLOW}Testing: $name... ${NC}"
    
    if [ -n "$data" ]; then
        http_code=$(curl -s -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" \
            -w "%{http_code}" \
            -o /tmp/response.json \
            -m 5)
    else
        http_code=$(curl -s -X "$method" "$BASE_URL$endpoint" \
            -w "%{http_code}" \
            -o /tmp/response.json \
            -m 5)
    fi
    
    if [ "$http_code" -eq "$expected_status" ] 2>/dev/null; then
        echo -e "${GREEN}✅ PASS ($http_code)${NC}"
        ((PASS++))
    else
        echo -e "${RED}❌ FAIL (Got $http_code, expected $expected_status)${NC}"
        ((FAIL++))
    fi
}

echo "================================"
echo "Users API - Curl Tests"
echo "================================"
echo ""

# Test 1: Create new user
echo "${YELLOW}1. Authentication Tests${NC}"
test_endpoint "POST /sync (new user)" "POST" "/users/sync" \
    '{"email":"test_'"$(date +%s)"'@example.com","name":"Test","device_id":"device1","device_model":"TestDevice","token":"token","timezone":"UTC"}' \
    200

# Test 2: Invalid email
test_endpoint "POST /sync (invalid email)" "POST" "/users/sync" \
    '{"email":"invalid","name":"Test","device_id":"device1","device_model":"TestDevice","token":"token","timezone":"UTC"}' \
    400

# Test 3: Missing device_id
test_endpoint "POST /sync (missing device)" "POST" "/users/sync" \
    '{"email":"test@example.com","name":"Test","device_id":"","device_model":"TestDevice","token":"token","timezone":"UTC"}' \
    400

echo ""
echo "${YELLOW}2. Public Endpoints${NC}"

# Test 4: Search users
test_endpoint "GET /search" "GET" "/users/search?query=test" "" 200

# Test 5: Search with invalid role
test_endpoint "GET /search (invalid role)" "GET" "/users/search?role=invalid_role" "" 400

echo ""
echo "${YELLOW}3. Profile Tests${NC}"

# Test 6: Get non-existent user
test_endpoint "GET /{user_id} (non-existent)" "GET" "/users/00000000-0000-0000-0000-000000000000" "" 404

echo ""
echo "================================"
echo "Results Summary"
echo "================================"
echo -e "✅ Passed: ${GREEN}$PASS${NC}"
echo -e "❌ Failed: ${RED}$FAIL${NC}"
TOTAL=$((PASS + FAIL))
if [ $TOTAL -gt 0 ]; then
    RATE=$((PASS * 100 / TOTAL))
    echo -e "📊 Rate: ${YELLOW}${RATE}%${NC}"
fi
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed${NC}"
    exit 1
fi
