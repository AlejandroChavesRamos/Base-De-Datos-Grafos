"""Moderacion: listar y borrar ofertas y proyectos."""
from app.database import db


def ofertas(limite: int = 200):
    return db.leer(
        """
        MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta)
        RETURN o{.id, .titulo, .estado, .fecha_publicacion} AS oferta, e.nombre AS empresa,
               COUNT { (:Usuario)-[:POSTULA_A]->(o) } AS postulantes
        ORDER BY e.nombre, o.fecha_publicacion DESC
        LIMIT $limite
        """,
        limite=limite,
    )


def proyectos(limite: int = 200):
    return db.leer(
        """
        MATCH (p:Proyecto)
        OPTIONAL MATCH (p)-[:PERTENECE_A]->(e:Empresa)
        RETURN p{.id, .nombre, .estado} AS proyecto, e.nombre AS empresa,
               COUNT { (:Usuario)-[:PARTICIPA_EN]->(p) } AS miembros
        ORDER BY p.nombre
        LIMIT $limite
        """,
        limite=limite,
    )


def eliminar_oferta(oid: str):
    """Borra la oferta y, en la misma transaccion: quita los avisos viejos que apuntaban a ella
    y avisa a quienes se habian postulado. Devuelve el titulo (o None si no existia)."""
    filas = db.escribir(
        """
        MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {id: $oid})
        OPTIONAL MATCH (u:Usuario)-[:POSTULA_A]->(o)
        WITH e, o, collect(u) AS postulantes
        OPTIONAL MATCH (n:Notificacion) WHERE n.enlace = '/empleos?oferta=' + o.id
        WITH e, o, postulantes, collect(n) AS viejas
        FOREACH (x IN viejas | DETACH DELETE x)
        FOREACH (x IN postulantes |
            CREATE (:Notificacion {id: randomUUID(), tipo: 'oferta_retirada',
                                   mensaje: 'La oferta "' + o.titulo + '" de ' + e.nombre + ' fue retirada por moderación.',
                                   leida: false, fecha: datetime(), enlace: '/empleos'})-[:PARA]->(x))
        WITH o, o.titulo AS titulo
        DETACH DELETE o
        RETURN titulo
        """,
        oid=oid,
    )
    return filas[0]["titulo"] if filas else None


def eliminar_proyecto(pid: str):
    filas = db.escribir(
        "MATCH (p:Proyecto {id: $pid}) WITH p, p.nombre AS nombre DETACH DELETE p RETURN nombre",
        pid=pid,
    )
    return filas[0]["nombre"] if filas else None
