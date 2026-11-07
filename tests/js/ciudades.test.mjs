import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CIUDADES, paresIniciales } from '../../app/static/animaciones/planeta/ciudades.js';

test('hay al menos 30 ciudades y Barranquilla es la primera', () => {
  assert.ok(CIUDADES.length >= 30);
  assert.equal(CIUDADES[0].nombre, 'Barranquilla');
});

test('coordenadas válidas y nombres únicos', () => {
  CIUDADES.forEach((c) => {
    assert.ok(Math.abs(c.lat) <= 90, c.nombre);
    assert.ok(Math.abs(c.lon) <= 180, c.nombre);
  });
  assert.equal(new Set(CIUDADES.map((c) => c.nombre)).size, CIUDADES.length);
});

test('los primeros arcos salen de Barranquilla', () => {
  paresIniciales(6).slice(0, 3).forEach(([o]) => assert.equal(o.nombre, 'Barranquilla'));
});

test('ningún par une una ciudad consigo misma', () => {
  paresIniciales(36).forEach(([o, d]) => assert.notEqual(o.nombre, d.nombre));
});

test('devuelve exactamente los pares pedidos', () => {
  assert.equal(paresIniciales(12).length, 12);
  assert.equal(paresIniciales(36).length, 36);
});

test('los pares no se repiten', () => {
  const claves = paresIniciales(36).map(([o, d]) => `${o.nombre}>${d.nombre}`);
  assert.equal(new Set(claves).size, claves.length);
});
