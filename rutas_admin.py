import json
import os
import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Blueprint, jsonify, redirect, render_template, request, session

import db_usuarios
from constantes import (
    CATALOG_PATH,
    FORMAS_GORRO_CONOCIDAS,
    RANGOS_CLICS,
    REGIONES_CHILE,
    TAGS_FORMA_GORRO_PATH,
    TAGS_GRAFICO_PATH,
    _texto_seguro,
    load_json,
)
from extensions import limiter
from servicio_tiendas import (
    _clics_por_producto,
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
            recibido = request.form.get("password", "")
            error = (
                f"Contraseña incorrecta. (debug temporal: recibiste {len(recibido)} "
                f"caracteres, el servidor espera {len(admin_pass)})"
            )

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

    # Clics reales de hoy por producto (2026-09-07, pedido del usuario) --
    # es la misma cuenta que usa _armar_tendencias para rankear Tendencias
    # en /vitrina, para que el usuario pueda confirmar que el ranking sale
    # de clics reales y no esta "inventado".
    catalog_por_nombre = {p["nombre"]: p for p in load_json(CATALOG_PATH)}
    tendencias_clics = [
        {"nombre": nombre, "tienda": catalog_por_nombre[nombre].get("tienda", ""), "clics_hoy": cantidad}
        for nombre, cantidad in _clics_por_producto(dias=1).most_common(15)
        if nombre in catalog_por_nombre
    ]

    return render_template(
        "admin_clics.html", filas=filas, rango=rango, rangos=RANGOS_CLICS,
        etiqueta_rango=config_rango["etiqueta"], tendencias_clics=tendencias_clics,
    )


@admin_bp.route("/admin/usuarios")
@requiere_admin
def admin_usuarios():
    usuarios = db_usuarios.listar_usuarios()
    return render_template("admin_usuarios.html", usuarios=usuarios)


@admin_bp.route("/admin/usuarios/respaldo")
@requiere_admin
def admin_respaldo_usuarios():
    """Descarga un JSON con todas las cuentas (incluye password_hash --
    es un hash, no sirve para nada sin volver a subirlo a esta misma app --
    y subperfiles) para poder restaurarlas si el disco de Render se borra
    en un redeploy (plan gratis, no tiene disco persistente)."""
    respaldo = db_usuarios.exportar_respaldo_completo()
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    cuerpo = json.dumps(respaldo, ensure_ascii=False, indent=2)
    return cuerpo, 200, {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Disposition": f'attachment; filename="respaldo_usuarios_{fecha}.json"',
    }


# --- Clasificacion manual de grafico/estampado (2026-08-29) ---------------
# Herramienta para que el dueno del proyecto clasifique a mano (viendo la
# foto real) si una prenda tiene grafico grande / texto grande / cara-logo
# gigante -- Claude NO analiza las fotos, solo construye la pantalla. El
# resultado se guarda en data/tags_grafico.json (separado de catalog.json,
# que sigue siendo generado solo por construir_catalogo_real.py, ver
# CLAUDE.md regla 3) para no tener que volver a correr ese script cada vez
# que se clasifica un producto.
CATEGORIAS_CLASIFICAR_GRAFICO = {"polera", "poleron", "camisa", "top", "conjunto"}
TAGS_GRAFICO_VALIDOS = {"texto_grande", "cara_logo_gigante", "prenda_simple"}
TAMANO_LOTE_GRAFICO = 22
TOTAL_LOTES_GRAFICO = 5


def cargar_tags_grafico():
    if not TAGS_GRAFICO_PATH.exists():
        return {}
    return load_json(TAGS_GRAFICO_PATH)


def guardar_tags_grafico(tags):
    TAGS_GRAFICO_PATH.write_text(json.dumps(tags, ensure_ascii=False, indent=2), encoding="utf-8")


def _productos_pendientes_grafico():
    catalog = load_json(CATALOG_PATH)
    tags = cargar_tags_grafico()
    pendientes = [
        p for p in catalog
        if p.get("categoria") in CATEGORIAS_CLASIFICAR_GRAFICO and p["id"] not in tags
    ]
    pendientes.sort(key=lambda p: p["id"])
    return pendientes


@admin_bp.route("/admin/clasificar-graficos")
@requiere_admin
def admin_clasificar_graficos():
    modo = "clasificados" if request.args.get("modo") == "clasificados" else "pendientes"
    try:
        lote = int(request.args.get("lote", "1"))
    except ValueError:
        lote = 1

    tags = cargar_tags_grafico()

    # Modo "ver ya clasificados" (2026-08-30, pedido del usuario): la
    # herramienta original solo mostraba pendientes -- una vez clasificado
    # un producto desaparecia de la vista y no habia forma de revisarlo de
    # nuevo salvo las fotos mandadas por chat. Reusa la misma tarjeta/chips/
    # zoom, mas recientes primero, con el tag actual pre-marcado (mismo
    # patron que /admin/clasificar-gorros) para poder corregir sin perder
    # lo ya bueno.
    if modo == "clasificados":
        catalog = load_json(CATALOG_PATH)
        por_id = {p["id"]: p for p in catalog}
        clasificados = [
            (pid, datos) for pid, datos in tags.items() if pid in por_id
        ]
        clasificados.sort(key=lambda par: par[1].get("clasificado_en", ""), reverse=True)
        total_lotes = max(1, (len(clasificados) + TAMANO_LOTE_GRAFICO - 1) // TAMANO_LOTE_GRAFICO)
        lote = max(1, min(lote, total_lotes))
        inicio = (lote - 1) * TAMANO_LOTE_GRAFICO
        pagina = clasificados[inicio:inicio + TAMANO_LOTE_GRAFICO]

        productos_json = [
            {
                "id": pid,
                "nombre": por_id[pid]["nombre"],
                "tienda": por_id[pid]["tienda"],
                "imagen": (por_id[pid].get("fotos") or [por_id[pid].get("imagen", "")])[0],
                "tags_actuales": datos.get("tags", []),
            }
            for pid, datos in pagina
        ]
        return render_template(
            "admin_clasificar_graficos.html",
            modo=modo,
            lote=lote,
            total_lotes=total_lotes,
            productos=productos_json,
            total_pendientes=len(_productos_pendientes_grafico()),
            ya_clasificados=len(tags),
        )

    lote = max(1, min(lote, TOTAL_LOTES_GRAFICO))
    pendientes = _productos_pendientes_grafico()
    inicio = (lote - 1) * TAMANO_LOTE_GRAFICO
    productos_lote = pendientes[inicio:inicio + TAMANO_LOTE_GRAFICO]

    productos_json = [
        {
            "id": p["id"],
            "nombre": p["nombre"],
            "tienda": p["tienda"],
            "imagen": (p.get("fotos") or [p.get("imagen", "")])[0],
            "tags_actuales": [],
        }
        for p in productos_lote
    ]

    return render_template(
        "admin_clasificar_graficos.html",
        modo=modo,
        lote=lote,
        total_lotes=TOTAL_LOTES_GRAFICO,
        productos=productos_json,
        total_pendientes=len(pendientes),
        ya_clasificados=len(tags),
    )


@admin_bp.route("/admin/api/clasificar-grafico/<producto_id>", methods=["POST"])
@requiere_admin
def admin_api_clasificar_grafico(producto_id):
    datos = request.get_json(silent=True) or {}
    tags_limpios = [t for t in datos.get("tags", []) if t in TAGS_GRAFICO_VALIDOS]

    tags = cargar_tags_grafico()
    tags[producto_id] = {
        "tags": tags_limpios,
        "clasificado_en": datetime.now(timezone.utc).isoformat(),
    }
    guardar_tags_grafico(tags)
    return jsonify({"ok": True})


# --- Revision visual de forma de gorro (2026-08-30) ------------------------
# El auto-detector de forma en construir_catalogo_real.py (curvo por
# default, lana si dice "beanie", plano si dice "snapback") es un supuesto
# razonable, no un dato literal como color/precio -- el usuario pidio poder
# revisarlo el mismo, con foto, igual que grafico/texto/logo. A diferencia
# de esa herramienta, aca se muestran TODOS los gorros pendientes de una
# vez (hoy son pocos) y se pre-selecciona la forma actual en vez de partir
# vacio -- confirmar sin tocar nada equivale a aceptar el default.
def cargar_tags_forma_gorro():
    if not TAGS_FORMA_GORRO_PATH.exists():
        return {}
    return load_json(TAGS_FORMA_GORRO_PATH)


def guardar_tags_forma_gorro(tags):
    TAGS_FORMA_GORRO_PATH.write_text(json.dumps(tags, ensure_ascii=False, indent=2), encoding="utf-8")


@admin_bp.route("/admin/clasificar-gorros")
@requiere_admin
def admin_clasificar_gorros():
    catalog = load_json(CATALOG_PATH)
    tags = cargar_tags_forma_gorro()
    gorros = [p for p in catalog if p.get("categoria") == "gorro"]
    gorros.sort(key=lambda p: p["id"])

    productos_json = [
        {
            "id": p["id"],
            "nombre": p["nombre"],
            "tienda": p["tienda"],
            "imagen": (p.get("fotos") or [p.get("imagen", "")])[0],
            "forma_actual": tags.get(p["id"], p.get("forma", "curvo")),
        }
        for p in gorros
    ]

    return render_template(
        "admin_clasificar_gorros.html",
        productos=productos_json,
        total_gorros=len(gorros),
        ya_revisados=len(tags),
    )


@admin_bp.route("/admin/api/clasificar-gorro/<producto_id>", methods=["POST"])
@requiere_admin
def admin_api_clasificar_gorro(producto_id):
    datos = request.get_json(silent=True) or {}
    forma = datos.get("forma")
    if forma not in FORMAS_GORRO_CONOCIDAS:
        return jsonify({"ok": False}), 400

    tags = cargar_tags_forma_gorro()
    tags[producto_id] = forma
    guardar_tags_forma_gorro(tags)
    return jsonify({"ok": True})
