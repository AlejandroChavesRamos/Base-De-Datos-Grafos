import * as THREE from '../vendor/three/three.module.min.js';
import { latLonAVec3, puntoArco } from './geo.js';
import { paresIniciales } from './ciudades.js';

const PUNTOS_CURVA = 48;
const RADIO_TUBO = 0.0048;
const DURACION_ONDA = 0.8;

const VERTICE = /* glsl */ `
  varying float vT;
  void main() {
    vT = uv.x;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const FRAGMENTO = /* glsl */ `
  uniform float uCabeza;
  uniform float uDesvanecer;
  uniform float uOpacidad;
  varying float vT;
  void main() {
    float trazo = smoothstep(uCabeza, uCabeza - 0.02, vT) * smoothstep(0.0, 0.03, vT);
    float cola = exp(-pow(max(uCabeza - vT, 0.0) / 0.3, 2.0));
    float punta = exp(-pow((vT - uCabeza) / 0.016, 2.0));
    vec3 azul = vec3(0.3, 0.64, 1.0);
    vec3 blanco = vec3(0.96, 0.97, 1.0);
    vec3 color = azul * trazo * (0.2 + cola * 0.85) * uDesvanecer + blanco * punta * 2.2 * step(uCabeza, 1.0);
    gl_FragColor = vec4(color * uOpacidad, 1.0);
    #include <colorspace_fragment>
  }
`;

function vec3(p) {
  return new THREE.Vector3(p.x, p.y, p.z);
}

function crearArco([origen, destino], radio, geoOnda) {
  const a = latLonAVec3(origen.lat, origen.lon, radio);
  const b = latLonAVec3(destino.lat, destino.lon, radio);
  const separacion = vec3(a).angleTo(vec3(b));
  const altura = 0.03 + separacion * 0.17;

  const puntos = [];
  for (let i = 0; i <= PUNTOS_CURVA; i++) puntos.push(vec3(puntoArco(a, b, i / PUNTOS_CURVA, radio, altura)));
  const curva = new THREE.CatmullRomCurve3(puntos);
  const geometria = new THREE.TubeGeometry(curva, 72, RADIO_TUBO, 5, false);
  const material = new THREE.ShaderMaterial({
    vertexShader: VERTICE,
    fragmentShader: FRAGMENTO,
    uniforms: { uCabeza: { value: 0 }, uDesvanecer: { value: 1 }, uOpacidad: { value: 1 } },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    toneMapped: false,
  });
  const malla = new THREE.Mesh(geometria, material);
  malla.visible = false;

  // Onda al llegar: un anillo pegado a la superficie, que crece y se apaga.
  const matOnda = new THREE.MeshBasicMaterial({
    color: 0x4da3ff,
    transparent: true,
    opacity: 0,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    toneMapped: false,
  });
  const onda = new THREE.Mesh(geoOnda, matOnda);
  const normal = vec3(b).normalize();
  onda.position.copy(normal).multiplyScalar(radio * 1.0015);
  onda.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
  onda.visible = false;

  return {
    malla,
    onda,
    material,
    matOnda,
    geometria,
    espera: 0,
    tiempo: 0,
    duracion: 1,
    activo: false,
  };
}

function programar(arco, espera) {
  arco.espera = espera;
  arco.tiempo = 0;
  arco.duracion = 1.6 + Math.random() * 1.2;
  arco.activo = false;
  arco.malla.visible = false;
}

export function crearArcos({ radio, cantidad }) {
  const objeto = new THREE.Group();
  const geoOnda = new THREE.RingGeometry(0.9, 1, 40);
  const arcos = paresIniciales(cantidad).map((par) => crearArco(par, radio, geoOnda));
  arcos.forEach((arco, i) => {
    objeto.add(arco.malla, arco.onda);
    // Los primeros, los de Barranquilla, salen casi de inmediato.
    programar(arco, i < 6 ? 0.15 + i * 0.5 : 1 + Math.random() * 9);
  });

  let activos = arcos.length;
  let opacidad = 1;

  return {
    objeto,
    fijarCantidad(n) {
      activos = Math.min(n, arcos.length);
      arcos.forEach((arco, i) => {
        if (i >= activos) {
          arco.malla.visible = false;
          arco.onda.visible = false;
        }
      });
    },
    fijarOpacidad(p) {
      opacidad = p;
      arcos.forEach((arco) => { arco.material.uniforms.uOpacidad.value = p; });
    },
    actualizar(dt) {
      for (let i = 0; i < activos; i++) {
        const arco = arcos[i];

        if (!arco.activo) {
          arco.espera -= dt;
          if (arco.espera > 0) continue;
          arco.activo = true;
          arco.malla.visible = true;
        }

        arco.tiempo += dt;
        const viaje = arco.tiempo / arco.duracion;
        const u = arco.material.uniforms;
        u.uCabeza.value = Math.min(viaje, 1.001);

        // Tras llegar, el trazo se apaga en el mismo tiempo que dura la onda.
        const trasLlegar = arco.tiempo - arco.duracion;
        u.uDesvanecer.value = trasLlegar > 0 ? Math.max(0, 1 - trasLlegar / DURACION_ONDA) : 1;

        if (trasLlegar > 0 && trasLlegar < DURACION_ONDA) {
          const p = trasLlegar / DURACION_ONDA;
          arco.onda.visible = true;
          arco.onda.scale.setScalar(0.03 + p * 0.2);
          arco.matOnda.opacity = (1 - p) * 0.9 * opacidad;
        } else {
          arco.onda.visible = false;
        }

        if (trasLlegar >= DURACION_ONDA) programar(arco, 0.4 + Math.random() * 4.5);
      }
    },
    liberar() {
      arcos.forEach((arco) => {
        arco.geometria.dispose();
        arco.material.dispose();
        arco.matOnda.dispose();
      });
      geoOnda.dispose();
    },
  };
}
