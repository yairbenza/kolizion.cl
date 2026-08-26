# Catalogo real

## Tanda 2 de upgrade a fotos/descripcion/stock real (2026-08-25)

Continuacion del piloto del 2026-08-24 (Novorich/Shatters/Stuffies Concept + Oversaints/Roots South). El dueño pidio extender el mismo tratamiento real a todo el catalogo restante; esta tanda cubrio las 6 tiendas chicas restantes que resultaron ser Shopify: **OVA Chile (20/20), Rotten (19/19), Simpl. (17/17), ForceBlack (22/22), Floating (17/17)** -- 100% de sus productos quedaron con fotos completas + descripcion real + `tallas_disponibles` real (disponible/agotado por talla, nunca cantidad exacta, mismo limite ya documentado). **AbsolutelyWrong quedo en 21/23** (ver caso dudoso abajo).

**Reutilizado sin cambios:** `cargar_shopify_cache()`/`datos_shopify_por_handle()` y el cruce por handle en `main()` (via `DATOS_SHOPIFY_UPGRADE`) ya eran genericos desde el piloto -- solo hizo falta bajar el `products.json` real de cada tienda nueva a `data/shopify_cache/` y agregar la tienda al dict, sin tocar `construir_producto()` ni el loop principal.

**Bug real encontrado y corregido en `_handle_de_path()`:** algunos links hardcodeados de tiendas (ej. AbsolutelyWrong, para diferenciar color de un mismo producto) traen `?variant=12345` al final de la URL -- la funcion vieja devolvia el handle con el query string pegado (`"producto?variant=123"`), que nunca hacia match contra el handle real de Shopify. Corregido para cortar todo desde el primer `?` antes de sacar el ultimo segmento del path. Esto afecta a CUALQUIER tienda con links `?variant=`, no solo AbsolutelyWrong -- ya corregido de forma general.

**Caso dudoso -- AbsolutelyWrong, 2 productos con link roto (no arreglado, queda para el dueño):** "PANTALON BASICO HEAVYWEIGHT (ROSADO)" y "(CAFE)" apuntan a `/products/pantalon-basico-heavyweight-1`, que hoy da **404 real** en el sitio de la tienda (confirmado con curl). El handle actual y vigente en la tienda es `pantalon-basico-heavyweight` (sin el "-1"), pero ese ya corresponde a OTRO producto real ("[PREVENTA] PANTALÓN BÁSICO HEAVYWEIGHT", con sus propios colores Negro/Gris/Azul Marino/Burdeo/Rosado) -- no se puede asumir que sean el mismo producto solo porque el nombre se parece, así que se dejaron las 2 fichas viejas sin tocar (siguen con su descripcion/imagen antigua, no con datos reales) en vez de adivinar. Revisar con el dueño si esas 2 variantes (Rosado/Café) siguen existiendo bajo el nuevo producto o si la tienda las discontinuo.

**Corte/subtipo/categoria:** sin cambios en esta tanda para las 6 tiendas -- ya estaban verificados a mano de antes, solo se agrego la capa de fotos/descripcion/stock real encima.

**Verificado:** `data/catalog.json` regenerado (658 productos, mismo total que antes -- no se agregaron productos nuevos, solo se enriquecieron los existentes), JSON valido, `probar_buscador_real.py` corrido sin errores.


## Piloto de catalogo "listo para vender" -- fotos/descripcion/stock reales (2026-08-24)

El usuario ya tiene consentimiento de las tiendas para usar un crawler y quiere pasar de "vista previa (ejemplo)" a fichas de producto reales, listas para el flujo de compra que Daniel esta construyendo aparte: fotos completas (no solo 3 de referencia), descripcion completa tal como la tiene la tienda (no resumida), y stock real por talla (no el generico "disponible/agotado"). Decision del usuario: por ahora "stock real" = disponible/agotado real por talla (Shopify publico NUNCA expone una cantidad exacta, solo `available: true/false` por variante -- confirmado con un `curl` real a `novorich.cl/products.json` antes de este trabajo; una cantidad exacta requeriria que cada tienda de acceso a su sistema de inventario, no solo permiso de crawler). Empezar con un piloto chico antes de tocar las 622 fichas restantes.

