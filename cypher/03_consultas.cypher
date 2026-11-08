// =====================================================================
// 03_consultas.cypher  -  Las consultas del proyecto
//
// ARCHIVO GENERADO por cypher/generar_consultas.py a partir de
// app/repositories/consultas_documento.py: son EXACTAMENTE las consultas que ejecuta la aplicacion
// (y las que el administrador ve en /consultas). No lo edites a mano: cambia la constante y regenera.
//
// COMO USARLO (Neo4j Browser):
//   1. Ejecuta   :use linkedun
//   2. Ejecuta el bloque de PARAMETROS de abajo (una vez por sesion). Cambia los ids para probar otros casos.
//   3. Ejecuta UNA consulta a la vez (cada una devuelve su propia tabla).
// Este archivo usa comandos del Browser (:params), asi que NO sirve para Ejecutar_cypher.py.
//
// Para ver el costo de cualquier consulta, anteponle PROFILE (ver la parte final).
// =====================================================================

// ---------------------------------------------------------------------
// PARAMETROS DE EJEMPLO
//   $id, $a, $b  -> ids de personas      $empresa -> id de una empresa
//   $oferta      -> id de una oferta     $limite  -> maximo de filas
// ---------------------------------------------------------------------
:params {limite: 10, id: 'u01', a: 'u01', b: 'u03', empresa: 'e04', oferta: 'o02'}

// =====================================================================
// LAS SEIS PREGUNTAS DEL ENUNCIADO
// =====================================================================

// ---------- Q1 ----------
// Pregunta 1: ¿Qué usuarios tienen habilidades similares?
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
LIMIT $limite;

// ---------- Q2 ----------
// Pregunta 2: ¿Qué contactos en común existen entre dos profesionales?
// CONECTA_CON es simétrica: se consulta sin dirección.
MATCH (a:Usuario {id: $a})-[:CONECTA_CON]-(c:Usuario)-[:CONECTA_CON]-(b:Usuario {id: $b})
WHERE a <> b AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(c) }
RETURN DISTINCT c{.id, .nombre, .apellido, .titular} AS usuario
ORDER BY usuario.nombre, usuario.apellido
LIMIT $limite;

// ---------- Q3 ----------
// Pregunta 3: ¿Cuál es la ruta más corta entre un usuario y una empresa?
// Se camina por contactos (CONECTA_CON) y por empleo VIGENTE (TRABAJA_EN con actual = true).
// allShortestPaths devuelve todas las rutas de la longitud mínima.
MATCH (u:Usuario {id: $id}), (e:Empresa {id: $empresa})
MATCH p = allShortestPaths((u)-[:CONECTA_CON|TRABAJA_EN*..8]-(e))
WHERE all(r IN relationships(p) WHERE type(r) = 'CONECTA_CON' OR r.actual = true)
  AND all(n IN nodes(p) WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(n) })
RETURN [n IN nodes(p) | coalesce(n.nombre + ' ' + n.apellido, n.nombre)] AS ruta, length(p) AS saltos
LIMIT $limite;

// ---------- Q4 ----------
// Pregunta 4: ¿Qué candidatos podrían recomendarse para una oferta según sus conexiones y competencias?
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
LIMIT $limite;

// ---------- Q5 ----------
// Pregunta 5: ¿Qué proyectos comparten tecnologías o miembros relacionados?
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
LIMIT $limite;

// ---------- Q6 ----------
// Pregunta 6: ¿Qué habilidades son las más demandadas en las ofertas?
// Solo ofertas abiertas, vigentes y de empresas activas.
MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {estado: 'abierta'})-[r:REQUIERE]->(h:Habilidad)
WHERE o.fecha_cierre >= date({timezone: 'America/Bogota'})
  AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(e) }
RETURN h.nombre AS habilidad, h.categoria AS categoria, count(o) AS ofertas,
       sum(CASE WHEN r.obligatoria THEN 1 ELSE 0 END) AS como_obligatoria
ORDER BY ofertas DESC, habilidad
LIMIT $limite;

// =====================================================================
// CAMINOS Y HABILIDADES COMPARTIDAS
// =====================================================================

// ---------- C1 ----------
// Caminos entre dos personas: ¿cómo están conectadas? (grados de separación)
// allShortestPaths devuelve todas las rutas de la longitud mínima; solo se camina por CONECTA_CON.
MATCH (a:Usuario {id: $a}), (b:Usuario {id: $b})
WHERE a <> b
MATCH p = allShortestPaths((a)-[:CONECTA_CON*..6]-(b))
WHERE all(n IN nodes(p) WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(n) })
RETURN [n IN nodes(p) | n.nombre + ' ' + n.apellido] AS ruta, length(p) AS saltos
LIMIT $limite;

