"""Chequeo acotado del boton 'Reiniciar conversacion': la ruta borra el
historial guardado, y las piezas del frontend estan presentes. test_client,
nunca un servidor real (ver CLAUDE.md)."""
import app as m

cliente = m.app.test_client()
email = "diagnostico-reiniciar@test.cl"

# 1) Guardar algunos mensajes de prueba directo (sin gastar en la API).
m.guardar_mensaje_chat(email, "usuario", "hola")
m.guardar_mensaje_chat(email, "koko", "hola! como estas")
historial = m.cargar_historial_chat(email)
assert len(historial) == 2, historial
print("OK: historial de prueba guardado (2 mensajes).")

# 2) Llamar la ruta nueva.
resp = cliente.post("/api/koko/reiniciar", json={"email": email})
assert resp.status_code == 200
assert resp.get_json() == {"ok": True}
print("OK: /api/koko/reiniciar responde ok.")

# 3) El historial quedo vacio.
historial_despues = m.cargar_historial_chat(email)
assert historial_despues == [], historial_despues
print("OK: el historial quedo vacio despues de reiniciar.")

# 4) Sin email no rompe (no-op).
resp2 = cliente.post("/api/koko/reiniciar", json={"email": ""})
assert resp2.status_code == 200
print("OK: sin email no rompe.")

# 5) Piezas del frontend.
html = cliente.get("/").get_data(as_text=True)
assert 'id="btn-reiniciar-koko"' in html
js = cliente.get("/static/koko.js").get_data(as_text=True)
for pieza in ["reiniciarConversacionKoko", "btn-reiniciar-koko", "/api/koko/reiniciar", "window.confirm"]:
    assert pieza in js, f"falta {pieza} en koko.js"
print("OK: boton e icono presentes en index.html y koko.js.")

print("\nTodo OK.")
