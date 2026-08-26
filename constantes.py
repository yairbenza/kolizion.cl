import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BASE_DIR / "data" / "catalog.json"
REGLAS_PATH = BASE_DIR / "data" / "reglas_streetwear.json"
HISTORIAL_PATH = BASE_DIR / "data" / "historial_usuarios.json"
CHATS_KOKO_PATH = BASE_DIR / "data" / "chats_koko.json"
TIENDAS_PATH = BASE_DIR / "data" / "tiendas.json"
ENVIOS_TIENDAS_PATH = BASE_DIR / "data" / "envios_tiendas.json"
CLICS_TIENDAS_PATH = BASE_DIR / "data" / "clics_tiendas.json"
REPORTES_MANUALES_PATH = BASE_DIR / "data" / "reportes_manuales.json"
FAVORITOS_PATH = BASE_DIR / "data" / "favoritos.json"
LIMITE_KOKO_PATH = BASE_DIR / "data" / "limite_koko.json"

LIMITE_MENSAJES_KOKO_DIA = 15
CANTIDAD_RESULTADOS = 5

LARGO_MAXIMO_TEXTO_LIBRE = 200
LARGO_MAXIMO_MENSAJE_KOKO = 4000
MAX_MENSAJES_HISTORIAL_KOKO = 60
VENTANA_CONFIRMACION_TIPO_PRENDA_KOKO = 6
GRAMAJE_MINIMO_CALIDAD_GSM = 180

CATEGORIAS_CON_GRAMAJE = {"polera", "camiseta"}

MATERIALES_CONOCIDOS = {
    "algodon_100": {"etiqueta": "Algodón 100%", "natural": True},
    "lana": {"etiqueta": "Lana", "natural": True},
    "cuero": {"etiqueta": "Cuero", "natural": True},
    "mezcla_algodon_poliester": {"etiqueta": "Mezcla algodón/poliéster", "natural": False},
    "poliester": {"etiqueta": "Poliéster", "natural": False},
    "nylon": {"etiqueta": "Nylon", "natural": False},
    "acrilico": {"etiqueta": "Acrílico", "natural": False},
}

CATEGORIA_GRUPOS = {
    "prenda superior": ["poleron", "camisa", "chaqueta", "polera", "chaleco", "camiseta", "top"],
    "prenda inferior": ["pantalon", "falda", "shorts", "faldacargo", "bikeshorts"],
}

TIPO_PRENDA_A_CATEGORIA_GRUPO = {
    tipo: grupo for grupo, tipos in CATEGORIA_GRUPOS.items() for tipo in tipos
}
TIPO_PRENDA_A_CATEGORIA_GRUPO["gorro"] = "gorro"

CORTES_CONOCIDOS = {
    "baggy": ["baggy"],
    "boxy fit": ["boxy fit", "boxyfit", "boxy"],
    "slim fit": ["slim fit", "slimfit", "slim"],
    "oversize": ["oversize", "oversized"],
    "skinny": ["skinny"],
    "regular fit": ["regular fit"],
    "straight": ["straight fit", "straight", "recto"],
}

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
    "gorro": ["gorro", "gorra", "jockey", "cap"],
    "accesorio": ["accesorio", "mochila", "cinturon"],
}

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
    "bomber": ["bomber"],
    "mezclilla": ["mezclilla", "denim", "jeans", "jean"],
    "cuero": ["cuero", "de cuero", "leather"],
}

SUBTIPOS_POR_TIPO_PRENDA = {
    "pantalon": {"buzo", "jeans", "cargo"},
    "shorts": {"jeans", "tela", "cargo", "bano"},
    "top": {"croptop", "babytee", "halter", "corset", "tanktop", "blusa"},
    "chaqueta": {"bomber", "mezclilla", "cuero"},
}

TIPOS_CON_LARGO = {"polera", "camiseta", "top"}

LARGOS_CONOCIDOS = {
    "crop": ["crop", "corto"],
    "normal": ["largo normal"],
    "extra largo": ["extra largo", "longline"],
}

MANGAS_CONOCIDAS = {
    "larga": ["manga larga", "mangas largas"],
    "corta": ["manga corta", "mangas cortas"],
}

CAPUCHAS_CONOCIDAS = {
    "con capucha": ["con capucha"],
    "sin capucha": ["sin capucha"],
}

