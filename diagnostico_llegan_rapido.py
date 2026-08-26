"""Chequeo de "Llegan rapido a ti" (reemplaza al mapa Leaflet que se saco):
_estimar_envio() (comuna/region/alias de Metropolitana/sin match), el panel
admin guardando comuna/region en vez de lat/lng, /api/tiendas_rapido
(orden + bandera direccion_configurada), y de paso /tienda/<id> + /ir/<id>
(que seguian usandose, ya no dependen del mapa). test_client, nunca un
servidor real (ver CLAUDE.md)."""
import app as m

cliente = m.app.test_client()

# --- 1) _estimar_envio(): comuna, region (+ alias Metropolitana), sin match ---
r_comuna = m._estimar_envio("Av. Nueva Providencia 1234, Providencia", "Providencia", "Metropolitana")
assert r_comuna["texto"] == "Envío en 1-2 días", r_comuna
print("OK: misma comuna en la direccion -> envio rapido (1-2 dias).")

r_region = m._estimar_envio("Vivo en Ñuñoa, Región Metropolitana", "Las Condes", "Metropolitana")
assert r_region["texto"] == "Envío en 2-4 días", r_region
print("OK: comuna distinta pero misma region -> envio medio (2-4 dias).")

r_alias = m._estimar_envio("Vivo en Santiago centro", "Las Condes", "Metropolitana")
assert r_alias["texto"] == "Envío en 2-4 días", r_alias
print('OK: alias "Santiago" reconoce la Region Metropolitana aunque no diga el nombre exacto.')

r_otra = m._estimar_envio("Vivo en Concepción", "Providencia", "Metropolitana")
assert r_otra["texto"] == "Envío en 4-7 días", r_otra
print("OK: otra region sin ningun match -> envio lento (4-7 dias).")

r_vacia = m._estimar_envio("", "Providencia", "Metropolitana")
assert r_vacia["texto"] == "Envío en 4-7 días", r_vacia
print("OK: sin direccion escrita, nunca coincide de pura casualidad (nunca compara contra texto vacio).")

# --- 2) Panel admin: comuna/region reemplaza a lat/lng ---
_password_real = m.ADMIN_PASSWORD
m.ADMIN_PASSWORD = "clave-diagnostico-llegan-rapido"
respaldo_tiendas = m.TIENDAS_PATH.read_text(encoding="utf-8") if m.TIENDAS_PATH.exists() else None

try:
    cliente.post("/admin/login", data={"password": "clave-diagnostico-llegan-rapido"})

    tiendas = m.cargar_tiendas()
    tiendas.pop("tienda-rapido-cerca", None)
    tiendas.pop("tienda-rapido-lejos", None)
    tiendas.pop("tienda-rapido-sin-ubicacion", None)
    m.guardar_tiendas(tiendas)

    cliente.post("/admin/tiendas/nueva", data={
        "id": "tienda-rapido-cerca", "nombre": "Tienda Cerca", "tipo": "con_sitio_web",
        "dominio": "tienda-cerca.cl", "codigo_descuento": "CERCA10",
        "comuna": "Providencia", "region": "Metropolitana",
    })
    guardada = m.cargar_tiendas().get("tienda-rapido-cerca")
    assert guardada and guardada.get("comuna") == "Providencia" and guardada.get("region") == "Metropolitana", guardada
    print("OK: /admin/tiendas/nueva guarda comuna/region (ya no lat/lng).")

    cliente.post("/admin/tiendas/nueva", data={
        "id": "tienda-rapido-lejos", "nombre": "Tienda Lejos", "tipo": "sin_sitio_web",
    })
    cliente.post("/admin/tiendas/tienda-rapido-lejos/ubicacion", data={
        "comuna": "Concepción", "region": "Biobío",
    })
    guardada2 = m.cargar_tiendas().get("tienda-rapido-lejos")
    assert guardada2.get("comuna") == "Concepción" and guardada2.get("region") == "Biobío", guardada2
    print("OK: /admin/tiendas/<id>/ubicacion actualiza comuna/region de una tienda ya creada.")

    # Region invalida (no esta en REGIONES_CHILE) se descarta -- nunca guarda basura.
    cliente.post("/admin/tiendas/tienda-rapido-lejos/ubicacion", data={
        "comuna": "Concepción", "region": "Una region que no existe",
    })
    guardada3 = m.cargar_tiendas().get("tienda-rapido-lejos")
    assert guardada3.get("region") == "", guardada3
    print("OK: una region que no esta en la lista fija de Chile se descarta (queda vacia, no guarda basura).")

    cliente.post("/admin/tiendas/nueva", data={
        "id": "tienda-rapido-sin-ubicacion", "nombre": "Tienda Sin Ubicacion", "tipo": "sin_sitio_web",
    })

    # --- 3) /api/tiendas_rapido: orden por cercania + bandera direccion_configurada ---
    resp_sin_direccion = cliente.get("/api/tiendas_rapido")
    data_sin = resp_sin_direccion.get_json()
    assert data_sin["direccion_configurada"] is False
    print("OK: sin direccion en la busqueda, direccion_configurada queda en False.")

    resp = cliente.get("/api/tiendas_rapido?direccion=" + "Vivo en Providencia, Santiago")
    data = resp.get_json()
    assert data["direccion_configurada"] is True
    filas = {f["id"]: f for f in data["tiendas"]}
    assert filas["tienda-rapido-cerca"]["envio_dias"] < filas["tienda-rapido-lejos"]["envio_dias"]
    assert filas["tienda-rapido-cerca"]["envio_dias"] < filas["tienda-rapido-sin-ubicacion"]["envio_dias"]
    ids_ordenados = [f["id"] for f in data["tiendas"]]
    assert ids_ordenados.index("tienda-rapido-cerca") < ids_ordenados.index("tienda-rapido-lejos")
    print("OK: /api/tiendas_rapido ordena las tiendas de mas cerca a mas lejos segun la direccion.")

    # --- 4) /api/tiendas_mapa ya no existe (se saco junto con el mapa) ---
    resp_mapa_viejo = cliente.get("/api/tiendas_mapa")
    assert resp_mapa_viejo.status_code == 404
    print("OK: /api/tiendas_mapa (del mapa que se saco) ya no existe.")

