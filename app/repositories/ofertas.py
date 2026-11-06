"""Consultas Cypher sobre ofertas laborales."""
from app.database import db


def recomendadas(uid: str, limite: int = 50):
    """Ofertas abiertas ordenadas por afinidad (habilidades que cumple el usuario
    con el nivel minimo) y por contactos que trabajan en la empresa."""
    return db.leer(
        """
        MATCH (u:Usuario {id: $id})
        MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {estado: 'abierta'})
        OPTIONAL MATCH (o)-[req:REQUIERE]->(h:Habilidad)
        OPTIONAL MATCH (u)-[tu:TIENE_HABILIDAD]->(h)
        WITH u, e, o, count(h) AS total_req,
             sum(CASE WHEN tu IS NOT NULL AND tu.nivel >= req.nivel_minimo THEN 1 ELSE 0 END) AS cumple,
             collect(CASE WHEN tu IS NOT NULL AND tu.nivel >= req.nivel_minimo THEN h.nombre END) AS cumplidas,
             collect(CASE WHEN tu IS NULL OR tu.nivel < req.nivel_minimo THEN h.nombre END) AS faltan
        RETURN o{.*} AS oferta,
               e{.id, .nombre, .sector} AS empresa,
               total_req, cumple, cumplidas, faltan,
               CASE WHEN total_req = 0 THEN 0
                    ELSE toInteger(round(100.0 * cumple / total_req)) END AS afinidad,
               [(u)-[:CONECTA_CON]-(c:Usuario)-[:TRABAJA_EN {actual: true}]->(e)
                  | c{.id, .nombre, .apellido}] AS contactos,
               [(u)-[p:POSTULA_A]->(o) | p.estado][0] AS postulacion
        ORDER BY afinidad DESC, size(contactos) DESC, o.fecha_publicacion DESC
        LIMIT $limite
        """,
        id=uid, limite=limite,
    )


def detalle(oid: str, uid: str):
    filas = db.leer(
        """
        MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {id: $oid})
        WHERE o.estado <> 'borrador'
        MATCH (u:Usuario {id: $uid})
        RETURN o{.*} AS oferta,
               e{.id, .nombre, .sector, .ciudad} AS empresa,
               [(o)-[r:REQUIERE]->(h:Habilidad) |
                   {habilidad: h.nombre, nivel_minimo: r.nivel_minimo,
                    obligatoria: r.obligatoria,
                    tu_nivel: [(u)-[t:TIENE_HABILIDAD]->(h) | t.nivel][0]}] AS requisitos,
               [(u)-[:CONECTA_CON]-(c:Usuario)-[:TRABAJA_EN {actual: true}]->(e)
                  | c{.id, .nombre, .apellido, .titular}] AS contactos,
               [(u)-[p:POSTULA_A]->(o) | {estado: p.estado, fecha: p.fecha}][0] AS postulacion,
               COUNT { (:Usuario)-[:POSTULA_A]->(o) } AS n_postulantes
        """,
        oid=oid, uid=uid,
    )
    return filas[0] if filas else None


def mis_postulaciones(uid: str):
    return db.leer(
        """
        MATCH (:Usuario {id: $id})-[p:POSTULA_A]->(o:Oferta)<-[:PUBLICA]-(e:Empresa)
        RETURN o{.id, .titulo} AS oferta, e.nombre AS empresa, p.estado AS estado, p.fecha AS fecha
        ORDER BY p.fecha DESC
        """,
        id=uid,
    )


def demanda_habilidades(limite: int = 5):
    return db.leer(
        """
        MATCH (:Oferta {estado: 'abierta'})-[:REQUIERE]->(h:Habilidad)
        RETURN h.nombre AS habilidad, count(*) AS ofertas
        ORDER BY ofertas DESC, habilidad
        LIMIT $limite
        """,
        limite=limite,
    )


# =====================================================================
#  Fase 6: gestion de ofertas (empresa) y postulaciones (persona)
# =====================================================================
import uuid  # noqa: E402


def empresa_de(oid: str):
    filas = db.leer("MATCH (e:Empresa)-[:PUBLICA]->(:Oferta {id: $oid}) RETURN e.id AS id", oid=oid)
    return filas[0]["id"] if filas else None


