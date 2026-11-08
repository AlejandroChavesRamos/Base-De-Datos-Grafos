"""Panel de administracion: crear y eliminar cuentas, catalogo de habilidades y moderacion.

Sin Neo4j: la sesion y los repositorios se simulan, como en test_panel_admin.py."""
import re

import pytest

TOKEN = "token-csrf"
PERMISOS_ADMIN = ["usuario.bloquear", "staff.gestionar", "sistema.auditar", "usuario.crear", "usuario.eliminar", "usuario.editar",
                  "catalogo.gestionar", "contenido.moderar", "analitica.administrar", "consultas.ver"]
PERMISOS_STAFF = ["usuario.bloquear", "contenido.moderar", "catalogo.gestionar"]
CLAVE = "Clave12345xx"


def _sesion(tipo, permisos, perfil_id=None):
    return {"tipo": tipo, "perfil_id": perfil_id, "perfil_nombre": "Prueba", "cuenta_id": "c-yo",
            "csrf_token": TOKEN, "roles": [tipo], "permisos": list(permisos), "email": "yo@prueba.co"}


def _detalle(id_, tipo="persona", impacto=None):
    base = {"persona": {"conexiones": 7, "postulaciones": 2, "participaciones_en_proyectos": 1, "notificaciones": 4},
            "empresa": {"ofertas": 3, "postulaciones_recibidas": 5, "empleados_vinculados": 2}}
    return {"id": id_, "email": f"{id_}@prueba.co", "tipo": tipo, "perfil_id": f"p-{id_}", "perfil": f"Perfil {id_}",
            "impacto": impacto or base.get(tipo, {"sesiones": 1})}


@pytest.fixture
def llamadas():
    return []


@pytest.fixture
def como(monkeypatch, llamadas):
    """Sesion + repositorios simulados. Todo lo que escribe queda anotado en 'llamadas'."""
    def espiar(ruta, retorno=None):
        def f(*a, **k):
            llamadas.append((ruta, *a))
            return retorno(*a, **k) if callable(retorno) else retorno
        monkeypatch.setattr(ruta, f)

    def activar(tipo, permisos=(), perfil_id=None, existentes=None):
        monkeypatch.setattr("app.dependencias.cuenta_opcional", lambda _r: _sesion(tipo, permisos, perfil_id))
        monkeypatch.setattr("app.dependencias.usuarios.resumen", lambda _id: {
            "id": _id, "nombre": "Ana", "apellido": "Ruiz", "titular": "T", "ciudad": "C", "empresa": None, "cargo": None,
            "rol_empresa": None, "conexiones": 0, "postulaciones": 0, "sin_leer": 0, "solicitudes": 0})
        monkeypatch.setattr("app.routers.admin.cuentas.listar", lambda _n: [])
        monkeypatch.setattr("app.routers.admin.eventos.recientes", lambda _n: [])
        espiar("app.routers.admin.cuentas.listar_filtrado", [])
        existentes = existentes or {}
        monkeypatch.setattr("app.routers.admin.cuentas.detalle_borrado", lambda i: existentes.get(i))
        monkeypatch.setattr("app.routers.admin.cuentas.tipo_de", lambda i: existentes.get(i))
        for nombre in ("eliminar_persona", "eliminar_empresa", "eliminar_interna"):
            espiar(f"app.routers.admin.cuentas.{nombre}")
        espiar("app.routers.admin.eventos.registrar")  # es el mismo modulo que usa services/auth.py
        monkeypatch.setattr("app.routers.admin.auth.confirmar_contrasena", lambda *a: True)
        # catalogo y moderacion
        monkeypatch.setattr("app.routers.admin.catalogo.listar", lambda: [
            {"habilidad": {"id": "h1", "nombre": "Python", "categoria": "tecnica"}, "usuarios": 12, "ofertas": 6, "proyectos": 4}])
        monkeypatch.setattr("app.routers.admin.catalogo.obtener", lambda i: (
            {"habilidad": {"id": "h1", "nombre": "Python", "categoria": "tecnica"}, "usuarios": 12, "ofertas": 6, "proyectos": 4}
            if i == "h1" else None))
        espiar("app.routers.admin.catalogo.crear", lambda n, c: n.lower() != "python")
        espiar("app.routers.admin.catalogo.eliminar", True)
        monkeypatch.setattr("app.routers.admin.moderacion.ofertas", lambda: [
            {"oferta": {"id": "o1", "titulo": "Backend", "estado": "abierta", "fecha_publicacion": None},
             "empresa": "Caribe", "postulantes": 3}])
        monkeypatch.setattr("app.routers.admin.moderacion.proyectos", lambda: [
            {"proyecto": {"id": "p1", "nombre": "Portal", "estado": "en_curso"}, "empresa": None, "miembros": 2}])
        espiar("app.routers.admin.moderacion.eliminar_oferta", lambda oid: "Backend" if oid == "o1" else None)
        espiar("app.routers.admin.moderacion.eliminar_proyecto", lambda pid: "Portal" if pid == "p1" else None)
        # alta de cuentas (la validacion de auth.py se ejecuta de verdad)
        espiar("app.services.auth.cuentas.crear_persona", lambda d: d["cuenta_id"])
        espiar("app.services.auth.cuentas.crear_empresa", lambda d: d["cuenta_id"])
        espiar("app.services.auth.cuentas.crear_interna", lambda d: d["cuenta_id"])
    activar.espiar = espiar
    return activar


def _tipos(llamadas, prefijo):
    return [x for x in llamadas if x[0].startswith(prefijo)]


