import * as THREE from '../vendor/three/three.module.min.js';

const VERTICE = /* glsl */ `
  attribute float aTamano;
  attribute float aFase;
  uniform float uTiempo;
  uniform float uEscala;
  varying float vBrillo;
  void main() {
    vBrillo = 0.55 + 0.45 * sin(uTiempo * 0.7 + aFase);
    gl_PointSize = aTamano * uEscala;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const FRAGMENTO = /* glsl */ `
  uniform float uOpacidad;
  varying float vBrillo;
  void main() {
    float d = length(gl_PointCoord - 0.5) * 2.0;
    float a = smoothstep(1.0, 0.1, d);
    gl_FragColor = vec4(vec3(0.82, 0.9, 1.0), a * vBrillo * uOpacidad);
    #include <colorspace_fragment>
  }
`;

function crearCapa(cantidad, radio, tamano, escala) {
  const posiciones = new Float32Array(cantidad * 3);
  const tamanos = new Float32Array(cantidad);
  const fases = new Float32Array(cantidad);
  const v = new THREE.Vector3();
  for (let i = 0; i < cantidad; i++) {
    v.randomDirection().multiplyScalar(radio * (0.8 + Math.random() * 0.4));
    posiciones.set([v.x, v.y, v.z], i * 3);
    tamanos[i] = tamano * (0.45 + Math.random() ** 3 * 1.6);
    fases[i] = Math.random() * Math.PI * 2;
  }
  const geometria = new THREE.BufferGeometry();
  geometria.setAttribute('position', new THREE.BufferAttribute(posiciones, 3));
  geometria.setAttribute('aTamano', new THREE.BufferAttribute(tamanos, 1));
  geometria.setAttribute('aFase', new THREE.BufferAttribute(fases, 1));
  const material = new THREE.ShaderMaterial({
    vertexShader: VERTICE,
    fragmentShader: FRAGMENTO,
    uniforms: { uTiempo: { value: 0 }, uEscala: { value: escala }, uOpacidad: { value: 1 } },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    toneMapped: false,
  });
  return new THREE.Points(geometria, material);
}

export function crearEstrellas({ cantidad = 2600 } = {}) {
  const escala = Math.min(window.devicePixelRatio || 1, 2);
  const lejanas = crearCapa(Math.round(cantidad * 0.72), 90, 1.5, escala);
  const cercanas = crearCapa(Math.round(cantidad * 0.28), 55, 2.4, escala);
  const objeto = new THREE.Group();
  objeto.add(lejanas, cercanas);

  let tiempo = 0;

  return {
    objeto,
    fijarOpacidad(p) {
      lejanas.material.uniforms.uOpacidad.value = p;
      cercanas.material.uniforms.uOpacidad.value = p;
    },
    actualizar(dt) {
      tiempo += dt;
      lejanas.material.uniforms.uTiempo.value = tiempo;
      cercanas.material.uniforms.uTiempo.value = tiempo;
      objeto.rotation.y += dt * 0.0016;
    },
    liberar() {
      for (const capa of [lejanas, cercanas]) {
        capa.geometry.dispose();
        capa.material.dispose();
      }
    },
  };
}
