# Base de datos de cuentas reales (Google + email/contraseña). Unica
# excepcion al patron "todo vive en app.py" de este proyecto -- se separo
# aca porque el schema + las funciones CRUD de la tabla "usuarios" son una
# pieza autocontenida que de otra forma hace mas dificil navegar app.py
# (ya con ~2800 lineas antes de esto). Es la PRIMERA base de datos SQL del
# proyecto -- todo lo demas (favoritos, historial, tiendas, etc.) sigue
# viviendo en data/*.json como siempre, esto no cambia.
#
# Toda consulta usa "?" como placeholder, NUNCA f-strings/concatenacion --
# es lo que mantiene cierto que este proyecto no tiene SQL injection (ver
# docs/seguridad.md).
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "kolizion.db"

# Campos de perfil que ya existian en localStorage (ver comun.js
# getPerfil/guardarPerfil) -- se reusan tal cual como columnas, para que
# migrar un perfil viejo sea copiar estos mismos nombres.
CAMPOS_PERFIL_TEXTO = ["nombre", "apellido", "genero", "direccion", "telefono"]
CAMPOS_PERFIL_NUMERO = ["edad", "altura", "peso"]
CAMPOS_PERFIL_LISTA = ["hobbie", "hobbie_musica_genero", "hobbie_deportes_subtipo"]


def get_conexion():
    """Conexion nueva por llamada -- este proyecto corre como un solo
    proceso Flask de desarrollo (ver comentario sobre flask-limiter en
    app.py), asi que no hace falta pool de conexiones. sqlite3.Row deja
    acceder a las columnas por nombre (fila["email"]) en vez de por
    indice."""
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


def inicializar_db():
    """Crea la tabla si no existe -- se llama una sola vez al arrancar la
    app (ver app.py). CREATE TABLE IF NOT EXISTS es seguro de llamar cada
    vez que arranca el servidor, no borra nada si ya existia."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conexion = get_conexion()
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            email                    TEXT NOT NULL UNIQUE,
            password_hash            TEXT,
            google_sub               TEXT UNIQUE,
            nombre                   TEXT,
            apellido                 TEXT,
            genero                   TEXT,
            edad                     INTEGER,
            altura                   REAL,
            peso                     REAL,
            direccion                TEXT,
            telefono                 TEXT,
            hobbie                   TEXT,
            hobbie_musica_genero     TEXT,
            hobbie_deportes_subtipo  TEXT,
            foto_perfil              TEXT,
            creado_en                TEXT NOT NULL,
            actualizado_en           TEXT,
            CHECK (password_hash IS NOT NULL OR google_sub IS NOT NULL)
        )
    """)
    conexion.commit()
    conexion.close()


def _normalizar_email(email):
    return (email or "").strip().lower()


def _numero_o_none(valor):
    """Convierte texto de un input HTML (ej. altura='1.80') a numero, o
    None si esta vacio/no es numero -- nunca revienta con un ValueError
    por un dato con formato raro (ej. '1,80' o 'no se')."""
    if valor in (None, ""):
        return None
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return None


def _lista_a_json(valor):
    """Las listas de hobbies llegan como list de Python (desde el perfil
    de localStorage) -- SQLite no tiene tipo array, se guardan como texto
    JSON y se decodifican de vuelta al leer (ver fila_a_dict)."""
    if not valor:
        return "[]"
    if isinstance(valor, str):
        return valor  # ya viene como JSON (ej. reenviado sin cambios)
    return json.dumps(valor, ensure_ascii=False)


def fila_a_dict(fila):
    """Convierte una fila de sqlite3.Row a dict, decodificando los campos
    de lista (guardados como texto JSON) de vuelta a listas de Python --
    mismo shape que el perfil de localStorage, para que el resto del
    codigo (JS y Python) no tenga que saber que la fuente cambio."""
    if fila is None:
        return None
    datos = dict(fila)
    for campo in CAMPOS_PERFIL_LISTA:
        try:
            datos[campo] = json.loads(datos.get(campo) or "[]")
        except (json.JSONDecodeError, TypeError):
            datos[campo] = []
    return datos


