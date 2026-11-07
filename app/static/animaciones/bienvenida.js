// Orquestador de la portada: decide qué se muestra, crea la escena y dirige las fases.
import * as THREE from './vendor/three/three.module.min.js';
import { elegirCalidad } from './calidad.js';
import { crearMonitorFps, conTiempoLimite } from './rendimiento.js';
import { crearPlaneta } from './planeta/planeta.js';
import { crearEstrellas } from './planeta/estrellas.js';
import { crearArcos } from './planeta/arcos.js';
import { crearLogo3d } from './intro/logo3d.js';
import { crearSecuencia } from './intro/secuencia.js';

const raiz = document.documentElement;
const parametros = new URLSearchParams(location.search);
const captura = parametros.has('captura');
const canvas = document.getElementById('escena');
const botonSaltar = document.getElementById('saltar');

const POSICION_PLANETA = new THREE.Vector3(0, -6.05, -8);
const POSICION_FINAL_CAMARA = new THREE.Vector3(0, 0, 0);
const LIMITE_TEXTURA_MS = 8000;

let renderizador = null;

function modoRespaldo(motivo) {
  if (motivo) console.error('Portada en modo de respaldo:', motivo);
  raiz.classList.add('estatico', 'listo');
  botonSaltar.hidden = true;
  renderizador?.setAnimationLoop(null);
}

function hayWebgl() {
  try {
    return !!document.createElement('canvas').getContext('webgl2');
  } catch {
    return false;
  }
}

function urlDeTextura(ancho) {
  return new URL(`./texturas/tierra-noche-${ancho}.webp`, import.meta.url).href;
}

