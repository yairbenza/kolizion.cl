import json
import re
from pathlib import Path

from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
CATALOG_PATH = BASE_DIR / "data" / "catalog.json"
REGLAS_PATH = BASE_DIR / "data" / "reglas_streetwear.json"

# Cuantos productos mostrar por busqueda (primaria y "mostrar mas
# opciones"), mientras se usa catalogo de prueba. La regla de "sin
# consenso" (2-3 alternativas) es aparte -- esa cantidad viene de una
# decision de trabajo documentada en CLAUDE.md, no de este numero.
CANTIDAD_RESULTADOS = 5


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def texto_producto(producto):
    return " ".join(
        [
            producto["nombre"],
            producto["categoria"],
            producto.get("descripcion", ""),
            " ".join(producto.get("ocasiones", [])),
            " ".join(producto.get("tags", [])),
        ]
    ).lower()


def formatear_producto(producto, razon, tallas_usuario=None):
    # De las 1-2 tallas estimadas para el usuario, TODAS las que este
    # producto en particular tenga en stock (nunca una que no tenga).
    tallas_coincidentes = []
    if tallas_usuario:
        disponibles = set(producto.get("tallas_disponibles", []))
        tallas_coincidentes = [t for t in ORDEN_TALLAS if t in tallas_usuario and t in disponibles]
    return {
        "nombre": producto["nombre"],
        "marca": producto.get("marca", ""),
        "tienda": producto["tienda"],
        "precio": producto.get("precio", ""),
        "descripcion": producto.get("descripcion", ""),
        "link": producto["link"],
        "razon": razon,
        "tallas_coincidentes": tallas_coincidentes,
    }


# Agrupa las categorias del catalogo en los 2 grupos que se preguntan en el
# formulario ("prenda superior" / "prenda inferior"). Si el usuario elige
# uno de estos, la busqueda descarta primero cualquier producto que no sea
# de ese grupo.
CATEGORIA_GRUPOS = {
    "prenda superior": ["poleron", "camisa", "chaqueta", "polera", "chaleco", "camiseta", "top"],
    "prenda inferior": ["pantalon", "falda", "shorts", "faldacargo", "bikeshorts"],
}

# Tipos de corte conocidos. Si el pedido menciona uno de estos, la busqueda
# descarta primero cualquier prenda que no tenga ese corte marcado en sus
# tags -- para que "boxy fit" nunca traiga algo "baggy" ni viceversa.
CORTES_CONOCIDOS = {
    "baggy": ["baggy"],
    "boxy fit": ["boxy fit", "boxyfit", "boxy"],
    "slim fit": ["slim fit", "slimfit", "slim"],
    "oversize": ["oversize", "oversized"],
    "skinny": ["skinny"],
    "regular fit": ["regular fit"],
    "straight": ["straight fit", "straight", "recto"],
}