def _post(cliente, ruta, datos=None, token=True):
    d = dict(datos or {})
    if token:
        d["csrf_token"] = TOKEN
    return cliente.post(ruta, data=d)


# ----------------------------------------------------------------- permisos
PAGINAS = ["/admin", "/admin/cuentas/nueva", "/admin/cuentas/c-x/eliminar", "/admin/habilidades",
           "/admin/habilidades/h1/eliminar", "/admin/contenido"]
ESPERADO = {  # (persona, empresa, staff, admin)
    "/admin": (403, 403, 200, 200), "/admin/cuentas/nueva": (403, 403, 403, 200),
    "/admin/cuentas/c-x/eliminar": (403, 403, 403, 200), "/admin/habilidades": (403, 403, 200, 200),
    "/admin/habilidades/h1/eliminar": (403, 403, 200, 200), "/admin/contenido": (403, 403, 200, 200)}


@pytest.mark.parametrize("ruta", PAGINAS)
def test_cada_pagina_exige_su_permiso(cliente, como, ruta):
    obtenidos = []
    for tipo, permisos, perfil in [("persona", ["perfil.editar"], "u1"), ("empresa", ["oferta.publicar"], "e1"),
                                   ("staff", PERMISOS_STAFF, None), ("admin", PERMISOS_ADMIN, None)]:
        como(tipo, permisos, perfil, {"c-x": _detalle("c-x")})
        obtenidos.append(cliente.get(ruta).status_code)
    assert tuple(obtenidos) == ESPERADO[ruta]


ACCIONES = [("/admin/cuentas/nueva", {"tipo": "persona"}), ("/admin/cuentas/c-x/eliminar", {"password": "x", "confirmar": "on"}),
            ("/admin/habilidades", {"nombre": "Rust", "categoria": "tecnica"}),
            ("/admin/habilidades/h1/eliminar", {"confirmar": "on"}), ("/admin/ofertas/o1/eliminar", {}),
            ("/admin/proyectos/p1/eliminar", {})]


@pytest.mark.parametrize("ruta,datos", ACCIONES)
def test_toda_accion_exige_token_csrf_incluso_siendo_admin(cliente, como, llamadas, ruta, datos):
    como("admin", PERMISOS_ADMIN, existentes={"c-x": _detalle("c-x")})
    assert _post(cliente, ruta, datos, token=False).status_code == 403
    assert _post(cliente, ruta, {**datos, "csrf_token": "falso"}, token=False).status_code == 403
    escrituras = [x for x in llamadas if x[0].split(".")[-1] in ("crear", "eliminar", "eliminar_persona", "eliminar_empresa",
                                                                  "eliminar_interna", "eliminar_oferta", "eliminar_proyecto",
                                                                  "crear_persona", "crear_interna")]
    assert not escrituras


@pytest.mark.parametrize("ruta,datos", ACCIONES)
@pytest.mark.parametrize("tipo,permisos,perfil", [("persona", ["perfil.editar"], "u1"), ("empresa", ["oferta.publicar"], "e1")])
def test_personas_y_empresas_no_ejecutan_acciones_del_panel(cliente, como, llamadas, ruta, datos, tipo, permisos, perfil):
    como(tipo, permisos, perfil, {"c-x": _detalle("c-x")})
    assert _post(cliente, ruta, datos).status_code == 403
    assert not [x for x in llamadas if "eliminar" in x[0] or "crear" in x[0]]


def test_staff_no_crea_ni_elimina_cuentas(cliente, como, llamadas):
    como("staff", PERMISOS_STAFF, existentes={"c-x": _detalle("c-x")})
    assert _post(cliente, "/admin/cuentas/nueva", {"tipo": "persona"}).status_code == 403
    assert _post(cliente, "/admin/cuentas/c-x/eliminar", {"password": "x", "confirmar": "on"}).status_code == 403
    assert not llamadas


# ------------------------------------------------------- lo que se muestra
def test_staff_no_ve_botones_de_crear_ni_eliminar_cuentas(cliente, como, monkeypatch):
    como("staff", PERMISOS_STAFF)
    monkeypatch.setattr("app.routers.admin.cuentas.listar", lambda _n: [
        {"id": "x1", "email": "x1@p.co", "tipo": "persona", "activa": True, "intentos": 0, "bloqueo_temporal": False, "perfil": "X"}])
    html = cliente.get("/admin").text
    assert "Nueva cuenta" not in html and "/eliminar" not in html
    assert 'action="/admin/cuentas/x1/estado"' in html


def test_admin_ve_crear_y_eliminar_pero_no_sobre_si_mismo(cliente, como, monkeypatch):
    como("admin", PERMISOS_ADMIN)
    monkeypatch.setattr("app.routers.admin.cuentas.listar", lambda _n: [
        {"id": "x1", "email": "x1@p.co", "tipo": "persona", "activa": True, "intentos": 0, "bloqueo_temporal": False, "perfil": "X"},
        {"id": "c-yo", "email": "yo@p.co", "tipo": "admin", "activa": True, "intentos": 0, "bloqueo_temporal": False, "perfil": "-"}])
    html = cliente.get("/admin").text
    assert "Nueva cuenta" in html and 'href="/admin/cuentas/x1/eliminar"' in html
    assert "/admin/cuentas/c-yo/eliminar" not in html


def test_pestanas_segun_permisos(cliente, como):
    como("staff", PERMISOS_STAFF)
    html = cliente.get("/admin").text
    assert 'href="/admin/habilidades"' in html and 'href="/admin/contenido"' in html
    como("admin", ["usuario.bloquear"])
    html = cliente.get("/admin").text
    assert 'href="/admin/habilidades"' not in html and 'href="/admin/contenido"' not in html