finally:
    if respaldo_tiendas is not None:
        m.TIENDAS_PATH.write_text(respaldo_tiendas, encoding="utf-8")
    else:
        tiendas = m.cargar_tiendas()
        for tid in ("tienda-rapido-cerca", "tienda-rapido-lejos", "tienda-rapido-sin-ubicacion"):
            tiendas.pop(tid, None)
        m.guardar_tiendas(tiendas)
    m.ADMIN_PASSWORD = _password_real

# --- 5) /tienda/<id> y /ir/<id> (regresion -- no dependian del mapa, se mantienen) ---
tiendas = m.cargar_tiendas()
tiendas["tienda-ficha-prueba"] = {"nombre": "Tienda Ficha Prueba", "tipo": "con_sitio_web", "dominio": "ficha.cl", "codigo_descuento": "FICHA10"}
m.guardar_tiendas(tiendas)
try:
    resp_ficha = cliente.get("/tienda/tienda-ficha-prueba")
    assert resp_ficha.status_code == 200
    assert b"Tienda Ficha Prueba" in resp_ficha.data
    print("OK: /tienda/<id> sigue funcionando (a donde llevan las tarjetas de 'Llegan rapido a ti').")

    resp_ir = cliente.get("/ir/tienda-ficha-prueba", follow_redirects=False)
    assert resp_ir.status_code == 302
    assert "ficha.cl" in resp_ir.headers.get("Location", "")
    clics = [c for c in m.cargar_clics_tiendas() if c["tienda"] == "tienda-ficha-prueba"]
    assert clics and clics[-1]["producto"] == "(visita general)"
    print("OK: /ir/<id> (visita general) sigue redirigiendo con descuento y registrando el clic.")

    resp_inexistente = cliente.get("/tienda/no-existe-esta-tienda")
    assert resp_inexistente.status_code in (301, 302)
    print("OK: /tienda/<id> de una tienda que no existe manda de vuelta a /vitrina, no rompe.")
finally:
    tiendas = m.cargar_tiendas()
    tiendas.pop("tienda-ficha-prueba", None)
    m.guardar_tiendas(tiendas)

# --- 6) /vitrina: la fila nueva esta, el mapa Leaflet ya no ---
resp_vitrina = cliente.get("/vitrina")
assert resp_vitrina.status_code == 200
html_vitrina = resp_vitrina.get_data(as_text=True)
assert "Llegan rápido a ti" in html_vitrina
assert "leaflet" not in html_vitrina.lower()
assert "btn-mapa-cerca" not in html_vitrina
print("OK: /vitrina muestra la fila 'Llegan rápido a ti' y ya no carga Leaflet ni el boton del mapa viejo.")

# --- 7) /: el campo Direccion y el boton de ubicacion estan en el perfil ---
resp_index = cliente.get("/")
assert resp_index.status_code == 200
html_index = resp_index.get_data(as_text=True)
assert 'name="direccion"' in html_index
assert 'id="btn-usar-ubicacion"' in html_index
assert 'id="modal-ubicacion-pregunta"' in html_index
print("OK: / tiene el campo Dirección en el perfil, el boton 'Usar mi ubicación actual' y su modal de permiso.")

print("\nTodo OK.")
