"""Chequeo del cambio de enfoque de hobbies -> estilo (2026-08-20): de
"regla positiva que fuerza un corte" a "exclusion suave de sentido comun"
(ver EXCLUSIONES_HOBBY en app.py) -- decision explicita del usuario: mas
confiable que imponer un unico estilo "correcto" por hobby. Las reglas
positivas viejas (REGLAS_HOBBY, ej. musica+rock) siguen existiendo pero
degradadas a sugerencia OPCIONAL para que Koko converse -- YA NO fuerzan
ningun corte en /api/recommend. Mezcla chequeos sin API (exclusiones,
compatibilidad hacia atras) y con API real (Koko ya no se salta la
pregunta del corte, costo)."""
import app as m

cliente = m.app.test_client()


def imprimir(texto):
    print(str(texto).encode("ascii", errors="replace").decode("ascii"))


# --- 1) EXCLUSIONES_HOBBY: exclusion de sentido comun, nunca oculta nada ---
assert m._categorias_deprioritizadas_por_hobby(["arte_cultura"], [], []) == {"bikeshorts"}
assert m._categorias_deprioritizadas_por_hobby(["deportes"], [], ["gym"]) == {"camisa"}
assert m._categorias_deprioritizadas_por_hobby(["gaming"], [], []) == set(), "gaming no deberia excluir nada (pedido explicito)"
assert m._categorias_deprioritizadas_por_hobby(["musica"], ["rock"], []) == set(), "rock no tiene exclusion, solo sugerencia opcional"
assert m._categorias_deprioritizadas_por_hobby(["deportes"], [], ["futbol"]) == set(), "solo 'gym' tiene exclusion validada, no todo 'deportes'"
print("OK: EXCLUSIONES_HOBBY -- arte_cultura excluye bikeshorts, deportes+gym excluye camisa, gaming y otras sub-opciones no excluyen nada.")

catalog = m.load_json(m.CATALOG_PATH)

# --- 2) elegir_candidatos: deprioritiza (mueve al final) pero NUNCA oculta ---
sin_excl = m.elegir_candidatos("", "", catalog, cantidad=len(catalog), categoria_pedida="prenda inferior")
con_excl = m.elegir_candidatos(
    "", "", catalog, cantidad=len(catalog), categoria_pedida="prenda inferior",
    categorias_deprioritizadas={"bikeshorts"},
)
bikeshorts_sin = [i for i, p in enumerate(sin_excl) if p["categoria"] == "bikeshorts"]
bikeshorts_con = [i for i, p in enumerate(con_excl) if p["categoria"] == "bikeshorts"]
assert len(bikeshorts_sin) == len(bikeshorts_con) and len(bikeshorts_con) > 0, "la cantidad de bikeshorts no deberia cambiar (nunca se ocultan)"
assert min(bikeshorts_con) >= min(bikeshorts_sin), "con la exclusion, el primer bikeshorts deberia quedar igual o mas atras"
print(f"OK: con exclusion, los {len(bikeshorts_con)} bikeshorts siguen todos presentes, solo quedan mas atras en el orden (antes en la posicion {min(bikeshorts_sin)}, ahora en la {min(bikeshorts_con)}).")

# Si se pide bikeshorts DIRECTAMENTE (filtro estricto de tipo de prenda), la exclusion no los saca -- siguen siendo el resultado.
candidatos_directos = m.elegir_candidatos(
    "", "bikeshorts", catalog, cantidad=5, categoria_pedida="prenda inferior",
    categorias_deprioritizadas={"bikeshorts"},
)
assert candidatos_directos and all(p["categoria"] == "bikeshorts" for p in candidatos_directos)
print("OK: si el usuario pide bikeshorts directamente, la exclusion de hobby NUNCA los saca (no es un filtro, solo reordena entre varias categorias).")

# --- 3) /api/recommend: la exclusion se aplica automaticamente con el perfil (modo yo), sin checkbox ---
payload_arte = {
    "modo": "yo", "email": "",
    "perfil": {"genero": "Mujer", "edad": 24, "altura": "1.65m", "peso": "58kg", "hobbie": ["arte_cultura"]},
    "categoria": "prenda inferior", "tipo_prenda": "", "subtipo": "", "largo": "",
    "manga": "", "capucha": "", "cierre": "", "corte": "", "ocasion": "", "precio": "",
    "gorro_camino": "", "gorro_colores": [], "gorro_outfit": "", "gorro_forma": "",
}
resp_arte = cliente.post("/api/recommend", json=payload_arte)
assert resp_arte.status_code == 200
print("OK: /api/recommend acepta el hobby 'arte_cultura' y no rompe (exclusion aplicada automaticamente, sin checkbox nuevo).")

