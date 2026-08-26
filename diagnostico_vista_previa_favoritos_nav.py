"""Chequeo acotado de las 2 features nuevas: vista previa rapida (3 fotos)
y la pagina /favoritos + su icono en la barra de nav. test_client, nunca un
servidor real (ver CLAUDE.md)."""
import app as app_module

cliente = app_module.app.test_client()

# 1) /favoritos existe y trae el molde correcto.
resp = cliente.get("/favoritos")
assert resp.status_code == 200, resp.status_code
html = resp.get_data(as_text=True)
for pieza in ["favoritos-lista", "favoritos-vacio", "favoritos-sin-perfil", "id=\"vp-imagen-principal\""]:
    assert pieza in html, f"falta {pieza} en /favoritos"
print("OK: /favoritos carga con su molde + modal de vista previa.")

# 2) La seccion de favoritos YA NO esta en /perfil (se movio).
html_perfil = cliente.get("/perfil").get_data(as_text=True)
for pieza in ["seccion-favoritos", "favoritos-lista"]:
    assert pieza not in html_perfil, f"{pieza} no deberia seguir en /perfil"
print("OK: /perfil ya no trae la seccion de favoritos.")

# 3) La barra de navegacion trae 5 items, con Favoritos entre Vitrina y Mi perfil.
for ruta in ["/", "/vitrina", "/perfil", "/favoritos", "/resultados"]:
    html = cliente.get(ruta).get_data(as_text=True)
    assert 'href="/favoritos"' in html, f"falta el link a /favoritos en {ruta}"
    assert html.count('class="barra-nav-item"') + html.count("barra-nav-item\"") >= 4
    pos_vitrina = html.find('data-ruta="/vitrina"')
    pos_favoritos = html.find('data-ruta="/favoritos"')
    pos_perfil = html.find('data-ruta="/perfil"')
    assert pos_vitrina < pos_favoritos < pos_perfil, f"orden incorrecto en {ruta}"
print("OK: Favoritos aparece entre Vitrina y Mi perfil en todas las paginas.")

# 4) El modal de vista previa esta en resultados/vitrina/favoritos, NO en index/perfil.
for ruta in ["/resultados", "/vitrina", "/favoritos"]:
    html = cliente.get(ruta).get_data(as_text=True)
    assert 'id="modal-vista-previa"' in html, f"falta el modal de vista previa en {ruta}"
for ruta in ["/", "/perfil"]:
    html = cliente.get(ruta).get_data(as_text=True)
    assert 'id="modal-vista-previa"' not in html, f"el modal de vista previa no deberia estar en {ruta}"
print("OK: el modal de vista previa solo esta donde hay tarjetas de producto.")

# 5) JS/CSS traen las piezas nuevas.
comun_js = cliente.get("/static/comun.js").get_data(as_text=True)
for pieza in ["imagenesPreview", "abrirVistaPrevia", "conectarVistaPrevia", "btn-vista-previa"]:
    assert pieza in comun_js, f"falta {pieza} en comun.js"
vitrina_js = cliente.get("/static/vitrina.js").get_data(as_text=True)
assert "btn-vista-previa" in vitrina_js and "conectarVistaPrevia" in vitrina_js
favoritos_js = cliente.get("/static/favoritos.js").get_data(as_text=True)
assert len(favoritos_js) > 0
css = cliente.get("/static/style.css").get_data(as_text=True)
for pieza in [".tarjeta-vista-previa", ".vp-miniatura", ".btn-vista-previa"]:
    assert pieza in css, f"falta {pieza} en style.css"
print("OK: JS y CSS nuevos presentes.")

# 6) Las imagenes variante existen de verdad para un producto real del catalogo.
catalog = app_module.load_json(app_module.CATALOG_PATH)
con_imagen = next(p for p in catalog if p.get("imagen", "").endswith(".svg"))
base = con_imagen["imagen"][len("/static/"):-4]
for sufijo in ("", "-trasera", "-detalle"):
    ruta_archivo = app_module.BASE_DIR / "static" / f"{base}{sufijo}.svg"
    assert ruta_archivo.exists(), f"falta {ruta_archivo}"
print("OK: las 3 variantes de imagen existen en disco para un producto real del catalogo.")

print("\nTodo OK.")
