
// Habilidades
UNWIND [
  {id:'h01', nombre:'Python',                categoria:'tecnica'},
  {id:'h02', nombre:'SQL',                   categoria:'tecnica'},
  {id:'h03', nombre:'Neo4j',                 categoria:'tecnica'},
  {id:'h04', nombre:'JavaScript',            categoria:'tecnica'},
  {id:'h05', nombre:'React',                 categoria:'tecnica'},
  {id:'h06', nombre:'Java',                  categoria:'tecnica'},
  {id:'h07', nombre:'Docker',                categoria:'tecnica'},
  {id:'h08', nombre:'Machine Learning',      categoria:'tecnica'},
  {id:'h09', nombre:'Ciberseguridad',        categoria:'tecnica'},
  {id:'h10', nombre:'Excel Avanzado',        categoria:'tecnica'},
  {id:'h25', nombre:'Power BI',              categoria:'tecnica'},
  {id:'h11', nombre:'Marketing Digital',     categoria:'negocios'},
  {id:'h12', nombre:'Contabilidad',          categoria:'negocios'},
  {id:'h13', nombre:'Gestion Logistica',     categoria:'negocios'},
  {id:'h14', nombre:'Comercio Exterior',     categoria:'negocios'},
  {id:'h24', nombre:'Gestion de Proyectos',  categoria:'negocios'},
  {id:'h15', nombre:'Diseno Grafico',        categoria:'creativa'},
  {id:'h16', nombre:'UX/UI',                 categoria:'creativa'},
  {id:'h17', nombre:'Atencion al Paciente',  categoria:'salud'},
  {id:'h18', nombre:'Gestion Hospitalaria',  categoria:'salud'},
  {id:'h19', nombre:'Docencia',              categoria:'educacion'},
  {id:'h20', nombre:'Liderazgo',             categoria:'blanda'},
  {id:'h21', nombre:'Comunicacion',          categoria:'blanda'},
  {id:'h22', nombre:'Trabajo en Equipo',     categoria:'blanda'},
  {id:'h23', nombre:'Ingles',                categoria:'idioma'}
] AS f
MERGE (h:Habilidad {id: f.id})
SET h.nombre = f.nombre, h.categoria = f.categoria;

// Empresas
UNWIND [
  {id:'e01', nombre:'Caribe Software Labs',               sector:'Tecnologia',        tamano:'mediana', ciudad:'Barranquilla',   sitio_web:'https://caribesoftwarelabs.example.com', descripcion:'Desarrollo de software a la medida y analitica de datos para el Caribe colombiano.'},
  {id:'e02', nombre:'PortData Logistica',                 sector:'Logistica',         tamano:'grande',  ciudad:'Barranquilla',   sitio_web:'https://portdata.example.com',           descripcion:'Operador logistico con tecnologia para seguimiento de carga portuaria.'},
  {id:'e03', nombre:'Clinica Mar Caribe',                 sector:'Salud',             tamano:'grande',  ciudad:'Barranquilla',   sitio_web:'https://clinicamarcaribe.example.com',   descripcion:'Clinica de alta complejidad con servicios de telemedicina.'},
  {id:'e04', nombre:'Banco del Litoral',                  sector:'Finanzas',          tamano:'grande',  ciudad:'Barranquilla',   sitio_web:'https://bancodellitoral.example.com',    descripcion:'Entidad financiera regional con foco en banca digital.'},
  {id:'e05', nombre:'Arenosa Creativa',                   sector:'Marketing y Diseno',tamano:'pequena', ciudad:'Barranquilla',   sitio_web:'https://arenosacreativa.example.com',    descripcion:'Agencia de marketing, branding y produccion digital.'},
  {id:'e06', nombre:'Instituto Tecnologico del Atlantico',sector:'Educacion',         tamano:'mediana', ciudad:'Puerto Colombia',sitio_web:'https://ita.example.com',                descripcion:'Institucion de educacion superior en ingenieria y ciencias.'},
  {id:'e07', nombre:'Exportadora Costa Norte',            sector:'Comercio Exterior', tamano:'mediana', ciudad:'Barranquilla',   sitio_web:'https://costanorte.example.com',         descripcion:'Exportacion de productos agricolas y manufacturados.'}
] AS f
MERGE (e:Empresa {id: f.id})
SET e += f;

