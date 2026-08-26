"""Diagnostico puntual: por que Koko no encuentra nada. No llama a la API
real -- solo revisa el catalogo y las funciones de deteccion/busqueda
directamente, para separar "problema de catalogo" de "problema de logica"."""
from app import (
    CATALOG_PATH,
    TIPOS_PRENDA_CONOCIDOS,
    detectar_tipo_prenda,
    elegir_candidatos,
    load_json,
)

print("=" * 70)
print("PASO 1: Conteo directo del catalogo real (mismo archivo que usa el formulario)")
print("=" * 70)
print("Ruta del catalogo:", CATALOG_PATH)
catalog = load_json(CATALOG_PATH)
print("Total de productos en el catalogo:", len(catalog))
poleras = [p for p in catalog if p.get("categoria", "").lower() == "polera"]
print("Productos con categoria == 'polera':", len(poleras))
for p in poleras[:5]:
    print(f"  - {p['nombre']} | genero={p['genero']} | corte={p.get('corte','')}")
print()

print("=" * 70)
print('PASO 2: que devuelve detectar_tipo_prenda() para el mensaje real del usuario')
print("=" * 70)
mensajes_de_prueba = [
    "quiero ver todas las poleras que hayan",
    "poleras",
    "polera",
    "quiero una polera",
]
for m in mensajes_de_prueba:
    resultado = detectar_tipo_prenda(m)
    print(f'  detectar_tipo_prenda("{m}") -> {resultado!r}')
print()

print("=" * 70)
print('PASO 3: si se fuerza tipo_prenda="polera" a mano, que devuelve elegir_candidatos()')
print("=" * 70)
candidatos = elegir_candidatos("", "polera", catalog, cantidad=5, categoria_pedida="prenda superior")
print(f"Candidatos encontrados: {len(candidatos)}")
for p in candidatos:
    print(f"  - {p['nombre']} | categoria={p['categoria']}")
print()

print("Tipos de prenda conocidos (para referencia):", list(TIPOS_PRENDA_CONOCIDOS.keys()))
