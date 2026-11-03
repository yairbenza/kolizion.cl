# Notificaciones push para la app de iOS (2026-11-03, ver ios-app/README.md).
#
# Apple (APNs) recibe los avisos y los entrega a cada iPhone. Para hablar con
# APNs se necesita una "clave de autenticacion" (.p8) que se descarga una sola
# vez desde developer.apple.com > Keys. Variables de entorno (ver .env.example):
#   APNS_KEY_ID      ID de 10 caracteres de esa clave
#   APNS_TEAM_ID     Team ID de la cuenta de Apple Developer
#   APNS_KEY_P8      contenido completo del archivo .p8 (con BEGIN/END)
#   APNS_ENTORNO     "produccion" (TestFlight y App Store) o "sandbox" (Xcode)
#   APPLE_BUNDLE_ID  cl.kolizion.app
# Si falta alguna, enviar() avisa con un error claro en vez de fallar raro.
#
# APNs exige HTTP/2, que la libreria estandar de Python (urllib) no habla --
# por eso aca si se usa httpx[http2] (agregada a requirements.txt).
import json
import os
import time

import jwt

import db_usuarios

APNS_KEY_ID = os.environ.get("APNS_KEY_ID", "")
APNS_TEAM_ID = os.environ.get("APNS_TEAM_ID", "")
APNS_KEY_P8 = os.environ.get("APNS_KEY_P8", "").replace("\\n", "\n")
APNS_ENTORNO = os.environ.get("APNS_ENTORNO", "produccion")
APPLE_BUNDLE_ID = os.environ.get("APPLE_BUNDLE_ID", "cl.kolizion.app")

_HOST_APNS = {
    "produccion": "https://api.push.apple.com",
    "sandbox": "https://api.sandbox.push.apple.com",
}
# Respuestas de APNs que significan "este token ya no sirve" (app borrada,
# token vencido): se sacan de la base de datos para no seguir mandandoles.
_RAZONES_TOKEN_MUERTO = {"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"}

_jwt_cache = {"token": None, "creado": 0}


def configurado():
    return bool(APNS_KEY_ID and APNS_TEAM_ID and "BEGIN PRIVATE KEY" in APNS_KEY_P8)


def _token_autorizacion():
    """APNs acepta el mismo JWT por hasta 1 hora -- se renueva cada 50 min."""
    if _jwt_cache["token"] and time.time() - _jwt_cache["creado"] < 50 * 60:
        return _jwt_cache["token"]
    ahora = int(time.time())
    token = jwt.encode(
        {"iss": APNS_TEAM_ID, "iat": ahora}, APNS_KEY_P8, algorithm="ES256",
        headers={"kid": APNS_KEY_ID},
    )
    _jwt_cache.update(token=token, creado=ahora)
    return token


def armar_payload(titulo, cuerpo, url=""):
    payload = {"aps": {"alert": {"title": titulo, "body": cuerpo}, "sound": "default"}}
    if url:
        payload["url"] = url
    return payload


def enviar_a_todos(titulo, cuerpo, url=""):
    """Manda el mismo aviso a todos los iPhone registrados. Devuelve
    {"enviados", "fallidos", "eliminados", "error"}."""
    if not configurado():
        return {"enviados": 0, "fallidos": 0, "eliminados": 0,
                "error": "Faltan las variables APNS_KEY_ID / APNS_TEAM_ID / APNS_KEY_P8 en el servidor."}

    import httpx  # import aca: solo hace falta al enviar, no para arrancar la app

    tokens = db_usuarios.listar_tokens_push("ios")
    resultado = {"enviados": 0, "fallidos": 0, "eliminados": 0, "error": ""}
    if not tokens:
        return resultado

    cuerpo_json = json.dumps(armar_payload(titulo, cuerpo, url), ensure_ascii=False).encode()
    headers = {
        "authorization": f"bearer {_token_autorizacion()}",
        "apns-topic": APPLE_BUNDLE_ID,
        "apns-push-type": "alert",
        "apns-priority": "10",
    }
    host = _HOST_APNS.get(APNS_ENTORNO, _HOST_APNS["produccion"])
    with httpx.Client(http2=True, timeout=10) as cliente:
        for token in tokens:
            try:
                resp = cliente.post(f"{host}/3/device/{token}", content=cuerpo_json, headers=headers)
            except httpx.HTTPError:
                resultado["fallidos"] += 1
                continue
            if resp.status_code == 200:
                resultado["enviados"] += 1
                continue
            resultado["fallidos"] += 1
            try:
                razon = resp.json().get("reason", "")
            except ValueError:
                razon = ""
            if resp.status_code == 410 or razon in _RAZONES_TOKEN_MUERTO:
                db_usuarios.eliminar_dispositivo(token)
                resultado["eliminados"] += 1
            elif razon in {"InvalidProviderToken", "ExpiredProviderToken", "TopicDisallowed"}:
                resultado["error"] = f"Apple rechazó la clave del servidor ({razon}) -- revisa APNS_KEY_ID, APNS_TEAM_ID y APNS_KEY_P8."
                break
    return resultado
