"""Configuracion de seguridad (se puede ajustar desde el .env)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _entero(nombre: str, defecto: int) -> int:
    return int(os.getenv(nombre, defecto))


SESION_HORAS = _entero("SESION_HORAS", 8)                     # duracion maxima de una sesion
SESION_INACTIVIDAD_MIN = _entero("SESION_INACTIVIDAD_MIN", 120)  # cierre por inactividad
MAX_INTENTOS = _entero("MAX_INTENTOS", 5)                     # intentos fallidos antes de bloquear
BLOQUEO_MIN = _entero("BLOQUEO_MIN", 15)                      # minutos de bloqueo temporal
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"  # true detras de HTTPS

COOKIE_SESION = "sesion"
COOKIE_CSRF = "csrf_pre"   # token de formulario para paginas sin sesion (login y registro)
