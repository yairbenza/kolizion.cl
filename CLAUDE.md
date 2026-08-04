# Proyecto

App/simulador que recomienda ropa streetwear según altura, peso, ocasión y presupuesto del usuario, cruzando con catálogo de tiendas chicas. El objetivo es dar visibilidad a tiendas pequeñas y ayudar al comprador a encontrar la prenda indicada sin importar la tienda.

## Fuera de alcance

Cualquier ocasión que no sea streetwear (matrimonio, oficina, entrevista de trabajo, playa, deporte, primera cita) — esos casos quedaron descartados del enfoque actual. No reincorporarlos sin que el usuario lo pida explícitamente.

Zapatillas/calzado también quedó fuera de alcance por ahora: se sacaron la ocasión "comprar zapatillas", sus reglas de recomendación, y la opción de categoría "zapatillas" del formulario. El foco actual es solo prendas de ropa. No reincorporar sin que el usuario lo pida explícitamente.

## Reglas de recomendación validadas

Ver `data/reglas_streetwear.json` para el detalle estructurado. Resumen:

**Alta confianza (3-4 respuestas coincidiendo, salvo donde se indique):**
- Hombre + concierto/festival + polera → oversize, colores oscuros, marca de streetwear reconocida o nicho valorado, tela transpirable.
- Hombre + junta de amigos/skate park + pantalón cargo → baggy/suelto, cómodo para moverse, buen precio, buena caída hasta el tobillo.
- Mujer + junta de amigos/skate park + pantalón cargo → baggy, cómodo, versátil, corte tiro bajo o cintura alta que estiliza.
- Mujer + concierto/festival + polera/top → ajustado, que favorezca la figura para la ocasión (5-6 respuestas coincidiendo). Si no hay stock en corte ajustado, ofrecer oversize/boxy fit como alternativa secundaria, no como recomendación principal.

**Confianza media:**
- Ninguna actualmente.

**Sin consenso — no recomendar con una sola opción:**
- Ninguna actualmente.

Estas reglas se seguirán ampliando/afinando a medida que lleguen más respuestas de validación. Cuando eso pase, actualizar solo las reglas puntuales indicadas — no tocar las que ya están confirmadas.

## Criterios de tagueo manual de corte

Cuando se cargue el catálogo de una tienda nueva y la ficha del producto no diga explícitamente el corte, usar estos criterios para asignar el campo `corte` de forma consistente.

**Prenda superior** (polera, polerón, camisa, chaqueta):

| Opción en la web | Cómo identificarlo |
| --- | --- |
| Slim fit | Se ciñe al cuerpo, marca la silueta, mangas ajustadas al brazo |
| Regular fit | Calce normal, leve entalle en la cintura, ni pegado ni suelto |
| Straight | Cae recto de arriba a abajo, sin ningún entalle en la cintura (a diferencia de regular, que sí puede entallar un poco) |
| Boxy fit | Ancho/cuadrado en el cuerpo, hombros rectos, pero de largo normal (no pasa mucho la cadera) |
| Oversized | Notablemente más grande que la talla normal: hombros caídos, largo que pasa la cadera, mangas anchas |

Nota: para polerón, comparar contra otros polerones, no contra poleras, por el grosor de la tela.

Rangos de holgura aproximados (no exactos — varían por marca) para cuando conviene apoyarse en un número en vez de solo la descripción:
- Slim/Skinny: 0-5cm de holgura respecto al cuerpo
- Regular/Straight: 5-14cm
- Boxy/Relajado: 14-20cm
- Oversized: 20cm o más

**Prenda inferior** (pantalón, jeans, cargo, buzo):

| Opción en la web | Cómo identificarlo |
| --- | --- |
| Skinny | Se ciñe a la pierna de principio a fin, mínimo espacio extra |
| Slim fit | Ajustado pero con un poco más de espacio que skinny, especialmente en el muslo |
| Straight fit | Caída recta, mismo ancho de muslo a tobillo, sin ajustar ni ensanchar |
| Baggy | Amplio en muslo y pierna, caída suelta hasta el tobillo, espacio notorio en toda la pierna |

Nota: para cargo, el corte (skinny/baggy/etc.) se evalúa igual que cualquier pantalón — los bolsillos grandes son una característica aparte, no cambian el criterio de ajuste. A diferencia de prenda superior, aquí NO hay un estándar de industria tan claro en centímetros — usar el mismo criterio proporcional (menos espacio = ajustado, más espacio = baggy) sin apoyarse en números exactos, ya que no están verificados.

**Definiciones cortas que se muestran en el formulario** (entre paréntesis, al lado de cada opción — solo texto visible, no afectan el filtro):

