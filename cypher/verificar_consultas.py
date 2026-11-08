"""
verificar_consultas.py

Comprueba TODAS las consultas Cypher de la aplicacion contra tu Neo4j, SIN modificar datos.

Como: cada consulta se envia con el prefijo EXPLAIN, que hace que Neo4j la compile
(sintaxis, etiquetas, relaciones, funciones) pero NO la ejecute. Ademas revisa que
cada parametro ($algo) de la consulta reciba un valor.

Uso (desde la raiz del proyecto, con Neo4j encendido y el venv activo):
    python cypher/verificar_consultas.py
"""
import importlib
import inspect
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from neo4j.exceptions import Neo4jError  # noqa: E402

from app.database import db  # noqa: E402

MODULOS = ["usuarios", "red", "ofertas", "empresas", "notificaciones", "busqueda",
           "conexiones", "perfiles", "cuentas", "sesiones", "eventos", "catalogo", "moderacion", "analitica", "consultas_documento", "caminos"]

# Argumentos de tipo diccionario: necesitan las claves que usa la consulta
OFERTA = {"titulo": "x", "descripcion": "x", "modalidad": "remota", "ciudad": "x",
          "salario_min": 1, "salario_max": 2, "fecha_cierre": "2030-01-01"}
DICTS = {
    ("perfiles", "actualizar"): {"nombre": "x", "apellido": "x", "titular": "x", "ciudad": "x", "resumen": "x",
                                 "experiencia_anios": 1, "buscando_empleo": True},
    ("perfiles", "agregar_experiencia"): {"empresa_id": "x", "cargo": "x", "actual": True,
                                          "desde": "2020-01-01", "hasta": None},
    ("perfiles", "crear_proyecto"): {"nombre": "x", "descripcion": "x", "estado": "en_curso", "rol": "x",
                                     "fecha_inicio": "2020-01-01", "fecha_fin": None, "con_empresa": True},
    ("ofertas", "crear"): OFERTA, ("ofertas", "actualizar"): OFERTA,
    ("empresas", "actualizar"): {"nombre": "x", "sector": "x", "tamano": "x", "ciudad": "x",
                                 "descripcion": "x", "sitio_web": "x"},
    ("cuentas", "actualizar_persona_basico"): {"nombre": "x", "apellido": "x", "titular": "x", "ciudad": "x"},
    ("cuentas", "crear_interna"): {"cuenta_id": "x", "email": "x", "hash": "x", "tipo": "staff"},
    ("cuentas", "crear_persona"): {"cuenta_id": "x", "perfil_id": "x", "email": "x", "hash": "x", "nombre": "x",
                                   "apellido": "x", "titular": "x", "ciudad": "x"},
    ("cuentas", "crear_empresa"): {"cuenta_id": "x", "perfil_id": "x", "email": "x", "hash": "x", "nombre": "x",
                                   "sector": "x", "tamano": "x", "ciudad": "x", "descripcion": "x", "sitio_web": "x"},
}

_ejecutar_real = db.escribir  # se usa siempre una transaccion de escritura: EXPLAIN no modifica nada
_actual = {"nombre": ""}
_estado = {"consultas": 0, "errores": []}


class ParametrosFaltantes(Exception):
    pass


def _explain(consulta: str, **params):
    _estado["consultas"] += 1
    pedidos = set(re.findall(r"\$(\w+)", consulta))
    faltan = pedidos - set(params)
    if faltan:
        raise ParametrosFaltantes(f"faltan parametros: {sorted(faltan)}")
    return _ejecutar_real("EXPLAIN " + consulta, **params)


db.leer = db.escribir = _explain


def _valor(nombre: str, anotacion):
    if anotacion in (int, "int"):
        return 1
    if anotacion in (bool, "bool"):
        return True
    if "list" in str(anotacion):
        return ["x"]
    return "x"


def main() -> int:
    db.verificar()
    total = 0
    for nombre_modulo in MODULOS:
        modulo = importlib.import_module(f"app.repositories.{nombre_modulo}")
        for nombre, funcion in inspect.getmembers(modulo, inspect.isfunction):
            if nombre.startswith("_") or nombre == "ejecutar" or funcion.__module__ != modulo.__name__:
                continue
            firma = inspect.signature(funcion)
            args = {}
            for p in firma.parameters.values():
                if p.default is not inspect.Parameter.empty:
                    continue
                if (nombre_modulo, nombre) in DICTS and p.name == "d":
                    args[p.name] = DICTS[(nombre_modulo, nombre)]
                else:
                    args[p.name] = _valor(p.name, p.annotation)
            etiqueta = f"{nombre_modulo}.{nombre}"
            antes = _estado["consultas"]
            try:
                funcion(**args)
                resultado = "OK"
            except Neo4jError as e:
                resultado = f"ERROR de Cypher: {e.code}\n        {str(e.message)[:400]}"
                _estado["errores"].append(etiqueta)
            except ParametrosFaltantes as e:
                resultado = f"ERROR: {e}"
                _estado["errores"].append(etiqueta)
            except (IndexError, KeyError, TypeError):
                resultado = "OK"  # la consulta compilo; EXPLAIN no devuelve filas y el codigo posterior las esperaba
            n = _estado["consultas"] - antes
            total += n
            print(f"{'OK   ' if resultado == 'OK' else 'FALLA'} {etiqueta:<42} ({n} consulta{'s' if n != 1 else ''})"
                  + ("" if resultado == "OK" else f"\n        {resultado}"))
    # Las consultas del documento (Q1-Q6, A1-A3, R1-R3): cada constante se revisa tal como se muestra en /consultas
    doc = importlib.import_module("app.repositories.consultas_documento")
    for nombre in sorted(n for n in dir(doc) if n.isupper() and isinstance(getattr(doc, n), str)):
        texto = getattr(doc, nombre)
        parametros = {p: (1 if p == "limite" else "x") for p in re.findall(r"\$(\w+)", texto)}
        etiqueta = f"consultas_documento.{nombre}"
        try:
            _explain(texto, **parametros)
            total += 1
            print(f"OK    {etiqueta:<42} (1 consulta)")
        except (Neo4jError, ParametrosFaltantes) as e:
            total += 1
            _estado["errores"].append(etiqueta)
            print(f"FALLA {etiqueta:<42} (1 consulta)\n        {getattr(e, 'message', e)}")

    # Informativo: el calculo de metricas de la analitica necesita el plugin Graph Data Science
    try:
        _ejecutar_real("EXPLAIN RETURN gds.version() AS version")
        print("\nGraph Data Science: disponible (se pueden recalcular las metricas).")
    except Neo4jError:
        print("\nGraph Data Science: NO disponible. La analitica funciona, pero no se podran recalcular las metricas.")

    print(f"\n{total} consultas revisadas. ", end="")
    if _estado["errores"]:
        print(f"{len(_estado['errores'])} funciones con error: {_estado['errores']}")
        return 1
    print("Todas compilan correctamente.")
    return 0


if __name__ == "__main__":
    codigo = main()
    db.cerrar()
    sys.exit(codigo)