CIERRES_CONOCIDOS = {
    "con cierre": ["con cierre"],
    "sin cierre": ["sin cierre", "crewneck"],
}

COLORES_GORRO_CONOCIDOS = ["blanco", "negro", "rojo", "azul", "amarillo", "beige", "morado", "verde"]
COLORES_VIVOS_GORRO = {"rojo", "azul", "amarillo", "morado", "verde"}
FORMAS_GORRO_CONOCIDAS = ["curvo", "plano", "lana"]

FORMA_GORRO_CONOCIDA = {
    "curvo": ["gorro curvo", "curvo"],
    "plano": ["gorro plano", "plano", "snapback"],
    "lana": ["gorro de lana", "gorro lana", "de lana", "lana", "beanie", "gorro tejido"],
}

LIMITES_PESO_KG = {
    "mujer": {"S": 60, "M": 70, "L": 80},
    "hombre": {"S": 68, "M": 80, "L": 92},
}

LIMITES_ALTURA_M = {
    "mujer": {"S": 1.65, "M": 1.70, "L": 1.75},
    "hombre": {"S": 1.70, "M": 1.78, "L": 1.85},
}

ORDEN_TALLAS = ["S", "M", "L", "XL"]

HOBBIES_CONOCIDOS = {
    "musica": {"etiqueta": "Música"},
    "deportes": {"etiqueta": "Deportes"},
    "relajo": {"etiqueta": "Relajo / lifestyle tranquilo"},
    "arte_cultura": {"etiqueta": "Arte y cultura"},
    "gaming": {"etiqueta": "Gaming"},
    "peliculas_series": {"etiqueta": "Películas y series"},
}

GENEROS_MUSICALES_CONOCIDOS = {
    "rock": {"etiqueta": "Rock"},
    "reggaeton": {"etiqueta": "Reguetón / urbano"},
    "pop": {"etiqueta": "Pop"},
    "hip_hop": {"etiqueta": "Hip-hop / rap"},
    "electronica": {"etiqueta": "Electrónica"},
    "indie": {"etiqueta": "Indie / alternativo"},
}

DEPORTES_CONOCIDOS = {
    "gym": {"etiqueta": "Gym"},
    "futbol": {"etiqueta": "Fútbol"},
    "baseball": {"etiqueta": "Baseball"},
    "ski": {"etiqueta": "Ski"},
}

EXCLUSIONES_HOBBY = {
    ("arte_cultura", None): {"bikeshorts"},
    ("deportes", "gym"): {"camisa"},
}

REGLAS_HOBBY = {
    ("musica", "rock"): [
        {
            "etiqueta": "Música: Rock",
            "prenda_preferida": {"polera", "poleron"},
            "corte": "oversize",
            "color_base": "predominantemente oscuro (negro, gris), dejando que el gráfico sea el punto focal",
            "nota": (
                "gráfico grande y llamativo tipo banda/concierto, no diseños minimalistas sin estampado; "
                "combinar con un pantalón suelto/baggy abajo"
            ),
            "confianza": "validacion_inicial",
        },
    ],
    ("deportes", "gym"): [
        {
            "etiqueta": "Deportes: Gym",
            "prenda_preferida": {"pantalon"},
            "corte": "baggy",
            "color_base": "sin restricción particular de color",
            "nota": (
                "con detalle de línea lateral, estilo jogger deportivo. Si el catálogo llega a tener "
                "marcas como Nike o Adidas son buena referencia de esta estética -- hoy el catálogo es "
                "de marcas chicas independientes, así que probablemente no las tenga: nunca prometas "
                "una marca que no esté realmente en los resultados"
            ),
            "confianza": "validacion_inicial",
        },
        {
            "etiqueta": "Deportes: Gym",
            "prenda_preferida": {"poleron"},
            "corte": "boxy fit",
            "color_base": "sin restricción particular de color",
            "nota": (
                "con diseño o estampado propio, no liso básico. Misma referencia opcional a Nike/Adidas "
                "que en pantalón, solo si el catálogo realmente las tiene"
            ),
            "confianza": "validacion_inicial",
        },
        {
            "etiqueta": "Deportes: Gym",
            "prenda_preferida": {"shorts"},
            "corte": "baggy",
            "color_base": "sin restricción particular de color",
            "nota": (
                "anchos y sueltos -- nunca ajustados ni tipo compresión, eso queda explícitamente fuera "
                "de esta idea (la ropa técnica ajustada sigue siendo la exclusión ya validada, no esta "
                "sugerencia)"
            ),
            "confianza": "validacion_inicial",
        },
        {
            "etiqueta": "Deportes: Gym",
            "prenda_preferida": {"gorro"},
            "tipo_sugerencia": "accesorio",
            "nota": (
                "un gorro/jockey es un accesorio frecuente para completar el look de gym -- mencionalo "
                "como complemento posible, nunca como si fuera la prenda principal que la persona pidió"
            ),
            "confianza": "validacion_inicial",
        },
    ],
}

