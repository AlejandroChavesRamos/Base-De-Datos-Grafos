"""Consultas Cypher sobre usuarios (perfil, relaciones y similitud)."""
from app.database import db


def resumen(uid: str):
    """Datos minimos del usuario para la barra superior y las tarjetas laterales."""
    filas = db.leer(
        """
        MATCH (u:Usuario {id: $id})
        OPTIONAL MATCH (u)-[t:TRABAJA_EN {actual: true}]->(e:Empresa)
        RETURN u{.*} AS u,
               e{.id, .nombre} AS empresa,
               t.cargo AS cargo, t.rol AS rol_empresa,
               COUNT { (u)-[:CONECTA_CON]-(:Usuario) } AS conexiones,
               COUNT { (u)-[:POSTULA_A]->(:Oferta) } AS postulaciones,
               COUNT { (:Notificacion {leida: false})-[:PARA]->(u) } AS sin_leer,
               COUNT { (:Usuario)-[:SOLICITA_CONEXION]->(u) } AS solicitudes
        """,
        id=uid,
    )
    if not filas:
        return None
    f = filas[0]
    return {**f["u"], "empresa": f["empresa"], "cargo": f["cargo"], "rol_empresa": f["rol_empresa"],
            "conexiones": f["conexiones"], "postulaciones": f["postulaciones"],
            "sin_leer": f["sin_leer"], "solicitudes": f["solicitudes"]}


def perfil_completo(uid: str):
    base = db.leer(
        """
        MATCH (u:Usuario {id: $id})
        OPTIONAL MATCH (u)-[t:TRABAJA_EN {actual: true}]->(e:Empresa)
        RETURN u{.*} AS usuario, e{.id, .nombre} AS empresa, t.cargo AS cargo,
               COUNT { (u)-[:CONECTA_CON]-(:Usuario) } AS conexiones
        """,
        id=uid,
    )
    if not base:
        return None
    experiencia = db.leer(
        """
        MATCH (:Usuario {id: $id})-[t:TRABAJA_EN]->(e:Empresa)
        RETURN e{.id, .nombre, .sector} AS empresa, t.cargo AS cargo, t.rol AS rol,
               t.desde AS desde, toString(t.desde) AS desde_iso, t.hasta AS hasta, t.actual AS actual
        ORDER BY t.actual DESC, t.desde DESC
        """,
        id=uid,
    )
    habilidades = db.leer(
        """
        MATCH (:Usuario {id: $id})-[r:TIENE_HABILIDAD]->(h:Habilidad)
        RETURN h{.id, .nombre, .categoria} AS habilidad, r.nivel AS nivel, r.anios AS anios
        ORDER BY r.nivel DESC, h.nombre
        """,
        id=uid,
    )
    proyectos = db.leer(
        """
        MATCH (:Usuario {id: $id})-[r:PARTICIPA_EN]->(p:Proyecto)
        OPTIONAL MATCH (p)-[:PERTENECE_A]->(e:Empresa)
        RETURN p{.id, .nombre, .descripcion, .estado} AS proyecto, r.rol AS rol,
               e.nombre AS empresa,
               [(p)-[:USA]->(h:Habilidad) | h.nombre] AS tecnologias
        ORDER BY p.estado, p.nombre
        """,
        id=uid,
    )
    b = base[0]
    return {"usuario": b["usuario"], "empresa": b["empresa"], "cargo": b["cargo"],
            "conexiones": b["conexiones"], "experiencia": experiencia,
            "habilidades": habilidades, "proyectos": proyectos}


def estado_relacion(a: str, b: str) -> str:
    """Relacion de 'a' con 'b': conectado | enviada | recibida | ninguna."""
    filas = db.leer(
        """
        MATCH (a:Usuario {id: $a}), (b:Usuario {id: $b})
        RETURN CASE
                 WHEN EXISTS { (a)-[:CONECTA_CON]-(b) } THEN 'conectado'
                 WHEN EXISTS { (a)-[:SOLICITA_CONEXION]->(b) } THEN 'enviada'
                 WHEN EXISTS { (b)-[:SOLICITA_CONEXION]->(a) } THEN 'recibida'
                 ELSE 'ninguna'
               END AS estado
        """,
        a=a, b=b,
    )
    return filas[0]["estado"] if filas else "ninguna"


def ruta(a: str, b: str):
    """Camino mas corto entre dos usuarios por CONECTA_CON (grado de conexion)."""
    filas = db.leer(
        """
        MATCH (a:Usuario {id: $a}), (b:Usuario {id: $b})
        MATCH p = shortestPath((a)-[:CONECTA_CON*..6]-(b))
        RETURN [n IN nodes(p) | n{.id, .nombre, .apellido}] AS ruta, length(p) AS saltos
        """,
        a=a, b=b,
    )
    return filas[0] if filas else None


def contactos_en_comun(a: str, b: str):
    return db.leer(
        """
        MATCH (:Usuario {id: $a})-[:CONECTA_CON]-(c:Usuario)-[:CONECTA_CON]-(:Usuario {id: $b})
        RETURN DISTINCT c{.id, .nombre, .apellido, .titular} AS usuario
        ORDER BY usuario.nombre
        """,
        a=a, b=b,
    )


def similares(uid: str, limite: int = 4):
    """Usuarios con habilidades parecidas (similitud de Jaccard)."""
    return db.leer(
        """
        MATCH (a:Usuario {id: $id})-[:TIENE_HABILIDAD]->(h:Habilidad)
        WITH a, collect(h) AS hab_a
        MATCH (b:Usuario) WHERE b <> a
        MATCH (b)-[:TIENE_HABILIDAD]->(hb:Habilidad)
        WITH a, hab_a, b, collect(hb) AS hab_b
        WITH b, hab_a, hab_b, [x IN hab_a WHERE x IN hab_b] AS comunes
        WHERE size(comunes) > 0
        RETURN b{.id, .nombre, .apellido, .titular} AS usuario,
               [x IN comunes | x.nombre] AS habilidades_comunes,
               round(1.0 * size(comunes) / (size(hab_a) + size(hab_b) - size(comunes)), 2) AS similitud
        ORDER BY similitud DESC, size(comunes) DESC
        LIMIT $limite
        """,
        id=uid, limite=limite,
    )