def crear(eid: str, publicada_por: str, d: dict):
    """Nace como 'borrador': se publica cuando ya tiene requisitos."""
    oid = uuid.uuid4().hex
    filas = db.escribir(
        """
        MATCH (e:Empresa {id: $eid})
        CREATE (o:Oferta {id: $oid, titulo: $titulo, descripcion: $descripcion, modalidad: $modalidad,
                          ciudad: $ciudad, salario_min: $salario_min, salario_max: $salario_max,
                          estado: 'borrador', fecha_publicacion: date(), fecha_cierre: date($fecha_cierre)})
        CREATE (e)-[:PUBLICA {fecha: date(), publicada_por: $publicada_por}]->(o)
        RETURN o.id AS id
        """,
        eid=eid, oid=oid, publicada_por=publicada_por, **d,
    )
    return filas[0]["id"] if filas else None


def actualizar(oid: str, d: dict) -> bool:
    filas = db.escribir(
        """
        MATCH (o:Oferta {id: $oid})
        SET o.titulo = $titulo, o.descripcion = $descripcion, o.modalidad = $modalidad,
            o.ciudad = $ciudad, o.salario_min = $salario_min, o.salario_max = $salario_max,
            o.fecha_cierre = date($fecha_cierre)
        RETURN o.id AS id
        """,
        oid=oid, **d,
    )
    return bool(filas)


def obtener_gestion(oid: str):
    filas = db.leer(
        """
        MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {id: $oid})
        RETURN o{.*} AS oferta, e{.id, .nombre} AS empresa,
               [(o)-[r:REQUIERE]->(h:Habilidad) |
                   {id: h.id, nombre: h.nombre, nivel_minimo: r.nivel_minimo, obligatoria: r.obligatoria}] AS requisitos
        """,
        oid=oid,
    )
    return filas[0] if filas else None


def gestion_de_empresa(eid: str):
    return db.leer(
        """
        MATCH (:Empresa {id: $eid})-[:PUBLICA]->(o:Oferta)
        RETURN o{.id, .titulo, .estado, .modalidad, .ciudad, .fecha_publicacion, .fecha_cierre} AS oferta,
               COUNT { (:Usuario)-[:POSTULA_A]->(o) } AS postulantes,
               COUNT { (o)-[:REQUIERE]->() } AS requisitos
        ORDER BY CASE o.estado WHEN 'abierta' THEN 0 WHEN 'borrador' THEN 1 ELSE 2 END,
                 o.fecha_publicacion DESC
        """,
        eid=eid,
    )


def guardar_requisito(oid: str, hid: str, nivel_minimo: int, obligatoria: bool) -> bool:
    """La relacion REQUIERE lleva el nivel minimo y si es obligatoria."""
    filas = db.escribir(
        """
        MATCH (o:Oferta {id: $oid}), (h:Habilidad {id: $hid})
        MERGE (o)-[r:REQUIERE]->(h)
        SET r.nivel_minimo = $nivel, r.obligatoria = $obligatoria
        RETURN h.nombre AS nombre
        """,
        oid=oid, hid=hid, nivel=nivel_minimo, obligatoria=obligatoria,
    )
    return bool(filas)


def quitar_requisito(oid: str, hid: str) -> bool:
    filas = db.escribir(
        """
        MATCH (:Oferta {id: $oid})-[r:REQUIERE]->(:Habilidad {id: $hid})
        DELETE r
        RETURN 1 AS ok
        """,
        oid=oid, hid=hid,
    )
    return bool(filas)


def publicar(oid: str):
    """Borrador -> abierta, y en la MISMA transaccion avisa a las personas afines:
    buscan empleo, no trabajan en la empresa, cumplen TODAS las habilidades obligatorias
    y al menos una requerida. Devuelve cuantas personas fueron notificadas, o None si
    no se pudo publicar (no es borrador o no tiene requisitos)."""
    filas = db.escribir(
        """
        MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {id: $oid})
        WHERE o.estado = 'borrador' AND COUNT { (o)-[:REQUIERE]->() } > 0
        SET o.estado = 'abierta', o.fecha_publicacion = date()
        WITH e, o
        OPTIONAL MATCH (u:Usuario)
        WHERE coalesce(u.buscando_empleo, false) = true
          AND NOT EXISTS { (u)-[:TRABAJA_EN {actual: true}]->(e) }
          AND NOT EXISTS {
                (o)-[r:REQUIERE {obligatoria: true}]->(h:Habilidad)
                WHERE NOT EXISTS { (u)-[t:TIENE_HABILIDAD]->(h) WHERE t.nivel >= r.nivel_minimo }
              }
          AND EXISTS {
                (o)-[r2:REQUIERE]->(h2:Habilidad)<-[t2:TIENE_HABILIDAD]-(u)
                WHERE t2.nivel >= r2.nivel_minimo
              }
        WITH e, o, collect(u) AS afines
        FOREACH (x IN afines |
            CREATE (:Notificacion {id: randomUUID(), tipo: 'oferta_afin',
                                   mensaje: 'Nueva oferta que coincide con tus habilidades: ' + o.titulo + ' en ' + e.nombre,
                                   leida: false, fecha: datetime(), enlace: '/empleos?oferta=' + o.id})-[:PARA]->(x))
        RETURN size(afines) AS notificados
        """,
        oid=oid,
    )
    return filas[0]["notificados"] if filas else None


