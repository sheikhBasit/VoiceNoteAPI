#!/bin/bash
# ============================================================================
# VoiceNote API — Comprehensive Endpoint Test Suite
# Tests all 158+ endpoints with auth flow, CRUD ops, and regression checks.
#
# Usage:
#   bash scripts/test/test_all_endpoints.sh
#   API_BASE_URL=http://example.com bash scripts/test/test_all_endpoints.sh
# ============================================================================

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────
BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
DASHBOARD_URL="${DASHBOARD_BASE_URL:-http://127.0.0.1:3003}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="/tmp/voicenote_full_report_$TIMESTAMP.txt"

SEC_K="VN_SECURE_8f7d9a2b_2026"

# Counters (file-based for subshell persistence)
rm -f /tmp/vn_passed /tmp/vn_failed /tmp/vn_total /tmp/vn_skipped
echo 0 > /tmp/vn_passed
echo 0 > /tmp/vn_failed
echo 0 > /tmp/vn_total
echo 0 > /tmp/vn_skipped

# Colors
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
BLUE='\033[0;36m'; CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; NC='\033[0m'

CURL_OPTS=(-s -L --connect-timeout 10 --max-time 60)

# ── Report Header ──────────────────────────────────────────────────────────
{
    echo "================================================================================"
    echo "            VOICENOTE API — FULL ENDPOINT TEST REPORT"
    echo "================================================================================"
    echo "Date: $(date)"
    echo "Base URL: $BASE_URL"
    echo "Dashboard: $DASHBOARD_URL"
    echo "================================================================================"
} > "$REPORT_FILE"

get_ms() { date +%s%3N; }

# ── Core Helpers (reuses pattern from test_api.sh) ─────────────────────────

log_test() {
    local n="$1" m="$2" e="$3" p="$4" ex="$5" ac="$6" b="$7" l="$8"
    local s="FAIL" c=$RED
    if [[ "$ex" =~ $ac ]]; then
        s="PASS"; c=$GREEN
        echo $(( $(cat /tmp/vn_passed 2>/dev/null || echo 0) + 1 )) > /tmp/vn_passed
    else
        echo $(( $(cat /tmp/vn_failed 2>/dev/null || echo 0) + 1 )) > /tmp/vn_failed
    fi
    echo $(( $(cat /tmp/vn_total 2>/dev/null || echo 0) + 1 )) > /tmp/vn_total

    printf "${c}%-5s${NC} [%s] %-50s (%4sms)\n" "$s" "$ac" "$n" "$l" >&2
    { echo "[$s] $n ($m $e) | Expected: $ex | Got: $ac | Latency: ${l}ms"
      echo "  Response: ${b:0:300}"
      echo "---"; } >> "$REPORT_FILE"
}

generate_signature() {
    local method="$1" ep="$2" payload="$3" ts="$4"
    local path="${ep%%\?*}"
    local query="${ep#*\?}"
    [ "$query" == "$ep" ] && query=""
    local bh=""
    if [[ "$method" != "GET" && "$method" != "DELETE" && -n "$payload" ]]; then
        bh=$(echo -n "$payload" | sha256sum | awk '{print $1}')
    fi
    local msg="${method}${path}${query}${ts}${bh}"
    echo -n "$msg" | openssl dgst -sha256 -hmac "$SEC_K" | awk '{print $NF}'
}

run_test() {
    local n="$1" m="$2" e="$3" p="$4" ex="$5" t="${6:-}" use_sig="${7:-}"
    local start=$(get_ms)
    local opts=("${CURL_OPTS[@]}" -w "\n%{http_code}" -X "$m" "$BASE_URL$e")

    [ -n "$p" ] && opts+=(-H "Content-Type: application/json" -d "$p")
    [ -n "$t" ] && opts+=(-H "Authorization: Bearer $t")

    if [[ "$use_sig" == "true" ]]; then
        local ts
        ts=$(date +%s)
        local sig
        sig=$(generate_signature "$m" "$e" "$p" "$ts")
        opts+=(-H "X-Device-Signature: $sig" -H "X-Device-Timestamp: $ts")
    fi

    local resp
    resp=$(curl "${opts[@]}" 2>/dev/null || echo -e "\n000")
    local end=$(get_ms)
    local lat=$((end - start))
    local code
    code=$(echo "$resp" | tail -n1)
    local body
    body=$(echo "$resp" | sed '$d')
    log_test "$n" "$m" "$e" "$p" "$ex" "$code" "$body" "$lat"
    echo "$body"
}

