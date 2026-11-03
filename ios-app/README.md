# KOLIZION para iPhone

Es una app nativa hecha con Capacitor que abre kolizion.cl y le suma login con Google y Apple, notificaciones push, compartir nativo y favoritos sin conexión. El detalle técnico está en `../docs/app_ios.md`.

## Configuración (una sola vez)

1. **Apple Developer Program**: inscríbete en developer.apple.com/programs (USD 99 al año).
2. **App ID**: en developer.apple.com → Certificates, IDs & Profiles → Identifiers → "+" → App IDs → App:
   - Bundle ID (explícito): `cl.kolizion.app`
   - Capabilities: marca **Push Notifications** y **Sign In with Apple**.
3. **Clave de push**: en la misma sección, Keys → "+" → marca **Apple Push Notifications service (APNs)** → descarga el `.p8`. Solo se puede descargar una vez, así que guárdalo bien. En Render → Environment agrega:
   - `APNS_KEY_ID`: el ID de la clave, 10 caracteres.
   - `APNS_TEAM_ID`: arriba a la derecha en developer.apple.com, 10 caracteres.
   - `APNS_KEY_P8`: el contenido completo del `.p8`.
   - `APNS_ENTORNO`: `produccion`.
4. **Google para iOS**: en console.cloud.google.com, en el mismo proyecto del login web, ve a Credentials → Create Credentials → OAuth client ID → tipo **iOS** → Bundle ID `cl.kolizion.app`. Copia el Client ID y agrégalo como `GOOGLE_IOS_CLIENT_ID` en Render y en Codemagic (paso 7).
5. **App Store Connect**: en appstoreconnect.apple.com → Apps → "+" → Nueva app:
   - Plataforma: iOS
   - Nombre: KOLIZION
   - Idioma: Español (México)
   - Bundle ID: `cl.kolizion.app`
   - SKU: `kolizion-ios`
6. **Clave API para Codemagic**: en App Store Connect → Users and Access → Integrations → App Store Connect API → "+" con acceso **App Manager**. Descarga el `.p8` y anota el Issuer ID y el Key ID.
7. **Codemagic**: entra a codemagic.io con tu cuenta de GitHub y agrega el repo `kolizion.cl`.
   - Team settings → Integrations → Developer Portal → agrega la clave del paso 6 con el nombre exacto **KOLIZION App Store Connect**.
   - Team settings → Code signing identities → iOS certificates → genera un certificado de distribución. Después, en iOS provisioning profiles, trae el perfil App Store de `cl.kolizion.app`.
   - En la app → Environment variables → crea el grupo **kolizion_ios** con `GOOGLE_IOS_CLIENT_ID`.

## Publicar una versión

1. En Codemagic, inicia el workflow **KOLIZION iOS -> TestFlight**. También se dispara al crear un tag `ios-v1.0.0`.
2. En unos 15 a 25 minutos la app aparece en TestFlight. Instala la app TestFlight en tu iPhone y pruébala.
3. En App Store Connect completa la ficha, agrega los screenshots, elige la build y presiona **Enviar a revisión**.

Si cambias el icono, los permisos o los plugins, sube `version` en `package.json` antes del build. Los cambios de la web (kolizion.cl) no necesitan una versión nueva de la app.

## Probar en un Mac (opcional)

```
npm install
GOOGLE_IOS_CLIENT_ID=... node scripts/preparar-ios.mjs
npx cap open ios
```
