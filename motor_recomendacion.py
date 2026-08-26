import re
from constantes import (
    CANTIDAD_RESULTADOS,
    CATEGORIAS_CON_GRAMAJE,
    CATEGORIA_GRUPOS,
    CIERRES_CONOCIDOS,
    CAPUCHAS_CONOCIDAS,
    COLORES_GORRO_CONOCIDOS,
    COLORES_VIVOS_GORRO,
    CORTES_CONOCIDOS,
    EXCLUSIONES_HOBBY,
    FORMA_GORRO_CONOCIDA,
    FORMAS_GORRO_CONOCIDAS,
    GRAMAJE_MINIMO_CALIDAD_GSM,
    LARGOS_CONOCIDOS,
    LIMITES_ALTURA_M,
    LIMITES_PESO_KG,
    MANGAS_CONOCIDAS,
    MATERIALES_CONOCIDOS,
    ORDEN_TALLAS,
    REGLAS_HOBBY,
    SUBTIPOS_CONOCIDOS,
    SUBTIPOS_POR_TIPO_PRENDA,
    TIPOS_CON_LARGO,
    TIPOS_PRENDA_CONOCIDOS,
    _contiene_palabra,
    _detectar,
    _detectar_reciente,
    tokenizar,
)


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


def _material_es_natural(producto):
    info = MATERIALES_CONOCIDOS.get(producto.get("material", ""))
    return bool(info and info["natural"])


def _algodon_buena_calidad(producto):
    """'Buena calidad' definida por el usuario: polera o camiseta de
    algodon 100% con gramaje >= GRAMAJE_MINIMO_CALIDAD_GSM. Sin el dato
    cargado, o fuera de esas 2 categorias, nunca se considera 'buena
    calidad' (no se inventa un umbral para lo que no esta definido)."""
    if producto.get("categoria") not in CATEGORIAS_CON_GRAMAJE:
        return False
    if producto.get("material") != "algodon_100":
        return False
    gsm = producto.get("gramaje_gsm")
    return isinstance(gsm, (int, float)) and gsm >= GRAMAJE_MINIMO_CALIDAD_GSM


def _texto_gramaje(producto):
    """Texto para la ficha del producto (ej: '220 GSM -- algodón grueso de
    calidad'). Vacio si no hay gramaje cargado (la mayoria del catalogo,
    hasta que cada tienda lo mande)."""
    gsm = producto.get("gramaje_gsm")
    if not isinstance(gsm, (int, float)):
        return ""
    calidad = "algodón grueso de calidad" if gsm >= GRAMAJE_MINIMO_CALIDAD_GSM else "algodón liviano"
    return f"{int(gsm)} GSM — {calidad}"


def filtrar_por_marca_autor(catalog, solo_marca_autor):
    """"Mostrar solo marcas de autor / diseño independiente" -- a
    diferencia de "priorizar materiales" (nunca oculta nada), este filtro
    SI es estricto: el usuario pidio explicitamente "mostrar SOLO", asi que
    se aplica como cualquier otro filtro duro del buscador (precio, forma
    de gorro, etc.), antes de elegir_candidatos. No filtra nada si
    solo_marca_autor es False."""
    if not solo_marca_autor:
        return catalog
    return [p for p in catalog if p.get("marca_autor")]


def formatear_producto(producto, razon, tallas_usuario=None):
    tallas_coincidentes = []
    if tallas_usuario:
        disponibles = set(producto.get("tallas_disponibles", []))
        tallas_coincidentes = [t for t in ORDEN_TALLAS if t in tallas_usuario and t in disponibles]
    return {
        "nombre": producto["nombre"],
        "marca": producto.get("marca", ""),
        "tienda": producto["tienda"],
        "categoria": producto.get("categoria", ""),
        "corte": producto.get("corte", ""),
        "material": MATERIALES_CONOCIDOS.get(producto.get("material", ""), {}).get("etiqueta", ""),
        "gramaje_texto": _texto_gramaje(producto),
        "marca_autor": bool(producto.get("marca_autor", False)),
        "precio": producto.get("precio", ""),
        "precio_original": producto.get("precio_original", ""),
        "descuento_pct": producto.get("descuento_pct"),
        "descripcion": producto.get("descripcion", ""),
        "link": producto["link"],
        "razon": razon,
        "tallas_coincidentes": tallas_coincidentes,
        "imagen": producto.get("imagen", ""),
    }


