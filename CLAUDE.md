# Proyecto

App/simulador que recomienda ropa streetwear según altura, peso, ocasión y presupuesto, cruzando con catálogo de tiendas chicas. Objetivo: dar visibilidad a tiendas pequeñas y ayudar al comprador a encontrar la prenda indicada.

## Fuera de alcance

No reincorporar sin pedido explícito del usuario:
- Ocasiones no-streetwear (matrimonio, oficina, entrevista de trabajo, playa, deporte, primera cita).
- Zapatillas/calzado (se sacó la ocasión, sus reglas, y la opción de categoría del formulario). Foco actual: solo prendas de ropa.

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

1. **¿Colores específicos o combinar con un outfit?**
   - *Colores específicos*: checkboxes (blanco, negro, rojo, azul, amarillo, beige, morado, verde) → filtra `color_dominante`.
   - *Combinar con outfit* → pregunta "¿Cómo es tu outfit?":

     | Outfit | Colores de gorro permitidos |
     | --- | --- |
     | Oscuro | Color vivo (rojo/azul/amarillo/morado/verde) como acento, o blanco para contraste limpio |
     | Claro | Negro para contraste, o color vivo como protagonista |
     | Colorido | Solo negro o blanco (neutro, para no sobrecargar) |
     | Otro | No filtra por color — muestra variedad |

2. **¿Qué tipo de gorro?** (siempre se pregunta, sin importar el camino elegido) → filtra `forma`: curvo / plano / lana (beanie, sin visera).

Tagueo: en gorros de dos tonos (tipo trucker), `color_dominante` = color del **panel frontal**, no toda la superficie.

Nota: hubo otra tabla más simple dando vueltas ("outfit neutro"/"colorido"/"buscas armonía") que no llegó a tener opciones de formulario definidas — si esa es la lógica que en verdad se quiere, avisar para reemplazar la de arriba.

## Imágenes ilustrativas del catálogo mock

Cada producto (prenda o gorro) trae un campo `imagen` → SVG en `static/img/{gorros,prendas}/`, generado a mano por `generar_imagenes_gorro.py` / `generar_imagenes_prendas.py` **antes** de correr `generar_catalogo_prueba.py`. Nunca son fotos reales ni copian logos/diseños de marcas reales — estética streetwear genérica (paneles de color, formas bold). La UI (`static/comun.js`) siempre muestra el aviso "Imagen ilustrativa de referencia, no es el producto real." debajo de la imagen.

- **Gorro**: el color de la imagen SÍ es el dato real (`color_dominante`). Curvo/plano en sólido y en dos tonos (panel frontal según la tabla `PANEL_SUGERIDO`); lana solo en sólido.
- **Prendas**: el catálogo mock no tiene campo de color real para prendas, así que `generar_catalogo_prueba.py` le asigna a cada producto un color **inventado** al azar (misma paleta de 8 colores) solo para la imagen — no se guarda como dato del producto ni filtra nada. Siluetas por tipo: polera (manga larga/corta), camiseta, camisa (con botones), chaqueta, polerón (4 combos capucha/cierre), los 6 subtipos de Top, pantalón/shorts/bike shorts/falda cargo (misma silueta para todos los subtipos de pantalón/shorts — ahí la variedad es solo de color).

## Talla — inferencia automática

Se cruza altura + peso (datos que el formulario ya pide, sin campo nuevo). Se calcula una talla según el peso y otra según la altura (tablas separadas); la **más chica** de las dos es la principal (para no ofrecer algo más ajustado de lo que corresponde), la otra queda como segunda opción. Si empatan, la segunda opción es la vecina más grande (o más chica si ya es XL). Cada resultado muestra TODAS las tallas coincidentes que tenga en stock (`tallas_coincidentes`). Si no calza en ninguna, se avisa en vez de dejar la página vacía sin explicación. Los gorros están exentos (talla única).

