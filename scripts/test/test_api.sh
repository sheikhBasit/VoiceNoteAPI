#!/bin/bash

# Configuration
BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="/tmp/robust_api_report_$TIMESTAMP.txt"
DETAILED_LOG="/tmp/robust_api_detailed_$TIMESTAMP.json"

# Test counters (File-based for subshell persistence)
SEC_K="VN_SECURE_8f7d9a2b_2026"
rm -f /tmp/api_passed /tmp/api_failed /tmp/api_total
echo 0 > /tmp/api_passed
echo 0 > /tmp/api_failed
echo 0 > /tmp/api_total
PASSED=0; FAILED=0; TOTAL=0; SKIPPED=0

# Colors
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
BLUE='\033[0;36m'; CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; NC='\033[0m'

# Common Curl Options for Robustness
CURL_OPTS=(-s -L --connect-timeout 10 --max-time 60)

# Report Initialization
{
    echo "================================================================================"
    echo "              VOICENOTE API STRESS & ROBUSTNESS REPORT"
    echo "================================================================================"
    echo "Date: $(date)"
    echo "Base: $BASE_URL"
    echo "================================================================================"
} > "$REPORT_FILE"

echo "{\"test_run\":{\"start\":\"$(date -Iseconds)\"},\"results\":[]}" > "$DETAILED_LOG"

get_ms() { date +%s%3N; }

log_test() {
    local n="$1"; local m="$2"; local e="$3"; local p="$4"; local ex="$5"; local ac="$6"; local b="$7"; local l="$8"
    local s="FAIL"; local c=$RED
    if [[ "$ex" =~ $ac ]]; then 
        s="PASS"; c=$GREEN
        echo $(( $(cat /tmp/api_passed 2>/dev/null || echo 0) + 1 )) > /tmp/api_passed
    else 
        echo $(( $(cat /tmp/api_failed 2>/dev/null || echo 0) + 1 )) > /tmp/api_failed
    fi
    echo $(( $(cat /tmp/api_total 2>/dev/null || echo 0) + 1 )) > /tmp/api_total
    
    local ac_total=$(cat /tmp/api_total)
    printf "${c}%-5s${NC} [%s] %-40s (%4sms)\n" "$s" "$ac" "$n" "$l" >&2
    { echo "[$s] $n ($m $e) | Code: $ac | Latency: ${l}ms"; echo "Payload: $p"; echo "Response: ${b:0:500}"; echo "---"; } >> "$REPORT_FILE"
}

generate_signature() {
    local method="$1"; local ep="$2"; local payload="$3"; local ts="$4"
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
    local n="$1"; local m="$2"; local e="$3"; local p="$4"; local ex="$5"; local t="$6"; local use_sig="$7"
    local start=$(get_ms)
    local opts=("${CURL_OPTS[@]}" -w "\n%{http_code}" -X "$m" "$BASE_URL$e")
    
    [ -n "$p" ] && opts+=(-H "Content-Type: application/json" -d "$p")
    [ -n "$t" ] && opts+=(-H "Authorization: Bearer $t")
    
    if [[ "$use_sig" == "true" ]]; then
        local ts=$(date +%s)
        local sig=$(generate_signature "$m" "$e" "$p" "$ts")
        opts+=("-H" "X-Device-Signature: $sig" -H "X-Device-Timestamp: $ts")
    fi

    local resp=$(curl "${opts[@]}")
    local end=$(get_ms); local lat=$((end - start))
    local code=$(echo "$resp" | tail -n1); local body=$(echo "$resp" | sed '$d')
    log_test "$n" "$m" "$e" "$p" "$ex" "$code" "$body" "$lat"
    echo "$body"
}

benchmark() {
    local l="$1"; local e="$2"; local c="$3"; local t="$4"
    echo -n "Benchmarking $l ($c users)... "
    local s=$(get_ms); local tmp="/tmp/bench_$$"; mkdir -p "$tmp"
    for i in $(seq 1 $c); do
        ( curl "${CURL_OPTS[@]}" -o /dev/null -w "%{http_code}\n" "$BASE_URL$e" -H "Authorization: Bearer $t" >> "$tmp/codes" ) &
    done
    wait
    local e_lat=$(get_ms); local d=$((e_lat-s)); local pass=$(grep -c "200" "$tmp/codes" 2>/dev/null || echo 0)
    local tps=$(awk "BEGIN {printf \"%.2f\", $c*1000/$d}")
    echo -e "${GREEN}$pass/$c Success${NC} | ${d}ms | $tps req/s"
    { echo "LOAD TEST: $l ($c users)"; echo "Pass Rate: $pass/$c | Throughput: $tps req/s"; echo "---"; } >> "$REPORT_FILE"
    rm -rf "$tmp"
}

