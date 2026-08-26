"""Reproduce EXACTO lo que reporto el usuario: "poleron oversize" y
"polerones oversize baratos" en el chat de Koko, contra la API REAL (no un
mock) -- para ver la respuesta y el tool_use tal cual saldrian en la app,
en vez de asumir por que el bug reportado antes "deberia estar arreglado".
Usa app.test_client() (nunca un servidor real, ver CLAUDE.md), pero SI llama
a la API de verdad porque el bug esta en como Koko decide, no solo en el
buscador determinista (ya se probo aparte que ese funciona bien)."""
import sys
import app as app_module


def imprimir(texto):
    print(texto.encode("ascii", errors="replace").decode("ascii"))


def probar(frase):
    imprimir(f"\n{'=' * 70}")
    imprimir(f"MENSAJE DEL USUARIO: {frase!r}")
    imprimir("=" * 70)

    cliente = app_module.app.test_client()
    resp = cliente.post(
        "/api/koko/chat",
        json={
            "email": "diagnostico-oversize@test.cl",
            "perfil": {"genero": "Hombre", "edad": 22, "altura": "1.75m", "peso": "70kg", "hobbie": "skate"},
            "mensajes": [{"rol": "usuario", "texto": frase}],
        },
    )
    data = resp.get_json()
    imprimir(f"HTTP status: {resp.status_code}")
    imprimir(f"respuesta_texto: {data.get('respuesta_texto')}")
    imprimir(f"sugerencia: {data.get('sugerencia')}")

    if data.get("sugerencia"):
        # Simula EXACTO lo que hace koko.js cuando el usuario aprieta
        # "Si, buscar": arma el payload y llama a /api/recommend.
        sug = data["sugerencia"]
        payload = {
            "modo": "yo", "email": "diagnostico-oversize@test.cl",
            "perfil": {"genero": "Hombre", "edad": 22, "altura": "1.75m", "peso": "70kg", "hobbie": "skate"},
            "categoria": sug.get("categoria", ""), "tipo_prenda": sug.get("tipo_prenda", ""),
            "subtipo": "", "largo": "", "manga": "", "capucha": "", "cierre": "",
            "corte": sug.get("corte", ""), "ocasion": "", "precio": "",
            "gorro_camino": "", "gorro_colores": [], "gorro_outfit": "", "gorro_forma": sug.get("forma_gorro", ""),
        }
        resp2 = cliente.post("/api/recommend", json=payload)
        data2 = resp2.get_json()
        recs = data2.get("recomendaciones", [])
        imprimir(f"--> /api/recommend con esa sugerencia: {len(recs)} resultado(s)")
        for r in recs[:5]:
            imprimir(f"    - {r['nombre']} | {r.get('corte')} | {r.get('precio')}")
        return len(recs) > 0
    return None


if __name__ == "__main__":
    resultados = {}
    for frase in ["poleron oversize", "polerones oversize baratos"]:
        resultados[frase] = probar(frase)

    imprimir(f"\n{'=' * 70}")
    imprimir("RESUMEN")
    imprimir("=" * 70)
    for frase, ok in resultados.items():
        estado = "PRODUCTOS ENCONTRADOS" if ok else ("SIN SUGERENCIA / SIN RESULTADOS" if ok is not None else "KOKO NO OFRECIO BUSQUEDA")
        imprimir(f"  {frase!r}: {estado}")
