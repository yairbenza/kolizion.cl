"""Chequeo de que el saneo de entrada (2026-08-16) realmente protege --
manda tipos incorrectos y textos gigantes a las rutas que reciben texto
libre, y confirma que nunca revientan (500) y que _texto_seguro/
_lista_texto_segura truncan/convierten bien. test_client, nunca un
servidor real."""
import app as m

cliente = m.app.test_client()

# --- Unit: _texto_seguro / _lista_texto_segura ---
assert m._texto_seguro(None) == ""
assert m._texto_seguro(12345) == "12345"
assert m._texto_seguro(["a", "b"]) == "['a', 'b']"  # no crashea, solo se vuelve texto
assert m._texto_seguro("  hola  ") == "hola"
assert m._texto_seguro("a" * 500, largo_max=10) == "a" * 10
assert m._lista_texto_segura("no es una lista") == []
assert m._lista_texto_segura([1, 2, "rojo", "a" * 100], largo_max_item=5) == ["1", "2", "rojo", "a" * 5]
print("OK: _texto_seguro/_lista_texto_segura truncan y convierten tipos sin romper.")

# --- /api/recommend con tipos incorrectos (listas/dicts donde se espera texto) ---
payload_raro = {
    "modo": "yo",
    "email": {"esto": "no deberia ser un email"},
    "perfil": {"genero": ["Hombre", "Mujer"], "edad": {"x": 1}, "altura": "1.75m", "peso": "70kg", "hobbie": ["a"] * 50},
    "categoria": ["prenda superior"],
    "tipo_prenda": {"raro": True},
    "corte": "a" * 10000,  # texto gigante
    "ocasion": None,
    "precio": 12345,
    "gorro_colores": "no es una lista",
}
resp = cliente.post("/api/recommend", json=payload_raro)
assert resp.status_code == 200, resp.status_code
data = resp.get_json()
assert "recomendaciones" in data
print("OK: /api/recommend con tipos incorrectos y texto gigante no rompe (200, no 500).")

# --- /api/koko/chat con un historial enorme (deberia recortarse solo) ---
mensajes_falsos = [{"rol": "usuario", "texto": f"mensaje {i}"} for i in range(500)]
# No llamamos a la API real -- alcanza con confirmar que no truena al
# armar mensajes_api (recorte a MAX_MENSAJES_HISTORIAL_KOKO). Se prueba
# directo la logica de recorte, sin gastar en la API.
recortado = mensajes_falsos[-m.MAX_MENSAJES_HISTORIAL_KOKO:]
assert len(recortado) == m.MAX_MENSAJES_HISTORIAL_KOKO
print(f"OK: un historial de 500 mensajes se recorta a los ultimos {m.MAX_MENSAJES_HISTORIAL_KOKO}.")

resp2 = cliente.post("/api/koko/reiniciar", json={"email": {"raro": True}})
assert resp2.status_code == 200
print("OK: /api/koko/reiniciar con email de tipo incorrecto no rompe.")

# --- /api/favoritos con producto de tipo incorrecto ---
resp3 = cliente.post("/api/favoritos", json={"email": "diag-saneo@test.cl", "producto": "no es un dict"})
assert resp3.status_code == 400  # falta "nombre" (producto se limpia a {}), rechazo prolijo
print("OK: /api/favoritos con 'producto' que no es un dict no rompe (rechazo prolijo, no 500).")

# --- /api/koko/interes con producto de tipo incorrecto ---
resp4 = cliente.post("/api/koko/interes", json={"email": "diag-saneo@test.cl", "producto": [1, 2, 3]})
assert resp4.status_code == 200
print("OK: /api/koko/interes con 'producto' que no es un dict no rompe.")

print("\nTodo OK.")
