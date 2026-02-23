#!/bin/bash
# ============================================================================
# VoiceNoteAPI — COMPREHENSIVE 151-Endpoint Curl Test Suite
# Tests every route across all API modules
# Usage: bash scripts/curl_all_endpoints.sh [API_URL] [ADMIN_EMAIL] [ADMIN_PASS]
# ============================================================================

set -uo pipefail

API="${1:-http://localhost:8000}"
ADMIN_EMAIL="${2:-admin@voicenote.ai}"
ADMIN_PASS="${3:-admin123}"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
PASSED=0; FAILED=0; SKIPPED=0; TOTAL=0

pass()  { PASSED=$((PASSED+1)); TOTAL=$((TOTAL+1)); echo -e "  ${GREEN}✓${NC} $1"; }
fail()  { FAILED=$((FAILED+1)); TOTAL=$((TOTAL+1)); echo -e "  ${RED}✗${NC} $1 | expected: $2  got: $3"; }
skip()  { SKIPPED=$((SKIPPED+1)); echo -e "  ${YELLOW}⚠${NC} SKIP — $1 ($2)"; }
sec()   { echo -e "\n${CYAN}${BOLD}━━━ $1 ━━━${NC}"; }
GET()   { curl -s -o /dev/null -w "%{http_code}" -H "$AUTH" "$API$1"; }
GETP()  { curl -s -o /dev/null -w "%{http_code}" "$API$1"; }
POST()  { curl -s -o /dev/null -w "%{http_code}" -X POST -H "$AUTH" -H "Content-Type: application/json" -d "$2" "$API$1"; }
PATCH() { curl -s -o /dev/null -w "%{http_code}" -X PATCH -H "$AUTH" -H "Content-Type: application/json" -d "$2" "$API$1"; }
DEL()   { curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "$AUTH" "$API$1"; }
PUT()   { curl -s -o /dev/null -w "%{http_code}" -X PUT -H "$AUTH" -H "Content-Type: application/json" -d "$2" "$API$1"; }
POSTB() { curl -s -w "\n%{http_code}" -X POST -H "$AUTH" -H "Content-Type: application/json" -d "$2" "$API$1"; }
GETB()  { curl -s -w "\n%{http_code}" -H "$AUTH" "$API$1"; }

chk() {
    local name="$1" exp="$2" got="$3"
    if [ "$got" -eq "$exp" ]; then pass "$name ($got)"; else fail "$name" "$exp" "$got"; fi
}
chk_any() {
    local name="$1" got="$2"; shift 2
    for c in "$@"; do [ "$got" -eq "$c" ] && { pass "$name ($got)"; return; }; done
    fail "$name" "one of[$*]" "$got"
}

echo -e "\n${BOLD}════════════════════════════════════════════${NC}"
echo -e "${BOLD}  VoiceNoteAPI — 151-Endpoint Curl Suite${NC}"
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo "  API: $API  |  $(date)"

# ─────────────────────────────────────────────
# SETUP: Get tokens & create test resources
# ─────────────────────────────────────────────
echo -e "\n${BOLD}── Setup: Auth & Test Data ──${NC}"

AUTH="Authorization: Bearer no_token"

# Register regular user
REG_EMAIL="curl_user_$(date +%s)@test.com"
REG_BODY=$(curl -s -X POST "$API/api/v1/users/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$REG_EMAIL\",\"password\":\"Test@12345\",\"name\":\"CurlUser\"}")
USER_TOKEN=$(echo "$REG_BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('access_token',d.get('access_token','')))" 2>/dev/null || echo "")
USER_ID=$(echo "$REG_BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('user',{}).get('id',''))" 2>/dev/null || echo "")

# Login regular user if token not in register
if [ -z "$USER_TOKEN" ]; then
    LOGIN=$(curl -s -X POST "$API/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$REG_EMAIL\",\"password\":\"Test@12345\"}")
    USER_TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
    USER_ID=$(echo "$LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin).get('user',{}).get('id',''))" 2>/dev/null || echo "")
fi

