# Motor de recomendacion (buscador por formulario)


## Reglas de recomendación validadas

Detalle estructurado en `data/reglas_streetwear.json`.

**Alta confianza** (3-4 respuestas coincidiendo, salvo donde se indique):

| Género | Ocasión | Prenda | Recomendación |
| --- | --- | --- | --- |
| Hombre | Concierto/festival | Polera | Oversize, colores oscuros, marca streetwear reconocida o nicho valorado, tela transpirable |
| Hombre | Junta de amigos/skate park | Pantalón cargo | Baggy/suelto, cómodo para moverse, buen precio, buena caída hasta el tobillo |
| Mujer | Junta de amigos/skate park | Pantalón cargo | Baggy, cómodo, versátil, tiro bajo o cintura alta que estiliza |
| Mujer | Concierto/festival | Polera/top | Ajustado que favorezca la figura (5-6 respuestas). Si no hay stock ajustado, oversize/boxy como alternativa secundaria, no principal |

**Confianza media:** ninguna todavía. **Sin consenso:** ninguna todavía. Cuando lleguen más respuestas de validación, actualizar solo la regla puntual indicada — no tocar las ya confirmadas.

## Filtros del formulario — mapa rápido

| Prenda | Subtipo | Largo | Manga | Capucha / cierre | Corte |
| --- | --- | --- | --- | --- | --- |
| Polera, Camiseta | — | ✅ (no en Hombre) | Polera: ✅ larga/corta | — | tabla "superior" |
| Polerón | — | — | — | ✅ con/sin capucha · ✅ con/sin cierre | tabla "superior" |
| Camisa, Chaqueta, Chaleco | — | — | — | — | tabla "superior" |
| Top (no ofrecido a Hombre) | ✅ croptop/babytee/halter/corset/tanktop/blusa | ✅ (no en Hombre) | — | — | tabla "superior" |
| Pantalón | ✅ buzo/jeans/cargo | — | — | — | tabla "inferior" |
| Shorts | ✅ jeans/tela/cargo/baño | — | — | — | tabla "inferior" |
| Falda cargo, Bike shorts | — | — | — | — | tabla "inferior" |
| Gorro | — (flujo propio, ver sección Gorro) | — | — | — | no aplica, talla única |

Todos estos campos son independientes entre sí (una prenda puede ser oversize Y crop Y manga larga a la vez) y son filtros **estrictos que nunca se relajan** — la única excepción es el corte dentro de "Mostrar más opciones" (ver esa sección).

Nota de código: en `TIPOS_PRENDA_CONOCIDOS` (`app.py`) el orden de detección importa por colisión de palabras — "polera" antes que "top" (regla validada dice "polera/top") y "top" antes que "poleron" (el subtipo "crop hoodie" contiene la palabra "hoodie").

## Corte — criterios de tagueo manual

Usar cuando la ficha de una tienda no diga el corte explícitamente.

**Prenda superior** (polera, polerón, camisa, chaqueta, top): comparar polerón contra otros polerones, no contra poleras, por el grosor de la tela.

| Opción | Cómo identificarlo | Holgura aprox.* |
| --- | --- | --- |
| Slim fit | Se ciñe al cuerpo, marca la silueta, mangas ajustadas al brazo | 0-5cm |
| Regular fit | Calce normal, leve entalle en la cintura | 5-14cm |
| Straight | Cae recto de arriba a abajo, sin ningún entalle en la cintura | 5-14cm |
| Boxy fit | Ancho/cuadrado, hombros rectos, largo normal (no pasa mucho la cadera) | 14-20cm |
| Oversized | Hombros caídos, largo que pasa la cadera, mangas anchas | 20cm o más |

\* No exacto, varía por marca — apoyo solo cuando la ficha da medidas de holgura concretas.

**Prenda inferior** (pantalón, jeans, cargo, buzo, shorts, falda cargo, bike shorts): el cargo se evalúa igual que cualquier pantalón, los bolsillos grandes no cambian el criterio. Acá NO hay estándar en centímetros verificado — usar el mismo criterio proporcional (menos espacio = ajustado, más espacio = baggy).

| Opción | Cómo identificarlo |
| --- | --- |
| Skinny | Se ciñe a la pierna de principio a fin, mínimo espacio extra |
| Slim fit | Ajustado, con un poco más de espacio, sobre todo en el muslo |
| Straight fit | Caída recta, mismo ancho de muslo a tobillo |
| Baggy | Amplio en muslo y pierna, caída suelta hasta el tobillo |

**Definiciones cortas del formulario** (solo texto visible entre paréntesis, no afectan el filtro):
- Superior: Slim fit (se pega al cuerpo) · Regular fit (calce normal) · Straight (cae recto, sin marcar cintura) · Boxy fit (ancho y cuadrado) · Oversized (grande y holgado, hombros caídos)
- Inferior: Skinny (bien pegado a la pierna) · Slim fit (ajustado, con algo de espacio) · Straight fit (calce parejo) · Baggy (holgado en toda la pierna)
- Prendas nuevas de mujer: Crop top (abdomen a la vista) · Baby tee (corto y ajustado) · Top halter (sin mangas, amarrado al cuello) · Corset top (costuras marcadas) · Falda cargo (bolsillos grandes) · Bike shorts (tipo ciclista)

## Manga, capucha, cierre — criterios de tagueo

Normalmente SÍ vienen explícitos o se ven en fotos (a diferencia de corte/talla, que a veces hay que inferir). "Sin cierre" es sinónimo de "crewneck" en la mayoría de las tiendas; "sin capucha" casi siempre se llama "crewneck" o "cuello redondo". Si la ficha no lo menciona ni se ve en fotos, preguntarle al usuario (dueño del proyecto) antes de taguear a ciegas — acá no hay tabla de medidas de la cual inferir, a diferencia de corte/talla.

## Gorro

Tipo de prenda independiente, flujo propio: no usa corte/subtipo/largo/manga/capucha/cierre, y no se filtra por talla S/M/L/XL (talla única/ajustable).

1. **¿Qué tipo de gorro?** (única pregunta obligatoria) → filtra `forma`: curvo / plano / lana (beanie, sin visera).
2. **Color** — ya NO tiene pregunta propia (2026-08-28, pedido del usuario: "elimina la pregunta obligatoria de color en gorros, deja solo la que ya es opcional"). Reusa el mismo checkbox opcional de color que el resto de las prendas (`campo-color`, hasta 3) — para gorro, ese color se compara contra el campo estructurado `color_dominante` (más confiable que buscarlo en la descripción, ver `_color_producto()` en `motor_recomendacion.py`), en vez del texto libre que usan las demás prendas.

