import json
import random
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from constantes import (
    ALIAS_METROPOLITANA,
    CLICS_TIENDAS_PATH,
    ENVIOS_TIENDAS_PATH,
    FAVORITOS_PATH,
    HISTORIAL_PATH,
    REGIONES_CHILE,
    REPORTES_MANUALES_PATH,
    RESENAS_PATH,
    TIENDAS_PATH,
    load_json,
    _normalizar_email,
    _parsear_fecha_iso,
    _quitar_tildes,
    _texto_seguro,
)
from motor_recomendacion import armar_resultados


def cargar_historial():
    if not HISTORIAL_PATH.exists():
        return {}
    return load_json(HISTORIAL_PATH)


def guardar_historial(historial):
    HISTORIAL_PATH.write_text(json.dumps(historial, ensure_ascii=False, indent=2), encoding="utf-8")


def registrar_busqueda(email, ocasion, categoria, tipo_prenda, corte, payload=None):
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
        # Guarda lo necesario para volver a correr esta misma busqueda desde
        # el historial (2026-08-28, pedido del usuario) -- None en entradas
        # viejas, guardadas antes de este cambio, asi que el frontend no
        # ofrece "volver" ahi (no hay como reconstruir esa busqueda).
        "payload": payload or None,
    })
    guardar_historial(historial)


def registrar_interes(email, producto):
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
    email = _normalizar_email(email)
    if not email:
        return False
    favoritos = cargar_favoritos()
    if email in favoritos:
        favoritos[email] = []
        guardar_favoritos(favoritos)
    return True


def _clics_por_producto(dias=7):
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


_ETIQUETAS_TENDENCIA_RESPALDO = ["Nuevo en la tienda", "Más buscado en {categoria}"]


def _armar_tendencias(catalog_disponible, cantidad):
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


def _armar_basado_en_busquedas(email, catalog_disponible, reglas, cantidad):
    """Fila "Basado en tus ultimas busquedas" de /vitrina (2026-08-30,
    pedido del usuario) -- solo para cuentas con sesion real, porque el
    historial de busquedas ya no se guarda para invitados (ver
    _email_sesion_actual en app.py). Reutiliza el mismo motor de siempre
    (armar_resultados/elegir_candidatos) con los criterios de las ultimas
    3 busquedas guardadas -- no inventa ningun criterio nuevo ni vuelve a
    analizar catalogo o fotos. Sin filtro de talla (esta fila es solo un
    vistazo, no vuelve a pedir el perfil)."""
    email = _normalizar_email(email)
    if not email:
        return []
    busquedas = cargar_historial().get(email, {}).get("busquedas", [])
    payloads = [b["payload"] for b in busquedas[-3:] if b.get("payload")]
    if not payloads:
        return []

    catalog_por_id = {p["id"]: p for p in catalog_disponible}
    ids_usados = set()
    resultado = []
    for payload in payloads:
        genero = (payload.get("perfil") or {}).get("genero", "")
        texto_pedido = " ".join([
            payload.get("categoria", ""), payload.get("tipo_prenda", ""),
            payload.get("subtipo", ""), payload.get("largo", ""),
            payload.get("manga", ""), payload.get("capucha", ""),
            payload.get("cierre", ""), payload.get("corte", ""),
            payload.get("ocasion", ""),
        ])
        candidatos = armar_resultados(
            genero, payload.get("ocasion", ""), payload.get("categoria", ""),
            texto_pedido, catalog_disponible, reglas,
            color_pedido=payload.get("colores") or None,
        )
        for c in candidatos:
            producto = catalog_por_id.get(c["id"])
            if producto is None or c["id"] in ids_usados:
                continue
            ids_usados.add(c["id"])
            resultado.append(producto)
            if len(resultado) >= cantidad:
                return resultado
    return resultado


def cargar_tiendas():
    if not TIENDAS_PATH.exists():
        return {}
    return load_json(TIENDAS_PATH)


