// Geometría del logo "Nodo": la U y la N son una sola línea que une cuatro nodos.
// Es la fuente de verdad del logo animado; marca/logo-un.svg dibuja estos mismos puntos.
// Lienzo de 200 × 140, con y hacia abajo y el logo centrado en (100, 70).

export const GROSOR = 9;

export const NODOS = [[40, 25], [100, 25], [160, 115], [160, 25]];

export const CENTRO_HUECO_U = [70, 65];

const CENTRO_CURVA = [70, 85];
const RADIO_CURVA = 30;

const redondear = (v) => Math.round(v * 1000) / 1000;

export function puntosTrazo(pasosCurva = 24) {
  const puntos = [NODOS[0]];
  for (let i = 0; i <= pasosCurva; i++) {
    const a = (i / pasosCurva) * Math.PI;
    puntos.push([
      redondear(CENTRO_CURVA[0] - RADIO_CURVA * Math.cos(a)),
      redondear(CENTRO_CURVA[1] + RADIO_CURVA * Math.sin(a)),
    ]);
  }
  puntos.push(NODOS[1], NODOS[2], NODOS[3]);
  return puntos;
}

function normal(a, b) {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const largo = Math.hypot(dx, dy);
  return [-dy / largo, dx / largo];
}

// Devuelve el polígono cerrado que rodea la línea: un lado de ida y el otro de vuelta.
export function contornoDeTrazo(puntos, grosor) {
  const mitad = grosor / 2;
  const limite = grosor * 0.75; // queda bajo los nodos, así las esquinas agudas no forman picos
  const ida = [];
  const vuelta = [];
  puntos.forEach((p, i) => {
    const previa = i > 0 ? normal(puntos[i - 1], p) : null;
    const siguiente = i < puntos.length - 1 ? normal(p, puntos[i + 1]) : null;
    const n1 = previa ?? siguiente;
    const n2 = siguiente ?? previa;
    let mx = n1[0] + n2[0];
    let my = n1[1] + n2[1];
    const largo = Math.hypot(mx, my) || 1;
    mx /= largo;
    my /= largo;
    const coseno = Math.max(mx * n1[0] + my * n1[1], 1e-6);
    const inglete = mitad / coseno;

    if (inglete <= limite) {
      ida.push([p[0] + mx * inglete, p[1] + my * inglete]);
      vuelta.push([p[0] - mx * inglete, p[1] - my * inglete]);
      return;
    }

    // Esquina aguda: por fuera se corta en bisel, porque una sola punta formaría un pico.
    const giro = n1[0] * n2[1] - n1[1] * n2[0];
    const hacia = giro < 0 ? ida : vuelta;
    const haciaInterior = giro < 0 ? vuelta : ida;
    const signo = giro < 0 ? 1 : -1;
    hacia.push(
      [p[0] + signo * n1[0] * mitad, p[1] + signo * n1[1] * mitad],
      [p[0] + signo * n2[0] * mitad, p[1] + signo * n2[1] * mitad],
    );
    haciaInterior.push([p[0] - signo * mx * limite, p[1] - signo * my * limite]);
  });
  return [...ida, ...vuelta.reverse()];
}

export function aEscena([x, y]) {
  return [(x - 100) / 50, (70 - y) / 50];
}