Se sacó por completo el camino "combinar con outfit" (sugerir color de gorro según si el outfit es oscuro/claro/colorido) que existía antes — era la pregunta obligatoria que se eliminó.

Tagueo: en gorros de dos tonos (tipo trucker), `color_dominante` = color del **panel frontal**, no toda la superficie.

**Fallback de forma sin resultados (2026-08-30, pedido del usuario):** si se pide una forma puntual (ej. plano) y el catalogo no tiene ningun gorro con esa forma, en vez de devolver 0 resultados se avisa ("No encontramos gorro plano, pero te mostramos otras formas de gorro disponibles.") y se muestran igual los gorros de las otras formas -- nunca se deja la busqueda vacia por esto. `filtrar_gorros_por_forma_con_aviso()` en `motor_recomendacion.py`, usada por `/api/recommend` (`app.py`); el aviso viaja en `aviso_gorro_forma` y se guarda/muestra igual que `sin_talla` (`static/comun.js`, `static/resultados.js`). No se toco el flujo de Koko (`servicio_koko.py` sigue usando `filtrar_gorros_por_forma()` sin el aviso).

## Talla — inferencia automática

Se cruza altura + peso (datos que el formulario ya pide, sin campo nuevo). Se calcula una talla según el peso y otra según la altura (tablas separadas); la **más chica** de las dos es la principal (para no ofrecer algo más ajustado de lo que corresponde), la otra queda como segunda opción. Si empatan, la segunda opción es la vecina más grande (o más chica si ya es XL). Cada resultado muestra TODAS las tallas coincidentes que tenga en stock (`tallas_coincidentes`). Si no calza en ninguna, se avisa en vez de dejar la página vacía sin explicación. Los gorros están exentos (talla única).

| Talla | Altura mujer | Peso mujer | Altura hombre | Peso hombre |
| --- | --- | --- | --- | --- |
| S | hasta 1.65m | hasta 60kg | hasta 1.70m | hasta 68kg |
| M | hasta 1.70m | hasta 70kg | hasta 1.78m | hasta 80kg |
| L | hasta 1.75m | hasta 80kg | hasta 1.85m | hasta 92kg |
| XL | más de 1.75m | más de 80kg | más de 1.85m | más de 92kg |

Rangos orientativos (la encuesta original se solapa entre tallas; para el cálculo se usan como topes fijos, no exactos).

## "Mostrar más opciones" — alternativas de corte y precio

Límite: el botón "Mostrar más opciones" se puede presionar como máximo **3 veces por búsqueda** (`static/resultados.js`, pedido del usuario 2026-08-28) — al tercer click, el botón desaparece.

Cuando ya no queda ningún producto que cumpla TODOS los filtros pedidos (incluido el corte específico, ej: "jeans baggy", o el precio máximo), el Plan B ya no deja la búsqueda vacía:
1. Completa primero con más productos del corte y precio exactos pedidos (todos los demás filtros intactos).
2. Si no alcanza a `CANTIDAD_RESULTADOS`, rellena el resto relajando **un requisito a la vez** — nunca el tipo de prenda (categoría) ni los demás filtros estrictos: color (a colores parecidos), **precio** (2026-08-28), y corte, en ese orden. Solo si ninguna de esas relajaciones por separado alcanza a llenar los cupos se combinan corte+color juntos, como último recurso.
3. La prioridad siempre es "misma prenda, otro corte o precio" antes que ofrecer un tipo de prenda distinto (pedido explícito del usuario, 2026-08-28) — por eso el tipo de prenda nunca se relaja en este mecanismo.

Estas alternativas nunca se mezclan en silencio con las que sí cumplen todo: van en un campo aparte (`alternativas` + `aviso_alternativas`), y el frontend (`static/resultados.js`) las pinta con un aviso destacado antes de las tarjetas (ej: `No encontramos más opciones en "boxy fit", pero esto también podría interesarte...`).

Ojo técnico (`buscar_plan_b` en `motor_recomendacion.py`): hay que sacar los productos ya mostrados del catálogo **antes** de llamar `elegir_candidatos(permitir_otros_cortes=True)`, no filtrarlos después — si no, la función ve que "todavía existen" productos del corte pedido (los ya mostrados) y nunca relaja nada. Para poder relajar precio, `/api/recommend` (`app.py`) ya NO filtra el catálogo por precio antes de llamar a `buscar_plan_b` (a diferencia de la búsqueda normal, que sigue filtrando estricto) — `buscar_plan_b` recibe el catálogo completo y aplica el precio internamente (`catalog_precio`), guardando también el catálogo sin filtrar para la etapa que lo relaja.

### "Relajar por esta vez" — preferencias negativas del perfil bloqueando resultados (2026-08-30)

Si el usuario tiene preferencias negativas activas en su perfil (`excluir_rotos`/`excluir_grafico_grande`/`excluir_texto_grande`/etc., ver `filtrar_por_preferencias_negativas` en `motor_recomendacion.py`) y una búsqueda queda en 0 resultados (recomendaciones **y** alternativas), `/api/recommend` (`app.py`) prueba apagando cada preferencia activa de a una (reusando el mismo filtro) para detectar cuál es la que realmente está bloqueando, y la devuelve en `preferencias_bloqueantes`. El frontend (`static/resultados.js`, función compartida `crearCajaRelajarPrefs`) muestra una caja "tienes marcado que no te gustan X — ¿buscamos igual solo por esta vez?"; si el usuario confirma, se reenvía la misma búsqueda agregando `relajar_preferencias_negativas` (nunca se toca el checkbox guardado en el perfil).

Este mismo aviso aparece también la **primera vez que "Mostrar más opciones" (Plan B) da 0 resultados nuevos** por esta causa (pedido del usuario, 2026-08-30) — antes solo se ofrecía en la búsqueda inicial, así que si una preferencia bloqueaba justo el Plan B, el usuario solo veía "No encontramos nada más." sin poder hacer nada. La detección de `preferencias_bloqueantes` en `app.py` ya era agnóstica de `plan_b` (prueba con `buscar_plan_b` cuando corresponde); lo que faltaba era mostrar la caja también en `buscarTanda()`, no solo en la carga inicial de la página.

