#!/bin/bash

# Configuration
API_URL=${API_URL:-"http://localhost:8000"}
OWNER_EMAIL="owner_$(date +%s)@example.com"
PART_EMAIL="part_$(date +%s)@example.com"
PASSWORD="testpass123"

echo "=== 1. Registering Owner ==="
OWNER_DATA=$(curl -s -X POST "$API_URL/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Owner\", \"email\": \"$OWNER_EMAIL\", \"password\": \"$PASSWORD\", \"timezone\": \"UTC\"}")
OWNER_TOKEN=$(echo $OWNER_DATA | grep -oP '(?<="access_token":")[^"]*')
echo "Owner Token: ${OWNER_TOKEN:0:10}..."

echo -e "\n=== 2. Registering Participant ==="
PART_DATA=$(curl -s -X POST "$API_URL/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Participant\", \"email\": \"$PART_EMAIL\", \"password\": \"$PASSWORD\", \"timezone\": \"UTC\"}")
PART_TOKEN=$(echo $PART_DATA | grep -oP '(?<="access_token":")[^"]*')
echo "Participant Token: ${PART_TOKEN:0:10}..."

echo -e "\n=== 3. Owner Creating Folder ==="
FOLDER_DATA=$(curl -s -X POST "$API_URL/api/v1/folders" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Shared Vault\", \"color\": \"#FF0000\"}")
FOLDER_ID=$(echo $FOLDER_DATA | grep -oP '(?<="id":")[^"]*')
echo "Folder ID: $FOLDER_ID"

echo -e "\n=== 4. Owner Creating Encrypted Note in Folder ==="
NOTE_DATA=$(curl -s -X POST "$API_URL/api/v1/notes/create" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Encrypted Strategy\",
    \"summary\": \"This is heavily encrypted content\",
    \"is_encrypted\": true,
    \"folder_id\": \"$FOLDER_ID\"
  }")
NOTE_ID=$(echo $NOTE_DATA | grep -oP '(?<="id":")[^"]*')
echo "Note ID: $NOTE_ID"

echo -e "\n=== 5. Sharing Folder with Participant ==="
curl -s -X POST "$API_URL/api/v1/folders/$FOLDER_ID/participants?user_email=$PART_EMAIL&role=EDITOR" \
  -H "Authorization: Bearer $OWNER_TOKEN"

echo -e "\n=== 6. Participant Listing Shared Folders ==="
curl -s -X GET "$API_URL/api/v1/folders" \
  -H "Authorization: Bearer $PART_TOKEN" | jq .

echo -e "\n=== 7. Owner Updating Folder ==="
curl -s -X PATCH "$API_URL/api/v1/folders/$FOLDER_ID" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Updated Shared Vault\", \"color\": \"#0000FF\"}" | jq .

echo -e "\n=== 8. Participant Retrieving Encrypted Note (Decrypted Access) ==="
curl -s -X GET "$API_URL/api/v1/notes/$NOTE_ID" \
  -H "Authorization: Bearer $PART_TOKEN" | jq .summary

echo -e "\n=== 9. Verifying Participants List ==="
curl -s -X GET "$API_URL/api/v1/folders/$FOLDER_ID/participants" \
  -H "Authorization: Bearer $PART_TOKEN" | jq .

echo -e "\n=== 10. Owner Deleting Folder (Notes should move to Uncategorized) ==="
curl -s -X DELETE "$API_URL/api/v1/folders/$FOLDER_ID" \
  -H "Authorization: Bearer $OWNER_TOKEN" | jq .

echo -e "\n=== 11. Verifying Note is now Uncategorized ==="
curl -s -X GET "$API_URL/api/v1/notes/$NOTE_ID" \
  -H "Authorization: Bearer $OWNER_TOKEN" | jq .folder_id

echo -e "\n=== Validation Complete ==="
