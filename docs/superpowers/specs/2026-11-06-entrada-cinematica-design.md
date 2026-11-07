# Entrada cinemática y portada con planeta — Diseño

**Fecha:** 2026-11-06
**Estado:** pendiente de revisión

## 1. Objetivo

Dar una primera impresión memorable a quien llega a la página sin haber iniciado sesión: una entrada cinemática con el logo "UN", seguida de una portada con un planeta vivo, un lema y dos botones que llevan al registro y al login existentes.

**Se considera logrado cuando:**
- Una persona sin sesión que abre `/` ve la entrada, llega a la portada y puede registrarse o iniciar sesión.
- Quien ya tiene sesión no ve nada de esto y su experiencia no cambia.
- La política de seguridad (CSP) sigue exactamente igual y la consola no muestra errores.
- Login y registro funcionan igual que antes, con el nuevo aspecto.
- Todas las animaciones están en una carpeta propia.

## 2. Decisiones aprobadas

| Tema | Decisión |
|---|---|
| Tecnología | Three.js con 3D real, sin dependencias externas en tiempo de ejecución |
| Logo | Concepto A, "Nodo": U y N unidas por una sola línea con puntos luminosos |
| Lema | "Todo empieza con UN contacto." |
| Login y registro | Mismos campos y lógica; tarjeta oscura tipo vidrio sobre el planeta |
| Luces de las ciudades | Doradas, solo en el planeta; todo lo demás en azul y blanco |
| Nombre | "UN" como símbolo; "LinkedUn" como nombre en los textos |

## 3. Fuera de alcance

- Cambios en la lógica de cuentas, sesiones, formularios o base de datos.
- Rediseño de las páginas internas: solo cambia el logo de la barra superior y el icono de pestaña.
- Sonido.
- Secciones adicionales en la portada: es una sola pantalla, sin desplazamiento.
- Cifras o actividad inventadas. Las líneas son una representación visual y no se presentan como tráfico real.
- Cambio del nombre LinkedUn.

## 4. Experiencia

### 4.1 Entrada cinemática (unos 6 segundos, una sola toma)

| Tiempo | Qué ocurre |
|---|---|
| 0,0–0,8 s | Negro, estrellas muy tenues y un punto de luz |
| 0,8–2,4 s | El punto se conecta con otros; las líneas dibujan la "UN" |
| 2,4–4,2 s | Las letras toman volumen 3D, con borde azul y un destello que las recorre |
| 4,2–6,0 s | La cámara atraviesa la "U" y sale al espacio; aparece el planeta |
| 6,0–7,0 s | Aparecen el lema, el subtítulo y los botones |

- El botón "Saltar" y la tecla Esc llevan directo a la portada.
- Se muestra una vez por sesión del navegador (`sessionStorage`). Si el almacenamiento falla, la entrada simplemente se muestra.

### 4.2 Portada

- **Planeta:** Tierra nocturna grande en la parte baja, como en la imagen de referencia, con rotación muy lenta y un halo azul en el borde.
- **Vista inicial:** centrada en el Caribe colombiano.
- **Arcos:** curvas de luz entre ciudades, con pulsos que viajan y una pequeña onda al llegar. Las primeras salen de Barranquilla. Unas 36 en escritorio y 12 en celular, que aparecen y desaparecen de forma escalonada.
- **Fondo:** estrellas con dos capas de profundidad.
- **Mouse:** estrellas y planeta se desplazan ligeramente con él; no se aplica en pantallas táctiles.

**Textos:**
- **Lema:** "Todo empieza con UN contacto."
- **Subtítulo:** "Conecta con profesionales y empresas, descubre empleos a tu medida y encuentra quién puede abrirte la puerta."
- **Botón principal:** "Crear mi cuenta" (blanco sólido), lleva a `/registro`.
- **Botón secundario:** "Iniciar sesión" (vidrio con borde), lleva a `/login`.
- **Crédito discreto:** "Imagen de la Tierra: NASA Earth Observatory".

### 4.3 Paso a login y registro

Son enlaces normales. Un fundido entre páginas con la regla CSS `@view-transition` suaviza el cambio en los navegadores compatibles; en los demás, la navegación es la habitual.

### 4.4 Login y registro

Aplica a `login.html`, `registro.html`, `registro_persona.html` y `registro_empresa.html`.

- Fondo: imagen fija del planeta (sin WebGL), con la barra superior oscura.
- Tarjeta oscura tipo vidrio con los campos, enlaces, errores y tokens actuales.
- El contraste de textos, campos y mensajes de error debe cumplir WCAG AA.