def colores_permitidos_por_outfit(outfit):
    outfit = (outfit or "").strip().lower()
    if outfit == "oscuro":
        return COLORES_VIVOS_GORRO | {"blanco"}
    if outfit == "claro":
        return COLORES_VIVOS_GORRO | {"negro"}
    if outfit == "colorido":
        return {"negro", "blanco"}
    return set(COLORES_GORRO_CONOCIDOS)


def filtrar_gorros_por_color(catalog, camino, colores_elegidos, outfit):
    camino = (camino or "").strip().lower()
    if camino == "colores" and colores_elegidos:
        permitidos = {c.strip().lower() for c in colores_elegidos}
    elif camino == "outfit":
        permitidos = colores_permitidos_por_outfit(outfit)
    else:
        return catalog
    return [
        p for p in catalog
        if p.get("categoria", "").lower() != "gorro" or p.get("color_dominante", "").lower() in permitidos
    ]


def filtrar_gorros_por_forma(catalog, forma):
    forma = (forma or "").strip().lower()
    if forma not in FORMAS_GORRO_CONOCIDAS:
        return catalog
    return [
        p for p in catalog
        if p.get("categoria", "").lower() != "gorro" or p.get("forma", "").lower() == forma
    ]


def detectar_corte_pedido(texto_pedido):
    return _detectar(texto_pedido, CORTES_CONOCIDOS)


def detectar_tipo_prenda(texto_pedido):
    return _detectar(texto_pedido, TIPOS_PRENDA_CONOCIDOS)


def detectar_corte_pedido_conversacion(mensajes):
    return _detectar_reciente(mensajes, CORTES_CONOCIDOS)


def detectar_tipo_prenda_conversacion(mensajes):
    return _detectar_reciente(mensajes, TIPOS_PRENDA_CONOCIDOS)


def detectar_forma_gorro_conversacion(mensajes):
    return _detectar_reciente(mensajes, FORMA_GORRO_CONOCIDA)


def detectar_forma_gorro(texto_pedido):
    return _detectar(texto_pedido, FORMA_GORRO_CONOCIDA)


def detectar_largo_pedido(texto_pedido):
    return _detectar(texto_pedido, LARGOS_CONOCIDOS)


def _subtipos_validos_para(tipo_prenda):
    if tipo_prenda and tipo_prenda in SUBTIPOS_POR_TIPO_PRENDA:
        permitidos = SUBTIPOS_POR_TIPO_PRENDA[tipo_prenda]
        return {k: v for k, v in SUBTIPOS_CONOCIDOS.items() if k in permitidos}
    return SUBTIPOS_CONOCIDOS


def detectar_subtipo_pedido(texto_pedido, tipo_prenda=None):
    return _detectar(texto_pedido, _subtipos_validos_para(tipo_prenda))


def detectar_subtipo_pedido_conversacion(mensajes, tipo_prenda=None):
    return _detectar_reciente(mensajes, _subtipos_validos_para(tipo_prenda))


def detectar_manga_pedido(texto_pedido):
    return _detectar(texto_pedido, MANGAS_CONOCIDAS)


def detectar_capucha_pedido(texto_pedido):
    return _detectar(texto_pedido, CAPUCHAS_CONOCIDAS)


def detectar_cierre_pedido(texto_pedido):
    return _detectar(texto_pedido, CIERRES_CONOCIDOS)


def filtrar_por_precio(catalog, precio_pedido):
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


def _limites(tabla, genero):
    genero = (genero or "").strip().lower()
    if genero in tabla:
        return tabla[genero]
    mujer, hombre = tabla["mujer"], tabla["hombre"]
    return {t: (mujer[t] + hombre[t]) / 2 for t in mujer}


def _talla_por_valor(valor, limites):
    if valor <= limites["S"]:
        return "S"
    if valor <= limites["M"]:
        return "M"
    if valor <= limites["L"]:
        return "L"
    return "XL"


def _talla_vecina(talla):
    idx = ORDEN_TALLAS.index(talla)
    if idx < len(ORDEN_TALLAS) - 1:
        return ORDEN_TALLAS[idx + 1]
    if idx > 0:
        return ORDEN_TALLAS[idx - 1]
    return None


def _parsear_numero(texto):
    match = re.search(r"\d+([.,]\d+)?", texto or "")
    if not match:
        return None
    return float(match.group().replace(",", "."))


def _parsear_altura_m(texto):
    valor = _parsear_numero(texto)
    if valor is None:
        return None
    return valor / 100 if valor > 10 else valor


