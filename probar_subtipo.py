"""Script de prueba: no es parte de la app, solo sirve para revisar en vivo
que el filtro de subtipo (pantalon de buzo/jeans/cargo, short de
jeans/tela/cargo/bano) funcione bien contra el servidor que esta corriendo
en http://127.0.0.1:5000."""
import json
import urllib.request

URL = "http://127.0.0.1:5000/api/recommend"


def buscar(tipo_prenda, subtipo, corte=""):
    payload = {
        "modo": "regalo",
        "genero": "Hombre",
        "categoria": "prenda inferior",
        "tipo_prenda": tipo_prenda,
        "subtipo": subtipo,
        "corte": corte,
        "ocasion": "universidad",
        "precio": "",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["recomendaciones"]


print("=== Pantalón CARGO (no debería traer jeans ni buzo) ===")
for r in buscar("pantalon", "pantalón cargo"):
    print(f"- {r['nombre']}")
print()

print("=== Pantalón de JEANS (no debería traer cargo ni buzo) ===")
for r in buscar("pantalon", "pantalón de jeans"):
    print(f"- {r['nombre']}")
print()

print("=== Pantalón CUALQUIERA (debería traer de todo tipo) ===")
for r in buscar("pantalon", "cualquiera"):
    print(f"- {r['nombre']}")
print()

print("=== Short de BAÑO (no debería traer jeans/tela/cargo) ===")
for r in buscar("shorts", "short de baño"):
    print(f"- {r['nombre']}")
