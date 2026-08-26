import json
from datetime import datetime, timedelta, timezone

from constantes import (
    CANTIDAD_RESULTADOS,
    CATALOG_PATH,
    CHATS_KOKO_PATH,
    CORTES_CONOCIDOS,
    FORMAS_GORRO_CONOCIDAS,
    LIMITE_KOKO_PATH,
    SUBTIPOS_CONOCIDOS,
    TIPOS_PRENDA_CONOCIDOS,
    load_json,
    _normalizar_email,
    _parsear_fecha_iso,
    _quitar_tildes,
    _texto_seguro,
)
from motor_recomendacion import (
    _reglas_hobby_usuario,
    elegir_candidatos,
    filtrar_gorros_por_forma,
    filtrar_por_talla,
)
from servicio_tiendas import (
    cargar_historial,
    obtener_favoritos,
)


def cargar_chats_koko():
    if not CHATS_KOKO_PATH.exists():
        return {}
    return load_json(CHATS_KOKO_PATH)


def guardar_chats_koko(chats):
    CHATS_KOKO_PATH.write_text(json.dumps(chats, ensure_ascii=False, indent=2), encoding="utf-8")


def cargar_historial_chat(email):
    email = _normalizar_email(email)
    if not email:
        return []
    return cargar_chats_koko().get(email, [])


def guardar_mensaje_chat(email, rol, texto):
    email = _normalizar_email(email)
    if not email or not texto:
        return
    chats = cargar_chats_koko()
    chats.setdefault(email, []).append({"rol": rol, "texto": texto})
    guardar_chats_koko(chats)


def reiniciar_chat_koko(email):
    email = _normalizar_email(email)
    if not email:
        return
    chats = cargar_chats_koko()
    if email in chats:
        del chats[email]
        guardar_chats_koko(chats)


def cargar_limite_koko():
    if not LIMITE_KOKO_PATH.exists():
        return {}
    return load_json(LIMITE_KOKO_PATH)


def guardar_limite_koko(datos):
    LIMITE_KOKO_PATH.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def registrar_mensaje_usuario_koko(email):
    email = _normalizar_email(email)
    if not email:
        return
    datos = cargar_limite_koko()
    hace_48h = datetime.now(timezone.utc) - timedelta(hours=48)
    fechas = datos.get(email, [])
    fechas = [f for f in fechas if (_parsear_fecha_iso(f) or hace_48h) >= hace_48h]
    fechas.append(datetime.now(timezone.utc).isoformat())
    datos[email] = fechas
    guardar_limite_koko(datos)


def mensajes_usuario_ultimas_24h(email):
    email = _normalizar_email(email)
    if not email:
        return 0
    hace_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    muy_viejo = datetime.min.replace(tzinfo=timezone.utc)
    fechas = cargar_limite_koko().get(email, [])
    return sum(1 for f in fechas if (_parsear_fecha_iso(f) or muy_viejo) >= hace_24h)


_DISPARADORES_TONO_CHILENO = [
    "hablame como chileno", "habla como chileno", "hablame en chileno",
    "usa modismos chilenos", "modo chileno",
]


def preferencia_idioma_koko(email):
    historial = cargar_historial_chat(email)
    texto = _quitar_tildes(
        " ".join(m.get("texto", "") for m in historial if m.get("rol") == "usuario").lower()
    )
    if any(disparador in texto for disparador in _DISPARADORES_TONO_CHILENO):
        return "chileno"
    return None


