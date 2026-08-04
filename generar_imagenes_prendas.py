"""Genera imagenes SVG ilustrativas (NO fotos reales, NO logos de ninguna
marca) para las prendas del catalogo de prueba: polera, poleron, camisa,
camiseta, chaqueta, los 6 subtipos de "top", pantalon, shorts, falda cargo
y bike shorts -- en los mismos 8 colores solidos usados para los gorros.

Los colores de cada producto son INVENTADOS solo para que la imagen se vea
distinta segun el producto (el catalogo mock no tenia un campo de color
para prendas) -- no representan un dato real de ninguna tienda.

Mismo estilo que generar_imagenes_gorro.py: formas geometricas simples,
color solido plano + lineas de costura, sin depender de ningun servicio de
generacion de imagenes externo.

No es parte de la app -- se corre a mano antes de generar_catalogo_prueba.py
para dejar listos los archivos en static/img/prendas/.
"""
from pathlib import Path

from generar_imagenes_gorro import COLOR_HEX, LINEA

BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "static" / "img" / "prendas"

VIEWBOX = '0 0 200 260'


def _svg(cuerpo_svg):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEWBOX}" width="200" height="260">\n'
        f'{cuerpo_svg}\n'
        f'</svg>'
    )


def _botones(x, y0, y1, n=4):
    ys = [y0 + (y1 - y0) * k / (n - 1) for k in range(n)]
    return "".join(f'<circle cx="{x}" cy="{y:.0f}" r="2.5" fill="{LINEA}"/>' for y in ys)


# ---------------------------------------------------------------------
# Prenda superior con mangas: polera (corta/larga), camiseta, camisa,
# chaqueta y poleron comparten un mismo torso base con distinta manga.
# ---------------------------------------------------------------------

def _torso_con_mangas(color, manga_larga, cuello="v"):
    if cuello == "v":
        collar = "Q100,74 60,55"
    else:
        collar = "Q100,64 60,55"

    if manga_larga:
        sleeve_izq = "L30,78 L42,196 L58,178 L60,140"
        sleeve_der = "L140,140 L142,178 L158,196 L170,78"
    else:
        sleeve_izq = "L30,78 L45,112 L60,95"
        sleeve_der = "L140,95 L155,112 L170,78"

    return (
        f'<path d="M60,55 {sleeve_izq} L60,230 L140,230 {sleeve_der} L140,55 {collar} Z" '
        f'fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
    )


def svg_polera(color_key, manga):
    color = COLOR_HEX[color_key]
    torso = _torso_con_mangas(color, manga_larga=(manga == "larga"), cuello="v")
    print_pecho = f'<circle cx="100" cy="110" r="10" fill="none" stroke="{LINEA}" stroke-width="1.5" stroke-dasharray="3 3"/>'
    return _svg(torso + print_pecho)


def svg_camiseta(color_key):
    color = COLOR_HEX[color_key]
    torso = _torso_con_mangas(color, manga_larga=False, cuello="redondo")
    return _svg(torso)


def svg_camisa(color_key):
    color = COLOR_HEX[color_key]
    torso = _torso_con_mangas(color, manga_larga=False, cuello="v")
    solapas = (
        f'<path d="M80,55 L100,90 L88,60 Z" fill="{LINEA}" opacity="0.35"/>'
        f'<path d="M120,55 L100,90 L112,60 Z" fill="{LINEA}" opacity="0.35"/>'
    )
    botones = _botones(100, 95, 220, n=5)
    return _svg(torso + solapas + botones)


def svg_chaqueta(color_key):
    color = COLOR_HEX[color_key]
    torso = _torso_con_mangas(color, manga_larga=True, cuello="redondo")
    apertura = f'<line x1="100" y1="60" x2="100" y2="228" stroke="{LINEA}" stroke-width="2"/>'
    solapas = (
        f'<path d="M78,56 L100,92 L90,58 Z" fill="{LINEA}" opacity="0.3"/>'
        f'<path d="M122,56 L100,92 L110,58 Z" fill="{LINEA}" opacity="0.3"/>'
    )
    return _svg(torso + apertura + solapas)


