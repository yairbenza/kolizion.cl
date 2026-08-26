"""Prueba puntual de los 3 ajustes al comportamiento de Koko (busqueda
precisa por filtros, tono chileno, y multiples opciones de outfit).

A diferencia de probar_koko.py, ESTE script SI llama a la API real de
Anthropic (3 llamadas cortas, con costo). No es parte de la suite normal de
pruebas del proyecto -- se corre a mano cuando se ajusta el prompt de Koko."""
import anthropic

from app import (
    ANTHROPIC_API_KEY,
    CATALOG_PATH,
    KOKO_TOOL_SUGERIR_BUSQUEDA,
    REGLAS_PATH,
    construir_system_prompt_koko,
    elegir_candidatos,
    load_json,
)

reglas = load_json(REGLAS_PATH)
system_prompt = construir_system_prompt_koko("", reglas)  # email vacio = usuario nuevo, sin historial
cliente = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def preguntar(texto_usuario):
    respuesta = cliente.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        system=system_prompt,
        tools=[KOKO_TOOL_SUGERIR_BUSQUEDA],
        messages=[{"role": "user", "content": texto_usuario}],
    )
    texto_partes = []
    sugerencia = None
    for bloque in respuesta.content:
        if bloque.type == "text":
            texto_partes.append(bloque.text)
        elif bloque.type == "tool_use" and bloque.name == "sugerir_busqueda":
            sugerencia = bloque.input
    return " ".join(texto_partes).strip(), sugerencia


print("=" * 70)
print('CASO (a): "necesito pantalones baggy" -- debe interpretar el filtro y llamar la tool')
print("=" * 70)
texto, sugerencia = preguntar("necesito pantalones baggy")
print("Koko dice:", texto)
print("Tool sugerir_busqueda llamada con:", sugerencia)
if sugerencia:
    catalog = load_json(CATALOG_PATH)
    texto_pedido = f'{sugerencia.get("tipo_prenda", "")} {sugerencia.get("corte", "")}'
    candidatos = elegir_candidatos(
        "Hombre", texto_pedido, catalog, cantidad=5, categoria_pedida=sugerencia.get("categoria", "")
    )
    print(f"\nProductos que devolveria el buscador real con esos filtros ({len(candidatos)}):")
    for p in candidatos:
        print(f"  - {p['nombre']} | categoria={p['categoria']} | corte={p.get('corte', '')}")
    todos_calzan = all(
        p["categoria"] == sugerencia.get("tipo_prenda") and "baggy" in p.get("corte", "").lower()
        for p in candidatos
    )
    print(f"¿Todos calzan EXACTO con tipo_prenda=pantalon y corte=baggy? {todos_calzan}")
else:
    print("(No llamo la tool -- revisar si el prompt necesita mas ajuste)")
print()

print("=" * 70)
print('CASO (b): mensaje casual, para confirmar el tono chileno/joven')
print("=" * 70)
texto, sugerencia = preguntar("hola! como andas")
print("Koko dice:", texto)
print("Sugerencia (deberia ser None, es solo un saludo):", sugerencia)
print()

print("=" * 70)
print('CASO (c): "que me combino con una camisa cuadrille y jeans negros" -- debe dar 2-3+ opciones')
print("=" * 70)
texto, sugerencia = preguntar("que me combino con una camisa cuadrille y jeans negros")
print("Koko dice:", texto)
print("Sugerencia:", sugerencia)
