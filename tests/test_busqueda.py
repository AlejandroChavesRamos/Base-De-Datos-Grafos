import pytest
from neo4j.exceptions import AuthError, ServiceUnavailable

from app.database import db
from app.repositories import busqueda


@pytest.mark.parametrize("entrada, esperado", [
    ("Tecnología", "tecnologia"),
    ("TECNOLOGÍA", "tecnologia"),
    ("tecnologia", "tecnologia"),
    ("Diseño", "diseno"),
    ("Educación Pública", "educacion publica"),
    ("Güiro", "guiro"),
    ("Tecnología", "tecnologia"),  # tilde escrita como carácter aparte
])
def test_sin_tildes(entrada, esperado):
    assert busqueda.sin_tildes(entrada) == esperado


def test_la_consulta_recibe_el_texto_sin_tildes(monkeypatch):
    llamadas = []
    monkeypatch.setattr(busqueda.db, "leer", lambda consulta, **p: llamadas.append(p) or [])
    busqueda.buscar("  Tecnología ")
    assert len(llamadas) == 3
    assert all(p["q"] == "tecnologia" and p["marcas"] for p in llamadas)


def test_todas_las_consultas_ignoran_tildes(monkeypatch):
    consultas = []
    monkeypatch.setattr(busqueda.db, "leer", lambda consulta, **_p: consultas.append(consulta) or [])
    busqueda.buscar("x")
    assert all("normalize(" in c and "$marcas" in c for c in consultas)


def test_texto_solo_con_marcas_no_devuelve_todo(monkeypatch):
    def falla(*_a, **_k):
        raise AssertionError("no debe consultar la base")
    monkeypatch.setattr(busqueda.db, "leer", falla)
    assert busqueda.buscar("́") == {"personas": [], "empresas": [], "ofertas": []}


def test_cypher_y_python_quitan_lo_mismo():
    """Contra el Neo4j real: si esta expresión falla, ninguna búsqueda funciona."""
    try:
        db.verificar()
    except (ServiceUnavailable, AuthError):
        pytest.skip("Neo4j no está disponible")
    consulta = f"RETURN {busqueda.expresion_sin_tildes('$texto')} AS r"
    for texto in ("Tecnología", "TECNOLOGÍA", "Diseño", "Educación", "Logística", "Güiro", "Peña Ñandú", "São Paulo",
                  "François", "tecnologia"):
        r = db.leer(consulta, texto=texto, marcas=busqueda.MARCAS)[0]["r"]
        assert r == busqueda.sin_tildes(texto), texto


# ------------------------------------------------------------ página completa
@pytest.fixture
def persona_con_resultados(monkeypatch):
    monkeypatch.setattr("app.dependencias.cuenta_opcional", lambda _r: {
        "tipo": "persona", "perfil_id": "u1", "perfil_nombre": "A", "cuenta_id": "c1", "csrf_token": "t",
        "roles": ["persona"], "permisos": [], "email": "a@b.co"})
    monkeypatch.setattr("app.repositories.usuarios.resumen", lambda _i: {"id": "u1", "nombre": "Ana", "apellido": "Ruiz"})
    monkeypatch.setattr(busqueda, "buscar", lambda _q: {
        "personas": [{"usuario": {"id": "u2", "nombre": "Luis", "apellido": "Paz", "titular": "Dev", "ciudad": "Cali"}}],
        "empresas": [{"empresa": {"id": "e1", "nombre": "Caribe Labs", "sector": "Tecnología", "ciudad": "Barranquilla"}}],
        "ofertas": [{"oferta": {"id": "o1", "titulo": "Backend", "estado": "abierta", "ciudad": "Cali"}, "empresa": "Caribe Labs"}]})


def test_la_pagina_muestra_los_resultados(cliente, persona_con_resultados):
    html = cliente.get("/buscar?q=tecnologia").text
    assert 'href="/perfil/u2"' in html
    assert 'href="/empresa/e1"' in html
    assert 'href="/empleos?oferta=o1"' in html
    assert "Sin empresas" not in html


def test_sin_texto_invita_a_buscar(cliente, persona_con_resultados):
    html = cliente.get("/buscar").text
    assert "Busca en LinkedUn" in html
    assert "Sin empresas" not in html
