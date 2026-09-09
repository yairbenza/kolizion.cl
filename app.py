import json
import os
import random
import secrets
from datetime import timedelta
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session

# Antes nada cargaba .env cuando se arrancaba con "python app.py" (solo el
# CLI "flask run" lo hace solo) -- por eso FLASK_SECRET_KEY del .env nunca
# se leia de verdad, y app.secret_key caia siempre en el fallback aleatorio
# de mas abajo. Cada reinicio del servidor (cada guardado de archivo con
# KOLIZION_DEBUG=1, cada vez que se cerraba y volvia a abrir) generaba una
# clave NUEVA, invalidando la cookie de sesion de todos -- por eso se
# cerraba la sesion de Google en cada refresh (bug real, 2026-08-27).
# override=False: si la variable ya existe en el entorno real (ej. la puso
# el usuario a mano), esa gana -- .env solo rellena lo que falte.
load_dotenv()

import db_usuarios
from constantes import (
    AJUSTES_TALLA_CONOCIDOS,
    ALIAS_METROPOLITANA,
    BASE_DIR,
    CANTIDAD_RESULTADOS,
    CATALOG_PATH,
    CATEGORIA_GRUPOS,
    CATEGORIAS_CON_GRAMAJE,
    CHATS_KOKO_PATH,
    CIERRES_CONOCIDOS,
    CLICS_TIENDAS_PATH,
    COLORES_CONOCIDOS,
    CORTES_CONOCIDOS,
    DEPORTES_CONOCIDOS,
    ENVIOS_TIENDAS_PATH,
    EXCLUSIONES_HOBBY,
    FAVORITOS_PATH,
    FORMA_GORRO_CONOCIDA,
    FORMAS_GORRO_CONOCIDAS,
    GENEROS_MUSICALES_CONOCIDOS,
    GRAMAJE_MINIMO_CALIDAD_GSM,
    HISTORIAL_PATH,
    HOBBIES_CONOCIDOS,
    LARGO_MAXIMO_MENSAJE_KOKO,
    LARGO_MAXIMO_TEXTO_LIBRE,
    LARGOS_CONOCIDOS,
    LIMITE_KOKO_PATH,
    LIMITE_MENSAJES_KOKO_DIA,
    LIMITES_ALTURA_M,
    LIMITES_PESO_KG,
    MANGAS_CONOCIDAS,
    MATERIALES_CONOCIDOS,
    MAX_MENSAJES_HISTORIAL_KOKO,
    ORDEN_TALLAS,
    PREFERENCIAS_GENERO_CONOCIDAS,
    RANGOS_CLICS,
    REGLAS_HOBBY,
    REGLAS_PATH,
    REGIONES_CHILE,
    REPORTES_MANUALES_PATH,
    SUBTIPOS_CONOCIDOS,
    SUBTIPOS_POR_TIPO_PRENDA,
    TIENDAS_PATH,
    TIPO_PRENDA_A_CATEGORIA_GRUPO,
    TIPOS_CON_LARGO,
    TIPOS_PRENDA_CONOCIDOS,
    VENTANA_CONFIRMACION_TIPO_PRENDA_KOKO,
    _contiene_palabra,
    _detectar,
    _detectar_reciente,
    _es_safari,
    _lista_texto_segura,
    _mencionado_en_conversacion,
    _normalizar_email,
    _parsear_fecha_iso,
    _quitar_tildes,
    _siguiente_seguro,
    _texto_seguro,
    _valor_o_deteccion,
    load_json,
    tokenizar,
)
from extensions import limiter
from motor_recomendacion import (
    _algodon_buena_calidad,
    _categorias_deprioritizadas_por_hobby,
    _completar_con_alternativas_de_corte,
    _limites,
    _material_es_natural,
    _parsear_altura_m,
    _parsear_numero,
    _reglas_hobby_usuario,
    _subtipos_validos_para,
    _talla_por_valor,
    _talla_vecina,
    _texto_gramaje,
    armar_resultados,
    buscar_plan_b,
    buscar_regla,
    detectar_capucha_pedido,
    detectar_cierre_pedido,
    detectar_color_pedido_conversacion,
    detectar_corte_pedido,
    detectar_corte_pedido_conversacion,
    detectar_forma_gorro,
    detectar_forma_gorro_conversacion,
    detectar_largo_pedido,
    detectar_manga_pedido,
    detectar_subtipo_pedido,
    detectar_subtipo_pedido_conversacion,
    detectar_tipo_prenda,
    detectar_tipo_prenda_conversacion,
    elegir_candidatos,
    estimar_tallas,
    tiene_stock,
    filtrar_gorros_por_forma_con_aviso,
    filtrar_por_exclusiones,
    filtrar_por_marca_autor,
    filtrar_por_preferencias_negativas,
    filtrar_por_precio,
    filtrar_por_talla,
    formatear_producto,
    texto_producto,
)
from rutas_admin import (
    ADMIN_PASSWORD,
    admin_bp,
    requiere_admin,
)
from rutas_auth import (
    FOTOS_USUARIOS_DIR,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    _EXTENSIONES_FOTO_PERMITIDAS,
    _google_intercambiar_code,
    _iniciar_sesion_usuario,
    _perfil_desde_formulario,
    auth_bp,
    requiere_cuenta,
)
from servicio_koko import (
    KOKO_SYSTEM_PROMPT_BASE,
    KOKO_TOOL_SUGERIR_BUSQUEDA,
    _bloque_hobbies_para_prompt,
    _resumen_favoritos_para_prompt,
    _resumen_perfil_para_prompt,
    _sugerencia_calza_con_catalogo,
    _sugerencia_candidatos_catalogo,
    _sugerencia_disponible_en_talla,
    _texto_reglas_para_prompt,
    cargar_chats_koko,
    cargar_historial_chat,
    cargar_limite_koko,
    construir_system_prompt_koko,
    guardar_chats_koko,
    guardar_limite_koko,
    guardar_mensaje_chat,
    mensajes_usuario_ultimas_24h,
    preferencia_idioma_koko,
    registrar_mensaje_usuario_koko,
    reiniciar_chat_koko,
    resumen_historial_para_prompt,
)
from servicio_stock_live import (
    aplicar_overlay as _aplicar_overlay_stock_live,
    guardar_resultado_verificacion as _guardar_resultado_verificacion_stock_live,
    iniciar_refresco_en_segundo_plano as _iniciar_refresco_stock_live,
    verificar_stock_producto,
)
from servicio_tiendas import (
    _armar_basado_en_busquedas,
    _armar_tendencias,
    _clics_por_producto,
    _dias_habiles_a_numero,
    _estimar_envio_real,
    _fecha_clic,
    alternar_favorito,
    cargar_clics_tiendas,
    cargar_envios_tiendas,
    cargar_favoritos,
    cargar_historial,
    cargar_reportes_manuales,
    cargar_tiendas,
    guardar_favoritos,
    guardar_historial,
    guardar_tiendas,
    obtener_favoritos,
    registrar_busqueda,
    registrar_clic_tienda,
    registrar_interes,
    registrar_reporte_manual,
    resumen_envio_general,
    resumen_resenas,
    vaciar_favoritos,
)

