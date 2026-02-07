
#!/bin/bash
set -e

BASE_URL="http://localhost:8001"

echo "Waiting for API at $BASE_URL..."
until curl -s "$BASE_URL/health" > /dev/null; do
  sleep 1
done
echo "API is ready!"

# 1. Get Token
echo "Authenticating..."
TIMESTAMP=$(date +%s)
PAYLOAD=$(cat <<EOF
{
  "name": "Benchmark User",
  "email": "bench_${TIMESTAMP}@example.com",
  "token": "bench-bio-token",
  "device_id": "bench-device",
  "device_model": "CurlScript",
  "primary_role": "GENERIC",
  "timezone": "UTC"
}
EOF
)

TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/users/sync" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "Failed to get token"
  exit 1
fi

SHORT_TOKEN=$(echo $TOKEN | cut -c1-10)
echo "Got Token: ${SHORT_TOKEN}..."

# 2. Benchmark Endpoint
echo "Running benchmarks..."

run_bench() {
  local ENDPOINT=$1
  local METHOD=$2
  local DATA=$3
  
  echo "--- Testing $METHOD $ENDPOINT ---"
  for i in $(seq 1 5); do
    curl -w "Time: %{time_total}s\n" -o /dev/null -s \
      -X "$METHOD" "$BASE_URL$ENDPOINT" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "$DATA"
  done
}

run_bench "/health" "GET" ""
run_bench "/api/v1/integrations/list" "GET" ""
run_bench "/api/v1/integrations/google/connect" "POST" '{"code": "bench_auth_code"}'

# Simulate note creation (light payload)
run_bench "/api/v1/notes/create" "POST" '{"title": "Bench Note", "summary": "Just a test note"}'
