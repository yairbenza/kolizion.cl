"""Script de prueba: no es parte de la app. Prueba el historial de Koko
(registrar_busqueda/registrar_interes/resumen_historial_para_prompt) SIN
llamar a la API real de Anthropic -- corre gratis y sin necesitar una
ANTHROPIC_API_KEY configurada. El endpoint /api/koko/chat en si (que si
llama a la API) se prueba a mano en el navegador."""
from app import (
    cargar_historial,
    guardar_historial,
    registrar_busqueda,
    registrar_interes,
    resumen_historial_para_prompt,
)

EMAIL_PRUEBA = "prueba_koko@test.local"


def limpiar():
    historial = cargar_historial()
    historial.pop(EMAIL_PRUEBA, None)
    guardar_historial(historial)


limpiar()

print("=== Usuario nuevo (sin historial) -> deberia dar None ===")
print(resumen_historial_para_prompt(EMAIL_PRUEBA))
print()

print("=== Despues de una busqueda 'yo' -> deberia mencionar corte/tipo/ocasion ===")
registrar_busqueda(EMAIL_PRUEBA, "concierto/festival", "prenda superior", "polera", "oversize")
print(resumen_historial_para_prompt(EMAIL_PRUEBA))
print()

print("=== Despues de tambien registrar interes en un producto ===")
registrar_interes(EMAIL_PRUEBA, {
    "nombre": "[MOCK] Polera Oversize Vertex 1", "tienda": "Tienda Mock (no real)",
    "categoria": "polera", "corte": "oversize",
})
print(resumen_historial_para_prompt(EMAIL_PRUEBA))
print()

print("=== Email vacio -> no debe registrar nada ni romper ===")
registrar_busqueda("", "carrete", "prenda inferior", "pantalon", "baggy")
print("resumen con email vacio:", resumen_historial_para_prompt(""))
print()

print("=== Busquedas 'regalo' nunca deben llegar aca (no se llama registrar_busqueda para regalo) ===")
print("(verificado por inspeccion de app.py: el llamado esta gateado a modo=='yo' y not plan_b)")

limpiar()
print("\nOK: historial de prueba limpiado.")
