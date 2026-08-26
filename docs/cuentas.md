# Cuentas de usuario reales

## Qué es y por qué (2026-08-24)

Antes de esto, el "perfil" (nombre, altura, peso, dirección, hobbies) vivía solo en el `localStorage` del navegador -- nunca tocaba el servidor. El usuario pidió cuentas reales (Google + email/contraseña) como paso previo a que KOLIZION funcione como e-commerce (el carrito/pago propio todavía no existe, queda para más adelante). Mientras tanto, se usó el punto de "comprar" que ya existía (clic en "Ver producto" / "Visitar tienda") como el lugar donde exigir cuenta.

**Decisión explícita del usuario**: navegar (buscar, ver resultados, chatear con Koko) sigue sin necesitar cuenta -- la cuenta solo se exige en el momento de comprar. Sesión de 30 días (antes eran 12 horas, solo para el panel de admin).

## "Mantener sesión iniciada" (2026-08-24, pedido explícito del usuario)

Al crear la cuenta y al loguearse (formulario normal Y "Continuar con Google"), aparece un checkbox "Mantener la sesión iniciada en este dispositivo" -- controla si `session.permanent` queda en `True` (dura los 30 días configurados) o `False` (cookie de sesión normal, se borra sola al cerrar el navegador del todo). Lógica en `_iniciar_sesion_usuario(usuario, recordar)` (`app.py`).

**En Safari, la sesión NUNCA queda como permanente**, sin importar lo que haya elegido la persona -- pedido explícito ("en Safari siempre debe pedir el inicio de sesión"). `_es_safari(user_agent)` detecta Safari de verdad (excluye Chrome/Firefox/Edge corriendo sobre WebKit en iOS, que también traen "Safari" en el User-Agent). En vez de mostrar un checkbox que en la práctica no se respeta, `/login` y `/registro` directamente NO lo muestran en Safari -- en su lugar aparece un aviso ("En Safari siempre te vamos a pedir iniciar sesión de nuevo cada vez que vuelvas"). `_iniciar_sesion_usuario` igual fuerza `recordar=False` del lado del servidor si detecta Safari, por si alguien manda el campo a mano (nunca confiar solo en que el HTML no lo muestre).

Para el flujo de Google (no pasa por un `<form>` tradicional): el valor del checkbox lo manda `static/auth.js` en el `POST /auth/google/iniciar` inicial, se guarda en `session["recordar_pendiente"]` (sobrevive el viaje a Google y de vuelta, mismo mecanismo que el perfil pendiente de migración) y se consume recién en `/auth/google/callback`.

Probado con `curl` simulando 3 casos (User-Agent de Chrome y de Safari real) mirando el header `Set-Cookie` de la respuesta: Chrome+checkbox marcado trae `Expires` (~30 días); Chrome sin marcar y Safari (aunque se mande `recordar=1` a la fuerza) nunca traen `Expires` -- cookie de sesión normal en los 2 casos.

## Ver las cuentas (`/admin/usuarios`, 2026-08-24)

Panel de solo lectura, protegido con el mismo `@requiere_admin` que ya usan `/admin/tiendas` y `/admin/clics` -- pestaña nueva "Usuarios" agregada al nav que comparten las 3 páginas. Muestra nombre, correo, si entra con Google/contraseña/ambos, fecha de creación, y los datos de perfil que tenga cargados (teléfono, altura, peso, dirección, foto). **Nunca muestra el hash de la contraseña** -- `db_usuarios.listar_usuarios()` ni siquiera lo trae de la base de datos en la consulta.

## Base de datos: primera SQL del proyecto

`data/kolizion.db` (SQLite, gitignorado) -- todo lo demás del proyecto sigue siendo JSON (`data/*.json`), esto no cambia. Una sola tabla, `usuarios`, con el schema y las funciones CRUD en **`db_usuarios.py`** (único módulo separado de `app.py` -- se sacó para no seguir engordando un archivo que ya tenía ~2800 líneas).

Todas las consultas usan `?` como placeholder (nunca f-strings/concatenación) -- así se mantiene cierto que este proyecto no tiene SQL injection (ver `docs/seguridad.md`).

Cuenta puede tener `password_hash` (si se registró con correo), `google_sub` (si usó Google), o ambos si vinculó las dos formas con el mismo correo -- nunca ninguno de los dos (`CHECK` en el schema).

## Login con Google (OAuth) -- sin librerías nuevas

Implementado a mano con `urllib` (stdlib de Python), sin agregar `requests` ni ninguna librería de OAuth -- mismo espíritu que el resto del proyecto ("sin agregar una dependencia nueva solo para esto", ver comentario de `_cargar_env_local` en `app.py`).

