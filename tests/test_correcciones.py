"""Regresiones de los fallos hallados en la auditoría."""
import re
from datetime import date
from pathlib import Path

import pytest

from app.repositories import busqueda, conexiones, cuentas, empresas, ofertas, perfiles, red, usuarios
from app.services import seguridad
from app.templating import AVISOS

OFERTA = {"id": "o1", "titulo": "Backend", "estado": "abierta", "ciudad": "Cali", "modalidad": "remota",
          "salario_min": 1000, "salario_max": 2000, "fecha_cierre": date(2020, 1, 1), "fecha_publicacion": date(2019, 1, 1),
          "descripcion": "Texto"}
EMPRESA = {"id": "e1", "nombre": "Caribe Labs", "descripcion": "x", "sector": "Salud", "ciudad": "Cali", "tamano": "mediana"}
USUARIO = {"id": "u2", "nombre": "Luis", "apellido": "Paz", "titular": "Dev", "ciudad": "Cali"}
REQUISITO = {"id": "h1", "nombre": "Python", "nivel_minimo": 3, "obligatoria": True}
# date() de Neo4j va en UTC: las ofertas se vencerian a las 7 p. m. de su ultimo dia.
HOY = "fecha_cierre >= date({timezone: 'America/Bogota'})"
POSTULANTE = {"usuario": USUARIO, "fecha": date(2026, 1, 1), "conocidos": [], "faltan_obligatorias": [], "cumple": 1, "total": 1, "afinidad": 100}


def _sesion(tipo, perfil_id=None, permisos=()):
    return {"tipo": tipo, "perfil_id": perfil_id, "perfil_nombre": "Caribe Labs", "cuenta_id": "c1", "csrf_token": "t",
            "roles": [tipo], "permisos": list(permisos), "email": "a@b.co"}


@pytest.fixture
def fijar(monkeypatch):
    def _f(ruta, valor):
        monkeypatch.setattr(f"app.repositories.{ruta}", lambda *_a, **_k: valor)
    return _f


@pytest.fixture
def como(monkeypatch, fijar):
    def activar(tipo, perfil_id=None, permisos=()):
        sesion = lambda _r: _sesion(tipo, perfil_id, permisos)  # noqa: E731
        monkeypatch.setattr("app.dependencias.cuenta_opcional", sesion)
        monkeypatch.setattr("app.routers.paginas.cuenta_opcional", sesion)
        fijar("usuarios.resumen", {"id": perfil_id, "nombre": "Ana", "apellido": "Ruiz"})
    return activar


@pytest.fixture
def consultas(monkeypatch):
    """Captura el texto de las consultas sin tocar la base."""
    capturadas = []
    def registrar(c, **_p):
        capturadas.append(c)
        return []
    for modulo in (busqueda, conexiones, cuentas, empresas, ofertas, perfiles, red, usuarios):
        monkeypatch.setattr(modulo.db, "leer", registrar)
        monkeypatch.setattr(modulo.db, "escribir", registrar)
    return capturadas


# ---------------------------------------------------------------- 2. CSRF
def test_dos_tokens_vacios_no_son_iguales():
    assert not seguridad.tokens_iguales("", "")
    assert not seguridad.tokens_iguales(None, None)
    assert not seguridad.tokens_iguales("a", "")
    assert not seguridad.tokens_iguales("a", "b")
    assert seguridad.tokens_iguales("abc", "abc")


def test_login_sin_cookie_ni_token_se_rechaza(cliente):
    assert cliente.post("/login", data={"email": "a@b.co", "password": "x"}).status_code == 403


@pytest.mark.parametrize("ruta", ["/registro/persona", "/registro/empresa"])
def test_registro_sin_cookie_ni_token_se_rechaza(cliente, ruta):
    assert cliente.post(ruta, data={"nombre": "N", "email": "a@b.co"}).status_code == 403