### Exclusiones duras por ocasión (mujer y hombre) — carrete/universidad/junta social/concierto (2026-08-30, extendido a hombre 2026-08-31)

`EXCLUSIONES_OCASION_GENERO` + `GRUPOS_OCASION` (`constantes.py`), aplicado en `elegir_candidatos()` (`motor_recomendacion.py`) para **ambos géneros** — a diferencia de `EXCLUSIONES_HOBBY` (que solo reordena vía `nivel_hobby`), esto SÍ saca la prenda del pool de candidatos, nunca solo la reordena (pedido explícito del usuario). `GRUPOS_OCASION` normaliza sinónimos de texto libre a una clave canónica (`carrete`, `universidad`, `social_casera` = junta social/junta familiar/junta de amigas/comida familiar/asado, `concierto_festival`) antes de buscar en `EXCLUSIONES_OCASION_GENERO`:

- **Carrete:** excluye poleron con capucha, chaleco, categoría completa "conjunto" (2026-09-02: los 8 productos actuales de esa categoría son sets tipo tracksuit/buzo). Pantalón usa la regla estricta `solo_confirmados` (ver abajo), NO la de subtipo/palabras_clave.
- **Universidad:** excluye chaqueta subtipo cuero.
- **Social/casera (junta social, junta familiar, junta de amigas, comida familiar, asado):** excluye pantalón subtipo buzo o con "buzo"/"jogger"/"sweatpant"/"sweat pant" en su nombre/descripción/tags real.
- **Concierto/festival:** excluye pantalón subtipo buzo o con esas mismas palabras clave.

Cada regla usa solo atributos que YA existen en el catálogo (categoría/subtipo/capucha/texto del producto) — "calzas" (carrete), "deportiva"/"casero"/"chill" (social/concierto) y "brillo"/"tachas" (boost de concierto) se omitieron a propósito porque el catálogo no tiene esos atributos tageados, no se inventaron.

**Bug real corregido (2026-09-02):** un pantalón de AbsolutelyWrong ("PANTALON BASICO HEAVYWEIGHT") apareció en una búsqueda de carrete pese a ser un buzo/sweatpant — la causa real: `subtipo` está vacío en 84 de los 144 pantalones del catálogo real (solo 7 tienen `subtipo == "buzo"` tageado), así que la regla original nunca los agarraba, aunque el filtro en sí (`elegir_candidatos()`, un único punto central que todo — búsqueda normal, Plan B, alternativas de corte/color/precio — atraviesa) sí se aplicaba correctamente y en el orden correcto (no era un bug de "orden" ni de fallback reintroduciendo productos). Primer fix: cada regla de pantalón/buzo acepta también `"palabras_clave"` (`_prenda_excluida_por_ocasion()` en `motor_recomendacion.py`), que busca esas palabras en el texto real del producto — mismo mecanismo (`_contiene_palabra` + `texto_producto()`) que ya usa el filtro de corte. Pero el producto reportado no tiene `subtipo` NI esas palabras en su texto real (la tienda no trae descripción propia) — seguía colándose.

**Regla `solo_confirmados` (2026-09-02, pedido explícito del usuario: "buzo nunca puede aparecer... ni en ninguna tanda de más opciones"):** para pantalón en carrete se invirtió la lógica — en vez de excluir lo confirmado como buzo, solo se **permiten** pantalones confirmados como jean o cargo (`subtipo` tageado, o esas palabras en el texto real, reusando `SUBTIPOS_CONOCIDOS["jeans"]`/`["cargo"]`, ver `_prenda_confirmada_segura()`). Cualquier pantalón sin forma de confirmar que NO es buzo queda fuera, incluido el caso reportado. Trade-off elegido explícitamente por el usuario (con la alternativa más laxa presentada y descartada): en carrete solo aparecen 53 de los 144 pantalones del catálogo (los 91 sin `subtipo` ni palabra confirmada, aunque muchos sean legítimamente jean/cargo, quedan ocultos por seguridad) — a cambio, garantía real de que nunca aparece un buzo, verificado también en Plan B/alternativas. `universidad`/`social_casera`/`concierto_festival` NO se tocaron, el usuario pidió esto puntual para carrete.

**2 bugs más corregidos (2026-09-03), mismo hilo:**
1. **El `subtipo` tageado no es garantía absoluta:** "Jogger Cargo UNK." (subtipo `"cargo"`, correcto) y "Pantalón Buzo Nike Cargo" (subtipo `"cargo"` también) seguían apareciendo en carrete porque `solo_confirmados` confiaba en el subtipo sin mirar si el nombre real decía "jogger"/"buzo". Fix: `"palabras_prohibidas"` en `solo_confirmados` (`_prenda_confirmada_segura()`) — si el texto real dice "buzo"/"jogger"/"sweatpant", queda excluido SIN IMPORTAR el subtipo tageado.
2. **Género "unisex" saltaba la exclusión entera:** la condición original solo aplicaba las exclusiones por ocasión si `genero` era `"mujer"` u `"hombre"` — pero el formulario "regalo" permite elegir "Unisex / No estoy segura/o", y con ese valor NINGUNA exclusión de ocasión se aplicaba (joggers, buzos, conjuntos, hoodies con capucha, todo pasaba). Como `EXCLUSIONES_OCASION_GENERO` es la misma lista para cualquier género desde el 2026-08-31, se sacó la condición: ahora se aplica siempre, sin importar el género de quien busca (o si no viene ninguno).

### Prioridad suave de subtipo por ocasión: jeans/cargo/jorts (2026-08-31)

`PRIORIDAD_SUBTIPO_OCASION` (`constantes.py`), reordena `puntaje()` en `elegir_candidatos()` — mismo mecanismo que `CORTE_ANCHO_PRIORIDAD_PANTALON` abajo, nunca excluye otro subtipo, solo lo deja más abajo en el orden. Reusa `GRUPOS_OCASION` para los sinónimos:

- **Pantalón + carrete:** prioriza subtipo jeans.
- **Pantalón + universidad / social-casera (junta social, junta familiar, junta de amigas, comida familiar, asado):** prioriza subtipo cargo.
- **Shorts + carrete:** prioriza subtipo jorts.

### Corte más ancho por defecto: pantalón/buzo en deporte o junta social (2026-08-28)

