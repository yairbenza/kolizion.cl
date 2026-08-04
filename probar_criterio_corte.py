"""Script de prueba: no es parte de la app. Verifica que los 9 productos
mock_criterio_* (descripcion sin decir el corte explicitamente) queden
DENTRO de los candidatos filtrados al buscar por ese corte, gracias al tag
que les asignamos siguiendo la tabla de CLAUDE.md. No mira el top-2 (eso
depende del orden del catalogo), sino la lista completa ya filtrada."""
from app import load_json, elegir_candidatos, CATALOG_PATH, REGLAS_PATH

catalog = load_json(CATALOG_PATH)

casos = [
    ("polera", "slim fit", "mock_criterio_01"),
    ("camisa", "regular fit", "mock_criterio_02"),
    ("chaqueta", "straight", "mock_criterio_03"),
    ("poleron", "boxy fit", "mock_criterio_04"),
    ("polera", "oversize", "mock_criterio_05"),
    ("pantalon", "skinny", "mock_criterio_06"),
    ("pantalon", "slim fit", "mock_criterio_07"),
    ("pantalon", "straight fit", "mock_criterio_08"),
    ("pantalon", "baggy", "mock_criterio_09"),
]

for tipo_prenda, corte, id_esperado in casos:
    texto_pedido = f"{tipo_prenda} {corte}"
    candidatos = elegir_candidatos("Hombre", texto_pedido, catalog, cantidad=len(catalog), categoria_pedida="")
    ids = [p["id"] for p in candidatos]
    estado = "OK" if id_esperado in ids else "FALTA"
    print(f"[{estado}] {tipo_prenda} + {corte} -> {id_esperado} {'esta' if id_esperado in ids else 'NO esta'} en los candidatos ({len(ids)} en total)")
