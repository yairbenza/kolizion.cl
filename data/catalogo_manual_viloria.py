"""Catalogo MANUAL de Viloria (venta por WhatsApp Business, sin sitio web
ni Shopify) -- separado a proposito del resto de construir_catalogo_real.py
(pedido explicito del usuario, 2026-08-29): actualizar precio/stock/tallas/
colores/productos de Viloria solo requiere editar ESTE archivo, sin tocar
ninguna otra tienda ni el resto del pipeline.

Cada producto trae un "idx" fijo (no la posicion en la lista) para que su
id ("real_viloria_%04d") nunca cambie aunque se agreguen/reordenen
productos mas adelante -- los numeros ya usados no se reciclan. El idx
corresponde al numero original de la lista de 16 productos que dio el
usuario, para poder seguir agregando los que faltan sin chocar ids.

Datos reales sacados de la ficha de WhatsApp Business de Viloria (link
wa.me de cada producto) mas la foto real del catalogo (recortada para
sacar la interfaz de WhatsApp, se conserva la prenda tal cual) cuando el
color de la prenda es inequivocamente visible en ella -- nunca inventados.
Solo estan cargados los productos que ya tienen foto real confirmada
(7 de 16 al 2026-08-29); el resto se agrega cuando lleguen sus fotos.
"""

VILORIA_PRODUCTOS = [
    {
        "idx": 1,
        "nombre": "TOADALLY FRESH",
        "precio": 24990,
        "precio_original": 27990,
        "link": "https://wa.me/p/28340166459004562/56981427342",
        "imagen": "/static/img/viloria/toadally-fresh.jpeg",
        "descripcion": "Una pieza llamativa, creativa y con identidad propia...",
        "tallas": ["S", "M", "L"],
        "colores": ["Blanco"],
    },
    {
        "idx": 2,
        "nombre": "Jersey's HELLSTAR Azul",
        "precio": 26990,
        "link": "https://wa.me/p/27651796711137373/56981427342",
        "imagen": "/static/img/viloria/jersey-hellstar-azul.jpeg",
        "colores": ["Azul", "Negro"],
    },
    {
        "idx": 3,
        "nombre": "Jersey's HELLSTAR Sports Morado",
        "precio": 26990,
        "link": "https://wa.me/p/37584812481164858/56981427342",
        "imagen": "/static/img/viloria/jersey-hellstar-sports-morado.jpeg",
        "colores": ["Morado", "Negro", "Blanco"],
    },
    {
        "idx": 4,
        "nombre": "Jersey's HELLSTAR Rojo",
        "precio": 26990,
        "link": "https://wa.me/p/27484964857867002/56981427342",
        "imagen": "/static/img/viloria/jersey-hellstar-rojo.jpeg",
        "colores": ["Rojo", "Negro", "Blanco"],
    },
    {
        "idx": 6,
        "nombre": "Chaqueta denim - DANGEROUS",
        "precio": 34990,
        "precio_original": 41990,
        "link": "https://wa.me/p/27985118037738558/56981427342",
        "imagen": "/static/img/viloria/chaqueta-denim-dangerous.jpeg",
        "descripcion": (
            "Chaqueta denim con efecto desgastado y bordado DANGEROUS. Una "
            "prenda con personalidad que eleva cualquier outfit.... "
            "Bordado DANGEROUS en pecho y espalda. Cuello y puños RIB."
        ),
        "tallas": ["S", "M", "L", "XL"],
        # Bug real (2026-08-29, reportado por el usuario): la ficha declara
        # 2 variantes (Cafe y Blue Jeans) pero la unica foto real que
        # tenemos es la Cafe -- taguear "Blue Jeans" hacia que la busqueda
        # "chaqueta azul" mostrara esta foto cafe como si fuera azul.
        # Se deja solo el color que la foto real confirma; si llega una
        # foto de la variante Blue Jeans se puede agregar de vuelta.
        "colores": ["Café"],
    },
    {
        "idx": 9,
        "nombre": "BANE - Oversized",
        "precio": 29990,
        "link": "https://wa.me/p/27671194605846275/56981427342",
        "imagen": "/static/img/viloria/bane-oversized.jpeg",
        "descripcion": (
            "Inspirada en prendas intervenidas a mano, la polera BANE "
            "incorpora un efecto de pinceladas y desgaste que le entrega "
            "un aspecto.... Estética dark/underground, tela gruesa 100% "
            "algodón."
        ),
        # XXL declarada en la ficha real pero la app solo modela hasta XL
        # (misma limitacion ya documentada para AbsolutelyWrong).
        "tallas": ["M", "L", "XL"],
        # Bug real (2026-08-30, reportado por el usuario): la ficha declara
        # 4 variantes (Blanco/Negro/Burdeo/Verde) pero la unica foto real
        # que tenemos es la Blanca -- igual que la Chaqueta DANGEROUS,
        # taguear las otras 3 hacia que buscar "polera verde" o "roja"
        # mostrara esta foto blanca. Se deja solo el color que la foto
        # confirma.
        "colores": ["Blanco"],
    },
    {
        "idx": 12,
        "nombre": "BANGE",
        "precio": 25990,
        "precio_original": 27990,
        "link": "https://wa.me/p/28081448914846326/56981427342",
        "imagen": "/static/img/viloria/bange.jpeg",
        "colores": ["Rosado"],
    },
]