# ---------------------------------------------------------------- 1. ofertas vencidas
@pytest.mark.parametrize("llamada", [
    lambda: ofertas.recomendadas("u"), lambda: ofertas.demanda_habilidades(), lambda: red.actividad("u"),
])
def test_consultas_publicas_excluyen_vencidas(consultas, llamada):
    llamada()
    assert any(HOY in c for c in consultas), consultas


def test_pagina_de_empresa_excluye_vencidas(consultas, monkeypatch):
    # empresas.obtener corta si no hay empresa: se simula que existe
    monkeypatch.setattr(empresas.db, "leer", lambda c, **_p: consultas.append(c) or [{"empresa": EMPRESA, "empleados": 0, "activa": True}])
    empresas.obtener("e", "u")
    assert any(HOY in c for c in consultas), consultas


def test_publicar_exige_fecha_vigente(consultas):
    ofertas.publicar("o")
    assert HOY in consultas[0]


def test_reabrir_exige_fecha_vigente(consultas):
    assert ofertas.reabrir("o") is False
    assert HOY in consultas[0] and "'cerrada'" in consultas[0]


def test_ruta_reabrir_explica_si_vencio(cliente, como, fijar, monkeypatch):
    como("empresa", "e1", ["oferta.publicar"])
    fijar("ofertas.empresa_de", "e1")
    fijar("ofertas.reabrir", False)
    r = cliente.post("/ofertas/o1/reabrir", data={"csrf_token": "t"})
    assert "error=oferta_vencida" in r.headers["location"]
    assert "oferta_vencida" in AVISOS["error"]


def test_gestion_de_empresa_marca_vencida(cliente, como, fijar):
    como("empresa", "e1", ["oferta.publicar"])
    fijar("empresas.obtener", {"empresa": EMPRESA, "empleados": 0, "ofertas": [], "contactos": [], "camino": None})
    fijar("empresas.empleados", [])
    fijar("ofertas.gestion_de_empresa", [
        {"oferta": OFERTA, "requisitos": 1, "postulantes": 2, "vencida": True},
        {"oferta": {**OFERTA, "id": "o2", "fecha_cierre": date(2040, 1, 1)}, "requisitos": 1, "postulantes": 0, "vencida": False}])
    html = cliente.get("/empresa/e1/gestion").text
    assert 'class="chip estado-vencida">Vencida<' in html
    assert re.search(r'data-indicador="abiertas"[^>]*>\s*<[^>]*>\s*1<', html)
    assert re.search(r'data-indicador="cerradas"[^>]*>\s*<[^>]*>\s*1<', html)


def _detalle(**extra):
    return {"oferta": OFERTA, "empresa": {"id": "e1", "nombre": "Caribe"}, "n_postulantes": 0, "postulacion": None,
            "contactos": [], "requisitos": [], **extra}


def test_empleo_vencido_no_ofrece_postularse(cliente, como, fijar):
    como("persona", "u1")
    fijar("ofertas.recomendadas", [])
    fijar("ofertas.mis_postulaciones", [])
    fijar("ofertas.detalle", _detalle(vencida=True))
    html = cliente.get("/empleos?oferta=o1").text
    assert "/empleos/o1/postular" not in html
    assert "Oferta vencida" in html


def test_gestion_de_oferta_avisa_que_vencio(cliente, como, fijar):
    como("empresa", "e1", ["oferta.publicar"])
    fijar("ofertas.empresa_de", "e1")
    fijar("ofertas.obtener_gestion", {"oferta": OFERTA, "empresa": EMPRESA, "requisitos": [REQUISITO], "vencida": True})
    fijar("perfiles.catalogo_habilidades", [])
    fijar("ofertas.postulantes", [])
    fijar("ofertas.candidatos_sugeridos", [])
    html = cliente.get("/ofertas/o1/gestion").text
    assert 'estado-vencida">Vencida<' in html
    assert "Cambia la fecha de cierre" in html