### 4.5 Identidad visual

| Elemento | Valor |
|---|---|
| Negro espacial | `#05070d` |
| Azul noche | `#0a1a33` |
| Azul profundo | `#0f2c5c` |
| Azul eléctrico (solo luces y detalles) | `#4da3ff` |
| Blanco | `#f5f8ff` |
| Dorado (solo ciudades del planeta) | según la textura |
| Tipografía | Sora variable, guardada en el proyecto (licencia OFL) |

### 4.6 Logo

Se entrega y se muestra para aprobación **antes** de animarlo:

- `logo-un.svg` (original vectorial)
- `logo-un-1024.png` (fondo transparente)
- `favicon.svg` y `favicon-32.png`

Sustituye al cuadrito "Un" azul de la barra superior. Los datos de la línea del logo viven en un solo módulo que usa la animación, para que el logo animado y el SVG coincidan.

## 5. Arquitectura

### 5.1 Archivos

```
app/static/animaciones/
├── bienvenida.js          orquesta: decide qué mostrar y da paso de la entrada a la portada
├── bienvenida.css         maquetación y animaciones de la portada
├── intro/
│   ├── trazo-logo.js      datos de la línea del logo
│   ├── logo3d.js          malla y materiales del logo
│   └── secuencia.js       línea de tiempo y cámara de la entrada
├── planeta/
│   ├── planeta.js         esfera, textura y halo
│   ├── arcos.js           arcos, pulsos y ondas
│   ├── ciudades.js        lista de ciudades (latitud y longitud)
│   └── estrellas.js       fondo de estrellas
├── texturas/
│   ├── tierra-noche-4096.webp
│   ├── tierra-noche-2048.webp
│   └── planeta-fijo.webp  imagen fija: respaldo y fondo de login
└── vendor/
    └── three/             Three.js 0.186.1 y su licencia

app/static/marca/          logo e icono
app/static/fuentes/        Sora variable y su licencia
app/static/css/acceso.css  aspecto oscuro de login y registro
app/templates/bienvenida.html
```

### 5.2 Cambios en archivos existentes

| Archivo | Cambio |
|---|---|
| `app/routers/paginas.py` | `/` sin sesión devuelve `bienvenida.html`; con sesión, el comportamiento actual |
| `app/templates/base.html` | Bloque para clase del `<body>`, bloque para estilos adicionales, icono de pestaña y logo nuevo |
| `app/templates/login.html`, `registro*.html` | Activan el aspecto oscuro con esos bloques |
| `app/static/css/estilos.css` | Solo lo necesario para el logo nuevo |
| `README.md` | Crédito y procedencia de los recursos externos |

`app/main.py` y su CSP **no se modifican**.

### 5.3 Rutas

- `/` sin sesión: muestra la portada, en lugar de redirigir a `/login?siguiente=%2F`.
- `/` con sesión de persona: inicio actual.
- `/` con sesión de empresa, staff o admin: sus redirecciones actuales.
- El resto de rutas protegidas siguen redirigiendo a `/login?siguiente=...`, así que los enlaces directos no cambian.
- Cerrar sesión sigue llevando a `/login`.

`bienvenida.html` es una plantilla independiente y no hereda de `base.html`, porque no lleva barra de navegación.

### 5.4 Restricciones de la CSP

La CSP actual permite scripts, fuentes y datos solo del propio sitio, e imágenes del sitio o `data:`. Consecuencias:

- **Sin CDN ni Google Fonts:** todo se sirve desde `/static`.
- **Sin scripts en línea:** tampoco `<script type="importmap">`. Los módulos se importan con rutas relativas, como `../vendor/three/three.module.min.js`.
- **Sin los addons de Three.js:** importan el nombre `three`, que requeriría un import map. Por eso no se usa su posprocesado:
  - Brillo con sprites aditivos y shaders propios.
  - Reflejos del logo con un entorno procedural (`PMREMGenerator.fromScene`).
  - Geometría del logo con `THREE.Shape` y `ExtrudeGeometry`, que son parte del núcleo.

### 5.5 Unidades

| Unidad | Responsabilidad | Depende de |
|---|---|---|
| `bienvenida.js` | Comprueba WebGL y preferencias, elige calidad, crea el renderizador, dirige las fases y atiende "Saltar" | Las demás |
| `intro/secuencia.js` | Línea de tiempo de la entrada; expone `iniciar()` y `saltar()` | `logo3d.js`, cámara |
| `intro/logo3d.js` | Construye el logo 3D | `trazo-logo.js`, Three.js |
| `planeta/planeta.js` | Tierra y halo; expone `actualizar(dt)` | Three.js, textura |
| `planeta/arcos.js` | Crea y anima los arcos | `ciudades.js`, Three.js |
| `planeta/estrellas.js` | Fondo de estrellas | Three.js |

