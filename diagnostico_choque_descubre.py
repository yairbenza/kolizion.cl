"""Chequeo acotado de los 3 cambios: animaciones "choque", frase de cierre
nueva, y el renombre Vitrina->Descubre en lo visible. test_client, nunca un
servidor real (ver CLAUDE.md)."""
import app as app_module

cliente = app_module.app.test_client()

# 1) Animaciones en el CSS.
css = cliente.get("/static/style.css").get_data(as_text=True)
for pieza in ["@keyframes choque-entrada", "@keyframes choque-shake", "animation: choque-entrada", "animation: choque-shake"]:
    assert pieza in css, f"falta {pieza} en style.css"
print("OK: las animaciones choque-entrada/choque-shake estan en el CSS.")

# 2) Frase de cierre nueva en index.html.
html = cliente.get("/").get_data(as_text=True)
assert "El choque de estilos empieza aquí." in html
assert "¿Listo para entrar a la calle?" not in html
print("OK: la frase de cierre nueva esta en index.html.")

# 3) Vitrina -> Descubre en todo lo visible.
for ruta in ["/", "/vitrina", "/perfil", "/favoritos", "/resultados"]:
    html = cliente.get(ruta).get_data(as_text=True)
    assert "<span>Descubre</span>" in html, f"falta el item de nav 'Descubre' en {ruta}"
    assert "<span>Vitrina</span>" not in html, f"todavia dice 'Vitrina' en la nav de {ruta}"
print("OK: la barra de navegacion dice 'Descubre' en las 5 paginas.")

html_vitrina = cliente.get("/vitrina").get_data(as_text=True)
assert "<title>KOLIZION · Descubre</title>" in html_vitrina
assert "<h1>Descubre</h1>" in html_vitrina
print("OK: titulo y <h1> de /vitrina dicen 'Descubre'.")

html_index = cliente.get("/").get_data(as_text=True)
assert "<h2>Descubre</h2>" in html_index  # tour de bienvenida
assert "<h2>La Vitrina</h2>" not in html_index
print("OK: la guia de bienvenida dice 'Descubre' en vez de 'La Vitrina'.")

vitrina_js = cliente.get("/static/vitrina.js").get_data(as_text=True)
assert "Cargando Descubre..." in vitrina_js
assert "cargando Descubre:" in vitrina_js
print("OK: los mensajes de carga de vitrina.js dicen 'Descubre'.")

print("\nTodo OK.")
