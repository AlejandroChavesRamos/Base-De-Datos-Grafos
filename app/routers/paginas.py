"""Rutas que devuelven paginas HTML (Jinja2)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.dependencias import cuenta_opcional, puede_gestionar, usuario_actual, visor
from app.repositories import (busqueda, empresas, notificaciones, ofertas,
                              red, usuarios)
from app.routers.utiles import render
from app.templating import templates

router = APIRouter()


def _visible(datos: dict | None, yo: dict) -> bool:
    """Lo de una cuenta desactivada solo lo ve el personal interno."""
    return bool(datos) and (datos.get("activa", True) or yo["tipo"] in ("admin", "staff"))


@router.get("/")
def inicio(request: Request):
    cuenta = cuenta_opcional(request)
    if not cuenta:
        return templates.TemplateResponse(request, "bienvenida.html", {})
    yo = usuario_actual(visor(cuenta))
    return render(
        request, "inicio.html", yo,
        empleos=ofertas.recomendadas(yo["id"], 3),
        actividad=red.actividad(yo["id"], 8),
        sugerencias=red.sugerencias(yo["id"], 4),
        demanda=ofertas.demanda_habilidades(5),
    )


@router.get("/yo")
def mi_perfil(yo: dict = Depends(usuario_actual)):
    return RedirectResponse(f"/perfil/{yo['id']}")


@router.get("/perfil/{usuario_id}")
def perfil(request: Request, usuario_id: str, yo: dict = Depends(visor)):
    datos = usuarios.perfil_completo(usuario_id)
    if not _visible(datos, yo):
        raise HTTPException(404, "Este perfil no existe.")
    # Empresas y staff pueden ver perfiles (p. ej. candidatos), pero sin acciones de red
    es_persona = yo["tipo"] == "persona"
    es_propio = es_persona and usuario_id == yo["id"]
    otra_persona = es_persona and not es_propio
    return render(
        request, "perfil.html", yo,
        p=datos, es_propio=es_propio,
        relacion=usuarios.estado_relacion(yo["id"], usuario_id) if otra_persona else "ninguna",
        ruta=usuarios.ruta(yo["id"], usuario_id) if otra_persona else None,
        en_comun=usuarios.contactos_en_comun(yo["id"], usuario_id) if otra_persona else [],
        similares=usuarios.similares(usuario_id, 4),
    )


@router.get("/empresa/{empresa_id}")
def empresa(request: Request, empresa_id: str, yo: dict = Depends(visor)):
    datos = empresas.obtener(empresa_id, yo["id"])
    if not _visible(datos, yo):
        raise HTTPException(404, "Esta empresa no existe.")
    return render(request, "empresa.html", yo, e=datos, gestiona=puede_gestionar(yo, empresa_id),
                  equipo=empresas.empleados(empresa_id)[:5])


@router.get("/red")
def mi_red(request: Request, yo: dict = Depends(usuario_actual)):
    return render(
        request, "red.html", yo,
        recibidas=red.solicitudes_recibidas(yo["id"]),
        enviadas=red.solicitudes_enviadas(yo["id"]),
        sugerencias=red.sugerencias(yo["id"], 6),
        contactos=red.conexiones(yo["id"]),
        colaboradores=red.colaboradores(yo["id"], 4),
    )


@router.get("/empleos")
def empleos(request: Request, oferta: str | None = None, yo: dict = Depends(usuario_actual)):
    lista = ofertas.recomendadas(yo["id"], 50)
    id_sel = oferta or (lista[0]["oferta"]["id"] if lista else None)
    return render(
        request, "empleos.html", yo,
        lista=lista, id_sel=id_sel,
        detalle=ofertas.detalle(id_sel, yo["id"]) if id_sel else None,
        postulaciones=ofertas.mis_postulaciones(yo["id"]),
    )


@router.get("/notificaciones")
def ver_notificaciones(request: Request, yo: dict = Depends(usuario_actual)):
    return render(request, "notificaciones.html", yo,
                  lista=notificaciones.listar(yo["id"]))


@router.get("/buscar")
def buscar(request: Request, q: str = "", yo: dict = Depends(usuario_actual)):
    resultados = busqueda.buscar(q) if q.strip() else None
    return render(request, "buscar.html", yo, q=q, resultados=resultados)


# --- Enlaces que usan las notificaciones de prueba ---
@router.get("/conexiones/solicitudes")
def _solicitudes():
    return RedirectResponse("/red")


@router.get("/postulaciones")
def _postulaciones():
    return RedirectResponse("/empleos")


@router.get("/ofertas/{oferta_id}")
def _oferta(oferta_id: str):
    return RedirectResponse(f"/empleos?oferta={oferta_id}")
