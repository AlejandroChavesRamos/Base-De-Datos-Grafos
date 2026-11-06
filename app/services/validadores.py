"""Validacion de formularios. Cada funcion devuelve (datos_limpios, errores)."""
from datetime import date

from app.services.auth import SECTORES, TAMANOS

MODALIDADES = {"presencial": "Presencial", "hibrida": "Híbrida", "remota": "Remota"}
ESTADOS_PROYECTO = {"en_curso": "En curso", "finalizado": "Finalizado"}
ESTADOS_POSTULACION = {"en_revision": "En revisión", "aceptada": "Aceptada", "rechazada": "Rechazada"}


def texto(valor, maximo: int) -> str:
    """Una sola linea: colapsa espacios y recorta."""
    return " ".join((valor or "").split())[:maximo]


def texto_largo(valor, maximo: int) -> str:
    """Varias lineas (descripciones): conserva los saltos de linea."""
    lineas = [" ".join(l.split()) for l in (valor or "").strip().splitlines()]
    return "\n".join(lineas).strip()[:maximo]


def entero(valor, minimo: int, maximo: int):
    try:
        n = int(str(valor).strip())
    except (TypeError, ValueError):
        return None
    return n if minimo <= n <= maximo else None


def fecha(valor):
    try:
        return date.fromisoformat((valor or "").strip())
    except ValueError:
        return None


def casilla(valor) -> bool:
    return valor in ("on", "true", "1")


def perfil(f):
    e = {}
    d = {"nombre": texto(f.get("nombre"), 60), "apellido": texto(f.get("apellido"), 60),
         "titular": texto(f.get("titular"), 120), "ciudad": texto(f.get("ciudad"), 60),
         "resumen": texto_largo(f.get("resumen"), 1000),
         "buscando_empleo": casilla(f.get("buscando_empleo"))}
    anios = entero(f.get("experiencia_anios"), 0, 60)
    d["experiencia_anios"] = anios if anios is not None else 0
    if not d["nombre"]:
        e["nombre"] = "Escribe tu nombre."
    if not d["apellido"]:
        e["apellido"] = "Escribe tu apellido."
    if not d["ciudad"]:
        e["ciudad"] = "Escribe tu ciudad."
    if anios is None:
        e["experiencia_anios"] = "Escribe un número entre 0 y 60."
    return d, e


def habilidad(f):
    e = {}
    hid = texto(f.get("habilidad_id"), 64)
    nivel = entero(f.get("nivel"), 1, 5)
    anios = entero(f.get("anios") or 0, 0, 60)
    if not hid:
        e["habilidad_id"] = "Elige una habilidad."
    if nivel is None:
        e["nivel"] = "El nivel va de 1 a 5."
    if anios is None:
        e["anios"] = "Los años van de 0 a 60."
    return {"hid": hid, "nivel": nivel, "anios": anios}, e


def experiencia(f):
    e = {}
    actual = casilla(f.get("actual"))
    desde, hasta = fecha(f.get("desde")), fecha(f.get("hasta"))
    d = {"empresa_id": texto(f.get("empresa_id"), 64), "cargo": texto(f.get("cargo"), 100),
         "actual": actual, "desde": desde.isoformat() if desde else None,
         "hasta": None if actual or not hasta else hasta.isoformat()}
    if not d["empresa_id"]:
        e["empresa_id"] = "Elige una empresa."
    if not d["cargo"]:
        e["cargo"] = "Escribe tu cargo."
    if not desde or desde > date.today():
        e["desde"] = "Escribe una fecha de inicio válida (no futura)."
    if not actual:
        if not hasta:
            e["hasta"] = "Indica la fecha de salida, o marca que es tu empleo actual."
        elif hasta > date.today() or (desde and hasta < desde):
            e["hasta"] = "La fecha de salida debe estar entre el inicio y hoy."
    return d, e


