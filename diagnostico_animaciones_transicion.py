"""Chequeo acotado de las 3 animaciones nuevas: redireccion a tienda,
rebote de favoritos, y esqueleto de carga. test_client, nunca un servidor
real (ver CLAUDE.md)."""
import app as m

cliente = m.app.test_client()

# 1) Esqueleto de carga: presente en las 5 paginas, spinner viejo ya no.
for ruta in ["/", "/resultados", "/vitrina", "/perfil", "/favoritos"]:
    html = cliente.get(ruta).get_data(as_text=True)
    assert 'id="cargando"' in html, f"falta #cargando en {ruta}"
    assert 'id="cargando-texto"' in html, f"falta #cargando-texto en {ruta}"
    assert "skeleton-lista" in html, f"falta el esqueleto en {ruta}"
    assert 'class="spinner"' not in html, f"todavia queda el spinner viejo en {ruta}"
print("OK: esqueleto de carga presente en las 5 paginas, spinner viejo eliminado.")

css = cliente.get("/static/style.css").get_data(as_text=True)
for pieza in [".skeleton-card", "@keyframes skeleton-brillo", "@keyframes girar"]:
    esperado = pieza != "@keyframes girar"
    assert (pieza in css) == esperado, f"{pieza} -> esperado presente={esperado}"
print("OK: CSS del esqueleto presente, @keyframes girar (spinner viejo) eliminado.")

# 2) Redireccion a tienda: modal presente donde hay tarjetas, no en index/perfil.
for ruta in ["/resultados", "/vitrina", "/favoritos"]:
    html = cliente.get(ruta).get_data(as_text=True)
    assert 'id="modal-redireccion"' in html, f"falta el modal de redireccion en {ruta}"
    assert 'id="redireccion-cuenta"' in html
for ruta in ["/", "/perfil"]:
    html = cliente.get(ruta).get_data(as_text=True)
    assert 'id="modal-redireccion"' not in html, f"el modal de redireccion no deberia estar en {ruta}"
print("OK: modal de redireccion solo donde hay tarjetas de producto.")

comun_js = cliente.get("/static/comun.js").get_data(as_text=True)
for pieza in ["abrirEnlaceConAnimacion", "REDIRECCION_PASOS", "vpLinkActual", "vpTiendaActual"]:
    assert pieza in comun_js, f"falta {pieza} en comun.js"
vitrina_js = cliente.get("/static/vitrina.js").get_data(as_text=True)
assert "abrirEnlaceConAnimacion" in vitrina_js
print("OK: JS de redireccion presente en comun.js y vitrina.js.")

# 3) Rebote de favoritos.
assert "favorito-pulso" in css
assert "classList.add(\"pulso\")" in comun_js
print("OK: animacion de favoritos presente.")

print("\nTodo OK.")
