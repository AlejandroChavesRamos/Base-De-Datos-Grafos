"""Las pantallas no deben mostrar tarjetas vacías cuando hay otra información útil que mostrar."""
from datetime import date

import pytest
from neo4j.exceptions import AuthError, ServiceUnavailable

from app.database import db
from app.repositories import cuentas, red, usuarios

USUARIO = {"id": "u2", "nombre": "Luis", "apellido": "Paz", "titular": "Dev", "ciudad": "Cali"}
OFERTA = {"id": "o1", "titulo": "Backend", "modalidad": "remota", "ciudad": "Cali"}
EMPRESA = {"id": "e1", "nombre": "Caribe Labs"}


def _sesion(tipo, perfil_id):
    return {"tipo": tipo, "perfil_id": perfil_id, "perfil_nombre": "Caribe Labs", "cuenta_id": "c1", "csrf_token": "t",
            "roles": [tipo], "permisos": [], "email": "a@b.co"}


@pytest.fixture
def base(monkeypatch):
    def fijar(ruta, valor):
        monkeypatch.setattr(f"app.repositories.{ruta}", lambda *_a, **_k: valor)
    sesion = lambda _r: _sesion("persona", "u1")  # noqa: E731
    monkeypatch.setattr("app.dependencias.cuenta_opcional", sesion)
    monkeypatch.setattr("app.routers.paginas.cuenta_opcional", sesion)
    fijar("usuarios.resumen", {"id": "u1", "nombre": "Ana", "apellido": "Ruiz", "conexiones": 0, "postulaciones": 0})
    fijar("ofertas.recomendadas", [])
    fijar("ofertas.demanda_habilidades", [])
    fijar("red.actividad", [])
    fijar("red.sugerencias", [])
    fijar("red.colaboradores", [])
    fijar("usuarios.perfil_completo", {"usuario": USUARIO, "conexiones": 0, "empresa": None, "experiencia": [],
                                       "habilidades": [], "proyectos": []})
    fijar("usuarios.similares", [])
    fijar("usuarios.estado_relacion", "ninguna")
    fijar("usuarios.ruta", None)
    fijar("usuarios.contactos_en_comun", [])
    fijar("usuarios.habilidades_en_comun", [])
    fijar("empresas.obtener", {"empresa": {**EMPRESA, "descripcion": "x", "sector": "Salud", "ciudad": "Cali", "tamano": "mediana"},
                               "empleados": 0, "ofertas": [], "contactos": [], "camino": None})
    fijar("empresas.empleados", [])
    return fijar


# -------------------------------------------------------- sugerencias de personas
def test_sugerencias_se_completan_cuando_faltan_amigos_en_comun(monkeypatch):
    respuestas = [
        [{"usuario": {"id": "a"}, "amigos_comunes": 2, "habilidades_comunes": 0, "puntaje": 6}],
        [{"usuario": {"id": "b", "ciudad": "Cali"}, "amigos_comunes": 0, "habilidades_comunes": 3, "misma_ciudad": False, "puntaje": 6},
         {"usuario": {"id": "c", "ciudad": "Cali"}, "amigos_comunes": 0, "habilidades_comunes": 0, "misma_ciudad": True, "puntaje": 1},
         {"usuario": {"id": "d", "ciudad": "Lima"}, "amigos_comunes": 0, "habilidades_comunes": 0, "misma_ciudad": False, "puntaje": 0}],
    ]
    llamadas = []
    def leer(_consulta, **p):
        llamadas.append(p)
        return respuestas.pop(0)
    monkeypatch.setattr(red.db, "leer", leer)
    filas = red.sugerencias("u", 4)
    assert [f["usuario"]["id"] for f in filas] == ["a", "b", "c", "d"]
    assert [f["motivo"] for f in filas] == ["2 contactos en común", "3 habilidades en común", "También en Cali", "En Lima"]
    assert llamadas[1]["excluir"] == ["a"] and llamadas[1]["limite"] == 3


def test_sugerencias_llenas_no_hacen_otra_consulta(monkeypatch):
    llamadas = []
    def leer(_c, **_p):
        llamadas.append(1)
        return [{"usuario": {"id": "a"}, "amigos_comunes": 1, "habilidades_comunes": 0, "puntaje": 3}]
    monkeypatch.setattr(red.db, "leer", leer)
    filas = red.sugerencias("u", 1)
    assert len(llamadas) == 1
    assert filas[0]["motivo"] == "1 contacto en común"


