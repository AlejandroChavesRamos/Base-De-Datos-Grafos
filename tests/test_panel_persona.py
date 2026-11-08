import re
from datetime import date
from pathlib import Path

import pytest

RESUMEN = {"id": "u1", "nombre": "Ana", "apellido": "Ruiz", "titular": "Analista", "conexiones": 4, "postulaciones": 1,
           "solicitudes": 1, "sin_leer": 2}


def _sesion(tipo, permisos=(), perfil_id=None):
    return {"tipo": tipo, "perfil_id": perfil_id, "perfil_nombre": "Prueba", "cuenta_id": "c-yo",
            "csrf_token": "token-csrf", "roles": [tipo], "permisos": list(permisos), "email": "yo@prueba.co"}


def _persona(id_="u2", nombre="Luis", apellido="Paz"):
    return {"id": id_, "nombre": nombre, "apellido": apellido, "titular": "Dev", "ciudad": "Cali"}


RECOMENDADA = {
    "oferta": {"id": "o1", "titulo": "Backend", "ciudad": "Cali", "modalidad": "remota"},
    "empresa": {"id": "e1", "nombre": "Caribe Labs"}, "cumple": 2, "total_req": 3, "contactos": [],
    "afinidad": 80, "postulacion": None}

DETALLE = {
    "oferta": {"id": "o1", "titulo": "Backend", "ciudad": "Cali", "modalidad": "remota", "estado": "abierta",
               "fecha_publicacion": date(2026, 1, 1), "fecha_cierre": date(2027, 1, 1), "salario_min": 1000,
               "salario_max": 2000, "descripcion": "Texto"},
    "empresa": {"id": "e1", "nombre": "Caribe Labs"}, "n_postulantes": 2, "postulacion": None, "contactos": [],
    "requisitos": [
        {"habilidad": "Python", "nivel_minimo": 3, "obligatoria": True, "tu_nivel": 4},
        {"habilidad": "SQL", "nivel_minimo": 3, "obligatoria": False, "tu_nivel": 1},
        {"habilidad": "Go", "nivel_minimo": 2, "obligatoria": False, "tu_nivel": None},
        {"habilidad": "Git", "nivel_minimo": 2, "obligatoria": False, "tu_nivel": 2}]}


@pytest.fixture
def datos(monkeypatch):
    def fijar(ruta, valor):
        monkeypatch.setattr(f"app.repositories.{ruta}", lambda *_a, **_k: valor)

    fijar("usuarios.resumen", RESUMEN)
    fijar("ofertas.recomendadas", [RECOMENDADA])
    fijar("ofertas.demanda_habilidades", [{"habilidad": "Python", "ofertas": 3}])
    fijar("ofertas.detalle", DETALLE)
    fijar("ofertas.mis_postulaciones", [])
    fijar("red.actividad", [])
    fijar("red.sugerencias", [{"usuario": _persona("u3", "Eva", "Mora"), "amigos_comunes": 2}])
    fijar("red.colaboradores", [])
    fijar("red.solicitudes_recibidas", [{"usuario": _persona("u4", "Rosa", "Gil"), "en_comun": 1, "fecha": date(2026, 1, 1), "mensaje": "Hola"}])
    fijar("red.solicitudes_enviadas", [{"usuario": _persona("u5", "Tom", "Sol"), "fecha": date(2026, 1, 1)},
                                       {"usuario": _persona("u6", "Sol", "Paz"), "fecha": date(2026, 1, 1)}])
    fijar("red.conexiones", [{"usuario": _persona(), "empresa": "Caribe Labs", "desde": date(2024, 1, 1)}])
    fijar("notificaciones.listar", [{"n": {"id": "n1", "tipo": "conexion_solicitud", "mensaje": "Hola", "fecha": date(2026, 1, 1), "leida": False}}])
    fijar("perfiles.proyectos_relacionados", [])
    fijar("perfiles.listar_proyectos", [{"proyecto": {"id": "p1", "nombre": "Puerto", "estado": "en_curso", "descripcion": "Texto"},
                                         "empresa": None, "miembros": 2, "tecnologias": ["Python"], "mi_rol": None}])
    fijar("perfiles.catalogo_habilidades", [{"id": "h1", "nombre": "Python", "categoria": "tecnica"}])
    fijar("perfiles.lista_empresas", [{"id": "e1", "nombre": "Caribe Labs"}])
    fijar("usuarios.perfil_completo", {"usuario": _persona("u1", "Ana", "Ruiz"), "conexiones": 3, "empresa": None,
                                       "experiencia": [], "habilidades": [], "proyectos": []})
    fijar("usuarios.similares", [])
    fijar("usuarios.estado_relacion", "ninguna")
    fijar("usuarios.ruta", None)
    fijar("usuarios.contactos_en_comun", [])
    fijar("empresas.obtener", {"empresa": {"id": "e1", "nombre": "Caribe Labs", "descripcion": "x", "sector": "Salud",
                                           "ciudad": "Cali", "tamano": "mediana"},
                               "empleados": 2, "ofertas": [], "contactos": [], "camino": None})
    fijar("empresas.empleados", [])  # la pagina de empresa tambien lista su equipo
    return fijar


