import * as THREE from '../vendor/three/three.module.min.js';
import { puntosTrazo, contornoDeTrazo, NODOS, GROSOR, aEscena } from './trazo-logo.js';
import { suavizar } from './fases.js';

const PROFUNDIDAD = 0.2;

function texturaHalo() {
  const lienzo = document.createElement('canvas');
  lienzo.width = lienzo.height = 128;
  const c = lienzo.getContext('2d');
  const g = c.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.18, 'rgba(160,210,255,.85)');
  g.addColorStop(0.5, 'rgba(77,163,255,.22)');
  g.addColorStop(1, 'rgba(77,163,255,0)');
  c.fillStyle = g;
  c.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(lienzo);
}

function texturaDestello() {
  const lienzo = document.createElement('canvas');
  lienzo.width = 512;
  lienzo.height = 64;
  const c = lienzo.getContext('2d');
  const h = c.createLinearGradient(0, 0, 512, 0);
  h.addColorStop(0, 'rgba(120,190,255,0)');
  h.addColorStop(0.5, 'rgba(235,245,255,1)');
  h.addColorStop(1, 'rgba(120,190,255,0)');
  c.fillStyle = h;
  c.fillRect(0, 0, 512, 64);
  c.globalCompositeOperation = 'destination-in';
  const v = c.createLinearGradient(0, 0, 0, 64);
  v.addColorStop(0, 'rgba(0,0,0,0)');
  v.addColorStop(0.5, 'rgba(0,0,0,1)');
  v.addColorStop(1, 'rgba(0,0,0,0)');
  c.fillStyle = v;
  c.fillRect(0, 0, 512, 64);
  return new THREE.CanvasTexture(lienzo);
}

// Entorno procedural para los reflejos del metal: un estudio de paneles luminosos.
function crearEntorno(renderizador) {
  const estudio = new THREE.Scene();
  estudio.background = new THREE.Color(0x01030a);
  const panel = (color, intensidad, x, y, z, ancho, alto) => {
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(ancho, alto),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(intensidad), side: THREE.DoubleSide }),
    );
    m.position.set(x, y, z);
    m.lookAt(0, 0, 0);
    estudio.add(m);
    return m;
  };
  panel(0xdfeeff, 9, 0, 7, 3, 12, 2.5);
  panel(0x4da3ff, 8, -8, 0, 3, 3, 12);
  panel(0x4da3ff, 5, 8, -2, 4, 2, 10);
  panel(0xf5f8ff, 5, 3, -7, 4, 10, 1.2);
  const generador = new THREE.PMREMGenerator(renderizador);
  const destino = generador.fromScene(estudio, 0.035);
  generador.dispose();
  estudio.traverse((o) => {
    if (o.isMesh) {
      o.geometry.dispose();
      o.material.dispose();
    }
  });
  return destino;
}

