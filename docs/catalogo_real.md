# Catalogo real

## Interes "anime" en Kotonaru Store + IPREX (2026-08-30)

Mismo mecanismo que `interes_musica`/`interes_arte` (ver seccion de abajo): `construir_producto()` ahora acepta tambien `interes_anime`/`franquicia_anime`, agregados a `tags` como `"anime"` + el nombre de la franquicia en minuscula. Revisados nombre + descripcion + tags de TODO Kotonaru (36 productos) e IPREX (62), mas imagen principal de los candidatos donde el texto no alcanzaba para confirmar.

**Kotonaru Store: 0 tageados.** 3 candidatos revisados por imagen ("Chii Neo Sigilism", "707 Nana VW", "Neo Yukii Vampire") -- las 3 son ilustraciones ORIGINALES estilo anime de la marca (ninguna referencia real a Chobits/Nana/una obra concreta), no se tagean por la regla explicita de "no marcar solo por parecer anime style".

**IPREX: 1 tageado** -- "Poleron ninja Kuromi" (`interes_anime=True`, `franquicia_anime="Kuromi"`): la imagen confirma la cara/orejas real de Kuromi (personaje de Sanrio con series de anime propias). 3 candidatos revisados y descartados por imagen: "Polera Waifu Saddabae" (foto de modelo IA con estilo anime, pero la polera en si no tiene grafico anime), "Polera Waifu triviales Saddabae" (grafico de un personaje original de la marca "Sad Rulay", sin franquicia real) y "Poleron personajes Saddabae" (grupo de personajes genericos sin identificador de obra). Los poleones "ninja [Nombre Latin]" (Daemon, Desperatio, Gehenna, etc.) tampoco se tagean: "ninja" es tematica generica, no evidencia de anime.

## IPREX, BEEWAY, WAV -- 3 tiendas web/automaticas + tags de interes musica/arte (2026-08-30)

**IPREX (iprex.cl):** el sitio principal es infraestructura B2B de fabricacion/merchandising corporativo (asi se describe a si mismo), pero tiene una tienda retail real aparte (`tienda.iprex.cl`, WordPress/WooCommerce con la API REST bloqueada -- se parseo el JSON-LD real de cada pagina de producto via curl, `cargar_iprex_cache()`). **62 de 67 productos cargados.** 5 excluidos por no ser retail individual: 3 packs "al por mayor (12 unidades)", 1 pedido interno pausado ("Fade Away, paralizado") y 1 producto con "TEST" literal en el nombre. Las chaquetas linea RACE (BMW, Ferrari, Nascar, Subaru, Ford, McLaren, Red Bull) se cargaron tal como las describe IPREX, sin agregar afirmaciones propias sobre licencias/autenticidad (pedido explicito del usuario). Envio: "despacho a todo Chile", gratis sobre $150.000, sin plazo en dias ni desglose RM/regiones publicado.

**BEEWAY (beeway.cl):** Shopify, 47 productos. **45 cargados**, 2 excluidos (1 entrada de evento/fiesta, 1 "PAGO DS" -- link de pago interno, no producto). Trae 14 jockeys/gorras -- `clasificar_prenda()` ahora reconoce "jockey"/"gorra"/"cap" como categoria `gorro` (antes caian por defecto a "polera", bug real). Estos gorros con visera no tienen `forma` curvo/plano/lana asignada (el flujo de forma de la app no maneja visera) -- aparecen en busquedas generales de gorro pero quedan fuera si el usuario filtra por una forma especifica; no rompe nada, solo no aplica ese filtro. Sin pagina de politica de envio (404 en las rutas Shopify habituales ni en el home) -- envio queda "no especificado".

**WAV (wearewav.cl):** Shopify, 43 productos. **30 cargados**, 13 excluidos: 7 "Bundle WAV" (combos de 2-3 productos en 1 ficha, no se puede taguear color/categoria real de un combo) + 6 accesorios fuera del alcance de la app (2 anillos, 2 bolsos, 2 pañoletas). Envio: 2-7 dias habiles RM/regiones principales, 7-12 dias en regiones extremas, gratis sobre $100.000 (`policies/shipping-policy` real).

