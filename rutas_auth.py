import io
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from functools import wraps
from pathlib import Path

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import db_usuarios
from constantes import (
    BASE_DIR,
    _es_safari,
    _lista_texto_segura,
    _siguiente_seguro,
    _texto_seguro,
)
from extensions import limiter
from motor_recomendacion import _parsear_altura_m, _parsear_numero

auth_bp = Blueprint("auth_bp", __name__)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

_EXTENSIONES_FOTO_PERMITIDAS = {"jpg", "jpeg", "png", "webp"}
_FORMATOS_FOTO = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}
FOTOS_USUARIOS_DIR = BASE_DIR / "static" / "img" / "usuarios"


def requiere_cuenta(vista):
    """Decorator para las rutas que exigen una cuenta real (hoy: los 2
    puntos de 'comprar', /ir/<tienda_id> y /ir/<tienda_id>/<producto>) --
    calco exacto de requiere_admin, pero para session['usuario_id'] en vez
    de session['admin_autenticado']. Ver docs/cuentas.md."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get("usuario_id"):
            return redirect(f"/login?siguiente={_siguiente_seguro(request.full_path.rstrip('?'))}")
        return vista(*args, **kwargs)
    return envoltura


def _perfil_desde_formulario(form):
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
    session.permanent = bool(recordar) and not _es_safari(request.user_agent.string)
    session["usuario_id"] = usuario["id"]


def _google_intercambiar_code(code):
    datos_token = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": url_for("auth_bp.auth_google_callback", _external=True),
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


@auth_bp.route("/registro", methods=["GET", "POST"])
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


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("6 per minute, 20 per hour", methods=["POST"])
def login():
    error = None
    siguiente = _siguiente_seguro(request.args.get("siguiente") or request.form.get("siguiente"))

    if request.method == "POST":
        email = _texto_seguro(request.form.get("email", ""), 200)
        password = request.form.get("password", "")
        usuario = db_usuarios.buscar_por_email(email)
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


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("usuario_id", None)
    return redirect("/")


@auth_bp.route("/auth/google/iniciar", methods=["POST"])
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
    session["recordar_pendiente"] = bool(datos.get("recordar"))
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
        "redirect_uri": url_for("auth_bp.auth_google_callback", _external=True),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    url_consentimiento = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(parametros)
    return jsonify({"url": url_consentimiento})


@auth_bp.route("/auth/google/callback", endpoint="auth_google_callback")
def auth_google_callback():
    siguiente = session.pop("auth_siguiente", None) or "/"
    perfil_pendiente = session.pop("perfil_pendiente_migracion", None) or {}
    email_pendiente = session.pop("email_pendiente_migracion", "")
    recordar = session.pop("recordar_pendiente", True)
    state_esperado = session.pop("oauth_state", None)

    if request.args.get("error"):
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
        email_existente = db_usuarios.buscar_por_email(userinfo["email"])
        if email_existente:
            db_usuarios.vincular_google(email_existente["id"], google_sub)
            usuario = db_usuarios.buscar_por_id(email_existente["id"])
        else:
            email_cuenta = email_pendiente or userinfo["email"]
            usuario = db_usuarios.crear_usuario(
                email_cuenta, google_sub=google_sub, perfil=perfil_pendiente
            )

    _iniciar_sesion_usuario(usuario, recordar=recordar)
    return render_template("_auth_sincronizar.html", usuario=usuario, siguiente=siguiente)


@auth_bp.route("/perfil/foto", methods=["POST"])
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

    datos = archivo.read()
    try:
        Image.open(io.BytesIO(datos)).verify()
        imagen = Image.open(io.BytesIO(datos))
        imagen.load()
    except (UnidentifiedImageError, OSError):
        return jsonify({"error": "El archivo no es una imagen válida."}), 400

    formato = _FORMATOS_FOTO[extension]
    if formato == "JPEG" and imagen.mode in ("RGBA", "P", "LA"):
        imagen = imagen.convert("RGB")

    usuario_id = session["usuario_id"]
    FOTOS_USUARIOS_DIR.mkdir(parents=True, exist_ok=True)
    nombre_archivo = f"{usuario_id}.{extension}"
    imagen.save(FOTOS_USUARIOS_DIR / nombre_archivo, format=formato)

    ruta_relativa = f"img/usuarios/{nombre_archivo}"
    db_usuarios.actualizar_foto_perfil(usuario_id, ruta_relativa)
    return jsonify({"foto_perfil": url_for("static", filename=ruta_relativa)})


@auth_bp.route("/api/subperfiles", methods=["GET"])
@requiere_cuenta
def listar_subperfiles_ruta():
    """Personas guardadas bajo esta cuenta para la busqueda 'regalo' (ver
    seccion-busqueda-regalo en index.html) -- reutilizables entre
    busquedas, igual que el perfil 'yo'."""
    return jsonify({"subperfiles": db_usuarios.listar_subperfiles(session["usuario_id"])})


@auth_bp.route("/api/subperfiles", methods=["POST"])
@requiere_cuenta
@limiter.limit("20 per minute, 100 per hour")
def crear_subperfil_ruta():
    datos = request.get_json(silent=True) or {}
    nombre = _texto_seguro(datos.get("nombre", ""), 100)
    if not nombre:
        return jsonify({"error": "El nombre es obligatorio."}), 400
    # altura/peso llegan como texto libre (el formulario de "regalo" acepta
    # "1.65m"/"60kg", igual que estimar_tallas()) -- se reusan los mismos
    # parsers tolerantes en vez de guardar el texto crudo, para que quede
    # un numero limpio (motor_recomendacion.py).
    subperfil = {
        "nombre": nombre,
        "apellido": _texto_seguro(datos.get("apellido", ""), 100),
        "genero": _texto_seguro(datos.get("genero", ""), 50),
        "edad": _parsear_numero(str(datos.get("edad") or "")),
        "altura": _parsear_altura_m(str(datos.get("altura") or "")),
        "peso": _parsear_numero(str(datos.get("peso") or "")),
        "hobbie": _lista_texto_segura(datos.get("hobbie")),
        "hobbie_musica_genero": _lista_texto_segura(datos.get("hobbie_musica_genero")),
        "hobbie_deportes_subtipo": _lista_texto_segura(datos.get("hobbie_deportes_subtipo")),
    }
    creado = db_usuarios.crear_subperfil(session["usuario_id"], subperfil)
    return jsonify({"subperfil": creado})


@auth_bp.route("/api/subperfiles/<int:subperfil_id>", methods=["DELETE"])
@requiere_cuenta
def eliminar_subperfil_ruta(subperfil_id):
    db_usuarios.eliminar_subperfil(subperfil_id, session["usuario_id"])
    return jsonify({"ok": True})


@auth_bp.route("/perfil/actualizar", methods=["POST"])
@requiere_cuenta
def actualizar_perfil_cuenta():
    # Solo datos de contacto (2026-08-30, pedido del usuario: separar "Mi
    # cuenta" -- correo/nombre/telefono -- de "Mi perfil" -- altura/peso/
    # direccion/hobbies, que ahora vive solo en el perfil de busqueda local,
    # ver perfil.js). A diferencia de _perfil_desde_formulario (usada en el
    # registro, que si necesita altura/peso/direccion/hobbies del perfil
    # migrado), aca NO se puede reusar esa funcion: manda "" para cualquier
    # campo no incluido en el form, y actualizar_perfil() lo tomaria como
    # "borrar" ese dato en vez de "no tocarlo".
    perfil = {
        "nombre": _texto_seguro(request.form.get("nombre", ""), 200),
        "apellido": _texto_seguro(request.form.get("apellido", ""), 200),
        "telefono": _texto_seguro(request.form.get("telefono", ""), 200),
    }
    db_usuarios.actualizar_perfil(session["usuario_id"], perfil)
    return redirect(request.referrer or "/perfil")
