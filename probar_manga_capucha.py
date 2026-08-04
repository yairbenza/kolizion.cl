"""Prueba en vivo (servidor en http://127.0.0.1:5000) de manga (polera) y
capucha/cierre (poleron)."""
import json
import urllib.request

URL = "http://127.0.0.1:5000/api/recommend"


def buscar(tipo_prenda, **extra):
    payload = {
        "modo": "regalo", "genero": "Hombre", "categoria": "prenda superior",
        "tipo_prenda": tipo_prenda, "subtipo": "", "largo": "",
        "manga": "", "capucha": "", "cierre": "", "corte": "",
        "ocasion": "", "precio": "",
    }
    payload.update(extra)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["recomendaciones"]


print("=== Polera MANGA LARGA (no deberia traer manga corta) ===")
print([r["nombre"] for r in buscar("polera", manga="manga larga")])
print("=== Polera MANGA CORTA ===")
print([r["nombre"] for r in buscar("polera", manga="manga corta")])
print()

print("=== Poleron CON CAPUCHA (no deberia traer sin capucha) ===")
print([r["nombre"] for r in buscar("poleron", capucha="con capucha")])
print("=== Poleron SIN CAPUCHA ===")
print([r["nombre"] for r in buscar("poleron", capucha="sin capucha")])
print()

print("=== Poleron SIN CIERRE (crewneck) ===")
print([r["nombre"] for r in buscar("poleron", cierre="sin cierre (crewneck)")])
print()

print("=== Poleron CON CAPUCHA + CON CIERRE (los 2 juntos, independientes) ===")
print([r["nombre"] for r in buscar("poleron", capucha="con capucha", cierre="con cierre")])
print("=== Poleron CON CAPUCHA + SIN CIERRE ===")
print([r["nombre"] for r in buscar("poleron", capucha="con capucha", cierre="sin cierre (crewneck)")])
print()

print("=== Polera OVERSIZE + MANGA LARGA (independiente del corte, ambos juntos) ===")
print([r["nombre"] for r in buscar("polera", corte="oversized", manga="manga larga")])
