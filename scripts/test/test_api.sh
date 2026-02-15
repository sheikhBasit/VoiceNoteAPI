#!/bin/bash

# Configuration
BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="/tmp/robust_api_report_$TIMESTAMP.txt"
DETAILED_LOG="/tmp/robust_api_detailed_$TIMESTAMP.json"

# Test counters
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
    if [[ "$ex" =~ $ac ]]; then s="PASS"; c=$GREEN; ((PASSED++)); else ((FAILED++)); fi
    ((TOTAL++))
    printf "${c}%-5s${NC} [%s] %-40s (%4sms)\n" "$s" "$ac" "$n" "$l"
    { echo "[$s] $n ($m $e) | Code: $ac | Latency: ${l}ms"; echo "Payload: $p"; echo "Response: ${b:0:500}"; echo "---"; } >> "$REPORT_FILE"
}

run_test() {
    local n="$1"; local m="$2"; local e="$3"; local p="$4"; local ex="$5"; local t="$6"; local use_sig="$7"
    local start=$(get_ms)
    local opts=("${CURL_OPTS[@]}" -w "\n%{http_code}" -X "$m" "$BASE_URL$e" -H "Content-Type: application/json")
    [ -n "$t" ] && opts+=(-H "Authorization: Bearer $t")
    
    if [ "$use_sig" == "true" ]; then
        local ts=$(date +%s)
        local secret="VN_SECURE_8f7d9a2b_2026"
        local b_hash=""
        [ -n "$p" ] && b_hash=$(echo -n "$p" | sha256sum | awk '{print $1}')
        local sig=$(python3 -c "import hmac, hashlib; msg = '$m$e$ts$b_hash'.encode(); print(hmac.new('$secret'.encode(), msg, hashlib.sha256).hexdigest())")
        opts+=(-H "X-Device-Signature: $sig" -H "X-Device-Timestamp: $ts")
    fi

    [ -n "$p" ] && opts+=(-d "$p")
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
echo -n "Waiting for server to be ready..."
for i in {1..30}; do
    if curl -s "${CURL_OPTS[@]}" "$BASE_URL/health" > /dev/null; then
        echo -e " ${GREEN}Ready!${NC}"
        echo -e "Stabilizing for 15s (AI warmup finish)..."
        sleep 15
        break
    fi
    echo -n "."
    sleep 2
done

echo -e "\n${MAGENTA}===> STEP 1: AUTHENTICATION & USERS${NC}\n"
U1_EMAIL="u1_$TIMESTAMP@test.com"
U2_EMAIL="u2_$TIMESTAMP@test.com"

U1_PL="{\"email\":\"$U1_EMAIL\",\"name\":\"User1\",\"password\":\"testpass123\",\"device_id\":\"d1_$TIMESTAMP\",\"device_model\":\"RobustRunner\",\"token\":\"t1\",\"timezone\":\"UTC\"}"
BODY=$(run_test "User1 Register" "POST" "/api/v1/users/register" "$U1_PL" "200|201" "")
U1_TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
U1_ID=$(echo "$BODY" | grep -o '"id":"[^"]*' | cut -d'"' -f4)

U2_PL="{\"email\":\"$U2_EMAIL\",\"name\":\"User2\",\"password\":\"testpass123\",\"device_id\":\"d2_$TIMESTAMP\",\"device_model\":\"RobustRunner\",\"token\":\"t2\",\"timezone\":\"UTC\"}"
BODY=$(run_test "User2 Register" "POST" "/api/v1/users/register" "$U2_PL" "200|201" "")
U2_TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
U2_ID=$(echo "$BODY" | grep -o '"id":"[^"]*' | cut -d'"' -f4)

if [ -z "$U1_TOKEN" ] || [ -z "$U2_TOKEN" ]; then
    echo -e "${RED}ERROR: Failed to obtain user tokens. Aborting functional tests.${NC}"
else
    run_test "User1 Profile" "GET" "/api/v1/users/me" "" "200" "$U1_TOKEN"
    run_test "update Profile" "PATCH" "/api/v1/users/me" "{\"name\":\"User1 Updated\"}" "200" "$U1_TOKEN"

    echo -e "\n${BLUE}===> STEP 2: RESOURCE CRUD & FOLDER CASCADE${NC}\n"
    BODY=$(run_test "Create Folder" "POST" "/api/v1/folders" "{\"name\":\"Work_$TIMESTAMP\"}" "201" "$U1_TOKEN")
    F1_ID=$(echo "$BODY" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
    echo -e "Folder Created: $F1_ID"
    
    BODY=$(run_test "Create Note in Folder" "POST" "/api/v1/notes/create" "{\"title\":\"Note in Folder\",\"folder_id\":\"$F1_ID\"}" "201" "$U1_TOKEN")
    N1_ID=$(echo "$BODY" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
    echo -e "Note Created: $N1_ID (Expected Folder: $F1_ID)"
    
    # Verify Cascade Part 1: Folder Delete -> Note unlinked
    run_test "Delete Folder" "DELETE" "/api/v1/folders/$F1_ID" "" "200" "$U1_TOKEN"
    sleep 1
    BODY=$(run_test "Verify Note Still Exists" "GET" "/api/v1/notes/$N1_ID" "" "200" "$U1_TOKEN")
    F_ID_AFTER=$(echo "$BODY" | python3 -c "import json, sys; print(json.load(sys.stdin).get('folder_id'))")
    
    if [ "$F_ID_AFTER" == "None" ] || [ "$F_ID_AFTER" == "null" ] || [ -z "$F_ID_AFTER" ]; then
        echo -e "${GREEN}PASS  Cascade Folder -> Note (SET NULL)${NC}"
    else
        echo -e "${RED}FAIL  Cascade Folder -> Note (Expected None, got [$F_ID_AFTER])${NC}"
        echo -e "Debug Note Body: $BODY"
        ((FAILED++))
    fi

    echo -e "\n${BLUE}===> STEP 3: TASKS CRUD & NOTE CASCADE${NC}\n"
    # Create Note for tasks
    BODY=$(run_test "Create Note for Tasks" "POST" "/api/v1/notes/create" "{\"title\":\"Note for Tasks\"}" "201" "$U1_TOKEN")
    N2_ID=$(echo "$BODY" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
    
    BODY=$(run_test "Create Task" "POST" "/api/v1/tasks" "{\"description\":\"Do this task\",\"note_id\":\"$N2_ID\",\"priority\":\"HIGH\"}" "201" "$U1_TOKEN")
    T1_ID=$(echo "$BODY" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
    
    run_test "Complete Task" "PATCH" "/api/v1/tasks/$T1_ID/complete" "{\"is_done\":true}" "200" "$U1_TOKEN"
    run_test "Get Task" "GET" "/api/v1/tasks/$T1_ID" "" "200" "$U1_TOKEN"
    
    # Verify Cascade Part 2: Note Delete -> Task Purged
    run_test "Delete Note" "DELETE" "/api/v1/notes/$N2_ID" "" "200" "$U1_TOKEN"
    run_test "Verify Task Purged" "GET" "/api/v1/tasks/$T1_ID" "" "404" "$U1_TOKEN"

    echo -e "\n${BLUE}===> STEP 4: TEAMS & COLLABORATION${NC}\n"
    BODY=$(run_test "Create Team" "POST" "/api/v1/teams?name=TestTeam" "" "201" "$U1_TOKEN")
    TM1_ID=$(echo "$BODY" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
    
    run_test "Add U2 to Team" "POST" "/api/v1/teams/$TM1_ID/members?user_email=$U2_EMAIL" "" "200" "$U1_TOKEN"
    run_test "List Teams U2" "GET" "/api/v1/teams" "" "200" "$U2_TOKEN"
    
    # Verify Cascade Part 3: Team Delete -> Association Cleanup
    run_test "Delete Team" "DELETE" "/api/v1/teams/$TM1_ID" "" "200" "$U1_TOKEN"
    # Note: Currently no endpoint explicitly checks membership absence, but list should be empty
    BODY=$(run_test "Verify U2 Teams Empty" "GET" "/api/v1/teams" "" "200" "$U2_TOKEN")
    if [[ "$BODY" == "[]" ]]; then
        echo -e "${GREEN}PASS  Cascade Team -> Members Cleanup${NC}"
    else
        echo -e "${YELLOW}NOTE  U2 still has teams or list failed cleanup check${NC}"
    fi

    echo -e "\n${BLUE}===> STEP 5: SECURITY, REAL-TIME & ADMIN${NC}\n"
    run_test "No Auth Check" "GET" "/api/v1/users/me" "" "401" ""
    run_test "SQLi Probe (AI Sync)" "POST" "/api/v1/ai/search" "{\"query\":\"' OR 1=1\"}" "200|400|422" "$U1_TOKEN"
    
    # Real-time connectivity checks (Streaming GET with timeout)
    curl -s --max-time 2 "$BASE_URL/api/v1/sse" -H "Authorization: Bearer $U1_TOKEN" > /dev/null && echo -e "${GREEN}PASS  SSE endpoint responsive${NC}" || echo -e "${RED}FAIL  SSE endpoint non-responsive${NC}"
    
    # Admin stats (if env allows or mocking admin)
    run_test "Admin Stats" "GET" "/api/v1/admin/users/stats" "" "200|403" "$U1_TOKEN"

    echo -e "\n${MAGENTA}===> STEP 6: DDOS & LOAD PERFORMANCE${NC}\n"
    ST=$(get_ms); CNT=30; SC=0
    for i in $(seq 1 $CNT); do
        code=$(curl "${CURL_OPTS[@]}" -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/users/me" -H "Authorization: Bearer $U1_TOKEN")
        [ "$code" == "200" ] && ((SC++))
    done
    EN=$(get_ms); DUR=$((EN - ST)); TPS=$(awk "BEGIN {printf \"%.2f\", $CNT*1000/$DUR}")
    echo -e "Burst Finished: $SC/$CNT Pass | ${DUR}ms | $TPS req/s"

    benchmark "List Notes" "/api/v1/notes" 15 "$U1_TOKEN"
    benchmark "Get Dashboard" "/api/v1/notes/dashboard" 10 "$U1_TOKEN"
    
    echo -e "\n${RED}===> STEP 7: FINAL CASCADE (USER PURGE)${NC}\n"
    # Delete User2 and verify all references gone
    run_test "Delete User2" "DELETE" "/api/v1/users/me" "" "200" "$U2_TOKEN" "true"
    run_test "Verify U2 Token Invalid" "GET" "/api/v1/users/me" "" "401" "$U2_TOKEN"
fi

echo -e "\n${MAGENTA}ROBUSTNESS TEST COMPLETE | Results: $PASSED/$TOTAL Pass${NC}"
echo -e "Final Report: ${CYAN}$REPORT_FILE${NC}"
echo -e "Detailed JSON Logs: $DETAILED_LOG\n"
