"""Utilidades de seguridad: hash de contrasenas, tokens y validaciones."""
import hashlib
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_ph = PasswordHasher()  # Argon2id con parametros por defecto recomendados
# Hash falso para que verificar() tarde igual cuando el correo no existe
_HASH_FALSO = _ph.hash("contrasena-inexistente-para-igualar-tiempos")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hashear(contrasena: str) -> str:
    return _ph.hash(contrasena)


def verificar(hash_guardado: str | None, contrasena: str) -> bool:
    objetivo = hash_guardado or _HASH_FALSO
    try:
        correcto = _ph.verify(objetivo, contrasena)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        correcto = False
    return correcto and hash_guardado is not None


def necesita_rehash(hash_guardado: str) -> bool:
    return _ph.check_needs_rehash(hash_guardado)


def nuevo_token() -> str:
    """Token aleatorio de 256 bits, seguro para URL y cookies."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 del token. En la base solo se guarda el hash, nunca el token."""
    return hashlib.sha256(token.encode()).hexdigest()


def tokens_iguales(a: str, b: str) -> bool:
    """Comparacion en tiempo constante (evita ataques de temporizacion)."""
    return bool(a) and bool(b) and secrets.compare_digest(a.encode(), b.encode())


def normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def email_valido(email: str) -> bool:
    return len(email) <= 254 and bool(EMAIL_RE.match(email))


def errores_contrasena(contrasena: str, email: str = "") -> list[str]:
    errores = []
    if len(contrasena) < 10:
        errores.append("Debe tener al menos 10 caracteres.")
    if len(contrasena) > 128:
        errores.append("Debe tener máximo 128 caracteres.")
    if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", contrasena) or not re.search(r"\d", contrasena):
        errores.append("Debe incluir letras y números.")
    if email and contrasena.lower() == email.lower():
        errores.append("No puede ser igual al correo.")
    return errores
