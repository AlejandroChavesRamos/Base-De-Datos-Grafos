"""Consultas Cypher sobre notificaciones."""
from app.database import db


def listar(uid: str):
    return db.leer(
        """
        MATCH (n:Notificacion)-[:PARA]->(:Usuario {id: $id})
        RETURN n{.*} AS n
        ORDER BY n.fecha DESC
        """,
        id=uid,
    )


def marcar_leida(nid: str, uid: str):
    """Marca como leida y devuelve el enlace de la notificacion (o None si no es del usuario)."""
    filas = db.escribir(
        """
        MATCH (n:Notificacion {id: $nid})-[:PARA]->(:Usuario {id: $uid})
        SET n.leida = true
        RETURN n.enlace AS enlace
        """,
        nid=nid, uid=uid,
    )
    return filas[0]["enlace"] if filas else None


def marcar_todas(uid: str):
    db.escribir(
        "MATCH (n:Notificacion {leida: false})-[:PARA]->(:Usuario {id: $uid}) SET n.leida = true",
        uid=uid,
    )
