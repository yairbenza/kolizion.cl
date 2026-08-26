"""Genera los iconos de la PWA a partir del logo real de KOLIZION
(static/img/kolizion-logo.png) -- nunca un logo inventado. El logo
original ya tiene ~18-20% de margen blanco alrededor del dibujo (medido a
mano), asi que el icono "any" es un resize directo; el "maskable" (los
launchers de Android lo recortan en circulo/squircle/etc, necesita mas
margen de seguridad) lo escala un poco mas chico y centrado, sumando
margen extra para nunca perder el logo al recortar.

No es parte de la app en si -- se corre a mano cuando haga falta
regenerar los iconos (ej. si el logo cambia)."""
from pathlib import Path

from PIL import Image

BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "static" / "img" / "kolizion-logo.png"
OUT_DIR = BASE_DIR / "static" / "img" / "icons"


def _icono_simple(logo, tamano):
    """Resize directo -- el logo original ya tiene margen de sobra."""
    return logo.resize((tamano, tamano), Image.LANCZOS)


def _icono_maskable(logo, tamano, escala=0.72):
    """Pega el logo, escalado mas chico, centrado en un canvas blanco --
    para que ningun launcher (circulo, squircle, etc.) lo recorte."""
    canvas = Image.new("RGB", (tamano, tamano), (255, 255, 255))
    lado_logo = int(tamano * escala)
    logo_chico = logo.resize((lado_logo, lado_logo), Image.LANCZOS).convert("RGB")
    offset = ((tamano - lado_logo) // 2, (tamano - lado_logo) // 2)
    canvas.paste(logo_chico, offset)
    return canvas


def generar():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    logo = Image.open(LOGO_PATH).convert("RGBA")

    generados = []
    for tamano in (192, 512):
        archivo = OUT_DIR / f"icon-{tamano}.png"
        _icono_simple(logo, tamano).save(archivo)
        generados.append(archivo.name)

    archivo = OUT_DIR / "icon-maskable-512.png"
    _icono_maskable(logo, 512).save(archivo)
    generados.append(archivo.name)

    # iOS (apple-touch-icon): sin transparencia, fondo blanco solido.
    archivo = OUT_DIR / "apple-touch-icon.png"
    logo.resize((180, 180), Image.LANCZOS).convert("RGB").save(archivo)
    generados.append(archivo.name)

    return generados


if __name__ == "__main__":
    archivos = generar()
    print(f"Generados {len(archivos)} iconos en {OUT_DIR}:")
    for a in archivos:
        print(" -", a)