//Usuarios
UNWIND [
  {id:'u01', nombre:'Camila',      apellido:'Restrepo',  titular:'Ingeniera de Software Senior',      ciudad:'Barranquilla',    experiencia_anios:9,  buscando_empleo:false, resumen:'Arquitecta de soluciones en la nube y bases de datos de grafos.'},
  {id:'u02', nombre:'Andres',      apellido:'Mendoza',   titular:'Desarrollador Backend',             ciudad:'Barranquilla',    experiencia_anios:6,  buscando_empleo:false, resumen:'Backend en Java y Python, APIs y microservicios.'},
  {id:'u03', nombre:'Valentina',   apellido:'Cano',      titular:'Cientifica de Datos',               ciudad:'Barranquilla',    experiencia_anios:5,  buscando_empleo:false, resumen:'Modelos predictivos para riesgo financiero.'},
  {id:'u04', nombre:'Santiago',    apellido:'Perez',     titular:'Ingeniero DevOps',                  ciudad:'Barranquilla',    experiencia_anios:5,  buscando_empleo:false, resumen:'Automatizacion, contenedores e infraestructura.'},
  {id:'u05', nombre:'Laura',       apellido:'Ortega',    titular:'Desarrolladora Full Stack',         ciudad:'Barranquilla',    experiencia_anios:6,  buscando_empleo:false, resumen:'Aplicaciones web con JavaScript y React.'},
  {id:'u06', nombre:'Juan David',  apellido:'Salcedo',   titular:'Analista de Ciberseguridad',        ciudad:'Barranquilla',    experiencia_anios:6,  buscando_empleo:false, resumen:'Deteccion de fraude y seguridad de aplicaciones.'},
  {id:'u07', nombre:'Mariana',     apellido:'Barros',    titular:'Ingeniera de Datos',                ciudad:'Puerto Colombia', experiencia_anios:4,  buscando_empleo:true,  resumen:'Pipelines de datos y modelado analitico.'},
  {id:'u08', nombre:'Felipe',      apellido:'Charris',   titular:'Disenador UX/UI',                   ciudad:'Barranquilla',    experiencia_anios:6,  buscando_empleo:false, resumen:'Disena interfaces centradas en el usuario.'},
  {id:'u09', nombre:'Daniela',     apellido:'Vergara',   titular:'Coordinadora Logistica',            ciudad:'Barranquilla',    experiencia_anios:7,  buscando_empleo:false, resumen:'Operacion portuaria y cadena de suministro.'},
  {id:'u10', nombre:'Carlos',      apellido:'Pacheco',   titular:'Analista de Comercio Exterior',     ciudad:'Soledad',         experiencia_anios:8,  buscando_empleo:false, resumen:'Tramites aduaneros y exportaciones.'},
  {id:'u11', nombre:'Sofia',       apellido:'Arango',    titular:'Analista de Sistemas Logisticos',   ciudad:'Barranquilla',    experiencia_anios:4,  buscando_empleo:true,  resumen:'Une logistica y tecnologia: sistemas de trazabilidad.'},
  {id:'u12', nombre:'Luis Fernando',apellido:'Gomez',    titular:'Contador Publico',                  ciudad:'Barranquilla',    experiencia_anios:10, buscando_empleo:false, resumen:'Contabilidad, auditoria y analisis financiero.'},
  {id:'u13', nombre:'Natalia',     apellido:'Jimenez',   titular:'Analista de Talento Humano',        ciudad:'Barranquilla',    experiencia_anios:5,  buscando_empleo:false, resumen:'Seleccion de personal en el sector financiero.'},
  {id:'u14', nombre:'Esteban',     apellido:'Villa',     titular:'Gerente de Operaciones',            ciudad:'Barranquilla',    experiencia_anios:10, buscando_empleo:false, resumen:'Liderazgo de operaciones y mejora de procesos.'},
  {id:'u15', nombre:'Isabella',    apellido:'Torres',    titular:'Medica General',                    ciudad:'Barranquilla',    experiencia_anios:7,  buscando_empleo:false, resumen:'Medicina general y telemedicina.'},
  {id:'u16', nombre:'Miguel Angel',apellido:'Rojas',     titular:'Enfermero Jefe',                    ciudad:'Barranquilla',    experiencia_anios:9,  buscando_empleo:false, resumen:'Cuidado critico y gestion de equipos de enfermeria.'},
  {id:'u17', nombre:'Paola',       apellido:'Herrera',   titular:'Jefe de Talento Humano Hospitalario',ciudad:'Barranquilla',   experiencia_anios:8,  buscando_empleo:false, resumen:'Gestion de personal y administracion hospitalaria.'},
  {id:'u18', nombre:'Ricardo',     apellido:'Blanco',    titular:'Docente e Investigador en Salud Digital',ciudad:'Barranquilla',experiencia_anios:12, buscando_empleo:false, resumen:'Investigacion aplicada: datos e inteligencia artificial en salud.'},
  {id:'u19', nombre:'Juliana',     apellido:'Martinez',  titular:'Docente de Matematicas',            ciudad:'Malambo',         experiencia_anios:6,  buscando_empleo:true,  resumen:'Ensenanza de matematicas y pensamiento computacional.'},
  {id:'u20', nombre:'Alejandro',   apellido:'Suarez',    titular:'Coordinador Academico',             ciudad:'Puerto Colombia', experiencia_anios:9,  buscando_empleo:false, resumen:'Diseno curricular y gestion academica.'},
  {id:'u21', nombre:'Manuela',     apellido:'Diaz',      titular:'Disenadora Grafica',                ciudad:'Barranquilla',    experiencia_anios:7,  buscando_empleo:false, resumen:'Identidad visual y piezas para campanas.'},
  {id:'u22', nombre:'Sebastian',   apellido:'Ruiz',      titular:'Especialista en Marketing Digital', ciudad:'Barranquilla',    experiencia_anios:6,  buscando_empleo:false, resumen:'Estrategia digital, pauta y analitica.'},
  {id:'u23', nombre:'Karen',       apellido:'Polo',      titular:'Community Manager',                 ciudad:'Barranquilla',    experiencia_anios:3,  buscando_empleo:false, resumen:'Gestion de comunidades y contenido para redes.'},
  {id:'u24', nombre:'Julian',      apellido:'De la Hoz', titular:'Director Creativo',                 ciudad:'Barranquilla',    experiencia_anios:10, buscando_empleo:false, resumen:'Direccion creativa de campanas de marca.'},
  {id:'u25', nombre:'Andrea',      apellido:'Castro',    titular:'Redactora de Contenidos Freelance', ciudad:'Santa Marta',     experiencia_anios:5,  buscando_empleo:true,  resumen:'Redaccion publicitaria y contenido SEO.'},
  {id:'u26', nombre:'Tomas',       apellido:'Navarro',   titular:'Estudiante de Ingenieria de Sistemas',ciudad:'Soledad',       experiencia_anios:1,  buscando_empleo:true,  resumen:'Busca su primera experiencia en desarrollo de software.'},
  {id:'u27', nombre:'Gabriela',    apellido:'Ibarra',    titular:'Lider de Talento Humano',           ciudad:'Barranquilla',    experiencia_anios:6,  buscando_empleo:false, resumen:'Seleccion y cultura en empresas de tecnologia.'}
] AS f
MERGE (u:Usuario {id: f.id})
SET u += f;