app = Flask(__name__)
limiter.init_app(app)


@app.errorhandler(429)
def limite_de_peticiones_excedido(error):
    mensaje = "Demasiadas peticiones seguidas -- espera un minuto e intenta de nuevo."
    if request.path.startswith("/api/"):
        return jsonify({"error": mensaje}), 429
    return mensaje, 429


def _cargar_env_local():
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

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
MODO_DEBUG = os.environ.get("KOLIZION_DEBUG", "").strip() == "1"

app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

# Refresco de stock en vivo en segundo plano (2026-09-07, pedido del
# usuario): cada 20 min (punto medio de "15-30 min" que eligio) recorre las
# tiendas Shopify (la gran mayoria del catalogo) y actualiza data/
# stock_live.json -- ver servicio_stock_live.py para el detalle completo de
# que plataformas se pueden verificar en vivo hoy y cuales no. Guard contra
# el reloader de Flask (solo con KOLIZION_DEBUG=1): sin esto, el proceso
# "lanzador" del modo debug tambien arrancaria su propio hilo ademas del
# proceso real que sirve las requests -- 2 refrescos duplicados en paralelo.
if not MODO_DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    _iniciar_refresco_stock_live(CATALOG_PATH)


def cargar_catalog_con_stock_live():
    """load_json(CATALOG_PATH) + la capa de stock en vivo aprendida (ver
    servicio_stock_live.py) -- nunca modifica catalog.json, solo ajusta la
    copia en memoria de esta request. Punto central: cualquier ruta que use
    esto ya queda al dia sin tener que tocar cada llamador por separado."""
    return _aplicar_overlay_stock_live(load_json(CATALOG_PATH))


app.permanent_session_lifetime = timedelta(days=30)
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024  # 3 MB
# Cookie de sesion solo por HTTPS en produccion (en debug/local, que corre
# por http://, exigir "secure" haria que la cookie nunca se mande y el login
# no funcionara nunca).
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = not MODO_DEBUG