def guardar_tiendas(tiendas):
    TIENDAS_PATH.write_text(json.dumps(tiendas, ensure_ascii=False, indent=2), encoding="utf-8")


def _parsear_comuna_region(comuna_texto, region_texto):
    comuna = _texto_seguro(comuna_texto, 60)
    region = _texto_seguro(region_texto, 40)
    if region not in REGIONES_CHILE:
        region = ""
    return comuna, region


def cargar_envios_tiendas():
    if not ENVIOS_TIENDAS_PATH.exists():
        return {}
    datos = load_json(ENVIOS_TIENDAS_PATH)
    datos.pop("_meta", None)
    return datos


def _dias_habiles_a_numero(texto):
    texto_norm = _quitar_tildes((texto or "").lower())
    if "mismo dia" in texto_norm:
        return 0
    if "dia siguiente" in texto_norm or "dia habil siguiente" in texto_norm:
        return 1
    match = re.search(r"\d+", texto_norm)
    return int(match.group()) if match else 99


def _estimar_envio_real(direccion_usuario, nombre_tienda):
    info = cargar_envios_tiendas().get(nombre_tienda)
    if not info:
        return {"texto": "Sin dato de envío investigado", "dias": 99, "tiene_dato": False}

    direccion_norm = _quitar_tildes((direccion_usuario or "").lower())
    en_rm = any(a in direccion_norm for a in ALIAS_METROPOLITANA)

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


def resumen_envio_general(nombre_tienda):
    """Politica de envio de la tienda SIN personalizar por direccion del
    usuario (a diferencia de _estimar_envio_real) -- para mostrar en la
    ficha de producto, seccion "Envios y cambios". None si no hay dato
    investigado para esa tienda (nunca se inventa un plazo)."""
    info = cargar_envios_tiendas().get(nombre_tienda)
    if not info:
        return None

    def _linea(etiqueta, segmento):
        segmento = segmento or {}
        dias = segmento.get("dias_habiles", "no especificado")
        if not segmento.get("disponible") or (dias or "").startswith("no especificado"):
            return f"{etiqueta}: sin plazo publicado por la tienda"
        return f"{etiqueta}: {dias}"

    lineas = [
        _linea("RM", info.get("envio_rm")),
        _linea("Regiones", info.get("envio_regiones")),
    ]
    retiro = info.get("retiro_tienda") or {}
    if retiro.get("disponible"):
        lineas.append(f"Retiro en tienda disponible ({retiro.get('comuna') or 'sin comuna publicada'})")
    return " · ".join(lineas)


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


def _fecha_clic(clic):
    return _parsear_fecha_iso(clic.get("fecha", ""))


# --- Resenas de producto (2026-08-27) -------------------------------------
# Guardadas por NOMBRE del producto (mismo criterio que favoritos.py --
# el id de catalog.json no es estable entre corridas de
# construir_catalogo_real.py, el nombre real de la tienda si lo es). Nunca
# se inventa una resena -- si no hay ninguna cargada para ese nombre, se
# devuelve el resumen vacio (total=0), nunca datos de relleno.
def cargar_resenas():
    if not RESENAS_PATH.exists():
        return {}
    return load_json(RESENAS_PATH)


def resumen_resenas(nombre_producto):
    nombre = _texto_seguro(nombre_producto)
    items = cargar_resenas().get(nombre, []) if nombre else []
    distribucion = {str(n): 0 for n in range(5, 0, -1)}
    suma = 0
    for r in items:
        estrellas = r.get("estrellas")
        if estrellas in (1, 2, 3, 4, 5):
            distribucion[str(estrellas)] += 1
            suma += estrellas
    total = len(items)
    return {
        "promedio": round(suma / total, 1) if total else 0,
        "total": total,
        "distribucion": distribucion,
        "items": sorted(items, key=lambda r: r.get("fecha", ""), reverse=True),
    }