**Intereses musica/arte (nuevo, reutilizable para cualquier tienda futura):** `construir_producto()` acepta `interes_musica`/`interes_arte` (booleanos), solo marcados cuando la descripcion real de la ficha lo dice explicito -- nunca por estetica. En WAV: **2 productos con `interes_musica`** ("Poleron Ghost Input 808" por el termino "808", produccion musical real en el nombre; "Crewneck Art Escapist" por la frase literal "a traves del arte, la musica, el baile") y **3 con `interes_arte`** (el mismo Art Escapist + "Haring Jort Japones" y el hoodie Warhol, ambos con referencia artistica explicita real). Se revisaron TODAS las descripciones de WAV buscando palabras de música/arte antes de descartar el resto -- ninguna otra ficha tiene evidencia real. No se creo un sistema de ranking aparte: estos tags se agregan al campo `tags` del producto, que ya entra al texto que compara `elegir_candidatos()` contra el pedido -- y `app.py` ya mete los hobbies del perfil (`"musica"` literal) en ese mismo texto de busqueda, asi que un usuario con "Música" en sus gustos obtiene una senal de ranking real (no una restriccion) reusando el mecanismo de palabras ya existente, sin tocar Koko ni crear infraestructura paralela. Limitacion conocida: es una senal suave -- con productos que ya comparten 3-4 palabras por categoria/ocasion generica, el empate hace que el tag de interes no siempre gane el top 5.

Las 3 quedan en `TIENDAS_OFICIALES` (venta in-app) y registradas en `data/tiendas.json`/`data/envios_tiendas.json`. Catalogo tras esto: 1317 productos. Verificado con `probar_buscador_real.py` sin errores.

## Blazze completa, Kagi solo streetwear, Magia Negra pendiente (2026-08-27)

**Magia Negra Clothing (magianegraclothing.com) -- NO investigada.** El
sitio esta con contraseña de Shopify ("password protected", 401 al pedir
`products.json`, redirect en el home) -- no es publica todavia. Usuario
confirmo dejarla pendiente hasta que la tienda abra o consiga la clave.

**Blazze (blazze.cl):** Shopify, 18 productos, todos cargados y
oficiales. Marca 100% denim -- ningun nombre real trae la categoria
("Blazze 04 - Zip set indigo", etc.), toda la categoria/subtipo/corte se
saco de la descripcion real de cada ficha. Encontrado un caso real de
"conjunto" (2 productos: chaqueta+jean del mismo lavado, variantes
combinadas S/M/L x 34/36/38/40 -- mismo criterio que los tracksuit de
Novorich). 4 productos con corte "straight" confirmado por texto literal
("pierna recta"). Revisada 1 foto a mano (outfit denim real, sin marca
ajena). Envio real: 2 a 5 dias habiles + retiro en "punto Blazze".

**Kagi (kagi.cl) -- cargada solo parcialmente, pedido explicito del
usuario.** De 45 productos reales, la mayoria es basico
elevado/minimalista fuera del foco streetwear (faldas, vestido, cardigan,
bufanda, bolsos/tote, posavasos, giftcard) -- mismo patron que Enila. El
usuario pidio cargar SOLO jeans/polerones/poleras/chalecos/chaquetas: de
esa lista Kagi solo tenia real 1 jort de denim, 2 poleras, 1 chaqueta y 1
cardigan (tratado como categoria "chaleco", mismo criterio ya usado con
Doslobos) -- ningun poleron ni pantalon-jean real. **6 de 45 productos
cargados**, los otros 39 quedaron afuera (`KAGI_HANDLES_STREETWEAR` en
`construir_catalogo_real.py`). Revisada 1 foto a mano (chaqueta con
broches metalicos, diseño propio). Envio: sin plazo publicado (pagina de
politica da 404, tampoco esta en el home).

**Catalogo: 868 productos en 24 tiendas** (844 + 18 Blazze + 6 Kagi).
**860 de 868 oficiales.** Verificado con `probar_buscador_real.py` sin
errores y `/api/tiendas_rapido?direccion=Santiago` mostrando el envio de
ambas.

