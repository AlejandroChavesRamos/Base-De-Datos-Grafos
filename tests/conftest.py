import os

from dotenv import load_dotenv

# Primero el .env, si existe; los valores por defecto solo aplican cuando no hay .env.
# El driver de Neo4j no conecta al crearse, así que la app se puede importar sin él.
load_dotenv()
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "sin-conexion")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def cliente():
    # Sin "with": no ejecuta el arranque de la app, que exige Neo4j encendido.
    return TestClient(app, follow_redirects=False)