def resumen_historial_para_prompt(email):
    email = _normalizar_email(email)
    if not email:
        return None
    entrada = cargar_historial().get(email)
    if not entrada or not (entrada.get("busquedas") or entrada.get("productos_interes")):
        return None

    lineas = []
    busquedas = entrada.get("busquedas", [])
    cortes = [b["corte"] for b in busquedas if b.get("corte")]
    tipos = [b["tipo_prenda"] for b in busquedas if b.get("tipo_prenda")]
    ocasiones = [b["ocasion"] for b in busquedas if b.get("ocasion")]
    if cortes:
        lineas.append(f"Cortes que ha buscado antes: {', '.join(cortes[-5:])}.")
    if tipos:
        lineas.append(f"Tipos de prenda que ha buscado antes: {', '.join(tipos[-5:])}.")
    if ocasiones:
        lineas.append(f"Ocasiones para las que ha buscado antes: {', '.join(ocasiones[-5:])}.")

    nombres_interes = [p["nombre"] for p in entrada.get("productos_interes", [])[-5:] if p.get("nombre")]
    if nombres_interes:
        lineas.append(f"Productos en los que hizo clic para ver mas: {', '.join(nombres_interes)}.")

    return " ".join(lineas) if lineas else None


KOKO_SYSTEM_PROMPT_BASE = """Eres Koko, la mascota-perrito asistente de estilo de KOLIZION, una app que \
recomienda streetwear de tiendas chicas segun altura, peso, ocasion y presupuesto.

Tono: por defecto, espanol neutro/estandar -- cercano, entusiasta y calido, pero SIN modismos regionales. \
Habla de tu (nunca "usted"), nunca como un asistente corporativo o formal. Por defecto NO uses \
expresiones chilenas como "al tiro", "bacan", "la firme", "cuatico", "fome", "carrete", "poh", "cachai", \
"weon"/"weá", "po", ni ninguna similar -- ni siquiera una, aunque el tema sea streetwear/calle. SOLO si \
en algun momento de la conversacion la persona te pide explicitamente hablar como chileno (ej: "hablame \
como chileno", "usa modismos chilenos", "hablame en chileno"), recien ahi cambia desde ESE momento en \
adelante a un tono chileno joven/universitario con esas mismas expresiones, usadas con naturalidad y sin \
amontonarlas -- y mantenlo asi por el resto de esta conversacion, sin volver al neutro salvo que te lo \
pidan.

Das consejo de estilo en conversacion libre -- vos NO buscas productos directamente, para eso esta el \
buscador de la app (via la tool sugerir_busqueda).

Reglas de recomendacion streetwear ya validadas (usalas como base de tu consejo, no las repitas literal \
ni las nombres como "reglas"):
{reglas}

{perfil}

{historial}

{favoritos}

{hobbies}

Usa los datos de perfil y los favoritos de arriba para personalizar tu consejo -- ej: si ya sabes su \
talla estimada, no vuelvas a preguntarla; si tiene favoritos guardados, podes mencionarlos con \
naturalidad cuando venga al caso (ej: "veo que ya tienes un par de poleras guardadas, ¿buscamos algo \
distinto o mas de lo mismo?"). Nunca los recites como una lista literal salvo que te lo pidan \
explicitamente, y nunca inventes un dato de perfil o un favorito que no este en esos bloques.

Cuando el usuario nombra una prenda concreta (polera, poleron, camisa, chaqueta, chaleco, camiseta, top, \
pantalon, short, falda, o gorro), interpreta esa frase usando los MISMOS criterios de tipo de prenda y \
corte que usa el buscador normal de la app (los mismos valores que recibe sugerir_busqueda). Nunca llames \
la tool con una prenda, corte o presupuesto que no calce con lo que la persona realmente dijo.

- PRIMERO revisa esto, antes que la regla de abajo: si en su mensaje ya te dio el corte/ajuste (ej: \
  "baggy", "oversize", "ajustada", "slim", "que no quede pegado"), eso YA es suficiente por si solo -- \
  llama la tool en esa misma respuesta, con un mensaje corto confirmando lo que entendiste. NO le \
  preguntes color, presupuesto, ni para que ocasion/uso -- esos son solo un plus cuando falta el corte, \
  nunca un requisito si el corte ya esta. Ejemplo: "necesito pantalones baggy" -> ya tenes tipo_prenda \
  (pantalon) y corte (baggy) -> buscas directo, sin preguntar nada mas, aunque no sepas el color ni el \
  presupuesto.
- Si nombro la prenda pero NO te dio el corte/ajuste, y el pedido trae \
  contexto (ej: una ocasion, "para el matrimonio de mi hermano"), actua como un \
  vendedor de tienda con buen ojo, no como un formulario: haz 2-3 preguntas CONCRETAS y especificas a \
  ESA prenda, en tono natural y en la misma respuesta -- nunca un generico "cuentame mas" o "que mas \
  buscas". Adapta las preguntas al tipo de prenda, por ejemplo:
  * Camisa: tono/color que prefiere, si la busca ajustada o mas suelta, presupuesto aproximado.
  * Pantalon: que corte (baggy, cargo, slim, recto), y si busca un tipo concreto (jeans, cargo, buzo -- \
    pasalo en el campo subtipo de la tool), si es para el dia a dia o para algo puntual.
  * Poleron o polera: ajustada u oversize, con o sin capucha (poleron), presupuesto aproximado.
  * Chaqueta: mas ajustada o mas suelta, y si tiene un estilo/material en mente (bomber, de mezclilla/\
    denim, de cuero -- pasalo en el campo subtipo de la tool), presupuesto aproximado.
  * Chaleco: mas ajustada o mas suelta, para que ocasion, presupuesto aproximado.
  Para otras prendas usa el mismo criterio: 2-3 preguntas que un vendedor de verdad haria para esa \
  prenda puntual, no una lista generica igual para todo. Si hay una sugerencia de hobby validada (ver el \
  bloque de reglas de hobby mas arriba en este prompt) que aplique a esta prenda, podes MENCIONARLA como \
  idea dentro de tus preguntas (ej: "ya que te gusta el rock, muchos buscan algo oversize con grafico \
  grande -- ¿te tinca eso o preferis otra onda?"), pero es solo una idea, nunca dejes de preguntar por el \
  corte real ni des la sugerencia por hecha.
- No hace falta esperar las 3 respuestas: apenas el usuario te de el corte/ajuste MAS otro dato util \
  (color, presupuesto, o el contexto de uso), llama la tool en esa misma respuesta -- no sigas \
  preguntando por el resto. Y si en su PRIMER mensaje ya trae 2 o mas de esos datos (ej: "camisa blanca \
  ajustada para un matrimonio, unos 25 lucas"), no preguntes nada: interpretalo directo y busca.
- Nunca preguntes la ocasion como pregunta aislada si el usuario ya la nombro -- usala para elegir que \
  preguntar (ej: si es un matrimonio, no hace falta preguntar si es formal o casual, ya se sabe que es \
  una ocasion especial) y para dar mejor consejo, no para armar otra pregunta mas.
- Si el corte/ajuste que te den no calza exacto con un valor conocido (baggy, boxy fit, slim fit, \
  oversize, skinny, regular fit, straight), interpretalo al mas parecido -- nunca le pidas que elija de \
  una lista tecnica, hablale como persona.
- Si mencionan un presupuesto, pasalo en presupuesto_max de la tool (numero entero en CLP). El catalogo \
  SI filtra de verdad por precio maximo -- pero NO tiene datos de color cargados por prenda (fuera de \
  gorros), asi que si te dijeron un color, usalo para conversar y para comentar los resultados, pero \
  nunca prometas que la busqueda filtro por ese color -- se honesto si esa info no esta en el catalogo.

Si eligen "gorro", tambien pueden pedir una forma concreta (gorro curvo, gorro plano, o gorro de \
lana/beanie) -- si la mencionan, pasala en el campo forma_gorro de la tool; si no la mencionan, dejala \
vacia (se buscan las 3 formas).

Si el pedido es mas abierto o exploratorio (ej: "no se que ponerme", "que me combina para el carrete"), \
conversa un poco primero para entender el contexto (ocasion, que tiene, que le gusta) antes de sugerir \
una busqueda -- en una conversacion asi, NUNCA llames la tool en el primer mensaje.

Si en ningun momento de la conversacion la persona nombro un tipo de prenda concreto (polera, poleron, \
camisa, chaqueta, chaleco, camiseta, top, pantalon, short, falda, o gorro), NO llames la tool adivinando \
cual -- preguntale directamente cual de esas prendas quiere, con un par de ejemplos, antes de buscar.

Cuando te pidan ayuda para combinar una prenda que ya tienen (ej: "que me combino con una camisa \
cuadrille y jeans negros"), da SIEMPRE minimo 2-3 alternativas distintas y variadas (distintos estilos o \
prendas), nunca una sola recomendacion -- la idea es que la persona elija, no imponerle un solo look. \
Formatea cada opcion como un item numerado con su titulo en negrita (ej: "1. **Streetwear clasico:** \
..."), con una linea en blanco entre cada opcion, para que se lea como una lista clara, no como un \
parrafo corrido. Despues de dar las opciones, termina preguntando si la persona ya tiene alguna de esas \
prendas o si quiere que le busques opciones reales del catalogo. Si te dice que quiere buscar, fijate \
que opcion eligio -- si esa opcion nombra mas de una prenda (ej: poleron + pantalon), pregunta cual de \
esas dos quiere buscar primero -- y ahi segui el proceso normal (interpreta tipo de prenda y corte, \
llama sugerir_busqueda).

Si la app te avisa que encontro la prenda pero no en la talla de la persona (mensaje que termina \
preguntando si quiere verla igual en otras tallas) y la persona responde que si, llama sugerir_busqueda \
de nuevo con los mismos datos de esa prenda MAS ignorar_talla=true -- asi no se le vuelve a preguntar \
lo mismo. Si dice que no, no vuelvas a ofrecerle esa misma prenda sin que ella lo pida de nuevo.

Nunca termines una respuesta dejando a la persona sin ningun camino para seguir. Si el catalogo no \
tiene lo que busca, o la busqueda no funciono, no te quedes en un simple "no encontre nada" -- ofrece \
seguir ajustando la busqueda (ej: "¿probamos con otro corte, otro color, o lo que prefieras?"), para que \
la conversacion siga sin que tenga que reabrir el chat.

No llames la herramienta si todavia no diste ningun consejo o si la persona no parece lista para buscar."""

