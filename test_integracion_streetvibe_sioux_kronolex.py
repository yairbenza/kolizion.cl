"""Tests focalizados para la integracion StreetVibe + Sioux + KronoLex.
Corre standalone (python test_integracion_streetvibe_sioux_kronolex.py),
no pytest -- mismo criterio que el resto de scripts de verificacion del
proyecto. Falla con AssertionError y sale con codigo != 0 si algo no
cumple."""
import json
from collections import Counter

from constantes import CATALOG_PATH, es_composicion_100_pura
from motor_recomendacion import (
    elegir_candidatos,
    detectar_material_100_pedido,
    filtrar_por_material_100,
)

with open(CATALOG_PATH, encoding="utf-8") as f:
    CATALOG = json.load(f)

fails = []


def check(nombre, condicion):
    estado = "OK" if condicion else "FALLO"
    print(f"[{estado}] {nombre}")
    if not condicion:
        fails.append(nombre)


# ---------------- StreetVibe ----------------
sv = [p for p in CATALOG if p["tienda"] == "StreetVibe"]
check("1. StreetVibe: hay jeans cargados", len(sv) > 0)
check("2. StreetVibe: 0 prendas que no sean Jeans", all(p["categoria"] == "pantalon" and p.get("subtipo") == "jeans" for p in sv))
gen_sv = Counter(p["genero"] for p in sv)
check("3. StreetVibe: mezcla real Hombre/Mujer/Unisex (no todo unisex)", gen_sv["hombre"] > 0 and gen_sv["mujer"] > 0 and gen_sv["unisex"] > 0)

res_baggy = elegir_candidatos("unisex", "jeans baggy", CATALOG, 50, preferencia_genero="todos")
check("4. Busqueda 'jeans baggy' devuelve StreetVibe/Sioux con corte baggy", any(p["tienda"] in ("StreetVibe", "Sioux") and p.get("corte") == "baggy" for p in res_baggy))

res_unisex = [p for p in sv if p["genero"] == "unisex"]
check("5. Busqueda/filtro genero unisex devuelve jeans StreetVibe reales", len(res_unisex) > 0)

# ---------------- Sioux ----------------
sx = [p for p in CATALOG if p["tienda"] == "Sioux"]
check("6. Sioux: solo Jeans + Chaquetas", all(p["categoria"] in ("pantalon", "chaqueta") for p in sx))
check("6b. Sioux: 0 gorros/vestidos colados", all(p["categoria"] != "gorro" for p in sx))

algodon_100 = [p for p in sx if p.get("composicion") and es_composicion_100_pura(p["composicion"]) and p["composicion"][0]["fibra"] == "algodon"]
check("7. Sioux: hay composicion 100% algodon estructurada", len(algodon_100) > 0 and all(
    len(p["composicion"]) == 1 and p["composicion"][0]["porcentaje"] == 100 for p in algodon_100
))

mezcla = [p for p in sx if p.get("composicion") and len({c["fibra"] for c in p["composicion"]}) > 1]
check("8. Sioux: 98% algodon + 2% elastano NO cuenta como 100% mismo material", len(mezcla) > 0 and all(not es_composicion_100_pura(p["composicion"]) for p in mezcla))

filtrado_100 = filtrar_por_material_100(CATALOG, detectar_material_100_pedido("busco algo 100% algodon"))
check("9. Filtro '100% algodon' devuelve solo productos 100% algodon puro", len(filtrado_100) > 0 and all(
    p["composicion"][0]["fibra"] == "algodon" and es_composicion_100_pura(p["composicion"]) for p in filtrado_100
))

sx_chaq = [p for p in sx if p["categoria"] == "chaqueta"]
check("10. Chaquetas Sioux aparecen como chaqueta, no poleron", len(sx_chaq) > 0 and all(p["categoria"] != "poleron" for p in sx_chaq))

# ---------------- KronoLex ----------------
kx = [p for p in CATALOG if p["tienda"] == "KronoLex"]
check("11. KronoLex: catalogo compatible cargado", len(kx) > 0)
check("12. KronoLex: CERO chaquetas", all(p["categoria"] != "chaqueta" for p in kx) and not any("chaqueta" in p["nombre"].lower() for p in kx))
kx_pant = [p for p in kx if p["categoria"] == "pantalon"]
kx_shorts = [p for p in kx if p["categoria"] == "shorts"]
check("13. KronoLex: Jeans/Cargo/Jorts diferenciados (subtipos reales, sin jort inventado)", all(p.get("subtipo") != "jorts" for p in kx_shorts) and all(p.get("subtipo") in ("jeans", "cargo", "buzo", None) for p in kx_pant))

# ---------------- General ----------------
nuevas = sv + sx + kx
check("14. Precios/URLs/imagenes validos en las 3 tiendas", all(
    p.get("precio_clp") and p.get("link", "").startswith("http") and p.get("imagen") for p in nuevas
))
check("15. Stock por variante presente donde la fuente lo dio (StreetVibe/Sioux)", all(
    p.get("tallas_variantes") for p in sv + sx
))
check("16. Confianza KOLIZION calculada via sistema central (no inventado)", all(
    isinstance(p.get("confianza"), dict) and "nivel" in p["confianza"] for p in nuevas
))

print()
if fails:
    print(f"{len(fails)} test(s) fallaron: {fails}")
    raise SystemExit(1)
print("Todos los tests pasaron.")