**Mecanismo nuevo en `construir_catalogo_real.py`:** `construir_producto()` ahora acepta 3 parametros opcionales -- `fotos` (lista de URLs reales), `descripcion_real` (texto plano) y `tallas_reales` (lista de tallas con stock real hoy). Si vienen, reemplazan la imagen ilustrativa/descripcion generica/rango tipico de tienda de siempre; si no vienen, comportamiento identico al de antes (las tiendas no tocadas en este piloto siguen igual). `cargar_shopify_cache()` lee un `products.json` de Shopify ya cacheado en disco (`data/shopify_cache/*.json`, bajado con `curl` real) y arma esos 3 campos automaticamente -- la categoria/subtipo/corte siguen sin tocarse por ahi, eso lo sigue haciendo `clasificar_prenda()`/`detectar_corte()`/`VERIFICADO_A_MANO` como siempre (nunca se infiere corte solo por tener datos de Shopify).

**3 tiendas nuevas cargadas 100% con datos reales** (nombre, precio, TODAS las fotos, descripcion completa y stock real por talla vienen directo de `products.json`, no transcritas a mano):

| Tienda | Productos cargados | Notas |
| --- | --- | --- |
| Novorich (www.novorich.cl) | 21 | Ver exclusiones abajo. **Hallazgo real importante: las 21 fichas cargadas muestran 0 tallas disponibles hoy** (agotado en las 4 tallas de cada una) -- no es un error de carga, es el estado real del sitio al 2026-08-24 (el propio sitio aclara que la confeccion toma 5-7 dias habiles, sugiere que trabajan sobre pedido/preventa). |
| Shatters (shatters.cl) | 8 | Poleron/hoodie simples, todos con descripcion generica identica ("Urban, comfortable, and made to stand out...") -- es la descripcion real de la tienda, se cargo tal cual aunque sea corta y repetida. 4 de las 8 muestran talla disponible hoy (S/M/L/XL), 4 sin stock. |
| Stuffies Concept (stuffiesconcept.com) | 2 | Ver exclusion del gorro con visera abajo. Los 2 hoodies "DICE HOODIE Third Edition" (Black/Blue Navy) tienen solo 1 talla M disponible cada uno hoy. |

**Exclusiones (no cargadas, con motivo):**
- **Novorich -- 3 duplicados del mismo hoodie** ("HODDIE - LUXURY WHITE" con handles `hoddie-luxury-white`, `-copia`, `-copia-1`, mismo precio/variantes): se comparo por foto y son el mismo producto repetido por error de carga de la propia tienda (confirmado: el handle mas antiguo, `hoddie-novvm-luxury`, tiene las 6 fotos que resultan de sumar las de los 3 duplicados). Se dejo solo `hoddie-novvm-luxury`.
- **Novorich -- Skullcap ($13.592):** gorro sin visera, pero la ficha real solo dice "tejido suave" sin confirmar material -- no se cargo para no inventar el dato (la app fuerza `material: "lana"` para cualquier gorro forma "lana", que aca seria una invencion). **Pendiente de confirmar con el usuario** si quiere que se cargue igual con material sin especificar.
- **Novorich -- 5 "TRACKSUIT"**: ver seccion "Categoria nueva 'conjunto'" mas abajo -- el usuario aprobo agregar la categoria y ya estan cargados, dejaron de estar excluidos.
- **Stuffies Concept -- "Three Stars Trucker Hat"** (2 variantes de color): gorro CON visera, mismo motivo que "Tag Camo Cap" de Floating (ver casos dudosos de mas abajo) -- el flujo de gorro de la app solo maneja curvo/plano/lana.

**2 tiendas YA cargadas, actualizadas a fotos/descripcion/stock reales** (elegidas por ser las 2 mas chicas de las 14 que ademas resultaron ser Shopify -- para minimizar el trabajo del piloto; corte/categoria/subtipo NO se tocaron, siguen siendo los ya verificados antes):

