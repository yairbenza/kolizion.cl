"""Prueba de punta a punta CON el arreglo: la misma conversacion real
guardada (hasta el 'ok' que antes fallaba) contra /api/koko/chat de verdad,
y despues /api/recommend con la sugerencia que devuelve -- para confirmar
con una corrida real y exitosa, no solo en teoria."""
import json

import app as m


def imprimir(texto):
    print(str(texto).encode("ascii", errors="replace").decode("ascii"))


historial_real = json.load(open("data/chats_koko.json", encoding="utf-8"))["yairbenza@gmail.com"]
idx_ok = next(i for i, mm in enumerate(historial_real) if mm["texto"].strip().lower() == "ok")
conversacion = historial_real[: idx_ok + 1]

cliente = m.app.test_client()
resp = cliente.post(
    "/api/koko/chat",
    json={
        "email": "yairbenza-diagnostico@gmail.com",  # email de prueba aparte, no toca el historial real
        "perfil": {"genero": "Hombre", "edad": 22, "altura": "1.75m", "peso": "70kg", "hobbie": "skate"},
        "mensajes": conversacion,
    },
)
data = resp.get_json()
imprimir(f"HTTP status: {resp.status_code}")
imprimir(f"respuesta_texto de Koko: {data.get('respuesta_texto')}")
imprimir(f"sugerencia: {data.get('sugerencia')}")

assert data.get("sugerencia"), "Koko deberia haber ofrecido una sugerencia de busqueda"
assert data["sugerencia"]["tipo_prenda"] == "poleron", f"esperaba poleron, salio {data['sugerencia']}"
assert data["sugerencia"]["corte"] == "oversize", f"esperaba oversize, salio {data['sugerencia']}"

sug = data["sugerencia"]
payload = {
    "modo": "yo", "email": "yairbenza-diagnostico@gmail.com",
    "perfil": {"genero": "Hombre", "edad": 22, "altura": "1.75m", "peso": "70kg", "hobbie": "skate"},
    "categoria": sug.get("categoria", ""), "tipo_prenda": sug.get("tipo_prenda", ""),
    "subtipo": "", "largo": "", "manga": "", "capucha": "", "cierre": "",
    "corte": sug.get("corte", ""), "ocasion": "", "precio": "",
    "gorro_camino": "", "gorro_colores": [], "gorro_outfit": "", "gorro_forma": sug.get("forma_gorro", ""),
}
resp2 = cliente.post("/api/recommend", json=payload)
data2 = resp2.get_json()
recs = data2.get("recomendaciones", [])

imprimir(f"\n--- Resultado de /api/recommend con la sugerencia de Koko ---")
imprimir(f"{len(recs)} producto(s) real(es) del catalogo:")
for r in recs:
    imprimir(f"  - {r['nombre']} | {r.get('corte')} | {r.get('precio')} | {r['tienda']}")

assert len(recs) > 0, "Deberia haber encontrado polerones oversize reales del catalogo"
imprimir("\nOK: la conversacion real que antes fallaba ahora encuentra productos reales.")
