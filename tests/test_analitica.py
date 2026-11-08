"""Fase 7: analitica de la red (panel, recalculo con GDS y mapa). Sin Neo4j: todo se simula."""
import json
import re

import pytest
from neo4j.exceptions import ClientError

from app.services import analitica as servicio

TOKEN = "token-csrf"
PERMISOS_STAFF = ["usuario.bloquear", "contenido.moderar", "catalogo.gestionar"]
PERMISOS_ADMIN = PERMISOS_STAFF + ["analitica.administrar", "consultas.ver", "staff.gestionar", "sistema.auditar", "usuario.crear",
                                   "usuario.eliminar", "usuario.editar"]


def _u(id_, nombre, pr=None, comunidad=None, ib=None, conexiones=0, empresa=None):
    return {"usuario": {"id": id_, "nombre": nombre, "apellido": "Prueba", "titular": f"Titular {nombre}",
                        "pagerank": pr, "comunidad": comunidad, "intermediacion": ib},
            "conexiones": conexiones, "empresa": empresa}


# ------------------------------------------------------------- servicio (puro)
def test_comunidades_se_numeran_de_la_mas_grande_a_la_mas_pequena():
    usuarios = [_u("a", "A", comunidad=7), _u("b", "B", comunidad=7), _u("c", "C", comunidad=7),
                _u("d", "D", comunidad=3), _u("e", "E", comunidad=9), _u("f", "F", comunidad=9), _u("g", "G")]
    assert servicio.numerar_comunidades(usuarios) == {7: 1, 9: 2, 3: 3}


def test_influyentes_ordena_por_pagerank_y_compara_con_las_conexiones():
    usuarios = [_u("a", "A", pr=0.30, conexiones=3), _u("b", "B", pr=0.20, conexiones=9),
                _u("c", "C", pr=0.10, conexiones=9), _u("d", "D", pr=None, conexiones=50)]
    filas = servicio.influyentes(usuarios, {}, 10)
    assert [f["usuario"]["id"] for f in filas] == ["a", "b", "c"]            # sin metrica no entra
    assert [f["puesto"] for f in filas] == [1, 2, 3]
    assert [f["puesto_conexiones"] for f in filas] == [3, 1, 1]              # b y c empatan en el 1.o por conexiones


def test_influyentes_respeta_el_limite():
    usuarios = [_u(str(i), str(i), pr=i / 100) for i in range(1, 30)]
    assert len(servicio.influyentes(usuarios, {}, 10)) == 10


def test_puentes_ignora_a_quien_no_conecta_nada():
    usuarios = [_u("a", "A", ib=12.0), _u("b", "B", ib=0.0), _u("c", "C", ib=None), _u("d", "D", ib=3.5)]
    assert [f["usuario"]["id"] for f in servicio.puentes(usuarios, {}, 5)] == ["a", "d"]


def test_comunidad_se_nombra_con_el_sector_y_las_habilidades_del_grafo():
    usuarios = [_u("a", "A", pr=0.2, comunidad=5), _u("b", "B", pr=0.4, comunidad=5), _u("c", "C", pr=0.1, comunidad=8)]
    num = servicio.numerar_comunidades(usuarios)
    habs = [{"comunidad": 5, "habilidad": "Python", "personas": 2}, {"comunidad": 5, "habilidad": "SQL", "personas": 2},
            {"comunidad": 5, "habilidad": "Docker", "personas": 1}, {"comunidad": 5, "habilidad": "Excel", "personas": 1},
            {"comunidad": 8, "habilidad": "Diseño", "personas": 1}]
    sect = [{"comunidad": 5, "sector": "Tecnologia", "personas": 2}, {"comunidad": 5, "sector": "Salud", "personas": 1}]
    c = servicio.comunidades(usuarios, num, habs, sect)
    assert [x["numero"] for x in c] == [1, 2]
    assert c[0]["etiqueta"] == "Tecnologia · Python, SQL, Docker"             # 3 habilidades como maximo
    assert [u["id"] for u in c[0]["lideres"]] == ["b", "a"]                    # el mas influyente primero
    assert c[1]["etiqueta"] == "Diseño"                                        # sin sector: solo habilidades


