"""Chequeo puntual: Koko da opciones de outfit bien formateadas y termina
ofreciendo buscar productos reales. API real (costo), no toda la bateria."""
import sys
from app import app


def imprimir(texto):
    print(texto.encode("ascii", errors="replace").decode("ascii"))

cliente = app.test_client()

print("=== Pide combinar con jeans grises ===")
mensajes = [{"rol": "usuario", "texto": "que me combino con unos jeans grises"}]
r1 = cliente.post("/api/koko/chat", json={"email": "", "mensajes": mensajes}).get_json()
texto1 = r1["respuesta_texto"]
imprimir(texto1)
print()
print("Tiene negrita (**):", "**" in texto1)
print("Tiene salto de linea:", "\n" in texto1)
print("Sugerencia (deberia ser None, solo dio consejo):", r1["sugerencia"])
print()

print("=== Confirma que quiere buscar ===")
mensajes.append({"rol": "koko", "texto": texto1})
mensajes.append({"rol": "usuario", "texto": "si, buscame la primera opcion"})
r2 = cliente.post("/api/koko/chat", json={"email": "", "mensajes": mensajes}).get_json()
imprimir("Koko dice: " + r2["respuesta_texto"])
print("Sugerencia:", r2["sugerencia"])
