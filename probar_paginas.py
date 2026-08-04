"""Prueba en vivo: confirma que / y /resultados renderizan sin error, y
que los archivos estaticos nuevos se sirven bien."""
import urllib.request

for ruta in ["/", "/resultados", "/static/comun.js", "/static/resultados.js", "/static/script.js"]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:5000{ruta}") as resp:
            print(f"[{resp.status}] {ruta} ({len(resp.read())} bytes)")
    except Exception as e:
        print(f"[ERROR] {ruta} -> {e}")
