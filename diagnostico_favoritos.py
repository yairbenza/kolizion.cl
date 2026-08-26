"""Chequeo rapido y acotado del nuevo sistema de favoritos, via
app.test_client() (nunca levanta un servidor real -- ver CLAUDE.md)."""
import json
from pathlib import Path

import app as app_module

FAVORITOS_PATH = app_module.FAVORITOS_PATH
respaldo = FAVORITOS_PATH.read_text(encoding="utf-8") if FAVORITOS_PATH.exists() else None

try:
    cliente = app_module.app.test_client()
    email = "diagnostico@test.cl"
    producto = {"nombre": "Poleron test diagnostico", "tienda": "Tienda X", "categoria": "poleron",
                "corte": "oversized", "precio": "$20.000", "link": "/ir/x/producto"}

    # 1) Vacio al principio
    resp = cliente.get(f"/api/favoritos?email={email}")
    assert resp.status_code == 200, resp.status_code
    assert resp.get_json()["favoritos"] == [], resp.get_json()

    # 2) Marcar
    resp = cliente.post("/api/favoritos", json={"email": email, "producto": producto})
    data = resp.get_json()
    assert resp.status_code == 200 and data["marcado"] is True, data

    resp = cliente.get(f"/api/favoritos?email={email}")
    favoritos = resp.get_json()["favoritos"]
    assert len(favoritos) == 1 and favoritos[0]["nombre"] == producto["nombre"], favoritos

    # 3) Volver a tocar la estrella = sacarlo
    resp = cliente.post("/api/favoritos", json={"email": email, "producto": producto})
    data = resp.get_json()
    assert data["marcado"] is False, data

    resp = cliente.get(f"/api/favoritos?email={email}")
    assert resp.get_json()["favoritos"] == []

    # 4) Sin email o sin nombre de producto -> error controlado, no 500
    resp = cliente.post("/api/favoritos", json={"email": "", "producto": producto})
    assert resp.status_code == 400
    resp = cliente.post("/api/favoritos", json={"email": email, "producto": {}})
    assert resp.status_code == 400

    print("OK: /api/favoritos funciona (marcar, listar, sacar, validaciones).")
finally:
    if respaldo is not None:
        FAVORITOS_PATH.write_text(respaldo, encoding="utf-8")
    elif FAVORITOS_PATH.exists():
        FAVORITOS_PATH.unlink()