def cambiar_estado(oid: str, permitidos: list[str], nuevo: str) -> bool:
    filas = db.escribir(
        """
        MATCH (o:Oferta {id: $oid})
        WHERE o.estado IN $permitidos
        SET o.estado = $nuevo
        RETURN o.id AS id
        """,
        oid=oid, permitidos=permitidos, nuevo=nuevo,
    )
    return bool(filas)


# ----- postulaciones -----
def postular(uid: str, oid: str):
    """Solo a ofertas abiertas y vigentes, y una sola vez por persona. Devuelve el titulo."""
    filas = db.escribir(
        """
        MATCH (u:Usuario {id: $uid}), (o:Oferta {id: $oid, estado: 'abierta'})
        WHERE o.fecha_cierre >= date() AND NOT EXISTS { (u)-[:POSTULA_A]->(o) }
        CREATE (u)-[:POSTULA_A {estado: 'enviada', fecha: date()}]->(o)
        RETURN o.titulo AS titulo
        """,
        uid=uid, oid=oid,
    )
    return filas[0]["titulo"] if filas else None


def retirar_postulacion(uid: str, oid: str) -> bool:
    filas = db.escribir(
        """
        MATCH (:Usuario {id: $uid})-[p:POSTULA_A]->(:Oferta {id: $oid})
        WHERE p.estado IN ['enviada', 'en_revision']
        DELETE p
        RETURN 1 AS ok
        """,
        uid=uid, oid=oid,
    )
    return bool(filas)


def postulantes(oid: str):
    """Postulantes de una oferta con su afinidad: requisitos cumplidos / requeridos."""
    return db.leer(
        """
        MATCH (o:Oferta {id: $oid})<-[p:POSTULA_A]-(u:Usuario)
        OPTIONAL MATCH (o)-[req:REQUIERE]->(h:Habilidad)
        OPTIONAL MATCH (u)-[tu:TIENE_HABILIDAD]->(h)
        WITH o, p, u, count(h) AS total,
             sum(CASE WHEN tu IS NOT NULL AND tu.nivel >= req.nivel_minimo THEN 1 ELSE 0 END) AS cumple,
             collect(CASE WHEN req.obligatoria AND (tu IS NULL OR tu.nivel < req.nivel_minimo)
                          THEN h.nombre END) AS faltan_obligatorias
        RETURN u{.id, .nombre, .apellido, .titular, .ciudad} AS usuario,
               p.estado AS estado, p.fecha AS fecha, total, cumple, faltan_obligatorias,
               CASE WHEN total = 0 THEN 0 ELSE toInteger(round(100.0 * cumple / total)) END AS afinidad,
               [(u)-[:CONECTA_CON]-(c:Usuario)-[:TRABAJA_EN {actual: true}]->(:Empresa)-[:PUBLICA]->(o)
                  | c.nombre + ' ' + c.apellido] AS conocidos
        ORDER BY afinidad DESC, p.fecha
        """,
        oid=oid,
    )


def cambiar_estado_postulacion(oid: str, uid: str, estado: str, texto: str) -> bool:
    """Cambia el estado y avisa a la persona en la misma transaccion."""
    filas = db.escribir(
        """
        MATCH (u:Usuario {id: $uid})-[p:POSTULA_A]->(o:Oferta {id: $oid})<-[:PUBLICA]-(e:Empresa)
        WHERE p.estado <> $estado
        SET p.estado = $estado
        CREATE (:Notificacion {id: randomUUID(), tipo: 'postulacion_estado',
                               mensaje: 'Tu postulación a "' + o.titulo + '" en ' + e.nombre + ' cambió a: ' + $texto,
                               leida: false, fecha: datetime(), enlace: '/empleos?oferta=' + o.id})-[:PARA]->(u)
        RETURN o.titulo AS titulo
        """,
        oid=oid, uid=uid, estado=estado, texto=texto,
    )
    return bool(filas)
