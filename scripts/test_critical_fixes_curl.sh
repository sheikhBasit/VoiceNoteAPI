#!/bin/bash
# ============================================================================
# Backend Critical Fixes - Curl Test Suite
#
# Tests all endpoints affected by the critical fixes:
# - Sync upload-batch endpoint
# - Admin wallet freeze/unfreeze/toggle-freeze
# - Admin revenue report
# - Admin create organization (Pydantic validation)
# - Admin analytics endpoints
#
# Usage: bash scripts/test_critical_fixes_curl.sh [API_URL]
# ============================================================================

set -euo pipefail

API_URL="${1:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@voicenote.ai}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
TOTAL=0

# ============================================================================
# Helper functions
# ============================================================================

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

# ============================================================================
# Authentication
# ============================================================================

echo ""
echo "============================================"
echo "  VoiceNote API - Critical Fixes Curl Tests"
echo "============================================"
echo ""
echo "API URL: $API_URL"
echo ""

echo "--- Authenticating as admin ---"
LOGIN_RESP=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/api/v1/users/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"${ADMIN_EMAIL}\", \"password\": \"${ADMIN_PASSWORD}\"}")

HTTP_CODE=$(echo "$LOGIN_RESP" | tail -1)
BODY=$(echo "$LOGIN_RESP" | head -n -1)

if [ "$HTTP_CODE" -ne 200 ]; then
    echo -e "${RED}Authentication failed (HTTP $HTTP_CODE). Using dev bypass token.${NC}"
    TOKEN="dev_admin-test-user"
else
    TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
    if [ -z "$TOKEN" ]; then
        echo -e "${YELLOW}No token in response. Using dev bypass token.${NC}"
        TOKEN="dev_admin-test-user"
    fi
fi

AUTH_HEADER="Authorization: Bearer ${TOKEN}"
echo ""

# ============================================================================
# 1. Sync Endpoint Tests
# ============================================================================

echo "--- 1. Sync Endpoint ---"

# Test sync endpoint exists (should return 401 without auth, not 404)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_URL}/api/v1/sync/upload-batch")
if [ "$STATUS" -ne 404 ]; then
    pass_test "Sync upload-batch endpoint is routable (not 404)"
else
    fail_test "Sync upload-batch endpoint is routable" "!= 404" "$STATUS"
fi

# Test sync with auth but no files (should return 400 or 422)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_URL}/api/v1/sync/upload-batch" \
    -H "$AUTH_HEADER")
if [ "$STATUS" -eq 400 ] || [ "$STATUS" -eq 422 ]; then
    pass_test "Sync upload-batch rejects empty upload ($STATUS)"
else
    fail_test "Sync upload-batch rejects empty upload" "400 or 422" "$STATUS"
fi

echo ""

# ============================================================================
# 2. Admin Wallet Toggle-Freeze
# ============================================================================

echo "--- 2. Admin Wallet Toggle-Freeze ---"

# Test toggle-freeze on nonexistent wallet (should return 404)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${API_URL}/api/v1/admin/wallets/nonexistent-user/toggle-freeze" \
    -H "$AUTH_HEADER")
check_status "Toggle-freeze nonexistent wallet returns 404" 404 "$STATUS"

# Test toggle-freeze without auth (should return 401 or 403)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${API_URL}/api/v1/admin/wallets/some-user/toggle-freeze")
if [ "$STATUS" -eq 401 ] || [ "$STATUS" -eq 403 ]; then
    pass_test "Toggle-freeze requires authentication ($STATUS)"
else
    fail_test "Toggle-freeze requires authentication" "401 or 403" "$STATUS"
fi

echo ""

# ============================================================================
# 3. Admin Wallet Freeze/Unfreeze
# ============================================================================

echo "--- 3. Admin Wallet Freeze/Unfreeze ---"

# Test freeze on nonexistent wallet
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${API_URL}/api/v1/admin/wallets/nonexistent-user/freeze?reason=test" \
    -H "$AUTH_HEADER")
check_status "Freeze nonexistent wallet returns 404" 404 "$STATUS"

# Test unfreeze on nonexistent wallet
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${API_URL}/api/v1/admin/wallets/nonexistent-user/unfreeze" \
    -H "$AUTH_HEADER")
check_status "Unfreeze nonexistent wallet returns 404" 404 "$STATUS"

# Test freeze without auth
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${API_URL}/api/v1/admin/wallets/some-user/freeze?reason=test")
if [ "$STATUS" -eq 401 ] || [ "$STATUS" -eq 403 ]; then
    pass_test "Freeze requires authentication ($STATUS)"