- Prenda superior: Slim fit (se pega al cuerpo) · Regular fit (calce normal) · Straight (cae recto, sin marcar cintura) · Boxy fit (ancho y cuadrado) · Oversized (grande y holgado, hombros caídos)
- Prenda inferior: Skinny (bien pegado a la pierna) · Slim fit (ajustado, con algo de espacio) · Straight fit (calce parejo) · Baggy (holgado en toda la pierna)
- Prendas nuevas de mujer: Crop top (corto, abdomen a la vista) · Baby tee (corto y ajustado) · Top halter (sin mangas, amarrado al cuello) · Corset top (ajustado, costuras marcadas) · Falda cargo (bolsillos grandes) · Bike shorts (ajustados, tipo ciclista)

## Ampliación streetwear de mujer

Se agregaron tipos de prenda nuevos al formulario porque el catálogo estaba menos desarrollado para mujer que para hombre.

**Prenda superior — "Top"** (una sola opción nueva en "¿qué prenda buscas?", independiente de polera/camisa/etc): al elegir "Top" aparece un segundo dropdown "¿qué tipo buscas?" con 6 subtipos — Crop top/Crop hoodie, Baby tee, Top con breteles/halter, Corset top, Tank top, Camisas/blusas — igual que el subtipo de pantalón (buzo/jeans/cargo). Usan la misma tabla de corte de arriba (slim fit/regular fit/straight/boxy fit/oversized).

**Prenda inferior** (opciones nuevas, independientes de Pantalón/Shorts, no como subtipo de ellos): Falda cargo (misma lógica de corte que cualquier pantalón — los bolsillos no cambian el criterio) y Bike shorts/shorts ciclista. Usan la misma tabla de corte de prenda inferior.

**Campo nuevo: Largo.** Solo aparece si la prenda elegida es un "top" (polera, camiseta, o el tipo "Top" con cualquiera de sus 6 subtipos). Opciones: Corto/crop, Largo normal, Extra largo (longline). Es independiente del corte — una prenda puede ser oversize Y crop al mismo tiempo, así que ambos filtros se aplican juntos, no uno reemplaza al otro.

