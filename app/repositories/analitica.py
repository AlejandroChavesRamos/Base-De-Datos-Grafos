"""Analitica de la red: metricas calculadas con Graph Data Science (GDS) y su lectura.

El calculo (recalcular) escribe tres propiedades en cada Usuario:
    pagerank        influencia (importa QUIEN te conecta, no solo cuantos)
    comunidad       grupo detectado con Louvain
    intermediacion  cuanto "puentea" entre grupos (betweenness)
y un nodo (:Metricas {id: 'red'}) con la fecha del ultimo calculo.
Las lecturas ocultan las cuentas desactivadas, como el resto de la aplicacion.
"""
import uuid

from neo4j.exceptions import Neo4jError

from app.database import db

_VISIBLE = "NOT EXISTS {{ (:Cuenta {{activa: false}})-[:TIENE_PERFIL]->({v}) }}"


def _activa(v: str) -> str:
    return _VISIBLE.format(v=v)


def gds_disponible() -> bool:
    try:
        db.leer("RETURN gds.version() AS version")
        return True
    except Neo4jError:
        return False


def estado_metricas():
    """Datos del ultimo calculo, o None si nunca se ha calculado."""
    filas = db.leer("MATCH (m:Metricas {id: 'red'}) RETURN m{.*} AS m")
    return filas[0]["m"] if filas else None


# Cada paso es independiente: si uno falla (p. ej. un algoritmo no instalado) los demas siguen.
_PASOS = [
    ("pagerank", "CALL gds.pageRank.write($g, {writeProperty: 'pagerank'}) "
                 "YIELD nodePropertiesWritten RETURN nodePropertiesWritten AS n"),
    ("comunidad", "CALL gds.louvain.write($g, {writeProperty: 'comunidad', concurrency: 1}) "
                  "YIELD communityCount, nodePropertiesWritten RETURN communityCount AS n"),
    ("intermediacion", "CALL gds.betweenness.write($g, {writeProperty: 'intermediacion'}) "
                       "YIELD nodePropertiesWritten RETURN nodePropertiesWritten AS n"),
]