def svg_poleron(color_key, capucha, cierre):
    color = COLOR_HEX[color_key]
    torso = _torso_con_mangas(color, manga_larga=True, cuello="redondo")
    if capucha == "con capucha":
        extra = f'<path d="M72,58 Q100,20 128,58 Q100,48 72,58 Z" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
    else:
        extra = ""
    if cierre == "con cierre":
        extra += f'<line x1="100" y1="62" x2="100" y2="228" stroke="{LINEA}" stroke-width="2"/>'
    else:
        extra += f'<rect x="78" y="150" width="44" height="26" rx="4" fill="none" stroke="{LINEA}" stroke-width="1.5"/>'
    return _svg(torso + extra)


# ---------------------------------------------------------------------
# Subtipos de "top" (prenda superior de mujer): cada uno con silueta
# distinta segun la tabla de definiciones de CLAUDE.md.
# ---------------------------------------------------------------------

def svg_top_croptop(color_key):
    color = COLOR_HEX[color_key]
    path = (
        f'<path d="M65,55 L35,78 L48,108 L65,95 L65,160 L135,160 L135,95 L152,108 L165,78 L135,55 '
        f'Q100,72 65,55 Z" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
    )
    return _svg(path)


def svg_top_babytee(color_key):
    color = COLOR_HEX[color_key]
    path = (
        f'<path d="M70,55 L48,72 L58,95 L70,86 L70,150 L130,150 L130,86 L142,95 L152,72 L130,55 '
        f'Q100,68 70,55 Z" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
    )
    return _svg(path)


def svg_top_halter(color_key):
    color = COLOR_HEX[color_key]
    lazo = f'<path d="M92,30 Q100,20 108,30 L104,55 L96,55 Z" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
    cuerpo = (
        f'<path d="M78,55 L65,90 L75,165 L125,165 L135,90 L122,55 Q100,68 78,55 Z" '
        f'fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
    )
    return _svg(lazo + cuerpo)


def svg_top_corset(color_key):
    color = COLOR_HEX[color_key]
    cuerpo = (
        f'<path d="M75,55 L65,90 L72,130 L60,165 L140,165 L128,130 L135,90 L125,55 '
        f'Q100,66 75,55 Z" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
    )
    huesillos = "".join(
        f'<line x1="80" y1="{y}" x2="120" y2="{y}" stroke="{LINEA}" stroke-width="1.5" stroke-dasharray="3 3"/>'
        for y in (95, 112, 129, 146)
    )
    return _svg(cuerpo + huesillos)


def svg_top_tanktop(color_key):
    color = COLOR_HEX[color_key]
    tirantes = (
        f'<rect x="78" y="35" width="10" height="25" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
        f'<rect x="112" y="35" width="10" height="25" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
    )
    cuerpo = (
        f'<path d="M70,60 L60,90 L65,220 L135,220 L140,90 L130,60 Q100,74 70,60 Z" '
        f'fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
    )
    return _svg(tirantes + cuerpo)


def svg_top_blusa(color_key):
    color = COLOR_HEX[color_key]
    torso = _torso_con_mangas(color, manga_larga=False, cuello="v")
    solapas = (
        f'<path d="M80,55 L100,88 L88,60 Z" fill="{LINEA}" opacity="0.3"/>'
        f'<path d="M120,55 L100,88 L112,60 Z" fill="{LINEA}" opacity="0.3"/>'
    )
    botones = _botones(100, 92, 220, n=5)
    return _svg(torso + solapas + botones)


TOP_SUBTIPOS = {
    "croptop": svg_top_croptop,
    "babytee": svg_top_babytee,
    "halter": svg_top_halter,
    "corset": svg_top_corset,
    "tanktop": svg_top_tanktop,
    "blusa": svg_top_blusa,
}


# ---------------------------------------------------------------------
# Prenda inferior: pantalon, shorts, falda cargo, bike shorts.
# ---------------------------------------------------------------------

