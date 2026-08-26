"""Chequeo de que el rate limiting realmente bloquea al pasarse del limite
(no solo que existe el decorator) -- /admin/login, /api/recommend, y de
paso confirma el mensaje generico de error. test_client, nunca un servidor
real. No prueba /api/koko/chat a proposito (para no arriesgar pegarle a la
API real 11 veces en un mismo minuto)."""
import app as m

cliente = m.app.test_client()


def limpiar_limiter():
    # Flask-Limiter con storage en memoria guarda el conteo por proceso --
    # como test_client corre en el MISMO proceso que este script, hay que
    # limpiarlo entre pruebas para que una no contamine a la otra.
    m.limiter.reset()


# --- /admin/login: 6 por minuto (solo POST) ---
limpiar_limiter()
_password_real = m.ADMIN_PASSWORD
m.ADMIN_PASSWORD = "clave-de-prueba-rate-limit"
try:
    codigos = []
    for _ in range(7):
        resp = cliente.post("/admin/login", data={"password": "incorrecta-a-proposito"})
        codigos.append(resp.status_code)
    assert codigos[:6] == [200] * 6, codigos
    assert codigos[6] == 429, codigos
    print("OK: /admin/login deja pasar 6 intentos por minuto y bloquea el 7mo con 429.")

    resp_bloqueado = cliente.post("/admin/login", data={"password": "incorrecta-a-proposito"})
    assert resp_bloqueado.status_code == 429
    texto = resp_bloqueado.get_data(as_text=True)
    assert "contraseñ" not in texto.lower() and "password" not in texto.lower()
    assert "Demasiadas peticiones" in texto
    print("OK: el bloqueo muestra un mensaje generico, sin ninguna pista sobre la contraseña.")

    # El GET (solo ver el formulario) no esta limitado -- sigue andando.
    resp_get = cliente.get("/admin/login")
    assert resp_get.status_code == 200
    print("OK: GET /admin/login (solo ver el formulario) no esta limitado.")
finally:
    m.ADMIN_PASSWORD = _password_real

# --- /api/recommend: 20 por minuto ---
limpiar_limiter()
payload = {
    "modo": "yo", "email": "", "perfil": {"genero": "Hombre", "edad": 22, "altura": "1.75m", "peso": "70kg"},
    "categoria": "prenda superior", "tipo_prenda": "polera", "corte": "", "ocasion": "", "precio": "",
}
codigos = []
for _ in range(21):
    resp = cliente.post("/api/recommend", json=payload)
    codigos.append(resp.status_code)
assert codigos[:20] == [200] * 20, codigos.count(200)
assert codigos[20] == 429, codigos[20]
print("OK: /api/recommend deja pasar 20 peticiones por minuto y bloquea la 21ra con 429.")

resp_json = cliente.post("/api/recommend", json=payload)
assert resp_json.status_code == 429
data_json = resp_json.get_json()
assert "error" in data_json
print("OK: /api/recommend bloqueado devuelve JSON (no HTML), consistente con el resto de /api/*.")

limpiar_limiter()
print("\nTodo OK.")
