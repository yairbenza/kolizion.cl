"""Reproduce la conversacion REAL guardada en data/chats_koko.json para
yairbenza@gmail.com hasta el punto exacto donde fallo ("ok" -> "no encontre
nada"), y muestra CADA paso interno (sugerencia cruda del modelo, deteccion
de tipo_prenda/corte sobre toda la conversacion, sugerencia corregida, y el
resultado de _sugerencia_calza_con_catalogo con su porque) -- para encontrar
la causa real en vez de asumir. Contra la API real (mismo texto exacto)."""
import json

import anthropic
import app as m


def imprimir(texto):
    print(str(texto).encode("ascii", errors="replace").decode("ascii"))


# Conversacion real, tal cual quedo guardada, hasta el mensaje "ok" incluido
# (el primer punto donde Koko respondio con el mensaje de fallo).
historial_real = json.load(open("data/chats_koko.json", encoding="utf-8"))["yairbenza@gmail.com"]
idx_ok = next(i for i, m_ in enumerate(historial_real) if m_["texto"].strip().lower() == "ok")
conversacion_hasta_ok = historial_real[: idx_ok + 1]

mensajes_api = [
    {"role": "user" if mm["rol"] == "usuario" else "assistant", "content": mm["texto"]}
    for mm in conversacion_hasta_ok
]

imprimir(f"Conversacion reproducida: {len(mensajes_api)} mensajes (hasta el 'ok' del usuario)")

reglas = m.load_json(m.REGLAS_PATH)
system_prompt = m.construir_system_prompt_koko("yairbenza@gmail.com", reglas)

cliente = anthropic.Anthropic(api_key=m.ANTHROPIC_API_KEY)
respuesta = cliente.messages.create(
    model="claude-sonnet-5",
    max_tokens=500,
    system=system_prompt,
    tools=[m.KOKO_TOOL_SUGERIR_BUSQUEDA],
    messages=mensajes_api,
)

sugerencia_cruda = None
texto_modelo = []
for bloque in respuesta.content:
    if bloque.type == "text":
        texto_modelo.append(bloque.text)
    elif bloque.type == "tool_use" and bloque.name == "sugerir_busqueda":
        sugerencia_cruda = dict(bloque.input)

imprimir(f"\n--- Lo que devolvio el modelo ---")
imprimir(f"texto: {' '.join(texto_modelo)!r}")
imprimir(f"sugerencia CRUDA (antes de corregir): {sugerencia_cruda}")

if sugerencia_cruda is not None:
    texto_conversacion = " ".join(mm["content"] for mm in mensajes_api)
    tipo_prenda_detectado = m.detectar_tipo_prenda(texto_conversacion)
    corte_detectado = m.detectar_corte_pedido(texto_conversacion)
    imprimir(f"\n--- Deteccion determinista sobre TODA la conversacion ---")
    imprimir(f"tipo_prenda_detectado: {tipo_prenda_detectado!r}")
    imprimir(f"corte_detectado: {corte_detectado!r}")

    sugerencia = dict(sugerencia_cruda)
    if tipo_prenda_detectado:
        sugerencia["tipo_prenda"] = tipo_prenda_detectado
        grupo = m.TIPO_PRENDA_A_CATEGORIA_GRUPO.get(tipo_prenda_detectado)
        if grupo:
            sugerencia["categoria"] = grupo
        if corte_detectado:
            sugerencia["corte"] = corte_detectado

        imprimir(f"\n--- Sugerencia CORREGIDA (lo que se valida contra el catalogo) ---")
        imprimir(sugerencia)

        catalog = m.load_json(m.CATALOG_PATH)
        catalog_filtrado = m.filtrar_gorros_por_forma(catalog, sugerencia.get("forma_gorro", ""))
        texto_pedido = f'{sugerencia.get("tipo_prenda", "")} {sugerencia.get("corte", "")}'
        candidatos = m.elegir_candidatos(
            "", texto_pedido, catalog_filtrado, cantidad=m.CANTIDAD_RESULTADOS,
            categoria_pedida=sugerencia.get("categoria", ""),
        )
        imprimir(f"\n--- elegir_candidatos('', {texto_pedido!r}, categoria_pedida={sugerencia.get('categoria', '')!r}) ---")
        imprimir(f"candidatos encontrados: {len(candidatos)}")
        for c in candidatos[:5]:
            imprimir(f"  - {c['nombre']} | categoria producto={c['categoria']!r} | corte={c.get('corte')!r}")

        if candidatos:
            tipo_prenda_val = sugerencia.get("tipo_prenda", "").lower()
            calzan = [c["categoria"].lower() == tipo_prenda_val for c in candidatos]
            imprimir(f"\ntipo_prenda esperado (minuscula): {tipo_prenda_val!r}")
            imprimir(f"todos calzan? {all(calzan)} -- detalle: {calzan}")
            imprimir(f"RESULTADO FINAL _sugerencia_calza_con_catalogo: {all(calzan) if candidatos else False}")
        else:
            imprimir("RESULTADO FINAL _sugerencia_calza_con_catalogo: False (candidatos vacio)")
    else:
        imprimir("\n--> tipo_prenda_detectado vacio: se hubiera pedido aclarar, NO el mensaje de 'no encontre nada'.")