## 2 tiendas nuevas mas: Haze Concept, Kotonaru Store -- Enila descartada (2026-08-27)

**Enila (enila.cl) -- NO cargada.** Ya estaba anotada como "caso dudoso"
desde una sesion anterior (Blazer $150.000, Chaleco, Blusa -- se siente
basico elevado/minimalista, no streetwear). Se le pregunto explicitamente
al usuario y confirmo dejarla afuera, consistente con el foco del
proyecto (ver `CLAUDE.md`).

**Haze Concept (hazeconcept.com):** Shopify, 43 productos, todos
cargados y oficiales. 0 "sin corte definido" -- casi todos los nombres ya
dicen "Boxy Fit"/"HEAVYWEIGHT". Revisada 1 foto a mano (logo propio "H"
bordado, sin marca ajena). Envio real: hasta 24h de procesamiento + 1 a 5
dias habiles de transito, con opcion Same Day en RM (Lun/Mie/Jue antes de
11 AM).

**Kotonaru Store (kotonaru-store.cl) -- la mas compleja de armar, con un
caso de contenido sensible encontrado:** plataforma Jumpseller (como
Rapt), sin catalogo publico masivo -- se armo a mano por producto (~45
paginas revisadas, `og:title`/`og:description`/`og:image`/
`product:price:amount`, sin IA de por medio para mantener el gasto de
tokens bajo). **9 productos de 45 NO se cargaron:**
- 1 cap con visera + 1 cadena/colgante (no es una prenda) + 1 gorro de
  lana que el nombre no detecta como tal (caso de 1 solo producto, no se
  armo el mecanismo de gorro aparte).
- **5 productos cuya UNICA foto real tiene nombre de archivo literal
  "mock_up_.../mockup..."** (Afriel Slim-fit T-shirt, Hoodie Skeleton
  Logo, Hoodie y T-Shirt "Misa Amane", Tank Tejido) -- mismo criterio que
  las fotos de IA descartadas en Club 33: no hay foto real disponible
  para esos productos, no se carga con una que no lo es.
- **"Reichsadler T-shirt Focalizado"**: la ficha real muestra el escudo
  del aguila imperial alemana ("Reichsadler") de forma explicita y
  grande en el estampado -- **se le pregunto al usuario dado el peso
  historico/simbolico de la imagen (no es la esvastica nazi, pero es un
  simbolo cargado) y decidio no cargar esa ficha puntual.** El hoodie
  "Hoodie BoxyFit CROP Reichsadler" (mismo nombre de coleccion) SI se
  cargo -- se reviso su foto real a mano y el diseño es abstracto/gotico,
  sin el aguila visible, asi que no aplica el mismo motivo.
- Quedan 36 productos cargados y oficiales, 0 "sin corte definido"
  (la mayoria de nombres ya dice "Boxy-fit"/"Oversize"/"Slim-fit").
  **Limitacion aceptada:** cada producto tiene 1 sola foto real (no una
  galeria completa) -- Jumpseller no expone las demas fotos del producto
  de forma barata de sacar sin scrapear cada pagina a fondo, mismo limite
  ya aceptado para Rapt.

Envio: sin plazo en dias publicado por Kotonaru (revisado home + politica
de reembolso, no tiene pagina de envio aparte).

**Catalogo: 844 productos en 22 tiendas** (765 + 43 Haze + 36 Kotonaru).
**836 de 844 oficiales.** Ambas registradas en `data/tiendas.json` y
`data/envios_tiendas.json`. Verificado con `probar_buscador_real.py` sin
errores y `/api/tiendas_rapido?direccion=Santiago` mostrando el envio de
ambas.

## 3 tiendas nuevas desde cero: Feroni Studios, Addictve, 1Libra (2026-08-27)