def estimar_tallas(genero, peso_texto, altura_texto):
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
    if not tallas_usuario:
        return catalog
    return [
        p for p in catalog
        if p.get("categoria", "").lower() == "gorro"
        or any(t in p.get("tallas_disponibles", []) for t in tallas_usuario)
    ]


def _categorias_deprioritizadas_por_hobby(hobbies, generos_musicales, deportes_subtipo=None):
    hobbies_norm = [(h or "").strip().lower() for h in (hobbies or [])]
    excluidas = set()
    for hobby in hobbies_norm:
        excluidas |= EXCLUSIONES_HOBBY.get((hobby, None), set())
    if "musica" in hobbies_norm:
        for genero in generos_musicales or []:
            excluidas |= EXCLUSIONES_HOBBY.get(("musica", (genero or "").strip().lower()), set())
    if "deportes" in hobbies_norm:
        for deporte in deportes_subtipo or []:
            excluidas |= EXCLUSIONES_HOBBY.get(("deportes", (deporte or "").strip().lower()), set())
    return excluidas


def _reglas_hobby_usuario(hobbies, generos_musicales, deportes_subtipo=None):
    hobbies_norm = [(h or "").strip().lower() for h in (hobbies or [])]
    reglas = []
    if "musica" in hobbies_norm:
        for genero in generos_musicales or []:
            reglas.extend(REGLAS_HOBBY.get(("musica", (genero or "").strip().lower()), []))
    if "deportes" in hobbies_norm:
        for deporte in deportes_subtipo or []:
            reglas.extend(REGLAS_HOBBY.get(("deportes", (deporte or "").strip().lower()), []))
    return reglas


def buscar_regla(genero, ocasion, reglas, niveles):
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
    genero, texto_pedido, catalog, cantidad, categoria_pedida=None, permitir_otros_cortes=False,
    priorizar_material_natural=False, categorias_deprioritizadas=None,
):
    genero = (genero or "").strip().lower()
    candidatos = [
        p for p in catalog if p["genero"].lower() in (genero, "unisex")
    ] or catalog

    tipo_prenda = detectar_tipo_prenda(texto_pedido)
    if tipo_prenda:
        candidatos = [p for p in candidatos if p["categoria"].lower() == tipo_prenda]
    else:
        grupo = CATEGORIA_GRUPOS.get((categoria_pedida or "").strip().lower())
        if grupo:
            candidatos = [p for p in candidatos if p["categoria"].lower() in grupo]

    if tipo_prenda in SUBTIPOS_POR_TIPO_PRENDA:
        subtipo_pedido = detectar_subtipo_pedido(texto_pedido, tipo_prenda)
        if subtipo_pedido:
            candidatos = [p for p in candidatos if p.get("subtipo", "").lower() == subtipo_pedido]

    if tipo_prenda in TIPOS_CON_LARGO:
        largo_pedido = detectar_largo_pedido(texto_pedido)
        if largo_pedido:
            candidatos = [p for p in candidatos if p.get("largo", "").lower() == largo_pedido]

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

    palabras_pedido = tokenizar(texto_pedido)

    def puntaje(producto):
        puntaje_palabras = len(palabras_pedido & tokenizar(texto_producto(producto)))
        categoria_producto = (producto.get("categoria") or "").lower()
        nivel_hobby = 0 if categoria_producto in (categorias_deprioritizadas or ()) else 1
        if priorizar_material_natural:
            return (
                nivel_hobby,
                1 if _material_es_natural(producto) else 0,
                1 if _algodon_buena_calidad(producto) else 0,
                puntaje_palabras,
            )
        return (nivel_hobby, puntaje_palabras)

    return sorted(candidatos, key=puntaje, reverse=True)[:cantidad]


