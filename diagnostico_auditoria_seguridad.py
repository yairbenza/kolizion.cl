"""Prueba real de los arreglos de seguridad (2026-10-13), con test_client y
una carpeta de datos TEMPORAL (nunca toca kolizion.db ni los JSON reales).
Correr desde la carpeta del proyecto: python diagnostico_auditoria_seguridad.py"""
import os
import sys
import tempfile
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="kz_seg_")
os.environ["KOLIZION_DATA_DIR"] = TMP
os.environ["KOLIZION_DB_PATH"] = str(Path(TMP) / "kolizion.db")
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-clave-invalida-de-prueba"  # nunca la real
os.environ["KOLIZION_DEBUG"] = ""
sys.path.insert(0, os.getcwd())

import app as m  # noqa: E402
import db_usuarios  # noqa: E402

assert str(db_usuarios.DB_PATH).startswith(TMP), db_usuarios.DB_PATH
c = m.app.test_client()
fallas = []


def chequear(condicion, texto):
    print(("OK   " if condicion else "FALLA ") + texto)
    if not condicion:
        fallas.append(texto)


def ip(n):
    return {"CF-Connecting-IP": f"203.0.113.{n}"}


# 1) Archivos sensibles NO accesibles por URL.
for url in ["/.env", "/static/../.env", "/static/%2e%2e/.env", "/static/.env", "/kolizion.db",
            "/data/kolizion.db", "/data/flask_secret_key.txt", "/app.py", "/.git/config",
            "/static/../app.py", "/static/comun.js.map", "/data/catalog.json"]:
    r = c.get(url, headers=ip(1))
    cuerpo = r.get_data(as_text=True)
    chequear(r.status_code == 404 and "ANTHROPIC" not in cuerpo and "SECRET" not in cuerpo,
             f"{url} -> {r.status_code} (debe ser 404)")
mapas = list(Path("static").rglob("*.map"))
chequear(not mapas, f"sin source maps en static/ ({mapas})")
js = " ".join(p.read_text(encoding="utf-8", errors="ignore") for p in Path("static").rglob("*.js"))
html = " ".join(p.read_text(encoding="utf-8", errors="ignore") for p in Path("templates").rglob("*.html"))
for secreto in ["ANTHROPIC_API_KEY", "GOOGLE_CLIENT_SECRET", "ADMIN_PASSWORD", "FLASK_SECRET_KEY", "sk-ant-", "GOCSPX-"]:
    chequear(secreto not in js and secreto not in html, f"'{secreto}' no aparece en static/ ni templates/")

# 2) Limite por IP: cada IP tiene su propio contador (antes era uno solo para todos).
m.limiter.reset()
codigos_a = [c.post("/api/koko/reiniciar", json={}, headers=ip(10)).status_code for _ in range(11)]
codigo_b = c.post("/api/koko/reiniciar", json={}, headers=ip(11)).status_code
chequear(codigos_a[:10] == [200] * 10 and codigos_a[10] == 429, f"IP A bloqueada en el intento 11 ({codigos_a})")
chequear(codigo_b == 200, f"IP B NO queda bloqueada por culpa de IP A ({codigo_b})")
m.limiter.reset()
codigos = [c.get("/api/estimar_talla", headers=ip(12)).status_code for _ in range(301)]
chequear(codigos[:300] == [200] * 300 and codigos[300] == 429,
         f"limite general: ruta sin limite propio bloquea la peticion 301 por minuto ({codigos[-2:]})")

# 3) Registro: honeypot, correo invalido, clave larga, caso normal.
m.limiter.reset()
r = c.post("/registro", data={"email": "bot@test.cl", "password": "clave-larga-123", "kz_web": "http://spam"}, headers=ip(20))
chequear(db_usuarios.buscar_por_email("bot@test.cl") is None and r.status_code == 200, "honeypot lleno -> NO crea cuenta")
c.post("/registro", data={"email": "sin-arroba", "password": "clave-larga-123"}, headers=ip(20))
c.post("/registro", data={"email": "a@b", "password": "clave-larga-123"}, headers=ip(20))
chequear(db_usuarios.buscar_por_email("a@b") is None, "correo sin dominio valido -> rechazado")
c.post("/registro", data={"email": "largo@test.cl", "password": "x" * 300}, headers=ip(20))
chequear(db_usuarios.buscar_por_email("largo@test.cl") is None, "clave de 300 caracteres -> rechazada")
r = c.post("/registro", data={"email": "persona@test.cl", "password": "clave-larga-123", "kz_web": ""}, headers=ip(20))
chequear(db_usuarios.buscar_por_email("persona@test.cl") is not None and r.status_code == 302, "registro normal sigue funcionando")
c.post("/logout")

