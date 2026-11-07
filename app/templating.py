"""Motor de plantillas Jinja2 y filtros de formato en espanol."""
from datetime import date, datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _a_python(v):
    """Convierte tipos temporales de Neo4j o cadenas ISO a date/datetime."""
    if v is None:
        return None
    if hasattr(v, "to_native"):
        v = v.to_native()
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
    return v


def fecha(v):
    d = _a_python(v)
    return "" if d is None else f"{d.day} {MESES[d.month - 1]} {d.year}"


def mes_anio(v):
    d = _a_python(v)
    return "" if d is None else f"{MESES[d.month - 1]} {d.year}"


def hace(v):
    d = _a_python(v)
    if d is None:
        return ""
    if isinstance(d, datetime):
        ahora = datetime.now(d.tzinfo) if d.tzinfo else datetime.now()
        seg = (ahora - d).total_seconds()
    else:
        seg = (date.today() - d).total_seconds()
    if seg < 60:
        return "ahora"
    if seg < 3600:
        return f"hace {int(seg // 60)} min"
    if seg < 86400:
        return f"hace {int(seg // 3600)} h"
    if seg < 86400 * 30:
        return f"hace {int(seg // 86400)} d"
    if seg < 86400 * 365:
        n = int(seg // (86400 * 30))
        return f"hace {n} {'mes' if n == 1 else 'meses'}"
    n = int(seg // (86400 * 365))
    return f"hace {n} {'año' if n == 1 else 'años'}"


def duracion(desde, hasta=None):
    d1, d2 = _a_python(desde), _a_python(hasta) or date.today()
    if d1 is None:
        return ""
    meses = (d2.year - d1.year) * 12 + (d2.month - d1.month) + 1
    anios, resto = divmod(max(meses, 1), 12)
    partes = []
    if anios:
        partes.append(f"{anios} {'año' if anios == 1 else 'años'}")
    if resto:
        partes.append(f"{resto} {'mes' if resto == 1 else 'meses'}")
    return " ".join(partes)


def cop(v):
    return "" if v is None else "$" + f"{int(v):,}".replace(",", ".")


def iniciales(nombre, apellido=None):
    if apellido:
        return (nombre[:1] + apellido[:1]).upper()
    palabras = (nombre or "?").split()
    return "".join(p[0] for p in palabras[:2]).upper()


def color_avatar(identificador):
    h = sum(ord(c) for c in str(identificador)) * 37 % 360
    return f"hsl({h}, 42%, 36%)"


def grado(saltos):
    return {1: "1er", 2: "2º"}.get(saltos, "3er+")


def nivel_texto(n):
    return {1: "Básico", 2: "Intermedio", 3: "Competente", 4: "Avanzado", 5: "Experto"}.get(n, "")


def estado_texto(e):
    return {"enviada": "Enviada", "en_revision": "En revisión",
            "aceptada": "Aceptada", "rechazada": "Rechazada"}.get(e, e or "")


templates.env.filters.update({
    "fecha": fecha, "mes_anio": mes_anio, "hace": hace, "duracion": duracion,
    "cop": cop, "iniciales": iniciales, "color_avatar": color_avatar,
    "grado": grado, "nivel_texto": nivel_texto, "estado_texto": estado_texto,
})

# Mensajes tras una accion. Por la URL solo viaja el CODIGO (?aviso=...), nunca el texto.
AVISOS = {
    "ok": {
        "conexion_enviada": "Invitación enviada.",
        "conexion_aceptada": "Ahora están conectados.",
        "invitacion_ignorada": "Invitación ignorada.",
        "invitacion_retirada": "Invitación retirada.",
        "contacto_eliminado": "Contacto eliminado.",
        "perfil_guardado": "Perfil actualizado.",
        "habilidad_guardada": "Habilidad guardada.",
        "habilidad_quitada": "Habilidad eliminada de tu perfil.",
        "experiencia_agregada": "Experiencia agregada.",
        "experiencia_quitada": "Experiencia eliminada.",
        "proyecto_creado": "Proyecto creado. Ya participas en él.",
        "proyecto_unido": "Te uniste al proyecto.",
        "proyecto_salido": "Saliste del proyecto.",
        "postulado": "Tu postulación fue enviada.",
        "postulacion_retirada": "Retiraste tu postulación.",
        "notificaciones_leidas": "Todas las notificaciones quedaron como leídas.",
        "password_cambiada": "Contraseña actualizada. Se cerraron tus otras sesiones.",
        "cuenta_eliminada": "Tu cuenta fue eliminada.",
        "empresa_guardada": "Datos de la empresa actualizados.",
        "oferta_creada": "Oferta guardada como borrador. Agrega los requisitos y publícala.",
        "oferta_actualizada": "Oferta actualizada.",
        "oferta_publicada": "Oferta publicada. Se avisó a {n} personas con un perfil afín.",
        "oferta_cerrada": "Oferta cerrada: ya no recibe postulaciones.",
        "oferta_reabierta": "Oferta reabierta.",
        "requisito_guardado": "Requisito guardado.",
        "requisito_quitado": "Requisito eliminado.",
        "estado_actualizado": "Estado actualizado. La persona recibió una notificación.",
        "rol_actualizado": "Rol actualizado. La persona recibió una notificación.",
    },
    "error": {
        "no_se_pudo": "No se pudo completar la acción. Puede que ya se hubiera realizado.",
        "no_postulable": "No puedes postularte: la oferta ya cerró, venció o ya te postulaste.",
        "no_publicable": "No se pudo publicar. Revisa que tenga al menos un requisito y una fecha de cierre vigente.",
        "oferta_vencida": "Esta oferta ya venció. Edita la fecha de cierre para reabrirla.",
        "requisito_necesario": "Una oferta publicada debe conservar al menos un requisito.",
        "experiencia_repetida": "Ya tienes registrada esa empresa con la misma fecha de inicio.",
        "dato_invalido": "Revisa los datos del formulario.",
    },
}
templates.env.globals["AVISOS"] = AVISOS
