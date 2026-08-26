"""Chequeo acotado de las 2 features nuevas (onboarding + favoritos):
que las paginas rendericen sin error y que las piezas clave esten
presentes. No levanta un servidor real -- test_client, ver CLAUDE.md."""
import app as app_module

cliente = app_module.app.test_client()

resp = cliente.get("/")
assert resp.status_code == 200, resp.status_code
html = resp.get_data(as_text=True)
for pieza in [
    "modal-onboarding-pregunta", "modal-onboarding-tour", "btn-onboarding-si",
    "btn-onboarding-no", "btn-tour-siguiente", "tour-slide",
]:
    assert pieza in html, f"falta {pieza} en index.html"
print("OK: index.html trae el modal de onboarding.")

resp = cliente.get("/favoritos")
assert resp.status_code == 200, resp.status_code
html = resp.get_data(as_text=True)
for pieza in ["favoritos-lista", "favoritos-vacio"]:
    assert pieza in html, f"falta {pieza} en favoritos.html"
print("OK: favoritos.html trae la seccion de favoritos (movida desde /perfil, 2026-08-09).")

resp = cliente.get("/vitrina")
assert resp.status_code == 200
print("OK: vitrina.html carga bien.")

resp = cliente.get("/resultados")
assert resp.status_code == 200
print("OK: resultados.html carga bien.")

css = cliente.get("/static/style.css").get_data(as_text=True)
for pieza in [".btn-favorito", ".modal-overlay", ".tarjeta-modal", ".tour-punto", ".lista-resultados"]:
    assert pieza in css, f"falta {pieza} en style.css"
print("OK: style.css trae las reglas nuevas.")

for nombre in ["comun.js", "script.js", "vitrina.js", "resultados.js", "perfil.js", "favoritos.js"]:
    js = cliente.get(f"/static/{nombre}").get_data(as_text=True)
    assert len(js) > 0, nombre
print("OK: todos los .js se sirven.")

print("\nTodo OK.")
