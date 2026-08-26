"""Agrega el campo "material" a cada producto de data/catalog.json -- pedido
del usuario (2026-08-19) para el filtro "Priorizar materiales de calidad"
del buscador (ver MATERIALES_CONOCIDOS en app.py). El catalogo REAL no trae
este dato (se le pedira a cada tienda mas adelante); este catalogo MOCK lo
recibe de forma variada, con 2 asignaciones logicas reusando datos que ya
existian (nunca al azar cuando hay una pista real):
- Gorro con forma "lana" -> material "lana" (literalmente es un gorro de lana).
- Chaqueta con subtipo "cuero" -> material "cuero" (idem).
El resto del catalogo (la inmensa mayoria) recibe un material al azar
(semilla fija, reproducible) de entre los 7 conocidos, con pesos que
imitan una distribucion real (algodon/mezclas mas comunes que lana/cuero).

A proposito NO se re-corre generar_catalogo_prueba.py completo (mismo
motivo que agregar_subtipos_chaqueta.py: reordenaria el generador de
numeros aleatorios compartido y cambiaria precios/tallas/colores de TODO
el catalogo sin necesidad) -- este script edita en el lugar cada producto
ya existente, sin tocar ningun otro campo.

No es parte de la app -- se corre a mano, una sola vez.
"""
import json
import random

from generar_catalogo_prueba import OUT_PATH

random.seed(19)

# Deben coincidir con las claves de MATERIALES_CONOCIDOS en app.py.
MATERIALES_PESOS = [
    ("algodon_100", 30),
    ("mezcla_algodon_poliester", 25),
    ("poliester", 20),
    ("nylon", 10),
    ("acrilico", 8),
    ("lana", 4),
    ("cuero", 3),
]
CLAVES = [m for m, _ in MATERIALES_PESOS]
PESOS = [p for _, p in MATERIALES_PESOS]

catalogo = json.loads(OUT_PATH.read_text(encoding="utf-8"))

contador_asignaciones_logicas = 0
for producto in catalogo:
    if producto.get("categoria") == "gorro" and producto.get("forma") == "lana":
        producto["material"] = "lana"
        contador_asignaciones_logicas += 1
    elif producto.get("categoria") == "chaqueta" and producto.get("subtipo") == "cuero":
        producto["material"] = "cuero"
        contador_asignaciones_logicas += 1
    else:
        producto["material"] = random.choices(CLAVES, weights=PESOS, k=1)[0]

OUT_PATH.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")

from collections import Counter
conteo = Counter(p["material"] for p in catalogo)
print(f"Material agregado a los {len(catalogo)} productos del catalogo.")
print(f"Asignaciones logicas (gorro de lana / chaqueta de cuero): {contador_asignaciones_logicas}")
print("Distribucion final:", dict(conteo))
