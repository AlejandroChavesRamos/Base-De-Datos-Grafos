import re

import pytest


def _cuenta_sesion(tipo, permisos=(), perfil_id=None):
    return {"tipo": tipo, "perfil_id": perfil_id, "perfil_nombre": "Prueba", "cuenta_id": "c-yo",
            "csrf_token": "token-csrf", "roles": [tipo], "permisos": list(permisos), "email": "yo@prueba.co"}


PERMISOS_ADMIN = ["usuario.bloquear", "staff.gestionar", "sistema.auditar"]


def _fila(id_, tipo="persona", activa=True, bloqueo=False):
    return {"id": id_, "email": f"{id_}@prueba.co", "tipo": tipo, "activa": activa,
            "intentos": 0, "bloqueo_temporal": bloqueo, "perfil": id_}


@pytest.fixture
def como(monkeypatch):
    """Simula una sesión y una lista de cuentas sin necesitar Neo4j."""
    def activar(tipo, permisos=(), filas=(), perfil_id=None):
        monkeypatch.setattr("app.dependencias.cuenta_opcional",
                            lambda _r: _cuenta_sesion(tipo, permisos, perfil_id))
        monkeypatch.setattr("app.routers.admin.cuentas.listar", lambda _n: list(filas))
        monkeypatch.setattr("app.routers.admin.eventos.recientes", lambda _n: [])
    return activar


def _indicador(html, nombre):
    m = re.search(rf'data-indicador="{nombre}"[^>]*>\s*<[^>]*>\s*(\d+)', html)
    assert m, f"sin indicador {nombre}"
    return int(m.group(1))


def test_panel_admin_usa_el_estilo_oscuro(cliente, como):
    como("admin", PERMISOS_ADMIN)
    html = cliente.get("/admin").text
    assert 'class="panel-interno"' in html
    assert "css/panel-interno.css" in html


def test_panel_staff_tambien_usa_el_estilo_oscuro(cliente, como):
    como("staff", ["usuario.bloquear"])
    r = cliente.get("/admin")
    assert r.status_code == 200
    assert 'class="panel-interno"' in r.text


def test_indicadores_clasifican_igual_que_las_filas(cliente, como):
    filas = [_fila("a"), _fila("b"), _fila("c", bloqueo=True), _fila("d", activa=False),
             _fila("e", activa=False, bloqueo=True)]
    como("admin", PERMISOS_ADMIN, filas)
    html = cliente.get("/admin").text
    assert _indicador(html, "total") == 5
    assert _indicador(html, "activas") == 2
    assert _indicador(html, "bloqueadas") == 1
    assert _indicador(html, "desactivadas") == 2


def test_indicadores_en_cero_sin_cuentas(cliente, como):
    como("admin", PERMISOS_ADMIN, [])
    html = cliente.get("/admin").text
    assert _indicador(html, "total") == 0
    assert _indicador(html, "activas") == 0


def test_aviso_si_la_lista_llega_al_limite(cliente, como):
    como("admin", PERMISOS_ADMIN, [_fila(f"u{i}") for i in range(100)])
    assert "primeras 100 cuentas" in cliente.get("/admin").text


def test_sin_aviso_por_debajo_del_limite(cliente, como):
    como("admin", PERMISOS_ADMIN, [_fila(f"u{i}") for i in range(99)])
    assert "primeras 100 cuentas" not in cliente.get("/admin").text


def test_permisos_como_etiquetas(cliente, como):
    como("admin", PERMISOS_ADMIN)
    html = cliente.get("/admin").text
    assert re.search(r'<li class="etiqueta-permiso">\s*sistema\.auditar\s*</li>', html)


def test_accion_de_estado_conserva_formulario_y_token(cliente, como):
    como("admin", PERMISOS_ADMIN, [_fila("otra")])
    html = cliente.get("/admin").text
    assert 'action="/admin/cuentas/otra/estado"' in html
    assert 'name="csrf_token" value="token-csrf"' in html
    assert 'name="activa" value="false"' in html
    assert ">Desactivar<" in html


def test_no_se_ofrece_accion_sobre_la_propia_cuenta(cliente, como):
    como("admin", PERMISOS_ADMIN, [_fila("c-yo", tipo="admin")])
    assert 'action="/admin/cuentas/c-yo/estado"' not in cliente.get("/admin").text


def test_staff_no_ve_accion_sobre_cuentas_internas(cliente, como):
    como("staff", ["usuario.bloquear"], [_fila("otro-admin", tipo="admin")])
    assert 'action="/admin/cuentas/otro-admin/estado"' not in cliente.get("/admin").text


def test_tablas_con_desplazamiento_accesibles_por_teclado(cliente, como):
    como("admin", PERMISOS_ADMIN, [_fila("a")])
    html = cliente.get("/admin").text
    assert len(re.findall(r'class="tabla-scroll tabla-alta"[^>]*tabindex="0"', html)) == 2


@pytest.mark.parametrize("tipo", ["admin", "staff"])
def test_cuenta_interna_usa_estilo_oscuro_y_dos_columnas(cliente, como, tipo):
    como(tipo, ["usuario.bloquear"])
    html = cliente.get("/cuenta").text
    assert 'class="panel-interno"' in html and "css/panel-interno.css" in html
    assert "panel-cuenta" in html
    assert 'action="/cuenta/password"' in html
    assert 'name="csrf_token" value="token-csrf"' in html
    assert re.search(r'<li class="etiqueta-permiso">\s*usuario\.bloquear\s*</li>', html)


def test_cuenta_interna_no_ofrece_eliminar(cliente, como):
    como("admin", PERMISOS_ADMIN)
    assert 'action="/cuenta/eliminar"' not in cliente.get("/cuenta").text


def test_admin_css_sin_movimiento_de_fondo_ni_dependencias_externas():
    from pathlib import Path
    css = (Path(__file__).resolve().parent.parent / "app/static/css/panel-interno.css").read_text(encoding="utf-8")
    assert not re.search(r"https?://", css)
    assert "infinite" not in css
    regla = re.search(r"body\.panel-interno\s*\{([^}]*)\}", css).group(1)
    assert "animation" not in regla and "transition" not in regla
    assert "#0a0c10" in regla and "#0b2147" in regla
