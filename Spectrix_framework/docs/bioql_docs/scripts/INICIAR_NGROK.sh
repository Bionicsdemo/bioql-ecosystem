#!/bin/bash
# Script para iniciar ngrok manualmente

echo "════════════════════════════════════════════════════════════════════════════"
echo "🌐 Iniciando ngrok tunnel para BioQL Server"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Verificar que ngrok existe
if [ ! -f "/opt/homebrew/bin/ngrok" ]; then
    echo "❌ ngrok no encontrado en /opt/homebrew/bin/ngrok"
    echo ""
    echo "Instalar ngrok:"
    echo "  brew install ngrok"
    exit 1
fi

echo "✅ ngrok encontrado"
echo ""

# Matar cualquier instancia previa de ngrok
pkill -f ngrok 2>/dev/null
sleep 2

echo "🚀 Iniciando ngrok en puerto 5001..."
echo ""

# Iniciar ngrok
/opt/homebrew/bin/ngrok http 5001 &

sleep 4

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "✅ ngrok iniciado"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📊 Dashboard de ngrok:"
echo "   http://localhost:4040"
echo ""
echo "🔗 Para obtener la URL pública:"
echo ""
echo "   Opción 1: Abrir en navegador"
echo "   $ open http://localhost:4040"
echo ""
echo "   Opción 2: Usar curl"
echo "   $ curl -s http://localhost:4040/api/tunnels | python3 -c \"import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])\""
echo ""
echo "⚠️  IMPORTANTE:"
echo "   1. Copia la URL que empieza con https://xxxxx.ngrok-free.app"
echo "   2. Pega esa URL en signup.html línea 325"
echo "   3. Haz commit y push a GitHub"
echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Presiona Ctrl+C para detener ngrok"
echo ""

# Mantener el script corriendo
wait