def test_inicio_y_red_muestran_el_motivo(cliente, base):
    base("red.sugerencias", [{"usuario": USUARIO, "amigos_comunes": 0, "motivo": "También en Cali"}])
    base("red.solicitudes_recibidas", [])
    base("red.solicitudes_enviadas", [])
    base("red.conexiones", [])
    assert "También en Cali" in cliente.get("/").text
    html = cliente.get("/red").text
    assert "También en Cali" in html and "contactos en común" not in html


def test_sin_sugerencias_no_queda_tarjeta_vacia(cliente, base):
    html = cliente.get("/").text
    assert "Personas que quizás conozcas" not in html
    assert "Sin sugerencias por ahora" not in html


# -------------------------------------------------------- novedades
def test_actividad_usa_novedades_de_la_red_si_no_hay_contactos(monkeypatch):
    llamadas = []
    def leer(consulta, **_p):
        llamadas.append(consulta)
        if "toString(o.fecha_publicacion)" in consulta and "fecha_cierre" in consulta:
            return [{"tipo": "oferta", "fecha": "2026-02-01", "contacto": None, "empresa": EMPRESA, "oferta": OFERTA}]
        return []
    monkeypatch.setattr(red.db, "leer", leer)
    filas = red.actividad("u", 8)
    assert filas and filas[0]["contacto"] is None
    assert any("fecha_cierre" in c for c in llamadas), "las novedades solo deben incluir ofertas vigentes"


def test_inicio_muestra_novedades_sin_contacto(cliente, base):
    base("red.actividad", [
        {"tipo": "oferta", "fecha": "2026-02-01", "contacto": None, "empresa": EMPRESA, "oferta": OFERTA},
        {"tipo": "proyecto", "fecha": "2026-02-01", "contacto": None, "rol": None,
         "proyecto": {"id": "p1", "nombre": "Puerto", "descripcion": "Texto", "estado": "en_curso"}, "tecnologias": ["Python"]}])
    html = cliente.get("/").text
    assert "Caribe Labs" in html and "está contratando" in html
    assert "Puerto" in html and 'href="/proyectos"' in html
    assert "Tu red aún está tranquila" not in html


def test_sin_demanda_no_queda_tarjeta_vacia(cliente, base):
    assert "Habilidades más pedidas" not in cliente.get("/").text


def test_aviso_para_agregar_habilidades_cuando_nada_coincide(cliente, base):
    base("ofertas.recomendadas", [{"oferta": OFERTA, "empresa": EMPRESA, "cumple": 0, "total_req": 2, "contactos": [], "afinidad": 0}])
    html = cliente.get("/").text
    assert 'href="/perfil/editar#habilidades"' in html
    assert "Agrega tus habilidades" in html


def test_sin_aviso_de_habilidades_cuando_hay_afinidad(cliente, base):
    base("ofertas.recomendadas", [{"oferta": OFERTA, "empresa": EMPRESA, "cumple": 1, "total_req": 2, "contactos": [], "afinidad": 50}])
    assert "Agrega tus habilidades" not in cliente.get("/").text


# -------------------------------------------------------- perfil
def test_perfil_propio_invita_a_completar(cliente, base):
    base("usuarios.perfil_completo", {"usuario": {**USUARIO, "id": "u1"}, "conexiones": 0, "empresa": None, "experiencia": [], "habilidades": [], "proyectos": []})
    html = cliente.get("/perfil/u1").text
    assert 'href="/perfil/editar#experiencia"' in html
    assert 'href="/perfil/editar#habilidades"' in html
    assert 'href="/proyectos"' in html


def test_perfil_ajeno_oculta_secciones_vacias(cliente, base):
    html = cliente.get("/perfil/u2").text
    for texto in ("Sin experiencia registrada", "Sin habilidades", "Sin proyectos", "Sin perfiles similares",
                  "No hay una ruta de contactos", "Cómo estás conectado"):
        assert texto not in html, texto
    for titulo in ("<h2>Experiencia</h2>", "<h2>Habilidades</h2>", "<h2>Proyectos</h2>", "Perfiles similares"):
        assert titulo not in html, titulo


