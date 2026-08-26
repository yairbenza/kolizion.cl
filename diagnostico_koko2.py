"""Diagnostico rapido (sin API real) de las funciones nuevas: deteccion de
forma de gorro, y guardado/carga de historial de chat."""
from app import (
    CATALOG_PATH,
    cargar_historial_chat,
    detectar_forma_gorro,
    elegir_candidatos,
    filtrar_gorros_por_forma,
    guardar_mensaje_chat,
    load_json,
)

print("=== detectar_forma_gorro ===")
for texto in ["quiero un gorro de lana", "un gorro plano porfa", "gorro curvo negro", "una polera"]:
    print(f'  "{texto}" -> {detectar_forma_gorro(texto)!r}')
print()

print("=== Catalogo: gorros de lana disponibles ===")
catalog = load_json(CATALOG_PATH)
catalog_lana = filtrar_gorros_por_forma(catalog, "lana")
candidatos = elegir_candidatos("", "gorro", catalog_lana, cantidad=5, categoria_pedida="gorro")
print(f"Candidatos gorro+lana: {len(candidatos)}")
for p in candidatos:
    print(f"  - {p['nombre']} | forma={p.get('forma','')}")
print()

print("=== Persistencia de chat (round-trip) ===")
EMAIL_PRUEBA = "prueba_persistencia@test.local"
guardar_mensaje_chat(EMAIL_PRUEBA, "usuario", "mensaje de prueba 1")
guardar_mensaje_chat(EMAIL_PRUEBA, "koko", "respuesta de prueba 1")
historial = cargar_historial_chat(EMAIL_PRUEBA)
print("Historial guardado:", historial)
assert historial == [
    {"rol": "usuario", "texto": "mensaje de prueba 1"},
    {"rol": "koko", "texto": "respuesta de prueba 1"},
], "El historial no quedo como se esperaba"
print("OK: se guardo y se recupero correctamente.")