Pedido del usuario: para pantalón/buzo, en ocasión "deporte" o "junta social", si la persona no pidió un corte específico, priorizar el corte más ancho/baggy disponible usando el campo `corte` ya tageado (nunca releyendo fotos). Es una prioridad **suave** (mismo mecanismo que `priorizar_material_natural`/`categorias_deprioritizadas`: reordena el `puntaje()` de `elegir_candidatos`, nunca filtra) — si no hay nada baggy en stock, igual se muestra lo que haya, solo más abajo en el orden. `CORTE_ANCHO_PRIORIDAD_PANTALON` en `motor_recomendacion.py`: baggy > straight fit > slim fit > skinny. "Deporte" no es una ocasión del dropdown (fuera de alcance salvo pedido explícito, ver `CLAUDE.md`) — esta regla solo aplica si llega como texto libre ("Otro") o vía Koko.

## Material del producto y "Priorizar materiales de calidad" (2026-08-19)

Filtro opcional, transversal a cualquier usuario -- explícitamente NO ligado a hobbies ni estilo (a diferencia de `REGLAS_HOBBY`, ver arriba). Checkbox al final de los formularios de búsqueda "yo" y "regalo" (`#prioridad-material-yo`/`#prioridad-material-regalo`, `.checkbox-inline` reusado standalone).

- **`MATERIALES_CONOCIDOS`** (`app.py`): 7 materiales -- 3 "naturales" (Algodón 100%, Lana, Cuero) y 4 no ("Mezcla algodón/poliéster", Poliéster, Nylon, Acrílico). El catálogo **real** todavía no trae este dato (se le pedirá a cada tienda más adelante, nunca se inventa para un producto real) -- `formatear_producto()` simplemente no muestra la fila de material si el producto no la tiene.
- **Solo prioriza, nunca oculta:** `elegir_candidatos()` suma un parámetro opcional `priorizar_material_natural` (default `False`, sin efecto en ningún llamador existente) que cambia el `puntaje()` final de un entero a una tupla de 3 niveles `(es_natural, es_algodon_buena_calidad, puntaje_palabras)` (el 2do nivel se agregó 2026-08-19, ver sección de gramaje abajo) -- los productos de fibra natural quedan primero en el orden, y dentro de esos, el algodón de buen gramaje queda antes que el resto; los sintéticos siguen ahí, nunca se filtran fuera. Threaded a través de `armar_resultados()`/`buscar_plan_b()`/`_completar_con_alternativas_de_corte()` hasta `/api/recommend` (nuevo campo `priorizar_material_natural`, booleano simple).
- **Se muestra en la ficha (vista previa rápida):** `formatear_producto()` agrega `"material"` (la etiqueta legible, ej. "Algodón 100%") a cada resultado; `_vista_previa.html`/`comun.js` pintan una fila `Material: ...` en el modal, oculta si el producto no trae material.
- **Datos del catálogo mock** (`agregar_materiales.py`, aditivo -- **a propósito no se re-corrió `generar_catalogo_prueba.py` completo**, mismo motivo que `agregar_subtipos_chaqueta.py`: reordenaría el generador de números aleatorios compartido y cambiaría precios/tallas/colores de TODO el catálogo sin necesidad real): los 790 productos existentes quedaron exactamente iguales salvo por el campo nuevo (verificado). 2 asignaciones **lógicas** reusando datos que ya existían (nunca al azar cuando hay una pista real): gorro con `forma == "lana"` → material `"lana"`; chaqueta con `subtipo == "cuero"` → material `"cuero"`. El resto (la inmensa mayoría) recibe un material al azar (semilla fija, reproducible) con pesos que imitan una distribución real -- algodón/mezclas más comunes que lana/cuero.
- **No se agregó al chat de Koko todavía** (ni al tool schema `KOKO_TOOL_SUGERIR_BUSQUEDA` ni al prompt) -- el pedido del usuario fue específicamente "un filtro opcional en el buscador", sin mencionar a Koko. Si se quiere que Koko también lo active (ej. si el usuario dice "algo de buena calidad"), es una extensión futura, no la de hoy.

### Gramaje (GSM) del algodón -- refina la priorización (2026-08-19)

Pedido del usuario: "para prendas de algodón, agrega el dato de gramaje (GSM)... considera 180 GSM o más como 'buena calidad' para poleras/camisetas de algodón". A propósito **acotado solo a polera/camiseta** -- un umbral de "buena calidad" en GSM para otras prendas (chaqueta, pantalón, etc.) no está definido, y no se inventó uno.

- **`GRAMAJE_MINIMO_CALIDAD_GSM = 180`**, **`_algodon_buena_calidad(producto)`** (`app.py`): `True` solo si `categoria` es polera/camiseta, `material == "algodon_100"`, y `gramaje_gsm >= 180`. Sin el dato cargado (la mayoría del catálogo real, hasta que cada tienda lo mande), o fuera de esas 2 categorías, siempre `False` -- nunca asume.
- **`_texto_gramaje(producto)`**: arma el texto de la ficha, ej. `"220 GSM — algodón grueso de calidad"` (o "algodón liviano" si es menor a 180) -- vacío si no hay gramaje cargado. Se muestra en `_vista_previa.html`/`comun.js` (`#vp-gramaje`), oculto si no aplica.
- **Datos del catálogo mock** (`agregar_gramaje.py`, aditivo, corre después de `agregar_materiales.py`): de las 20 poleras/camisetas de algodón 100% que hay, la mitad quedó arriba de 180 GSM y la mitad abajo (semilla fija), para poder ver los 2 casos.

## "Marca de autor" / diseño independiente (2026-08-19)

Insignia + filtro para destacar tiendas/productos con identidad de diseño propia (no genérico ni fast fashion) -- parte central de la propuesta de KOLIZION ("dar visibilidad a marcas independientes"). A diferencia de "Priorizar materiales de calidad" (nunca oculta, solo reordena), **este filtro SÍ es estricto**: el usuario pide explícitamente "mostrar SOLO".

