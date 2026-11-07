// Script clásico y bloqueante: decide el estado inicial antes de pintar, para evitar destellos.
// js-animado: los textos esperan a que la escena esté lista.
// js-intro: además, se reproduce la entrada cinemática.
// Si bienvenida.js no arranca a tiempo (red lenta o fallo), se pasa a la imagen fija.
// Una vez activa la escena, ella decide: el temporizador no interfiere con una entrada en pausa.
(function () {
  var LIMITE_ARRANQUE_MS = 4500;
  var raiz = document.documentElement;
  var parametros = new URLSearchParams(location.search);
  if (parametros.has('captura')) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var webgl = false;
  try {
    webgl = !!document.createElement('canvas').getContext('webgl2');
  } catch (e) { /* sin WebGL se usa la portada fija */ }
  if (!webgl) return;

  raiz.classList.add('js-animado');

  var vista = false;
  try {
    vista = sessionStorage.getItem('un_intro_vista') === '1';
  } catch (e) { /* sin almacenamiento, la entrada simplemente se muestra */ }
  if (!vista) raiz.classList.add('js-intro');

  setTimeout(function () {
    if (raiz.classList.contains('escena-activa')) return;
    raiz.classList.remove('js-animado', 'js-intro');
    raiz.classList.add('estatico', 'listo');
  }, LIMITE_ARRANQUE_MS);
})();
