import json
import os
import random
import re
import secrets
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import anthropic
from flask import Flask, request, jsonify, render_template, redirect, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import db_usuarios

app = Flask(__name__)

# Rate limiting (2026-08-16, pedido explicito antes de produccion): limita
# cuantas peticiones seguidas puede mandar la MISMA ip a las rutas
# sensibles (login de admin, buscador, chat de Koko) -- ver los decorators
# @limiter.limit(...) en cada ruta. Storage en memoria (nada nuevo que
# instalar/configurar) -- funciona perfecto con un solo proceso, que es
# como corre esta app hoy. OJO si el hosting real llega a correr VARIOS
# procesos a la vez (ej. gunicorn con varios workers): cada uno cuenta
# aparte, asi que el limite efectivo total seria mas alto que el numero de
# aca -- si eso pasa, hace falta un storage compartido (ej. Redis) para
# que el conteo sea el mismo entre todos los procesos.
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")


@app.errorhandler(429)
def limite_de_peticiones_excedido(error):
    """Respuesta generica al pasarse un limite -- nunca dice CUAL limite
    ni por que (ej. nunca "demasiados intentos de contraseña"), para no
    darle pistas a quien este probando cosas."""
    mensaje = "Demasiadas peticiones seguidas -- espera un minuto e intenta de nuevo."
    if request.path.startswith("/api/"):
        return jsonify({"error": mensaje}), 429
    return mensaje, 429

BASE_DIR = Path(__file__).parent
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

# Cuantos mensajes puede mandarle CADA usuario (por email) a Koko en un dia
# -- protege contra un costo descontrolado de la API de Anthropic. Ventana
# movil de 24h (no se reinicia a medianoche), ver mensajes_usuario_ultimas_24h().
LIMITE_MENSAJES_KOKO_DIA = 15

# Cuantos productos mostrar por busqueda (primaria y "mostrar mas
# opciones"), mientras se usa catalogo de prueba. La regla de "sin
# consenso" (2-3 alternativas) es aparte -- esa cantidad viene de una
# decision de trabajo documentada en CLAUDE.md, no de este numero.
CANTIDAD_RESULTADOS = 5


