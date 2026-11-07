# Entrada cinemática y portada con planeta — Plan de construcción

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mostrar a quien llega sin sesión una entrada cinemática con el logo UN, seguida de una portada con un planeta 3D vivo que lleva al registro y al login.

**Architecture:** Página Jinja independiente (`bienvenida.html`) servida en `/` sin sesión. Una escena Three.js única contiene logo y planeta, y `bienvenida.js` dirige las fases. La lógica pura (geografía, calidad, tiempos) vive en módulos sin Three.js para probarla con Node. Login y registro cambian solo por CSS.

**Tech Stack:** FastAPI + Jinja2, Three.js 0.186.1 sin bundler (módulos ES), Sora variable, pytest + httpx (rutas), `node --test` (lógica pura), navegador integrado (visual).

**Spec:** `docs/superpowers/specs/2026-11-06-entrada-cinematica-design.md`

## Global Constraints

- `app/main.py` no se modifica: la CSP queda exactamente igual.
- Sin URLs externas en código propio; todo se sirve desde `/static`.
- Sin scripts en línea ni `importmap`. Imports siempre relativos; nunca `from 'three'`.
- Sin addons de Three.js: solo `three.module.min.js` y `three.core.min.js`.
- Colores: `#05070d`, `#0a1a33`, `#0f2c5c`, `#4da3ff`, `#f5f8ff`. El dorado solo proviene de la textura del planeta.
- Textos exactos: lema "Todo empieza con UN contacto."; subtítulo "Conecta con profesionales y empresas, descubre empleos a tu medida y encuentra quién puede abrirte la puerta."; botones "Crear mi cuenta" e "Iniciar sesión"; crédito "Imagen de la Tierra: NASA Earth Observatory".
- Sin cifras ni actividad inventadas, sin sonido.
- Sin cambios de lógica en cuentas, sesiones, formularios ni base de datos.
- Cada módulo de escena expone `{ objeto, actualizar(dt), liberar() }`.
- **Descargas:** cada una se confirma con nombre, fuente y tamaño antes de hacerla. Van a una carpeta vacía propia en el scratchpad y se procesan con `python -I` desde un script guardado aparte.
- **Commits:** solo cuando se pidan. Si se piden estando en `main`, se crea antes una rama `entrada-cinematica`. No hay pasos de commit en este plan por esa razón.

## Review Focus

1. **Cookie de sesión vencida o inválida en `/`:** debe verse la portada, no un error ni un bucle de redirección. Prueba en la Tarea 2.
2. **Textura lenta o que falla:** la portada no puede quedar en negro; pasados 8 s se usa la imagen fija. Pruebas en la Tarea 3.
3. **GPU reiniciada o portátil que despierta (pérdida de contexto WebGL):** se pasa a la imagen fija con textos y botones visibles. Prueba en la Tarea 3.
4. **Celular en horizontal (812 × 375):** lema y botones caben sin desplazamiento ni solaparse. Prueba en la Tarea 2.
5. **Volver atrás desde login:** la entrada no se repite y el planeta sigue animado. Prueba en la Tarea 5.

---

### Tarea 1: Logo "Nodo" (requiere aprobación)

**Files:**
- Create: `app/static/animaciones/package.json` (`{"private": true, "type": "module"}`, para que Node trate los `.js` como módulos)
- Create: `app/static/animaciones/intro/trazo-logo.js`
- Create: `app/static/marca/logo-un.svg`, `logo-un-1024.png`, `favicon.svg`, `favicon-32.png`
- Test: `tests/js/trazo-logo.test.mjs`

**Interfaces:**
- Produces:
  - `PUNTOS_CLAVE: [x, y][]`, `NODOS: [x, y][]`, `GROSOR: number`
  - `puntosTrazo(pasosCurva = 24): [x, y][]`
  - `contornoDeTrazo(puntos, grosor): [x, y][]`
  - `aEscena([x, y]): [number, number]`, con `x' = (x - 100) / 50`, `y' = (70 - y) / 50`
  - `CENTRO_HUECO_U = [60, 65]`

Geometría inicial en un lienzo de 200 × 140: línea continua desde `(30,25)` hasta `(30,85)`, semicírculo inferior de centro `(60,85)` y radio 30 hasta `(90,85)`, sube a `(90,25)` (trazo compartido con la N), diagonal a `(150,115)` y sube a `(150,25)`. Nodos en `(30,25)`, `(90,25)`, `(150,115)` y `(150,25)`. Grosor 9.

