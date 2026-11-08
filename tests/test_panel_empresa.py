import re
from datetime import date
from pathlib import Path

import pytest

PERMISOS_EMPRESA = ["oferta.publicar", "empresa.asignar_rrhh"]
EMPRESA = {"id": "e01", "nombre": "Caribe Labs", "descripcion": "Software", "sector": "Tecnologia",
           "ciudad": "Barranquilla", "tamano": "11-50", "sitio_web": "https://caribe.example"}


def _sesion(tipo, permisos=(), perfil_id=None):
    return {"tipo": tipo, "perfil_id": perfil_id, "perfil_nombre": "Caribe Labs", "cuenta_id": "c-yo",
            "csrf_token": "token-csrf", "roles": [tipo], "permisos": list(permisos), "email": "yo@prueba.co"}


def _oferta(id_, estado="abierta", postulantes=0, requisitos=1):
    return {"oferta": {"id": id_, "titulo": f"Cargo {id_}", "estado": estado, "modalidad": "remoto",
                       "ciudad": "Barranquilla", "fecha_publicacion": date(2026, 1, 1),
                       "fecha_cierre": date(2027, 1, 1)},
            "requisitos": requisitos, "postulantes": postulantes}


@pytest.fixture
def datos(monkeypatch):
    """Datos de una empresa sin necesitar Neo4j."""
    def fijar(ruta, valor):
        monkeypatch.setattr(ruta, lambda *_a, **_k: valor)

    monkeypatch.setattr("app.repositories.empresas.obtener", lambda eid, _uid: {
        "empresa": {**EMPRESA, "id": eid}, "empleados": 2,
        "ofertas": [{"oferta": {"id": "o1", "titulo": "Backend", "ciudad": "Barranquilla", "modalidad": "remoto",
                                "fecha_publicacion": date(2026, 1, 1)}}],
        "contactos": [], "camino": None})
    fijar("app.repositories.empresas.empleados", [
        {"usuario": {"id": "u1", "nombre": "Ana", "apellido": "Ruiz", "titular": "Analista"},
         "rol": "rrhh", "cargo": "Analista"}])
    fijar("app.repositories.ofertas.gestion_de_empresa", [])
    fijar("app.repositories.ofertas.empresa_de", "e01")
    fijar("app.repositories.ofertas.postulantes", [])
    fijar("app.repositories.ofertas.candidatos_sugeridos", [])
    fijar("app.repositories.perfiles.catalogo_habilidades", [{"id": "h1", "nombre": "Python", "categoria": "tecnica"}])
    fijar("app.repositories.usuarios.perfil_completo", {
        "usuario": {"id": "u9", "nombre": "Luis", "apellido": "Paz", "titular": "Dev", "ciudad": "Bogotá"},
        "conexiones": 3, "empresa": None, "experiencia": [], "habilidades": [], "proyectos": []})
    fijar("app.repositories.usuarios.similares", [])
    fijar("app.repositories.usuarios.estado_relacion", "ninguna")
    fijar("app.repositories.usuarios.ruta", None)
    fijar("app.repositories.usuarios.contactos_en_comun", [])
    fijar("app.repositories.usuarios.habilidades_en_comun", [])
    return fijar


@pytest.fixture
def como_empresa(monkeypatch, datos):
    monkeypatch.setattr("app.dependencias.cuenta_opcional", lambda _r: _sesion("empresa", PERMISOS_EMPRESA, "e01"))


@pytest.fixture
def como_rrhh(monkeypatch, datos):
    monkeypatch.setattr("app.dependencias.cuenta_opcional", lambda _r: _sesion("persona", [], "u1"))
    monkeypatch.setattr("app.repositories.usuarios.resumen", lambda _i: {
        "id": "u1", "nombre": "Ana", "apellido": "Ruiz", "empresa": {"id": "e01", "nombre": "Caribe Labs"},
        "rol_empresa": "rrhh"})


def _oferta_gestion(datos, estado="borrador", requisitos=(), postulantes=()):
    datos("app.repositories.ofertas.obtener_gestion", {
        "oferta": {"id": "o1", "titulo": "Backend", "estado": estado, "ciudad": "Barranquilla", "modalidad": "remoto",
                   "salario_min": 1000, "salario_max": 2000, "fecha_cierre": date(2027, 1, 1), "descripcion": "Texto"},
        "empresa": {"id": "e01", "nombre": "Caribe Labs"}, "requisitos": list(requisitos)})
    datos("app.repositories.ofertas.postulantes", list(postulantes))
    datos("app.repositories.ofertas.candidatos_sugeridos", [])


