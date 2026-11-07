import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const codigo = readFileSync(new URL('../../app/static/animaciones/precarga.js', import.meta.url), 'utf8');

// Ejecuta el script real con un navegador mínimo y devuelve sus clases y temporizadores.
function ejecutar({ reducido = false, webgl = true, vista = false, busqueda = '' } = {}) {
  const clases = new Set();
  const temporizadores = [];
  vm.runInNewContext(codigo, {
    URLSearchParams,
    location: { search: busqueda },
    matchMedia: () => ({ matches: reducido }),
    sessionStorage: { getItem: () => (vista ? '1' : null) },
    setTimeout: (fn, ms) => temporizadores.push({ fn, ms }),
    document: {
      documentElement: {
        classList: {
          add: (...c) => c.forEach((x) => clases.add(x)),
          remove: (...c) => c.forEach((x) => clases.delete(x)),
          contains: (x) => clases.has(x),
        },
      },
      createElement: () => ({ getContext: () => webgl }),
    },
  });
  return { clases, temporizadores };
}

test('visita nueva: oculta los textos, pide la entrada y deja un temporizador de seguridad', () => {
  const { clases, temporizadores } = ejecutar();
  assert.ok(clases.has('js-animado') && clases.has('js-intro'));
  assert.equal(temporizadores.length, 1);
  assert.ok(temporizadores[0].ms <= 5000, `tarda ${temporizadores[0].ms} ms`);
});

test('quien vuelve no repite la entrada', () => {
  const { clases } = ejecutar({ vista: true });
  assert.ok(clases.has('js-animado'));
  assert.ok(!clases.has('js-intro'));
});

test('si la escena nunca arranca, pasa a la imagen fija con los textos visibles', () => {
  const { clases, temporizadores } = ejecutar();
  temporizadores[0].fn();
  assert.ok(clases.has('estatico') && clases.has('listo'));
  assert.ok(!clases.has('js-animado') && !clases.has('js-intro'));
});

test('si la escena ya arrancó, el temporizador no toca nada, aunque la entrada esté en pausa', () => {
  const { clases, temporizadores } = ejecutar();
  clases.add('escena-activa');
  temporizadores[0].fn();
  assert.ok(clases.has('js-animado') && clases.has('js-intro'));
  assert.ok(!clases.has('estatico') && !clases.has('listo'));
});

test('con movimiento reducido no hay clases ni temporizador', () => {
  const { clases, temporizadores } = ejecutar({ reducido: true });
  assert.equal(clases.size, 0);
  assert.equal(temporizadores.length, 0);
});

test('sin WebGL no hay clases ni temporizador', () => {
  const { clases, temporizadores } = ejecutar({ webgl: false });
  assert.equal(clases.size, 0);
  assert.equal(temporizadores.length, 0);
});