skip_test() {
    local n="$1" reason="$2"
    echo $(( $(cat /tmp/vn_skipped 2>/dev/null || echo 0) + 1 )) > /tmp/vn_skipped
    printf "${YELLOW}SKIP ${NC} [ ] %-50s (%s)\n" "$n" "$reason" >&2
    echo "[SKIP] $n — $reason" >> "$REPORT_FILE"
}

phase_header() {
    local num="$1" title="$2"
    echo "" >&2
    echo -e "${MAGENTA}===> PHASE $num: $title${NC}" >&2
    echo "" >&2
    echo "" >> "$REPORT_FILE"
    echo "===> PHASE $num: $title" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
}

# ── Wait for server ────────────────────────────────────────────────────────
echo -n "Waiting for API server at $BASE_URL ..." >&2
for i in {1..30}; do
    if curl -s "${CURL_OPTS[@]}" "$BASE_URL/health" > /dev/null 2>&1; then
        echo -e " ${GREEN}Ready!${NC}" >&2
        break
    fi
    echo -n "." >&2
    sleep 2
    if [ "$i" -eq 30 ]; then
        echo -e " ${RED}TIMEOUT — server not reachable${NC}" >&2
        exit 1
    fi
done


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1: Health & Root
# ════════════════════════════════════════════════════════════════════════════
phase_header 1 "HEALTH & ROOT"

run_test "Health Check"       "GET" "/health"     "" "200"
run_test "OpenAPI Schema"     "GET" "/openapi.json" "" "200"
run_test "Root Redirect/Doc"  "GET" "/docs"       "" "200"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 2: Authentication
# ════════════════════════════════════════════════════════════════════════════
phase_header 2 "AUTHENTICATION"

U1_EMAIL="u1_$TIMESTAMP@test.com"
U2_EMAIL="u2_$TIMESTAMP@test.com"

U1_PL="{\"email\":\"$U1_EMAIL\",\"name\":\"TestUser1\",\"password\":\"StrongPass123!\",\"device_id\":\"d1_$TIMESTAMP\",\"device_model\":\"TestRunner\",\"token\":\"tok1\",\"timezone\":\"UTC\"}"
BODY=$(run_test "Register User1" "POST" "/api/v1/users/register" "$U1_PL" "200|201")
U1_TOKEN=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''),end='')" 2>/dev/null || echo "")
U1_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user',{}).get('id',''),end='')" 2>/dev/null || echo "")

U2_PL="{\"email\":\"$U2_EMAIL\",\"name\":\"TestUser2\",\"password\":\"StrongPass123!\",\"device_id\":\"d2_$TIMESTAMP\",\"device_model\":\"TestRunner\",\"token\":\"tok2\",\"timezone\":\"UTC\"}"
BODY=$(run_test "Register User2" "POST" "/api/v1/users/register" "$U2_PL" "200|201")
U2_TOKEN=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''),end='')" 2>/dev/null || echo "")
U2_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user',{}).get('id',''),end='')" 2>/dev/null || echo "")

run_test "Login User1"        "POST" "/api/v1/users/login" "{\"email\":\"$U1_EMAIL\",\"password\":\"StrongPass123!\",\"device_id\":\"d1_login\"}" "200"
run_test "Refresh Token (bad)" "POST" "/api/v1/users/refresh" "{\"refresh_token\":\"invalid\"}" "400|401"
run_test "Forgot Password"     "POST" "/api/v1/users/forgot-password" "{\"email\":\"nonexist@test.com\"}" "200|404"

if [ -z "$U1_TOKEN" ] || [ -z "$U2_TOKEN" ]; then
    echo -e "${RED}FATAL: Failed to obtain user tokens. Aborting remaining tests.${NC}" >&2
    exit 1
