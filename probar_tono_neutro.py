"""Reprueba rapida del tono neutro por defecto, tras reforzar el prompt."""
from app import app

cliente = app.test_client()
for msg in ["pantalon baggy", "hola como estas", "busco algo para el carrete con los amigos"]:
    resp = cliente.post("/api/koko/chat", json={"email": "", "mensajes": [{"rol": "usuario", "texto": msg}]})
    data = resp.get_json()
    print(f'--- "{msg}" ---')
    print(data["respuesta_texto"])
    print()
