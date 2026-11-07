// Mide la fluidez real y avisa cuando se mantiene baja durante varios segundos.
export function crearMonitorFps({ umbral = 40, segundos = 3, alBajar }) {
  let tiempoBajo = 0;
  return function registrar(dt) {
    if (dt <= 0 || dt > 0.5) return; // pausas largas, como volver de otra pestaña, no cuentan
    tiempoBajo = 1 / dt < umbral ? tiempoBajo + dt : Math.max(0, tiempoBajo - dt);
    if (tiempoBajo >= segundos - 1e-6) {
      tiempoBajo = 0;
      alBajar();
    }
  };
}

export function conTiempoLimite(promesa, ms) {
  let temporizador;
  const limite = new Promise((_, rechazar) => {
    temporizador = setTimeout(() => rechazar(new Error(`Se agotó el tiempo de espera (${ms} ms)`)), ms);
  });
  return Promise.race([promesa, limite]).finally(() => clearTimeout(temporizador));
}