Primeras tiendas totalmente nuevas desde Club 33 (nunca antes en el
catalogo). Las 3 resultaron ser Shopify -- mismo mecanismo 100% real de
siempre (`cargar_shopify_cache()`, Tanda 6). Pedido explicito del usuario
de priorizar tokens: no se reviso foto por foto de cada producto, se
revisaron muestras (2 a 4 por tienda) mas los casos que se veian raros a
simple vista por nombre.

**Feroni Studios (feronistudios.cl):** 5 productos, todos cargados.
Descripciones reales dan corte explicito para 2 que el nombre no
detectaba solo ("Long Sleeve FERONI" -> slim fit, "Full Zip Hoodie
Leopardo" -> boxy fit + capucha/cierre confirmados por texto). Revisada 1
foto a mano (shooting real, sin marca ajena). Envio: sin plazo publicado
(solo "despacho a todo Chile" en el banner).

**Addictve (addictve.cl):** 31 productos, todos cargados. Fichas reales
muy completas (material con %, gramaje GSM, "boxy fit" ya en el nombre de
varios) -- 0 productos quedaron "sin corte definido", el nombre solo ya
alcanzaba. Revisadas 2 fotos a mano (jean con tag propio, hoodie liso),
sin marca ajena. Envio real encontrado: 1 a 3 dias habiles de
procesamiento + transito por Bluexpress (RM ~24h, regiones 1 a 5 dias).

**1Libra (1libra.cl) -- la mas grande, con un caso serio encontrado:**
121 productos reales en el sitio, se cargaron 80. **41 excluidos:**
- 22 packs/sets de 2-3 prendas distintas vendidas como una sola ficha
  (ej. "PACK HOODIE + POLERA") + 7 gorros "Snapback" (visera, sin
  categoria en la app) + 1 gift card.
- **19 productos de la linea "RACE DEPT"** con diseños que copian el
  escudo de Porsche (misma forma de escudo, mismo patron a cuadros) y
  dicen literal **"PORSCHE"** en el estampado de varios; otros usan el
  estilo/colores de **Rothmans** (marca real de patrocinio de carreras,
  escuderia Porsche de los 80s). A diferencia de El Pulento Style (que
  revendia prendas ajenas reales), esto es manufactura propia de 1Libra
  con estampado que parodia/copia marcas reales -- **se le pregunto
  explicitamente al usuario y eligio excluir solo esa linea, no la tienda
  completa** (el resto -- ~80 productos -- es diseño propio sin marca
  ajena, verificado revisando 2 fotos fuera de esa linea). Ver
  `excluir_handles` de `LIBRA1` en `construir_catalogo_real.py` para la
  lista completa de los 19 handles excluidos.

0 productos de las 3 tiendas quedaron "sin corte definido" -- casi todos
los nombres ya dicen "OVERSIZED"/"BOXYFIT" literal, `detectar_corte()` los
tomo solos sin necesitar revision manual producto por producto.

**Catalogo: 765 productos en 20 tiendas** (649 + 5 + 31 + 80). **757 de
765 quedan oficiales** (todo menos los 8 gorros IA de Selvanegrawear).
Envio real investigado y agregado para las 3 (`data/envios_tiendas.json`)
y registradas en `data/tiendas.json` (`1libra`, `addictve`,
`feroni-studios`, todas `sin_sitio_web` -- mismo patron que las demas).
Verificado con `probar_buscador_real.py` sin errores y
`/api/tiendas_rapido?direccion=Santiago` mostrando el envio real de las 3.

## Rapt y Selvanegrawear oficiales -- ultimas 2, con excepcion de gorros IA (2026-08-27)

Las 2 unicas tiendas que quedaban sin fotos/descripcion reales. Pedido
explicito del usuario de priorizar tokens -- se evito re-scrapear
galerias completas donde no habia una fuente masiva barata.

**Rapt (rapt.cl):** plataforma Jumpseller, sin `products.json` publico
(Shopify) ni Store API (WooCommerce) -- no hay archivo para cachear y
cruzar en bloque. Se saco el dato real mas barato posible: `og:description`
de cada una de las 20 paginas de producto (1 curl por producto, sin IA de
por medio) -- da descripcion real corta pero con composicion real
("60% algodon", "70% algodon / 30% poliester", "silueta boxy/baggy", etc.).
La foto (`imagen`) ya era real desde el 2026-08-19 (Rapt nunca tuvo
ilustracion mock) -- se paso como `fotos: [esa misma foto]` para que el
modal deje de usar el truco de imagen ilustrativa, sin prometer una
galeria de varias fotos que no se pudo conseguir sin scrapear cada pagina
a mano (fuera de alcance hoy por costo). 3 cortes nuevos confirmados por
texto real: "RAW DENIM JACKET" y "FOUNDATION TROUSER"/"FOUNDATION TROUSER
BLACK" (antes "sin corte definido"). Revisada 1 foto a mano (logo propio
"raptstudios", sin marca ajena). 20/20 productos quedan oficiales.

