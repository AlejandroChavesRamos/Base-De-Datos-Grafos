import re
from pathlib import Path

import pytest
from fastapi.responses import PlainTextResponse

CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "frame-ancestors 'none'; form-action 'self'; base-uri 'self'")


def _cuenta(tipo, perfil_id=None):
    return {"tipo": tipo, "perfil_id": perfil_id, "perfil_nombre": "Prueba", "cuenta_id": "c1",
            "csrf_token": "t", "roles": [], "permisos": [], "email": "a@b.co"}


def test_sin_sesion_ve_portada(cliente):
    r = cliente.get("/")
    texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", r.text))
    assert r.status_code == 200
    assert "Todo empieza con UN contacto." in texto
    assert "Conecta con profesionales y empresas, descubre empleos a tu medida y encuentra quién puede abrirte la puerta." in texto
    assert 'href="/registro"' in r.text and 'href="/login"' in r.text
    assert "Crear mi cuenta" in texto and "Iniciar sesión" in texto
    assert "Imagen de la Tierra: NASA Earth Observatory" in texto


def test_sin_scripts_en_linea_ni_urls_externas(cliente):
    html = cliente.get("/").text
    assert not re.search(r"<script(?![^>]*\bsrc=)", html)
    assert not re.search(r"https?://(?!testserver)", html)


def test_csp_sin_cambios(cliente):
    assert cliente.get("/").headers["content-security-policy"] == CSP


def test_cookie_invalida_ve_portada(cliente, monkeypatch):
    monkeypatch.setattr("app.dependencias.sesiones.validar", lambda _: None)
    cliente.cookies.set("sesion", "basura")
    r = cliente.get("/")
    assert r.status_code == 200
    assert "Crear mi cuenta" in r.text


def test_sin_cookie_no_consulta_la_base(cliente, monkeypatch):
    def falla(*_a, **_k):
        raise AssertionError("no debe consultar Neo4j")
    monkeypatch.setattr("app.dependencias.sesiones.validar", falla)
    assert cliente.get("/").status_code == 200


def test_empresa_redirige_a_su_pagina(cliente, monkeypatch):
    monkeypatch.setattr("app.routers.paginas.cuenta_opcional", lambda _r: _cuenta("empresa", "e01"))
    r = cliente.get("/")
    assert r.status_code == 303
    assert r.headers["location"] == "/empresa/e01"


def test_admin_redirige_a_panel(cliente, monkeypatch):
    monkeypatch.setattr("app.routers.paginas.cuenta_opcional", lambda _r: _cuenta("admin"))
    r = cliente.get("/")
    assert r.status_code == 303
    assert r.headers["location"] == "/admin"


def test_persona_ve_su_inicio(cliente, monkeypatch):
    monkeypatch.setattr("app.routers.paginas.cuenta_opcional", lambda _r: _cuenta("persona", "u01"))
    monkeypatch.setattr("app.dependencias.usuarios.resumen", lambda _i: {"id": "u01", "nombre": "A", "apellido": "B"})
    for modulo, funcion in (("ofertas", "recomendadas"), ("ofertas", "demanda_habilidades"),
                            ("red", "actividad"), ("red", "sugerencias")):
        monkeypatch.setattr(f"app.routers.paginas.{modulo}.{funcion}", lambda *_a: [])
    monkeypatch.setattr("app.routers.paginas.render", lambda _r, plantilla, _y, **_d: PlainTextResponse(plantilla))
    r = cliente.get("/")
    assert r.status_code == 200
    assert r.text == "inicio.html"


def test_enlace_directo_conserva_siguiente(cliente):
    r = cliente.get("/perfil/u01")
    assert r.status_code == 303
    assert r.headers["location"] == "/login?siguiente=%2Fperfil%2Fu01"


def test_recursos_con_tipo_correcto(cliente):
    assert "javascript" in cliente.get("/static/animaciones/precarga.js").headers["content-type"]
    assert "javascript" in cliente.get("/static/animaciones/bienvenida.js").headers["content-type"]
    assert "font/woff2" in cliente.get("/static/fuentes/sora-latin-wght-normal.woff2").headers["content-type"]


def test_codigo_propio_sin_dependencias_externas():
    revisados = 0
    for f in Path("app/static/animaciones").rglob("*"):
        if f.suffix in (".js", ".css") and "vendor" not in f.parts:
            t = f.read_text(encoding="utf-8")
            assert not re.search(r"https?://", t), f
            assert not re.search(r"from\s+['\"]three['\"]", t), f
            revisados += 1
    assert revisados > 0


@pytest.mark.parametrize("ruta", ["/login", "/registro", "/registro/persona", "/registro/empresa"])
def test_acceso_oscuro_sin_tocar_formulario(cliente, ruta):
    html = cliente.get(ruta).text
    assert 'class="acceso"' in html and "css/acceso.css" in html
    if ruta in ("/login", "/registro/persona", "/registro/empresa"):
        assert 'name="csrf_token"' in html


def test_login_conserva_campos(cliente):
    html = cliente.get("/login?siguiente=/red").text
    assert 'name="email"' in html and 'name="password"' in html
    assert 'name="siguiente" value="/red"' in html


def test_logo_y_favicon_en_paginas_publicas(cliente):
    html = cliente.get("/login").text
    assert "marca/logo-un.svg" in html and "marca/favicon.svg" in html


def _regla_css(selector):
    css = Path("app/static/animaciones/bienvenida.css").read_text(encoding="utf-8")
    return re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css).group(1)


def test_textos_ocultos_no_reciben_clics_ni_foco():
    assert "visibility: hidden" in _regla_css(".js-animado .portada")
    assert "visibility: visible" in _regla_css(".js-animado.listo .portada")


def test_sin_temporizador_css_que_muestre_textos_sobre_una_entrada_en_pausa():
    css = Path("app/static/animaciones/bienvenida.css").read_text(encoding="utf-8")
    assert "aparecer-seguro" not in css