@pytest.mark.parametrize("ruta", ["/admin/cuentas/nueva?tipo=persona", "/admin/cuentas/c-x/eliminar", "/admin/habilidades",
                                  "/admin/habilidades/h1/eliminar", "/admin/contenido"])
def test_pantallas_nuevas_usan_el_estilo_oscuro(cliente, como, ruta):
    como("admin", PERMISOS_ADMIN, existentes={"c-x": _detalle("c-x")})
    r = cliente.get(ruta)
    assert r.status_code == 200 and 'class="panel-interno"' in r.text and "css/panel-interno.css" in r.text


# ---------------------------------------------------------------- filtro
def test_sin_filtro_se_usa_la_consulta_de_siempre(cliente, como, llamadas):
    como("admin", PERMISOS_ADMIN)
    cliente.get("/admin")
    assert not _tipos(llamadas, "app.routers.admin.cuentas.listar_filtrado")


def test_con_filtro_se_consulta_con_el_texto_limpio(cliente, como, llamadas):
    como("admin", PERMISOS_ADMIN)
    r = cliente.get("/admin?q=%20%20Caribe%20%20labs%20")
    assert ("app.routers.admin.cuentas.listar_filtrado", 100, "Caribe labs") in llamadas
    assert 'value="Caribe labs"' in r.text and "Quitar filtro" in r.text


# ----------------------------------------------------------- crear cuentas
def test_el_selector_de_tipo_depende_del_permiso(cliente, como):
    como("admin", PERMISOS_ADMIN)
    html = cliente.get("/admin/cuentas/nueva").text
    assert all(f"tipo={t}" in html for t in ("persona", "empresa", "staff", "admin"))
    como("admin", ["usuario.crear"])  # sin staff.gestionar no puede crear cuentas internas
    html = cliente.get("/admin/cuentas/nueva").text
    assert "tipo=staff" not in html and "tipo=admin" not in html


def test_cada_tipo_muestra_sus_campos(cliente, como):
    como("admin", PERMISOS_ADMIN)
    assert "Apellido" in cliente.get("/admin/cuentas/nueva?tipo=persona").text
    assert "Sector" in cliente.get("/admin/cuentas/nueva?tipo=empresa").text
    html = cliente.get("/admin/cuentas/nueva?tipo=staff").text
    assert "Apellido" not in html and "Sector" not in html and "Contraseña inicial" in html


def test_crear_persona_valida_y_deja_rastro(cliente, como, llamadas):
    como("admin", PERMISOS_ADMIN)
    r = _post(cliente, "/admin/cuentas/nueva", {"tipo": "persona", "nombre": "Ana", "apellido": "Gómez", "ciudad": "Cali",
                                                 "email": "ANA@Prueba.co", "password": CLAVE, "password2": CLAVE})
    assert r.status_code == 303 and r.headers["location"] == "/admin?aviso=cuenta_creada"
    creada = _tipos(llamadas, "app.services.auth.cuentas.crear_persona")[0][1]
    assert creada["email"] == "ana@prueba.co" and creada["hash"].startswith("$argon2id$") and CLAVE not in creada["hash"]
    assert any(x[0] == "app.routers.admin.eventos.registrar" and x[1] == "c-yo" and x[2] == "cuenta_creada_admin" and x[4] == "persona"
               for x in llamadas)


def test_crear_persona_invalida_muestra_errores_y_no_guarda(cliente, como, llamadas):
    como("admin", PERMISOS_ADMIN)
    r = _post(cliente, "/admin/cuentas/nueva", {"tipo": "persona", "nombre": "", "apellido": "X", "ciudad": "",
                                                 "email": "mal", "password": "corta", "password2": "corta"})
    assert r.status_code == 422
    assert all(t in r.text for t in ("Escribe tu nombre", "correo válido", "10 caracteres"))
    assert not _tipos(llamadas, "app.services.auth.cuentas.crear_")


def test_crear_empresa_y_cuentas_internas(cliente, como, llamadas):
    como("admin", PERMISOS_ADMIN)
    r = _post(cliente, "/admin/cuentas/nueva", {"tipo": "empresa", "nombre": "Mar SAS", "sector": "Logística", "tamano": "mediana",
                                                 "ciudad": "BAQ", "email": "mar@p.co", "password": CLAVE, "password2": CLAVE})
    assert r.status_code == 303 and _tipos(llamadas, "app.services.auth.cuentas.crear_empresa")
    for tipo in ("staff", "admin"):
        r = _post(cliente, "/admin/cuentas/nueva", {"tipo": tipo, "email": f"{tipo}@p.co", "password": CLAVE, "password2": CLAVE})
        assert r.status_code == 303
    internas = _tipos(llamadas, "app.services.auth.cuentas.crear_interna")
    assert [x[1]["tipo"] for x in internas] == ["staff", "admin"]
    assert all(x[1]["hash"].startswith("$argon2id$") for x in internas)


def test_cuenta_interna_con_clave_debil_no_se_crea(cliente, como, llamadas):
    como("admin", PERMISOS_ADMIN)
    r = _post(cliente, "/admin/cuentas/nueva", {"tipo": "admin", "email": "a@p.co", "password": "debil", "password2": "debil"})
    assert r.status_code == 422 and "10 caracteres" in r.text
    assert not _tipos(llamadas, "app.services.auth.cuentas.crear_interna")


