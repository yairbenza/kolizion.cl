"""Chequeo del bug reportado (2026-08-17): Koko recomendaba camisa en vez de
chaqueta. Causa real: un mismo mensaje que nombra "chaqueta" Y "camisa"
(comun en conversaciones sobre combinar outfits) hacia que la correccion
determinista devolviera SIEMPRE la que aparece primero en el diccionario
(camisa), sin importar cual era el tema real -- incluso cuando Koko ya
habia entendido bien "chaqueta". Corregido con _valor_o_deteccion() (confia
en la propuesta de Koko si es valida y fue mencionada, en vez de recalcular
a ciegas). De paso: chaqueta ahora tiene subtipos reales (bomber, mezclilla,
cuero). Contra la API real (costo)."""
import app as m

cliente = m.app.test_client()


def imprimir(texto):
    print(str(texto).encode("ascii", errors="replace").decode("ascii"))


def chat(mensajes, email):
    resp = cliente.post("/api/koko/chat", json={"email": email, "mensajes": mensajes})
    return resp.get_json()


print("=" * 70)
print("1) Reproduccion de la conversacion real que fallaba (outfit con camisa Y chaqueta)")
print("=" * 70)
mensajes = [
    {"rol": "usuario", "texto": "hola quiero ir a una fiesta semiformal manana y no se que jeans ponerme"},
]
r1 = chat(mensajes, "diag-chaqueta-1@test.cl")
mensajes.append({"rol": "koko", "texto": r1["respuesta_texto"]})
mensajes.append({"rol": "usuario", "texto": "mmmm, capaz tengo unos jeans en mi casa.... quiero combinarlos con una camisa azul marino"})
r2 = chat(mensajes, "diag-chaqueta-1@test.cl")
mensajes.append({"rol": "koko", "texto": r2["respuesta_texto"]})
mensajes.append({"rol": "usuario", "texto": "me falta la chaqueta"})
r3 = chat(mensajes, "diag-chaqueta-1@test.cl")
imprimir("Koko (pregunta por la chaqueta): " + r3["respuesta_texto"])
mensajes.append({"rol": "koko", "texto": r3["respuesta_texto"]})
mensajes.append({"rol": "usuario", "texto": "me gusta mas suelta, algo bomber puede ser"})
r4 = chat(mensajes, "diag-chaqueta-1@test.cl")
imprimir("\nKoko (deberia buscar CHAQUETA, no camisa): " + r4["respuesta_texto"])
print("Sugerencia:", r4["sugerencia"])
assert r4["sugerencia"] is not None, "deberia tener suficiente info para buscar (suelta + bomber)"
assert r4["sugerencia"]["tipo_prenda"] == "chaqueta", f"BUG: penso que era {r4['sugerencia']['tipo_prenda']!r} en vez de chaqueta"
print("OK: busca CHAQUETA (no camisa) -- el bug real esta resuelto.\n")

print("=" * 70)
print('2) Pedido directo del usuario: "necesito una chaqueta bomber suelta"')
print("=" * 70)
r5 = chat([{"rol": "usuario", "texto": "necesito una chaqueta bomber suelta"}], "diag-chaqueta-2@test.cl")
imprimir("Koko: " + r5["respuesta_texto"])
print("Sugerencia:", r5["sugerencia"])
assert r5["sugerencia"] is not None, "corte (suelta->oversize) + subtipo (bomber) ya alcanzan, deberia buscar directo"
assert r5["sugerencia"]["tipo_prenda"] == "chaqueta"
assert r5["sugerencia"].get("subtipo") == "bomber"
print("OK: categoria correcta (chaqueta) y subtipo bomber detectado.\n")

print("=" * 70)
print("3) El buscador real trae productos bomber de verdad para esa sugerencia")
print("=" * 70)
payload = {
    "modo": "yo", "email": "diag-chaqueta-2@test.cl", "perfil": {"genero": "Hombre", "edad": 25, "altura": "1.78m", "peso": "75kg"},
    "categoria": r5["sugerencia"].get("categoria", ""), "tipo_prenda": r5["sugerencia"].get("tipo_prenda", ""),
    "subtipo": r5["sugerencia"].get("subtipo", ""), "largo": "", "manga": "", "capucha": "", "cierre": "",
    "corte": r5["sugerencia"].get("corte", ""), "ocasion": "", "precio": "",
    "gorro_camino": "", "gorro_colores": [], "gorro_outfit": "", "gorro_forma": "",
}
resp = cliente.post("/api/recommend", json=payload)
data = resp.get_json()
recs = data.get("recomendaciones", [])
print(f"Resultados: {len(recs)}")
for r in recs:
    imprimir(f"  - {r['nombre']}")
assert len(recs) > 0, "no deberia venir vacio -- hay 30 chaquetas bomber en el catalogo"
assert all("bomber" in r["nombre"].lower() for r in recs), "todos los resultados deberian ser bomber"
print("OK: el buscador real trae chaquetas bomber de verdad, no camisas ni otra cosa.\n")

print("=" * 70)
print("4) Regresion: pantalon de jeans sigue funcionando (denim no se cruzo con chaqueta)")
print("=" * 70)
r6 = chat([{"rol": "usuario", "texto": "necesito unos pantalones de jeans slim"}], "diag-chaqueta-3@test.cl")
imprimir("Koko: " + r6["respuesta_texto"])
print("Sugerencia:", r6["sugerencia"])
assert r6["sugerencia"] is not None
assert r6["sugerencia"]["tipo_prenda"] == "pantalon"
assert r6["sugerencia"].get("subtipo") == "jeans"
print("OK: pantalon de jeans sigue funcionando igual que antes (sin cruce con chaqueta/mezclilla).\n")

print("Todo OK.")
