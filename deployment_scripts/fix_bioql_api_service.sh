#!/bin/bash
# Fix bioql-api.service on server

SERVER="root@167.71.86.90"

echo "🔍 Diagnosing bioql-api.service failure..."
echo ""

# Check the service logs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Service Logs (last 50 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh $SERVER 'journalctl -u bioql-api.service -n 50 --no-pager'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Checking if directory exists"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh $SERVER 'ls -la /root/bioql_apps/bioql_quillow_docking/web_interface/ 2>&1'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Checking service configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh $SERVER 'cat /etc/systemd/system/bioql-api.service'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Testing manual startup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh $SERVER << 'EOF'
cd /root/bioql_apps/bioql_quillow_docking/web_interface/
if [ -f venv/bin/python ]; then
    echo "✅ Virtual environment exists"
    echo "Testing Python..."
    venv/bin/python --version
    echo ""
    echo "Testing imports..."
    venv/bin/python -c "import flask; print('✅ Flask available')" 2>&1
    venv/bin/python -c "import gunicorn; print('✅ Gunicorn available')" 2>&1
else
    echo "❌ Virtual environment not found at venv/"
fi

if [ -f wsgi.py ]; then
    echo "✅ wsgi.py exists"
    head -20 wsgi.py
else
    echo "❌ wsgi.py not found"
fi

if [ -f gunicorn_config.py ]; then
    echo "✅ gunicorn_config.py exists"
    cat gunicorn_config.py
else
    echo "❌ gunicorn_config.py not found"
fi
EOF
