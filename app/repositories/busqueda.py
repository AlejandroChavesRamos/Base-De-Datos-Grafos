"""Busqueda simple por texto en usuarios, empresas y ofertas. Ignora mayusculas y tildes."""
import unicodedata

from app.database import db

# Marcas que se quitan: grave, aguda, circunflejo, tilde de la ñ, diéresis y cedilla.
MARCAS = ["̀", "́", "̂", "̃", "̈", "̧"]


def sin_tildes(texto: str) -> str:
    """'Diseño' -> 'diseno'. Debe quitar lo mismo que expresion_sin_tildes en Cypher."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if c not in MARCAS)


def expresion_sin_tildes(expresion: str) -> str:
    """Lo mismo que sin_tildes, como expresion Cypher. Necesita el parametro $marcas."""
    return f"reduce(s = normalize(toLower({expresion}), NFD), m IN $marcas | replace(s, m, ''))"


PERSONA = expresion_sin_tildes("u.nombre + ' ' + u.apellido + ' ' + coalesce(u.titular, '')")
EMPRESA = expresion_sin_tildes("e.nombre + ' ' + coalesce(e.sector, '')")
OFERTA = expresion_sin_tildes("o.titulo")


def _activa(perfil: str) -> str:
    """Condicion Cypher: el perfil no pertenece a una cuenta desactivada."""
    return f"NOT EXISTS {{ (:Cuenta {{activa: false}})-[:TIENE_PERFIL]->({perfil}) }}"


def buscar(q: str, limite: int = 10):
    q = sin_tildes(q.strip())
    if not q:
        return {"personas": [], "empresas": [], "ofertas": []}
    personas = db.leer(
        f"""
        MATCH (u:Usuario)
        WHERE {PERSONA} CONTAINS $q AND {_activa("u")}
        RETURN u{{.id, .nombre, .apellido, .titular, .ciudad}} AS usuario
        ORDER BY u.nombre LIMIT $limite
        """,
        q=q, marcas=MARCAS, limite=limite,
    )
    empresas = db.leer(
        f"""
        MATCH (e:Empresa)
        WHERE {EMPRESA} CONTAINS $q AND {_activa("e")}
        RETURN e{{.id, .nombre, .sector, .ciudad}} AS empresa
        ORDER BY e.nombre LIMIT $limite
        """,
        q=q, marcas=MARCAS, limite=limite,
    )
    ofertas = db.leer(
        f"""
        MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta)
        WHERE o.estado <> 'borrador' AND {OFERTA} CONTAINS $q AND {_activa("e")}
        RETURN o{{.id, .titulo, .estado, .ciudad}} AS oferta, e.nombre AS empresa,
               o.fecha_cierre < date({{timezone: 'America/Bogota'}}) AS vencida
        ORDER BY o.titulo LIMIT $limite
        """,
        q=q, marcas=MARCAS, limite=limite,
    )
    return {"personas": personas, "empresas": empresas, "ofertas": ofertas}
