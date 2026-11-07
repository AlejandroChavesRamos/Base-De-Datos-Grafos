import * as THREE from '../vendor/three/three.module.min.js';
import { faseEn, suavizar } from './fases.js';
import { CENTRO_HUECO_U, aEscena } from './trazo-logo.js';

const Z_LOGO = 10;
const DISTANCIA_MINIMA = 4.6;
const ANCHO_LOGO = 3.1;
const OBJETIVO_FINAL = new THREE.Vector3(0, 0, -8);

// Toda la entrada es una sola toma: la cámara nunca salta, solo se mueve.
export function crearSecuencia({ camara, logo, posicionFinal, alRevelar, alTerminar }) {
  logo.objeto.position.z = Z_LOGO;

  const [huecoX, huecoY] = aEscena(CENTRO_HUECO_U);
  const objetivoLogo = new THREE.Vector3(0, 0, Z_LOGO);
  const objetivo = new THREE.Vector3();

  function distanciaDeInicio() {
    // En pantallas angostas la cámara se aleja para que el logo quepa de lado a lado.
    const mitad = Math.tan(THREE.MathUtils.degToRad(camara.fov / 2));
    return Math.max(DISTANCIA_MINIMA, ANCHO_LOGO / (2 * mitad * camara.aspect));
  }

  function curvaDeTravesia() {
    return new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, 0, Z_LOGO + distanciaDeInicio()),
      new THREE.Vector3(huecoX * 0.75, huecoY, Z_LOGO + 1.5),
      new THREE.Vector3(huecoX, huecoY, Z_LOGO),
      new THREE.Vector3(huecoX * 0.6, huecoY, Z_LOGO - 3),
      posicionFinal.clone(),
    ], false, 'centripetal');
  }

  let tiempo = 0;
  let curva = null;
  let terminada = false;

  function encuadreEstatico() {
    camara.position.set(0, 0, Z_LOGO + distanciaDeInicio());
    camara.lookAt(objetivoLogo);
  }

  function terminar() {
    if (terminada) return;
    terminada = true;
    camara.position.copy(posicionFinal);
    camara.lookAt(OBJETIVO_FINAL);
    logo.ocultar();
    alRevelar(1);
    alTerminar();
  }

  encuadreEstatico();
  logo.fijarInicio(0);
  alRevelar(0);

  return {
    get terminada() {
      return terminada;
    },
    actualizar(dt) {
      if (terminada) return;
      tiempo += dt;
      const { nombre, progreso } = faseEn(tiempo);

      if (nombre === 'inicio') {
        logo.fijarInicio(progreso);
        encuadreEstatico();
      } else if (nombre === 'trazo') {
        logo.fijarTrazo(suavizar(progreso));
        encuadreEstatico();
      } else if (nombre === 'volumen') {
        logo.fijarTrazo(1);
        logo.fijarVolumen(progreso);
        logo.fijarDestello((progreso - 0.35) / 0.6);
        // Un avance lentísimo de cámara le da peso al logo, y un giro breve deja ver su volumen.
        camara.position.set(0, 0, Z_LOGO + distanciaDeInicio() - suavizar(progreso) * 0.28);
        camara.lookAt(objetivoLogo);
        const giro = Math.sin(progreso * Math.PI);
        logo.objeto.rotation.set(giro * 0.2, giro * -0.5, 0);
      } else if (nombre === 'travesia') {
        if (!curva) {
          logo.fijarVolumen(1);
          logo.fijarDestello(1);
          logo.objeto.rotation.set(0, 0, 0);
          curva = curvaDeTravesia();
        }
        // Acelera poco a poco, sin frenar antes del hueco.
        const e = suavizar(progreso);
        curva.getPoint(e, camara.position);
        objetivo.lerpVectors(objetivoLogo, OBJETIVO_FINAL, suavizar((progreso - 0.2) / 0.7));
        camara.lookAt(objetivo);
        logo.fijarSalida(progreso / 0.45);
        alRevelar(suavizar((progreso - 0.25) / 0.75));
      } else {
        terminar();
      }
    },
    saltar: terminar,
    liberar() {
      logo.liberar();
    },
  };
}