| Tienda | Productos actualizados | Notas |
| --- | --- | --- |
| Oversaints | 9/9 | Cruzados por handle contra `products.json` real. 4 de 9 muestran talla disponible hoy, 5 sin stock. |
| Roots South | 15/15 | Cruzados por handle. **Las 15 fichas muestran 0 tallas disponibles hoy** (mismo patron que Novorich -- otro hallazgo real, no un error). |

El precio de estas 2 tiendas NO se re-verifico contra el sitio actual en este pase (solo se actualizo foto/descripcion/stock) -- si con el tiempo el precio real cambio, queda pendiente para una proxima pasada.

**Frontend actualizado para mostrar fotos reales cuando existen** (`static/comun.js`, `static/vitrina.js`):
- `imagenesPreview()` (vista previa rapida) usa el set completo de `rec.fotos` cuando el producto lo tiene, en vez del truco de espejar/recortar el dibujo ilustrativo.
- La miniatura de la tarjeta (`rec.imagen`) ya queda como la primera foto real para estos productos -- como no empieza con `/static/img/`, `esImagenIlustrativa()` detecta solo que es real y el aviso "Imagen ilustrativa de referencia" deja de aparecer automaticamente (no hizo falta tocar esa funcion).
- El boton de link ahora dice **"Ver producto"** para fichas reales y sigue diciendo **"Ver producto (ejemplo)"** para las que todavia tienen imagen ilustrativa -- el catalogo va a tener una mezcla de ambas mientras se sigue completando el resto, asi que el texto es condicional por producto, no un cambio global.

**Politica de envio agregada** (`data/envios_tiendas.json`, regla 7 de `CLAUDE.md`): Novorich, Shatters y Stuffies Concept revisadas a mano -- ninguna publica plazo separado por RM/regiones ni retiro en tienda. Novorich no tiene pagina de politica de envio (404) pero si aclara que la CONFECCION toma 5-7 dias habiles antes de despachar (produccion sobre pedido). Shatters da un plazo general de 2-9 dias habiles sin separar por zona. Stuffies Concept tiene un banner "2-3 dias habiles" que contradice su propia politica ("varia segun la region", sin numero) -- mismo patron que ForceBlack, no se tomo el banner como dato confiable.

**Registradas en `/admin/tiendas`** (`data/tiendas.json`): las 3 tiendas nuevas, mismo patron que las demas (sin codigo de descuento real todavia).

## Categoria nueva "conjunto" (2026-08-25)

Los 5 "TRACKSUIT" de Novorich (hoodie + pantalon vendidos como una sola pieza) no encajaban en el esquema de la app, donde cada producto es 1 sola prenda (de arriba o de abajo). El usuario eligio explicitamente la opcion mas simple: una categoria nueva `"conjunto"` con una sola ficha por producto, aceptando que por ahora **no aparece en las 2 busquedas estructuradas del formulario** ("prenda superior"/"prenda inferior", via `CATEGORIA_GRUPOS` en `app.py`) -- solo se encuentra por texto libre o por Koko. Es una limitacion conocida y aceptada, no un bug pendiente.

**Implementacion:** `clasificar_prenda()` en `construir_catalogo_real.py` ahora detecta la palabra "tracksuit"/"conjunto" en el nombre real del producto y devuelve `categoria="conjunto"` directo (sin subtipo/manga/largo -- esos campos son de 1 sola prenda, no aplican a un set de 2 piezas, no se inventa un valor). Se prefirio esto por sobre agregar 5 entradas a `VERIFICADO_A_MANO` (mas fragil: se rompe si la tienda renombra el producto) -- ademas queda reutilizable automaticamente si otra tienda futura vende conjuntos. Los 5 handles se sacaron de la lista de exclusion de `NOVORICH` (`cargar_shopify_cache(...)`) y ahora cargan con fotos/descripcion/stock reales igual que el resto de Novorich.

**Resultado real (verificado en `data/catalog.json` tras regenerar):** 5 productos con `categoria == "conjunto"`, catalogo total 658 productos.

