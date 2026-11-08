"""Laboratorio de consultas (/consultas): las consultas que pide el documento, visibles y ejecutables.
Es solo para administracion (permiso 'consultas.ver'). Sin Neo4j: la sesion y las filas se simulan; lo que se
comprueba es quien lo ve, lo que SE MUESTRA y lo que SE ENVIA."""
import re

import pytest
from markupsafe import escape

from app.repositories import consultas_documento as cd
from app.services import laboratorio

TOKEN = "token-csrf"
PERMISOS_ADMIN = ["usuario.bloquear", "staff.gestionar", "sistema.auditar", "usuario.crear", "usuario.eliminar", "usuario.editar",
                  "catalogo.gestionar", "contenido.moderar", "analitica.administrar", "consultas.ver"]
PERMISOS_STAFF = ["usuario.bloquear", "contenido.moderar", "catalogo.gestionar"]
PERSONAS = [("u1", "Ana Ruiz"), ("u2", "Beto Paz"), ("u3", "Caro Rojo")]


def _sesion(tipo, permisos, perfil_id=None):
    return {"tipo": tipo, "perfil_id": perfil_id, "perfil_nombre": "Prueba", "cuenta_id": "c-yo", "csrf_token": TOKEN,
            "roles": [tipo], "permisos": list(permisos), "email": "yo@prueba.co"}


def _usr(id_="u2", nombre="Beto", **extra):
    return {"id": id_, "nombre": nombre, "apellido": "Paz", "titular": "Ingeniero", **extra}


# Filas de ejemplo con la forma EXACTA que devuelve cada consulta
FILAS = {
    "q1": [{"usuario": _usr(), "habilidades_comunes": ["Python", "SQL"], "similitud": 0.4}],
    "q2": [{"usuario": _usr("u3", "Caro")}],
    "q3": [{"ruta": ["Ana Ruiz", "Beto Paz", "Caribe Labs"], "saltos": 2}],
    "q4": [{"usuario": _usr(buscando_empleo=True), "n_cumple": 4, "total_req": 5, "habilidades": ["Python"], "contactos": ["Ana Ruiz"],
            "puntaje": 45, "postulado": False}],
    "q5": [{"proyecto_1": "Puerto", "proyecto_2": "Fraude", "tecnologias": ["Python"], "miembros": ["Ana Ruiz"], "afinidad": 3}],
    "q6": [{"habilidad": "Inglés", "categoria": "idioma", "ofertas": 7, "como_obligatoria": 3}],
    "a1": [{"usuario": _usr(pagerank=0.31), "conexiones": 9}],
    "a2": [{"comunidad": 12, "miembros": 3, "personas": ["Ana Ruiz", "Beto Paz"]}],
    "a3": [{"usuario": _usr(intermediacion=14.0), "conexiones": 4}],
    "r1": [{"usuario": _usr(), "amigos_comunes": 2, "habilidades_comunes": 1, "puntaje": 7}],
    "r2": [{"oferta": {"id": "o1", "titulo": "Backend"}, "empresa": "Caribe", "cumple": 3, "total_req": 4, "afinidad": 75, "contactos": []}],
    "r3": [{"usuario": _usr(), "proyectos_compartidos": ["Puerto"]}],
}
POR_TEXTO = {c["cypher"]: c["id"] for c in laboratorio.CONSULTAS}


@pytest.fixture
def ejecutadas():
    return []


@pytest.fixture
def como(monkeypatch, ejecutadas):
    def activar(tipo, permisos=(), perfil_id=None, filas=None):
        monkeypatch.setattr("app.dependencias.cuenta_opcional", lambda _r: _sesion(tipo, permisos, perfil_id))
        monkeypatch.setattr("app.dependencias.usuarios.resumen", lambda _id: {
            "id": _id, "nombre": "Ana", "apellido": "Ruiz", "titular": "T", "ciudad": "C", "empresa": None, "cargo": None,
            "rol_empresa": None, "conexiones": 0, "postulaciones": 0, "sin_leer": 0, "solicitudes": 0})
        monkeypatch.setattr("app.services.laboratorio.analitica.personas_visibles",
                            lambda: [{"id": i, "nombre": n.split()[0], "apellido": n.split()[1]} for i, n in PERSONAS])
        monkeypatch.setattr("app.services.laboratorio.perfiles.lista_empresas", lambda: [{"id": "e1", "nombre": "Caribe Labs"}, {"id": "e2", "nombre": "Otra"}])
        monkeypatch.setattr("app.services.laboratorio.moderacion.ofertas",
                            lambda: [{"oferta": {"id": "o-x", "titulo": "Backend", "estado": "abierta"}, "empresa": "Caribe", "postulantes": 0}])

        def correr(consulta, **params):
            ejecutadas.append((POR_TEXTO[consulta], params))
            return (filas or FILAS)[POR_TEXTO[consulta]], 3.2
        monkeypatch.setattr("app.services.laboratorio.cd.ejecutar", correr)
    return activar


