import os
import random
import secrets
from datetime import timedelta
from pathlib import Path

import anthropic
from flask import Flask, jsonify, redirect, render_template, request, session

import db_usuarios
from constantes import (
    ALIAS_METROPOLITANA,
    BASE_DIR,
    CANTIDAD_RESULTADOS,
    CATALOG_PATH,
    CATEGORIA_GRUPOS,
    CATEGORIAS_CON_GRAMAJE,
    CHATS_KOKO_PATH,
    CIERRES_CONOCIDOS,
    CLICS_TIENDAS_PATH,
    COLORES_GORRO_CONOCIDOS,
    COLORES_VIVOS_GORRO,
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
    colores_permitidos_por_outfit,
    detectar_capucha_pedido,
    detectar_cierre_pedido,
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
    filtrar_gorros_por_color,
    filtrar_gorros_por_forma,
    filtrar_por_marca_autor,
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
from servicio_tiendas import (
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

app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(days=30)
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024  # 3 MB

db_usuarios.inicializar_db()

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)


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


@app.route("/perfil")
def perfil():
    usuario = None
    if session.get("usuario_id"):
        usuario = db_usuarios.buscar_por_id(session["usuario_id"])
    return render_template("perfil.html", usuario=usuario)


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
    return jsonify({"tallas": estimar_tallas(genero, peso, altura)})


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


@app.route("/api/recommend", methods=["POST"])
@limiter.limit("20 per minute")
def recommend():
    data = request.get_json() or {}
    catalog = load_json(CATALOG_PATH)
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
    ocasion = _texto_seguro(data.get("ocasion", ""))
    precio = _texto_seguro(data.get("precio", ""))
    gorro_camino = _texto_seguro(data.get("gorro_camino", ""))
    gorro_colores = _lista_texto_segura(data.get("gorro_colores"))
    gorro_outfit = _texto_seguro(data.get("gorro_outfit", ""))
    gorro_forma = _texto_seguro(data.get("gorro_forma", ""))
    email = _texto_seguro(data.get("email", ""))
    ignorar_talla = bool(data.get("ignorar_talla"))
    priorizar_material_natural = bool(data.get("priorizar_material_natural"))
    solo_marca_autor = bool(data.get("solo_marca_autor"))

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


# --- Endpoints Koko ----------------------------------------------------------

@app.route("/api/koko/historial_chat")
def koko_historial_chat():
    email = _texto_seguro(request.args.get("email", ""))
    return jsonify({
        "mensajes": cargar_historial_chat(email),
        "preferencia_idioma": preferencia_idioma_koko(email),
    })


@app.route("/api/koko/reiniciar", methods=["POST"])
def koko_reiniciar():
    data = request.get_json() or {}
    email = _texto_seguro(data.get("email", ""))
    reiniciar_chat_koko(email)
    return jsonify({"ok": True})


@app.route("/api/koko/interes", methods=["POST"])
def koko_interes():
    data = request.get_json() or {}
    email = _texto_seguro(data.get("email", ""))
    producto = data.get("producto") or {}
    if not isinstance(producto, dict):
        producto = {}
    registrar_interes(email, producto)
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
    modo_debug = os.environ.get("KOLIZION_DEBUG", "").strip() == "1"
    app.run(debug=modo_debug, host="0.0.0.0", port=5000)
