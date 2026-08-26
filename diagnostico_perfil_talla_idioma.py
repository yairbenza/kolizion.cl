"""Chequeo acotado: 1) 'orientacion_sexual' desaparecio de todas partes,
2) /api/estimar_talla funciona, 3) preferencia_idioma_koko detecta bien.
test_client, nunca un servidor real (ver CLAUDE.md)."""
import app as m

cliente = m.app.test_client()

# 1) orientacion_sexual ya no aparece en index.html ni en perfil.js.
html = cliente.get("/").get_data(as_text=True)
assert "orientacion_sexual" not in html
assert "Orientación sexual" not in html
js = cliente.get("/static/perfil.js").get_data(as_text=True)
assert "orientacion_sexual" not in js
print("OK: 'orientacion_sexual' ya no aparece en index.html ni perfil.js.")

# 2) /api/estimar_talla.
resp = cliente.get("/api/estimar_talla?genero=Hombre&peso=70kg&altura=1.75m")
assert resp.status_code == 200
tallas = resp.get_json()["tallas"]
assert isinstance(tallas, list) and len(tallas) > 0, tallas
print(f"OK: /api/estimar_talla devuelve {tallas} para Hombre/70kg/1.75m.")

resp_vacio = cliente.get("/api/estimar_talla?genero=&peso=&altura=")
assert resp_vacio.get_json()["tallas"] == []
print("OK: sin peso/altura, devuelve lista vacia (no rompe).")

# 3) preferencia_idioma_koko: sin historial -> None; con "hablame como chileno" -> "chileno".
email_sin = "diag-idioma-sin@test.cl"
assert m.preferencia_idioma_koko(email_sin) is None
print("OK: sin historial, preferencia_idioma es None.")

email_con = "diag-idioma-con@test.cl"
m.reiniciar_chat_koko(email_con)  # por si quedo algo de una corrida anterior
m.guardar_mensaje_chat(email_con, "usuario", "hola")
m.guardar_mensaje_chat(email_con, "koko", "hola! como estas")
m.guardar_mensaje_chat(email_con, "usuario", "oye hablame como chileno de ahora en adelante")
assert m.preferencia_idioma_koko(email_con) == "chileno"
print("OK: con 'hablame como chileno' en el historial, preferencia_idioma es 'chileno'.")

# 4) La ruta /api/koko/historial_chat trae el campo nuevo sin romper el viejo.
resp2 = cliente.get(f"/api/koko/historial_chat?email={email_con}")
data2 = resp2.get_json()
assert data2["preferencia_idioma"] == "chileno"
assert len(data2["mensajes"]) == 3
print("OK: /api/koko/historial_chat trae 'preferencia_idioma' sin romper 'mensajes'.")

# 5) Piezas del frontend de /perfil.
perfil_js = cliente.get("/static/perfil.js").get_data(as_text=True)
for pieza in ["agregarTallaEstimada", "agregarPreferenciaIdiomaKoko", "/api/estimar_talla", "preferencia_idioma"]:
    assert pieza in perfil_js, f"falta {pieza} en perfil.js"
print("OK: perfil.js trae las funciones nuevas.")

# Limpieza: no dejar datos de prueba en data/chats_koko.json.
m.reiniciar_chat_koko(email_con)
m.reiniciar_chat_koko(email_sin)

print("\nTodo OK.")
