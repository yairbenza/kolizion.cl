"""Script de prueba: no es parte de la app. Prueba en vivo contra el
servidor (http://127.0.0.1:5000) los 3 agregados nuevos: tipos de prenda de
mujer, el campo largo, y la inferencia de talla."""
import json
import urllib.request

URL = "http://127.0.0.1:5000/api/recommend"


def buscar(**kwargs):
    payload = {
        "modo": "regalo", "genero": "Mujer", "categoria": "", "tipo_prenda": "",
        "subtipo": "", "largo": "", "corte": "", "ocasion": "", "precio": "",
        "altura": "1.65m", "peso": "62kg",
    }
    payload.update(kwargs)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


print("=== Tipos nuevos de prenda superior/inferior ===")
tipos_nuevos = [
    ("crop top / crop hoodie", "prenda superior"),
    ("baby tee", "prenda superior"),
    ("top con breteles / halter", "prenda superior"),
    ("corset top", "prenda superior"),
    ("falda cargo", "prenda inferior"),
    ("bike shorts / shorts ciclista", "prenda inferior"),
]
for tipo, categoria in tipos_nuevos:
    resp = buscar(categoria=categoria, tipo_prenda=tipo)
    nombres = [r["nombre"] for r in resp["recomendaciones"]]
    estado = "OK" if nombres else "VACIO"
    print(f"[{estado}] tipo_prenda='{tipo}' -> {nombres}")
print()

print("=== Campo LARGO (independiente del corte) ===")
resp = buscar(categoria="prenda superior", tipo_prenda="polera", corte="oversize", largo="crop")
nombres = [r["nombre"] for r in resp["recomendaciones"]]
print(f"Polera OVERSIZE + CROP -> {nombres}")
resp = buscar(categoria="prenda superior", tipo_prenda="polera", corte="oversize", largo="extra largo (longline)")
nombres = [r["nombre"] for r in resp["recomendaciones"]]
print(f"Polera OVERSIZE + EXTRA LARGO -> {nombres}")
print()

print("=== Talla inferida (sin preguntar talla al usuario) ===")
# Peso bajo -> deberia inferir S (y quizas M como vecina)
resp = buscar(categoria="prenda superior", tipo_prenda="polera", peso="48kg", altura="1.55m")
print("Peso 48kg, altura 1.55m ->", [
    (r["nombre"], r["talla_disponible"]) for r in resp["recomendaciones"]
])
# Peso medio -> M/L
resp = buscar(categoria="prenda superior", tipo_prenda="polera", peso="65kg", altura="1.65m")
print("Peso 65kg, altura 1.65m ->", [
    (r["nombre"], r["talla_disponible"]) for r in resp["recomendaciones"]
])
# Sin dato de peso -> no debe filtrar por talla (talla_disponible = None)
resp = buscar(categoria="prenda superior", tipo_prenda="polera", peso="")
print("Sin peso ->", [
    (r["nombre"], r["talla_disponible"]) for r in resp["recomendaciones"]
])
