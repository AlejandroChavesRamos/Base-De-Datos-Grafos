"""Registro, login y logout."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import config
from app.dependencias import cuenta_opcional, inicio_de, ruta_interna, verificar_csrf
from app.repositories import eventos, sesiones
from app.services import auth, seguridad
from app.templating import templates

router = APIRouter()

MENSAJE_LOGIN = ("Correo o contraseña incorrectos. Tras varios intentos fallidos, "
                 "la cuenta se bloquea temporalmente.")
MENSAJE_CSRF = "El formulario expiró. Inténtalo de nuevo."


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _ua(request: Request) -> str:
    return request.headers.get("user-agent", "")


def _publica(request: Request, plantilla: str, status: int = 200, **datos):
    """Renderiza una pagina publica con su token de formulario (double-submit cookie)."""
    token = request.cookies.get(config.COOKIE_CSRF) or seguridad.nuevo_token()
    resp = templates.TemplateResponse(
        request, plantilla,
        {"yo": None, "csrf_previo": token, "errores": {}, "valores": {}, **datos},
        status_code=status,
    )
    resp.set_cookie(config.COOKIE_CSRF, token, max_age=3600, httponly=True,
                    samesite="lax", secure=config.COOKIE_SECURE, path="/")
    return resp


def _csrf_previo_ok(request: Request, token_form: str) -> bool:
    return seguridad.tokens_iguales(request.cookies.get(config.COOKIE_CSRF, ""), token_form)


def _entrar(request: Request, token: str, destino: str):
    """Responde con la cookie de sesion. Cierra la sesion anterior si la habia."""
    anterior = request.cookies.get(config.COOKIE_SESION)
    if anterior:
        sesiones.revocar(seguridad.hash_token(anterior))
    resp = RedirectResponse(destino, status_code=303)
    resp.set_cookie(config.COOKIE_SESION, token, max_age=config.SESION_HORAS * 3600,
                    httponly=True, samesite="lax", secure=config.COOKIE_SECURE, path="/")
    resp.delete_cookie(config.COOKIE_CSRF, path="/")
    return resp


# ---------------------------------------------------------------- login
@router.get("/login")
def login_form(request: Request, siguiente: str = "/"):
    cuenta = cuenta_opcional(request)
    if cuenta:
        return RedirectResponse(inicio_de(cuenta["tipo"], cuenta["perfil_id"]), status_code=303)
    return _publica(request, "login.html", siguiente=ruta_interna(siguiente))


@router.post("/login")
def login_enviar(request: Request, email: str = Form(""), password: str = Form(""),
                 siguiente: str = Form("/"), csrf_token: str = Form("")):
    siguiente = ruta_interna(siguiente)
    if not _csrf_previo_ok(request, csrf_token):
        return _publica(request, "login.html", 403, error=MENSAJE_CSRF, siguiente=siguiente,
                        valores={"email": email})
    token = auth.iniciar_sesion(email, password, _ip(request), _ua(request))
    if not token:
        return _publica(request, "login.html", 401, error=MENSAJE_LOGIN, siguiente=siguiente,
                        valores={"email": email})
    return _entrar(request, token, siguiente)


# ------------------------------------------------------------- registro
@router.get("/registro")
def registro_elegir(request: Request):
    return _publica(request, "registro.html")


@router.get("/registro/persona")
def registro_persona_form(request: Request):
    return _publica(request, "registro_persona.html")


@router.post("/registro/persona")
def registro_persona_enviar(
    request: Request, nombre: str = Form(""), apellido: str = Form(""), ciudad: str = Form(""),
    titular: str = Form(""), email: str = Form(""), password: str = Form(""),
    password2: str = Form(""), csrf_token: str = Form(""),
):
    valores = {"nombre": nombre, "apellido": apellido, "ciudad": ciudad, "titular": titular, "email": email}
    if not _csrf_previo_ok(request, csrf_token):
        return _publica(request, "registro_persona.html", 403, errores={"general": MENSAJE_CSRF}, valores=valores)
    try:
        r = auth.registrar_persona({**valores, "password": password, "password2": password2}, _ip(request))
    except auth.ErrorFormulario as e:
        return _publica(request, "registro_persona.html", 422, errores=e.errores, valores=valores)
    token = auth.abrir_sesion(r["cuenta_id"], _ip(request), _ua(request))
    return _entrar(request, token, inicio_de("persona", r["perfil_id"]))


@router.get("/registro/empresa")
def registro_empresa_form(request: Request):
    return _publica(request, "registro_empresa.html", sectores=auth.SECTORES, tamanos=auth.TAMANOS)


@router.post("/registro/empresa")
def registro_empresa_enviar(
    request: Request, nombre: str = Form(""), sector: str = Form(""), tamano: str = Form(""),
    ciudad: str = Form(""), descripcion: str = Form(""), sitio_web: str = Form(""),
    email: str = Form(""), password: str = Form(""), password2: str = Form(""),
    csrf_token: str = Form(""),
):
    valores = {"nombre": nombre, "sector": sector, "tamano": tamano, "ciudad": ciudad,
               "descripcion": descripcion, "sitio_web": sitio_web, "email": email}
    extra = {"sectores": auth.SECTORES, "tamanos": auth.TAMANOS, "valores": valores}
    if not _csrf_previo_ok(request, csrf_token):
        return _publica(request, "registro_empresa.html", 403, errores={"general": MENSAJE_CSRF}, **extra)
    try:
        r = auth.registrar_empresa({**valores, "password": password, "password2": password2}, _ip(request))
    except auth.ErrorFormulario as e:
        return _publica(request, "registro_empresa.html", 422, errores=e.errores, **extra)
    token = auth.abrir_sesion(r["cuenta_id"], _ip(request), _ua(request))
    return _entrar(request, token, inicio_de("empresa", r["perfil_id"]))


# --------------------------------------------------------------- logout
def _salir(request: Request):
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(config.COOKIE_SESION, path="/")
    return resp


@router.post("/logout")
def logout(request: Request, cuenta: dict = Depends(verificar_csrf)):
    token = request.cookies.get(config.COOKIE_SESION, "")
    auth.cerrar_sesion(token)
    eventos.registrar(cuenta["cuenta_id"], "logout", _ip(request))
    return _salir(request)


@router.post("/logout-todas")
def logout_todas(request: Request, cuenta: dict = Depends(verificar_csrf)):
    sesiones.revocar_de_cuenta(cuenta["cuenta_id"])
    eventos.registrar(cuenta["cuenta_id"], "logout_todas", _ip(request))
    return _salir(request)