- **`producto["marca_autor"]`** (booleano, campo del catálogo -- decisión: a nivel de **producto**, no de tienda, porque es lo que de verdad se busca/muestra en `catalog.json`; el sistema de tiendas reales (`data/tiendas.json`) es un sistema aparte sin catálogo propio, ver "Tiendas reales y tracking"). **Para catálogo real, este dato NO depende de que la tienda lo declare** -- lo define KOLIZION mismo al cargar cada tienda piloto, según si tiene identidad de diseño propia o no (pedido explícito del usuario, para evitar auto-declaraciones infladas).
- **`filtrar_por_marca_autor(catalog, solo_marca_autor)`** (`app.py`): filtro estricto de catálogo, mismo lugar/patrón que `filtrar_por_precio()` (se aplica temprano en `/api/recommend`, antes de `elegir_candidatos`) -- si `solo_marca_autor` es `True`, oculta todo lo que no esté marcado. Nuevo campo `solo_marca_autor` (booleano) en `/api/recommend`.
- **Insignia visible en 3 lugares** (`formatear_producto()` agrega `"marca_autor"` a cada resultado, así que aparece en cualquier listado sin trabajo extra): tarjetas de `/resultados` (`comun.js`), tarjetas de `/vitrina` (`vitrina.js`), y la ficha/vista previa (`_vista_previa.html`, `#vp-marca-autor`) -- mismo texto "✦ Marca de autor" en los 3, clase `.insignia-marca-autor` (borde/texto color de marca, sin relleno, para no competir visualmente con la insignia roja de oferta).
- **Datos del catálogo mock** (`agregar_marca_autor.py`, aditivo): ~30% de los 790 productos marcados al azar (semilla fija) -- variado a propósito para poder ver la insignia funcionando sin que sea rarísima ni la mayoría.
- **No se agregó a Koko** (mismo criterio que el filtro de material arriba) -- pedido específico del buscador, no del chat.

## Volver atrás sin perder los filtros

Si el navegador restaura `/` desde su caché (bfcache), el estado del formulario queda intacto solo. Si el navegador SÍ recarga la página de cero al volver atrás (`performance.getEntriesByType("navigation")[0].type === "back_forward"`) y hay una búsqueda guardada (`sessionStorage.ultimoPayload`), `static/script.js` salta directo a la sección de filtros ya llena (función `restaurarFiltros()`) en vez de reiniciar el formulario.

Casos particulares: un valor que no calza con ninguna opción del select (era texto libre en "Otro") selecciona "Otro" y rellena ese input; un valor vacío (era "Me da igual") deja esa opción si existe. El link "← Hacer una nueva búsqueda" es navegación normal — no dispara esto, a propósito deja el formulario limpio.

**Atajo directo "Cambiar requisitos de búsqueda" (2026-08-22):** además del botón atrás, `/resultados` tiene un botón visible arriba (`#btn-cambiar-filtros`, `templates/resultados.html` + `static/resultados.js`) que manda a `/?volver_filtros=1` -- `script.js` detecta ese parámetro (mismo lugar donde se detecta `editar_perfil`, con la misma prioridad) y llama a `restaurarFiltros()` con el `sessionStorage.ultimoPayload` de siempre, sin depender de que el navegador reporte `back_forward` (que no siempre pasa, ej. si el usuario abre `/resultados` en una pestaña nueva o el bfcache no aplica). Limpia el parámetro de la URL después (`history.replaceState`), mismo patrón que `editar_perfil`.

**Botón "Limpiar filtros" (2026-08-22):** en las 2 pantallas de filtros (`seccion-busqueda-yo`/`seccion-busqueda-regalo`), junto al link "Volver" -- para el caso en que el usuario llegó con valores guardados (por cualquiera de los 2 caminos de arriba) y quiere partir de cero. `limpiarFiltros(prefix)` (`script.js`) llama a `form.reset()` y despues dispara "change" a mano en categoría/corte/ocasión -- `reset()` solo limpia valores, no dispara eventos, así que sin esto los campos dependientes (tipo de prenda, subtipo, largo, manga, capucha, cierre, y los campos "otro") se quedarían con las opciones/visibilidad de antes de limpiar.

## BUG GRAVE encontrado y corregido (2026-08-22) -- casi todos los selects filtraban sin que el usuario lo pidiera

Encontrado probando "Cambiar requisitos de búsqueda" con clicks reales (no un caso aislado): un `<select>` que el usuario nunca toca queda en su PRIMERA opción, no en ninguna "sin preferencia". Casi todas las listas de opciones (`TIPO_PRENDA_OPCIONES`, `CORTE_OPCIONES`, `SUBTIPO_OPCIONES`, `LARGO_OPCIONES_LISTA`, `MANGA_OPCIONES`, `CAPUCHA_OPCIONES`, `CIERRE_OPCIONES` en `script.js`, más los `<select>` estáticos de ocasión y precio en `index.html`) tenían la opción neutra ("Me da igual"/"Cualquiera"/"Cualquier precio") al FINAL de la lista -- así que un usuario que, por ejemplo, elegía "Prenda superior" y no tocaba "¿Qué prenda buscas?" terminaba buscando literalmente "Polera" (la primera opción real), no "cualquier prenda superior". Mismo problema encadenado en corte, subtipo, largo, manga, capucha, cierre, ocasión y precio -- probablemente la causa de varios "no encontramos nada" que parecían huecos del catálogo y en realidad eran filtros que nadie pidió.

**Arreglo:** se reordenaron las listas para que la opción neutra vaya PRIMERO (`"Otro"` sigue al final -- no es neutro, es un camino aparte de texto libre). Esto no cambia ningún `value` ni la lógica de detección (`valorFinal()`, `detectar_*_pedido()` siguen comparando por el mismo string, no por posición) -- solo el orden en que se listan, así que no había código que dependiera de la posición (verificado con grep, el único acceso por índice es `opcion[0]` para sacar el texto de una tupla `[texto, definición]`, no una posición del array).

**Efecto secundario encontrado y corregido de paso:** `precio-yo`/`precio-regalo` tenían el atributo `required` -- inofensivo mientras el default fuera un precio real, pero al mover "Cualquier precio" (value `""`) al frente, el navegador bloqueaba el envío del formulario entero (`required` rechaza un value vacío) sin ningún error visible en consola. Se sacó `required` de esos 2 selects -- un value vacío ahí es una respuesta válida ("no filtrar por precio"), no un campo sin completar. Verificado con `form.checkValidity()` antes y después del fix.

Probado de punta a punta con el servidor real corriendo (no solo `probar_reglas.py`): "Prenda superior" + "Poleron" sin tocar nada más ahora trae resultados reales (antes: 0, por quedar atrapado en "Polera" en vez de "cualquier prenda superior" cuando corresponde, o en combinaciones estrictas como corte+cierre que nadie pidió).

## Hobbies del perfil y tendencia de estilo (2026-08-18)

