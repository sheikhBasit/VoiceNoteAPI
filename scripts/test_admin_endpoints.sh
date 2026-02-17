#!/bin/bash
# Admin Endpoints Curl Test Suite
# Tests all implemented admin endpoints (Phases 1-5)

set -e

API_URL="${API_URL:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-adminpass123}"

echo "========================================="
echo "Admin Endpoints Test Suite"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get admin token
echo "🔐 Getting admin token..."
ADMIN_TOKEN=$(curl -s -X POST "$API_URL/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
  | jq -r '.access_token' 2>/dev/null || echo "")

if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "null" ]; then
    echo -e "${RED}❌ Failed to get admin token${NC}"
    echo "Please ensure:"
    echo "  1. API is running at $API_URL"
    echo "  2. Admin user exists with email: $ADMIN_EMAIL"
    exit 1
fi

echo -e "${GREEN}✅ Admin token obtained${NC}"
echo ""

# Test counter
PASSED=0
FAILED=0

test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    
    echo -n "Testing: $name... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET "$API_URL$endpoint" \
            -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null || echo "000")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL$endpoint" \
            -H "Authorization: Bearer $ADMIN_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null || echo "000")
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE "$API_URL$endpoint" \
            -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null || echo "000")
    elif [ "$method" = "PATCH" ]; then
        response=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL$endpoint" \
            -H "Authorization: Bearer $ADMIN_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null || echo "000")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✅ PASS${NC} (HTTP $http_code)"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC} (HTTP $http_code)"
        ((FAILED++))
    fi
}

echo "========================================="
echo "PHASE 1: Dashboard & Metrics"
echo "========================================="
test_endpoint "Dashboard Overview" "GET" "/api/v1/admin/dashboard/overview"
test_endpoint "Real-time Metrics" "GET" "/api/v1/admin/metrics/realtime"
test_endpoint "System Health" "GET" "/api/v1/admin/system/health"
test_endpoint "List Tasks" "GET" "/api/v1/admin/tasks?limit=10"
echo ""

echo "========================================="
echo "PHASE 2: Operations"
echo "========================================="
test_endpoint "List API Keys" "GET" "/api/v1/admin/api-keys"
test_endpoint "API Key Health" "GET" "/api/v1/admin/api-keys/health"
test_endpoint "List Wallets" "GET" "/api/v1/admin/wallets?limit=10"
echo ""

echo "========================================="
echo "PHASE 3: Analytics"
echo "========================================="
END_DATE=$(date +%s)000
START_DATE=$(($(date +%s) - 2592000))000
test_endpoint "Usage Analytics" "GET" "/api/v1/admin/analytics/usage?start_date=$START_DATE&end_date=$END_DATE&group_by=day"
test_endpoint "Growth Analytics" "GET" "/api/v1/admin/analytics/growth"
test_endpoint "Revenue Report" "GET" "/api/v1/admin/reports/revenue?start_date=$START_DATE&end_date=$END_DATE"
test_endpoint "User Behavior" "GET" "/api/v1/admin/analytics/user-behavior"
test_endpoint "System Metrics" "GET" "/api/v1/admin/analytics/system-metrics"
echo ""

echo "========================================="
echo "PHASE 4: Celery & Jobs"
echo "========================================="
test_endpoint "Active Celery Tasks" "GET" "/api/v1/admin/celery/tasks/active"
test_endpoint "Pending Celery Tasks" "GET" "/api/v1/admin/celery/tasks/pending"
test_endpoint "Worker Stats" "GET" "/api/v1/admin/celery/workers/stats"
test_endpoint "Registered Tasks" "GET" "/api/v1/admin/celery/workers/tasks"
test_endpoint "Queue Info" "GET" "/api/v1/admin/celery/queues"
echo ""

echo "========================================="
echo "PHASE 5: User Management"
echo "========================================="
test_endpoint "Search Users" "GET" "/api/v1/admin/users/search?limit=10"
echo ""

echo "========================================="
echo "AUDIT & ACTIVITY LOGS"
echo "========================================="
test_endpoint "Recent Activity" "GET" "/api/v1/admin/activity/recent?hours=24&limit=10"
test_endpoint "Activity Stats" "GET" "/api/v1/admin/activity/stats?days=30"
test_endpoint "Activity Timeline" "GET" "/api/v1/admin/activity/timeline?days=7"
test_endpoint "Audit Logs" "GET" "/api/v1/admin/audit-logs?limit=20"
echo ""

echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Total: $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed${NC}"
    exit 1
fi