KOKO_TOOL_SUGERIR_BUSQUEDA = {
    "name": "sugerir_busqueda",
    "description": (
        "Propone activar el buscador real de la app con una prenda (y opcionalmente un corte) "
        "concretos, despues de haber dado consejo de estilo en la conversacion."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "categoria": {
                "type": "string",
                "enum": ["prenda superior", "prenda inferior", "gorro"],
            },
            "tipo_prenda": {
                "type": "string",
                "enum": list(TIPOS_PRENDA_CONOCIDOS.keys()),
            },
            "corte": {
                "type": "string",
                "enum": list(CORTES_CONOCIDOS.keys()),
            },
            "forma_gorro": {
                "type": "string",
                "description": "Solo si categoria es 'gorro' y la persona pidio una forma concreta.",
                "enum": FORMAS_GORRO_CONOCIDAS,
            },
            "subtipo": {
                "type": "string",
                "description": (
                    "Solo si tipo_prenda es 'pantalon', 'shorts', 'top' o 'chaqueta' Y la persona pidio "
                    "una variante concreta (ej. pantalon de 'jeans'/'cargo'/'buzo', chaqueta 'bomber'/"
                    "'mezclilla'(tambien dicha 'denim' o de 'jean')/'cuero'). Si no la menciono, dejalo vacio."
                ),
                "enum": list(SUBTIPOS_CONOCIDOS.keys()),
            },
            "presupuesto_max": {
                "type": "integer",
                "description": (
                    "Solo si la persona menciono un presupuesto o tope de precio (ej: 'unos 30 mil', "
                    "'no mas de 25 lucas'). Numero entero en pesos chilenos (CLP), sin puntos ni "
                    "simbolo (ej: 30000). El catalogo SI filtra por esto de verdad -- nunca inventes "
                    "un numero que la persona no dijo."
                ),
            },
            "ignorar_talla": {
                "type": "boolean",
                "description": (
                    "Poner en true SOLO cuando ya le avisaste a la persona que no habia stock en su "
                    "talla y ella confirmo que igual quiere ver las opciones en otras tallas. En "
                    "cualquier otro caso, dejalo en false (o no lo mandes)."
                ),
            },
        },
        "required": ["categoria", "tipo_prenda"],
    },
}


