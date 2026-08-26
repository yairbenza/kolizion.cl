"""Segunda ronda de diagnostico del bug reportado: prueba variantes de
perfil (genero, talla, sin altura/peso) y repite la MISMA frase varias
veces (la API no es 100% determinista) para ver si el fallo es
intermitente o depende de un perfil concreto. Contra la API real."""
import app as app_module


def imprimir(texto):
    print(texto.encode("ascii", errors="replace").decode("ascii"))


def probar(frase, perfil, etiqueta, mensajes_previos=None):
    cliente = app_module.app.test_client()
    mensajes = list(mensajes_previos or [])
    mensajes.append({"rol": "usuario", "texto": frase})

    resp = cliente.post(
        "/api/koko/chat",
        json={"email": f"diag-{etiqueta}@test.cl", "perfil": perfil, "mensajes": mensajes},
    )
    data = resp.get_json()
    sug = data.get("sugerencia")
    if not sug:
        imprimir(f"[{etiqueta}] SIN sugerencia -- respuesta: {data.get('respuesta_texto')!r}")
        return

    payload = {
        "modo": "yo", "email": f"diag-{etiqueta}@test.cl", "perfil": perfil,
        "categoria": sug.get("categoria", ""), "tipo_prenda": sug.get("tipo_prenda", ""),
        "subtipo": "", "largo": "", "manga": "", "capucha": "", "cierre": "",
        "corte": sug.get("corte", ""), "ocasion": "", "precio": "",
        "gorro_camino": "", "gorro_colores": [], "gorro_outfit": "", "gorro_forma": sug.get("forma_gorro", ""),
    }
    resp2 = cliente.post("/api/recommend", json=payload)
    data2 = resp2.get_json()
    recs = data2.get("recomendaciones", [])
    imprimir(f"[{etiqueta}] sugerencia={sug} -> {len(recs)} resultado(s), sin_talla={data2.get('sin_talla')}")


if __name__ == "__main__":
    imprimir("--- Perfiles distintos, mismo mensaje 'poleron oversize' ---")
    probar("poleron oversize", {"genero": "Mujer", "edad": 24, "altura": "1.60m", "peso": "55kg", "hobbie": "musica"}, "mujer-1.60-55")
    probar("poleron oversize", {"genero": "Hombre", "edad": 30, "altura": "1.95m", "peso": "110kg", "hobbie": "gym"}, "hombre-alto-pesado")
    probar("poleron oversize", {"genero": "Hombre", "edad": 19, "altura": "1.60m", "peso": "50kg"}, "hombre-bajo-liviano")
    probar("poleron oversize", {"genero": "Unisex", "edad": 22, "altura": "", "peso": "", "hobbie": "skate"}, "sin-altura-peso")
    probar("poleron oversize", {"genero": "", "edad": "", "altura": "", "peso": "", "hobbie": ""}, "perfil-vacio")

    imprimir("\n--- Misma frase 'poleron oversize', 3 veces (perfil hombre 1.75/70) ---")
    perfil_base = {"genero": "Hombre", "edad": 22, "altura": "1.75m", "peso": "70kg", "hobbie": "skate"}
    for i in range(3):
        probar("poleron oversize", perfil_base, f"repeticion-{i+1}")

    imprimir("\n--- Conversacion de 2 turnos (saludo, despues pide el poleron) ---")
    previos = [
        {"rol": "usuario", "texto": "hola"},
        {"rol": "koko", "texto": "Hola! Soy Koko, tu asistente de estilo. Que buscas hoy?"},
    ]
    probar("quiero un poleron oversize", perfil_base, "dos-turnos", mensajes_previos=previos)

    imprimir("\n--- Frase exacta reportada, con Mujer (por si el usuario no es hombre) ---")
    probar("polerones oversize baratos", {"genero": "Mujer", "edad": 25, "altura": "1.65m", "peso": "60kg", "hobbie": "arte"}, "mujer-baratos")