**Selvanegrawear (selvanegrawear.cl):** WooCommerce, mismo mecanismo que
El Pulento Style (Store API publica, `datos_woocommerce_por_slug()`,
reincorporada al codigo). **Los 8 gorros NO quedaron oficiales:** su
imagen real en el sitio de la tienda es literalmente
"Gemini_Generated_Image_*.png" (generada por IA, confirmado por el nombre
de archivo) para los 8 -- no hay foto real publicada de ningun gorro. Las
12 poleras + 2 canguros si tienen fotos reales (confirmado revisando 1 a
mano: logo propio "SELVA NEGRA", foto real de persona) y quedaron
oficiales.

**Mecanismo nuevo: `TIENDAS_OFICIALES_EXCEPCIONES`** (`construir_catalogo_real.py`)
-- primera vez que "oficial" necesita ser por categoria dentro de una
misma tienda, no toda o nada. `{"Selvanegrawear": {"gorro"}}` hoy; queda
generico por si otra tienda futura tiene el mismo caso (una parte del
catalogo con fotos reales, otra parte sin ellas).

Catalogo: 649 productos sin cambio de cantidad. **641 de 649 productos
quedan oficiales en total** (todo el catalogo excepto los 8 gorros de
Selvanegrawear). Verificado con `probar_buscador_real.py` sin errores.

## 8 tiendas mas oficiales: Doslobos, Rotten, OVA Chile, Floating, Oversaints, Roots South, Shatters, Stuffies Concept (2026-08-27)

Mismo tratamiento, en bloque para ahorrar tokens (pedido explicito del
usuario). Las 8 ya tenian fotos/descripcion/stock reales de tandas
anteriores (2026-08-24/25) -- se reviso 1 foto real de cada una a mano
(o 2 para Stuffies Concept, ver abajo) y se agregaron todas juntas a
`TIENDAS_OFICIALES`, sin tocar mas datos.

**Caso revisado con mas cuidado -- Stuffies Concept:** los 2 productos
tienen fotos con nombre de archivo "Imagen_de_Codex_..." (sospechoso,
mismo patron que las imagenes de IA descartadas en Club 33) mezcladas con
fotos "DSC####.jpg" (camara real). Se bajaron ambos tipos: el logo bordado
(3 estrellas) es IDENTICO entre la foto "Codex" (flat lay) y la foto real
de estudio (persona usandolo) -- mismo diseño real, probablemente una
herramienta de edicion/fondo llamada "Codex" proceso una foto real en vez
de generarla desde cero. Se dejaron ambas fotos sin sacar ninguna.

Catalogo: 649 productos sin cambio de cantidad. **607 de 649 productos
quedan oficiales -- solo faltan Rapt (20) y Selvanegrawear (22)**, las 2
unicas tiendas que todavia no tienen fotos/descripcion/stock reales
cargados (requieren el trabajo completo, como Club 33).

## AbsolutelyWrong y UNK Chile oficiales (2026-08-27)

Mismo tratamiento. Ambas ya tenian fotos/descripcion/stock reales (Tanda 2
y Tanda 3 respectivamente, 2026-08-25). Revisada 1 foto real de cada una a
mano -- buzo "ABSOLUTELY" (logo propio bordado) y poleron acid-wash de UNK
(grafismo propio en la manga) -- diseno propio, sin logos de marca ajena.
Solo se agregaron a `TIENDAS_OFICIALES`. AbsolutelyWrong sigue con el caso
dudoso ya documentado mas abajo (2 productos con link roto, sin foto real,
sin tocar). Catalogo: 649 productos sin cambio de cantidad, 23
(AbsolutelyWrong) + 103 (UNK Chile) mas marcados oficiales.