Cada unidad de escena recibe lo que necesita y expone `actualizar(dt)` y `liberar()`, así que se puede ajustar sin tocar las demás.

## 6. Respaldos y accesibilidad

El HTML de la portada contiene el lema y los botones desde el principio. Las animaciones son una mejora, nunca un requisito para registrarse o iniciar sesión.

| Situación | Comportamiento |
|---|---|
| Sin JavaScript o sin WebGL | Imagen fija del planeta, con textos y botones visibles |
| Error al crear la escena o cargar la textura | Igual que el caso anterior, con el error registrado en consola |
| `prefers-reduced-motion` | Sin entrada ni movimiento: imagen fija, textos y botones |
| Celular | Textura de 2048, 12 arcos, menor resolución, sin efecto de mouse |
| Rendimiento bajo sostenido | Se reduce la resolución y el número de arcos |
| Pestaña oculta | La animación se pausa |
| Teclado y lector de pantalla | "Saltar" y los botones son enfocables; el canvas es decorativo (`aria-hidden`) |

**Objetivo de rendimiento:** 60 fps en un portátil normal, con resolución limitada a 2× en escritorio y 1,5× en celular.

## 7. Recursos externos

Cada descarga requiere confirmación con nombre, fuente y tamaño justo antes de hacerla.

| Recurso | Fuente | Tamaño | Licencia |
|---|---|---|---|
| `BlackMarble_2016_3km.jpg` | NASA Earth Observatory (`assets.science.nasa.gov`) | 8,1 MB (confirmado) | Imágenes de NASA, con crédito |
| `three.module.min.js` y `three.core.min.js`, versión 0.186.1 | npm | Por confirmar al descargar | MIT |
| Sora variable, `sora-latin-wght-normal.woff2`, versión 5.2.5 | npm `@fontsource-variable/sora` | 34 KB (confirmado) | OFL 1.1 |

- La textura se reduce a 4096 × 2048 y 2048 × 1024 en WebP. El JPEG original no se guarda en el repositorio.
- `planeta-fijo.webp` se obtiene con una captura de la propia escena, sin arcos, una vez terminado el planeta. Hasta entonces, la portada usa un fondo negro con los mismos textos y botones.
- Se usa Three.js 0.186.1 porque 0.187.0 tenía solo una semana publicada.
- La imagen enviada como referencia (450 px, una sola cara) guía el estilo, pero no se usa como textura.

## 8. Verificación

El proyecto no tiene pruebas automatizadas de interfaz; la verificación se hace en el navegador con la app corriendo:

1. **Portada:** sin sesión, `/` muestra la entrada y después la portada, sin errores de CSP en consola.
2. **Repetición:** al recargar en la misma sesión no se repite la entrada.
3. **Saltar:** el botón y Esc funcionan.
4. **Botones:** llevan a `/registro` y `/login`.
5. **Login:** correcto, con clave incorrecta (el error se ve y se lee bien) y con enlace directo (`/perfil/u01` sin sesión vuelve ahí tras entrar).
6. **Registro:** persona y empresa, incluyendo errores de validación, con cuentas de prueba.
7. **Sesión iniciada:** persona, empresa y admin no ven la portada.
8. **Respaldos:** movimiento reducido, celular (375 px) y WebGL desactivado.
9. **Rendimiento:** medir fps de la portada en el navegador integrado y anotar el resultado.
10. **CSP:** `git diff` confirma que `app/main.py` no cambió.

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| Rendimiento en equipos modestos o gráficos integrados | Niveles de calidad, reducción automática e imagen fija como último recurso |
| El navegador integrado puede no reflejar los fps de un equipo real | Se informa como medición parcial; conviene probar también en Chrome |
| El brillo sin posprocesado puede lucir menos intenso | Sprites y shaders ajustados por capas; revisión visual antes de cerrar |
| Peso de la página | Textura adaptada al dispositivo y caché estándar de archivos estáticos |
| Parecido del nombre con LinkedIn si se publica | Decisión aplazada, fuera de este alcance |

## 10. Orden de construcción

1. Logo: se muestra para aprobación.
2. Portada estática con textos, botones, ruta y respaldos.
3. Planeta y estrellas.
4. Arcos de conexión.
5. Entrada cinemática y paso continuo al planeta.
6. Aspecto oscuro de login y registro.
7. Verificación completa.
