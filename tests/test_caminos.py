"""Requisito 7 del enunciado: consultar caminos y conexiones entre usuarios, empresas y oportunidades laborales.
Tambien: habilidades compartidas entre dos personas (perfil) y proyectos que comparten tecnologias o miembros.
Sin Neo4j: la sesion y las filas se simulan."""
from datetime import date

import pytest

TOKEN = "token-csrf"


def _sesion(tipo, perfil_id=None):
    return {"tipo": tipo, "perfil_id": perfil_id, "perfil_nombre": "Prueba", "cuenta_id": "c-yo", "csrf_token": TOKEN,
            "roles": [tipo], "permisos": ["oferta.publicar"] if tipo == "empresa" else [], "email": "yo@prueba.co"}


def _resumen(_id):
    return {"id": _id, "nombre": "Ana", "apellido": "Ruiz", "titular": "T", "ciudad": "C", "empresa": None, "cargo": None, "rol_empresa": None,
            "conexiones": 0, "postulaciones": 0, "sin_leer": 0, "solicitudes": 0}


@pytest.fixture
def llamadas():
    return []


@pytest.fixture
def como(monkeypatch, llamadas):
    def activar(tipo="persona", perfil_id="u1"):
        monkeypatch.setattr("app.dependencias.cuenta_opcional", lambda _r: _sesion(tipo, perfil_id))
        monkeypatch.setattr("app.dependencias.usuarios.resumen", _resumen)
        monkeypatch.setattr("app.routers.caminos.repo.personas", lambda: [("u1", "Ana Ruiz"), ("u2", "Beto Paz"), ("u3", "Caro Rojo")])
        monkeypatch.setattr("app.routers.caminos.repo.empresas", lambda: [("e1", "Caribe Labs"), ("e2", "Otra")])
        monkeypatch.setattr("app.routers.caminos.repo.ofertas", lambda: [("o1", "Backend · Caribe Labs")])
    return activar


def _rutas(monkeypatch, llamadas, rutas):
    """Simula las tres consultas de caminos y anota con que origen y destino se llaman."""
    for nombre in ("a_persona", "a_empresa", "a_oferta"):
        monkeypatch.setattr(f"app.routers.caminos.repo.{nombre}", (lambda n: lambda uid, destino: llamadas.append((n, uid, destino)) or rutas)(nombre))
    # TIPOS guarda las funciones originales: se reconstruye con las simuladas
    import app.routers.caminos as r
    monkeypatch.setattr(r, "TIPOS", {k: (t, p, getattr(r.repo, f)) for (k, (t, p, _), f) in
                                     zip(r.TIPOS, [(k, v, None) for k, v in r.TIPOS.items()], ("a_persona", "a_empresa", "a_oferta"))})


RUTA = [{"ruta": ["Ana Ruiz", "Beto Paz", "Caribe Labs"], "saltos": 2}]


# ---------------------------------------------------------------- explorador
def test_el_explorador_exige_sesion(cliente):
    r = cliente.get("/caminos")
    assert r.status_code == 303 and r.headers["location"].startswith("/login")


@pytest.mark.parametrize("tipo,perfil,destino", [("empresa", "e1", "/empresa/e1"), ("staff", None, "/admin"), ("admin", None, "/admin")])
def test_solo_las_personas_tienen_explorador_de_caminos(cliente, como, tipo, perfil, destino):
    como(tipo, perfil)
    r = cliente.get("/caminos")
    assert r.status_code == 303 and r.headers["location"] == destino


def test_la_pagina_ofrece_los_tres_destinos_sin_ejecutar_nada(cliente, como, monkeypatch, llamadas):
    como("persona", "u1")
    _rutas(monkeypatch, llamadas, RUTA)
    html = cliente.get("/caminos").text
    assert all(f'data-camino="{t}"' in html for t in ("persona", "empresa", "oferta"))
    assert 'class="panel-interno"' in html and 'href="/caminos"' in html
    assert 'value="u2"' in html and 'value="u3"' in html and 'value="u1"' not in html      # una persona no puede ser su propio destino
    assert 'value="e1"' in html and 'value="o1"' in html
    assert not llamadas