@pytest.fixture
def como_persona(monkeypatch, datos):
    sesion = lambda _r: _sesion("persona", [], "u1")  # noqa: E731
    monkeypatch.setattr("app.dependencias.cuenta_opcional", sesion)
    monkeypatch.setattr("app.routers.paginas.cuenta_opcional", sesion)  # la ruta / importa su propia copia


def _indicador(html, nombre):
    m = re.search(rf'data-indicador="{nombre}"[^>]*>\s*<[^>]*>\s*(\d+)', html)
    assert m, f"sin indicador {nombre}"
    return int(m.group(1))


# ------------------------------------------------------------ tema
@pytest.mark.parametrize("ruta", ["/", "/red", "/empleos", "/notificaciones", "/buscar", "/proyectos",
                                  "/perfil/editar", "/cuenta", "/perfil/u9", "/empresa/e1"])
def test_todas_las_pantallas_de_persona_son_oscuras(cliente, como_persona, ruta):
    r = cliente.get(ruta)
    assert r.status_code == 200, ruta
    assert 'class="panel-interno"' in r.text
    assert "css/panel-interno.css" in r.text


def test_error_sin_sesion_es_oscuro(cliente):
    r = cliente.get("/no-existe", headers={"accept": "text/html"})
    assert r.status_code == 404
    assert 'class="panel-interno"' in r.text and "css/panel-interno.css" in r.text


@pytest.mark.parametrize("tipo", ["staff", "admin"])
def test_perfil_visto_por_cuenta_interna_es_oscuro(cliente, monkeypatch, datos, tipo):
    monkeypatch.setattr("app.dependencias.cuenta_opcional", lambda _r: _sesion(tipo, ["usuario.bloquear"]))
    assert 'class="panel-interno"' in cliente.get("/perfil/u9").text


# ------------------------------------------------------------ inicio
def test_inicio_muestra_barra_de_afinidad(cliente, como_persona):
    html = cliente.get("/").text
    assert re.search(r'class="afinidad-barra"[^>]*>\s*<i style="width:\s*80%', html)
    assert 'href="/empleos?oferta=o1"' in html
    assert "Tienes" in html and 'href="/red"' in html


# ------------------------------------------------------------ red
def test_red_con_indicadores_que_cuadran(cliente, como_persona):
    html = cliente.get("/red").text
    assert _indicador(html, "contactos") == 1
    assert _indicador(html, "recibidas") == 1
    assert _indicador(html, "enviadas") == 2


def test_red_conserva_acciones_e_invitaciones_primero(cliente, como_persona):
    html = cliente.get("/red").text
    for accion in ("/conexiones/aceptar/u4", "/conexiones/ignorar/u4", "/conexiones/solicitar/u3",
                   "/conexiones/eliminar/u2", "/conexiones/retirar/u5"):
        assert f'action="{accion}"' in html, accion
    assert html.index("Invitaciones</h2>") < html.index("Personas que quizás conozcas")
    assert 'name="csrf_token" value="token-csrf"' in html


# ------------------------------------------------------------ empleos
def test_empleos_con_barra_de_cumplimiento(cliente, como_persona):
    html = cliente.get("/empleos?oferta=o1").text
    assert "Cumples 2 de 4 requisitos" in html
    assert re.search(r'class="barra-cumplimiento"[^>]*>\s*<i style="width:\s*50%', html)
    assert 'action="/empleos/o1/postular"' in html


def test_empleo_sin_requisitos_no_muestra_barra(cliente, como_persona, datos):
    datos("ofertas.detalle", {**DETALLE, "requisitos": []})
    html = cliente.get("/empleos?oferta=o1").text
    assert "barra-cumplimiento" not in html
    assert "Cumples" not in html.split("detalle-empleo", 1)[1]


def test_nivel_exacto_cuenta_como_cumplido(cliente, como_persona, datos):
    datos("ofertas.detalle", {**DETALLE, "requisitos": [
        {"habilidad": "Git", "nivel_minimo": 2, "obligatoria": False, "tu_nivel": 2}]})
    assert "Cumples 1 de 1 requisito" in cliente.get("/empleos?oferta=o1").text