| Producto | Fotos | Precio | Tallas disponibles hoy |
| --- | --- | --- | --- |
| NOVVM LUXURY - BLACK TRACKSUIT | 3 | $64.990 | ninguna (agotado) |
| NOVVM LUXURY - PURPLE TRACKSUIT | 3 | $64.990 | ninguna (agotado) |
| NOVVM LUXURY - WHITE TRACKSUIT | 3 | $82.990 | ninguna (agotado) |
| NOVVM ESSENCE - PURPLE TRACKSUIT | 4 | $82.990 | ninguna (agotado) |
| NOVVM ESSENCE - BLVCK TRACKSUIT | 8 | $65.000 | **S, M, L, XL (stock completo)** |

No se toco nada del buscador, del checkout, ni de otras tiendas -- alcance acotado solo a esta categoria nueva.

**Catalogo total tras este piloto: 653 productos en 17 tiendas** (622 anteriores + 21 Novorich + 8 Shatters + 2 Stuffies Concept). Corte real asignado: 416/645 prendas (204 "sin corte definido" explicito + ~25 sin ninguna senal de corte ni en nombre ni verificado a mano, mismo patron pre-existente en el resto del catalogo). Verificado: `probar_buscador_real.py` sigue funcionando y ya recomienda productos de las tiendas nuevas (ej. "HODDIE - ESSENCE BLACK" de Novorich aparece para "Hombre / concierto / polera oversize").

## Ampliación desde el Excel de candidatas (2026-08-22/23, en curso)

El usuario pidió seguir cargando y tageando tiendas del Excel de candidatas (`C:\Users\56982\Downloads\tiendas_ropa_urbana_lista_final.xlsx`, hoja "Tiendas unificadas", ~80 filas) de forma autónoma y continua, sin pausar a confirmar cada decisión — casos dudosos se documentan aquí para revisión, no se espera respuesta antes de seguir avanzando. Ver la sección "Casos dudosos / anómalos" más abajo para la lista completa a revisar.

**Tiendas nuevas cargadas hasta ahora** (además de las 8 originales — OVA Chile, Oversaints, El Pulento Style, Rapt, Roots South, Rotten, Selvanegrawear, Simpl.):

| Tienda | Productos | Notas |
| --- | --- | --- |
| AbsolutelyWrong | 23 | Marca propia, Shopify. Incluye preventa. |
| ForceBlack | 22 | Solo jeans + 1 short, marca propia. |
| Floating | 17 | Marca propia. "Tag Camo Cap" excluido (gorro tipo cap, sin categoría en la app). |
| BANG GANG (bvnggvng.cl) | 92 | Catálogo grande, extraído vía `products.json` de Shopify (ver técnica abajo). Excluidos: seguro de envío, máscara, 3 gorros tipo cap, packs "Mystery" (sorpresa). |
| UNK Chile (unkchile.cl) | 103 | Catálogo grande, `products.json`. Excluidos: producto de prueba, ítems a $0, gorros/beanies/snapback/dadhats, bolsos/mochilas, ropa de niño ("...Kids..."). 63 productos (poleras gráficas/tie-dye + chaquetas cortaviento) quedaron "sin corte definido" — formas muy variadas, sin señal clara ni en texto ni en foto. |
| Doslobos (dosloboschile.cl) | 231 | Catálogo muy grande (373 productos totales en la tienda, 2 páginas de `products.json`) — solo se cargó ropa. Excluidos: Bolsos (77), bufandas (8), Gorro (22), falda (1). 98 poleras quedaron "sin corte definido" (el corte varía producto a producto, verificado en 2 casos distintos — no se generalizó). |

**CATÁLOGO COMPLETO: 622 productos reales en 14 tiendas piloto.**

**Técnica nueva para catálogos grandes (2026-08-23):** para tiendas Shopify con muchos productos, `WebFetch` en la página de colección se queda corto (trunca, no siempre trae precio/link/imagen juntos). Mucho más confiable: `curl https://{tienda}/products.json?limit=250` — devuelve TODOS los productos con nombre/precio/handle/imagen en un JSON limpio, sin scraping de HTML. Usado para BANG GANG (92 productos en 1 sola descarga). Recomendado para cualquier tienda Shopify grande de ahora en adelante.

