"""Genera data/catalog.json con datos de prueba (mock) inventados: 6
productos por cada combinacion de filtros que existe en los selects del
formulario (static/script.js) -- tipo de prenda + corte para prenda
superior; tipo + subtipo + corte para prenda inferior (pantalon/shorts).
Asi cualquier busqueda que se pueda armar con el formulario encuentra
stock, no solo las reglas validadas.

No es parte de la app -- se corre a mano cuando se quiera regenerar el
catalogo de prueba (por ejemplo si cambian las opciones del formulario).
Todo lo que genera es inventado: nombres, marcas, tiendas, precios y links
NO son reales.
"""
import json
import random
from pathlib import Path

from generar_imagenes_gorro import COLOR_HEX, PANEL_SUGERIDO
from generar_imagenes_prendas import TOP_SUBTIPOS

random.seed(42)

BASE_DIR = Path(__file__).parent
OUT_PATH = BASE_DIR / "data" / "catalog.json"

# Deben coincidir con TIPO_PRENDA_OPCIONES y CORTE_OPCIONES en
# static/script.js (los valores que llegan al buscador van en minuscula).
TIPOS_SUPERIOR = ["polera", "poleron", "chaqueta", "camisa", "camiseta", "top"]
TIPOS_INFERIOR = ["pantalon", "shorts", "faldacargo", "bikeshorts"]
CORTES_SUPERIOR = ["slim fit", "regular fit", "straight", "boxy fit", "oversize"]
CORTES_INFERIOR = ["skinny", "baggy", "slim fit", "straight fit"]

NOMBRES_TIPO = {
    "polera": "Polera",
    "poleron": "Polerón",
    "chaqueta": "Chaqueta",
    "camisa": "Camisa",
    "camiseta": "Camiseta",
    "pantalon": "Pantalón",
    "shorts": "Shorts",
    "top": "Top",
    "faldacargo": "Falda Cargo",
    "bikeshorts": "Bike Shorts",
}
# Nombres lindos para los subtipos nuevos de "top"; los de pantalon/shorts
# (buzo, jeans, cargo, tela, bano) siguen usando subtipo.capitalize().
NOMBRES_SUBTIPO = {
    "croptop": "Crop Top",
    "babytee": "Baby Tee",
    "halter": "Halter",
    "corset": "Corset",
    "tanktop": "Tank Top",
    "blusa": "Blusa",
    "bomber": "Bomber",
    "mezclilla": "de Mezclilla",
    "cuero": "de Cuero",
}
NOMBRES_CORTE = {
    "slim fit": "Slim Fit",
    "regular fit": "Regular Fit",
    "straight": "Straight",
    "boxy fit": "Boxy Fit",
    "oversize": "Oversize",
    "skinny": "Skinny",
    "straight fit": "Straight Fit",
    "baggy": "Baggy",
}

# Deben coincidir con TIPOS_CON_LARGO y LARGOS_CONOCIDOS en app.py. El largo
# es independiente del corte, asi que en vez de generar todas las
# combinaciones corte x largo (serian demasiadas), el largo simplemente
# rota entre los 6 productos de cada combo tipo x corte.
TIPOS_CON_LARGO = {"polera", "camiseta", "top"}
LARGOS = ["crop", "normal", "extra largo"]
NOMBRES_LARGO = {"crop": "Crop", "normal": "Largo Normal", "extra largo": "Extra Largo"}

# Manga solo en "polera"; capucha/cierre solo en "poleron". Deben coincidir
# con MANGAS_CONOCIDAS/CAPUCHAS_CONOCIDAS/CIERRES_CONOCIDOS en app.py.
MANGAS = ["larga", "corta"]
NOMBRES_MANGA = {"larga": "Manga Larga", "corta": "Manga Corta"}
# Las 4 combinaciones posibles de capucha x cierre, para que dentro de los
# 6 productos de cada corte queden representadas todas (no solo 2 sueltas).
COMBOS_CAPUCHA_CIERRE = [
    ("con capucha", "con cierre"),
    ("con capucha", "sin cierre"),
    ("sin capucha", "con cierre"),
    ("sin capucha", "sin cierre"),
]
NOMBRES_CAPUCHA = {"con capucha": "Con Capucha", "sin capucha": "Sin Capucha"}
NOMBRES_CIERRE = {"con cierre": "Con Cierre", "sin cierre": "Sin Cierre"}