# Tipos de prenda conocidos (deben coincidir con el campo "categoria" del
# catalogo). Si el pedido menciona uno de estos, la busqueda descarta
# primero cualquier producto que no sea exactamente de ese tipo -- esta es
# la prioridad 1 de la busqueda, y nunca se relaja (ni en "mostrar mas
# opciones"): si alguien busca "polera", nunca debe aparecer un poleron.
#
# IMPORTANTE sobre el orden: se revisa en el orden en que estan escritos
# aqui abajo, y se queda con el PRIMER tipo que calce. "faldacargo" y
# "bikeshorts" van antes que "falda"/"shorts" porque contienen esas
# palabras completas dentro de su propia frase (si el generico se revisara
# primero, nunca se detectaria el especifico).
#
# Nota sobre "top": antes "top" era sinonimo de "polera" (por la regla
# validada que dice "polera/top"). Ahora "top" es su propio tipo (con
# subtipos: crop top, baby tee, halter, corset, tank top, camisas/blusas),
# asi que se le saco "top" a la lista de polera. Orden critico con "top":
# - "polera" ANTES que "top": el texto de la regla validada trae las dos
#   palabras juntas ("polera/top"), y necesitamos que gane "polera" ahi.
# - "top" ANTES que "poleron": el subtipo "Crop top / Crop hoodie" contiene
#   la palabra "hoodie" (clave de poleron), y si poleron se revisara antes
#   se detectaria por error "poleron" en vez de "top" cuando alguien
#   selecciona ese subtipo dentro de Top.
TIPOS_PRENDA_CONOCIDOS = {
    "faldacargo": ["falda cargo", "cargo skirt", "faldacargo"],
    "bikeshorts": ["bike shorts", "shorts ciclista", "bikeshorts", "ciclista"],
    "polera": ["polera"],
    "top": ["top"],
    "poleron": ["poleron", "hoodie"],
    "camisa": ["camisa"],
    "camiseta": ["camiseta"],
    "chaqueta": ["chaqueta"],
    "chaleco": ["chaleco"],
    "pantalon": ["pantalon"],
    "shorts": ["shorts", "short"],
    "falda": ["falda"],
    "jockey": ["jockey", "gorra"],
    "accesorio": ["accesorio", "mochila", "cinturon"],
}

# Subtipos conocidos de pantalon/shorts/top (deben coincidir con el campo
# "subtipo" del catalogo). Igual que el tipo de prenda, es un filtro
# estricto que nunca se relaja: si piden "pantalon de jeans", nunca debe
# aparecer un pantalon cargo.
SUBTIPOS_CONOCIDOS = {
    "buzo": ["buzo", "jogger"],
    "jeans": ["jeans", "denim"],
    "cargo": ["cargo"],
    "tela": ["tela"],
    "bano": ["bano", "baño"],
    "croptop": ["crop top", "crop hoodie", "croptop"],
    "babytee": ["baby tee", "babytee"],
    "halter": ["halter", "top con breteles", "breteles"],
    "corset": ["corset", "top estructurado"],
    "tanktop": ["tank top", "tanktop", "musculosa"],
    "blusa": ["blusa", "camisas/blusas", "camisas / blusas"],
}

# Tipos de prenda "top" (independiente del corte -- una prenda puede ser
# oversize Y crop al mismo tiempo). Solo se pregunta/filtra por largo en
# estos tipos.
TIPOS_CON_LARGO = {"polera", "camiseta", "top"}

# Largo conocido. Igual que el corte, es un filtro estricto que nunca se
# relaja. Ojo: "normal" solo se detecta como frase "largo normal" completa
# (no la palabra "normal" sola), para que no calce por accidente con texto
# random que use esa palabra tan comun por otro motivo.
LARGOS_CONOCIDOS = {
    "crop": ["crop", "corto"],
    "normal": ["largo normal"],
    "extra largo": ["extra largo", "longline"],
}

# Manga: solo aplica a "polera". Independiente del corte -- una polera
# puede ser oversize Y manga larga al mismo tiempo. Filtro estricto, nunca
# se relaja.
MANGAS_CONOCIDAS = {
    "larga": ["manga larga", "mangas largas"],
    "corta": ["manga corta", "mangas cortas"],
}

# Capucha y cierre: solo aplican a "poleron". Son dos preguntas
# independientes entre si y del corte. Ojo: se usan las frases completas
# "con capucha"/"sin capucha" (nunca la palabra "capucha" sola), porque
# "capucha" sola aparece tanto en "con capucha" como en "sin capucha" y
# calzaria con las dos por igual.
CAPUCHAS_CONOCIDAS = {
    "con capucha": ["con capucha"],
    "sin capucha": ["sin capucha"],
}
CIERRES_CONOCIDOS = {
    "con cierre": ["con cierre"],
    "sin cierre": ["sin cierre", "crewneck"],
}