def test_busqueda_marca_vencida_como_cerrada(cliente, como, monkeypatch):
    como("persona", "u1")
    monkeypatch.setattr("app.repositories.busqueda.buscar", lambda _q: {"personas": [], "empresas": [], "ofertas": [
        {"oferta": {"id": "o1", "titulo": "Backend", "estado": "abierta", "ciudad": "Cali"}, "empresa": "Caribe", "vencida": True}]})
    assert "Cerrada" in cliente.get("/buscar?q=b").text


def test_css_tiene_estado_vencida():
    css = (Path(__file__).resolve().parent.parent / "app/static/css/panel-interno.css").read_text(encoding="utf-8")
    assert ".estado-vencida" in css


# ---------------------------------------------------------------- 3 y 8. experiencia
def test_experiencia_bloquea_al_usuario_antes_de_leer(consultas):
    perfiles.agregar_experiencia("u", {"empresa_id": "e", "cargo": "x", "actual": True, "desde": "2020-01-01", "hasta": None})
    c = consultas[0]
    assert "SET u." in c and c.index("SET u.") < c.index("OPTIONAL MATCH"), "el bloqueo debe ir antes de leer los empleos"


def test_experiencia_no_duplica_empresa_y_fecha(consultas):
    perfiles.agregar_experiencia("u", {"empresa_id": "e", "cargo": "x", "actual": True, "desde": "2020-01-01", "hasta": None})
    assert "t.desde = date($desde)" in consultas[0]


def test_experiencia_repetida_da_error_claro(cliente, como, fijar):
    como("persona", "u1")
    fijar("perfiles.agregar_experiencia", False)
    r = cliente.post("/perfil/experiencia", data={"csrf_token": "t", "empresa_id": "e1", "cargo": "x", "desde": "2020-01-01", "actual": "on"})
    assert "error=experiencia_repetida" in r.headers["location"]
    assert "experiencia_repetida" in AVISOS["error"]


@pytest.mark.parametrize("llamada,bloqueo,revisa", [
    (lambda: conexiones.solicitar("a", "b", ""), "SET a.", "NOT EXISTS { (a)-[:SOLICITA_CONEXION]-(b) }"),
    (lambda: ofertas.postular("u", "o"), "SET u.", "NOT EXISTS { (u)-[:POSTULA_A]->(o) }"),
])
def test_clics_simultaneos_se_atienden_en_fila(consultas, llamada, bloqueo, revisa):
    llamada()
    assert consultas[0].index(bloqueo) < consultas[0].index(revisa), "debe bloquear antes de comprobar si ya existe"


# ---------------------------------------------------------------- 4. cuentas desactivadas
@pytest.mark.parametrize("llamada", [
    lambda: busqueda.buscar("x"), lambda: red.sugerencias("u", 3), lambda: red.conexiones("u"),
    lambda: red.solicitudes_recibidas("u"), lambda: red.solicitudes_enviadas("u"), lambda: red.actividad("u"),
    lambda: usuarios.similares("u"), lambda: usuarios.contactos_en_comun("a", "b"), lambda: empresas.empleados("e"),
    lambda: ofertas.recomendadas("u"), lambda: ofertas.detalle("o", "u"), lambda: ofertas.postulantes("o"),
    lambda: ofertas.postular("u", "o"), lambda: conexiones.solicitar("a", "b", ""),
])
def test_consultas_ocultan_cuentas_desactivadas(consultas, llamada):
    llamada()
    assert consultas and all("activa: false" in c for c in consultas), [c[:90] for c in consultas if "activa: false" not in c]


def _perfil(activa=True):
    return {"usuario": USUARIO, "conexiones": 0, "empresa": None, "experiencia": [], "habilidades": [], "proyectos": [], "activa": activa}


def test_perfil_desactivado_es_404_para_otros(cliente, como, fijar):
    como("persona", "u1")
    fijar("usuarios.perfil_completo", _perfil(False))
    assert cliente.get("/perfil/u2", headers={"accept": "text/html"}).status_code == 404