def _cargar_env_local():
    """Carga variables desde un archivo .env local (si existe, nunca se
    commitea) al entorno del proceso -- sin agregar una dependencia nueva
    solo para esto. No pisa una variable que ya este seteada afuera."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for linea in env_path.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave = clave.strip()
        if clave and clave not in os.environ:
            os.environ[clave] = valor.strip().strip('"').strip("'")


_cargar_env_local()

# Clave de la API de Anthropic para el chat de Koko (ver seccion "Koko" en
# CLAUDE.md). Se lee de una variable de entorno real o de un archivo .env
# local -- nunca hardcodeada ni pedida por chat. Si falta, /api/koko/chat
# responde con un aviso en vez de caerse.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Contraseña del panel de administrador (/admin/tiendas, /admin/clics) --
# mismo mecanismo que ANTHROPIC_API_KEY (.env local, nunca en el codigo ni
# en git). Si no esta configurada, el login queda deshabilitado a proposito
# (nadie puede entrar, ni con la clave en blanco) en vez de dejar el panel
# abierto por error.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

# Credenciales de Google OAuth (cuentas reales de usuario, ver
# docs/cuentas.md) -- mismo mecanismo .env que ANTHROPIC_API_KEY/
# ADMIN_PASSWORD. Si estan vacias, el boton "Continuar con Google" queda
# deshabilitado a proposito (no se ofrece la opcion) en vez de fallar feo
# a mitad del flujo -- sigue funcionando el registro con email/contraseña.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# Clave para firmar la cookie de sesion (login de admin Y cuentas de
# usuario). Preferimos una fija en FLASK_SECRET_KEY (.env) -- IMPORTANTE en
# un hosting real que corra mas de un proceso (ej. gunicorn con varios
# workers): si cada proceso genera la suya propia al azar, una sesion
# firmada por un proceso no la reconoce otro, y el login falla de forma
# intermitente y rara. Sin esa variable (caso normal en desarrollo local,
# un solo proceso), se genera sola al arrancar -- ahi el unico efecto de
# que cambie es que las sesiones viejas dejan de ser validas.
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
# 30 dias (2026-08-24, pedido explicito del usuario para que un cliente no
# tenga que volver a loguearse cada rato) -- antes eran 12 horas. Tambien
# alarga la sesion del panel de admin (mismo mecanismo de sesion), aceptado:
# sigue protegido por contraseña + rate limiting, y tiene boton de logout.
app.permanent_session_lifetime = timedelta(days=30)
# Limite de tamaño de subida (foto de perfil, ver /perfil/foto) -- Werkzeug
# rechaza el request ANTES de bufferear todo el archivo si se pasa, en vez
# de dejar que alguien mande un archivo gigante y se coma la memoria.
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024  # 3 MB

db_usuarios.inicializar_db()


def requiere_admin(vista):
    """Decorator para las rutas /admin/* -- si no hay sesion valida, manda
    a /admin/login (guardando a donde queria ir, para volver ahi despues)."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get("admin_autenticado"):
            return redirect(f"/admin/login?siguiente={request.path}")
        return vista(*args, **kwargs)
    return envoltura


def _siguiente_seguro(valor, por_defecto="/"):
    """Valida el parametro 'siguiente' (a donde volver despues de
    loguearse) -- debe ser una ruta interna que empiece con '/' y nunca
    '//' o contener '://', para que nadie pueda armar un link de login que
    en realidad redirija a un sitio externo (mismo criterio que ya se usa
    en /admin/login)."""
    valor = (valor or "").strip()
    if not valor or not valor.startswith("/") or valor.startswith("//") or "://" in valor:
        return por_defecto
    return valor


def _es_safari(user_agent_texto):
    """Detecta Safari de verdad (no Chrome/Firefox/Edge corriendo sobre el
    motor de Safari en iOS, que tambien traen 'Safari' en el User-Agent).
    2026-08-24, pedido explicito del usuario: en Safari la sesion nunca se
    guarda como 'permanente' -- siempre vuelve a pedir el login, sin
    importar si la persona eligio 'mantener sesion iniciada' (ver
    _iniciar_sesion_usuario). Deteccion por texto, nunca 100% infalible,
    pero suficiente para esto (no es una barrera de seguridad, solo decide
    cuanto dura la sesion)."""
    ua = (user_agent_texto or "").lower()
    if "safari" not in ua:
        return False
    otros_motores = ("chrome", "chromium", "crios", "fxios", "edgios", "edg/", "opr/", "android")
    return not any(m in ua for m in otros_motores)


def requiere_cuenta(vista):
    """Decorator para las rutas que exigen una cuenta real (hoy: los 2
    puntos de 'comprar', /ir/<tienda_id> y /ir/<tienda_id>/<producto>) --
    calco exacto de requiere_admin, pero para session["usuario_id"] en vez
    de session["admin_autenticado"]. Ver docs/cuentas.md."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get("usuario_id"):
            return redirect(f"/login?siguiente={_siguiente_seguro(request.full_path.rstrip('?'))}")
        return vista(*args, **kwargs)
    return envoltura


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- Saneo de entrada (2026-08-16) ------------------------------------------
# Nunca confiar en el tipo ni el largo de lo que llega en un JSON de
# afuera -- request.get_json() ya evita que un JSON mal formado rompa nada
# (Flask/Werkzeug lo manejan solos), pero nada impide que alguien mande
# {"categoria": ["a","b"]} o un string de 5MB donde se espera un texto
# corto. Sin esto, un campo que no es string revienta mas abajo (ej.
# " ".join() con algo que no sea texto tira TypeError -> error 500) en vez
# de fallar de forma prolija.

LARGO_MAXIMO_TEXTO_LIBRE = 200
LARGO_MAXIMO_MENSAJE_KOKO = 4000
MAX_MENSAJES_HISTORIAL_KOKO = 60
# Ventana reciente (2026-08-25, ver _valor_o_deteccion) para confirmar que
# el tipo_prenda que Koko propuso de verdad sigue siendo el tema actual --
# ultimos 6 mensajes (~3 idas y vueltas), no toda la conversacion (que
# puede tener hasta MAX_MENSAJES_HISTORIAL_KOKO mensajes de largo).
VENTANA_CONFIRMACION_TIPO_PRENDA_KOKO = 6


def _texto_seguro(valor, largo_max=LARGO_MAXIMO_TEXTO_LIBRE):
    """Convierte lo que mande el usuario a un string limpio y acotado.
    Trunca en vez de rechazar -- mejor UX (la busqueda/el mensaje sigue
    funcionando, solo se recorta lo excesivo) y nunca None/lista/dict de
    aca en adelante, pase lo que pase con el tipo original."""
    if valor is None:
        return ""
    if not isinstance(valor, str):
        valor = str(valor)
    return valor.strip()[:largo_max]


def _lista_texto_segura(valor, largo_max_item=30, cantidad_max=20):
    """Version en lista de _texto_seguro -- para campos tipo
    gorro_colores. Si "valor" ni siquiera es una lista, devuelve []."""
    if not isinstance(valor, list):
        return []
    return [_texto_seguro(v, largo_max_item) for v in valor[:cantidad_max]]


# --- Historial por email, para personalizar el chat de Koko -----------------
# Un solo archivo JSON (mismo patron que catalog.json/reglas_streetwear.json),
# dict keyado por email en minuscula. Nunca se registra nada de busquedas
# "regalo" -- son sobre otra persona, no sobre el estilo de quien busca.

def cargar_historial():
    if not HISTORIAL_PATH.exists():
        return {}
    return load_json(HISTORIAL_PATH)


def guardar_historial(historial):
    HISTORIAL_PATH.write_text(json.dumps(historial, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalizar_email(email):
    return (email or "").strip().lower()


def _parsear_fecha_iso(texto):
    """Parsea una fecha ISO guardada por esta misma app (siempre con
    datetime.now(timezone.utc).isoformat()). Devuelve None si esta ausente
    o mal formada, en vez de reventar -- quien la use decide que hacer con
    ese None (normalmente: tratarla como si nunca hubiera pasado)."""
    try:
        return datetime.fromisoformat(texto)
    except (ValueError, TypeError):
        return None


def registrar_busqueda(email, ocasion, categoria, tipo_prenda, corte):
    """Guarda una busqueda que el usuario hizo para si mismo (modo "yo") en
    su historial, para que Koko pueda basarse en ella despues."""
    email = _normalizar_email(email)
    if not email:
        return
    historial = cargar_historial()
    entrada = historial.setdefault(email, {"busquedas": [], "productos_interes": []})
    entrada["busquedas"].append({
        "fecha": datetime.now(timezone.utc).isoformat(),
        "ocasion": ocasion or "",
        "categoria": categoria or "",
        "tipo_prenda": tipo_prenda or "",
        "corte": corte or "",
    })
    guardar_historial(historial)


def registrar_interes(email, producto):
    """Guarda que el usuario hizo clic en "Ver producto" de una tarjeta de
    resultado (tambien solo aplica a busquedas "yo")."""
    email = _normalizar_email(email)
    if not email:
        return
    historial = cargar_historial()
    entrada = historial.setdefault(email, {"busquedas": [], "productos_interes": []})
    entrada["productos_interes"].append({
        "fecha": datetime.now(timezone.utc).isoformat(),
        "nombre": _texto_seguro(producto.get("nombre", "")),
        "tienda": _texto_seguro(producto.get("tienda", "")),
        "categoria": _texto_seguro(producto.get("categoria", "")),
        "corte": _texto_seguro(producto.get("corte", "")),
    })
    guardar_historial(historial)


# --- Favoritos por email -----------------------------------------------
# Mismo patron que el historial: un JSON keyado por email en minuscula,
# lista de productos (snapshot de lo que ya se mostro en una tarjeta -- se
# guarda tal cual llega, nunca se inventa nada nuevo). "nombre" identifica
# el producto dentro del catalogo mock (unico, mismo criterio que ya usa
# _clics_por_producto mas abajo).

def cargar_favoritos():
    if not FAVORITOS_PATH.exists():
        return {}
    return load_json(FAVORITOS_PATH)


def guardar_favoritos(favoritos):
    FAVORITOS_PATH.write_text(json.dumps(favoritos, ensure_ascii=False, indent=2), encoding="utf-8")


def obtener_favoritos(email):
    email = _normalizar_email(email)
    if not email:
        return []
    return cargar_favoritos().get(email, [])


def alternar_favorito(email, producto):
    """Si el producto (por nombre) ya estaba en favoritos, lo saca; si no
    estaba, lo agrega. Devuelve True si quedo marcado, False si se saco."""
    email = _normalizar_email(email)
    nombre = _texto_seguro(producto.get("nombre", ""))
    if not email or not nombre:
        return False

    favoritos = cargar_favoritos()
    lista = favoritos.setdefault(email, [])
    existente = next((p for p in lista if p.get("nombre") == nombre), None)

    if existente:
        lista.remove(existente)
        guardar_favoritos(favoritos)
        return False

    lista.append({
        "nombre": nombre,
        "marca": _texto_seguro(producto.get("marca", "")),
        "tienda": _texto_seguro(producto.get("tienda", "")),
        "categoria": _texto_seguro(producto.get("categoria", "")),
        "corte": _texto_seguro(producto.get("corte", "")),
        "precio": _texto_seguro(producto.get("precio", "")),
        "precio_original": _texto_seguro(producto.get("precio_original", "")),
        "descuento_pct": producto.get("descuento_pct") if isinstance(producto.get("descuento_pct"), (int, float)) else None,
        "descripcion": _texto_seguro(producto.get("descripcion", ""), 500),
        "link": _texto_seguro(producto.get("link", ""), 500),
        "imagen": _texto_seguro(producto.get("imagen", ""), 500),
        "fecha": datetime.now(timezone.utc).isoformat(),
    })
    guardar_favoritos(favoritos)
    return True


def vaciar_favoritos(email):
    """Borra TODOS los favoritos guardados de un email de una sola vez
    (boton "Borrar todos" en /favoritos, con confirmacion en el frontend)."""
    email = _normalizar_email(email)
    if not email:
        return False
    favoritos = cargar_favoritos()
    if email in favoritos:
        favoritos[email] = []
        guardar_favoritos(favoritos)
    return True


def _clics_por_producto(dias=7):
    """Cuenta clics en 'Ver producto' de TODOS los usuarios (historial_usuarios.json)
    de los ultimos N dias, agrupados por nombre de producto (unico dentro
    del catalogo mock -- 'tienda' es siempre la misma). Se usa como
    criterio real para la seccion Tendencias de /vitrina."""
    limite = datetime.now(timezone.utc) - timedelta(days=dias)
    conteo = Counter()
    for entrada in cargar_historial().values():
        for item in entrada.get("productos_interes", []):
            try:
                fecha = datetime.fromisoformat(item["fecha"])
            except (KeyError, ValueError):
                continue
            if fecha >= limite:
                conteo[item.get("nombre", "")] += 1
    return conteo


# Cuando no hay (o no alcanza) data real de clics para llenar Tendencias, se
# completa con estas etiquetas genericas -- describen algo real del
# producto (su categoria) o son honestas sobre no tener metricas todavia,
# nunca inventan un numero falso.
_ETIQUETAS_TENDENCIA_RESPALDO = ["Nuevo en la tienda", "Más buscado en {categoria}"]


def _armar_tendencias(catalog_disponible, cantidad):
    """Arma la seccion Tendencias: primero los productos con mas clics
    reales en las ultimas 24h (etiquetados con su puesto en el ranking), y
    si no hay suficientes, completa al azar con etiquetas genericas
    rotativas. Devuelve lista de (producto, razon).

    Ventana angosta a proposito (2026-08-26, antes eran 7 dias): "Tendencias"
    debe reflejar lo que esta caliente AHORA, no un acumulado de la semana
    -- con 7 dias, un producto que exploto ayer y ya nadie mira hoy podia
    seguir arriba varios dias mas solo por inercia."""
    conteo = _clics_por_producto(dias=1)
    catalog_por_nombre = {p["nombre"]: p for p in catalog_disponible}

    ranking = [n for n, _ in conteo.most_common() if n in catalog_por_nombre][:cantidad]
    resultado = []
    ids_usados = set()
    for puesto, nombre in enumerate(ranking, start=1):
        producto = catalog_por_nombre[nombre]
        etiqueta = "N.°1 en clics hoy" if puesto == 1 else f"N.°{puesto} en clics hoy"
        resultado.append((producto, etiqueta))
        ids_usados.add(producto["id"])

    faltan = cantidad - len(resultado)
    if faltan > 0:
        candidatos = [p for p in catalog_disponible if p["id"] not in ids_usados]
        for i, producto in enumerate(random.sample(candidatos, min(faltan, len(candidatos)))):
            etiqueta = _ETIQUETAS_TENDENCIA_RESPALDO[i % len(_ETIQUETAS_TENDENCIA_RESPALDO)]
            etiqueta = etiqueta.format(categoria=producto.get("categoria", "esta categoría"))
            resultado.append((producto, etiqueta))

    return resultado


# --- Historial de la CONVERSACION de Koko, para nunca perderla -------------
# Archivo aparte de historial_usuarios.json a proposito: ese guarda datos
# ESTRUCTURADOS (busquedas/clics) para personalizar el consejo; este guarda
# el texto crudo de la charla, para poder recuperarla tal cual cuando el
# usuario recarga la pagina o vuelve a abrir el chat. Mismo patron (dict
# keyado por email en minuscula), mismo archivo gitignored (es dato real de
# uso, no mock).

def cargar_chats_koko():
    if not CHATS_KOKO_PATH.exists():
        return {}
    return load_json(CHATS_KOKO_PATH)


def guardar_chats_koko(chats):
    CHATS_KOKO_PATH.write_text(json.dumps(chats, ensure_ascii=False, indent=2), encoding="utf-8")


def cargar_historial_chat(email):
    email = _normalizar_email(email)
    if not email:
        return []
    return cargar_chats_koko().get(email, [])


def guardar_mensaje_chat(email, rol, texto):
    """Agrega UN mensaje al final del historial guardado de este email. Se
    llama una vez por cada mensaje nuevo (nunca con la conversacion
    completa), porque el frontend siempre manda la conversacion entera en
    cada request -- guardar todo de nuevo cada vez duplicaria los mensajes
    viejos."""
    email = _normalizar_email(email)
    if not email or not texto:
        return
    chats = cargar_chats_koko()
    chats.setdefault(email, []).append({"rol": rol, "texto": texto})
    guardar_chats_koko(chats)


def reiniciar_chat_koko(email):
    """Borra el historial guardado de este email -- usado por el boton
    'Reiniciar conversacion' del chat (ver koko.js). Si el email no tiene
    historial (o no vino email), no hace nada -- no es un error."""
    email = _normalizar_email(email)
    if not email:
        return
    chats = cargar_chats_koko()
    if email in chats:
        del chats[email]
        guardar_chats_koko(chats)


# --- Limite diario de mensajes a Koko (2026-08-11) --------------------------
# Archivo APARTE de chats_koko.json a proposito: ese es el historial que se
# le muestra al usuario (y que "Reiniciar conversacion" borra); este es
# solo un registro interno de cuando mando cada mensaje, para el limite --
# si vivieran juntos, reiniciar la conversacion tambien reiniciaria el
# limite, y cualquiera podria saltarselo tocando ese boton.

def cargar_limite_koko():
    if not LIMITE_KOKO_PATH.exists():
        return {}
    return load_json(LIMITE_KOKO_PATH)


def guardar_limite_koko(datos):
    LIMITE_KOKO_PATH.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def registrar_mensaje_usuario_koko(email):
    """Guarda la fecha/hora de un mensaje del usuario a Koko, para el
    limite diario. De paso, poda las fechas de mas de 48h (con margen de
    sobra sobre las 24h que realmente importan) para que el archivo no
    crezca sin limite -- no hace falta guardar mas que eso."""
    email = _normalizar_email(email)
    if not email:
        return
    datos = cargar_limite_koko()
    hace_48h = datetime.now(timezone.utc) - timedelta(hours=48)
    fechas = datos.get(email, [])
    fechas = [f for f in fechas if (_parsear_fecha_iso(f) or hace_48h) >= hace_48h]
    fechas.append(datetime.now(timezone.utc).isoformat())
    datos[email] = fechas
    guardar_limite_koko(datos)


def mensajes_usuario_ultimas_24h(email):
    """Cuenta los mensajes que este email le mando a Koko en las ultimas
    24 horas -- ventana movil (se va "cayendo" mensaje por mensaje a
    medida que pasan las 24h desde que se mando cada uno, no se reinicia
    de golpe a medianoche). Sin email, no hay como llevar la cuenta -- 0
    (sin limite; el resto de la app tampoco personaliza nada sin email)."""
    email = _normalizar_email(email)
    if not email:
        return 0
    hace_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    muy_viejo = datetime.min.replace(tzinfo=timezone.utc)
    fechas = cargar_limite_koko().get(email, [])
    return sum(1 for f in fechas if (_parsear_fecha_iso(f) or muy_viejo) >= hace_24h)


# Frases gatillo que hacen que Koko cambie de tono neutro a chileno DESDE
# ESE MOMENTO (ver KOKO_SYSTEM_PROMPT_BASE mas abajo) -- mismo criterio,
# solo para poder mostrar en "Mi perfil" si el usuario ya lo pidio alguna
# vez, sin tener que llamar a la API de nuevo.
_DISPARADORES_TONO_CHILENO = [
    "hablame como chileno", "habla como chileno", "hablame en chileno",
    "usa modismos chilenos", "modo chileno",
]


def preferencia_idioma_koko(email):
    """Revisa el historial guardado de este email por si en algun momento
    pidio explicitamente que Koko le hable como chileno. Si nunca lo pidio,
    devuelve None -- el default sigue siendo neutro, y no hay ninguna
    "preferencia configurada" que mostrar en ese caso (ver /perfil)."""
    historial = cargar_historial_chat(email)
    texto = _quitar_tildes(
        " ".join(m.get("texto", "") for m in historial if m.get("rol") == "usuario").lower()
    )
    if any(disparador in texto for disparador in _DISPARADORES_TONO_CHILENO):
        return "chileno"
    return None


# --- Tiendas reales y su tracking (2026-08-10) -------------------------------
# Sistema aparte del catalogo mock: tiendas reales con las que hay convenio.
# Cada tienda es "con_sitio_web" (link automatico con codigo de descuento,
# clics medibles) o "sin_sitio_web" (solo Instagram/WhatsApp, no hay como
# automatizar -- el registro depende de lo que la tienda reporte a mano).
# Decision del usuario (2026-08-10): no es definitivo, la estrategia puede
# cambiar -- mantener esto simple, sin sobre-construir.

def cargar_tiendas():
    if not TIENDAS_PATH.exists():
        return {}
    return load_json(TIENDAS_PATH)


def guardar_tiendas(tiendas):
    TIENDAS_PATH.write_text(json.dumps(tiendas, ensure_ascii=False, indent=2), encoding="utf-8")


# Las 16 regiones de Chile (nombres cortos, como se usan en el habla
# cotidiana) -- lista fija para el <select> del panel de admin y para
# reconocer el alias "Santiago"/"RM" de Metropolitana en _estimar_envio_real().
REGIONES_CHILE = [
    "Arica y Parinacota", "Tarapacá", "Antofagasta", "Atacama", "Coquimbo",
    "Valparaíso", "Metropolitana", "O'Higgins", "Maule", "Ñuble", "Biobío",
    "La Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes",
]


def _parsear_comuna_region(comuna_texto, region_texto):
    """Valida la comuna/region de una tienda, cargadas a mano en el panel
    de admin -- la comuna es texto libre (hay ~345, no vale la pena una
    lista fija), la region debe ser una de REGIONES_CHILE o queda vacia
    (nunca guarda un valor inventado)."""
    comuna = _texto_seguro(comuna_texto, 60)
    region = _texto_seguro(region_texto, 40)
    if region not in REGIONES_CHILE:
        region = ""
    return comuna, region


def cargar_envios_tiendas():
    """Politica de envio real por tienda (RM / regiones / retiro en tienda),
    investigada a mano entrando al sitio de cada una -- ver
    docs/tiendas_admin.md para el detalle y la fecha de revision. Clave =
    nombre de la tienda, igual a como se guarda en data/tiendas.json."""
    if not ENVIOS_TIENDAS_PATH.exists():
        return {}
    datos = load_json(ENVIOS_TIENDAS_PATH)
    datos.pop("_meta", None)
    return datos


ALIAS_METROPOLITANA = ("santiago", "region metropolitana", " rm", "rm ")


def _dias_habiles_a_numero(texto):
    """Saca un numero aproximado de un texto tipo '2 a 6 dias habiles' para
    poder ordenar tiendas de mas rapida a mas lenta. Casos especiales
    ANTES de buscar un digito: algunos textos describen el caso rapido con
    palabras ("mismo dia", "dia habil siguiente") y recien despues
    mencionan un numero mas grande para un caso secundario (ej. Roots
    South: "mismo dia... ; resto de la RM cada 48 horas") -- buscar el
    primer digito a ciegas ahi agarraria el "48" y mandaria a esa tienda
    al final por error, cuando en realidad es la mas rapida. Si el texto
    no trae ningun numero ni esas frases (ej. "no especificado"), devuelve
    99 para que esa tienda quede al final del orden en vez de arriba por
    casualidad."""
    texto_norm = _quitar_tildes((texto or "").lower())
    if "mismo dia" in texto_norm:
        return 0
    if "dia siguiente" in texto_norm or "dia habil siguiente" in texto_norm:
        return 1
    match = re.search(r"\d+", texto_norm)
    return int(match.group()) if match else 99


def _estimar_envio_real(direccion_usuario, nombre_tienda):
    """Tiempo de despacho REAL (no una aproximacion por comuna) -- usa los
    datos investigados a mano en data/envios_tiendas.json (ver
    cargar_envios_tiendas). Decide si la direccion que escribio el usuario
    esta en la Region Metropolitana (alias comunes: "Santiago"/"RM"/"Region
    Metropolitana") o en otra region conocida (REGIONES_CHILE), y muestra
    el dato de esa tienda para ese caso. Si la tienda no tiene dato
    investigado, o la tienda no publica el plazo (dias_habiles ==
    "no especificado"), se muestra honestamente en vez de inventar un
    numero -- misma filosofia que _estimar_envio() antes de esto."""
    info = cargar_envios_tiendas().get(nombre_tienda)
    if not info:
        return {"texto": "Sin dato de envío investigado", "dias": 99, "tiene_dato": False}

    direccion_norm = _quitar_tildes((direccion_usuario or "").lower())
    en_rm = any(a in direccion_norm for a in ALIAS_METROPOLITANA)
    if not en_rm:
        # Si escribio el nombre de otra region conocida, tambien cuenta
        # como "no es RM" aunque no haya matcheado los alias de arriba.
        en_rm = False

    if en_rm:
        etiqueta, segmento = "RM", info.get("envio_rm", {})
    else:
        etiqueta, segmento = "Regiones", info.get("envio_regiones", {})

    dias_texto = (segmento or {}).get("dias_habiles", "no especificado")
    if not segmento or not segmento.get("disponible") or dias_texto.startswith("no especificado"):
        return {"texto": f"{etiqueta}: sin plazo publicado por la tienda", "dias": 99, "tiene_dato": False}

    return {
        "texto": f"{etiqueta}: {dias_texto}",
        "dias": _dias_habiles_a_numero(dias_texto),
        "tiene_dato": True,
    }


def cargar_clics_tiendas():
    if not CLICS_TIENDAS_PATH.exists():
        return []
    return load_json(CLICS_TIENDAS_PATH)


def registrar_clic_tienda(tienda_id, producto):
    clics = cargar_clics_tiendas()
    clics.append({
        "tienda": tienda_id,
        "producto": producto,
        "fecha": datetime.now(timezone.utc).isoformat(),
    })
    CLICS_TIENDAS_PATH.write_text(json.dumps(clics, ensure_ascii=False, indent=2), encoding="utf-8")


def cargar_reportes_manuales():
    if not REPORTES_MANUALES_PATH.exists():
        return []
    return load_json(REPORTES_MANUALES_PATH)


def registrar_reporte_manual(tienda_id, fecha, monto):
    reportes = cargar_reportes_manuales()
    reportes.append({
        "tienda": tienda_id,
        "fecha": fecha,
        "monto": monto,
        "fecha_registro": datetime.now(timezone.utc).isoformat(),
    })
    REPORTES_MANUALES_PATH.write_text(json.dumps(reportes, ensure_ascii=False, indent=2), encoding="utf-8")


def resumen_historial_para_prompt(email):
    """Arma un resumen en texto plano del historial del usuario para meter
    en el prompt de Koko. Devuelve None si todavia no hay nada guardado
    (usuario nuevo -- Koko debe dar consejo general, no inventar gustos)."""
    email = _normalizar_email(email)
    if not email:
        return None
    entrada = cargar_historial().get(email)
    if not entrada or not (entrada.get("busquedas") or entrada.get("productos_interes")):
        return None

    lineas = []
    busquedas = entrada.get("busquedas", [])
    cortes = [b["corte"] for b in busquedas if b.get("corte")]
    tipos = [b["tipo_prenda"] for b in busquedas if b.get("tipo_prenda")]
    ocasiones = [b["ocasion"] for b in busquedas if b.get("ocasion")]
    if cortes:
        lineas.append(f"Cortes que ha buscado antes: {', '.join(cortes[-5:])}.")
    if tipos:
        lineas.append(f"Tipos de prenda que ha buscado antes: {', '.join(tipos[-5:])}.")
    if ocasiones:
        lineas.append(f"Ocasiones para las que ha buscado antes: {', '.join(ocasiones[-5:])}.")

    nombres_interes = [p["nombre"] for p in entrada.get("productos_interes", [])[-5:] if p.get("nombre")]
    if nombres_interes:
        lineas.append(f"Productos en los que hizo clic para ver mas: {', '.join(nombres_interes)}.")

    return " ".join(lineas) if lineas else None


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


# Material del producto (2026-08-19, filtro "Priorizar materiales de
# calidad" del buscador). El catalogo REAL todavia no tiene este dato --
# sera algo que se le pida a cada tienda mas adelante (nunca se inventa
# para un producto real); el catalogo MOCK lo trae variado a proposito
# (ver agregar_materiales.py), para poder probar el filtro con casos de
# sobra en ambos grupos. "natural" es lo unico que importa para priorizar
# -- cuero/lana/algodon 100% van primero, el resto (sinteticos y mezclas)
# no se oculta, solo queda despues.
MATERIALES_CONOCIDOS = {
    "algodon_100": {"etiqueta": "Algodón 100%", "natural": True},
    "lana": {"etiqueta": "Lana", "natural": True},
    "cuero": {"etiqueta": "Cuero", "natural": True},
    "mezcla_algodon_poliester": {"etiqueta": "Mezcla algodón/poliéster", "natural": False},
    "poliester": {"etiqueta": "Poliéster", "natural": False},
    "nylon": {"etiqueta": "Nylon", "natural": False},
    "acrilico": {"etiqueta": "Acrílico", "natural": False},
}


def _material_es_natural(producto):
    info = MATERIALES_CONOCIDOS.get(producto.get("material", ""))
    return bool(info and info["natural"])


# Gramaje (GSM) del algodon (2026-08-19, refina "Priorizar materiales de
# calidad"). Solo tiene sentido en polera/camiseta -- para otras prendas
# (chaqueta, pantalon, etc.) un umbral de "buena calidad" en GSM no esta
# definido, asi que a proposito NO se extrapola. El catalogo REAL no trae
# este dato todavia (mismo criterio que "material": se cargara tienda por
# tienda, nunca inventado); el catalogo MOCK lo trae variado a proposito en
# poleras/camisetas de algodon 100% (ver agregar_gramaje.py).
GRAMAJE_MINIMO_CALIDAD_GSM = 180
CATEGORIAS_CON_GRAMAJE = {"polera", "camiseta"}


def _algodon_buena_calidad(producto):
    """'Buena calidad' definida por el usuario: polera o camiseta de
    algodon 100% con gramaje >= GRAMAJE_MINIMO_CALIDAD_GSM. Sin el dato
    cargado, o fuera de esas 2 categorias, nunca se considera "buena
    calidad" (no se inventa un umbral para lo que no esta definido)."""
    if producto.get("categoria") not in CATEGORIAS_CON_GRAMAJE:
        return False
    if producto.get("material") != "algodon_100":
        return False
    gsm = producto.get("gramaje_gsm")
    return isinstance(gsm, (int, float)) and gsm >= GRAMAJE_MINIMO_CALIDAD_GSM


def _texto_gramaje(producto):
    """Texto para la ficha del producto (ej: "220 GSM -- algodón grueso de
    calidad"). Vacio si no hay gramaje cargado (la mayoria del catalogo,
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


# Agrupa las categorias del catalogo en los 2 grupos que se preguntan en el
# formulario ("prenda superior" / "prenda inferior"). Si el usuario elige
# uno de estos, la busqueda descarta primero cualquier producto que no sea
# de ese grupo.
CATEGORIA_GRUPOS = {
    "prenda superior": ["poleron", "camisa", "chaqueta", "polera", "chaleco", "camiseta", "top"],
    "prenda inferior": ["pantalon", "falda", "shorts", "faldacargo", "bikeshorts"],
}

# Reverso de CATEGORIA_GRUPOS (tipo de prenda -> grupo), mas "gorro" (que no
# esta en CATEGORIA_GRUPOS porque no se pregunta como grupo en el
# formulario, pero si es una categoria valida de la tool de Koko). Se usa
# para corregir la categoria que Koko haya sugerido, a partir del tipo de
# prenda detectado -- ver koko_chat().
TIPO_PRENDA_A_CATEGORIA_GRUPO = {
    tipo: grupo for grupo, tipos in CATEGORIA_GRUPOS.items() for tipo in tipos
}
TIPO_PRENDA_A_CATEGORIA_GRUPO["gorro"] = "gorro"

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

# Hobbies del perfil (2026-08-18, reemplaza el campo de texto libre que
# tenia antes; ampliado 2026-08-19). Checkboxes en /perfil -- se puede
# elegir mas de uno. Si eligen "musica" o "deportes", se despliega un
# segundo grupo con sub-opciones concretas (GENEROS_MUSICALES_CONOCIDOS /
# DEPORTES_CONOCIDOS). Estas 3 listas son SOLO la taxonomia (que opciones
# existen, para el selector y para las etiquetas legibles) -- no traen
# ninguna asociacion de estilo. Las asociaciones hobby -> estilo viven
# aparte, en REGLAS_HOBBY, y se agregan de a una SOLO despues de que el
# dueño del proyecto las valide (ver mas abajo) -- decision 2026-08-19,
# antes hubo una version de esto con "vibra"/"corte_sugerido" inventados
# sin validar, se saco.
HOBBIES_CONOCIDOS = {
    "musica": {"etiqueta": "Música"},
    "deportes": {"etiqueta": "Deportes"},
    "relajo": {"etiqueta": "Relajo / lifestyle tranquilo"},
    "arte_cultura": {"etiqueta": "Arte y cultura"},
    "gaming": {"etiqueta": "Gaming"},
    "peliculas_series": {"etiqueta": "Películas y series"},
}

# Solo aplica si "musica" esta entre los hobbies elegidos.
GENEROS_MUSICALES_CONOCIDOS = {
    "rock": {"etiqueta": "Rock"},
    "reggaeton": {"etiqueta": "Reguetón / urbano"},
    "pop": {"etiqueta": "Pop"},
    "hip_hop": {"etiqueta": "Hip-hop / rap"},
    "electronica": {"etiqueta": "Electrónica"},
    "indie": {"etiqueta": "Indie / alternativo"},
}

# Solo aplica si "deportes" esta entre los hobbies elegidos (2026-08-19).
DEPORTES_CONOCIDOS = {
    "gym": {"etiqueta": "Gym"},
    "futbol": {"etiqueta": "Fútbol"},
    "baseball": {"etiqueta": "Baseball"},
    "ski": {"etiqueta": "Ski"},
}

# Exclusiones suaves por hobby (2026-08-20) -- ENFOQUE PRINCIPAL para
# cruzar hobby con estilo, reemplaza el enfoque anterior de "regla positiva
# que fuerza un corte" (REGLAS_HOBBY, mas abajo, ahora es solo una
# sugerencia opcional). Decision explicita del usuario: en vez de imponer
# UN estilo "correcto" por hobby, el hobby solo ayuda a descartar
# (deprioritizar, NUNCA ocultar) categorias que claramente no calzan -- la
# base de la recomendacion sigue siendo corte/ocasion/color de siempre.
#
# LIMITACION HONESTA: el catalogo (mock y, probablemente, el real tambien)
# no tiene categorias de "ropa tecnica deportiva" (mallas de compresion,
# running de alto rendimiento) ni de "ropa formal/de vestir" como tales --
# se usa la categoria real MAS PARECIDA como proxy:
# - "bikeshorts" ("ajustados, tipo ciclista") es lo mas cercano a
#   compresion/running que existe en TIPOS_PRENDA_CONOCIDOS.
# - "camisa" es la prenda mas formal-codificada del catalogo (la que se usa
#   para ocasiones semiformales en las conversaciones reales de Koko).
# Si el catalogo real llega a tener mas variedad de categorias, esto se
# puede afinar para dejar de depender de estos proxies.
#
# Formato: hobby (o (hobby, sub-opcion) para musica/deportes) -> set de
# tipo_prenda a deprioritizar. "gaming" no tiene entrada a proposito (pedido
# explicito del usuario: "sin exclusiones fuertes evidentes, se mantiene el
# catalogo general").
EXCLUSIONES_HOBBY = {
    ("arte_cultura", None): {"bikeshorts"},
    ("deportes", "gym"): {"camisa"},
}


def _categorias_deprioritizadas_por_hobby(hobbies, generos_musicales, deportes_subtipo=None):
    """Categorias que los hobbies de este usuario sugieren NO priorizar --
    ver EXCLUSIONES_HOBBY. Nunca oculta nada (a diferencia de un filtro
    estricto): solo se usa para reordenar en elegir_candidatos(), igual
    patron que priorizar_material_natural. Ignora cualquier hobby/
    sub-opcion sin exclusion definida (nunca inventa una)."""
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


# Reglas POSITIVAS de hobby -> estilo (2026-08-19, degradadas a sugerencia
# OPCIONAL 2026-08-20 -- decision explicita del usuario: el enfoque de
# exclusion de arriba es "mas confiable" que forzar un unico estilo
# "correcto" por hobby). Ya NO se usan para fijar un corte por defecto en
# /api/recommend (se saco esa logica) -- Koko puede seguir MENCIONANDOLAS
# como idea/sugerencia en la conversacion (ver _bloque_hobbies_para_prompt),
# pero nunca reemplazando lo que el usuario realmente pida ni saltandose
# preguntas por esto.
#
# Formato (2026-08-23: cada hobby ahora es una LISTA de sugerencias, no un
# unico dict -- un mismo hobby puede sugerir cosas distintas por tipo de
# prenda, ej. "Gym" sugiere un corte para pantalon y otro para poleron. Cada
# sugerencia individual trae:
# - "prenda_preferida": set de tipo_prenda a los que aplica ESTA sugerencia
#   puntual (nunca a otra prenda).
# - "corte"/"color_base"/"nota": ideas para que Koko converse con criterio
#   -- el catalogo mock no tiene color ni estampado cargado por prenda
#   (fuera de gorro/chaqueta), asi que nunca se usan para filtrar ni para
#   el orden de resultados.
# - "tipo_sugerencia": "corte" (default, se omite) o "accesorio" -- esta
#   ultima es para sugerencias que no tienen un corte real de por medio
#   (ej. "gorro como accesorio frecuente"), se renderiza distinto en
#   _bloque_hobbies_para_prompt (sin mencionar ningun corte inventado).
# - "confianza": "validacion_inicial" (referencias visuales, no encuesta a
#   muchas personas).
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
    # Deportes: Gym (2026-08-23) -- refuerzo POSITIVO pedido explicitamente
    # por el dueño del proyecto, para sumar a la exclusion suave que ya
    # existia (EXCLUSIONES_HOBBY -- deprioriza "camisa", eso NO cambia).
    # Esto es un plus conversacional nuevo, no reemplaza esa exclusion.
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
    # Proximos hobbies (futbol, gaming, etc.) se agregan aca con la misma
    # forma (lista de sugerencias) apenas el dueño del proyecto valide su
    # sugerencia -- ver propuesta pendiente de revision en CLAUDE.md /
    # conversacion.
}


def _reglas_hobby_usuario(hobbies, generos_musicales, deportes_subtipo=None):
    """Reglas de hobby YA VALIDADAS que aplican a este perfil -- sugerencias
    OPCIONALES para que Koko converse con criterio (ver
    _bloque_hobbies_para_prompt), ya NO se usan para cambiar el resultado
    de una busqueda por formulario (eso ahora lo hace
    _categorias_deprioritizadas_por_hobby, ver arriba). Ignora cualquier
    hobby/sub-opcion que todavia no tenga una regla validada en
    REGLAS_HOBBY (hoy, la inmensa mayoria) -- nunca inventa una asociacion
    que no este ahi."""
    hobbies_norm = [(h or "").strip().lower() for h in (hobbies or [])]
    reglas = []
    if "musica" in hobbies_norm:
        for genero in generos_musicales or []:
            reglas.extend(REGLAS_HOBBY.get(("musica", (genero or "").strip().lower()), []))
    if "deportes" in hobbies_norm:
        for deporte in deportes_subtipo or []:
            reglas.extend(REGLAS_HOBBY.get(("deportes", (deporte or "").strip().lower()), []))
    return reglas


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
    "gorro": ["gorro", "gorra", "jockey", "cap"],
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
    # Subtipos de chaqueta (2026-08-17). "denim" y "jeans" tambien
    # significan "mezclilla" en una chaqueta -- se resuelve sin choque con
    # el "jeans" de pantalon/shorts porque SUBTIPOS_POR_TIPO_PRENDA
    # restringe que canonicos son validos segun el tipo_prenda ya conocido
    # (ver detectar_subtipo_pedido()) antes de buscar coincidencias.
    "bomber": ["bomber"],
    "mezclilla": ["mezclilla", "denim", "jeans", "jean"],
    "cuero": ["cuero", "de cuero", "leather"],
}

# Restringe que subtipos son validos para cada tipo de prenda -- evita que
# una palabra compartida entre 2 tipos (ej. "jeans"/"denim", que aplica
# tanto a pantalon como a chaqueta) se cruce con el canonico equivocado.
# Sin esto, "chaqueta denim" podia devolver el subtipo "jeans" (pensado
# para pantalon), que ninguna chaqueta del catalogo tiene -- resultado
# vacio aunque si hubiera chaquetas de mezclilla. Los tipos que no
# aparecen aca (polera, poleron, camisa, camiseta, gorro, etc.) no tienen
# subtipo -- el filtro de subtipo directamente no se aplica para ellos
# (ver elegir_candidatos).
SUBTIPOS_POR_TIPO_PRENDA = {
    "pantalon": {"buzo", "jeans", "cargo"},
    "shorts": {"jeans", "tela", "cargo", "bano"},
    "top": {"croptop", "babytee", "halter", "corset", "tanktop", "blusa"},
    "chaqueta": {"bomber", "mezclilla", "cuero"},
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

# Gorro: no tiene corte (slim/oversize no aplica) -- en cambio tiene su
# propio flujo de color y forma. El color viene de dos caminos posibles:
# 1) colores especificos elegidos a mano (checkboxes), o 2) que combine con
# el outfit (se traduce a un set de colores permitidos segun esta tabla).
# "vivos" son los colores fuertes/de acento; blanco/negro/beige quedan
# fuera de ese grupo (son los neutros).
COLORES_GORRO_CONOCIDOS = ["blanco", "negro", "rojo", "azul", "amarillo", "beige", "morado", "verde"]
COLORES_VIVOS_GORRO = {"rojo", "azul", "amarillo", "morado", "verde"}
FORMAS_GORRO_CONOCIDAS = ["curvo", "plano", "lana"]

# Variantes de texto para detectar la forma de gorro que alguien pide en
# lenguaje natural (ej. a Koko) -- mismo patron que CORTES_CONOCIDOS/etc,
# para poder usar _detectar().
FORMA_GORRO_CONOCIDA = {
    "curvo": ["gorro curvo", "curvo"],
    "plano": ["gorro plano", "plano", "snapback"],
    "lana": ["gorro de lana", "gorro lana", "de lana", "lana", "beanie", "gorro tejido"],
}


def colores_permitidos_por_outfit(outfit):
    """Devuelve el set de color_dominante que tiene sentido para un gorro
    segun como es el outfit de la persona."""
    outfit = (outfit or "").strip().lower()
    if outfit == "oscuro":
        # Color fuerte como acento, o blanco para contraste limpio.
        return COLORES_VIVOS_GORRO | {"blanco"}
    if outfit == "claro":
        # Negro para contraste, o color vivo como protagonista.
        return COLORES_VIVOS_GORRO | {"negro"}
    if outfit == "colorido":
        # Un solo color neutro para no sobrecargar el look.
        return {"negro", "blanco"}
    # "otro" (o cualquier valor no reconocido): no filtramos por color.
    return set(COLORES_GORRO_CONOCIDOS)


def filtrar_gorros_por_color(catalog, camino, colores_elegidos, outfit):
    """Filtro estricto de color_dominante para gorros -- nunca se relaja.
    Solo afecta productos categoria "gorro"; el resto del catalogo pasa
    sin tocar. "camino" es "colores" (usa colores_elegidos tal cual) o
    "outfit" (usa colores_permitidos_por_outfit)."""
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
    """Filtro estricto de forma (curvo/plano) para gorros -- nunca se
    relaja. Solo afecta productos categoria "gorro"."""
    forma = (forma or "").strip().lower()
    if forma not in FORMAS_GORRO_CONOCIDAS:
        return catalog
    return [
        p for p in catalog
        if p.get("categoria", "").lower() != "gorro" or p.get("forma", "").lower() == forma
    ]


def _quitar_tildes(texto):
    """Normaliza tildes/acentos (ej: 'pantalón' -> 'pantalon') para que
    detectar un tipo de prenda/corte no dependa de si la persona escribio
    el acento o no -- ni las variantes en TIPOS_PRENDA_CONOCIDOS/etc (sin
    tilde) ni lo que escribe un usuario real (con tilde) deberian fallar
    por esto."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _contiene_palabra(texto, variante):
    """Busca 'variante' como palabra (o frase) completa dentro de 'texto',
    nunca como fragmento de otra palabra -- ej: la palabra "la" no debe
    calzar solo porque el texto contiene "blancas". Acepta ademas el plural
    en español agregando "s" o "es" al final (ej: "polera" tambien calza
    con "poleras", "pantalon" con "pantalones") -- si no, alguien que
    escribe en plural (lo mas natural) no calzaba con nada."""
    return re.search(rf"\b{re.escape(variante)}(?:es|s)?\b", texto) is not None


def tokenizar(texto):
    """Separa un texto en las palabras que realmente lo componen (sin
    tildes/comas/slashes pegados), para poder comparar palabra por palabra
    en vez de buscar un fragmento de texto dentro de otro."""
    return set(re.findall(r"[a-záéíóúñ0-9]+", texto.lower()))


def _detectar(texto_pedido, conocidos):
    """Escanea texto_pedido buscando alguna de las frases de 'conocidos'
    (dict: nombre canonico -> lista de variantes). Devuelve el nombre
    canonico de la primera que calce, o None si no se menciono ninguna."""
    texto = _quitar_tildes(texto_pedido.lower())
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


def _detectar_reciente(mensajes, conocidos):
    """Igual que _detectar(), pero para una conversacion completa (lista de
    mensajes, del mas antiguo al mas reciente): revisa los mensajes desde
    el ULTIMO hacia el primero y devuelve la coincidencia del mensaje mas
    reciente que mencione algo conocido.

    BUG encontrado en produccion (2026-08-10, conversacion real de un
    usuario): antes se armaba un solo texto gigante con toda la
    conversacion (" ".join(...)) y se buscaba ahi -- pero _detectar()
    devuelve la PRIMERA coincidencia segun el ORDEN del diccionario
    "conocidos" (ej. TIPOS_PRENDA_CONOCIDOS tiene "polera" antes que
    "poleron"), no la mas relevante. En una conversacion larga que toco
    varios tipos de prenda (ej. Koko sugirio combos con "polera oversize"
    Y despues el usuario penso en "poleron oversize" para un regalo), esto
    hacia que "polera" le ganara a "poleron" SIEMPRE que las dos palabras
    aparecieran en algun punto de la charla, sin importar cual era el tema
    actual -- y esa sugerencia equivocada (buscar "polera baggy" en vez de
    "poleron oversize") no traia ningun resultado, mostrando "no encontre
    nada" aunque el catalogo si tuviera poleron oversize. Escanear mensaje
    por mensaje, del mas nuevo al mas viejo, resuelve esto Y sigue
    sirviendo para el caso original (Koko nombra la prenda en su propia
    sugerencia y el usuario solo confirma sin repetirla) -- ese nombre
    sigue estando en uno de los ultimos mensajes."""
    for mensaje in reversed(mensajes):
        texto = _quitar_tildes((mensaje or "").lower())
        for canonico, variantes in conocidos.items():
            if any(_contiene_palabra(texto, variante) for variante in variantes):
                return canonico
    return None


def _mencionado_en_conversacion(canonico, conocidos, mensajes):
    """Revisa si el termino canonico (ej. 'chaqueta') aparece mencionado en
    CUALQUIER mensaje de la conversacion (no solo el mas reciente) -- lo usa
    _valor_o_deteccion() para confirmar que un valor que Koko ya eligio
    realmente se dijo en algun momento, antes de confiar en el."""
    variantes = conocidos.get(canonico)
    if not variantes:
        return False
    return any(
        any(_contiene_palabra(_quitar_tildes((m or "").lower()), v) for v in variantes)
        for m in mensajes
    )


def _valor_o_deteccion(valor_propuesto, conocidos, mensajes, detector_conversacion, mensajes_confirmacion=None):
    """Si Koko ya propuso un valor valido (existe en 'conocidos') Y esa
    palabra realmente aparece en algun mensaje de la conversacion, se confia
    en la lectura de Koko -- tiene mas contexto real que un regex (ej. sabe
    distinguir "combina con tu camisa" de "quiero una chaqueta" DENTRO del
    mismo mensaje, algo que _detectar_reciente no puede: revisa mensaje por
    mensaje, pero si un mismo mensaje nombra 2 prendas, siempre devuelve la
    que aparece primero en el diccionario "conocidos", no la que es
    realmente el tema -- BUG real encontrado 2026-08-17 con una conversacion
    de verdad ("...cerremos el look con la chaqueta! Para que combine con la
    camisa azul marino..." -- ese mensaje menciona ambas, y como "camisa"
    esta antes que "chaqueta" en TIPOS_PRENDA_CONOCIDOS, la correccion le
    devolvia SIEMPRE "camisa" al usuario, aunque el tema real fuera la
    chaqueta y Koko ya lo hubiera entendido bien). Si Koko no propuso nada
    valido, o propuso algo que nunca se menciono en la conversacion
    (probable invento del modelo), recien ahi se usa la deteccion
    determinista de siempre como red de seguridad.

    mensajes_confirmacion (opcional, 2026-08-25): con que mensajes se
    confirma que la propuesta de Koko "se dijo en algun momento" -- por
    defecto usa el mismo 'mensajes' (todo el historial), como siempre. Se
    puede pasar una ventana mas chica (solo los ultimos mensajes) para el
    caso donde "se menciono en algun momento de TODA la conversacion" es
    demasiado permisivo -- ver BUG "poleron + pantalon de buzo" (2026-08-25,
    koko_chat()) mas abajo, donde Koko podia terminar confirmando una
    prenda que ya no era el tema, solo porque se habia nombrado muchos
    mensajes atras."""
    propuesto = (valor_propuesto or "").lower()
    ventana = mensajes if mensajes_confirmacion is None else mensajes_confirmacion
    if propuesto in conocidos and _mencionado_en_conversacion(propuesto, conocidos, ventana):
        return propuesto
    return detector_conversacion(mensajes)


def detectar_corte_pedido_conversacion(mensajes):
    return _detectar_reciente(mensajes, CORTES_CONOCIDOS)


def detectar_tipo_prenda_conversacion(mensajes):
    return _detectar_reciente(mensajes, TIPOS_PRENDA_CONOCIDOS)


def detectar_forma_gorro_conversacion(mensajes):
    return _detectar_reciente(mensajes, FORMA_GORRO_CONOCIDA)


def detectar_forma_gorro(texto_pedido):
    """Revisa si el pedido menciona una forma de gorro especifica (curvo,
    plano, o de lana/beanie)."""
    return _detectar(texto_pedido, FORMA_GORRO_CONOCIDA)


def detectar_largo_pedido(texto_pedido):
    """Revisa si el pedido menciona un largo especifico (ej: "crop",
    "extra largo")."""
    return _detectar(texto_pedido, LARGOS_CONOCIDOS)


def _subtipos_validos_para(tipo_prenda):
    """Subconjunto de SUBTIPOS_CONOCIDOS valido para ese tipo de prenda --
    ver SUBTIPOS_POR_TIPO_PRENDA. Si el tipo no tiene subtipos (o no se
    especifico), devuelve el dict completo tal cual (comportamiento previo,
    sigue sirviendo si algun dia se llama sin tipo_prenda)."""
    if tipo_prenda and tipo_prenda in SUBTIPOS_POR_TIPO_PRENDA:
        permitidos = SUBTIPOS_POR_TIPO_PRENDA[tipo_prenda]
        return {k: v for k, v in SUBTIPOS_CONOCIDOS.items() if k in permitidos}
    return SUBTIPOS_CONOCIDOS


def detectar_subtipo_pedido(texto_pedido, tipo_prenda=None):
    """Revisa si el pedido menciona un subtipo especifico (ej: "cargo",
    "jeans", "corset", "bomber"). Restringido a los subtipos validos de
    tipo_prenda cuando se conoce (ver _subtipos_validos_para) -- evita que
    una palabra compartida entre 2 tipos (ej. "jeans"/"denim") se cruce con
    el tipo de prenda equivocado."""
    return _detectar(texto_pedido, _subtipos_validos_para(tipo_prenda))


def detectar_subtipo_pedido_conversacion(mensajes, tipo_prenda=None):
    return _detectar_reciente(mensajes, _subtipos_validos_para(tipo_prenda))


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
    (ej: no hay dato de peso), no filtra nada. Los gorros quedan exentos --
    son talla unica/ajustable, no usan S/M/L/XL."""
    if not tallas_usuario:
        return catalog
    return [
        p for p in catalog
        if p.get("categoria", "").lower() == "gorro"
        or any(t in p.get("tallas_disponibles", []) for t in tallas_usuario)
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
    genero, texto_pedido, catalog, cantidad, categoria_pedida=None, permitir_otros_cortes=False,
    priorizar_material_natural=False, categorias_deprioritizadas=None,
):
    """Filtra por genero (o unisex); despues por tipo de prenda (prioridad 1)
    y por corte (prioridad 2); al final ordena por cuantas palabras del
    pedido aparecen en cada producto.

    priorizar_material_natural (2026-08-19, filtro "Priorizar materiales de
    calidad"): NUNCA oculta nada -- solo hace que los productos de fibra
    natural (ver MATERIALES_CONOCIDOS) queden primero en el orden final,
    antes de desempatar por palabras en comun. Un producto sin material
    cargado (la mayoria del catalogo real, hasta que cada tienda lo mande)
    simplemente no se prioriza -- no se asume que sea sintetico ni natural.

    categorias_deprioritizadas (2026-08-20, exclusion suave por hobby --
    ver EXCLUSIONES_HOBBY): set de tipo_prenda que quedan al FINAL del
    orden, nunca ocultos. Independiente de priorizar_material_natural (los
    2 se pueden combinar); es el nivel de mas prioridad en el desempate,
    porque "no calza con tu hobby" es un descarte de sentido comun mas
    fuerte que preferir un material -- pero sigue siendo solo orden, jamas
    un filtro.

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

    # El subtipo solo aplica a pantalon/shorts/top/chaqueta -- si no, palabras
    # sueltas de otras reglas (ej: "tela transpirable" en la regla de
    # poleras) podrian calzar por error con una palabra clave de subtipo
    # (ej: "tela").
    if tipo_prenda in SUBTIPOS_POR_TIPO_PRENDA:
        subtipo_pedido = detectar_subtipo_pedido(texto_pedido, tipo_prenda)
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
        puntaje_palabras = len(palabras_pedido & tokenizar(texto_producto(producto)))
        # Nivel de hobby SIEMPRE va primero en el desempate (mas fuerte que
        # material): "no calza con tu hobby" es un descarte de sentido
        # comun, no una preferencia de gusto. Si no hay exclusiones (el
        # caso mas comun -- la mayoria de hobbies no tiene ninguna, o el
        # usuario no cargo hobbies), todos quedan en nivel 1 y no cambia
        # nada respecto de antes.
        categoria_producto = (producto.get("categoria") or "").lower()
        nivel_hobby = 0 if categoria_producto in (categorias_deprioritizadas or ()) else 1
        if priorizar_material_natural:
            # Niveles: hobby, despues natural antes que sintetico, despues
            # algodon de buen gramaje (>=180 GSM, solo polera/camiseta)
            # antes que el resto; recien ahi desempata por palabras en
            # comun. Nunca oculta nada, solo reordena.
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
    """Busqueda primaria: solo usa reglas sin_consenso o de confianza alta.
    Las reglas de confianza media se reservan para el Plan B."""
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
    """Cuando "mostrar mas opciones" ya no tiene mas productos que cumplan
    TODOS los filtros (incluido el corte pedido), completa los cupos que
    faltan relajando SOLO el corte -- mantiene tipo de prenda, subtipo,
    largo, manga, capucha/cierre y ocasion/precio (esos nunca se relajan).
    Devuelve (alternativas_formateadas, aviso_o_None); si no se pidio un
    corte especifico, o igual no aparece nada relajando el corte, devuelve
    ([], None) y el llamador no debe mostrar ningun aviso de alternativa."""
    corte_pedido = detectar_corte_pedido(texto_pedido)
    if faltan <= 0 or not corte_pedido:
        return [], None

    # Hay que sacar los ya mostrados del catalogo ANTES de llamar a
    # elegir_candidatos, no despues -- si no, permitir_otros_cortes nunca se
    # activa: elegir_candidatos ve que "todavia existen" productos del corte
    # pedido (los que ya se mostraron) y por eso no relaja nada, aunque para
    # el usuario ya no quede ninguno nuevo que mostrar.
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
    """Se llama cuando el usuario dice que la busqueda primaria no le sirvio.
    Usa la regla de confianza media si existe; si no, amplia el buscador
    simple mostrando los siguientes mejores candidatos del catalogo.

    Prioridad al ampliar: primero se completa con mas productos que sigan
    cumpliendo TODOS los filtros (tipo de prenda, subtipo, largo, manga,
    capucha/cierre, ocasion, precio); si con eso no alcanza a completar
    CANTIDAD_RESULTADOS, se rellena el resto relajando SOLO el corte
    (ej: pidieron "baggy" y ya no queda ninguno mas -> se ofrecen otros
    cortes de la misma prenda), dejando eso marcado aparte como alternativa,
    nunca mezclado silenciosamente con los resultados exactos.

    Devuelve (exactos, alternativas, aviso_alternativas) -- "aviso_alternativas"
    es None si no hubo que relajar nada."""
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

    # Para no repetir lo que ya se mostro en la busqueda primaria, primero
    # calculamos esos mismos resultados (busqueda estricta) y los excluimos
    # de la lista ampliada. Asi, si la primaria no mostro nada (ej: no habia
    # nada "boxy fit"), el Plan B parte mostrando desde el primer resultado
    # en vez de saltarse resultados que nunca se mostraron.
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


# --- Koko: asistente de estilo con chat (API de Anthropic) ------------------
# Ver seccion "Koko" en CLAUDE.md. Koko da consejo en conversacion libre y,
# cuando ya tiene claro que ofrecer, llama la tool "sugerir_busqueda" en vez
# de que el backend tenga que parsear texto libre para saber que buscar.

KOKO_SYSTEM_PROMPT_BASE = """Eres Koko, la mascota-perrito asistente de estilo de KOLIZION, una app que \
recomienda streetwear de tiendas chicas segun altura, peso, ocasion y presupuesto.

Tono: por defecto, espanol neutro/estandar -- cercano, entusiasta y calido, pero SIN modismos regionales. \
Habla de tu (nunca "usted"), nunca como un asistente corporativo o formal. Por defecto NO uses \
expresiones chilenas como "al tiro", "bacan", "la firme", "cuatico", "fome", "carrete", "poh", "cachai", \
"weon"/"weá", "po", ni ninguna similar -- ni siquiera una, aunque el tema sea streetwear/calle. SOLO si \
en algun momento de la conversacion la persona te pide explicitamente hablar como chileno (ej: "hablame \
como chileno", "usa modismos chilenos", "hablame en chileno"), recien ahi cambia desde ESE momento en \
adelante a un tono chileno joven/universitario con esas mismas expresiones, usadas con naturalidad y sin \
amontonarlas -- y mantenlo asi por el resto de esta conversacion, sin volver al neutro salvo que te lo \
pidan.

Das consejo de estilo en conversacion libre -- vos NO buscas productos directamente, para eso esta el \
buscador de la app (via la tool sugerir_busqueda).

Reglas de recomendacion streetwear ya validadas (usalas como base de tu consejo, no las repitas literal \
ni las nombres como "reglas"):
{reglas}

{perfil}

{historial}

{favoritos}

{hobbies}

Usa los datos de perfil y los favoritos de arriba para personalizar tu consejo -- ej: si ya sabes su \
talla estimada, no vuelvas a preguntarla; si tiene favoritos guardados, podes mencionarlos con \
naturalidad cuando venga al caso (ej: "veo que ya tienes un par de poleras guardadas, ¿buscamos algo \
distinto o mas de lo mismo?"). Nunca los recites como una lista literal salvo que te lo pidan \
explicitamente, y nunca inventes un dato de perfil o un favorito que no este en esos bloques.

Cuando el usuario nombra una prenda concreta (polera, poleron, camisa, chaqueta, chaleco, camiseta, top, \
pantalon, short, falda, o gorro), interpreta esa frase usando los MISMOS criterios de tipo de prenda y \
corte que usa el buscador normal de la app (los mismos valores que recibe sugerir_busqueda). Nunca llames \
la tool con una prenda, corte o presupuesto que no calce con lo que la persona realmente dijo.

- PRIMERO revisa esto, antes que la regla de abajo: si en su mensaje ya te dio el corte/ajuste (ej: \
  "baggy", "oversize", "ajustada", "slim", "que no quede pegado"), eso YA es suficiente por si solo -- \
  llama la tool en esa misma respuesta, con un mensaje corto confirmando lo que entendiste. NO le \
  preguntes color, presupuesto, ni para que ocasion/uso -- esos son solo un plus cuando falta el corte, \
  nunca un requisito si el corte ya esta. Ejemplo: "necesito pantalones baggy" -> ya tenes tipo_prenda \
  (pantalon) y corte (baggy) -> buscas directo, sin preguntar nada mas, aunque no sepas el color ni el \
  presupuesto.
- Si nombro la prenda pero NO te dio el corte/ajuste, y el pedido trae \
  contexto (ej: una ocasion, "para el matrimonio de mi hermano"), actua como un \
  vendedor de tienda con buen ojo, no como un formulario: haz 2-3 preguntas CONCRETAS y especificas a \
  ESA prenda, en tono natural y en la misma respuesta -- nunca un generico "cuentame mas" o "que mas \
  buscas". Adapta las preguntas al tipo de prenda, por ejemplo:
  * Camisa: tono/color que prefiere, si la busca ajustada o mas suelta, presupuesto aproximado.
  * Pantalon: que corte (baggy, cargo, slim, recto), y si busca un tipo concreto (jeans, cargo, buzo -- \
    pasalo en el campo subtipo de la tool), si es para el dia a dia o para algo puntual.
  * Poleron o polera: ajustada u oversize, con o sin capucha (poleron), presupuesto aproximado.
  * Chaqueta: mas ajustada o mas suelta, y si tiene un estilo/material en mente (bomber, de mezclilla/\
    denim, de cuero -- pasalo en el campo subtipo de la tool), presupuesto aproximado.
  * Chaleco: mas ajustada o mas suelta, para que ocasion, presupuesto aproximado.
  Para otras prendas usa el mismo criterio: 2-3 preguntas que un vendedor de verdad haria para esa \
  prenda puntual, no una lista generica igual para todo. Si hay una sugerencia de hobby validada (ver el \
  bloque de reglas de hobby mas arriba en este prompt) que aplique a esta prenda, podes MENCIONARLA como \
  idea dentro de tus preguntas (ej: "ya que te gusta el rock, muchos buscan algo oversize con grafico \
  grande -- ¿te tinca eso o preferis otra onda?"), pero es solo una idea, nunca dejes de preguntar por el \
  corte real ni des la sugerencia por hecha.
- No hace falta esperar las 3 respuestas: apenas el usuario te de el corte/ajuste MAS otro dato util \
  (color, presupuesto, o el contexto de uso), llama la tool en esa misma respuesta -- no sigas \
  preguntando por el resto. Y si en su PRIMER mensaje ya trae 2 o mas de esos datos (ej: "camisa blanca \
  ajustada para un matrimonio, unos 25 lucas"), no preguntes nada: interpretalo directo y busca.
- Nunca preguntes la ocasion como pregunta aislada si el usuario ya la nombro -- usala para elegir que \
  preguntar (ej: si es un matrimonio, no hace falta preguntar si es formal o casual, ya se sabe que es \
  una ocasion especial) y para dar mejor consejo, no para armar otra pregunta mas.
- Si el corte/ajuste que te den no calza exacto con un valor conocido (baggy, boxy fit, slim fit, \
  oversize, skinny, regular fit, straight), interpretalo al mas parecido -- nunca le pidas que elija de \
  una lista tecnica, hablale como persona.
- Si mencionan un presupuesto, pasalo en presupuesto_max de la tool (numero entero en CLP). El catalogo \
  SI filtra de verdad por precio maximo -- pero NO tiene datos de color cargados por prenda (fuera de \
  gorros), asi que si te dijeron un color, usalo para conversar y para comentar los resultados, pero \
  nunca prometas que la busqueda filtro por ese color -- se honesto si esa info no esta en el catalogo.

Si eligen "gorro", tambien pueden pedir una forma concreta (gorro curvo, gorro plano, o gorro de \
lana/beanie) -- si la mencionan, pasala en el campo forma_gorro de la tool; si no la mencionan, dejala \
vacia (se buscan las 3 formas).

Si el pedido es mas abierto o exploratorio (ej: "no se que ponerme", "que me combina para el carrete"), \
conversa un poco primero para entender el contexto (ocasion, que tiene, que le gusta) antes de sugerir \
una busqueda -- en una conversacion asi, NUNCA llames la tool en el primer mensaje.

Si en ningun momento de la conversacion la persona nombro un tipo de prenda concreto (polera, poleron, \
camisa, chaqueta, chaleco, camiseta, top, pantalon, short, falda, o gorro), NO llames la tool adivinando \
cual -- preguntale directamente cual de esas prendas quiere, con un par de ejemplos, antes de buscar.

Cuando te pidan ayuda para combinar una prenda que ya tienen (ej: "que me combino con una camisa \
cuadrille y jeans negros"), da SIEMPRE minimo 2-3 alternativas distintas y variadas (distintos estilos o \
prendas), nunca una sola recomendacion -- la idea es que la persona elija, no imponerle un solo look. \
Formatea cada opcion como un item numerado con su titulo en negrita (ej: "1. **Streetwear clasico:** \
..."), con una linea en blanco entre cada opcion, para que se lea como una lista clara, no como un \
parrafo corrido. Despues de dar las opciones, termina preguntando si la persona ya tiene alguna de esas \
prendas o si quiere que le busques opciones reales del catalogo. Si te dice que quiere buscar, fijate \
que opcion eligio -- si esa opcion nombra mas de una prenda (ej: poleron + pantalon), pregunta cual de \
esas dos quiere buscar primero -- y ahi segui el proceso normal (interpreta tipo de prenda y corte, \
llama sugerir_busqueda).

Si la app te avisa que encontro la prenda pero no en la talla de la persona (mensaje que termina \
preguntando si quiere verla igual en otras tallas) y la persona responde que si, llama sugerir_busqueda \
de nuevo con los mismos datos de esa prenda MAS ignorar_talla=true -- asi no se le vuelve a preguntar \
lo mismo. Si dice que no, no vuelvas a ofrecerle esa misma prenda sin que ella lo pida de nuevo.

Nunca termines una respuesta dejando a la persona sin ningun camino para seguir. Si el catalogo no \
tiene lo que busca, o la busqueda no funciono, no te quedes en un simple "no encontre nada" -- ofrece \
seguir ajustando la busqueda (ej: "¿probamos con otro corte, otro color, o lo que prefieras?"), para que \
la conversacion siga sin que tenga que reabrir el chat.

No llames la herramienta si todavia no diste ningun consejo o si la persona no parece lista para buscar."""

KOKO_TOOL_SUGERIR_BUSQUEDA = {
    "name": "sugerir_busqueda",
    "description": (
        "Propone activar el buscador real de la app con una prenda (y opcionalmente un corte) "
        "concretos, despues de haber dado consejo de estilo en la conversacion."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "categoria": {
                "type": "string",
                "enum": ["prenda superior", "prenda inferior", "gorro"],
            },
            "tipo_prenda": {
                "type": "string",
                "enum": list(TIPOS_PRENDA_CONOCIDOS.keys()),
            },
            "corte": {
                "type": "string",
                "enum": list(CORTES_CONOCIDOS.keys()),
            },
            "forma_gorro": {
                "type": "string",
                "description": "Solo si categoria es 'gorro' y la persona pidio una forma concreta.",
                "enum": FORMAS_GORRO_CONOCIDAS,
            },
            "subtipo": {
                "type": "string",
                "description": (
                    "Solo si tipo_prenda es 'pantalon', 'shorts', 'top' o 'chaqueta' Y la persona pidio "
                    "una variante concreta (ej. pantalon de 'jeans'/'cargo'/'buzo', chaqueta 'bomber'/"
                    "'mezclilla'(tambien dicha 'denim' o de 'jean')/'cuero'). Si no la menciono, dejalo vacio."
                ),
                "enum": list(SUBTIPOS_CONOCIDOS.keys()),
            },
            "presupuesto_max": {
                "type": "integer",
                "description": (
                    "Solo si la persona menciono un presupuesto o tope de precio (ej: 'unos 30 mil', "
                    "'no mas de 25 lucas'). Numero entero en pesos chilenos (CLP), sin puntos ni "
                    "simbolo (ej: 30000). El catalogo SI filtra por esto de verdad -- nunca inventes "
                    "un numero que la persona no dijo."
                ),
            },
            "ignorar_talla": {
                "type": "boolean",
                "description": (
                    "Poner en true SOLO cuando ya le avisaste a la persona que no habia stock en su "
                    "talla y ella confirmo que igual quiere ver las opciones en otras tallas. En "
                    "cualquier otro caso, dejalo en false (o no lo mandes)."
                ),
            },
        },
        "required": ["categoria", "tipo_prenda"],
    },
}


def _sugerencia_candidatos_catalogo(sugerencia, catalog=None):
    """Corre el mismo filtro estricto que usa el buscador real (categoria/
    tipo_prenda exacto, mas corte/subtipo si se pidieron) y devuelve los
    candidatos que calzarian. Recibe "catalog" opcional (por defecto el
    catalogo completo) para poder reusarse tambien con un catalogo ya
    filtrado por talla -- ver _sugerencia_disponible_en_talla()."""
    catalog = load_json(CATALOG_PATH) if catalog is None else catalog
    catalog = filtrar_gorros_por_forma(catalog, sugerencia.get("forma_gorro", ""))
    texto_pedido = f'{sugerencia.get("tipo_prenda", "")} {sugerencia.get("corte", "")} {sugerencia.get("subtipo", "")}'
    return elegir_candidatos(
        "", texto_pedido, catalog, cantidad=CANTIDAD_RESULTADOS,
        categoria_pedida=sugerencia.get("categoria", ""),
    )


def _sugerencia_calza_con_catalogo(sugerencia):
    """Capa de validacion extra: confirma que, si se buscara con estos
    filtros, TODOS los productos que saldrian calzan exacto con la
    categoria de prenda pedida -- antes de dejar que el frontend muestre la
    sugerencia de Koko. Si no hay ni un producto que calce, tampoco se
    considera valida (no tiene sentido sugerir una busqueda vacia). No mira
    talla -- eso lo revisa aparte _sugerencia_disponible_en_talla()."""
    candidatos = _sugerencia_candidatos_catalogo(sugerencia)
    if not candidatos:
        return False
    tipo_prenda = sugerencia.get("tipo_prenda", "").lower()
    return all(p["categoria"].lower() == tipo_prenda for p in candidatos)


def _sugerencia_disponible_en_talla(sugerencia, tallas_usuario):
    """Ya se confirmo que la sugerencia calza con el catalogo (categoria
    exacta) -- esto revisa ADEMAS si queda algun candidato en alguna de las
    tallas estimadas del usuario. Devuelve True si no hay tallas estimadas
    (nada que revisar) o si al menos 1 candidato tiene esa talla."""
    if not tallas_usuario:
        return True
    catalog = filtrar_por_talla(load_json(CATALOG_PATH), tallas_usuario)
    return bool(_sugerencia_candidatos_catalogo(sugerencia, catalog))


def _texto_reglas_para_prompt(reglas):
    lineas = []
    for regla in reglas.get("reglas", []):
        atributos = ", ".join(regla.get("atributos", []))
        lineas.append(f'- {regla["genero"]} + {regla["ocasion"]} + {regla["prenda"]}: {atributos}')
    return "\n".join(lineas) if lineas else "(sin reglas validadas todavia)"


def _bloque_hobbies_para_prompt(hobbies, generos_musicales, deportes_subtipo=None):
    """Arma el texto de sugerencias de hobby VALIDADAS para el prompt de
    Koko -- ver REGLAS_HOBBY. Degradado a sugerencia OPCIONAL 2026-08-20
    (antes forzaba el corte y le decia a Koko que se saltara la pregunta --
    decision explicita del usuario: el enfoque de exclusion por categoria,
    ver EXCLUSIONES_HOBBY, es mas confiable que imponer un unico estilo
    "correcto"). Si el usuario no tiene ninguna sugerencia validada
    aplicable (hoy, casi siempre -- solo existe la de musica+rock), Koko no
    inventa ningun gusto/tendencia que no este validada."""
    reglas_hobby = _reglas_hobby_usuario(hobbies, generos_musicales, deportes_subtipo)
    if not reglas_hobby:
        return (
            "Todavia no hay ninguna sugerencia de estilo validada para los hobbies de este usuario (o "
            "no tiene hobbies cargados en su perfil) -- NO le atribuyas ningun gusto musical o de "
            "estilo que no haya dicho el mismo en la conversacion. Nunca inventes una asociacion "
            "hobby->estilo que no este en esta lista."
        )
    lineas = []
    for regla in reglas_hobby:
        prendas = " o ".join(sorted(regla["prenda_preferida"]))
        if regla.get("tipo_sugerencia") == "accesorio":
            # Sugerencias sin corte real de por medio (ej. "gorro como
            # accesorio frecuente") -- no inventar un corte que no aplica.
            lineas.append(f'- Sobre {prendas}: {regla["nota"]}.')
        else:
            lineas.append(
                f'- Si busca {prendas}: podes mencionar como IDEA un corte "{regla["corte"]}", color base '
                f'{regla["color_base"]}. {regla["nota"]}. Para cualquier otra prenda que no sea esa, esta '
                "sugerencia no aplica."
            )
    hobbies_texto = ", ".join(sorted({r["etiqueta"] for r in reglas_hobby}))
    return (
        f"Este usuario eligio en su perfil que le gusta {hobbies_texto}. Con eso, tenes esta(s) "
        'sugerencia(s) de estilo OPCIONAL(ES) -- validada(s) por el dueño del proyecto (confianza '
        '"validacion_inicial": referencias visuales, no una encuesta a muchas personas), pero SOLO una '
        "idea, nunca una regla dura ni un dato que ya tengas confirmado:\n" + "\n".join(lineas) + "\n\n"
        "Como usarlas: si la prenda que busca la persona calza con alguna, podes MENCIONARLA como idea "
        'dentro de tu respuesta (ej: "como te gusta el rock, muchos buscan algo oversize con gráfico '
        'grande, ¿te tinca eso o preferis otra onda?"). Nunca la des por confirmada ni te saltees '
        "preguntar el corte real -- segui siempre el proceso normal de preguntas (ver mas abajo en este "
        "prompt), esto es solo un plus conversacional. SIEMPRE prioriza lo que el usuario diga "
        'explicitamente en la conversacion por sobre esta sugerencia (ej: si pide algo con "diseño '
        'chico" o un corte distinto, seguí lo que pidió). Nunca prometas que la búsqueda filtró por '
        "color o estampado -- el catálogo no tiene esos datos cargados por prenda (fuera de gorro y "
        "chaqueta), así que color_base/la nota son solo para que converses con criterio, nunca una "
        "promesa de filtro real."
    )


def _resumen_perfil_para_prompt(perfil, tallas_usuario):
    """Arma un resumen en texto plano de los datos de perfil que el usuario
    ya cargo (genero/edad/altura/peso, mas la talla estimada) para que Koko
    los pueda usar en la conversacion sin volver a preguntarlos -- ej. para
    hablar de talla, o ajustar el consejo a la edad. Nunca inventa un dato
    que no venga en 'perfil': si algo falta, simplemente no aparece en la
    linea. Los datos sensibles (nombre, gmail, telefono) nunca llegan hasta
    aca -- el frontend nunca los manda (decision de privacidad ya tomada,
    ver docs/ui_features.md)."""
    genero = _texto_seguro(perfil.get("genero"))
    edad = _texto_seguro(perfil.get("edad", ""))
    altura = _texto_seguro(perfil.get("altura", ""))
    peso = _texto_seguro(perfil.get("peso", ""))
    partes = []
    if genero:
        partes.append(f"genero {genero}")
    if edad:
        partes.append(f"{edad} anos")
    if altura:
        partes.append(f"{altura}m de altura")
    if peso:
        partes.append(f"{peso}kg")
    if not partes:
        return (
            "Este usuario todavia no cargo datos de perfil (genero/edad/altura/peso) -- no asumas "
            "ninguno, pregunta si hace falta para dar un consejo mas preciso."
        )
    texto = "Datos de perfil que ya dio el usuario (no se los vuelvas a preguntar): " + ", ".join(partes) + "."
    if tallas_usuario:
        extra = f" (o {tallas_usuario[1]})" if len(tallas_usuario) > 1 else ""
        texto += f" Talla estimada: {tallas_usuario[0]}{extra}."
    return texto


def _resumen_favoritos_para_prompt(email):
    """Arma un resumen en texto plano de los favoritos ya guardados del
    usuario (data/favoritos.json, via obtener_favoritos), para que Koko los
    pueda mencionar con naturalidad en la conversacion -- ej. para no
    repetir lo mismo que ya tiene guardado, o preguntar si busca algo
    parecido o distinto. Devuelve None si no hay ninguno (o no hay email) --
    Koko no debe asumir que tiene favoritos si no los tiene."""
    favoritos = obtener_favoritos(email)
    if not favoritos:
        return None
    nombres = [f'{f.get("nombre", "")} ({f.get("tienda", "")})' for f in favoritos[-8:] if f.get("nombre")]
    if not nombres:
        return None
    return f"Tiene {len(favoritos)} producto(s) guardados como favoritos, los mas recientes: {', '.join(nombres)}."


def construir_system_prompt_koko(
    email, reglas, hobbies=None, generos_musicales=None, deportes_subtipo=None, perfil=None, tallas_usuario=None,
):
    resumen = resumen_historial_para_prompt(email)
    if resumen:
        bloque_historial = (
            "Historial de este usuario en la app (usalo para personalizar tu consejo, y MENCIONA "
            'explicitamente por que recomiendas algo en base a esto, ej: "como sueles preferir '
            f'oversize..."): {resumen}'
        )
    else:
        bloque_historial = (
            "Este usuario todavia no tiene historial en la app (es nuevo o no ha buscado nada) -- "
            "da consejo general basado en las reglas de arriba, sin inventar gustos que no conoces."
        )
    favoritos_texto = _resumen_favoritos_para_prompt(email) or (
        "Este usuario todavia no tiene ningun favorito guardado -- no asumas que tiene alguno."
    )
    return KOKO_SYSTEM_PROMPT_BASE.format(
        reglas=_texto_reglas_para_prompt(reglas), historial=bloque_historial,
        hobbies=_bloque_hobbies_para_prompt(hobbies, generos_musicales, deportes_subtipo),
        perfil=_resumen_perfil_para_prompt(perfil or {}, tallas_usuario or []),
        favoritos=favoritos_texto,
    )


@app.route("/api/koko/historial_chat")
def koko_historial_chat():
    """Devuelve la conversacion guardada de este email, para que el
    frontend la pinte de nuevo al abrir el chat -- nunca se pierde al
    recargar la pagina o volver a entrar. Tambien devuelve
    "preferencia_idioma" (None o "chileno") -- lo usa /perfil para mostrar
    si el usuario ya le pidio a Koko hablar como chileno alguna vez."""
    email = _texto_seguro(request.args.get("email", ""))
    return jsonify({
        "mensajes": cargar_historial_chat(email),
        "preferencia_idioma": preferencia_idioma_koko(email),
    })


@app.route("/api/estimar_talla")
def api_estimar_talla():
    """Talla estimada a partir de genero/peso/altura -- mismo calculo que
    ya usa el buscador (estimar_tallas), expuesto aparte para que /perfil
    la pueda mostrar como referencia sin tener que duplicar la logica en
    JS. No necesita catalogo ni hace ninguna busqueda."""
    genero = _texto_seguro(request.args.get("genero", ""))
    peso = _texto_seguro(request.args.get("peso", ""))
    altura = _texto_seguro(request.args.get("altura", ""))
    return jsonify({"tallas": estimar_tallas(genero, peso, altura)})


@app.route("/api/koko/reiniciar", methods=["POST"])
def koko_reiniciar():
    """Borra el historial de chat guardado de este email -- boton
    'Reiniciar conversacion' del panel de Koko. El frontend pide
    confirmacion antes de llamar aca (ver koko.js)."""
    data = request.get_json() or {}
    email = _texto_seguro(data.get("email", ""))
    reiniciar_chat_koko(email)
    return jsonify({"ok": True})


@app.route("/api/koko/chat", methods=["POST"])
@limiter.limit("10 per minute")
def koko_chat():
    data = request.get_json() or {}
    email = _texto_seguro(data.get("email", ""))
    perfil = data.get("perfil") or {}
    if not isinstance(perfil, dict):
        perfil = {}
    hobbies = _lista_texto_segura(perfil.get("hobbie"))
    generos_musicales = _lista_texto_segura(perfil.get("hobbie_musica_genero"))
    deportes_subtipo = _lista_texto_segura(perfil.get("hobbie_deportes_subtipo"))
    # Talla estimada del usuario (2026-08-25): mismo calculo que usa el
    # buscador real, para poder avisar en el chat ANTES de sugerir una
    # busqueda que despues saldria vacia en la talla de esta persona.
    tallas_usuario = estimar_tallas(
        _texto_seguro(perfil.get("genero")), _texto_seguro(perfil.get("peso", "")), _texto_seguro(perfil.get("altura", "")),
    )
    mensajes = data.get("mensajes") or []
    if not isinstance(mensajes, list):
        mensajes = []
    # Tope de cuantos mensajes de historial se procesan de una -- protege
    # contra un payload armado a mano (no por el frontend real, que nunca
    # manda tanto) con miles de mensajes falsos, que saldria caro en
    # tokens de la API. Se queda con los ultimos (los mas relevantes para
    # la conversacion actual).
    mensajes = mensajes[-MAX_MENSAJES_HISTORIAL_KOKO:]

    mensajes_api = [
        {
            "role": "user" if m.get("rol") == "usuario" else "assistant",
            "content": _texto_seguro(m.get("texto", ""), LARGO_MAXIMO_MENSAJE_KOKO),
        }
        for m in mensajes
        if isinstance(m, dict) and m.get("texto")
    ]
    if not mensajes_api:
        return jsonify({"respuesta_texto": "", "sugerencia": None})

    # El frontend siempre manda la conversacion completa, pero el ultimo
    # mensaje es siempre el nuevo (el resto ya se guardo en llamadas
    # anteriores) -- se guarda aparte al final, junto con la respuesta.
    ultimo_mensaje_usuario = (
        mensajes_api[-1]["content"] if mensajes_api[-1]["role"] == "user" else ""
    )

    # Limite diario de mensajes (2026-08-11): se revisa ANTES de llamar a
    # la API real (para no gastar la llamada si ya esta topado) y antes de
    # sumar este mensaje al conteo. Se guarda igual en el historial
    # visible (para que quede prolijo si se recarga la pagina), pero NO
    # cuenta como uno mas de los 15 -- ya esta bloqueado, seguir contando
    # mientras insiste no cambia nada.
    if mensajes_usuario_ultimas_24h(email) >= LIMITE_MENSAJES_KOKO_DIA:
        respuesta_texto = (
            "Guau, llegaste al límite de mensajes de hoy con Koko 🐶 -- vuelve mañana para seguir la charla."
        )
        guardar_mensaje_chat(email, "usuario", ultimo_mensaje_usuario)
        guardar_mensaje_chat(email, "koko", respuesta_texto)
        return jsonify({"respuesta_texto": respuesta_texto, "sugerencia": None, "limite_alcanzado": True})

    if not ANTHROPIC_API_KEY:
        respuesta_texto = (
            "Guau... todavia no puedo responder: falta configurar la clave de la API de Anthropic "
            "en el servidor. Avisale al dueno del proyecto."
        )
        guardar_mensaje_chat(email, "usuario", ultimo_mensaje_usuario)
        guardar_mensaje_chat(email, "koko", respuesta_texto)
        return jsonify({"respuesta_texto": respuesta_texto, "sugerencia": None})

    # Recien aca se sabe que el mensaje realmente va a llegar a la API real
    # -- cuenta para el limite diario. (El caso de arriba, sin clave
    # configurada, no cuenta: no es culpa ni responsabilidad del usuario.)
    registrar_mensaje_usuario_koko(email)

    reglas = load_json(REGLAS_PATH)
    system_prompt = construir_system_prompt_koko(
        email, reglas, hobbies, generos_musicales, deportes_subtipo, perfil=perfil, tallas_usuario=tallas_usuario,
    )

    cliente = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        respuesta = cliente.messages.create(
            model="claude-sonnet-5",
            max_tokens=500,
            system=system_prompt,
            tools=[KOKO_TOOL_SUGERIR_BUSQUEDA],
            messages=mensajes_api,
        )
    except Exception as exc:
        respuesta_texto = f"Guau, tuve un problema para responder ({exc}). Intenta de nuevo."
        guardar_mensaje_chat(email, "usuario", ultimo_mensaje_usuario)
        guardar_mensaje_chat(email, "koko", respuesta_texto)
        return jsonify({"respuesta_texto": respuesta_texto, "sugerencia": None})

    texto_partes = []
    sugerencia = None
    for bloque in respuesta.content:
        if bloque.type == "text":
            texto_partes.append(bloque.text)
        elif bloque.type == "tool_use" and bloque.name == "sugerir_busqueda":
            sugerencia = dict(bloque.input)

    # Corrige la sugerencia contra lo que se dijo en la conversacion,
    # usando los mismos detectores que usa el buscador por formulario
    # (detectar_tipo_prenda_conversacion/detectar_corte_pedido_conversacion/
    # detectar_forma_gorro_conversacion) sobre la conversacion completa --
    # usuario Y Koko, no solo usuario. Antes solo se miraba lo que escribia
    # el usuario, pero eso rompia el flujo de "Koko sugiere 2-3 opciones de
    # outfit -> el usuario elige una sin repetir el nombre de la prenda"
    # (ej: "buscame la primera opcion"): la prenda concreta la habia
    # nombrado KOKO, no el usuario, asi que el gate la descartaba como si
    # fuera una adivinanza.
    #
    # BUG encontrado en produccion (2026-08-10) y corregido de paso: la
    # primera version de este fix juntaba TODOS los mensajes en un solo
    # texto largo antes de buscar -- en una conversacion que toco varios
    # tipos de prenda (ej. Koko sugirio "polera oversize" como combo hace
    # rato, y el usuario penso despues en "poleron oversize" para un
    # regalo), eso hacia que ganara la prenda que aparece primero en el
    # DICCIONARIO (TIPOS_PRENDA_CONOCIDOS tiene "polera" antes que
    # "poleron"), no la del tema actual -- terminaba armando una busqueda
    # de "polera baggy" (de un tema viejo) en vez de "poleron oversize" (lo
    # que se estaba pidiendo), y esa busqueda vieja no traia resultados:
    # "no encontre nada" aunque el catalogo si tuviera lo pedido. Ahora se
    # revisan los mensajes del mas reciente al mas antiguo (funciones
    # "..._conversacion", ver mas arriba) y se usa la coincidencia del
    # mensaje mas nuevo -- sigue sirviendo para el caso original (el nombre
    # de Koko sigue estando en uno de los ultimos mensajes) sin dejar que
    # temas ya superados le ganen al actual. Si NADIE (ni usuario ni Koko)
    # nombro una prenda concreta en ningun momento, recien ahi se descarta
    # la sugerencia y se pregunta, en vez de arriesgarse a mostrar la
    # categoria equivocada.
    if sugerencia is not None:
        textos_mensajes = [m["content"] for m in mensajes_api]
        # BUG "poleron + pantalon de buzo" (2026-08-25): _valor_o_deteccion
        # confiaba en el tipo_prenda que Koko proponia con tal de que esa
        # palabra se hubiera dicho en ALGUN momento de la conversacion --
        # en una charla larga, eso dejaba que una prenda mencionada hace
        # rato (ej. un combo viejo "poleron + pantalon de buzo") todavia
        # "confirmara" una propuesta equivocada de Koko mucho despues,
        # aunque el pedido actual fuera solo por el poleron (mismo tipo de
        # bug que el de "chaqueta/camisa" del 2026-08-17, pero cruzando
        # MENSAJES en vez de dentro del mismo mensaje). Se acota la
        # confirmacion a los ultimos mensajes -- si la propuesta de Koko no
        # se sostiene ahi, cae al detector determinista de siempre, que
        # busca desde el mensaje mas reciente hacia atras y encuentra la
        # prenda del tema actual.
        tipo_prenda_detectado = _valor_o_deteccion(
            sugerencia.get("tipo_prenda"), TIPOS_PRENDA_CONOCIDOS, textos_mensajes,
            detectar_tipo_prenda_conversacion,
            mensajes_confirmacion=textos_mensajes[-VENTANA_CONFIRMACION_TIPO_PRENDA_KOKO:],
        )

        if not tipo_prenda_detectado:
            sugerencia = None
            texto_partes = [
                "Antes de tirarte el buscador, cuéntame bien qué tipo de prenda andas buscando: "
                "¿algo de arriba (polera, polerón, camisa, chaqueta...), de abajo (pantalón, short, "
                "falda...), o un gorro?"
            ]
        else:
            sugerencia["tipo_prenda"] = tipo_prenda_detectado
            grupo = TIPO_PRENDA_A_CATEGORIA_GRUPO.get(tipo_prenda_detectado)
            if grupo:
                sugerencia["categoria"] = grupo
            corte_detectado = _valor_o_deteccion(
                sugerencia.get("corte"), CORTES_CONOCIDOS, textos_mensajes,
                detectar_corte_pedido_conversacion,
            )
            if corte_detectado:
                sugerencia["corte"] = corte_detectado
            if tipo_prenda_detectado == "gorro":
                forma_detectada = _valor_o_deteccion(
                    sugerencia.get("forma_gorro"), FORMA_GORRO_CONOCIDA, textos_mensajes,
                    detectar_forma_gorro_conversacion,
                )
                if forma_detectada:
                    sugerencia["forma_gorro"] = forma_detectada
            if tipo_prenda_detectado in SUBTIPOS_POR_TIPO_PRENDA:
                subtipo_detectado = _valor_o_deteccion(
                    sugerencia.get("subtipo"), _subtipos_validos_para(tipo_prenda_detectado), textos_mensajes,
                    lambda mensajes: detectar_subtipo_pedido_conversacion(mensajes, tipo_prenda_detectado),
                )
                if subtipo_detectado:
                    sugerencia["subtipo"] = subtipo_detectado

            # Segunda capa de validacion: confirma contra el catalogo real
            # que lo que se le mostraria al usuario calza exacto con la
            # categoria pedida, antes de dejar que el frontend lo muestre.
            if not _sugerencia_calza_con_catalogo(sugerencia):
                sugerencia = None
                texto_partes = [
                    "Mmm, no encontré nada que calce bien con eso en el catálogo todavía. "
                    "¿Quieres que ajustemos la búsqueda? Puedo probar con otro corte, otro tipo de "
                    "prenda, o lo que prefieras."
                ]
            elif tallas_usuario and not sugerencia.get("ignorar_talla") and not _sugerencia_disponible_en_talla(sugerencia, tallas_usuario):
                # Anticipar el "sin stock en tu talla" (2026-08-25): hay
                # productos de esa categoria en el catalogo, pero ninguno
                # calza con la talla estimada de este usuario -- se lo
                # decimos ANTES de dejar que confirme una busqueda que
                # saldria vacia, en vez de que se entere recien en
                # /resultados. Si dice que si, Koko debe volver a llamar la
                # tool con ignorar_talla=true (ver KOKO_TOOL_SUGERIR_BUSQUEDA
                # y el prompt) para saltarse este mismo aviso la 2da vez.
                sugerencia = None
                nombre_prenda = TIPOS_PRENDA_CONOCIDOS.get(tipo_prenda_detectado, [tipo_prenda_detectado])[0]
                texto_partes = [
                    f"Encontré {nombre_prenda}, pero no en tu talla -- ¿quieres que te muestre igual "
                    "las opciones disponibles en otras tallas?"
                ]

    respuesta_final = " ".join(texto_partes).strip()
    guardar_mensaje_chat(email, "usuario", ultimo_mensaje_usuario)
    guardar_mensaje_chat(email, "koko", respuesta_final)

    return jsonify({
        "respuesta_texto": respuesta_final,
        "sugerencia": sugerencia,
    })


@app.route("/api/koko/interes", methods=["POST"])
def koko_interes():
    """Se llama cuando el usuario hace clic en "Ver producto" de una tarjeta
    de resultado -- una de las 2 senales de "interes" que usa el historial
    de Koko (la otra es lo que ya busca, registrado en /api/recommend)."""
    data = request.get_json() or {}
    email = _texto_seguro(data.get("email", ""))
    producto = data.get("producto") or {}
    if not isinstance(producto, dict):
        producto = {}
    registrar_interes(email, producto)
    return jsonify({"ok": True})


@app.route("/api/favoritos", methods=["GET"])
def api_favoritos():
    email = _texto_seguro(request.args.get("email", ""))
    return jsonify({"favoritos": obtener_favoritos(email)})


@app.route("/api/favoritos", methods=["POST"])
def api_favoritos_alternar():
    data = request.get_json() or {}
    email = _texto_seguro(data.get("email", ""))
    producto = data.get("producto") or {}
    if not isinstance(producto, dict):
        producto = {}
    if not email or not _texto_seguro(producto.get("nombre")):
        return jsonify({"ok": False}), 400
    marcado = alternar_favorito(email, producto)
    return jsonify({"ok": True, "marcado": marcado})


@app.route("/api/favoritos", methods=["DELETE"])
def api_favoritos_vaciar():
    email = _texto_seguro(request.args.get("email", ""))
    if not email:
        return jsonify({"ok": False}), 400
    vaciar_favoritos(email)
    return jsonify({"ok": True})


@app.route("/sw.js")
def service_worker():
    """Sirve el service worker desde la RAIZ (no /static/sw.js) para que
    su alcance ("scope") por defecto sea toda la app -- un service worker
    solo puede controlar paginas dentro de la carpeta donde se sirve (o
    mas abajo), y /static/ no alcanza a cubrir /, /vitrina, etc. El header
    Service-Worker-Allowed es ademas explicito, por las dudas."""
    resp = app.send_static_file("sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/resultados")
def resultados():
    # La pagina en si es solo el molde -- los resultados los deja guardados
    # script.js en sessionStorage antes de mandar aca, y resultados.js los
    # lee y los dibuja al cargar.
    return render_template("resultados.html")


@app.route("/vitrina")
def vitrina():
    # Igual que /resultados: el molde nomas, vitrina.js pide los productos
    # a /api/vitrina y los dibuja al cargar.
    return render_template("vitrina.html")


@app.route("/perfil")
def perfil():
    # El perfil de navegacion (altura/peso/hobbies para buscar) sigue
    # viviendo en localStorage (ver comun.js) -- esta pagina lo muestra
    # igual que siempre. Ademas, si hay una cuenta real logueada (ver
    # docs/cuentas.md), se le pasa el registro de la base de datos para
    # mostrar la seccion de cuenta (correo, foto, cerrar sesion).
    usuario = None
    if session.get("usuario_id"):
        usuario = db_usuarios.buscar_por_id(session["usuario_id"])
    return render_template("perfil.html", usuario=usuario)


@app.route("/favoritos")
def favoritos():
    # Igual que /vitrina: el molde nomas, favoritos.js pide la lista a
    # /api/favoritos y la dibuja al cargar.
    return render_template("favoritos.html")


@app.route("/ir/<tienda_id>")
@requiere_cuenta
def ir_a_tienda_general(tienda_id):
    """Visita general a una tienda (no a un producto en particular) -- la
    usa el boton 'Visitar tienda' de la ficha de tienda (/tienda/<id>,
    abierta desde el mapa 'Descubre tiendas cerca de mi'). Mismo mecanismo
    que ir_a_tienda() de abajo (descuento aplicado + clic registrado para
    el tracking), pero sin redirect a un producto especifico -- va a la
    home. El clic se guarda con producto="(visita general)" para
    distinguirlo en /admin/clics.

    @requiere_cuenta (2026-08-24): este es uno de los 2 puntos donde se
    exige cuenta real para "comprar" -- ver docs/cuentas.md. El otro es
    ir_a_tienda() de abajo; el 3ro (catalogo mock) se bloquea del lado del
    cliente en abrirEnlaceConAnimacion (comun.js)."""
    tienda = cargar_tiendas().get(tienda_id)
    if not tienda or tienda.get("tipo") != "con_sitio_web":
        return redirect("/")
    registrar_clic_tienda(tienda_id, "(visita general)")
    url_destino = f'https://{tienda["dominio"]}/discount/{tienda["codigo_descuento"]}'
    return redirect(url_destino)


@app.route("/ir/<tienda_id>/<path:producto>")
@requiere_cuenta
def ir_a_tienda(tienda_id, producto):
    """Link que se comparte/publica para un producto de una tienda real
    'con_sitio_web' -- redirige directo a la pagina del producto con el
    codigo de descuento ya aplicado (formato Shopify), sin que la persona
    tenga que escribirlo, y deja registrado el clic (fecha/tienda/producto)
    para el tracking. Si la tienda no existe o es 'sin_sitio_web' (no hay
    sitio al que redirigir), manda al inicio en vez de fallar feo."""
    tienda = cargar_tiendas().get(tienda_id)
    if not tienda or tienda.get("tipo") != "con_sitio_web":
        return redirect("/")
    registrar_clic_tienda(tienda_id, producto)
    url_destino = f'https://{tienda["dominio"]}/discount/{tienda["codigo_descuento"]}?redirect=/products/{producto}'
    return redirect(url_destino)


@app.route("/tienda/<tienda_id>")
def tienda_perfil(tienda_id):
    """Ficha de una tienda dentro de la app -- a donde lleva tocar una
    tarjeta de la fila "Llegan rapido a ti" (nunca directo a Maps ni al
    sitio externo sin pasar por /ir/, que es lo que deja el clic
    registrado). Todavia no muestra productos propios de la tienda -- el
    catalogo de prueba y las tiendas reales son 2 sistemas separados a
    proposito (ver CLAUDE.md), asi que no hay como saber que vende cada
    tienda real sin inventarlo."""
    tienda = cargar_tiendas().get(tienda_id)
    if not tienda:
        return redirect("/vitrina")
    return render_template("tienda_perfil.html", tienda_id=tienda_id, tienda=tienda)


@app.route("/api/tiendas_rapido")
def api_tiendas_rapido():
    """Tiendas piloto ordenadas por tiempo de despacho REAL a la direccion
    que el usuario escribio en su perfil (RM vs regiones) -- ver
    _estimar_envio_real() y data/envios_tiendas.json (investigado a mano
    por tienda, ver docs/tiendas_admin.md). Ya no es una aproximacion por
    comuna del local: la comuna se sigue guardando por tienda (para
    retiro en tienda a futuro) pero no se usa para esta estimacion."""
    direccion = _texto_seguro(request.args.get("direccion", ""), 300)
    filas = []
    for tienda_id, datos in cargar_tiendas().items():
        comuna = datos.get("comuna", "")
        region = datos.get("region", "")
        estimacion = _estimar_envio_real(direccion, datos.get("nombre", tienda_id))
        filas.append({
            "id": tienda_id,
            "nombre": datos.get("nombre", tienda_id),
            "comuna": comuna,
            "region": region,
            "envio_texto": estimacion["texto"],
            "envio_dias": estimacion["dias"],
            "envio_tiene_dato": estimacion["tiene_dato"],
        })
    # Ordena primero por si la tienda tiene plazo de envio verificado o no
    # (pedido explicito del usuario, 2026-08-24): una tienda CON dato
    # siempre va antes que una SIN dato, sin excepcion -- no depende de que
    # "sin dato" numericamente valga 99 en _dias_habiles_a_numero (eso ya
    # las mandaba al final en la practica, pero no era una garantia
    # explicita si algun dia una tienda con dato real tuviera un numero
    # igual o mayor a 99). Dentro de cada grupo, ordena por dias como
    # antes (mas rapida primero).
    filas.sort(key=lambda f: (not f["envio_tiene_dato"], f["envio_dias"]))
    return jsonify({"tiendas": filas, "direccion_configurada": bool(direccion)})


@app.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("6 per minute, 20 per hour", methods=["POST"])
def admin_login():
    error = None
    siguiente = request.args.get("siguiente") or request.form.get("siguiente") or "/admin/tiendas"
    # Solo permite volver a una ruta interna de /admin/ -- nunca a una URL
    # externa (evita que alguien arme un link tipo /admin/login?siguiente=
    # https://sitio-malo.cl y despues del login mande para alla).
    if not siguiente.startswith("/admin/"):
        siguiente = "/admin/tiendas"

    if request.method == "POST":
        if not ADMIN_PASSWORD:
            error = "Todavía no se configuró ADMIN_PASSWORD en el servidor -- avisale al dueño del proyecto."
        elif secrets.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
            session.permanent = True
            session["admin_autenticado"] = True
            return redirect(siguiente)
        else:
            error = "Contraseña incorrecta."

    return render_template("admin_login.html", error=error, siguiente=siguiente)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_autenticado", None)
    return redirect("/admin/login")


# --- Cuentas de usuario reales (Google + email/contraseña) -----------------
# Ver docs/cuentas.md para el diseño completo. Reusa el mismo mecanismo de
# sesion que /admin/login (app.secret_key, session.permanent) pero con
# session["usuario_id"] en vez de session["admin_autenticado"] -- una
# persona puede estar logueada como usuario y como admin al mismo tiempo,
# son 2 llaves de sesion independientes.

def _perfil_desde_formulario(form):
    """Arma un dict de perfil (mismos nombres que CAMPOS_PERFIL_* en
    db_usuarios) a partir de un form de /registro -- los campos de lista
    (hobbies) llegan como texto JSON en inputs ocultos, escritos por JS
    desde getPerfil() antes de enviar (ver static/auth.js)."""
    perfil = {}
    for campo in db_usuarios.CAMPOS_PERFIL_TEXTO + db_usuarios.CAMPOS_PERFIL_NUMERO:
        perfil[campo] = _texto_seguro(form.get(campo, ""), 200)
    for campo in db_usuarios.CAMPOS_PERFIL_LISTA:
        try:
            valor = json.loads(form.get(campo, "[]"))
        except (json.JSONDecodeError, TypeError):
            valor = []
        perfil[campo] = _lista_texto_segura(valor)
    return perfil


def _iniciar_sesion_usuario(usuario, recordar=True):
    """Arranca la sesion de la cuenta ya identificada (registro, login o
    Google). 'recordar' controla si la sesion dura los 30 dias
    configurados (session.permanent = True) o si es una sesion normal de
    navegador, que se borra sola al cerrar el navegador del todo --
    pedido explicito del usuario, 2026-08-24: se pregunta al crear la
    cuenta (y tambien al loguearse) si quiere quedar recordado en ese
    dispositivo. En Safari NUNCA se guarda como permanente, sin importar
    lo que haya elegido -- siempre vuelve a pedir el login (ver
    _es_safari), porque Safari en iOS puede borrar la sesion sola de
    todas formas y asi no queda un estado a medias/inconsistente."""
    session.permanent = bool(recordar) and not _es_safari(request.user_agent.string)
    session["usuario_id"] = usuario["id"]


@app.route("/registro", methods=["GET", "POST"])
@limiter.limit("10 per minute, 30 per hour", methods=["POST"])
def registro():
    error = None
    siguiente = _siguiente_seguro(request.args.get("siguiente") or request.form.get("siguiente"))

    if request.method == "POST":
        email = _texto_seguro(request.form.get("email", ""), 200)
        password = request.form.get("password", "")
        if not email or "@" not in email:
            error = "Ingresa un correo válido."
        elif len(password) < 8:
            error = "La contraseña debe tener al menos 8 caracteres."
        elif db_usuarios.buscar_por_email(email):
            error = "Ya existe una cuenta con ese correo -- inicia sesión en vez de crear una nueva."
        else:
            perfil = _perfil_desde_formulario(request.form)
            usuario = db_usuarios.crear_usuario(
                email, password_hash=generate_password_hash(password), perfil=perfil
            )
            _iniciar_sesion_usuario(usuario, recordar=request.form.get("recordar") == "1")
            return redirect(siguiente)

    google_disponible = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    es_safari = _es_safari(request.user_agent.string)
    return render_template(
        "registro.html", error=error, siguiente=siguiente,
        google_disponible=google_disponible, es_safari=es_safari,
    )


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("6 per minute, 20 per hour", methods=["POST"])
def login():
    error = None
    siguiente = _siguiente_seguro(request.args.get("siguiente") or request.form.get("siguiente"))

    if request.method == "POST":
        email = _texto_seguro(request.form.get("email", ""), 200)
        password = request.form.get("password", "")
        usuario = db_usuarios.buscar_por_email(email)
        # Mensaje generico a proposito (nunca decir si el email existe o
        # no) -- mismo criterio que /admin/login, evita darle pistas a
        # quien este probando contraseñas al voleo.
        if not usuario or not usuario["password_hash"] or not check_password_hash(
            usuario["password_hash"], password
        ):
            error = "Correo o contraseña incorrectos."
        else:
            _iniciar_sesion_usuario(usuario, recordar=request.form.get("recordar") == "1")
            return redirect(siguiente)

    google_disponible = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    es_safari = _es_safari(request.user_agent.string)
    return render_template(
        "login.html", error=error, siguiente=siguiente,
        google_disponible=google_disponible, es_safari=es_safari,
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("usuario_id", None)
    return redirect("/")


@app.route("/auth/google/iniciar", methods=["POST"])
@limiter.limit("10 per minute, 30 per hour")
def auth_google_iniciar():
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        return jsonify({"error": "Google login no está configurado."}), 503

    datos = request.get_json(silent=True) or {}
    perfil = datos.get("perfil") if isinstance(datos.get("perfil"), dict) else None
    siguiente = _siguiente_seguro(datos.get("siguiente"))

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session["auth_siguiente"] = siguiente
    # Igual que el checkbox "mantener sesion iniciada" de /login y
    # /registro, pero mandado por auth.js (no hay un <form> tradicional en
    # este flujo) -- se guarda en la sesion para usarlo en el callback,
    # donde recien se sabe si la cuenta quedo lista.
    session["recordar_pendiente"] = bool(datos.get("recordar"))
    # El perfil de localStorage (si habia uno) queda guardado en la sesion
    # -- sobrevive el viaje de ida y vuelta a accounts.google.com porque es
    # la misma cookie firmada (mismo mecanismo que admin_autenticado). Solo
    # se usa si la cuenta resulta ser NUEVA (ver auth_google_callback).
    if perfil:
        campos_validos = (
            db_usuarios.CAMPOS_PERFIL_TEXTO
            + db_usuarios.CAMPOS_PERFIL_NUMERO
            + db_usuarios.CAMPOS_PERFIL_LISTA
        )
        session["perfil_pendiente_migracion"] = {
            campo: perfil.get(campo) for campo in campos_validos if campo in perfil
        }
        session["email_pendiente_migracion"] = _texto_seguro(perfil.get("gmail", ""), 200)
    else:
        session.pop("perfil_pendiente_migracion", None)
        session.pop("email_pendiente_migracion", None)

    parametros = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": url_for("auth_google_callback", _external=True),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    url_consentimiento = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(parametros)
    return jsonify({"url": url_consentimiento})


def _google_intercambiar_code(code):
    """Intercambia el 'code' del callback por un access_token, y con ese
    token pide el perfil (email/nombre/foto) a Google -- todo con urllib
    (sin agregar la libreria 'requests', ver docs/cuentas.md). Devuelve el
    dict de userinfo, o None si algo falla (red, credenciales, etc.)."""
    datos_token = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": url_for("auth_google_callback", _external=True),
        "grant_type": "authorization_code",
    }
    try:
        peticion_token = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=urllib.parse.urlencode(datos_token).encode(),
            method="POST",
        )
        with urllib.request.urlopen(peticion_token, timeout=10) as resp:
            tokens = json.loads(resp.read())

        peticion_userinfo = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f'Bearer {tokens["access_token"]}'},
        )
        with urllib.request.urlopen(peticion_userinfo, timeout=10) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError):
        return None


@app.route("/auth/google/callback")
def auth_google_callback():
    siguiente = session.pop("auth_siguiente", None) or "/"
    perfil_pendiente = session.pop("perfil_pendiente_migracion", None) or {}
    email_pendiente = session.pop("email_pendiente_migracion", "")
    recordar = session.pop("recordar_pendiente", True)
    state_esperado = session.pop("oauth_state", None)

    if request.args.get("error"):
        # El usuario cancelo el consentimiento en Google -- no es un error
        # nuestro, solo se lo manda de vuelta al login sin drama.
        return redirect("/login")

    state_recibido = request.args.get("state", "")
    if not state_esperado or state_recibido != state_esperado:
        return redirect("/login")

    code = request.args.get("code", "")
    userinfo = _google_intercambiar_code(code) if code else None
    if not userinfo or not userinfo.get("email"):
        return redirect("/login")

    google_sub = userinfo.get("sub", "")
    usuario = db_usuarios.buscar_por_google_sub(google_sub)

    if not usuario:
        # Si ya existia una cuenta con ese email (creada antes con
        # contraseña), se vincula en vez de crear una cuenta duplicada.
        email_existente = db_usuarios.buscar_por_email(userinfo["email"])
        if email_existente:
            db_usuarios.vincular_google(email_existente["id"], google_sub)
            usuario = db_usuarios.buscar_por_id(email_existente["id"])
        else:
            # Cuenta genuinamente nueva: si habia un perfil de localStorage
            # pendiente, se usa para completar los campos que Google no
            # manda (altura, peso, direccion, hobbies, telefono) -- y el
            # EMAIL que se usa es el del perfil pendiente si existia (para
            # heredar favoritos/historial ya guardados bajo ese email hoy),
            # no el email verificado de Google.
            email_cuenta = email_pendiente or userinfo["email"]
            usuario = db_usuarios.crear_usuario(
                email_cuenta, google_sub=google_sub, perfil=perfil_pendiente
            )

    _iniciar_sesion_usuario(usuario, recordar=recordar)
    return render_template("_auth_sincronizar.html", usuario=usuario, siguiente=siguiente)


_EXTENSIONES_FOTO_PERMITIDAS = {"jpg", "jpeg", "png", "webp"}
FOTOS_USUARIOS_DIR = BASE_DIR / "static" / "img" / "usuarios"


@app.route("/perfil/foto", methods=["POST"])
@requiere_cuenta
@limiter.limit("10 per minute, 30 per hour")
def subir_foto_perfil():
    archivo = request.files.get("foto")
    if not archivo or not archivo.filename:
        return jsonify({"error": "No se recibió ningún archivo."}), 400

    nombre_seguro = secure_filename(archivo.filename)
    extension = nombre_seguro.rsplit(".", 1)[-1].lower() if "." in nombre_seguro else ""
    if extension not in _EXTENSIONES_FOTO_PERMITIDAS:
        return jsonify({"error": "Formato no permitido -- usa JPG, PNG o WEBP."}), 400

    # El nombre del archivo en disco SIEMPRE sale del usuario_id autenticado
    # (nunca del nombre que mando el navegador) -- asi no hace falta
    # confiar en secure_filename() para evitar path traversal, ya es
    # imposible por construccion.
    usuario_id = session["usuario_id"]
    FOTOS_USUARIOS_DIR.mkdir(parents=True, exist_ok=True)
    nombre_archivo = f"{usuario_id}.{extension}"
    archivo.save(FOTOS_USUARIOS_DIR / nombre_archivo)

    ruta_relativa = f"img/usuarios/{nombre_archivo}"
    db_usuarios.actualizar_foto_perfil(usuario_id, ruta_relativa)
    return jsonify({"foto_perfil": url_for("static", filename=ruta_relativa)})


@app.route("/perfil/actualizar", methods=["POST"])
@requiere_cuenta
def actualizar_perfil_cuenta():
    """Editar los datos de la cuenta ya logueada (nombre, telefono, altura,
    peso, direccion, hobbies, etc.) -- mismo set de campos que /registro,
    reusa _perfil_desde_formulario. No toca email/contraseña."""
    perfil = _perfil_desde_formulario(request.form)
    db_usuarios.actualizar_perfil(session["usuario_id"], perfil)
    return redirect("/perfil")


@app.route("/admin/tiendas")
@requiere_admin
def admin_tiendas():
    tiendas = cargar_tiendas()
    clics = cargar_clics_tiendas()
    reportes = cargar_reportes_manuales()

    conteo_clics = Counter(c["tienda"] for c in clics)
    total_reportado = Counter()
    reportes_por_tienda = {}
    for r in reportes:
        total_reportado[r["tienda"]] += r.get("monto", 0)
        reportes_por_tienda.setdefault(r["tienda"], []).append(r)

    filas = []
    for tienda_id, datos in tiendas.items():
        filas.append({
            "id": tienda_id,
            "nombre": datos.get("nombre", tienda_id),
            "tipo": datos.get("tipo"),
            "dominio": datos.get("dominio", ""),
            "codigo_descuento": datos.get("codigo_descuento", ""),
            "comuna": datos.get("comuna", ""),
            "region": datos.get("region", ""),
            "clics": conteo_clics.get(tienda_id, 0),
            "total_reportado": total_reportado.get(tienda_id, 0),
            "reportes": sorted(
                reportes_por_tienda.get(tienda_id, []), key=lambda r: r["fecha"], reverse=True
            ),
        })
    filas.sort(key=lambda f: f["nombre"].lower())

    return render_template("admin_tiendas.html", tiendas=filas, regiones=REGIONES_CHILE)


@app.route("/admin/tiendas/nueva", methods=["POST"])
@requiere_admin
def admin_tiendas_nueva():
    tienda_id = _texto_seguro(request.form.get("id", ""), 60).lower().replace(" ", "-")
    nombre = _texto_seguro(request.form.get("nombre", ""), 100)
    tipo = _texto_seguro(request.form.get("tipo", ""), 20)

    if tienda_id and nombre and tipo in ("con_sitio_web", "sin_sitio_web"):
        tiendas = cargar_tiendas()
        tienda = {"nombre": nombre, "tipo": tipo}
        if tipo == "con_sitio_web":
            tienda["dominio"] = _texto_seguro(request.form.get("dominio", ""), 200)
            tienda["codigo_descuento"] = _texto_seguro(request.form.get("codigo_descuento", ""), 60)
        # Comuna/region opcional -- si no se completa, la tienda simplemente
        # queda con la estimacion de envio mas lenta hasta que se le cargue
        # despues (ver /admin/tiendas/<id>/ubicacion).
        comuna, region = _parsear_comuna_region(request.form.get("comuna", ""), request.form.get("region", ""))
        if comuna:
            tienda["comuna"] = comuna
            tienda["region"] = region
        tiendas[tienda_id] = tienda
        guardar_tiendas(tiendas)

    return redirect("/admin/tiendas")


@app.route("/admin/tiendas/<tienda_id>/ubicacion", methods=["POST"])
@requiere_admin
def admin_tiendas_ubicacion(tienda_id):
    """Carga o actualiza la comuna/region de una tienda ya agregada -- por
    separado del alta (arriba) para poder completarla despues, sin tener
    que volver a crear la tienda. Ya no se usa para estimar el tiempo de
    envio de "Llegan rapido a ti" (eso ahora sale de
    data/envios_tiendas.json, ver _estimar_envio_real) -- queda como dato
    de referencia (ej. para mostrar retiro en tienda a futuro)."""
    tiendas = cargar_tiendas()
    if tienda_id in tiendas:
        comuna, region = _parsear_comuna_region(request.form.get("comuna", ""), request.form.get("region", ""))
        if comuna:
            tiendas[tienda_id]["comuna"] = comuna
            tiendas[tienda_id]["region"] = region
            guardar_tiendas(tiendas)

    return redirect("/admin/tiendas")


@app.route("/admin/tiendas/<tienda_id>/reporte", methods=["POST"])
@requiere_admin
def admin_tiendas_reporte(tienda_id):
    fecha = _texto_seguro(request.form.get("fecha", ""), 20)
    monto_texto = _texto_seguro(request.form.get("monto", ""), 20)
    try:
        monto = int(monto_texto)
    except ValueError:
        monto = 0

    if tienda_id in cargar_tiendas() and fecha and monto:
        registrar_reporte_manual(tienda_id, fecha, monto)

    return redirect("/admin/tiendas")


# Rangos de fecha para el panel de clics (/admin/clics) -- "dias": None
# significa sin filtro (todo el historial). "frase" se usa para armar el
# resumen copiable ("Esta semana te mandamos X clics...").
RANGOS_CLICS = {
    "7": {"etiqueta": "Últimos 7 días", "frase": "esta semana", "dias": 7},
    "14": {"etiqueta": "Últimas 2 semanas", "frase": "estas 2 semanas", "dias": 14},
    "30": {"etiqueta": "Últimos 30 días", "frase": "este mes", "dias": 30},
    "todo": {"etiqueta": "Todo el tiempo", "frase": "en total", "dias": None},
}


def _fecha_clic(clic):
    """Fecha ISO guardada en un clic (ver registrar_clic_tienda) -- un clic
    con fecha invalida/ausente simplemente no entra en ningun filtro de
    rango (pero si se cuenta en "todo el tiempo"). Ver _parsear_fecha_iso."""
    return _parsear_fecha_iso(clic.get("fecha", ""))


@app.route("/admin/clics")
@requiere_admin
def admin_clics():
    """Panel de clics: total por tienda + detalle por producto, filtrado
    por rango de fecha, mas un resumen copiable para mandarle a cada
    tienda (ej. "Esta semana te mandamos 12 clics..."). Usa los mismos
    datos que ya cuenta /admin/tiendas (clics_tiendas.json) -- esto solo
    agrega el filtro de fecha y el desglose por producto que faltaban."""
    rango = request.args.get("rango", "7")
    if rango not in RANGOS_CLICS:
        rango = "7"
    config_rango = RANGOS_CLICS[rango]

    clics = cargar_clics_tiendas()
    if config_rango["dias"] is not None:
        desde = datetime.now(timezone.utc) - timedelta(days=config_rango["dias"])
        # Una fecha invalida/ausente (_fecha_clic devuelve None) queda
        # afuera de cualquier rango con filtro -- solo "todo el tiempo"
        # (dias=None, este bloque ni se ejecuta) los sigue contando.
        clics = [c for c in clics if (_fecha_clic(c) or datetime.min.replace(tzinfo=timezone.utc)) >= desde]

    por_tienda = {}
    for c in clics:
        entrada = por_tienda.setdefault(c["tienda"], {"total": 0, "productos": Counter()})
        entrada["total"] += 1
        entrada["productos"][c.get("producto") or "(sin nombre)"] += 1

    tiendas = cargar_tiendas()
    filas = []
    for tienda_id, datos in tiendas.items():
        info = por_tienda.get(tienda_id, {"total": 0, "productos": Counter()})
        total = info["total"]
        filas.append({
            "id": tienda_id,
            "nombre": datos.get("nombre", tienda_id),
            "total": total,
            "productos": info["productos"].most_common(),
            "resumen": (
                f'Hola! {config_rango["frase"].capitalize()} te mandamos {total} '
                f'clic{"s" if total != 1 else ""} desde KOLIZION 🔥'
            ),
        })
    filas.sort(key=lambda f: f["total"], reverse=True)

    return render_template(
        "admin_clics.html", filas=filas, rango=rango, rangos=RANGOS_CLICS,
        etiqueta_rango=config_rango["etiqueta"],
    )


@app.route("/admin/usuarios")
@requiere_admin
def admin_usuarios():
    """Lista de cuentas reales (Google + email/contraseña, ver
    docs/cuentas.md) -- panel de solo lectura, mismo /admin protegido que
    ya usan /admin/tiendas y /admin/clics. Nunca muestra password_hash
    (listar_usuarios() ni siquiera lo trae de la base de datos)."""
    usuarios = db_usuarios.listar_usuarios()
    return render_template("admin_usuarios.html", usuarios=usuarios)


@app.route("/api/vitrina")
def api_vitrina():
    """Navegacion libre sin preguntas: Tendencias/Nuevos lanzamientos/Ofertas/Destacados.
    Ningun producto se repite entre las 4 secciones.
    - Ofertas: dato real del catalogo (precio_original/descuento_pct, ver
      generar_catalogo_prueba.py), ordenado de mayor a menor descuento.
    - Tendencias: dato real cuando hay (clics de las ultimas 24h, ver
      _armar_tendencias), con respaldo generico si no alcanza.
    - Nuevos lanzamientos / Destacados: el catalogo mock no tiene un dato
      real de fecha de publicacion ni de "destacado", asi que ambas son
      una muestra al azar (distinta cada vez que se entra) -- avisar si
      mas adelante se quiere un criterio real (ej. fecha real de alta del
      producto para lanzamientos)."""
    catalog = load_json(CATALOG_PATH)
    cantidad = 10

    catalogo_ofertas = sorted(
        (p for p in catalog if p.get("en_oferta")),
        key=lambda p: p.get("descuento_pct", 0),
        reverse=True,
    )[:cantidad]
    ids_usados = {p["id"] for p in catalogo_ofertas}

    resto = [p for p in catalog if p["id"] not in ids_usados]
    tendencias_con_razon = _armar_tendencias(resto, cantidad)
    ids_usados |= {p["id"] for p, _ in tendencias_con_razon}

    resto = [p for p in resto if p["id"] not in ids_usados]
    lanzamientos = random.sample(resto, min(cantidad, len(resto)))
    ids_usados |= {p["id"] for p in lanzamientos}

    resto = [p for p in resto if p["id"] not in ids_usados]
    destacados = random.sample(resto, min(cantidad, len(resto)))

    return jsonify({
        "tendencias": [formatear_producto(p, razon) for p, razon in tendencias_con_razon],
        "lanzamientos": [formatear_producto(p, "Recién llegado a KOLIZION") for p in lanzamientos],
        "ofertas": [
            formatear_producto(p, f'-{p["descuento_pct"]}% sobre el precio normal')
            for p in catalogo_ofertas
        ],
        "destacados": [formatear_producto(p, "Producto destacado") for p in destacados],
    })


@app.route("/api/recommend", methods=["POST"])
@limiter.limit("20 per minute")
def recommend():
    data = request.get_json() or {}
    catalog = load_json(CATALOG_PATH)
    reglas = load_json(REGLAS_PATH)
    modo = data.get("modo")
    plan_b = bool(data.get("plan_b"))
    # Saneo de entrada: todo lo que viene del cliente pasa por
    # _texto_seguro/_lista_texto_segura antes de usarse -- nunca confiar en
    # que el tipo/largo sea el esperado solo porque el formulario de
    # verdad manda strings cortos (alguien podria pegarle directo a la
    # API con cualquier otra cosa).
    categoria = _texto_seguro(data.get("categoria", ""))
    tipo_prenda = _texto_seguro(data.get("tipo_prenda", ""))
    subtipo = _texto_seguro(data.get("subtipo", ""))
    largo = _texto_seguro(data.get("largo", ""))
    manga = _texto_seguro(data.get("manga", ""))
    capucha = _texto_seguro(data.get("capucha", ""))
    cierre = _texto_seguro(data.get("cierre", ""))
    corte = _texto_seguro(data.get("corte", ""))
    ocasion = _texto_seguro(data.get("ocasion", ""))
    precio = _texto_seguro(data.get("precio", ""))
    gorro_camino = _texto_seguro(data.get("gorro_camino", ""))
    gorro_colores = _lista_texto_segura(data.get("gorro_colores"))
    gorro_outfit = _texto_seguro(data.get("gorro_outfit", ""))
    gorro_forma = _texto_seguro(data.get("gorro_forma", ""))
    email = _texto_seguro(data.get("email", ""))
    # Solo Koko lo manda, y solo despues de avisar que no habia stock en la
    # talla y que la persona confirmo que igual quiere ver otras tallas
    # (ver KOKO_TOOL_SUGERIR_BUSQUEDA / _sugerencia_disponible_en_talla).
    ignorar_talla = bool(data.get("ignorar_talla"))
    # "Priorizar materiales de calidad" y "Mostrar solo marcas de autor"
    # (2026-08-19): booleanos simples, no necesitan _texto_seguro -- nunca
    # se usan como texto, solo como flags.
    priorizar_material_natural = bool(data.get("priorizar_material_natural"))
    solo_marca_autor = bool(data.get("solo_marca_autor"))

    # Historial para Koko: solo se registra la busqueda primaria (no cada
    # "mostrar mas opciones" de la misma busqueda) y solo modo "yo" -- una
    # busqueda "regalo" es sobre el estilo de otra persona, no del usuario.
    if modo == "yo" and not plan_b:
        registrar_busqueda(email, ocasion, categoria, tipo_prenda, corte)

    catalog = filtrar_por_precio(catalog, precio)
    catalog = filtrar_gorros_por_color(catalog, gorro_camino, gorro_colores, gorro_outfit)
    catalog = filtrar_gorros_por_forma(catalog, gorro_forma)
    catalog = filtrar_por_marca_autor(catalog, solo_marca_autor)

    if modo == "yo":
        perfil = data.get("perfil") or {}
        genero = _texto_seguro(perfil.get("genero"))
        peso = _texto_seguro(perfil.get("peso", ""))
        altura = _texto_seguro(perfil.get("altura", ""))
        hobbies = _lista_texto_segura(perfil.get("hobbie"))
        generos_musicales = _lista_texto_segura(perfil.get("hobbie_musica_genero"))
        deportes_subtipo = _lista_texto_segura(perfil.get("hobbie_deportes_subtipo"))
        # Exclusion suave por hobby (2026-08-20, ver EXCLUSIONES_HOBBY):
        # categorias que claramente no calzan con el hobby quedan al final
        # del orden, nunca ocultas -- reemplaza el enfoque anterior de
        # forzar un corte por defecto (REGLAS_HOBBY sigue existiendo, pero
        # ahora es solo una sugerencia que Koko puede mencionar en la
        # conversacion, ya no cambia el resultado de una busqueda por
        # formulario).
        categorias_deprioritizadas = _categorias_deprioritizadas_por_hobby(
            hobbies, generos_musicales, deportes_subtipo
        )
        campos_pedido = [categoria, tipo_prenda, subtipo, largo, manga, capucha, cierre, corte, ocasion]
        texto_pedido = " ".join([" ".join(hobbies)] + campos_pedido)
    else:
        genero = _texto_seguro(data.get("genero"))
        peso = _texto_seguro(data.get("peso", ""))
        altura = _texto_seguro(data.get("altura", ""))
        categorias_deprioritizadas = set()
        campos_pedido = [categoria, tipo_prenda, subtipo, largo, manga, capucha, cierre, corte, ocasion]
        texto_pedido = " ".join(campos_pedido)

    # Talla: se infiere sola cruzando altura y peso que el usuario ya
    # ingreso -- no se agrega ninguna pregunta nueva de talla.
    tallas_usuario = estimar_tallas(genero, peso, altura)
    catalog_con_talla = catalog if ignorar_talla else filtrar_por_talla(catalog, tallas_usuario)

    if plan_b:
        resultados, alternativas, aviso_alternativas = buscar_plan_b(
            genero, ocasion, categoria, texto_pedido, catalog_con_talla, reglas, tallas_usuario,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas,
        )
    else:
        resultados = armar_resultados(
            genero, ocasion, categoria, texto_pedido, catalog_con_talla, reglas, tallas_usuario,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas,
        )
        alternativas, aviso_alternativas = [], None

    sin_talla = False
    if not resultados and not alternativas and tallas_usuario:
        # Si sin filtrar por talla SI habia resultados, el vacio es
        # especificamente por talla -- avisamos eso en vez de un vacio sin
        # explicacion.
        if plan_b:
            resultados_sin_talla, alternativas_sin_talla, _ = buscar_plan_b(
                genero, ocasion, categoria, texto_pedido, catalog, reglas,
                priorizar_material_natural=priorizar_material_natural,
                categorias_deprioritizadas=categorias_deprioritizadas,
            )
            sin_talla = bool(resultados_sin_talla) or bool(alternativas_sin_talla)
        else:
            resultados_sin_talla = armar_resultados(
                genero, ocasion, categoria, texto_pedido, catalog, reglas,
                priorizar_material_natural=priorizar_material_natural,
                categorias_deprioritizadas=categorias_deprioritizadas,
            )
            sin_talla = bool(resultados_sin_talla)

    return jsonify({
        "recomendaciones": resultados,
        "alternativas": alternativas,
        "aviso_alternativas": aviso_alternativas,
        "sin_talla": sin_talla,
    })


if __name__ == "__main__":
    # host="0.0.0.0": escucha en todas las interfaces de red, no solo en
    # esta compu -- asi el celular (u otro dispositivo en la misma wifi)
    # puede entrar usando la IP local de la compu en vez de 127.0.0.1.
    #
    # debug=True SOLO si se prende a mano con KOLIZION_DEBUG=1 en el .env
    # (desarrollo local, ya configurado asi -- ver .env). El default es
    # SIEMPRE False: si esto se sube a un hosting real y a alguien se le
    # olvida tocar algo, queda seguro solo. El debugger interactivo de
    # Flask (debug=True) deja EJECUTAR CODIGO PYTHON desde el navegador
    # con solo encontrar un error -- y sin el, las paginas de error de
    # Flask son genericas, sin tracebacks ni datos internos.
    modo_debug = os.environ.get("KOLIZION_DEBUG", "").strip() == "1"
    app.run(debug=modo_debug, host="0.0.0.0", port=5000)
