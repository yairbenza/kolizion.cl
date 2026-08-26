"""Chequeo acotado de la PWA: manifest, iconos, service worker (ruta +
scope), meta tags de iOS, y registro en comun.js. test_client, nunca un
servidor real (ver CLAUDE.md)."""
import json

import app as m

cliente = m.app.test_client()

# 1) manifest.json valido, con los 3 iconos reales.
resp = cliente.get("/static/manifest.json")
assert resp.status_code == 200
manifest = json.loads(resp.get_data(as_text=True))
assert manifest["name"] == "KOLIZION"
assert manifest["display"] == "standalone"
assert manifest["start_url"] == "/"
assert len(manifest["icons"]) == 3
print("OK: manifest.json valido con 3 iconos.")

for icono in manifest["icons"]:
    ruta_relativa = icono["src"].lstrip("/")
    resp_icono = cliente.get(f"/{ruta_relativa}")
    assert resp_icono.status_code == 200, icono["src"]
print("OK: los 3 iconos del manifest se sirven de verdad (200).")

resp_apple = cliente.get("/static/img/icons/apple-touch-icon.png")
assert resp_apple.status_code == 200
print("OK: apple-touch-icon.png se sirve.")

# 2) Service worker en /sw.js (no /static/sw.js), con scope de raiz.
resp_sw = cliente.get("/sw.js")
assert resp_sw.status_code == 200
assert resp_sw.headers.get("Service-Worker-Allowed") == "/"
sw_texto = resp_sw.get_data(as_text=True)
assert "addEventListener(\"fetch\"" in sw_texto
print("OK: /sw.js se sirve con Service-Worker-Allowed: /")

# 3) Las 9 paginas traen el manifest + meta de iOS + icono.
paginas = ["/", "/vitrina", "/perfil", "/favoritos", "/resultados", "/admin/login"]
for ruta in paginas:
    html = cliente.get(ruta).get_data(as_text=True)
    for pieza in [
        'rel="manifest" href="/static/manifest.json"',
        'name="theme-color" content="#0d0d0d"',
        'name="apple-mobile-web-app-capable" content="yes"',
        'rel="apple-touch-icon"',
    ]:
        assert pieza in html, f"falta {pieza} en {ruta}"
print("OK: las paginas principales traen el manifest + meta de iOS.")

# 4) comun.js registra el service worker.
comun_js = cliente.get("/static/comun.js").get_data(as_text=True)
assert 'serviceWorker' in comun_js and 'register("/sw.js")' in comun_js
print("OK: comun.js registra el service worker en /sw.js.")

print("\nTodo OK.")