**2 bugs reales de clasificación encontrados y corregidos en `construir_catalogo_real.py` (afectan a CUALQUIER tienda, no solo las nuevas):**
1. `clasificar_prenda()` no reconocía "short"/"shorts" en el nombre — nunca había aparecido en las 8 tiendas originales. Los productos caían por defecto a categoría "polera" (incorrecta). Agregada rama nueva para "short".
2. `clasificar_prenda()` solo activaba categoría "pantalon" con las palabras "trouser"/"pantalon" — "jean"/"denim" solo contaban para el *subtipo*, nunca para la categoría en sí. Encontrado cargando ForceBlack (22 productos "... jeans" que caían a "polera"). Corregido: ahora "jean"/"denim" también disparan la categoría pantalón (el chequeo de chaqueta/"denim jacket" sigue teniendo prioridad, así que no se cruza con chaquetas de mezclilla).

**3 mecanismos de override nuevos agregados a `construir_producto()`** (antes `VERIFICADO_A_MANO` solo podía forzar `corte`/`material`/`gramaje_gsm`): ahora también puede forzar `categoria`, `subtipo`, y `largo` — necesarios para nombres de producto que no traen ninguna palabra clave reconocible (ej. "Thunder Black" es un jean pero no dice "jean" en el nombre) o cuando la ficha real contradice lo que el nombre sugeriría (ej. "Baby tee" que la propia tienda aclara que NO es largo crop).

**Tiendas revisadas y descartadas (no cargadas):**
- **Daravos** (daravos.cl): sitio WooCommerce con datos inconsistentes — producto principal "agotado", varios links a productos individuales devuelven 404. Se dejó de lado por baja calidad de datos disponibles hoy; se puede reintentar más adelante.
- **Inkultura** (inkultura.cl): vende poleras de bandas/anime con licencia de terceros (Rawayana, Iron Maiden, BabyMetal, etc.) — no es diseño propio, no calza con el criterio "marcas independientes" del proyecto.
- **jags.cl, archived.cl, kavu.store, palamleon.cl, project009.cl, butterflly.cl, stodak.cl**: dominios no resuelven (DNS muerto) o dan error — la tienda puede haber cerrado o cambiado de dominio.
- **drugstore.cl**: es una galería comercial física (mall), no la tienda de streetwear "Drugstore_cl" del Instagram original — entidad distinta, no cargada.

**Fresh Brand (freshbrand.cl)**: revisada y descartada también — inventario prácticamente vacío al momento de revisar (solo 2 bolsos + 1 jean agotado; las categorías "poleras"/"polerones" mostraban "no hay productos aquí"). Se puede reintentar más adelante si vuelven a tener stock.

**Pendientes de cargar (identificadas como reales, quedaron fuera por decisión explícita del usuario de parar la carga de tiendas en Doslobos para avanzar en otras cosas — no por ningún problema con ellas):** Below Apparel (belowapparel.com), Kuro Archives (kuroarchives.com), Artmob (artmob.cl — marketplace multi-marca, revisar con cuidado para no marcar `marca_autor=true` en productos revendidos), Hood House (hoodhouse.cl — también multi-marca, incluye reventa de Obey). Quedan ~65 filas del Excel sin investigar todavía (las que no tenían pista de dominio real, ver metodología abajo).

## Casos dudosos / anómalos para revisión del dueño del proyecto

Cada uno se resolvió con la decisión más razonable posible para no frenar la carga, siguiendo el mismo criterio ya usado antes (nunca inventar, preferir la foto real cuando el texto es ambiguo) — pero quedan para tu confirmación:

1. **Enila (enila.cl)** — está en el Excel como "tienda ropa urbana", pero sus productos (Blazer $150.000, Chaleco $79.900, Blusa $65.000) se sienten más "básicos elevados/minimalistas" que streetwear. No se cargó todavía — confirmar si encaja con el proyecto antes de sumarla.
2. **AbsolutelyWrong — "Polerón Básico Heavyweight"**: la ficha real dice literal "Boxy Regular Fit" (mezcla 2 cortes). Se revisó la foto y se optó por `boxy fit` (silueta ancha/cuadrada visible). Revisar si están de acuerdo con ese desempate.
3. **Floating — "Polera Esencial"**: la ficha dice "calce ajustado" pero la foto muestra una silueta claramente ancha/boxy (no ajustada al cuerpo). Se priorizó la foto sobre el texto de marketing → `boxy fit`. Mismo tipo de contradicción texto/foto que el caso anterior.
4. **Floating — "Baby tee"**: nombrada "baby tee" (que por regla general de la app implica largo crop), pero la ficha real aclara explícitamente que NO es corta, da medidas de largo normal. Se respetó la ficha real por sobre la regla genérica del nombre — quedó como `top`/`babytee` (por el nombre) pero con `largo: normal` (por la ficha). Revisar si en general conviene sacar el subtipo "babytee" cuando el largo real no es crop.
5. **Floating — "Noir Pulse"/"Nuit Volt"**: ficha dice "combinación entre boxy y oversize" (texto de marketing ambiguo, sin desempate claro). Se revisó la foto y se optó por `oversize` (hombros caídos, mangas anchas, largo que pasa la cadera). Aplica a toda la línea "Perfect Fit" de la marca.
6. **Floating — "Tag Camo Cap"**: gorro tipo cap/snapback con visera. El flujo de gorro de la app solo maneja curvo/plano/lana (sin visera) — no se cargó. Si se quiere vender gorros con visera, hay que definir esa categoría primero.
7. **Artmob / Hood House (pendientes de cargar)**: ambas son "marketplaces" que revenden marcas de terceros (Artmob incluye a Stodak y otras marcas dentro de sus colecciones; Hood House vende Obey, Two Jeys, además de su propia línea). Cuando se carguen, hay que separar cuidadosamente qué productos son diseño propio de la tienda (`marca_autor: true`) de los que son reventa de otra marca (`marca_autor: false`, o directamente no cargarlos — mismo criterio que se usó para excluir Reserved.cl).
8. **BANG GANG — "Poleron Crystals Logo BG"**: la tienda tiene 2 productos reales distintos (IDs y precios distintos, $39.990 y $69.990) con el nombre EXACTAMENTE igual — no es un error nuestro, la tienda los nombró igual. Ambos quedaron cargados como productos separados; en el buscador van a aparecer con el mismo nombre pero son fichas/links distintos. Si se quiere diferenciarlos visualmente habría que agregar algo al nombre a mano (ej. "(v2)").
9. **BANG GANG — packs "Mystery" no cargados**: la tienda vende "Pack Poleras Mystery Double/Triple" y "Pack Polerones Mystery..." (producto sorpresa, no se sabe cuál diseño específico llega) — no se pueden representar honestamente en el catálogo (no hay un producto real y determinado detrás), se dejaron fuera.
10. **Doslobos — "Sweater"/"Cardigan" clasificados como `chaleco`, no `poleron`**: la tienda los categoriza junto con los hoodies (mismo `product_type` "Hoodie" en su sistema), pero no tienen capucha — se decidió tratarlos como `chaleco` (categoría de la app para prendas de punto sin capucha) en vez de `poleron`. Confirmar si están de acuerdo con esa decisión.
11. **Doslobos — 2 productos "METAL GRAY/BLACK PANTS"**: la propia tienda los tenía mal etiquetados bajo el tipo "Hoodie" en su sistema interno (son pantalones). Se corrigió la categoría acá basándose en el nombre real del producto, no en la clasificación (errónea) de la tienda.
12. **Doslobos — 50 "Poleras" sin corte definido**: a diferencia de otras tiendas donde el corte es consistente por línea, acá se verificó que el corte varía producto a producto dentro de la misma categoría "Poleras" (un producto decía "Boxy-fit", otro "Oversize-fit", sin patrón por nombre) — no se generalizó ninguno para no arriesgar un dato incorrecto. Si se quiere completar esto, hay que revisar la ficha real de cada una (o al menos agruparlas por línea/diseño como se hizo con las tiendas chicas).
13. **Doslobos — 17 "Chaquetas" generalizadas a `oversize`**: solo se verificó 1 producto representativo ("CAMO 10TH BOMBER-JACKET"), no 2 como en el resto de los casos — menor certeza que las demás decisiones de este documento. Revisar con más cuidado si se quiere confirmar.