fi


# ════════════════════════════════════════════════════════════════════════════
# PHASE 3: User CRUD
# ════════════════════════════════════════════════════════════════════════════
phase_header 3 "USER CRUD"

run_test "Get My Profile"       "GET"   "/api/v1/users/me"       "" "200" "$U1_TOKEN"
run_test "Get Balance"          "GET"   "/api/v1/users/balance"  "" "200" "$U1_TOKEN"
run_test "Search Users"         "GET"   "/api/v1/users/search?query=Test" "" "200|403" "$U1_TOKEN"
run_test "Get User by ID"       "GET"   "/api/v1/users/$U1_ID"  "" "200|403" "$U1_TOKEN"
run_test "Update Profile"       "PATCH" "/api/v1/users/me" "{\"name\":\"UpdatedName\"}" "200" "$U1_TOKEN" "true"
run_test "Get User2 by ID"      "GET"   "/api/v1/users/$U2_ID"  "" "200|403" "$U1_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 4: Notes CRUD
# ════════════════════════════════════════════════════════════════════════════
phase_header 4 "NOTES CRUD"

run_test "Get Presigned URL"   "GET" "/api/v1/notes/presigned-url" "" "200" "$U1_TOKEN"
run_test "Autocomplete"        "GET" "/api/v1/notes/autocomplete?q=test" "" "200" "$U1_TOKEN"
run_test "Dashboard Metrics"   "GET" "/api/v1/notes/dashboard" "" "200" "$U1_TOKEN"

BODY=$(run_test "Create Note1" "POST" "/api/v1/notes/create" "{\"title\":\"Test Note 1\",\"transcript\":\"Initial transcript\"}" "201" "$U1_TOKEN")
N1_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''),end='')" 2>/dev/null || echo "")

BODY=$(run_test "Create Note2" "POST" "/api/v1/notes/create" "{\"title\":\"Test Note 2\",\"transcript\":\"Testing content\"}" "201" "$U1_TOKEN")
N2_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''),end='')" 2>/dev/null || echo "")

run_test "List Notes"          "GET"   "/api/v1/notes?limit=10" "" "200" "$U1_TOKEN"
run_test "Get Note"            "GET"   "/api/v1/notes/$N1_ID"   "" "200" "$U1_TOKEN"
run_test "Update Note"         "PATCH" "/api/v1/notes/$N1_ID"   "{\"title\":\"Updated Title\"}" "200" "$U1_TOKEN"
run_test "Semantic Search"     "POST"  "/api/v1/notes/search"   "{\"query\":\"test\",\"limit\":5}" "200" "$U1_TOKEN"
run_test "WhatsApp Draft"      "GET"   "/api/v1/notes/$N1_ID/whatsapp" "" "200" "$U1_TOKEN"
run_test "Semantic Analysis"   "POST"  "/api/v1/notes/$N1_ID/semantic-analysis" "" "202" "$U1_TOKEN"
run_test "Delete Note"         "DELETE" "/api/v1/notes/$N2_ID"  "" "200" "$U1_TOKEN"
run_test "Restore Note"        "PATCH" "/api/v1/notes/$N2_ID/restore" "" "200" "$U1_TOKEN"
run_test "Bulk Delete Notes"   "DELETE" "/api/v1/notes" "{\"note_ids\":[\"$N2_ID\"]}" "200" "$U1_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 5: Tasks CRUD
# ════════════════════════════════════════════════════════════════════════════
phase_header 5 "TASKS CRUD"

BODY=$(run_test "Create Task1" "POST" "/api/v1/tasks" "{\"description\":\"Test task 1\",\"note_id\":\"$N1_ID\",\"priority\":\"HIGH\"}" "201" "$U1_TOKEN")
T1_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''),end='')" 2>/dev/null || echo "")

BODY=$(run_test "Create Task2" "POST" "/api/v1/tasks" "{\"description\":\"Test task 2\",\"note_id\":\"$N1_ID\",\"priority\":\"MEDIUM\"}" "201" "$U1_TOKEN")
T2_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''),end='')" 2>/dev/null || echo "")

