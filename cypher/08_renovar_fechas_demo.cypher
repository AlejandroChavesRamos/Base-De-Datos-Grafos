// =====================================================================
// 08_renovar_fechas_demo.cypher  -  Renueva el plazo de las ofertas de demostracion
//
// Las ofertas abiertas de 02_datos.cypher cierran unos 2 o 3 meses despues de cargarlas. Cuando ese plazo
// se acerca, ejecuta este script para volver a darles el mismo margen desde HOY. No toca nada mas:
// solo cambia la fecha de cierre de las ofertas de demostracion que sigan ABIERTAS (una oferta que se
// cerro o que esta en borrador no se modifica, y tampoco las ofertas que publique cualquier usuario).
//
// Es seguro ejecutarlo todas las veces que haga falta:
//   python cypher/Ejecutar_cypher.py cypher/08_renovar_fechas_demo.cypher
// =====================================================================
UNWIND [
  ['o01', 73],
  ['o02', 78],
  ['o03', 83],
  ['o04', 68],
  ['o05', 74],
  ['o06', 63],
  ['o07', 85],
  ['o08', 71],
  ['o09', 88],
  ['o10', 70],
  ['o11', 75],
  ['o12', 81]
] AS par
MATCH (o:Oferta {id: par[0], estado: 'abierta'})
SET o.fecha_cierre = date({timezone: 'America/Bogota'}) + duration({days: par[1]});
