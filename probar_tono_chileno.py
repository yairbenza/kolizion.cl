"""Reprueba rapida del cambio a modo chileno cuando se pide explicitamente."""
from app import app

cliente = app.test_client()
mensajes = [{"rol": "usuario", "texto": "hola"}]
resp = cliente.post("/api/koko/chat", json={"email": "", "mensajes": mensajes})
print("1) saludo neutro:", resp.get_json()["respuesta_texto"][:150])

mensajes.append({"rol": "koko", "texto": resp.get_json()["respuesta_texto"]})
mensajes.append({"rol": "usuario", "texto": "hablame como chileno de ahora en adelante"})
resp2 = cliente.post("/api/koko/chat", json={"email": "", "mensajes": mensajes})
print("\n2) pide modo chileno:", resp2.get_json()["respuesta_texto"])

mensajes.append({"rol": "koko", "texto": resp2.get_json()["respuesta_texto"]})
mensajes.append({"rol": "usuario", "texto": "busco un poleron"})
resp3 = cliente.post("/api/koko/chat", json={"email": "", "mensajes": mensajes})
print("\n3) deberia seguir en chileno:", resp3.get_json()["respuesta_texto"])