@pytest.mark.parametrize("tipo,destino,funcion", [("persona", "u2", "a_persona"), ("empresa", "e1", "a_empresa"), ("oferta", "o1", "a_oferta")])
def test_cada_destino_usa_su_consulta_y_siempre_parte_de_quien_tiene_la_sesion(cliente, como, monkeypatch, llamadas, tipo, destino, funcion):
    como("persona", "u3")
    _rutas(monkeypatch, llamadas, RUTA)
    r = cliente.get(f"/caminos?tipo={tipo}&destino={destino}&id=u1&a=u1&origen=u1")        # intenta cambiar el origen por la URL
    assert r.status_code == 200 and llamadas == [(funcion, "u3", destino)]


@pytest.mark.parametrize("url,mensaje", [
    ("/caminos?tipo=inventado&destino=u2", "Elige a dónde quieres llegar"),
    ("/caminos?tipo=persona", "Elige un destino de la lista"),
    ("/caminos?tipo=persona&destino=", "Elige un destino de la lista"),
    ("/caminos?tipo=persona&destino=u1", "no es una opción válida"),                  # uno mismo
    ("/caminos?tipo=persona&destino=u999", "no es una opción válida"),
    ("/caminos?tipo=empresa&destino=o1", "no es una opción válida"),                 # id de oferta en el selector de empresas
    ("/caminos?tipo=oferta&destino=o-vencida", "no es una opción válida"),           # no esta entre las ofertas abiertas
    ("/caminos?tipo=persona&destino=%27%20OR%201%3D1", "no es una opción válida")])
def test_un_destino_invalido_se_rechaza_sin_consultar_la_base(cliente, como, monkeypatch, llamadas, url, mensaje):
    como()
    _rutas(monkeypatch, llamadas, RUTA)
    r = cliente.get(url)
    assert r.status_code == 200 and mensaje in r.text and not llamadas


def test_la_ruta_se_muestra_con_tu_como_origen_y_el_grado(cliente, como, monkeypatch, llamadas):
    como()
    _rutas(monkeypatch, llamadas, [{"ruta": ["Ana Ruiz", "Beto Paz", "Caro Rojo"], "saltos": 2},
                                   {"ruta": ["Ana Ruiz", "Dani Gil", "Caro Rojo"], "saltos": 2}])
    html = cliente.get("/caminos?tipo=persona&destino=u3").text
    bloque = html.split('data-resultado="persona"')[1].split("</section>")[0]
    assert bloque.count("data-ruta") == 2 and "2 rutas de 2 saltos" in bloque and "2º grado de conexión" in bloque
    assert ">Tú<" in bloque and "Ana Ruiz" not in bloque.split("data-ruta")[1]       # el primero siempre es "Tú", no el nombre
    assert "Beto Paz" in bloque and "Dani Gil" in bloque and "Caro Rojo" in bloque


def test_el_camino_a_una_oferta_termina_en_la_oferta(cliente, como, monkeypatch, llamadas):
    como()
    _rutas(monkeypatch, llamadas, [{"ruta": ["Ana Ruiz", "Beto Paz", "Caribe Labs"], "saltos": 3, "oferta": "Backend"}])
    bloque = cliente.get("/caminos?tipo=oferta&destino=o1").text.split('data-resultado="oferta"')[1].split("</section>")[0]
    assert "Caribe Labs" in bloque and "Oferta: Backend" in bloque and "3 saltos" in bloque and "grado de conexión" not in bloque


def test_sin_camino_se_explica_que_hacer(cliente, como, monkeypatch, llamadas):
    como()
    _rutas(monkeypatch, llamadas, [])
    bloque = cliente.get("/caminos?tipo=empresa&destino=e2").text.split('data-resultado="empresa"')[1].split("</section>")[0]
    assert "Sin camino todavía" in bloque and "Otra" in bloque and "data-ruta" not in bloque


def test_los_nombres_del_camino_se_escapan(cliente, como, monkeypatch, llamadas):
    como()
    _rutas(monkeypatch, llamadas, [{"ruta": ["Ana", "<script>alert(1)</script>", "Caro"], "saltos": 2}])
    html = cliente.get("/caminos?tipo=persona&destino=u3").text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_los_caminos_usan_las_consultas_del_documento_con_los_parametros_correctos(monkeypatch):
    from app.repositories import caminos, consultas_documento as cd
    vistas = []
    monkeypatch.setattr("app.repositories.caminos._doc.ejecutar", lambda texto, **p: vistas.append((texto, p)) or ([], 1.0))
    caminos.a_persona("u1", "u2"), caminos.a_empresa("u1", "e1"), caminos.a_oferta("u1", "o1")
    assert vistas == [(cd.C1_CAMINO_PERSONA, {"a": "u1", "b": "u2", "limite": 5}), (cd.Q3_RUTA, {"id": "u1", "empresa": "e1", "limite": 5}),
                      (cd.C2_CAMINO_OFERTA, {"id": "u1", "oferta": "o1", "limite": 5})]


