// Ciudades que unen los arcos. Es una representación visual, no tráfico real.
// Primero las del continente americano, que es lo que se ve al abrir la portada.
export const CIUDADES = [
  { nombre: 'Barranquilla', lat: 10.96, lon: -74.8 },
  { nombre: 'Bogotá', lat: 4.71, lon: -74.07 },
  { nombre: 'Medellín', lat: 6.24, lon: -75.58 },
  { nombre: 'Ciudad de Panamá', lat: 8.98, lon: -79.52 },
  { nombre: 'Caracas', lat: 10.48, lon: -66.9 },
  { nombre: 'Miami', lat: 25.76, lon: -80.19 },
  { nombre: 'Ciudad de México', lat: 19.43, lon: -99.13 },
  { nombre: 'Lima', lat: -12.05, lon: -77.04 },
  { nombre: 'Quito', lat: -0.18, lon: -78.47 },
  { nombre: 'São Paulo', lat: -23.55, lon: -46.63 },
  { nombre: 'Buenos Aires', lat: -34.6, lon: -58.38 },
  { nombre: 'Santiago de Chile', lat: -33.45, lon: -70.67 },
  { nombre: 'Nueva York', lat: 40.71, lon: -74.01 },
  { nombre: 'Atlanta', lat: 33.75, lon: -84.39 },
  { nombre: 'Toronto', lat: 43.65, lon: -79.38 },
  { nombre: 'Santo Domingo', lat: 18.49, lon: -69.93 },
  { nombre: 'San José', lat: 9.93, lon: -84.09 },
  { nombre: 'Los Ángeles', lat: 34.05, lon: -118.24 },
  { nombre: 'Madrid', lat: 40.42, lon: -3.7 },
  { nombre: 'Londres', lat: 51.51, lon: -0.13 },
  { nombre: 'París', lat: 48.86, lon: 2.35 },
  { nombre: 'Berlín', lat: 52.52, lon: 13.4 },
  { nombre: 'Lisboa', lat: 38.72, lon: -9.14 },
  { nombre: 'Dakar', lat: 14.72, lon: -17.47 },
  { nombre: 'Lagos', lat: 6.52, lon: 3.38 },
  { nombre: 'Johannesburgo', lat: -26.2, lon: 28.05 },
  { nombre: 'El Cairo', lat: 30.04, lon: 31.24 },
  { nombre: 'Dubái', lat: 25.2, lon: 55.27 },
  { nombre: 'Bombay', lat: 19.08, lon: 72.88 },
  { nombre: 'Singapur', lat: 1.35, lon: 103.82 },
  { nombre: 'Tokio', lat: 35.68, lon: 139.69 },
  { nombre: 'Sídney', lat: -33.87, lon: 151.21 },
];

const AMERICANAS = 18;

const DESDE_BARRANQUILLA = ['Bogotá', 'Miami', 'Madrid', 'São Paulo', 'Ciudad de México', 'Nueva York'];

// Lista determinista: la portada siempre abre con los mismos arcos desde Barranquilla.
export function paresIniciales(n) {
  const porNombre = new Map(CIUDADES.map((c) => [c.nombre, c]));
  const pares = [];
  const vistos = new Set();

  const anadir = (origen, destino) => {
    const clave = `${origen.nombre}>${destino.nombre}`;
    if (origen === destino || vistos.has(clave) || pares.length >= n) return;
    vistos.add(clave);
    pares.push([origen, destino]);
  };

  DESDE_BARRANQUILLA.forEach((nombre) => anadir(CIUDADES[0], porNombre.get(nombre)));

  let semilla = 7;
  const azar = (limite) => {
    semilla = (semilla * 1664525 + 1013904223) % 4294967296;
    return Math.floor((semilla / 4294967296) * limite);
  };

  while (pares.length < n) {
    // Tres de cada cuatro arcos salen de América, para que casi siempre haya movimiento a la vista.
    const origen = CIUDADES[azar(4) < 3 ? azar(AMERICANAS) : azar(CIUDADES.length)];
    anadir(origen, CIUDADES[azar(CIUDADES.length)]);
  }
  return pares;
}
