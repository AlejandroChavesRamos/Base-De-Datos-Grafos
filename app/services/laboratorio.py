"""Laboratorio de consultas (/consultas): las consultas que pide el documento.

Cada consulta se muestra con su pregunta, su texto Cypher (el mismo que se ejecuta),
sus parametros y su resultado. Es una herramienta de administracion: solo la ve quien
tiene el permiso 'consultas.ver' (admin), asi que aqui no hay reglas por tipo de cuenta;
lo unico que se valida es que cada valor elegido sea una de las opciones ofrecidas.
"""
import re

from app.repositories import analitica, moderacion, perfiles
from app.repositories import consultas_documento as cd

LIMITE = 10

# Parametro: nombre del campo del formulario, etiqueta y de que lista se elige
P_PERSONA = {"campo": "persona", "etiqueta": "Persona", "tipo": "persona"}
P_PERSONA_A = {"campo": "persona_a", "etiqueta": "Primera persona", "tipo": "persona"}
P_PERSONA_B = {"campo": "persona_b", "etiqueta": "Segunda persona", "tipo": "persona"}
P_EMPRESA = {"campo": "empresa", "etiqueta": "Empresa de destino", "tipo": "empresa"}
P_OFERTA = {"campo": "oferta", "etiqueta": "Oferta", "tipo": "oferta"}


def _persona(u):
    return {"t": f"{u['nombre']} {u.get('apellido') or ''}".strip(), "href": f"/perfil/{u['id']}"}


def _lista(valores):
    return ", ".join(str(v) for v in valores) if valores else "—"


def _num(v, decimales=3):
    return "—" if v is None else f"{v:.{decimales}f}"


# --- presentadores: filas de Neo4j -> (columnas, filas de celdas) -----------------------
def _p_q1(f):
    return (["Persona", "Titular", "Habilidades en común", "Similitud"],
            [[_persona(x["usuario"]), x["usuario"].get("titular") or "—", _lista(x["habilidades_comunes"]), _num(x["similitud"], 2)] for x in f])


def _p_q2(f):
    return (["Contacto en común", "Titular"], [[_persona(x["usuario"]), x["usuario"].get("titular") or "—"] for x in f])


def _p_q3(f):
    return (["Ruta", "Saltos"], [[" → ".join(x["ruta"]), str(x["saltos"])] for x in f])


def _p_q4(f):
    return (["Candidato", "Titular", "Requisitos cumplidos", "Habilidades", "Contactos en la empresa", "Puntaje", "¿Ya se postuló?", "Busca empleo"],
            [[_persona(x["usuario"]), x["usuario"].get("titular") or "—", f"{x['n_cumple']} de {x['total_req']}", _lista(x["habilidades"]),
              _lista(x["contactos"]), str(x["puntaje"]), "Sí" if x["postulado"] else "No",
              "Sí" if x["usuario"].get("buscando_empleo") else "No"] for x in f])


def _p_q5(f):
    return (["Proyecto 1", "Proyecto 2", "Tecnologías en común", "Miembros en común", "Afinidad"],
            [[x["proyecto_1"], x["proyecto_2"], _lista(x["tecnologias"]), _lista(x["miembros"]), str(x["afinidad"])] for x in f])


def _p_q6(f):
    return (["Habilidad", "Categoría", "Ofertas que la piden", "Como obligatoria"],
            [[x["habilidad"], (x["categoria"] or "").capitalize(), str(x["ofertas"]), str(x["como_obligatoria"])] for x in f])


def _p_c1(f):
    return (["Ruta", "Saltos"], [[" → ".join(x["ruta"]), str(x["saltos"])] for x in f])


def _p_c2(f):
    return (["Ruta hasta la oferta", "Saltos", "Oferta"], [[" → ".join(x["ruta"] + [x["oferta"]]), str(x["saltos"]), x["oferta"]] for x in f])


def _p_h1(f):
    return (["Habilidad", "Categoría", "Nivel de la primera persona", "Nivel de la segunda"],
            [[x["habilidad"], (x["categoria"] or "").capitalize(), str(x["nivel_a"]), str(x["nivel_b"])] for x in f])


def _p_a1(f):
    return (["Puesto", "Persona", "PageRank", "Conexiones"],
            [[str(i), _persona(x["usuario"]), _num(x["usuario"]["pagerank"]), str(x["conexiones"])] for i, x in enumerate(f, 1)])


