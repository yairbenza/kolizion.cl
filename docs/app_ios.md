# App de iOS (App Store)

## Qué es y por qué (2026-11-03)

La app de iPhone es una "ventana" nativa hecha con **Capacitor** (`ios-app/`) que abre `https://kolizion.cl`. Todo lo que cambia en la web aparece en la app al tiro, sin mandar una versión nueva a Apple. Solo hay que publicar una versión nueva si cambia algo de `ios-app/` (plugins, icono, permisos).

Apple rechaza las apps que son solo un sitio web envuelto (guía 4.2), así que la app suma 4 cosas nativas, todas en `static/nativo.js` (se carga solo dentro de la app):

1. **Login nativo con Google y Apple.** Google bloquea su login web dentro de apps (`disallowed_useragent`). En la app el teléfono entrega un `id_token` firmado y el servidor lo verifica con las claves públicas de Google/Apple (`/auth/nativo/google`, `/auth/nativo/apple` en `rutas_auth.py`). Apple **exige** "Iniciar sesión con Apple" si la app ofrece Google (guía 4.8).
2. **Notificaciones push.** Los tokens se guardan en la tabla `dispositivos_push` (`db_usuarios.py`) y se envían desde `/admin/push` (`rutas_push.py` + `servicio_push.py`, que habla con APNs por HTTP/2).
3. **Compartir nativo.** Hay un botón "Compartir" en la ficha de producto (`compartirProducto()` en `comun.js`). En la web usa `navigator.share` o copia el link.
4. **Favoritos sin conexión.** `nativo.js` copia los favoritos y una foto chica de cada uno al teléfono. Si no hay internet, la app muestra `ios-app/www/offline.html` con esa copia y vuelve sola cuando regresa la señal.

Además, en la app:
- Los links a tiendas se abren en un navegador interno, y los de Instagram, WhatsApp y TikTok en sus apps.
- La barra de estado cambia de color según el modo claro u oscuro.

## Cómo sabe el servidor que la visita viene de la app

Capacitor agrega `KolizionApp/1.0` al User-Agent (`ios-app/capacitor.config.json`). `_es_app_ios()` (`constantes.py`) lo detecta y el context processor de `app.py` expone `es_app` a todos los templates. Con `es_app`:
- `_pwa_meta.html` agrega `viewport-fit=cover`, espacio para la "isla"/barra de estado y carga `nativo.js`.
- `login.html` y `registro.html` muestran "Continuar con Apple".
- "Continuar con Google" solo aparece si `GOOGLE_IOS_CLIENT_ID` está configurado.

## Cosas obligatorias de Apple que se agregaron a la web

- **Eliminar cuenta desde la app** (guía 5.1.1(v)) está en "Mi cuenta → Eliminar mi cuenta" (`_barra_cuenta.html`, `POST /cuenta/eliminar`). Hay que escribir ELIMINAR para confirmar. Borra la cuenta, los subperfiles, los dispositivos push, los favoritos, el historial, los chats de Koko y la foto. `data/limite_koko.json` NO se borra a propósito, porque si no, borrar la cuenta serviría para saltarse el tope diario de Koko; esas fechas se limpian solas a las 48 h.
- **Política de privacidad**: `/privacidad`. **Soporte**: `/soporte`. Si cambia qué datos se guardan o con quién se comparten, hay que actualizar `/privacidad` y también las respuestas de "Privacidad de la app" en App Store Connect.

## Base de datos

- Columna nueva `usuarios.apple_sub`. El CHECK viejo (`password_hash OR google_sub`) no dejaba crear cuentas que solo entran con Apple. Como SQLite no permite cambiar un CHECK, `_migrar_apple_sub()` copia la tabla a una nueva con el schema actual. Corre una sola vez al arrancar, conserva los mismos ids y filas, y se probó con una base de datos del schema viejo.
- Tabla nueva `dispositivos_push` (token, plataforma, usuario_id opcional).

## Variables de entorno nuevas (Render)

Ver `.env.example`: `GOOGLE_IOS_CLIENT_ID`, `APPLE_BUNDLE_ID`, `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_KEY_P8`, `APNS_ENTORNO`. Dependencias nuevas en `requirements.txt`: `PyJWT[crypto]` (verificar tokens y firmar el JWT de APNs) y `httpx[http2]` (APNs solo acepta HTTP/2).

## Build sin Mac (Codemagic)

La carpeta `ios-app/ios/` no se sube a git. En cada build, `codemagic.yaml` (en la raíz) corre `npm install` y `node scripts/preparar-ios.mjs`. Ese script hace `cap add ios`/`cap sync` y deja configurado:
- Permisos de ubicación, cámara y fotos con sus textos.
- Push y Sign in with Apple (entitlements).
- Solo iPhone, en vertical.
- Icono y splash (`ios-app/assets/`).
- El esquema de URL de Google.
- El AppDelegate que entrega el token de push.

Después Codemagic firma la app y la sube a TestFlight. Se dispara a mano desde Codemagic o con un tag `ios-v*`.

## Pendiente / no probado aquí

- La compilación de iOS no se pudo correr en el entorno donde se hizo esto (sin Mac ni acceso a npm). Lo que sí se probó: el backend completo con tests (migración, login Google/Apple con tokens firmados, push con APNs simulado, eliminar cuenta, páginas en modo app y web) y el script `preparar-ios.mjs` sobre un proyecto de Xcode de prueba. El primer build en Codemagic es la prueba real.
- Al eliminar una cuenta de Apple, Apple recomienda revocar el token con su API (`/auth/revoke`). No está implementado porque necesita guardar el `authorization_code` y una clave extra. Hoy se borra todo lo nuestro, y la persona puede quitar KOLIZION en Ajustes → Apple ID.