# ---------------------------------------------------------- quien puede verlas
def test_sin_sesion_no_se_ve(cliente):
    r = cliente.get("/consultas")
    assert r.status_code == 303 and r.headers["location"].startswith("/login")


@pytest.mark.parametrize("tipo,permisos,perfil", [("persona", ["perfil.editar"], "u1"), ("empresa", ["oferta.publicar"], "e1"),
                                                   ("staff", PERMISOS_STAFF, None)])
def test_solo_el_admin_ve_las_consultas(cliente, como, ejecutadas, tipo, permisos, perfil):
    como(tipo, permisos, perfil)
    for url in ("/consultas", "/consultas?consulta=q6", "/consultas?consulta=q1&persona=u1"):
        r = cliente.get(url)
        assert r.status_code == 403
        assert "MATCH" not in r.text and "Cypher" not in r.text            # ni siquiera el texto de las consultas
    assert not ejecutadas


def test_el_admin_las_ve(cliente, como):
    como("admin", PERMISOS_ADMIN)
    r = cliente.get("/consultas")
    assert r.status_code == 200 and 'class="panel-interno"' in r.text


def test_el_acceso_depende_del_permiso_no_del_tipo_de_cuenta(cliente, como):
    como("persona", PERMISOS_ADMIN, "u1")            # una persona a la que se le dieron privilegios de admin
    assert cliente.get("/consultas").status_code == 200
    como("admin", ["usuario.bloquear"])              # y un admin al que se le quito ese permiso
    assert cliente.get("/consultas").status_code == 403


@pytest.mark.parametrize("tipo,permisos,perfil,visible", [("persona", ["perfil.editar"], "u1", False), ("empresa", ["oferta.publicar"], "e1", False),
                                                           ("staff", PERMISOS_STAFF, None, False), ("admin", PERMISOS_ADMIN, None, True)])
def test_el_enlace_del_menu_solo_aparece_a_quien_puede_entrar(cliente, como, monkeypatch, tipo, permisos, perfil, visible):
    como(tipo, permisos, perfil)
    monkeypatch.setattr("app.routers.paginas.red.solicitudes_recibidas", lambda *a: [])
    monkeypatch.setattr("app.routers.analitica.repo.estado_metricas", lambda: None)
    html = cliente.get("/cuenta").text
    assert ('href="/consultas"' in html) is visible


# ------------------------------------------------------------- lo que se muestra
def test_la_pagina_muestra_las_12_consultas_con_su_pregunta(cliente, como):
    como("admin", PERMISOS_ADMIN)
    html = cliente.get("/consultas").text
    assert len(re.findall(r'<article class="consulta"', html)) == 12
    for c in laboratorio.CONSULTAS:
        assert escape(c["pregunta"]) in html and f'id="{c["id"]}"' in html
    for grupo in ("Las seis preguntas del enunciado", "Analítica de la red", "Recomendaciones"):
        assert grupo in html


def test_las_preguntas_del_enunciado_estan_todas(cliente, como):
    como("admin", PERMISOS_ADMIN)
    html = cliente.get("/consultas").text
    for pregunta in ("¿Qué usuarios tienen habilidades similares?", "¿Qué contactos en común existen entre dos profesionales?",
                     "¿Cuál es la ruta más corta entre un usuario y una empresa?",
                     "¿Qué candidatos podrían recomendarse para una oferta según sus conexiones y competencias?",
                     "¿Qué proyectos comparten tecnologías o miembros relacionados?",
                     "¿Qué habilidades son las más demandadas en las ofertas?"):
        assert str(escape(pregunta)) in html


def test_el_texto_cypher_que_se_ve_es_exactamente_el_que_se_ejecuta(cliente, como, ejecutadas):
    como("admin", PERMISOS_ADMIN)
    html = cliente.get("/consultas").text
    for c in laboratorio.CONSULTAS:
        assert str(escape(c["cypher"])) in html, f"{c['id']}: el texto mostrado no coincide con el constante"
    for c in laboratorio.CONSULTAS:     # y lo que llega a Neo4j al ejecutar es ese mismo texto, sin tocar
        ejecutadas.clear()
        params = "&".join(f"{p['campo']}={'e1' if p['tipo'] == 'empresa' else ('o-x' if p['tipo'] == 'oferta' else 'u2')}" for p in c["parametros"])
        r = cliente.get(f"/consultas?consulta={c['id']}&{params}")
        assert r.status_code == 200 and ejecutadas and ejecutadas[0][0] == c["id"], c["id"]


