"""Prueba de los 5 ajustes nuevos a Koko. SI llama a la API real de
Anthropic (tiene costo) -- correr solo a mano."""
from app import app

cliente = app.test_client()
EMAIL_PRUEBA = "prueba_ajustes2@test.local"


def enviar(mensajes_previos, texto_nuevo, email=""):
    payload = [{"rol": rol, "texto": t} for rol, t in mensajes_previos]
    payload.append({"rol": "usuario", "texto": texto_nuevo})
    resp = cliente.post("/api/koko/chat", json={"email": email, "mensajes": payload})
    return resp.get_json()


print("=" * 70)
print('CASO 1: tono neutro por defecto -- mensaje casual, sin pedir chileno')
print("=" * 70)
data = enviar([], "hola, como estas?")
print("Koko dice:", data["respuesta_texto"])
print()

print("=" * 70)
print('CASO 2: pide "hablame como chileno" y confirma que cambia el tono')
print("=" * 70)
historial = [("usuario", "hola"), ("koko", data["respuesta_texto"])]
data2 = enviar(historial, "hablame como chileno de ahora en adelante")
print("Koko dice (deberia notarse el cambio o confirmar el cambio):", data2["respuesta_texto"])
historial.append(("usuario", "hablame como chileno de ahora en adelante"))
historial.append(("koko", data2["respuesta_texto"]))
data3 = enviar(historial, "que tal el clima hoy")
print("Koko dice (deberia seguir en tono chileno):", data3["respuesta_texto"])
print()

print("=" * 70)
print('CASO 3: "busco una polera negra" -- NO deberia preguntar la ocasion')
print("=" * 70)
data4 = enviar([], "busco una polera negra")
print("Koko dice:", data4["respuesta_texto"])
print("Sugerencia:", data4["sugerencia"])
print()

print("=" * 70)
print('CASO 5: "quiero un gorro de lana" -- debe traer solo gorros de lana')
print("=" * 70)
data5 = enviar([], "quiero un gorro de lana")
print("Koko dice:", data5["respuesta_texto"])
print("Sugerencia:", data5["sugerencia"])
print()

print("=" * 70)
print("PERSISTENCIA: revisando /api/koko/historial_chat para el email de prueba")
print("=" * 70)
enviar([], "esto es un mensaje de prueba de persistencia", email=EMAIL_PRUEBA)
resp = cliente.get(f"/api/koko/historial_chat?email={EMAIL_PRUEBA}")
data_hist = resp.get_json()
print(f"Mensajes guardados ({len(data_hist['mensajes'])}):")
for m in data_hist["mensajes"]:
    print(f"  [{m['rol']}] {m['texto'][:80]}")

# Limpieza del email de prueba para no dejar basura en el archivo real.
from app import cargar_chats_koko, guardar_chats_koko
chats = cargar_chats_koko()
chats.pop(EMAIL_PRUEBA, None)
guardar_chats_koko(chats)
print("\n(email de prueba limpiado del archivo)")
