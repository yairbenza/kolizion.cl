"""Verificacion de stock en vivo (2026-09-07, pedido del usuario -- parte 3
del pedido de "stock global": revalidar antes de comprar + compartir esa
actualizacion con todos, sin sobrecargar a las tiendas chicas).

Arquitectura elegida despues de verificar a mano (curl real, 2026-09-07) las
plataformas que hoy tiene el catalogo -- ver docs/buscador.md para el
detalle completo de lo probado:

- Shopify (la gran mayoria de las tiendas): endpoint publico real
  `/products.json` -- trae TODAS las variantes de TODOS los productos de la
  tienda en una sola llamada, se usa para el refresco de fondo periodico.
  Para el chequeo puntual al agregar al carrito se usa `<link>.js` (endpoint
  AJAX del propio tema, publico, sin API key) -- a diferencia de
  `<link>.json`, que en el tema de Doslobos NO trae "available" por
  variante (confirmado a mano), `<link>.js` si lo trae siempre.
- IPREX: su API REST de WooCommerce esta bloqueada, pero cada ficha SI trae
  un bloque real `<script type="application/ld+json">` tipo Product con
  `offers.availability` (confirmado a mano en una ficha real). Solo da
  disponibilidad del producto COMPLETO, no por talla -- la propia fuente no
  separa mas que eso, asi que no se inventa mas granularidad de la que hay.
- RAPT (Jumpseller): verificado a mano -- la tienda esta HOY con clave/
  desactivada al publico ("Ingrese usando contraseña"), no hay ficha real
  que leer todavia. verificar_stock_producto() simplemente no encuentra
  fuente para este dominio y no inventa un resultado.
- Cualquier otra tienda/plataforma no reconocida: tampoco se inventa nada,
  se sigue mostrando el stock de la ultima recarga manual de catalog.json,
  igual que hoy.

Nunca toca data/catalog.json (regla del proyecto: ese archivo solo se
genera con construir_catalogo_real.py). Todo lo aprendido en vivo se guarda
aparte en data/stock_live.json y se aplica como una capa encima del
catalogo real al armar cada respuesta -- ver aplicar_overlay(), llamado
desde app.py (cargar_catalog_con_stock_live())."""

import json
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

from constantes import STOCK_LIVE_PATH, load_json
from construir_catalogo_real import _variantes_talla_shopify

_USER_AGENT = "Mozilla/5.0 (compatible; KolizionStockBot/1.0)"
_TIMEOUT_SEGUNDOS = 8
_LOCK = threading.Lock()


def _get_texto(url):
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT_SEGUNDOS) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _dominio(link):
    partes = urlparse(link)
    return f"{partes.scheme}://{partes.netloc}"


def _handle_de_link(link):
    return link.rstrip("/").split("/")[-1]


# --- Overlay en disco (data/stock_live.json) --------------------------------

