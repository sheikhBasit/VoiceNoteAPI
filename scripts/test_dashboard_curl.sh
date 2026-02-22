#!/bin/bash
# ============================================================================
# Dashboard API Integration - Curl Test Suite
#
# Tests all backend API endpoints used by the Next.js admin dashboard.
# These endpoints are the ones called by the dashboard hooks (useUsers,
# useDashboard, useAnalytics, useBilling, useModeration, useAudit,
# useSettings, useOperations).
#
# Usage: bash scripts/test_dashboard_curl.sh [API_URL]
# ============================================================================

set -euo pipefail

API_URL="${1:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@voicenote.ai}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

PASSED=0
FAILED=0
TOTAL=0

pass_test() {
    PASSED=$((PASSED + 1))
    TOTAL=$((TOTAL + 1))
    echo -e "  ${GREEN}PASS${NC} $1"
}

fail_test() {
    FAILED=$((FAILED + 1))
    TOTAL=$((TOTAL + 1))
    echo -e "  ${RED}FAIL${NC} $1 (expected: $2, got: $3)"
}

check_status() {
    local test_name="$1"
    local expected_status="$2"
    local actual_status="$3"

    if [ "$actual_status" -eq "$expected_status" ]; then
        pass_test "$test_name"
    else
        fail_test "$test_name" "$expected_status" "$actual_status"
    fi
}

check_not_404() {
    local test_name="$1"
    local actual_status="$2"

    if [ "$actual_status" -ne 404 ]; then
        pass_test "$test_name (HTTP $actual_status)"
    else
        fail_test "$test_name" "!= 404" "$actual_status"
    fi
}

# ============================================================================
# Authentication
# ============================================================================

echo ""
echo "============================================"
echo "  Dashboard API - Curl Test Suite"
echo "============================================"
echo ""
echo "API URL: $API_URL"
echo ""

echo "--- Authenticating ---"
LOGIN_RESP=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/api/v1/users/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"${ADMIN_EMAIL}\", \"password\": \"${ADMIN_PASSWORD}\"}")

HTTP_CODE=$(echo "$LOGIN_RESP" | tail -1)
BODY=$(echo "$LOGIN_RESP" | head -n -1)

if [ "$HTTP_CODE" -ne 200 ]; then
    echo -e "${YELLOW}Login failed (HTTP $HTTP_CODE). Using dev bypass token.${NC}"
    TOKEN="dev_admin-test-user"
else
    TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
    if [ -z "$TOKEN" ]; then
        echo -e "${YELLOW}No token in response. Using dev bypass token.${NC}"
        TOKEN="dev_admin-test-user"
    fi
fi

AUTH="Authorization: Bearer ${TOKEN}"
echo ""

NOW_MS=$(python3 -c "import time; print(int(time.time() * 1000))")
THIRTY_DAYS_AGO=$((NOW_MS - 2592000000))

# ============================================================================
# 1. Dashboard Overview (useDashboardOverview hook)
# ============================================================================

echo "--- 1. Dashboard Overview ---"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/dashboard/overview" -H "$AUTH")
check_status "GET /admin/dashboard/overview" 200 "$STATUS"

echo ""

# ============================================================================
# 2. User Management (useUsers hook)
# ============================================================================

echo "--- 2. User Management ---"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/users?page=1&limit=20" -H "$AUTH")
check_status "GET /admin/users (paginated)" 200 "$STATUS"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/users?page=1&limit=20&search=test" -H "$AUTH")
check_status "GET /admin/users (with search)" 200 "$STATUS"

# Test unauthenticated access
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/users?page=1&limit=20")
if [ "$STATUS" -eq 401 ] || [ "$STATUS" -eq 403 ]; then
    pass_test "GET /admin/users requires auth ($STATUS)"
else
    fail_test "GET /admin/users requires auth" "401 or 403" "$STATUS"
fi

echo ""

# ============================================================================
# 3. Analytics (useAnalytics hooks)
# ============================================================================

