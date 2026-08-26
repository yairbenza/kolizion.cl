# Proyecto

**KOLIZION** — app/simulador que recomienda ropa streetwear (según altura, peso, ocasión y presupuesto) de tiendas chilenas chicas, cruzando con un catálogo real. Objetivo: dar visibilidad a tiendas pequeñas y ayudar al comprador a encontrar la prenda indicada. (Nombre viejo, desactualizado si aparece en algún lado: "KLLE-0".)

## Fuera de alcance

No reincorporar sin pedido explícito del usuario:
- Ocasiones no-streetwear (matrimonio, oficina, entrevista de trabajo, playa, deporte, primera cita).
- Zapatillas/calzado. Foco actual: solo prendas de ropa.

## Reglas de trabajo (siempre vigentes)

1. **El usuario no sabe programar.** Antes de cambios importantes, explicar en español simple qué se va a hacer y para qué sirve.
2. **Nunca inventar productos, links, o datos de tienda** (corte/capucha/material/etc.) que no vengan de la ficha real — si la ficha no da señal clara, marcar explícitamente como no definido/no especificado y preguntar al usuario, no adivinar.
3. **`data/catalog.json` nunca se edita a mano** — es generado por `construir_catalogo_real.py`. Cualquier cambio de tagueo va en los diccionarios de ese script, y después hay que volver a correrlo (no se corre solo). Ver `docs/catalogo_real.md`.
4. Cuando no hay consenso claro en una categoría, mostrar 2-3 opciones en vez de una sola recomendación.
5. PowerShell en este equipo tiene un límite de ~965 bytes por comando — para probar varios casos a la vez, guardarlos en un script (`.py`/`.ps1`) y correrlo, no escribir pruebas largas directo en la terminal.
6. **Documentación detallada vive en `docs/`** (ver índice abajo) — este archivo solo tiene lo esencial. Leer el doc relevante antes de tocar esa área en vez de asumir de memoria.
7. **Cada vez que se agregue una tienda nueva al catálogo**, entrar a su sitio real y buscar su política de envío (despacho a RM, despacho a regiones, retiro en tienda física) y guardarla en `data/envios_tiendas.json`, con la misma estructura que las tiendas ya cargadas ahí. Si el sitio no especifica algo claramente, anotarlo como "no especificado" en vez de asumir o inventar un plazo.
8. **Estructura modular del backend (optimización de tokens):**
   - `app.py`: Servidor Flask principal, blueprints y orquestación de endpoints.
   - `motor_recomendacion.py`: Lógica de filtros de ropa, ocasiones, cortes, tallas, gramajes y Plan B.
   - `servicio_koko.py`: Prompts, límites diarios, llamadas a Anthropic y validaciones de Koko.
   - `servicio_tiendas.py`: Gestión de tiendas, tracking de clics, favoritos, reportes y estimación de envíos.
   - `rutas_auth.py`: Blueprint de autenticación (registro, login, Google OAuth, fotos de perfil).
   - `rutas_admin.py`: Blueprint del panel de administración (`/admin/*`, tiendas, clics, usuarios).
   - `constantes.py`: Constantes, paths, diccionarios de prendas y utilidades de normalización/saneo.
   - `db_usuarios.py`: Base de datos SQLite (`kolizion.db`) y funciones CRUD de usuarios.

## Índice de documentación (`docs/`)

Cada archivo trae el detalle completo con fechas y el porqué de cada decisión — leer el que aplique antes de trabajar en esa parte, no hace falta cargarlos todos de entrada:

- **`docs/buscador.md`** — motor de recomendación: reglas de ocasión validadas, filtros del formulario, criterios de tagueo (corte/talla/manga/capucha/cierre/gorro), material y "marca de autor", Plan B ("mostrar más opciones"), hobbies del perfil.
- **`docs/catalogo_real.md`** — cómo se construyó el catálogo real (`construir_catalogo_real.py`), las 8 tiendas piloto, estado actual del tagueo, imágenes ilustrativas.
- **`docs/koko.md`** — asistente de chat con IA (API Anthropic): prompt, tool calling, detección de prenda/corte/capucha, bugs encontrados y corregidos, límite diario de mensajes.
- **`docs/marca.md`** — identidad visual: paleta, tipografía, splash de apertura, animaciones de marca, textos de bienvenida.
- **`docs/tiendas_admin.md`** — tiendas reales con convenio, tracking de clics/descuentos, panel `/admin`, estimación de envío.
- **`docs/ui_features.md`** — barra de navegación, onboarding, favoritos, PWA, vista previa rápida de producto.
- **`docs/seguridad.md`** — revisiones de seguridad y de producción ya hechas (qué se revisó y qué se corrigió).
- **`docs/cuentas.md`** — cuentas de usuario reales (Google OAuth + email/contraseña): schema de la base de datos, migración desde localStorage, los 2 puntos donde se exige cuenta para comprar.