- [ ] **Paso 1: Escribir las pruebas**

```js
test('el trazo empieza y termina en los nodos extremos', () => {
  const p = puntosTrazo();
  assert.deepEqual(p[0], [30, 25]);
  assert.deepEqual(p.at(-1), [150, 25]);
});
test('la curva de la U llega abajo a y=115', () => {
  assert.ok(Math.abs(Math.max(...puntosTrazo().map(q => q[1])) - 115) < 0.01);
});
test('contorno de un segmento recto: 4 vértices a ±grosor/2', () => {
  const c = contornoDeTrazo([[0, 0], [10, 0]], 2);
  assert.equal(c.length, 4);
  assert.deepEqual(c.map(q => Math.abs(q[1])), [1, 1, 1, 1]);
});
test('las esquinas agudas no se disparan: límite de inglete 2×grosor', () => {
  const pts = puntosTrazo();
  contornoDeTrazo(pts, GROSOR).forEach(v =>
    assert.ok(Math.min(...pts.map(q => Math.hypot(v[0]-q[0], v[1]-q[1]))) <= GROSOR * 2));
});
test('aEscena centra el lienzo', () => assert.deepEqual(aEscena([100, 70]), [0, 0]));
```

- [ ] **Paso 2:** Ejecutar `node --test "tests/js/**/*.test.mjs"`. Esperado: falla porque el módulo no existe.
- [ ] **Paso 3:** Implementar `trazo-logo.js` sin dependencias. `contornoDeTrazo` desplaza a ambos lados con inglete limitado y devuelve un polígono cerrado.
- [ ] **Paso 4:** Ejecutar las pruebas. Esperado: pasan.
- [ ] **Paso 5:** Crear `logo-un.svg`: trazo `#f5f8ff`, nodos `#4da3ff` con halo suave, fondo transparente. `favicon.svg`: el mismo trazo sobre cuadrado redondeado `#0a1a33`.
- [ ] **Paso 6:** Exportar los PNG con Chrome sin interfaz: `chrome.exe --headless --disable-gpu --default-background-color=00000000 --window-size=1024,1024 --screenshot=<ruta> <svg>`. Comprobar con Pillow que `logo-un-1024.png` es RGBA, mide 1024 × 1024 y la esquina tiene alfa 0.
- [ ] **Paso 7: Enseñar el logo y esperar aprobación.** Mostrarlo sobre negro y en tamaño 32 px. Si cambia la geometría, actualizar `trazo-logo.js` y repetir los pasos 2 a 6. **No seguir sin aprobación.**

---

### Tarea 2: Portada estática, ruta y respaldos

**Files:**
- Create: `requirements-dev.txt` (`-r requirements.txt`, `pytest`, `httpx`)
- Create: `tests/conftest.py`, `tests/test_portada.py`
- Create: `app/templates/bienvenida.html`
- Create: `app/static/animaciones/bienvenida.css`, `app/static/animaciones/precarga.js`
- Create: `app/static/fuentes/sora-latin-wght-normal.woff2`, `LICENCIA-OFL.txt`
- Modify: `app/routers/paginas.py:1-21`

**Interfaces:**
- Produces:
  - `/` sin sesión devuelve `bienvenida.html`.
  - `precarga.js` añade a `<html>` la clase `js-intro` si procede; la clave de `sessionStorage` es `un_intro_vista`.
  - `<html>` recibe `listo` para revelar textos y `estatico` para la imagen fija.
  - IDs: `#escena` (canvas), `#saltar` (botón, `hidden` por defecto).
  - Variables CSS: `--negro`, `--noche`, `--profundo`, `--electrico`, `--blanco`.

`inicio` queda sin `Depends`: llama a `cuenta_opcional(request)`, devuelve la portada con `templates.TemplateResponse(request, "bienvenida.html", {})` si es `None`, y si no llama a `usuario_actual(visor(cuenta))` y sigue como hoy.

`tests/conftest.py` fija valores por defecto de `NEO4J_URI`, `NEO4J_USER` y `NEO4J_PASSWORD` con `os.environ.setdefault` antes de importar la app, y expone `cliente = TestClient(app, follow_redirects=False)` **sin** `with`, para no ejecutar el arranque que exige Neo4j.