def test_tipo_de_cuenta_inventado_se_rechaza(cliente, como, llamadas):
    como("admin", PERMISOS_ADMIN)
    assert _post(cliente, "/admin/cuentas/nueva", {"tipo": "superadmin", "email": "z@p.co", "password": CLAVE,
                                                    "password2": CLAVE}).status_code == 403
    como("admin", ["usuario.crear"])  # sin staff.gestionar no se crean cuentas internas
    assert _post(cliente, "/admin/cuentas/nueva", {"tipo": "admin", "email": "z@p.co", "password": CLAVE,
                                                    "password2": CLAVE}).status_code == 403
    assert not _tipos(llamadas, "app.services.auth.cuentas.crear_")


def test_correo_duplicado_da_error_claro(cliente, como, monkeypatch):
    como("admin", PERMISOS_ADMIN)
    from neo4j.exceptions import ConstraintError

    def duplicado(_d):
        raise ConstraintError("duplicado")
    monkeypatch.setattr("app.services.auth.cuentas.crear_persona", duplicado)
    r = _post(cliente, "/admin/cuentas/nueva", {"tipo": "persona", "nombre": "Ana", "apellido": "G", "ciudad": "Cali",
                                                 "email": "ana@p.co", "password": CLAVE, "password2": CLAVE})
    assert r.status_code == 422 and "ya está registrado" in r.text


# --------------------------------------------------------- eliminar cuentas
def test_la_confirmacion_muestra_que_se_perdera(cliente, como):
    como("admin", PERMISOS_ADMIN, existentes={"c-p": _detalle("c-p"), "c-e": _detalle("c-e", "empresa")})
    html = cliente.get("/admin/cuentas/c-p/eliminar").text
    assert all(t in html for t in ("<strong>7</strong> conexiones", "<strong>4</strong> notificaciones", "participaciones en proyectos"))
    html = cliente.get("/admin/cuentas/c-e/eliminar").text
    assert "<strong>3</strong> ofertas" in html and "postulaciones recibidas" in html


@pytest.mark.parametrize("tipo,funcion", [("persona", "eliminar_persona"), ("empresa", "eliminar_empresa"),
                                           ("staff", "eliminar_interna"), ("admin", "eliminar_interna")])
def test_eliminar_cada_tipo_usa_su_borrado(cliente, como, llamadas, tipo, funcion):
    como("admin", PERMISOS_ADMIN, existentes={"c-x": _detalle("c-x", tipo)})
    r = _post(cliente, "/admin/cuentas/c-x/eliminar", {"password": "la-del-admin", "confirmar": "on"})
    assert r.status_code == 303 and r.headers["location"] == "/admin?aviso=cuenta_eliminada_admin"
    borrado = _tipos(llamadas, f"app.routers.admin.cuentas.{funcion}")
    assert len(borrado) == 1
    if funcion != "eliminar_interna":
        assert borrado[0][1:] == ("c-x", "p-c-x")  # cuenta y perfil
    assert any(x[0] == "app.routers.admin.eventos.registrar" and x[2] == "cuenta_eliminada_admin" and x[4] == tipo for x in llamadas)


def test_eliminar_exige_casilla_y_contrasena_del_admin(cliente, como, llamadas, monkeypatch):
    como("admin", PERMISOS_ADMIN, existentes={"c-x": _detalle("c-x")})
    assert _post(cliente, "/admin/cuentas/c-x/eliminar", {"password": "x"}).status_code == 422
    monkeypatch.setattr("app.routers.admin.auth.confirmar_contrasena", lambda *a: False)
    r = _post(cliente, "/admin/cuentas/c-x/eliminar", {"password": "mala", "confirmar": "on"})
    assert r.status_code == 422 and "no es correcta" in r.text
    assert not _tipos(llamadas, "app.routers.admin.cuentas.eliminar_")


def test_la_contrasena_que_se_verifica_es_la_del_admin(cliente, como, monkeypatch):
    como("admin", PERMISOS_ADMIN, existentes={"c-x": _detalle("c-x")})
    vistas = []
    monkeypatch.setattr("app.routers.admin.auth.confirmar_contrasena", lambda cuenta_id, clave, ip: vistas.append(cuenta_id) or True)
    _post(cliente, "/admin/cuentas/c-x/eliminar", {"password": "x", "confirmar": "on"})
    assert vistas == ["c-yo"]  # la cuenta del administrador, no la que se borra


def test_nadie_elimina_su_propia_cuenta_ni_cuentas_inexistentes(cliente, como, llamadas):
    como("admin", PERMISOS_ADMIN, existentes={"c-yo": _detalle("c-yo", "admin")})
    assert cliente.get("/admin/cuentas/c-yo/eliminar").status_code == 400
    assert _post(cliente, "/admin/cuentas/c-yo/eliminar", {"password": "x", "confirmar": "on"}).status_code == 400
    assert _post(cliente, "/admin/cuentas/zzz/eliminar", {"password": "x", "confirmar": "on"}).status_code == 404
    assert not _tipos(llamadas, "app.routers.admin.cuentas.eliminar_")


def test_sin_staff_gestionar_no_se_eliminan_cuentas_internas(cliente, como, llamadas):
    como("admin", ["usuario.eliminar", "usuario.bloquear"], existentes={"c-s": _detalle("c-s", "staff")})
    assert cliente.get("/admin/cuentas/c-s/eliminar").status_code == 403
    assert _post(cliente, "/admin/cuentas/c-s/eliminar", {"password": "x", "confirmar": "on"}).status_code == 403
    assert not _tipos(llamadas, "app.routers.admin.cuentas.eliminar_")