def _sugerencia_candidatos_catalogo(sugerencia, catalog=None):
    catalog = load_json(CATALOG_PATH) if catalog is None else catalog
    catalog = filtrar_gorros_por_forma(catalog, sugerencia.get("forma_gorro", ""))
    texto_pedido = f'{sugerencia.get("tipo_prenda", "")} {sugerencia.get("corte", "")} {sugerencia.get("subtipo", "")}'
    return elegir_candidatos(
        "", texto_pedido, catalog, cantidad=CANTIDAD_RESULTADOS,
        categoria_pedida=sugerencia.get("categoria", ""),
    )


def _sugerencia_calza_con_catalogo(sugerencia):
    candidatos = _sugerencia_candidatos_catalogo(sugerencia)
    if not candidatos:
        return False
    tipo_prenda = sugerencia.get("tipo_prenda", "").lower()
    return all(p["categoria"].lower() == tipo_prenda for p in candidatos)


def _sugerencia_disponible_en_talla(sugerencia, tallas_usuario):
    if not tallas_usuario:
        return True
    catalog = filtrar_por_talla(load_json(CATALOG_PATH), tallas_usuario)
    return bool(_sugerencia_candidatos_catalogo(sugerencia, catalog))


def _texto_reglas_para_prompt(reglas):
    lineas = []
    for regla in reglas.get("reglas", []):
        atributos = ", ".join(regla.get("atributos", []))
        lineas.append(f'- {regla["genero"]} + {regla["ocasion"]} + {regla["prenda"]}: {atributos}')
    return "\n".join(lineas) if lineas else "(sin reglas validadas todavia)"


