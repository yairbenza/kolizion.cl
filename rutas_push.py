# Rutas de notificaciones push de la app de iOS (2026-11-03). La logica de
# envio vive en servicio_push.py; los tokens, en db_usuarios.py.
import re

from flask import Blueprint, jsonify, render_template, request, session

import db_usuarios
import servicio_push
from constantes import _texto_seguro
from extensions import limiter
from rutas_admin import requiere_admin

push_bp = Blueprint("push_bp", __name__)

# Un token de APNs son 64 caracteres hexadecimales (a veces mas largo en
# iOS nuevos) -- cualquier otra cosa se rechaza.
_TOKEN_VALIDO = re.compile(r"^[0-9a-fA-F]{64,200}$")


@push_bp.route("/api/push/registrar", methods=["POST"])
@limiter.limit("20 per hour")
def api_push_registrar():
    datos = request.get_json(silent=True) or {}
    token = str(datos.get("token") or "")
    if not _TOKEN_VALIDO.match(token):
        return jsonify({"error": "Token inválido."}), 400
    db_usuarios.registrar_dispositivo(token.lower(), "ios", session.get("usuario_id"))
    return jsonify({"ok": True})


@push_bp.route("/admin/push", methods=["GET", "POST"])
@requiere_admin
def admin_push():
    resultado = None
    form = {"titulo": "", "cuerpo": "", "url": ""}
    if request.method == "POST":
        form = {
            "titulo": _texto_seguro(request.form.get("titulo", ""), 60),
            "cuerpo": _texto_seguro(request.form.get("cuerpo", ""), 180),
            "url": _texto_seguro(request.form.get("url", ""), 300),
        }
        # Solo links internos (ej. /vitrina): al tocar el aviso la app abre
        # esa pagina de kolizion.cl.
        if form["url"] and not form["url"].startswith("/"):
            resultado = {"error": "El link tiene que empezar con / (ej. /vitrina)."}
        elif not form["titulo"] or not form["cuerpo"]:
            resultado = {"error": "Título y mensaje son obligatorios."}
        else:
            resultado = servicio_push.enviar_a_todos(form["titulo"], form["cuerpo"], form["url"])
    return render_template(
        "admin_push.html",
        dispositivos=len(db_usuarios.listar_tokens_push("ios")),
        configurado=servicio_push.configurado(),
        resultado=resultado,
        form=form,
    )