// ---------- C2 ----------
// Camino desde una persona hasta una oferta (oportunidad laboral).
// La oferta se alcanza por la empresa que la publica (PUBLICA): se camina por contactos (CONECTA_CON)
// y por empleo VIGENTE (TRABAJA_EN con actual = true) hasta la empresa, y se suma ese último salto.
MATCH (u:Usuario {id: $id}), (e:Empresa)-[:PUBLICA]->(o:Oferta {id: $oferta})
WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(e) }
MATCH p = allShortestPaths((u)-[:CONECTA_CON|TRABAJA_EN*..8]-(e))
WHERE all(r IN relationships(p) WHERE type(r) = 'CONECTA_CON' OR r.actual = true)
  AND all(n IN nodes(p) WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(n) })
RETURN [n IN nodes(p) | coalesce(n.nombre + ' ' + n.apellido, n.nombre)] AS ruta,
       length(p) + 1 AS saltos, o.titulo AS oferta
LIMIT $limite;

// ---------- H1 ----------
// Habilidades que comparten dos personas, con el nivel (1 a 5) que tiene cada una.
MATCH (a:Usuario {id: $a})-[ta:TIENE_HABILIDAD]->(h:Habilidad)<-[tb:TIENE_HABILIDAD]-(b:Usuario {id: $b})
WHERE a <> b
RETURN h.nombre AS habilidad, h.categoria AS categoria, ta.nivel AS nivel_a, tb.nivel AS nivel_b
ORDER BY h.nombre
LIMIT $limite;

// =====================================================================
// ANALÍTICA DE LA RED
// =====================================================================

// ---------- A1 ----------
// Usuarios más influyentes: PageRank (calculado con Graph Data Science) frente al número de conexiones.
// PageRank pondera QUIÉN te conecta, no solo cuántos contactos tienes.
MATCH (u:Usuario)
WHERE u.pagerank IS NOT NULL AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(u) }
RETURN u{.id, .nombre, .apellido, .titular, .pagerank} AS usuario,
       COUNT { (u)-[:CONECTA_CON]-(x:Usuario) WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(x) } } AS conexiones
ORDER BY u.pagerank DESC
LIMIT $limite;

// ---------- A2 ----------
// Comunidades detectadas con el algoritmo de Louvain (propiedad 'comunidad', escrita por GDS).
// Una comunidad es un grupo de personas más conectadas entre sí que con el resto.
MATCH (u:Usuario)
WHERE u.comunidad IS NOT NULL AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(u) }
RETURN u.comunidad AS comunidad, count(u) AS miembros, collect(u.nombre + ' ' + u.apellido) AS personas
ORDER BY miembros DESC, comunidad
LIMIT $limite;

// ---------- A3 ----------
// Usuarios puente: centralidad de intermediación (propiedad 'intermediacion', escrita por GDS).
// Mide cuántos caminos más cortos entre otras personas pasan por esta persona.
MATCH (u:Usuario)
WHERE u.intermediacion IS NOT NULL AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(u) }
RETURN u{.id, .nombre, .apellido, .titular, .intermediacion} AS usuario,
       COUNT { (u)-[:CONECTA_CON]-(x:Usuario) WHERE NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(x) } } AS conexiones
ORDER BY u.intermediacion DESC
LIMIT $limite;

// =====================================================================
// RECOMENDACIONES
// =====================================================================

// ---------- R1 ----------
// Recomendación de contactos ("personas que quizás conozcas").
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
LIMIT $limite;

// ---------- R2 ----------
// Recomendación de empleos.
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
LIMIT $limite;

// ---------- R3 ----------
// Recomendación de colaboradores.
// Personas con las que ya compartiste un proyecto y con las que todavía no estás conectado.
MATCH (u:Usuario {id: $id})-[:PARTICIPA_EN]->(p:Proyecto)<-[:PARTICIPA_EN]-(col:Usuario)
WHERE col <> u
  AND NOT EXISTS { (u)-[:CONECTA_CON]-(col) }
  AND NOT EXISTS { (u)-[:SOLICITA_CONEXION]-(col) }
  AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(col) }
RETURN col{.id, .nombre, .apellido, .titular} AS usuario, collect(DISTINCT p.nombre) AS proyectos_compartidos
ORDER BY size(proyectos_compartidos) DESC, usuario.nombre
LIMIT $limite;

// =====================================================================
// PAGINA PROYECTOS
// =====================================================================