# ------------------------------------------------------------- habilidades
def test_catalogo_muestra_el_uso_de_cada_habilidad(cliente, como):
    como("staff", PERMISOS_STAFF)
    html = cliente.get("/admin/habilidades").text
    assert "Python" in html and "<td>12</td>" in html and "<td>6</td>" in html and "<td>4</td>" in html


def test_crear_habilidad_limpia_el_nombre_y_deja_rastro(cliente, como, llamadas):
    como("staff", PERMISOS_STAFF)
    r = _post(cliente, "/admin/habilidades", {"nombre": "  Rust   Lang ", "categoria": "tecnica"})
    assert r.status_code == 303 and r.headers["location"] == "/admin/habilidades?aviso=habilidad_creada"
    assert ("app.routers.admin.catalogo.crear", "Rust Lang", "tecnica") in llamadas
    assert any(x[0] == "app.routers.admin.eventos.registrar" and x[2] == "habilidad_creada" and x[4] == "Rust Lang" for x in llamadas)


def test_habilidad_invalida_o_duplicada_da_error(cliente, como):
    como("staff", PERMISOS_STAFF)
    r = _post(cliente, "/admin/habilidades", {"nombre": "x", "categoria": "otra"})
    assert r.status_code == 422 and "al menos 2" in r.text and "Elige una categoría" in r.text
    r = _post(cliente, "/admin/habilidades", {"nombre": "python", "categoria": "tecnica"})
    assert r.status_code == 422 and "Ya existe" in r.text


def test_eliminar_habilidad_avisa_de_cuantos_vinculos_se_pierden(cliente, como):
    como("staff", PERMISOS_STAFF)
    html = cliente.get("/admin/habilidades/h1/eliminar").text
    assert "<strong>12</strong> perfiles" in html and "<strong>6</strong> ofertas" in html and "<strong>4</strong> proyectos" in html
    assert cliente.get("/admin/habilidades/zzz/eliminar").status_code == 404


def test_eliminar_habilidad_exige_confirmar(cliente, como, llamadas):
    como("staff", PERMISOS_STAFF)
    assert _post(cliente, "/admin/habilidades/h1/eliminar", {}).status_code == 422
    assert not _tipos(llamadas, "app.routers.admin.catalogo.eliminar")
    r = _post(cliente, "/admin/habilidades/h1/eliminar", {"confirmar": "on"})
    assert r.status_code == 303 and ("app.routers.admin.catalogo.eliminar", "h1") in llamadas


# --------------------------------------------------------------- moderacion
def test_moderacion_pide_dos_pasos_antes_de_borrar(cliente, como):
    como("staff", PERMISOS_STAFF)
    html = cliente.get("/admin/contenido").text
    assert "Backend" in html and "Portal" in html and html.count('class="confirmar"') == 2 and html.count("Sí, eliminar") == 2


def test_staff_elimina_oferta_y_proyecto_con_rastro(cliente, como, llamadas):
    como("staff", PERMISOS_STAFF)
    assert _post(cliente, "/admin/ofertas/o1/eliminar").headers["location"] == "/admin/contenido?aviso=oferta_moderada"
    assert _post(cliente, "/admin/proyectos/p1/eliminar").headers["location"] == "/admin/contenido?aviso=proyecto_eliminado"
    registro = [(x[2], x[4]) for x in llamadas if x[0] == "app.routers.admin.eventos.registrar"]
    assert ("oferta_eliminada_moderacion", "Backend") in registro and ("proyecto_eliminado_moderacion", "Portal") in registro


def test_moderar_algo_inexistente_es_404(cliente, como):
    como("staff", PERMISOS_STAFF)
    assert _post(cliente, "/admin/ofertas/zzz/eliminar").status_code == 404
    assert _post(cliente, "/admin/proyectos/zzz/eliminar").status_code == 404


# ============================================================================
#  Modificar cuentas y dar / quitar privilegios de administrador
# ============================================================================
CLAVE_NUEVA = "OtraClave2026x"


def _editable(id_, tipo="persona", rol_admin=False):
    perfil = {"persona": {"id": f"p-{id_}", "nombre": "Ana", "apellido": "Ruiz", "titular": "Ingeniera", "ciudad": "Cali"},
              "empresa": {"id": f"p-{id_}", "nombre": "Caribe", "sector": "Tecnología", "tamano": "mediana", "ciudad": "Barranquilla",
                          "descripcion": "Software", "sitio_web": ""}}.get(tipo)
    return {"id": id_, "email": f"{id_}@prueba.co", "tipo": tipo, "perfil_id": perfil["id"] if perfil else None,
            "perfil": perfil, "rol_admin": rol_admin}


@pytest.fixture
def edicion(monkeypatch, llamadas):
    """Simula las cuentas que se pueden modificar y anota todo lo que se escribe."""
    def preparar(existentes):
        monkeypatch.setattr("app.routers.admin.cuentas.para_editar", lambda i: existentes.get(i))
        monkeypatch.setattr("app.routers.admin.cuentas.permisos_del_rol", lambda rol: ["catalogo.gestionar", "usuario.crear", "usuario.eliminar"])
        for ruta in ("cuentas.actualizar_email", "cuentas.actualizar_persona_basico", "cuentas.otorgar_admin", "cuentas.quitar_admin",
                     "cuentas.actualizar_hash", "cuentas.reiniciar_intentos", "empresas.actualizar", "sesiones.revocar_de_cuenta"):
            monkeypatch.setattr(f"app.routers.admin.{ruta}", (lambda r: lambda *a: llamadas.append((r, *a)))(ruta))
        monkeypatch.setattr("app.routers.admin.auth.confirmar_contrasena", lambda *a: llamadas.append(("confirmar", a[0])) or True)
    return preparar