echo "--- 3. Analytics ---"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/analytics/usage?start_date=${THIRTY_DAYS_AGO}&end_date=${NOW_MS}&group_by=day" \
    -H "$AUTH")
check_status "GET /admin/analytics/usage" 200 "$STATUS"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/analytics/growth" -H "$AUTH")
check_status "GET /admin/analytics/growth" 200 "$STATUS"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/reports/revenue?start_date=${THIRTY_DAYS_AGO}&end_date=${NOW_MS}" \
    -H "$AUTH")
check_status "GET /admin/reports/revenue" 200 "$STATUS"

echo ""

# ============================================================================
# 4. Billing & Wallets (useBilling hooks)
# ============================================================================

echo "--- 4. Billing & Wallets ---"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/wallets" -H "$AUTH")
check_status "GET /admin/wallets" 200 "$STATUS"

# Toggle-freeze on nonexistent (404 expected)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${API_URL}/api/v1/admin/wallets/nonexistent/toggle-freeze" -H "$AUTH")
check_status "POST /admin/wallets/toggle-freeze (nonexistent)" 404 "$STATUS"

echo ""

# ============================================================================
# 5. Content Moderation (useModeration hooks)
# ============================================================================

echo "--- 5. Content Moderation ---"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/notes/audit?limit=20&offset=0" -H "$AUTH")
check_not_404 "GET /admin/notes/audit" "$STATUS"

echo ""

# ============================================================================
# 6. Audit Logs (useAudit hooks)
# ============================================================================

echo "--- 6. Audit Logs ---"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/audit-logs?limit=20&offset=0" -H "$AUTH")
check_status "GET /admin/audit-logs" 200 "$STATUS"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/audit-logs?action=MAKE_ADMIN&limit=10" -H "$AUTH")
check_status "GET /admin/audit-logs (filtered)" 200 "$STATUS"

echo ""

# ============================================================================
# 7. Settings (useSettings hooks)
# ============================================================================

echo "--- 7. Settings ---"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/settings/ai" -H "$AUTH")
check_status "GET /admin/settings/ai" 200 "$STATUS"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/api-keys" -H "$AUTH")
check_status "GET /admin/api-keys" 200 "$STATUS"

echo ""

# ============================================================================
# 8. Operations (useOperations hooks)
# ============================================================================

echo "--- 8. Operations ---"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/celery/tasks/active" -H "$AUTH")
check_not_404 "GET /admin/celery/tasks/active" "$STATUS"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/transactions?limit=5" -H "$AUTH")
check_not_404 "GET /admin/transactions" "$STATUS"

echo ""

# ============================================================================
# 9. System Health
# ============================================================================

echo "--- 9. System Health ---"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/system-health" -H "$AUTH")
check_not_404 "GET /admin/system-health" "$STATUS"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/db-stats" -H "$AUTH")
check_not_404 "GET /admin/db-stats" "$STATUS"

echo ""

# ============================================================================
# 10. User Auth Endpoints (used by dashboard login)
# ============================================================================

echo "--- 10. User Auth ---"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/users/me" -H "$AUTH")
check_status "GET /users/me" 200 "$STATUS"

# Test login with invalid credentials
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${API_URL}/api/v1/users/login" \
    -H "Content-Type: application/json" \
    -d '{"email": "invalid@test.com", "password": "wrong"}')
if [ "$STATUS" -eq 400 ] || [ "$STATUS" -eq 401 ] || [ "$STATUS" -eq 404 ]; then
    pass_test "POST /users/login rejects invalid creds ($STATUS)"
else
    fail_test "POST /users/login rejects invalid creds" "400/401/404" "$STATUS"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "============================================"
echo "  RESULTS"
echo "============================================"
echo ""
echo -e "  Total:  $TOTAL"
echo -e "  ${GREEN}Passed: $PASSED${NC}"
echo -e "  ${RED}Failed: $FAILED${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All dashboard curl tests passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED test(s) failed.${NC}"
    exit 1
fi
