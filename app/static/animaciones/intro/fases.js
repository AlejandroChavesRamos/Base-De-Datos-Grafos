// Línea de tiempo de la entrada, en segundos. Lógica pura, sin Three.js.
export const TIEMPOS = { trazo: 0.8, volumen: 2.4, travesia: 4.2, fin: 6.0 };

export function faseEn(t) {
  const { trazo, volumen, travesia, fin } = TIEMPOS;
  if (t >= fin) return { nombre: 'fin', progreso: 1 };
  if (t >= travesia) return { nombre: 'travesia', progreso: (t - travesia) / (fin - travesia) };
  if (t >= volumen) return { nombre: 'volumen', progreso: (t - volumen) / (travesia - volumen) };
  if (t >= trazo) return { nombre: 'trazo', progreso: (t - trazo) / (volumen - trazo) };
  return { nombre: 'inicio', progreso: Math.max(t, 0) / trazo };
}

export function suavizar(p) {
  const x = Math.min(1, Math.max(0, p));
  return x * x * x * (x * (x * 6 - 15) + 10);
}
