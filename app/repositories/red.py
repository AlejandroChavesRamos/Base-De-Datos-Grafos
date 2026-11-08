"""Consultas Cypher sobre la red de contactos."""
from app.database import db
from app.repositories import consultas_documento as _doc

_USUARIO = "{.id, .nombre, .apellido, .titular}"


def _activa(perfil: str) -> str:
    """Condicion Cypher: el perfil no pertenece a una cuenta desactivada."""
    return f"NOT EXISTS {{ (:Cuenta {{activa: false}})-[:TIENE_PERFIL]->({perfil}) }}"


def conexiones(uid: str):
    return db.leer(
        f"""
        MATCH (:Usuario {{id: $id}})-[c:CONECTA_CON]-(o:Usuario)
        WHERE {_activa("o")}
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
        WHERE {_activa("o")}
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
        WHERE {_activa("o")}
        RETURN o{_USUARIO} AS usuario, s.fecha AS fecha
        ORDER BY s.fecha DESC
        """,
        id=uid,
    )


def _motivo(fila: dict) -> str:
    """Por que se sugiere a esta persona, en palabras."""
    if fila.get("amigos_comunes"):
        n = fila["amigos_comunes"]
        return f"{n} {'contacto' if n == 1 else 'contactos'} en común"
    if fila.get("habilidades_comunes"):
        n = fila["habilidades_comunes"]
        return f"{n} {'habilidad' if n == 1 else 'habilidades'} en común"
    ciudad = fila["usuario"].get("ciudad")
    if fila.get("misma_ciudad"):
        return f"También en {ciudad}"
    return f"En {ciudad}" if ciudad else ""


def sugerencias(uid: str, limite: int = 5):
    """Primero amigos de amigos (3 por amigo comun + 1 por habilidad comun). Si no alcanzan,
    como en una cuenta nueva, se completa con personas afines: habilidades, ciudad y red."""
    filas = db.leer(
        f"""
        MATCH (u:Usuario {{id: $id}})-[:CONECTA_CON]-(amigo:Usuario)-[:CONECTA_CON]-(sug:Usuario)
        WHERE sug <> u
          AND NOT (u)-[:CONECTA_CON]-(sug)
          AND NOT (u)-[:SOLICITA_CONEXION]-(sug)
          AND {_activa("sug")} AND {_activa("amigo")}
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
    faltan = limite - len(filas)
    if faltan > 0:
        filas += db.leer(
            f"""
            MATCH (u:Usuario {{id: $id}}), (sug:Usuario)
            WHERE sug <> u AND NOT sug.id IN $excluir
              AND NOT (u)-[:CONECTA_CON]-(sug)
              AND NOT (u)-[:SOLICITA_CONEXION]-(sug)
              AND {_activa("sug")}
            WITH sug, COUNT {{ (u)-[:TIENE_HABILIDAD]->(:Habilidad)<-[:TIENE_HABILIDAD]-(sug) }} AS habilidades_comunes,
                 sug.ciudad = u.ciudad AS misma_ciudad, COUNT {{ (sug)-[:CONECTA_CON]-() }} AS contactos
            RETURN sug{{.id, .nombre, .apellido, .titular, .ciudad}} AS usuario, 0 AS amigos_comunes,
                   habilidades_comunes, misma_ciudad,
                   habilidades_comunes * 2 + CASE WHEN misma_ciudad THEN 1 ELSE 0 END AS puntaje
            ORDER BY puntaje DESC, contactos DESC, sug.nombre
            LIMIT $limite
            """,
            id=uid, excluir=[f["usuario"]["id"] for f in filas], limite=faltan,
        )
    return [{**f, "motivo": _motivo(f)} for f in filas]


def _novedades(limite: int):
    """Para quien aun no tiene contactos: ofertas vigentes y proyectos de toda la red."""
    ofertas = db.leer(
        f"""
        MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {{estado: 'abierta'}})
        WHERE o.fecha_cierre >= date({{timezone: 'America/Bogota'}}) AND {_activa("e")}
        RETURN 'oferta' AS tipo, toString(o.fecha_publicacion) AS fecha, null AS contacto,
               e{{.id, .nombre}} AS empresa, o{{.id, .titulo, .modalidad, .ciudad}} AS oferta
        ORDER BY fecha DESC LIMIT $limite
        """,
        limite=limite,
    )
    proyectos = db.leer(
        f"""
        MATCH (p:Proyecto {{estado: 'en_curso'}})
        WHERE EXISTS {{ (x:Usuario)-[:PARTICIPA_EN]->(p) WHERE {_activa("x")} }}
        RETURN 'proyecto' AS tipo, toString(p.fecha_inicio) AS fecha, null AS contacto, null AS rol,
               p{{.id, .nombre, .descripcion, .estado}} AS proyecto,
               [(p)-[:USA]->(h:Habilidad) | h.nombre] AS tecnologias
        ORDER BY fecha DESC LIMIT $limite
        """,
        limite=limite,
    )
    return sorted(ofertas + proyectos, key=lambda x: x["fecha"], reverse=True)[:limite]


def actividad(uid: str, limite: int = 8):
    """Publicaciones del inicio, derivadas del grafo: ofertas de las empresas
    de tus contactos y proyectos en los que participan. Sin contactos, novedades de la red."""
    ofertas = db.leer(
        f"""
        MATCH (:Usuario {{id: $id}})-[:CONECTA_CON]-(c:Usuario)
              -[:TRABAJA_EN {{actual: true}}]->(e:Empresa)
              -[:PUBLICA]->(o:Oferta {{estado: 'abierta'}})
        WHERE o.fecha_cierre >= date({{timezone: 'America/Bogota'}}) AND {_activa("c")} AND {_activa("e")}
        RETURN 'oferta' AS tipo, toString(o.fecha_publicacion) AS fecha,
               c{_USUARIO} AS contacto, e{{.id, .nombre}} AS empresa,
               o{{.id, .titulo, .modalidad, .ciudad}} AS oferta
        """,
        id=uid,
    )
    proyectos = db.leer(
        f"""
        MATCH (:Usuario {{id: $id}})-[:CONECTA_CON]-(c:Usuario)-[r:PARTICIPA_EN]->(p:Proyecto)
        WHERE {_activa("c")}
        RETURN 'proyecto' AS tipo, toString(p.fecha_inicio) AS fecha,
               c{_USUARIO} AS contacto, r.rol AS rol,
               p{{.id, .nombre, .descripcion, .estado}} AS proyecto,
               [(p)-[:USA]->(h:Habilidad) | h.nombre] AS tecnologias
        """,
        id=uid,
    )
    propias = sorted(ofertas + proyectos, key=lambda x: x["fecha"], reverse=True)[:limite]
    return propias or _novedades(limite)


def colaboradores(uid: str, limite: int = 4):
    """Personas con las que ya compartiste un proyecto y con las que aun no estas conectado."""
    return _doc.colaboradores(uid, limite)