def test_no_se_ejecuta_nada_al_abrir_la_pagina(cliente, como, ejecutadas):
    como("admin", PERMISOS_ADMIN)
    cliente.get("/consultas")
    assert not ejecutadas


def test_el_admin_elige_libremente_a_las_personas_de_las_consultas(cliente, como, ejecutadas):
    como("admin", PERMISOS_ADMIN)
    cliente.get("/consultas?consulta=q2&persona_a=u3&persona_b=u2")
    assert ejecutadas[-1] == ("q2", {"a": "u3", "b": "u2", "limite": 10})
    cliente.get("/consultas?consulta=q3&persona=u3&empresa=e2")
    assert ejecutadas[-1] == ("q3", {"id": "u3", "empresa": "e2", "limite": 10})
    cliente.get("/consultas?consulta=q4&oferta=o-x")
    assert ejecutadas[-1] == ("q4", {"oferta": "o-x", "limite": 10})
    html = cliente.get("/consultas").text
    assert all(f'name="{n}"' in html for n in ("persona", "persona_a", "persona_b", "empresa", "oferta"))


def test_cada_consulta_lista_sus_parametros_y_son_los_que_se_envian():
    for c in laboratorio.CONSULTAS:
        valores = {p["campo"]: "x" for p in c["parametros"]}
        enviados = set(c["armar"](valores)) | {"limite"}
        assert laboratorio.parametros_cypher(c) == enviados, c["id"]


def test_las_consultas_del_laboratorio_solo_leen_datos():
    prohibidas = re.compile(r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|CALL|LOAD)\b", re.I)
    constantes = {n: getattr(cd, n) for n in dir(cd) if n.isupper() and isinstance(getattr(cd, n), str)}
    assert len(constantes) == 13                                              # 12 del laboratorio + proyectos relacionados
    for nombre, texto in constantes.items():
        sin_comentarios = "\n".join(l for l in texto.splitlines() if not l.strip().startswith("//"))
        assert not prohibidas.search(sin_comentarios), f"{nombre} contiene una instruccion que escribe"


def test_las_consultas_que_muestran_personas_ocultan_cuentas_desactivadas():
    for nombre in ("Q1_SIMILARES", "Q2_COMUNES", "Q3_RUTA", "Q4_CANDIDATOS", "Q5_PROYECTOS", "Q6_DEMANDA", "A1_INFLUYENTES", "A2_COMUNIDADES",
                   "A3_PUENTES", "R1_CONTACTOS", "R2_EMPLEOS", "R3_COLABORADORES"):
        assert "activa: false" in getattr(cd, nombre), nombre


def test_el_laboratorio_solo_usa_transacciones_de_lectura(monkeypatch):
    usadas = []
    monkeypatch.setattr("app.repositories.consultas_documento.db.leer", lambda c, **p: usadas.append("leer") or [])
    monkeypatch.setattr("app.repositories.consultas_documento.db.escribir", lambda c, **p: usadas.append("escribir") or [])
    filas, ms = cd.ejecutar(cd.Q6_DEMANDA, limite=5)
    cd.colaboradores("u1"), cd.proyectos_relacionados("u1"), cd.candidatos("o1")
    assert set(usadas) == {"leer"} and filas == [] and ms >= 0


# ------------------------------------------------------------------ resultados
def test_los_parametros_del_formulario_se_validan_contra_las_opciones_ofrecidas(cliente, como, ejecutadas):
    como("admin", PERMISOS_ADMIN)
    assert "no es una opción válida" in cliente.get("/consultas?consulta=q1&persona=u999").text
    assert "Elige:" in cliente.get("/consultas?consulta=q1").text
    assert "no es una opción válida" in cliente.get("/consultas?consulta=q3&persona=u1&empresa=zzz").text
    assert "no es una opción válida" in cliente.get("/consultas?consulta=q4&oferta=o-inexistente").text
    assert "no es una opción válida" in cliente.get("/consultas?consulta=q1&persona=%27%20OR%201%3D1").text
    assert not ejecutadas


def test_consulta_desconocida_se_ignora(cliente, como, ejecutadas):
    como("admin", PERMISOS_ADMIN)
    assert cliente.get("/consultas?consulta=q99").status_code == 200 and not ejecutadas


@pytest.mark.parametrize("consulta,esperado", [
    ("q5", ["Puerto", "Fraude", "Afinidad"]), ("q6", ["Inglés", "Ofertas que la piden", ">7<"]),
    ("a1", ["Beto Paz", "0.310", "Conexiones"]), ("a2", ["12", "Ana Ruiz, Beto Paz"]), ("a3", ["14.00", "Intermediación"])])
