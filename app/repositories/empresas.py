"""Consultas Cypher sobre empresas."""
from app.database import db


def obtener(eid: str, uid: str):
    base = db.leer(
        """
        MATCH (e:Empresa {id: $eid})
        RETURN e{.*} AS empresa,
               COUNT { (:Usuario)-[:TRABAJA_EN {actual: true}]->(e) } AS empleados
        """,
        eid=eid,
    )
    if not base:
        return None
    ofertas = db.leer(
        """
        MATCH (:Empresa {id: $eid})-[:PUBLICA]->(o:Oferta {estado: 'abierta'})
        RETURN o{.id, .titulo, .modalidad, .ciudad, .fecha_publicacion} AS oferta
        ORDER BY o.fecha_publicacion DESC
        """,
        eid=eid,
    )
    contactos = db.leer(
        """
        MATCH (:Usuario {id: $uid})-[:CONECTA_CON]-(c:Usuario)
              -[t:TRABAJA_EN {actual: true}]->(:Empresa {id: $eid})
        RETURN c{.id, .nombre, .apellido} AS usuario, t.cargo AS cargo
        """,
        uid=uid, eid=eid,
    )
    camino = db.leer(
        """
        MATCH (u:Usuario {id: $uid}), (e:Empresa {id: $eid})
        MATCH p = shortestPath((u)-[:CONECTA_CON|TRABAJA_EN*..8]-(e))
        WHERE all(r IN relationships(p) WHERE type(r) = 'CONECTA_CON' OR r.actual = true)
        RETURN [n IN nodes(p) | n.nombre] AS ruta, length(p) AS saltos
        """,
        uid=uid, eid=eid,
    )
    b = base[0]
    return {"empresa": b["empresa"], "empleados": b["empleados"], "ofertas": ofertas,
            "contactos": contactos, "camino": camino[0] if camino else None}


# =====================================================================
#  Fase 6: gestion de la empresa
# =====================================================================
def actualizar(eid: str, d: dict) -> bool:
    filas = db.escribir(
        """
        MATCH (e:Empresa {id: $eid})
        SET e.nombre = $nombre, e.sector = $sector, e.tamano = $tamano, e.ciudad = $ciudad,
            e.descripcion = $descripcion, e.sitio_web = $sitio_web
        RETURN e.id AS id
        """,
        eid=eid, **d,
    )
    return bool(filas)


def empleados(eid: str):
    return db.leer(
        """
        MATCH (u:Usuario)-[t:TRABAJA_EN {actual: true}]->(:Empresa {id: $eid})
        RETURN u{.id, .nombre, .apellido, .titular} AS usuario, t.rol AS rol, t.cargo AS cargo
        ORDER BY u.nombre, u.apellido
        """,
        eid=eid,
    )


def cambiar_rol(eid: str, uid: str, rol: str) -> bool:
    """Asigna 'rrhh' o 'trabajador' a un empleado VIGENTE y le avisa."""
    filas = db.escribir(
        """
        MATCH (u:Usuario {id: $uid})-[t:TRABAJA_EN {actual: true}]->(e:Empresa {id: $eid})
        WHERE t.rol <> $rol
        SET t.rol = $rol
        CREATE (:Notificacion {id: randomUUID(), tipo: 'rol_empresa',
                               mensaje: CASE WHEN $rol = 'rrhh'
                                             THEN 'Ahora puedes gestionar las ofertas de ' + e.nombre + ' (RR. HH.).'
                                             ELSE 'Ya no gestionas las ofertas de ' + e.nombre + '.' END,
                               leida: false, fecha: datetime(), enlace: '/'})-[:PARA]->(u)
        RETURN u.nombre AS nombre
        """,
        eid=eid, uid=uid, rol=rol,
    )
    return bool(filas)
