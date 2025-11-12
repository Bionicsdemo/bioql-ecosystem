#!/bin/bash
# Wait for Modal server to be ready

URL="https://spectrix--bioql-vscode-fastapi-app.modal.run/health"
MAX_WAIT=300  # 5 minutes
ELAPSED=0

echo "🔄 Waiting for Modal server to load..."
echo "   This may take 2-5 minutes for cold start"
echo ""

while [ $ELAPSED -lt $MAX_WAIT ]; do
    RESPONSE=$(curl -s -w "\n%{http_code}" "$URL" 2>&1)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)

    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Server ready!"
        echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
        echo ""
        echo "🎉 You can now use @bioql in VS Code!"
        exit 0
    fi

    echo -ne "\r⏳ Waiting... ${ELAPSED}s elapsed"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

echo ""
echo "❌ Timeout after ${MAX_WAIT}s"
echo "Check logs: modal app logs bioql-vscode"
exit 1
