// =====================================================================
// 06_permisos_admin.cypher  -  Permisos nuevos del panel de administracion
// Para bases que YA tienen cargado 01_schema.cypher. Idempotente (MERGE).
//
//   usuario.crear / usuario.eliminar  -> solo admin
//   catalogo.gestionar                -> staff y admin
//
// Ejecutar:
//   python cypher/Ejecutar_cypher.py cypher/06_permisos_admin.cypher
// =====================================================================
UNWIND [
  {rol: 'admin', permisos: ['usuario.crear', 'usuario.eliminar', 'catalogo.gestionar']},
  {rol: 'staff', permisos: ['catalogo.gestionar']}
] AS fila
MATCH (r:Rol {nombre: fila.rol})
UNWIND fila.permisos AS codigo
MERGE (p:Permiso {codigo: codigo})
MERGE (r)-[:PERMITE]->(p);
