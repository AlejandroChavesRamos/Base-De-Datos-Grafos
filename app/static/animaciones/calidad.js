// Decide cuánto se dibuja según el dispositivo. Función pura: recibe los datos y no toca el navegador.
export function elegirCalidad({ ancho, tactil, reducido, webgl }) {
  if (reducido || !webgl) {
    return { modo: 'estatico', textura: null, arcos: 0, pixelRatioMax: 1, segmentos: 0, parallax: false };
  }
  if (tactil || ancho < 768) {
    return { modo: 'ligero', textura: 2048, arcos: 12, pixelRatioMax: 1.5, segmentos: 64, parallax: false };
  }
  return { modo: 'completo', textura: 4096, arcos: 36, pixelRatioMax: 2, segmentos: 128, parallax: true };
}