TALLAS = ["S", "M", "L", "XL"]

ADJETIVOS = [
    "Urban", "Street", "Nocturno", "Vertex", "Drift", "Loom",
    "Nova", "Rustik", "Blend", "Kraft", "Aero", "Volt",
]
MARCAS = [
    "Nocturno Wear", "Riot Streetwear", "Concrete Co.", "Drift Label",
    "Loom Studio", "Vertex Supply", "Blackout Co.", "Curbside",
    "Static Wear", "Aero Street", "Kraft & Sons", "Volt Label",
]
OCASIONES = [
    "carrete", "universidad", "junta social", "junta familiar",
    "concierto/festival", "junta de amigos/skate park",
]

# Subtipos deben coincidir con SUBTIPO_OPCIONES en static/script.js. Solo
# aplican a pantalon/shorts/top/chaqueta -- para el resto de tipos no se
# genera este campo. Chaqueta agregado 2026-08-17 (ver
# agregar_subtipos_chaqueta.py -- ese script es el que de verdad genero los
# productos actuales en data/catalog.json de forma aditiva, sin rehacer
# todo el catalogo; esto queda documentado aca para que una futura corrida
# completa de este generador tambien los incluya).
SUBTIPOS = {
    "pantalon": ["buzo", "jeans", "cargo"],
    "shorts": ["jeans", "tela", "cargo", "bano"],
    "top": ["croptop", "babytee", "halter", "corset", "tanktop", "blusa"],
    "chaqueta": ["bomber", "mezclilla", "cuero"],
}

# Combinaciones fijas para las que SIEMPRE generamos un producto marcado
# en_oferta=True (ademas del ~30% al azar de generar_productos), para poder
# probar el filtro "cualquier precio en oferta" con casos garantizados.
COMBOS_OFERTA_GARANTIZADA = [
    ("polera", "oversize"),
    ("polera", "slim fit"),
    ("poleron", "boxy fit"),
    ("chaqueta", "regular fit"),
    ("chaqueta", "straight"),
    ("camisa", "slim fit"),
    ("camiseta", "oversize"),
    ("pantalon", "baggy"),
    ("pantalon", "skinny"),
    ("shorts", "straight fit"),
]

# Color de cada imagen ilustrativa de prenda: INVENTADO solo para que la
# imagen se vea distinta segun el producto (el catalogo mock no tenia campo
# de color para prendas, a diferencia de gorro que si usa color_dominante
# como filtro real). No se agrega como campo del producto ni se usa para
# filtrar -- existe unicamente en el nombre del archivo SVG.
COLORES_PRENDA = list(COLOR_HEX.keys())


def _imagen_prenda(tipo, subtipo, manga, capucha, cierre, color):
    """Arma la ruta a la imagen ilustrativa (static/img/prendas/, generadas
    por generar_imagenes_prendas.py) que corresponde a este producto."""
    if tipo == "polera":
        return f"img/prendas/prenda-polera-manga-{manga}-{color}.svg"
    if tipo == "poleron":
        slug = f"{capucha.replace(' ', '-')}-{cierre.replace(' ', '-')}"
        return f"img/prendas/prenda-poleron-{slug}-{color}.svg"
    if tipo == "top" and subtipo in TOP_SUBTIPOS:
        return f"img/prendas/prenda-top-{subtipo}-{color}.svg"
    if tipo in ("camiseta", "camisa", "chaqueta", "pantalon", "shorts", "faldacargo", "bikeshorts"):
        return f"img/prendas/prenda-{tipo}-{color}.svg"
    return None


