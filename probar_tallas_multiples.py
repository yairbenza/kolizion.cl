"""Prueba en vivo: confirma que se muestren TODAS las tallas coincidentes
(no solo una), y que nunca se muestre una talla que el producto no tenga."""
import json
import urllib.request

URL = "http://127.0.0.1:5000/api/recommend"

payload = {
    "modo": "regalo", "genero": "Mujer", "categoria": "prenda superior",
    "tipo_prenda": "polera", "corte": "oversized", "ocasion": "",
    "precio": "", "altura": "1.63m", "peso": "65kg",  # deberia dar 2 tallas
}
data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as resp:
    body = json.load(resp)

for r in body["recomendaciones"]:
    print(f"- {r['nombre']}")
    print(f"    tallas_coincidentes: {r['tallas_coincidentes']}")
