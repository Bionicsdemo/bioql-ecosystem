# 🔍 DEBUG: EmailJS No Envía Correos

## ✅ Lo Que Ya Verificamos

1. ✅ Template configurado con `{{user_email}}` en "To Email"
2. ✅ Variables del código coinciden con el template
3. ✅ Service ID: `service_vh3hbgr`
4. ✅ Template ID: `template_5rnk5dp`
5. ✅ Public Key: `Uoq5AonGyDGvl5kvE`

## 🔧 Nueva Versión con Debug Detallado

Acabo de actualizar `signup.html` con logging muy detallado. Cuando hagas el próximo registro, verás en la **Console (F12)**:

```javascript
📧 Attempting to send email via EmailJS...
Service ID: service_vh3hbgr
Template ID: template_5rnk5dp
Email params: {to_name: "...", user_email: "...", ...}
```

Y luego:
- ✅ `Email sent via EmailJS successfully!` + Response details
- O ❌ `Email sending failed with error:` + Error completo

**IMPORTANTE:** También aparecerá un `alert()` con el error exacto si falla.

---

## 🧪 PASO 1: Push y Probar de Nuevo

```bash
cd /Users/heinzjungbluth/Desktop/bioql_website
git push origin main
```

Espera ~1 minuto para que Vercel despliegue.

Luego ve a: https://www.spectrixrd.com/signup.html

**ANTES de hacer submit:**
1. Abre Console (F12 → Console)
2. Deja la console abierta
3. Haz el registro con:
   - Tarjeta: 4242 4242 4242 4242
   - CVC: 123

**COPIA TODO lo que aparezca en la console** relacionado con EmailJS y envíamelo.

---

## 🔍 PASO 2: Verificar Template en EmailJS Dashboard

### Ir a Template Settings
https://dashboard.emailjs.com/admin/templates/template_5rnk5dp

### Verificar estas configuraciones:

#### 1. "To Email" (ya lo verificaste)
```
{{user_email}}
```
✅ Correcto

#### 2. "From Name"
Debe ser algo como:
```
BioQL Team
```
o
```
Spectrix RD team
```

#### 3. "From Email"
Debe ser:
```
Use Default Email Address  [✓ checked]
```

O si tienes un dominio verificado:
```
noreply@spectrixrd.com
```

#### 4. "Reply To"
Debe estar **vacío** o tener:
```
{{user_email}}
```

⚠️ **IMPORTANTE:** Si pones `{{user_email}}` en "Reply To", el usuario recibirá respuestas a su propio email.

#### 5. "Subject"
Debe ser algo como:
```
Your BioQL API Key - Welcome!
```
o
```
Your Api Key!
```

#### 6. "Content" (Cuerpo del Email)
Debe tener el HTML completo del archivo EMAIL_TEMPLATE.html.

**Para verificar:**
1. Haz click en el campo "Content"
2. Verifica que tenga código HTML con:
   - `{{to_name}}`
   - `{{api_key}}`
   - `{{user_id}}`
   - `{{stripe_customer_id}}`

---

## 🚨 POSIBLES PROBLEMAS

### Problema #1: Límite de Emails Alcanzado (Free Tier)

EmailJS Free tier permite:
- **200 emails/mes**
- **2 templates**

Si ya enviaste muchos emails de prueba, podrías haber alcanzado el límite.

**Verificar:**
https://dashboard.emailjs.com/admin

En el dashboard principal, verás:
```
Emails sent this month: X / 200
```

Si está cerca de 200, ese es el problema.

**Solución:**
- Espera hasta el próximo mes
- O actualiza a plan de pago

---

### Problema #2: Template Content Vacío o Incorrecto

Si el campo "Content" del template está vacío o no tiene el HTML correcto, el email puede fallar silenciosamente.

**Verificar:**
1. Ve a: https://dashboard.emailjs.com/admin/templates/template_5rnk5dp
2. Haz click en "Content"
3. Verifica que tenga HTML completo (no solo texto)

**Si está vacío, debes pegar el contenido de:**
`/Users/heinzjungbluth/Desktop/bioql_website/EMAIL_TEMPLATE.html`

