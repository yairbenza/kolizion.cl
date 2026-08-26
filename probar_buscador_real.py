"""Prueba manual: confirma que el buscador normal (formulario, no Koko)
encuentra bien productos REALES del catalogo con pedidos tipicos.
No es parte de la app, correr a mano con el patron ya validado del
proyecto (mas rapido que levantar el servidor)."""
from app import load_json, armar_resultados, CATALOG_PATH, REGLAS_PATH

catalog = load_json(CATALOG_PATH)
reglas = load_json(REGLAS_PATH)

CASOS = [
    ("Hombre", "junta de amigos/skate park", "prenda inferior", "pantalon baggy"),
    ("Hombre", "concierto/festival", "prenda superior", "polera oversize"),
    ("Hombre", "carrete", "prenda superior", "poleron con capucha"),
    ("Mujer", "concierto/festival", "prenda superior", "top ajustado"),
    ("Mujer", "junta de amigos/skate park", "prenda inferior", "pantalon baggy"),
]

for genero, ocasion, categoria, texto in CASOS:
    print(f'=== {genero} | "{ocasion}" | categoria="{categoria}" | pedido="{texto}" ===')
    resultados = armar_resultados(genero, ocasion, categoria, texto, catalog, reglas)
    if not resultados:
        print("  (SIN RESULTADOS)")
    for r in resultados:
        print(f"  - {r['nombre']} | {r['marca']} @ {r['tienda']} | corte={r.get('corte')} | {r['precio']}")
    print()