# 4) Login: honeypot bloquea aunque la clave sea correcta; login normal OK.
m.limiter.reset()
r = c.post("/login", data={"email": "persona@test.cl", "password": "clave-larga-123", "kz_web": "x"}, headers=ip(21))
chequear(r.status_code == 200 and "incorrectos" in r.get_data(as_text=True), "login con honeypot lleno -> rechazado")
r = c.post("/login", data={"email": "persona@test.cl", "password": "clave-larga-123"}, headers=ip(21))
chequear(r.status_code == 302, "login normal sigue funcionando")
c.post("/logout")
pagina = c.get("/login", headers=ip(21)).get_data(as_text=True)
chequear('name="kz_web"' in pagina, "el campo trampa aparece en /login")
chequear('name="kz_web"' in c.get("/registro", headers=ip(21)).get_data(as_text=True), "el campo trampa aparece en /registro")

# 5) Koko: tope global, tope por IP, error generico.
msg = {"email": "koko@test.cl", "mensajes": [{"rol": "usuario", "texto": "hola"}]}
m.limiter.reset()
os.environ["KOKO_LIMITE_DIA_GLOBAL"] = "0"
d = c.post("/api/koko/chat", json=msg, headers=ip(30)).get_json()
chequear(d.get("limite_alcanzado") is True and "energía" in d["respuesta_texto"], "tope GLOBAL alcanzado -> no llama a la IA")
os.environ["KOKO_LIMITE_DIA_POR_IP"] = "2"
m.limiter.reset()
codigos = [c.post("/api/koko/chat", json=dict(msg, email=f"otro{i}@test.cl"), headers=ip(31)).status_code for i in range(3)]
chequear(codigos == [200, 200, 429], f"tope por IP: cambiar de correo no lo salta ({codigos})")
os.environ["KOKO_LIMITE_DIA_POR_IP"] = ""
os.environ["KOKO_LIMITE_DIA_POR_PERSONA"] = "1"
os.environ["KOKO_LIMITE_DIA_GLOBAL"] = ""
m.limiter.reset()
d1 = c.post("/api/koko/chat", json=msg, headers=ip(32)).get_json()
chequear("problema para responder" in d1["respuesta_texto"] and "sk-ant" not in d1["respuesta_texto"]
         and "401" not in d1["respuesta_texto"] and "Error" not in d1["respuesta_texto"],
         f"error de la IA -> mensaje generico sin detalles ({d1['respuesta_texto'][:70]!r})")
d2 = c.post("/api/koko/chat", json=msg, headers=ip(32)).get_json()
chequear(d2.get("limite_alcanzado") is True, "tope POR PERSONA (1) -> el 2do mensaje no llama a la IA")
os.environ["KOKO_LIMITE_DIA_POR_PERSONA"] = ""
chequear(m.tope_koko("KOKO_LIMITE_DIA_POR_PERSONA", m.LIMITE_MENSAJES_KOKO_DIA) == 15, "tope por persona por defecto = 15")
chequear(m.mensajes_koko_globales_hoy() >= 1, "el contador global del dia suma")

# 6) Favoritos: tope por persona.
import servicio_tiendas  # noqa: E402
servicio_tiendas.MAX_FAVORITOS_POR_PERSONA = 2
m.limiter.reset()
res = [c.post("/api/favoritos", json={"email": "fav@test.cl", "producto": {"nombre": f"P{i}"}}, headers=ip(40)).get_json()["marcado"] for i in range(3)]
chequear(res == [True, True, False], f"tope de favoritos por persona ({res})")

# 7) Entrada mal formada no revienta (500).
m.limiter.reset()
for ruta, cuerpo in [("/api/koko/chat", {"mensajes": "no-es-lista", "perfil": [1]}),
                     ("/api/favoritos", {"email": ["x"], "producto": "texto"}),
                     ("/api/recommend", {"categoria": ["a"], "precio": {"x": 1}})]:
    r = c.post(ruta, json=cuerpo, headers=ip(50))
    chequear(r.status_code < 500, f"{ruta} con datos basura -> {r.status_code} (sin error 500)")
r = c.post("/api/recommend", data=b"x" * (4 * 1024 * 1024), headers=dict(ip(50), **{"Content-Type": "application/json"}))
chequear(r.status_code == 413, f"peticion de 4 MB -> {r.status_code} (debe ser 413, demasiado grande)")

print()
print(f"carpeta temporal usada: {TMP}")
print("TODO OK" if not fallas else f"{len(fallas)} FALLA(S)")
sys.exit(1 if fallas else 0)
