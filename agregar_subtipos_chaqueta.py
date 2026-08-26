"""Agrega productos de chaqueta con subtipo (bomber, mezclilla, cuero) a
data/catalog.json -- pedido del usuario (2026-08-17): Koko no podia pedir un
tipo concreto de chaqueta porque el catalogo mock no tenia esa variante.

A PROPOSITO no se re-corre generar_catalogo_prueba.py completo: ese script
usa un solo generador de numeros aleatorios compartido para TODO el
catalogo, asi que agregar una combinacion nueva en medio de la secuencia
correria los precios/tallas/colores de TODOS los productos generados
despues (camisa, camiseta, top, pantalon, shorts, etc.) sin ningun cambio
real en esas categorias -- innecesariamente riesgoso. Este script en cambio
SOLO agrega productos nuevos, reusando _crear_producto() para que tengan
exactamente la misma forma que el resto del catalogo, sin tocar ni un
producto existente. Los productos nuevos usan el prefijo "mock_chaqueta_sub_"
para no chocar con ningun ID ya generado.

No es parte de la app -- se corre a mano, una sola vez.
"""
import json

from generar_catalogo_prueba import CORTES_SUPERIOR, OUT_PATH, _crear_producto

SUBTIPOS_CHAQUETA = ["bomber", "mezclilla", "cuero"]

catalogo = json.loads(OUT_PATH.read_text(encoding="utf-8"))
ids_existentes = {p["id"] for p in catalogo}

nuevos = []
contador = 1
for subtipo in SUBTIPOS_CHAQUETA:
    for corte in CORTES_SUPERIOR:
        for i in range(1, 7):
            producto = _crear_producto(contador, "chaqueta", corte, i, subtipo=subtipo)
            producto["id"] = f"mock_chaqueta_sub_{contador:04d}"
            assert producto["id"] not in ids_existentes, f"ID repetido: {producto['id']}"
            nuevos.append(producto)
            contador += 1

catalogo.extend(nuevos)
OUT_PATH.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Agregados {len(nuevos)} productos de chaqueta con subtipo ({', '.join(SUBTIPOS_CHAQUETA)}).")
print(f"Catalogo total ahora: {len(catalogo)} productos.")