REQUISITO = {"id": "h1", "nombre": "Python", "nivel_minimo": 3, "obligatoria": True}
POSTULANTE = {"usuario": {"id": "u5", "nombre": "Eva", "apellido": "Mora", "titular": "Dev", "ciudad": "Cali"},
              "fecha": date(2026, 1, 1), "conocidos": [], "faltan_obligatorias": [], "cumple": 2, "total": 3,
              "afinidad": 67, "estado": "enviada"}


def _indicador(html, nombre):
    m = re.search(rf'data-indicador="{nombre}"[^>]*>\s*<[^>]*>\s*(\d+)', html)
    assert m, f"sin indicador {nombre}"
    return int(m.group(1))


RUTAS_EMPRESA = ["/empresa/e01/gestion", "/empresa/e01", "/empresa/e01/editar", "/empresa/e01/ofertas/nueva",
                 "/cuenta", "/perfil/u9"]


# ------------------------------------------------------------ tema
@pytest.mark.parametrize("ruta", RUTAS_EMPRESA)
def test_todas_las_pantallas_de_empresa_son_oscuras(cliente, como_empresa, ruta):
    r = cliente.get(ruta)
    assert r.status_code == 200, ruta
    assert 'class="panel-interno"' in r.text
    assert "css/panel-interno.css" in r.text


def test_gestion_de_oferta_es_oscura(cliente, como_empresa, datos):
    _oferta_gestion(datos)
    assert 'class="panel-interno"' in cliente.get("/ofertas/o1/gestion").text


def test_otra_empresa_tambien_se_ve_oscura(cliente, como_empresa):
    assert 'class="panel-interno"' in cliente.get("/empresa/e99").text


def test_rrhh_ve_la_gestion_oscura_con_indicadores_pero_sin_acciones_de_la_cuenta(cliente, como_rrhh):
    html = cliente.get("/empresa/e01/gestion").text
    assert 'class="panel-interno"' in html
    assert _indicador(html, "abiertas") == 0
    assert 'href="/empresa/e01/editar"' not in html
    assert 'action="/empresa/e01/empleados/u1/rol"' not in html


def test_rrhh_ve_la_nueva_oferta_con_bloques_y_pasos(cliente, como_rrhh):
    html = cliente.get("/empresa/e01/ofertas/nueva").text
    assert html.count('class="bloque-titulo"') == 3
    assert "pasos-oferta" in html


def test_gestion_de_oferta_rrhh_igual_que_empresa(cliente, como_rrhh, datos):
    _oferta_gestion(datos, requisitos=[REQUISITO], postulantes=[POSTULANTE])
    html = cliente.get("/ofertas/o1/gestion").text
    assert 'class="panel-interno"' in html
    assert "afinidad-barra" in html
    assert html.index('id="postulantes"') < html.index('id="requisitos"')


# ------------------------------------------------------------ gestión
def test_indicadores_de_gestion(cliente, como_empresa, datos):
    datos("app.repositories.ofertas.gestion_de_empresa", [
        _oferta("a", "abierta", 3), _oferta("b", "abierta", 1), _oferta("c", "borrador", 0), _oferta("d", "cerrada", 5)])
    html = cliente.get("/empresa/e01/gestion").text
    assert _indicador(html, "abiertas") == 2
    assert _indicador(html, "borradores") == 1
    assert _indicador(html, "cerradas") == 1
    assert _indicador(html, "postulantes") == 9


def test_indicadores_en_cero_sin_ofertas(cliente, como_empresa):
    html = cliente.get("/empresa/e01/gestion").text
    assert _indicador(html, "abiertas") == 0
    assert _indicador(html, "postulantes") == 0
    assert "Aún no has creado ofertas" in html


def test_gestion_ofrece_acciones_y_equipo(cliente, como_empresa, datos):
    datos("app.repositories.ofertas.gestion_de_empresa", [_oferta("a")])
    html = cliente.get("/empresa/e01/gestion").text
    assert 'href="/empresa/e01/ofertas/nueva"' in html
    assert 'href="/empresa/e01/editar"' in html
    assert re.search(r'class="btn btn-borde btn-chico"[^>]*href="/ofertas/a/gestion"|href="/ofertas/a/gestion"[^>]*class="btn btn-borde btn-chico"', html)
    assert 'action="/empresa/e01/empleados/u1/rol"' in html
    assert 'id="equipo"' in html