def test_las_ofertas_del_selector_son_solo_abiertas_vigentes_y_de_empresas_activas(monkeypatch):
    from app.repositories import caminos
    textos = []
    monkeypatch.setattr("app.repositories.caminos.db.leer", lambda q, **p: textos.append(q) or [{"id": "o1", "titulo": "Backend", "empresa": "Caribe"}])
    assert caminos.ofertas() == [("o1", "Backend · Caribe")]
    assert "estado: 'abierta'" in textos[0] and "fecha_cierre >= date(" in textos[0] and "activa: false" in textos[0]


# ------------------------------------------------- ruta hasta una oferta (empleos)
def _empleos(monkeypatch, camino, llamadas):
    detalle = {"oferta": {"id": "o1", "titulo": "Backend", "ciudad": "Cali", "modalidad": "remota", "estado": "abierta", "fecha_publicacion": date(2026, 1, 1),
                          "fecha_cierre": date(2099, 1, 1), "salario_min": 1000, "salario_max": 2000, "descripcion": "Texto"},
               "empresa": {"id": "e1", "nombre": "Caribe Labs"}, "n_postulantes": 0, "postulacion": None, "contactos": [], "requisitos": []}
    monkeypatch.setattr("app.routers.paginas.ofertas.recomendadas", lambda *a: [{"oferta": detalle["oferta"], "empresa": detalle["empresa"], "total_req": 0, "cumple": 0,
                                                                              "cumplidas": [], "faltan": [], "afinidad": 0, "contactos": [], "postulacion": None}])
    monkeypatch.setattr("app.routers.paginas.ofertas.detalle", lambda *a: detalle)
    monkeypatch.setattr("app.routers.paginas.ofertas.mis_postulaciones", lambda *a: [])
    monkeypatch.setattr("app.routers.paginas.ofertas.camino_a_oferta", lambda uid, oid: llamadas.append((uid, oid)) or camino)


def test_la_oferta_muestra_el_camino_hasta_ella(cliente, como, monkeypatch, llamadas):
    como("persona", "u7")
    _empleos(monkeypatch, {"ruta": ["Ana Ruiz", "Beto Paz", "Caribe Labs"], "saltos": 3, "oferta": "Backend"}, llamadas)
    html = cliente.get("/empleos?oferta=o1").text
    bloque = html.split('id="camino-oferta"')[1].split("</article>")[0]
    assert "Cómo llegas a esta oferta" in bloque and "3 saltos" in bloque and ">Tú<" in bloque and "Beto Paz" in bloque and "Oferta: Backend" in bloque
    assert 'href="/caminos?tipo=oferta&destino=o1#camino-oferta"' in bloque
    assert llamadas == [("u7", "o1")]                                              # con quien tiene la sesion como origen


def test_si_ya_trabajas_en_la_empresa_lo_dice(cliente, como, monkeypatch, llamadas):
    como()
    _empleos(monkeypatch, {"ruta": ["Ana Ruiz", "Caribe Labs"], "saltos": 2, "oferta": "Backend"}, llamadas)
    assert "Ya trabajas en la empresa que la publica" in cliente.get("/empleos?oferta=o1").text


def test_sin_ruta_la_oferta_lo_explica(cliente, como, monkeypatch, llamadas):
    como()
    _empleos(monkeypatch, None, llamadas)
    bloque = cliente.get("/empleos?oferta=o1").text.split('id="camino-oferta"')[1].split("</article>")[0]
    assert "Tu red todavía no llega a Caribe Labs" in bloque and "data-ruta" not in bloque


