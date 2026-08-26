"""Prueba puntual: confirma que Koko nunca mezcla categorias de prenda.
Llama /api/koko/chat de verdad (con el test client de Flask, sin levantar
servidor) para los 3 casos pedidos. SI llama a la API real de Anthropic
(tiene costo) -- correr solo a mano, igual que probar_koko_ajustes.py."""
from app import app, TIPOS_PRENDA_CONOCIDOS

CASOS = [
    ("pantalon baggy", "pantalón baggy", "pantalon"),
    ("polera oversize", "polera oversize", "polera"),
    ("poleron con capucha", "polerón con capucha", "poleron"),
]

cliente = app.test_client()

for _, mensaje, tipo_esperado in CASOS:
    print("=" * 70)
    print(f'Mensaje: "{mensaje}" -- se espera tipo_prenda="{tipo_esperado}"')
    print("=" * 70)
    resp = cliente.post(
        "/api/koko/chat",
        json={"email": "", "mensajes": [{"rol": "usuario", "texto": mensaje}]},
    )
    data = resp.get_json()
    print("Koko dice:", data.get("respuesta_texto"))
    sugerencia = data.get("sugerencia")
    print("Sugerencia:", sugerencia)
    if sugerencia:
        ok = sugerencia.get("tipo_prenda") == tipo_esperado
        print(f'¿tipo_prenda es exactamente "{tipo_esperado}"? {ok}')
    else:
        print("(No llamo la tool)")
    print()

print("Tipos de prenda validos, por si sirve de referencia:", list(TIPOS_PRENDA_CONOCIDOS.keys()))
