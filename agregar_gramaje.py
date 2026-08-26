"""Agrega el campo "gramaje_gsm" (entero) a las poleras/camisetas de
algodon 100% de data/catalog.json -- pedido del usuario (2026-08-19), para
refinar "Priorizar materiales de calidad": 180 GSM o mas se considera
"buena calidad" para poleras/camisetas de algodon (ver
GRAMAJE_MINIMO_CALIDAD_GSM en app.py). Fuera de esas 2 categorias (o sin
material algodon 100%) no se agrega este campo -- un umbral de calidad en
GSM para otras prendas no esta definido, asi que no se inventa.

Se reparte variado a proposito (semilla fija, reproducible): la mitad
arriba de 180 GSM (algodon grueso de calidad) y la mitad abajo (liviano),
para poder ver los 2 casos funcionando.

A proposito NO se re-corre generar_catalogo_prueba.py completo (mismo
motivo que los otros agregar_*.py). No es parte de la app -- se corre a
mano, una sola vez, despues de agregar_materiales.py (necesita que
"material" ya este cargado).
"""
import json
import random

from generar_catalogo_prueba import OUT_PATH

random.seed(29)

CATEGORIAS_CON_GRAMAJE = {"polera", "camiseta"}
GRAMAJE_MINIMO_CALIDAD = 180

catalogo = json.loads(OUT_PATH.read_text(encoding="utf-8"))

candidatos = [
    p for p in catalogo
    if p.get("categoria") in CATEGORIAS_CON_GRAMAJE and p.get("material") == "algodon_100"
]
assert candidatos, "no hay poleras/camisetas de algodon 100% -- correr agregar_materiales.py primero"

agregados = 0
for i, producto in enumerate(candidatos):
    if i % 2 == 0:
        producto["gramaje_gsm"] = random.randint(GRAMAJE_MINIMO_CALIDAD, 260)
    else:
        producto["gramaje_gsm"] = random.randint(120, GRAMAJE_MINIMO_CALIDAD - 1)
    agregados += 1

OUT_PATH.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")

buena_calidad = sum(1 for p in candidatos if p["gramaje_gsm"] >= GRAMAJE_MINIMO_CALIDAD)
print(f"gramaje_gsm agregado a {agregados} poleras/camisetas de algodon 100%.")
print(f"De esas, {buena_calidad} quedaron en >= {GRAMAJE_MINIMO_CALIDAD} GSM (buena calidad) y {agregados - buena_calidad} debajo.")
