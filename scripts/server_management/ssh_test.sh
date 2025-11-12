#!/bin/bash
# Test SSH connection to BioQL server

SERVER="167.71.86.90"
USER="root"

echo "=========================================="
echo "🔍 Testing SSH to $SERVER"
echo "=========================================="

# Test 1: Port is open
echo ""
echo "Test 1: Checking if SSH port is open..."
if nc -zv -w 3 $SERVER 22 2>&1 | grep -q succeeded; then
    echo "✅ Port 22 is OPEN"
else
    echo "❌ Port 22 is CLOSED"
    exit 1
fi

# Test 2: Get SSH banner
echo ""
echo "Test 2: Getting SSH banner..."
BANNER=$(timeout 5 bash -c "exec 3<>/dev/tcp/$SERVER/22 && cat <&3" 2>/dev/null | head -1)
if [ ! -z "$BANNER" ]; then
    echo "✅ SSH Banner: $BANNER"
else
    echo "⚠️  Could not get SSH banner"
fi

# Test 3: Try interactive SSH (will prompt for password)
echo ""
echo "Test 3: Attempting SSH connection..."
echo "Password: P31e27r12u1@HJG"
echo ""
echo "Ejecuta este comando MANUALMENTE en otra terminal:"
echo ""
echo "  ssh $USER@$SERVER"
echo ""
echo "Y ejecuta estos comandos cuando conectes:"
echo ""
echo "  ps aux | grep python | grep bioql | head -5"
echo "  systemctl status nginx | head -3"
echo "  netstat -tulpn | grep LISTEN | grep -E '5001|5002|8100|9000'"
echo ""

echo "=========================================="
echo "SSH está respondiendo pero paramiko falla"
echo "Solución: Usar terminal SSH manual o esperar"
echo "=========================================="
