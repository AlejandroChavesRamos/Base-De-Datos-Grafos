"""Las consultas que pide el documento, tal como se ejecutan.

La pantalla /consultas muestra el texto de estas constantes y las ejecuta: lo que se
ve es EXACTAMENTE lo que se envia a Neo4j. Todas solo leen datos, ocultan las cuentas
desactivadas y reciben sus valores por parametros ($nombre), nunca pegados al texto.

  Q1-Q6  las seis preguntas del enunciado
  C1-C2  caminos entre personas y desde una persona hasta una oferta (Q3 es el camino hasta una empresa)
  H1     habilidades que comparten dos personas
  A1-A3  analitica de la red (usa propiedades calculadas con Graph Data Science)
  R1-R3  recomendaciones de contactos, empleos y colaboradores
"""
import time

from app.database import db

Q1_SIMILARES = """// Pregunta 1: ¿Qué usuarios tienen habilidades similares?
// Similitud de Jaccard = habilidades en común / habilidades de ambos sin repetir.
MATCH (a:Usuario {id: $id})-[:TIENE_HABILIDAD]->(h:Habilidad)
WITH a, collect(h) AS hab_a
MATCH (b:Usuario)
WHERE b <> a AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(b) }
MATCH (b)-[:TIENE_HABILIDAD]->(hb:Habilidad)
WITH a, hab_a, b, collect(hb) AS hab_b
WITH b, hab_a, hab_b, [x IN hab_a WHERE x IN hab_b] AS comunes
WHERE size(comunes) > 0
RETURN b{.id, .nombre, .apellido, .titular} AS usuario,
       [x IN comunes | x.nombre] AS habilidades_comunes,
       round(1.0 * size(comunes) / (size(hab_a) + size(hab_b) - size(comunes)), 2) AS similitud
ORDER BY similitud DESC, size(comunes) DESC
LIMIT $limite"""

Q2_COMUNES = """// Pregunta 2: ¿Qué contactos en común existen entre dos profesionales?
// CONECTA_CON es simétrica: se consulta sin dirección.
MATCH (a:Usuario {id: $a})-[:CONECTA_CON]-(c:Usuario)-[:CONECTA_CON]-(b:Usuario {id: $b})
WHERE a <> b AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(c) }
RETURN DISTINCT c{.id, .nombre, .apellido, .titular} AS usuario
ORDER BY usuario.nombre, usuario.apellido
LIMIT $limite"""

Q3_RUTA = """// Pregunta 3: ¿Cuál es la ruta más corta entre un usuario y una empresa?
// Se camina por contactos (CONECTA_CON) y por empleo VIGENTE (TRABAJA_EN con actual = true).
// allShortestPaths devuelve todas las rutas de la longitud mínima.
MATCH (u:Usuario {id: $id}), (e:Empresa {id: $empresa})
MATCH p = allShortestPaths((u)-[:CONECTA_CON|TRABAJA_EN*..8]-(e))
WHERE all(r IN relationships(p) WHERE type(r) = 'CONECTA_CON' OR r.actual = true)
  AND all(n IN nodes(p) WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(n) })
RETURN [n IN nodes(p) | coalesce(n.nombre + ' ' + n.apellido, n.nombre)] AS ruta, length(p) AS saltos
LIMIT $limite"""