def test_comunidad_sin_datos_tiene_etiqueta_honesta():
    usuarios = [_u("a", "A", comunidad=1)]
    assert servicio.comunidades(usuarios, {1: 1}, [], [])[0]["etiqueta"] == "Sin datos suficientes"


def test_hay_metricas():
    assert not servicio.hay_metricas([_u("a", "A")]) and servicio.hay_metricas([_u("a", "A", pr=0.1)])


# ----------------------------------------------------------------- fixtures
def _sesion(tipo, permisos, perfil_id=None):
    return {"tipo": tipo, "perfil_id": perfil_id, "perfil_nombre": "Prueba", "cuenta_id": "c-yo", "csrf_token": TOKEN,
            "roles": [tipo], "permisos": list(permisos), "email": "yo@prueba.co"}


# La red de prueba: u1 (Ana) conoce a u2 y u3; u4 (Dani) no conoce a nadie de ellos.
# Comunidades de Louvain: u1 y u2 en la 10, u3 en la 20, u4 en la 30. La empresa e1 emplea a u1 y recibio postulacion de u3 y u4.
USUARIOS = [_u("u1", "Ana", 0.31, 10, 8.0, 5, "Caribe Labs"), _u("u2", "Beto", 0.22, 10, 1.0, 9),
            _u("u3", "Caro", 0.12, 20, 0.0, 2), _u("u4", "Dani", 0.05, 30, 0.0, 1)]
ARISTAS = [{"origen": "u1", "destino": "u2"}, {"origen": "u1", "destino": "u3"}, {"origen": "u3", "destino": "u4"}, {"origen": "u2", "destino": "u3"}]


@pytest.fixture
def llamadas():
    return []


@pytest.fixture
def como(monkeypatch, llamadas):
    def activar(tipo, permisos=(), perfil_id=None, metricas=True, gds=True):
        monkeypatch.setattr("app.dependencias.cuenta_opcional", lambda _r: _sesion(tipo, permisos, perfil_id))
        monkeypatch.setattr("app.dependencias.usuarios.resumen", lambda _id: {
            "id": _id, "nombre": "Ana", "apellido": "Ruiz", "titular": "T", "ciudad": "C", "empresa": None, "cargo": None,
            "rol_empresa": None, "conexiones": 0, "postulaciones": 0, "sin_leer": 0, "solicitudes": 0})
        usuarios = USUARIOS if metricas else [_u(u["usuario"]["id"], u["usuario"]["nombre"]) for u in USUARIOS]
        r = "app.routers.analitica.repo."
        monkeypatch.setattr(r + "usuarios_con_metricas", lambda *a, **k: usuarios)
        monkeypatch.setattr(r + "estado_metricas", lambda: ({"calculado_en": None, "calculado_por": "admin@x.co", "usuarios": 4, "comunidades": 3} if metricas else None))
        monkeypatch.setattr(r + "resumen_red", lambda: {"usuarios": 4, "conexiones": 11, "empresas": 3, "ofertas": 5, "proyectos": 2})
        monkeypatch.setattr(r + "habilidades_por_comunidad", lambda ids=None: (llamadas.append(("habilidades", None if ids is None else tuple(ids))),
                            [{"comunidad": 10, "habilidad": "Python", "personas": 2}, {"comunidad": 20, "habilidad": "Diseño", "personas": 1}])[1])
        monkeypatch.setattr(r + "sectores_por_comunidad", lambda ids=None: [{"comunidad": 10, "sector": "Tecnologia", "personas": 2}])
        monkeypatch.setattr(r + "brecha_habilidades", lambda _n: [{"habilidad": "Inglés", "demanda": 7, "talento": 12},
                                                                  {"habilidad": "Python", "demanda": 6, "talento": 3},
                                                                  {"habilidad": "Rust", "demanda": 0, "talento": 0}])
        monkeypatch.setattr(r + "gds_disponible", lambda: (llamadas.append(("gds",)), gds)[1])
        monkeypatch.setattr(r + "contactos_de", lambda uid: {"yo": uid, "contactos": ["u2", "u3"]})
        monkeypatch.setattr(r + "red_de_empresa", lambda eid: {"empleados": ["u1"], "postulantes": ["u3", "u4"]})
        monkeypatch.setattr(r + "aristas_entre", lambda ids: (llamadas.append(("aristas", tuple(sorted(ids)))),
                                                             [a for a in ARISTAS if a["origen"] in ids and a["destino"] in ids])[1])
        monkeypatch.setattr("app.routers.analitica.eventos.registrar", lambda *a: llamadas.append(("evento", a[1], a[3])))
    return activar