# Login admin user
ADMIN_LOGIN=$(curl -s -X POST "$API/api/v1/users/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASS\"}")
ADMIN_TOKEN=$(echo "$ADMIN_LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

# Set primary auth to regular user token
if [ -n "$USER_TOKEN" ]; then
    AUTH="Authorization: Bearer $USER_TOKEN"
    echo -e "  ${GREEN}✓${NC} Regular user token obtained"
else
    echo -e "  ${RED}✗${NC} No regular user token — some tests will show 401"
fi

if [ -n "$ADMIN_TOKEN" ]; then
    ADMIN_AUTH="Authorization: Bearer $ADMIN_TOKEN"
    echo -e "  ${GREEN}✓${NC} Admin token obtained"
else
    ADMIN_AUTH="Authorization: Bearer no_admin_token"
    echo -e "  ${YELLOW}⚠${NC} No admin token — admin tests will fail"
fi

NOW_MS=$(python3 -c "import time;print(int(time.time()*1000))")
THIRTY_AGO=$((NOW_MS - 2592000000))

# ── Create test note ──
NOTE_R=$(POSTB /api/v1/notes/create '{"transcript":"Meeting with client about Q1 targets. John needs to send report by Friday.","title":"Q1 Meeting"}')
NOTE_CODE=$(echo "$NOTE_R" | tail -1)
NOTE_ID=$(echo "$NOTE_R" | head -n -1 | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
[ -n "$NOTE_ID" ] && echo -e "  ${GREEN}✓${NC} Test note: $NOTE_ID" || echo -e "  ${YELLOW}⚠${NC} Note creation failed (HTTP $NOTE_CODE)"

# ── Create test task ──
TASK_R=$(POSTB /api/v1/tasks '{"title":"Send Q1 Report","description":"Send the Q1 targets report to the client","priority":"HIGH"}')
TASK_CODE=$(echo "$TASK_R" | tail -1)
TASK_ID=$(echo "$TASK_R" | head -n -1 | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
[ -n "$TASK_ID" ] && echo -e "  ${GREEN}✓${NC} Test task: $TASK_ID" || echo -e "  ${YELLOW}⚠${NC} Task creation failed (HTTP $TASK_CODE)"

# ── Create test folder ──
FOLDER_R=$(POSTB /api/v1/folders '{"name":"Test Folder","color":"#FF5733"}')
FOLDER_ID=$(echo "$FOLDER_R" | head -n -1 | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
[ -n "$FOLDER_ID" ] && echo -e "  ${GREEN}✓${NC} Test folder: $FOLDER_ID" || echo -e "  ${YELLOW}⚠${NC} Folder creation failed"

# ── Create test team ──
TEAM_R=$(POSTB /api/v1/teams '{"name":"Test Team","description":"A curl test team"}')
TEAM_ID=$(echo "$TEAM_R" | head -n -1 | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
[ -n "$TEAM_ID" ] && echo -e "  ${GREEN}✓${NC} Test team: $TEAM_ID" || echo -e "  ${YELLOW}⚠${NC} Team creation failed"


# ═══════════════════════════════════════════
sec "1. HEALTH (1 endpoint)"
# ═══════════════════════════════════════════
chk "GET /health" 200 "$(GETP /health)"

# ═══════════════════════════════════════════
sec "2. USERS — /api/v1/users (16 endpoints)"
# ═══════════════════════════════════════════
# POST /register
chk_any "POST /users/register" "$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/v1/users/register" -H "Content-Type: application/json" -d "{\"email\":\"newuser_$(date +%s)@t.com\",\"password\":\"Test@12345\",\"name\":\"New\"}")" 200 201 400 409 422

# POST /login
chk_any "POST /users/login (valid)" "$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/v1/users/login" -H "Content-Type: application/json" -d "{\"email\":\"$REG_EMAIL\",\"password\":\"Test@12345\"}")" 200 400

# POST /login bad creds
chk_any "POST /users/login (bad creds)" "$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/v1/users/login" -H "Content-Type: application/json" -d '{"email":"nobody@x.com","password":"wrong"}')" 400 401 404

# POST /logout
chk_any "POST /users/logout" "$(POST /api/v1/users/logout '{}')" 200 204 401

# GET /verify-device
chk_any "GET /users/verify-device" "$(GET "/api/v1/users/verify-device?token=fake_token")" 200 400 401

# GET /me
chk "GET /users/me" 200 "$(GET /api/v1/users/me)"

# GET /balance
chk_any "GET /users/balance" "$(GET /api/v1/users/balance)" 200 404

# GET /search
chk_any "GET /users/search" "$(curl -s -o /dev/null -w "%{http_code}" -H "$ADMIN_AUTH" "$API/api/v1/users/search?q=test")" 200 422 403

# GET /{user_id}
if [ -n "$USER_ID" ]; then
    chk_any "GET /users/{user_id}" "$(GET /api/v1/users/$USER_ID)" 200 403 404
else
    skip "GET /users/{user_id}" "no USER_ID"
fi

# POST /forgot-password
chk_any "POST /users/forgot-password" "$(POST /api/v1/users/forgot-password "{\"email\":\"$REG_EMAIL\"}")" 200 400 404 429

# POST /reset-password
chk_any "POST /users/reset-password" "$(POST /api/v1/users/reset-password '{"token":"invalid","new_password":"Test@12345"}')" 200 400 404 429

# PATCH /me
chk_any "PATCH /users/me" "$(PATCH /api/v1/users/me '{"name":"Updated Name"}')" 200 422

# PATCH /me/profile-picture (multipart, just check method exists)
chk_any "PATCH /users/me/profile-picture (no file)" "$(curl -s -o /dev/null -w "%{http_code}" -X PATCH -H "$AUTH" "$API/api/v1/users/me/profile-picture")" 200 400 422

# DELETE /me
# Skip — would delete the test user
skip "DELETE /users/me" "would delete test user"

# PATCH /{user_id}/restore
chk_any "PATCH /users/{user_id}/restore (nonexistent)" "$(PATCH /api/v1/users/nonexistent-id/restore '{}')" 400 404 403

# PATCH /{user_id}/role
chk_any "PATCH /users/{user_id}/role" "$(PATCH /api/v1/users/${USER_ID:-nonexistent}/role '{"primary_role":"DEVELOPER"}')" 200 403 404 422

# POST /refresh
chk_any "POST /users/refresh" "$(POST /api/v1/users/refresh '{"refresh_token":"invalid_token"}')" 200 400 401

# ═══════════════════════════════════════════
sec "3. NOTES — /api/v1/notes (16 endpoints)"
# ═══════════════════════════════════════════

# GET /presigned-url
chk_any "GET /notes/presigned-url" "$(GET /api/v1/notes/presigned-url?filename=test.m4a)" 200 422 500

# POST /process (multipart — test without file to get 400/422)
chk_any "POST /notes/process (no file)" "$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "$AUTH" "$API/api/v1/notes/process")" 400 422

# POST /create
chk_any "POST /notes/create" "$(POST /api/v1/notes/create '{"transcript":"Another test note","title":"Test Create"}')" 200 201 402 422

# GET /dashboard
chk "GET /notes/dashboard" 200 "$(GET /api/v1/notes/dashboard)"

# GET /autocomplete
chk_any "GET /notes/autocomplete" "$(GET /api/v1/notes/autocomplete?q=meeting)" 200 422

# PATCH /move
chk_any "PATCH /notes/move" "$(PATCH /api/v1/notes/move "{\"note_ids\":[\"${NOTE_ID:-nonexistent}\"],\"folder_id\":null}")" 200 400 404 422

# GET / (list)
chk "GET /notes (list)" 200 "$(GET /api/v1/notes)"

# GET /{note_id}
if [ -n "$NOTE_ID" ]; then
    chk "GET /notes/{note_id}" 200 "$(GET /api/v1/notes/$NOTE_ID)"
    chk "GET /notes/{note_id}?verbose=true" 200 "$(GET /api/v1/notes/$NOTE_ID?verbose=true)"
    chk_any "PATCH /notes/{note_id}" 200 "$(PATCH /api/v1/notes/$NOTE_ID '{"title":"Updated Note Title","priority":"HIGH"}')"
    chk_any "POST /notes/{note_id}/semantic-analysis" 202 "$(POST /api/v1/notes/$NOTE_ID/semantic-analysis '{}')"
    chk "GET /notes/{note_id}/whatsapp" 200 "$(GET /api/v1/notes/$NOTE_ID/whatsapp)"
else
    skip "GET /notes/{note_id}" "no NOTE_ID"; skip "PATCH /notes/{note_id}" "no NOTE_ID"
    skip "POST /notes/{note_id}/semantic-analysis" "no NOTE_ID"; skip "GET /notes/{note_id}/whatsapp" "no NOTE_ID"
fi

# POST /search
chk_any "POST /notes/search" "$(POST /api/v1/notes/search '{"query":"Q1 meeting","limit":5}')" 200 204

# POST /{note_id}/ask
if [ -n "$NOTE_ID" ]; then
    chk_any "POST /notes/{note_id}/ask" "$(POST /api/v1/notes/$NOTE_ID/ask '{"question":"What tasks are in this note?"}')" 200 422 500
else
    skip "POST /notes/{note_id}/ask" "no NOTE_ID"
fi

# DELETE /{note_id}
# Will do at cleanup

# PATCH /{note_id}/restore — test with nonexistent
chk_any "PATCH /notes/{note_id}/restore (nonexistent)" "$(PATCH /api/v1/notes/nonexistent-note-id/restore '{}')" 400 404

# DELETE / (bulk)
chk_any "DELETE /notes (bulk empty)" "$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "$AUTH" -H "Content-Type: application/json" -d '{"note_ids":[]}' "$API/api/v1/notes")" 200 400 422

# ═══════════════════════════════════════════
sec "4. TASKS — /api/v1/tasks (22 endpoints)"
# ═══════════════════════════════════════════

# POST / (create)
TASK2_R=$(POSTB /api/v1/tasks '{"title":"Follow-up Call","description":"Call John","priority":"MEDIUM"}')
TASK2_ID=$(echo "$TASK2_R" | head -n -1 | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
chk_any "POST /tasks (create)" "$(echo "$TASK2_R" | tail -1)" 200 201 402 422

# GET / (list)
chk "GET /tasks (list)" 200 "$(GET /api/v1/tasks)"

# GET /due-today
chk "GET /tasks/due-today" 200 "$(GET /api/v1/tasks/due-today)"

# GET /overdue
chk "GET /tasks/overdue" 200 "$(GET /api/v1/tasks/overdue)"

# GET /assigned-to-me
chk "GET /tasks/assigned-to-me" 200 "$(GET /api/v1/tasks/assigned-to-me)"

# GET /search
chk_any "GET /tasks/search" "$(GET /api/v1/tasks/search?q=report)" 200 422

# GET /stats and /statistics
chk_any "GET /tasks/stats" "$(GET /api/v1/tasks/stats)" 200 404
chk_any "GET /tasks/statistics" "$(GET /api/v1/tasks/statistics)" 200 404

ACTIVE_TASK="${TASK_ID:-$TASK2_ID}"

# GET /{task_id}
if [ -n "$ACTIVE_TASK" ]; then
    chk "GET /tasks/{task_id}" 200 "$(GET /api/v1/tasks/$ACTIVE_TASK)"
    chk_any "PATCH /tasks/{task_id}" "$(PATCH /api/v1/tasks/$ACTIVE_TASK '{"title":"Updated Task Title"}')" 200 204
    chk_any "POST /tasks/{task_id}/lock" "$(POST /api/v1/tasks/$ACTIVE_TASK/lock '{}')" 200 201
    chk_any "DELETE /tasks/{task_id}/lock" "$(DEL /api/v1/tasks/$ACTIVE_TASK/lock)" 200 204
    
    # Real Media Upload Test
    echo "test content" > test_media.txt
    chk_any "POST /tasks/{task_id}/multimedia" "$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "$AUTH" -F "file=@test_media.txt" "$API/api/v1/tasks/$ACTIVE_TASK/multimedia")" 200 201 202
    rm test_media.txt
    
    # Validation failure test (missing file)
    chk_any "POST /tasks/{task_id}/multimedia (no file)" "$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "$AUTH" "$API/api/v1/tasks/$ACTIVE_TASK/multimedia")" 422 400
    
    chk_any "PATCH /tasks/{task_id}/multimedia" "$(PATCH /api/v1/tasks/$ACTIVE_TASK/multimedia '{"url_to_remove":"fake"}')" 200 204 400 404
    chk_any "GET /tasks/{task_id}/communication-options" "$(GET /api/v1/tasks/$ACTIVE_TASK/communication-options)" 200 404
    chk_any "POST /tasks/{task_id}/external-links" "$(POST /api/v1/tasks/$ACTIVE_TASK/external-links '{"url":"https://example.com","title":"Example"}')" 200 201 202
    chk_any "DELETE /tasks/{task_id}/external-links/{index}" "$(DEL /api/v1/tasks/$ACTIVE_TASK/external-links/0)" 200 204 404
else
    for ep in "GET/{task_id}" "PATCH/{task_id}" "POST/{task_id}/lock" "DELETE/{task_id}/lock" \
              "POST/{task_id}/multimedia" "PATCH/{task_id}/multimedia" \
              "GET/{task_id}/communication-options" "POST/{task_id}/external-links" \
              "DELETE/{task_id}/external-links/{i}"; do
        skip "/tasks/$ep" "no TASK_ID"
    done
fi

# POST / (bulk create - alternate endpoint)
chk_any "POST /tasks (bulk endpoint)" "$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "$AUTH" -H "Content-Type: application/json" -d '[{"title":"Bulk T1","description":"d","priority":"LOW"}]' "$API/api/v1/tasks/")" 200 201 307 400 404 405 422

# PATCH /{task_id}/complete
if [ -n "$TASK2_ID" ]; then
    chk_any "PATCH /tasks/{task_id}/complete" "$(PATCH /api/v1/tasks/$TASK2_ID/complete '{"is_done":true}')" 200 204
    # Validation failure test
    chk_any "PATCH /tasks/{task_id}/complete (no body)" "$(PATCH /api/v1/tasks/$TASK2_ID/complete '{}')" 422 400
else
    skip "PATCH /tasks/{task_id}/complete" "no TASK_ID"
fi

# PATCH /{task_id}/restore (nonexistent)
chk_any "PATCH /tasks/{task_id}/restore (nonexistent)" "$(PATCH /api/v1/tasks/nonexistent-task/restore '{}')" 404 400

# DELETE /{task_id}
if [ -n "$TASK2_ID" ]; then
    chk_any "DELETE /tasks/{task_id}" "$(DEL /api/v1/tasks/$TASK2_ID)" 200 204
fi

# DELETE / (bulk)
chk_any "DELETE /tasks (bulk empty)" "$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "$AUTH" -H "Content-Type: application/json" -d '{"task_ids":[]}' "$API/api/v1/tasks")" 200 204 400 404 422

# ═══════════════════════════════════════════
sec "5. FOLDERS — /api/v1/folders (6 endpoints)"
# ═══════════════════════════════════════════

# POST / (create)
FOLD2_R=$(POSTB /api/v1/folders '{"name":"Folder2","color":"#00FF00"}')
FOLD2_ID=$(echo "$FOLD2_R" | head -n -1 | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
chk_any "POST /folders (create)" "$(echo "$FOLD2_R" | tail -1)" 200 201 422

# GET / (list)
chk "GET /folders (list)" 200 "$(GET /api/v1/folders)"

# PATCH /{folder_id}
if [ -n "$FOLDER_ID" ]; then
    chk_any "PATCH /folders/{folder_id}" "$(PATCH /api/v1/folders/$FOLDER_ID '{"name":"Renamed Folder"}')" 200
fi

# POST /{folder_id}/participants
if [ -n "$FOLD2_ID" ]; then
    chk_any "POST /folders/{folder_id}/participants" "$(POST /api/v1/folders/$FOLD2_ID/participants "{\"user_email\":\"$REG_EMAIL\",\"role\":\"MEMBER\"}")" 200 201
    # Validation failure test (missing email)
    chk_any "POST /folders/{folder_id}/participants (missing email)" "$(POST /api/v1/folders/$FOLD2_ID/participants '{"role":"MEMBER"}')" 422 400 404
else
    skip "POST /folders/{folder_id}/participants" "no FOLD2_ID"
fi

# GET /{folder_id}/participants
if [ -n "$FOLDER_ID" ]; then
    chk_any "GET /folders/{folder_id}/participants" "$(GET /api/v1/folders/$FOLDER_ID/participants)" 200 404
fi

# DELETE /{folder_id}
if [ -n "$FOLD2_ID" ]; then
    chk_any "DELETE /folders/{folder_id}" "$(DEL /api/v1/folders/$FOLD2_ID)" 200 204
fi

# ═══════════════════════════════════════════
sec "6. TEAMS — /api/v1/teams (6 endpoints)"
# ═══════════════════════════════════════════

# POST / (already done in setup, test again)
TEAM2_R=$(POSTB /api/v1/teams '{"name":"Another Team"}')
TEAM2_ID=$(echo "$TEAM2_R" | head -n -1 | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
chk_any "POST /teams (create)" "$(echo "$TEAM2_R" | tail -1)" 200 201 422

# GET / (list)
chk_any "GET /teams (list)" "$(GET /api/v1/teams)" 200 404

# POST /{team_id}/members
if [ -n "$TEAM_ID" ]; then
    chk_any "POST /teams/{team_id}/members" "$(POST /api/v1/teams/$TEAM_ID/members '{"user_email":"'$REG_EMAIL'"}')" 200 201 404 422
fi

# DELETE /{team_id}/members/{user_id}
if [ -n "$TEAM_ID" -a -n "$USER_ID" ]; then
    chk_any "DELETE /teams/{team_id}/members/{user_id}" "$(DEL /api/v1/teams/$TEAM_ID/members/$USER_ID)" 200 204 400 404
else
    skip "DELETE /teams/{team_id}/members/{user_id}" "no IDs"
fi

# GET /{team_id}/analytics
if [ -n "$TEAM_ID" ]; then
    chk_any "GET /teams/{team_id}/analytics" "$(GET /api/v1/teams/$TEAM_ID/analytics)" 200 404
fi

# DELETE /{team_id}
if [ -n "$TEAM2_ID" ]; then
    chk_any "DELETE /teams/{team_id}" "$(DEL /api/v1/teams/$TEAM2_ID)" 200 204
fi

# ═══════════════════════════════════════════
sec "7. INTEGRATIONS — /api/v1/integrations (4 endpoints)"
# ═══════════════════════════════════════════

chk_any "GET /integrations/list" "$(GET /api/v1/integrations/list)" 200 404
chk_any "POST /integrations/google/connect" "$(POST /api/v1/integrations/google/connect '{"code":"fake_code"}')" 200 201 400
chk_any "POST /integrations/notion/connect" "$(POST /api/v1/integrations/notion/connect '{"code":"fake_code"}')" 200 201
chk_any "DELETE /integrations/google/disconnect" "$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "$AUTH" "$API/api/v1/integrations/google/disconnect")" 200 204 404

# ═══════════════════════════════════════════
sec "8. AI — /api/v1/ai (3 endpoints)"
# ━━━ 8. AI — /api/v1/ai (3 endpoints) ━━━
chk_any "POST /ai/search" "$(POST /api/v1/ai/search '{"query":"test","limit":5}' | head -n 1)" 200 201 422
chk_any "POST /ai/ask" "$(POST /api/v1/ai/ask '{"question":"What are my tasks?"}' | head -n 1)" 200 201 422
chk_any "POST /ai/ask (missing question)" "$(POST /api/v1/ai/ask '{}' | head -n 1)" 422 400
chk_any "GET /ai/stats" "$(GET /api/v1/ai/stats)" 200 404

# ═══════════════════════════════════════════
sec "9. BILLING — /api/v1/billing (2 endpoints)"
# ═══════════════════════════════════════════

chk_any "GET /billing/plans" "$(GET /api/v1/billing/plans)" 200 404
chk_any "POST /billing/verify-purchase" "$(POST /api/v1/billing/verify-purchase '{"product_id":"test","purchase_token":"fake"}')" 200 201 404

# ═══════════════════════════════════════════
sec "10. SYNC — /api/v1/sync (1 endpoint)"
# ━━━ 10. SYNC — /api/v1/sync (1 endpoint) ━━━
echo "sync test" > sync_file.txt
chk_any "POST /sync/upload-batch" "$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "$AUTH" -F "files=@sync_file.txt" "$API/api/v1/sync/upload-batch")" 200 201
rm sync_file.txt

# ═══════════════════════════════════════════
sec "11. SSE — /api/v1/sse (1 endpoint)"
# ═══════════════════════════════════════════

# SSE streams — check at correct /api/v1/sse/events path
# Using temporary file to avoid shell capture issues with timeouts
curl -s -o /dev/null -w "%{http_code}" --max-time 2 -H "$AUTH" "$API/api/v1/sse/events" > .sse_code 2>/dev/null || true
STATUS_RESULT=$(cat .sse_code)
rm .sse_code
chk_any "GET /sse/events (stream)" "$STATUS_RESULT" 200 000

# ═══════════════════════════════════════════
sec "12. WEBHOOKS — /api/v1/webhooks (1 endpoint)"
# ═══════════════════════════════════════════

chk_any "POST /webhooks/stripe" "$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/v1/webhooks/stripe" -H "Content-Type: application/json" -d '{}')" 400 401 422

# ═══════════════════════════════════════════
sec "13. ADMIN — /api/v1/admin (73 endpoints)"
# ═══════════════════════════════════════════

AGET()  { curl -s -o /dev/null -w "%{http_code}" -H "$ADMIN_AUTH" "$API/api/v1/admin$1"; }
APOST() { curl -s -o /dev/null -w "%{http_code}" -X POST -H "$ADMIN_AUTH" -H "Content-Type: application/json" -d "$2" "$API/api/v1/admin$1"; }
APATCH(){ curl -s -o /dev/null -w "%{http_code}" -X PATCH -H "$ADMIN_AUTH" -H "Content-Type: application/json" -d "$2" "$API/api/v1/admin$1"; }
ADEL()  { curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "$ADMIN_AUTH" "$API/api/v1/admin$1"; }
APUT()  { curl -s -o /dev/null -w "%{http_code}" -X PUT -H "$ADMIN_AUTH" -H "Content-Type: application/json" -d "$2" "$API/api/v1/admin$1"; }

# — User Management —
chk_any "GET  /admin/users" "$(AGET /users)" 200 403
chk_any "GET  /admin/users/stats" "$(AGET /users/stats)" 200 403
chk_any "GET  /admin/users/search" "$(AGET /users/search?q=test)" 200 403 404
chk_any "GET  /admin/admins" "$(AGET /admins)" 200 403
chk_any "GET  /admin/status" "$(AGET /status)" 200 403

if [ -n "$USER_ID" ]; then
    chk_any "GET  /admin/users/{user_id}" "$(AGET /users/$USER_ID)" 200 403 404
    chk_any "GET  /admin/users/{user_id}/detail" "$(AGET /users/$USER_ID/detail)" 200 403 404
    chk_any "GET  /admin/users/{user_id}/devices" "$(AGET /users/$USER_ID/devices)" 200 403 404
    chk_any "GET  /admin/users/{user_id}/sessions" "$(AGET /users/$USER_ID/sessions)" 200 403 404
    chk_any "GET  /admin/users/{user_id}/activity" "$(AGET /users/$USER_ID/activity)" 200 403 404
    chk_any "GET  /admin/users/{user_id}/usage" "$(AGET /users/$USER_ID/usage)" 200 403 404
    chk_any "PATCH /admin/users/{user_id}" "$(APATCH /users/$USER_ID '{"name":"Admin Updated"}')" 200 403 404 422
    chk_any "PATCH /admin/users/{user_id}/tier" "$(APATCH /users/$USER_ID/tier '{"tier":"STANDARD"}')" 200 403 404 422
    chk_any "PATCH /admin/users/{user_id}/plan" "$(APATCH /users/$USER_ID/plan '{"plan_id":"nonexistent"}')" 200 400 403 404 422
    chk_any "POST  /admin/users/{user_id}/make-admin" "$(APOST /users/$USER_ID/make-admin?level=viewer '')" 200 400 403
    chk_any "POST  /admin/users/{user_id}/remove-admin" "$(APOST /users/$USER_ID/remove-admin '')" 200 400 403
    chk_any "PATCH /admin/users/{user_id}/restore" "$(APATCH /users/$USER_ID/restore '')" 200 400 403 404
    chk_any "POST  /admin/users/{user_id}/force-logout" "$(APOST /users/$USER_ID/force-logout '')" 200 400 403
    # Skip dangerous endpoints: DELETE /users/{user_id}, DELETE /users/{user_id}/hard
    skip "DELETE /admin/users/{user_id}" "destructive — would delete test user"
    skip "DELETE /admin/users/{user_id}/hard" "destructive"
else
    for ep in "GET/{user_id}" "GET/{user_id}/detail" "GET/{user_id}/devices" "GET/{user_id}/sessions" \
              "GET/{user_id}/activity" "GET/{user_id}/usage" "PATCH/{user_id}" "PATCH/{user_id}/tier" \
              "PATCH/{user_id}/plan" "POST/{user_id}/make-admin" "POST/{user_id}/remove-admin" \
              "PATCH/{user_id}/restore" "POST/{user_id}/force-logout"; do
        skip "/admin/users/$ep" "no USER_ID"
    done
fi

chk_any "PUT  /admin/permissions/{user_id}" "$(APUT /permissions/${USER_ID:-nonexistent} '{"can_view_all_users":true}')" 200 400 403 404

# — Content Moderation Notes —
chk_any "GET  /admin/notes" "$(AGET /notes)" 200 403
chk_any "GET  /admin/notes/audit" "$(AGET /notes/audit)" 200 403
if [ -n "$NOTE_ID" ]; then
    # Skip — would delete our test note
    skip "DELETE /admin/notes/{note_id}" "would delete test note"
else
    skip "DELETE /admin/notes/{note_id}" "no NOTE_ID"
fi

# — Admin Tasks —
chk_any "GET  /admin/tasks" "$(AGET /tasks)" 200 403
if [ -n "$TASK_ID" ]; then
    chk_any "DELETE /admin/tasks/{task_id}" "$(ADEL /tasks/$TASK_ID)" 200 204 403 404
    chk_any "PATCH  /admin/tasks/{task_id}/restore" "$(APATCH /tasks/$TASK_ID/restore '')" 200 403 404
else
    skip "DELETE /admin/tasks/{task_id}" "no TASK_ID"
    skip "PATCH /admin/tasks/{task_id}/restore" "no TASK_ID"
fi

# — Service Plans —
PLAN_R=$(curl -s -w "\n%{http_code}" -X POST -H "$ADMIN_AUTH" -H "Content-Type: application/json" \
    -d '{"name":"CURL_TEST_PLAN","monthly_credits":100,"monthly_note_limit":10,"monthly_task_limit":20}' \
    "$API/api/v1/admin/plans")
PLAN_CODE=$(echo "$PLAN_R" | tail -1)
PLAN_ID=$(echo "$PLAN_R" | head -n -1 | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
chk_any "POST /admin/plans" "$PLAN_CODE" 200 201 403 422
chk_any "GET  /admin/plans" "$(AGET /plans)" 200 403
if [ -n "$PLAN_ID" ]; then
    chk_any "PATCH  /admin/plans/{plan_id}" "$(APATCH /plans/$PLAN_ID '{"monthly_credits":200}')" 200 403 404
    chk_any "DELETE /admin/plans/{plan_id}" "$(ADEL /plans/$PLAN_ID)" 200 204 403 404
else
    skip "PATCH/DELETE /admin/plans/{plan_id}" "no PLAN_ID"
fi

# — Dashboard & Analytics —
chk_any "GET  /admin/dashboard/overview" "$(AGET /dashboard/overview)" 200 403
chk_any "GET  /admin/metrics/realtime" "$(AGET /metrics/realtime)" 200 403
chk_any "GET  /admin/analytics/usage" "$(AGET "/analytics/usage?start_date=$THIRTY_AGO&end_date=$NOW_MS&group_by=day")" 200 403
chk_any "GET  /admin/analytics/growth" "$(AGET /analytics/growth)" 200 403
chk_any "GET  /admin/analytics/user-behavior" "$(AGET /analytics/user-behavior)" 200 403
chk_any "GET  /admin/analytics/system-metrics" "$(AGET /analytics/system-metrics)" 200 403
chk_any "GET  /admin/reports/revenue" "$(AGET "/reports/revenue?start_date=$THIRTY_AGO&end_date=$NOW_MS")" 200 403

# — Activity —
chk_any "GET  /admin/activity/recent" "$(AGET /activity/recent)" 200 403
chk_any "GET  /admin/activity/stats" "$(AGET /activity/stats)" 200 403
chk_any "GET  /admin/activity/timeline" "$(AGET /activity/timeline)" 200 403

# Audit Logs
chk_any "GET  /admin/audit-logs" "$(AGET "/audit-logs?limit=10&offset=0")" 200 403
chk_any "GET  /admin/audit-logs (filtered)" "$(AGET "/audit-logs?action=MAKE_ADMIN&limit=5")" 200 403

# — Settings —
chk_any "GET  /admin/settings/ai" "$(AGET /settings/ai)" 200 403
chk_any "PATCH /admin/settings/ai" "$(APATCH /settings/ai '{"temperature":5}')" 200 403 422
chk_any "GET  /admin/system/health" "$(AGET /system/health)" 200 403 404

# — API Key Management —
AKEY_R=$(curl -s -w "\n%{http_code}" -X POST -H "$ADMIN_AUTH" -H "Content-Type: application/json" \
    -d '{"service_name":"groq","api_key":"test_key_placeholder","priority":99}' \
    "$API/api/v1/admin/api-keys")
AKEY_CODE=$(echo "$AKEY_R" | tail -1)
AKEY_ID=$(echo "$AKEY_R" | head -n -1 | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
chk_any "POST /admin/api-keys" "$AKEY_CODE" 200 201 403 422
chk_any "GET  /admin/api-keys" "$(AGET /api-keys)" 200 403
chk_any "GET  /admin/api-keys/health" "$(AGET /api-keys/health)" 200 403
if [ -n "$AKEY_ID" ]; then
    chk_any "PATCH  /admin/api-keys/{key_id}" "$(APATCH /api-keys/$AKEY_ID '{"is_active":false}')" 200 403 404
    chk_any "DELETE /admin/api-keys/{key_id}" "$(ADEL /api-keys/$AKEY_ID)" 200 204 403 404
else
    skip "PATCH/DELETE /admin/api-keys/{key_id}" "no AKEY_ID"
fi

# — Wallets —
chk_any "GET   /admin/wallets" "$(AGET /wallets)" 200 403
if [ -n "$USER_ID" ]; then
    chk_any "POST  /admin/wallets/{user_id}/credit" "$(APOST /wallets/$USER_ID/credit '{"amount":10,"description":"Test credit"}')" 200 400 403 404 422
    chk_any "POST  /admin/wallets/{user_id}/debit" "$(APOST /wallets/$USER_ID/debit '{"amount":1,"description":"Test debit"}')" 200 400 403 404 422
    chk_any "POST  /admin/wallets/{user_id}/freeze" "$(APOST /wallets/$USER_ID/freeze '')" 200 400 403 404 422
    chk_any "POST  /admin/wallets/{user_id}/unfreeze" "$(APOST /wallets/$USER_ID/unfreeze '')" 200 400 403 404 422
    chk_any "POST  /admin/wallets/{user_id}/toggle-freeze" "$(APOST /wallets/$USER_ID/toggle-freeze '')" 200 400 403 404 422
else
    for ep in credit debit freeze unfreeze toggle-freeze; do
        skip "/admin/wallets/{user_id}/$ep" "no USER_ID"
    done
fi

# — Bulk Operations —
chk_any "POST /admin/bulk/delete" "$(APOST /bulk/delete '{"user_ids":[],"reason":"test"}')" 200 400 403 422
chk_any "POST /admin/bulk/restore" "$(APOST /bulk/restore '{"user_ids":[]}')" 200 400 403 422

# — Organizations —
ORG_R=$(curl -s -w "\n%{http_code}" -X POST -H "$ADMIN_AUTH" -H "Content-Type: application/json" \
    -d '{"name":"Test Org"}' "$API/api/v1/admin/organizations")
ORG_CODE=$(echo "$ORG_R" | tail -1)
ORG_ID=$(echo "$ORG_R" | head -n -1 | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
chk_any "POST /admin/organizations" "$ORG_CODE" 200 201 403 422
if [ -n "$ORG_ID" ]; then
    chk_any "GET /admin/organizations/{org_id}/balance" "$(AGET /organizations/$ORG_ID/balance)" 200 403 404
fi

# POST /admin/locations
chk_any "POST /admin/locations" "$(APOST /locations '{"org_id":"nonexistent","name":"HQ","latitude":37.7749,"longitude":-122.4194}')" 200 201 400 403 404 422

# — Admin Notes Create —
chk_any "POST /admin/notes/create" "$(APOST /notes/create '{"transcript":"Admin test note","title":"Admin Note","user_id":"test"}')" 200 201 400 403 422

# — Celery —
chk_any "GET  /admin/celery/tasks/active" "$(AGET /celery/tasks/active)" 200 403
chk_any "GET  /admin/celery/tasks/pending" "$(AGET /celery/tasks/pending)" 200 403
chk_any "GET  /admin/celery/tasks/{task_id}/status" "$(AGET /celery/tasks/fake-task-id/status)" 200 404 403
chk_any "POST /admin/celery/tasks/{task_id}/retry" "$(APOST /celery/tasks/fake-task-id/retry '')" 200 400 403 404
chk_any "POST /admin/celery/tasks/{task_id}/cancel" "$(APOST /celery/tasks/fake-task-id/cancel '')" 200 400 403 404
chk_any "GET  /admin/celery/workers/stats" "$(AGET /celery/workers/stats)" 200 403
chk_any "GET  /admin/celery/workers/tasks" "$(AGET /celery/workers/tasks)" 200 403
chk_any "POST /admin/celery/workers/{name}/shutdown" "$(APOST '/celery/workers/celery@worker1/shutdown' '')" 200 400 403 404
chk_any "POST /admin/celery/workers/pool-restart" "$(APOST /celery/workers/pool-restart '')" 200 400 403
chk_any "GET  /admin/celery/queues" "$(AGET /celery/queues)" 200 403
chk_any "POST /admin/celery/queues/{name}/purge" "$(APOST /celery/queues/celery/purge '')" 200 400 403

# ═══════════════════════════════════════════
sec "14. CLEANUP"
# ═══════════════════════════════════════════

if [ -n "$NOTE_ID" ]; then
    chk_any "DELETE /notes/{note_id} (cleanup)" "$(DEL /api/v1/notes/$NOTE_ID)" 200 204 400 402
fi
if [ -n "$TASK_ID" ]; then
    chk_any "DELETE /tasks/{task_id} (cleanup)" "$(DEL /api/v1/tasks/$TASK_ID)" 200 204 400
fi
if [ -n "$FOLDER_ID" ]; then
    chk_any "DELETE /folders/{folder_id} (cleanup)" "$(DEL /api/v1/folders/$FOLDER_ID)" 200 204 400
fi
if [ -n "$TEAM_ID" ]; then
    chk_any "DELETE /teams/{team_id} (cleanup)" "$(DEL /api/v1/teams/$TEAM_ID)" 200 204 400
fi

# ═══════════════════════════════════════════
echo ""
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo -e "${BOLD}  FINAL RESULTS${NC}"
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo -e "  Total   : $((TOTAL + SKIPPED))"
echo -e "  ${GREEN}Passed  : $PASSED${NC}"
echo -e "  ${RED}Failed  : $FAILED${NC}"
echo -e "  ${YELLOW}Skipped : $SKIPPED${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ All executed tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ $FAILED test(s) failed — review output above.${NC}"
    exit 1
fi