def _contiene_palabra(texto, variante):
    """Busca 'variante' como palabra (o frase) completa dentro de 'texto',
    nunca como fragmento de otra palabra -- ej: la palabra "la" no debe
    calzar solo porque el texto contiene "blancas"."""
    return re.search(rf"\b{re.escape(variante)}\b", texto) is not None


def tokenizar(texto):
    """Separa un texto en las palabras que realmente lo componen (sin
    tildes/comas/slashes pegados), para poder comparar palabra por palabra
    en vez de buscar un fragmento de texto dentro de otro."""
    return set(re.findall(r"[a-záéíóúñ0-9]+", texto.lower()))


def _detectar(texto_pedido, conocidos):
    """Escanea texto_pedido buscando alguna de las frases de 'conocidos'
    (dict: nombre canonico -> lista de variantes). Devuelve el nombre
    canonico de la primera que calce, o None si no se menciono ninguna."""
    texto = texto_pedido.lower()
    for canonico, variantes in conocidos.items():
        if any(_contiene_palabra(texto, variante) for variante in variantes):
            return canonico
    return None


def detectar_corte_pedido(texto_pedido):
    """Revisa si el pedido menciona un corte especifico (ej: "boxy fit")."""
    return _detectar(texto_pedido, CORTES_CONOCIDOS)


def detectar_tipo_prenda(texto_pedido):
    """Revisa si el pedido menciona un tipo de prenda especifico (ej:
    "polera"), igual al campo "categoria" del catalogo."""
    return _detectar(texto_pedido, TIPOS_PRENDA_CONOCIDOS)


def detectar_largo_pedido(texto_pedido):
    """Revisa si el pedido menciona un largo especifico (ej: "crop",
    "extra largo")."""
    return _detectar(texto_pedido, LARGOS_CONOCIDOS)


def detectar_subtipo_pedido(texto_pedido):
    """Revisa si el pedido menciona un subtipo de pantalon/shorts/top
    especifico (ej: "cargo", "jeans", "corset")."""
    return _detectar(texto_pedido, SUBTIPOS_CONOCIDOS)


def detectar_manga_pedido(texto_pedido):
    """Revisa si el pedido menciona un largo de manga (solo aplica a
    "polera"): "larga" o "corta"."""
    return _detectar(texto_pedido, MANGAS_CONOCIDAS)


def detectar_capucha_pedido(texto_pedido):
    """Revisa si el pedido menciona capucha (solo aplica a "poleron"):
    "con capucha" o "sin capucha"."""
    return _detectar(texto_pedido, CAPUCHAS_CONOCIDAS)


def detectar_cierre_pedido(texto_pedido):
    """Revisa si el pedido menciona cierre (solo aplica a "poleron"):
    "con cierre" o "sin cierre" (crewneck)."""
    return _detectar(texto_pedido, CIERRES_CONOCIDOS)


def filtrar_por_precio(catalog, precio_pedido):
    """Filtra el catalogo segun la opcion de precio elegida en el
    formulario. Es un filtro estricto que se aplica ANTES que cualquier otra
    busqueda, y nunca se relaja (ni en "mostrar mas opciones"):
    - "" (cualquier precio): no filtra nada.
    - "oferta": deja solo productos marcados como en oferta.
    - un numero (ej: "50000"): deja productos con precio_clp menor o igual.
    """
    valor = (precio_pedido or "").strip().lower()
    if not valor:
        return catalog
    if valor == "oferta":
        return [p for p in catalog if p.get("en_oferta")]
    try:
        tope = int(valor)
    except ValueError:
        return catalog
    return [p for p in catalog if p.get("precio_clp", 0) <= tope]


# Topes de peso (kg) y altura (m) de cada talla, por genero. Son rangos
# orientativos, no una tabla exacta. "unisex"/otro usa el promedio de mujer
# y hombre.
LIMITES_PESO_KG = {
    "mujer": {"S": 60, "M": 70, "L": 80},
    "hombre": {"S": 68, "M": 80, "L": 92},
}
LIMITES_ALTURA_M = {
    "mujer": {"S": 1.65, "M": 1.70, "L": 1.75},
    "hombre": {"S": 1.70, "M": 1.78, "L": 1.85},
}