def _post(cliente, ruta, token=True):
    return cliente.post(ruta, data={"csrf_token": TOKEN} if token else {})


def _en_tabla(html, tabla):
    return html.split(f'data-tabla="{tabla}"')[1].split("</table>")[0]


def _personas_en_la_pagina(html):
    return {n for n in ("Ana", "Beto", "Caro", "Dani") if f"/perfil/u{['Ana', 'Beto', 'Caro', 'Dani'].index(n) + 1}\"" in html}


def _indicador(html, nombre):
    m = re.search(rf'data-indicador="{nombre}"[^>]*>\s*<[^>]*>\s*([^<]+)<', html)
    assert m, f"sin indicador {nombre}"
    return m.group(1).strip()


PERSONA = ("persona", ["perfil.editar"], "u1")
EMPRESA = ("empresa", ["oferta.publicar"], "e1")
STAFF = ("staff", PERMISOS_STAFF, None)
ADMIN = ("admin", PERMISOS_ADMIN, None)


# ------------------------------------------------------------------- panel
def test_el_panel_exige_sesion(cliente):
    r = cliente.get("/analitica")
    assert r.status_code == 303 and r.headers["location"].startswith("/login")


@pytest.mark.parametrize("cuenta", [PERSONA, EMPRESA, ADMIN])
def test_personas_empresas_y_admin_ven_el_panel_con_estilo_oscuro(cliente, como, cuenta):
    como(*cuenta)
    r = cliente.get("/analitica")
    assert r.status_code == 200 and 'class="panel-interno"' in r.text
    assert all(f'data-tabla="{t}"' in r.text for t in ("influyentes", "puentes", "demanda"))


def test_el_staff_no_tiene_analitica(cliente, como):
    como(*STAFF)
    assert cliente.get("/analitica").status_code == 403
    assert cliente.get("/analitica/mapa").status_code == 403
    assert cliente.get("/analitica/mapa.json").status_code == 403


# ----------------------------------------------------- cada quien ve su circulo
def test_una_persona_solo_ve_la_analitica_de_ella_y_de_sus_contactos(cliente, como):
    como(*PERSONA)
    html = cliente.get("/analitica").text
    assert _personas_en_la_pagina(html) == {"Ana", "Beto", "Caro"}            # Dani no es su contacto: no aparece en NINGUNA tabla
    assert "Dani" not in html
    assert 'data-alcance="persona"' in html and "Tu red por dentro" in html
    assert _indicador(html, "personas") == "3" and _indicador(html, "conexiones") == "3"   # u1-u2, u1-u3, u2-u3


def test_las_comunidades_de_una_persona_se_numeran_y_cuentan_dentro_de_su_circulo(cliente, como, llamadas):
    como(*PERSONA)
    html = cliente.get("/analitica").text
    assert 'data-comunidad="1"' in html and 'data-comunidad="2"' in html and 'data-comunidad="3"' not in html   # la 30 (Dani) no existe para ella
    assert _indicador(html, "comunidades") == "2"
    assert ("habilidades", ("u1", "u2", "u3")) in llamadas                      # las habilidades de cada comunidad solo cuentan a su circulo