def recalcular(por: str) -> dict:
    """Proyecta la red de contactos en memoria, calcula las metricas y las guarda.
    Devuelve {'usuarios', 'conexiones', 'comunidades', 'hechos': [...], 'fallos': {paso: mensaje}}."""
    grafo = f"red_{uuid.uuid4().hex[:8]}"  # nombre unico: dos recalculos a la vez no se pisan
    proy = db.escribir(
        "CALL gds.graph.project($g, 'Usuario', {CONECTA_CON: {orientation: 'UNDIRECTED'}}) "
        "YIELD nodeCount, relationshipCount RETURN nodeCount AS usuarios, relationshipCount AS relaciones",
        g=grafo,
    )
    resultado = {"usuarios": proy[0]["usuarios"] if proy else 0,
                 "conexiones": (proy[0]["relaciones"] // 2) if proy else 0,
                 "comunidades": 0, "hechos": [], "fallos": {}}
    try:
        for nombre, consulta in _PASOS:
            try:
                filas = db.escribir(consulta, g=grafo)
                resultado["hechos"].append(nombre)
                if nombre == "comunidad" and filas:
                    resultado["comunidades"] = filas[0]["n"]
            except Neo4jError as e:
                resultado["fallos"][nombre] = str(e.message)[:160]
        if resultado["hechos"]:
            db.escribir(
                """
                MERGE (m:Metricas {id: 'red'})
                SET m.calculado_en = datetime(), m.calculado_por = $por, m.usuarios = $usuarios,
                    m.conexiones = $conexiones, m.comunidades = $comunidades, m.calculos = $hechos
                """,
                por=por, usuarios=resultado["usuarios"], conexiones=resultado["conexiones"],
                comunidades=resultado["comunidades"], hechos=resultado["hechos"],
            )
    finally:
        db.escribir("CALL gds.graph.drop($g, false) YIELD graphName RETURN graphName", g=grafo)
    return resultado


# ------------------------------------------------------------------ lecturas
def resumen_red():
    filas = db.leer(
        f"""
        RETURN COUNT {{ (u:Usuario) WHERE {_activa("u")} }} AS usuarios,
               COUNT {{ (a:Usuario)-[:CONECTA_CON]->(b:Usuario) WHERE {_activa("a")} AND {_activa("b")} }} AS conexiones,
               COUNT {{ (e:Empresa) WHERE {_activa("e")} }} AS empresas,
               COUNT {{ (e:Empresa)-[:PUBLICA]->(o:Oferta {{estado: 'abierta'}})
                        WHERE o.fecha_cierre >= date({{timezone: 'America/Bogota'}}) AND {_activa("e")} }} AS ofertas,
               COUNT {{ (p:Proyecto) }} AS proyectos
        """
    )
    return filas[0]


def usuarios_con_metricas(limite: int = 1000):
    """Todas las personas visibles con sus metricas (las que aun no tienen, vienen en None)."""
    return db.leer(
        f"""
        MATCH (u:Usuario) WHERE {_activa("u")}
        OPTIONAL MATCH (u)-[:TRABAJA_EN {{actual: true}}]->(e:Empresa)
        RETURN u{{.id, .nombre, .apellido, .titular, .pagerank, .comunidad, .intermediacion}} AS usuario,
               COUNT {{ (u)-[:CONECTA_CON]-(x:Usuario) WHERE {_activa("x")} }} AS conexiones,
               e.nombre AS empresa
        ORDER BY coalesce(u.pagerank, 0) DESC
        LIMIT $limite
        """,
        limite=limite,
    )


def habilidades_por_comunidad(ids: list[str] | None = None):
    """Con 'ids' solo cuenta a esas personas (la analitica de una persona o una empresa);
    sin 'ids' cuenta a toda la red (solo el admin)."""
    return db.leer(
        f"""
        MATCH (u:Usuario)-[:TIENE_HABILIDAD]->(h:Habilidad)
        WHERE u.comunidad IS NOT NULL AND {_activa("u")} AND ($ids IS NULL OR u.id IN $ids)
        RETURN u.comunidad AS comunidad, h.nombre AS habilidad, count(u) AS personas
        """,
        ids=ids,
    )


def sectores_por_comunidad(ids: list[str] | None = None):
    return db.leer(
        f"""
        MATCH (u:Usuario)-[:TRABAJA_EN {{actual: true}}]->(e:Empresa)
        WHERE u.comunidad IS NOT NULL AND {_activa("u")} AND {_activa("e")} AND ($ids IS NULL OR u.id IN $ids)
        RETURN u.comunidad AS comunidad, e.sector AS sector, count(u) AS personas
        """,
        ids=ids,
    )


def brecha_habilidades(limite: int = 10):
    """Demanda (ofertas abiertas que la piden) frente a oferta de talento (personas que la tienen)."""
    return db.leer(
        f"""
        MATCH (h:Habilidad)
        OPTIONAL MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {{estado: 'abierta'}})-[:REQUIERE]->(h)
        WHERE o.fecha_cierre >= date({{timezone: 'America/Bogota'}}) AND {_activa("e")}
        WITH h, count(DISTINCT o) AS demanda
        RETURN h.nombre AS habilidad, demanda,
               COUNT {{ (u:Usuario)-[:TIENE_HABILIDAD]->(h) WHERE {_activa("u")} }} AS talento
        ORDER BY demanda DESC, habilidad
        LIMIT $limite
        """,
        limite=limite,
    )


def personas_visibles(limite: int = 500):
    """Para los selectores del laboratorio de consultas."""
    return db.leer(
        f"""
        MATCH (u:Usuario) WHERE {_activa("u")}
        RETURN u.id AS id, u.nombre AS nombre, u.apellido AS apellido
        ORDER BY u.nombre, u.apellido
        LIMIT $limite
        """,
        limite=limite,
    )


# --------------------------------------------------------------------- mapa
def aristas_entre(ids: list[str]):
    return db.leer(
        """
        MATCH (a:Usuario)-[:CONECTA_CON]-(b:Usuario)
        WHERE a.id < b.id AND a.id IN $ids AND b.id IN $ids
        RETURN a.id AS origen, b.id AS destino
        """,
        ids=ids,
    )


def contactos_de(uid: str):
    """Ids de la persona y de sus contactos directos (para su mapa personal)."""
    filas = db.leer(
        f"""
        MATCH (u:Usuario {{id: $id}})
        OPTIONAL MATCH (u)-[:CONECTA_CON]-(c:Usuario) WHERE {_activa("c")}
        RETURN u.id AS yo, collect(c.id) AS contactos
        """,
        id=uid,
    )
    return filas[0] if filas else {"yo": uid, "contactos": []}


def red_de_empresa(empresa_id: str):
    """El circulo de una empresa: sus trabajadores actuales y las personas que se postularon a sus ofertas."""
    filas = db.leer(
        f"""
        MATCH (e:Empresa {{id: $id}})
        OPTIONAL MATCH (t:Usuario)-[:TRABAJA_EN {{actual: true}}]->(e) WHERE {_activa("t")}
        WITH e, collect(DISTINCT t.id) AS empleados
        OPTIONAL MATCH (p:Usuario)-[:POSTULA_A]->(:Oferta)<-[:PUBLICA]-(e) WHERE {_activa("p")}
        RETURN empleados, collect(DISTINCT p.id) AS postulantes
        """,
        id=empresa_id,
    )
    return filas[0] if filas else {"empleados": [], "postulantes": []}
