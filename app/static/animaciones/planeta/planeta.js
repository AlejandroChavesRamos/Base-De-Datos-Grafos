import * as THREE from '../vendor/three/three.module.min.js';
import { rotacionYParaLon } from './geo.js';

const VELOCIDAD_GIRO = 0.01; // rad/s
const RADIO = 5;
const INCLINACION = -0.86; // sube el Caribe hacia la zona visible del planeta
const LON_INICIAL = -74.8; // Barranquilla

const VERTICE_TIERRA = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vVista;
  void main() {
    vUv = uv;
    vNormal = normalize(normalMatrix * normal);
    vec4 pos = modelViewMatrix * vec4(position, 1.0);
    vVista = normalize(-pos.xyz);
    gl_Position = projectionMatrix * pos;
  }
`;

const FRAGMENTO_TIERRA = /* glsl */ `
  uniform sampler2D uMapa;
  uniform float uHayMapa;
  uniform float uBrillo;
  uniform float uPulso;
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vVista;
  void main() {
    vec3 n = normalize(vNormal);
    float frente = max(dot(n, normalize(vVista)), 0.0);

    // Luces de las ciudades, llevadas hacia el dorado de la imagen de referencia.
    vec3 mapa = uHayMapa > 0.001 ? texture2D(uMapa, vUv).rgb * uHayMapa : vec3(0.0);
    float lum = dot(mapa, vec3(0.299, 0.587, 0.114));
    float ciudad = smoothstep(0.015, 0.3, lum);
    vec3 dorado = mix(vec3(1.0, 0.56, 0.17), vec3(1.0, 0.82, 0.52), smoothstep(0.3, 1.0, lum));
    vec3 luces = dorado * ciudad * (0.55 + lum * 2.1) * uPulso;

    // Tierra y océano apenas visibles, para que el planeta no sea un círculo negro.
    vec3 suelo = mapa * vec3(0.22, 0.34, 0.62) * (1.0 - ciudad);
    vec3 base = vec3(0.0012, 0.0032, 0.0095) + suelo;

    // Borde iluminado, más intenso en la parte alta, como en la referencia.
    float borde = pow(1.0 - frente, 5.5);
    float arriba = smoothstep(-0.25, 0.85, n.y);
    vec3 halo = vec3(0.24, 0.5, 1.0) * borde * (0.05 + 0.95 * arriba);

    gl_FragColor = vec4((base + luces + halo) * uBrillo, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

const VERTICE_ATMOSFERA = /* glsl */ `
  varying vec3 vNormal;
  varying vec3 vVista;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vec4 pos = modelViewMatrix * vec4(position, 1.0);
    vVista = normalize(-pos.xyz);
    gl_Position = projectionMatrix * pos;
  }
`;

const FRAGMENTO_ATMOSFERA = /* glsl */ `
  uniform float uBrillo;
  varying vec3 vNormal;
  varying vec3 vVista;
  void main() {
    vec3 n = normalize(vNormal);
    float i = pow(clamp(-dot(n, normalize(vVista)) / 0.25, 0.0, 1.0), 3.0);
    float arriba = smoothstep(-0.35, 0.85, n.y);
    vec3 color = mix(vec3(0.16, 0.42, 1.0), vec3(0.62, 0.84, 1.0), i);
    gl_FragColor = vec4(color * i * (0.06 + 0.72 * arriba) * uBrillo, 1.0);
    #include <colorspace_fragment>
  }
`;

export function crearPlaneta({ textura = null, segmentos = 128 }) {
  const objeto = new THREE.Group();
  const inclinacion = new THREE.Group();
  inclinacion.rotation.x = INCLINACION;
  objeto.add(inclinacion);

  const nucleo = new THREE.Group();
  nucleo.rotation.y = rotacionYParaLon(LON_INICIAL);
  inclinacion.add(nucleo);

  const geoTierra = new THREE.SphereGeometry(RADIO, segmentos, Math.round(segmentos * 0.75));
  const matTierra = new THREE.ShaderMaterial({
    vertexShader: VERTICE_TIERRA,
    fragmentShader: FRAGMENTO_TIERRA,
    uniforms: {
      uMapa: { value: textura },
      uHayMapa: { value: textura ? 1 : 0 },
      uBrillo: { value: 1 },
      uPulso: { value: 1 },
    },
  });
  nucleo.add(new THREE.Mesh(geoTierra, matTierra));

  const geoAtmosfera = new THREE.SphereGeometry(RADIO * 1.032, segmentos, Math.round(segmentos * 0.75));
  const matAtmosfera = new THREE.ShaderMaterial({
    vertexShader: VERTICE_ATMOSFERA,
    fragmentShader: FRAGMENTO_ATMOSFERA,
    uniforms: { uBrillo: { value: 1 } },
    side: THREE.BackSide,
    blending: THREE.AdditiveBlending,
    transparent: true,
    depthWrite: false,
    toneMapped: false,
  });
  objeto.add(new THREE.Mesh(geoAtmosfera, matAtmosfera));

  let tiempo = 0;
  let mapaListo = Boolean(textura);

  return {
    objeto,
    nucleo,
    radio: RADIO,
    fijarTextura(t) {
      matTierra.uniforms.uMapa.value = t;
      mapaListo = Boolean(t);
    },
    fijarBrillo(p) {
      objeto.visible = p > 0;
      matTierra.uniforms.uBrillo.value = p;
      matAtmosfera.uniforms.uBrillo.value = p;
    },
    actualizar(dt) {
      tiempo += dt;
      nucleo.rotation.y += VELOCIDAD_GIRO * dt;
      // Si la textura llega tarde, las luces aparecen con un fundido, sin saltos.
      const mezcla = matTierra.uniforms.uHayMapa;
      if (mapaListo && mezcla.value < 1) mezcla.value = Math.min(1, mezcla.value + dt / 0.8);
      matTierra.uniforms.uPulso.value = 1 + 0.06 * Math.sin(tiempo * 0.9);
    },
    liberar() {
      geoTierra.dispose();
      matTierra.dispose();
      geoAtmosfera.dispose();
      matAtmosfera.dispose();
      matTierra.uniforms.uMapa.value?.dispose();
    },
  };
}