@app.after_request
def _agregar_headers_seguridad(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not MODO_DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

db_usuarios.inicializar_db()

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)


# El icono de "Mi cuenta" (avatar fijo arriba, ver _barra_cuenta.html) esta
# en TODAS las paginas, asi que "usuario" tiene que estar disponible en
# cualquier template sin que cada ruta lo pase a mano -- un solo lookup por
# request en vez de repetirlo en index()/resultados()/vitrina()/etc.
@app.context_processor
def _inyectar_usuario_sesion():
    usuario = None
    if session.get("usuario_id"):
        usuario = db_usuarios.buscar_por_id(session["usuario_id"])
    return {"usuario": usuario}


# --- Vistas HTML -------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/resultados")
def resultados():
    return render_template("resultados.html")


@app.route("/vitrina")
def vitrina():
    return render_template("vitrina.html")


def _email_sesion_actual():
    # Email de la cuenta REAL con sesion iniciada (Google OAuth o
    # email/contraseña, ver docs/cuentas.md) -- a diferencia del "perfil"
    # de localStorage (un dato que la persona escribe a mano y que
    # cualquiera podria mandar en el body de una request), esto sale del
    # lado del servidor (session["usuario_id"]), asi que es confiable para
    # decidir de quien es un dato guardado. None si no hay sesion.
    if not session.get("usuario_id"):
        return None
    usuario = db_usuarios.buscar_por_id(session["usuario_id"])
    return usuario["email"] if usuario else None


@app.route("/perfil")
def perfil():
    return render_template("perfil.html")


@app.route("/favoritos")
def favoritos():
    return render_template("favoritos.html")


@app.route("/tienda/<tienda_id>")
def tienda_perfil(tienda_id):
    tienda = cargar_tiendas().get(tienda_id)
    if not tienda:
        return redirect("/vitrina")
    return render_template("tienda_perfil.html", tienda_id=tienda_id, tienda=tienda)


@app.route("/ir/<tienda_id>")
@requiere_cuenta
def ir_a_tienda_general(tienda_id):
    tienda = cargar_tiendas().get(tienda_id)
    if not tienda or tienda.get("tipo") != "con_sitio_web":
        return redirect("/")
    registrar_clic_tienda(tienda_id, "(visita general)")
    url_destino = f'https://{tienda["dominio"]}/discount/{tienda["codigo_descuento"]}'
    return redirect(url_destino)


@app.route("/ir/<tienda_id>/<path:producto>")
@requiere_cuenta
def ir_a_tienda(tienda_id, producto):
    tienda = cargar_tiendas().get(tienda_id)
    if not tienda or tienda.get("tipo") != "con_sitio_web":
        return redirect("/")
    registrar_clic_tienda(tienda_id, producto)
    url_destino = f'https://{tienda["dominio"]}/discount/{tienda["codigo_descuento"]}?redirect=/products/{producto}'
    return redirect(url_destino)


