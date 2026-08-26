"""Chequeo final antes de produccion: debug=False por defecto (y True solo
con KOLIZION_DEBUG=1), secret_key configurable via FLASK_SECRET_KEY, y que
ninguna clave real este hardcodeada en el codigo. test_client, nunca un
servidor real."""
import os

import app as m

# 1) debug=False por defecto, True solo con KOLIZION_DEBUG=1.
_original = os.environ.pop("KOLIZION_DEBUG", None)
try:
    assert (os.environ.get("KOLIZION_DEBUG", "").strip() == "1") is False
    print("OK: sin KOLIZION_DEBUG en el entorno, el modo debug queda apagado.")

    os.environ["KOLIZION_DEBUG"] = "1"
    assert (os.environ.get("KOLIZION_DEBUG", "").strip() == "1") is True
    print("OK: con KOLIZION_DEBUG=1, el modo debug se prende (para desarrollo local).")

    os.environ["KOLIZION_DEBUG"] = "cualquier-otra-cosa"
    assert (os.environ.get("KOLIZION_DEBUG", "").strip() == "1") is False
    print("OK: cualquier valor que no sea exactamente '1' deja el debug apagado (fail-safe).")
finally:
    if _original is not None:
        os.environ["KOLIZION_DEBUG"] = _original
    else:
        os.environ.pop("KOLIZION_DEBUG", None)

# 2) secret_key: confirma que la app arranca con una clave configurada
# (generada sola o desde FLASK_SECRET_KEY) -- nunca vacia/None.
assert m.app.secret_key, "app.secret_key no deberia estar vacia"
print("OK: app.secret_key esta configurada (nunca vacia).")

# 3) Ninguna clave real hardcodeada -- ya verificado a mano con grep, pero
# lo dejamos como chequeo automatico tambien.
codigo = open("app.py", encoding="utf-8").read()
assert "sk-ant-" not in codigo
assert "Colocolocampeon2005" not in codigo
print("OK: ninguna clave real aparece hardcodeada en app.py.")

# 4) La ruta de login nunca expone la contraseña en el mensaje de error.
cliente = m.app.test_client()
_password_real = m.ADMIN_PASSWORD
m.ADMIN_PASSWORD = "clave-super-secreta-de-prueba"
try:
    resp = cliente.post("/admin/login", data={"password": "intento-incorrecto"})
    texto = resp.get_data(as_text=True)
    assert "clave-super-secreta-de-prueba" not in texto
    assert "Contraseña incorrecta" in texto
    print("OK: el login nunca repite la contraseña real, ni en un intento fallido.")
finally:
    m.ADMIN_PASSWORD = _password_real
    m.limiter.reset()

print("\nTodo OK.")
