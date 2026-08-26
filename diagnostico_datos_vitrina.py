# -*- coding: utf-8 -*-
"""Diagnostico de una sola vez: muestra los datos REALES detras de las 4
secciones de /vitrina (Tendencias, Ofertas, Nuevos lanzamientos, Destacados)
para que el usuario pueda verificar si "quedaron bien" antes de mostrarlas.

No modifica nada -- solo lee catalog.json e historial_usuarios.json y
replica la logica de api_vitrina()/_armar_tendencias() en app.py."""
import json
import random
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).parent
catalog = json.loads((BASE / "data" / "catalog.json").read_text(encoding="utf-8"))
historial = json.loads((BASE / "data" / "historial_usuarios.json").read_text(encoding="utf-8"))

cantidad = 10

# --- Ofertas ---
en_oferta = [p for p in catalog if p.get("en_oferta")]
print(f"=== OFERTAS ===  ({len(en_oferta)} productos marcados en_oferta=True en el catalogo real)")
if not en_oferta:
    print("  -> Ningun producto del catalogo real tiene descuento cargado ahora mismo.")
    print("     La seccion 'Ofertas' de /vitrina sale VACIA en este momento (no es un bug del calculo, es que no hay dato).")
else:
    for p in sorted(en_oferta, key=lambda p: p.get("descuento_pct", 0), reverse=True)[:cantidad]:
        print(f"  - {p['nombre']} | tienda: {p.get('tienda')} | {p.get('precio_original')} -> {p.get('precio')} | -{p.get('descuento_pct')}%")

# --- Tendencias (clics reales ultimas 24h) ---
limite = datetime.now(timezone.utc) - timedelta(days=1)
conteo = Counter()
sin_nombre = 0
for entrada in historial.values():
    for item in entrada.get("productos_interes", []):
        try:
            fecha = datetime.fromisoformat(item["fecha"])
        except (KeyError, ValueError):
            continue
        if fecha >= limite:
            nombre = item.get("nombre", "")
            if not nombre:
                sin_nombre += 1
                continue
            conteo[nombre] += 1

print(f"\n=== TENDENCIAS ===  (clics reales en 'Ver producto' de las ULTIMAS 24 HORAS, todos los usuarios)")
if not conteo:
    print("  -> No hay ningun clic real registrado en las ultimas 24h.")
    print("     Los 10 productos que se ven ahora en /vitrina son etiqueta generica rotativa")
    print("     ('Nuevo en la tienda' / 'Mas buscado en {categoria}'), NO un ranking real de clics.")
else:
    for puesto, (nombre, n) in enumerate(conteo.most_common(cantidad), start=1):
        print(f"  {puesto}. {nombre} -- {n} clics")
if sin_nombre:
    print(f"  (aviso: {sin_nombre} clics del historial no tienen nombre de producto guardado, no se cuentan)")

# --- Ultimo clic real registrado, para dar contexto de "hace cuanto" ---
todos = []
for entrada in historial.values():
    for item in entrada.get("productos_interes", []):
        try:
            fecha = datetime.fromisoformat(item["fecha"])
        except (KeyError, ValueError):
            continue
        todos.append((fecha, item.get("nombre", "")))
if todos:
    todos.sort(reverse=True)
    ultimo_fecha, ultimo_nombre = todos[0]
    horas = (datetime.now(timezone.utc) - ultimo_fecha).total_seconds() / 3600
    print(f"  (el clic mas reciente de TODO el historial es de hace {horas:.0f} horas: '{ultimo_nombre}')")

# --- Nuevos lanzamientos / Destacados ---
print(f"\n=== NUEVOS LANZAMIENTOS ===")
print("  -> El catalogo no guarda fecha real de publicacion todavia.")
print("     Esta seccion es una muestra AL AZAR del catalogo, distinta cada vez que se entra a /vitrina.")
print("     'Hace cuanto salieron' NO es un dato real para esta seccion -- no preguntar por fecha real todavia.")

print(f"\n=== DESTACADOS ===")
print("  -> Igual que lanzamientos: no hay un campo real de 'destacado' en el catalogo.")
print("     Tambien es muestra al azar, no un criterio elegido.")

# --- Visitas/clics reales en las TIENDAS PILOTO (sistema aparte, via /ir/<tienda>/<producto>) ---
clics_path = BASE / "data" / "clics_tiendas.json"
if clics_path.exists():
    clics = json.loads(clics_path.read_text(encoding="utf-8"))
    por_tienda = Counter(c.get("tienda") for c in clics)
    print(f"\n=== VISITAS A TIENDAS PILOTO (sistema aparte, no es lo mismo que 'Tendencias') ===")
    print(f"  Total de clics 'Visitar tienda' / redirecciones registrados: {len(clics)}")
    for tienda, n in por_tienda.most_common():
        print(f"  - {tienda}: {n} clics")
    print("  (Este es el conteo real de gente que salio de KOLIZION hacia la tienda -- se ve en detalle en /admin/clics.")
    print("   No mide visitas DENTRO del sitio real de la tienda, eso la tienda solo lo sabe por su propia plataforma.)")