- [ ] **Paso 1:** Confirmar la descarga de la fuente: `npm pack @fontsource-variable/sora@5.2.5` (34 KB el archivo usado). Copiar el `.woff2` y la licencia.
- [ ] **Paso 2:** Instalar con `.venv/Scripts/python -m pip install -r requirements-dev.txt`.
- [ ] **Paso 3: Escribir las pruebas**

```python
CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "frame-ancestors 'none'; form-action 'self'; base-uri 'self'")

def test_sin_sesion_ve_portada(cliente):
    r = cliente.get("/")
    texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", r.text))
    assert r.status_code == 200
    assert "Todo empieza con UN contacto." in texto
    assert 'href="/registro"' in r.text and 'href="/login"' in r.text
    assert "Crear mi cuenta" in texto and "Iniciar sesión" in texto
    assert "Imagen de la Tierra: NASA Earth Observatory" in texto

def test_sin_scripts_en_linea_ni_urls_externas(cliente):
    html = cliente.get("/").text
    assert not re.search(r"<script(?![^>]*\bsrc=)", html)
    assert not re.search(r"https?://(?!testserver)", html)

def test_csp_sin_cambios(cliente):
    assert cliente.get("/").headers["content-security-policy"] == CSP

def test_cookie_invalida_ve_portada(cliente, monkeypatch):      # Review Focus 1
    monkeypatch.setattr("app.dependencias.sesiones.validar", lambda _: None)
    assert cliente.get("/", cookies={"sesion": "basura"}).status_code == 200

def test_empresa_y_admin_redirigen(cliente, monkeypatch): ...   # Location /empresa/e01 y /admin
def test_persona_ve_su_inicio(cliente, monkeypatch): ...        # visor y render simulados; no devuelve la portada
def test_enlace_directo_conserva_siguiente(cliente):
    r = cliente.get("/perfil/u01")
    assert r.status_code == 303
    assert r.headers["location"] == "/login?siguiente=%2Fperfil%2Fu01"

def test_recursos_con_tipo_correcto(cliente):
    assert "javascript" in cliente.get("/static/animaciones/precarga.js").headers["content-type"]
    assert "font/woff2" in cliente.get("/static/fuentes/sora-latin-wght-normal.woff2").headers["content-type"]

def test_codigo_propio_sin_dependencias_externas():
    for f in Path("app/static/animaciones").rglob("*"):
        if f.suffix in (".js", ".css") and "vendor" not in f.parts:
            t = f.read_text(encoding="utf-8")
            assert not re.search(r"https?://", t), f
            assert not re.search(r"from\s+['\"]three['\"]", t), f
```

La prueba de tipos importa porque `nosniff` y los módulos ES exigen el tipo correcto, y Python lo lee del registro de Windows en cada equipo.

- [ ] **Paso 4:** Ejecutar `.venv/Scripts/python -m pytest tests -q`. Esperado: fallan las de portada.
- [ ] **Paso 5:** Implementar la ruta en `paginas.py`.
- [ ] **Paso 6:** Crear `bienvenida.html`. Incluye `<script src=precarga.js>` en `<head>` (clásico y bloqueante, para evitar destellos), `<script type="module" src=bienvenida.js>`, canvas `aria-hidden`, botón Saltar, logo, `h1`, subtítulo, botones y crédito. Cada palabra del lema va en un `span`, y "UN" lleva énfasis. El módulo `bienvenida.js` se añade como archivo vacío por ahora.
- [ ] **Paso 7:** Crear `precarga.js`. Añade `js-intro` solo si no hay `prefers-reduced-motion`, existe WebGL, la clave no está en `sessionStorage` (si lanza excepción, se considera no vista) y no hay `?captura=1`.
- [ ] **Paso 8:** Crear `bienvenida.css`. Fondo `--negro`, botones principal y vidrio, foco visible, revelado escalonado con `.listo` y `@view-transition { navigation: auto; }`. Seguridad: bajo `.js-intro` el contenido parte oculto y una animación con retraso de 12 s lo muestra aunque el JavaScript no cargue. `height: 100dvh`, tamaños con `clamp()`, y regla para `max-height: 480px` que compacte textos.
- [ ] **Paso 9:** Ejecutar pytest. Esperado: todo pasa.
- [ ] **Paso 10: Verificar en el navegador.**
  - Sin sesión, `/` muestra textos y botones sin errores en consola.
  - A 375 × 812 y a 812 × 375 (Review Focus 4), `document.documentElement.scrollHeight <= innerHeight` y lema y botones no se solapan.
  - Con `js-intro` y `bienvenida.js` renombrado temporalmente, el contenido aparece a los 12 s. Restaurar el nombre.

