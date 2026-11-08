"""Analitica de la red, mapa interactivo y laboratorio de consultas.

Cada cuenta ve la analitica de SU circulo, nunca la de toda la red:

  persona   ella y las personas con las que esta conectada
  empresa   sus trabajadores actuales y las personas que se postularon a sus ofertas
  admin     toda la red (permiso 'analitica.administrar'); es el unico que recalcula las metricas
  staff     sin analitica

El circulo se decide AQUI, en el servidor, segun la cuenta: lo que pida el navegador no lo cambia.
Las consultas del documento (/consultas) son solo para quien tenga el permiso 'consultas.ver' (admin).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from neo4j.exceptions import Neo4jError

from app.dependencias import permiso_post, permiso_requerido, visor
from app.repositories import analitica as repo
from app.repositories import eventos
from app.routers.utiles import render, volver
from app.services import analitica as servicio
from app.services import laboratorio

router = APIRouter()

TEXTOS = {
    "red": ("La red por dentro", "Lo que dice el grafo sobre toda la red: quién influye, qué grupos se forman y qué habilidades se piden.",
            "Estás viendo toda la red (administración)."),
    "persona": ("Tu red por dentro", "Quién influye en tu círculo, qué grupos se forman y qué habilidades se piden.",
                "Incluye solo tus datos y los de las personas con las que estás conectado."),
    "empresa": ("Tu equipo y tus candidatos", "Quién influye entre las personas de tu empresa, qué grupos se forman y qué habilidades se piden.",
                "Incluye a tus trabajadores actuales y a las personas que se postularon a tus ofertas."),
}


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _alcance(yo: dict, pedido: str | None = None) -> str:
    """'red', 'persona' o 'empresa'. Se decide por la cuenta; si el navegador pide otro, se rechaza."""
    if "analitica.administrar" in yo["permisos"]:
        alcance = "red"
    elif yo["tipo"] == "persona":
        alcance = "persona"
    elif yo["tipo"] == "empresa":
        alcance = "empresa"
    else:
        raise HTTPException(403, "La analítica no está disponible para esta cuenta.")
    if pedido and pedido != alcance:
        raise HTTPException(403, "No puedes ver la analítica de ese alcance.")
    return alcance


def _circulo(yo: dict, alcance: str) -> dict:
    """Ids de las personas que esta cuenta puede ver en la analitica (None = toda la red)."""
    if alcance == "persona":
        c = repo.contactos_de(yo["id"])
        return {"ids": set(c["contactos"]) | {yo["id"]}, "empleados": set(), "postulantes": set()}
    if alcance == "empresa":
        r = repo.red_de_empresa(yo["id"])
        empleados, postulantes = set(r["empleados"]), set(r["postulantes"]) - set(r["empleados"])
        return {"ids": empleados | postulantes, "empleados": empleados, "postulantes": postulantes}
    return {"ids": None, "empleados": set(), "postulantes": set()}


def _aristas(alcance: str, circulo: dict, ids: list[str]) -> list[dict]:
    aristas = repo.aristas_entre(ids)
    if alcance == "empresa":  # entre candidatos solo se muestran los vinculos con alguien de la empresa
        e = circulo["empleados"]
        aristas = [a for a in aristas if a["origen"] in e or a["destino"] in e]
    return aristas


def _en_circulo(usuarios: list[dict], circulo: dict) -> list[dict]:
    if circulo["ids"] is None:
        return usuarios
    return [f for f in usuarios if f["usuario"]["id"] in circulo["ids"]]


# ================================================================== panel
@router.get("/analitica")
def panel(request: Request, yo: dict = Depends(visor)):
    alcance = _alcance(yo)
    circulo = _circulo(yo, alcance)
    usuarios = _en_circulo(repo.usuarios_con_metricas(), circulo)
    ids_circulo = sorted(circulo["ids"]) if circulo["ids"] is not None else None
    numeracion = servicio.numerar_comunidades(usuarios)  # se numeran DENTRO del circulo: Comunidad 1, 2, 3...
    estado = repo.estado_metricas()
    comunidades = servicio.comunidades(usuarios, numeracion, repo.habilidades_por_comunidad(ids_circulo), repo.sectores_por_comunidad(ids_circulo))
    desactualizadas, resumen = False, None
    if alcance == "red":
        r = resumen = repo.resumen_red()
        desactualizadas = bool(estado and estado.get("usuarios") != r["usuarios"])
        indicadores = [("personas", r["usuarios"], "Personas"), ("conexiones", r["conexiones"], "Conexiones"),
                       ("comunidades", len(comunidades), "Comunidades"), ("empresas", r["empresas"], "Empresas"),
                       ("ofertas", r["ofertas"], "Ofertas abiertas")]
    elif alcance == "persona":
        indicadores = [("personas", len(circulo["ids"]), "Personas en tu red"),
                       ("conexiones", len(_aristas(alcance, circulo, ids_circulo)), "Conexiones entre ellas"),
                       ("comunidades", len(comunidades), "Comunidades")]
    else:
        indicadores = [("trabajadores", len(circulo["empleados"]), "Trabajadores"),
                       ("postulantes", len(circulo["postulantes"]), "Personas que se postularon"),
                       ("comunidades", len(comunidades), "Comunidades")]
    puede_administrar = alcance == "red"
    titulo, subtitulo, alcance_texto = TEXTOS[alcance]
    return render(
        request, "analitica.html", yo,
        alcance=alcance, titulo=titulo, subtitulo=subtitulo, alcance_texto=alcance_texto, indicadores=indicadores,
        estado=estado, resumen=resumen, hay_metricas=servicio.hay_metricas(usuarios), desactualizadas=desactualizadas,
        influyentes=servicio.influyentes(usuarios, numeracion), puentes=servicio.puentes(usuarios, numeracion),
        comunidades=comunidades, demanda=repo.brecha_habilidades(10),
        puede_administrar=puede_administrar, gds=repo.gds_disponible() if puede_administrar else None,
        puede_ver_consultas="consultas.ver" in yo["permisos"],
    )


@router.post("/analitica/recalcular")
def recalcular(request: Request, yo: dict = Depends(permiso_post("analitica.administrar"))):
    if not repo.gds_disponible():
        return volver("/analitica", error="gds_no_disponible")
    try:
        r = repo.recalcular(yo["email"])
    except Neo4jError:
        eventos.registrar(yo["cuenta_id"], "metricas_fallidas", _ip(request), "")
        return volver("/analitica", error="metricas_fallidas")
    eventos.registrar(yo["cuenta_id"], "metricas_recalculadas", _ip(request),
                      f"{r['usuarios']} personas, {r['comunidades']} comunidades; fallos: {','.join(r['fallos']) or 'ninguno'}")
    if not r["hechos"]:
        return volver("/analitica", error="metricas_fallidas")
    return volver("/analitica", aviso="metricas_parciales" if r["fallos"] else "metricas_recalculadas")


# ================================================================== mapa
@router.get("/analitica/mapa")
def mapa(request: Request, yo: dict = Depends(visor)):
    return render(request, "analitica_mapa.html", yo, alcance=_alcance(yo, request.query_params.get("alcance")))


@router.get("/analitica/mapa.json")
def mapa_datos(request: Request, yo: dict = Depends(visor)):
    alcance = _alcance(yo, request.query_params.get("alcance"))
    circulo = _circulo(yo, alcance)
    todos = repo.usuarios_con_metricas()
    elegidos = _en_circulo(todos, circulo)
    if alcance == "red":
        elegidos = elegidos[:300]  # los mas influyentes: un mapa de miles de puntos no se puede leer
    numeracion = servicio.numerar_comunidades(elegidos)
    ids = [f["usuario"]["id"] for f in elegidos]
    nodos = [{"id": f["usuario"]["id"], "nombre": f"{f['usuario']['nombre']} {f['usuario']['apellido']}",
              "corto": f["usuario"]["nombre"], "titular": f["usuario"].get("titular"),
              "pagerank": f["usuario"].get("pagerank"), "comunidad": numeracion.get(f["usuario"].get("comunidad")),
              "yo": alcance == "persona" and f["usuario"]["id"] == yo["id"]} for f in elegidos]
    leyenda = [{"numero": c["numero"], "etiqueta": c["etiqueta"], "miembros": c["miembros"]}
               for c in servicio.comunidades(elegidos, numeracion, repo.habilidades_por_comunidad(ids), repo.sectores_por_comunidad(ids))]
    return JSONResponse({"alcance": alcance, "nodos": nodos, "aristas": _aristas(alcance, circulo, ids), "comunidades": leyenda})


# ============================================================= laboratorio
@router.get("/consultas")
def consultas(request: Request, consulta: str | None = None, yo: dict = Depends(permiso_requerido("consultas.ver"))):
    opciones = laboratorio.Opciones()
    activa = laboratorio.POR_ID.get(consulta or "")
    resultado = laboratorio.ejecutar(activa, request.query_params, opciones) if activa else None
    tarjetas = [{**c, "params": [{**p, "opciones": opciones.de(p["tipo"])} for p in c["parametros"]],
                 "nombres_param": sorted(laboratorio.parametros_cypher(c))} for c in laboratorio.CONSULTAS]
    return render(request, "consultas.html", yo, tarjetas=tarjetas, grupos=laboratorio.GRUPOS,
                  activa=activa["id"] if activa else None, resultado=resultado, elegido=request.query_params)