else
    fail_test "Freeze requires authentication" "401 or 403" "$STATUS"
fi

echo ""

# ============================================================================
# 4. Admin Revenue Report
# ============================================================================

echo "--- 4. Admin Revenue Report ---"

NOW_MS=$(python3 -c "import time; print(int(time.time() * 1000))")
THIRTY_DAYS_AGO=$((NOW_MS - 2592000000))

# Test revenue report endpoint exists and returns data
RESP=$(curl -s -w "\n%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/reports/revenue?start_date=${THIRTY_DAYS_AGO}&end_date=${NOW_MS}" \
    -H "$AUTH_HEADER")
STATUS=$(echo "$RESP" | tail -1)
check_status "Revenue report endpoint returns 200" 200 "$STATUS"

# Test revenue report without auth
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/reports/revenue?start_date=${THIRTY_DAYS_AGO}&end_date=${NOW_MS}")
if [ "$STATUS" -eq 401 ] || [ "$STATUS" -eq 403 ]; then
    pass_test "Revenue report requires authentication ($STATUS)"
else
    fail_test "Revenue report requires authentication" "401 or 403" "$STATUS"
fi

# Test revenue report missing required params
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/reports/revenue" \
    -H "$AUTH_HEADER")
check_status "Revenue report requires query params (422)" 422 "$STATUS"

echo ""

# ============================================================================
# 5. Admin Create Organization (Pydantic Validation)
# ============================================================================

echo "--- 5. Admin Create Organization ---"

# Test valid organization creation
ORG_ID="org_curl_$(date +%s)"
RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "${API_URL}/api/v1/admin/organizations" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"id\": \"${ORG_ID}\", \"name\": \"Curl Test Org\"}")
STATUS=$(echo "$RESP" | tail -1)
check_status "Create organization with valid data returns 201" 201 "$STATUS"

# Test missing 'name' field (Pydantic validation)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${API_URL}/api/v1/admin/organizations" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"id\": \"org_no_name\"}")
check_status "Create org missing name returns 422" 422 "$STATUS"

# Test missing 'id' field (Pydantic validation)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${API_URL}/api/v1/admin/organizations" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"No ID Org\"}")
check_status "Create org missing id returns 422" 422 "$STATUS"

# Test empty body
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${API_URL}/api/v1/admin/organizations" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{}")
check_status "Create org empty body returns 422" 422 "$STATUS"

# Test without auth
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "${API_URL}/api/v1/admin/organizations" \
    -H "Content-Type: application/json" \
    -d "{\"id\": \"org_unauth\", \"name\": \"Unauthorized Org\"}")
if [ "$STATUS" -eq 401 ] || [ "$STATUS" -eq 403 ]; then
    pass_test "Create organization requires authentication ($STATUS)"
else
    fail_test "Create organization requires authentication" "401 or 403" "$STATUS"
fi

echo ""

# ============================================================================
# 6. Admin Analytics Endpoints
# ============================================================================

echo "--- 6. Admin Analytics Endpoints ---"

# Usage analytics
RESP=$(curl -s -w "\n%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/analytics/usage?start_date=${THIRTY_DAYS_AGO}&end_date=${NOW_MS}&group_by=day" \
    -H "$AUTH_HEADER")
STATUS=$(echo "$RESP" | tail -1)
check_status "Usage analytics returns 200" 200 "$STATUS"

# Growth analytics
RESP=$(curl -s -w "\n%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/analytics/growth" \
    -H "$AUTH_HEADER")
STATUS=$(echo "$RESP" | tail -1)
check_status "Growth analytics returns 200" 200 "$STATUS"

# User behavior analytics
RESP=$(curl -s -w "\n%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/analytics/user-behavior" \
    -H "$AUTH_HEADER")
STATUS=$(echo "$RESP" | tail -1)
check_status "User behavior analytics returns 200" 200 "$STATUS"

# System metrics
RESP=$(curl -s -w "\n%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/analytics/system-metrics" \
    -H "$AUTH_HEADER")
STATUS=$(echo "$RESP" | tail -1)
check_status "System metrics returns 200" 200 "$STATUS"

echo ""

# ============================================================================
# 7. Audit Logs
# ============================================================================

echo "--- 7. Audit Logs ---"

RESP=$(curl -s -w "\n%{http_code}" -X GET \
    "${API_URL}/api/v1/admin/audit-logs?limit=10" \
    -H "$AUTH_HEADER")
STATUS=$(echo "$RESP" | tail -1)
check_status "Audit logs returns 200" 200 "$STATUS"

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
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED test(s) failed.${NC}"
    exit 1
fi
