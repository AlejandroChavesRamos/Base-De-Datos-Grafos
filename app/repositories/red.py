"""Consultas Cypher sobre la red de contactos."""
from app.database import db

_USUARIO = "{.id, .nombre, .apellido, .titular}"


def conexiones(uid: str):
    return db.leer(
        f"""
        MATCH (:Usuario {{id: $id}})-[c:CONECTA_CON]-(o:Usuario)
        OPTIONAL MATCH (o)-[:TRABAJA_EN {{actual: true}}]->(e:Empresa)
        RETURN o{_USUARIO} AS usuario, e.nombre AS empresa, c.desde AS desde
        ORDER BY c.desde DESC
        """,
        id=uid,
    )


def solicitudes_recibidas(uid: str):
    return db.leer(
        f"""
        MATCH (o:Usuario)-[s:SOLICITA_CONEXION]->(u:Usuario {{id: $id}})
        RETURN o{_USUARIO} AS usuario, s.mensaje AS mensaje, s.fecha AS fecha,
               COUNT {{ (o)-[:CONECTA_CON]-(:Usuario)-[:CONECTA_CON]-(u) }} AS en_comun
        ORDER BY s.fecha DESC
        """,
        id=uid,
    )


def solicitudes_enviadas(uid: str):
    return db.leer(
        f"""
        MATCH (u:Usuario {{id: $id}})-[s:SOLICITA_CONEXION]->(o:Usuario)
        RETURN o{_USUARIO} AS usuario, s.fecha AS fecha
        ORDER BY s.fecha DESC
        """,
        id=uid,
    )


def sugerencias(uid: str, limite: int = 5):
    """Amigos de amigos que aun no son contacto. Puntaje: 3 por amigo comun + 1 por habilidad comun."""
    return db.leer(
        f"""
        MATCH (u:Usuario {{id: $id}})-[:CONECTA_CON]-(amigo:Usuario)-[:CONECTA_CON]-(sug:Usuario)
        WHERE sug <> u
          AND NOT (u)-[:CONECTA_CON]-(sug)
          AND NOT (u)-[:SOLICITA_CONEXION]-(sug)
        WITH u, sug, count(DISTINCT amigo) AS amigos_comunes
        OPTIONAL MATCH (u)-[:TIENE_HABILIDAD]->(h:Habilidad)<-[:TIENE_HABILIDAD]-(sug)
        WITH sug, amigos_comunes, count(h) AS habilidades_comunes
        RETURN sug{_USUARIO} AS usuario, amigos_comunes, habilidades_comunes,
               amigos_comunes * 3 + habilidades_comunes AS puntaje
        ORDER BY puntaje DESC
        LIMIT $limite
        """,
        id=uid, limite=limite,
    )


def actividad(uid: str, limite: int = 8):
    """Publicaciones del inicio, derivadas del grafo: ofertas de las empresas
    de tus contactos y proyectos en los que participan."""
    ofertas = db.leer(
        f"""
        MATCH (:Usuario {{id: $id}})-[:CONECTA_CON]-(c:Usuario)
              -[:TRABAJA_EN {{actual: true}}]->(e:Empresa)
              -[:PUBLICA]->(o:Oferta {{estado: 'abierta'}})
        RETURN 'oferta' AS tipo, toString(o.fecha_publicacion) AS fecha,
               c{_USUARIO} AS contacto, e{{.id, .nombre}} AS empresa,
               o{{.id, .titulo, .modalidad, .ciudad}} AS oferta
        """,
        id=uid,
    )
    proyectos = db.leer(
        f"""
        MATCH (:Usuario {{id: $id}})-[:CONECTA_CON]-(c:Usuario)-[r:PARTICIPA_EN]->(p:Proyecto)
        RETURN 'proyecto' AS tipo, toString(p.fecha_inicio) AS fecha,
               c{_USUARIO} AS contacto, r.rol AS rol,
               p{{.id, .nombre, .descripcion, .estado}} AS proyecto,
               [(p)-[:USA]->(h:Habilidad) | h.nombre] AS tecnologias
        """,
        id=uid,
    )
    return sorted(ofertas + proyectos, key=lambda x: x["fecha"], reverse=True)[:limite]