# ------------------------------------------------------------ perfil de empresa
def test_empleo_propio_lleva_a_su_gestion(cliente, como_empresa):
    html = cliente.get("/empresa/e01").text
    assert 'href="/ofertas/o1/gestion"' in html
    assert "/empleos?oferta=" not in html


def test_empleo_de_otra_empresa_se_muestra_sin_enlace(cliente, como_empresa):
    html = cliente.get("/empresa/e99").text
    assert "Backend" in html
    assert "/empleos?oferta=" not in html
    assert 'href="/ofertas/o1/gestion"' not in html


def test_persona_conserva_el_enlace_a_empleos(cliente, como_rrhh):
    assert 'href="/empleos?oferta=o1"' in cliente.get("/empresa/e01").text


def test_perfil_propio_tiene_accesos_de_gestion(cliente, como_empresa):
    html = cliente.get("/empresa/e01").text
    assert 'href="/empresa/e01/gestion"' in html and 'href="/empresa/e01/editar"' in html


def test_otra_empresa_no_ofrece_accesos_de_gestion(cliente, como_empresa):
    html = cliente.get("/empresa/e99").text
    assert 'href="/empresa/e99/gestion"' not in html and 'href="/empresa/e99/editar"' not in html


@pytest.mark.parametrize("ruta", ["/empresa/e01", "/empresa/e01/gestion", "/empresa/e01/editar"])
def test_mi_empresa_se_marca_como_activa(cliente, como_empresa, ruta):
    assert re.search(r'class="nav-item activo" href="/empresa/e01"', cliente.get(ruta).text)


def test_mi_empresa_activa_tambien_en_una_oferta(cliente, como_empresa, datos):
    _oferta_gestion(datos)
    assert re.search(r'class="nav-item activo" href="/empresa/e01"', cliente.get("/ofertas/o1/gestion").text)


@pytest.mark.parametrize("ruta", ["/perfil/u9", "/cuenta", "/empresa/e99"])
def test_mi_empresa_no_se_marca_fuera_de_ella(cliente, como_empresa, ruta):
    assert not re.search(r'class="nav-item activo" href="/empresa/e01"', cliente.get(ruta).text)


# ------------------------------------------------------------ formulario de oferta
def test_nueva_oferta_con_bloques_y_pasos(cliente, como_empresa):
    html = cliente.get("/empresa/e01/ofertas/nueva").text
    assert html.count('class="bloque-titulo"') == 3
    assert re.search(r'aria-current="step"[^>]*>\s*<span[^>]*>1<', html)
    for campo in ("titulo", "descripcion", "modalidad", "ciudad", "salario_min", "salario_max", "fecha_cierre"):
        assert f'name="{campo}"' in html, campo
    assert 'action="/empresa/e01/ofertas/nueva"' in html
    assert 'name="csrf_token" value="token-csrf"' in html


def test_nueva_oferta_invalida_conserva_datos_y_muestra_errores(cliente, como_empresa):
    r = cliente.post("/empresa/e01/ofertas/nueva", data={"csrf_token": "token-csrf", "titulo": "Mi cargo"})
    assert r.status_code == 422
    assert 'value="Mi cargo"' in r.text
    assert 'class="error-campo"' in r.text
    assert 'class="panel-interno"' in r.text


def test_editar_oferta_no_muestra_pasos(cliente, como_empresa, datos):
    _oferta_gestion(datos, estado="abierta")
    html = cliente.get("/ofertas/o1/editar").text
    assert "pasos-oferta" not in html
    assert 'action="/ofertas/o1/editar"' in html


# ------------------------------------------------------------ gestión de oferta
def _paso_actual(html):
    m = re.search(r'aria-current="step"[^>]*>\s*<span[^>]*>(\d)<', html)
    return int(m.group(1)) if m else None


def test_borrador_sin_requisitos_esta_en_el_paso_2(cliente, como_empresa, datos):
    _oferta_gestion(datos, estado="borrador")
    assert _paso_actual(cliente.get("/ofertas/o1/gestion").text) == 2


