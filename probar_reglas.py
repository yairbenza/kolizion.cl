"""Script de prueba: no es parte de la app, solo sirve para revisar que las
reglas de recomendacion (categoria, corte, y el Plan B) funcionen bien antes
de abrir la pagina."""
from app import load_json, armar_resultados, buscar_plan_b, CATALOG_PATH, REGLAS_PATH

catalog = load_json(CATALOG_PATH)
reglas = load_json(REGLAS_PATH)

print("=== Hombre + concierto + 'prenda superior' (regla alta, debe dar poleras/polerones oversize) ===")
for r in armar_resultados("Hombre", "concierto/festival", "prenda superior", "", catalog, reglas):
    print(f"- {r['nombre']} ({r['tienda']})")
print()

print("=== Mujer + concierto (regla alta desde ahora, deberia dar polera/top ajustado) ===")
for r in armar_resultados("Mujer", "concierto/festival", "", "", catalog, reglas):
    print(f"- {r['nombre']} ({r['tienda']})")
print()

print("=== Hombre + 'prenda inferior' + corte boxy fit (NO deberia traer nada baggy) ===")
for r in armar_resultados("Hombre", "junta familiar", "prenda inferior", "boxy fit", catalog, reglas):
    print(f"- {r['nombre']} ({r['tienda']})")
print()

print("=== Hombre + 'prenda inferior' + corte baggy (SI deberia traer el pantalon cargo) ===")
for r in armar_resultados("Hombre", "junta familiar", "prenda inferior", "baggy", catalog, reglas):
    print(f"- {r['nombre']} ({r['tienda']})")
print()

print('=== Hombre + "prenda inferior" + boxy fit -- PLAN B (no hay boxy fit en catalogo, deberia mostrar otros cortes en vez de nada) ===')
for r in buscar_plan_b("Hombre", "junta familiar", "prenda inferior", "boxy fit", catalog, reglas):
    print(f"- {r['nombre']} ({r['tienda']})")
    print(f"  razon: {r['razon']}")
print()