def listar_usuarios():
    """Todas las cuentas, mas nuevas primero -- para /admin/usuarios. Nunca
    incluye password_hash en el resultado (no hace falta para mostrarlo, y
    asi ni por error se termina mostrando algo asi en una pantalla)."""
    conexion = get_conexion()
    filas = conexion.execute(
        "SELECT id, email, google_sub, nombre, apellido, genero, edad, altura, peso, "
        "direccion, telefono, foto_perfil, creado_en, actualizado_en, "
        "(password_hash IS NOT NULL) AS tiene_password "
        "FROM usuarios ORDER BY creado_en DESC"
    ).fetchall()
    conexion.close()
    return [fila_a_dict(f) for f in filas]


def buscar_por_email(email):
    conexion = get_conexion()
    fila = conexion.execute(
        "SELECT * FROM usuarios WHERE email = ?", (_normalizar_email(email),)
    ).fetchone()
    conexion.close()
    return fila_a_dict(fila)


def buscar_por_google_sub(google_sub):
    if not google_sub:
        return None
    conexion = get_conexion()
    fila = conexion.execute(
        "SELECT * FROM usuarios WHERE google_sub = ?", (google_sub,)
    ).fetchone()
    conexion.close()
    return fila_a_dict(fila)


def buscar_por_id(usuario_id):
    conexion = get_conexion()
    fila = conexion.execute(
        "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    conexion.close()
    return fila_a_dict(fila)


def crear_usuario(email, password_hash=None, google_sub=None, perfil=None):
    """Crea una cuenta nueva. 'perfil' es el dict (opcional) migrado desde
    localStorage -- mismos nombres de campo que CAMPOS_PERFIL_*. Devuelve
    el usuario recien creado (como dict, ver fila_a_dict)."""
    perfil = perfil or {}
    ahora = datetime.now(timezone.utc).isoformat()

    columnas = ["email", "password_hash", "google_sub", "creado_en"]
    valores = [_normalizar_email(email), password_hash, google_sub, ahora]

    for campo in CAMPOS_PERFIL_TEXTO:
        columnas.append(campo)
        valores.append(perfil.get(campo) or None)
    for campo in CAMPOS_PERFIL_NUMERO:
        columnas.append(campo)
        valores.append(_numero_o_none(perfil.get(campo)))
    for campo in CAMPOS_PERFIL_LISTA:
        columnas.append(campo)
        valores.append(_lista_a_json(perfil.get(campo)))

    placeholders = ", ".join("?" for _ in columnas)
    conexion = get_conexion()
    cursor = conexion.execute(
        f"INSERT INTO usuarios ({', '.join(columnas)}) VALUES ({placeholders})",
        valores,
    )
    conexion.commit()
    usuario_id = cursor.lastrowid
    conexion.close()
    return buscar_por_id(usuario_id)


def actualizar_perfil(usuario_id, perfil):
    """Actualiza los campos de perfil (no email/password/google_sub) de
    una cuenta ya existente -- usada por /perfil cuando alguien edita sus
    datos ya logueado."""
    ahora = datetime.now(timezone.utc).isoformat()
    columnas = ["actualizado_en"]
    valores = [ahora]

    for campo in CAMPOS_PERFIL_TEXTO:
        if campo in perfil:
            columnas.append(campo)
            valores.append(perfil.get(campo) or None)
    for campo in CAMPOS_PERFIL_NUMERO:
        if campo in perfil:
            columnas.append(campo)
            valores.append(_numero_o_none(perfil.get(campo)))
    for campo in CAMPOS_PERFIL_LISTA:
        if campo in perfil:
            columnas.append(campo)
            valores.append(_lista_a_json(perfil.get(campo)))

    set_clause = ", ".join(f"{col} = ?" for col in columnas)
    valores.append(usuario_id)
    conexion = get_conexion()
    conexion.execute(f"UPDATE usuarios SET {set_clause} WHERE id = ?", valores)
    conexion.commit()
    conexion.close()


def actualizar_foto_perfil(usuario_id, ruta_relativa):
    conexion = get_conexion()
    conexion.execute(
        "UPDATE usuarios SET foto_perfil = ?, actualizado_en = ? WHERE id = ?",
        (ruta_relativa, datetime.now(timezone.utc).isoformat(), usuario_id),
    )
    conexion.commit()
    conexion.close()


def vincular_google(usuario_id, google_sub):
    """Vincula una cuenta que ya existia (creada con email/contraseña) a
    un google_sub -- caso de alguien que se registro con contraseña y
    despues usa 'Continuar con Google' con el mismo email."""
    conexion = get_conexion()
    conexion.execute(
        "UPDATE usuarios SET google_sub = ? WHERE id = ?", (google_sub, usuario_id)
    )
    conexion.commit()
    conexion.close()
