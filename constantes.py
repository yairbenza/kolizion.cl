import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BASE_DIR / "data" / "catalog.json"
REGLAS_PATH = BASE_DIR / "data" / "reglas_streetwear.json"
FAMOSOS_ESTILO_PATH = BASE_DIR / "data" / "famosos_estilo.json"
HISTORIAL_PATH = BASE_DIR / "data" / "historial_usuarios.json"
CHATS_KOKO_PATH = BASE_DIR / "data" / "chats_koko.json"
TIENDAS_PATH = BASE_DIR / "data" / "tiendas.json"
TAGS_GRAFICO_PATH = BASE_DIR / "data" / "tags_grafico.json"
TAGS_FORMA_GORRO_PATH = BASE_DIR / "data" / "tags_forma_gorro.json"
ENVIOS_TIENDAS_PATH = BASE_DIR / "data" / "envios_tiendas.json"
CLICS_TIENDAS_PATH = BASE_DIR / "data" / "clics_tiendas.json"
REPORTES_MANUALES_PATH = BASE_DIR / "data" / "reportes_manuales.json"
FAVORITOS_PATH = BASE_DIR / "data" / "favoritos.json"
RESENAS_PATH = BASE_DIR / "data" / "resenas.json"
LIMITE_KOKO_PATH = BASE_DIR / "data" / "limite_koko.json"

# Subido temporalmente para pruebas (2026-08-26, pedido del usuario) -- volver
# a 15 antes de sacar la app real (asi se controla el gasto de API por persona).
LIMITE_MENSAJES_KOKO_DIA = 1000
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

# Regla validada (ver docs/buscador.md, tabla "Filtros del formulario"):
# "top" (croptop/babytee/halter/corset/tanktop/blusa) no se ofrece a
# genero "hombre" -- estaba documentada pero nunca aplicada en el
# buscador, asi que una busqueda amplia (ej. "prenda superior" sin tipo
# especifico) para hombre podia devolver tops (bug real reportado por el
# usuario, 2026-08-26). Filtro general por categoria, no por producto --
# si se valida otra categoria exclusiva de un genero, se agrega aca.
CATEGORIAS_EXCLUIDAS_POR_GENERO = {
    "hombre": {"top"},
}

TIPO_PRENDA_A_CATEGORIA_GRUPO = {
    tipo: grupo for grupo, tipos in CATEGORIA_GRUPOS.items() for tipo in tipos
}
TIPO_PRENDA_A_CATEGORIA_GRUPO["gorro"] = "gorro"

# Apodos con los que la gente nombra estas tiendas en el chat aunque no
# coincidan con el nombre real del catalogo -- confirmados por el propio
# usuario (Doslobos = "Don Lobo", UNK Chile = "IO Chile"). Solo sirven para
# que una exclusion en Koko ("nada de Don Lobo") encuentre la tienda real;
# no se agregan mas alias sin que el usuario los confirme.
ALIAS_TIENDAS = {
    "don lobo": "Doslobos",
    "dos lobos": "Doslobos",
    "io chile": "UNK Chile",
}

# Colores que Koko/el buscador pueden pedir de forma explicita (clave
# canonica -> variantes de texto para encontrarlos en nombre/tags/
# descripcion del producto, mismo mecanismo que ya usa CORTES_CONOCIDOS).
# El catalogo NO tiene un campo "color" estructurado para la mayoria de las
# prendas (solo gorro tiene "color_dominante") -- por eso el match real se
# hace contra el texto existente de la ficha, nunca inventando un color que
# no este escrito ahi (2026-08-27).
COLORES_CONOCIDOS = {
    "rojo": ["rojo", "roja", "red"],
    "azul": ["azul", "blue"],
    "verde": ["verde", "green"],
    "beige": ["beige"],
    "negro": ["negro", "negra", "black"],
    "blanco": ["blanco", "blanca", "white"],
    "gris": ["gris", "grey", "gray"],
    "cafe": ["cafe", "marron", "brown"],
    "amarillo": ["amarillo", "amarilla", "yellow"],
    "naranja": ["naranja", "naranjo", "orange"],
    "morado": ["morado", "morada", "purpura", "purple"],
    "rosado": ["rosado", "rosada", "rosa", "fucsia", "pink"],
    "celeste": ["celeste"],
}

# Expansion secundaria SOLO para "Buscar mas" cuando ya no quedan prendas
# del color exacto -- colores visualmente cercanos, nunca uno completamente
# distinto (pedido explicito del usuario, 2026-08-27). Un color sin entrada
# aca simplemente no tiene expansion (no rompe nada, solo no amplia).
COLORES_SIMILARES = {
    "rojo": ["burdeo", "granate", "terracota", "naranja oscuro"],
    "azul": ["celeste", "azul marino", "petroleo"],
    "verde": ["oliva", "musgo", "verde oscuro"],
    "beige": ["crema", "arena", "cafe claro"],
    "negro": ["gris oscuro"],
    "blanco": ["crema", "off-white", "offwhite"],
}

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
    "pantalon": ["pantalon", "buzo"],
    "shorts": ["shorts", "short", "jorts"],
    "falda": ["falda"],
    "gorro": ["gorro", "gorra", "jockey", "cap"],
    "accesorio": ["accesorio", "mochila", "cinturon"],
}

