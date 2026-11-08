"""Acciones de una persona: red de contactos, perfil, habilidades, experiencia,
proyectos, postulaciones, notificaciones y cuenta. Todo POST exige sesion y token CSRF."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import config
from app.dependencias import formulario, persona_post, ruta_interna, usuario_actual, verificar_csrf, visor
from app.repositories import (conexiones, cuentas, eventos, notificaciones, ofertas, perfiles,
                              usuarios)
from app.routers.utiles import render, volver
from app.services import auth, validadores
from app.templating import templates

router = APIRouter()


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _resultado(ok: bool, f, defecto: str, aviso: str, ancla: str = ""):
    destino = ruta_interna(f.get("volver"), defecto)
    return volver(destino, aviso=aviso if ok else None, error=None if ok else "no_se_pudo", ancla=ancla)


# ============================================================ conexiones
@router.post("/conexiones/solicitar/{destino}")
def solicitar(destino: str, f=Depends(formulario), yo: dict = Depends(persona_post)):
    ok = conexiones.solicitar(yo["id"], destino, validadores.texto(f.get("mensaje"), 300))
    return _resultado(ok, f, f"/perfil/{destino}", "conexion_enviada")


@router.post("/conexiones/aceptar/{origen}")
def aceptar(origen: str, f=Depends(formulario), yo: dict = Depends(persona_post)):
    return _resultado(conexiones.aceptar(yo["id"], origen), f, "/red", "conexion_aceptada")


@router.post("/conexiones/ignorar/{origen}")
def ignorar(origen: str, f=Depends(formulario), yo: dict = Depends(persona_post)):
    return _resultado(conexiones.retirar_solicitud(origen, yo["id"]), f, "/red", "invitacion_ignorada")


@router.post("/conexiones/retirar/{destino}")
def retirar(destino: str, f=Depends(formulario), yo: dict = Depends(persona_post)):
    return _resultado(conexiones.retirar_solicitud(yo["id"], destino), f, "/red", "invitacion_retirada")


@router.post("/conexiones/eliminar/{otro}")
def eliminar_contacto(otro: str, f=Depends(formulario), yo: dict = Depends(persona_post)):
    return _resultado(conexiones.eliminar(yo["id"], otro), f, "/red", "contacto_eliminado")


# ================================================================ perfil
def _pagina_editar(request: Request, yo: dict, status: int = 200, err: dict | None = None,
                   val: dict | None = None):
    p = usuarios.perfil_completo(yo["id"])
    return render(request, "perfil_editar.html", yo, status, p=p,
                  catalogo=perfiles.catalogo_habilidades(), empresas=[(e["id"], e["nombre"]) for e in perfiles.lista_empresas()],
                  err=err or {}, val=val or {})


@router.get("/perfil/editar")
def editar_form(request: Request, yo: dict = Depends(usuario_actual)):
    return _pagina_editar(request, yo)


@router.post("/perfil/editar")
def editar_enviar(request: Request, f=Depends(formulario), yo: dict = Depends(persona_post)):
    datos, errores = validadores.perfil(f)
    if errores:
        return _pagina_editar(request, yo, 422, {"perfil": errores}, {"perfil": datos})
    ok = perfiles.actualizar(yo["id"], datos)
    return volver("/perfil/editar", aviso="perfil_guardado" if ok else None,
                  error=None if ok else "no_se_pudo")


@router.post("/perfil/habilidades")
def guardar_habilidad(request: Request, f=Depends(formulario), yo: dict = Depends(persona_post)):
    datos, errores = validadores.habilidad(f)
    if errores:
        return _pagina_editar(request, yo, 422, {"habilidad": errores}, {"habilidad": f})
    ok = perfiles.guardar_habilidad(yo["id"], datos["hid"], datos["nivel"], datos["anios"])
    return volver("/perfil/editar", aviso="habilidad_guardada" if ok else None,
                  error=None if ok else "no_se_pudo", ancla="habilidades")


@router.post("/perfil/habilidades/{hid}/quitar")
def quitar_habilidad(hid: str, yo: dict = Depends(persona_post)):
    ok = perfiles.quitar_habilidad(yo["id"], hid)
    return volver("/perfil/editar", aviso="habilidad_quitada" if ok else None,
                  error=None if ok else "no_se_pudo", ancla="habilidades")


@router.post("/perfil/experiencia")
def agregar_experiencia(request: Request, f=Depends(formulario), yo: dict = Depends(persona_post)):
    datos, errores = validadores.experiencia(f)
    if errores:
        return _pagina_editar(request, yo, 422, {"experiencia": errores}, {"experiencia": f})
    ok = perfiles.agregar_experiencia(yo["id"], datos)
    return volver("/perfil/editar", aviso="experiencia_agregada" if ok else None,
                  error=None if ok else "experiencia_repetida", ancla="experiencia")


@router.post("/perfil/experiencia/quitar")
def quitar_experiencia(f=Depends(formulario), yo: dict = Depends(persona_post)):
    desde = validadores.fecha(f.get("desde"))
    ok = bool(desde) and perfiles.quitar_experiencia(yo["id"], validadores.texto(f.get("empresa_id"), 64),
                                                     desde.isoformat())
    return volver("/perfil/editar", aviso="experiencia_quitada" if ok else None,
                  error=None if ok else "no_se_pudo", ancla="experiencia")


# ============================================================= proyectos
def _pagina_proyectos(request: Request, yo: dict, status: int = 200, err: dict | None = None,
                      val=None):
    return render(request, "proyectos.html", yo, status,
                  proyectos=perfiles.listar_proyectos(yo["id"]),
                  relacionados=perfiles.proyectos_relacionados(yo["id"], 4),
                  afines=perfiles.proyectos_afines(6),
                  catalogo=perfiles.catalogo_habilidades(), err=err or {}, val=val or {})


@router.get("/proyectos")
def proyectos(request: Request, yo: dict = Depends(usuario_actual)):
    return _pagina_proyectos(request, yo)


@router.post("/proyectos")
def crear_proyecto(request: Request, f=Depends(formulario), yo: dict = Depends(persona_post)):
    datos, techs, errores = validadores.proyecto(f)
    if errores:
        return _pagina_proyectos(request, yo, 422, errores, {"f": f, "techs": techs})
    ok = perfiles.crear_proyecto(yo["id"], datos, techs)
    return volver("/proyectos", aviso="proyecto_creado" if ok else None, error=None if ok else "no_se_pudo")


@router.post("/proyectos/{pid}/unirse")
def unirse(pid: str, f=Depends(formulario), yo: dict = Depends(persona_post)):
    rol = validadores.texto(f.get("rol"), 60) or "Colaborador"
    return _resultado(perfiles.unirse_proyecto(yo["id"], pid, rol), f, "/proyectos", "proyecto_unido")


@router.post("/proyectos/{pid}/salir")
def salir(pid: str, f=Depends(formulario), yo: dict = Depends(persona_post)):
    return _resultado(perfiles.salir_proyecto(yo["id"], pid), f, "/proyectos", "proyecto_salido")


# ========================================================== postulaciones
@router.post("/empleos/{oid}/postular")
def postular(oid: str, yo: dict = Depends(persona_post)):
    titulo = ofertas.postular(yo["id"], oid)
    if titulo:
        return volver(f"/empleos?oferta={oid}", aviso="postulado")
    return volver(f"/empleos?oferta={oid}", error="no_postulable")


@router.post("/empleos/{oid}/retirar")
def retirar_postulacion(oid: str, yo: dict = Depends(persona_post)):
    ok = ofertas.retirar_postulacion(yo["id"], oid)
    return volver(f"/empleos?oferta={oid}", aviso="postulacion_retirada" if ok else None,
                  error=None if ok else "no_se_pudo")


# ========================================================= notificaciones
@router.post("/notificaciones/leer-todas")
def leer_todas(yo: dict = Depends(persona_post)):
    notificaciones.marcar_todas(yo["id"])
    return volver("/notificaciones", aviso="notificaciones_leidas")


@router.post("/notificaciones/{nid}/leer")
def leer_una(nid: str, yo: dict = Depends(persona_post)):
    enlace = notificaciones.marcar_leida(nid, yo["id"])
    return RedirectResponse(ruta_interna(enlace, "/notificaciones"), status_code=303)


# ================================================================ cuenta
def _pagina_cuenta(request: Request, yo: dict, status: int = 200, err: dict | None = None):
    return render(request, "cuenta.html", yo, status, err=err or {})


@router.get("/cuenta")
def cuenta(request: Request, yo: dict = Depends(visor)):
    return _pagina_cuenta(request, yo)


@router.post("/cuenta/password")
def cambiar_password(request: Request, f=Depends(formulario), yo: dict = Depends(visor),
                     cuenta: dict = Depends(verificar_csrf)):
    errores = auth.cambiar_contrasena(
        cuenta["cuenta_id"], cuenta["email"], f.get("actual", ""), f.get("nueva", ""),
        f.get("nueva2", ""), request.cookies.get(config.COOKIE_SESION, ""), _ip(request))
    if errores:
        return _pagina_cuenta(request, yo, 422, {"password": errores})
    return volver("/cuenta", aviso="password_cambiada")


@router.post("/cuenta/eliminar")
def eliminar_cuenta(request: Request, f=Depends(formulario), yo: dict = Depends(visor),
                    cuenta: dict = Depends(verificar_csrf)):
    if yo["tipo"] not in ("persona", "empresa"):
        raise HTTPException(403, "Las cuentas internas las elimina un administrador.")
    errores = {}
    if f.get("confirmar") != "on":
        errores["confirmar"] = "Marca la casilla para confirmar."
    elif not auth.confirmar_contrasena(cuenta["cuenta_id"], f.get("password", ""), _ip(request)):
        errores["password"] = "La contraseña no es correcta."
    if errores:
        return _pagina_cuenta(request, yo, 422, {"eliminar": errores})
    eventos.registrar(cuenta["cuenta_id"], "cuenta_eliminada", _ip(request), yo["tipo"])
    if yo["tipo"] == "persona":
        cuentas.eliminar_persona(cuenta["cuenta_id"], yo["id"])
    else:
        cuentas.eliminar_empresa(cuenta["cuenta_id"], yo["id"])
    resp = RedirectResponse("/login?aviso=cuenta_eliminada", status_code=303)
    resp.delete_cookie(config.COOKIE_SESION, path="/")
    return resp
