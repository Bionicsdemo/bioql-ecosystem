# 🎯 PASOS FINALES - EmailJS Debug

## ✅ Estado Actual

```
🟢 Servidor:     CORRIENDO (PID 2413)
🟢 Ngrok:        ACTIVO (https://ac510c965a21.ngrok-free.app)
✅ signup.html:  Actualizado con debug detallado
✅ Commits:      Hechos (6424c7c)
⏳ Push:         PENDIENTE
```

---

## 🚀 PASO 1: Push a GitHub

```bash
cd /Users/heinzjungbluth/Desktop/bioql_website
git push origin main
```

Espera ~1 minuto para que Vercel despliegue.

---

## 🧪 PASO 2: Probar con Debug Activado

### Preparación:
1. Ve a: https://www.spectrixrd.com/signup.html
2. **Abre Console del navegador (F12 → Console)**
3. **Mantén la Console abierta**

### Registro:
```
Email:    jgheinz@gmail.com
Tarjeta:  4242 4242 4242 4242
Fecha:    12/34
CVC:      123
ZIP:      12345
```

### Lo que verás en Console:

Si funciona:
```javascript
📧 Attempting to send email via EmailJS...
Service ID: service_vh3hbgr
Template ID: template_5rnk5dp
Email params: {...}
✅ Email sent via EmailJS successfully!
Response: {status: 200, text: "OK"}
```

Si falla:
```javascript
📧 Attempting to send email via EmailJS...
❌ Email sending failed with error:
Error message: [MENSAJE DEL ERROR]
Error status: [CÓDIGO]
```

**También aparecerá un alert() con el error.**

### ⚠️ IMPORTANTE:
**Copia TODO el output de la console relacionado con EmailJS y envíamelo.**

---

## 🔍 PASO 3: Test desde EmailJS Dashboard

Esto confirmará si el template está bien configurado.

### 3.1 Ir al Template:
https://dashboard.emailjs.com/admin/templates/template_5rnk5dp

### 3.2 Click en "Test It" o "Send Test Email"

### 3.3 Completar los valores:
```
to_name: Test User
user_email: jgheinz@gmail.com
api_key: bioql_TEST_KEY_123
user_id: 999
stripe_customer_id: cus_TEST_123
```

### 3.4 Click "Send"

### 3.5 Verificar:
- ¿Llegó el email a jgheinz@gmail.com?
- ¿Apareció algún error?

**Si el test funciona → El problema está en el código del frontend**
**Si el test falla → El problema está en la configuración de EmailJS**

---

## 📋 PASO 4: Verificar Configuración de EmailJS

### 4.1 Verificar Service:
https://dashboard.emailjs.com/admin

1. Click en "Email Services"
2. Busca: `service_vh3hbgr`
3. Estado debe ser: **Connected** (verde)

Si no está conectado:
- Click en el service
- Conecta tu cuenta de Gmail/Outlook
- Autoriza la aplicación

### 4.2 Verificar Límite de Emails:
En el dashboard principal: https://dashboard.emailjs.com/admin

Busca:
```
Emails sent this month: X / 200
```

**Si X está cerca de 200 → Has alcanzado el límite del plan gratuito**

### 4.3 Verificar Template Content:
https://dashboard.emailjs.com/admin/templates/template_5rnk5dp

**IMPORTANTE:** El campo "Content" debe tener HTML completo (no solo texto).

Para verificar:
1. Click en el campo "Content"
2. Debe mostrar código HTML largo con etiquetas `<html>`, `<style>`, `<table>`, etc.

**Si está vacío o tiene solo texto:**

1. Abre el archivo:
   ```bash
   cat /Users/heinzjungbluth/Desktop/bioql_website/EMAIL_TEMPLATE.html
   ```

2. Copia TODO el contenido (desde `<!DOCTYPE html>` hasta `</html>`)

3. Pégalo en el campo "Content" del template

4. Guardar

---

## 🐛 Errores Comunes y Soluciones

### Error: "Template not found"
**Causa:** Template ID incorrecto
**Solución:** Verifica que sea `template_5rnk5dp`

### Error: "Service not found"
**Causa:** Service ID incorrecto
**Solución:** Verifica que sea `service_vh3hbgr`

### Error: "Invalid parameters"
**Causa:** Variables del template no coinciden
**Solución:** Template debe tener: `{{to_name}}`, `{{user_email}}`, `{{api_key}}`, `{{user_id}}`, `{{stripe_customer_id}}`

### Error: "Quota exceeded"
**Causa:** Límite de 200 emails/mes alcanzado
**Solución:** Espera al próximo mes o actualiza a plan de pago

### Error: "Failed to send email"
**Causa:** Content del template vacío o Service no conectado
**Solución:** Verifica el Content y la conexión del Service

### Sin error pero no llega email
**Causa:** Email en spam o Service no autorizado
**Solución:** Revisa spam y verifica que el Service esté autorizado en Gmail/Outlook

---

## 📊 Checklist de Verificación

Marca cada punto:

- [ ] Push a GitHub ejecutado
- [ ] Vercel desplegó (espera 1 min)
- [ ] Registro hecho con Console abierta
- [ ] Output de Console copiado
- [ ] Test desde EmailJS Dashboard ejecutado
- [ ] Service está Connected (verde)
- [ ] Template Content tiene HTML completo
- [ ] No se alcanzó límite de 200 emails/mes

---

## 💬 Qué Enviarme

Después de hacer los pasos anteriores, envíame:

1. **Output completo de la Console** (todo lo relacionado con EmailJS)
2. **Mensaje del alert()** que apareció
3. **Resultado del Test desde Dashboard:** ¿Llegó el email?
4. **Estado del Service:** ¿Connected o no?
5. **Emails enviados este mes:** X / 200
6. **Content del template:** ¿Tiene HTML o está vacío?

Con esa información podré identificar el problema exacto.

---

## 🔄 Solución Alternativa

Si EmailJS no funciona después de todo esto, puedo implementar **envío de emails desde el backend** usando:

- **Python smtplib** (Gmail SMTP)
- **SendGrid API** (gratuito hasta 100 emails/día)
- **AWS SES** (muy económico)

Esto requiere modificar `bioql_auth_server.py` para enviar el email después de crear el usuario.

**Pero primero intentemos identificar el problema de EmailJS.** 🔍

---

## 🎯 Resumen

1. ✅ **Push a GitHub**
2. 🧪 **Probar con Console abierta** → Copiar error
3. 🔍 **Test desde EmailJS Dashboard** → ¿Funciona?
4. 📋 **Verificar configuración** → Service, Content, Límite
5. 💬 **Enviarme los resultados**

**TIEMPO ESTIMADO: 5 minutos**

---

**El servidor está listo, el código de debug está listo. Solo falta hacer push y probar para ver el error exacto.** 🚀
