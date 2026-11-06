"""Escrituras sobre el perfil de una persona: datos, habilidades, experiencia y proyectos."""
import uuid

from app.database import db


# ------------------------------------------------------------------ datos
def actualizar(uid: str, d: dict) -> bool:
    filas = db.escribir(
        """
        MATCH (u:Usuario {id: $id})
        SET u.nombre = $nombre, u.apellido = $apellido, u.titular = $titular,
            u.ciudad = $ciudad, u.resumen = $resumen,
            u.experiencia_anios = $experiencia_anios, u.buscando_empleo = $buscando_empleo
        RETURN u.id AS id
        """,
        id=uid, **d,
    )
    return bool(filas)


def catalogo_habilidades():
    return db.leer(
        "MATCH (h:Habilidad) RETURN h.id AS id, h.nombre AS nombre, h.categoria AS categoria "
        "ORDER BY h.categoria, h.nombre"
    )


def lista_empresas():
    return db.leer("MATCH (e:Empresa) RETURN e.id AS id, e.nombre AS nombre ORDER BY e.nombre")


# ------------------------------------------------------------ habilidades
def guardar_habilidad(uid: str, hid: str, nivel: int, anios: int) -> bool:
    """MERGE: si ya la tenia, actualiza nivel y anios; si no, la crea."""
    filas = db.escribir(
        """
        MATCH (u:Usuario {id: $uid}), (h:Habilidad {id: $hid})
        MERGE (u)-[r:TIENE_HABILIDAD]->(h)
        SET r.nivel = $nivel, r.anios = $anios
        RETURN h.nombre AS nombre
        """,
        uid=uid, hid=hid, nivel=nivel, anios=anios,
    )
    return bool(filas)


def quitar_habilidad(uid: str, hid: str) -> bool:
    filas = db.escribir(
        """
        MATCH (:Usuario {id: $uid})-[r:TIENE_HABILIDAD]->(:Habilidad {id: $hid})
        DELETE r
        RETURN 1 AS ok
        """,
        uid=uid, hid=hid,
    )
    return bool(filas)


# ------------------------------------------------------------ experiencia
def agregar_experiencia(uid: str, d: dict) -> bool:
    """Regla del modelo: solo UN empleo vigente. Si el nuevo es vigente, el anterior
    se cierra (actual=false, hasta=desde del nuevo) en la MISMA transaccion."""
    filas = db.escribir(
        """
        MATCH (u:Usuario {id: $uid}), (e:Empresa {id: $empresa_id})
        OPTIONAL MATCH (u)-[prev:TRABAJA_EN {actual: true}]->()
        WITH u, e, collect(prev) AS previos
        FOREACH (p IN CASE WHEN $actual THEN previos ELSE [] END |
                 SET p.actual = false, p.hasta = date($desde))
        CREATE (u)-[:TRABAJA_EN {rol: 'trabajador', cargo: $cargo, desde: date($desde),
                                 hasta: CASE WHEN $actual THEN null ELSE date($hasta) END,
                                 actual: $actual}]->(e)
        RETURN e.nombre AS empresa
        """,
        uid=uid, **d,
    )
    return bool(filas)


def quitar_experiencia(uid: str, empresa_id: str, desde: str) -> bool:
    filas = db.escribir(
        """
        MATCH (:Usuario {id: $uid})-[t:TRABAJA_EN]->(:Empresa {id: $eid})
        WHERE t.desde = date($desde)
        DELETE t
        RETURN 1 AS ok
        """,
        uid=uid, eid=empresa_id, desde=desde,
    )
    return bool(filas)


# -------------------------------------------------------------- proyectos
def listar_proyectos(uid: str):
    return db.leer(
        """
        MATCH (p:Proyecto)
        OPTIONAL MATCH (p)-[:PERTENECE_A]->(e:Empresa)
        RETURN p{.id, .nombre, .descripcion, .estado, .fecha_inicio} AS proyecto,
               e.nombre AS empresa,
               [(p)-[:USA]->(h:Habilidad) | h.nombre] AS tecnologias,
               COUNT { (:Usuario)-[:PARTICIPA_EN]->(p) } AS miembros,
               [(:Usuario {id: $uid})-[r:PARTICIPA_EN]->(p) | r.rol][0] AS mi_rol
        ORDER BY p.estado, p.nombre
        """,
        uid=uid,
    )


def crear_proyecto(uid: str, d: dict, techs: list[str]) -> bool:
    filas = db.escribir(
        """
        MATCH (u:Usuario {id: $uid})
        CREATE (p:Proyecto {id: $pid, nombre: $nombre, descripcion: $descripcion, estado: $estado,
                            fecha_inicio: date($fecha_inicio),
                            fecha_fin: CASE WHEN $fecha_fin IS NULL THEN null ELSE date($fecha_fin) END})
        CREATE (u)-[:PARTICIPA_EN {rol: $rol, desde: date($fecha_inicio)}]->(p)
        WITH u, p
        OPTIONAL MATCH (u)-[:TRABAJA_EN {actual: true}]->(e:Empresa) WHERE $con_empresa
        FOREACH (_ IN CASE WHEN e IS NULL THEN [] ELSE [1] END | CREATE (p)-[:PERTENECE_A]->(e))
        WITH p
        UNWIND $techs AS tid
        MATCH (h:Habilidad {id: tid})
        CREATE (p)-[:USA]->(h)
        RETURN count(h) AS tecnologias
        """,
        uid=uid, pid=uuid.uuid4().hex, techs=techs, **d,
    )
    return True if filas else _proyecto_sin_tecnologias(uid, d)


def _proyecto_sin_tecnologias(uid, d):
    """El UNWIND anterior no devuelve filas cuando la lista de tecnologias esta vacia,
    pero el proyecto ya se creo. Se confirma buscandolo."""
    filas = db.leer(
        "MATCH (:Usuario {id: $uid})-[:PARTICIPA_EN]->(p:Proyecto {nombre: $nombre}) RETURN count(p) AS n",
        uid=uid, nombre=d["nombre"],
    )
    return bool(filas and filas[0]["n"])


def unirse_proyecto(uid: str, pid: str, rol: str) -> bool:
    filas = db.escribir(
        """
        MATCH (u:Usuario {id: $uid}), (p:Proyecto {id: $pid})
        WHERE NOT EXISTS { (u)-[:PARTICIPA_EN]->(p) }
        CREATE (u)-[:PARTICIPA_EN {rol: $rol, desde: date()}]->(p)
        RETURN 1 AS ok
        """,
        uid=uid, pid=pid, rol=rol,
    )
    return bool(filas)


def salir_proyecto(uid: str, pid: str) -> bool:
    filas = db.escribir(
        """
        MATCH (:Usuario {id: $uid})-[r:PARTICIPA_EN]->(:Proyecto {id: $pid})
        DELETE r
        RETURN 1 AS ok
        """,
        uid=uid, pid=pid,
    )
    return bool(filas)