//Relacion tiene habilidad
UNWIND [
  ['u01','h01',5,8],['u01','h02',4,7],['u01','h03',4,3],['u01','h20',5,5],['u01','h23',4,6],['u01','h24',4,4],
  ['u02','h06',5,6],['u02','h02',4,6],['u02','h07',3,3],['u02','h01',3,2],['u02','h22',4,5],
  ['u03','h01',5,5],['u03','h08',5,4],['u03','h02',4,5],['u03','h25',4,3],['u03','h23',4,4],
  ['u04','h07',5,5],['u04','h01',3,3],['u04','h09',3,2],['u04','h22',4,4],['u04','h23',3,3],
  ['u05','h04',5,6],['u05','h05',5,4],['u05','h01',3,2],['u05','h16',3,2],['u05','h22',5,5],
  ['u06','h09',5,6],['u06','h01',3,3],['u06','h07',3,2],['u06','h23',4,5],
  ['u07','h02',5,6],['u07','h01',4,4],['u07','h03',3,1],['u07','h25',4,3],['u07','h08',3,1],
  ['u08','h16',5,6],['u08','h15',4,5],['u08','h05',3,2],['u08','h21',4,5],['u08','h04',2,1],
  ['u09','h13',5,7],['u09','h10',4,6],['u09','h20',4,4],['u09','h21',4,6],['u09','h23',3,3],
  ['u10','h14',5,8],['u10','h13',3,3],['u10','h23',4,6],['u10','h21',4,6],['u10','h10',3,4],
  ['u11','h13',4,4],['u11','h02',3,3],['u11','h01',3,2],['u11','h10',4,4],['u11','h25',3,2],['u11','h22',4,4],
  ['u12','h12',5,10],['u12','h10',5,9],['u12','h25',3,2],['u12','h21',3,5],
  ['u13','h21',4,4],['u13','h22',4,5],['u13','h10',4,5],['u13','h20',3,2],['u13','h23',3,3],['u13','h12',3,3],
  ['u14','h20',5,10],['u14','h13',4,8],['u14','h24',5,7],['u14','h23',4,8],['u14','h21',4,10],
  ['u15','h17',5,7],['u15','h21',5,7],['u15','h22',4,7],['u15','h23',3,4],
  ['u16','h17',5,9],['u16','h20',4,5],['u16','h22',5,9],
  ['u17','h18',5,8],['u17','h20',4,4],['u17','h21',4,6],['u17','h24',4,5],['u17','h10',3,5],
  ['u18','h19',5,12],['u18','h08',3,3],['u18','h01',3,4],['u18','h18',3,3],['u18','h23',4,10],['u18','h02',3,4],
  ['u19','h19',5,6],['u19','h21',4,6],['u19','h22',4,6],['u19','h10',3,3],
  ['u20','h19',4,9],['u20','h20',4,5],['u20','h24',4,4],['u20','h21',4,9],
  ['u21','h15',5,7],['u21','h16',3,2],['u21','h21',4,6],['u21','h22',4,5],
  ['u22','h11',5,6],['u22','h25',3,2],['u22','h21',4,6],['u22','h23',3,4],['u22','h10',3,5],
  ['u23','h11',4,3],['u23','h15',3,3],['u23','h21',5,4],['u23','h22',4,3],
  ['u24','h15',5,10],['u24','h20',4,6],['u24','h11',3,5],['u24','h16',3,3],['u24','h23',3,4],
  ['u25','h21',5,5],['u25','h11',3,2],['u25','h23',4,5],
  ['u26','h01',3,1],['u26','h02',2,1],['u26','h04',2,1],['u26','h22',4,2],['u26','h23',3,2],
  ['u27','h20',4,5],['u27','h21',5,6],['u27','h22',4,6],['u27','h23',3,3]
] AS t
MATCH (u:Usuario {id: t[0]}), (h:Habilidad {id: t[1]})
MERGE (u)-[r:TIENE_HABILIDAD]->(h)
SET r.nivel = t[2], r.anios = t[3];