REGIONES_CHILE = [
    "Arica y Parinacota", "Tarapacá", "Antofagasta", "Atacama", "Coquimbo",
    "Valparaíso", "Metropolitana", "O'Higgins", "Maule", "Ñuble", "Biobío",
    "La Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes",
]

ALIAS_METROPOLITANA = ("santiago", "region metropolitana", " rm", "rm ")

RANGOS_CLICS = {
    "7": {"etiqueta": "Últimos 7 días", "frase": "esta semana", "dias": 7},
    "14": {"etiqueta": "Últimas 2 semanas", "frase": "estas 2 semanas", "dias": 14},
    "30": {"etiqueta": "Últimos 30 días", "frase": "este mes", "dias": 30},
    "todo": {"etiqueta": "Todo el tiempo", "frase": "en total", "dias": None},
}


# --- Funciones de utilidad y sanitización ------------------------------------

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _texto_seguro(valor, largo_max=LARGO_MAXIMO_TEXTO_LIBRE):
    if valor is None:
        return ""
    if not isinstance(valor, str):
        valor = str(valor)
    return valor.strip()[:largo_max]


def _lista_texto_segura(valor, largo_max_item=30, cantidad_max=20):
    if not isinstance(valor, list):
        return []
    return [_texto_seguro(v, largo_max_item) for v in valor[:cantidad_max]]


def _normalizar_email(email):
    return (email or "").strip().lower()


def _parsear_fecha_iso(texto):
    try:
        return datetime.fromisoformat(texto)
    except (ValueError, TypeError):
        return None


def _quitar_tildes(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _contiene_palabra(texto, variante):
    return re.search(rf"\b{re.escape(variante)}(?:es|s)?\b", texto) is not None


def tokenizar(texto):
    return set(re.findall(r"[a-záéíóúñ0-9]+", texto.lower()))


def _detectar(texto_pedido, conocidos):
    texto = _quitar_tildes(texto_pedido.lower())
    for canonico, variantes in conocidos.items():
        if any(_contiene_palabra(texto, variante) for variante in variantes):
            return canonico
    return None


def _detectar_reciente(mensajes, conocidos):
    for mensaje in reversed(mensajes):
        texto = _quitar_tildes((mensaje or "").lower())
        for canonico, variantes in conocidos.items():
            if any(_contiene_palabra(texto, variante) for variante in variantes):
                return canonico
    return None


def _mencionado_en_conversacion(canonico, conocidos, mensajes):
    variantes = conocidos.get(canonico)
    if not variantes:
        return False
    return any(
        any(_contiene_palabra(_quitar_tildes((m or "").lower()), v) for v in variantes)
        for m in mensajes
    )


def _valor_o_deteccion(valor_propuesto, conocidos, mensajes, detector_conversacion, mensajes_confirmacion=None):
    propuesto = (valor_propuesto or "").lower()
    ventana = mensajes if mensajes_confirmacion is None else mensajes_confirmacion
    if propuesto in conocidos and _mencionado_en_conversacion(propuesto, conocidos, ventana):
        return propuesto
    return detector_conversacion(mensajes)


def _siguiente_seguro(valor, por_defecto="/"):
    valor = (valor or "").strip()
    if not valor or not valor.startswith("/") or valor.startswith("//") or "://" in valor:
        return por_defecto
    return valor


def _es_safari(user_agent_texto):
    ua = (user_agent_texto or "").lower()
    if "safari" not in ua:
        return False
    otros_motores = ("chrome", "chromium", "crios", "fxios", "edgios", "edg/", "opr/", "android")
    return not any(m in ua for m in otros_motores)