def test_similares_se_completan_con_la_red(monkeypatch):
    respuestas = [[], [{"usuario": {**USUARIO}, "habilidades_comunes": []}]]
    monkeypatch.setattr(usuarios.db, "leer", lambda _c, **_p: respuestas.pop(0))
    filas = usuarios.similares("u", 4)
    assert filas[0]["usuario"]["id"] == "u2"


def test_perfil_muestra_similares_por_ciudad(cliente, base):
    base("usuarios.similares", [{"usuario": USUARIO, "habilidades_comunes": []}])
    assert "En Cali" in cliente.get("/perfil/u2").text


# -------------------------------------------------------- empresa
def test_empresa_oculta_tarjetas_vacias_al_visitante(cliente, base):
    html = cliente.get("/empresa/e1").text
    for texto in ("Sin empleos abiertos", "Ningún contacto trabaja aquí", "Tu red todavía no llega", "Cómo llegas a esta empresa"):
        assert texto not in html, texto


def test_empresa_sin_contactos_muestra_a_su_gente(cliente, base):
    base("empresas.empleados", [{"usuario": USUARIO, "rol": "trabajador", "cargo": "Analista"}])
    html = cliente.get("/empresa/e1").text
    assert "Personas en esta empresa" in html and 'href="/perfil/u2"' in html
    assert "Analista" in html


def test_empresa_con_contactos_los_prefiere(cliente, base):
    base("empresas.obtener", {"empresa": {**EMPRESA, "descripcion": "x", "sector": "Salud", "ciudad": "Cali", "tamano": "mediana"},
                              "empleados": 1, "ofertas": [], "camino": {"saltos": 2, "ruta": ["Ana", "Luis", "Caribe Labs"]},
                              "contactos": [{"usuario": {"id": "u2", "nombre": "Luis", "apellido": "Paz"}, "cargo": "Dev"}]})
    html = cliente.get("/empresa/e1").text
    assert "Tus contactos aquí" in html and "Cómo llegas a esta empresa" in html
    assert "Personas en esta empresa" not in html


def test_empresa_propia_sin_empleos_invita_a_crear(cliente, monkeypatch, base):
    monkeypatch.setattr("app.dependencias.cuenta_opcional", lambda _r: {**_sesion("empresa", "e1"), "permisos": ["oferta.publicar"]})
    html = cliente.get("/empresa/e1").text
    assert 'href="/empresa/e1/ofertas/nueva"' in html
    assert "Publica tu primera oferta" in html


# -------------------------------------------------------- búsqueda
def _busqueda(monkeypatch, **grupos):
    monkeypatch.setattr("app.repositories.busqueda.buscar", lambda _q: {"personas": [], "empresas": [], "ofertas": [], **grupos})


def test_busqueda_oculta_grupos_vacios(cliente, base, monkeypatch):
    _busqueda(monkeypatch, empresas=[{"empresa": {**EMPRESA, "sector": "Salud", "ciudad": "Cali"}}])
    html = cliente.get("/buscar?q=x").text
    assert "Caribe Labs" in html
    assert "Sin personas" not in html and "Sin empleos" not in html and "<h2>Personas" not in html


def test_busqueda_sin_nada_da_un_solo_mensaje_con_salidas(cliente, base, monkeypatch):
    _busqueda(monkeypatch)
    html = cliente.get("/buscar?q=zzzz").text
    assert "Sin resultados para" in html and "zzzz" in html
    assert 'href="/empleos"' in html and 'href="/red"' in html
    assert "Sin empresas" not in html


# -------------------------------------------------------- bienvenida
def test_cuenta_nueva_recibe_notificacion_de_bienvenida(monkeypatch):
    consultas = []
    monkeypatch.setattr(cuentas.db, "escribir", lambda c, **_p: consultas.append(c) or [{"cuenta_id": "c"}])
    cuentas.crear_persona({})
    assert ":Notificacion" in consultas[0] and "'/perfil/editar'" in consultas[0], "debe crearse en la misma transacción"


def test_consultas_reales_de_respaldo_compilan_contra_neo4j():
    """Contra el Neo4j real y sin modificar nada: un usuario inexistente no debe romper las consultas."""
    try:
        db.verificar()
    except (ServiceUnavailable, AuthError):
        pytest.skip("Neo4j no está disponible")
    assert red.sugerencias("no-existe", 3) == []
    assert red.actividad("no-existe", 3) is not None
    assert usuarios.similares("no-existe", 3) == []