## Imágenes ilustrativas del catálogo mock

Cada producto (prenda o gorro) trae un campo `imagen` → SVG en `static/img/{gorros,prendas}/`, generado a mano por `generar_imagenes_gorro.py` / `generar_imagenes_prendas.py` **antes** de correr `generar_catalogo_prueba.py`. Nunca son fotos reales ni copian logos/diseños de marcas reales — estética streetwear genérica (paneles de color, formas bold). La UI (`static/comun.js`) siempre muestra el aviso "Imagen ilustrativa de referencia, no es el producto real." debajo de la imagen.

- **Gorro**: el color de la imagen SÍ es el dato real (`color_dominante`). Curvo/plano en sólido y en dos tonos (panel frontal según la tabla `PANEL_SUGERIDO`); lana solo en sólido.
- **Prendas**: el catálogo mock no tiene campo de color real para prendas, así que `generar_catalogo_prueba.py` le asigna a cada producto un color **inventado** al azar (misma paleta de 8 colores) solo para la imagen — no se guarda como dato del producto ni filtra nada. Siluetas por tipo: polera (manga larga/corta), camiseta, camisa (con botones), chaqueta, polerón (4 combos capucha/cierre), los 6 subtipos de Top, pantalón/shorts/bike shorts/falda cargo (misma silueta para todos los subtipos de pantalón/shorts — ahí la variedad es solo de color).

## Taguear catálogo real que no trae estos datos explícitos

Ni corte ni talla vienen siempre explícitos en la ficha de una tienda real. El criterio es que Claude infiera el dato producto por producto contra las tablas de arriba — **no** preguntar de entrada ni dejar el campo vacío:
- **Corte**: comparar descripción/medidas contra la tabla de corte (y los cm cuando la ficha dé medidas concretas de holgura).
- **Talla** (`tallas_disponibles`): si la ficha da medidas propias de la prenda (ancho de pecho, largo), cruzarlas contra la tabla de talla de arriba para inferir a qué talla(s) le calzarían.

Si la ficha no da ni descripción ni medidas suficientes para inferir con confianza, no inventar el dato — preguntarle al usuario (dueño del proyecto) antes de taguear a ciegas.

## Cómo se construyó el catálogo real (2026-08-19/20)

`data/catalog.json` dejó de ser el catálogo mock — ahora son **138 productos reales** de 8 tiendas piloto chilenas de streetwear (OVA Chile, Oversaints, El Pulento Style, Rapt, Roots South, Rotten, Selvanegrawear, Simpl.), investigadas a mano el 2026-08-19 (de 14 candidatas, 9 tenían sitio real; Reserved se dejó afuera a propósito por revender marcas de lujo con riesgo de réplica). El catálogo mock viejo quedó respaldado en `data/catalog_mock_backup.json`, nunca se borra.

**`construir_catalogo_real.py` es la ÚNICA fuente de verdad — nunca editar `data/catalog.json` a mano.** Reconstruye el catálogo completo desde cero cada vez que se corre (`.\venv\Scripts\python.exe construir_catalogo_real.py`), a partir de:
- Listas de productos por tienda (nombre, precio, link, imagen) sacadas directo de la página real (WebFetch), nunca inventadas.
- `clasificar_prenda()`: categoría/subtipo/género/manga/largo inferidos del nombre real con reglas explícitas (ej. "cargo" en el nombre → subtipo cargo).
- `VERIFICADO_A_MANO`: dict nombre→corte (+ material/gramaje cuando aplica), verificado a mano leyendo la ficha real de al menos un producto representativo de cada línea/colección (mismo diseño, distinto color) — el corte encontrado se generaliza a toda esa línea, nunca entre líneas distintas. Sin señal clara de un corte específico (selector múltiple, texto ambiguo), se marca literal `"sin corte definido"` — nunca se adivina.
- `CAPUCHA_CIERRE_VERIFICADO` (2026-08-20): mismo método para polerones — `"con capucha"`/`"con cierre"` solo si la ficha o el **nombre mismo** dice literalmente "capucha"/"hoodie"/"gorro" (capucha) o "cierre"/"zip"/"zipper" (cierre); sin esa señal, `"no especificado"` — nunca se asume "sin capucha"/"sin cierre" por defecto.