## Simpl. y ForceBlack oficiales (2026-08-27)

Mismo pedido, mismo tratamiento -- ambas ya tenian fotos/descripcion/stock
reales desde la Tanda 2 (2026-08-25). Revisada 1 foto real de cada una a
mano (pantalon negro liso de Simpl., jean negro de ForceBlack en foto de
espejo) -- diseno propio, sin logos de marca ajena. Solo se agregaron a
`TIENDAS_OFICIALES`, sin tocar datos. Envio: ambas ya estaban marcadas
"sin plazo publicado por la tienda" en `data/envios_tiendas.json` desde
antes (investigado en su momento, no es que falte revisar). Catalogo:
649 productos sin cambio de cantidad, 17 (Simpl.) + 22 (ForceBlack) mas
marcados oficiales.

## BANG GANG oficial, El Pulento Style bloqueada por posible reventa no autorizada (2026-08-27)

Usuario pidio el mismo tratamiento de Novorich/Club 33 para BANG GANG
(bvnggvng.cl) y El Pulento Style (elpulentostyle.cl) -- ambas YA estaban en
el catalogo (BANG GANG ya tenia fotos/descripcion/stock reales desde la
Tanda 3 del 2026-08-25; El Pulento Style seguia con imagen ilustrativa
desde el piloto original del 2026-08-19).

**BANG GANG -- marcada oficial sin cambios de datos.** Ya tenia todo real
(92 productos). Se revisaron a mano 4 fotos de productos distintos --
diseños propios de la marca (logo "BANGGANG" con relieve/cristales),
prendas fisicas reales fotografiadas colgadas, sin señales de IA ni de
marca ajena. Solo se agrego "BANG GANG" a `TIENDAS_OFICIALES`.

**El Pulento Style -- NO se marco oficial, cambio revertido.** Se bajo la
Store API publica de WooCommerce (`data/woocommerce_cache/elpulentostyle.json`,
144 productos reales) para cruzar los 12 productos ya cargados por
handle/slug -- mismo mecanismo que Shopify pero para WooCommerce (funcion
nueva `datos_woocommerce_por_slug()`, queda en el codigo lista para usar).
**Al revisar las fotos reales que la propia tienda subio, 5 de 5 productos
chequeados a mano son poleras con logos de marcas ajenas, no diseño propio
de "El Pulento Style"** pese a que la ficha del producto dice "Diseño
Bordado"/"Diseño Estampado" como si fuera de la marca -- y no es una sola
marca: "RED LINES OVERSIZE STYLE", "BLACK & MONEY OVERZISE", "BROWN &
OVERZISE" y la primera foto de "BLACK & CENTER OVERZISE" muestran el
logo/wordmark **NIKE**; "BLACK & STREET OVERZISE" muestra el logo de
**Corteiz** (marca UK real, icono de Alcatraz) -- es decir, la tienda
mezcla fotos de al menos 2 marcas de streetwear reales y ajenas bajo
nombres de producto genericos propios, patron de reventa/replica
multi-marca, no un error puntual de una sola foto. Mismo criterio ya usado
en este proyecto para descartar Reserved.cl e Inkultura (reventa de marca
ajena, riesgo de replica/falsificacion) -- se revirtio el cambio
(se saco del `TIENDAS_OFICIALES` y del cruce de `DATOS_SHOPIFY_UPGRADE`
antes de guardar `catalog.json`) y la tienda queda exactamente como estaba
antes de hoy (12 productos con imagen ilustrativa, sin fotos reales, sin
marcar oficial). **Pendiente de decision del usuario:** sacar la tienda
del catalogo por completo (mismo trato que Reserved.cl), pedirle que
aclare/corrija sus fotos si es un error de carga de su parte, o alguna
otra resolucion -- no se toco nada mas de esta tienda mientras tanto.