def _p_a2(f):
    return (["Comunidad (id de Louvain)", "Miembros", "Personas"], [[str(x["comunidad"]), str(x["miembros"]), _lista(x["personas"])] for x in f])


def _p_a3(f):
    return (["Persona", "Intermediación", "Conexiones"],
            [[_persona(x["usuario"]), _num(x["usuario"]["intermediacion"], 2), str(x["conexiones"])] for x in f])


def _p_r1(f):
    return (["Persona", "Titular", "Contactos en común", "Habilidades en común", "Puntaje"],
            [[_persona(x["usuario"]), x["usuario"].get("titular") or "—", str(x["amigos_comunes"]), str(x["habilidades_comunes"]), str(x["puntaje"])] for x in f])


def _p_r2(f):
    return (["Oferta", "Empresa", "Afinidad", "Requisitos cumplidos", "Contactos en la empresa"],
            [[{"t": x["oferta"]["titulo"], "href": f"/empleos?oferta={x['oferta']['id']}"}, x["empresa"], f"{x['afinidad']} %",
              f"{x['cumple']} de {x['total_req']}", _lista(x["contactos"])] for x in f])


def _p_r3(f):
    return (["Persona", "Titular", "Proyectos compartidos"],
            [[_persona(x["usuario"]), x["usuario"].get("titular") or "—", _lista(x["proyectos_compartidos"])] for x in f])


CONSULTAS = [
    {"id": "q1", "grupo": "enunciado", "codigo": "Q1", "pregunta": "¿Qué usuarios tienen habilidades similares?",
     "cypher": cd.Q1_SIMILARES, "parametros": [P_PERSONA], "presentar": _p_q1,
     "armar": lambda v: {"id": v["persona"]}},
    {"id": "q2", "grupo": "enunciado", "codigo": "Q2", "pregunta": "¿Qué contactos en común existen entre dos profesionales?",
     "cypher": cd.Q2_COMUNES, "parametros": [P_PERSONA_A, P_PERSONA_B], "presentar": _p_q2,
     "armar": lambda v: {"a": v["persona_a"], "b": v["persona_b"]}},
    {"id": "q3", "grupo": "enunciado", "codigo": "Q3", "pregunta": "¿Cuál es la ruta más corta entre un usuario y una empresa?",
     "cypher": cd.Q3_RUTA, "parametros": [P_PERSONA, P_EMPRESA], "presentar": _p_q3,
     "armar": lambda v: {"id": v["persona"], "empresa": v["empresa"]}},
    {"id": "q4", "grupo": "enunciado", "codigo": "Q4",
     "pregunta": "¿Qué candidatos podrían recomendarse para una oferta según sus conexiones y competencias?",
     "cypher": cd.Q4_CANDIDATOS, "parametros": [P_OFERTA], "presentar": _p_q4,
     "armar": lambda v: {"oferta": v["oferta"]}},
    {"id": "q5", "grupo": "enunciado", "codigo": "Q5", "pregunta": "¿Qué proyectos comparten tecnologías o miembros relacionados?",
     "cypher": cd.Q5_PROYECTOS, "parametros": [], "presentar": _p_q5, "armar": lambda v: {}},
    {"id": "q6", "grupo": "enunciado", "codigo": "Q6", "pregunta": "¿Qué habilidades son las más demandadas en las ofertas?",
     "cypher": cd.Q6_DEMANDA, "parametros": [], "presentar": _p_q6, "armar": lambda v: {}},
    {"id": "c1", "grupo": "caminos", "codigo": "C1", "pregunta": "¿Cómo están conectadas dos personas?",
     "cypher": cd.C1_CAMINO_PERSONA, "parametros": [P_PERSONA_A, P_PERSONA_B], "presentar": _p_c1,
     "armar": lambda v: {"a": v["persona_a"], "b": v["persona_b"]}},
    {"id": "c2", "grupo": "caminos", "codigo": "C2", "pregunta": "¿Cuál es el camino de una persona hasta una oferta laboral?",
     "cypher": cd.C2_CAMINO_OFERTA, "parametros": [P_PERSONA, P_OFERTA], "presentar": _p_c2,
     "armar": lambda v: {"id": v["persona"], "oferta": v["oferta"]}},
    {"id": "h1", "grupo": "caminos", "codigo": "H1", "pregunta": "¿Qué habilidades comparten dos personas?",
     "cypher": cd.H1_HABILIDADES_EN_COMUN, "parametros": [P_PERSONA_A, P_PERSONA_B], "presentar": _p_h1,
     "armar": lambda v: {"a": v["persona_a"], "b": v["persona_b"]}},
    {"id": "a1", "grupo": "analitica", "codigo": "A1", "pregunta": "¿Quiénes son los usuarios más influyentes?",
     "cypher": cd.A1_INFLUYENTES, "parametros": [], "presentar": _p_a1, "armar": lambda v: {}, "requiere_metricas": True},
    {"id": "a2", "grupo": "analitica", "codigo": "A2", "pregunta": "¿Qué comunidades se detectan en la red?",
     "cypher": cd.A2_COMUNIDADES, "parametros": [], "presentar": _p_a2, "armar": lambda v: {}, "requiere_metricas": True},
    {"id": "a3", "grupo": "analitica", "codigo": "A3", "pregunta": "¿Quiénes conectan a personas que de otro modo no se conocerían?",
     "cypher": cd.A3_PUENTES, "parametros": [], "presentar": _p_a3, "armar": lambda v: {}, "requiere_metricas": True},
    {"id": "r1", "grupo": "recomendacion", "codigo": "R1", "pregunta": "¿A qué personas podría conectarme?",
     "cypher": cd.R1_CONTACTOS, "parametros": [P_PERSONA], "presentar": _p_r1,
     "armar": lambda v: {"id": v["persona"]}},
    {"id": "r2", "grupo": "recomendacion", "codigo": "R2", "pregunta": "¿Qué empleos me convienen?",
     "cypher": cd.R2_EMPLEOS, "parametros": [P_PERSONA], "presentar": _p_r2,
     "armar": lambda v: {"id": v["persona"]}},
    {"id": "r3", "grupo": "recomendacion", "codigo": "R3", "pregunta": "¿Con quién podría colaborar?",
     "cypher": cd.R3_COLABORADORES, "parametros": [P_PERSONA], "presentar": _p_r3,
     "armar": lambda v: {"id": v["persona"]}},
]
POR_ID = {c["id"]: c for c in CONSULTAS}
GRUPOS = [("enunciado", "Las seis preguntas del enunciado"), ("caminos", "Caminos y habilidades compartidas"), ("analitica", "Analítica de la red"),
          ("recomendacion", "Recomendaciones")]


