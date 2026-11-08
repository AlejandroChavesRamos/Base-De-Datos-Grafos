"""Panel de staff y admin. El acceso se decide con permisos guardados en el grafo."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from neo4j.exceptions import ConstraintError

from app.dependencias import formulario, permiso_post, permiso_requerido, verificar_csrf
from app.repositories import catalogo, cuentas, empresas, eventos, moderacion, sesiones
from app.routers.utiles import render, volver
from app.services import auth, seguridad, validadores
from app.services.auth import SECTORES, TAMANOS
from app.templating import templates

router = APIRouter(prefix="/admin")


@router.get("")
def panel(request: Request, q: str = "", yo: dict = Depends(permiso_requerido("usuario.bloquear"))):
    puede_auditar = "sistema.auditar" in yo["permisos"]
    texto = " ".join(q.split())
    return templates.TemplateResponse(request, "admin.html", {
        "yo": yo, "ruta_actual": request.url.path,
        "cuentas": cuentas.listar_filtrado(100, texto) if texto else cuentas.listar(100),
        "q_admin": texto,
        "puede_crear": "usuario.crear" in yo["permisos"],
        "puede_eliminar": "usuario.eliminar" in yo["permisos"],
        "puede_editar": "usuario.editar" in yo["permisos"],
        "puede_privilegios": "staff.gestionar" in yo["permisos"],
        "puede_catalogo": "catalogo.gestionar" in yo["permisos"],
        "puede_moderar": "contenido.moderar" in yo["permisos"],
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


# =====================================================================
#  Crear y eliminar cuentas, catalogo de habilidades y moderacion.
#  Cada pagina y cada accion exige un PERMISO del grafo (Cuenta -> Rol -> Permiso):
#
#    usuario.crear / usuario.eliminar   crear y eliminar cuentas        (admin)
#    staff.gestionar                    tocar cuentas de staff / admin  (admin)
#    catalogo.gestionar                 crear / eliminar habilidades    (staff, admin)
#    contenido.moderar                  eliminar ofertas y proyectos    (staff, admin)
# =====================================================================
def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _auditar(yo: dict, request: Request, tipo: str, detalle: str = ""):
    """El evento queda ligado a QUIEN hizo la accion."""
    eventos.registrar(yo["cuenta_id"], tipo, _ip(request), detalle)


# ------------------------------------------------------------ crear cuentas
def _tipos_permitidos(yo: dict) -> list[str]:
    tipos = ["persona", "empresa"]
    if "staff.gestionar" in yo["permisos"]:
        tipos += ["staff", "admin"]
    return tipos


def _pagina_nueva(request, yo, status=200, tipo=None, errores=None, valores=None):
    return render(request, "admin_cuenta_nueva.html", yo, status, tipo=tipo, tipos=_tipos_permitidos(yo),
                  sectores=[(s, s) for s in SECTORES], tamanos=list(TAMANOS.items()),
                  errores=errores or {}, valores=valores or {})


@router.get("/cuentas/nueva")
def nueva_form(request: Request, tipo: str | None = None,
               yo: dict = Depends(permiso_requerido("usuario.crear"))):
    return _pagina_nueva(request, yo, tipo=tipo if tipo in _tipos_permitidos(yo) else None)


@router.post("/cuentas/nueva")
def nueva(request: Request, f=Depends(formulario), yo: dict = Depends(permiso_post("usuario.crear"))):
    tipo = f.get("tipo", "")
    if tipo not in _tipos_permitidos(yo):
        raise HTTPException(403, "No puedes crear ese tipo de cuenta.")
    campos = {"persona": ["nombre", "apellido", "ciudad", "titular", "email", "password", "password2"],
              "empresa": ["nombre", "sector", "tamano", "ciudad", "descripcion", "sitio_web", "email", "password", "password2"],
              "staff": ["email", "password", "password2"], "admin": ["email", "password", "password2"]}[tipo]
    datos = {k: f.get(k, "") for k in campos}
    valores = {k: v for k, v in datos.items() if not k.startswith("password")}
    try:
        if tipo == "persona":
            auth.registrar_persona(datos, _ip(request))
        elif tipo == "empresa":
            auth.registrar_empresa(datos, _ip(request))
        else:
            auth.crear_cuenta_interna(datos, tipo)
    except auth.ErrorFormulario as e:
        return _pagina_nueva(request, yo, 422, tipo, e.errores, valores)
    _auditar(yo, request, "cuenta_creada_admin", tipo)
    return volver("/admin", aviso="cuenta_creada")


# --------------------------------------------------------- eliminar cuentas
def _objetivo_eliminable(yo: dict, cuenta_id: str) -> dict:
    """Reglas para eliminar una cuenta; devuelve su detalle o lanza el error que corresponda."""
    objetivo = cuentas.detalle_borrado(cuenta_id)
    if not objetivo:
        raise HTTPException(404, "La cuenta no existe.")
    if cuenta_id == yo["cuenta_id"]:
        raise HTTPException(400, "No puedes eliminar tu propia cuenta desde el panel.")
    if objetivo["tipo"] in ("staff", "admin") and "staff.gestionar" not in yo["permisos"]:
        raise HTTPException(403, "No tienes permiso para eliminar cuentas internas.")
    return objetivo


@router.get("/cuentas/{cuenta_id}/eliminar")
def eliminar_form(request: Request, cuenta_id: str, yo: dict = Depends(permiso_requerido("usuario.eliminar"))):
    return render(request, "admin_cuenta_eliminar.html", yo, c=_objetivo_eliminable(yo, cuenta_id), errores={})


@router.post("/cuentas/{cuenta_id}/eliminar")
def eliminar(request: Request, cuenta_id: str, f=Depends(formulario),
             yo: dict = Depends(permiso_post("usuario.eliminar"))):
    objetivo = _objetivo_eliminable(yo, cuenta_id)
    errores = {}
    if f.get("confirmar") != "on":
        errores["confirmar"] = "Marca la casilla para confirmar."
    elif not auth.confirmar_contrasena(yo["cuenta_id"], f.get("password", ""), _ip(request)):
        errores["password"] = "Tu contraseña no es correcta."  # se pide la del ADMIN, no la de la cuenta borrada
    if errores:
        return render(request, "admin_cuenta_eliminar.html", yo, 422, c=objetivo, errores=errores)
    if objetivo["tipo"] == "persona":
        cuentas.eliminar_persona(cuenta_id, objetivo["perfil_id"])
    elif objetivo["tipo"] == "empresa":
        cuentas.eliminar_empresa(cuenta_id, objetivo["perfil_id"])
    else:
        cuentas.eliminar_interna(cuenta_id)
    _auditar(yo, request, "cuenta_eliminada_admin", objetivo["tipo"])
    return volver("/admin", aviso="cuenta_eliminada_admin")


# ------------------------------------------------- catalogo de habilidades
def _pagina_habilidades(request, yo, status=200, errores=None, valores=None):
    return render(request, "admin_habilidades.html", yo, status, habilidades=catalogo.listar(),
                  categorias=[(c, c.capitalize()) for c in validadores.CATEGORIAS],
                  errores=errores or {}, valores=valores or {})


@router.get("/habilidades")
def habilidades(request: Request, yo: dict = Depends(permiso_requerido("catalogo.gestionar"))):
    return _pagina_habilidades(request, yo)


@router.post("/habilidades")
def crear_habilidad(request: Request, f=Depends(formulario), yo: dict = Depends(permiso_post("catalogo.gestionar"))):
    datos, errores = validadores.habilidad_catalogo(f)
    if not errores and not catalogo.crear(datos["nombre"], datos["categoria"]):
        errores["nombre"] = "Ya existe una habilidad con ese nombre."
    if errores:
        return _pagina_habilidades(request, yo, 422, errores, datos)
    _auditar(yo, request, "habilidad_creada", datos["nombre"])
    return volver("/admin/habilidades", aviso="habilidad_creada")


@router.get("/habilidades/{hid}/eliminar")
def eliminar_habilidad_form(request: Request, hid: str, yo: dict = Depends(permiso_requerido("catalogo.gestionar"))):
    h = catalogo.obtener(hid)
    if not h:
        raise HTTPException(404, "La habilidad no existe.")
    return render(request, "admin_habilidad_eliminar.html", yo, h=h, errores={})


@router.post("/habilidades/{hid}/eliminar")
def eliminar_habilidad(request: Request, hid: str, f=Depends(formulario),
                       yo: dict = Depends(permiso_post("catalogo.gestionar"))):
    h = catalogo.obtener(hid)
    if not h:
        raise HTTPException(404, "La habilidad no existe.")
    if f.get("confirmar") != "on":
        return render(request, "admin_habilidad_eliminar.html", yo, 422, h=h,
                      errores={"confirmar": "Marca la casilla para confirmar."})
    catalogo.eliminar(hid)
    _auditar(yo, request, "habilidad_eliminada", h["habilidad"]["nombre"])
    return volver("/admin/habilidades", aviso="habilidad_eliminada")


# ----------------------------------------------------------------- moderacion
@router.get("/contenido")
def contenido(request: Request, yo: dict = Depends(permiso_requerido("contenido.moderar"))):
    return render(request, "admin_contenido.html", yo, ofertas=moderacion.ofertas(), proyectos=moderacion.proyectos())


@router.post("/ofertas/{oid}/eliminar")
def eliminar_oferta(request: Request, oid: str, yo: dict = Depends(permiso_post("contenido.moderar"))):
    titulo = moderacion.eliminar_oferta(oid)
    if titulo is None:
        raise HTTPException(404, "La oferta no existe.")
    _auditar(yo, request, "oferta_eliminada_moderacion", titulo)
    return volver("/admin/contenido", aviso="oferta_moderada")


@router.post("/proyectos/{pid}/eliminar")
def eliminar_proyecto(request: Request, pid: str, yo: dict = Depends(permiso_post("contenido.moderar"))):
    nombre = moderacion.eliminar_proyecto(pid)
    if nombre is None:
        raise HTTPException(404, "El proyecto no existe.")
    _auditar(yo, request, "proyecto_eliminado_moderacion", nombre)
    return volver("/admin/contenido", aviso="proyecto_eliminado")


# ------------------------------------------------------ modificar una cuenta
def _objetivo_modificable(yo: dict, cuenta_id: str) -> dict:
    """Cuenta que este administrador puede modificar (datos o privilegios), o el error que corresponda."""
    objetivo = cuentas.para_editar(cuenta_id)
    if not objetivo:
        raise HTTPException(404, "La cuenta no existe.")
    if cuenta_id == yo["cuenta_id"]:
        raise HTTPException(400, "No puedes modificar tu propia cuenta desde el panel.")
    if objetivo["tipo"] in ("staff", "admin") and "staff.gestionar" not in yo["permisos"]:
        raise HTTPException(403, "No tienes permiso para modificar cuentas internas.")
    return objetivo


def _pagina_editar(request, yo, objetivo, status=200, errores=None, valores=None):
    perfil = objetivo.get("perfil") or {}
    base = {"email": objetivo["email"], **{k: perfil.get(k, "") for k in ("nombre", "apellido", "titular", "ciudad", "sector", "tamano", "descripcion", "sitio_web")}}
    return render(request, "admin_cuenta_editar.html", yo, status, c=objetivo, errores=errores or {},
                  valores={**base, **(valores or {})}, sectores=[(s, s) for s in SECTORES], tamanos=list(TAMANOS.items()))


@router.get("/cuentas/{cuenta_id}/editar")
def editar_form(request: Request, cuenta_id: str, yo: dict = Depends(permiso_requerido("usuario.editar"))):
    return _pagina_editar(request, yo, _objetivo_modificable(yo, cuenta_id))


@router.post("/cuentas/{cuenta_id}/editar")
def editar(request: Request, cuenta_id: str, f=Depends(formulario), yo: dict = Depends(permiso_post("usuario.editar"))):
    objetivo = _objetivo_modificable(yo, cuenta_id)
    email = seguridad.normalizar_email(f.get("email"))
    errores, perfil_nuevo = {}, None
    if not seguridad.email_valido(email):
        errores["email"] = "Escribe un correo válido."
    if objetivo["tipo"] == "persona":
        perfil_nuevo = {"nombre": validadores.texto(f.get("nombre"), 60), "apellido": validadores.texto(f.get("apellido"), 60),
                        "titular": validadores.texto(f.get("titular"), 120), "ciudad": validadores.texto(f.get("ciudad"), 60)}
        for campo, mensaje in (("nombre", "Escribe el nombre."), ("apellido", "Escribe el apellido."), ("ciudad", "Escribe la ciudad.")):
            if not perfil_nuevo[campo]:
                errores[campo] = mensaje
    elif objetivo["tipo"] == "empresa":
        perfil_nuevo, e = validadores.empresa(f)
        errores.update(e)
    nueva = f.get("nueva_password", "")
    if nueva:
        problemas = seguridad.errores_contrasena(nueva, email)
        if problemas:
            errores["nueva_password"] = " ".join(problemas)
    valores = {k: f.get(k, "") for k in ("email", "nombre", "apellido", "titular", "ciudad", "sector", "tamano", "descripcion", "sitio_web")}
    if errores:
        return _pagina_editar(request, yo, objetivo, 422, errores, valores)
    # La modificacion de una cuenta ajena exige la contrasena del administrador (como eliminarla)
    if not auth.confirmar_contrasena(yo["cuenta_id"], f.get("password_admin", ""), _ip(request)):
        return _pagina_editar(request, yo, objetivo, 422, {"password_admin": "Tu contraseña no es correcta."}, valores)

    cambios = []
    if email != objetivo["email"]:
        try:
            cuentas.actualizar_email(cuenta_id, email)   # primero lo que puede fallar (correo repetido)
        except ConstraintError:
            return _pagina_editar(request, yo, objetivo, 422, {"email": "Este correo ya está registrado."}, valores)
        cambios.append("correo")
    actual = objetivo.get("perfil") or {}
    if objetivo["tipo"] == "persona" and any(perfil_nuevo[k] != (actual.get(k) or "") for k in perfil_nuevo):
        cuentas.actualizar_persona_basico(objetivo["perfil_id"], perfil_nuevo)
        cambios.append("datos del perfil")
    elif objetivo["tipo"] == "empresa" and any(perfil_nuevo[k] != (actual.get(k) or "") for k in perfil_nuevo):
        empresas.actualizar(objetivo["perfil_id"], perfil_nuevo)
        cambios.append("datos de la empresa")
    if nueva:
        cuentas.actualizar_hash(cuenta_id, seguridad.hashear(nueva))
        cuentas.reiniciar_intentos(cuenta_id)            # tambien la desbloquea
        sesiones.revocar_de_cuenta(cuenta_id)            # y se cierran sus sesiones abiertas
        cambios.append("contraseña restablecida")
    _auditar(yo, request, "cuenta_modificada_admin", f"{objetivo['tipo']}: {', '.join(cambios) or 'sin cambios'}")
    return volver("/admin", aviso="cuenta_modificada")


# --------------------------------------------- privilegios de administrador
def _pagina_privilegios(request, yo, objetivo, status=200, errores=None):
    return render(request, "admin_cuenta_privilegios.html", yo, status, c=objetivo, errores=errores or {},
                  permisos_admin=cuentas.permisos_del_rol("admin"))


def _objetivo_con_privilegios(yo: dict, cuenta_id: str) -> dict:
    objetivo = _objetivo_modificable(yo, cuenta_id)
    if objetivo["tipo"] == "admin":
        raise HTTPException(400, "Las cuentas de tipo administrador ya tienen todos los privilegios.")
    return objetivo


@router.get("/cuentas/{cuenta_id}/privilegios")
def privilegios_form(request: Request, cuenta_id: str, yo: dict = Depends(permiso_requerido("staff.gestionar"))):
    return _pagina_privilegios(request, yo, _objetivo_con_privilegios(yo, cuenta_id))


@router.post("/cuentas/{cuenta_id}/privilegios")
def privilegios(request: Request, cuenta_id: str, f=Depends(formulario), yo: dict = Depends(permiso_post("staff.gestionar"))):
    objetivo = _objetivo_con_privilegios(yo, cuenta_id)
    errores = {}
    if f.get("confirmar") != "on":
        errores["confirmar"] = "Marca la casilla para confirmar."
    elif not auth.confirmar_contrasena(yo["cuenta_id"], f.get("password", ""), _ip(request)):
        errores["password"] = "Tu contraseña no es correcta."
    if errores:
        return _pagina_privilegios(request, yo, objetivo, 422, errores)
    if objetivo["rol_admin"]:
        cuentas.quitar_admin(cuenta_id)
        _auditar(yo, request, "privilegios_retirados", objetivo["tipo"])
        return volver("/admin", aviso="privilegios_retirados")
    cuentas.otorgar_admin(cuenta_id)
    _auditar(yo, request, "privilegios_otorgados", objetivo["tipo"])
    return volver("/admin", aviso="privilegios_otorgados")