Nota técnica: "top" era antes sinónimo de "polera" en el buscador (la regla validada #4 dice "polera/top"). Ahora "top" es su propio tipo, así que se le sacó esa palabra a "polera" — la regla 4 sigue encontrando poleras igual (por la palabra "polera"), pero ya no reacciona a la palabra suelta "top". Si el usuario escribe "top" en un campo libre sin decir "polera", ahora apunta al tipo "Top" nuevo, no a poleras.

## Atributos adicionales: manga, capucha, cierre

Preguntas condicionales nuevas, independientes del corte (una polera puede ser oversize Y manga larga a la vez; un polerón puede ser boxy fit Y con capucha Y con cierre, las 3 cosas no se pisan entre sí):

- **Polera** → "¿Manga larga o manga corta?" (campo `manga`: `larga` / `corta`).
- **Polerón** → dos preguntas separadas: "¿Con capucha o sin capucha?" (campo `capucha`: `con capucha` / `sin capucha`) y "¿Con cierre o sin cierre (crewneck)?" (campo `cierre`: `con cierre` / `sin cierre`).

Ningún otro tipo de prenda pregunta esto (ni siquiera "Top" ni sus subtipos).

Criterio de tagueo cuando la ficha de un catálogo real no lo diga con esas palabras exactas: esto normalmente SÍ viene explícito o es fácil de ver en fotos/descripción (a diferencia de corte o talla, que a veces hay que inferir) — "poleron sin cierre" es sinónimo de "crewneck" en la mayoría de las tiendas, y "sin capucha" casi siempre se llama "crewneck" o "cuello redondo" también. Si la ficha no menciona ninguna de las dos cosas ni se ve en las fotos, preguntarle al usuario (dueño del proyecto) antes de taguear a ciegas — a diferencia de corte/talla, aquí no hay una tabla de medidas de la cual inferir.

## Gorro

Tipo de prenda nuevo, independiente ("Gorro" en el dropdown principal "¿qué buscas?", junto a Prenda superior/Prenda inferior). No usa corte ni las preguntas de subtipo/largo/manga/capucha/cierre — tiene su propio flujo, y tampoco se filtra por talla S/M/L/XL (es talla única/ajustable).

**Paso 1** — "¿Buscas colores específicos o que combine con un outfit?":
- **Camino A (colores específicos):** checkboxes de selección múltiple — blanco, negro, rojo, azul, amarillo, beige, morado, verde. Filtra productos cuyo `color_dominante` esté entre los marcados.
- **Camino B (combinar con outfit):** pregunta "¿Cómo es tu outfit?" (Oscuro / Claro / Colorido / Otro), que se traduce a un set de colores permitidos:

| Outfit | Colores de gorro permitidos |
| --- | --- |
| Oscuro | Color vivo (rojo, azul, amarillo, morado, verde) como acento, o blanco para contraste limpio |
| Claro | Negro para contraste, o color vivo como protagonista |
| Colorido | Solo negro o blanco (un color neutro, para no sobrecargar) |
| Otro | No filtra por color — muestra variedad |

**Paso 2** (siempre, sin importar el camino elegido) — "¿Qué tipo de gorro?": filtra por el campo `forma` (`curvo` / `plano` / `lana`). "Gorro de lana" (beanie, sin visera) se agregó como tercera opción de esta misma pregunta.

Nota: había otra tabla más simple dando vueltas ("outfit neutro" / "outfit ya colorido" / "buscas armonía") que no llegó a tener opciones de formulario definidas — si esa es la lógica que en verdad quieres, avisar para reemplazar la de arriba.

**Criterio de tagueo:** en gorros de diseño de dos tonos (tipo trucker), el `color_dominante` se define por el **panel frontal**, no por la superficie total de la prenda.

**Imágenes de referencia:** cada gorro del catálogo mock trae un campo `imagen` que apunta a un SVG ilustrativo en `static/img/gorros/` (generados por `generar_imagenes_gorro.py`, corridos a mano antes de `generar_catalogo_prueba.py`). NO son fotos reales de producto ni de ninguna tienda — son dibujos simples (forma + color plano) hechos desde cero en Python, sin depender de ningún servicio de generación de imágenes externo. Inspirados de forma muy genérica en la estética streetwear (paneles de color, tipografía/forma bold, combinación panel frontal + visera) pero sin copiar logos, nombres ni diseños de ninguna marca real. En el buscador (`static/comun.js`), cada tarjeta de resultado que tiene `imagen` muestra debajo un aviso: "Imagen ilustrativa de referencia, no es el producto real." — para que quede claro que es solo para pruebas visuales, no un catálogo real. Cubren: curvo y plano en color sólido y en dos tonos (panel frontal distinto, según la tabla `PANEL_SUGERIDO` del script), y gorro de lana en color sólido.

## Imágenes de referencia de prendas (no solo gorro)

Igual que los gorros, cada prenda del catálogo mock (polera, camiseta, camisa, chaqueta, polerón, los 6 subtipos de "Top", pantalón, shorts, falda cargo, bike shorts) trae un campo `imagen` que apunta a un SVG ilustrativo en `static/img/prendas/` (generados por `generar_imagenes_prendas.py`, corrido a mano antes de `generar_catalogo_prueba.py`, mismo estilo de silueta simple + color plano, sin fotos reales ni logos). El aviso "Imagen ilustrativa de referencia, no es el producto real." se muestra igual que en gorro.

El color de cada imagen es **inventado**: el catálogo mock no tiene un campo de color real para prendas (a diferencia de gorro, que sí filtra por `color_dominante`), así que `generar_catalogo_prueba.py` le asigna a cada producto un color al azar (de la misma paleta de 8 colores de gorro) solo para que la imagen se vea distinta entre productos — ese color no queda guardado como campo del producto ni se usa para filtrar nada, existe únicamente en el nombre del archivo SVG.

Siluetas: polera (varía según manga larga/corta), camiseta, camisa (con botones), chaqueta (con cierre al medio), polerón (varía según capucha con/sin y cierre con/sin — 4 combinaciones), los 6 subtipos de Top (croptop, baby tee, halter, corset con líneas de costura, tank top con tirantes, blusa), pantalón, shorts, bike shorts y falda cargo (con bolsillos). Pantalón/shorts usan la misma silueta sin importar el subtipo (buzo/jeans/cargo/tela/baño) — la variedad ahí es solo de color, no de forma.

## Talla inferida automáticamente

El buscador infiere la talla del usuario cruzando altura y peso — datos que el formulario ya pide, no se agregó ninguna pregunta nueva de talla. Calcula una talla según el peso y otra según la altura (cada una por separado, contra su propia tabla), y usa la MÁS CHICA de las dos como principal (para no ofrecer algo más ajustado de lo que corresponde); la otra talla calculada queda como segunda opción. Si peso y altura dan la misma talla, la segunda opción es la vecina más grande (o más chica si ya es XL). Muestra en cada resultado cuál de esas tallas tiene ese producto ("Disponible en tu talla: M"). Si no calza en ninguna, se muestra un aviso en vez de dejar la página vacía sin explicación.

Tabla orientativa (los rangos de la encuesta original se solapan entre tallas; para el cálculo se usan como topes fijos y no exactos):

| Talla | Altura — mujer | Peso — mujer | Altura — hombre | Peso — hombre |
| --- | --- | --- | --- | --- |
| S | hasta 1.65m | hasta 60kg | hasta 1.70m | hasta 68kg |
| M | hasta 1.70m | hasta 70kg | hasta 1.78m | hasta 80kg |
| L | hasta 1.75m | hasta 80kg | hasta 1.85m | hasta 92kg |
| XL | más de 1.75m | más de 80kg | más de 1.85m | más de 92kg |

## Cómo taguear catálogo real que no trae estos datos explícitos

Ni "corte" ni "talla" van a venir siempre explícitos en la ficha de una tienda real. Cuando eso pase, el criterio no es preguntarle al usuario ni dejar el campo vacío — es que yo (Claude) asocie el dato manualmente, producto por producto, usando la descripción y las medidas que sí traiga la ficha, contra las tablas de este documento:

- **Corte**: comparar la descripción/medidas del producto contra la tabla de "Criterios de tagueo manual de corte" de arriba (y los rangos en cm cuando la ficha dé medidas concretas de holgura).
- **Talla (`tallas_disponibles`)**: mismo principio, pero al revés — la tabla de altura/peso de la sección de talla describe qué cuerpo le calza a cada talla. Si la ficha del producto da medidas propias de la prenda (ej: ancho de pecho, largo), usar esas medidas para inferir a qué talla(s) de esa tabla le quedarían bien, y taguear el producto con esa(s) talla(s).

Si la ficha no da ni descripción ni medidas suficientes para inferir con algo de confianza, no inventar el dato — mejor preguntarle al usuario (dueño del proyecto) antes de taguear a ciegas.

## Datos de referencia sin usar

`data/referencia_no_oficial.json` guarda dos respuestas de Mica (carrete/fiesta y universidad/polerón) que sí calzan con el enfoque streetwear, pero que NO son parte de las reglas oficiales validadas arriba. Son solo contexto extra por ahora.

## Volver atrás sin perder los filtros

Antes, si el usuario llegaba a `/resultados` y apretaba el botón "atrás" del navegador, `index.html` no se acordaba de nada: volvía siempre al primer paso del formulario (perfil o "¿para quién es esta búsqueda?"), perdiendo la categoría/tipo de prenda/corte/etc. que ya había elegido.

Ahora `static/script.js` detecta ese caso puntual (usando `performance.getEntriesByType("navigation")[0].type === "back_forward"`, la forma estándar de saber si la página se cargó por un "atrás"/"adelante" del navegador y no por una visita normal) y, si además hay una búsqueda guardada de esta sesión (`sessionStorage.ultimoPayload`, el mismo dato que ya se usaba para pintar `/resultados`), salta directo a la sección de filtros (`seccion-busqueda-yo` o `seccion-busqueda-regalo`, según corresponda) con todos los campos ya rellenados como habían quedado — función `restaurarFiltros()`.

Si el navegador restaura la página desde su caché interna (bfcache) en vez de recargarla, esto ni siquiera hace falta: el estado queda congelado tal cual estaba. `restaurarFiltros()` es el respaldo para cuando el navegador SÍ recarga la página de cero.

Casos que se manejan aparte:
- Si un select no encuentra el valor guardado entre sus opciones (pasó porque el usuario había escrito algo en el campo libre de "Otro"), se selecciona "Otro" y se rellena ese campo de texto con el valor guardado.
- Si el valor guardado viene vacío (era "Me da igual"), se deja esa opción seleccionada si existe.
- El link "← Hacer una nueva búsqueda" de `/resultados` sigue mandando a un formulario limpio, porque es una navegación normal (no "atrás"), no dispara `restaurarFiltros()`.

## Reglas de trabajo

- Cuando no hay consenso claro en una categoría, mostrar 2-3 opciones en vez de una sola recomendación.
- Nunca inventar productos o links que no vengan de un catálogo real.
- El usuario no sabe programar: antes de hacer cambios importantes, explicar en español simple qué se va a hacer y para qué sirve, antes de ejecutarlo.
- PowerShell en este equipo tiene un límite de ~965 bytes por comando. Cuando pruebes varios casos a la vez, guárdalos en un archivo de script (.py o .ps1) y ejecuta ese archivo con un comando corto, en vez de escribir pruebas largas directo en la terminal.
