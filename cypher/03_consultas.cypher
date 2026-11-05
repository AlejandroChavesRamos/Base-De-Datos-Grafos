

// A1. Que usuarios tienen habilidades similares a las de un usuario?
//     Similitud de Jaccard = comunes / (total A + total B - comunes)

MATCH (a:Usuario {id: 'u01'})-[:TIENE_HABILIDAD]->(h:Habilidad)
WITH a, collect(h) AS hab_a
MATCH (b:Usuario) WHERE b <> a
MATCH (b)-[:TIENE_HABILIDAD]->(hb:Habilidad)
WITH a, hab_a, b, collect(hb) AS hab_b
WITH b, hab_a, hab_b, [x IN hab_a WHERE x IN hab_b] AS comunes
WHERE size(comunes) > 0
RETURN b.nombre + ' ' + b.apellido AS usuario,
       b.titular AS titular,
       [x IN comunes | x.nombre] AS habilidades_comunes,
       size(comunes) AS n_comunes,
       round(1.0 * size(comunes) / (size(hab_a) + size(hab_b) - size(comunes)), 2) AS similitud
ORDER BY similitud DESC, n_comunes DESC
LIMIT 10;


// A2. Que contactos en comun existen entre dos profesionales?
//     (el patron no lleva direccion: CONECTA_CON es simetrica)

MATCH (a:Usuario {id: 'u01'})-[:CONECTA_CON]-(c:Usuario)-[:CONECTA_CON]-(b:Usuario {id: 'u03'})
RETURN c.id AS id,
       c.nombre + ' ' + c.apellido AS contacto_en_comun,
       c.titular AS titular
ORDER BY contacto_en_comun;



// A3. Cual es la ruta mas corta entre un usuario y una empresa?
//     Se puede viajar por conexiones y por empleo VIGENTE (actual = true).
//     El filtro evita contar el historial laboral como un vinculo activo.

MATCH (u:Usuario {id: 'u26'}), (e:Empresa {id: 'e04'})
MATCH p = shortestPath((u)-[:CONECTA_CON|TRABAJA_EN*..8]-(e))
WHERE all(r IN relationships(p) WHERE type(r) = 'CONECTA_CON' OR r.actual = true)
RETURN [n IN nodes(p) | n.nombre] AS ruta,
       length(p) AS saltos;

// Variante: TODAS las rutas mas cortas (alternativas de igual longitud)
MATCH (u:Usuario {id: 'u26'}), (e:Empresa {id: 'e04'})
MATCH p = allShortestPaths((u)-[:CONECTA_CON|TRABAJA_EN*..8]-(e))
WHERE all(r IN relationships(p) WHERE type(r) = 'CONECTA_CON' OR r.actual = true)
RETURN [n IN nodes(p) | n.nombre] AS ruta, length(p) AS saltos;


MATCH (u:Usuario {id: 'u26'}), (e:Empresa {id: 'e04'})
MATCH p = shortestPath((u)-[:CONECTA_CON|TRABAJA_EN*..8]-(e))
WHERE all(r IN relationships(p) WHERE type(r) = 'CONECTA_CON' OR r.actual = true)
RETURN p;



// A4. Que candidatos se pueden recomendar para una oferta, segun sus
//     competencias y sus conexiones con la empresa?
//     - Debe cumplir TODAS las habilidades obligatorias (con nivel minimo).
//     - Se excluye a quien ya trabaja en la empresa.
//     - puntaje = 10 por habilidad requerida cumplida + 5 por contacto
//       que trabaja actualmente en la empresa.

MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {id: 'o02'})
MATCH (o)-[req:REQUIERE]->(h:Habilidad)
WITH e, o, count(h) AS total_req,
     sum(CASE WHEN req.obligatoria THEN 1 ELSE 0 END) AS total_oblig
MATCH (o)-[req:REQUIERE]->(h:Habilidad)<-[th:TIENE_HABILIDAD]-(u:Usuario)
WHERE th.nivel >= req.nivel_minimo
  AND NOT EXISTS { (u)-[:TRABAJA_EN {actual: true}]->(e) }
WITH e, o, u, total_req, total_oblig,
     collect(h.nombre) AS cumple,
     count(h) AS n_cumple,
     sum(CASE WHEN req.obligatoria THEN 1 ELSE 0 END) AS oblig_cumplidas
WHERE oblig_cumplidas = total_oblig
OPTIONAL MATCH (u)-[:CONECTA_CON]-(emp:Usuario)-[:TRABAJA_EN {actual: true}]->(e)
WITH u, total_req, cumple, n_cumple,
     collect(DISTINCT emp.nombre + ' ' + emp.apellido) AS contactos_en_empresa
RETURN u.nombre + ' ' + u.apellido AS candidato,
       u.titular AS titular,
       toString(n_cumple) + ' de ' + toString(total_req) AS requisitos_cumplidos,
       cumple AS habilidades_que_cumple,
       contactos_en_empresa,
       n_cumple * 10 + size(contactos_en_empresa) * 5 AS puntaje
ORDER BY puntaje DESC;



// A5. Que proyectos comparten tecnologias o miembros?

