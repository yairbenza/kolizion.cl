import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from functools import wraps
from pathlib import Path

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
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

auth_bp = Blueprint("auth_bp", __name__)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

_EXTENSIONES_FOTO_PERMITIDAS = {"jpg", "jpeg", "png", "webp"}
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
        "redirect_uri": url_for("auth_google_callback", _external=True),
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

    usuario_id = session["usuario_id"]
    FOTOS_USUARIOS_DIR.mkdir(parents=True, exist_ok=True)
    nombre_archivo = f"{usuario_id}.{extension}"
    archivo.save(FOTOS_USUARIOS_DIR / nombre_archivo)

    ruta_relativa = f"img/usuarios/{nombre_archivo}"
    db_usuarios.actualizar_foto_perfil(usuario_id, ruta_relativa)
    return jsonify({"foto_perfil": url_for("static", filename=ruta_relativa)})


@auth_bp.route("/perfil/actualizar", methods=["POST"])
@requiere_cuenta
def actualizar_perfil_cuenta():
    perfil = _perfil_desde_formulario(request.form)
    db_usuarios.actualizar_perfil(session["usuario_id"], perfil)
    return redirect("/perfil")
