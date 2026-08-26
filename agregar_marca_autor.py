"""Agrega el campo "marca_autor" (booleano) a cada producto de
data/catalog.json -- pedido del usuario (2026-08-19): insignia "Marca de
autor" para destacar tiendas/productos con identidad de diseño propia (no
generico ni fast fashion), parte central de la propuesta de KOLIZION.

Para el catalogo REAL, este dato NO depende de que la tienda lo declare --
lo define KOLIZION mismo al cargar cada tienda piloto, segun si tiene
identidad de diseño propia o no (ver CLAUDE.md). Para este catalogo MOCK,
se marca de forma variada (semilla fija, reproducible) -- ~30% de los
productos, para poder ver la insignia funcionando sin que sea ni
rarisima ni la mayoria.

A proposito NO se re-corre generar_catalogo_prueba.py completo (mismo
motivo que los otros agregar_*.py: reordenaria el generador de numeros
aleatorios compartido y cambiaria precios/tallas/colores de TODO el
catalogo sin necesidad real) -- este script edita en el lugar cada
producto ya existente, sin tocar ningun otro campo.

No es parte de la app -- se corre a mano, una sola vez.
"""
import json
import random

from generar_catalogo_prueba import OUT_PATH

random.seed(23)

PROPORCION_MARCA_AUTOR = 0.3

catalogo = json.loads(OUT_PATH.read_text(encoding="utf-8"))

for producto in catalogo:
    producto["marca_autor"] = random.random() < PROPORCION_MARCA_AUTOR

OUT_PATH.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")

marcados = sum(1 for p in catalogo if p["marca_autor"])
print(f"marca_autor agregado a los {len(catalogo)} productos del catalogo.")
print(f"Marcados como 'Marca de autor': {marcados} ({marcados / len(catalogo):.0%}).")
