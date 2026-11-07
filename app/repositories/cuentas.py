"""Consultas Cypher sobre cuentas de acceso (:Cuenta)."""
from neo4j.exceptions import ConstraintError  # noqa: F401  (se captura en el servicio)

from app.database import db


def por_email(email: str):
    filas = db.leer(
        """
        MATCH (c:Cuenta {email: $email})
        RETURN c.id AS id, c.password_hash AS password_hash,
               coalesce(c.activa, false) AS activa,
               c.bloqueado_hasta IS NOT NULL AND c.bloqueado_hasta > datetime() AS bloqueada
        """,
        email=email,
    )
    return filas[0] if filas else None


def registrar_fallo(cuenta_id: str, maximo: int, minutos: int):
    """Suma un intento fallido; al llegar al maximo bloquea la cuenta temporalmente.
    Si un bloqueo anterior ya vencio, el conteo vuelve a empezar en 1."""
    filas = db.escribir(
        """
        MATCH (c:Cuenta {id: $id})
        WITH c, CASE WHEN c.bloqueado_hasta IS NOT NULL AND c.bloqueado_hasta <= datetime()
                     THEN 1 ELSE coalesce(c.intentos_fallidos, 0) + 1 END AS n
        SET c.intentos_fallidos = n,
            c.bloqueado_hasta = CASE
                WHEN n >= $maximo THEN datetime() + duration({minutes: $minutos})
                WHEN c.bloqueado_hasta IS NOT NULL AND c.bloqueado_hasta <= datetime() THEN null
                ELSE c.bloqueado_hasta END
        RETURN n AS intentos, n >= $maximo AS bloqueada
        """,
        id=cuenta_id, maximo=maximo, minutos=minutos,
    )
    return filas[0]


def reiniciar_intentos(cuenta_id: str):
    db.escribir(
        "MATCH (c:Cuenta {id: $id}) SET c.intentos_fallidos = 0, c.bloqueado_hasta = null",
        id=cuenta_id,
    )


def actualizar_hash(cuenta_id: str, nuevo_hash: str):
    db.escribir(
        "MATCH (c:Cuenta {id: $id}) SET c.password_hash = $hash",
        id=cuenta_id, hash=nuevo_hash,
    )


def crear_persona(d: dict):
    """Cuenta + Usuario + rol, en una sola transaccion (o se crea todo o nada)."""
    filas = db.escribir(
        """
        MATCH (r:Rol {nombre: 'persona'})
        CREATE (c:Cuenta {id: $cuenta_id, email: $email, password_hash: $hash, tipo: 'persona',
                          activa: true, email_verificado: false, intentos_fallidos: 0,
                          creada_en: datetime()})
        CREATE (u:Usuario {id: $perfil_id, nombre: $nombre, apellido: $apellido, titular: $titular,
                           ciudad: $ciudad, resumen: '', experiencia_anios: 0, buscando_empleo: true})
        CREATE (c)-[:TIENE_PERFIL]->(u)
        CREATE (c)-[:TIENE_ROL]->(r)
        CREATE (:Notificacion {id: randomUUID(), tipo: 'bienvenida', leida: false, fecha: datetime(),
                               mensaje: 'Bienvenido a LinkedUn. Completa tu perfil para recibir empleos a tu medida.',
                               enlace: '/perfil/editar'})-[:PARA]->(u)
        RETURN c.id AS cuenta_id
        """,
        **d,
    )
    return filas[0]["cuenta_id"] if filas else None


def crear_empresa(d: dict):
    filas = db.escribir(
        """
        MATCH (r:Rol {nombre: 'empresa'})
        CREATE (c:Cuenta {id: $cuenta_id, email: $email, password_hash: $hash, tipo: 'empresa',
                          activa: true, email_verificado: false, intentos_fallidos: 0,
                          creada_en: datetime()})
        CREATE (e:Empresa {id: $perfil_id, nombre: $nombre, sector: $sector, tamano: $tamano,
                           ciudad: $ciudad, descripcion: $descripcion, sitio_web: $sitio_web})
        CREATE (c)-[:TIENE_PERFIL]->(e)
        CREATE (c)-[:TIENE_ROL]->(r)
        RETURN c.id AS cuenta_id
        """,
        **d,
    )
    return filas[0]["cuenta_id"] if filas else None


