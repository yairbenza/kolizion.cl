from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def ip_cliente():
    """IP real de quien hace la peticion, para los limites por IP (auditoria
    de seguridad 2026-10-13). En produccion toda visita entra por Cloudflare
    (Render lo pone delante), asi que request.remote_addr es la IP del proxy
    -- la MISMA para todos. Antes de esto, cada limite "por IP" era en la
    practica un solo limite compartido por todo el sitio (10 personas usando
    Koko en el mismo minuto bloqueaban a todas las demas, y cualquiera podia
    dejar /login bloqueado para todos). Cloudflare pone la IP real en
    CF-Connecting-IP y pisa cualquier valor que intente mandar el navegador,
    asi que no se puede falsificar. Sin ese header (desarrollo local), se usa
    la IP directa de siempre."""
    return request.headers.get("CF-Connecting-IP", "").strip() or get_remote_address()


# default_limits: tope general por IP para TODAS las rutas que no tengan uno
# propio mas estricto -- red de seguridad contra spam/abuso de rutas que
# antes no tenian ningun limite (favoritos, perfil, subperfiles, etc.).
# Holgado a proposito: una persona normal no se acerca ni de lejos.
limiter = Limiter(
    ip_cliente,
    storage_uri="memory://",
    default_limits=["300 per minute", "5000 per hour"],
)