// a) Por tecnologias (habilidades) en comun
MATCH (p1:Proyecto)-[:USA]->(h:Habilidad)<-[:USA]-(p2:Proyecto)
WHERE p1.id < p2.id
WITH p1, p2, collect(h.nombre) AS tecnologias_comunes
RETURN p1.nombre AS proyecto_1, p2.nombre AS proyecto_2,
       tecnologias_comunes, size(tecnologias_comunes) AS n
ORDER BY n DESC
LIMIT 10;

// b) Por miembros en comun
MATCH (p1:Proyecto)<-[:PARTICIPA_EN]-(u:Usuario)-[:PARTICIPA_EN]->(p2:Proyecto)
WHERE p1.id < p2.id
WITH p1, p2, collect(u.nombre + ' ' + u.apellido) AS miembros_comunes
RETURN p1.nombre AS proyecto_1, p2.nombre AS proyecto_2,
       miembros_comunes, size(miembros_comunes) AS n
ORDER BY n DESC;

// c) Afinidad combinada (tecnologias + 2 puntos por cada miembro compartido)
MATCH (p1:Proyecto), (p2:Proyecto)
WHERE p1.id < p2.id
OPTIONAL MATCH (p1)-[:USA]->(h:Habilidad)<-[:USA]-(p2)
WITH p1, p2, collect(DISTINCT h.nombre) AS tecnologias
OPTIONAL MATCH (p1)<-[:PARTICIPA_EN]-(u:Usuario)-[:PARTICIPA_EN]->(p2)
WITH p1, p2, tecnologias, collect(DISTINCT u.nombre + ' ' + u.apellido) AS miembros
WHERE size(tecnologias) + size(miembros) > 0
RETURN p1.nombre AS proyecto_1, p2.nombre AS proyecto_2,
       tecnologias, miembros,
       size(tecnologias) + size(miembros) * 2 AS afinidad
ORDER BY afinidad DESC
LIMIT 10;



// A6. Que habilidades son las mas demandadas en las ofertas?
//     (solo ofertas abiertas)

MATCH (o:Oferta {estado: 'abierta'})-[r:REQUIERE]->(h:Habilidad)
RETURN h.nombre AS habilidad,
       h.categoria AS categoria,
       count(o) AS ofertas_que_la_piden,
       sum(CASE WHEN r.obligatoria THEN 1 ELSE 0 END) AS como_obligatoria
ORDER BY ofertas_que_la_piden DESC, habilidad
LIMIT 10;

// Extra: brecha entre demanda (ofertas) y talento disponible (usuarios)
MATCH (h:Habilidad)
OPTIONAL MATCH (o:Oferta {estado: 'abierta'})-[:REQUIERE]->(h)
WITH h, count(DISTINCT o) AS demanda
OPTIONAL MATCH (u:Usuario)-[:TIENE_HABILIDAD]->(h)
RETURN h.nombre AS habilidad, demanda, count(DISTINCT u) AS usuarios_con_la_habilidad
ORDER BY demanda DESC, habilidad
LIMIT 10;



// PARTE B - RECOMENDACIONES



// B1. Recomendacion de contactos ("personas que quizas conozcas")
//     Amigos de amigos que aun no son contacto ni tienen solicitud
//     pendiente. Puntaje = 3 por amigo en comun + 1 por habilidad en comun.

MATCH (u:Usuario {id: 'u05'})-[:CONECTA_CON]-(amigo:Usuario)-[:CONECTA_CON]-(sug:Usuario)
WHERE sug <> u
  AND NOT (u)-[:CONECTA_CON]-(sug)
  AND NOT (u)-[:SOLICITA_CONEXION]-(sug)
WITH u, sug,
     collect(DISTINCT amigo.nombre + ' ' + amigo.apellido) AS por_medio_de,
     count(DISTINCT amigo) AS amigos_comunes
OPTIONAL MATCH (u)-[:TIENE_HABILIDAD]->(h:Habilidad)<-[:TIENE_HABILIDAD]-(sug)
WITH sug, por_medio_de, amigos_comunes, count(h) AS habilidades_comunes
RETURN sug.nombre + ' ' + sug.apellido AS sugerencia,
       sug.titular AS titular,
       por_medio_de, amigos_comunes, habilidades_comunes,
       amigos_comunes * 3 + habilidades_comunes AS puntaje
ORDER BY puntaje DESC
LIMIT 5;



// B2. Recomendacion de empleos para un usuario
//     Ofertas abiertas donde cumple niveles minimos, a las que aun no se
//     ha postulado. Suma puntos si tiene contactos en la empresa.

MATCH (u:Usuario {id: 'u07'})-[tu:TIENE_HABILIDAD]->(h:Habilidad)<-[req:REQUIERE]-(o:Oferta {estado: 'abierta'})
WHERE tu.nivel >= req.nivel_minimo
  AND NOT (u)-[:POSTULA_A]->(o)
WITH u, o, count(h) AS coincidencias, collect(h.nombre) AS habilidades
MATCH (e:Empresa)-[:PUBLICA]->(o)
OPTIONAL MATCH (u)-[:CONECTA_CON]-(c:Usuario)-[:TRABAJA_EN {actual: true}]->(e)
WITH o, e, coincidencias, habilidades,
     collect(DISTINCT c.nombre + ' ' + c.apellido) AS contactos_en_empresa
