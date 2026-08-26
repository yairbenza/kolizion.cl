"""Chequeo de la profundidad de preguntas de Koko (2026-08-17): pedido con
contexto pero sin detalles -> 2-3 preguntas CONCRETAS (no "cuentame mas")
antes de buscar; con suficiente info (front-loaded o tras responder) ->
busca directo; pedido ya especifico (corte incluido) -> sigue buscando de
inmediato, sin preguntar nada (no debia romperse). Contra la API real
(costo) -- no es parte de la bateria rapida, correr aparte quien lo pida."""
import app as m

cliente = m.app.test_client()


def imprimir(texto):
    print(str(texto).encode("ascii", errors="replace").decode("ascii"))


def chat(mensajes, email):
    resp = cliente.post("/api/koko/chat", json={"email": email, "mensajes": mensajes})
    return resp.get_json()


print("=" * 70)
print('1) "necesito una camisa para un matrimonio" -- contexto pero sin detalles')
print("=" * 70)
mensajes = [{"rol": "usuario", "texto": "necesito una camisa para un matrimonio"}]
r1 = chat(mensajes, "diag-preguntas-1@test.cl")
imprimir("Koko: " + r1["respuesta_texto"])
print("Sugerencia (deberia ser None -- todavia no busca):", r1["sugerencia"])
assert r1["sugerencia"] is None, "Koko busco de inmediato sin preguntar nada -- no deberia"
assert "?" in r1["respuesta_texto"], "la respuesta deberia traer al menos una pregunta"
print("OK: no busco de inmediato, y la respuesta trae una pregunta.\n")

print("=" * 70)
print("2) El usuario responde 2 datos utiles (ajuste + presupuesto) -> ahora si busca")
print("=" * 70)
mensajes.append({"rol": "koko", "texto": r1["respuesta_texto"]})
mensajes.append({"rol": "usuario", "texto": "la prefiero ajustada, y tengo como 30 lucas de presupuesto"})
r2 = chat(mensajes, "diag-preguntas-1@test.cl")
imprimir("Koko: " + r2["respuesta_texto"])
print("Sugerencia:", r2["sugerencia"])
assert r2["sugerencia"] is not None, "con ajuste + presupuesto ya deberia buscar"
assert r2["sugerencia"]["tipo_prenda"] == "camisa"
print("OK: con 2 datos utiles, busca directo (sin insistir en la 3ra pregunta).\n")

print("=" * 70)
print('3) Mensaje "front-loaded": todo el detalle en un solo mensaje -> busca de una, sin preguntar')
print("=" * 70)
mensajes3 = [{"rol": "usuario", "texto": "necesito una camisa blanca ajustada para un matrimonio, unos 25 lucas"}]
r3 = chat(mensajes3, "diag-preguntas-2@test.cl")
imprimir("Koko: " + r3["respuesta_texto"])
print("Sugerencia:", r3["sugerencia"])
assert r3["sugerencia"] is not None, "con todo el detalle en el primer mensaje, no deberia preguntar nada"
assert r3["sugerencia"]["tipo_prenda"] == "camisa"
print("OK: con el detalle completo desde el primer mensaje, busca directo.\n")

print("=" * 70)
print('4) Pedido YA especifico ("pantalones baggy") -- regresion: sigue buscando de inmediato')
print("=" * 70)
mensajes4 = [{"rol": "usuario", "texto": "necesito pantalones baggy"}]
r4 = chat(mensajes4, "diag-preguntas-3@test.cl")
imprimir("Koko: " + r4["respuesta_texto"])
print("Sugerencia:", r4["sugerencia"])
assert r4["sugerencia"] is not None, "un pedido ya especifico (con corte) no deberia generar preguntas"
assert r4["sugerencia"]["tipo_prenda"] == "pantalon"
assert r4["sugerencia"]["corte"] == "baggy"
print("OK: un pedido ya especifico sigue buscando directo, sin preguntas de mas (no se rompio).\n")

print("Todo OK.")