Q4_CANDIDATOS = """// Pregunta 4: ¿Qué candidatos podrían recomendarse para una oferta según sus conexiones y competencias?
// Debe cumplir TODAS las habilidades obligatorias (con su nivel mínimo) y no trabajar ya en la empresa.
// Puntaje = 10 por requisito cumplido + 5 por cada contacto suyo que trabaja en la empresa.
MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {id: $oferta})
MATCH (o)-[req:REQUIERE]->(h:Habilidad)
WITH e, o, count(h) AS total_req, sum(CASE WHEN req.obligatoria THEN 1 ELSE 0 END) AS total_oblig
MATCH (o)-[req:REQUIERE]->(h:Habilidad)<-[th:TIENE_HABILIDAD]-(u:Usuario)
WHERE th.nivel >= req.nivel_minimo
  AND NOT EXISTS { (u)-[:TRABAJA_EN {actual: true}]->(e) }
  AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(u) }
WITH e, o, u, total_req, total_oblig, collect(h.nombre) AS cumple, count(h) AS n_cumple,
     sum(CASE WHEN req.obligatoria THEN 1 ELSE 0 END) AS oblig_cumplidas
WHERE oblig_cumplidas = total_oblig
WITH e, o, u, total_req, cumple, n_cumple,
     [(u)-[:CONECTA_CON]-(c:Usuario)-[:TRABAJA_EN {actual: true}]->(e)
        WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(c) }
        | c.nombre + ' ' + c.apellido] AS contactos
RETURN u{.id, .nombre, .apellido, .titular, .buscando_empleo} AS usuario,
       n_cumple, total_req, cumple AS habilidades, contactos,
       n_cumple * 10 + size(contactos) * 5 AS puntaje,
       EXISTS { (u)-[:POSTULA_A]->(o) } AS postulado
ORDER BY puntaje DESC
LIMIT $limite"""

Q5_PROYECTOS = """// Pregunta 5: ¿Qué proyectos comparten tecnologías o miembros relacionados?
// Afinidad = tecnologías en común + 2 puntos por cada miembro compartido.
MATCH (p1:Proyecto), (p2:Proyecto)
WHERE p1.id < p2.id
OPTIONAL MATCH (p1)-[:USA]->(h:Habilidad)<-[:USA]-(p2)
WITH p1, p2, collect(DISTINCT h.nombre) AS tecnologias
OPTIONAL MATCH (p1)<-[:PARTICIPA_EN]-(u:Usuario)-[:PARTICIPA_EN]->(p2)
WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(u) }
WITH p1, p2, tecnologias, collect(DISTINCT u.nombre + ' ' + u.apellido) AS miembros
WHERE size(tecnologias) + size(miembros) > 0
RETURN p1.nombre AS proyecto_1, p2.nombre AS proyecto_2, tecnologias, miembros,
       size(tecnologias) + size(miembros) * 2 AS afinidad
ORDER BY afinidad DESC
LIMIT $limite"""

Q6_DEMANDA = """// Pregunta 6: ¿Qué habilidades son las más demandadas en las ofertas?
// Solo ofertas abiertas, vigentes y de empresas activas.
MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {estado: 'abierta'})-[r:REQUIERE]->(h:Habilidad)
WHERE o.fecha_cierre >= date({timezone: 'America/Bogota'})
  AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(e) }
RETURN h.nombre AS habilidad, h.categoria AS categoria, count(o) AS ofertas,
       sum(CASE WHEN r.obligatoria THEN 1 ELSE 0 END) AS como_obligatoria
ORDER BY ofertas DESC, habilidad
LIMIT $limite"""

C1_CAMINO_PERSONA = """// Caminos entre dos personas: ¿cómo están conectadas? (grados de separación)
// allShortestPaths devuelve todas las rutas de la longitud mínima; solo se camina por CONECTA_CON.
MATCH (a:Usuario {id: $a}), (b:Usuario {id: $b})
WHERE a <> b
MATCH p = allShortestPaths((a)-[:CONECTA_CON*..6]-(b))
WHERE all(n IN nodes(p) WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(n) })
RETURN [n IN nodes(p) | n.nombre + ' ' + n.apellido] AS ruta, length(p) AS saltos
LIMIT $limite"""

C2_CAMINO_OFERTA = """// Camino desde una persona hasta una oferta (oportunidad laboral).
// La oferta se alcanza por la empresa que la publica (PUBLICA): se camina por contactos (CONECTA_CON)
// y por empleo VIGENTE (TRABAJA_EN con actual = true) hasta la empresa, y se suma ese último salto.
MATCH (u:Usuario {id: $id}), (e:Empresa)-[:PUBLICA]->(o:Oferta {id: $oferta})
WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(e) }
MATCH p = allShortestPaths((u)-[:CONECTA_CON|TRABAJA_EN*..8]-(e))
WHERE all(r IN relationships(p) WHERE type(r) = 'CONECTA_CON' OR r.actual = true)
  AND all(n IN nodes(p) WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(n) })
RETURN [n IN nodes(p) | coalesce(n.nombre + ' ' + n.apellido, n.nombre)] AS ruta,
       length(p) + 1 AS saltos, o.titulo AS oferta
LIMIT $limite"""