def cargar_overlay():
    if not STOCK_LIVE_PATH.exists():
        return {}
    try:
        return json.loads(STOCK_LIVE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def guardar_overlay(overlay):
    STOCK_LIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STOCK_LIVE_PATH.write_text(json.dumps(overlay, ensure_ascii=False, indent=2), encoding="utf-8")


def _ahora_iso():
    return datetime.now(timezone.utc).isoformat()


def registrar_resultado(overlay, producto_id, *, variantes=None, disponible_general=None, fuente):
    """Guarda lo aprendido de un producto -- "una observacion mas reciente
    gana" (pedido del usuario, punto C de la extension original) se resuelve
    simplemente guardando el timestamp de ahora: todas las escrituras pasan
    por _LOCK y se guardan al toque, asi que a esta escala de trafico nunca
    llega una respuesta vieja despues de una mas nueva para el MISMO
    producto (no hay 2 refrescos del mismo producto corriendo en paralelo)."""
    overlay[producto_id] = {
        "tallas_variantes": variantes,
        "disponible_general": disponible_general,
        "actualizado": _ahora_iso(),
        "fuente": fuente,
    }


def guardar_resultado_verificacion(producto_id, resultado):
    """Envoltorio de registrar_resultado() + cargar/guardar overlay bajo
    _LOCK, para que los llamadores (ej. /api/verificar_stock en app.py) no
    necesiten tocar el lock ni el archivo directamente."""
    with _LOCK:
        overlay = cargar_overlay()
        registrar_resultado(
            overlay, producto_id,
            variantes=resultado.get("variantes"),
            disponible_general=resultado.get("disponible_general"),
            fuente=resultado["fuente"],
        )
        guardar_overlay(overlay)


def aplicar_overlay(catalog, overlay=None):
    """Capa de stock en vivo encima del catalogo real -- se llama justo
    despues de cargar catalog.json (ver cargar_catalog_con_stock_live() en
    app.py). Nunca modifica catalog.json; un producto sin entrada en el
    overlay queda exactamente como estaba (el stock de la ultima recarga
    manual, igual que hoy)."""
    if overlay is None:
        overlay = cargar_overlay()
    if not overlay:
        return catalog
    for p in catalog:
        entry = overlay.get(p["id"])
        if not entry:
            continue
        variantes = entry.get("tallas_variantes")
        if variantes is not None:
            p["tallas_variantes"] = variantes
            p["tallas_disponibles"] = [v["talla"] for v in variantes if v.get("disponible")]
        elif entry.get("disponible_general") is False:
            # Solo se sabe que el producto ENTERO esta agotado (ej. IPREX,
            # que no separa stock por talla) -- eso si se puede aplicar con
            # certeza a todas las tallas ya cargadas, sin inventar
            # granularidad que la fuente real no dio.
            p["tallas_disponibles"] = []
            if p.get("tallas_variantes"):
                p["tallas_variantes"] = [{**v, "disponible": False} for v in p["tallas_variantes"]]
    return catalog


# --- Chequeo puntual (al momento de "Agregar al carrito") -------------------

def verificar_stock_producto(producto):
    """Verificacion en vivo de UN producto puntual. Devuelve un dict:
    {"fuente": "shopify"|"iprex"|None, "variantes": [...] o None,
    "disponible_general": bool o None}. fuente=None quiere decir que no se
    pudo verificar nada real para esta tienda ahora (tienda caida, sin
    fuente publica conocida, etc.) -- nunca se inventa un resultado en ese
    caso, el llamador debe seguir con el dato que ya tenia."""
    link = producto.get("link", "")
    if not link:
        return {"fuente": None, "variantes": None, "disponible_general": None}
    dominio = _dominio(link)

    if "iprex.cl" in dominio:
        return _verificar_iprex(link)
    if "zamu.cl" in dominio:
        return _verificar_zamu(link)

    # Shopify se prueba para el resto -- <link>.js responde 404/HTML de
    # error en cualquier tienda que no sea Shopify, asi que esto ya actua
    # como la deteccion (no hace falta mantener una lista aparte de "cuales
    # tiendas son Shopify").
    return _verificar_shopify(link)


def _verificar_shopify(link):
    try:
        data = json.loads(_get_texto(f"{link}.js"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return {"fuente": None, "variantes": None, "disponible_general": None}
    variantes_crudas = data.get("variants")
    if not isinstance(variantes_crudas, list):
        return {"fuente": None, "variantes": None, "disponible_general": None}
    variantes = []
    vistas = set()
    for v in variantes_crudas:
        talla = v.get("option1") or v.get("title")
        if not talla or talla in vistas:
            continue
        vistas.add(talla)
        variantes.append({"talla": talla, "disponible": bool(v.get("available"))})
    if not variantes:
        return {"fuente": None, "variantes": None, "disponible_general": None}
    return {"fuente": "shopify", "variantes": variantes, "disponible_general": None}


_PATRON_LD_JSON = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)


def _verificar_iprex(link):
    try:
        html = _get_texto(link)
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"fuente": None, "variantes": None, "disponible_general": None}
    for bloque in _PATRON_LD_JSON.findall(html):
        try:
            data = json.loads(bloque)
        except json.JSONDecodeError:
            continue
        if data.get("@type") != "Product":
            continue
        disponibilidad = (data.get("offers") or {}).get("availability") or ""
        return {
            "fuente": "iprex",
            "variantes": None,
            "disponible_general": disponibilidad.endswith("InStock"),
        }
    return {"fuente": None, "variantes": None, "disponible_general": None}


def _verificar_zamu(link):
    """ZAMU (WooCommerce) SI tiene API publica (Store API), pero a
    diferencia de Shopify no da stock por variante/talla en una sola
    llamada -- las variantes son sub-recursos aparte (products/<id>/
    variations no existe en esta version de la API, y cada variacion
    necesitaria su propia request). Con solo 9 productos en el catalogo no
    compensa pedir N variantes por producto (mismo criterio de "no hacer
    requests innecesarios" del refresco en bloque) -- se usa el stock
    agregado del producto completo (is_in_stock + is_purchasable), igual
    granularidad que IPREX."""
    slug = _handle_de_link(link)
    try:
        data = json.loads(_get_texto(f"https://zamu.cl/wp-json/wc/store/v1/products?slug={slug}"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return {"fuente": None, "variantes": None, "disponible_general": None}
    if not isinstance(data, list):
        return {"fuente": None, "variantes": None, "disponible_general": None}
    producto_padre = next((item for item in data if item.get("type") != "variation"), None)
    if not producto_padre:
        return {"fuente": None, "variantes": None, "disponible_general": None}
    disponible = bool(producto_padre.get("is_in_stock") and producto_padre.get("is_purchasable"))
    return {"fuente": "zamu", "variantes": None, "disponible_general": disponible}


# --- Refresco de fondo (Shopify, cada N minutos) ----------------------------

def _refrescar_stock_shopify_en_bloque(catalog, overlay):
    """1 sola llamada por tienda (products.json, pagina de a 250) trae TODAS
    las variantes de TODOS sus productos -- pedido explicito del usuario:
    "si una sola respuesta oficial entrega todo el estado, no hacer N
    requests". Tiendas que no respondan como Shopify real (WooCommerce,
    Jumpseller, caidas, sitio distinto) se saltan solas -- no hace falta
    mantener una lista aparte de "cuales tiendas son Shopify", se detecta
    con la respuesta real de cada dominio."""
    dominio_por_tienda = {}
    for p in catalog:
        dominio_por_tienda.setdefault(p["tienda"], _dominio(p["link"]))

    for tienda, dominio in dominio_por_tienda.items():
        productos_shopify = {}
        pagina = 1
        while True:
            try:
                data = json.loads(_get_texto(f"{dominio}/products.json?limit=250&page={pagina}"))
            except (urllib.error.URLError, TimeoutError, ValueError, OSError):
                productos_shopify = None
                break
            productos = data.get("products")
            if productos is None:
                productos_shopify = None
                break
            if not productos:
                break
            for prod in productos:
                if prod.get("handle"):
                    productos_shopify[prod["handle"]] = prod
            if len(productos) < 250:
                break
            pagina += 1

        if not productos_shopify:
            continue  # no es Shopify (o no respondio) -- se sigue con lo que ya habia

        for p in catalog:
            if p["tienda"] != tienda:
                continue
            prod_shopify = productos_shopify.get(_handle_de_link(p["link"]))
            if not prod_shopify:
                continue
            variantes = _variantes_talla_shopify(prod_shopify)
            registrar_resultado(overlay, p["id"], variantes=variantes, fuente="shopify")
        time.sleep(0.3)  # no golpear todas las tiendas en el mismo instante


def ciclo_refresco_stock_live(catalog_path, intervalo_segundos):
    while True:
        try:
            catalog = load_json(catalog_path)
            with _LOCK:
                overlay = cargar_overlay()
                _refrescar_stock_shopify_en_bloque(catalog, overlay)
                guardar_overlay(overlay)
        except Exception:
            pass  # un error de red puntual nunca debe tumbar el hilo de fondo
        time.sleep(intervalo_segundos)


def iniciar_refresco_en_segundo_plano(catalog_path, intervalo_segundos=1200):
    """intervalo_segundos default 1200 (20 min) -- punto medio de "cada 15-30
    minutos" (elegido explicitamente por el usuario, 2026-09-07) para no
    sobrecargar a las tiendas chicas."""
    hilo = threading.Thread(
        target=ciclo_refresco_stock_live, args=(catalog_path, intervalo_segundos), daemon=True,
    )
    hilo.start()
    return hilo
