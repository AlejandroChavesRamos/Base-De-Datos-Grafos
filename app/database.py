import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


class Neo4jConexion:
    def __init__(self):
        self._database = os.getenv("NEO4J_DATABASE", "neo4j")
        self._driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")),
        )

    def verificar(self):
        self._driver.verify_connectivity()

    def cerrar(self):
        self._driver.close()

    def leer(self, consulta: str, **params):
        with self._driver.session(database=self._database) as sesion:
            return sesion.execute_read(
                lambda tx: [r.data() for r in tx.run(consulta, **params)]
            )

    def escribir(self, consulta: str, **params):
        with self._driver.session(database=self._database) as sesion:
            return sesion.execute_write(
                lambda tx: [r.data() for r in tx.run(consulta, **params)]
            )


db = Neo4jConexion()
