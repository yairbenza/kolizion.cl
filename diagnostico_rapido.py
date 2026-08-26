"""Chequeo puntual (no toda la bateria): plan_b sigue devolviendo algo
para 'pantalon baggy'."""
from app import app

cliente = app.test_client()
payload = {
    "modo": "regalo", "altura": "1.75m", "peso": "75kg", "genero": "Hombre",
    "categoria": "prenda inferior", "tipo_prenda": "pantalon", "subtipo": "",
    "largo": "", "manga": "", "capucha": "", "cierre": "", "corte": "baggy",
    "ocasion": "", "precio": "", "gorro_camino": "", "gorro_colores": [],
    "gorro_outfit": "", "gorro_forma": "",
}
r = cliente.post("/api/recommend", json={**payload, "plan_b": True}).get_json()
print(f"2) Plan B -> recomendaciones: {len(r.get('recomendaciones', []))} | alternativas: {len(r.get('alternativas', []))}")