DESCUENTOS_POSIBLES = [10, 15, 20, 25, 30, 35, 40, 50]


def _decidir_oferta(precio_clp, en_oferta=None):
    """Decide (si en_oferta es None) o fuerza si el producto esta en oferta,
    y si lo esta calcula un precio ORIGINAL mas alto + el % de descuento
    correspondiente -- para que la seccion "Ofertas" de /vitrina pueda
    mostrar un porcentaje real y ordenar de mayor a menor descuento, en vez
    de un simple flag sin numero detras. precio_clp (el precio final que
    paga el comprador) nunca cambia."""
    if en_oferta is None:
        en_oferta = random.random() < 0.3
    if not en_oferta:
        return en_oferta, None, None
    descuento_pct = random.choice(DESCUENTOS_POSIBLES)
    precio_original_clp = round(precio_clp / (1 - descuento_pct / 100) / 100) * 100
    return en_oferta, precio_original_clp, descuento_pct


def _formatear_clp(valor):
    return f"${valor:,}".replace(",", ".")


# Gorro no tiene corte ni tallas S/M/L/XL (es su propio flujo: color +
# forma) -- por eso no usa _crear_producto/generar_productos, tiene su
# propia funcion. Deben coincidir con COLORES_GORRO_CONOCIDOS y
# FORMAS_GORRO_CONOCIDAS en app.py.
COLORES_GORRO = ["blanco", "negro", "rojo", "azul", "amarillo", "beige", "morado", "verde"]
FORMAS_GORRO = ["curvo", "plano", "lana"]
NOMBRES_FORMA_GORRO = {"curvo": "Curvo", "plano": "Plano", "lana": "de Lana"}


def generar_productos_gorro():
    productos = []
    contador = 1
    for color in COLORES_GORRO:
        for forma in FORMAS_GORRO:
            for i in range(1, 7):
                marca = random.choice(MARCAS)
                adjetivo = random.choice(ADJETIVOS)
                precio_clp = random.randint(6, 25) * 1000 + random.choice([490, 990])
                en_oferta, precio_original_clp, descuento_pct = _decidir_oferta(precio_clp)
                descripcion = (
                    f"Gorro {NOMBRES_FORMA_GORRO[forma].lower()}, color dominante {color}, "
                    "estilo streetwear urbano, producto de prueba (no real)."
                )
                if en_oferta:
                    descripcion += " ¡En oferta!"

                # Imagen ilustrativa (SVG generado, no foto real): la mitad
                # de los gorros con visera (i>3) usan la version de dos
                # tonos (panel frontal en un color de contraste sugerido),
                # la otra mitad solido. Lana siempre solido.
                if forma == "lana":
                    imagen = f"img/gorros/gorro-lana-{color}.svg"
                elif i > 3:
                    imagen = f"img/gorros/gorro-{forma}-{color}-panel-{PANEL_SUGERIDO[color]}.svg"
                else:
                    imagen = f"img/gorros/gorro-{forma}-{color}.svg"

                productos.append({
                    "id": f"mock_gorro_{contador:04d}",
                    "nombre": f"[MOCK] Gorro {NOMBRES_FORMA_GORRO[forma]} {color.capitalize()} {adjetivo} {i}",
                    "marca": f"{marca} (marca inventada)",
                    "tienda": "Tienda Mock (no real)",
                    "link": f"https://mock-no-real.cl/gorro-{color}-{forma}-{i}",
                    "precio": _formatear_clp(precio_clp),
                    "precio_clp": precio_clp,
                    "precio_original": _formatear_clp(precio_original_clp) if en_oferta else "",
                    "descuento_pct": descuento_pct,
                    "en_oferta": en_oferta,
                    "descripcion": descripcion,
                    "imagen": f"/static/{imagen}",
                    "genero": "unisex",
                    "categoria": "gorro",
                    "color_dominante": color,
                    "forma": forma,
                    "ocasiones": OCASIONES,
                    "tags": ["streetwear", "urbano", color, forma],
                })
                contador += 1
    return productos