Pedido del usuario: ampliar "Hobbie" en el perfil (`index.html`) -- antes era un campo de **texto libre** (nunca fue una lista fija de 3 opciones, aunque así se recordaba) que apenas se usaba para recomendar (solo se sumaba como texto suelto a la búsqueda). Ahora es un grupo de **checkboxes** (se puede elegir más de uno, mismo patrón visual que los colores de gorro -- `.campo-checkboxes`/`.grid-checkboxes`/`.checkbox-inline`, ya existían): Música, Deportes, Relajo/lifestyle tranquilo, Arte y cultura, Gaming, Películas y series. Si se marca "Música", se despliega un segundo grupo de géneros (Rock, Reguetón/urbano, Pop, Hip-hop/rap, Electrónica, Indie/alternativo) -- `#hobbie-musica` dispara el toggle de `#campo-hobbie-musica-genero` (`script.js`).

- **Dato guardado:** `perfil.hobbie` pasa a ser un **array** (antes string) y se suma `perfil.hobbie_musica_genero` (array, solo relevante si `"musica"` está en `hobbie`). `precargarPerfil()` ya no puede usar el loop genérico de `campo.value = ...` para estos 2 campos (son checkboxes, no inputs de texto) -- los salta explícitamente y los marca aparte, mismo patrón que ya existía para `gorro_colores`. El envío del formulario tampoco puede confiar en `Object.fromEntries(new FormData(...))` (se queda solo con el ÚLTIMO checkbox marcado de cada "name" repetido) -- se recolectan aparte con `querySelectorAll(...):checked`.
- **`/perfil` muestra etiquetas legibles**, no los códigos internos (`musica` → "Música", con los géneros/deportes entre paréntesis si aplica) -- `ETIQUETAS_HOBBIE`/`ETIQUETAS_GENERO_MUSICAL`/`ETIQUETAS_DEPORTE` en `perfil.js`, mismo texto que las listas de `app.py` (duplicado a propósito: uno es para el prompt de Koko en el servidor, el otro para pintar HTML en el navegador, no vale la pena compartir código por esto).
- **Compatibilidad con perfiles guardados antes de este cambio:** si `perfil.hobbie` todavía es un string (formato viejo), `_lista_texto_segura()` lo trata como lista vacía (no revienta, simplemente no aporta ninguna señal) -- probado explícitamente.

### Rediseño 2026-08-19: las asociaciones hobby→estilo se validan una por una, no se inventan

La primera versión (2026-08-18, arriba) tenía `"vibra"`/`"corte_sugerido"` **inventados por Claude** para cada hobby (deportes → athleisure, gaming → oversize, etc.), sin que el usuario los validara. El usuario frenó esto explícitamente: *"no quiero que inventes asociaciones sin que yo las valide primero... recuerda el patrón que seguimos con las reglas de ocasión: primero definir el criterio con casos reales, después programarlo"*. Se sacaron `"vibra"`/`"corte_sugerido"` de `HOBBIES_CONOCIDOS`/`GENEROS_MUSICALES_CONOCIDOS` -- esas 2 listas (+ `DEPORTES_CONOCIDOS`, nueva) ahora son **solo taxonomía** (qué opciones existen en el selector), sin ninguna asociación de estilo.

- **`REGLAS_HOBBY`** (`app.py`): diccionario aparte, con las asociaciones **ya validadas**, una por una -- hoy solo `("musica", "rock")`. Formato pensado para sumar hobbies después sin cambiar la forma:
  - `"prenda_preferida"`: set de `tipo_prenda` a los que aplica (nunca se aplica a otra prenda).
  - `"corte"`: el único campo que de verdad mueve una búsqueda (valor real de `CORTES_CONOCIDOS`). Default SOLO si el usuario no eligió un corte propio -- nunca lo reemplaza (mismo mecanismo de corte de siempre, no un filtro nuevo).
  - `"color_base"`/`"nota"`: el catálogo no tiene color/estampado por prenda (fuera de gorro/chaqueta) -- solo para que Koko converse con criterio, nunca para filtrar.
  - `"confianza": "validacion_inicial"` -- tal como lo aclaró el usuario (referencias visuales, no encuesta a muchas personas). Koko debe tratarlo como default razonable, y **siempre prioriza lo que el usuario diga explícitamente en el chat por sobre la regla**.
  - Regla actual: **Música: Rock** → prenda preferida polera/poleron, corte oversize, color predominantemente oscuro (negro, gris) dejando el gráfico como protagonista, nota: gráfico grande tipo banda/concierto (no minimalista), combinar con pantalón suelto/baggy abajo.
- **`_reglas_hobby_usuario(hobbies, generos_musicales, deportes_subtipo)`**: las reglas validadas que aplican a este perfil. **(2026-08-20: ya NO se usan para fijar un corte por defecto en `/api/recommend` -- ver el rediseño más abajo, esto quedó solo como sugerencia conversacional para Koko.)**
- **Lección de prompt-engineering (2026-08-19, sigue vigente):** decirle a Koko "esta regla aplica si el hobby es rock" **no bastaba** -- el modelo la trataba como una tabla de referencia genérica y hasta preguntaba "¿qué estilo de música te gusta?" a un usuario que YA tenía "rock" en su perfil. Probado en aislado (prompt mínimo, sin las demás instrucciones compitiendo) para confirmar que el problema era la redacción, no el largo del prompt. **Arreglo:** `_bloque_hobbies_para_prompt()` abre con un hecho ya conocido en primera persona ("este usuario eligió en su perfil que le gusta...") en vez de una regla condicional abstracta -- este patrón de redacción se mantuvo en el rediseño de abajo, solo cambió de "esto ya es un hecho, no lo preguntes" a "esto es una idea opcional, mencionala pero preguntá igual".
- **Deportes ahora tiene sub-opciones** (`DEPORTES_CONOCIDOS`: Gym, Fútbol, Baseball, Ski -- Baseball/Ski agregados a pedido del usuario 2026-08-19), mismo patrón que música: `#hobbie-deportes` despliega `#campo-hobbie-deportes-subtipo`, guardado en `perfil.hobbie_deportes_subtipo` (array). `SUBGRUPOS_HOBBIE` (`script.js`) generaliza el toggle/precarga/recolección para música Y deportes en un solo loop, para no duplicar la lógica cuando se sume un tercer sub-grupo.
- **Nota sobre la lista de hobbies:** el usuario pidió eliminar "ciclismo, lectura, cocina, fotografía" -- esos 4 **nunca estuvieron** en la lista real (`HOBBIES_CONOCIDOS`), así que no había nada que sacar; se le avisó explícitamente para no dejar pasar la confusión en silencio.
- **Propuesta de reglas para otros hobbies:** pendiente de validación del usuario (no implementada) -- gym, fútbol, baseball, ski, gaming, arte y cultura, relajo, películas/series, y los géneros musicales reggaetón/pop/hip-hop/electrónica/indie. Se le presentó una tabla propuesta en el chat; recién se agregan a `REGLAS_HOBBY` una por una cuando el usuario las confirme o ajuste.