def _escrituras(llamadas):
    return [x for x in llamadas if x[0].split(".")[-1] in ("actualizar_email", "actualizar_persona_basico", "otorgar_admin", "quitar_admin",
                                                           "actualizar_hash", "actualizar", "revocar_de_cuenta")]


FORM_PERSONA = {"nombre": "Ana", "apellido": "Ruiz", "titular": "Ingeniera", "ciudad": "Cali", "email": "c-p@prueba.co",
                "nueva_password": "", "password_admin": "la-del-admin"}


def test_editar_y_privilegios_exigen_su_permiso(cliente, como, edicion):
    existentes = {"c-p": _editable("c-p"), "c-s": _editable("c-s", "staff")}
    esperado = {"/admin/cuentas/c-p/editar": (403, 403, 403, 200), "/admin/cuentas/c-p/privilegios": (403, 403, 403, 200)}
    for ruta, quienes in esperado.items():
        obtenidos = []
        for tipo, permisos, perfil in [("persona", ["perfil.editar"], "u1"), ("empresa", ["oferta.publicar"], "e1"),
                                       ("staff", PERMISOS_STAFF, None), ("admin", PERMISOS_ADMIN, None)]:
            como(tipo, permisos, perfil)
            edicion(existentes)
            obtenidos.append(cliente.get(ruta).status_code)
        assert tuple(obtenidos) == quienes, ruta


@pytest.mark.parametrize("ruta", ["/admin/cuentas/c-p/editar", "/admin/cuentas/c-p/privilegios"])
def test_editar_y_privilegios_exigen_csrf_y_no_escriben_sin_el(cliente, como, edicion, llamadas, ruta):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p")})
    assert _post(cliente, ruta, {**FORM_PERSONA, "confirmar": "on", "password": "x"}, token=False).status_code == 403
    assert not _escrituras(llamadas)


def test_no_se_modifica_la_propia_cuenta_ni_una_inexistente(cliente, como, edicion, llamadas):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-yo": _editable("c-yo", "staff")})
    for ruta in ("/admin/cuentas/c-yo/editar", "/admin/cuentas/c-yo/privilegios"):
        assert cliente.get(ruta).status_code == 400
    assert _post(cliente, "/admin/cuentas/c-yo/editar", FORM_PERSONA).status_code == 400
    assert _post(cliente, "/admin/cuentas/c-yo/privilegios", {"confirmar": "on", "password": "x"}).status_code == 400
    assert cliente.get("/admin/cuentas/zzz/editar").status_code == 404 and cliente.get("/admin/cuentas/zzz/privilegios").status_code == 404
    assert not _escrituras(llamadas)


def test_cuentas_internas_exigen_staff_gestionar_para_modificarse(cliente, como, edicion, llamadas):
    como("admin", [p for p in PERMISOS_ADMIN if p != "staff.gestionar"])
    edicion({"c-s": _editable("c-s", "staff"), "c-a": _editable("c-a", "admin")})
    for c in ("c-s", "c-a"):
        assert cliente.get(f"/admin/cuentas/{c}/editar").status_code == 403
        assert _post(cliente, f"/admin/cuentas/{c}/editar", {"email": "x@p.co", "password_admin": "x"}).status_code == 403
    assert not _escrituras(llamadas)


# ------------------------------------------------------------------- editar
def test_el_formulario_de_editar_se_llena_y_cambia_segun_el_tipo(cliente, como, edicion):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p"), "c-e": _editable("c-e", "empresa"), "c-s": _editable("c-s", "staff")})
    html = cliente.get("/admin/cuentas/c-p/editar").text
    assert 'value="Ana"' in html and 'value="c-p@prueba.co"' in html and 'name="apellido"' in html and 'name="sector"' not in html
    html = cliente.get("/admin/cuentas/c-e/editar").text
    assert 'value="Caribe"' in html and 'name="sector"' in html and 'name="apellido"' not in html
    html = cliente.get("/admin/cuentas/c-s/editar").text
    assert 'name="apellido"' not in html and 'name="sector"' not in html and 'name="email"' in html
    assert all("value=" not in re.search(rf'<input[^>]*name="{n}"[^>]*>', html).group(0) for n in ("nueva_password", "password_admin"))


def test_editar_una_persona_cambia_correo_y_datos_y_deja_rastro(cliente, como, edicion, llamadas):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p")})
    r = _post(cliente, "/admin/cuentas/c-p/editar", {**FORM_PERSONA, "nombre": "  Ana   María ", "ciudad": "Bogotá", "email": " NUEVO@Prueba.co "})
    assert r.status_code == 303 and r.headers["location"] == "/admin?aviso=cuenta_modificada"
    assert ("cuentas.actualizar_email", "c-p", "nuevo@prueba.co") in llamadas
    datos = next(x for x in llamadas if x[0] == "cuentas.actualizar_persona_basico")
    assert datos[1] == "p-c-p" and datos[2] == {"nombre": "Ana María", "apellido": "Ruiz", "titular": "Ingeniera", "ciudad": "Bogotá"}
    assert any(x[0] == "app.routers.admin.eventos.registrar" and x[2] == "cuenta_modificada_admin" and "correo, datos del perfil" in x[4] for x in llamadas)
    assert ("confirmar", "c-yo") in llamadas                                 # se verifico la contrasena del ADMIN


