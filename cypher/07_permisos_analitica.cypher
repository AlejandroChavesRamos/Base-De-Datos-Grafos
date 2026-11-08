// =====================================================================
// 07_permisos_analitica.cypher  -  Permisos de la analitica, de las consultas
// y de la edicion de cuentas. Para bases que YA tienen cargado 01_schema.cypher.
// Idempotente: se puede ejecutar varias veces (y aunque ya se hubiera ejecutado antes).
//
//   analitica.administrar -> SOLO admin: recalcular metricas y ver TODA la red.
//   consultas.ver         -> SOLO admin: laboratorio de consultas (/consultas).
//   usuario.editar        -> SOLO admin: modificar los datos de una cuenta.
//
// Personas y empresas ven la analitica de su propio circulo sin necesitar permisos.
//
// Ejecutar:
//   python cypher/Ejecutar_cypher.py cypher/07_permisos_analitica.cypher
// =====================================================================
UNWIND ['analitica.administrar', 'consultas.ver', 'usuario.editar'] AS codigo
MATCH (r:Rol {nombre: 'admin'})
MERGE (p:Permiso {codigo: codigo})
MERGE (r)-[:PERMITE]->(p);

// El staff ya no administra la analitica: si se le habia dado antes, se le quita.
MATCH (:Rol {nombre: 'staff'})-[x:PERMITE]->(:Permiso {codigo: 'analitica.administrar'})
DELETE x;