| Talla | Altura mujer | Peso mujer | Altura hombre | Peso hombre |
| --- | --- | --- | --- | --- |
| S | hasta 1.65m | hasta 60kg | hasta 1.70m | hasta 68kg |
| M | hasta 1.70m | hasta 70kg | hasta 1.78m | hasta 80kg |
| L | hasta 1.75m | hasta 80kg | hasta 1.85m | hasta 92kg |
| XL | más de 1.75m | más de 80kg | más de 1.85m | más de 92kg |

Rangos orientativos (la encuesta original se solapa entre tallas; para el cálculo se usan como topes fijos, no exactos).

## Taguear catálogo real que no trae estos datos explícitos

Ni corte ni talla vienen siempre explícitos en la ficha de una tienda real. El criterio es que Claude infiera el dato producto por producto contra las tablas de arriba — **no** preguntar de entrada ni dejar el campo vacío:
- **Corte**: comparar descripción/medidas contra la tabla de corte (y los cm cuando la ficha dé medidas concretas de holgura).
- **Talla** (`tallas_disponibles`): si la ficha da medidas propias de la prenda (ancho de pecho, largo), cruzarlas contra la tabla de talla de arriba para inferir a qué talla(s) le calzarían.

Si la ficha no da ni descripción ni medidas suficientes para inferir con confianza, no inventar el dato — preguntarle al usuario (dueño del proyecto) antes de taguear a ciegas.

## "Mostrar más opciones" — alternativas de corte

Cuando ya no queda ningún producto que cumpla TODOS los filtros pedidos (incluido el corte específico, ej: "jeans baggy"), el Plan B ya no deja la búsqueda vacía:
1. Completa primero con más productos del corte exacto pedido (todos los demás filtros intactos).
2. Si no alcanza a `CANTIDAD_RESULTADOS`, rellena el resto relajando **solo el corte** (mismo tipo de prenda, otro ajuste) — nunca el tipo de prenda ni los demás filtros estrictos.
3. No se relaja nada más por ahora (el catálogo mock suele alcanzar a llenar con el paso 2).

Estas alternativas nunca se mezclan en silencio con las que sí cumplen todo: van en un campo aparte (`alternativas` + `aviso_alternativas`), y el frontend (`static/resultados.js`) las pinta con un aviso destacado antes de las tarjetas (ej: `No encontramos más opciones en "boxy fit", pero esto también podría interesarte...`).

Ojo técnico (`buscar_plan_b` en `app.py`): hay que sacar los productos ya mostrados del catálogo **antes** de llamar `elegir_candidatos(permitir_otros_cortes=True)`, no filtrarlos después — si no, la función ve que "todavía existen" productos del corte pedido (los ya mostrados) y nunca relaja nada.

## Volver atrás sin perder los filtros

Si el navegador restaura `/` desde su caché (bfcache), el estado del formulario queda intacto solo. Si el navegador SÍ recarga la página de cero al volver atrás (`performance.getEntriesByType("navigation")[0].type === "back_forward"`) y hay una búsqueda guardada (`sessionStorage.ultimoPayload`), `static/script.js` salta directo a la sección de filtros ya llena (función `restaurarFiltros()`) en vez de reiniciar el formulario.

Casos particulares: un valor que no calza con ninguna opción del select (era texto libre en "Otro") selecciona "Otro" y rellena ese input; un valor vacío (era "Me da igual") deja esa opción si existe. El link "← Hacer una nueva búsqueda" es navegación normal — no dispara esto, a propósito deja el formulario limpio.

## Koko — asistente de estilo con chat

Mascota-perrito de Kolizion. Ícono "Conversemos con Koko" arriba a la derecha de `index.html` (no en `resultados.html` todavía) que abre un panel de chat aparte (overlay `#panel-koko`, fuera de las secciones del formulario) — nunca mezclado con el flujo normal de búsqueda.