//Relacion Trabaja en 
UNWIND [
  // vigentes
  ['u01','e01','trabajador','Ingeniera de Software Senior','2019-03-01',null,true],
  ['u02','e01','trabajador','Desarrollador Backend','2021-06-01',null,true],
  ['u03','e04','trabajador','Cientifica de Datos','2022-02-01',null,true],
  ['u04','e02','trabajador','Ingeniero DevOps','2020-09-01',null,true],
  ['u05','e01','trabajador','Desarrolladora Full Stack','2022-08-01',null,true],
  ['u06','e04','trabajador','Analista de Ciberseguridad','2021-01-01',null,true],
  ['u07','e02','trabajador','Ingeniera de Datos','2023-01-15',null,true],
  ['u08','e05','trabajador','Disenador UX/UI','2021-04-01',null,true],
  ['u09','e02','trabajador','Coordinadora Logistica','2018-05-01',null,true],
  ['u10','e07','trabajador','Analista de Comercio Exterior','2019-10-01',null,true],
  ['u11','e02','trabajador','Analista de Sistemas Logisticos','2022-03-01',null,true],
  ['u12','e04','trabajador','Contador Publico','2015-07-01',null,true],
  ['u13','e04','rrhh','Analista de Talento Humano','2021-11-01',null,true],
  ['u14','e07','trabajador','Gerente de Operaciones','2017-02-01',null,true],
  ['u15','e03','trabajador','Medica General','2018-02-01',null,true],
  ['u16','e03','trabajador','Enfermero Jefe','2016-08-01',null,true],
  ['u17','e03','rrhh','Jefe de Talento Humano','2016-03-01',null,true],
  ['u18','e06','trabajador','Docente Investigador','2012-08-01',null,true],
  ['u19','e06','trabajador','Docente de Matematicas','2020-02-01',null,true],
  ['u20','e06','trabajador','Coordinador Academico','2017-01-15',null,true],
  ['u21','e05','trabajador','Disenadora Grafica','2020-02-01',null,true],
  ['u22','e05','trabajador','Especialista en Marketing Digital','2021-09-01',null,true],
  ['u23','e05','trabajador','Community Manager','2023-02-01',null,true],
  ['u24','e05','trabajador','Director Creativo','2016-01-01',null,true],
  ['u27','e01','rrhh','Lider de Talento Humano','2021-02-01',null,true],
  // historial
  ['u01','e04','trabajador','Desarrolladora de Software','2015-02-01','2019-02-28',false],
  ['u02','e02','trabajador','Desarrollador Junior','2018-06-01','2021-05-31',false],
  ['u05','e05','trabajador','Desarrolladora Web','2019-05-01','2022-07-31',false],
  ['u09','e07','trabajador','Auxiliar Logistico','2014-03-01','2018-04-30',false],
  ['u12','e07','trabajador','Auxiliar Contable','2010-01-01','2015-06-30',false]
] AS t
MATCH (u:Usuario {id: t[0]}), (e:Empresa {id: t[1]})
MERGE (u)-[r:TRABAJA_EN {desde: date(t[4])}]->(e)
SET r.rol = t[2],
    r.cargo = t[3],
    r.hasta = CASE WHEN t[5] IS NULL THEN null ELSE date(t[5]) END,
    r.actual = t[6];


