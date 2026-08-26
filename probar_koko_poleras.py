"""Prueba de cierre del bug de plurales: le pide 'poleras' a Koko de verdad
(API real, tiene costo) y confirma que trae productos reales del catalogo."""
from app import app, CATALOG_PATH, elegir_candidatos, load_json

cliente = app.test_client()

mensaje = "quiero ver todas las poleras que hayan"
print(f'Mensaje a Koko: "{mensaje}"')
resp = cliente.post("/api/koko/chat", json={"email": "", "mensajes": [{"rol": "usuario", "texto": mensaje}]})
data = resp.get_json()
print("Koko dice:", data["respuesta_texto"])
sugerencia = data["sugerencia"]
print("Sugerencia (tool call):", sugerencia)
print()

if not sugerencia:
    print("FALLO: Koko no llamo la herramienta de busqueda.")
else:
    catalog = load_json(CATALOG_PATH)
    texto_pedido = f'{sugerencia.get("tipo_prenda","")} {sugerencia.get("corte","")}'
    candidatos = elegir_candidatos(
        "", texto_pedido, catalog, cantidad=5, categoria_pedida=sugerencia.get("categoria", "")
    )
    print(f"Productos reales que se le mostrarian al usuario ({len(candidatos)}):")
    for p in candidatos:
        print(f"  - {p['nombre']} | categoria={p['categoria']} | corte={p.get('corte','')}")
    print()
    print("EXITO" if candidatos else "FALLO: sin productos")