ORDEN_TALLAS = ["S", "M", "L", "XL"]


def _limites(tabla, genero):
    genero = (genero or "").strip().lower()
    if genero in tabla:
        return tabla[genero]
    # unisex u otro: promedio de ambas tablas, como aproximacion neutra.
    mujer, hombre = tabla["mujer"], tabla["hombre"]
    return {t: (mujer[t] + hombre[t]) / 2 for t in mujer}


def _talla_por_valor(valor, limites):
    """Ubica un valor (peso o altura) en su talla segun los 3 topes
    (S/M/L); lo que quede por encima del tope de L es XL."""
    if valor <= limites["S"]:
        return "S"
    if valor <= limites["M"]:
        return "M"
    if valor <= limites["L"]:
        return "L"
    return "XL"


def _talla_vecina(talla):
    """La talla inmediatamente mas grande (o mas chica si ya es XL)."""
    idx = ORDEN_TALLAS.index(talla)
    if idx < len(ORDEN_TALLAS) - 1:
        return ORDEN_TALLAS[idx + 1]
    if idx > 0:
        return ORDEN_TALLAS[idx - 1]
    return None


def _parsear_numero(texto):
    """Saca el primer numero de un texto libre (ej: "70kg" -> 70.0)."""
    match = re.search(r"\d+([.,]\d+)?", texto or "")
    if not match:
        return None
    return float(match.group().replace(",", "."))


def _parsear_altura_m(texto):
    """Como _parsear_numero, pero normaliza a metros (ej: "175cm" -> 1.75;
    "1.75m" -> 1.75)."""
    valor = _parsear_numero(texto)
    if valor is None:
        return None
    return valor / 100 if valor > 10 else valor


def estimar_tallas(genero, peso_texto, altura_texto):
    """Estima la talla del usuario cruzando altura y peso (datos que ya
    pide el formulario -- no se agrega ninguna pregunta nueva de talla).
    Calcula una talla por cada dato por separado y usa la MAS CHICA de las
    dos como principal (para no ofrecer algo mas ajustado de lo que
    corresponde); la otra talla calculada queda como segunda opcion. Si
    ambos datos dan la misma talla, la segunda opcion es la vecina mas
    grande (o mas chica si ya es XL). Devuelve [] si no hay ni peso ni
    altura validos."""
    peso = _parsear_numero(peso_texto)
    altura = _parsear_altura_m(altura_texto)
    if peso is None and altura is None:
        return []

    talla_peso = _talla_por_valor(peso, _limites(LIMITES_PESO_KG, genero)) if peso is not None else None
    talla_altura = _talla_por_valor(altura, _limites(LIMITES_ALTURA_M, genero)) if altura is not None else None

    if talla_peso and talla_altura:
        principal, otra = sorted([talla_peso, talla_altura], key=ORDEN_TALLAS.index)
        if principal == otra:
            vecina = _talla_vecina(principal)
            return [principal, vecina] if vecina else [principal]
        return [principal, otra]

    talla_unica = talla_peso or talla_altura
    vecina = _talla_vecina(talla_unica)
    return [talla_unica, vecina] if vecina else [talla_unica]


def filtrar_por_talla(catalog, tallas_usuario):
    """Filtra el catalogo dejando solo productos que tengan stock en AL
    MENOS UNA de las tallas estimadas. Si no se pudo estimar ninguna talla
    (ej: no hay dato de peso), no filtra nada."""
    if not tallas_usuario:
        return catalog
    return [
        p for p in catalog
        if any(t in p.get("tallas_disponibles", []) for t in tallas_usuario)
    ]