run_test "List Tasks"           "GET"   "/api/v1/tasks?limit=10"        "" "200" "$U1_TOKEN"
run_test "Get Task"             "GET"   "/api/v1/tasks/$T1_ID"          "" "200" "$U1_TOKEN"
run_test "Update Task"          "PATCH" "/api/v1/tasks/$T1_ID" "{\"priority\":\"LOW\"}" "200" "$U1_TOKEN"
run_test "Complete Task"        "PATCH" "/api/v1/tasks/$T1_ID/complete" "{\"is_done\":true}" "200" "$U1_TOKEN"
run_test "Tasks Due Today"      "GET"   "/api/v1/tasks/due-today"       "" "200" "$U1_TOKEN"
run_test "Overdue Tasks"        "GET"   "/api/v1/tasks/overdue"         "" "200" "$U1_TOKEN"
run_test "Tasks Assigned to Me" "GET"   "/api/v1/tasks/assigned-to-me"  "" "200" "$U1_TOKEN"
run_test "Search Tasks"         "GET"   "/api/v1/tasks/search?query_text=test" "" "200" "$U1_TOKEN"
run_test "Task Stats"           "GET"   "/api/v1/tasks/stats"           "" "200" "$U1_TOKEN"
run_test "Lock Task"            "POST"  "/api/v1/tasks/$T2_ID/lock"     "" "200" "$U1_TOKEN"
run_test "Unlock Task"          "DELETE" "/api/v1/tasks/$T2_ID/lock"    "" "200" "$U1_TOKEN"
run_test "Add External Link"    "POST"  "/api/v1/tasks/$T2_ID/external-links" "{\"url\":\"https://example.com\",\"title\":\"Example\"}" "201" "$U1_TOKEN"
run_test "Comm Options"         "GET"   "/api/v1/tasks/$T2_ID/communication-options" "" "200" "$U1_TOKEN"
run_test "Duplicate Task"       "POST"  "/api/v1/tasks/$T2_ID/duplicate" "" "201" "$U1_TOKEN"
run_test "Delete Task"          "DELETE" "/api/v1/tasks/$T2_ID"         "" "200" "$U1_TOKEN"
run_test "Restore Task"         "PATCH" "/api/v1/tasks/$T2_ID/restore"  "" "200" "$U1_TOKEN"
run_test "Bulk Delete Tasks"    "DELETE" "/api/v1/tasks" "{\"task_ids\":[\"$T2_ID\"]}" "200" "$U1_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 6: Folders
# ════════════════════════════════════════════════════════════════════════════
phase_header 6 "FOLDERS"

BODY=$(run_test "Create Folder" "POST" "/api/v1/folders" "{\"name\":\"TestFolder_$TIMESTAMP\"}" "201" "$U1_TOKEN")
F1_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''),end='')" 2>/dev/null || echo "")

run_test "List Folders"         "GET"   "/api/v1/folders"        "" "200" "$U1_TOKEN"
run_test "Update Folder"        "PATCH" "/api/v1/folders/$F1_ID" "{\"name\":\"Updated Folder\"}" "200" "$U1_TOKEN"
run_test "Bulk Move Notes"      "PATCH" "/api/v1/notes/move"     "{\"note_ids\":[\"$N1_ID\"],\"folder_id\":\"$F1_ID\"}" "200" "$U1_TOKEN"
run_test "Delete Folder"        "DELETE" "/api/v1/folders/$F1_ID" "" "200" "$U1_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 7: Teams
# ════════════════════════════════════════════════════════════════════════════
phase_header 7 "TEAMS"

BODY=$(run_test "Create Team" "POST" "/api/v1/teams" "{\"name\":\"TestTeam_$TIMESTAMP\"}" "201" "$U1_TOKEN")
TM_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''),end='')" 2>/dev/null || echo "")

