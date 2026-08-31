import hashlib
import re
from constantes import (
    ALIAS_TIENDAS,
    CANTIDAD_RESULTADOS,
    CATEGORIAS_CON_GRAMAJE,
    CATEGORIAS_EXCLUIDAS_POR_GENERO,
    CATEGORIA_GRUPOS,
    CIERRES_CONOCIDOS,
    CAPUCHAS_CONOCIDAS,
    COLORES_CONOCIDOS,
    COLORES_SIMILARES,
    CORTES_CONOCIDOS,
    EXCLUSIONES_HOBBY,
    EXCLUSIONES_OCASION_MUJER,
    FORMA_GORRO_CONOCIDA,
    FORMAS_GORRO_CONOCIDAS,
    GRAMAJE_MINIMO_CALIDAD_GSM,
    GRUPOS_OCASION_MUJER,
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
    _quitar_tildes,
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


def filtrar_por_exclusiones(catalog, terminos_excluidos):
    """Saca del catalogo cualquier producto que calce con algo que la
    persona dijo explicitamente que NO quiere (tienda, marca, color, corte,
    categoria, etc. -- lo que haya nombrado, ej. "nada de Don Lobo",
    "excepto Nike", "pero no negras"). Filtro real y estricto: si un
    producto calza con CUALQUIER termino de la lista, se saca por completo
    (pedido del usuario, 2026-08-27). Se compara contra tienda, marca y el
    mismo texto (nombre/categoria/descripcion/tags) que ya usa el resto del
    buscador -- no se inventa ningun dato nuevo por producto."""
    if not terminos_excluidos:
        return catalog
    resultado = catalog
    for termino_crudo in terminos_excluidos:
        termino = _quitar_tildes((termino_crudo or "").strip().lower())
        if not termino:
            continue
        tienda_canonica = ALIAS_TIENDAS.get(termino)
        resultado = [
            p
            for p in resultado
            if not (
                (tienda_canonica and p.get("tienda", "") == tienda_canonica)
                or _contiene_palabra(_quitar_tildes(p.get("tienda", "").lower()), termino)
                or _contiene_palabra(_quitar_tildes(p.get("marca", "").lower()), termino)
                or _contiene_palabra(_quitar_tildes(texto_producto(p)), termino)
            )
        ]
    return resultado


# Preferencia negativa por checkbox (2026-08-28, /perfil): a diferencia de
# filtrar_por_exclusiones (texto libre), esto usa tags reales del catalogo
# (es_desgastado, grafico_grande, texto_grande, cara_logo_grande) en vez de
# buscar palabras. Los 3 ultimos solo existen en los productos ya revisados a
# mano (lote piloto, ver construir_catalogo_real.py) -- un producto sin esa
# clave simplemente no tiene .get(...) en True, asi que nunca se excluye por
# algo que todavia no se evaluo (no se asume "no tiene"). "No me gustan los
# jeans" se sacó (pedido del usuario, 2026-08-28: no le sirve ese filtro).
def filtrar_por_preferencias_negativas(catalog, prefs):
    if not prefs:
        return catalog
    return [
        p
        for p in catalog
        if not (
            (prefs.get("excluir_rotos") and p.get("es_desgastado"))
            or (prefs.get("excluir_grafico_grande") and p.get("grafico_grande"))
            or (prefs.get("excluir_texto_grande") and p.get("texto_grande"))
            or (prefs.get("excluir_cara_logo_grande") and p.get("cara_logo_grande"))
        )
    ]


def formatear_producto(producto, razon, tallas_usuario=None):
    tallas_coincidentes = []
    if tallas_usuario:
        disponibles = set(producto.get("tallas_disponibles", []))
        tallas_coincidentes = [t for t in ORDEN_TALLAS if t in tallas_usuario and t in disponibles]
    return {
        "id": producto["id"],
        "nombre": producto["nombre"],
        "marca": producto.get("marca", ""),
        "tienda": producto["tienda"],
        "categoria": producto.get("categoria", ""),
        "corte": producto.get("corte", ""),
        "material": MATERIALES_CONOCIDOS.get(producto.get("material", ""), {}).get("etiqueta", ""),
        "gramaje_texto": _texto_gramaje(producto),
        "marca_autor": bool(producto.get("marca_autor", False)),
        "genero": producto.get("genero", ""),
        "interes_musica": bool(producto.get("interes_musica", False)),
        "interes_arte": bool(producto.get("interes_arte", False)),
        "precio": producto.get("precio", ""),
        "precio_original": producto.get("precio_original", ""),
        "descuento_pct": producto.get("descuento_pct"),
        "descripcion": producto.get("descripcion", ""),
        "link": producto["link"],
        "razon": razon,
        "tallas_coincidentes": tallas_coincidentes,
        "imagen": producto.get("imagen", ""),
        "fotos": producto.get("fotos", []),
        "oficial": bool(producto.get("oficial", False)),
        "tallas_disponibles": producto.get("tallas_disponibles", []),
        "tallas_variantes": producto.get("tallas_variantes", []),
        "colores_disponibles": producto.get("colores_disponibles", []),
        "subtipo": producto.get("subtipo", ""),
        "manga": producto.get("manga", ""),
        "largo": producto.get("largo", ""),
        "capucha": producto.get("capucha", ""),
        "cierre": producto.get("cierre", ""),
    }


def tiene_stock(producto):
    """True si el producto tiene stock real en alguna talla -- mismo
    criterio que productoTieneStock() en comun.js (decide "Agregar al
    carrito" vs "Proximamente"), aca para poder ocultar agotados en
    Descubre (2026-08-30, pedido del usuario). Gorros lana (talla unica,
    ver construir_producto) siempre traen tallas_disponibles=["Unica"],
    asi que cuentan como con stock salvo que la tienda diga lo contrario."""
    variantes = producto.get("tallas_variantes")
    if variantes:
        return any(v.get("disponible") for v in variantes)
    return bool(producto.get("tallas_disponibles"))


def filtrar_gorros_por_forma(catalog, forma):
    forma = (forma or "").strip().lower()
    if forma not in FORMAS_GORRO_CONOCIDAS:
        return catalog
    return [
        p for p in catalog
        if p.get("categoria", "").lower() != "gorro" or p.get("forma", "").lower() == forma
    ]


def filtrar_gorros_por_forma_con_aviso(catalog, forma):
    """Igual que filtrar_gorros_por_forma, pero si la forma pedida (plano/
    curvo/lana) no tiene ningun gorro en el catalogo, en vez de dejar la
    busqueda en 0 resultados avisa que esa forma no se encontro y muestra
    las otras formas de gorro que si hay (2026-08-30, pedido del usuario)."""
    forma = (forma or "").strip().lower()
    if forma not in FORMAS_GORRO_CONOCIDAS:
        return catalog, None
    filtrado = filtrar_gorros_por_forma(catalog, forma)
    if any(p.get("categoria", "").lower() == "gorro" for p in filtrado):
        return filtrado, None
    if not any(p.get("categoria", "").lower() == "gorro" for p in catalog):
        return filtrado, None
    return catalog, f"No encontramos gorro {forma}, pero te mostramos otras formas de gorro disponibles."


_PATRON_COLOR_DECLARADO = re.compile(
    r"\bcolor\s*:\s*(.+?)(?:\s*(?:tipo\s*calce|tipo\b|material\b|referencia\b|composici|cuidado|talla|medidas|garant)|$)",
    re.IGNORECASE,
)


def _color_declarado(producto):
    """Bastante descripciones (243 de 658, revisado 2026-08-27) traen un
    campo "Color : X" escrito a mano dentro del texto libre de la ficha --
    cuando existe, es MUCHO mas confiable que buscar la palabra suelta en
    toda la descripcion (evita falsos positivos reales encontrados en el
    catalogo, ej. una chaqueta "Color : Negro" que tambien menciona de paso
    "detalle... color azul" en otra parte del texto -- sin esto, pedir
    "azul" la mostraba igual). Si no existe ese campo, no se inventa nada:
    se vuelve None y el llamador cae de vuelta al texto completo."""
    match = _PATRON_COLOR_DECLARADO.search(producto.get("descripcion", ""))
    return _quitar_tildes(match.group(1).strip().lower()) if match else None


def _color_producto(producto):
    """Fuente de color mas confiable disponible para el producto: gorro
    tiene un campo estructurado propio (`color_dominante`, curado a mano --
    ver docs/buscador.md); el resto depende de que la descripcion declare
    "Color : X", y si tampoco hay eso, se cae al texto completo de la
    ficha."""
    color_dominante = producto.get("color_dominante")
    if color_dominante:
        return color_dominante.strip().lower()
    return _color_declarado(producto)


def _color_coincide_exacto(producto, color_pedido):
    variantes = COLORES_CONOCIDOS.get(color_pedido, [color_pedido])
    fuente = _color_producto(producto)
    if fuente is not None:
        return any(_contiene_palabra(fuente, v) for v in variantes)
    return any(_contiene_palabra(texto_producto(producto), v) for v in variantes)


def _color_coincide_similar(producto, color_pedido):
    variantes = COLORES_SIMILARES.get(color_pedido, [])
    fuente = _color_producto(producto)
    if fuente is not None:
        return any(_contiene_palabra(fuente, v) for v in variantes)
    return any(_contiene_palabra(texto_producto(producto), v) for v in variantes)


def detectar_color_pedido(texto_pedido):
    return _detectar(texto_pedido, COLORES_CONOCIDOS)


def detectar_color_pedido_conversacion(mensajes):
    return _detectar_reciente(mensajes, COLORES_CONOCIDOS)


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


def _orden_neutral(texto_pedido, producto_id):
    """Numero estable (mismo input -> mismo numero siempre) pero sin
    relacion con la tienda ni con el orden del catalogo -- ver el
    comentario en puntaje() dentro de elegir_candidatos()."""
    texto = f"{texto_pedido}|{producto_id}".encode("utf-8")
    return int(hashlib.md5(texto).hexdigest(), 16)


def _diversificar_por_tienda(ordenados, cantidad):
    """Recorre la lista YA ordenada por relevancia y arma los "cantidad"
    resultados finales evitando 2 seguidos de la misma tienda -- pedido del
    usuario (2026-08-27): que los resultados no queden monopolizados
    visualmente por una sola tienda grande (ej. Doslobos/UNK Chile, que
    tienen muchisimos mas productos cargados que el resto).

    En cada paso toma SIEMPRE el mas relevante disponible; si ese calza con
    la tienda del resultado anterior, busca el siguiente mas relevante de
    OTRA tienda mas abajo en la lista (nunca baja la relevancia a proposito,
    solo cambia CUAL de los empates/cercanos elige). Si no hay ninguna
    alternativa de otra tienda entre lo que queda, repite la tienda -- no
    se sacrifica calidad solo por diversidad (pedido explicito del
    usuario)."""
    restantes = list(ordenados)
    elegidos = []
    while restantes and len(elegidos) < cantidad:
        tienda_anterior = elegidos[-1]["tienda"] if elegidos else None
        idx = next((i for i, p in enumerate(restantes) if p["tienda"] != tienda_anterior), 0)
        elegidos.append(restantes.pop(idx))
    return elegidos


CORTE_ANCHO_PRIORIDAD_PANTALON = {"baggy": 3, "straight fit": 2, "slim fit": 1, "skinny": 0}


def _excluidos_por_ocasion_mujer(ocasion):
    """Reglas duras (2026-08-30, pedido del usuario): para MUJER, ciertas
    combinaciones prenda+ocasion se sacan del pool de candidatos, no solo
    se reordenan (a diferencia de EXCLUSIONES_HOBBY / nivel_hobby). Solo
    aplica a hombre = no tocar (el usuario lo pidio asi de forma explicita)."""
    ocasion_norm = _quitar_tildes((ocasion or "").strip().lower())
    grupo = GRUPOS_OCASION_MUJER.get(ocasion_norm)
    return EXCLUSIONES_OCASION_MUJER.get(grupo, []) if grupo else []


def _prenda_excluida_por_ocasion(producto, reglas_exclusion):
    categoria = (producto.get("categoria") or "").lower()
    for regla in reglas_exclusion:
        if categoria != regla.get("categoria"):
            continue
        if "subtipo" in regla and (producto.get("subtipo") or "").lower() != regla["subtipo"]:
            continue
        if "capucha" in regla and (producto.get("capucha") or "").lower() != regla["capucha"]:
            continue
        return True
    return False


def elegir_candidatos(
    genero, texto_pedido, catalog, cantidad, categoria_pedida=None, permitir_otros_cortes=False,
    permitir_otro_subtipo=False,
    priorizar_material_natural=False, categorias_deprioritizadas=None,
    color_pedido=None, permitir_colores_similares=False, ocasion=None,
):
    genero = (genero or "").strip().lower()
    # Antes, si el filtro de genero+categoria daba 0 resultados, el "or
    # catalog" hacia fallback al catalogo COMPLETO sin filtrar genero --
    # asi "poleras para hombre" podia terminar mostrando tops de mujer
    # (bug real reportado por el usuario, 2026-08-26). El fallback solo
    # tiene sentido cuando no hay genero definido (texto_pedido sin perfil);
    # si el usuario SI pidio un genero, ese filtro debe ser estricto -- si
    # no hay nada en ese genero, mejor 0 resultados que mezclar el otro.
    candidatos = [p for p in catalog if p["genero"].lower() in (genero, "unisex")] if genero else catalog

    categorias_excluidas = CATEGORIAS_EXCLUIDAS_POR_GENERO.get(genero, set())
    if categorias_excluidas:
        candidatos = [p for p in candidatos if p["categoria"].lower() not in categorias_excluidas]

    if genero == "mujer":
        reglas_exclusion_ocasion = _excluidos_por_ocasion_mujer(ocasion)
        if reglas_exclusion_ocasion:
            candidatos = [
                p for p in candidatos if not _prenda_excluida_por_ocasion(p, reglas_exclusion_ocasion)
            ]

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
            candidatos_del_subtipo = [p for p in candidatos if p.get("subtipo", "").lower() == subtipo_pedido]
            if candidatos_del_subtipo or not permitir_otro_subtipo:
                candidatos = candidatos_del_subtipo

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

    if color_pedido:
        # Igual filosofia que el corte: primero exacto, estricto. Solo si
        # esta permitido relajar (Plan B / "Buscar mas", cuando ya no queda
        # NINGUN color exacto) se amplia a colores visualmente cercanos --
        # nunca al reves, y nunca si todavia hay algo del color exacto
        # (pedido explicito del usuario, 2026-08-27). Se acepta un color
        # solo (Koko) o una lista de hasta 3 (buscador normal, checkboxes)
        # -- basta con calzar con UNO de los pedidos, no con todos.
        colores = color_pedido if isinstance(color_pedido, (list, tuple, set)) else [color_pedido]
        candidatos_color_exacto = [
            p for p in candidatos if any(_color_coincide_exacto(p, c) for c in colores)
        ]
        if candidatos_color_exacto:
            candidatos = candidatos_color_exacto
        elif permitir_colores_similares:
            candidatos = [
                p for p in candidatos if any(_color_coincide_similar(p, c) for c in colores)
            ]
        else:
            candidatos = candidatos_color_exacto

    # Pedido del usuario (2026-08-28): en pantalon/buzo para ocasion
    # "deporte" o "junta social", si la persona no pidio un corte
    # especifico, priorizar el corte mas ancho/baggy disponible -- usando
    # el campo "corte" ya tageado, nunca releyendo fotos. Es una prioridad
    # suave (reordena el puntaje), nunca un filtro duro: si no hay nada
    # baggy, igual se muestra lo que haya, solo mas abajo en la lista.
    corte_ancho_prioridad = None
    if not corte_pedido and tipo_prenda == "pantalon":
        ocasion_norm = _quitar_tildes((ocasion or "").strip().lower())
        if ocasion_norm in {"deporte", "junta social"}:
            corte_ancho_prioridad = CORTE_ANCHO_PRIORIDAD_PANTALON

    palabras_pedido = tokenizar(texto_pedido)

    def puntaje(producto):
        puntaje_palabras = len(palabras_pedido & tokenizar(texto_producto(producto)))
        categoria_producto = (producto.get("categoria") or "").lower()
        nivel_hobby = 0 if categoria_producto in (categorias_deprioritizadas or ()) else 1
        nivel_corte_ancho = (
            corte_ancho_prioridad.get((producto.get("corte") or "").lower(), 0)
            if corte_ancho_prioridad else 0
        )
        # Cuando se busca "gorro" sin pedir una forma puntual (el formulario
        # normal SIEMPRE pide forma, pero Koko puede dejarla vacia), curvo y
        # lana quedaban empatados en puntaje_palabras y el desempate neutral
        # podia poner un gorro de lana (beanie) antes que uno curvo (jockey/
        # cap) al puro azar -- bug real reportado por el usuario (2026-08-30):
        # curvo es la forma abrumadoramente mas comun/variada del catalogo,
        # asi que gana el empate por defecto. No excluye lana, solo lo ordena
        # despues (mismo criterio que nivel_corte_ancho arriba).
        nivel_forma_gorro = (
            0 if categoria_producto == "gorro" and (producto.get("forma") or "").lower() == "lana" else 1
        )
        # Python ordena empates preservando el orden ORIGINAL de la lista --
        # sin este ultimo termino, cuando 2 productos empatan en relevancia
        # (muy comun: la mayoria de las busquedas no comparten ninguna
        # palabra con el texto del producto) ganaba el que estuviera antes
        # en catalog.json, es decir la tienda que se cargo primero en
        # construir_catalogo_real.py -- un sesgo real por orden de carga,
        # nada que ver con que tan bien calza con lo pedido (bug reportado
        # por el usuario, 2026-08-27). Se reemplaza por un desempate neutral
        # (hash estable de la busqueda + id del producto): mismo resultado
        # si se repite la MISMA busqueda, pero no favorece siempre a la
        # misma tienda en busquedas distintas.
        desempate_neutral = _orden_neutral(texto_pedido, producto.get("id", ""))
        if priorizar_material_natural:
            return (
                nivel_hobby,
                nivel_corte_ancho,
                1 if _material_es_natural(producto) else 0,
                1 if _algodon_buena_calidad(producto) else 0,
                puntaje_palabras,
                nivel_forma_gorro,
                desempate_neutral,
            )
        return (nivel_hobby, nivel_corte_ancho, puntaje_palabras, nivel_forma_gorro, desempate_neutral)

    ordenados = sorted(candidatos, key=puntaje, reverse=True)
    return _diversificar_por_tienda(ordenados, cantidad)


def armar_resultados(
    genero, ocasion, categoria, texto_pedido, catalog, reglas, tallas_usuario=None,
    priorizar_material_natural=False, categorias_deprioritizadas=None, color_pedido=None,
):
    regla = buscar_regla(genero, ocasion, reglas, {"sin_consenso"})
    if regla:
        texto_extra = f'{regla.get("prenda", "")} streetwear urbano'
        candidatos = elegir_candidatos(
            genero, f"{texto_pedido} {texto_extra}", catalog, cantidad=3, categoria_pedida=categoria,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=color_pedido, ocasion=ocasion,
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
            categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=color_pedido, ocasion=ocasion,
        )
        razon = (
            f'Segun una regla validada (confianza alta) para '
            f'{regla["genero"]} en "{regla["ocasion"]}": buscamos {atributos_txt}.'
        )
        return [formatear_producto(p, razon, tallas_usuario) for p in candidatos]

    candidatos = elegir_candidatos(
        genero, texto_pedido, catalog, cantidad=CANTIDAD_RESULTADOS, categoria_pedida=categoria,
        priorizar_material_natural=priorizar_material_natural,
        categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=color_pedido, ocasion=ocasion,
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
    genero, texto_pedido, catalog, catalog_precio, categoria, tallas_usuario, ids_ya_mostrados, faltan,
    razon_alternativa_fn,
    priorizar_material_natural=False, categorias_deprioritizadas=None, color_pedido=None,
    precio_pedido=None, ocasion=None,
):
    corte_pedido = detectar_corte_pedido(texto_pedido)
    tiene_precio = bool((precio_pedido or "").strip())
    if faltan <= 0 or not (corte_pedido or color_pedido or tiene_precio):
        return [], None

    # "permitir_otros_cortes" de elegir_candidatos solo abre el corte si el
    # corte EXACTO no calzo con NADA -- pero a esta altura ya sacamos del
    # catalogo restante todo lo que era exacto en corte+color a la vez (paso
    # "exactos" de buscar_plan_b), asi que casi siempre queda algo con el
    # corte exacto pero color equivocado, y eso "atrapa" el filtro sin dejar
    # abrir el corte. Por eso, para las etapas donde el corte debe quedar
    # totalmente libre, se le saca la palabra del corte al texto pedido --
    # asi elegir_candidatos ni siquiera detecta que se pidio un corte.
    texto_corte_libre = texto_pedido
    if corte_pedido:
        patron_corte = re.compile(
            r"\b(?:" + "|".join(re.escape(v) for v in CORTES_CONOCIDOS[corte_pedido]) + r")(?:es|s)?\b",
            re.IGNORECASE,
        )
        texto_corte_libre = patron_corte.sub("", texto_pedido)

    # Relajacion en cascada, UN requisito a la vez -- nunca se combinan 2
    # relajaciones de una (pedido explicito del usuario, 2026-08-27: "nunca
    # pasar directamente a resultados que incumplan varios filtros"). Orden:
    # 1) colores cercanos; 2) precio; 3) cualquier corte; el tipo de prenda
    # (categoria) nunca se toca en ninguna etapa -- si esas 3 relajaciones de
    # a una no alcanzan a llenar los cupos, recien se combinan corte+color
    # (pedido del usuario, 2026-08-28: misma prenda con otro corte o precio,
    # siempre antes que ofrecer un tipo de prenda distinto).
    etapas = []
    if color_pedido:
        # corte y precio siguen exactos
        etapas.append((texto_pedido, False, True, False, "color"))
    if tiene_precio:
        # corte y color siguen exactos, se usa el catalogo sin filtrar por precio
        etapas.append((texto_pedido, False, False, True, "precio"))
    if corte_pedido:
        # corte totalmente libre (la palabra ya no esta en el texto), color y precio exactos
        etapas.append((texto_corte_libre, True, False, False, "corte"))
    if corte_pedido and color_pedido:
        etapas.append((texto_corte_libre, True, True, False, "ambos"))

    ids_excluidos = set(ids_ya_mostrados)
    encontrados = []
    etapa_con_resultados = None
    for texto_etapa, permitir_otros_cortes, permitir_colores_similares, relajar_precio, nombre_etapa in etapas:
        if len(encontrados) >= faltan:
            break
        catalog_base = catalog if relajar_precio else catalog_precio
        catalog_restante = [p for p in catalog_base if p["id"] not in ids_excluidos]
        candidatos = elegir_candidatos(
            genero, texto_etapa, catalog_restante, cantidad=faltan - len(encontrados),
            categoria_pedida=categoria, permitir_otros_cortes=permitir_otros_cortes,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas,
            color_pedido=color_pedido, permitir_colores_similares=permitir_colores_similares,
            ocasion=ocasion,
        )
        if candidatos:
            encontrados.extend(candidatos)
            ids_excluidos.update(p["id"] for p in candidatos)
            if etapa_con_resultados is None:
                etapa_con_resultados = nombre_etapa

    if not encontrados:
        return [], None

    if etapa_con_resultados == "color":
        aviso = (
            "No encontramos mas opciones en ese color exacto, pero esto tambien podria "
            "interesarte (colores parecidos):"
        )
    elif etapa_con_resultados == "precio":
        aviso = (
            "No encontramos mas opciones en ese precio, pero esto tambien podria "
            "interesarte (mismo tipo de prenda, otro precio):"
        )
    else:
        aviso = (
            f'No encontramos mas opciones en "{corte_pedido}", pero esto tambien podria '
            "interesarte (mismo tipo de prenda, otro corte):"
        )
    alternativas = [formatear_producto(p, razon_alternativa_fn(p), tallas_usuario) for p in encontrados]
    return alternativas, aviso


def buscar_plan_b(
    genero, ocasion, categoria, texto_pedido, catalog, reglas, tallas_usuario=None,
    priorizar_material_natural=False, categorias_deprioritizadas=None, color_pedido=None,
    precio_pedido=None, ids_excluir=None,
):
    # ids_excluir: productos ya mostrados en esta busqueda (resultado inicial
    # + clics previos de "mostrar mas opciones"). Sin esto, cada clic repetia
    # exactamente los mismos productos porque la busqueda es determinista
    # (bug reportado por el usuario, 2026-08-28).
    if ids_excluir:
        catalog = [p for p in catalog if p["id"] not in ids_excluir]

    # "catalog" aca puede venir sin filtrar por precio (a diferencia de la
    # busqueda normal) -- asi _completar_con_alternativas_de_corte tiene
    # acceso al catalogo completo para su etapa de relajar precio. El resto
    # de las etapas (primarios/exactos/regla media) sigue respetando el
    # precio pedido de forma estricta via catalog_precio.
    catalog_precio = filtrar_por_precio(catalog, precio_pedido)

    regla = buscar_regla(genero, ocasion, reglas, {"media"})
    if regla:
        atributos_txt = ", ".join(regla.get("atributos", []))
        texto_extra = f'{regla.get("prenda", "")} {atributos_txt}'
        candidatos = elegir_candidatos(
            genero, f"{texto_pedido} {texto_extra}", catalog_precio, cantidad=CANTIDAD_RESULTADOS,
            categoria_pedida=categoria, permitir_otros_cortes=True,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas,
            color_pedido=color_pedido, permitir_colores_similares=True, ocasion=ocasion,
        )
        razon = (
            f'Opcion alternativa (confianza media) para '
            f'{regla["genero"]} en "{regla["ocasion"]}": buscamos {atributos_txt}.'
        )
        return [formatear_producto(p, razon, tallas_usuario) for p in candidatos], [], None

    primarios = elegir_candidatos(
        genero, texto_pedido, catalog_precio, cantidad=CANTIDAD_RESULTADOS, categoria_pedida=categoria,
        priorizar_material_natural=priorizar_material_natural,
        categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=color_pedido, ocasion=ocasion,
    )
    ids_ya_mostrados = {p["id"] for p in primarios}

    exactos = [
        p
        for p in elegir_candidatos(
            genero, texto_pedido, catalog_precio, cantidad=len(catalog_precio), categoria_pedida=categoria,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=color_pedido, ocasion=ocasion,
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
            "Alternativa fuera del corte/precio pedido (sin regla validada todavia) que "
            f'coincide con la categoria "{p["categoria"]}".'
        )

    alternativas, aviso = _completar_con_alternativas_de_corte(
        genero, texto_pedido, catalog, catalog_precio, categoria, tallas_usuario, ids_ya_mostrados,
        CANTIDAD_RESULTADOS - len(exactos), razon_alternativa,
        priorizar_material_natural=priorizar_material_natural,
        categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=color_pedido,
        precio_pedido=precio_pedido, ocasion=ocasion,
    )
    return [formatear_producto(p, razon_exacta(p), tallas_usuario) for p in exactos], alternativas, aviso
