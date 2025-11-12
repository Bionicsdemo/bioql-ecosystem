# 🚀 QUICK START - Probar Sistema en 5 Minutos

## ✅ Bugs Ya Corregidos
1. ✅ **Stripe valida ANTES de crear usuario** - No más API keys unbillable
2. ✅ **EmailJS con error handling** - Mejor logging y debugging
3. ✅ **Usuario huérfano eliminado** - Base de datos limpia

---

## 📋 Antes de Empezar (HACER UNA VEZ)

### Configurar EmailJS Template
1. Ve a: https://dashboard.emailjs.com/admin/templates/template_5rnk5dp
2. En **"To email"**, pon: `{{user_email}}`
3. Guardar template

---

## 🏃 Iniciar Servidor

```bash
cd /Users/heinzjungbluth/Desktop/Server_bioql

# Si ngrok no está en PATH:
export PATH="/opt/homebrew/bin:$PATH"

# Iniciar
./START_BIOQL_SERVER.sh
```

**Copiar la URL de ngrok que aparece:**
```
Public URL: https://abc123.ngrok-free.app  ← COPIAR ESTA
```

---

## 🔧 Si la URL de ngrok Cambió

```bash
# 1. Editar signup.html línea 325
# 2. Pegar nueva URL de ngrok
# 3. Push a GitHub

cd /Users/heinzjungbluth/Desktop/bioql_website
git add signup.html
git commit -m "Update ngrok URL"
git push origin main
```

---

## 🧪 Probar Registro

1. **Ir a:** https://www.spectrixrd.com/signup.html

2. **Llenar:**
   - Nombre: Tu Nombre
   - Email: tu-email@gmail.com
   - Tarjeta: `4242 4242 4242 4242`
   - Fecha: `12/34`
   - CVC: `123` ← IMPORTANTE
   - ZIP: `12345`

3. **Click:** "Create Account & Get API Key"

---

## ✅ Verificar Éxito

### 1. Console del Navegador (F12)
```javascript
✅ Stripe PaymentMethod created: pm_...
✅ User registered: {user: {...}}
✅ Email sent via EmailJS
```

### 2. Logs del Servidor
```
✅ Stripe customer created: cus_...
✅ Payment method attached
✅ Default payment method set
```

### 3. Stripe Dashboard
https://dashboard.stripe.com/customers
- ✅ Cliente creado
- ✅ Tarjeta adjunta

### 4. Email Recibido
- ✅ Email con API key y diseño quantum

### 5. Base de Datos
```bash
sqlite3 /Users/heinzjungbluth/Desktop/Server_bioql/auth_server/users.db \
  "SELECT * FROM users ORDER BY id DESC LIMIT 1;"
```

---

## ❌ Si Algo Falla

### Error: "Payment validation failed"
→ Verifica tarjeta: `4242 4242 4242 4242`, CVC: `123`

### Error: "Email sending failed"
→ Configurar EmailJS template con `{{user_email}}`

### Error: "ngrok not found"
→ `export PATH="/opt/homebrew/bin:$PATH"`

---

## 📁 Archivos de Referencia

- 📖 [BUGS_CORREGIDOS_Y_TESTING.md](BUGS_CORREGIDOS_Y_TESTING.md) - Guía completa
- 📖 [RESUMEN_SISTEMA_BIOQL.txt](RESUMEN_SISTEMA_BIOQL.txt) - Arquitectura
- 📖 [EJECUTAR_SERVIDOR.md](EJECUTAR_SERVIDOR.md) - Instrucciones servidor

---

## 🎯 Checklist Rápido

- [ ] EmailJS template configurado con `{{user_email}}`
- [ ] Servidor corriendo
- [ ] ngrok URL copiada (si cambió)
- [ ] signup.html actualizado (si ngrok cambió)
- [ ] Probado con tarjeta 4242..., CVC 123
- [ ] Usuario en base de datos
- [ ] Cliente en Stripe
- [ ] Email recibido

**¡Listo para probar!** 🚀