## Campo "oficial" y boton "Proximamente" (2026-08-27)

El usuario pidio dedicar una sesion a pasar tiendas de "vista previa" a
"oficial" (fotos reales, descripcion completa, stock real), empezando por
Novorich y Club 33 (consentimiento confirmado para ambas). Al revisar el
estado real antes de tocar nada, se encontro que **Novorich ya tenia fotos/
descripcion/stock reales desde el piloto del 2026-08-24** -- lo unico que
faltaba era que el frontend reflejara ese estado "listo para vender" (hasta
ahora, tener fotos reales y ser "oficial" eran la misma cosa implicitamente,
pero ya hay 9+ tiendas con fotos reales sin tener el visto bueno explicito
de "oficial"). **Club 33 no existe todavia en el catalogo ni en el codigo**
(nunca investigada) -- queda pendiente hasta que el usuario pase su sitio
web real.

**Decision del usuario:** se agrego un campo nuevo `"oficial": true/false`
por producto, distinto de "tiene foto real" -- solo lo tienen las tiendas
con consentimiento explicito para vender de verdad (hoy: Novorich). Mientras
el checkout interno (que Daniel esta construyendo aparte) no exista, un
producto oficial **no debe linkear afuera a comprar**: el boton pasa de
"Ver producto"/"Ir a la tienda" a un texto inerte **"Proximamente"** (gris,
sin click), tanto en la tarjeta de resultados/vitrina como en el modal
"Vista previa rapida". Las demas tiendas con fotos reales pero sin el flag
`oficial` siguen linkeando afuera normal, sin cambios.

**Implementacion:**
- `TIENDAS_OFICIALES` (set, `construir_catalogo_real.py`, junto a
  `construir_producto()`) -- hoy solo `{"Novorich"}`. Agregar `"Club 33"`
  ahi cuando se cargue con su sitio real.
- `producto["oficial"]` se calcula automatico en `construir_producto()`
  segun ese set, para cualquier tienda (no hace falta tocarlo tienda por
  tienda al cargar productos nuevos de una tienda ya marcada oficial).
- `botonAccionProductoHtml(rec)` (nuevo, `static/comun.js`) centraliza la
  decision del boton de "ir a comprar" -- usado por `renderResultados()`
  (comun.js) y `tarjetaVitrina()` (vitrina.js), para no duplicar la
  logica en 2 archivos.
- Modal de vista previa (`abrirVistaPrevia()`, comun.js): el boton
  `#vp-link` tambien pasa a "Proximamente" deshabilitado (clase
  `.boton-proximamente`, `aria-disabled`) cuando `rec.oficial` -- el click
  listener corta antes de abrir el link externo.

**Bug real encontrado y corregido de paso:** `formatear_producto()`
(`motor_recomendacion.py`), la UNICA funcion que arma la respuesta de
`/api/recommend` y `/api/vitrina` para el frontend, nunca copiaba el campo
`fotos` del producto -- significa que el modal "Vista previa rapida" jamas
mostro el set completo de fotos reales para NINGUNA tienda desde el piloto
del 24-08 (solo se veia 1 foto, la miniatura). Corregido agregando
`"fotos": producto.get("fotos", [])` y `"oficial": bool(producto.get("oficial", False))`
al dict que arma esa funcion. Verificado con `formatear_producto()` real
contra un producto de Novorich: las 8 fotos reales y `oficial: true` ya
llegan en el JSON de respuesta.

**Catalogo regenerado:** 658 productos (sin cambio de cantidad), 26 de
Novorich con `oficial: true`, resto en `false`. Verificado con
`data/catalog.json` tras correr `construir_catalogo_real.py`.

**Pendiente de decision del usuario (sin resolver hoy):** el gorro
"Skullcap" de Novorich ($13.592) sigue sin cargarse -- la ficha real no
confirma el material ("tejido suave", sin decir si es lana), no se carga
para no inventar el dato (ver piloto 2026-08-24 mas abajo).

## Club 33 cargada (2026-08-27)

