"""Diagnostico del boton 'mostrar mas opciones' con 'pantalon baggy'. Llama
/api/recommend directamente (test client, sin servidor real, sin costo) con
el mismo payload que mandaria el formulario, primero normal y despues con
plan_b=true, para ver exactamente que devuelve el backend."""
import json

from app import app, CATALOG_PATH, load_json

PAYLOAD_BASE = {
    "modo": "regalo",
    "altura": "1.75m",
    "peso": "75kg",
    "genero": "Hombre",
    "categoria": "prenda inferior",
    "tipo_prenda": "pantalon",
    "subtipo": "",
    "largo": "",
    "manga": "",
    "capucha": "",
    "cierre": "",
    "corte": "baggy",
    "ocasion": "",
    "precio": "",
    "gorro_camino": "",
    "gorro_colores": [],
    "gorro_outfit": "",
    "gorro_forma": "",
}

cliente = app.test_client()

print("=== Catalogo: cuantos pantalon+baggy hay en total (Hombre o unisex) ===")
catalog = load_json(CATALOG_PATH)
pantalones_baggy = [
    p for p in catalog
    if p["categoria"] == "pantalon" and p["genero"].lower() in ("hombre", "unisex")
    and "baggy" in p.get("corte", "").lower()
]
print(f"Total: {len(pantalones_baggy)}")
print()

print("=== Busqueda primaria (plan_b=false) ===")
resp1 = cliente.post("/api/recommend", json=PAYLOAD_BASE)
data1 = resp1.get_json()
print(f"STATUS: {resp1.status_code}")
print(f"recomendaciones: {len(data1.get('recomendaciones', []))}")
for r in data1.get("recomendaciones", []):
    print(f"  - {r['nombre']}")
print()

print("=== Mostrar mas opciones (plan_b=true) ===")
resp2 = cliente.post("/api/recommend", json={**PAYLOAD_BASE, "plan_b": True})
data2 = resp2.get_json()
print(f"STATUS: {resp2.status_code}")
print("Respuesta completa:")
print(json.dumps(data2, ensure_ascii=False, indent=2)[:3000])
