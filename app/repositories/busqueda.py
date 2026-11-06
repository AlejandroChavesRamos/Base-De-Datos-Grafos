"""Busqueda simple por texto en usuarios, empresas y ofertas."""
from app.database import db


def buscar(q: str, limite: int = 10):
    q = q.strip()
    personas = db.leer(
        """
        MATCH (u:Usuario)
        WHERE toLower(u.nombre + ' ' + u.apellido + ' ' + coalesce(u.titular, ''))
              CONTAINS toLower($q)
        RETURN u{.id, .nombre, .apellido, .titular, .ciudad} AS usuario
        ORDER BY u.nombre LIMIT $limite
        """,
        q=q, limite=limite,
    )
    empresas = db.leer(
        """
        MATCH (e:Empresa)
        WHERE toLower(e.nombre + ' ' + coalesce(e.sector, '')) CONTAINS toLower($q)
        RETURN e{.id, .nombre, .sector, .ciudad} AS empresa
        ORDER BY e.nombre LIMIT $limite
        """,
        q=q, limite=limite,
    )
    ofertas = db.leer(
        """
        MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta)
        WHERE o.estado <> 'borrador' AND toLower(o.titulo) CONTAINS toLower($q)
        RETURN o{.id, .titulo, .estado, .ciudad} AS oferta, e.nombre AS empresa
        ORDER BY o.titulo LIMIT $limite
        """,
        q=q, limite=limite,
    )
    return {"personas": personas, "empresas": empresas, "ofertas": ofertas}