SUBTIPOS_CONOCIDOS = {
    "buzo": ["buzo", "jogger"],
    "jeans": ["jeans", "jean", "denim", "mezclilla"],
    "cargo": ["cargo"],
    "tela": ["tela"],
    "bano": ["bano", "baño"],
    "jorts": ["jort", "jorts"],
    "croptop": ["crop top", "crop hoodie", "croptop"],
    "babytee": ["baby tee", "babytee"],
    "halter": ["halter", "top con breteles", "breteles"],
    "corset": ["corset", "top estructurado"],
    "tanktop": ["tank top", "tanktop", "musculosa"],
    "blusa": ["blusa", "camisas/blusas", "camisas / blusas"],
    "bomber": ["bomber"],
    "mezclilla": ["mezclilla", "denim", "jeans", "jean"],
    "cuero": ["cuero", "de cuero", "leather"],
    # 2026-08-30: "chaleco" ya existia como tipo de prenda en el formulario
    # pero sin subtipo -- cardigan (categoria exclusiva de mujer, regla del
    # 2026-08-28) no se podia buscar especificamente, se mezclaba con los
    # 26 chalecos genericos unisex del catalogo.
    "cardigan": ["cardigan", "cardigans"],
}

SUBTIPOS_POR_TIPO_PRENDA = {
    "pantalon": {"buzo", "jeans", "cargo"},
    "shorts": {"jeans", "tela", "cargo", "bano", "jorts"},
    "top": {"croptop", "babytee", "halter", "corset", "tanktop", "blusa"},
    "chaqueta": {"bomber", "mezclilla", "cuero"},
    "chaleco": {"cardigan"},
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
    "anime": {"etiqueta": "Anime"},
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

# Exclusiones duras por ocasion, SOLO mujer (pedido explicito del usuario,
# 2026-08-30). A diferencia de EXCLUSIONES_HOBBY (que solo reordena, ver
# nivel_hobby en motor_recomendacion.py), estas SI sacan la prenda del pool
# de candidatos -- el usuario pidio expresamente no tocar el ranking para
# esto. Cada regla usa solo atributos que YA existen en el catalogo
# (categoria/subtipo/capucha); "calzas" (carrete), "deportiva"/"casero"/
# "chill" (junta social, junta familiar, asado, concierto) y "brillo"/
# "tachas" (boost de concierto) se omitieron a proposito porque el catalogo
# no tiene esos atributos tageados (ver docs/buscador.md) -- no se inventaron.
EXCLUSIONES_OCASION_MUJER = {
    "carrete": [
        {"categoria": "poleron", "capucha": "con capucha"},
        {"categoria": "chaleco"},
        {"categoria": "pantalon", "subtipo": "buzo"},
    ],
    "universidad": [
        {"categoria": "chaqueta", "subtipo": "cuero"},
    ],
    "social_casera": [
        {"categoria": "pantalon", "subtipo": "buzo"},
    ],
    "concierto_festival": [
        {"categoria": "pantalon", "subtipo": "buzo"},
    ],
}

# Sinonimos de texto libre ("otro" en el formulario, o texto de Koko) que
# mapean a las claves de arriba -- "junta social"/"junta familiar" son los
# valores reales del <select> del formulario; el resto son la forma en que
# el usuario nombro la misma ocasion al pedir esta regla.
GRUPOS_OCASION_MUJER = {
    "carrete": "carrete",
    "universidad": "universidad",
    "junta social": "social_casera",
    "junta de amigas": "social_casera",
    "junta familiar": "social_casera",
    "comida familiar": "social_casera",
    "asado": "social_casera",
    "concierto/festival": "concierto_festival",
    "concierto": "concierto_festival",
    "festival": "concierto_festival",
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


def _mencionado_en_mensaje_mas_reciente(canonico, conocidos, mensajes):
    """Como _mencionado_en_conversacion, pero solo cuenta si el canonico
    aparece en el mensaje MAS RECIENTE que menciona algun tipo conocido --
    evita que un tema ya superado (mencionado varios turnos atras, ej. un
    "pantalon" nombrado de pasada antes de enfocarse en el "poleron") siga
    "confirmando" una propuesta de Koko que ya no es la vigente."""
    for mensaje in reversed(mensajes):
        texto = _quitar_tildes((mensaje or "").lower())
        if any(_contiene_palabra(texto, variante) for variantes in conocidos.values() for variante in variantes):
            variantes_canonico = conocidos.get(canonico) or []
            return any(_contiene_palabra(texto, v) for v in variantes_canonico)
    return False


def _valor_o_deteccion(
    valor_propuesto, conocidos, mensajes, detector_conversacion,
    mensajes_confirmacion=None, solo_mensaje_mas_reciente=False,
):
    propuesto = (valor_propuesto or "").lower()
    ventana = mensajes if mensajes_confirmacion is None else mensajes_confirmacion
    if propuesto in conocidos:
        confirmado = (
            _mencionado_en_mensaje_mas_reciente(propuesto, conocidos, ventana)
            if solo_mensaje_mas_reciente
            else _mencionado_en_conversacion(propuesto, conocidos, ventana)
        )
        if confirmado:
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
