
// 0. Verifica que el plugin este instalado (si da error, falta instalar GDS
//    en Neo4j Desktop > instancia > Plugins, y reiniciar la instancia)
RETURN gds.version() AS version_gds;

// 1. Proyeccion en memoria de la red de usuarios (conexiones sin direccion)
CALL gds.graph.drop('red', false);

CALL gds.graph.project(
  'red',
  'Usuario',
  {CONECTA_CON: {orientation: 'UNDIRECTED'}}
);

// 2. Usuarios mas influyentes (PageRank): solo consulta
CALL gds.pageRank.stream('red')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).nombre + ' ' + gds.util.asNode(nodeId).apellido AS usuario,
       round(score, 3) AS influencia
ORDER BY influencia DESC
LIMIT 10;

// 3. Comunidades detectadas (Louvain): solo consulta
CALL gds.louvain.stream('red')
YIELD nodeId, communityId
WITH communityId, collect(gds.util.asNode(nodeId).nombre) AS miembros
RETURN communityId AS comunidad, size(miembros) AS tamano, miembros
ORDER BY tamano DESC;

// 4. Guardar resultados en los nodos para que la aplicacion los lea
//    rapido desde el panel (propiedades: pagerank y comunidad)
CALL gds.pageRank.write('red', {writeProperty: 'pagerank'})
YIELD nodePropertiesWritten;

CALL gds.louvain.write('red', {writeProperty: 'comunidad'})
YIELD communityCount, nodePropertiesWritten;

// 5. Lectura desde el panel de analitica
MATCH (u:Usuario)
RETURN u.comunidad AS comunidad,
       count(*) AS usuarios,
       collect(u.nombre) AS miembros,
       round(max(u.pagerank), 3) AS influencia_maxima
ORDER BY usuarios DESC;

// 6. Libera la proyeccion de memoria
CALL gds.graph.drop('red');
