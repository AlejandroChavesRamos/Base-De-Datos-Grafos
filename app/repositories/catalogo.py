"""Catalogo de habilidades (lo gestionan staff y admin)."""
from app.database import db


def listar():
    return db.leer(
        """
        MATCH (h:Habilidad)
        RETURN h{.id, .nombre, .categoria} AS habilidad,
               COUNT { (:Usuario)-[:TIENE_HABILIDAD]->(h) } AS usuarios,
               COUNT { (:Oferta)-[:REQUIERE]->(h) } AS ofertas,
               COUNT { (:Proyecto)-[:USA]->(h) } AS proyectos
        ORDER BY h.categoria, h.nombre
        """
    )


def obtener(hid: str):
    filas = db.leer(
        """
        MATCH (h:Habilidad {id: $id})
        RETURN h{.id, .nombre, .categoria} AS habilidad,
               COUNT { (:Usuario)-[:TIENE_HABILIDAD]->(h) } AS usuarios,
               COUNT { (:Oferta)-[:REQUIERE]->(h) } AS ofertas,
               COUNT { (:Proyecto)-[:USA]->(h) } AS proyectos
        """,
        id=hid,
    )
    return filas[0] if filas else None


def crear(nombre: str, categoria: str) -> bool:
    """No permite duplicados aunque cambien mayusculas ('python' = 'Python')."""
    filas = db.escribir(
        """
        WITH $nombre AS nombre
        WHERE NOT EXISTS { MATCH (x:Habilidad) WHERE toLower(x.nombre) = toLower(nombre) }
        CREATE (h:Habilidad {id: randomUUID(), nombre: nombre, categoria: $categoria})
        RETURN h.id AS id
        """,
        nombre=nombre, categoria=categoria,
    )
    return bool(filas)


def eliminar(hid: str) -> bool:
    """DETACH DELETE: tambien se borran los vinculos (habilidades de personas,
    requisitos de ofertas y tecnologias de proyectos)."""
    filas = db.escribir("MATCH (h:Habilidad {id: $id}) DETACH DELETE h RETURN 1 AS ok", id=hid)
    return bool(filas)
