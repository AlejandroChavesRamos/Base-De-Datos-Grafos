"""El README es lo primero que lee quien evalua o instala el proyecto: lo que dice debe ser verdad."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
README = (RAIZ / "README.md").read_text(encoding="utf-8").replace("\r\n", "\n")


def test_el_readme_esta_en_utf8_y_con_las_secciones_clave():
    for seccion in ("## Requisitos", "## Cómo correr el proyecto", "## Cuentas de demostración", "## Qué cubre del enunciado",
                    "## Modelo del grafo", "## Scripts de la carpeta `cypher/`", "## Pruebas", "## Solución de problemas", "## Seguridad"):
        assert seccion in README, seccion


def test_los_requisitos_estan_todos_y_gds_figura_como_requisito():
    for requisito in ("Python", "Neo4j", "Node.js", "WebGL", "Graph Data Science", "RETURN gds.version()", "Neo4j Aura Free no incluye GDS"):
        assert requisito in README, requisito
    seccion = README.split("### El plugin Graph Data Science es un requisito")[1].split("##")[0]
    assert "quedan vacías" in seccion and "Recalcular métricas" in README


def test_cada_script_de_cypher_esta_explicado():
    scripts = sorted(p.name for p in (RAIZ / "cypher").iterdir() if p.suffix in (".cypher", ".py"))
    assert len(scripts) >= 10
    for nombre in scripts:
        assert f"`{nombre}`" in README or nombre.split(".")[0] in README, f"el README no menciona {nombre}"


def test_cada_variable_del_env_example_esta_documentada_con_su_valor():
    variables = dict(l.split("=", 1) for l in (RAIZ / ".env.example").read_text(encoding="utf-8-sig").replace("\r", "").splitlines()
                     if l and not l.startswith("#"))
    assert len(variables) >= 9
    for nombre, valor in variables.items():
        assert f"`{nombre}`" in README, nombre
        if nombre != "NEO4J_PASSWORD":
            assert f"`{valor}`" in README, f"{nombre}: el valor por defecto del README no coincide con .env.example ({valor})"


def test_los_comandos_del_readme_usan_archivos_que_existen():
    rutas = set(re.findall(r"`?((?:cypher|app|tests)/[\w./{}-]+?\.(?:py|cypher|js|mjs|css|html))`?", README))
    rutas |= set(re.findall(r"python (cypher/[\w.]+\.py)", README)) | set(re.findall(r"Ejecutar_cypher\.py (cypher/[\w.]+)", README))
    assert len(rutas) >= 8
    faltan = sorted(r for r in rutas if "{" not in r and not (RAIZ / r).exists())
    assert not faltan, f"el README menciona archivos que no existen: {faltan}"


def test_las_cuentas_de_demostracion_coinciden_con_generar_cuentas():
    fuente = (RAIZ / "cypher" / "generar_cuentas.py").read_text(encoding="utf-8-sig")
    claves = dict(re.findall(r'^(CLAVE_\w+) = "([^"]+)"', fuente, re.M))
    assert claves["CLAVE_PRUEBA"] in README and claves["CLAVE_STAFF"] in README and claves["CLAVE_ADMIN"] in README
    for correo in ("staff@redprofesional.test", "admin@redprofesional.test"):
        assert correo in fuente and correo in README
    assert "contacto@caribesoftwarelabs.example.com" in README and "camila.restrepo@example.com" in README


def test_el_readme_describe_los_roles_y_los_scripts_de_mantenimiento():
    for texto in ("Un administrador puede darle el rol `admin`", "08_renovar_fechas_demo.cypher", "generar_consultas.py", "COOKIE_SECURE", "NEO4J_DATABASE",
                  "CREATE DATABASE linkedun", "python cypher/verificar_consultas.py", "python -m pytest"):
        assert texto in README, texto


def test_el_readme_conserva_lo_de_la_portada_y_los_recursos():
    for texto in ("## Portada y animaciones", "### Regenerar la imagen fija del planeta", "## Procedencia de los recursos",
                  "Three.js 0.186.1", "Sora variable 5.2.5", "Cytoscape.js 3.30.4"):
        assert texto in README, texto
    assert (RAIZ / "app/static/vendor/cytoscape/LICENSE").exists()