//Relacion conecta en 
UNWIND [
  // Grupo A: tecnologia (u01 es el hub)
  ['u01','u02','2021-07-01'],['u01','u03','2022-03-12'],['u01','u04','2021-02-20'],['u01','u05','2022-09-05'],
  ['u01','u06','2022-05-18'],['u01','u07','2023-02-01'],['u01','u27','2022-01-10'],
  ['u02','u03','2022-04-01'],['u02','u04','2021-08-09'],['u02','u05','2022-09-20'],['u02','u27','2022-02-14'],
  ['u03','u07','2023-02-10'],['u03','u06','2022-07-19'],['u04','u06','2022-06-07'],
  ['u05','u08','2023-01-16'],['u05','u27','2022-10-03'],
  // Grupo B: logistica, comercio exterior y finanzas
  ['u09','u10','2019-11-05'],['u09','u11','2022-03-20'],['u09','u14','2020-01-13'],['u10','u14','2020-05-02'],
  ['u11','u14','2023-09-11'],['u12','u13','2021-03-08'],['u12','u14','2021-06-30'],['u09','u12','2022-08-17'],
  ['u10','u12','2020-10-10'],['u06','u12','2021-02-11'],['u03','u13','2022-02-25'],
  // Grupo C: salud y educacion
  ['u15','u16','2018-06-01'],['u15','u17','2019-01-21'],['u16','u17','2019-03-15'],['u17','u20','2022-09-09'],
  ['u18','u19','2020-03-03'],['u18','u20','2018-02-12'],['u19','u20','2020-06-22'],['u15','u18','2023-07-07'],
  // Grupo D: creativo y marketing
  ['u21','u22','2021-10-01'],['u21','u23','2023-03-06'],['u21','u24','2020-03-02'],['u22','u23','2023-03-07'],
  ['u22','u24','2021-10-04'],['u23','u25','2023-06-01'],['u24','u25','2022-05-05'],['u22','u25','2022-11-11'],
  ['u21','u25','2022-12-01'],
  // Puentes entre grupos
  ['u08','u21','2021-05-10'],['u08','u24','2021-05-12'],['u08','u22','2022-01-18'],   // tecnologia <-> creativo
  ['u04','u11','2022-04-04'],['u04','u09','2021-01-25'],['u07','u11','2023-03-01'],   // tecnologia <-> logistica
  ['u01','u11','2023-06-14'],['u01','u14','2023-04-22'],                              // hub con logistica
  ['u01','u18','2022-11-03'],['u18','u03','2024-02-14'],                              // tecnologia <-> academia/salud
  ['u02','u15','2024-05-05'],['u02','u16','2024-05-06'],                              // tecnologia <-> salud
  ['u13','u27','2023-05-09'],['u17','u27','2023-08-08'],                              // comunidad de RR. HH.
  ['u01','u26','2026-09-15'],['u18','u26','2026-08-30']                               // estudiante
] AS p
MATCH (a:Usuario {id: p[0]}), (b:Usuario {id: p[1]})
MERGE (a)-[r:CONECTA_CON]->(b)
SET r.desde = date(p[2]);

//Relacion Solicita conexion
UNWIND [
  ['u26','u05','Hola Laura, soy estudiante y me gustaria aprender de tu experiencia en React.','2026-10-28'],
  ['u25','u08','Hola Felipe, trabajamos en el mismo ecosistema creativo, conectemos.','2026-10-29'],
  ['u10','u01','Camila, me interesa conocer mas sobre analitica de datos en logistica.','2026-10-30'],
  ['u23','u08','Felipe, admiro tu trabajo en UX. Me encantaria conectar.','2026-10-31']
] AS s
MATCH (a:Usuario {id: s[0]}), (b:Usuario {id: s[1]})
MERGE (a)-[r:SOLICITA_CONEXION]->(b)
SET r.mensaje = s[2], r.fecha = date(s[3]);

//Proyectos
UNWIND [
  {id:'p01', nombre:'Plataforma de Seguimiento de Carga Portuaria',   descripcion:'Trazabilidad en tiempo real de contenedores en el puerto.',        estado:'en_curso',   fecha_inicio:'2026-01-15', fecha_fin:null},
  {id:'p02', nombre:'Recomendador de Productos Bancarios',            descripcion:'Modelo de recomendacion de productos para clientes del banco.',   estado:'finalizado', fecha_inicio:'2024-03-01', fecha_fin:'2025-02-28'},
  {id:'p03', nombre:'Portal de Empleo Universitario',                 descripcion:'Portal abierto que conecta estudiantes con practicas y vacantes.',estado:'en_curso',   fecha_inicio:'2026-05-01', fecha_fin:null},
  {id:'p04', nombre:'Telemedicina para Comunidades del Atlantico',    descripcion:'Consultas medicas remotas para municipios del departamento.',     estado:'en_curso',   fecha_inicio:'2025-09-01', fecha_fin:null},
  {id:'p05', nombre:'Campana Carnaval Digital',                       descripcion:'Campana multicanal para el Carnaval de Barranquilla.',            estado:'finalizado', fecha_inicio:'2026-01-10', fecha_fin:'2026-03-05'},
  {id:'p06', nombre:'Plataforma de Cursos Virtuales',                 descripcion:'Aula virtual institucional con seguimiento academico.',           estado:'finalizado', fecha_inicio:'2023-06-01', fecha_fin:'2024-06-30'},
  {id:'p07', nombre:'Tablero de Comercio Exterior',                   descripcion:'Dashboard de exportaciones, aranceles y rutas.',                  estado:'en_curso',   fecha_inicio:'2026-04-01', fecha_fin:null},
  {id:'p08', nombre:'Deteccion de Fraude con Grafos',                 descripcion:'Proyecto abierto para detectar anillos de fraude con Neo4j.',     estado:'en_curso',   fecha_inicio:'2026-02-01', fecha_fin:null},
  {id:'p09', nombre:'API de Citas Medicas',                           descripcion:'Servicio de agendamiento de citas integrado a la clinica.',       estado:'finalizado', fecha_inicio:'2024-08-01', fecha_fin:'2025-04-15'}
] AS f
MERGE (p:Proyecto {id: f.id})
SET p.nombre = f.nombre,
    p.descripcion = f.descripcion,
    p.estado = f.estado,
    p.fecha_inicio = date(f.fecha_inicio),
    p.fecha_fin = CASE WHEN f.fecha_fin IS NULL THEN null ELSE date(f.fecha_fin) END;