---

### Tarea 3: Planeta, estrellas y orquestador

**Files:**
- Create: `app/static/animaciones/vendor/three/` (`three.module.min.js`, `three.core.min.js`, `LICENSE`)
- Create: `app/static/animaciones/texturas/tierra-noche-4096.webp`, `tierra-noche-2048.webp`, `planeta-fijo.webp`
- Create: `app/static/animaciones/planeta/geo.js`, `planeta.js`, `estrellas.js`
- Create: `app/static/animaciones/calidad.js`, `rendimiento.js`
- Modify: `app/static/animaciones/bienvenida.js`, `bienvenida.css`
- Test: `tests/js/geo.test.mjs`, `tests/js/calidad.test.mjs`

**Interfaces:**
- Produces:
  - `geo.js`: `latLonAVec3(lat, lon, r) → {x, y, z}` (lon 0 en +x, coincide con el mapeo de `SphereGeometry`); `rotacionYParaLon(lon) → radianes`; `puntoArco(a, b, t, r, altura) → {x, y, z}` (interpolación esférica; radio `r + altura·sin(πt)`)
  - `calidad.js`: `elegirCalidad({ancho, tactil, reducido, webgl}) → {modo, textura, arcos, pixelRatioMax, segmentos, parallax}`
  - `rendimiento.js`: `crearMonitorFps({umbral = 40, segundos = 3, alBajar}) → registrar(dt)`; `conTiempoLimite(promesa, ms) → Promise`
  - `planeta.js`: `crearPlaneta({textura, segmentos}) → {objeto, nucleo, radio, actualizar, liberar}`; hijos del planeta deben añadirse a `nucleo`, que es el que gira
  - `estrellas.js`: `crearEstrellas({cantidad}) → {objeto, actualizar, liberar}`
  - `bienvenida.js`: `modoRespaldo()` añade la clase `estatico`, detiene el bucle y muestra los textos

- [ ] **Paso 1:** Confirmar descarga de `three@0.186.1` (`npm pack`, sin ejecutar scripts). Comprobar que `three.module.min.js` importa `./three.core.min.js` de forma relativa.
- [ ] **Paso 2:** Confirmar descarga de `BlackMarble_2016_3km.jpg` (8,1 MB) desde `https://assets.science.nasa.gov/content/dam/science/esd/eo/images/imagerecords/144000/144898/`. Generar con Pillow los WebP de 4096 × 2048 y 2048 × 1024, calidad 82. No guardar el JPEG en el repositorio.
- [ ] **Paso 3: Escribir las pruebas**

```js
test('lon 0 está en +x y lon 90 en -z', () => {
  casi(latLonAVec3(0, 0, 1), {x: 1, y: 0, z: 0});
  casi(latLonAVec3(0, 90, 1), {x: 0, y: 0, z: -1});
});
test('rotacionYParaLon deja Barranquilla de frente', () => {
  const p = latLonAVec3(0, -74.8, 1), g = rotacionYParaLon(-74.8);
  assert.ok(Math.abs(p.x * Math.cos(g) + p.z * Math.sin(g)) < 1e-9);
  assert.ok(-p.x * Math.sin(g) + p.z * Math.cos(g) > 0.999);
});
test('el arco parte y llega a la superficie y se eleva en medio', () => { ... });
test('puntoArco con a == b no produce NaN', () => { ... });
test('reducido o sin WebGL → modo estatico', () => {
  assert.equal(elegirCalidad({ancho: 1920, tactil: false, reducido: true, webgl: true}).modo, 'estatico');
  assert.equal(elegirCalidad({ancho: 1920, tactil: false, reducido: false, webgl: false}).modo, 'estatico');
});
test('escritorio', () => assert.deepEqual(
  pick(elegirCalidad({ancho: 1920, tactil: false, reducido: false, webgl: true})),
  {modo: 'completo', textura: 4096, arcos: 36, pixelRatioMax: 2, parallax: true}));
test('celular', () => assert.deepEqual(
  pick(elegirCalidad({ancho: 375, tactil: true, reducido: false, webgl: true})),
  {modo: 'ligero', textura: 2048, arcos: 12, pixelRatioMax: 1.5, parallax: false}));
test('el monitor avisa tras 3 s bajo 40 fps, una sola vez por tanda', () => { ... });
test('el monitor no avisa con 60 fps', () => { ... });
test('conTiempoLimite rechaza si la promesa tarda demasiado', async () => { ... }); // Review Focus 2
```