def test_resultados_sin_parametros(cliente, como, consulta, esperado):
    como("admin", PERMISOS_ADMIN)
    r = cliente.get(f"/consultas?consulta={consulta}")
    bloque = r.text.split(f'data-resultado="{consulta}"')[1].split("</article>")[0]
    assert all(e in bloque for e in esperado)
    assert "1 fila ·" in bloque and "3 ms" in bloque


def test_resultado_con_enlaces_a_los_perfiles(cliente, como):
    como("admin", PERMISOS_ADMIN)
    bloque = cliente.get("/consultas?consulta=q1&persona=u1").text.split('data-resultado="q1"')[1].split("</article>")[0]
    assert '<a href="/perfil/u2">Beto Paz</a>' in bloque and "Python, SQL" in bloque and "0.40" in bloque
    assert "Ana Ruiz → Beto Paz → Caribe Labs" in cliente.get("/consultas?consulta=q3&persona=u1&empresa=e1").text


def test_q4_muestra_puntaje_y_si_ya_se_postulo(cliente, como):
    como("admin", PERMISOS_ADMIN)
    bloque = cliente.get("/consultas?consulta=q4&oferta=o-x").text.split('data-resultado="q4"')[1]
    assert "4 de 5" in bloque and ">45<" in bloque and "¿Ya se postuló?" in bloque


def test_sin_filas_se_explica_y_sin_metricas_se_indica_como_calcularlas(cliente, como):
    como("admin", PERMISOS_ADMIN, filas={**FILAS, "q1": [], "a1": []})
    assert "Sin resultados" in cliente.get("/consultas?consulta=q1&persona=u1").text
    assert "Sin métricas todavía" in cliente.get("/consultas?consulta=a1").text


def test_el_texto_que_viene_de_la_base_se_escapa(cliente, como):
    como("admin", PERMISOS_ADMIN, filas={**FILAS, "q6": [{"habilidad": "<script>alert(1)</script>", "categoria": "x", "ofertas": 1, "como_obligatoria": 0}]})
    html = cliente.get("/consultas?consulta=q6").text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_el_detalle_cypher_es_accesible_y_solo_la_consulta_activa_tiene_resultado(cliente, como):
    como("admin", PERMISOS_ADMIN)
    html = cliente.get("/consultas?consulta=q6").text
    assert html.count("<details class=\"cypher-detalle\">") == 12 and html.count('data-resultado=') == 1
    assert 'class="cypher" tabindex="0"' in html and "Ver la consulta Cypher" in html


# ---------------------------------------------------- recomendaciones en la app
def _sesion_persona(monkeypatch):
    monkeypatch.setattr("app.dependencias.cuenta_opcional", lambda _r: _sesion("persona", ["perfil.editar"], "u1"))
    monkeypatch.setattr("app.dependencias.usuarios.resumen", lambda _id: {"id": _id, "nombre": "Ana", "apellido": "R", "titular": "T", "ciudad": "C",
                        "empresa": None, "cargo": None, "rol_empresa": None, "conexiones": 0, "postulaciones": 0, "sin_leer": 0, "solicitudes": 0})


def test_candidatos_sugeridos_solo_buscan_empleo_y_no_se_han_postulado(monkeypatch):
    from app.repositories import ofertas
    filas = [{"usuario": _usr("a", "A", buscando_empleo=True), "postulado": False}, {"usuario": _usr("b", "B", buscando_empleo=False), "postulado": False},
             {"usuario": _usr("c", "C", buscando_empleo=True), "postulado": True}, {"usuario": _usr("d", "D", buscando_empleo=True), "postulado": False}]
    monkeypatch.setattr("app.repositories.ofertas._doc.candidatos", lambda oid, n: filas)
    assert [f["usuario"]["id"] for f in ofertas.candidatos_sugeridos("o1", 5)] == ["a", "d"]
    assert [f["usuario"]["id"] for f in ofertas.candidatos_sugeridos("o1", 1)] == ["a"]


def test_red_muestra_colaboradores_sugeridos_solo_si_hay(cliente, monkeypatch):
    _sesion_persona(monkeypatch)
    for n, v in [("solicitudes_recibidas", []), ("solicitudes_enviadas", []), ("sugerencias", []), ("conexiones", [])]:
        monkeypatch.setattr(f"app.routers.paginas.red.{n}", (lambda v: lambda *a: v)(v))
    monkeypatch.setattr("app.routers.paginas.red.colaboradores", lambda *a: [{"usuario": _usr(), "proyectos_compartidos": ["Puerto", "Fraude"]}])
    html = cliente.get("/red").text
    assert 'id="colaboradores"' in html and "Proyecto: Puerto, Fraude" in html
    monkeypatch.setattr("app.routers.paginas.red.colaboradores", lambda *a: [])
    assert 'id="colaboradores"' not in cliente.get("/red").text