# Wait for server to be ready
echo -n "Waiting for server to be ready..." >&2
for i in {1..30}; do
    if curl -s "${CURL_OPTS[@]}" "$BASE_URL/health" > /dev/null; then
        echo -e " ${GREEN}Ready!${NC}" >&2
        echo -e "Stabilizing for 15s (AI warmup finish)..." >&2
        sleep 15
        break
    fi
    echo -n "." >&2
    sleep 2
done

echo -e "\n${MAGENTA}===> STEP 1: AUTHENTICATION & USERS${NC}\n" >&2
U1_EMAIL="u1_$TIMESTAMP@test.com"
U2_EMAIL="u2_$TIMESTAMP@test.com"

U1_PL="{\"email\":\"$U1_EMAIL\",\"name\":\"User1\",\"password\":\"testpass123\",\"device_id\":\"d1_$TIMESTAMP\",\"device_model\":\"RobustRunner\",\"token\":\"t1\",\"timezone\":\"UTC\"}"
BODY=$(run_test "User1 Register" "POST" "/api/v1/users/register" "$U1_PL" "200|201" "")
U1_TOKEN=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('access_token',''), end='')")
U1_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('user',{}).get('id',''), end='')")

U2_PL="{\"email\":\"$U2_EMAIL\",\"name\":\"User2\",\"password\":\"testpass123\",\"device_id\":\"d2_$TIMESTAMP\",\"device_model\":\"RobustRunner\",\"token\":\"t2\",\"timezone\":\"UTC\"}"
BODY=$(run_test "User2 Register" "POST" "/api/v1/users/register" "$U2_PL" "200|201" "")
U2_TOKEN=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('access_token',''), end='')")
U2_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('user',{}).get('id',''), end='')")

if [ -z "$U1_TOKEN" ] || [ -z "$U2_TOKEN" ]; then
    echo -e "${RED}ERROR: Failed to obtain user tokens. Aborting functional tests.${NC}"