def _crear_producto(contador, tipo, corte, i, subtipo=None, largo=None, manga=None, capucha=None, cierre=None):
    marca = random.choice(MARCAS)
    adjetivo = random.choice(ADJETIVOS)
    # Rango amplio a proposito para poder probar los 5 tramos de precio del
    # formulario (25k/50k/75k/100k/200k).
    precio_clp = random.randint(9, 190) * 1000 + random.choice([490, 990])
    en_oferta, precio_original_clp, descuento_pct = _decidir_oferta(precio_clp)
    tallas_disponibles = random.sample(TALLAS, k=random.randint(2, 4))  # variado, inventado solo para probar el filtro
    color_imagen = random.choice(COLORES_PRENDA)

    nombre_subtipo = f" {NOMBRES_SUBTIPO.get(subtipo, subtipo.capitalize() if subtipo else '')}" if subtipo else ""
    nombre_largo = f" {NOMBRES_LARGO[largo]}" if largo else ""
    nombre_manga = f" {NOMBRES_MANGA[manga]}" if manga else ""
    nombre_capucha = f" {NOMBRES_CAPUCHA[capucha]}" if capucha else ""
    nombre_cierre = f" {NOMBRES_CIERRE[cierre]}" if cierre else ""
    slug_subtipo = f"-{subtipo}" if subtipo else ""
    slug_largo = f"-{largo.replace(' ', '-')}" if largo else ""
    slug_manga = f"-{manga}" if manga else ""
    slug_capucha = f"-{capucha.replace(' ', '-')}" if capucha else ""
    slug_cierre = f"-{cierre.replace(' ', '-')}" if cierre else ""
    slug = f"{tipo}{slug_subtipo}{slug_largo}{slug_manga}{slug_capucha}{slug_cierre}-{corte.replace(' ', '-')}-{i}"

    descripcion = f"Corte {NOMBRES_CORTE[corte].lower()}"
    if largo:
        descripcion += f", largo {NOMBRES_LARGO[largo].lower()}"
    if manga:
        descripcion += f", {NOMBRES_MANGA[manga].lower()}"
    if capucha:
        descripcion += f", {capucha}"
    if cierre:
        descripcion += f", {cierre}"
    descripcion += ", estilo streetwear urbano, producto de prueba (no real)."
    if en_oferta:
        descripcion += " ¡En oferta!"

    imagen = _imagen_prenda(tipo, subtipo, manga, capucha, cierre, color_imagen)

    producto = {
        "id": f"mock_{contador:04d}",
        "nombre": (
            f"[MOCK] {NOMBRES_TIPO[tipo]}{nombre_subtipo}{nombre_largo}{nombre_manga}"
            f"{nombre_capucha}{nombre_cierre} {NOMBRES_CORTE[corte]} {adjetivo} {i}"
        ),
        "marca": f"{marca} (marca inventada)",
        "tienda": "Tienda Mock (no real)",
        "link": f"https://mock-no-real.cl/{slug}",
        "precio": _formatear_clp(precio_clp),
        "precio_clp": precio_clp,
        "precio_original": _formatear_clp(precio_original_clp) if en_oferta else "",
        "descuento_pct": descuento_pct,
        "en_oferta": en_oferta,
        "tallas_disponibles": tallas_disponibles,
        "descripcion": descripcion,
        "imagen": f"/static/{imagen}" if imagen else "",
        "genero": "unisex",
        "categoria": tipo,
        "corte": corte,
        "ocasiones": OCASIONES,
        "tags": ["streetwear", "urbano", corte],
    }
    if subtipo:
        producto["subtipo"] = subtipo
    if largo:
        producto["largo"] = largo
    if manga:
        producto["manga"] = manga
    if capucha:
        producto["capucha"] = capucha
    if cierre:
        producto["cierre"] = cierre
    return producto


