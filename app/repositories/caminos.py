"""Caminos desde una persona hasta otra persona, una empresa o una oferta.

Cubre el requisito "consultar caminos y conexiones entre usuarios, empresas y oportunidades laborales".
Usa las mismas consultas del documento (consultas_documento.py): C1, Q3 y C2.
"""
from app.database import db
from app.repositories import analitica, perfiles
from app.repositories import consultas_documento as _doc

LIMITE = 5   # rutas alternativas de la misma longitud minima


def a_persona(uid: str, destino: str):
    return _doc.ejecutar(_doc.C1_CAMINO_PERSONA, a=uid, b=destino, limite=LIMITE)[0]


def a_empresa(uid: str, empresa_id: str):
    return _doc.ejecutar(_doc.Q3_RUTA, id=uid, empresa=empresa_id, limite=LIMITE)[0]


def a_oferta(uid: str, oferta_id: str):
    return _doc.ejecutar(_doc.C2_CAMINO_OFERTA, id=uid, oferta=oferta_id, limite=LIMITE)[0]


# ---- listas para elegir el destino (solo lo visible: sin cuentas desactivadas ni ofertas vencidas) ----
def personas():
    return [(p["id"], f"{p['nombre']} {p['apellido']}") for p in analitica.personas_visibles()]


def empresas():
    return [(e["id"], e["nombre"]) for e in perfiles.lista_empresas()]


def ofertas():
    filas = db.leer(
        """
        MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {estado: 'abierta'})
        WHERE o.fecha_cierre >= date({timezone: 'America/Bogota'})
          AND NOT EXISTS { (:Cuenta {activa: false})-[:TIENE_PERFIL]->(e) }
        RETURN o.id AS id, o.titulo AS titulo, e.nombre AS empresa
        ORDER BY e.nombre, o.titulo
        LIMIT 300
        """
    )
    return [(f["id"], f"{f['titulo']} · {f['empresa']}") for f in filas]