Tienda nueva (club33.cl), consentimiento confirmado por el usuario. Shopify,
5 productos en `products.json`, pero **solo se cargaron 3** -- ver motivo
abajo. Marcada `oficial: true` (mismo mecanismo que Novorich, arriba).

**2 productos excluidos por fotos falsas (no fotos reales):** "ICE STAR
HOODIE" y "NOT FOR EVERYONE HOODIE" tienen casi todas sus fotos con nombre
de archivo literal "ChatGPT_Image_..."/"ai-creation-..." -- imagenes
generadas por IA, no fotos de la prenda fisica. Confirmado bajando y
mirando las imagenes: Ice Star Hoodie tiene 8 fotos, 7 son IA y solo 1 es
real (foto real: hoodie colgado en un arbol, con imperfecciones reales que
las de IA no tienen); Not For Everyone Hoodie tiene 8 de 8 generadas por
IA, cero fotos reales. Como hoy el criterio de "oficial" es justamente
fotos reales, se dejaron afuera del catalogo -- decision explicita del
usuario, no cargarlas hasta que la tienda suba fotos reales. Los handles
excluidos (`excluir_handles` en `CLUB33`, `construir_catalogo_real.py`)
son `hoodie-ice-star` y `hoodie-navy-rey`.

**3 productos cargados, fotos 100% reales verificadas a mano:**

| Producto | Precio | Corte | Material/gramaje | Tallas disponibles hoy |
| --- | --- | --- | --- | --- |
| T-SHIRT "PACIFIC SUN" | $23.990 | boxy fit | Algodón 100%, 280 gsm | S, M, L, XL |
| T-SHIRT "LEMON PALETA" | $23.990 | boxy fit | Algodón 100%, 280 gsm | S, L, XL (M agotado) |
| HOODIE "C33" SS26. | $33.000 | boxy fit | Algodón 100%, 900 gsm | Solo XL |

**Descripcion real encontrada fuera del products.json:** el `body_html` de
los 5 productos viene vacio (la tienda nunca escribio nada ahi), pero la
pagina real de cada producto SI tiene una seccion de specs/descripcion
aparte (material, gramaje, calce, cuidado) que `products.json` no expone.
Se armo `descripcion_real` a mano por handle (`CLUB33_DESCRIPCION_REAL`,
`construir_catalogo_real.py`) citando literal ese texto real (WebFetch a
cada pagina de producto, 2026-08-27) -- nada inventado, solo ensamblado.

**Corte "boxy fit" verificado por texto, no por foto:** la propia ficha de
los 3 productos dice literal "Calce boxy fit medio" -- no fue necesario
desempatar por foto como en otros casos dudosos del catalogo.

**Capucha/cierre del hoodie:** "con capucha" (nombre dice "HOODIE" +
ficha real dice literal "Capucha amplia sin costura"). "Sin cierre"
confirmado por foto real de una persona usandolo (pullover con bolsillo
canguro, sin zipper) + la ficha describe "bolsillo tipo canguro frontal"
sin mencionar cierre en ningun lado.

**Envio real agregado a `data/envios_tiendas.json`:** RM 1 a 2 dias
habiles, regiones 3 a 5 dias habiles, envio gratis sobre $50.000
(Chilexpress/Starken). Sin pagina de politica de envio aparte (404) --
dato sacado del home/footer del sitio. Tienda registrada en
`data/tiendas.json` (`club-33`, `sin_sitio_web` -- mismo patron que las
demas, sin codigo de descuento real todavia) para que aparezca en
"Llegan rapido a ti" (verificado con `/api/tiendas_rapido?direccion=Santiago`:
aparece "RM: 1 a 2 dias habiles").

**Catalogo regenerado:** 661 productos en 18 tiendas (658 + 3 de Club 33).
29 productos con `oficial: true` en total (26 Novorich + 3 Club 33).
Verificado con `probar_buscador_real.py` sin errores y con
`formatear_producto()` real contra los 3 productos de Club 33 (fotos y
`oficial: true` llegan bien al JSON de respuesta).

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
