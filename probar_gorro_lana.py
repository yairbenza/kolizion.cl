import json
import urllib.request

URL = "http://127.0.0.1:5000/api/recommend"
payload = {
    "modo": "regalo", "genero": "Hombre", "categoria": "gorro",
    "gorro_camino": "colores", "gorro_colores": ["negro"], "gorro_forma": "lana",
    "precio": "", "altura": "1.75m", "peso": "70kg",
}
data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as resp:
    body = json.load(resp)

for r in body["recomendaciones"]:
    print(f"- {r['nombre']}")