def test_una_empresa_ve_a_sus_trabajadores_y_a_quienes_se_postularon(cliente, como, llamadas):
    como(*EMPRESA)
    html = cliente.get("/analitica").text
    assert _personas_en_la_pagina(html) == {"Ana", "Caro", "Dani"}              # trabajador + postulantes; Beto (contacto de Ana) no
    assert "Beto" not in html
    assert 'data-alcance="empresa"' in html and "Tu equipo y tus candidatos" in html
    assert _indicador(html, "trabajadores") == "1" and _indicador(html, "postulantes") == "2"
    assert ("habilidades", ("u1", "u3", "u4")) in llamadas


def test_el_admin_ve_toda_la_red(cliente, como, llamadas):
    como(*ADMIN)
    html = cliente.get("/analitica").text
    assert _personas_en_la_pagina(html) == {"Ana", "Beto", "Caro", "Dani"}
    assert 'data-alcance="red"' in html and "La red por dentro" in html
    assert _indicador(html, "personas") == "4" and _indicador(html, "empresas") == "3" and _indicador(html, "ofertas") == "5"
    assert ("habilidades", None) in llamadas                                    # sin filtro: toda la red


def test_los_privilegios_de_admin_dan_la_vista_completa_aunque_sea_una_persona(cliente, como):
    como("persona", PERMISOS_ADMIN, "u1")
    html = cliente.get("/analitica").text
    assert 'data-alcance="red"' in html and "Dani" in html
    como(*PERSONA)
    assert "Dani" not in cliente.get("/analitica").text                         # y al perderlos vuelve a ver solo su circulo


def test_el_panel_muestra_influencia_comunidades_y_puentes(cliente, como):
    como(*ADMIN)
    html = cliente.get("/analitica").text
    assert "0.310" in html and "Caribe Labs" in html
    assert "Comunidad 1" in html and "Tecnologia · Python" in html
    assert re.search(r'data-comunidad="3"', html)
    assert "8.0" in _en_tabla(html, "puentes")


def test_el_panel_senala_cuando_el_orden_difiere_del_de_conexiones(cliente, como):
    como(*ADMIN)
    assert "(baja)" in _en_tabla(cliente.get("/analitica").text, "influyentes") or "(sube)" in _en_tabla(cliente.get("/analitica").text, "influyentes")


def test_demanda_frente_a_talento_y_oculta_lo_que_nadie_pide(cliente, como):
    como(*PERSONA)                                # dato de mercado, no de personas: lo ven todos
    html = _en_tabla(cliente.get("/analitica").text, "demanda")
    assert "Inglés" in html and "Hay más personas que ofertas" in html
    assert "Python" in html and "Hay más ofertas que personas" in html and "Rust" not in html


def test_sin_metricas_se_explica_que_hacer_segun_quien_mira(cliente, como):
    como(*PERSONA, metricas=False)
    html = cliente.get("/analitica").text
    assert "Sin métricas todavía" in html and "Un administrador las calcula" in html and 'data-tabla="influyentes"' not in html
    assert _indicador(html, "comunidades") == "—"
    como(*ADMIN, metricas=False)
    assert 'Calcúlalas con' in cliente.get("/analitica").text


def test_avisa_si_la_red_cambio_desde_el_ultimo_calculo_solo_al_admin(cliente, como, monkeypatch):
    como(*ADMIN)
    monkeypatch.setattr("app.routers.analitica.repo.resumen_red", lambda: {"usuarios": 9, "conexiones": 1, "empresas": 1, "ofertas": 1, "proyectos": 1})
    assert "La red cambió desde el último cálculo" in cliente.get("/analitica").text
    como(*PERSONA)
    assert "La red cambió" not in cliente.get("/analitica").text


def test_botones_segun_el_tipo_de_cuenta(cliente, como, llamadas):
    como(*PERSONA)
    html = cliente.get("/analitica").text
    assert "Recalcular métricas" not in html and 'href="/consultas"' not in html and 'href="/analitica/mapa"' in html
    assert ("gds",) not in llamadas                                              # a una persona no se le consulta GDS
    como(*ADMIN)
    html = cliente.get("/analitica").text
    assert 'action="/analitica/recalcular"' in html and 'href="/consultas"' in html
    como(*ADMIN, gds=False)
    html = cliente.get("/analitica").text
    assert "GDS no disponible" in html and 'action="/analitica/recalcular"' not in html


