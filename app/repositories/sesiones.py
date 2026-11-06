"""Consultas Cypher sobre sesiones (:Sesion). Solo se guarda el HASH del token."""
import uuid

from app import config
from app.database import db


def crear(cuenta_id: str, token_hash: str, csrf_token: str, ip: str, user_agent: str):
    db.escribir(
        """
        MATCH (c:Cuenta {id: $cuenta_id})
        CREATE (s:Sesion {id: $id, token_hash: $token_hash, csrf_token: $csrf,
                          creada_en: datetime(),
                          expira_en: datetime() + duration({hours: $horas}),
                          ultima_actividad: datetime(),
                          ip: $ip, user_agent: $ua, revocada: false})
        CREATE (s)-[:DE]->(c)
        """,
        cuenta_id=cuenta_id, id=uuid.uuid4().hex, token_hash=token_hash, csrf=csrf_token,
        horas=config.SESION_HORAS, ip=ip, ua=user_agent,
    )


def validar(token_hash: str):
    """Una sola consulta: valida la sesion y trae cuenta, perfil, roles y permisos.
    Devuelve None si la sesion no existe, esta revocada, expiro, o la cuenta esta inactiva."""
    filas = db.leer(
        """
        MATCH (s:Sesion {token_hash: $h})-[:DE]->(c:Cuenta)
        WHERE s.revocada = false
          AND s.expira_en > datetime()
          AND s.ultima_actividad > datetime() - duration({minutes: $inactividad})
          AND c.activa = true
        OPTIONAL MATCH (c)-[:TIENE_PERFIL]->(p)
        OPTIONAL MATCH (c)-[:TIENE_ROL]->(r:Rol)
        OPTIONAL MATCH (r)-[:PERMITE]->(perm:Permiso)
        RETURN s.id AS sesion_id, s.csrf_token AS csrf_token,
               s.ultima_actividad < datetime() - duration({minutes: 5}) AS refrescar,
               c.id AS cuenta_id, c.email AS email, c.tipo AS tipo,
               p.id AS perfil_id, p.nombre AS perfil_nombre,
               collect(DISTINCT r.nombre) AS roles,
               collect(DISTINCT perm.codigo) AS permisos
        """,
        h=token_hash, inactividad=config.SESION_INACTIVIDAD_MIN,
    )
    if not filas:
        return None
    f = filas[0]
    if f["refrescar"]:  # se actualiza como maximo cada 5 minutos para no escribir en cada peticion
        db.escribir("MATCH (s:Sesion {id: $id}) SET s.ultima_actividad = datetime()", id=f["sesion_id"])
    return f


def revocar(token_hash: str):
    db.escribir("MATCH (s:Sesion {token_hash: $h}) SET s.revocada = true", h=token_hash)


def revocar_de_cuenta(cuenta_id: str):
    db.escribir(
        "MATCH (s:Sesion)-[:DE]->(:Cuenta {id: $id}) WHERE s.revocada = false SET s.revocada = true",
        id=cuenta_id,
    )


def limpiar():
    """Borra sesiones vencidas o revocadas hace mas de un dia."""
    db.escribir(
        """
        MATCH (s:Sesion)
        WHERE s.expira_en < datetime() - duration({days: 1})
           OR (s.revocada = true AND s.ultima_actividad < datetime() - duration({days: 1}))
        DETACH DELETE s
        """
    )


def revocar_otras(cuenta_id: str, token_hash_actual: str):
    """Cierra todas las sesiones de la cuenta MENOS la actual (p. ej. tras cambiar la contrasena)."""
    db.escribir(
        """
        MATCH (s:Sesion)-[:DE]->(:Cuenta {id: $id})
        WHERE s.token_hash <> $h AND s.revocada = false
        SET s.revocada = true
        """,
        id=cuenta_id, h=token_hash_actual,
    )