@pytest.mark.parametrize("tipo", ["admin", "staff"])
def test_perfil_desactivado_visible_para_cuentas_internas(cliente, como, fijar, tipo):
    como(tipo)
    fijar("usuarios.perfil_completo", _perfil(False))
    fijar("usuarios.similares", [])
    assert cliente.get("/perfil/u2").status_code == 200


def test_empresa_desactivada_es_404_para_otros(cliente, como, fijar):
    como("persona", "u1")
    fijar("empresas.obtener", {"empresa": EMPRESA, "empleados": 0, "ofertas": [], "contactos": [], "camino": None, "activa": False})
    fijar("empresas.empleados", [])
    assert cliente.get("/empresa/e1", headers={"accept": "text/html"}).status_code == 404


# ---------------------------------------------------------------- 5 y 10. borrar empresa
def test_borrar_empresa_archiva_y_conserva_historial(consultas):
    cuentas.eliminar_empresa("c", "e")
    c = consultas[0]
    assert "EmpresaArchivada" in c and "REMOVE e:Empresa" in c
    assert "x.actual = false" in c, "los empleos vigentes deben quedar cerrados"


def test_borrar_empresa_quita_notificaciones_de_sus_ofertas(consultas):
    cuentas.eliminar_empresa("c", "e")
    assert ":Notificacion" in consultas[0] and "enlaces" in consultas[0]


def test_perfil_muestra_empresa_archivada_sin_enlace(cliente, como, fijar):
    como("persona", "u1")
    fijar("usuarios.perfil_completo", {**_perfil(), "experiencia": [
        {"empresa": {"id": "e9", "nombre": "Vieja SA"}, "archivada": True, "cargo": "Dev", "rol": "trabajador",
         "desde": date(2020, 1, 1), "desde_iso": "2020-01-01", "hasta": date(2021, 1, 1), "actual": False}]})
    fijar("usuarios.similares", [])
    fijar("usuarios.estado_relacion", "ninguna")
    fijar("usuarios.ruta", None)
    fijar("usuarios.contactos_en_comun", [])
    html = cliente.get("/perfil/u2").text
    assert "Vieja SA" in html and 'href="/empresa/e9"' not in html


def test_experiencia_consulta_tambien_empresas_archivadas(consultas, monkeypatch):
    monkeypatch.setattr(usuarios.db, "leer", lambda c, **_p: consultas.append(c) or [{"usuario": USUARIO, "empresa": None, "cargo": None, "conexiones": 0, "activa": True}])
    usuarios.perfil_completo("u")
    exp = next(c for c in consultas if "t.desde AS desde" in c)
    assert "EmpresaArchivada" in exp and "(e:Empresa)" not in exp


def test_quitar_experiencia_funciona_con_empresa_archivada(consultas):
    perfiles.quitar_experiencia("u", "e", "2020-01-01")
    assert ":Empresa {id" not in consultas[0]


# ---------------------------------------------------------------- 6. selector de estado
def _gestion_oferta(fijar, postulantes, estado="abierta", requisitos=(REQUISITO,)):
    fijar("ofertas.empresa_de", "e1")
    fijar("ofertas.obtener_gestion", {"oferta": {**OFERTA, "estado": estado, "fecha_cierre": date(2040, 1, 1)}, "empresa": EMPRESA,
                                      "requisitos": list(requisitos), "vencida": False})
    fijar("perfiles.catalogo_habilidades", [])
    fijar("ofertas.postulantes", postulantes)
    fijar("ofertas.candidatos_sugeridos", [])


def test_selector_no_aparenta_estado_en_postulacion_enviada(cliente, como, fijar):
    como("empresa", "e1", ["oferta.publicar"])
    _gestion_oferta(fijar, [{**POSTULANTE, "estado": "enviada"}])
    html = cliente.get("/ofertas/o1/gestion").text
    sel = re.search(r'<select[^>]*name="estado"[^>]*>(.*?)</select>', html, re.S)
    assert 'required' in sel.group(0)
    assert re.search(r'<option value="" selected disabled>', sel.group(1))


