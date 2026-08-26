"""Prueba puntual de la capa de validacion nueva de Koko: verificacion
automatica contra el catalogo + "preguntar en vez de adivinar" cuando la
prenda no quedo clara en la conversacion. SI llama a la API real de
Anthropic (tiene costo) -- correr solo a mano."""
from app import app

cliente = app.test_client()


def preguntar(mensajes):
    """mensajes: lista de (rol, texto) en orden cronologico."""
    payload = [{"rol": rol, "texto": texto} for rol, texto in mensajes]
    resp = cliente.post("/api/koko/chat", json={"email": "", "mensajes": payload})
    return resp.get_json()


print("=" * 70)
print('REGRESION: "pantalón baggy" -- debe seguir funcionando igual que antes')
print("=" * 70)
data = preguntar([("usuario", "pantalón baggy")])
print("Koko dice:", data["respuesta_texto"])
print("Sugerencia:", data["sugerencia"])
print()

print("=" * 70)
print('CASO AMBIGUO: "necesito algo para el carrete" -- NO deberia adivinar, debe preguntar')
print("=" * 70)
data = preguntar([("usuario", "necesito algo para el carrete")])
print("Koko dice:", data["respuesta_texto"])
print("Sugerencia (deberia ser None):", data["sugerencia"])
print()

print("=" * 70)
print('CONTEXTO EN VARIOS TURNOS: primero "quiero un poleron", despues solo "que sea con capucha"')
print("=" * 70)
data = preguntar([
    ("usuario", "quiero un poleron para el frio"),
    ("koko", "Dale, ¿lo quieres con capucha o sin capucha?"),
    ("usuario", "que sea con capucha"),
])
print("Koko dice:", data["respuesta_texto"])
print("Sugerencia (deberia seguir siendo poleron, no None):", data["sugerencia"])