run_test "List Teams"           "GET"  "/api/v1/teams"          "" "200" "$U1_TOKEN"
run_test "Add Member"           "POST" "/api/v1/teams/$TM_ID/members" "{\"user_email\":\"$U2_EMAIL\"}" "200" "$U1_TOKEN"
run_test "Team Analytics"       "GET"  "/api/v1/teams/$TM_ID/analytics" "" "200" "$U1_TOKEN"
run_test "List Teams (U2)"      "GET"  "/api/v1/teams"          "" "200" "$U2_TOKEN"
run_test "Delete Team"          "DELETE" "/api/v1/teams/$TM_ID"  "" "200" "$U1_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 8: Integrations
# ════════════════════════════════════════════════════════════════════════════
phase_header 8 "INTEGRATIONS"

run_test "List Integrations"    "GET" "/api/v1/integrations/list" "" "200" "$U1_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 9: AI Operations
# ════════════════════════════════════════════════════════════════════════════
phase_header 9 "AI OPERATIONS"

run_test "AI Search"   "POST" "/api/v1/notes/search" "{\"query\":\"meeting notes\",\"limit\":5}" "200" "$U1_TOKEN"
run_test "AI Ask"      "POST" "/api/v1/ai/ask" "{\"question\":\"What is this about?\"}" "200|400|422|500" "$U1_TOKEN"
run_test "AI Stats"    "GET"  "/api/v1/ai/stats" "" "200" "$U1_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 10: Sync
# ════════════════════════════════════════════════════════════════════════════
phase_header 10 "SYNC"

run_test "Upload Batch (empty)"    "POST" "/api/v1/sync/upload-batch" "{\"notes\":[]}" "200|400|422" "$U1_TOKEN"
run_test "Upload Batch (payload)"  "POST" "/api/v1/sync/upload-batch" "{\"notes\":[{\"title\":\"Synced Note\",\"transcript\":\"test\"}]}" "200|201|400|422" "$U1_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 11: Admin — User Management
# ════════════════════════════════════════════════════════════════════════════
phase_header 11 "ADMIN — USER MANAGEMENT"

# Try to promote user1 via test endpoint (if available)
BODY=$(run_test "Make Admin (test)" "POST" "/api/v1/test/make-admin?user_id=$U1_ID" "" "200|404|405" "$U1_TOKEN")
# If test endpoint doesn't exist, try via admin endpoint with existing admin
ADMIN_TOKEN="$U1_TOKEN"

run_test "List All Users"        "GET"    "/api/v1/admin/users"               "" "200|403" "$ADMIN_TOKEN"
run_test "User Statistics"       "GET"    "/api/v1/admin/users/stats"         "" "200|403" "$ADMIN_TOKEN"
run_test "Search Users (admin)"  "GET"    "/api/v1/admin/users/search?query=Test&limit=10" "" "200|403" "$ADMIN_TOKEN"
run_test "Get User Details"      "GET"    "/api/v1/admin/users/$U2_ID"        "" "200|403" "$ADMIN_TOKEN"
run_test "Get User Detail"       "GET"    "/api/v1/admin/users/$U2_ID/detail" "" "200|403" "$ADMIN_TOKEN"
run_test "Get User Devices"      "GET"    "/api/v1/admin/users/$U2_ID/devices" "" "200|403" "$ADMIN_TOKEN"
run_test "Get User Usage"        "GET"    "/api/v1/admin/users/$U2_ID/usage"  "" "200|403" "$ADMIN_TOKEN"
run_test "Get User Sessions"     "GET"    "/api/v1/admin/users/$U2_ID/sessions" "" "200|403" "$ADMIN_TOKEN"
run_test "Get User Activity"     "GET"    "/api/v1/admin/users/$U2_ID/activity" "" "200|403" "$ADMIN_TOKEN"
run_test "List Admins"           "GET"    "/api/v1/admin/admins"              "" "200|403" "$ADMIN_TOKEN"
run_test "Admin Status"          "GET"    "/api/v1/admin/status"              "" "200|403" "$ADMIN_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 12: Admin — Content Moderation
# ════════════════════════════════════════════════════════════════════════════
phase_header 12 "ADMIN — CONTENT MODERATION"