def parametros_cypher(c: dict) -> set[str]:
    """Nombres $parametro que usa el texto Cypher de la consulta."""
    return set(re.findall(r"\$(\w+)", c["cypher"]))


class Opciones:
    """Listas para los selectores. Cada una se consulta una sola vez por peticion."""

    def __init__(self):
        self._cache = {}

    def de(self, tipo: str) -> list[tuple[str, str]]:
        if tipo not in self._cache:
            self._cache[tipo] = getattr(self, f"_{tipo}")()
        return self._cache[tipo]

    def _persona(self):
        return [(p["id"], f"{p['nombre']} {p['apellido']}") for p in analitica.personas_visibles()]

    def _empresa(self):
        return [(e["id"], e["nombre"]) for e in perfiles.lista_empresas()]

    def _oferta(self):
        return [(x["oferta"]["id"], f"{x['empresa']} · {x['oferta']['titulo']}") for x in moderacion.ofertas()]


def resolver(c: dict, formulario, opciones: Opciones):
    """Valores de los parametros ya validados contra las opciones ofrecidas.
    Devuelve (valores, error). Lo que llega del formulario nunca se usa sin comprobarlo."""
    valores = {}
    for p in c["parametros"]:
        elegido = (formulario.get(p["campo"]) or "").strip()
        permitidos = {i for i, _ in opciones.de(p["tipo"])}
        if not elegido:
            return None, f"Elige: {p['etiqueta'].lower()}."
        if elegido not in permitidos:
            return None, f"«{p['etiqueta']}» no es una opción válida para tu cuenta."
        valores[p["campo"]] = elegido
    return valores, None


def ejecutar(c: dict, formulario, opciones: Opciones) -> dict:
    valores, error = resolver(c, formulario, opciones)
    if error:
        return {"error": error}
    filas, ms = cd.ejecutar(c["cypher"], limite=LIMITE, **c["armar"](valores))
    columnas, celdas = c["presentar"](filas)
    return {"columnas": columnas, "filas": celdas, "n": len(celdas), "ms": ms, "valores": valores,
            "sin_metricas": bool(c.get("requiere_metricas")) and not celdas}