export function crearLogo3d({ renderizador }) {
  const objeto = new THREE.Group();
  const puntos = puntosTrazo().map((p) => aEscena(p));
  const v3 = (p) => new THREE.Vector3(p[0], p[1], 0);

  // --- Línea de luz que dibuja el logo ---
  const camino = new THREE.CurvePath();
  for (let i = 0; i < puntos.length - 1; i++) {
    camino.add(new THREE.LineCurve3(v3(puntos[i]), v3(puntos[i + 1])));
  }
  const SEGMENTOS = 420;
  const geoNucleo = new THREE.TubeGeometry(camino, SEGMENTOS, 0.024, 8, false);
  const geoAura = new THREE.TubeGeometry(camino, SEGMENTOS, 0.07, 8, false);
  const matNucleo = new THREE.MeshBasicMaterial({
    color: new THREE.Color(0xf5f8ff).multiplyScalar(1.6),
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
  });
  const matAura = new THREE.MeshBasicMaterial({
    color: 0x4da3ff,
    transparent: true,
    opacity: 0.32,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
  });
  const lineaNucleo = new THREE.Mesh(geoNucleo, matNucleo);
  const lineaAura = new THREE.Mesh(geoAura, matAura);
  objeto.add(lineaAura, lineaNucleo);

  // --- Logo macizo ---
  const contorno = contornoDeTrazo(puntosTrazo(), GROSOR).map((p) => aEscena(p));
  const forma = new THREE.Shape(contorno.map((p) => new THREE.Vector2(p[0], p[1])));
  const geoMacizo = new THREE.ExtrudeGeometry(forma, {
    depth: PROFUNDIDAD,
    bevelEnabled: true,
    bevelThickness: 0.035,
    bevelSize: 0.022,
    bevelSegments: 4,
    curveSegments: 12,
  });
  geoMacizo.translate(0, 0, -PROFUNDIDAD / 2);
  const entorno = crearEntorno(renderizador);
  const matMacizo = new THREE.MeshPhysicalMaterial({
    color: 0xb8d0f5,
    metalness: 1,
    roughness: 0.2,
    clearcoat: 1,
    clearcoatRoughness: 0.12,
    envMap: entorno.texture,
    envMapIntensity: 1.25,
    transparent: true,
    opacity: 0,
  });
  const macizo = new THREE.Mesh(geoMacizo, matMacizo);
  macizo.visible = false;
  objeto.add(macizo);

  // --- Nodos ---
  const geoNodo = new THREE.SphereGeometry(0.135, 32, 24);
  const matNodo = new THREE.MeshPhysicalMaterial({
    color: 0x4da3ff,
    emissive: 0x1464d8,
    emissiveIntensity: 0.75,
    metalness: 0.4,
    roughness: 0.18,
    clearcoat: 1,
    envMap: entorno.texture,
    transparent: true,
    opacity: 0,
  });
  const mapaHalo = texturaHalo();
  const nodos = NODOS.map((n) => {
    const [x, y] = aEscena(n);
    const esfera = new THREE.Mesh(geoNodo, matNodo);
    esfera.position.set(x, y, PROFUNDIDAD / 2 + 0.03);
    esfera.visible = false;
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({
      map: mapaHalo,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      depthTest: false,
      transparent: true,
      opacity: 0,
      toneMapped: false,
    }));
    halo.position.set(x, y, 0.2);
    halo.scale.setScalar(0.1);
    objeto.add(esfera, halo);
    // Fracción de la línea en la que la luz alcanza este nodo.
    let mejor = 0;
    let distancia = Infinity;
    const q = new THREE.Vector3(x, y, 0);
    for (let i = 0; i <= 400; i++) {
      const d = camino.getPointAt(i / 400).distanceTo(q);
      if (d < distancia) {
        distancia = d;
        mejor = i / 400;
      }
    }
    return { esfera, halo, alcance: mejor };
  });

  // --- Punta de la línea mientras dibuja ---
  const punta = new THREE.Sprite(new THREE.SpriteMaterial({
    map: mapaHalo,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    depthTest: false,
    transparent: true,
    toneMapped: false,
  }));
  punta.scale.setScalar(0.62);
  objeto.add(punta);

  // --- Destello que recorre el logo ---
  const mapaDestello = texturaDestello();
  const destello = new THREE.Sprite(new THREE.SpriteMaterial({
    map: mapaDestello,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    depthTest: false,
    transparent: true,
    opacity: 0,
    toneMapped: false,
  }));
  destello.scale.set(3.6, 0.1, 1);
  objeto.add(destello);

  // --- Halo de fondo y luces ---
  const fondo = new THREE.Sprite(new THREE.SpriteMaterial({
    map: mapaHalo,
    color: 0x2a6fe0,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    transparent: true,
    opacity: 0,
    toneMapped: false,
  }));
  fondo.position.z = -0.9;
  fondo.scale.setScalar(6);
  objeto.add(fondo);

  const luzClave = new THREE.DirectionalLight(0xf5f8ff, 1.6);
  luzClave.position.set(-2, 3, 4);
  const luzBorde = new THREE.PointLight(0x4da3ff, 22, 12, 1.6);
  luzBorde.position.set(2.4, -1.2, -1.6);
  const luzBarrido = new THREE.PointLight(0xdcecff, 0, 6, 1.4);
  luzBarrido.position.z = 1.2;
  objeto.add(luzClave, luzBorde, luzBarrido);

  let ultimoTrazo = -1;

  return {
    objeto,
    // Fase inicial: un punto de luz en el primer nodo; los demás, apenas sugeridos.
    fijarInicio(p) {
      const e = suavizar(p);
      nodos.forEach((n, i) => {
        n.halo.material.opacity = i === 0 ? e : e * 0.16;
        n.halo.scale.setScalar(i === 0 ? 0.5 + e * 0.4 : 0.34);
      });
      punta.visible = false;
      lineaNucleo.geometry.setDrawRange(0, 0);
      lineaAura.geometry.setDrawRange(0, 0);
    },
    fijarTrazo(p) {
      const avance = Math.min(1, Math.max(0, p));
      if (avance !== ultimoTrazo) {
        ultimoTrazo = avance;
        const n = Math.floor(geoNucleo.index.count * avance / 6) * 6;
        const a = Math.floor(geoAura.index.count * avance / 6) * 6;
        geoNucleo.setDrawRange(0, n);
        geoAura.setDrawRange(0, a);
      }
      punta.visible = avance > 0 && avance < 1;
      if (punta.visible) punta.position.copy(camino.getPointAt(avance));
      nodos.forEach((n, i) => {
        const encendido = suavizar((avance - n.alcance) / 0.06);
        n.halo.material.opacity = Math.max(i === 0 ? 1 : 0.16, encendido);
        n.halo.scale.setScalar((i === 0 ? 0.9 : 0.34) + encendido * (i === 0 ? 0 : 0.56));
      });
    },
    fijarVolumen(p) {
      const e = suavizar(p / 0.72);
      macizo.visible = e > 0;
      macizo.scale.z = Math.max(0.001, e);
      matMacizo.opacity = suavizar(p / 0.35);
      matMacizo.transparent = matMacizo.opacity < 1;
      const salida = 1 - suavizar(p / 0.5);
      matNucleo.opacity = salida;
      matAura.opacity = 0.32 * salida;
      lineaNucleo.visible = salida > 0;
      lineaAura.visible = salida > 0;
      matNodo.opacity = e;
      matNodo.transparent = e < 1;
      nodos.forEach((n) => {
        n.esfera.visible = e > 0;
        n.esfera.scale.setScalar(Math.max(0.001, e));
        n.halo.material.opacity = 0.34 + 0.66 * (1 - e);
        n.halo.scale.setScalar(0.9 + e * 0.3);
      });
      fondo.material.opacity = e * 0.34;
    },
    fijarDestello(p) {
      const avance = Math.min(1, Math.max(0, p));
      const activo = avance > 0 && avance < 1;
      destello.visible = activo;
      const x = -2.2 + avance * 4.4;
      destello.position.set(x, 0.25 - avance * 0.5, 0.45);
      destello.material.opacity = Math.sin(avance * Math.PI) * 0.95;
      luzBarrido.position.x = x;
      luzBarrido.position.y = 0.8 - avance * 1.6;
      luzBarrido.intensity = Math.sin(avance * Math.PI) * 26;
      matMacizo.envMapRotation.y = -0.7 + avance * 1.4;
      matMacizo.envMapIntensity = 1.25 + Math.sin(avance * Math.PI) * 0.9;
    },
    fijarSalida(p) {
      const q = 1 - suavizar(p);
      fondo.material.opacity = 0.34 * q;
      nodos.forEach((n) => { n.halo.material.opacity = 0.34 * q; });
    },
    ocultar() {
      objeto.visible = false;
    },
    actualizar() {},
    liberar() {
      [geoNucleo, geoAura, geoMacizo, geoNodo].forEach((g) => g.dispose());
      [matNucleo, matAura, matMacizo, matNodo].forEach((m) => m.dispose());
      nodos.forEach((n) => n.halo.material.dispose());
      [punta, destello, fondo].forEach((s) => s.material.dispose());
      mapaHalo.dispose();
      mapaDestello.dispose();
      entorno.dispose();
    },
  };
}