# --- 4) REGLAS_HOBBY (rock) YA NO fuerza el corte en /api/recommend -- ahora es solo sugerencia para Koko ---
payload_rock = {
    "modo": "yo", "email": "",
    "perfil": {"genero": "Hombre", "edad": 22, "altura": "1.75m", "peso": "70kg",
               "hobbie": ["musica"], "hobbie_musica_genero": ["rock"]},
    "categoria": "prenda superior", "tipo_prenda": "poleron", "subtipo": "", "largo": "",
    "manga": "", "capucha": "", "cierre": "", "corte": "", "ocasion": "", "precio": "",
    "gorro_camino": "", "gorro_colores": [], "gorro_outfit": "", "gorro_forma": "",
}
resp_rock = cliente.post("/api/recommend", json=payload_rock)
recs_rock = resp_rock.get_json()["recomendaciones"]
cortes_presentes = {r["corte"] for r in recs_rock}
assert len(cortes_presentes) > 1 or "oversize" not in [c.lower() for c in cortes_presentes], (
    f"si TODOS los resultados salieron oversize sin que el usuario lo pidiera, la regla vieja seguiria forzando el corte -- cortes: {cortes_presentes}"
)
print(f"OK: rock + poleron sin corte propio ya NO fuerza 'oversize' -- salen varios cortes mezclados ({cortes_presentes}), el buscador normal decide.")

# --- 5) Perfil legacy (hobbie como texto libre, formato viejo) no rompe ---
payload_legacy = dict(payload_rock)
payload_legacy["perfil"] = dict(payload_rock["perfil"], hobbie="skate, musica", hobbie_musica_genero=None)
resp_legacy = cliente.post("/api/recommend", json=payload_legacy)
assert resp_legacy.status_code == 200
print("OK: un perfil guardado con el formato viejo (hobbie como texto) no rompe /api/recommend.")

# --- 6) index.html: deportes con sub-opciones (gym/futbol/baseball/ski) sigue presente ---
html = cliente.get("/").get_data(as_text=True)
for campo in ['id="hobbie-deportes"', 'id="campo-hobbie-deportes-subtipo"',
              'name="hobbie_deportes_subtipo" value="baseball"', 'name="hobbie_deportes_subtipo" value="ski"',
              'name="hobbie_deportes_subtipo" value="gym"', 'name="hobbie_deportes_subtipo" value="futbol"']:
    assert campo in html, f"falta {campo} en index.html"
print("OK: index.html tiene las sub-opciones de deportes (gym, futbol, baseball, ski).")

# --- 7) Koko: la sugerencia de rock ahora es OPCIONAL -- ya no se salta la pregunta del corte (API real) ---
print("\n" + "=" * 70)
print("Koko con perfil musica+rock, pide un poleron sin especificar corte")
print("=" * 70)
resp = cliente.post("/api/koko/chat", json={
    "email": "diag-hobbies-2@test.cl",
    "perfil": {"genero": "Hombre", "edad": 24, "altura": "1.78m", "peso": "75kg",
               "hobbie": ["musica"], "hobbie_musica_genero": ["rock"]},
    "mensajes": [{"rol": "usuario", "texto": "necesito un poleron"}],
})
data = resp.get_json()
imprimir("Koko: " + data["respuesta_texto"])
print("Sugerencia:", data["sugerencia"])
assert data["sugerencia"] is None, "Koko NO deberia buscar todavia -- sigue sin saber el corte real, la sugerencia de hobby ya no reemplaza la pregunta"
assert "?" in data["respuesta_texto"], "deberia seguir preguntando por el corte, como con cualquier otro usuario"
print("OK: Koko sigue preguntando el corte con normalidad (la sugerencia de rock, si aparece, es solo un plus conversacional, ya no reemplaza la pregunta).\n")

print("Todo OK.")