// ---------- Proyectos relacionados con los tuyos ----------
// Proyectos relacionados con los tuyos: usan alguna de las mismas tecnologías y aún no participas en ellos.
MATCH (u:Usuario {id: $id})-[:PARTICIPA_EN]->(mio:Proyecto)-[:USA]->(h:Habilidad)<-[:USA]-(otro:Proyecto)
WHERE NOT EXISTS { (u)-[:PARTICIPA_EN]->(otro) }
RETURN otro{.id, .nombre, .estado} AS proyecto, collect(DISTINCT h.nombre) AS tecnologias,
       collect(DISTINCT mio.nombre) AS relacionado_con
ORDER BY size(tecnologias) DESC, proyecto.nombre
LIMIT $limite;


// =====================================================================
// ESCRITURA (CRUD): sentencias equivalentes a las que ejecuta la aplicacion.
// Cubren las funcionalidades del enunciado con datos de prueba (u99, e99, o99, p99)
// que se borran al final, asi que la base queda como estaba.
// =====================================================================

// --- 1. CRUD de usuarios: crear, consultar y actualizar ------------------------
CREATE (u:Usuario {id: 'u99', nombre: 'Prueba', apellido: 'Temporal',
                   titular: 'Usuario de prueba', ciudad: 'Barranquilla',
                   experiencia_anios: 0, buscando_empleo: true})
RETURN u;

MATCH (u:Usuario {id: 'u99'}) RETURN u;

MATCH (u:Usuario {id: 'u99'})
SET u.titular = 'Desarrollador Python', u.ciudad = 'Soledad', u.experiencia_anios = 2
RETURN u;

// --- 3. Vincular usuarios con habilidades, empresas y proyectos ----------------
// Habilidad: MERGE crea la relacion o, si ya existe, solo actualiza nivel y anios.
MATCH (u:Usuario {id: 'u99'}), (h:Habilidad {id: 'h01'})
MERGE (u)-[r:TIENE_HABILIDAD]->(h)
SET r.nivel = 4, r.anios = 2
RETURN h.nombre, r.nivel;

MATCH (u:Usuario {id: 'u99'}), (h:Habilidad {id: 'h02'})
MERGE (u)-[r:TIENE_HABILIDAD]->(h)
SET r.nivel = 3, r.anios = 1
RETURN h.nombre, r.nivel;

// Empresa: un solo empleo vigente; el anterior (si existe) se cierra en la misma sentencia.
MATCH (u:Usuario {id: 'u99'}), (e:Empresa {id: 'e01'})
OPTIONAL MATCH (u)-[prev:TRABAJA_EN {actual: true}]->()
WITH u, e, collect(prev) AS previos
FOREACH (p IN previos | SET p.actual = false, p.hasta = date())
CREATE (u)-[:TRABAJA_EN {rol: 'trabajador', cargo: 'Desarrollador', desde: date(), hasta: null, actual: true}]->(e)
RETURN e.nombre;

// Proyecto: se crea, el usuario participa y se enlazan sus tecnologias (UNWIND).
MATCH (u:Usuario {id: 'u99'})
CREATE (p:Proyecto {id: 'p99', nombre: 'Proyecto de prueba', descripcion: 'Ejemplo',
                    estado: 'en_curso', fecha_inicio: date()})
CREATE (u)-[:PARTICIPA_EN {rol: 'lider', desde: date()}]->(p)
WITH p
UNWIND ['h01', 'h02'] AS tid
MATCH (h:Habilidad {id: tid})
CREATE (p)-[:USA]->(h)
RETURN p.nombre, count(h) AS tecnologias;

// --- 4 y 5. Registrar una empresa, su oferta y las habilidades que requiere ----
CREATE (e:Empresa {id: 'e99', nombre: 'Empresa de Prueba', sector: 'Tecnología',
                   tamano: 'pequena', ciudad: 'Barranquilla'})
RETURN e;

// La oferta nace en borrador y queda enlazada a la empresa con PUBLICA.
MATCH (e:Empresa {id: 'e99'})
CREATE (o:Oferta {id: 'o99', titulo: 'Desarrollador Junior', descripcion: 'Oferta de prueba',
                  modalidad: 'remota', ciudad: 'Barranquilla', salario_min: 2500000, salario_max: 3500000,
                  estado: 'borrador', fecha_publicacion: date(), fecha_cierre: date() + duration({days: 30})})
CREATE (e)-[:PUBLICA {fecha: date(), publicada_por: 'u99'}]->(o)
RETURN o.titulo;

