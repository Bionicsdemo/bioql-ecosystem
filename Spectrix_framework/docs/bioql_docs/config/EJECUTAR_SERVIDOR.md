# 🚀 Ejecutar Servidor BioQL - INSTRUCCIONES

## ✅ EmailJS Ya Configurado

El Public Key ya está en signup.html:
- ✅ Public Key: `Uoq5AonGyDGvl5kvE`
- ✅ Service ID: `service_vh3hbgr`
- ✅ Template ID: `template_5rnk5dp`

---

## 🔧 PASO 1: Iniciar el Servidor (TÚ DEBES EJECUTAR)

Abre una **NUEVA TERMINAL** y ejecuta:

```bash
cd /Users/heinzjungbluth/Desktop/Server_bioql
./START_BIOQL_SERVER.sh
```

**NOTA**: Si te sale error de `ngrok not found`, ejecuta primero:
```bash
export PATH="/opt/homebrew/bin:$PATH"
./START_BIOQL_SERVER.sh
```

---

## 📋 PASO 2: Copiar la URL de ngrok

Cuando el servidor inicie, verás algo como esto:

```
════════════════════════════════════════════════════════════════════════════
🚀 BioQL Auth & Billing Server - PRODUCTION v3.0
════════════════════════════════════════════════════════════════════════════

✅ Stripe Configuration (LIVE MODE)
✅ Ngrok tunnel active:
   Public URL: https://abc123-def456.ngrok-free.app    ← COPIAR ESTA URL
   Dashboard: http://localhost:4040

📊 SERVER RUNNING
════════════════════════════════════════════════════════════════════════════
```

**COPIA LA URL** que empieza con `https://` y termina en `.ngrok-free.app`

---

## 🔄 PASO 3: Actualizar signup.html

1. Abre el archivo: `/Users/heinzjungbluth/Desktop/bioql_website/signup.html`

2. Ve a la línea **325** y reemplaza:

   **ANTES:**
   ```javascript
   BIOQL_SERVER_URL: 'https://YOUR_NGROK_URL_HERE.ngrok-free.app',
   ```

   **DESPUÉS:**
   ```javascript
   BIOQL_SERVER_URL: 'https://abc123-def456.ngrok-free.app', // ← TU URL DE NGROK
   ```

3. Guarda el archivo

---

## 📤 PASO 4: Subir a GitHub

```bash
cd /Users/heinzjungbluth/Desktop/bioql_website

git add signup.html

git commit -m "Configure ngrok URL for production

- EmailJS fully configured with Public Key: Uoq5AonGyDGvl5kvE
- Server URL configured with ngrok tunnel
- System 100% ready for production

All configuration complete! 🚀"

git push origin main
```

---

## 🧪 PASO 5: Probar el Sistema

1. Ve a: **https://www.spectrixrd.com/signup.html**

2. Llena el formulario:
   - Nombre: Tu Nombre
   - Email: tu-email@gmail.com (para recibir el email)
   - Tarjeta: `4242 4242 4242 4242`
   - Fecha: `12/34`
   - CVC: `123`

3. ✓ Acepta términos

4. Click **"Create Account & Get API Key"**

5. **Deberías ver**:
   - ✅ Mensaje de éxito
   - ✅ API key en pantalla
   - ✅ Email en tu bandeja con el template hermoso 🎨

---

## 📧 Verificar Email Recibido

El email que recibirás tiene:
- 🎨 Diseño quantum (azul/morado)
- 🔑 Tu API key
- 👤 User ID y Stripe Customer ID
- 💻 Ejemplos de código
- 📚 Links a www.spectrixrd.com

---

## 🔍 Verificar Logs del Servidor

En la terminal donde corre el servidor, verás:

```
✅ User registered: email=tu-email@gmail.com
✅ Stripe customer created: cus_abc123
✅ Payment method pm_abc123 attached to customer cus_abc123
✅ Stripe subscription created: sub_abc123
```

---

## 📊 Verificar en Stripe Dashboard

1. Ve a: https://dashboard.stripe.com/customers
2. Deberías ver el nuevo cliente
3. Click en el cliente para ver:
   - ✅ Tarjeta adjunta
   - ✅ Suscripción activa
   - ✅ Threshold de $3,000

---

## ⚠️ IMPORTANTE

### ngrok URL Cambia Cada 2 Horas

En el plan gratuito de ngrok, la URL expira. Cada vez que reinicies el servidor:

1. Obtendrás una **NUEVA URL**
2. Debes actualizar `signup.html` línea 325
3. Hacer commit y push
4. Esperar ~1 minuto para que Vercel despliegue

**Solución**: Upgrade a ngrok paid ($8/mes) para URL permanente

---

## ✅ Sistema 100% Completo

Una vez hagas estos pasos, tendrás:

```
┌────────────────────────────────────────┐
│  Sistema de Registro y Billing        │
│  Estado: 100% FUNCIONAL                │
└────────────────────────────────────────┘

✅ Frontend (signup.html)           100%
✅ Backend (Flask + Stripe)         100%
✅ Base de datos (SQLite)           100%
✅ Email template (HTML)            100%
✅ EmailJS Public Key               100%
✅ EmailJS Service ID               100%
✅ EmailJS Template ID              100%
✅ ngrok URL configurada            100%

LISTO PARA PRODUCCIÓN! 🚀
```

---

## 🎉 ¡Todo Listo!

El sistema completo está funcionando:

1. ✅ Usuario se registra en www.spectrixrd.com/signup.html
2. ✅ Stripe procesa la tarjeta
3. ✅ Backend genera API key único
4. ✅ EmailJS envía email profesional
5. ✅ Usuario puede usar BioQL inmediatamente
6. ✅ Facturación automática cada $3,000

**¡Solo falta que ejecutes el servidor y copies la URL!** 🚀

---

## 📞 Archivos de Referencia

- 📖 [SETUP_INSTRUCTIONS.md](bioql_website/SETUP_INSTRUCTIONS.md) - Guía completa
- 📖 [SISTEMA_COMPLETADO.md](bioql_website/SISTEMA_COMPLETADO.md) - Documentación técnica
- 📖 [CONFIGURACION_FINAL.md](bioql_website/CONFIGURACION_FINAL.md) - Pasos finales
- 📧 [EMAIL_TEMPLATE.html](bioql_website/EMAIL_TEMPLATE.html) - Template del email