def buscar_regla(genero, ocasion, reglas, niveles):
    """Busca una regla que calce con genero + ocasion y cuya confianza este
    dentro del set 'niveles' (ej: {"alta"} o {"media"})."""
    genero = (genero or "").strip().lower()
    ocasion = (ocasion or "").strip().lower()
    for regla in reglas.get("reglas", []):
        if (
            regla["genero"].strip().lower() == genero
            and regla["ocasion"].strip().lower() == ocasion
            and regla.get("confianza") in niveles
        ):
            return regla
    return None


def elegir_candidatos(
    genero, texto_pedido, catalog, cantidad, categoria_pedida=None, permitir_otros_cortes=False
):
    """Filtra por genero (o unisex); despues por tipo de prenda (prioridad 1)
    y por corte (prioridad 2); al final ordena por cuantas palabras del
    pedido aparecen en cada producto.

    Prioridad 1 (tipo de prenda): si el pedido menciona una prenda concreta
    (ej: "polera"), o si no la menciona pero se eligio un grupo conocido del
    formulario (ej: "prenda inferior"), el filtro es estricto y NUNCA se
    relaja, ni siquiera en "mostrar mas opciones".

    Prioridad 2 (corte/ajuste): si el pedido menciona un corte (ej:
    "baggy"), el filtro tambien es estricto -- excepto cuando
    permitir_otros_cortes=True (Plan B) y no queda ningun producto de ese
    corte, en cuyo caso se muestran otros ajustes en vez de dejar la
    busqueda vacia.
    """
    genero = (genero or "").strip().lower()
    candidatos = [
        p for p in catalog if p["genero"].lower() in (genero, "unisex")
    ] or catalog

    tipo_prenda = detectar_tipo_prenda(texto_pedido)
    if tipo_prenda:
        # Filtro estricto (prioridad 1): nunca se relaja, ni en el Plan B.
        candidatos = [p for p in candidatos if p["categoria"].lower() == tipo_prenda]
    else:
        grupo = CATEGORIA_GRUPOS.get((categoria_pedida or "").strip().lower())
        if grupo:
            candidatos = [p for p in candidatos if p["categoria"].lower() in grupo]

    # El subtipo solo aplica a pantalon/shorts/top -- si no, palabras sueltas
    # de otras reglas (ej: "tela transpirable" en la regla de poleras)
    # podrian calzar por error con una palabra clave de subtipo (ej: "tela").
    if tipo_prenda in ("pantalon", "shorts", "top"):
        subtipo_pedido = detectar_subtipo_pedido(texto_pedido)
        if subtipo_pedido:
            # Filtro estricto (igual que tipo de prenda): nunca se relaja.
            candidatos = [p for p in candidatos if p.get("subtipo", "").lower() == subtipo_pedido]

    # El largo solo aplica a prendas tipo "top" (ver TIPOS_CON_LARGO), y es
    # independiente del corte -- una prenda puede ser oversize Y crop al
    # mismo tiempo, asi que este filtro se suma al de corte, no lo reemplaza.
    if tipo_prenda in TIPOS_CON_LARGO:
        largo_pedido = detectar_largo_pedido(texto_pedido)
        if largo_pedido:
            # Filtro estricto (igual que tipo de prenda): nunca se relaja.
            candidatos = [p for p in candidatos if p.get("largo", "").lower() == largo_pedido]

    # Manga solo aplica a "polera"; capucha y cierre solo a "poleron". Los 3
    # son independientes del corte (una polera puede ser oversize Y manga
    # larga a la vez), asi que se suman al filtro de corte, no lo reemplazan.
    if tipo_prenda == "polera":
        manga_pedida = detectar_manga_pedido(texto_pedido)
        if manga_pedida:
            candidatos = [p for p in candidatos if p.get("manga", "").lower() == manga_pedida]

    if tipo_prenda == "poleron":
        capucha_pedida = detectar_capucha_pedido(texto_pedido)
        if capucha_pedida:
            candidatos = [p for p in candidatos if p.get("capucha", "").lower() == capucha_pedida]
        cierre_pedido = detectar_cierre_pedido(texto_pedido)
        if cierre_pedido:
            candidatos = [p for p in candidatos if p.get("cierre", "").lower() == cierre_pedido]

    corte_pedido = detectar_corte_pedido(texto_pedido)
    if corte_pedido:
        variantes = CORTES_CONOCIDOS[corte_pedido]
        candidatos_del_corte = [
            p for p in candidatos if any(_contiene_palabra(texto_producto(p), v) for v in variantes)
        ]
        if candidatos_del_corte or not permitir_otros_cortes:
            candidatos = candidatos_del_corte
        # si permitir_otros_cortes=True y no hay nada de ese corte, se
        # mantienen los candidatos sin filtrar por corte (otros ajustes).

    palabras_pedido = tokenizar(texto_pedido)

    def puntaje(producto):
        return len(palabras_pedido & tokenizar(texto_producto(producto)))

    return sorted(candidatos, key=puntaje, reverse=True)[:cantidad]