# ------------------------------------------------------------ búsqueda
def test_busqueda_muestra_cantidades(cliente, como_persona, monkeypatch):
    monkeypatch.setattr("app.repositories.busqueda.buscar", lambda _q: {
        "personas": [{"usuario": _persona(f"u{i}")} for i in range(10)],
        "empresas": [{"empresa": {"id": "e1", "nombre": "Caribe", "sector": "Salud", "ciudad": "Cali"}}],
        "ofertas": []})
    html = cliente.get("/buscar?q=x").text
    assert re.search(r"Personas\s*<small[^>]*>10\+</small>", html)
    assert re.search(r"Empresas\s*<small[^>]*>1</small>", html)
    assert "<h2>Empleos" not in html  # los grupos sin resultados se ocultan


def test_busqueda_sin_texto_no_muestra_cantidades(cliente, como_persona):
    html = cliente.get("/buscar").text
    assert "Busca en LinkedUn" in html
    assert "Personas" not in html.split("</header>", 1)[1]


# ------------------------------------------------------------ proyectos, perfil y cuenta
def test_proyectos_en_dos_columnas_conserva_formularios(cliente, como_persona):
    html = cliente.get("/proyectos").text
    assert "grid-proyectos" in html
    assert 'action="/proyectos/p1/unirse"' in html and 'action="/proyectos"' in html
    assert 'name="techs"' in html


def test_editar_perfil_tiene_indice_a_cada_seccion(cliente, como_persona):
    html = cliente.get("/perfil/editar").text
    for ancla in ("datos", "habilidades", "experiencia"):
        assert f'href="#{ancla}"' in html, ancla
        assert f'id="{ancla}"' in html, ancla
    for accion in ("/perfil/editar", "/perfil/habilidades", "/perfil/experiencia"):
        assert f'action="{accion}"' in html, accion
    assert 'name="buscando_empleo"' in html


def test_notificacion_conserva_su_accion(cliente, como_persona):
    html = cliente.get("/notificaciones").text
    assert 'action="/notificaciones/n1/leer"' in html
    assert 'action="/notificaciones/leer-todas"' in html


def test_cuenta_de_persona_con_eliminar_y_sin_permisos(cliente, como_persona):
    html = cliente.get("/cuenta").text
    assert "panel-cuenta" in html
    assert 'action="/cuenta/password"' in html and 'action="/cuenta/eliminar"' in html
    assert "etiqueta-permiso" not in html
    assert 'href="/perfil/u1"' in html


def test_empresa_vista_por_persona_conserva_su_informacion(cliente, como_persona, datos):
    datos("empresas.obtener", {"empresa": {"id": "e1", "nombre": "Caribe Labs", "descripcion": "x", "sector": "Salud", "ciudad": "Cali", "tamano": "mediana"},
                              "empleados": 1, "ofertas": [], "camino": {"saltos": 1, "ruta": ["Ana", "Caribe Labs"]},
                              "contactos": [{"usuario": _persona(), "cargo": "Dev"}]})
    html = cliente.get("/empresa/e1").text
    assert "Cómo llegas a esta empresa" in html and "Tus contactos aquí" in html


# ------------------------------------------------------------ estilos
def test_css_cubre_los_elementos_de_persona():
    css = (Path(__file__).resolve().parent.parent / "app/static/css/panel-interno.css").read_text(encoding="utf-8")
    for selector in (".buscador", ".buscador input::placeholder", ".grid-inicio", ".perfil-mini-avatar", ".fila-dato", ".enlaces-rapidos a:hover", ".aviso",
                     ".adjunto", ".barras .barra", ".tarjeta-persona", ".invitacion", ".notificacion",
                     ".fila-simple", ".fila-empleo.seleccionado", ".barra-cumplimiento", ".grid-proyectos",
                     ".indice-perfil", ".grid-empleos", ".lista-empleos", 'select[multiple]', ".pagina-error"):
        assert selector in css, selector


def test_filas_de_empleo_no_se_salen_de_las_tarjetas_sin_relleno():
    css = (Path(__file__).resolve().parent.parent / "app/static/css/panel-interno.css").read_text(encoding="utf-8")
    assert re.search(r"\.seccion \.fila-empleo\s*\{[^}]*margin", css)
    assert not re.search(r"body\.panel-interno \.fila-empleo\s*\{[^}]*margin", css)


def test_celular_barra_y_lista_de_empleos_compactas():
    css = (Path(__file__).resolve().parent.parent / "app/static/css/panel-interno.css").read_text(encoding="utf-8")
    assert re.search(r"\.buscador\s*\{[^}]*min-width:\s*0", css)
    assert re.search(r"\.lista-empleos\s*\{[^}]*max-height:\s*340px", css)