- [ ] **Paso 4:** Ejecutar `node --test "tests/js/**/*.test.mjs"`. Esperado: fallan las nuevas.
- [ ] **Paso 5:** Implementar `geo.js`, `calidad.js` y `rendimiento.js`. Sin Three.js. Ejecutar las pruebas. Esperado: pasan.
- [ ] **Paso 6:** Implementar `planeta.js`: esfera con la textura (`SRGBColorSpace`), azul muy oscuro donde no hay luces, y una esfera exterior `BackSide` aditiva con Fresnel para el halo, más intenso arriba. Rotación inicial `rotacionYParaLon(-74.8)`, velocidad 0,01 rad/s. Valores iniciales de encuadre: radio 5, centro `(0, -5.2, -8)`.
- [ ] **Paso 7:** Implementar `estrellas.js`: dos capas de `Points`, puntos redondos por shader, sin textura externa.
- [ ] **Paso 8:** Implementar `bienvenida.js`: elegir calidad, crear renderizador, cargar textura con `conTiempoLimite(..., 8000)`, activar el bucle y añadir `listo`.
  - Cualquier excepción o fallo de textura llama a `modoRespaldo()` y registra con `console.error`.
  - `webglcontextlost` llama a `modoRespaldo()`.
  - Se pausa con `visibilitychange`, se ajusta con `resize` y solo mueve con el mouse si `calidad.parallax`.
  - `monitor.alBajar` reduce el `pixelRatio` y luego los arcos.
- [ ] **Paso 9:** Añadir `?captura=1`: oculta textos y arcos, sin entrada. Generar `planeta-fijo.webp` a 1920 × 1080 con Chrome sin interfaz (`--enable-unsafe-swiftshader --virtual-time-budget=6000`) y convertir con Pillow, calidad 80. Usarla en `bienvenida.css` para `.estatico` y como fondo inicial.
- [ ] **Paso 10: Verificar en el navegador.**
  - El planeta se parece a la referencia, con el Caribe de frente, y no hay errores de CSP.
  - Con la textura renombrada temporalmente (Review Focus 2), se ve la imagen fija y los botones. Restaurar.
  - Con `document.querySelector('canvas').getContext('webgl2').getExtension('WEBGL_lose_context').loseContext()` (Review Focus 3), se pasa a la imagen fija con los botones visibles.
  - Con movimiento reducido, se ve la imagen fija, sin canvas animado.

---

### Tarea 4: Arcos de conexión

**Files:**
- Create: `app/static/animaciones/planeta/ciudades.js`, `arcos.js`
- Modify: `app/static/animaciones/bienvenida.js`
- Test: `tests/js/ciudades.test.mjs`

**Interfaces:**
- Consumes: `puntoArco`, `latLonAVec3` de `geo.js`; `planeta.nucleo`, `planeta.radio`
- Produces:
  - `ciudades.js`: `CIUDADES: {nombre, lat, lon}[]` (al menos 30, primero Barranquilla); `paresIniciales(n) → [origen, destino][]`
  - `arcos.js`: `crearArcos({radio, cantidad}) → {objeto, actualizar(dt), fijarCantidad(n), liberar()}`

- [ ] **Paso 1: Escribir las pruebas**

```js
test('hay al menos 30 ciudades y Barranquilla es la primera', () => {
  assert.ok(CIUDADES.length >= 30);
  assert.equal(CIUDADES[0].nombre, 'Barranquilla');
});
test('coordenadas válidas y nombres únicos', () => { ... });
test('los primeros arcos salen de Barranquilla', () => {
  paresIniciales(6).slice(0, 3).forEach(([o]) => assert.equal(o.nombre, 'Barranquilla'));
});
test('ningún par une una ciudad consigo misma', () => {
  paresIniciales(36).forEach(([o, d]) => assert.notEqual(o.nombre, d.nombre));
});
```