def armar_resultados(genero, ocasion, categoria, texto_pedido, catalog, reglas, tallas_usuario=None):
    """Busqueda primaria: solo usa reglas sin_consenso o de confianza alta.
    Las reglas de confianza media se reservan para el Plan B."""
    regla = buscar_regla(genero, ocasion, reglas, {"sin_consenso"})
    if regla:
        texto_extra = f'{regla.get("prenda", "")} streetwear urbano'
        candidatos = elegir_candidatos(
            genero, f"{texto_pedido} {texto_extra}", catalog, cantidad=3, categoria_pedida=categoria
        )
        razon = (
            f'Sin consenso claro para este caso todavia: {regla.get("nota", "")} '
            "Te mostramos varias alternativas para que elijas."
        )
        return [formatear_producto(p, razon, tallas_usuario) for p in candidatos]

    regla = buscar_regla(genero, ocasion, reglas, {"alta"})
    if regla:
        atributos_txt = ", ".join(regla.get("atributos", []))
        texto_extra = f'{regla.get("prenda", "")} {atributos_txt}'
        candidatos = elegir_candidatos(
            genero, f"{texto_pedido} {texto_extra}", catalog, cantidad=CANTIDAD_RESULTADOS, categoria_pedida=categoria
        )
        razon = (
            f'Segun una regla validada (confianza alta) para '
            f'{regla["genero"]} en "{regla["ocasion"]}": buscamos {atributos_txt}.'
        )
        return [formatear_producto(p, razon, tallas_usuario) for p in candidatos]

    candidatos = elegir_candidatos(genero, texto_pedido, catalog, cantidad=CANTIDAD_RESULTADOS, categoria_pedida=categoria)
    return [
        formatear_producto(
            p,
            "Resultado de prueba (sin regla validada todavia): coincide con la "
            f'categoria "{p["categoria"]}" del catalogo urbano.',
            tallas_usuario,
        )
        for p in candidatos
    ]