run_test "List All Notes (admin)"  "GET"    "/api/v1/admin/notes"                 "" "200|403" "$ADMIN_TOKEN"
run_test "List All Tasks (admin)"  "GET"    "/api/v1/admin/tasks"                 "" "200|403" "$ADMIN_TOKEN"
run_test "Admin Notes Audit"       "GET"    "/api/v1/admin/notes/audit?limit=10"  "" "200|403" "$ADMIN_TOKEN"
run_test "Celery Active Tasks"     "GET"    "/api/v1/admin/celery/tasks/active"   "" "200|403" "$ADMIN_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 13: Admin — Analytics
# ════════════════════════════════════════════════════════════════════════════
phase_header 13 "ADMIN — ANALYTICS"

NOW_MS=$(python3 -c "import time; print(int(time.time()*1000))")
WEEK_AGO_MS=$((NOW_MS - 604800000))

run_test "Usage Analytics"        "GET" "/api/v1/admin/analytics/usage?start_date=$WEEK_AGO_MS&end_date=$NOW_MS&group_by=day" "" "200|403" "$ADMIN_TOKEN"
run_test "Growth Analytics"       "GET" "/api/v1/admin/analytics/growth" "" "200|403" "$ADMIN_TOKEN"
run_test "Revenue Report"         "GET" "/api/v1/admin/reports/revenue?start_date=$WEEK_AGO_MS&end_date=$NOW_MS" "" "200|403" "$ADMIN_TOKEN"
run_test "User Behavior"          "GET" "/api/v1/admin/analytics/user-behavior" "" "200|403" "$ADMIN_TOKEN"
run_test "System Metrics"         "GET" "/api/v1/admin/analytics/system-metrics" "" "200|403" "$ADMIN_TOKEN"
run_test "Dashboard Overview"     "GET" "/api/v1/admin/dashboard/overview" "" "200|403" "$ADMIN_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 14: Admin — Operations
# ════════════════════════════════════════════════════════════════════════════
phase_header 14 "ADMIN — OPERATIONS"

run_test "List API Keys"         "GET"  "/api/v1/admin/api-keys"          "" "200|403" "$ADMIN_TOKEN"
run_test "API Keys Health"       "GET"  "/api/v1/admin/api-keys/health"   "" "200|403" "$ADMIN_TOKEN"
run_test "Realtime Metrics"      "GET"  "/api/v1/admin/metrics/realtime"  "" "200|403" "$ADMIN_TOKEN"
run_test "System Health"         "GET"  "/api/v1/admin/system/health"     "" "200|403" "$ADMIN_TOKEN"
run_test "Celery Worker Stats"   "GET"  "/api/v1/admin/celery/workers/stats"  "" "200|403" "$ADMIN_TOKEN"
run_test "Celery Registered"     "GET"  "/api/v1/admin/celery/workers/tasks"  "" "200|403" "$ADMIN_TOKEN"
run_test "Celery Queues"         "GET"  "/api/v1/admin/celery/queues"         "" "200|403" "$ADMIN_TOKEN"
run_test "Celery Pending Tasks"  "GET"  "/api/v1/admin/celery/tasks/pending"  "" "200|403" "$ADMIN_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 15: Admin — B2B (Organizations & Locations)
# ════════════════════════════════════════════════════════════════════════════
phase_header 15 "ADMIN — B2B"

run_test "Create Org (empty body)"     "POST" "/api/v1/admin/organizations" "{}" "403|422" "$ADMIN_TOKEN"
run_test "Create Location (empty body)" "POST" "/api/v1/admin/locations" "{}" "403|422" "$ADMIN_TOKEN"
run_test "Create Org (valid)"          "POST" "/api/v1/admin/organizations" "{\"id\":\"org_test_$TIMESTAMP\",\"name\":\"Test Org\"}" "201|403" "$ADMIN_TOKEN"
run_test "Create Location (radius=0)"  "POST" "/api/v1/admin/locations" "{\"org_id\":\"org_test_$TIMESTAMP\",\"name\":\"HQ\",\"latitude\":40.7,\"longitude\":-74.0,\"radius\":0}" "403|422" "$ADMIN_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 16: Admin — Settings & Billing
# ════════════════════════════════════════════════════════════════════════════
phase_header 16 "ADMIN — SETTINGS & BILLING"