//Proyectos de empresas
UNWIND [['p01','e02'],['p02','e04'],['p04','e03'],['p05','e05'],['p06','e06'],['p07','e07'],['p09','e03']] AS t
MATCH (p:Proyecto {id: t[0]}), (e:Empresa {id: t[1]})
MERGE (p)-[:PERTENECE_A]->(e);

//Teconologias del proyecto 
UNWIND [
  ['p01','h01'],['p01','h02'],['p01','h07'],['p01','h13'],
  ['p02','h01'],['p02','h08'],['p02','h02'],['p02','h25'],
  ['p03','h04'],['p03','h05'],['p03','h16'],['p03','h03'],
  ['p04','h01'],['p04','h08'],['p04','h09'],
  ['p05','h11'],['p05','h15'],['p05','h16'],
  ['p06','h04'],['p06','h05'],['p06','h02'],['p06','h06'],
  ['p07','h25'],['p07','h02'],['p07','h14'],['p07','h10'],
  ['p08','h03'],['p08','h01'],['p08','h09'],['p08','h08'],
  ['p09','h06'],['p09','h02'],['p09','h07']
] AS t
MATCH (p:Proyecto {id: t[0]}), (h:Habilidad {id: t[1]})
MERGE (p)-[:USA]->(h);

//Relacion Participa en
UNWIND [
  ['u04','p01','DevOps'],['u07','p01','Ingeniera de datos'],['u11','p01','Analista funcional'],['u09','p01','Lider de negocio'],
  ['u03','p02','Lider tecnica'],['u12','p02','Experto de negocio'],['u06','p02','Seguridad'],
  ['u05','p03','Lider tecnica'],['u08','p03','Diseno UX'],['u26','p03','Desarrollador junior'],['u18','p03','Asesor academico'],
  ['u15','p04','Experta clinica'],['u17','p04','Coordinadora'],['u18','p04','Asesor'],['u02','p04','Desarrollador backend'],
  ['u21','p05','Diseno grafico'],['u22','p05','Estrategia digital'],['u23','p05','Redes sociales'],['u24','p05','Direccion creativa'],['u08','p05','Diseno de experiencia'],
  ['u18','p06','Director academico'],['u19','p06','Contenidos'],['u20','p06','Coordinacion'],['u05','p06','Desarrollo frontend'],
  ['u10','p07','Experto de dominio'],['u14','p07','Patrocinador'],['u11','p07','Analista'],['u12','p07','Analisis financiero'],
  ['u01','p08','Lider tecnica'],['u03','p08','Modelos de ML'],['u06','p08','Seguridad'],['u07','p08','Ingenieria de datos'],
  ['u02','p09','Desarrollador backend'],['u16','p09','Experto clinico'],['u15','p09','Experta clinica']
] AS t
MATCH (u:Usuario {id: t[0]}), (p:Proyecto {id: t[1]})
MERGE (u)-[r:PARTICIPA_EN]->(p)
SET r.rol = t[2];

