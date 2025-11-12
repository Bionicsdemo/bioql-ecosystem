#!/bin/bash

echo "🧪 Testing BioQL Agent Endpoint"
echo "================================"
echo ""

API_KEY="__BIOQL_REDACTED__"
ENDPOINT="https://spectrix--bioql-agent-create-fastapi-app.modal.run"

echo "📡 Endpoint: $ENDPOINT"
echo "🔑 API Key: ${API_KEY:0:20}..."
echo ""

echo "Test 1: Simple request"
echo "----------------------"
RESPONSE=$(curl -s -X POST "$ENDPOINT" \
  -H 'Content-Type: application/json' \
  -d "{\"api_key\": \"$API_KEY\", \"request\": \"hello\"}")

SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))")
ACTION=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('action', 'none'))")

echo "Success: $SUCCESS"
echo "Action: $ACTION"
echo ""

echo "Test 2: Bell state request"
echo "--------------------------"
RESPONSE=$(curl -s -X POST "$ENDPOINT" \
  -H 'Content-Type: application/json' \
  -d "{\"api_key\": \"$API_KEY\", \"request\": \"Generate Bell state on IBM simulator with 1000 shots no QEC\"}")

SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))")
ACTION=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('action', 'none'))")
HAS_CODE=$(echo "$RESPONSE" | python3 -c "import sys, json; print('code' in json.load(sys.stdin))")

echo "Success: $SUCCESS"
echo "Action: $ACTION"
echo "Has Code: $HAS_CODE"
echo ""

if [ "$SUCCESS" = "True" ]; then
    echo "✅ Agent is working correctly!"
else
    echo "❌ Agent has issues"
    echo "Response: $RESPONSE"
fi

echo ""
echo "================================"
echo "If you see '✅ Agent is working correctly!', the server is fine."
echo "The issue is likely in the VSCode extension configuration."
echo ""
echo "To fix in VSCode:"
echo "1. Open Settings (Cmd+,)"
echo "2. Search for 'bioql'"
echo "3. Set 'bioql.apiKey' to: $API_KEY"
echo "4. Set 'bioql.mode' to: modal"
echo "5. Reload Window (Cmd+Shift+P -> 'Developer: Reload Window')"
