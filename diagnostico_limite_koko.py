"""Chequeo acotado del limite diario de mensajes a Koko: conteo/poda de
fechas, bloqueo real via la ruta (sin gastar en la API -- se sembra el
archivo de limite directo), y que 'Reiniciar conversacion' NO sirva para
saltarse el limite (el bug que se evito a proposito). test_client, nunca
un servidor real."""
import json
from datetime import datetime, timedelta, timezone

import app as m

cliente = m.app.test_client()
respaldo_limite = m.LIMITE_KOKO_PATH.read_text(encoding="utf-8") if m.LIMITE_KOKO_PATH.exists() else None
respaldo_chats = m.CHATS_KOKO_PATH.read_text(encoding="utf-8") if m.CHATS_KOKO_PATH.exists() else None

try:
    email = "diag-limite@test.cl"

    # 1) registrar_mensaje_usuario_koko + conteo + poda de fechas viejas.
    m.guardar_limite_koko({})  # arranca limpio
    ahora = datetime.now(timezone.utc)
    m.guardar_limite_koko({
        email: [
            (ahora - timedelta(hours=1)).isoformat(),   # cuenta
            (ahora - timedelta(hours=23)).isoformat(),  # cuenta (justo dentro)
            (ahora - timedelta(hours=25)).isoformat(),  # NO cuenta (fuera de 24h)
            (ahora - timedelta(hours=50)).isoformat(),  # se poda al registrar uno nuevo (>48h)
        ]
    })
    assert m.mensajes_usuario_ultimas_24h(email) == 2, m.mensajes_usuario_ultimas_24h(email)
    print("OK: cuenta solo los mensajes de las ultimas 24h.")

    m.registrar_mensaje_usuario_koko(email)
    fechas = m.cargar_limite_koko()[email]
    # Se guarda con umbral de 48h (1h, 23h, 25h + el nuevo -- el de 50h se
    # poda), pero se CUENTA con umbral de 24h (1h, 23h y el nuevo -- el de
    # 25h queda guardado pero no cuenta para el limite).
    assert len(fechas) == 4, fechas
    assert m.mensajes_usuario_ultimas_24h(email) == 3, m.mensajes_usuario_ultimas_24h(email)
    print("OK: registrar_mensaje_usuario_koko agrega y poda solo lo de mas de 48h; el conteo usa 24h.")

    # 2) Bloqueo real via la ruta -- se sembra el limite ya topado (15),
    # sin llamar a la API real.
    m.guardar_limite_koko({email: [(ahora - timedelta(minutes=1)).isoformat()] * m.LIMITE_MENSAJES_KOKO_DIA})
    resp = cliente.post("/api/koko/chat", json={
        "email": email, "perfil": {"genero": "Hombre"},
        "mensajes": [{"rol": "usuario", "texto": "hola de nuevo"}],
    })
    data = resp.get_json()
    assert data.get("limite_alcanzado") is True, data
    assert "límite" in data["respuesta_texto"].lower()
    print("OK: con 15 mensajes en las ultimas 24h, la ruta bloquea sin llamar a la API.")

    # El intento bloqueado NO debe sumar al conteo (se quedan en 15, no 16).
    assert m.mensajes_usuario_ultimas_24h(email) == m.LIMITE_MENSAJES_KOKO_DIA
    print("OK: el intento bloqueado no suma al conteo.")

    # Igual queda guardado en el historial visible (chats_koko.json).
    historial = m.cargar_historial_chat(email)
    assert historial[-2]["texto"] == "hola de nuevo"
    assert "límite" in historial[-1]["texto"].lower()
    print("OK: el intercambio bloqueado igual queda en el historial visible.")

    # 3) "Reiniciar conversacion" NO debe resetear el limite (el loophole que se evito).
    m.reiniciar_chat_koko(email)
    assert m.cargar_historial_chat(email) == []  # el historial visible SI se borra
    assert m.mensajes_usuario_ultimas_24h(email) == m.LIMITE_MENSAJES_KOKO_DIA  # el limite NO
    print("OK: reiniciar la conversacion borra el historial visible pero NO el limite diario.")

    resp2 = cliente.post("/api/koko/chat", json={
        "email": email, "perfil": {},
        "mensajes": [{"rol": "usuario", "texto": "intento despues de reiniciar"}],
    })
    assert resp2.get_json().get("limite_alcanzado") is True
    print("OK: despues de reiniciar la conversacion, sigue bloqueado -- no hay atajo.")

    # 4) Sin email, no hay limite (no hay como llevar la cuenta).
    assert m.mensajes_usuario_ultimas_24h("") == 0
    print("OK: sin email, mensajes_usuario_ultimas_24h da 0 (sin romper).")

    # 5) Piezas del frontend.
    koko_js = cliente.get("/static/koko.js").get_data(as_text=True)
    for pieza in ["deshabilitarInputKoko", "limite_alcanzado"]:
        assert pieza in koko_js, f"falta {pieza} en koko.js"
    print("OK: koko.js maneja 'limite_alcanzado' y deshabilita el input.")

finally:
    if respaldo_limite is not None:
        m.LIMITE_KOKO_PATH.write_text(respaldo_limite, encoding="utf-8")
    elif m.LIMITE_KOKO_PATH.exists():
        m.LIMITE_KOKO_PATH.unlink()
    if respaldo_chats is not None:
        m.CHATS_KOKO_PATH.write_text(respaldo_chats, encoding="utf-8")

print("\nTodo OK.")