def test_borrador_con_requisitos_esta_en_el_paso_3(cliente, como_empresa, datos):
    _oferta_gestion(datos, estado="borrador", requisitos=[REQUISITO])
    assert _paso_actual(cliente.get("/ofertas/o1/gestion").text) == 3


def test_oferta_abierta_no_muestra_pasos(cliente, como_empresa, datos):
    _oferta_gestion(datos, estado="abierta")
    assert "pasos-oferta" not in cliente.get("/ofertas/o1/gestion").text


def test_postulantes_antes_que_requisitos_y_con_barra(cliente, como_empresa, datos):
    _oferta_gestion(datos, estado="abierta", requisitos=[REQUISITO, {**REQUISITO, "id": "h2", "nombre": "SQL"}],
                    postulantes=[POSTULANTE])
    html = cliente.get("/ofertas/o1/gestion").text
    assert html.index('id="postulantes"') < html.index('id="requisitos"')
    assert re.search(r'class="afinidad-barra"[^>]*>\s*<i style="width:\s*67%', html)
    assert 'action="/ofertas/o1/postulaciones/u5/estado"' in html
    assert 'action="/ofertas/o1/requisitos"' in html
    assert 'action="/ofertas/o1/requisitos/h1/quitar"' in html
    assert 'action="/ofertas/o1/cerrar"' in html


# ------------------------------------------------------------ editar empresa, cuenta y perfil
def test_editar_empresa_muestra_datos_actuales(cliente, como_empresa):
    html = cliente.get("/empresa/e01/editar").text
    assert "Datos actuales" in html
    assert html.count('class="bloque-titulo"') == 2
    assert 'action="/empresa/e01/editar"' in html
    assert 'name="csrf_token" value="token-csrf"' in html


def test_cuenta_de_empresa_oscura_con_eliminar_y_sin_permisos_tecnicos(cliente, como_empresa):
    html = cliente.get("/cuenta").text
    assert "panel-cuenta" in html
    assert 'action="/cuenta/password"' in html and 'action="/cuenta/eliminar"' in html
    assert 'name="confirmar"' in html
    assert "etiqueta-permiso" not in html
    assert 'href="/empresa/e01/gestion"' in html


def test_perfil_visto_por_empresa_sin_enlace_a_red(cliente, como_empresa):
    html = cliente.get("/perfil/u9").text
    assert "3 contactos" in html
    assert 'href="/red"' not in html


def test_perfil_visto_por_persona_conserva_enlace_a_red(cliente, como_rrhh):
    assert 'href="/red"' in cliente.get("/perfil/u9").text


# ------------------------------------------------------------ estilos
def _css():
    return (Path(__file__).resolve().parent.parent / "app/static/css/panel-interno.css").read_text(encoding="utf-8")


def test_css_cubre_los_elementos_de_empresa():
    css = _css()
    for selector in (".estado-abierta", ".estado-borrador", ".estado-cerrada", ".estado-enviada", ".zona-peligro",
                     ".btn-peligro", ".entrada-chica", ".campo textarea", ".campo select", ".fila-empleo:hover",
                     ".cabecera-avatar", ".banner-grande", ".nivel i", ".afinidad-barra", ".pasos-oferta",
                     ".chip-azul", ".btn-estado", ".postulante"):
        assert selector in css, selector


def test_antiguo_admin_css_ya_no_existe():
    assert not (Path(__file__).resolve().parent.parent / "app/static/css/admin.css").exists()


def test_equipo_y_requisitos_no_aplastan_el_contenido():
    css = _css()
    regla = re.search(r"\.rejilla-equipo \.fila-accion \.persona\s*\{([^}]*)\}", css)
    assert regla and "100%" in regla.group(1)
    fila = re.search(r"body\.panel-interno \.pad-fila\s*\{([^}]*)\}", css).group(1)
    assert "nowrap" in fila


def test_sectores_de_los_datos_de_prueba_existen_en_la_lista():
    from app.services.auth import SECTORES
    datos = (Path(__file__).resolve().parent.parent / "cypher/02_datos.cypher").read_text(encoding="utf-8")
    usados = set(re.findall(r"sector:\s*'([^']+)'", datos))
    assert usados, "no se encontraron sectores"
    assert usados <= set(SECTORES), usados - set(SECTORES)
