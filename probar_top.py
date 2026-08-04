"""Prueba en vivo (servidor en http://127.0.0.1:5000) del tipo "Top"
consolidado y sus 6 subtipos (crop top, baby tee, halter, corset, tank top,
camisas/blusas)."""
import json
import urllib.request

URL = "http://127.0.0.1:5000/api/recommend"


def buscar(subtipo, corte=""):
    payload = {
        "modo": "regalo", "genero": "Mujer", "categoria": "prenda superior",
        "tipo_prenda": "top", "subtipo": subtipo, "corte": corte,
        "ocasion": "", "precio": "", "altura": "1.65m", "peso": "60kg",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["recomendaciones"]


for subtipo in [
    "crop top / crop hoodie", "baby tee", "top con breteles / halter",
    "corset top", "tank top", "camisas/blusas", "cualquiera",
]:
    nombres = [r["nombre"] for r in buscar(subtipo)]
    estado = "OK" if nombres else "VACIO"
    print(f"[{estado}] subtipo='{subtipo}' -> {nombres}")

print()
print("=== Top + corset + oversize (subtipo y corte juntos, estricto) ===")
print([r["nombre"] for r in buscar("corset top", corte="oversize")])