//ofertas 
UNWIND [
  {id:'o01', empresa:'e01', publicada_por:'u27', titulo:'Desarrollador Backend Python',       descripcion:'Construccion de APIs y servicios de datos.',            modalidad:'hibrida',    ciudad:'Barranquilla', salario_min:6000000, salario_max:9000000,  estado:'abierta', fecha_publicacion:'2026-10-05', fecha_cierre:'2026-11-30'},
  {id:'o02', empresa:'e01', publicada_por:'u27', titulo:'Ingeniero de Datos Senior',          descripcion:'Diseno de pipelines y modelos analiticos.',             modalidad:'hibrida',    ciudad:'Barranquilla', salario_min:9000000, salario_max:13000000, estado:'abierta', fecha_publicacion:'2026-10-08', fecha_cierre:'2026-12-05'},
  {id:'o03', empresa:'e01', publicada_por:'u27', titulo:'Desarrollador Full Stack React',     descripcion:'Interfaces web y APIs para clientes del Caribe.',       modalidad:'remota',     ciudad:'Barranquilla', salario_min:5500000, salario_max:8500000,  estado:'abierta', fecha_publicacion:'2026-10-10', fecha_cierre:'2026-12-10'},
  {id:'o04', empresa:'e04', publicada_por:'u13', titulo:'Analista de Ciberseguridad',         descripcion:'Monitoreo y respuesta a incidentes.',                   modalidad:'presencial', ciudad:'Barranquilla', salario_min:7000000, salario_max:10000000, estado:'abierta', fecha_publicacion:'2026-10-02', fecha_cierre:'2026-11-25'},
  {id:'o05', empresa:'e04', publicada_por:'u13', titulo:'Cientifico de Datos',                descripcion:'Modelos de riesgo y deteccion de fraude.',              modalidad:'hibrida',    ciudad:'Barranquilla', salario_min:9000000, salario_max:14000000, estado:'abierta', fecha_publicacion:'2026-10-06', fecha_cierre:'2026-12-01'},
  {id:'o06', empresa:'e02', publicada_por:'e02', titulo:'Coordinador Logistico Portuario',    descripcion:'Coordinacion de operaciones de carga en el puerto.',    modalidad:'presencial', ciudad:'Barranquilla', salario_min:5000000, salario_max:7500000,  estado:'abierta', fecha_publicacion:'2026-10-01', fecha_cierre:'2026-11-20'},
  {id:'o07', empresa:'e07', publicada_por:'e07', titulo:'Analista de Comercio Exterior',      descripcion:'Gestion de exportaciones y documentacion aduanera.',    modalidad:'presencial', ciudad:'Barranquilla', salario_min:4500000, salario_max:6500000,  estado:'abierta', fecha_publicacion:'2026-10-12', fecha_cierre:'2026-12-12'},
  {id:'o08', empresa:'e03', publicada_por:'u17', titulo:'Enfermero/a Especialista UCI',       descripcion:'Cuidado de pacientes en unidad de cuidados intensivos.',modalidad:'presencial', ciudad:'Barranquilla', salario_min:4800000, salario_max:6800000,  estado:'abierta', fecha_publicacion:'2026-10-04', fecha_cierre:'2026-11-28'},
  {id:'o09', empresa:'e06', publicada_por:'e06', titulo:'Docente de Ingenieria de Sistemas',  descripcion:'Catedra en programacion y bases de datos.',             modalidad:'presencial', ciudad:'Puerto Colombia', salario_min:4000000, salario_max:6000000, estado:'abierta', fecha_publicacion:'2026-10-03', fecha_cierre:'2026-12-15'},
  {id:'o10', empresa:'e05', publicada_por:'e05', titulo:'Disenador UX/UI',                    descripcion:'Diseno de productos digitales para marcas regionales.', modalidad:'hibrida',    ciudad:'Barranquilla', salario_min:4500000, salario_max:7000000,  estado:'abierta', fecha_publicacion:'2026-10-07', fecha_cierre:'2026-11-27'},
  {id:'o11', empresa:'e05', publicada_por:'e05', titulo:'Especialista en Marketing Digital',  descripcion:'Planeacion y analitica de campanas.',                   modalidad:'hibrida',    ciudad:'Barranquilla', salario_min:4000000, salario_max:6000000,  estado:'abierta', fecha_publicacion:'2026-10-09', fecha_cierre:'2026-12-02'},
  {id:'o12', empresa:'e02', publicada_por:'e02', titulo:'DevOps Engineer',                    descripcion:'Infraestructura y despliegue de la plataforma logistica.',modalidad:'remota',   ciudad:'Barranquilla', salario_min:8000000, salario_max:12000000, estado:'abierta', fecha_publicacion:'2026-10-11', fecha_cierre:'2026-12-08'},
  {id:'o13', empresa:'e03', publicada_por:'u17', titulo:'Analista Administrativo Hospitalario',descripcion:'Gestion administrativa y facturacion hospitalaria.',   modalidad:'presencial', ciudad:'Barranquilla', salario_min:3800000, salario_max:5200000,  estado:'cerrada', fecha_publicacion:'2026-08-10', fecha_cierre:'2026-09-10'}
] AS f
MERGE (o:Oferta {id: f.id})
SET o.titulo = f.titulo,
    o.descripcion = f.descripcion,
    o.modalidad = f.modalidad,
    o.ciudad = f.ciudad,
    o.salario_min = f.salario_min,
    o.salario_max = f.salario_max,
    o.estado = f.estado,
    o.fecha_publicacion = date(f.fecha_publicacion),
    o.fecha_cierre = date(f.fecha_cierre)
WITH o, f
MATCH (e:Empresa {id: f.empresa})
MERGE (e)-[r:PUBLICA]->(o)
SET r.fecha = date(f.fecha_publicacion), r.publicada_por = f.publicada_por;

