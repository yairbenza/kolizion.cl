import os
import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Blueprint, redirect, render_template, request, session

import db_usuarios
from constantes import (
    RANGOS_CLICS,
    REGIONES_CHILE,
    _texto_seguro,
)
from extensions import limiter
from servicio_tiendas import (
    _fecha_clic,
    _parsear_comuna_region,
    cargar_clics_tiendas,
    cargar_reportes_manuales,
    cargar_tiendas,
    guardar_tiendas,
    registrar_reporte_manual,
)

admin_bp = Blueprint("admin_bp", __name__)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


def requiere_admin(vista):
    """Decorator para las rutas /admin/* -- si no hay sesion valida, manda
    a /admin/login (guardando a donde queria ir, para volver ahi despues)."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get("admin_autenticado"):
            return redirect(f"/admin/login?siguiente={request.path}")
        return vista(*args, **kwargs)
    return envoltura


@admin_bp.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("6 per minute, 20 per hour", methods=["POST"])
def admin_login():
    error = None
    siguiente = request.args.get("siguiente") or request.form.get("siguiente") or "/admin/tiendas"
    if not siguiente.startswith("/admin/"):
        siguiente = "/admin/tiendas"

    if request.method == "POST":
        import app
        admin_pass = getattr(app, "ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD", ""))
        if not admin_pass:
            error = "Todavía no se configuró ADMIN_PASSWORD en el servidor -- avisale al dueño del proyecto."
        elif secrets.compare_digest(request.form.get("password", ""), admin_pass):
            session.permanent = True
            session["admin_autenticado"] = True
            return redirect(siguiente)
        else:
            error = "Contraseña incorrecta."

    return render_template("admin_login.html", error=error, siguiente=siguiente)


@admin_bp.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_autenticado", None)
    return redirect("/admin/login")


@admin_bp.route("/admin/tiendas")
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


@admin_bp.route("/admin/tiendas/nueva", methods=["POST"])
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
        comuna, region = _parsear_comuna_region(request.form.get("comuna", ""), request.form.get("region", ""))
        if comuna:
            tienda["comuna"] = comuna
            tienda["region"] = region
        tiendas[tienda_id] = tienda
        guardar_tiendas(tiendas)

    return redirect("/admin/tiendas")


@admin_bp.route("/admin/tiendas/<tienda_id>/ubicacion", methods=["POST"])
@requiere_admin
def admin_tiendas_ubicacion(tienda_id):
    tiendas = cargar_tiendas()
    if tienda_id in tiendas:
        comuna, region = _parsear_comuna_region(request.form.get("comuna", ""), request.form.get("region", ""))
        if comuna:
            tiendas[tienda_id]["comuna"] = comuna
            tiendas[tienda_id]["region"] = region
            guardar_tiendas(tiendas)

    return redirect("/admin/tiendas")


@admin_bp.route("/admin/tiendas/<tienda_id>/reporte", methods=["POST"])
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


@admin_bp.route("/admin/clics")
@requiere_admin
def admin_clics():
    rango = request.args.get("rango", "7")
    if rango not in RANGOS_CLICS:
        rango = "7"
    config_rango = RANGOS_CLICS[rango]

    clics = cargar_clics_tiendas()
    if config_rango["dias"] is not None:
        desde = datetime.now(timezone.utc) - timedelta(days=config_rango["dias"])
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


@admin_bp.route("/admin/usuarios")
@requiere_admin
def admin_usuarios():
    usuarios = db_usuarios.listar_usuarios()
    return render_template("admin_usuarios.html", usuarios=usuarios)