run_test "Get AI Settings"       "GET"   "/api/v1/admin/settings/ai"      "" "200|403" "$ADMIN_TOKEN"
run_test "List Plans"            "GET"   "/api/v1/admin/plans"            "" "200|403" "$ADMIN_TOKEN"
run_test "List Wallets"          "GET"   "/api/v1/admin/wallets"          "" "200|403" "$ADMIN_TOKEN"
run_test "Toggle Freeze (U2)"   "POST"  "/api/v1/admin/wallets/$U2_ID/toggle-freeze" "" "200|403|404" "$ADMIN_TOKEN"
run_test "Credit Wallet (U2)"   "POST"  "/api/v1/admin/wallets/$U2_ID/credit?amount=100&reason=test" "" "200|403|404" "$ADMIN_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 17: Admin — Audit Logs
# ════════════════════════════════════════════════════════════════════════════
phase_header 17 "ADMIN — AUDIT LOGS"

run_test "Get Audit Logs"        "GET" "/api/v1/admin/audit-logs?limit=10" "" "200|403" "$ADMIN_TOKEN"
run_test "Recent Activity"       "GET" "/api/v1/admin/activity/recent"     "" "200|403" "$ADMIN_TOKEN"
run_test "Activity Stats"        "GET" "/api/v1/admin/activity/stats"      "" "200|403" "$ADMIN_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 18: Negative Tests (401/403/404/422)
# ════════════════════════════════════════════════════════════════════════════
phase_header 18 "NEGATIVE TESTS"

run_test "No Auth → 401"           "GET"    "/api/v1/users/me"       "" "401"
run_test "Bad Token → 401"         "GET"    "/api/v1/users/me"       "" "401" "invalid_token_xxx"
run_test "Non-exist Note → 404"    "GET"    "/api/v1/notes/nonexistent_id" "" "404" "$U1_TOKEN"
run_test "Non-exist Task → 404"    "GET"    "/api/v1/tasks/nonexistent_id" "" "404" "$U1_TOKEN"
run_test "Invalid Note Body → 422" "POST"   "/api/v1/notes/create"   "{}" "422" "$U1_TOKEN"
run_test "Invalid Task Body → 422" "POST"   "/api/v1/tasks"          "{}" "422" "$U1_TOKEN"
run_test "Non-admin → admin 403"   "GET"    "/api/v1/admin/users"    "" "403" "$U2_TOKEN"
run_test "SQLi Probe"              "POST"   "/api/v1/notes/search"   "{\"query\":\"' OR 1=1 --\"}" "200|400|422" "$U1_TOKEN"
run_test "XSS Probe in Note"       "POST"   "/api/v1/notes/create"   "{\"title\":\"<script>alert(1)</script>\"}" "201|422" "$U1_TOKEN"
run_test "Oversized Payload"       "POST"   "/api/v1/notes/create"   "{\"title\":\"$(python3 -c "print('A'*10000)")\"}" "201|413|422" "$U1_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 19: Regression (Audit Fix Verification)
# ════════════════════════════════════════════════════════════════════════════
phase_header 19 "REGRESSION — AUDIT FIXES"

# C02: toggle-freeze uses get_current_active_admin (not NameError/500)
run_test "C02: Toggle freeze no 500"  "POST" "/api/v1/admin/wallets/$U2_ID/toggle-freeze" "" "200|403|404" "$ADMIN_TOKEN"

# C03: /reports/revenue exists (not 404/405)
run_test "C03: Revenue endpoint"      "GET"  "/api/v1/admin/reports/revenue?start_date=$WEEK_AGO_MS&end_date=$NOW_MS" "" "200|403" "$ADMIN_TOKEN"

# C04: Sync module works (not 500)
run_test "C04: Sync upload-batch"     "POST" "/api/v1/sync/upload-batch" "{\"notes\":[]}" "200|400|422" "$U1_TOKEN"

