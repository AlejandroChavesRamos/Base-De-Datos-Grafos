"""Logica de registro, inicio y cierre de sesion."""
import uuid

from neo4j.exceptions import ConstraintError

from app import config
from app.repositories import cuentas, eventos, sesiones
from app.services import seguridad

SECTORES = ["Tecnología", "Logística", "Salud", "Finanzas", "Educación", "Marketing y Diseño",
            "Comercio Exterior", "Manufactura", "Construcción", "Comercio", "Servicios", "Otro"]
TAMANOS = {"pequena": "Pequeña", "mediana": "Mediana", "grande": "Grande"}


class ErrorFormulario(Exception):
    """Errores de validacion por campo: {'email': 'mensaje', ...}"""

    def __init__(self, errores: dict):
        super().__init__("Formulario invalido")
        self.errores = errores


def _limpiar(valor: str, maximo: int) -> str:
    return " ".join((valor or "").split())[:maximo]


def _validar_acceso(email: str, password: str, password2: str, errores: dict):
    if not seguridad.email_valido(email):
        errores["email"] = "Escribe un correo válido."
    problemas = seguridad.errores_contrasena(password, email)
    if problemas:
        errores["password"] = " ".join(problemas)
    elif password != password2:
        errores["password2"] = "Las contraseñas no coinciden."


def registrar_persona(form: dict, ip: str) -> dict:
    nombre = _limpiar(form.get("nombre"), 60)
    apellido = _limpiar(form.get("apellido"), 60)
    titular = _limpiar(form.get("titular"), 120)
    ciudad = _limpiar(form.get("ciudad"), 60)
    email = seguridad.normalizar_email(form.get("email"))
    errores: dict = {}
    if not nombre:
        errores["nombre"] = "Escribe tu nombre."
    if not apellido:
        errores["apellido"] = "Escribe tu apellido."
    if not ciudad:
        errores["ciudad"] = "Escribe tu ciudad."
    _validar_acceso(email, form.get("password", ""), form.get("password2", ""), errores)
    if errores:
        raise ErrorFormulario(errores)

    datos = {"cuenta_id": uuid.uuid4().hex, "perfil_id": uuid.uuid4().hex, "email": email,
             "hash": seguridad.hashear(form["password"]), "nombre": nombre, "apellido": apellido,
             "titular": titular or "Profesional en búsqueda de oportunidades", "ciudad": ciudad}
    try:
        cuenta_id = cuentas.crear_persona(datos)
    except ConstraintError:
        raise ErrorFormulario({"email": "Este correo ya está registrado."})
    if not cuenta_id:
        raise RuntimeError("Faltan los roles en la base. Ejecuta cypher/01_schema.cypher.")
    eventos.registrar(cuenta_id, "registro", ip, "persona")
    return {"cuenta_id": cuenta_id, "perfil_id": datos["perfil_id"], "tipo": "persona"}


def registrar_empresa(form: dict, ip: str) -> dict:
    nombre = _limpiar(form.get("nombre"), 100)
    sector = form.get("sector", "")
    tamano = form.get("tamano", "")
    ciudad = _limpiar(form.get("ciudad"), 60)
    descripcion = _limpiar(form.get("descripcion"), 400)
    sitio_web = _limpiar(form.get("sitio_web"), 200)
    email = seguridad.normalizar_email(form.get("email"))
    errores: dict = {}
    if not nombre:
        errores["nombre"] = "Escribe el nombre de la empresa."
    if sector not in SECTORES:
        errores["sector"] = "Elige un sector."
    if tamano not in TAMANOS:
        errores["tamano"] = "Elige el tamaño de la empresa."
    if not ciudad:
        errores["ciudad"] = "Escribe la ciudad."
    if sitio_web and not sitio_web.lower().startswith(("http://", "https://")):
        errores["sitio_web"] = "Debe empezar por http:// o https://"
    _validar_acceso(email, form.get("password", ""), form.get("password2", ""), errores)
    if errores:
        raise ErrorFormulario(errores)

    datos = {"cuenta_id": uuid.uuid4().hex, "perfil_id": uuid.uuid4().hex, "email": email,
             "hash": seguridad.hashear(form["password"]), "nombre": nombre, "sector": sector,
             "tamano": tamano, "ciudad": ciudad,
             "descripcion": descripcion or "Empresa registrada en LinkedUn.", "sitio_web": sitio_web}
    try:
        cuenta_id = cuentas.crear_empresa(datos)
    except ConstraintError:
        raise ErrorFormulario({"email": "Este correo ya está registrado."})
    if not cuenta_id:
        raise RuntimeError("Faltan los roles en la base. Ejecuta cypher/01_schema.cypher.")
    eventos.registrar(cuenta_id, "registro", ip, "empresa")
    return {"cuenta_id": cuenta_id, "perfil_id": datos["perfil_id"], "tipo": "empresa"}