- [ ] **Paso 2:** Ejecutar las pruebas. Esperado: fallan.
- [ ] **Paso 3:** Implementar `ciudades.js`. Ejecutar las pruebas. Esperado: pasan.
- [ ] **Paso 4:** Implementar `arcos.js`. `TubeGeometry` sobre `CatmullRomCurve3` con 48 puntos de `puntoArco`, radio de tubo 0,006 y `altura` proporcional a la distancia angular. `ShaderMaterial` aditivo con `depthTest` activo, para que el planeta tape lo que queda detrás; usa `uv.x` y un uniforme `uCabeza` para dibujar una línea tenue con un pulso brillante `#f5f8ff` sobre `#4da3ff`. Al llegar, una onda: anillo que crece y se desvanece en 0,8 s. Ciclo de 2,5 a 4 s, inicio escalonado, reutilizando geometrías, sin crear objetos por cuadro.
- [ ] **Paso 5:** Integrarlo en `bienvenida.js` como hijo de `planeta.nucleo`, con `calidad.arcos`. Conectar `monitor.alBajar` con `fijarCantidad`. Omitir con `?captura=1`.
- [ ] **Paso 6: Verificar en el navegador.** Los primeros arcos salen del Caribe, los pulsos viajan, los de atrás quedan ocultos y hay ondas al llegar. `renderer.info.memory.geometries` se mantiene estable tras 60 s (exponerlo temporalmente para medirlo y quitarlo después). No hay errores en consola.

---

### Tarea 5: Entrada cinemática

**Files:**
- Create: `app/static/animaciones/intro/logo3d.js`, `secuencia.js`, `fases.js`
- Modify: `app/static/animaciones/bienvenida.js`, `bienvenida.css`
- Test: `tests/js/fases.test.mjs`

**Interfaces:**
- Consumes: `puntosTrazo`, `contornoDeTrazo`, `NODOS`, `aEscena`, `CENTRO_HUECO_U` de `trazo-logo.js`; escena y cámara de `bienvenida.js`
- Produces:
  - `fases.js`: `TIEMPOS = {trazo: 0.8, volumen: 2.4, travesia: 4.2, fin: 6.0}`; `faseEn(t) → {nombre, progreso}`, con nombres `inicio`, `trazo`, `volumen`, `travesia`, `fin`
  - `logo3d.js`: `crearLogo3d() → {objeto, fijarTrazo(p), fijarVolumen(p), fijarDestello(p), actualizar, liberar}`
  - `secuencia.js`: `crearSecuencia({escena, camara, logo, posicionFinal, alTerminar}) → {actualizar(dt), saltar(), liberar()}`

- [ ] **Paso 1: Escribir las pruebas**

```js
test('fases en sus límites', () => {
  assert.equal(faseEn(0).nombre, 'inicio');
  assert.equal(faseEn(0.8).nombre, 'trazo');
  assert.equal(faseEn(2.4).nombre, 'volumen');
  assert.equal(faseEn(4.2).nombre, 'travesia');
  assert.equal(faseEn(6).nombre, 'fin');
});
test('el progreso va de 0 a 1 dentro de cada fase', () => {
  assert.equal(faseEn(0.8).progreso, 0);
  assert.ok(Math.abs(faseEn(1.6).progreso - 0.5) < 1e-9);
});
test('más allá del final se mantiene en fin con progreso 1', () =>
  assert.deepEqual(faseEn(99), {nombre: 'fin', progreso: 1}));
```

- [ ] **Paso 2:** Ejecutar las pruebas. Esperado: fallan.
- [ ] **Paso 3:** Implementar `fases.js`. Ejecutar las pruebas. Esperado: pasan.
- [ ] **Paso 4:** Implementar `logo3d.js`.
  - Línea fina con `setDrawRange` para `fijarTrazo`.
  - Sprites aditivos en cada nodo, generados con un `CanvasTexture`.
  - Malla con `THREE.Shape` desde `contornoDeTrazo`, `ExtrudeGeometry` con bisel y `MeshPhysicalMaterial` azul profundo muy metálico.
  - Reflejos de un entorno procedural con `PMREMGenerator.fromScene`.
  - `fijarVolumen` escala z de 0 a 1; `fijarDestello` mueve una luz y una franja aditiva.
