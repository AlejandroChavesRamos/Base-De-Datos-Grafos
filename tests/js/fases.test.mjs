import { test } from 'node:test';
import assert from 'node:assert/strict';
import { TIEMPOS, faseEn, suavizar } from '../../app/static/animaciones/intro/fases.js';

test('los tiempos coinciden con el diseño', () => {
  assert.deepEqual(TIEMPOS, { trazo: 0.8, volumen: 2.4, travesia: 4.2, fin: 6.0 });
});

test('fases en sus límites', () => {
  assert.equal(faseEn(0).nombre, 'inicio');
  assert.equal(faseEn(0.8).nombre, 'trazo');
  assert.equal(faseEn(2.4).nombre, 'volumen');
  assert.equal(faseEn(4.2).nombre, 'travesia');
  assert.equal(faseEn(6).nombre, 'fin');
});

test('el progreso va de 0 a 1 dentro de cada fase', () => {
  assert.equal(faseEn(0.8).progreso, 0);
  assert.ok(Math.abs(faseEn(1.6).progreso - 0.5) < 1e-9);
  assert.ok(Math.abs(faseEn(5.1).progreso - 0.5) < 1e-9);
});

test('más allá del final se mantiene en fin con progreso 1', () => {
  assert.deepEqual(faseEn(99), { nombre: 'fin', progreso: 1 });
});

test('un tiempo negativo se trata como el inicio', () => {
  assert.deepEqual(faseEn(-1), { nombre: 'inicio', progreso: 0 });
});

test('suavizar conserva los extremos y el centro', () => {
  assert.equal(suavizar(0), 0);
  assert.equal(suavizar(1), 1);
  assert.equal(suavizar(0.5), 0.5);
  assert.equal(suavizar(-3), 0);
  assert.equal(suavizar(4), 1);
});
