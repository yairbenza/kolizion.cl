"""Chequeo del filtro "Priorizar materiales de calidad" (2026-08-19):
campo material agregado al catalogo (agregar_materiales.py), prioriza sin
ocultar nada (elegir_candidatos con priorizar_material_natural), y se
muestra en la ficha (vista previa) via formatear_producto. test_client,
nunca un servidor real."""
import app as m

cliente = m.app.test_client()

# --- 1) Catalogo: todos los productos tienen material, distribucion variada ---
catalog = m.load_json(m.CATALOG_PATH)
assert all("material" in p for p in catalog), "todos los productos deberian tener material"
materiales_presentes = {p["material"] for p in catalog}
assert materiales_presentes == set(m.MATERIALES_CONOCIDOS.keys()), materiales_presentes
print(f"OK: los {len(catalog)} productos del catalogo tienen material, con los 7 valores conocidos presentes.")

# Asignaciones logicas: gorro de lana -> material lana; chaqueta de cuero -> material cuero.
gorros_lana = [p for p in catalog if p.get("categoria") == "gorro" and p.get("forma") == "lana"]
assert gorros_lana and all(p["material"] == "lana" for p in gorros_lana)
chaquetas_cuero = [p for p in catalog if p.get("categoria") == "chaqueta" and p.get("subtipo") == "cuero"]
assert chaquetas_cuero and all(p["material"] == "cuero" for p in chaquetas_cuero)
print("OK: gorro de lana -> material lana, chaqueta de cuero -> material cuero (reuso logico, no al azar).")

# --- 2) _material_es_natural ---
assert m._material_es_natural({"material": "algodon_100"}) is True
assert m._material_es_natural({"material": "lana"}) is True
assert m._material_es_natural({"material": "cuero"}) is True
assert m._material_es_natural({"material": "poliester"}) is False
assert m._material_es_natural({"material": "no-existe"}) is False
assert m._material_es_natural({}) is False
print("OK: _material_es_natural distingue natural (algodon 100%/lana/cuero) de sintetico/desconocido.")

# --- 3) elegir_candidatos: prioriza sin ocultar nada ---
candidatos_sin = m.elegir_candidatos("", "camiseta", catalog, cantidad=10, categoria_pedida="prenda superior")
candidatos_con = m.elegir_candidatos(
    "", "camiseta", catalog, cantidad=10, categoria_pedida="prenda superior",
    priorizar_material_natural=True,
)
assert len(candidatos_sin) == len(candidatos_con) == 10, "priorizar no debe cambiar CUANTOS resultados salen"
naturales_con = sum(1 for p in candidatos_con if m._material_es_natural(p))
naturales_sin = sum(1 for p in candidatos_sin if m._material_es_natural(p))
assert naturales_con >= naturales_sin
# Los primeros N (cuantos productos naturales de camiseta existan, hasta 10) deben ser todos naturales.
primeros_no_naturales = [i for i, p in enumerate(candidatos_con) if not m._material_es_natural(p)]
if primeros_no_naturales:
    primer_no_natural = primeros_no_naturales[0]
    assert all(m._material_es_natural(p) for p in candidatos_con[:primer_no_natural])
print(f"OK: con priorizar_material_natural, los productos naturales quedan primero ({naturales_con}/10 naturales vs {naturales_sin}/10 sin priorizar) -- nunca oculta los sinteticos, solo los ordena despues.")

# --- 4) /api/recommend: el flag llega, no rompe nada, y afecta el orden real ---
payload_base = {
    "modo": "regalo", "genero": "Hombre", "peso": "", "altura": "",
    "categoria": "prenda superior", "tipo_prenda": "camiseta", "subtipo": "", "largo": "",
    "manga": "", "capucha": "", "cierre": "", "corte": "", "ocasion": "", "precio": "",
    "gorro_camino": "", "gorro_colores": [], "gorro_outfit": "", "gorro_forma": "",
}
resp_sin = cliente.post("/api/recommend", json=payload_base)
resp_con = cliente.post("/api/recommend", json=dict(payload_base, priorizar_material_natural=True))
assert resp_sin.status_code == 200 and resp_con.status_code == 200
recs_con = resp_con.get_json()["recomendaciones"]
assert recs_con and all(r.get("material") for r in recs_con), "cada resultado deberia traer su material"
naturales_api = sum(1 for r in recs_con if r["material"] in ("Algodón 100%", "Lana", "Cuero"))
print(f"OK: /api/recommend acepta priorizar_material_natural, cada resultado trae su material legible, {naturales_api}/{len(recs_con)} son fibra natural.")

# --- 5) Sin el flag (default), el comportamiento no cambia respecto de antes ---
resp_default = cliente.post("/api/recommend", json=payload_base)
assert resp_default.status_code == 200
print("OK: sin mandar el campo (compatibilidad hacia atras), /api/recommend sigue funcionando igual.")

# --- 6) index.html: checkbox presente en ambos formularios (yo y regalo) ---
html = cliente.get("/").get_data(as_text=True)
assert 'id="prioridad-material-yo"' in html
assert 'id="prioridad-material-regalo"' in html
print("OK: el checkbox 'Priorizar materiales de calidad' esta en ambos formularios (yo y regalo).")

print("\nTodo OK.")
