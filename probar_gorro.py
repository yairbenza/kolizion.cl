"""Prueba en vivo (servidor en http://127.0.0.1:5000) del flujo de Gorro:
camino de colores especificos, camino de outfit, forma, y que la talla
S/M/L/XL no le afecte."""
import json
import urllib.request

URL = "http://127.0.0.1:5000/api/recommend"


def buscar(**extra):
    payload = {
        "modo": "regalo", "genero": "Hombre", "categoria": "gorro",
        "gorro_camino": "", "gorro_colores": [], "gorro_outfit": "", "gorro_forma": "",
        "precio": "", "altura": "1.75m", "peso": "70kg",
    }
    payload.update(extra)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["recomendaciones"]


print("=== Sin filtro de color (deberia traer variedad) ===")
print([r["nombre"] for r in buscar()])
print()

print("=== Camino COLORES: rojo + azul (no deberia traer otros colores) ===")
print([r["nombre"] for r in buscar(gorro_camino="colores", gorro_colores=["rojo", "azul"])])
print()

print("=== Camino OUTFIT oscuro (deberia traer vivos o blanco) ===")
print([r["nombre"] for r in buscar(gorro_camino="outfit", gorro_outfit="oscuro")])
print()

print("=== Camino OUTFIT claro (deberia traer vivos o negro) ===")
print([r["nombre"] for r in buscar(gorro_camino="outfit", gorro_outfit="claro")])
print()

print("=== Camino OUTFIT colorido (SOLO negro/blanco) ===")
print([r["nombre"] for r in buscar(gorro_camino="outfit", gorro_outfit="colorido")])
print()

print("=== Forma PLANO + color negro juntos ===")
print([r["nombre"] for r in buscar(gorro_camino="colores", gorro_colores=["negro"], gorro_forma="plano")])
print()

print("=== Talla: gorro no debe filtrarse por S/M/L/XL (peso extremo 150kg) ===")
resultados = buscar(peso="150kg", altura="1.95m")
print([r["nombre"] for r in resultados])
print("tallas_coincidentes de cada uno (deberia venir vacio, no filtrar):",
      [r["tallas_coincidentes"] for r in resultados])