def test_enlaces_del_menu_a_la_analitica(cliente, como):
    for cuenta, visible in [(PERSONA, True), (EMPRESA, True), (ADMIN, True), (STAFF, False)]:
        como(*cuenta)
        assert ('href="/analitica"' in cliente.get("/cuenta").text) is visible, cuenta[0]


# ---------------------------------------------------------------- recalcular
def _resultado(hechos=("pagerank", "comunidad", "intermediacion"), fallos=None):
    return {"usuarios": 27, "conexiones": 61, "comunidades": 4, "hechos": list(hechos), "fallos": fallos or {}}


def test_solo_el_admin_recalcula(cliente, como, monkeypatch, llamadas):
    monkeypatch.setattr("app.routers.analitica.repo.recalcular", lambda por: llamadas.append(("recalcular", por)) or _resultado())
    como(*ADMIN)
    assert _post(cliente, "/analitica/recalcular", token=False).status_code == 403          # sin CSRF
    for cuenta in (PERSONA, EMPRESA, STAFF):
        como(*cuenta)
        assert _post(cliente, "/analitica/recalcular").status_code == 403
    assert not [x for x in llamadas if x[0] == "recalcular"]


def test_recalcular_deja_rastro_y_vuelve_al_panel(cliente, como, monkeypatch, llamadas):
    monkeypatch.setattr("app.routers.analitica.repo.recalcular", lambda por: llamadas.append(("recalcular", por)) or _resultado())
    como(*ADMIN)
    r = _post(cliente, "/analitica/recalcular")
    assert r.status_code == 303 and r.headers["location"] == "/analitica?aviso=metricas_recalculadas"
    assert ("recalcular", "yo@prueba.co") in llamadas
    assert any(x[0] == "evento" and x[1] == "metricas_recalculadas" and "4 comunidades" in x[2] for x in llamadas)


def test_recalcular_sin_gds_no_intenta_nada(cliente, como, monkeypatch, llamadas):
    monkeypatch.setattr("app.routers.analitica.repo.recalcular", lambda por: llamadas.append(("recalcular", por)) or _resultado())
    como(*ADMIN, gds=False)
    assert _post(cliente, "/analitica/recalcular").headers["location"] == "/analitica?error=gds_no_disponible"
    assert not [x for x in llamadas if x[0] == "recalcular"]


def test_recalcular_con_un_algoritmo_caido_avisa_que_fue_parcial(cliente, como, monkeypatch):
    como(*ADMIN)
    monkeypatch.setattr("app.routers.analitica.repo.recalcular", lambda por: _resultado(("pagerank", "comunidad"), {"intermediacion": "no existe"}))
    assert _post(cliente, "/analitica/recalcular").headers["location"] == "/analitica?aviso=metricas_parciales"


def test_recalcular_fallido_no_se_presenta_como_exito(cliente, como, monkeypatch):
    como(*ADMIN)
    monkeypatch.setattr("app.routers.analitica.repo.recalcular", lambda por: _resultado((), {"pagerank": "x", "comunidad": "x"}))
    assert _post(cliente, "/analitica/recalcular").headers["location"] == "/analitica?error=metricas_fallidas"

    def explota(_por):
        raise ClientError("fallo al proyectar el grafo")
    monkeypatch.setattr("app.routers.analitica.repo.recalcular", explota)
    assert _post(cliente, "/analitica/recalcular").headers["location"] == "/analitica?error=metricas_fallidas"


# --------------------------------------------------------------------- mapa
def test_el_mapa_de_una_persona_solo_incluye_a_ella_y_sus_contactos(cliente, como, llamadas):
    como(*PERSONA)
    assert cliente.get("/analitica/mapa").status_code == 200
    datos = cliente.get("/analitica/mapa.json").json()
    assert datos["alcance"] == "persona"
    assert sorted(n["id"] for n in datos["nodos"]) == ["u1", "u2", "u3"]       # u4 no es contacto: no aparece
    assert ("aristas", ("u1", "u2", "u3")) in llamadas                          # y solo se piden aristas entre esos tres
    assert all(a["origen"] != "u4" and a["destino"] != "u4" for a in datos["aristas"])
    assert [n["yo"] for n in datos["nodos"] if n["id"] == "u1"] == [True]