def test_editar_sin_cambios_no_escribe_nada(cliente, como, edicion, llamadas):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p")})
    assert _post(cliente, "/admin/cuentas/c-p/editar", FORM_PERSONA).status_code == 303
    assert not _escrituras(llamadas)
    assert any(x[0] == "app.routers.admin.eventos.registrar" and "sin cambios" in x[4] for x in llamadas)


def test_editar_con_la_contrasena_del_admin_incorrecta_no_cambia_nada(cliente, como, edicion, llamadas, monkeypatch):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p")})
    monkeypatch.setattr("app.routers.admin.auth.confirmar_contrasena", lambda *a: False)
    r = _post(cliente, "/admin/cuentas/c-p/editar", {**FORM_PERSONA, "ciudad": "Bogotá"})
    assert r.status_code == 422 and "Tu contraseña no es correcta" in r.text and 'value="Bogotá"' in r.text   # conserva lo escrito
    assert not _escrituras(llamadas)


def test_editar_con_datos_invalidos_muestra_errores_y_ni_pide_la_contrasena(cliente, como, edicion, llamadas):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p")})
    r = _post(cliente, "/admin/cuentas/c-p/editar", {**FORM_PERSONA, "nombre": "", "ciudad": "", "email": "mal"})
    assert r.status_code == 422 and all(t in r.text for t in ("Escribe el nombre", "Escribe la ciudad", "correo válido"))
    assert not _escrituras(llamadas) and ("confirmar", "c-yo") not in llamadas


def test_editar_con_un_correo_repetido_no_aplica_ningun_otro_cambio(cliente, como, edicion, llamadas, monkeypatch):
    from neo4j.exceptions import ConstraintError
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p")})

    def duplicado(*a):
        raise ConstraintError("dup")
    monkeypatch.setattr("app.routers.admin.cuentas.actualizar_email", duplicado)
    r = _post(cliente, "/admin/cuentas/c-p/editar", {**FORM_PERSONA, "email": "otro@prueba.co", "ciudad": "Bogotá", "nueva_password": CLAVE_NUEVA})
    assert r.status_code == 422 and "ya está registrado" in r.text
    assert not _escrituras(llamadas)                                          # ni el perfil ni la contrasena


def test_editar_una_empresa(cliente, como, edicion, llamadas):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-e": _editable("c-e", "empresa")})
    r = _post(cliente, "/admin/cuentas/c-e/editar", {"nombre": "Caribe SAS", "sector": "Logística", "tamano": "grande", "ciudad": "Barranquilla",
                                                      "descripcion": "Software", "sitio_web": "https://c.example.com", "email": "c-e@prueba.co",
                                                      "nueva_password": "", "password_admin": "x"})
    assert r.status_code == 303
    escrito = next(x for x in llamadas if x[0] == "empresas.actualizar")
    assert escrito[1] == "p-c-e" and escrito[2]["nombre"] == "Caribe SAS" and escrito[2]["sector"] == "Logística" and escrito[2]["tamano"] == "grande"
    assert not [x for x in llamadas if x[0] == "cuentas.actualizar_email"]
    r = _post(cliente, "/admin/cuentas/c-e/editar", {"nombre": "X", "sector": "inventado", "tamano": "x", "ciudad": "B", "email": "c-e@prueba.co", "password_admin": "x"})
    assert r.status_code == 422 and "Elige un sector" in r.text


def test_restablecer_la_contrasena_la_guarda_con_hash_desbloquea_y_cierra_sesiones(cliente, como, edicion, llamadas):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p")})
    r = _post(cliente, "/admin/cuentas/c-p/editar", {**FORM_PERSONA, "nueva_password": CLAVE_NUEVA})
    assert r.status_code == 303
    hashed = next(x for x in llamadas if x[0] == "cuentas.actualizar_hash")
    assert hashed[1] == "c-p" and hashed[2].startswith("$argon2id$") and CLAVE_NUEVA not in hashed[2]
    assert ("cuentas.reiniciar_intentos", "c-p") in llamadas and ("sesiones.revocar_de_cuenta", "c-p") in llamadas
    assert all(CLAVE_NUEVA not in str(x) for x in llamadas if x[0] == "app.routers.admin.eventos.registrar")   # nunca queda en el registro
    assert any("contraseña restablecida" in x[4] for x in llamadas if x[0] == "app.routers.admin.eventos.registrar")


def test_una_contrasena_debil_no_se_acepta_al_restablecer(cliente, como, edicion, llamadas):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p")})
    r = _post(cliente, "/admin/cuentas/c-p/editar", {**FORM_PERSONA, "nueva_password": "corta"})
    assert r.status_code == 422 and "10 caracteres" in r.text
    assert not _escrituras(llamadas)


# -------------------------------------------------------------- privilegios
def test_la_pantalla_de_privilegios_lista_exactamente_lo_que_se_concede(cliente, como, edicion):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p"), "c-q": _editable("c-q", rol_admin=True)})
    html = cliente.get("/admin/cuentas/c-p/privilegios").text
    assert "Dar privilegios de administrador" in html and "<code>usuario.eliminar</code>" in html and "además" in html
    html = cliente.get("/admin/cuentas/c-q/privilegios").text
    assert "Retirar privilegios de administrador" in html and "data-permisos-admin" not in html


def test_dar_privilegios_de_admin_a_una_cuenta_existente(cliente, como, edicion, llamadas):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p"), "c-e": _editable("c-e", "empresa"), "c-s": _editable("c-s", "staff")})
    for destino, tipo in (("c-p", "persona"), ("c-e", "empresa"), ("c-s", "staff")):
        r = _post(cliente, f"/admin/cuentas/{destino}/privilegios", {"confirmar": "on", "password": "la-del-admin"})
        assert r.status_code == 303 and r.headers["location"] == "/admin?aviso=privilegios_otorgados"
        assert ("cuentas.otorgar_admin", destino) in llamadas
        assert any(x[0] == "app.routers.admin.eventos.registrar" and x[2] == "privilegios_otorgados" and x[4] == tipo for x in llamadas)
    assert not [x for x in llamadas if x[0] == "cuentas.quitar_admin"]