@app.route("/sw.js")
def service_worker():
    resp = app.send_static_file("sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


# --- Endpoints API -----------------------------------------------------------

@app.route("/api/vitrina")
def api_vitrina():
    # 2026-08-30, pedido del usuario: Descubre no debe mostrar prendas
    # agotadas (mismo criterio que decide "Agregar al carrito" vs
    # "Proximamente" en la ficha, ver tiene_stock()).
    catalog = [p for p in cargar_catalog_con_stock_live() if tiene_stock(p)]

    # 2026-08-31, pedido del usuario: Descubre tampoco respetaba "Excluir
    # caracteristicas" (texto grande/grafico grande/cara-logo gigante/rotos)
    # -- esas preferencias viven en localStorage del navegador, no en el
    # perfil del servidor, asi que el frontend las manda como query param
    # (ver vitrina.js). Si viene vacio o mal formado, no se excluye nada
    # (mismo comportamiento que /api/recommend sin preferencias).
    try:
        prefs_vitrina = json.loads(request.args.get("prefs") or "{}")
    except (TypeError, ValueError):
        prefs_vitrina = {}
    if isinstance(prefs_vitrina, dict):
        catalog = filtrar_por_preferencias_negativas(catalog, prefs_vitrina)

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

    # "Basado en tus ultimas busquedas" (2026-08-30, pedido del usuario):
    # solo para cuentas con sesion real -- el historial de busquedas no se
    # guarda para invitados (ver _email_sesion_actual), asi que para ellos
    # esta lista siempre queda vacia y el frontend no muestra la fila.
    resto = [p for p in resto if p["id"] not in ids_usados]
    email_sesion = _email_sesion_actual()
    basado_busquedas = (
        _armar_basado_en_busquedas(email_sesion, resto, load_json(REGLAS_PATH), cantidad)
        if email_sesion else []
    )
    ids_usados |= {p["id"] for p in basado_busquedas}

    resto = [p for p in resto if p["id"] not in ids_usados]
    lanzamientos = random.sample(resto, min(cantidad, len(resto)))
    ids_usados |= {p["id"] for p in lanzamientos}

    resto = [p for p in resto if p["id"] not in ids_usados]
    destacados = random.sample(resto, min(cantidad, len(resto)))

    return jsonify({
        "tendencias": [formatear_producto(p, razon) for p, razon in tendencias_con_razon],
        "basado_busquedas": [
            formatear_producto(p, "Basado en tu búsqueda reciente") for p in basado_busquedas
        ],
        "lanzamientos": [formatear_producto(p, "Recién llegado a KOLIZION") for p in lanzamientos],
        "ofertas": [
            formatear_producto(p, f'-{p["descuento_pct"]}% sobre el precio normal')
            for p in catalogo_ofertas
        ],
        "destacados": [formatear_producto(p, "Producto destacado") for p in destacados],
    })


@app.route("/api/tiendas_rapido")
def api_tiendas_rapido():
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
    filas.sort(key=lambda f: (not f["envio_tiene_dato"], f["envio_dias"]))
    return jsonify({"tiendas": filas, "direccion_configurada": bool(direccion)})


@app.route("/api/estimar_talla")
def api_estimar_talla():
    genero = _texto_seguro(request.args.get("genero", ""))
    peso = _texto_seguro(request.args.get("peso", ""))
    altura = _texto_seguro(request.args.get("altura", ""))
    ajuste_talla = _texto_seguro(request.args.get("ajuste_talla", "")).strip().lower()
    if ajuste_talla not in AJUSTES_TALLA_CONOCIDOS:
        ajuste_talla = "normal"
    return jsonify({"tallas": estimar_tallas(genero, peso, altura, ajuste_talla)})


@app.route("/api/verificar_stock", methods=["POST"])
@limiter.limit("30 per minute")
def api_verificar_stock():
    """Revalidacion en vivo al momento de "Agregar al carrito" (2026-09-07,
    pedido del usuario) -- consulta la ficha real de la tienda (ver
    servicio_stock_live.py: Shopify via <link>.js, IPREX via JSON-LD, ZAMU
    via WooCommerce Store API; el resto de las plataformas todavia no tiene
    una fuente publica verificada, asi que sigue con el dato de catalog.json
    sin bloquear la compra).
    Lo que se aprenda aca se guarda en el overlay compartido -- otros
    usuarios que busquen este mismo producto despues ya ven el dato
    actualizado, sin tener que volver a consultarlo (pedido del usuario:
    reducir verificaciones repetidas)."""
    data = request.get_json() or {}
    producto_id = _texto_seguro(data.get("producto_id", ""), 80)
    talla_pedida = _texto_seguro(data.get("talla", ""), 20).strip().upper()
    if not producto_id:
        return jsonify({"verificado": False}), 400

    catalog = load_json(CATALOG_PATH)
    producto = next((p for p in catalog if p["id"] == producto_id), None)
    if not producto:
        return jsonify({"verificado": False}), 404

    resultado = verificar_stock_producto(producto)
    if resultado["fuente"] is None:
        return jsonify({"verificado": False})

    _guardar_resultado_verificacion_stock_live(producto_id, resultado)

    if resultado["variantes"] is not None:
        disponible = any(
            v["talla"].strip().upper() == talla_pedida and v["disponible"]
            for v in resultado["variantes"]
        )
        return jsonify({
            "verificado": True,
            "disponible": disponible,
            "talla_confirmada": True,
            "tallas_variantes": resultado["variantes"],
            "tallas_disponibles": [v["talla"] for v in resultado["variantes"] if v["disponible"]],
        })

    # Solo se supo disponibilidad del producto COMPLETO (ej. IPREX, que no
    # separa stock por talla) -- si esta agotado, aplica igual a la talla
    # pedida (no hay ninguna talla disponible si no queda nada); si SI tiene
    # stock, no se puede confirmar la talla puntual, se avisa asi.
    disponible_general = bool(resultado["disponible_general"])
    return jsonify({
        "verificado": True,
        "disponible": disponible_general,
        "talla_confirmada": False,
    })


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


@app.route("/api/resenas", methods=["GET"])
def api_resenas():
    nombre = _texto_seguro(request.args.get("nombre", ""))
    return jsonify(resumen_resenas(nombre))


@app.route("/api/envio_tienda", methods=["GET"])
def api_envio_tienda():
    tienda = _texto_seguro(request.args.get("tienda", ""))
    return jsonify({"texto": resumen_envio_general(tienda)})


@app.route("/api/recommend", methods=["POST"])
@limiter.limit("20 per minute")
def recommend():
    data = request.get_json() or {}
    catalog = cargar_catalog_con_stock_live()
    reglas = load_json(REGLAS_PATH)
    modo = data.get("modo")
    plan_b = bool(data.get("plan_b"))

    categoria = _texto_seguro(data.get("categoria", ""))
    tipo_prenda = _texto_seguro(data.get("tipo_prenda", ""))
    subtipo = _texto_seguro(data.get("subtipo", ""))
    largo = _texto_seguro(data.get("largo", ""))
    manga = _texto_seguro(data.get("manga", ""))
    capucha = _texto_seguro(data.get("capucha", ""))
    cierre = _texto_seguro(data.get("cierre", ""))
    corte = _texto_seguro(data.get("corte", ""))
    # El buscador normal manda "colores" (checkboxes, hasta 3). Koko sigue
    # mandando "color" en singular (un solo campo en su tool) -- se acepta
    # cualquiera de los 2 y se juntan en una sola lista (pedido del usuario,
    # 2026-08-27: poder elegir hasta 3 colores en la busqueda).
    colores = [c.lower() for c in _lista_texto_segura(data.get("colores"), cantidad_max=3)]
    color_unico = _texto_seguro(data.get("color", "")).lower()
    if color_unico:
        colores.append(color_unico)
    colores = list(dict.fromkeys(c for c in colores if c in COLORES_CONOCIDOS))[:3]
    ocasion = _texto_seguro(data.get("ocasion", ""))
    precio = _texto_seguro(data.get("precio", ""))
    gorro_forma = _texto_seguro(data.get("gorro_forma", ""))
    ignorar_talla = bool(data.get("ignorar_talla"))
    priorizar_material_natural = bool(data.get("priorizar_material_natural"))
    solo_marca_autor = bool(data.get("solo_marca_autor"))
    excluir = _lista_texto_segura(data.get("excluir"))
    ids_excluir = set(_lista_texto_segura(data.get("ids_excluir"), largo_max_item=40, cantidad_max=200))

    # "_historial_replay" (2026-08-28, pedido del usuario): lo manda el
    # boton "Ver estos resultados de nuevo" del historial en /perfil al
    # volver a correr una busqueda ya guardada -- si se registrara de nuevo,
    # cada vez que alguien vuelve a mirar un resultado viejo se le sumaria
    # una entrada duplicada en su propio historial.
    if modo == "yo" and not plan_b and not data.get("_historial_replay"):
        # El historial visible en /perfil (2026-08-26, pedido del usuario)
        # solo debe contar busquedas hechas con sesion REAL iniciada -- ya
        # no se usa el email que manda el cliente (perfil de localStorage,
        # no verificado). Sin sesion, simplemente no se guarda nada.
        email_sesion = _email_sesion_actual()
        if email_sesion:
            payload_reproducible = {
                "modo": "yo",
                "perfil": data.get("perfil") or {},
                "categoria": categoria,
                "tipo_prenda": tipo_prenda,
                "subtipo": subtipo,
                "largo": largo,
                "manga": manga,
                "capucha": capucha,
                "cierre": cierre,
                "corte": corte,
                "colores": colores,
                "ocasion": ocasion,
                "precio": precio,
                "gorro_forma": gorro_forma,
                "ignorar_talla": ignorar_talla,
                "priorizar_material_natural": priorizar_material_natural,
                "solo_marca_autor": solo_marca_autor,
                "excluir": excluir,
            }
            registrar_busqueda(email_sesion, ocasion, categoria, tipo_prenda, corte, payload=payload_reproducible)

    catalog, aviso_gorro_forma = filtrar_gorros_por_forma_con_aviso(catalog, gorro_forma)
    catalog = filtrar_por_marca_autor(catalog, solo_marca_autor)
    catalog = filtrar_por_exclusiones(catalog, excluir)

    # "Relajar por esta vez" (2026-08-30, pedido del usuario): cuando una
    # busqueda con preferencias negativas activas da 0 resultados, el
    # frontend pregunta si buscar igual incluyendo esas opciones -- si el
    # usuario dice que si, reenvia la MISMA busqueda agregando la clave que
    # quiere relajar en esta lista. Solo afecta esta llamada puntual: nunca
    # se toca data.preferencias_negativas ni lo guardado en el perfil.
    preferencias_negativas = (data.get("preferencias_negativas") or {}) if modo == "yo" else {}
    if not isinstance(preferencias_negativas, dict):
        preferencias_negativas = {}
    relajar_ahora = set(_lista_texto_segura(data.get("relajar_preferencias_negativas")))
    catalog_antes_de_prefs = catalog
    prefs_efectivas = {k: (bool(v) and k not in relajar_ahora) for k, v in preferencias_negativas.items()}
    if modo == "yo":
        catalog = filtrar_por_preferencias_negativas(catalog, prefs_efectivas)

    # Preferencia de calce del perfil (2026-09-07, pedido del usuario): "Como
    # prefieres que te quede la ropa" -- Ajustado/Normal/Holgado, se guarda en
    # /perfil (ver perfil.js) y solo aplica a busquedas "yo" (en "regalo" no
    # hay perfil personal guardado). Cualquier valor que no sea uno de los 3
    # conocidos cae a "normal" (el calculo de siempre, sin desplazar nada).
    ajuste_talla = _texto_seguro(data.get("ajuste_talla", "")).strip().lower() if modo == "yo" else "normal"
    if ajuste_talla not in AJUSTES_TALLA_CONOCIDOS:
        ajuste_talla = "normal"

    # Preferencia de genero del perfil (2026-09-08, pedido del usuario):
    # "con_unisex" (default)/"solo_mi_genero"/"todos" -- solo aplica a "yo"
    # (en "regalo" no hay perfil personal guardado). Ver elegir_candidatos()
    # en motor_recomendacion.py para el detalle de que cambia cada opcion.
    preferencia_genero = (
        _texto_seguro(data.get("preferencia_genero", "")).strip().lower() if modo == "yo" else "con_unisex"
    )
    if preferencia_genero not in PREFERENCIAS_GENERO_CONOCIDAS:
        preferencia_genero = "con_unisex"

    if modo == "yo":
        perfil = data.get("perfil") or {}
        genero = _texto_seguro(perfil.get("genero"))
        peso = _texto_seguro(perfil.get("peso", ""))
        altura = _texto_seguro(perfil.get("altura", ""))
        hobbies = _lista_texto_segura(perfil.get("hobbie"))
        generos_musicales = _lista_texto_segura(perfil.get("hobbie_musica_genero"))
        deportes_subtipo = _lista_texto_segura(perfil.get("hobbie_deportes_subtipo"))
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

    tallas_usuario = estimar_tallas(genero, peso, altura, ajuste_talla)
    catalog_con_talla = catalog if ignorar_talla else filtrar_por_talla(catalog, tallas_usuario)

    if plan_b:
        resultados, alternativas, aviso_alternativas = buscar_plan_b(
            genero, ocasion, categoria, texto_pedido, catalog_con_talla, reglas, tallas_usuario,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=colores,
            precio_pedido=precio, ids_excluir=ids_excluir, preferencia_genero=preferencia_genero,
        )
    else:
        catalog_con_precio = filtrar_por_precio(catalog_con_talla, precio)
        resultados = armar_resultados(
            genero, ocasion, categoria, texto_pedido, catalog_con_precio, reglas, tallas_usuario,
            priorizar_material_natural=priorizar_material_natural,
            categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=colores,
            preferencia_genero=preferencia_genero,
        )
        alternativas, aviso_alternativas = [], None

    sin_talla = False
    if not resultados and not alternativas and tallas_usuario:
        if plan_b:
            resultados_sin_talla, alternativas_sin_talla, _ = buscar_plan_b(
                genero, ocasion, categoria, texto_pedido, catalog, reglas,
                priorizar_material_natural=priorizar_material_natural,
                categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=colores,
                precio_pedido=precio, ids_excluir=ids_excluir, preferencia_genero=preferencia_genero,
            )
            sin_talla = bool(resultados_sin_talla) or bool(alternativas_sin_talla)
        else:
            resultados_sin_talla = armar_resultados(
                genero, ocasion, categoria, texto_pedido, filtrar_por_precio(catalog, precio), reglas,
                priorizar_material_natural=priorizar_material_natural,
                categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=colores,
                preferencia_genero=preferencia_genero,
            )
            sin_talla = bool(resultados_sin_talla)

    # Si quedo en 0 resultados y el usuario tiene preferencias negativas
    # activas, revisamos (reusando la misma logica de filtro, solo que con
    # cada clave apagada de a una) cual de ellas es realmente la que esta
    # bloqueando -- para poder preguntarle exactamente por esa, en vez de
    # ofrecer relajar algo que no tenia nada que ver.
    preferencias_bloqueantes = []
    activas = [k for k, v in preferencias_negativas.items() if v and k not in relajar_ahora]
    if modo == "yo" and activas and not resultados and not alternativas:
        def _hay_resultados_con(prefs_prueba):
            catalog_prueba = filtrar_por_preferencias_negativas(catalog_antes_de_prefs, prefs_prueba)
            catalog_prueba = catalog_prueba if ignorar_talla else filtrar_por_talla(catalog_prueba, tallas_usuario)
            if plan_b:
                r, a, _ = buscar_plan_b(
                    genero, ocasion, categoria, texto_pedido, catalog_prueba, reglas, tallas_usuario,
                    priorizar_material_natural=priorizar_material_natural,
                    categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=colores,
                    precio_pedido=precio, ids_excluir=ids_excluir, preferencia_genero=preferencia_genero,
                )
                return bool(r) or bool(a)
            r = armar_resultados(
                genero, ocasion, categoria, texto_pedido, filtrar_por_precio(catalog_prueba, precio), reglas,
                tallas_usuario, priorizar_material_natural=priorizar_material_natural,
                categorias_deprioritizadas=categorias_deprioritizadas, color_pedido=colores,
                preferencia_genero=preferencia_genero,
            )
            return bool(r)

        for clave in activas:
            prueba = dict(prefs_efectivas)
            prueba[clave] = False
            if _hay_resultados_con(prueba):
                preferencias_bloqueantes.append(clave)

        if not preferencias_bloqueantes and len(activas) > 1:
            prueba_todas = {k: False for k in prefs_efectivas}
            if _hay_resultados_con(prueba_todas):
                preferencias_bloqueantes = list(activas)

    return jsonify({
        "recomendaciones": resultados,
        "alternativas": alternativas,
        "aviso_alternativas": aviso_alternativas,
        "sin_talla": sin_talla,
        "preferencias_bloqueantes": preferencias_bloqueantes,
        "aviso_gorro_forma": aviso_gorro_forma,
    })


@app.route("/api/historial")
def api_historial():
    # "Ver historial" en Mi perfil (2026-08-26, pedido del usuario) -- solo
    # visible con sesion REAL iniciada (nunca por un email que mande el
    # cliente en la URL, cualquiera podria pedir el de otra persona). Mas
    # reciente primero.
    email_sesion = _email_sesion_actual()
    if not email_sesion:
        return jsonify({"logged_in": False, "busquedas": [], "productos_interes": []})
    entrada = cargar_historial().get(_normalizar_email(email_sesion), {})
    return jsonify({
        "logged_in": True,
        "busquedas": list(reversed(entrada.get("busquedas", []))),
        "productos_interes": list(reversed(entrada.get("productos_interes", []))),
    })


# --- Endpoints Koko ----------------------------------------------------------

@app.route("/api/koko/historial_chat")
def koko_historial_chat():
    # Si hay sesion real, manda ese correo siempre -- nunca el que mande el
    # navegador en la URL (alguien logueado no puede pedir el chat de otra
    # persona logueada). Sin sesion (invitado sin cuenta), sigue igual que
    # antes: usa el correo que mande el cliente (riesgo ya conocido y
    # aceptado en toda la app, ver docs/cuentas.md).
    email = _email_sesion_actual() or _texto_seguro(request.args.get("email", ""))
    return jsonify({
        "mensajes": cargar_historial_chat(email),
        "preferencia_idioma": preferencia_idioma_koko(email),
    })


@app.route("/api/koko/reiniciar", methods=["POST"])
def koko_reiniciar():
    data = request.get_json() or {}
    # Mismo criterio que koko_historial_chat: con sesion real, ese correo
    # manda siempre; sin sesion, se respeta el correo del invitado.
    email = _email_sesion_actual() or _texto_seguro(data.get("email", ""))
    reiniciar_chat_koko(email)
    return jsonify({"ok": True})


@app.route("/api/koko/interes", methods=["POST"])
def koko_interes():
    data = request.get_json() or {}
    producto = data.get("producto") or {}
    if not isinstance(producto, dict):
        producto = {}
    # Mismo criterio que registrar_busqueda: solo cuenta para el historial
    # si hay sesion real iniciada (ver _email_sesion_actual).
    email_sesion = _email_sesion_actual()
    if email_sesion:
        registrar_interes(email_sesion, producto)
    return jsonify({"ok": True})


@app.route("/api/koko/chat", methods=["POST"])
@limiter.limit("10 per minute")
def koko_chat():
    data = request.get_json() or {}
    # Mismo criterio que koko_historial_chat: con sesion real, ese correo
    # manda siempre (nunca el que mande el navegador en el body); sin
    # sesion, se respeta el correo del invitado (riesgo ya conocido y
    # aceptado en toda la app, no exclusivo de Koko -- ver docs/cuentas.md).
    email = _email_sesion_actual() or _texto_seguro(data.get("email", ""))
    perfil = data.get("perfil") or {}
    if not isinstance(perfil, dict):
        perfil = {}
    hobbies = _lista_texto_segura(perfil.get("hobbie"))
    generos_musicales = _lista_texto_segura(perfil.get("hobbie_musica_genero"))
    deportes_subtipo = _lista_texto_segura(perfil.get("hobbie_deportes_subtipo"))
    tallas_usuario = estimar_tallas(
        _texto_seguro(perfil.get("genero")), _texto_seguro(perfil.get("peso", "")), _texto_seguro(perfil.get("altura", "")),
    )
    mensajes = data.get("mensajes") or []
    if not isinstance(mensajes, list):
        mensajes = []
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

    ultimo_mensaje_usuario = (
        mensajes_api[-1]["content"] if mensajes_api[-1]["role"] == "user" else ""
    )

    if mensajes_usuario_ultimas_24h(email) >= LIMITE_MENSAJES_KOKO_DIA:
        respuesta_texto = (
            "Guau, llegaste al límite de mensajes de hoy con Koko 🐶 -- vuelve mañana para seguir la charla."
        )
        guardar_mensaje_chat(email, "usuario", ultimo_mensaje_usuario)
        guardar_mensaje_chat(email, "koko", respuesta_texto)
        return jsonify({"respuesta_texto": respuesta_texto, "sugerencia": None, "limite_alcanzado": True})

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        respuesta_texto = (
            "Guau... todavia no puedo responder: falta configurar la clave de la API de Anthropic "
            "en el servidor. Avisale al dueno del proyecto."
        )
        guardar_mensaje_chat(email, "usuario", ultimo_mensaje_usuario)
        guardar_mensaje_chat(email, "koko", respuesta_texto)
        return jsonify({"respuesta_texto": respuesta_texto, "sugerencia": None})

    registrar_mensaje_usuario_koko(email)

    reglas = load_json(REGLAS_PATH)
    system_prompt = construir_system_prompt_koko(
        email, reglas, hobbies, generos_musicales, deportes_subtipo, perfil=perfil, tallas_usuario=tallas_usuario,
        mensaje_usuario=ultimo_mensaje_usuario,
    )

    cliente = anthropic.Anthropic(api_key=api_key)
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

    if sugerencia is not None:
        textos_mensajes = [m["content"] for m in mensajes_api]
        tipo_prenda_detectado = _valor_o_deteccion(
            sugerencia.get("tipo_prenda"), TIPOS_PRENDA_CONOCIDOS, textos_mensajes,
            detectar_tipo_prenda_conversacion,
            mensajes_confirmacion=textos_mensajes[-VENTANA_CONFIRMACION_TIPO_PRENDA_KOKO:],
            solo_mensaje_mas_reciente=True,
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
            color_detectado = _valor_o_deteccion(
                sugerencia.get("color"), COLORES_CONOCIDOS, textos_mensajes,
                detectar_color_pedido_conversacion,
            )
            if color_detectado:
                sugerencia["color"] = color_detectado
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
                    lambda msgs: detectar_subtipo_pedido_conversacion(msgs, tipo_prenda_detectado),
                )
                if subtipo_detectado:
                    sugerencia["subtipo"] = subtipo_detectado

            if not _sugerencia_calza_con_catalogo(sugerencia):
                sugerencia = None
                texto_partes = [
                    "Mmm, no encontré nada que calce bien con eso en el catálogo todavía. "
                    "¿Quieres que ajustemos la búsqueda? Puedo probar con otro corte, otro tipo de "
                    "prenda, o lo que prefieras."
                ]
            elif tallas_usuario and not sugerencia.get("ignorar_talla") and not _sugerencia_disponible_en_talla(sugerencia, tallas_usuario):
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


if __name__ == "__main__":
    app.run(debug=MODO_DEBUG, host="0.0.0.0", port=5000)
