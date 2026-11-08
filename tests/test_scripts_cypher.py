"""Los scripts de la carpeta cypher/ y su coherencia con la aplicacion."""
import importlib.util
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def leer(rel: str) -> str:
    return (RAIZ / rel).read_text(encoding="utf-8-sig").replace("\r\n", "\n")


# ------------------------------------------------ 03_consultas.cypher: mismo texto que ejecuta la app
def _generador():
    spec = importlib.util.spec_from_file_location("generar_consultas", RAIZ / "cypher" / "generar_consultas.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_03_consultas_es_exactamente_lo_que_genera_la_app():
    """Si cambias una consulta de consultas_documento.py y olvidas regenerar el script, esta prueba falla:
    ejecuta  python cypher/generar_consultas.py"""
    assert leer("cypher/03_consultas.cypher") == _generador().generar()


def test_03_consultas_incluye_cada_consulta_del_documento_textualmente():
    from app.repositories import consultas_documento as cd
    script = leer("cypher/03_consultas.cypher")
    constantes = {n: getattr(cd, n) for n in dir(cd) if n.isupper() and isinstance(getattr(cd, n), str)}
    assert len(constantes) == 16
    for nombre, texto in constantes.items():
        assert texto in script, f"{nombre} no aparece en 03_consultas.cypher"


def test_03_consultas_trae_los_parametros_de_todas_las_consultas():
    script = leer("cypher/03_consultas.cypher")
    declarados = set(re.findall(r"(\w+): ", re.search(r"^:params \{(.*)\}$", script, re.M).group(1)))
    usados = set(re.findall(r"\$(\w+)", re.sub(r"^//.*$", "", script, flags=re.M)))
    assert usados <= declarados, f"faltan en :params: {usados - declarados}"


def test_03_consultas_conserva_los_ejemplos_de_crud_y_de_profile():
    script = leer("cypher/03_consultas.cypher")
    for pieza in ("CREATE (u:Usuario", "SET u.titular", "DELETE s", "DETACH DELETE u", "PROFILE\nMATCH"):
        assert pieza in script, pieza


# ------------------------------------------------ 02_datos.cypher: los datos de demostracion no caducan
def _ofertas_02():
    return {m.group(1): (m.group(2), int(m.group(3)), int(m.group(4))) for m in re.finditer(
        r"\{id:'(o\d+)'.*?estado:'(\w+)',\s*publicada_hace:(\d+),\s*cierra_en:(-?\d+)\}", leer("cypher/02_datos.cypher"))}


def test_las_fechas_de_las_ofertas_son_relativas_al_dia_de_la_carga():
    datos = leer("cypher/02_datos.cypher")
    ofertas = _ofertas_02()
    assert len(ofertas) == 13
    for linea in datos.splitlines():
        if linea.strip().startswith("{id:'o"):
            assert not re.search(r"'20\d\d-\d\d-\d\d'", linea), f"fecha fija en una oferta: {linea[:60]}"
    assert "duration({days: f.cierra_en})" in datos and "duration({days: f.publicada_hace})" in datos


def test_las_ofertas_abiertas_cierran_con_mucho_margen_y_la_cerrada_sigue_cerrada():
    ofertas = _ofertas_02()
    abiertas = {k: v for k, v in ofertas.items() if v[0] == "abierta"}
    assert len(abiertas) == 12 and all(cierre >= 45 for _, _, cierre in abiertas.values()), abiertas
    assert all(publicada > 0 for _, publicada, _ in ofertas.values())
    estado, _, cierre = ofertas["o13"]
    assert estado == "cerrada" and cierre < 0


def test_postulaciones_invitaciones_y_avisos_tambien_son_relativos():
    datos = leer("cypher/02_datos.cypher")
    assert not re.search(r"\['u\d+','o\d+','\w+','20\d\d", datos)                     # postulaciones
    assert not re.search(r"\['u\d+','u\d+','[^']*','20\d\d", datos)                    # invitaciones
    assert not re.search(r"fecha:'20\d\d", datos)                                       # avisos
    assert datos.count("duration({days: t[3]})") == 1 and "duration({days: s[3]})" in datos and "duration({days: f.hace_dias})" in datos
    assert re.search(r"\['u26','o01','enviada',\d+\]", datos)


def test_08_renueva_exactamente_las_ofertas_abiertas_de_02_con_los_mismos_plazos():
    script = leer("cypher/08_renovar_fechas_demo.cypher")
    plazos_08 = {k: int(v) for k, v in re.findall(r"\['(o\d+)', (\d+)\]", script)}
    plazos_02 = {k: cierre for k, (estado, _, cierre) in _ofertas_02().items() if estado == "abierta"}
    assert plazos_08 == plazos_02


def test_08_solo_toca_ofertas_abiertas_y_solo_su_fecha_de_cierre():
    sin_comentarios = "\n".join(l for l in leer("cypher/08_renovar_fechas_demo.cypher").splitlines() if not l.strip().startswith("//"))
    assert "estado: 'abierta'" in sin_comentarios and "SET o.fecha_cierre" in sin_comentarios
    assert not re.search(r"\b(CREATE|MERGE|DELETE|DETACH|REMOVE)\b", sin_comentarios)
    assert sin_comentarios.count("SET") == 1


def test_los_scripts_se_dividen_en_sentencias_como_lo_hace_ejecutar_cypher():
    """Ejecutar_cypher.py quita las lineas de comentario y corta en ';' al final de linea."""
    for rel, esperadas in (("cypher/01_schema.cypher", None), ("cypher/02_datos.cypher", 15), ("cypher/08_renovar_fechas_demo.cypher", 1)):
        texto = "\n".join(l for l in leer(rel).splitlines() if not l.strip().startswith("//"))
        sentencias = [p.strip() for p in re.split(r";\s*(?:\n|$)", texto) if p.strip()]
        assert all(re.match(r"(UNWIND|MATCH|CREATE|MERGE|WITH)", s) for s in sentencias), rel
        if esperadas:
            assert len(sentencias) == esperadas, rel


# ------------------------------------------------ permisos: lo que el codigo exige existe en el esquema
def test_todo_permiso_que_exige_la_aplicacion_esta_definido_en_el_esquema():
    """Evita el error clasico: agregar un permiso en el codigo y olvidar darselo a un rol en 01_schema.cypher."""
    esquema = leer("cypher/01_schema.cypher")
    definidos = set(re.findall(r"'([a-z]+\.[a-z_]+)'", esquema))
    exigidos = set()
    for ruta in list((RAIZ / "app").rglob("*.py")) + list((RAIZ / "app" / "templates").glob("*.html")):
        texto = ruta.read_text(encoding="utf-8-sig")
        exigidos |= set(re.findall(r'permiso_(?:requerido|post)\(\s*"([a-z]+\.[a-z_]+)"', texto))
        exigidos |= set(re.findall(r'"([a-z]+\.[a-z_]+)" in yo\["permisos"\]', texto))
        exigidos |= set(re.findall(r"'([a-z]+\.[a-z_]+)' in yo\.permisos", texto))
    assert len(exigidos) >= 10, exigidos
    assert exigidos <= definidos, f"permisos que exige la app y no estan en 01_schema.cypher: {sorted(exigidos - definidos)}"


def test_los_scripts_de_migracion_existen_y_cubren_los_permisos_nuevos():
    for rel in ("cypher/06_permisos_admin.cypher", "cypher/07_permisos_analitica.cypher", "cypher/08_renovar_fechas_demo.cypher"):
        assert (RAIZ / rel).exists(), rel
    migraciones = leer("cypher/06_permisos_admin.cypher") + leer("cypher/07_permisos_analitica.cypher")
    for permiso in ("usuario.crear", "usuario.eliminar", "catalogo.gestionar", "analitica.administrar", "consultas.ver", "usuario.editar"):
        assert permiso in migraciones, permiso