def test_retirar_privilegios_si_ya_los_tenia(cliente, como, edicion, llamadas):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-q": _editable("c-q", rol_admin=True)})
    r = _post(cliente, "/admin/cuentas/c-q/privilegios", {"confirmar": "on", "password": "x"})
    assert r.headers["location"] == "/admin?aviso=privilegios_retirados"
    assert ("cuentas.quitar_admin", "c-q") in llamadas and not [x for x in llamadas if x[0] == "cuentas.otorgar_admin"]


def test_privilegios_exigen_confirmar_y_la_contrasena_del_admin(cliente, como, edicion, llamadas, monkeypatch):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-p": _editable("c-p")})
    assert _post(cliente, "/admin/cuentas/c-p/privilegios", {"password": "x"}).status_code == 422
    monkeypatch.setattr("app.routers.admin.auth.confirmar_contrasena", lambda *a: False)
    r = _post(cliente, "/admin/cuentas/c-p/privilegios", {"confirmar": "on", "password": "mala"})
    assert r.status_code == 422 and "no es correcta" in r.text
    assert not _escrituras(llamadas)


def test_una_cuenta_de_tipo_admin_no_necesita_ni_admite_privilegios(cliente, como, edicion, llamadas):
    como("admin", PERMISOS_ADMIN)
    edicion({"c-a": _editable("c-a", "admin")})
    assert cliente.get("/admin/cuentas/c-a/privilegios").status_code == 400
    assert _post(cliente, "/admin/cuentas/c-a/privilegios", {"confirmar": "on", "password": "x"}).status_code == 400
    assert not _escrituras(llamadas)


def test_la_tabla_muestra_el_privilegio_y_las_acciones_segun_los_permisos(cliente, como, monkeypatch):
    fila = lambda id_, tipo, roles: {"id": id_, "email": f"{id_}@p.co", "tipo": tipo, "activa": True, "intentos": 0, "bloqueo_temporal": False, "perfil": id_, "roles": roles}
    filas = [fila("x-p", "persona", ["persona", "admin"]), fila("x-q", "persona", ["persona"]), fila("x-a", "admin", ["admin"])]
    como("admin", PERMISOS_ADMIN)
    monkeypatch.setattr("app.routers.admin.cuentas.listar", lambda _n: filas)
    html = cliente.get("/admin").text
    assert html.count("+ Admin") == 1                                          # solo quien tiene el privilegio ADICIONAL (no los de tipo admin)
    assert 'href="/admin/cuentas/x-p/editar"' in html and 'href="/admin/cuentas/x-q/privilegios"' in html
    assert 'href="/admin/cuentas/x-a/privilegios"' not in html and 'href="/admin/cuentas/x-a/editar"' in html
    como("staff", PERMISOS_STAFF)
    monkeypatch.setattr("app.routers.admin.cuentas.listar", lambda _n: filas[:2])
    html = cliente.get("/admin").text
    assert "/editar" not in html and "/privilegios" not in html


def test_con_privilegios_una_persona_entra_al_panel_y_lo_ve_en_su_menu(cliente, como, monkeypatch):
    como("persona", PERMISOS_ADMIN, "u1")                                      # una persona a la que se le dio el rol admin
    assert cliente.get("/admin").status_code == 200
    assert 'href="/admin"' in cliente.get("/cuenta").text and "Panel de administración" in cliente.get("/cuenta").text
    como("persona", ["perfil.editar"], "u1")                                   # una persona comun no
    assert cliente.get("/admin").status_code == 403
    assert "Panel de administración" not in cliente.get("/cuenta").text


def test_poder_editar_cuentas_no_basta_para_dar_privilegios_de_admin(cliente, como, edicion, llamadas):
    """Dar el rol admin es lo mas delicado: exige 'staff.gestionar', un permiso distinto de 'usuario.editar'."""
    como("admin", ["usuario.bloquear", "usuario.editar"])
    edicion({"c-p": _editable("c-p")})
    assert cliente.get("/admin/cuentas/c-p/editar").status_code == 200           # puede editar datos...
    assert cliente.get("/admin/cuentas/c-p/privilegios").status_code == 403      # ...pero no dar privilegios
    assert _post(cliente, "/admin/cuentas/c-p/privilegios", {"confirmar": "on", "password": "x"}).status_code == 403
    assert not [x for x in llamadas if x[0].endswith("otorgar_admin")]
    como("admin", ["usuario.bloquear", "staff.gestionar"])                       # y al reves: puede darlos aunque no edite datos
    edicion({"c-p": _editable("c-p")})
    assert cliente.get("/admin/cuentas/c-p/privilegios").status_code == 200
    assert cliente.get("/admin/cuentas/c-p/editar").status_code == 403


def test_un_permiso_no_alcanza_para_otro_en_las_acciones_nuevas(cliente, como, edicion, llamadas):
    como("admin", ["usuario.bloquear", "staff.gestionar", "usuario.crear", "usuario.eliminar", "catalogo.gestionar"])   # todo menos editar
    edicion({"c-p": _editable("c-p")})
    assert _post(cliente, "/admin/cuentas/c-p/editar", FORM_PERSONA).status_code == 403
    assert not _escrituras(llamadas)
