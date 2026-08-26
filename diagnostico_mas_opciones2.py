"""Segunda vuelta del diagnostico: prueba varias combinaciones realistas
(genero, precio, talla) para 'pantalon baggy' y ve si alguna deja el Plan B
realmente vacio -- y si es asi, por que (poca oferta real, o filtro de
talla/precio muy restrictivo)."""
import itertools

from app import app, CATALOG_PATH, load_json

cliente = app.test_client()
catalog = load_json(CATALOG_PATH)

print("=== Cuantos pantalon+baggy hay por genero ===")
for genero in ("hombre", "mujer", "unisex"):
    n = sum(
        1 for p in catalog
        if p["categoria"] == "pantalon" and "baggy" in p.get("corte", "").lower()
        and p["genero"].lower() in (genero, "unisex")
    )
    print(f"  {genero}: {n}")
print()

combos = [
    {"genero": "Mujer", "altura": "1.60m", "peso": "55kg", "precio": ""},
    {"genero": "Mujer", "altura": "1.60m", "peso": "55kg", "precio": "25000"},
    {"genero": "Hombre", "altura": "1.90m", "peso": "100kg", "precio": ""},
    {"genero": "Hombre", "altura": "1.75m", "peso": "75kg", "precio": "25000"},
]

for combo in combos:
    payload = {
        "modo": "regalo", "categoria": "prenda inferior", "tipo_prenda": "pantalon",
        "subtipo": "", "largo": "", "manga": "", "capucha": "", "cierre": "",
        "corte": "baggy", "ocasion": "", "gorro_camino": "", "gorro_colores": [],
        "gorro_outfit": "", "gorro_forma": "",
        **combo,
    }
    r1 = cliente.post("/api/recommend", json=payload).get_json()
    r2 = cliente.post("/api/recommend", json={**payload, "plan_b": True}).get_json()
    print(f"--- {combo} ---")
    print(f"  primaria: {len(r1.get('recomendaciones', []))} | "
          f"plan_b recomendaciones: {len(r2.get('recomendaciones', []))} | "
          f"alternativas: {len(r2.get('alternativas', []))} | "
          f"sin_talla: {r2.get('sin_talla')}")
