"""
generar_consultas.py

Regenera cypher/03_consultas.cypher a partir de las constantes de app/repositories/consultas_documento.py.
Esas constantes son EXACTAMENTE las consultas que ejecuta la aplicacion (y las que el admin ve en /consultas),
asi el "script de consultas" del documento nunca se desfasa de lo que hace el sistema.

Uso (desde la raiz del proyecto):
    python cypher/generar_consultas.py

No edites 03_consultas.cypher a mano: cambia la constante y vuelve a generarlo. Una prueba automatica
(tests/test_scripts_cypher.py) falla si el archivo y las constantes dejan de coincidir.
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
for _k, _v in {"NEO4J_URI": "bolt://localhost:7687", "NEO4J_USER": "neo4j", "NEO4J_PASSWORD": "x"}.items():
    os.environ.setdefault(_k, _v)   # el driver no se conecta al importarse: solo hacen falta los textos

from app.repositories import consultas_documento as cd  # noqa: E402
from app.services import laboratorio  # noqa: E402

DESTINO = RAIZ / "cypher" / "03_consultas.cypher"

CABECERA = """// =====================================================================
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
"""

APENDICE = """

// =====================================================================
// ESCRITURA (CRUD): sentencias equivalentes a las que ejecuta la aplicacion
// =====================================================================

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

// Solicitar una conexion: no a uno mismo, ni a un contacto, ni si ya hay una invitacion pendiente.
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

// Aceptar una invitacion: la invitacion se borra y nace CONECTA_CON (relacion simetrica)
MATCH (a:Usuario {id: 'u99'})-[s:SOLICITA_CONEXION]->(b:Usuario {id: 'u05'})
DELETE s
WITH a, b
WHERE NOT EXISTS { (a)-[:CONECTA_CON]-(b) }
CREATE (a)-[:CONECTA_CON {desde: date()}]->(b)
RETURN a.nombre, b.nombre;

// Postularse a una oferta: solo si esta abierta, vigente y una sola vez por persona
MATCH (u:Usuario {id: 'u99'}), (o:Oferta {id: 'o04', estado: 'abierta'})
WHERE o.fecha_cierre >= date({timezone: 'America/Bogota'}) AND NOT EXISTS { (u)-[:POSTULA_A]->(o) }
CREATE (u)-[:POSTULA_A {estado: 'enviada', fecha: date({timezone: 'America/Bogota'})}]->(o)
RETURN o.titulo;

// Eliminar (DETACH borra tambien sus relaciones)
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
"""


def generar() -> str:
    partes = [CABECERA]
    grupo_actual = None
    titulos = dict(laboratorio.GRUPOS)
    orden = {g: i for i, (g, _) in enumerate(laboratorio.GRUPOS)}
    for c in sorted(laboratorio.CONSULTAS, key=lambda c: orden[c["grupo"]]):   # estable: conserva el orden de cada grupo
        if c["grupo"] != grupo_actual:
            grupo_actual = c["grupo"]
            partes.append(f"\n// =====================================================================\n// {titulos[grupo_actual].upper()}\n// =====================================================================\n")
        partes.append(f"\n// ---------- {c['codigo']} ----------\n{c['cypher']};\n")
    partes.append("\n// =====================================================================\n// PAGINA PROYECTOS\n// =====================================================================\n")
    partes.append(f"\n// ---------- Proyectos relacionados con los tuyos ----------\n{cd.PROYECTOS_RELACIONADOS};\n")
    partes.append(APENDICE)
    return "".join(partes)


def main() -> None:
    DESTINO.write_text(generar(), encoding="utf-8", newline="\n")
    print(f"Escrito {DESTINO.relative_to(RAIZ)} ({len(generar().splitlines())} lineas)")


if __name__ == "__main__":
    main()
