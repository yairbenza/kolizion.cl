"""Prueba puntual: busca con un peso muy extremo, filtrando ademas por
subtipo+corte muy especifico, para tratar de forzar el caso "no encontramos
tu talla en las opciones actuales"."""
import json
import urllib.request

URL = "http://127.0.0.1:5000/api/recommend"

payload = {
    "modo": "regalo", "genero": "Mujer", "categoria": "prenda inferior",
    "tipo_prenda": "pantalon", "subtipo": "pantalón cargo", "corte": "baggy",
    "ocasion": "", "precio": "", "altura": "1.90m", "peso": "140kg",
}
data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as resp:
    body = json.load(resp)

print(json.dumps(body, ensure_ascii=False, indent=2))