### Rediseño 2026-08-20: de "regla positiva forzada" a "exclusión suave de sentido común"

Cambio de enfoque explícito del usuario, un día después del rediseño de arriba: en vez de que cada hobby tenga una regla positiva de qué mostrar (que termina imponiendo un único estilo "correcto"), el hobby ahora solo ayuda a **descartar categorías que claramente no calzan** -- nunca fuerza una recomendación. La base de la búsqueda sigue siendo corte/ocasión/color de siempre; el hobby es "un filtro adicional suave" (palabras del usuario), no una autoridad.

- **`EXCLUSIONES_HOBBY`** (`app.py`): hobby (o `(hobby, sub-opción)` para música/deportes) → set de `tipo_prenda` a deprioritizar. Hoy:
  - `("arte_cultura", None)` → `{"bikeshorts"}`.
  - `("deportes", "gym")` → `{"camisa"}`.
  - `"gaming"` **no tiene entrada** -- pedido explícito del usuario ("sin exclusiones fuertes evidentes, se mantiene el catálogo general").
- **Limitación honesta, documentada en el código:** el catálogo (mock, y probablemente el real también) no tiene categorías de "ropa técnica-deportiva" (mallas de compresión, running de alto rendimiento) ni "ropa formal/de vestir" como tales -- se usó la categoría real **más parecida** como proxy: `bikeshorts` ("ajustados, tipo ciclista") para lo primero, `camisa` (la prenda más formal-codificada del catálogo, la que ya se usaba para contextos semiformales en conversaciones reales de Koko) para lo segundo. Si el catálogo real algún día trae más variedad de categorías, esto se puede afinar.
- **`_categorias_deprioritizadas_por_hobby(hobbies, generos_musicales, deportes_subtipo)`**: junta las exclusiones de todos los hobbies del perfil en un solo set.
- **Mecanismo -- reusa el patrón de `priorizar_material_natural`, NUNCA oculta:** `elegir_candidatos()` suma `categorias_deprioritizadas` (set, default `None`) como el **primer** nivel del `puntaje()` (más fuerte que material: "no calza con tu hobby" es sentido común, no una preferencia de gusto) -- los productos de esas categorías quedan al final del orden, pero si el usuario pide esa categoría directamente (ej. "bikeshorts" explícito), el filtro estricto de tipo de prenda ya los dejó como único candidato posible, así que igual aparecen. Threaded por los mismos 3 lugares que material (`armar_resultados()`/`buscar_plan_b()`/`_completar_con_alternativas_de_corte()`).
- **Automático en `/api/recommend` (modo "yo"), sin checkbox nuevo:** a diferencia de "priorizar materiales" (el usuario lo prende a mano), la exclusión por hobby se calcula sola a partir del perfil en cada búsqueda -- es una corrección de sentido común, no una preferencia que haya que activar.
- **`REGLAS_HOBBY` (la regla de Música: Rock) queda como sugerencia OPCIONAL, ya NO fuerza nada:** se sacó por completo la línea que sustituía el `corte` en `/api/recommend` (`if not detectar_corte_pedido(corte) and regla_hobby: corte = regla_hobby["corte"]`) -- una búsqueda por formulario o por Koko con hobby "rock" ahora se comporta exactamente igual que sin ese hobby. En el prompt de Koko, `_bloque_hobbies_para_prompt()` se reescribió de "esto ya es un hecho, no lo preguntes" a "esto es una idea opcional, podés mencionarla pero preguntá igual el corte real, y siempre priorizá lo que el usuario diga". Verificado con `diagnostico_hobbies_estilo.py` (API real): con perfil música+rock, Koko pide un poleron y **sigue preguntando** ajuste/capucha/presupuesto con normalidad, mencionando la idea del rock como un plus ("Como sé que te gusta el rock, una idea es ir por algo oversize... Pero decime qué onda buscas vos"), nunca como una sugerencia ya decidida.

### Refuerzo positivo: Deportes → Gym (2026-08-23)

Pedido explícito del usuario: sumar una sugerencia POSITIVA para Koko sobre "Gym" además de la exclusión que ya existía (`("deportes","gym") → {"camisa"}`, sin cambios) — "una sugerencia dentro de lo que ya se muestra", nunca un filtro nuevo ni un reemplazo de la exclusión.

- **`REGLAS_HOBBY` cambió de forma (2026-08-23):** cada entrada ahora es una **lista** de sugerencias en vez de un único dict — un mismo hobby puede sugerir cortes distintos según la prenda (Gym sugiere algo distinto para pantalón que para polerón). `("musica","rock")` se envolvió en una lista de 1 elemento por consistencia, sin cambiar su contenido ni su comportamiento. `_reglas_hobby_usuario()` ahora usa `.extend()` en vez de `.append()` para aplanar esas listas.
- **4 sugerencias nuevas para `("deportes","gym")`:**
  - Pantalón → corte baggy, con detalle de línea lateral (estilo jogger deportivo).
  - Polerón → corte boxy fit, con diseño/estampado propio (no liso básico).
  - Shorts → corte baggy, anchos y sueltos — nota explícita de que "ajustado/compresión" sigue excluido, esta sugerencia no lo contradice.
  - Gorro → tipo `"accesorio"` (campo nuevo `tipo_sugerencia`), sin corte de por medio: sugiere mencionarlo como complemento frecuente, nunca como la prenda principal.
