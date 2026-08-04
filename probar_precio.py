"""Script de prueba: no es parte de la app, solo sirve para revisar en vivo
que el filtro de Precio (tope, en oferta, cualquier precio) funcione bien
contra el servidor que esta corriendo en http://127.0.0.1:5000."""
import json
import urllib.request

URL = "http://127.0.0.1:5000/api/recommend"


def buscar(precio, tipo_prenda="poleron", corte="oversize"):
    payload = {
        "modo": "regalo",
        "genero": "Hombre",
        "categoria": "prenda superior",
        "tipo_prenda": tipo_prenda,
        "corte": corte,
        "ocasion": "universidad",
        "precio": precio,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["recomendaciones"]


print("=== Polerón oversize, MAX $25.000 ===")
for r in buscar("25000"):
    print(f"- {r['nombre']} | {r['precio']}")
print()

print("=== Polerón oversize, CUALQUIER PRECIO EN OFERTA ===")
for r in buscar("oferta"):
    print(f"- {r['nombre']} | {r['precio']} | {r['descripcion']}")
print()

print("=== Polera slim fit, CUALQUIER PRECIO EN OFERTA (el garantizado) ===")
for r in buscar("oferta", tipo_prenda="polera", corte="slim fit"):
    print(f"- {r['nombre']} | {r['precio']} | {r['descripcion']}")
print()

print("=== Shorts straight fit, CUALQUIER PRECIO EN OFERTA (el garantizado) ===")
for r in buscar("oferta", tipo_prenda="shorts", corte="straight fit"):
    print(f"- {r['nombre']} | {r['precio']} | {r['descripcion']}")
