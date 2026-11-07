"""Escrituras sobre la red de contactos. Cada operacion es UNA transaccion: la
notificacion se crea en la misma sentencia que el cambio (equivale a un trigger)."""
from app.database import db


def solicitar(origen: str, destino: str, mensaje: str) -> bool:
    """Crea la invitacion si no es a si mismo, no son contactos y no hay otra pendiente.
    El SET bloquea a ambos: varios clics simultaneos se atienden en fila y no la duplican."""
    filas = db.escribir(
        """
        MATCH (a:Usuario {id: $a}), (b:Usuario {id: $b})
        WHERE a <> b AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(b) }
        SET a.actualizado = datetime(), b.actualizado = datetime()
        WITH a, b
        WHERE NOT EXISTS { (a)-[:CONECTA_CON]-(b) }
          AND NOT EXISTS { (a)-[:SOLICITA_CONEXION]-(b) }
        CREATE (a)-[:SOLICITA_CONEXION {fecha: date(), mensaje: $mensaje}]->(b)
        CREATE (:Notificacion {id: randomUUID(), tipo: 'conexion_solicitud', origen: a.id,
                               mensaje: a.nombre + ' ' + a.apellido + ' quiere conectar contigo.',
                               leida: false, fecha: datetime(), enlace: '/red'})-[:PARA]->(b)
        RETURN 1 AS ok
        """,
        a=origen, b=destino, mensaje=mensaje,
    )
    return bool(filas)


# Borra el aviso de una invitacion ya resuelta. Las anteriores a la propiedad 'origen'
# se reconocen por el nombre de quien la envio, con el que empieza el mensaje.
_BORRAR_AVISO = """
        WITH a, b
        OPTIONAL MATCH (n:Notificacion {tipo: 'conexion_solicitud'})-[:PARA]->(b)
        WHERE n.origen = a.id OR (n.origen IS NULL AND n.mensaje STARTS WITH a.nombre + ' ' + a.apellido + ' ')
        DETACH DELETE n
        WITH DISTINCT a, b
"""


def aceptar(receptor: str, solicitante: str) -> bool:
    """La invitacion se borra y nace CONECTA_CON (la relacion simetrica)."""
    filas = db.escribir(
        """
        MATCH (a:Usuario {id: $solicitante})-[s:SOLICITA_CONEXION]->(b:Usuario {id: $receptor})
        DELETE s
        """ + _BORRAR_AVISO + """
        WITH a, b
        WHERE NOT EXISTS { (a)-[:CONECTA_CON]-(b) }
        CREATE (a)-[:CONECTA_CON {desde: date()}]->(b)
        CREATE (:Notificacion {id: randomUUID(), tipo: 'conexion_aceptada',
                               mensaje: b.nombre + ' ' + b.apellido + ' aceptó tu invitación.',
                               leida: false, fecha: datetime(), enlace: '/perfil/' + b.id})-[:PARA]->(a)
        RETURN 1 AS ok
        """,
        solicitante=solicitante, receptor=receptor,
    )
    return bool(filas)


def retirar_solicitud(origen: str, destino: str) -> bool:
    """Sirve para ignorar (la borra el receptor) y para retirar (la borra quien la envio)."""
    filas = db.escribir(
        """
        MATCH (a:Usuario {id: $a})-[s:SOLICITA_CONEXION]->(b:Usuario {id: $b})
        DELETE s
        """ + _BORRAR_AVISO + """
        RETURN 1 AS ok
        """,
        a=origen, b=destino,
    )
    return bool(filas)


def eliminar(a: str, b: str) -> bool:
    filas = db.escribir(
        """
        MATCH (:Usuario {id: $a})-[c:CONECTA_CON]-(:Usuario {id: $b})
        DELETE c
        RETURN 1 AS ok
        """,
        a=a, b=b,
    )
    return bool(filas)