H1_HABILIDADES_EN_COMUN = """// Habilidades que comparten dos personas, con el nivel (1 a 5) que tiene cada una.
MATCH (a:Usuario {id: $a})-[ta:TIENE_HABILIDAD]->(h:Habilidad)<-[tb:TIENE_HABILIDAD]-(b:Usuario {id: $b})
WHERE a <> b
RETURN h.nombre AS habilidad, h.categoria AS categoria, ta.nivel AS nivel_a, tb.nivel AS nivel_b
ORDER BY h.nombre
LIMIT $limite"""

A1_INFLUYENTES = """// Usuarios más influyentes: PageRank (calculado con Graph Data Science) frente al número de conexiones.
// PageRank pondera QUIÉN te conecta, no solo cuántos contactos tienes.
MATCH (u:Usuario)
WHERE u.pagerank IS NOT NULL AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(u) }
RETURN u{.id, .nombre, .apellido, .titular, .pagerank} AS usuario,
       COUNT { (u)-[:CONECTA_CON]-(x:Usuario) WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(x) } } AS conexiones
ORDER BY u.pagerank DESC
LIMIT $limite"""

A2_COMUNIDADES = """// Comunidades detectadas con el algoritmo de Louvain (propiedad 'comunidad', escrita por GDS).
// Una comunidad es un grupo de personas más conectadas entre sí que con el resto.
MATCH (u:Usuario)
WHERE u.comunidad IS NOT NULL AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(u) }
RETURN u.comunidad AS comunidad, count(u) AS miembros, collect(u.nombre + ' ' + u.apellido) AS personas
ORDER BY miembros DESC, comunidad
LIMIT $limite"""

A3_PUENTES = """// Usuarios puente: centralidad de intermediación (propiedad 'intermediacion', escrita por GDS).
// Mide cuántos caminos más cortos entre otras personas pasan por esta persona.
MATCH (u:Usuario)
WHERE u.intermediacion IS NOT NULL AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(u) }
RETURN u{.id, .nombre, .apellido, .titular, .intermediacion} AS usuario,
       COUNT { (u)-[:CONECTA_CON]-(x:Usuario) WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(x) } } AS conexiones
ORDER BY u.intermediacion DESC
LIMIT $limite"""

R1_CONTACTOS = """// Recomendación de contactos ("personas que quizás conozcas").
// Amigos de amigos que aún no son contacto ni tienen invitación pendiente.
// Puntaje = 3 por cada contacto en común + 1 por cada habilidad en común.
MATCH (u:Usuario {id: $id})-[:CONECTA_CON]-(amigo:Usuario)-[:CONECTA_CON]-(sug:Usuario)
WHERE sug <> u
  AND NOT EXISTS { (u)-[:CONECTA_CON]-(sug) }
  AND NOT EXISTS { (u)-[:SOLICITA_CONEXION]-(sug) }
  AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(sug) }
  AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(amigo) }
WITH u, sug, count(DISTINCT amigo) AS amigos_comunes
OPTIONAL MATCH (u)-[:TIENE_HABILIDAD]->(h:Habilidad)<-[:TIENE_HABILIDAD]-(sug)
WITH sug, amigos_comunes, count(h) AS habilidades_comunes
RETURN sug{.id, .nombre, .apellido, .titular} AS usuario, amigos_comunes, habilidades_comunes,
       amigos_comunes * 3 + habilidades_comunes AS puntaje
ORDER BY puntaje DESC
LIMIT $limite"""

