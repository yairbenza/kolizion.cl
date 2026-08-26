"""Chequeo acotado del panel de admin nuevo: login/logout protegen las
rutas, filtro de fecha funciona, desglose por producto y resumen copiable
se arman bien. test_client, nunca un servidor real (ver CLAUDE.md)."""
import json
from datetime import datetime, timedelta, timezone

import app as m

cliente = m.app.test_client()

# 1) Sin sesion, /admin/tiendas y /admin/clics redirigen a /admin/login.
for ruta in ["/admin/tiendas", "/admin/clics"]:
    resp = cliente.get(ruta, follow_redirects=False)
    assert resp.status_code == 302, (ruta, resp.status_code)
    assert resp.headers["Location"].startswith("/admin/login"), resp.headers["Location"]
print("OK: sin sesion, /admin/tiendas y /admin/clics redirigen al login.")

# 2) Con ADMIN_PASSWORD vacia, el login rechaza cualquier intento, sin
# importar la clave. Se fuerza vacia aca (en vez de asumir el estado real
# del .env, que ya puede tener una contraseña real configurada) para que
# este chequeo no dependa de si el usuario ya la configuro o no.
_password_real = m.ADMIN_PASSWORD
m.ADMIN_PASSWORD = ""
resp = cliente.post("/admin/login", data={"password": "lo-que-sea"})
assert resp.status_code == 200
assert "ADMIN_PASSWORD" in resp.get_data(as_text=True)
print("OK: con ADMIN_PASSWORD vacia, el login queda deshabilitado (no deja pasar con nada).")

# 3) Con una contraseña configurada: clave incorrecta rechaza, correcta entra.
m.ADMIN_PASSWORD = "clave-de-prueba-123"
try:
    resp = cliente.post("/admin/login", data={"password": "incorrecta"})
    assert resp.status_code == 200
    assert "Contraseña incorrecta" in resp.get_data(as_text=True)
    print("OK: clave incorrecta muestra error y no deja pasar.")

    resp = cliente.post("/admin/login", data={"password": "clave-de-prueba-123"}, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/admin/tiendas"
    print("OK: clave correcta redirige a /admin/tiendas.")

    # 4) Con sesion, ambas paginas cargan bien.
    resp = cliente.get("/admin/tiendas")
    assert resp.status_code == 200
    resp = cliente.get("/admin/clics")
    assert resp.status_code == 200
    print("OK: con sesion, /admin/tiendas y /admin/clics cargan (200).")

    # 5) Logout saca la sesion.
    resp = cliente.post("/admin/logout", follow_redirects=False)
    assert resp.status_code == 302 and resp.headers["Location"] == "/admin/login"
    resp = cliente.get("/admin/tiendas", follow_redirects=False)
    assert resp.status_code == 302
    print("OK: logout saca la sesion, /admin/tiendas vuelve a pedir login.")

    # Vuelve a entrar para probar el panel de clics con datos reales.
    cliente.post("/admin/login", data={"password": "clave-de-prueba-123"})
finally:
    pass

# 6) Panel de clics: filtro de fecha + desglose por producto + resumen.
# Datos de prueba: se restauran los archivos originales al final.
respaldo_tiendas = m.TIENDAS_PATH.read_text(encoding="utf-8") if m.TIENDAS_PATH.exists() else None
respaldo_clics = m.CLICS_TIENDAS_PATH.read_text(encoding="utf-8") if m.CLICS_TIENDAS_PATH.exists() else None

try:
    tiendas = m.cargar_tiendas()
    tiendas["tienda-diagnostico"] = {"nombre": "Tienda Diagnóstico", "tipo": "con_sitio_web", "dominio": "x.cl", "codigo_descuento": "X10"}
    m.guardar_tiendas(tiendas)

    ahora = datetime.now(timezone.utc)
    clics = [
        {"tienda": "tienda-diagnostico", "producto": "poleron-negro", "fecha": (ahora - timedelta(days=1)).isoformat()},
        {"tienda": "tienda-diagnostico", "producto": "poleron-negro", "fecha": (ahora - timedelta(days=2)).isoformat()},
        {"tienda": "tienda-diagnostico", "producto": "gorro-plano", "fecha": (ahora - timedelta(days=3)).isoformat()},
        {"tienda": "tienda-diagnostico", "producto": "gorro-plano", "fecha": (ahora - timedelta(days=20)).isoformat()},  # fuera de 7 y 14 dias
    ]
    m.CLICS_TIENDAS_PATH.write_text(json.dumps(clics, ensure_ascii=False, indent=2), encoding="utf-8")

    html_7 = cliente.get("/admin/clics?rango=7").get_data(as_text=True)
    assert "3 clics" in html_7, "deberian contarse 3 clics en los ultimos 7 dias"
    assert "poleron-negro — 2 clic" in html_7
    assert "gorro-plano — 1 clic" in html_7
    assert "Esta semana te mandamos 3 clics" in html_7
    print("OK: rango=7 cuenta 3 clics, desglose por producto correcto, resumen correcto.")

    html_todo = cliente.get("/admin/clics?rango=todo").get_data(as_text=True)
    assert "4 clics" in html_todo
    assert "En total te mandamos 4 clics" in html_todo
    print("OK: rango=todo cuenta los 4 clics (incluye el de hace 20 dias).")

finally:
    if respaldo_tiendas is not None:
        m.TIENDAS_PATH.write_text(respaldo_tiendas, encoding="utf-8")
    if respaldo_clics is not None:
        m.CLICS_TIENDAS_PATH.write_text(respaldo_clics, encoding="utf-8")
    m.ADMIN_PASSWORD = _password_real

print("\nTodo OK.")