// REQUIERE lleva el nivel minimo y si la habilidad es obligatoria.
MATCH (o:Oferta {id: 'o99'})
UNWIND [{hid: 'h01', nivel: 3, obligatoria: true}, {hid: 'h02', nivel: 2, obligatoria: false}] AS req
MATCH (h:Habilidad {id: req.hid})
MERGE (o)-[r:REQUIERE]->(h)
SET r.nivel_minimo = req.nivel, r.obligatoria = req.obligatoria
RETURN h.nombre, r.nivel_minimo, r.obligatoria;

// Publicar: solo si tiene al menos un requisito.
MATCH (o:Oferta {id: 'o99', estado: 'borrador'})
WHERE EXISTS { (o)-[:REQUIERE]->(:Habilidad) }
SET o.estado = 'abierta', o.fecha_publicacion = date()
RETURN o.titulo, o.estado;

// --- 2. Conexiones profesionales entre usuarios ------------------------------
// Solicitar: no a uno mismo, ni a un contacto, ni si ya hay una invitacion pendiente.
// La notificacion se crea en la misma sentencia (equivale a un trigger).
MATCH (a:Usuario {id: 'u99'}), (b:Usuario {id: 'u05'})
WHERE a <> b
  AND NOT EXISTS { (a)-[:CONECTA_CON]-(b) }
  AND NOT EXISTS { (a)-[:SOLICITA_CONEXION]-(b) }
CREATE (a)-[:SOLICITA_CONEXION {fecha: date(), mensaje: 'Hola'}]->(b)
CREATE (:Notificacion {id: randomUUID(), tipo: 'conexion_solicitud',
                       mensaje: a.nombre + ' ' + a.apellido + ' quiere conectar contigo.',
                       leida: false, fecha: datetime(), enlace: '/red'})-[:PARA]->(b)
RETURN 1 AS ok;

// Aceptar: la invitacion se borra y nace CONECTA_CON (relacion simetrica).
MATCH (a:Usuario {id: 'u99'})-[s:SOLICITA_CONEXION]->(b:Usuario {id: 'u05'})
DELETE s
WITH a, b
WHERE NOT EXISTS { (a)-[:CONECTA_CON]-(b) }
CREATE (a)-[:CONECTA_CON {desde: date()}]->(b)
RETURN a.nombre, b.nombre;

// --- 6. Postularse a una oferta ----------------------------------------------
// Solo si esta abierta, vigente y una sola vez por persona.
MATCH (u:Usuario {id: 'u99'}), (o:Oferta {id: 'o99', estado: 'abierta'})
WHERE o.fecha_cierre >= date() AND NOT EXISTS { (u)-[:POSTULA_A]->(o) }
CREATE (u)-[:POSTULA_A {estado: 'enviada', fecha: date()}]->(o)
RETURN o.titulo;

// La empresa cambia el estado de la postulacion y la persona recibe un aviso.
MATCH (u:Usuario {id: 'u99'})-[p:POSTULA_A]->(o:Oferta {id: 'o99'})<-[:PUBLICA]-(e:Empresa)
SET p.estado = 'en_revision'
CREATE (:Notificacion {id: randomUUID(), tipo: 'postulacion_estado',
                       mensaje: 'Tu postulación a "' + o.titulo + '" en ' + e.nombre + ' cambió a: En revisión',
                       leida: false, fecha: datetime(), enlace: '/empleos'})-[:PARA]->(u)
RETURN o.titulo, p.estado;

// --- 1. CRUD de usuarios: eliminar (y limpiar los datos de prueba) -------------
// DETACH DELETE borra el nodo junto con todas sus relaciones.
MATCH (n:Notificacion)-[:PARA]->(:Usuario {id: 'u99'}) DETACH DELETE n;
MATCH (n:Notificacion) WHERE n.mensaje STARTS WITH 'Prueba Temporal' DETACH DELETE n;
MATCH (x) WHERE (x:Oferta AND x.id = 'o99') OR (x:Empresa AND x.id = 'e99') OR (x:Proyecto AND x.id = 'p99')
DETACH DELETE x;
MATCH (u:Usuario {id: 'u99'}) DETACH DELETE u;


// =====================================================================
// EVIDENCIA PARA EL COMPONENTE DE INVESTIGACION
// Antepon PROFILE a cualquier consulta de arriba para ver cuantos accesos a la base (db hits) hace.
// Ejemplo: amigos de amigos de amigos (3 saltos) de una persona; en SQL seria un auto-JOIN por cada salto.
// =====================================================================
PROFILE
MATCH (a:Usuario {id: 'u26'})-[:CONECTA_CON*3]-(x:Usuario)
WHERE x <> a AND NOT (a)-[:CONECTA_CON]-(x)
RETURN DISTINCT x.nombre + ' ' + x.apellido AS alcanzable_en_3_saltos;
