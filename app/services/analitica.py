"""Arma lo que muestra el panel de analitica a partir de las filas de la base.
Son funciones puras (sin acceso a Neo4j), faciles de probar."""
from collections import Counter, defaultdict


def numerar_comunidades(usuarios: list[dict]) -> dict:
    """{id de Louvain: 1..k}, de la comunidad mas grande a la mas pequena.
    Los ids que entrega Louvain son arbitrarios; asi las personas ven 'Comunidad 1, 2, 3'."""
    tamanos = Counter(f["usuario"]["comunidad"] for f in usuarios if f["usuario"].get("comunidad") is not None)
    orden = sorted(tamanos, key=lambda c: (-tamanos[c], c))
    return {c: i + 1 for i, c in enumerate(orden)}


def _posiciones(valores: dict) -> dict:
    """Posicion 1, 2, 3... por valor descendente (los empates comparten posicion)."""
    pos, anterior, rango = {}, None, 0
    for i, (clave, v) in enumerate(sorted(valores.items(), key=lambda kv: -kv[1]), start=1):
        if v != anterior:
            rango, anterior = i, v
        pos[clave] = rango
    return pos


def influyentes(usuarios: list[dict], numeracion: dict, limite: int = 10) -> list[dict]:
    """Top por PageRank, con la posicion que tendria solo por numero de conexiones."""
    con_pr = [f for f in usuarios if f["usuario"].get("pagerank") is not None]
    por_conexiones = _posiciones({f["usuario"]["id"]: f["conexiones"] for f in con_pr})
    salida = []
    for i, f in enumerate(sorted(con_pr, key=lambda f: -f["usuario"]["pagerank"])[:limite], start=1):
        u = f["usuario"]
        salida.append({"puesto": i, "usuario": u, "pagerank": u["pagerank"], "conexiones": f["conexiones"],
                       "puesto_conexiones": por_conexiones[u["id"]], "empresa": f.get("empresa"),
                       "comunidad": numeracion.get(u.get("comunidad"))})
    return salida


def puentes(usuarios: list[dict], numeracion: dict, limite: int = 5) -> list[dict]:
    con_ib = [f for f in usuarios if f["usuario"].get("intermediacion") is not None and f["usuario"]["intermediacion"] > 0]
    ordenados = sorted(con_ib, key=lambda f: -f["usuario"]["intermediacion"])[:limite]
    return [{"usuario": f["usuario"], "intermediacion": f["usuario"]["intermediacion"], "conexiones": f["conexiones"],
             "comunidad": numeracion.get(f["usuario"].get("comunidad"))} for f in ordenados]


def comunidades(usuarios: list[dict], numeracion: dict, habilidades: list[dict], sectores: list[dict]) -> list[dict]:
    """Cada comunidad con su tamano, una etiqueta calculada del propio grafo (sector que mas se repite
    y habilidades mas comunes) y sus miembros mas influyentes."""
    miembros = defaultdict(list)
    for f in usuarios:
        c = f["usuario"].get("comunidad")
        if c is not None:
            miembros[c].append(f)
    hab, sec = defaultdict(Counter), defaultdict(Counter)
    for r in habilidades:
        hab[r["comunidad"]][r["habilidad"]] += r["personas"]
    for r in sectores:
        if r["sector"]:
            sec[r["comunidad"]][r["sector"]] += r["personas"]
    salida = []
    for c, lista in miembros.items():
        top_h = [n for n, _ in sorted(hab[c].items(), key=lambda kv: (-kv[1], kv[0]))[:3]]
        top_s = sorted(sec[c].items(), key=lambda kv: (-kv[1], kv[0]))
        sector = top_s[0][0] if top_s else None
        etiqueta = " · ".join(x for x in [sector, ", ".join(top_h)] if x) or "Sin datos suficientes"
        lideres = sorted(lista, key=lambda f: -(f["usuario"].get("pagerank") or 0))[:4]
        salida.append({"numero": numeracion[c], "miembros": len(lista), "etiqueta": etiqueta, "sector": sector,
                       "habilidades": top_h, "lideres": [f["usuario"] for f in lideres]})
    return sorted(salida, key=lambda d: d["numero"])


def hay_metricas(usuarios: list[dict]) -> bool:
    return any(f["usuario"].get("pagerank") is not None for f in usuarios)