def armar_resultados(
    genero, ocasion, categoria, texto_pedido, catalog, reglas, tallas_usuario=None,
    priorizar_material_natural=False, categorias_deprioritizadas=None,
):
    regla = buscar_regla(genero, ocasion, reglas, {"sin_consenso"})
    if regla:
        texto_extra = f'{regla.get("prenda", "")} streetwear urbano'
        candidatos = elegir_candidatos(
            genero, f"{texto_pedido} {texto_extra}", catalog, cantidad=3, categoria_pedida=categoria,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas,
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
            genero, f"{texto_pedido} {texto_extra}", catalog, cantidad=CANTIDAD_RESULTADOS, categoria_pedida=categoria,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas,
        )
        razon = (
            f'Segun una regla validada (confianza alta) para '
            f'{regla["genero"]} en "{regla["ocasion"]}": buscamos {atributos_txt}.'
        )
        return [formatear_producto(p, razon, tallas_usuario) for p in candidatos]

    candidatos = elegir_candidatos(
        genero, texto_pedido, catalog, cantidad=CANTIDAD_RESULTADOS, categoria_pedida=categoria,
        priorizar_material_natural=priorizar_material_natural,
        categorias_deprioritizadas=categorias_deprioritizadas,
    )
    return [
        formatear_producto(
            p,
            "Resultado de prueba (sin regla validada todavia): coincide con la "
            f'categoria "{p["categoria"]}" del catalogo urbano.',
            tallas_usuario,
        )
        for p in candidatos
    ]


def _completar_con_alternativas_de_corte(
    genero, texto_pedido, catalog, categoria, tallas_usuario, ids_ya_mostrados, faltan, razon_alternativa_fn,
    priorizar_material_natural=False, categorias_deprioritizadas=None,
):
    corte_pedido = detectar_corte_pedido(texto_pedido)
    if faltan <= 0 or not corte_pedido:
        return [], None

    catalog_restante = [p for p in catalog if p["id"] not in ids_ya_mostrados]
    candidatos = elegir_candidatos(
        genero, texto_pedido, catalog_restante, cantidad=faltan,
        categoria_pedida=categoria, permitir_otros_cortes=True,
        priorizar_material_natural=priorizar_material_natural,
        categorias_deprioritizadas=categorias_deprioritizadas,
    )
    if not candidatos:
        return [], None

    aviso = (
        f'No encontramos mas opciones en "{corte_pedido}", pero esto tambien podria '
        "interesarte (mismo tipo de prenda, otro corte):"
    )
    alternativas = [formatear_producto(p, razon_alternativa_fn(p), tallas_usuario) for p in candidatos]
    return alternativas, aviso


def buscar_plan_b(
    genero, ocasion, categoria, texto_pedido, catalog, reglas, tallas_usuario=None,
    priorizar_material_natural=False, categorias_deprioritizadas=None,
):
    regla = buscar_regla(genero, ocasion, reglas, {"media"})
    if regla:
        atributos_txt = ", ".join(regla.get("atributos", []))
        texto_extra = f'{regla.get("prenda", "")} {atributos_txt}'
        candidatos = elegir_candidatos(
            genero, f"{texto_pedido} {texto_extra}", catalog, cantidad=CANTIDAD_RESULTADOS,
            categoria_pedida=categoria, permitir_otros_cortes=True,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas,
        )
        razon = (
            f'Opcion alternativa (confianza media) para '
            f'{regla["genero"]} en "{regla["ocasion"]}": buscamos {atributos_txt}.'
        )
        return [formatear_producto(p, razon, tallas_usuario) for p in candidatos], [], None

    primarios = elegir_candidatos(
        genero, texto_pedido, catalog, cantidad=CANTIDAD_RESULTADOS, categoria_pedida=categoria,
        priorizar_material_natural=priorizar_material_natural,
        categorias_deprioritizadas=categorias_deprioritizadas,
    )
    ids_ya_mostrados = {p["id"] for p in primarios}

    exactos = [
        p
        for p in elegir_candidatos(
            genero, texto_pedido, catalog, cantidad=len(catalog), categoria_pedida=categoria,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas,
        )
        if p["id"] not in ids_ya_mostrados
    ][:CANTIDAD_RESULTADOS]
    ids_ya_mostrados = ids_ya_mostrados | {p["id"] for p in exactos}

    def razon_exacta(p):
        return (
            "Mas opciones del catalogo urbano (sin regla validada todavia) que "
            f'coinciden con la categoria "{p["categoria"]}".'
        )

    def razon_alternativa(p):
        return (
            "Alternativa fuera del corte pedido (sin regla validada todavia) que "
            f'coincide con la categoria "{p["categoria"]}".'
        )

    alternativas, aviso = _completar_con_alternativas_de_corte(
        genero, texto_pedido, catalog, categoria, tallas_usuario, ids_ya_mostrados,
        CANTIDAD_RESULTADOS - len(exactos), razon_alternativa,
        priorizar_material_natural=priorizar_material_natural,
        categorias_deprioritizadas=categorias_deprioritizadas,
    )
    return [formatear_producto(p, razon_exacta(p), tallas_usuario) for p in exactos], alternativas, aviso