RETURN o.titulo AS oferta, e.nombre AS empresa, o.modalidad AS modalidad,
       coincidencias, habilidades, contactos_en_empresa,
       coincidencias * 10 + size(contactos_en_empresa) * 5 AS puntaje
ORDER BY puntaje DESC
LIMIT 5;



// B3. Recomendacion de colaboradores
//     Personas con las que compartio un proyecto pero con las que todavia
//     no esta conectado.

MATCH (u:Usuario {id: 'u02'})-[:PARTICIPA_EN]->(p:Proyecto)<-[:PARTICIPA_EN]-(col:Usuario)
WHERE col <> u
  AND NOT (u)-[:CONECTA_CON]-(col)
RETURN col.nombre + ' ' + col.apellido AS colaborador,
       col.titular AS titular,
       collect(p.nombre) AS proyectos_compartidos
ORDER BY size(proyectos_compartidos) DESC;



// PARTE C - ANALITICA 
// Para PageRank y comunidades reales ver 04_analitica_gds.cypher



// C1. Usuarios mas influyentes por numero de conexiones (grado)

MATCH (u:Usuario)
RETURN u.nombre + ' ' + u.apellido AS usuario,
       u.titular AS titular,
       COUNT { (u)-[:CONECTA_CON]-(:Usuario) } AS conexiones
ORDER BY conexiones DESC
LIMIT 10;


// C2. Usuarios "puente": conectan personas que de otro modo no se conocen
//     Cuenta pares de contactos suyos que NO estan conectados entre si.

MATCH (u:Usuario)-[:CONECTA_CON]-(a:Usuario), (u)-[:CONECTA_CON]-(b:Usuario)
WHERE a.id < b.id AND NOT (a)-[:CONECTA_CON]-(b)
RETURN u.nombre + ' ' + u.apellido AS usuario,
       count(*) AS pares_que_conecta
ORDER BY pares_que_conecta DESC
LIMIT 10;


// C3. Empresas con mas postulaciones recibidas

MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta)
OPTIONAL MATCH (u:Usuario)-[:POSTULA_A]->(o)
RETURN e.nombre AS empresa,
       count(DISTINCT o) AS ofertas,
       count(u) AS postulaciones
ORDER BY postulaciones DESC;

// C4. Postulaciones por estado

MATCH (:Usuario)-[r:POSTULA_A]->(:Oferta)
RETURN r.estado AS estado, count(*) AS total
ORDER BY total DESC;


// C5. Quien puede publicar ofertas de una empresa?
//     (la regla de permisos del modelo: RR. HH. vigente de esa empresa)

MATCH (u:Usuario)-[t:TRABAJA_EN {actual: true, rol: 'rrhh'}]->(e:Empresa {id: 'e01'})
RETURN u.nombre + ' ' + u.apellido AS persona, t.cargo AS cargo;


// PARTE D - CRUD DE EJEMPLO (lo que hara la aplicacion)


// Crear un usuario
CREATE (u:Usuario {id: 'u99', nombre: 'Prueba', apellido: 'Temporal',
                   titular: 'Usuario de prueba', ciudad: 'Barranquilla',
                   experiencia_anios: 0, buscando_empleo: true})
RETURN u;

// Consultar
MATCH (u:Usuario {id: 'u99'}) RETURN u;

// Actualizar
MATCH (u:Usuario {id: 'u99'})
SET u.titular = 'Actualizado', u.ciudad = 'Soledad'
RETURN u;

// Aceptar una solicitud de conexion (se borra la solicitud y se crea CONECTA_CON)
MATCH (a:Usuario {id: 'u26'})-[s:SOLICITA_CONEXION]->(b:Usuario {id: 'u05'})
DELETE s
MERGE (a)-[c:CONECTA_CON]->(b)
ON CREATE SET c.desde = date()
RETURN a.nombre, b.nombre, c.desde;

// Postularse a una oferta (MERGE evita postulaciones duplicadas)
MATCH (u:Usuario {id: 'u99'}), (o:Oferta {id: 'o04'})
MERGE (u)-[r:POSTULA_A]->(o)
ON CREATE SET r.estado = 'enviada', r.fecha = date()
RETURN u.nombre, o.titulo, r.estado;

// Eliminar (DETACH borra tambien sus relaciones)
MATCH (u:Usuario {id: 'u99'}) DETACH DELETE u;



// PARTE E - EVIDENCIA PARA EL COMPONENTE DE INVESTIGACION
// Ejecuta con PROFILE para ver cuantos accesos a la base hace cada
// consulta. Sirve para contrastar con el equivalente en SQL (auto-joins).


PROFILE
MATCH (a:Usuario {id: 'u26'})-[:CONECTA_CON*3]-(x:Usuario)
WHERE x <> a AND NOT (a)-[:CONECTA_CON]-(x)
RETURN DISTINCT x.nombre + ' ' + x.apellido AS alcanzable_en_3_saltos;
