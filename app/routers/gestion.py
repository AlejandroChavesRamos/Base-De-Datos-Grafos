"""Gestion de empresa: ofertas, requisitos, postulantes y RR. HH.

Quien puede gestionar una empresa lo decide dependencias.puede_gestionar:
la cuenta de la empresa, o una persona con TRABAJA_EN {rol: 'rrhh'} vigente en ella."""
from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencias import (dueno_empresa, dueno_empresa_post, formulario, gestor_empresa,
                              gestor_empresa_post, gestor_oferta, gestor_oferta_post)
from app.repositories import empresas, ofertas, perfiles
from app.routers.utiles import render, volver
from app.services import validadores
from app.services.auth import SECTORES, TAMANOS

router = APIRouter()


# ============================================================ empresa
@router.get("/empresa/{empresa_id}/gestion")
def panel(request: Request, empresa_id: str, yo: dict = Depends(gestor_empresa)):
    datos = empresas.obtener(empresa_id, yo["id"])
    if not datos:
        raise HTTPException(404, "Esta empresa no existe.")
    return render(request, "empresa_gestion.html", yo, e=datos["empresa"],
                  ofertas=ofertas.gestion_de_empresa(empresa_id),
                  empleados=empresas.empleados(empresa_id),
                  es_dueno=yo["tipo"] == "empresa",
                  puede_asignar="empresa.asignar_rrhh" in yo["permisos"])


def _pagina_editar_empresa(request, yo, empresa_id, status=200, err=None, val=None):
    datos = empresas.obtener(empresa_id, yo["id"])
    if not datos:
        raise HTTPException(404, "Esta empresa no existe.")
    return render(request, "empresa_editar.html", yo, status, e=datos["empresa"],
                  sectores=[(s, s) for s in SECTORES], tamanos=list(TAMANOS.items()), err=err or {}, val=val or datos["empresa"])


@router.get("/empresa/{empresa_id}/editar")
def editar_empresa_form(request: Request, empresa_id: str, yo: dict = Depends(dueno_empresa)):
    return _pagina_editar_empresa(request, yo, empresa_id)


@router.post("/empresa/{empresa_id}/editar")
def editar_empresa(request: Request, empresa_id: str, f=Depends(formulario),
                   yo: dict = Depends(dueno_empresa_post)):
    datos, errores = validadores.empresa(f)
    if errores:
        return _pagina_editar_empresa(request, yo, empresa_id, 422, errores, datos)
    ok = empresas.actualizar(empresa_id, datos)
    return volver(f"/empresa/{empresa_id}/gestion", aviso="empresa_guardada" if ok else None,
                  error=None if ok else "no_se_pudo")


@router.post("/empresa/{empresa_id}/empleados/{uid}/rol")
def cambiar_rol(empresa_id: str, uid: str, f=Depends(formulario),
                yo: dict = Depends(dueno_empresa_post)):
    # Ademas de ser la cuenta duena, el permiso sale del grafo (Rol -> Permiso)
    if "empresa.asignar_rrhh" not in yo["permisos"]:
        raise HTTPException(403, "No tienes permiso para asignar RR. HH.")
    rol = f.get("rol")
    if rol not in ("rrhh", "trabajador"):
        raise HTTPException(400, "Rol no válido.")
    ok = empresas.cambiar_rol(empresa_id, uid, rol)
    return volver(f"/empresa/{empresa_id}/gestion", aviso="rol_actualizado" if ok else None,
                  error=None if ok else "no_se_pudo", ancla="equipo")


# ============================================================== ofertas
def _pagina_oferta(request, yo, status=200, err=None, val=None, nueva=True, empresa_id=None, oferta_id=None):
    return render(request, "oferta_form.html", yo, status, nueva=nueva, empresa_id=empresa_id,
                  oferta_id=oferta_id, modalidades=list(validadores.MODALIDADES.items()), err=err or {}, val=val or {})


@router.get("/empresa/{empresa_id}/ofertas/nueva")
def nueva_form(request: Request, empresa_id: str, yo: dict = Depends(gestor_empresa)):
    return _pagina_oferta(request, yo, empresa_id=empresa_id)


@router.post("/empresa/{empresa_id}/ofertas/nueva")
def nueva(request: Request, empresa_id: str, f=Depends(formulario),
          yo: dict = Depends(gestor_empresa_post)):
    datos, errores = validadores.oferta(f)
    if errores:
        return _pagina_oferta(request, yo, 422, errores, f, empresa_id=empresa_id)
    # 'publicada_por' guarda QUIEN la creo (id de la persona de RR. HH. o de la empresa)
    oid = ofertas.crear(empresa_id, yo["id"], datos)
    if not oid:
        raise HTTPException(404, "Esta empresa no existe.")
    return volver(f"/ofertas/{oid}/gestion", aviso="oferta_creada")