def _piernas(color, largo_pierna, gap=10):
    y_fin = largo_pierna
    mitad = 100
    return (
        f'<path d="M55,50 L145,50 L150,90 L{mitad + gap // 2},90 L{mitad + gap // 2},{y_fin} '
        f'L{mitad - 6},{y_fin} L{mitad - 4},90 L{mitad - gap // 2},90 L{mitad - gap // 2},90 '
        f'L50,90 Z" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
        f'<path d="M55,50 L145,50 L150,90 L100,96 L50,90 Z" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
        f'<path d="M100,90 L106,{y_fin} L94,{y_fin} L94,90 Z" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
        f'<path d="M50,90 L94,90 L88,{y_fin} L58,{y_fin} Z" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
        f'<path d="M150,90 L106,90 L112,{y_fin} L142,{y_fin} Z" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
        f'<rect x="55" y="42" width="90" height="12" rx="4" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
    )


def svg_pantalon(color_key):
    color = COLOR_HEX[color_key]
    return _svg(_piernas(color, largo_pierna=230))


def svg_shorts(color_key):
    color = COLOR_HEX[color_key]
    return _svg(_piernas(color, largo_pierna=140))


def svg_bikeshorts(color_key):
    color = COLOR_HEX[color_key]
    piezas = _piernas(color, largo_pierna=115, gap=6)
    return _svg(piezas)


def svg_faldacargo(color_key):
    color = COLOR_HEX[color_key]
    falda = (
        f'<path d="M60,45 L140,45 L165,210 L35,210 Z" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
        f'<rect x="60" y="42" width="80" height="12" rx="4" fill="{color}" stroke="{LINEA}" stroke-width="2"/>'
    )
    bolsillos = (
        f'<rect x="48" y="110" width="32" height="38" rx="3" fill="none" stroke="{LINEA}" stroke-width="1.5"/>'
        f'<rect x="120" y="110" width="32" height="38" rx="3" fill="none" stroke="{LINEA}" stroke-width="1.5"/>'
    )
    return _svg(falda + bolsillos)


# ---------------------------------------------------------------------
# Directorio de generadores -> nombre de archivo (sin color ni ".svg").
# Usado por generar_catalogo_prueba.py para armar la ruta de cada producto.
# ---------------------------------------------------------------------

COMBOS_CAPUCHA_CIERRE = [
    ("con capucha", "con cierre"),
    ("con capucha", "sin cierre"),
    ("sin capucha", "con cierre"),
    ("sin capucha", "sin cierre"),
]


def generar():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generados = []

    def _guardar(nombre, svg):
        (OUT_DIR / nombre).write_text(svg, encoding="utf-8")
        generados.append(nombre)

    for color in COLOR_HEX:
        for manga in ("corta", "larga"):
            _guardar(f"prenda-polera-manga-{manga}-{color}.svg", svg_polera(color, manga))
        _guardar(f"prenda-camiseta-{color}.svg", svg_camiseta(color))
        _guardar(f"prenda-camisa-{color}.svg", svg_camisa(color))
        _guardar(f"prenda-chaqueta-{color}.svg", svg_chaqueta(color))
        for capucha, cierre in COMBOS_CAPUCHA_CIERRE:
            slug = f"{capucha.replace(' ', '-')}-{cierre.replace(' ', '-')}"
            _guardar(f"prenda-poleron-{slug}-{color}.svg", svg_poleron(color, capucha, cierre))
        for subtipo, func in TOP_SUBTIPOS.items():
            _guardar(f"prenda-top-{subtipo}-{color}.svg", func(color))
        _guardar(f"prenda-pantalon-{color}.svg", svg_pantalon(color))
        _guardar(f"prenda-shorts-{color}.svg", svg_shorts(color))
        _guardar(f"prenda-bikeshorts-{color}.svg", svg_bikeshorts(color))
        _guardar(f"prenda-faldacargo-{color}.svg", svg_faldacargo(color))

    return generados


if __name__ == "__main__":
    archivos = generar()
    print(f"Generados {len(archivos)} SVG en {OUT_DIR}")
