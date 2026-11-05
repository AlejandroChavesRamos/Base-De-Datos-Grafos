from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError

_ph = PasswordHasher()
# Hash falso para igualar tiempos cuando el email no existe
_HASH_FALSO = _ph.hash("contraseña-inexistente")

def hashear(contrasena: str) -> str:
    return _ph.hash(contrasena)

def verificar(hash_guardado: str | None, contrasena: str) -> bool:
    try:
        return _ph.verify(hash_guardado or _HASH_FALSO, contrasena) and hash_guardado is not None
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False

def necesita_rehash(hash_guardado: str) -> bool:
    return _ph.check_needs_rehash(hash_guardado)