def test_el_mapa_de_una_empresa_incluye_su_equipo_y_solo_los_vinculos_con_el(cliente, como):
    como(*EMPRESA)
    datos = cliente.get("/analitica/mapa.json").json()
    assert datos["alcance"] == "empresa" and sorted(n["id"] for n in datos["nodos"]) == ["u1", "u3", "u4"]
    pares = {(a["origen"], a["destino"]) for a in datos["aristas"]}
    assert pares == {("u1", "u3")}      # u3-u4 son dos candidatos entre si: no se muestra; u1 (trabajador)-u3 si
    assert cliente.get("/analitica/mapa").status_code == 200


def test_el_admin_ve_el_mapa_de_toda_la_red(cliente, como):
    como(*ADMIN)
    datos = cliente.get("/analitica/mapa.json").json()
    assert datos["alcance"] == "red" and len(datos["nodos"]) == 4
    assert cliente.get("/analitica/mapa").status_code == 200


@pytest.mark.parametrize("cuenta,pide", [(PERSONA, "red"), (PERSONA, "empresa"), (EMPRESA, "red"), (EMPRESA, "persona"), (ADMIN, "persona")])
def test_nadie_pide_el_mapa_de_otro_alcance(cliente, como, cuenta, pide):
    como(*cuenta)
    assert cliente.get(f"/analitica/mapa.json?alcance={pide}").status_code == 403
    assert cliente.get(f"/analitica/mapa?alcance={pide}").status_code == 403


def test_el_mapa_entrega_comunidades_numeradas_dentro_del_circulo(cliente, como):
    como(*PERSONA)
    datos = cliente.get("/analitica/mapa.json").json()
    por_id = {n["id"]: n for n in datos["nodos"]}
    assert por_id["u1"]["comunidad"] == 1 and por_id["u2"]["comunidad"] == 1 and por_id["u3"]["comunidad"] == 2
    assert [c["numero"] for c in datos["comunidades"]] == [1, 2]


def test_la_pagina_del_mapa_no_tiene_scripts_en_linea(cliente, como):
    como(*PERSONA)
    html = cliente.get("/analitica/mapa").text
    etiquetas = re.findall(r"<script\b[^>]*>", html)
    assert len(etiquetas) == 2 and all("src=" in e for e in etiquetas)           # la CSP solo permite scripts propios
    assert "vendor/cytoscape/cytoscape.min.js" in html and "js/mapa-red.js" in html
    assert 'role="img"' in html and "aria-label=" in html and 'aria-live="polite"' in html


def test_cytoscape_esta_empaquetado_con_su_licencia(cliente):
    js = cliente.get("/static/vendor/cytoscape/cytoscape.min.js")
    assert js.status_code == 200 and len(js.content) > 100_000
    assert "Permission is hereby granted" in cliente.get("/static/vendor/cytoscape/LICENSE").text
    assert cliente.get("/static/js/mapa-red.js").status_code == 200


# ------------------------------------------------------------------ permisos
def _linea_de_rol(esquema, rol):
    i = esquema.index(f"rol: '{rol}'")
    return esquema[i:esquema.index("}", i)]


def test_los_permisos_estan_en_el_esquema_y_en_la_migracion():
    esquema = open("cypher/01_schema.cypher", encoding="utf-8-sig").read()
    admin, staff = _linea_de_rol(esquema, "admin"), _linea_de_rol(esquema, "staff")
    for permiso in ("analitica.administrar", "consultas.ver", "usuario.editar"):
        assert permiso in admin and permiso not in staff, permiso               # solo el admin
    migracion = open("cypher/07_permisos_analitica.cypher", encoding="utf-8-sig").read()
    assert all(p in migracion for p in ("analitica.administrar", "consultas.ver", "usuario.editar"))
    assert "DELETE x" in migracion and "'staff'" in migracion                    # y se le quita al staff si lo tenia
