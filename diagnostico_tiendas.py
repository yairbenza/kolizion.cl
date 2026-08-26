"""Chequeo puntual del sistema de tiendas (con/sin sitio web, redirect,
reporte manual). Usa el test client de Flask -- no toca ningun puerto ni
proceso real, no interfiere con el servidor que ya esta corriendo."""
from app import app, cargar_tiendas, cargar_clics_tiendas, cargar_reportes_manuales, guardar_tiendas

# Limpieza de datos de prueba de corridas anteriores.
tiendas = cargar_tiendas()
tiendas.pop("tienda-prueba", None)
tiendas.pop("tienda-sin-web-prueba", None)
guardar_tiendas(tiendas)

cliente = app.test_client()

print("=== Agregar tienda CON sitio web ===")
r1 = cliente.post("/admin/tiendas/nueva", data={
    "id": "tienda-prueba", "nombre": "Tienda Prueba", "tipo": "con_sitio_web",
    "dominio": "tienda-prueba.cl", "codigo_descuento": "KOLIZION10",
})
print("Status redirect:", r1.status_code)
print("Guardada:", cargar_tiendas().get("tienda-prueba"))

print("\n=== /ir/ redirige con el descuento aplicado ===")
r2 = cliente.get("/ir/tienda-prueba/pantalon-cargo-negro")
print("Status:", r2.status_code, "-> Location:", r2.headers.get("Location"))
clics = [c for c in cargar_clics_tiendas() if c["tienda"] == "tienda-prueba"]
print("Clic registrado:", clics[-1] if clics else None)

print("\n=== Agregar tienda SIN sitio web + reporte manual ===")
cliente.post("/admin/tiendas/nueva", data={
    "id": "tienda-sin-web-prueba", "nombre": "Tienda Sin Web Prueba", "tipo": "sin_sitio_web",
})
r3 = cliente.post("/admin/tiendas/tienda-sin-web-prueba/reporte", data={"fecha": "2026-08-10", "monto": "45000"})
print("Status redirect:", r3.status_code)
reportes = [r for r in cargar_reportes_manuales() if r["tienda"] == "tienda-sin-web-prueba"]
print("Reporte guardado:", reportes[-1] if reportes else None)

print("\n=== Pagina /admin/tiendas carga bien ===")
r4 = cliente.get("/admin/tiendas")
print("Status:", r4.status_code)
print("Contiene ambas tiendas:", b"Tienda Prueba" in r4.data and b"Tienda Sin Web Prueba" in r4.data)

# Limpieza final.
tiendas = cargar_tiendas()
tiendas.pop("tienda-prueba", None)
tiendas.pop("tienda-sin-web-prueba", None)
guardar_tiendas(tiendas)
print("\n(datos de prueba limpiados)")