def buscar_plan_b(genero, ocasion, categoria, texto_pedido, catalog, reglas, tallas_usuario=None):
    """Se llama cuando el usuario dice que la busqueda primaria no le sirvio.
    Usa la regla de confianza media si existe; si no, amplia el buscador
    simple mostrando los siguientes mejores candidatos del catalogo."""
    regla = buscar_regla(genero, ocasion, reglas, {"media"})
    if regla:
        atributos_txt = ", ".join(regla.get("atributos", []))
        texto_extra = f'{regla.get("prenda", "")} {atributos_txt}'
        candidatos = elegir_candidatos(
            genero, f"{texto_pedido} {texto_extra}", catalog, cantidad=CANTIDAD_RESULTADOS,
            categoria_pedida=categoria, permitir_otros_cortes=True,
        )
        razon = (
            f'Opcion alternativa (confianza media) para '
            f'{regla["genero"]} en "{regla["ocasion"]}": buscamos {atributos_txt}.'
        )
        return [formatear_producto(p, razon, tallas_usuario) for p in candidatos]

    # Para no repetir lo que ya se mostro en la busqueda primaria, primero
    # calculamos esos mismos resultados (busqueda estricta) y los excluimos
    # de la lista ampliada (permitir_otros_cortes=True). Asi, si la primaria
    # no mostro nada (ej: no habia nada "boxy fit"), el Plan B parte mostrando
    # desde el primer resultado en vez de saltarse resultados que nunca se
    # mostraron.
    primarios = elegir_candidatos(genero, texto_pedido, catalog, cantidad=CANTIDAD_RESULTADOS, categoria_pedida=categoria)
    ids_ya_mostrados = {p["id"] for p in primarios}
    candidatos = [
        p
        for p in elegir_candidatos(
            genero, texto_pedido, catalog, cantidad=len(catalog),
            categoria_pedida=categoria, permitir_otros_cortes=True,
        )
        if p["id"] not in ids_ya_mostrados
    ][:CANTIDAD_RESULTADOS]
    return [
        formatear_producto(
            p,
            "Mas opciones del catalogo urbano (sin regla validada todavia) que "
            f'coinciden con la categoria "{p["categoria"]}".',
            tallas_usuario,
        )
        for p in candidatos
    ]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/resultados")
def resultados():
    # La pagina en si es solo el molde -- los resultados los deja guardados
    # script.js en sessionStorage antes de mandar aca, y resultados.js los
    # lee y los dibuja al cargar.
    return render_template("resultados.html")


@app.route("/api/recommend", methods=["POST"])
def recommend():
    data = request.get_json()
    catalog = load_json(CATALOG_PATH)
    reglas = load_json(REGLAS_PATH)
    modo = data.get("modo")
    plan_b = bool(data.get("plan_b"))
    categoria = data.get("categoria", "")
    tipo_prenda = data.get("tipo_prenda", "")
    subtipo = data.get("subtipo", "")
    largo = data.get("largo", "")
    manga = data.get("manga", "")
    capucha = data.get("capucha", "")
    cierre = data.get("cierre", "")
    corte = data.get("corte", "")
    ocasion = data.get("ocasion", "")
    precio = data.get("precio", "")

    catalog = filtrar_por_precio(catalog, precio)

    campos_pedido = [categoria, tipo_prenda, subtipo, largo, manga, capucha, cierre, corte, ocasion]
    if modo == "yo":
        perfil = data.get("perfil") or {}
        genero = perfil.get("genero")
        peso = perfil.get("peso", "")
        altura = perfil.get("altura", "")
        texto_pedido = " ".join([perfil.get("hobbie", "")] + campos_pedido)
    else:
        genero = data.get("genero")
        peso = data.get("peso", "")
        altura = data.get("altura", "")
        texto_pedido = " ".join(campos_pedido)

    # Talla: se infiere sola cruzando altura y peso que el usuario ya
    # ingreso -- no se agrega ninguna pregunta nueva de talla.
    tallas_usuario = estimar_tallas(genero, peso, altura)
    catalog_con_talla = filtrar_por_talla(catalog, tallas_usuario)

    buscar_func = buscar_plan_b if plan_b else armar_resultados
    resultados = buscar_func(genero, ocasion, categoria, texto_pedido, catalog_con_talla, reglas, tallas_usuario)

    sin_talla = False
    if not resultados and tallas_usuario:
        # Si sin filtrar por talla SI habia resultados, el vacio es
        # especificamente por talla -- avisamos eso en vez de un vacio sin
        # explicacion.
        resultados_sin_talla = buscar_func(genero, ocasion, categoria, texto_pedido, catalog, reglas)
        sin_talla = bool(resultados_sin_talla)

    return jsonify({"recomendaciones": resultados, "sin_talla": sin_talla})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