@router.get("/ofertas/{oferta_id}/gestion")
def gestion_oferta(request: Request, oferta_id: str, yo: dict = Depends(gestor_oferta)):
    datos = ofertas.obtener_gestion(oferta_id)
    return render(request, "oferta_gestion.html", yo, o=datos["oferta"], e=datos["empresa"],
                  vencida=datos.get("vencida"),
                  requisitos=datos["requisitos"], catalogo=perfiles.catalogo_habilidades(),
                  postulantes=ofertas.postulantes(oferta_id),
                  candidatos=ofertas.candidatos_sugeridos(oferta_id, 5),
                  estados=validadores.ESTADOS_POSTULACION, err={})


@router.get("/ofertas/{oferta_id}/editar")
def editar_form(request: Request, oferta_id: str, yo: dict = Depends(gestor_oferta)):
    o = ofertas.obtener_gestion(oferta_id)["oferta"]
    val = {**o, "fecha_cierre": o["fecha_cierre"].iso_format() if hasattr(o["fecha_cierre"], "iso_format")
           else str(o["fecha_cierre"])}
    return _pagina_oferta(request, yo, val=val, nueva=False, oferta_id=oferta_id)


@router.post("/ofertas/{oferta_id}/editar")
def editar(request: Request, oferta_id: str, f=Depends(formulario),
           yo: dict = Depends(gestor_oferta_post)):
    datos, errores = validadores.oferta(f)
    if errores:
        return _pagina_oferta(request, yo, 422, errores, f, nueva=False, oferta_id=oferta_id)
    ok = ofertas.actualizar(oferta_id, datos)
    return volver(f"/ofertas/{oferta_id}/gestion", aviso="oferta_actualizada" if ok else None,
                  error=None if ok else "no_se_pudo")


@router.post("/ofertas/{oferta_id}/requisitos")
def agregar_requisito(request: Request, oferta_id: str, f=Depends(formulario),
                      yo: dict = Depends(gestor_oferta_post)):
    datos, errores = validadores.requisito(f)
    if errores:
        return volver(f"/ofertas/{oferta_id}/gestion", error="dato_invalido", ancla="requisitos")
    ok = ofertas.guardar_requisito(oferta_id, datos["hid"], datos["nivel"], datos["obligatoria"])
    return volver(f"/ofertas/{oferta_id}/gestion", aviso="requisito_guardado" if ok else None,
                  error=None if ok else "no_se_pudo", ancla="requisitos")


@router.post("/ofertas/{oferta_id}/requisitos/{hid}/quitar")
def quitar_requisito(oferta_id: str, hid: str, yo: dict = Depends(gestor_oferta_post)):
    ok = ofertas.quitar_requisito(oferta_id, hid)
    return volver(f"/ofertas/{oferta_id}/gestion", aviso="requisito_quitado" if ok else None,
                  error=None if ok else "requisito_necesario", ancla="requisitos")


@router.post("/ofertas/{oferta_id}/publicar")
def publicar(oferta_id: str, yo: dict = Depends(gestor_oferta_post)):
    notificados = ofertas.publicar(oferta_id)
    if notificados is None:
        return volver(f"/ofertas/{oferta_id}/gestion", error="no_publicable")
    return volver(f"/ofertas/{oferta_id}/gestion", aviso="oferta_publicada", n=notificados)


@router.post("/ofertas/{oferta_id}/cerrar")
def cerrar(oferta_id: str, yo: dict = Depends(gestor_oferta_post)):
    ok = ofertas.cambiar_estado(oferta_id, ["abierta"], "cerrada")
    return volver(f"/ofertas/{oferta_id}/gestion", aviso="oferta_cerrada" if ok else None,
                  error=None if ok else "no_se_pudo")


@router.post("/ofertas/{oferta_id}/reabrir")
def reabrir(oferta_id: str, yo: dict = Depends(gestor_oferta_post)):
    ok = ofertas.reabrir(oferta_id)
    return volver(f"/ofertas/{oferta_id}/gestion", aviso="oferta_reabierta" if ok else None,
                  error=None if ok else "oferta_vencida")


@router.post("/ofertas/{oferta_id}/postulaciones/{uid}/estado")
def estado_postulacion(oferta_id: str, uid: str, f=Depends(formulario),
                       yo: dict = Depends(gestor_oferta_post)):
    estado = f.get("estado")
    if estado not in validadores.ESTADOS_POSTULACION:
        raise HTTPException(400, "Estado no válido.")
    ok = ofertas.cambiar_estado_postulacion(oferta_id, uid, estado, validadores.ESTADOS_POSTULACION[estado])
    return volver(f"/ofertas/{oferta_id}/gestion", aviso="estado_actualizado" if ok else None,
                  error=None if ok else "no_se_pudo", ancla="postulantes")