R2_EMPLEOS = """// Recomendación de empleos.
// Ofertas abiertas y vigentes a las que aún no te has postulado, ordenadas por afinidad
// (requisitos que cumples con el nivel mínimo) y por contactos que trabajan en la empresa.
MATCH (u:Usuario {id: $id})
MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {estado: 'abierta'})
WHERE o.fecha_cierre >= date({timezone: 'America/Bogota'})
  AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(e) }
  AND NOT EXISTS { (u)-[:POSTULA_A]->(o) }
OPTIONAL MATCH (o)-[req:REQUIERE]->(h:Habilidad)
OPTIONAL MATCH (u)-[tu:TIENE_HABILIDAD]->(h)
WITH u, e, o, count(h) AS total_req,
     sum(CASE WHEN tu IS NOT NULL AND tu.nivel >= req.nivel_minimo THEN 1 ELSE 0 END) AS cumple
RETURN o{.id, .titulo} AS oferta, e.nombre AS empresa, cumple, total_req,
       CASE WHEN total_req = 0 THEN 0 ELSE toInteger(round(100.0 * cumple / total_req)) END AS afinidad,
       [(u)-[:CONECTA_CON]-(c:Usuario)-[:TRABAJA_EN {actual: true}]->(e)
          WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(c) }
          | c.nombre + ' ' + c.apellido] AS contactos
ORDER BY afinidad DESC, size(contactos) DESC
LIMIT $limite"""

R3_COLABORADORES = """// Recomendación de colaboradores.
// Personas con las que ya compartiste un proyecto y con las que todavía no estás conectado.
MATCH (u:Usuario {id: $id})-[:PARTICIPA_EN]->(p:Proyecto)<-[:PARTICIPA_EN]-(col:Usuario)
WHERE col <> u
  AND NOT EXISTS { (u)-[:CONECTA_CON]-(col) }
  AND NOT EXISTS { (u)-[:SOLICITA_CONEXION]-(col) }
  AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(col) }
RETURN col{.id, .nombre, .apellido, .titular} AS usuario, collect(DISTINCT p.nombre) AS proyectos_compartidos
ORDER BY size(proyectos_compartidos) DESC, usuario.nombre
LIMIT $limite"""

PROYECTOS_RELACIONADOS = """// Proyectos relacionados con los tuyos: usan alguna de las mismas tecnologías y aún no participas en ellos.
MATCH (u:Usuario {id: $id})-[:PARTICIPA_EN]->(mio:Proyecto)-[:USA]->(h:Habilidad)<-[:USA]-(otro:Proyecto)
WHERE NOT EXISTS { (u)-[:PARTICIPA_EN]->(otro) }
RETURN otro{.id, .nombre, .estado} AS proyecto, collect(DISTINCT h.nombre) AS tecnologias,
       collect(DISTINCT mio.nombre) AS relacionado_con
ORDER BY size(tecnologias) DESC, proyecto.nombre
LIMIT $limite"""


def ejecutar(consulta: str, **params):
    """Ejecuta una consulta de solo lectura. Devuelve (filas, milisegundos)."""
    t0 = time.perf_counter()
    filas = db.leer(consulta, **params)
    return filas, (time.perf_counter() - t0) * 1000


# ---- Usadas por las paginas de la aplicacion ----
def colaboradores(uid: str, limite: int = 5):
    return ejecutar(R3_COLABORADORES, id=uid, limite=limite)[0]


def proyectos_relacionados(uid: str, limite: int = 4):
    return ejecutar(PROYECTOS_RELACIONADOS, id=uid, limite=limite)[0]


def candidatos(oferta_id: str, limite: int = 20):
    return ejecutar(Q4_CANDIDATOS, oferta=oferta_id, limite=limite)[0]


def camino_a_oferta(uid: str, oferta_id: str):
    """La ruta mas corta de la persona hasta la oferta (o None si no hay)."""
    filas = ejecutar(C2_CAMINO_OFERTA, id=uid, oferta=oferta_id, limite=1)[0]
    return filas[0] if filas else None


def habilidades_en_comun(a: str, b: str, limite: int = 30):
    return ejecutar(H1_HABILIDADES_EN_COMUN, a=a, b=b, limite=limite)[0]


def proyectos_afines(limite: int = 6):
    """Q5: pares de proyectos que comparten tecnologias o miembros."""
    return ejecutar(Q5_PROYECTOS, limite=limite)[0]
