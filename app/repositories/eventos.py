"""Registro de auditoria: nodos (:Evento)-[:SOBRE]->(:Cuenta). Nunca se guardan contrasenas."""
import uuid

from app.database import db


def registrar(cuenta_id, tipo: str, ip: str = "", detalle: str = ""):
    db.escribir(
        """
        CREATE (e:Evento {id: $id, tipo: $tipo, fecha: datetime(), ip: $ip, detalle: $detalle})
        WITH e
        OPTIONAL MATCH (c:Cuenta {id: $cuenta_id})
        FOREACH (_ IN CASE WHEN c IS NULL THEN [] ELSE [1] END | CREATE (e)-[:SOBRE]->(c))
        """,
        id=uuid.uuid4().hex, tipo=tipo, ip=ip, detalle=detalle, cuenta_id=cuenta_id,
    )


def recientes(limite: int = 50):
    return db.leer(
        """
        MATCH (e:Evento)
        OPTIONAL MATCH (e)-[:SOBRE]->(c:Cuenta)
        RETURN e{.tipo, .fecha, .ip, .detalle} AS evento, c.email AS email
        ORDER BY e.fecha DESC
        LIMIT $limite
        """,
        limite=limite,
    )