**Para que funcione, hace falta configurar en `.env`** (ver plantilla en `.env.example`):
```
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```
Se consiguen en [console.cloud.google.com](https://console.cloud.google.com/): crear proyecto → "OAuth consent screen" (tipo Externo) → "Credentials" → "Create Credentials" → "OAuth client ID" (Aplicación web). En "Authorized redirect URIs" hay que agregar **las 2 URLs**:
- `http://localhost:5000/auth/google/callback` (para probar en la compu de desarrollo)
- `https://tu-dominio-real.com/auth/google/callback` (cuando se compre el dominio -- ver más abajo por qué hace falta)

Si estas 2 variables están vacías, el botón "Continuar con Google" simplemente no aparece -- el registro con correo/contraseña sigue funcionando igual (mismo criterio que `ADMIN_PASSWORD` vacío deshabilitando el panel de admin).

**Por qué hace falta un dominio propio**: Google exige que la URL de vuelta (`redirect_uri`) esté registrada de antemano y sea siempre la misma. El código nunca hardcodea un dominio (usa `url_for(..., _external=True)`), así que apenas se compre el dominio y se agregue esa segunda URL en Google Cloud Console, funciona sin tocar una línea de código.

**Gap conocido, no un defecto**: sin la librería `requests` (que trae `certifi`), algunas instalaciones de Python en Windows pueden no tener el certificado raíz y dar `CERTIFICATE_VERIFY_FAILED` la primera vez que se llama a Google -- es un problema de entorno conocido y solucionable (actualizar certificados de Python), no un error de diseño.

## Los 2 puntos donde se exige cuenta para "comprar"

1. **Catálogo mock** (`data/catalog.json`, tarjetas de `/resultados` y `/vitrina`): el bloqueo es del lado del cliente, en `abrirEnlaceConAnimacion()` (`static/comun.js`) -- si `window.KOLIZION_LOGUEADO` es falso, manda a `/login?siguiente=...` en vez de mostrar la animación y abrir la tienda externa. `window.KOLIZION_LOGUEADO` lo define `templates/_barra_nav.html` (incluido en todas las páginas) a partir de la sesión de Flask.
2. **Tiendas piloto reales** (`data/tiendas.json`, `/ir/<tienda_id>` y `/ir/<tienda_id>/<producto>`): el bloqueo es del lado del servidor, con el decorator `requiere_cuenta` en `app.py` (calco de `requiere_admin`, el mismo patrón que ya usaba el panel de admin) -- necesario porque el botón "Visitar tienda" de `templates/tienda_perfil.html` es un link plano sin JS.

Se mantuvo `target="_blank"` en el botón "Visitar tienda" (se había considerado sacarlo, pero rompía la experiencia para quien YA tiene sesión: sin él, el clic navega la pestaña actual fuera de la app en vez de abrir la tienda en una pestaña nueva). Para quien no tiene sesión, la pestaña nueva simplemente muestra el login -- funciona bien igual, solo que la pestaña nueva no muestra la tienda de inmediato.

## Migración de localStorage a la cuenta

- **Registro con correo/contraseña** (`/registro`): la página no navega a ningún lado, así que el JS (inline en `templates/registro.html`) lee `getPerfil()` al cargar y precarga/incluye los campos que ya existían (nombre, apellido, género, edad, altura, peso, dirección, hobbies) en inputs ocultos, junto con correo/contraseña nuevos.
- **Google** (cruza a `accounts.google.com` y vuelve): el perfil de localStorage se manda primero a `POST /auth/google/iniciar`, que lo guarda temporalmente en la sesión de Flask (sobrevive el viaje de ida y vuelta, misma cookie firmada). En `/auth/google/callback`, **solo si la cuenta es nueva** se usa ese perfil pendiente para completar lo que Google no manda (altura, peso, dirección, hobbies, teléfono) -- si la cuenta ya existía, se descarta para no pisar datos reales. El **email de la cuenta nueva** es el que tenía el perfil pendiente (si había uno), no el de Google -- así hereda los favoritos/historial que ya existían bajo ese correo (ver más abajo).
- Después del callback, `templates/_auth_sincronizar.html` sincroniza el localStorage con los datos reales de la cuenta antes de seguir -- importante si el login fue desde un dispositivo nuevo donde no había nada guardado.

## Relación con el sistema de "email" que ya existía

Antes de las cuentas reales, `perfil.gmail` ya se mandaba al servidor (sin autenticar, cualquiera podía mandar cualquier email) como clave de `data/favoritos.json`, `data/historial_usuarios.json`, `data/limite_koko.json` y `data/chats_koko.json`. **Esto no se tocó** -- sigue funcionando igual para quien navega sin cuenta. La cuenta real, cuando existe, usa el mismo email como identidad -- por eso alguien que se registra con el correo que ya usaba antes de tener cuenta "hereda" sus favoritos/historial previos sin tener que hacer nada especial.

## Foto de perfil

`POST /perfil/foto` (multipart, requiere cuenta). Extensión permitida (`.jpg .jpeg .png .webp`) + tamaño máximo 3MB (`app.config["MAX_CONTENT_LENGTH"]`). El nombre del archivo en disco sale siempre del `usuario_id` autenticado (nunca del nombre que mandó el navegador) -- evita cualquier path traversal sin depender de nada más. Se guarda en `static/img/usuarios/` (gitignorado).

**Gap aceptado, no silencioso**: no se reprocesa la imagen server-side (ej. con Pillow) antes de guardarla -- lo más prolijo sería abrir y volver a guardar la imagen como capa extra de seguridad contra archivos disfrazados de imagen. Se dejó pendiente para una v2 si hace falta (no se agregó Pillow como dependencia nueva solo para esto).

## Verificado de punta a punta (2026-08-24)

- Registro con correo/contraseña migrando un perfil de localStorage con datos reales (nombre, apellido, género, edad, altura, peso, dirección, hobbies) -- confirmado en la fila de la base de datos.
- Login con contraseña correcta e incorrecta (mensaje genérico, no dice si el correo existe).
- Bloqueo del lado del cliente: click en "Ver producto" sin sesión → redirige a `/login?siguiente=...`; con sesión → muestra la animación y abre la tienda.
- Bloqueo del lado del servidor: `/ir/<tienda_id>` sin sesión → redirige a login; con sesión → sigue el flujo normal de la tienda.
- Subida de foto: archivo válido se guarda y se refleja en `/perfil`; archivo con extensión no permitida se rechaza con error 400 (nunca un 500).

Falta probar en este equipo (necesita `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` reales, que todavía no están configurados): el flujo completo de "Continuar con Google", incluida la migración de perfil pendiente y la vinculación con una cuenta ya existente por correo.