def proyecto(f):
    e = {}
    inicio, fin = fecha(f.get("fecha_inicio")), fecha(f.get("fecha_fin"))
    estado = f.get("estado", "")
    d = {"nombre": texto(f.get("nombre"), 120), "descripcion": texto_largo(f.get("descripcion"), 600),
         "estado": estado, "rol": texto(f.get("rol"), 60),
         "fecha_inicio": inicio.isoformat() if inicio else None,
         "fecha_fin": fin.isoformat() if fin and estado == "finalizado" else None,
         "con_empresa": casilla(f.get("con_empresa"))}
    if len(d["nombre"]) < 3:
        e["nombre"] = "El nombre debe tener al menos 3 caracteres."
    if estado not in ESTADOS_PROYECTO:
        e["estado"] = "Elige el estado."
    if len(d["rol"]) < 2:
        e["rol"] = "Escribe tu rol en el proyecto."
    if not inicio:
        e["fecha_inicio"] = "Escribe la fecha de inicio."
    if estado == "finalizado" and (not fin or (inicio and fin < inicio)):
        e["fecha_fin"] = "Indica una fecha de fin posterior al inicio."
    techs = list(dict.fromkeys(t for t in f.getlist("techs") if t))
    if len(techs) > 10:
        e["techs"] = "Elige máximo 10 tecnologías."
    return d, techs[:10], e


def oferta(f):
    e = {}
    cierre = fecha(f.get("fecha_cierre"))
    smin, smax = entero(f.get("salario_min"), 0, 1_000_000_000), entero(f.get("salario_max"), 0, 1_000_000_000)
    d = {"titulo": texto(f.get("titulo"), 120), "descripcion": texto_largo(f.get("descripcion"), 2000),
         "modalidad": f.get("modalidad", ""), "ciudad": texto(f.get("ciudad"), 60),
         "salario_min": smin, "salario_max": smax,
         "fecha_cierre": cierre.isoformat() if cierre else None}
    if len(d["titulo"]) < 3:
        e["titulo"] = "El título debe tener al menos 3 caracteres."
    if len(d["descripcion"]) < 10:
        e["descripcion"] = "Describe el cargo (mínimo 10 caracteres)."
    if d["modalidad"] not in MODALIDADES:
        e["modalidad"] = "Elige la modalidad."
    if not d["ciudad"]:
        e["ciudad"] = "Escribe la ciudad."
    if smin is None:
        e["salario_min"] = "Escribe un valor válido."
    if smax is None:
        e["salario_max"] = "Escribe un valor válido."
    elif smin is not None and smax < smin:
        e["salario_max"] = "Debe ser mayor o igual al mínimo."
    if not cierre or cierre < date.today():
        e["fecha_cierre"] = "Elige una fecha de cierre desde hoy en adelante."
    return d, e


def requisito(f):
    e = {}
    hid = texto(f.get("habilidad_id"), 64)
    nivel = entero(f.get("nivel_minimo"), 1, 5)
    if not hid:
        e["habilidad_id"] = "Elige una habilidad."
    if nivel is None:
        e["nivel_minimo"] = "El nivel va de 1 a 5."
    return {"hid": hid, "nivel": nivel, "obligatoria": casilla(f.get("obligatoria"))}, e


def empresa(f):
    e = {}
    d = {"nombre": texto(f.get("nombre"), 100), "sector": f.get("sector", ""), "tamano": f.get("tamano", ""),
         "ciudad": texto(f.get("ciudad"), 60), "descripcion": texto_largo(f.get("descripcion"), 400),
         "sitio_web": texto(f.get("sitio_web"), 200)}
    if not d["nombre"]:
        e["nombre"] = "Escribe el nombre de la empresa."
    if d["sector"] not in SECTORES:
        e["sector"] = "Elige un sector."
    if d["tamano"] not in TAMANOS:
        e["tamano"] = "Elige el tamaño."
    if not d["ciudad"]:
        e["ciudad"] = "Escribe la ciudad."
    if d["sitio_web"] and not d["sitio_web"].lower().startswith(("http://", "https://")):
        e["sitio_web"] = "Debe empezar por http:// o https://"
    return d, e