**Después de cualquier cambio a estos diccionarios, hay que volver a correr el script** para que `catalog.json` refleje el cambio — el script no se corre solo. (Se encontró y corrigió un desajuste así el 2026-08-20: un corte ya verificado en el diccionario que no se había aplicado porque faltaba re-correr el script.)

**Estado del tagueo (verificado 2026-08-20):** de 134 productos reales, 126 son prendas (sin contar gorros) — 83 tienen corte real asignado y 43 quedan `"sin corte definido"` a propósito (la ficha real no da una sola opción clara). Correr el script imprime la lista completa de "sin corte definido" al final, para revisar de a poco si en algún momento se quiere ampliar.

**Capucha/cierre de los polerones (2026-08-20, 2 pasadas):** primero se revisó el texto de cada ficha/nombre; para lo que quedó sin dato, se revisó además la FOTO real del producto (ver `CAPUCHA_CIERRE_VERIFICADO` en `construir_catalogo_real.py`). Resultado: 21/24 con capucha confirmada, 17/24 con cierre confirmado. `FUENTE_CAPUCHA_CIERRE` (mismo archivo) indica, producto por producto, si el dato salió del texto o de la foto — revisar ahí primero si alguna vez hay dudas sobre un dato puntual. Quedan sin poder confirmar: los 2 "BUZO BAGGY" de OVA Chile (la única foto disponible está recortada a la altura del pecho).

**Pantalones "cargo" (2026-08-20, confirmado por foto):** de los 16 pantalones reales, se revisó la foto de cada línea de Simpl./Rapt buscando bolsillos cargo visibles — ninguno los tiene (son baggy simples de bolsillo normal). El único pantalón cargo real del catálogo sigue siendo "Pantalón Cargo Woodland" (Simpl.), confirmado por nombre. Esto es un límite real del catálogo piloto, no un hueco de tagueo.

**4 productos sacados del catálogo (2026-08-20):** las "Sudadera" de Selvanegrawear (Gris Perla, Marengo, Oranwutang, Sudamérica) estaban categorizadas como `poleron`, pero al revisar el sitio real (selvanegrawear.cl) se confirmó que son **musculosas sin mangas de liquidación** ("Remate"/"Stock Total" en el sitio de la tienda, 50% descuento, 1 sola talla cada una), no polerones — decisión del dueño del proyecto de sacarlas en vez de dejarlas mal categorizadas. No hay categoría "musculosa"/tank top en la app todavía; si se quiere venderlas más adelante hay que agregar esa categoría primero (ver `SELVANEGRA_POLERAS` en `construir_catalogo_real.py`, quedaron comentadas ahí con el motivo).

**Aviso pendiente de confirmar con el dueño del proyecto:** "Espresso Zip Knit" (Roots South) está categorizado como `poleron` (por la palabra "Zip" en el nombre), pero la foto real muestra un **chaleco/cardigan tejido con cuello alto, sin capucha** — se le asignó `capucha: sin capucha` (confirmado por foto) porque eso sí se pudo verificar, pero la categoría "poleron" en sí podría no ser la más precisa (podría ser mejor `chaleco`). No se cambió la categoría sin pedirlo.

Script de prueba rápida del buscador contra el catálogo real: `probar_buscador_real.py` (mismo patrón que `probar_reglas.py`, correr con `.\venv\Scripts\python.exe probar_buscador_real.py`).
