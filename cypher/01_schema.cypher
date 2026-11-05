//  Restricciones de unicidad 
CREATE CONSTRAINT cuenta_id IF NOT EXISTS FOR (n:Cuenta) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT cuenta_email IF NOT EXISTS FOR (n:Cuenta) REQUIRE n.email IS UNIQUE;
CREATE CONSTRAINT usuario_id IF NOT EXISTS FOR (n:Usuario) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT empresa_id IF NOT EXISTS FOR (n:Empresa) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT habilidad_id IF NOT EXISTS FOR (n:Habilidad) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT habilidad_nombre IF NOT EXISTS FOR (n:Habilidad) REQUIRE n.nombre IS UNIQUE;
CREATE CONSTRAINT proyecto_id IF NOT EXISTS FOR (n:Proyecto) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT oferta_id IF NOT EXISTS FOR (n:Oferta) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT sesion_id IF NOT EXISTS FOR (n:Sesion) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT sesion_token IF NOT EXISTS FOR (n:Sesion) REQUIRE n.token_hash IS UNIQUE;
CREATE CONSTRAINT notificacion_id IF NOT EXISTS FOR (n:Notificacion) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT evento_id IF NOT EXISTS FOR (n:Evento) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT rol_nombre IF NOT EXISTS FOR (n:Rol) REQUIRE n.nombre IS UNIQUE;
CREATE CONSTRAINT permiso_codigo IF NOT EXISTS FOR (n:Permiso) REQUIRE n.codigo IS UNIQUE;


CREATE INDEX oferta_estado IF NOT EXISTS FOR (n:Oferta) ON (n.estado);
CREATE INDEX usuario_ciudad IF NOT EXISTS FOR (n:Usuario) ON (n.ciudad);
CREATE INDEX notificacion_leida IF NOT EXISTS FOR (n:Notificacion) ON (n.leida);

// Roles 
UNWIND ['persona', 'empresa', 'staff', 'admin'] AS nombre
MERGE (:Rol {nombre: nombre});

// Permisos y su asignacion a roles 
UNWIND [
  {rol: 'persona', permisos: ['perfil.editar', 'conexion.solicitar', 'oferta.postular']},
  {rol: 'empresa', permisos: ['empresa.editar', 'oferta.publicar', 'empresa.asignar_rrhh']},
  {rol: 'staff',   permisos: ['usuario.bloquear', 'contenido.moderar']},
  {rol: 'admin',   permisos: ['usuario.bloquear', 'contenido.moderar', 'staff.gestionar', 'sistema.auditar']}
] AS fila
MATCH (r:Rol {nombre: fila.rol})
UNWIND fila.permisos AS codigo
MERGE (p:Permiso {codigo: codigo})
MERGE (r)-[:PERMITE]->(p);