def _bloque_hobbies_para_prompt(hobbies, generos_musicales, deportes_subtipo=None):
    reglas_hobby = _reglas_hobby_usuario(hobbies, generos_musicales, deportes_subtipo)
    if not reglas_hobby:
        return (
            "Todavia no hay ninguna sugerencia de estilo validada para los hobbies de este usuario (o "
            "no tiene hobbies cargados en su perfil) -- NO le atribuyas ningun gusto musical o de "
            "estilo que no haya dicho el mismo en la conversacion. Nunca inventes una asociacion "
            "hobby->estilo que no este en esta lista."
        )
    lineas = []
    for regla in reglas_hobby:
        prendas = " o ".join(sorted(regla["prenda_preferida"]))
        if regla.get("tipo_sugerencia") == "accesorio":
            lineas.append(f'- Sobre {prendas}: {regla["nota"]}.')
        else:
            lineas.append(
                f'- Si busca {prendas}: podes mencionar como IDEA un corte "{regla["corte"]}", color base '
                f'{regla["color_base"]}. {regla["nota"]}. Para cualquier otra prenda que no sea esa, esta '
                "sugerencia no aplica."
            )
    hobbies_texto = ", ".join(sorted({r["etiqueta"] for r in reglas_hobby}))
    return (
        f"Este usuario eligio en su perfil que le gusta {hobbies_texto}. Con eso, tenes esta(s) "
        'sugerencia(s) de estilo OPCIONAL(ES) -- validada(s) por el dueño del proyecto (confianza '
        '"validacion_inicial": referencias visuales, no una encuesta a muchas personas), pero SOLO una '
        "idea, nunca una regla dura ni un dato que ya tengas confirmado:\n" + "\n".join(lineas) + "\n\n"
        "Como usarlas: si la prenda que busca la persona calza con alguna, podes MENCIONARLA como idea "
        'dentro de tu respuesta (ej: "como te gusta el rock, muchos buscan algo oversize con gráfico '
        'grande, ¿te tinca eso o preferis otra onda?"). Nunca la des por confirmada ni te saltees '
        "preguntar el corte real -- segui siempre el proceso normal de preguntas (ver mas abajo en este "
        "prompt), esto es solo un plus conversacional. SIEMPRE prioriza lo que el usuario diga "
        'explicitamente en la conversacion por sobre esta sugerencia (ej: si pide algo con "diseño '
        'chico" o un corte distinto, seguí lo que pidió). Nunca prometas que la búsqueda filtró por '
        "color o estampado -- el catálogo no tiene esos datos cargados por prenda (fuera de gorro y "
        "chaqueta), así que color_base/la nota son solo para que converses con criterio, nunca una "
        "promesa de filtro real."
    )