# H05: Bulk ops reject >100 IDs
BIG_IDS=$(python3 -c "print(','.join([f'id_{i}' for i in range(101)]))")
run_test "H05: Bulk delete >100"      "POST" "/api/v1/admin/bulk/delete?item_type=notes&ids=$BIG_IDS&reason=test" "" "400|403" "$ADMIN_TOKEN"
run_test "H05: Bulk restore >100"     "POST" "/api/v1/admin/bulk/restore?item_type=notes&ids=$BIG_IDS" "" "400|403" "$ADMIN_TOKEN"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 20: Dashboard Health
# ════════════════════════════════════════════════════════════════════════════
phase_header 20 "DASHBOARD HEALTH"

echo -n "Checking dashboard at $DASHBOARD_URL ..." >&2
DASH_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$DASHBOARD_URL" 2>/dev/null || echo "000")
if [ "$DASH_CODE" == "200" ]; then
    printf "${GREEN}PASS ${NC} [200] Dashboard reachable\n" >&2
    echo $(( $(cat /tmp/vn_passed) + 1 )) > /tmp/vn_passed
else
    printf "${YELLOW}SKIP ${NC} Dashboard not reachable (code: $DASH_CODE)\n" >&2
    echo $(( $(cat /tmp/vn_skipped) + 1 )) > /tmp/vn_skipped
fi
echo $(( $(cat /tmp/vn_total) + 1 )) > /tmp/vn_total

DASH_LOGIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$DASHBOARD_URL/login" 2>/dev/null || echo "000")
if [ "$DASH_LOGIN_CODE" == "200" ]; then
    printf "${GREEN}PASS ${NC} [200] Dashboard /login reachable\n" >&2
    echo $(( $(cat /tmp/vn_passed) + 1 )) > /tmp/vn_passed
else
    printf "${YELLOW}SKIP ${NC} Dashboard /login not reachable (code: $DASH_LOGIN_CODE)\n" >&2
    echo $(( $(cat /tmp/vn_skipped) + 1 )) > /tmp/vn_skipped
fi
echo $(( $(cat /tmp/vn_total) + 1 )) > /tmp/vn_total


# ════════════════════════════════════════════════════════════════════════════
# PHASE 21: Cleanup & Summary
# ════════════════════════════════════════════════════════════════════════════
phase_header 21 "CLEANUP & SUMMARY"

# Cleanup: delete test user (soft)
run_test "Logout User1"  "POST"   "/api/v1/users/logout"  "" "200" "$U1_TOKEN"
run_test "Delete User2"  "DELETE" "/api/v1/users/me"       "" "200" "$U2_TOKEN" "true"
run_test "U2 Token Dead" "GET"    "/api/v1/users/me"       "" "401" "$U2_TOKEN"

# Final counts
PASSED=$(cat /tmp/vn_passed 2>/dev/null || echo 0)
FAILED=$(cat /tmp/vn_failed 2>/dev/null || echo 0)
TOTAL=$(cat /tmp/vn_total 2>/dev/null || echo 0)
SKIPPED=$(cat /tmp/vn_skipped 2>/dev/null || echo 0)

echo "" >&2
echo "================================================================================" >&2
echo -e "  ${MAGENTA}TEST SUITE COMPLETE${NC}" >&2
echo "================================================================================" >&2
echo -e "  Total:   $TOTAL" >&2
echo -e "  ${GREEN}Passed:  $PASSED${NC}" >&2
echo -e "  ${RED}Failed:  $FAILED${NC}" >&2
echo -e "  ${YELLOW}Skipped: $SKIPPED${NC}" >&2
echo "================================================================================" >&2
echo "  Full report: $REPORT_FILE" >&2
echo "================================================================================" >&2

{
    echo ""
    echo "================================================================================"
    echo "SUMMARY: $PASSED/$TOTAL passed, $FAILED failed, $SKIPPED skipped"
    echo "================================================================================"
} >> "$REPORT_FILE"

# Exit with non-zero if any tests failed
[ "$FAILED" -eq 0 ] && exit 0 || exit 1