function iniciar() {
  // precarga.js ya pasó a la imagen fija porque este módulo llegó tarde.
  if (raiz.classList.contains('estatico')) return;

  const calidad = elegirCalidad({
    ancho: innerWidth,
    tactil: matchMedia('(pointer: coarse)').matches,
    reducido: !captura && matchMedia('(prefers-reduced-motion: reduce)').matches,
    webgl: hayWebgl(),
  });

  if (calidad.modo === 'estatico') {
    modoRespaldo();
    return;
  }

  renderizador = new THREE.WebGLRenderer({
    canvas,
    antialias: calidad.modo === 'completo',
    powerPreference: 'high-performance',
    preserveDrawingBuffer: captura,
  });
  renderizador.setClearColor(0x05070d, 1);
  renderizador.toneMapping = THREE.ACESFilmicToneMapping;
  renderizador.toneMappingExposure = 1.05;

  let pixelRatio = Math.min(devicePixelRatio || 1, calidad.pixelRatioMax);
  renderizador.setPixelRatio(pixelRatio);
  renderizador.setSize(innerWidth, innerHeight, false);

  const escena = new THREE.Scene();
  const camara = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.1, 300);

  const estrellas = crearEstrellas({ cantidad: calidad.modo === 'completo' ? 2600 : 1200 });
  escena.add(estrellas.objeto);

  const planeta = crearPlaneta({ segmentos: calidad.segmentos });
  planeta.objeto.position.copy(POSICION_PLANETA);
  escena.add(planeta.objeto);

  let cantidadArcos = calidad.arcos;
  const arcos = captura ? null : crearArcos({ radio: planeta.radio, cantidad: cantidadArcos });
  if (arcos) planeta.nucleo.add(arcos.objeto);

  const cargaTextura = new THREE.TextureLoader().loadAsync(urlDeTextura(calidad.textura)).then((t) => {
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = Math.min(8, renderizador.capabilities.getMaxAnisotropy());
    planeta.fijarTextura(t);
  });

  // --- Movimiento de cámara con el mouse ---
  const objetivo = { x: 0, y: 0 };
  if (calidad.parallax && !captura) {
    addEventListener('pointermove', (e) => {
      objetivo.x = (e.clientX / innerWidth - 0.5) * 2;
      objetivo.y = (e.clientY / innerHeight - 0.5) * 2;
    }, { passive: true });
  }

  // --- Adaptación si el equipo no da la talla ---
  const registrarFps = crearMonitorFps({
    alBajar: () => {
      if (pixelRatio > 1) {
        pixelRatio = Math.max(1, pixelRatio * 0.75);
        renderizador.setPixelRatio(pixelRatio);
        renderizador.setSize(innerWidth, innerHeight, false);
      } else if (arcos && cantidadArcos > 8) {
        cantidadArcos = Math.max(8, Math.floor(cantidadArcos * 0.6));
        arcos.fijarCantidad(cantidadArcos);
      }
    },
  });

  // --- Entrada cinemática ---
  let secuencia = null;
  let arcosActivos = true;
  if (raiz.classList.contains('js-intro') && !captura) {
    arcosActivos = false;
    try {
      sessionStorage.setItem('un_intro_vista', '1');
    } catch { /* sin almacenamiento, volverá a mostrarse */ }

    const logo = crearLogo3d({ renderizador });
    escena.add(logo.objeto);
    secuencia = crearSecuencia({
      camara,
      logo,
      posicionFinal: POSICION_FINAL_CAMARA,
      alRevelar(p) {
        planeta.fijarBrillo(p);
        estrellas.fijarOpacidad(0.35 + 0.65 * p);
        arcos?.fijarOpacidad(p);
        if (p > 0.5) arcosActivos = true;
      },
      alTerminar() {
        const teniaFoco = document.activeElement === botonSaltar;
        botonSaltar.hidden = true;
        escena.remove(logo.objeto);
        secuencia.liberar();
        secuencia = null;
        raiz.classList.add('listo');
        if (teniaFoco) document.querySelector('.boton-principal')?.focus({ preventScroll: true });
      },
    });

    const saltar = () => secuencia?.saltar();
    botonSaltar.hidden = false;
    botonSaltar.addEventListener('click', saltar);
    addEventListener('keydown', (e) => {
      if (e.key === 'Escape') saltar();
    });
  }

  // --- Bucle ---
  let anterior = performance.now();
  function cuadro(ahora) {
    const dt = Math.min((ahora - anterior) / 1000, 0.1);
    registrarFps((ahora - anterior) / 1000);
    anterior = ahora;

    estrellas.actualizar(dt);
    planeta.actualizar(dt);
    if (arcosActivos) arcos?.actualizar(dt);

    if (secuencia) {
      secuencia.actualizar(dt);
    } else {
      camara.position.x += (objetivo.x * 0.32 - camara.position.x) * Math.min(1, dt * 2.2);
      camara.position.y += (-objetivo.y * 0.18 - camara.position.y) * Math.min(1, dt * 2.2);
      camara.lookAt(0, 0, -8);
    }

    renderizador.render(escena, camara);
  }

  function cuadroSeguro(ahora) {
    try {
      cuadro(ahora);
    } catch (error) {
      modoRespaldo(error);
    }
  }

  function reanudar() {
    anterior = performance.now();
    renderizador.setAnimationLoop(cuadroSeguro);
  }

  document.addEventListener('visibilitychange', () => {
    if (raiz.classList.contains('estatico')) return;
    if (document.hidden) renderizador.setAnimationLoop(null);
    else reanudar();
  });

  addEventListener('pageshow', (e) => {
    if (e.persisted && !raiz.classList.contains('estatico')) reanudar();
  });

  addEventListener('resize', () => {
    camara.aspect = innerWidth / innerHeight;
    camara.updateProjectionMatrix();
    renderizador.setSize(innerWidth, innerHeight, false);
  });

  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault();
    modoRespaldo('se perdió el contexto WebGL');
  });

  // --- Arranque ---
  if (captura) raiz.classList.add('captura');
  raiz.classList.add('escena-activa');
  reanudar();
  // Sin entrada, textos y botones no esperan a la textura: las luces aparecen luego con un fundido.
  if (!secuencia) raiz.classList.add('listo');
  conTiempoLimite(cargaTextura, LIMITE_TEXTURA_MS).catch((error) => modoRespaldo(error));
}

try {
  iniciar();
} catch (error) {
  modoRespaldo(error);
}