---

### Problema #3: Service No Configurado Correctamente

**Verificar Service:**
https://dashboard.emailjs.com/admin

1. Haz click en "Email Services"
2. Verifica que `service_vh3hbgr` esté listado
3. Verifica que el estado sea: **Connected** (verde)

Si no está conectado:
1. Haz click en el service
2. Sigue las instrucciones para conectar (Gmail, Outlook, etc.)

---

### Problema #4: Template Variables No Coinciden

El template debe tener **exactamente** estas variables:

```html
{{to_name}}          <!-- Nombre del usuario -->
{{user_email}}       <!-- Email del usuario -->
{{api_key}}          <!-- API key generado -->
{{user_id}}          <!-- ID del usuario -->
{{stripe_customer_id}} <!-- Stripe customer ID -->
```

Si el template tiene variables diferentes (ej: `{{name}}` en vez de `{{to_name}}`), el email fallará.

---

## 🔧 PASO 3: Verificar Content del Template

### Copiar Contenido del Template Correcto

1. Lee el archivo:
   ```bash
   cat /Users/heinzjungbluth/Desktop/bioql_website/EMAIL_TEMPLATE.html
   ```

2. Copia TODO el contenido (desde `<!DOCTYPE html>` hasta `</html>`)

3. Ve a: https://dashboard.emailjs.com/admin/templates/template_5rnk5dp

4. Pega el contenido en el campo "Content"

5. Guardar template

---

## 🧪 PASO 4: Probar con Test de EmailJS

EmailJS tiene una función de TEST que te permite enviar un email de prueba SIN necesidad de hacer registro.

### Test desde Dashboard:

1. Ve a: https://dashboard.emailjs.com/admin/templates/template_5rnk5dp

2. Haz click en "Test It" o "Send Test Email"

3. Completa los valores de prueba:
   ```
   to_name: Test User
   user_email: jgheinz@gmail.com
   api_key: bioql_TEST123
   user_id: 999
   stripe_customer_id: cus_TEST123
   ```

4. Haz click en "Send"

5. Verifica si llega el email a jgheinz@gmail.com

**Si el test funciona:**
→ El problema está en el frontend (signup.html)

**Si el test NO funciona:**
→ El problema está en la configuración de EmailJS

---

## 📊 Checklist de Verificación

Verifica estos puntos en EmailJS Dashboard:

- [ ] Template ID correcto: `template_5rnk5dp`
- [ ] Service ID correcto: `service_vh3hbgr`
- [ ] Service conectado y activo (verde)
- [ ] "To Email" = `{{user_email}}`
- [ ] "Subject" configurado
- [ ] "Content" tiene HTML completo con todas las variables
- [ ] No has alcanzado el límite de 200 emails/mes
- [ ] Test desde dashboard funciona

---

## 🎯 Próximos Pasos

1. **Push a GitHub:**
   ```bash
   cd /Users/heinzjungbluth/Desktop/bioql_website
   git push origin main
   ```

2. **Espera 1 minuto** para Vercel deploy

3. **Haz un nuevo registro** con Console (F12) abierta

4. **Copia el error exacto** que aparece en Console y alert()

5. **Haz un test** desde EmailJS Dashboard

6. **Envíame los resultados:**
   - Qué dice la Console
   - Si el test de EmailJS funciona
   - Cuántos emails has enviado este mes

Con esa información podré identificar el problema exacto. 🔍

---

## 💡 Solución Alternativa: Backend Email

Si EmailJS sigue sin funcionar, puedo modificar el backend para que envíe emails usando:

1. **Python smtplib** (Gmail SMTP)
2. **SendGrid API**
3. **AWS SES**

Esto requeriría:
- Configurar credenciales de SMTP
- Modificar `bioql_auth_server.py`
- Enviar email desde el backend en vez del frontend

Pero primero intenta el debug de EmailJS para ver el error exacto.

---

**RESUMEN:** Haz push, prueba de nuevo con Console abierta, y envíame el error exacto que aparece. También haz el test desde EmailJS Dashboard para confirmar si el template funciona. 🚀