# ------------------------------------------------ habilidades compartidas (perfil)
def _perfil(monkeypatch, comunes, llamadas):
    datos = {"usuario": {"id": "u2", "nombre": "Beto", "apellido": "Paz", "titular": "Dev", "ciudad": "Cali", "resumen": "", "experiencia_anios": 3,
                         "buscando_empleo": False}, "empresa": None, "cargo": None, "conexiones": 1, "experiencia": [], "habilidades": [], "proyectos": []}
    monkeypatch.setattr("app.routers.paginas.usuarios.perfil_completo", lambda uid: datos)
    monkeypatch.setattr("app.routers.paginas.usuarios.estado_relacion", lambda a, b: "ninguna")
    monkeypatch.setattr("app.routers.paginas.usuarios.ruta", lambda a, b: None)
    monkeypatch.setattr("app.routers.paginas.usuarios.contactos_en_comun", lambda a, b: [])
    monkeypatch.setattr("app.routers.paginas.usuarios.similares", lambda uid, n: [])
    monkeypatch.setattr("app.routers.paginas.usuarios.habilidades_en_comun", lambda a, b: llamadas.append((a, b)) or comunes)


def test_el_perfil_de_otra_persona_muestra_las_habilidades_en_comun_con_quien_mira(cliente, como, monkeypatch, llamadas):
    como("persona", "u7")
    _perfil(monkeypatch, [{"habilidad": "Python", "categoria": "tecnica", "nivel_a": 5, "nivel_b": 3},
                          {"habilidad": "SQL", "categoria": "tecnica", "nivel_a": 2, "nivel_b": 4}], llamadas)
    html = cliente.get("/perfil/u2").text
    bloque = html.split('id="habilidades-comunes"')[1].split("</section>")[0]
    assert "Habilidades en común contigo" in bloque and "Python" in bloque and "SQL" in bloque
    assert "Tú: Experto" in bloque and "Beto: Competente" in bloque and "Tú: Intermedio" in bloque and "Beto: Avanzado" in bloque
    assert llamadas == [("u7", "u2")]


def test_sin_habilidades_en_comun_lo_dice(cliente, como, monkeypatch, llamadas):
    como()
    _perfil(monkeypatch, [], llamadas)
    assert "No comparten habilidades registradas todavía" in cliente.get("/perfil/u2").text


def test_el_perfil_propio_y_el_de_las_empresas_no_calculan_habilidades_en_comun(cliente, como, monkeypatch, llamadas):
    como()
    _perfil(monkeypatch, [{"habilidad": "Python", "categoria": "tecnica", "nivel_a": 5, "nivel_b": 3}], llamadas)
    assert 'id="habilidades-comunes"' not in cliente.get("/perfil/u1").text and not llamadas
    como("empresa", "e1")
    assert 'id="habilidades-comunes"' not in cliente.get("/perfil/u2").text and not llamadas


# ------------------------------------------------ Q5 visible en la pagina de proyectos
def _proyectos(monkeypatch, afines):
    monkeypatch.setattr("app.routers.acciones.perfiles.listar_proyectos", lambda uid: [])
    monkeypatch.setattr("app.routers.acciones.perfiles.catalogo_habilidades", lambda: [])
    monkeypatch.setattr("app.routers.acciones.perfiles.proyectos_relacionados", lambda uid, n: [])
    monkeypatch.setattr("app.routers.acciones.perfiles.proyectos_afines", lambda n: afines)


def test_proyectos_muestra_los_pares_que_comparten_tecnologias_o_miembros(cliente, como, monkeypatch):
    como()
    _proyectos(monkeypatch, [{"proyecto_1": "Puerto", "proyecto_2": "Fraude", "tecnologias": ["Python", "SQL"], "miembros": ["Ana Ruiz"], "afinidad": 4},
                             {"proyecto_1": "Portal", "proyecto_2": "Cursos", "tecnologias": [], "miembros": [], "afinidad": 1}])
    html = cliente.get("/proyectos").text
    tabla = html.split('data-tabla="afines"')[1].split("</table>")[0]
    assert "Puerto" in tabla and "Fraude" in tabla and "Python, SQL" in tabla and "Ana Ruiz" in tabla and ">4<" in tabla
    assert "Proyectos que comparten tecnologías o miembros" in html


def test_sin_pares_afines_no_se_muestra_la_seccion(cliente, como, monkeypatch):
    como()
    _proyectos(monkeypatch, [])
    assert 'id="afines"' not in cliente.get("/proyectos").text