- **`tipo_sugerencia: "accesorio"` (campo nuevo):** para sugerencias sin corte real (como la de gorro). `_bloque_hobbies_para_prompt()` las renderiza distinto (sin inventar un corte que no aplica) — todo lo demás (`corte`/`color_base`/etc.) sigue igual para las sugerencias normales.
- **Marcas de referencia (Nike/Adidas):** el pedido fue "si el catálogo las tiene" — hoy el catálogo (622 productos, 14 tiendas) es 100% marcas chicas independientes, **cero productos Nike/Adidas** (verificado). El texto del prompt se lo dice explícitamente a Koko: puede nombrarlas como referencia de estética, pero nunca prometer que el catálogo real las tiene si no están.
- Sigue siendo solo conversacional (Koko), igual que el resto de `REGLAS_HOBBY` desde el rediseño de arriba — no cambia el resultado de una búsqueda por formulario ni por `/api/recommend`.
- Verificado sin API (carga del módulo + `_reglas_hobby_usuario`/`_bloque_hobbies_para_prompt` con perfil deportes+gym) y con `probar_reglas.py`/`probar_buscador_real.py`. No se corrió `diagnostico_hobbies_estilo.py` completo (API real, con costo) para esto -- solo se validó que sigue cargando y que la regla de rock no se rompió.

## Tags de interes por producto (musica/arte) como señal de ranking (2026-08-30)

Distinto de `REGLAS_HOBBY`/`EXCLUSIONES_HOBBY` (arriba, a nivel categoria): esto es un tag a nivel **producto individual**, `interes_musica`/`interes_arte` (booleano), agregado en `construir_producto()` (`construir_catalogo_real.py`) solo cuando la ficha real de la tienda lo dice explicito -- primer uso real, WAV (ver `docs/catalogo_real.md`). No es una restriccion ni un filtro nuevo: el tag se suma al campo `tags` del producto, que ya entra al texto que `elegir_candidatos()` compara contra el pedido (`texto_producto()`), y `app.py` ya mete los hobbies del perfil (incluida la palabra literal `"musica"`) en ese texto de busqueda -- asi que un usuario con "Música" en sus gustos le da una ventaja de ranking real a esos productos, reusando el mecanismo de coincidencia de palabras ya existente en vez de crear un sistema de prioridad aparte. Reutilizable para cualquier tienda futura sin tocar nada mas.

## Camisa: carrete (lino/algodón, casual) vs universidad (más formal) (2026-09-03)

Pedido explícito del usuario: no tratar toda "camisa" como una sola categoría pareja entre ocasiones -- una camisa de carrete es de lino o algodón (casual), una para ir a la u generalmente es más formal.

- El catálogo real no tiene un campo "formal"/"casual" para camisa (ni subtipo tageado -- las 2 camisas reales de hoy tienen `subtipo: null`). En vez de inventar ese dato o adivinar por material (lino/algodón tampoco garantiza informalidad por sí solo), se reusó el mecanismo `solo_confirmados` que ya existía para pantalón+carrete (ver arriba): **universidad** solo admite una camisa si su nombre/descripción real la declara formal (`"vestir"`, `"formal"`, `"oxford"`, `"popelina"`) -- `EXCLUSIONES_OCASION_GENERO["universidad"]` en `constantes.py`.
- Con el catálogo actual (2 camisas: "Camisa Moon Ritual" de Doslobos -- flanela oversize con capucha, sin material declarado; "Camisa de Algodón 90%" de ZAMU -- descrita literal como "ideal para looks casuales y de uso diario") **ninguna califica como formal**, así que las 2 quedan fuera de universidad hasta que exista una camisa real tageada como formal. Ambas siguen apareciendo normal en carrete y el resto de ocasiones (junta social, concierto/festival, etc.) -- no se tocó nada ahí.
- No se creó un subtipo nuevo en `SUBTIPOS_CONOCIDOS`/`SUBTIPOS_POR_TIPO_PRENDA` (eso alimenta la búsqueda libre de texto, "camisa cargo" por ejemplo, fuera de alcance de este pedido) -- la detección es solo por palabra en el texto real del producto, mismo patrón que `palabras_clave`/`palabras_prohibidas` de pantalón.
- Verificado con `_prenda_excluida_por_ocasion()` directo sobre las 2 camisas reales: ambas `excluida=False` en carrete/junta social, ambas `excluida=True` en universidad.

## Diversificación por tienda no debe bajar la relevancia (bug corregido, 2026-09-07)

Pedido del usuario: "REGLA, si hay muchas prendas disponibles para tal opción, tienen que aparecer primero sí o sí las con más alto nivel [de confianza/relevancia] -- si dos prendas cumplen exactamente con todo lo que el cliente busca, esas van primero".

- `_diversificar_por_tienda()` (evita 2 tarjetas seguidas de la misma tienda, `docs` arriba explican el porqué) tenía un bug real: cuando una tienda dominaba el tramo de arriba (ej. 3 productos top de Doslobos) y otra tienda tenía solo 1-2 productos de puntaje mucho más bajo, el algoritmo igual "colaba" el producto de menor puntaje antes que el segundo/tercer producto de mayor puntaje de la tienda dominante -- solo para alternar tienda. Verificado con un caso de prueba directo (puntajes 10/9/8 de tienda A y 5/4 de tienda B): salía A1(10), B1(5), A2(9), B2(4), A3(8) -- el de puntaje 5 adelante de los de 9 y 8.
- Esto contradecía la intención ya escrita en el propio comentario de la función ("nunca baja la relevancia a propósito, solo cambia CUAL de los empates/cercanos elige") -- en la práctica sí bajaba la relevancia, no solo entre empates/cercanos sino sin importar la distancia de puntaje.
- **Fix:** `elegir_candidatos()` ahora agrupa los candidatos por nivel de relevancia REAL (mismos `nivel_hobby`/`nivel_corte_ancho`/`nivel_subtipo_ocasion`/`puntaje_palabras`/`nivel_forma_gorro` -- todo el `puntaje()` menos el desempate neutral del final, que es un hash único por producto y nunca debía contar como "nivel" real) antes de pasarle la lista a `_diversificar_por_tienda()`. La diversificación por tienda ahora SOLO puede reordenar productos dentro de un mismo nivel -- nunca deja pasar uno de un nivel más bajo antes de agotar los de nivel más alto, sin importar cuántas prendas de la misma tienda haya arriba. Reverificado con el mismo caso de prueba: ahora sale A1, A2, A3, B1, B2 (orden estrictamente por nivel), y la diversificación dentro de un mismo nivel (empate real) sigue funcionando igual que antes.
- No se tocó ninguna otra parte del ranking (prioridad de subtipo, corte ancho, forma de gorro, exclusiones de ocasión, etc.) -- solo la función de diversificación y cómo se arman los grupos que recibe.

## Datos de referencia sin usar

`data/referencia_no_oficial.json` guarda dos respuestas de Mica (carrete/fiesta, universidad/polerón) que calzan con el enfoque streetwear pero NO son reglas oficiales validadas. Solo contexto extra.