//Requiere
UNWIND [
  ['o01','h01',4,true],['o01','h02',3,true],['o01','h07',2,false],
  ['o02','h01',4,true],['o02','h02',4,true],['o02','h03',3,false],['o02','h25',3,false],['o02','h23',3,false],
  ['o03','h04',4,true],['o03','h05',4,true],['o03','h16',2,false],['o03','h22',3,false],
  ['o04','h09',4,true],['o04','h01',2,false],['o04','h23',3,false],
  ['o05','h08',4,true],['o05','h01',4,true],['o05','h02',3,true],['o05','h25',3,false],['o05','h23',3,false],
  ['o06','h13',4,true],['o06','h20',3,false],['o06','h10',3,true],['o06','h23',3,false],
  ['o07','h14',4,true],['o07','h10',3,true],['o07','h23',4,true],
  ['o08','h17',4,true],['o08','h22',4,true],['o08','h21',3,false],
  ['o09','h19',4,true],['o09','h01',3,false],['o09','h02',3,false],['o09','h23',3,false],
  ['o10','h16',4,true],['o10','h15',3,false],['o10','h04',2,false],['o10','h21',3,false],
  ['o11','h11',4,true],['o11','h25',3,false],['o11','h21',4,true],
  ['o12','h07',4,true],['o12','h01',3,true],['o12','h09',3,false],['o12','h23',3,false],
  ['o13','h18',4,true],['o13','h10',3,true],['o13','h24',3,false]
] AS t
MATCH (o:Oferta {id: t[0]}), (h:Habilidad {id: t[1]})
MERGE (o)-[r:REQUIERE]->(h)
SET r.nivel_minimo = t[2], r.obligatoria = t[3];

//Relacion Postula
UNWIND [
  ['u26','o01','enviada','2026-10-20'],
  ['u02','o02','en_revision','2026-10-18'],
  ['u03','o02','en_revision','2026-10-19'],
  ['u07','o02','enviada','2026-10-21'],
  ['u26','o03','enviada','2026-10-22'],
  ['u04','o04','en_revision','2026-10-17'],
  ['u18','o05','enviada','2026-10-23'],
  ['u07','o05','rechazada','2026-10-15'],
  ['u11','o06','en_revision','2026-10-16'],
  ['u11','o07','enviada','2026-10-24'],
  ['u19','o09','en_revision','2026-10-14'],
  ['u02','o09','enviada','2026-10-25'],
  ['u21','o10','rechazada','2026-10-12'],
  ['u25','o11','enviada','2026-10-26'],
  ['u23','o11','en_revision','2026-10-13'],
  ['u26','o12','enviada','2026-10-27'],
  ['u06','o12','rechazada','2026-10-11'],
  ['u16','o13','rechazada','2026-08-20']
] AS t
MATCH (u:Usuario {id: t[0]}), (o:Oferta {id: t[1]})
MERGE (u)-[r:POSTULA_A]->(o)
SET r.estado = t[2], r.fecha = date(t[3]);

//Notificaciones 
UNWIND [
  {id:'n01', para:'u05', tipo:'conexion_solicitud',  mensaje:'Tomas Navarro quiere conectar contigo.',                              leida:false, fecha:'2026-10-28T09:15:00', enlace:'/conexiones/solicitudes'},
  {id:'n02', para:'u08', tipo:'conexion_solicitud',  mensaje:'Andrea Castro quiere conectar contigo.',                              leida:false, fecha:'2026-10-29T10:00:00', enlace:'/conexiones/solicitudes'},
  {id:'n03', para:'u01', tipo:'conexion_solicitud',  mensaje:'Carlos Pacheco quiere conectar contigo.',                             leida:false, fecha:'2026-10-30T08:40:00', enlace:'/conexiones/solicitudes'},
  {id:'n04', para:'u02', tipo:'postulacion_estado',  mensaje:'Tu postulacion a "Ingeniero de Datos Senior" esta en revision.',      leida:true,  fecha:'2026-10-19T14:20:00', enlace:'/postulaciones'},
  {id:'n05', para:'u21', tipo:'postulacion_estado',  mensaje:'Tu postulacion a "Disenador UX/UI" fue rechazada.',                   leida:false, fecha:'2026-10-20T16:05:00', enlace:'/postulaciones'},
  {id:'n06', para:'u26', tipo:'oferta_afin',         mensaje:'Nueva oferta que coincide con tus habilidades: "Desarrollador Backend Python".', leida:false, fecha:'2026-10-05T08:00:00', enlace:'/ofertas/o01'},
  {id:'n07', para:'u07', tipo:'oferta_afin',         mensaje:'Nueva oferta que coincide con tus habilidades: "Cientifico de Datos".', leida:false, fecha:'2026-10-06T08:00:00', enlace:'/ofertas/o05'}
] AS f
MATCH (u:Usuario {id: f.para})
MERGE (n:Notificacion {id: f.id})
SET n.tipo = f.tipo, n.mensaje = f.mensaje, n.leida = f.leida,
    n.fecha = datetime(f.fecha), n.enlace = f.enlace
MERGE (n)-[:PARA]->(u);
