"""Chequeo de "Marca de autor" (insignia + filtro estricto "mostrar solo")
y del refinamiento de "Priorizar materiales de calidad" con gramaje GSM
(2026-08-19). test_client, nunca un servidor real."""
import app as m

cliente = m.app.test_client()

# --- 1) Catalogo: marca_autor en todos, gramaje solo en polera/camiseta de algodon 100% ---
catalog = m.load_json(m.CATALOG_PATH)
assert all("marca_autor" in p for p in catalog)
marcados = [p for p in catalog if p["marca_autor"]]
assert marcados and len(marcados) < len(catalog), "deberia ser variado, ni 0 ni todos"
print(f"OK: marca_autor presente en los {len(catalog)} productos, variado ({len(marcados)} marcados).")

con_gramaje = [p for p in catalog if "gramaje_gsm" in p]
assert con_gramaje, "deberia haber productos con gramaje"
assert all(p["categoria"] in ("polera", "camiseta") and p["material"] == "algodon_100" for p in con_gramaje)
sin_gramaje_otras_categorias = [p for p in catalog if p["categoria"] not in ("polera", "camiseta") and "gramaje_gsm" in p]
assert not sin_gramaje_otras_categorias, "gramaje no deberia existir fuera de polera/camiseta"
print(f"OK: gramaje_gsm solo en poleras/camisetas de algodon 100% ({len(con_gramaje)} productos), nunca en otras categorias.")

# --- 2) _algodon_buena_calidad / _texto_gramaje ---
assert m._algodon_buena_calidad({"categoria": "polera", "material": "algodon_100", "gramaje_gsm": 220}) is True
assert m._algodon_buena_calidad({"categoria": "polera", "material": "algodon_100", "gramaje_gsm": 150}) is False
assert m._algodon_buena_calidad({"categoria": "chaqueta", "material": "algodon_100", "gramaje_gsm": 300}) is False, "chaqueta no tiene umbral definido"
assert m._algodon_buena_calidad({"categoria": "polera", "material": "poliester", "gramaje_gsm": 220}) is False
assert m._algodon_buena_calidad({"categoria": "polera", "material": "algodon_100"}) is False, "sin gramaje cargado, no se asume nada"
print("OK: _algodon_buena_calidad solo aplica a polera/camiseta + algodon 100% + >=180 GSM, nunca inventa para otras prendas.")

assert m._texto_gramaje({"gramaje_gsm": 220}) == "220 GSM — algodón grueso de calidad"
assert m._texto_gramaje({"gramaje_gsm": 150}) == "150 GSM — algodón liviano"
assert m._texto_gramaje({}) == ""
print("OK: _texto_gramaje arma el texto de la ficha, vacio si no hay dato.")

# --- 3) filtrar_por_marca_autor: estricto, oculta lo que no cumple ---
sin_filtrar = m.filtrar_por_marca_autor(catalog, False)
assert len(sin_filtrar) == len(catalog)
filtrado = m.filtrar_por_marca_autor(catalog, True)
assert len(filtrado) == len(marcados)
assert all(p["marca_autor"] for p in filtrado)
print("OK: filtrar_por_marca_autor no toca nada si esta apagado, y oculta todo lo que no es marca_autor si esta prendido (filtro estricto, a diferencia de material).")

# --- 4) elegir_candidatos: con priorizar_material_natural, el algodon de buen gramaje queda primero ---
candidatos = m.elegir_candidatos(
    "", "polera", catalog, cantidad=15, categoria_pedida="prenda superior",
    priorizar_material_natural=True,
)
primeros_no_buena_calidad = [i for i, p in enumerate(candidatos) if not m._algodon_buena_calidad(p) and m._material_es_natural(p)]
# Todo lo "buena calidad" (algodon >=180 GSM) deberia estar antes que lo natural-pero-no-buena-calidad.
if primeros_no_buena_calidad:
    idx_primer_no_calidad = primeros_no_buena_calidad[0]
    hay_buena_calidad_despues = any(m._algodon_buena_calidad(p) for p in candidatos[idx_primer_no_calidad:])
    assert not hay_buena_calidad_despues, "un producto de buena calidad quedo despues de uno natural-pero-no-buena-calidad"
print("OK: dentro de los materiales naturales, el algodon de buen gramaje (>=180 GSM) queda primero.")

# --- 5) /api/recommend: ambos flags juntos, extremo a extremo ---
payload_base = {
    "modo": "regalo", "genero": "Hombre", "peso": "", "altura": "",
    "categoria": "prenda superior", "tipo_prenda": "polera", "subtipo": "", "largo": "",
    "manga": "", "capucha": "", "cierre": "", "corte": "", "ocasion": "", "precio": "",
    "gorro_camino": "", "gorro_colores": [], "gorro_outfit": "", "gorro_forma": "",
}
resp_solo_autor = cliente.post("/api/recommend", json=dict(payload_base, solo_marca_autor=True))
assert resp_solo_autor.status_code == 200
recs_autor = resp_solo_autor.get_json()["recomendaciones"]
assert recs_autor and all(r["marca_autor"] for r in recs_autor)
print("OK: /api/recommend con solo_marca_autor=True devuelve solo productos marcados.")

resp_ambos = cliente.post("/api/recommend", json=dict(payload_base, solo_marca_autor=True, priorizar_material_natural=True))
assert resp_ambos.status_code == 200
recs_ambos = resp_ambos.get_json()["recomendaciones"]
assert recs_ambos and all(r["marca_autor"] for r in recs_ambos)
print("OK: los 2 filtros funcionan juntos sin romperse (solo marca de autor + priorizar material).")

resp_default = cliente.post("/api/recommend", json=payload_base)
assert resp_default.status_code == 200
print("OK: sin mandar ninguno de los 2 flags (compatibilidad hacia atras), /api/recommend sigue funcionando igual.")

# --- 6) index.html: checkboxes presentes en ambos formularios ---
html = cliente.get("/").get_data(as_text=True)
for campo in ['id="solo-marca-autor-yo"', 'id="solo-marca-autor-regalo"']:
    assert campo in html, f"falta {campo} en index.html"
print("OK: el checkbox 'Mostrar solo marcas de autor' esta en ambos formularios (yo y regalo).")

print("\nTodo OK.")
