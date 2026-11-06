"""Funciones comunes de las rutas."""
from fastapi import Request
from fastapi.responses import RedirectResponse

from app.templating import templates


def render(request: Request, plantilla: str, yo: dict, status: int = 200, **datos):
    contexto = {"yo": yo, "ruta_actual": request.url.path, **datos}
    return templates.TemplateResponse(request, plantilla, contexto, status_code=status)


def volver(url: str, aviso: str | None = None, error: str | None = None,
           ancla: str = "", **extra):
    """Redireccion 303 (tras un POST) con un aviso o error. Solo se envian CODIGOS por la URL;
    el texto vive en templating.AVISOS, asi nadie puede inyectar mensajes."""
    params = []
    if aviso:
        params.append(f"aviso={aviso}")
    elif error:
        params.append(f"error={error}")
    params += [f"{k}={v}" for k, v in extra.items()]
    if params:
        url += ("&" if "?" in url else "?") + "&".join(params)
    return RedirectResponse(url + (f"#{ancla}" if ancla else ""), status_code=303)