- [ ] **Paso 5:** Implementar `secuencia.js`. Según `faseEn`, llama a los métodos del logo. En `travesia`, la cámara avanza con suavizado cruzando `aEscena(CENTRO_HUECO_U)` hacia `posicionFinal`, y el logo se desvanece detrás. `saltar()` coloca todo en el estado final y llama a `alTerminar` una sola vez.
- [ ] **Paso 6:** Integrarla en `bienvenida.js`: si `<html>` tiene `js-intro`, guardar `un_intro_vista` en `sessionStorage` (dentro de `try`), mostrar `#saltar`, atender Esc y clic, e iniciar. `alTerminar` oculta `#saltar`, libera el logo y añade `listo`. Si la textura no ha cargado al entrar en `travesia`, el planeta aparece con fundido cuando llega; si falla, `modoRespaldo()`.
- [ ] **Paso 7: Verificar en el navegador.** Desde sesión nueva y limpia:
  - Las cuatro fases se ven en orden y sin cortes.
  - Saltar y Esc funcionan y devuelven el foco a la portada.
  - Al recargar no se repite.
  - Ir a `/login` y volver atrás (Review Focus 5): no se repite y el planeta sigue animado.
  - Cambiar el tamaño de la ventana durante la entrada no la rompe.
  - No hay errores en consola.

---

### Tarea 6: Login, registro y logo en la barra

**Files:**
- Create: `app/static/css/acceso.css`
- Modify: `app/templates/base.html:7-14`
- Modify: `app/templates/login.html`, `registro.html`, `registro_persona.html`, `registro_empresa.html`
- Modify: `app/static/css/estilos.css:33` (`.logo-marca`)
- Test: `tests/test_portada.py`

**Interfaces:**
- Consumes: `planeta-fijo.webp`, fuente Sora, `marca/`
- Produces: en `base.html`, los bloques `clase_cuerpo` y `estilos`

El logo tiene trazo claro y la barra interna es blanca, por lo que en la barra va sobre un cuadrado `#0a1a33` (`.logo-marca`). Ese cuadrado sustituye el fondo azul actual.

- [ ] **Paso 1: Escribir las pruebas**

```python
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
```

- [ ] **Paso 2:** Ejecutar pytest. Esperado: fallan.
- [ ] **Paso 3:** Modificar `base.html` con `<body class="{% block clase_cuerpo %}{% endblock %}">`, `{% block estilos %}{% endblock %}`, los enlaces de favicon y el logo como `<img alt="">` dentro de `.logo-marca`. Conservar `aria-label`.
- [ ] **Paso 4:** Activar los bloques en las cuatro plantillas. Solo esas líneas.
- [ ] **Paso 5:** Crear `acceso.css`, todo bajo `body.acceso`: fondo `planeta-fijo.webp` fijo, con capa oscura; barra oscura; `.tarjeta` vidrio; `.campo input`, `.campo select`, `label`, `.alerta`, `.pie-formulario`, `.sub`, `.opcion`, `.icono-caja`, `.btn-solido`, `.btn-borde`; foco visible; `@view-transition`.
- [ ] **Paso 6:** Ejecutar pytest. Esperado: pasan todas.
- [ ] **Paso 7: Verificar en el navegador.**
  - Las cuatro páginas, a 1280 px y 375 px.
  - Con clave incorrecta, el error se ve y se lee bien. Registro con errores de validación.
  - Contraste calculado en consola ≥ 4,5:1 en texto, etiquetas, enlaces y errores.
  - El inicio con sesión mantiene su aspecto claro, con el logo nuevo.

---

### Tarea 7: Verificación final y documentación

**Files:**
- Modify: `README.md`

- [ ] **Paso 1:** Añadir al README: cómo correr la app y las pruebas, procedencia y licencias (NASA, Three.js MIT, Sora OFL), y cómo regenerar `planeta-fijo.webp` con `?captura=1`.
- [ ] **Paso 2:** Ejecutar `.venv/Scripts/python -m pytest tests -q` y `node --test "tests/js/**/*.test.mjs"`. Esperado: todo pasa.
- [ ] **Paso 3:** Ejecutar `git diff --stat -- app/main.py app/services app/repositories app/routers/auth.py`. Esperado: sin cambios.
- [ ] **Paso 4:** Recorrer los 10 puntos de la sección 8 de la spec en el navegador, con cuentas de prueba. Registrar lo que no se pudo comprobar. Si se crearon cuentas al probar el registro, indicarlo.
- [ ] **Paso 5:** Medir los fps de la portada a 1280 × 720, e informar la cifra como medición parcial. Dejar anotado que hay que probar en Chrome real.
- [ ] **Paso 6:** Medir el peso total de la portada en la primera carga, a partir de las peticiones de red, e informarlo.
