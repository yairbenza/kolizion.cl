"""Chequeo puntual del nuevo /api/vitrina (ofertas ordenadas por
descuento, tendencias con razon)."""
from app import app

cliente = app.test_client()
data = cliente.get("/api/vitrina").get_json()

print("=== Ofertas (deberian venir ordenadas de mayor a menor %) ===")
porcentajes = [r["razon"] for r in data["ofertas"][:5]]
for razon in porcentajes:
    print(" ", razon)

print("\n=== Tendencias (sin clics reales todavia -> respaldo generico) ===")
for r in data["tendencias"][:4]:
    print(" ", r["nombre"][:50], "->", r["razon"])

print(f"\nTotales: tendencias={len(data['tendencias'])} ofertas={len(data['ofertas'])} destacados={len(data['destacados'])}")