**Motor:** IA real vía API de Anthropic (decisión explícita del usuario, no un árbol de reglas fijo — así Koko conversa libre de verdad). Requiere `ANTHROPIC_API_KEY` configurada como variable de entorno o en un archivo `.env` local (gitignored, ver `.env.example`); si falta, `/api/koko/chat` responde con un aviso en vez de caerse. Tiene costo por mensaje y necesita internet — a diferencia del resto de la app, que es 100% local/mock.

**Cómo sugiere una búsqueda:** Koko da consejo en conversación libre (nunca busca productos él mismo) y, cuando ya tiene claro qué ofrecer, llama una tool (`sugerir_busqueda`, con `categoria`/`tipo_prenda`/`corte`) en vez de que el backend tenga que parsear su texto. El frontend (`static/koko.js`) muestra esa sugerencia como una mini-tarjeta "¿Buscamos X para ti?"; si el usuario confirma, arma el mismo payload que usa una búsqueda normal (modo "yo") y llama a `buscar()` de `script.js` — reusa 100% el pipeline existente, no hay lógica de búsqueda duplicada.

**Animación:** clase `.koko-pensando` (`@keyframes koko-rebote` en `style.css`) se agrega al avatar justo antes de mandar el mensaje y se saca en el `finally` de `enviarMensajeKoko` — así nunca queda pegada, prenda o falle la respuesta.

**Historial y personalización (`data/historial_usuarios.json`, gitignored — es dato real de uso, no mock):** dict keyado por email en minúscula, con `busquedas` (ocasión/categoria/tipo_prenda/corte de cada búsqueda que el usuario hace **para sí mismo**) y `productos_interes` (clics en "Ver producto"). Dos señales de interés, ambas se registran:
- `registrar_busqueda` se llama desde `/api/recommend` solo cuando `modo=="yo"` y no es "mostrar más opciones" (para no duplicar la misma búsqueda).
- `registrar_interes` se llama desde el nuevo endpoint `/api/koko/interes`, disparado por un listener en `renderResultados` (`comun.js`) al hacer clic en "Ver producto" — solo si la búsqueda activa es "yo" y hay email guardado. Las búsquedas "regalo" nunca se registran (son sobre el estilo de otra persona).

`resumen_historial_para_prompt(email)` arma el texto que se mete en el prompt de Koko; devuelve `None` si el usuario es nuevo (Koko da consejo general basado en `data/reglas_streetwear.json`, sin inventar gustos). Con historial, el prompt le pide a Koko mencionar explícitamente el motivo (ej. "como sueles preferir oversize...").

**Nota de privacidad (cambio respecto a una decisión anterior):** el formulario "yo" antes mandaba el perfil al servidor sin el gmail a propósito (ver `static/script.js`). Ahora el gmail SÍ viaja como campo `email` aparte de `perfil`, solo para identificar el historial — nombre y orientación sexual siguen sin mandarse nunca.

**Sin login:** el email es solo un identificador de texto libre, no hay contraseña ni autenticación — cualquiera que escriba el mismo correo ve "su" historial.

## Datos de referencia sin usar

`data/referencia_no_oficial.json` guarda dos respuestas de Mica (carrete/fiesta, universidad/polerón) que calzan con el enfoque streetwear pero NO son reglas oficiales validadas. Solo contexto extra.

## Reglas de trabajo

- Cuando no hay consenso claro en una categoría, mostrar 2-3 opciones en vez de una sola recomendación.
- Nunca inventar productos o links que no vengan de un catálogo real.
- El usuario no sabe programar: antes de hacer cambios importantes, explicar en español simple qué se va a hacer y para qué sirve.
- PowerShell en este equipo tiene un límite de ~965 bytes por comando. Para probar varios casos a la vez, guardarlos en un archivo de script (.py o .ps1) y ejecutarlo con un comando corto, en vez de escribir pruebas largas directo en la terminal.
