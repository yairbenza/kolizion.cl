"""Genera imagenes SVG ilustrativas (NO fotos reales, NO logos de ninguna
marca) para los gorros del catalogo de prueba: gorro con visera curva,
visera plana, y gorro de lana -- en distintos colores solidos y en version
de dos tonos (panel frontal de un color, resto de otro).

Inspirado de forma MUY generica en la estetica streetwear (colores solidos
planos, formas geometricas limpias, panel frontal + visera) -- sin copiar
logos, nombres ni disenos de ninguna marca real.

No es parte de la app -- se corre a mano antes de generar_catalogo_prueba.py
para dejar listos los archivos en static/img/gorros/.
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "static" / "img" / "gorros"

_RE_VIEWBOX = re.compile(r'viewBox="([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+)"')
_RE_DIMENSIONES = re.compile(r'width="(\d+)" height="(\d+)"')


def variantes_svg(svg_frontal):
    """A partir de una imagen SVG ya armada ("vista frontal", una prenda o
    un gorro), arma 2 variantes mas reusando el mismo dibujo -- sin
    escribir arte nuevo por cada tipo de prenda/gorro:
    - "trasera": el mismo dibujo espejado horizontalmente.
    - "detalle": un recorte con zoom a la mitad superior del dibujo.

    Sirve para probar de punta a punta el mecanismo de "3 fotos por
    producto" de la vista previa rapida (ver CLAUDE.md) mientras el
    catalogo sigue siendo de prueba -- son inventadas, no fotos reales.
    Cuando haya catalogo real con fotos de verdad, estas 3 rutas se
    reemplazan por las fotos reales de cada producto.
    """
    x0, y0, ancho, alto = (float(v) for v in _RE_VIEWBOX.search(svg_frontal).groups())
    ancho_px, alto_px = _RE_DIMENSIONES.search(svg_frontal).groups()

    tx = -(2 * x0 + ancho)
    trasera = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:g} {y0:g} {ancho:g} {alto:g}" '
        f'width="{ancho_px}" height="{alto_px}">'
        f'<g transform="scale(-1,1) translate({tx:g},0)">{svg_frontal}</g>'
        f'</svg>'
    )

    viewbox_detalle = f'{x0 + ancho * 0.1:g} {y0 + alto * 0.12:g} {ancho * 0.8:g} {alto * 0.42:g}'
    detalle = _RE_VIEWBOX.sub(f'viewBox="{viewbox_detalle}"', svg_frontal, count=1)

    return svg_frontal, trasera, detalle

COLOR_HEX = {
    "blanco": "#f2f0ea",
    "negro": "#1a1a1a",
    "rojo": "#c8102e",
    "azul": "#1560d1",
    "amarillo": "#f5c518",
    "beige": "#d8c3a5",
    "morado": "#6b2fb3",
    "verde": "#2e8b57",
}

# Pareja de contraste sugerida para las versiones de dos tonos (panel
# frontal en un color distinto al resto del gorro). Deben coincidir con
# como generar_catalogo_prueba.py arma los nombres de archivo.
PANEL_SUGERIDO = {
    "blanco": "azul",
    "negro": "rojo",
    "rojo": "negro",
    "azul": "blanco",
    "amarillo": "negro",
    "beige": "verde",
    "morado": "amarillo",
    "verde": "beige",
}

LINEA = "rgba(0,0,0,0.28)"


def _oscurecer(hex_color, factor=0.75):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (max(0, int(c * factor)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def svg_gorro_visera(forma, color_cuerpo, color_panel=None):
    """forma: "curvo" o "plano". Gorro con panel frontal + visera."""
    cuerpo = COLOR_HEX[color_cuerpo]
    panel = COLOR_HEX[color_panel] if color_panel else cuerpo

    if forma == "curvo":
        visera = (
            f'<path d="M40 110 Q120 150 200 110 Q120 128 40 110 Z" '
            f'fill="{cuerpo}" stroke="{LINEA}" stroke-width="2"/>'
        )
    else:
        visera = (
            f'<path d="M52 110 L188 110 L172 136 L68 136 Z" '
            f'fill="{cuerpo}" stroke="{LINEA}" stroke-width="2"/>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 200" width="240" height="200">
  <path d="M40 110 Q40 20 120 20 Q200 20 200 110 Z" fill="{cuerpo}" stroke="{LINEA}" stroke-width="2"/>
  {visera}
  <polygon points="95,110 145,110 120,42" fill="{panel}" stroke="{LINEA}" stroke-width="2"/>
  <line x1="103" y1="98" x2="120" y2="52" stroke="{LINEA}" stroke-width="1.5" stroke-dasharray="4 3"/>
  <line x1="137" y1="98" x2="120" y2="52" stroke="{LINEA}" stroke-width="1.5" stroke-dasharray="4 3"/>
  <circle cx="120" cy="21" r="6" fill="{cuerpo}" stroke="{LINEA}" stroke-width="2"/>
</svg>"""


def svg_gorro_lana(color):
    cuerpo = COLOR_HEX[color]
    cuff = _oscurecer(cuerpo)
    ribs = "".join(
        f'<line x1="{x}" y1="45" x2="{x}" y2="128" stroke="{LINEA}" stroke-width="1" opacity="0.5"/>'
        for x in range(60, 190, 18)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 200" width="240" height="200">
  <path d="M55 158 Q45 40 120 24 Q195 40 185 158 Z" fill="{cuerpo}" stroke="{LINEA}" stroke-width="2"/>
  {ribs}
  <rect x="50" y="128" width="140" height="32" rx="6" fill="{cuff}" stroke="{LINEA}" stroke-width="2"/>
  <circle cx="120" cy="20" r="11" fill="{cuerpo}" stroke="{LINEA}" stroke-width="2"/>
</svg>"""


def generar():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generados = []

    def _guardar_con_variantes(nombre_base, svg_frontal):
        frontal, trasera, detalle = variantes_svg(svg_frontal)
        for sufijo, contenido in (("", frontal), ("-trasera", trasera), ("-detalle", detalle)):
            nombre = f"{nombre_base}{sufijo}.svg"
            (OUT_DIR / nombre).write_text(contenido, encoding="utf-8")
            generados.append(nombre)

    for forma in ("curvo", "plano"):
        for color in COLOR_HEX:
            _guardar_con_variantes(f"gorro-{forma}-{color}", svg_gorro_visera(forma, color))
            panel = PANEL_SUGERIDO[color]
            _guardar_con_variantes(f"gorro-{forma}-{color}-panel-{panel}", svg_gorro_visera(forma, color, panel))

    for color in COLOR_HEX:
        _guardar_con_variantes(f"gorro-lana-{color}", svg_gorro_lana(color))

    return generados


if __name__ == "__main__":
    archivos = generar()
    print(f"Generados {len(archivos)} SVG en {OUT_DIR}")
