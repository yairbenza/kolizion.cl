"""Chequeo acotado: el icono fijo + tour de la guia de bienvenida estan en
las 4 paginas, y la pregunta inicial solo en index.html. test_client, nunca
un servidor real (ver CLAUDE.md)."""
import app as app_module

cliente = app_module.app.test_client()

paginas = ["/", "/perfil", "/vitrina"]
piezas_compartidas = ["btn-abrir-guia", "fab-ayuda", "modal-onboarding-tour", "btn-cerrar-tour", "btn-tour-siguiente"]

for ruta in paginas:
    resp = cliente.get(ruta)
    assert resp.status_code == 200, (ruta, resp.status_code)
    html = resp.get_data(as_text=True)
    for pieza in piezas_compartidas:
        assert pieza in html, f"falta {pieza} en {ruta}"
print("OK: icono + tour presentes en /, /perfil, /vitrina.")

# /resultados necesita datos en sessionStorage para no redirigir -- solo
# chequeamos que sirva bien la plantilla (el JS de redireccion corre en el
# navegador, no en test_client).
resp = cliente.get("/resultados")
assert resp.status_code == 200
html = resp.get_data(as_text=True)
for pieza in piezas_compartidas:
    assert pieza in html, f"falta {pieza} en /resultados"
print("OK: icono + tour presentes en /resultados.")

resp = cliente.get("/")
html = resp.get_data(as_text=True)
assert "modal-onboarding-pregunta" in html
assert html.count('id="modal-onboarding-tour"') == 1
print("OK: pregunta inicial solo en index.html, tour sin duplicar.")

for ruta in ["/perfil", "/vitrina", "/resultados"]:
    html = cliente.get(ruta).get_data(as_text=True)
    assert 'id="modal-onboarding-pregunta"' not in html, f"la pregunta inicial no deberia estar en {ruta}"
print("OK: la pregunta inicial NO aparece en las otras paginas.")

css = cliente.get("/static/style.css").get_data(as_text=True)
for pieza in [".fab-ayuda", ".btn-cerrar-tour", "object-fit: cover"]:
    assert pieza in css, f"falta {pieza} en style.css"
print("OK: CSS nuevo presente.")

print("\nTodo OK.")