def generar_productos():
    productos = []
    contador = 1

    # Para cada tipo (superior + inferior): si tiene subtipos definidos en
    # SUBTIPOS, se genera el cruce COMPLETO tipo x subtipo x corte (6 de
    # cada uno), para que el filtro de subtipo tenga stock en todos los
    # cortes. Si no tiene subtipos, solo se cruza tipo x corte. Los tipos en
    # TIPOS_CON_LARGO ademas rotan por los 3 largos dentro de cada tanda de
    # 6 -- no se genera el cruce completo con largo tambien (séria
    # demasiadas combinaciones), solo se busca que haya de todo un poco.
    for tipo, cortes in [(t, CORTES_SUPERIOR) for t in TIPOS_SUPERIOR] + [(t, CORTES_INFERIOR) for t in TIPOS_INFERIOR]:
        subtipos_tipo = SUBTIPOS.get(tipo, [None])
        for subtipo in subtipos_tipo:
            for corte in cortes:
                for i in range(1, 7):
                    largo = LARGOS[(i - 1) % len(LARGOS)] if tipo in TIPOS_CON_LARGO else None
                    manga = MANGAS[(i - 1) % len(MANGAS)] if tipo == "polera" else None
                    capucha = cierre = None
                    if tipo == "poleron":
                        capucha, cierre = COMBOS_CAPUCHA_CIERRE[(i - 1) % len(COMBOS_CAPUCHA_CIERRE)]
                    productos.append(_crear_producto(
                        contador, tipo, corte, i, subtipo=subtipo, largo=largo,
                        manga=manga, capucha=capucha, cierre=cierre,
                    ))
                    contador += 1

    return productos


def generar_productos_oferta():
    """Genera un producto en_oferta=True por cada combo en
    COMBOS_OFERTA_GARANTIZADA (10 por defecto), para probar el filtro
    "cualquier precio en oferta" sin depender del azar. Reusa
    _crear_producto y despues fuerza en_oferta=True (que ya trae el
    resto de campos: tallas_disponibles, largo si corresponde, etc)."""
    productos = []
    for n, (tipo, corte) in enumerate(COMBOS_OFERTA_GARANTIZADA, start=1):
        subtipos_tipo = SUBTIPOS.get(tipo)
        subtipo = random.choice(subtipos_tipo) if subtipos_tipo else None
        largo = random.choice(LARGOS) if tipo in TIPOS_CON_LARGO else None
        manga = random.choice(MANGAS) if tipo == "polera" else None
        capucha, cierre = random.choice(COMBOS_CAPUCHA_CIERRE) if tipo == "poleron" else (None, None)

        producto = _crear_producto(
            9000 + n, tipo, corte, n, subtipo=subtipo, largo=largo,
            manga=manga, capucha=capucha, cierre=cierre,
        )
        producto["id"] = f"mock_oferta_{n:02d}"
        # _crear_producto ya pudo haber decidido en_oferta=True por si solo
        # (30% de las veces) y en ese caso ya trae precio_original/descuento
        # calculados -- si no, hay que calcularlos aca al forzarlo.
        if not producto["en_oferta"]:
            _, precio_original_clp, producto["descuento_pct"] = _decidir_oferta(
                producto["precio_clp"], en_oferta=True
            )
            producto["precio_original"] = _formatear_clp(precio_original_clp)
        producto["en_oferta"] = True
        if "¡En oferta!" not in producto["descripcion"]:
            producto["descripcion"] += " ¡En oferta!"
        producto["nombre"] = producto["nombre"].replace("[MOCK]", "[MOCK] [OFERTA]", 1)
        productos.append(producto)
    return productos


if __name__ == "__main__":
    productos = generar_productos() + generar_productos_oferta() + generar_productos_gorro()
    OUT_PATH.write_text(
        json.dumps(productos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Generados {len(productos)} productos mock en {OUT_PATH}")
