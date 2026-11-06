"""Panel de staff y admin. El acceso se decide con permisos guardados en el grafo."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.dependencias import permiso_requerido, verificar_csrf
from app.repositories import cuentas, eventos, sesiones
from app.templating import templates

router = APIRouter(prefix="/admin")


@router.get("")
def panel(request: Request, yo: dict = Depends(permiso_requerido("usuario.bloquear"))):
    puede_auditar = "sistema.auditar" in yo["permisos"]
    return templates.TemplateResponse(request, "admin.html", {
        "yo": yo, "ruta_actual": request.url.path,
        "cuentas": cuentas.listar(100),
        "eventos": eventos.recientes(30) if puede_auditar else None,
        "puede_auditar": puede_auditar,
        "puede_gestionar_staff": "staff.gestionar" in yo["permisos"],
        "mensaje": request.query_params.get("ok"),
    })


@router.post("/cuentas/{cuenta_id}/estado")
def cambiar_estado(
    request: Request, cuenta_id: str, activa: str = Form(...),
    yo: dict = Depends(permiso_requerido("usuario.bloquear")),
    _csrf: dict = Depends(verificar_csrf),
):
    objetivo = cuentas.tipo_de(cuenta_id)
    if not objetivo:
        raise HTTPException(404, "La cuenta no existe.")
    if cuenta_id == yo["cuenta_id"]:
        raise HTTPException(400, "No puedes cambiar el estado de tu propia cuenta.")
    # Solo quien tiene 'staff.gestionar' (admin) puede tocar cuentas de staff o admin
    if objetivo["tipo"] in ("staff", "admin") and "staff.gestionar" not in yo["permisos"]:
        raise HTTPException(403, "No tienes permiso para gestionar cuentas internas.")
    nueva = activa == "true"
    cuentas.cambiar_activa(cuenta_id, nueva)
    if not nueva:
        sesiones.revocar_de_cuenta(cuenta_id)  # se expulsa de inmediato
    eventos.registrar(cuenta_id, "cuenta_activada" if nueva else "cuenta_desactivada",
                      request.client.host if request.client else "", f"por {yo['email']}")
    return RedirectResponse("/admin?ok=1", status_code=303)