else
    run_test "User1 Profile" "GET" "/api/v1/users/me" "" "200" "$U1_TOKEN"
    run_test "update Profile" "PATCH" "/api/v1/users/me" "{\"name\":\"User1 Updated\"}" "200" "$U1_TOKEN" "true"

    echo -e "\n${BLUE}===> STEP 2: RESOURCE CRUD & FOLDER CASCADE${NC}\n" >&2
    BODY=$(run_test "Create Folder" "POST" "/api/v1/folders" "{\"name\":\"Work_$TIMESTAMP\"}" "201" "$U1_TOKEN")
    F1_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    echo -e "Folder Created: $F1_ID" >&2
    
    BODY=$(run_test "Create Note in Folder" "POST" "/api/v1/notes/create" "{\"title\":\"Note in Folder\",\"folder_id\":\"$F1_ID\"}" "201" "$U1_TOKEN")
    N1_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    echo -e "Note Created: $N1_ID (Expected Folder: $F1_ID)" >&2
    
    # Verify Cascade Part 1: Folder Delete -> Note unlinked
    run_test "Delete Folder" "DELETE" "/api/v1/folders/$F1_ID" "" "200" "$U1_TOKEN"
    sleep 1
    BODY=$(run_test "Verify Note Still Exists" "GET" "/api/v1/notes/$N1_ID" "" "200" "$U1_TOKEN")
    F_ID_AFTER=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('folder_id'))")
    
    if [ "$F_ID_AFTER" == "None" ] || [ "$F_ID_AFTER" == "null" ] || [ -z "$F_ID_AFTER" ]; then
        echo -e "${GREEN}PASS  Cascade Folder -> Note (SET NULL)${NC}" >&2
    else
        echo -e "${RED}FAIL  Cascade Folder -> Note (Expected null, got [$F_ID_AFTER])${NC}" >&2
        echo -e "Debug Note Body: $BODY" >&2
        ((FAILED++))
    fi

    echo -e "\n${BLUE}===> STEP 3: TASKS CRUD & NOTE CASCADE${NC}\n" >&2
    # Create Note for tasks
    BODY=$(run_test "Create Note for Tasks" "POST" "/api/v1/notes/create" "{\"title\":\"Note for Tasks\"}" "201" "$U1_TOKEN")
    N2_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    
    BODY=$(run_test "Create Task" "POST" "/api/v1/tasks" "{\"description\":\"Do this task\",\"note_id\":\"$N2_ID\",\"priority\":\"HIGH\"}" "201" "$U1_TOKEN")
    T1_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    
    run_test "Complete Task" "PATCH" "/api/v1/tasks/$T1_ID/complete" "{\"is_done\":true}" "200" "$U1_TOKEN"
    run_test "Get Task" "GET" "/api/v1/tasks/$T1_ID" "" "200" "$U1_TOKEN"
    
    # Verify Cascade Part 2: Note Delete -> Task Purged
    run_test "Delete Note" "DELETE" "/api/v1/notes/$N2_ID" "" "200" "$U1_TOKEN"
    run_test "Verify Task Purged" "GET" "/api/v1/tasks/$T1_ID" "" "404" "$U1_TOKEN"

    echo -e "\n${BLUE}===> STEP 4: TEAMS & COLLABORATION${NC}\n" >&2
    BODY=$(run_test "Create Team" "POST" "/api/v1/teams?name=TestTeam" "" "201" "$U1_TOKEN")
    TM1_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    
    run_test "Add U2 to Team" "POST" "/api/v1/teams/$TM1_ID/members?user_email=$U2_EMAIL" "" "200" "$U1_TOKEN"
    run_test "List Teams U2" "GET" "/api/v1/teams" "" "200" "$U2_TOKEN"
    
    # Verify Cascade Part 3: Team Delete -> Association Cleanup
    run_test "Delete Team" "DELETE" "/api/v1/teams/$TM1_ID" "" "200" "$U1_TOKEN"
    
    BODY=$(run_test "Verify U2 Teams Empty" "GET" "/api/v1/teams" "" "200" "$U2_TOKEN")
    if [[ "$BODY" == "[]" ]]; then
        echo -e "${GREEN}PASS  Cascade Team -> Members Cleanup${NC}" >&2
    else
        echo -e "${RED}FAIL  Cascade Team -> Members Cleanup (Got $BODY)${NC}" >&2
        ((FAILED++))
    fi

    echo -e "\n${BLUE}===> STEP 5: SECURITY, REAL-TIME & ADMIN${NC}\n" >&2
    run_test "No Auth Check" "GET" "/api/v1/users/me" "" "401" ""
    run_test "SQLi Probe (AI Sync)" "POST" "/api/v1/ai/search" "{\"query\":\"' OR 1=1\"}" "200|400|422" "$U1_TOKEN"
    
    # Real-time connectivity checks (Streaming GET with timeout)
    curl -s --max-time 2 "$BASE_URL/api/v1/sse" -H "Authorization: Bearer $U1_TOKEN" > /dev/null && echo -e "${GREEN}PASS  SSE endpoint responsive${NC}" || echo -e "${RED}FAIL  SSE endpoint non-responsive${NC}"
    
    run_test "Task Statistics" "GET" "/api/v1/tasks/stats" "" "200" "$U1_TOKEN"
    run_test "User Search" "GET" "/api/v1/users/search?query=User1" "" "200" "$U1_TOKEN"
    
    # Admin stats (if env allows or mocking admin)
    run_test "Admin Stats" "GET" "/api/v1/admin/users/stats" "" "200|403" "$U1_TOKEN"

    echo -e "\n${MAGENTA}===> STEP 6: DDOS & LOAD PERFORMANCE${NC}\n" >&2
    ST=$(get_ms); CNT=30; SC=0
    for i in $(seq 1 $CNT); do
        code=$(curl "${CURL_OPTS[@]}" -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/users/me" -H "Authorization: Bearer $U1_TOKEN")
        [ "$code" == "200" ] && ((SC++))
    done
    EN=$(get_ms); DUR=$((EN - ST)); TPS=$(awk "BEGIN {printf \"%.2f\", $CNT*1000/$DUR}")
    echo -e "Burst Finished: $SC/$CNT Pass | ${DUR}ms | $TPS req/s"

    benchmark "List Notes" "/api/v1/notes" 15 "$U1_TOKEN"
    benchmark "Get Dashboard" "/api/v1/notes/dashboard" 10 "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 8: AUTHENTICATION & SESSION MANAGEMENT${NC}\n" >&2
    run_test "Login User1" "POST" "/api/v1/users/login" "{\"email\":\"$U1_EMAIL\",\"password\":\"testpass123\",\"device_id\":\"d1_login\"}" "200" ""
    # Refresh token test - expects 400/401 for invalid token (testing error handling)
    run_test "Refresh Token" "POST" "/api/v1/users/refresh" "{\"refresh_token\":\"invalid_token\"}" "400|401" ""
    run_test "Logout" "POST" "/api/v1/users/logout" "" "200" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 9: ADVANCED NOTE OPERATIONS${NC}\n" >&2
    run_test "Get Presigned URL" "GET" "/api/v1/notes/presigned-url" "" "200" "$U1_TOKEN"
    run_test "Autocomplete" "GET" "/api/v1/notes/autocomplete?q=test" "" "200" "$U1_TOKEN"
    
    BODY=$(run_test "Create Note for Restore" "POST" "/api/v1/notes/create" "{\"title\":\"To Restore\"}" "201" "$U1_TOKEN")
    N_RESTORE_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    run_test "Delete Note for Restore" "DELETE" "/api/v1/notes/$N_RESTORE_ID" "" "200" "$U1_TOKEN"
    run_test "Restore Note" "PATCH" "/api/v1/notes/$N_RESTORE_ID/restore" "" "200" "$U1_TOKEN"
    run_test "Get WhatsApp Draft" "GET" "/api/v1/notes/$N_RESTORE_ID/whatsapp" "" "200" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 10: ADVANCED TASK OPERATIONS${NC}\n" >&2
    BODY=$(run_test "Create Note for Tasks" "POST" "/api/v1/notes/create" "{\"title\":\"Task Note\"}" "201" "$U1_TOKEN")
    N_TASK_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    
    BODY=$(run_test "Create Task Advanced" "POST" "/api/v1/tasks" "{\"description\":\"Advanced task\",\"note_id\":\"$N_TASK_ID\",\"priority\":\"HIGH\"}" "201" "$U1_TOKEN")
    T_ADV_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    
    run_test "List Tasks" "GET" "/api/v1/tasks?limit=10" "" "200" "$U1_TOKEN"
    run_test "Tasks Due Today" "GET" "/api/v1/tasks/due-today" "" "200" "$U1_TOKEN"
    run_test "Overdue Tasks" "GET" "/api/v1/tasks/overdue" "" "200" "$U1_TOKEN"
    run_test "Tasks Assigned to Me" "GET" "/api/v1/tasks/assigned-to-me" "" "200" "$U1_TOKEN"
    run_test "Search Tasks" "GET" "/api/v1/tasks/search?query_text=Advanced" "" "200" "$U1_TOKEN"
    run_test "Update Task" "PATCH" "/api/v1/tasks/$T_ADV_ID" "{\"priority\":\"MEDIUM\"}" "200" "$U1_TOKEN"
    run_test "Get Comm Options" "GET" "/api/v1/tasks/$T_ADV_ID/communication-options" "" "200" "$U1_TOKEN"
    run_test "Delete Task" "DELETE" "/api/v1/tasks/$T_ADV_ID" "" "200" "$U1_TOKEN"
    run_test "Restore Task" "PATCH" "/api/v1/tasks/$T_ADV_ID/restore" "" "200" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 11: FOLDER OPERATIONS${NC}\n" >&2
    run_test "List Folders" "GET" "/api/v1/folders" "" "200" "$U1_TOKEN"
    BODY=$(run_test "Create Folder Advanced" "POST" "/api/v1/folders" "{\"name\":\"Advanced Folder\"}" "201" "$U1_TOKEN")
    F_ADV_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    run_test "Update Folder" "PATCH" "/api/v1/folders/$F_ADV_ID" "{\"name\":\"Updated Folder\"}" "200" "$U1_TOKEN"
    run_test "Delete Folder Advanced" "DELETE" "/api/v1/folders/$F_ADV_ID" "" "200" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 12: TEAM COLLABORATION${NC}\n" >&2
    BODY=$(run_test "Create Team Advanced" "POST" "/api/v1/teams?name=AdvTeam" "" "201" "$U1_TOKEN")
    TM_ADV_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    run_test "Get Team Analytics" "GET" "/api/v1/teams/$TM_ADV_ID/analytics" "" "200" "$U1_TOKEN"
    run_test "Delete Team Advanced" "DELETE" "/api/v1/teams/$TM_ADV_ID" "" "200" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 13: INTEGRATIONS${NC}\n" >&2
    run_test "List Integrations" "GET" "/api/v1/integrations/list" "" "200" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 14: AI OPERATIONS${NC}\n" >&2
    run_test "AI Ask" "POST" "/api/v1/ai/ask" "{\"question\":\"What is this?\"}" "200|400|422|500" "$U1_TOKEN"
    run_test "AI Stats" "GET" "/api/v1/ai/stats" "" "200" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 15: USER OPERATIONS${NC}\n" >&2
    run_test "Get User Balance" "GET" "/api/v1/users/balance" "" "200" "$U1_TOKEN"
    run_test "Get User by ID" "GET" "/api/v1/users/$U1_ID" "" "200" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 16: ADMIN OPERATIONS${NC}\n" >&2
    run_test "List All Users (Admin)" "GET" "/api/v1/admin/users" "" "200|403" "$U1_TOKEN"
    run_test "Get Admin Status" "GET" "/api/v1/admin/status" "" "200|403" "$U1_TOKEN"
    run_test "List Admins" "GET" "/api/v1/admin/admins" "" "200|403" "$U1_TOKEN"
    run_test "Get User Devices (Admin)" "GET" "/api/v1/admin/users/$U1_ID/devices" "" "200|403" "$U1_TOKEN"
    run_test "Get User Usage (Admin)" "GET" "/api/v1/admin/users/$U1_ID/usage" "" "200|403" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 17: BILLING & WEBHOOKS${NC}\n" >&2
    run_test "List Plans" "GET" "/api/v1/admin/plans" "" "200|403" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 18: ADDITIONAL NOTE OPERATIONS${NC}\n" >&2
    BODY=$(run_test "Create Note for Search" "POST" "/api/v1/notes/create" "{\"title\":\"Search Test\",\"transcript\":\"This is a test note\"}" "201" "$U1_TOKEN")
    N_SEARCH_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    run_test "Semantic Search" "POST" "/api/v1/notes/search" "{\"query\":\"test\",\"limit\":5}" "200" "$U1_TOKEN"
    run_test "Update Note" "PATCH" "/api/v1/notes/$N_SEARCH_ID" "{\"title\":\"Updated Title\"}" "200" "$U1_TOKEN"
    run_test "Semantic Analysis" "POST" "/api/v1/notes/$N_SEARCH_ID/semantic-analysis" "" "202" "$U1_TOKEN"
    run_test "Bulk Delete Notes" "DELETE" "/api/v1/notes" "{\"note_ids\":[\"$N_SEARCH_ID\"]}" "200" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 19: ADDITIONAL TASK OPERATIONS${NC}\n" >&2
    BODY=$(run_test "Create Note for Task Ops" "POST" "/api/v1/notes/create" "{\"title\":\"Task Ops\"}" "201" "$U1_TOKEN")
    N_TASK_OPS_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    
    BODY=$(run_test "Create Task for Ops" "POST" "/api/v1/tasks" "{\"description\":\"Task ops test\",\"note_id\":\"$N_TASK_OPS_ID\",\"priority\":\"HIGH\"}" "201" "$U1_TOKEN")
    T_OPS_ID=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('id',''), end='')")
    
    run_test "Lock Task" "POST" "/api/v1/tasks/$T_OPS_ID/lock" "" "200" "$U1_TOKEN"
    run_test "Unlock Task" "DELETE" "/api/v1/tasks/$T_OPS_ID/lock" "" "200" "$U1_TOKEN"
    run_test "Add External Link" "POST" "/api/v1/tasks/$T_OPS_ID/external-links" "{\"url\":\"https://example.com\",\"title\":\"Example\"}" "201" "$U1_TOKEN"
    run_test "Task Statistics Alias" "GET" "/api/v1/tasks/statistics" "" "200" "$U1_TOKEN"
    run_test "Duplicate Task" "POST" "/api/v1/tasks/$T_OPS_ID/duplicate" "" "201" "$U1_TOKEN"
    run_test "Bulk Delete Tasks" "DELETE" "/api/v1/tasks" "{\"task_ids\":[\"$T_OPS_ID\"]}" "200" "$U1_TOKEN"
    
    echo -e "\n${CYAN}===> STEP 20: SYNC & BATCH OPERATIONS${NC}\n" >&2
    run_test "Batch Upload" "POST" "/api/v1/sync/upload-batch" "{\"notes\":[]}" "200|400|422" "$U1_TOKEN"
    
    echo -e "\n${MAGENTA}===> STEP 21: FINAL CASCADE (USER PURGE)${NC}\n" >&2
    # Delete User2 and verify all references gone
    run_test "Delete User2" "DELETE" "/api/v1/users/me" "" "200" "$U2_TOKEN" "true"
    run_test "Verify U2 Token Invalid" "GET" "/api/v1/users/me" "" "401" "$U2_TOKEN"
fi

PASSED=$(cat /tmp/api_passed)
FAILED=$(cat /tmp/api_failed)
TOTAL=$(cat /tmp/api_total)

echo -e "\n${MAGENTA}ROBUSTNESS TEST COMPLETE | Results: $PASSED/$TOTAL Pass${NC}"
echo -e "Final Report: ${CYAN}$REPORT_FILE${NC}"
echo -e "Detailed JSON Logs: $DETAILED_LOG\n"