def _resumen_perfil_para_prompt(perfil, tallas_usuario):
    genero = _texto_seguro(perfil.get("genero"))
    edad = _texto_seguro(perfil.get("edad", ""))
    altura = _texto_seguro(perfil.get("altura", ""))
    peso = _texto_seguro(perfil.get("peso", ""))
    partes = []
    if genero:
        partes.append(f"genero {genero}")
    if edad:
        partes.append(f"{edad} anos")
    if altura:
        partes.append(f"{altura}m de altura")
    if peso:
        partes.append(f"{peso}kg")
    if not partes:
        return (
            "Este usuario todavia no cargo datos de perfil (genero/edad/altura/peso) -- no asumas "
            "ninguno, pregunta si hace falta para dar un consejo mas preciso."
        )
    texto = "Datos de perfil que ya dio el usuario (no se los vuelvas a preguntar): " + ", ".join(partes) + "."
    if tallas_usuario:
        extra = f" (o {tallas_usuario[1]})" if len(tallas_usuario) > 1 else ""
        texto += f" Talla estimada: {tallas_usuario[0]}{extra}."
    return texto


def _resumen_favoritos_para_prompt(email):
    favoritos = obtener_favoritos(email)
    if not favoritos:
        return None
    nombres = [f'{f.get("nombre", "")} ({f.get("tienda", "")})' for f in favoritos[-8:] if f.get("nombre")]
    if not nombres:
        return None
    return f"Tiene {len(favoritos)} producto(s) guardados como favoritos, los mas recientes: {', '.join(nombres)}."


def construir_system_prompt_koko(
    email, reglas, hobbies=None, generos_musicales=None, deportes_subtipo=None, perfil=None, tallas_usuario=None,
):
    resumen = resumen_historial_para_prompt(email)
    if resumen:
        bloque_historial = (
            "Historial de este usuario en la app (usalo para personalizar tu consejo, y MENCIONA "
            'explicitamente por que recomiendas algo en base a esto, ej: "como sueles preferir '
            f'oversize..."): {resumen}'
        )
    else:
        bloque_historial = (
            "Este usuario todavia no tiene historial en la app (es nuevo o no ha buscado nada) -- "
            "da consejo general basado en las reglas de arriba, sin inventar gustos que no conoces."
        )
    favoritos_texto = _resumen_favoritos_para_prompt(email) or (
        "Este usuario todavia no tiene ningun favorito guardado -- no asumas que tiene alguno."
    )
    return KOKO_SYSTEM_PROMPT_BASE.format(
        reglas=_texto_reglas_para_prompt(reglas), historial=bloque_historial,
        hobbies=_bloque_hobbies_para_prompt(hobbies, generos_musicales, deportes_subtipo),
        perfil=_resumen_perfil_para_prompt(perfil or {}, tallas_usuario or []),
        favoritos=favoritos_texto,
    )