# ----- Gestion (panel de staff / admin) -----
def listar(limite: int = 100):
    return db.leer(
        """
        MATCH (c:Cuenta)
        OPTIONAL MATCH (c)-[:TIENE_PERFIL]->(p)
        RETURN c.id AS id, c.email AS email, c.tipo AS tipo, coalesce(c.activa, false) AS activa,
               coalesce(c.intentos_fallidos, 0) AS intentos,
               c.bloqueado_hasta IS NOT NULL AND c.bloqueado_hasta > datetime() AS bloqueo_temporal,
               coalesce(p.nombre + ' ' + p.apellido, p.nombre, '-') AS perfil
        ORDER BY c.tipo, c.email
        LIMIT $limite
        """,
        limite=limite,
    )


def tipo_de(cuenta_id: str):
    filas = db.leer("MATCH (c:Cuenta {id: $id}) RETURN c.tipo AS tipo, c.email AS email", id=cuenta_id)
    return filas[0] if filas else None


def cambiar_activa(cuenta_id: str, activa: bool):
    db.escribir(
        """
        MATCH (c:Cuenta {id: $id})
        SET c.activa = $activa, c.intentos_fallidos = 0, c.bloqueado_hasta = null
        """,
        id=cuenta_id, activa=activa,
    )


# =====================================================================
#  Fase 6: gestion de la propia cuenta
# =====================================================================
def por_id(cuenta_id: str):
    filas = db.leer(
        """
        MATCH (c:Cuenta {id: $id})
        RETURN c.id AS id, c.password_hash AS password_hash,
               c.bloqueado_hasta IS NOT NULL AND c.bloqueado_hasta > datetime() AS bloqueada
        """,
        id=cuenta_id,
    )
    return filas[0] if filas else None


def eliminar_persona(cuenta_id: str, perfil_id: str):
    """Borra cuenta, perfil, notificaciones y sesiones. Los eventos de auditoria
    permanecen, pero sin vinculo con la cuenta."""
    db.escribir(
        """
        MATCH (c:Cuenta {id: $cid})-[:TIENE_PERFIL]->(u:Usuario {id: $pid})
        OPTIONAL MATCH (n:Notificacion)-[:PARA]->(u)
        WITH c, u, collect(n) AS ns
        OPTIONAL MATCH (s:Sesion)-[:DE]->(c)
        WITH c, u, ns, collect(s) AS ss
        FOREACH (x IN ns | DETACH DELETE x)
        FOREACH (x IN ss | DETACH DELETE x)
        DETACH DELETE u, c
        """,
        cid=cuenta_id, pid=perfil_id,
    )


def eliminar_empresa(cuenta_id: str, perfil_id: str):
    """Borra la cuenta y las ofertas de la empresa, con sus postulaciones, requisitos y
    avisos. Si alguien trabajo alli, el historial de esa persona es suyo: la empresa queda
    como :EmpresaArchivada (invisible para el resto del sitio) y sus empleos, cerrados."""
    db.escribir(
        """
        MATCH (c:Cuenta {id: $cid})-[:TIENE_PERFIL]->(e:Empresa {id: $pid})
        OPTIONAL MATCH (e)-[:PUBLICA]->(o:Oferta)
        WITH c, e, collect(o) AS os, collect('/empleos?oferta=' + o.id) AS enlaces
        OPTIONAL MATCH (n:Notificacion) WHERE n.enlace IN enlaces
        WITH c, e, os, collect(n) AS ns
        OPTIONAL MATCH (s:Sesion)-[:DE]->(c)
        WITH c, e, os, ns, collect(s) AS ss
        OPTIONAL MATCH (:Proyecto)-[p:PERTENECE_A]->(e)
        WITH c, e, os, ns, ss, collect(p) AS proyectos
        OPTIONAL MATCH (:Usuario)-[t:TRABAJA_EN]->(e)
        WITH c, e, os, ns, ss, proyectos, collect(t) AS empleos
        FOREACH (x IN os + ns + ss | DETACH DELETE x)
        FOREACH (x IN proyectos | DELETE x)
        FOREACH (x IN empleos | SET x.actual = false, x.hasta = coalesce(x.hasta, date()), x.rol = 'trabajador')
        FOREACH (_ IN CASE WHEN size(empleos) > 0 THEN [1] ELSE [] END | REMOVE e:Empresa SET e:EmpresaArchivada)
        FOREACH (_ IN CASE WHEN size(empleos) = 0 THEN [1] ELSE [] END | DETACH DELETE e)
        DETACH DELETE c
        """,
        cid=cuenta_id, pid=perfil_id,
    )