def abrir_sesion(cuenta_id: str, ip: str, user_agent: str) -> str:
    """Crea una sesion NUEVA (siempre, para evitar fijacion de sesion). Devuelve el token
    que va en la cookie; en la base solo queda su hash."""
    token = seguridad.nuevo_token()
    sesiones.crear(cuenta_id, seguridad.hash_token(token), seguridad.nuevo_token(), ip, user_agent[:200])
    return token


def iniciar_sesion(email: str, contrasena: str, ip: str, user_agent: str) -> str | None:
    """Devuelve el token de sesion, o None si las credenciales no son validas.
    El motivo del fallo nunca se revela a quien intenta entrar."""
    email = seguridad.normalizar_email(email)
    cuenta = cuentas.por_email(email)
    # Se verifica SIEMPRE (con un hash falso si no existe) para que tarde lo mismo
    correcta = seguridad.verificar(cuenta["password_hash"] if cuenta else None, contrasena)

    if not cuenta:
        eventos.registrar(None, "login_fallido", ip, "correo no registrado")
        return None
    if cuenta["bloqueada"] or not cuenta["activa"]:
        eventos.registrar(cuenta["id"], "login_rechazado", ip, "cuenta bloqueada o inactiva")
        return None
    if not correcta:
        estado = cuentas.registrar_fallo(cuenta["id"], config.MAX_INTENTOS, config.BLOQUEO_MIN)
        eventos.registrar(cuenta["id"], "login_fallido", ip, f"intento {estado['intentos']}")
        if estado["bloqueada"]:
            eventos.registrar(cuenta["id"], "cuenta_bloqueada", ip, f"{config.BLOQUEO_MIN} minutos")
        return None

    cuentas.reiniciar_intentos(cuenta["id"])
    if seguridad.necesita_rehash(cuenta["password_hash"]):
        cuentas.actualizar_hash(cuenta["id"], seguridad.hashear(contrasena))
    token = abrir_sesion(cuenta["id"], ip, user_agent)
    eventos.registrar(cuenta["id"], "login_ok", ip)
    return token


def cerrar_sesion(token: str):
    sesiones.revocar(seguridad.hash_token(token))


# ------------------------------------------------ acciones sobre la propia cuenta
def confirmar_contrasena(cuenta_id: str, contrasena: str, ip: str) -> bool:
    """Pide la contrasena otra vez para acciones sensibles. Los fallos cuentan para el
    bloqueo, asi una sesion robada no sirve para adivinar la contrasena sin limite."""
    cuenta = cuentas.por_id(cuenta_id)
    if not cuenta:
        return False
    correcta = seguridad.verificar(cuenta["password_hash"], contrasena)
    if cuenta["bloqueada"]:
        return False
    if not correcta:
        cuentas.registrar_fallo(cuenta_id, config.MAX_INTENTOS, config.BLOQUEO_MIN)
        eventos.registrar(cuenta_id, "verificacion_fallida", ip, "confirmacion de contrasena")
        return False
    cuentas.reiniciar_intentos(cuenta_id)
    return True


def cambiar_contrasena(cuenta_id: str, email: str, actual: str, nueva: str, nueva2: str,
                       token_actual: str, ip: str) -> dict:
    """Devuelve un diccionario de errores (vacio si todo salio bien). Al cambiarla se
    cierran las DEMAS sesiones de la cuenta."""
    errores: dict = {}
    problemas = seguridad.errores_contrasena(nueva, email)
    if problemas:
        errores["nueva"] = " ".join(problemas)
    elif nueva != nueva2:
        errores["nueva2"] = "Las contraseñas no coinciden."
    elif nueva == actual:
        errores["nueva"] = "La nueva contraseña debe ser distinta de la actual."
    if errores:
        return errores
    if not confirmar_contrasena(cuenta_id, actual, ip):
        return {"actual": "La contraseña actual no es correcta."}
    cuentas.actualizar_hash(cuenta_id, seguridad.hashear(nueva))
    sesiones.revocar_otras(cuenta_id, seguridad.hash_token(token_actual))
    eventos.registrar(cuenta_id, "password_cambiada", ip, "se cerraron las demás sesiones")
    return {}