def test_selector_marca_el_estado_real(cliente, como, fijar):
    como("empresa", "e1", ["oferta.publicar"])
    _gestion_oferta(fijar, [{**POSTULANTE, "estado": "aceptada"}])
    html = cliente.get("/ofertas/o1/gestion").text
    assert re.search(r'<option value="aceptada"\s+selected', html)
    assert '<option value="" selected disabled>' not in html


# ---------------------------------------------------------------- 7. requisitos de oferta publicada
def test_quitar_requisito_protege_el_ultimo_de_una_publicada(consultas):
    ofertas.quitar_requisito("o", "h")
    assert "'borrador'" in consultas[0] and "> 1" in consultas[0]


def test_abierta_con_un_requisito_no_ofrece_quitarlo(cliente, como, fijar):
    como("empresa", "e1", ["oferta.publicar"])
    _gestion_oferta(fijar, [])
    assert "/requisitos/h1/quitar" not in cliente.get("/ofertas/o1/gestion").text


def test_abierta_con_dos_requisitos_si_ofrece_quitar(cliente, como, fijar):
    como("empresa", "e1", ["oferta.publicar"])
    _gestion_oferta(fijar, [], requisitos=(REQUISITO, {**REQUISITO, "id": "h2", "nombre": "SQL"}))
    assert "/requisitos/h1/quitar" in cliente.get("/ofertas/o1/gestion").text


def test_borrador_con_un_requisito_si_ofrece_quitar(cliente, como, fijar):
    como("empresa", "e1", ["oferta.publicar"])
    _gestion_oferta(fijar, [], estado="borrador")
    assert "/requisitos/h1/quitar" in cliente.get("/ofertas/o1/gestion").text


def test_quitar_requisito_explica_el_error(cliente, como, fijar):
    como("empresa", "e1", ["oferta.publicar"])
    fijar("ofertas.empresa_de", "e1")
    fijar("ofertas.quitar_requisito", False)
    r = cliente.post("/ofertas/o1/requisitos/h1/quitar", data={"csrf_token": "t"})
    assert "error=requisito_necesario" in r.headers["location"]
    assert "requisito_necesario" in AVISOS["error"]


# ---------------------------------------------------------------- 9. páginas de error
def test_error_con_sesion_mantiene_la_navegacion(cliente, como):
    como("persona", "u1")
    html = cliente.get("/ruta-que-no-existe", headers={"accept": "text/html"}).text
    assert "Unirse ahora" not in html
    assert 'action="/logout"' in html


def test_error_sin_sesion_muestra_acceso_publico(cliente):
    html = cliente.get("/ruta-que-no-existe", headers={"accept": "text/html"}).text
    assert "Unirse ahora" in html


def test_error_no_falla_si_la_base_no_responde(cliente, monkeypatch):
    def caida(_r):
        raise RuntimeError("Neo4j caído")
    monkeypatch.setattr("app.dependencias.cuenta_opcional", caida)
    r = cliente.get("/ruta-que-no-existe", headers={"accept": "text/html"})
    assert r.status_code == 404 and "No encontramos" in r.text


# ---------------------------------------------------------------- 10. notificaciones de invitación
def test_solicitud_guarda_quien_la_envia(consultas):
    conexiones.solicitar("a", "b", "")
    assert "origen: a.id" in consultas[0]


@pytest.mark.parametrize("llamada", [lambda: conexiones.retirar_solicitud("a", "b"), lambda: conexiones.aceptar("b", "a")])
def test_responder_invitacion_borra_su_notificacion(consultas, llamada):
    llamada()
    assert "conexion_solicitud" in consultas[0] and "DETACH DELETE n" in consultas[0]
