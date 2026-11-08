"""
Dependencias de FastAPI: identifican a quien hace la peticion y aplican la
seguridad (sesion, rol, permiso y CSRF). Las rutas solo declaran lo que exigen:

    Depends(usuario_actual)                       -> persona con sesion valida
    Depends(visor)                                -> cualquier cuenta con sesion valida
    Depends(permiso_requerido("usuario.bloquear")) -> permiso verificado en el grafo
    Depends(verificar_csrf)                       -> POST autenticado con token CSRF
"""
from urllib.parse import quote

from fastapi import Depends, HTTPException, Request

from app import config
from app.repositories import ofertas, sesiones, usuarios
from app.services import seguridad


def redirigir(url: str, codigo: int = 303) -> HTTPException:
    """Redireccion lanzada como excepcion (main.py la convierte en respuesta)."""
    return HTTPException(codigo, headers={"Location": url})


def ruta_interna(url: str | None, defecto: str = "/") -> str:
    """Solo permite redirigir a rutas internas (evita 'open redirect')."""
    if url and url.startswith("/") and not url.startswith("//") and "\\" not in url:
        return url
    return defecto


def cuenta_opcional(request: Request) -> dict | None:
    token = request.cookies.get(config.COOKIE_SESION)
    return sesiones.validar(seguridad.hash_token(token)) if token else None


def cuenta_actual(request: Request) -> dict:
    cuenta = cuenta_opcional(request)
    if not cuenta:
        destino = "/login"
        if request.method == "GET":
            consulta = f"?{request.url.query}" if request.url.query else ""
            destino += "?siguiente=" + quote(request.url.path + consulta, safe="")
        raise redirigir(destino)
    return cuenta


def inicio_de(tipo: str, perfil_id: str | None) -> str:
    if tipo == "empresa":
        return f"/empresa/{perfil_id}"
    if tipo in ("staff", "admin"):
        return "/admin"
    return "/"


def visor(cuenta: dict = Depends(cuenta_actual)) -> dict:
    """Datos de la cuenta autenticada, con la forma que esperan las plantillas."""
    if cuenta["tipo"] == "persona":
        yo = usuarios.resumen(cuenta["perfil_id"])
        if not yo:
            raise HTTPException(500, "La cuenta no tiene un perfil asociado.")
    elif cuenta["tipo"] == "empresa":
        yo = {"id": cuenta["perfil_id"], "nombre": cuenta["perfil_nombre"], "apellido": ""}
    else:
        yo = {"id": cuenta["cuenta_id"], "nombre": cuenta["email"], "apellido": ""}
    yo.update(tipo=cuenta["tipo"], cuenta_id=cuenta["cuenta_id"], csrf_token=cuenta["csrf_token"],
              roles=cuenta["roles"], permisos=cuenta["permisos"], email=cuenta["email"])
    return yo


def usuario_actual(yo: dict = Depends(visor)) -> dict:
    """Solo personas. Las demas cuentas van a su propia pagina de inicio."""
    if yo["tipo"] != "persona":
        raise redirigir(inicio_de(yo["tipo"], yo["id"]))
    return yo


def permiso_requerido(codigo: str):
    """Fabrica de dependencias: exige un permiso del rol de la cuenta (RBAC en el grafo)."""
    def verificar(yo: dict = Depends(visor)) -> dict:
        if codigo not in yo["permisos"]:
            raise HTTPException(403, "No tienes permiso para ver esta página.")
        return yo
    return verificar


async def formulario(request: Request):
    """Cuerpo del formulario (multidict). Starlette lo guarda en cache, asi que se puede
    pedir desde varias dependencias sin leerlo dos veces."""
    return await request.form()


def verificar_csrf(cuenta: dict = Depends(cuenta_actual), f=Depends(formulario)) -> dict:
    """Protege los POST de usuarios con sesion: el token del formulario debe
    coincidir con el que se guardo en el nodo :Sesion."""
    if not seguridad.tokens_iguales(cuenta["csrf_token"], f.get("csrf_token", "")):
        raise HTTPException(403, "El formulario expiró o no es válido. Recarga la página e inténtalo de nuevo.")
    return cuenta


def persona_post(yo: dict = Depends(usuario_actual), _c: dict = Depends(verificar_csrf)) -> dict:
    """Persona con sesion y token CSRF valido (para acciones que modifican datos)."""
    return yo


# ------------------------------------------------ permisos sobre una empresa
def puede_gestionar(yo: dict, empresa_id: str) -> bool:
    """Quien puede publicar y gestionar ofertas de una empresa:
      - la CUENTA de esa empresa (con el permiso 'oferta.publicar' de su rol), o
      - una persona que trabaja AHORA en ella con rol 'rrhh' (propiedad de TRABAJA_EN)."""
    if yo["tipo"] == "empresa":
        return yo["id"] == empresa_id and "oferta.publicar" in yo["permisos"]
    if yo["tipo"] == "persona":
        return bool(yo.get("empresa")) and yo["empresa"]["id"] == empresa_id and yo.get("rol_empresa") == "rrhh"
    return False


def gestor_empresa(empresa_id: str, yo: dict = Depends(visor)) -> dict:
    if not puede_gestionar(yo, empresa_id):
        raise HTTPException(403, "No tienes permiso para gestionar esta empresa.")
    return yo


def gestor_empresa_post(yo: dict = Depends(gestor_empresa), _c: dict = Depends(verificar_csrf)) -> dict:
    return yo


def dueno_empresa(empresa_id: str, yo: dict = Depends(visor)) -> dict:
    """Solo la cuenta propietaria de la empresa (no el personal de RR. HH.)."""
    if yo["tipo"] != "empresa" or yo["id"] != empresa_id:
        raise HTTPException(403, "Solo la cuenta de la empresa puede hacer esto.")
    return yo


def dueno_empresa_post(yo: dict = Depends(dueno_empresa), _c: dict = Depends(verificar_csrf)) -> dict:
    return yo


def gestor_oferta(oferta_id: str, yo: dict = Depends(visor)) -> dict:
    """Resuelve la empresa duena de la oferta y comprueba el permiso sobre ella."""
    empresa_id = ofertas.empresa_de(oferta_id)
    if not empresa_id:
        raise HTTPException(404, "La oferta no existe.")
    if not puede_gestionar(yo, empresa_id):
        raise HTTPException(403, "No tienes permiso para gestionar esta oferta.")
    return {**yo, "empresa_id": empresa_id}


def gestor_oferta_post(yo: dict = Depends(gestor_oferta), _c: dict = Depends(verificar_csrf)) -> dict:
    return yo


def permiso_post(codigo: str):
    """Como permiso_requerido, pero ademas exige el token CSRF (para acciones POST)."""
    chequeo = permiso_requerido(codigo)

    def dependencia(yo: dict = Depends(chequeo), _c: dict = Depends(verificar_csrf)) -> dict:
        return yo
    return dependencia
