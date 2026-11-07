import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  puntosTrazo, contornoDeTrazo, aEscena, GROSOR, NODOS, CENTRO_HUECO_U,
} from '../../app/static/animaciones/intro/trazo-logo.js';

test('el trazo empieza y termina en los nodos extremos', () => {
  const p = puntosTrazo();
  assert.deepEqual(p[0], NODOS[0]);
  assert.deepEqual(p.at(-1), NODOS.at(-1));
});

test('la curva de la U llega abajo a y=115', () => {
  const maxY = Math.max(...puntosTrazo().map((q) => q[1]));
  assert.ok(Math.abs(maxY - 115) < 0.01, `maxY=${maxY}`);
});

test('contorno de un segmento recto: 4 vértices a ±grosor/2', () => {
  const c = contornoDeTrazo([[0, 0], [10, 0]], 2);
  assert.equal(c.length, 4);
  assert.deepEqual(c.map((q) => Math.abs(q[1])), [1, 1, 1, 1]);
});

test('las esquinas agudas no asoman fuera de los nodos: límite de inglete 0,75×grosor', () => {
  const pts = puntosTrazo();
  contornoDeTrazo(pts, GROSOR).forEach((v) => {
    const d = Math.min(...pts.map((q) => Math.hypot(v[0] - q[0], v[1] - q[1])));
    assert.ok(d <= GROSOR * 0.75 + 1e-9, `vértice a ${d} del trazo`);
  });
});

test('el contorno no tiene puntas agudas, que el bisel 3D convertiría en picos', () => {
  const c = contornoDeTrazo(puntosTrazo(), GROSOR);
  const area = c.reduce((s, p, i) => {
    const q = c[(i + 1) % c.length];
    return s + p[0] * q[1] - q[0] * p[1];
  }, 0);
  c.forEach((p, i) => {
    const a = c[(i - 1 + c.length) % c.length];
    const b = c[(i + 1) % c.length];
    const u = [a[0] - p[0], a[1] - p[1]];
    const v = [b[0] - p[0], b[1] - p[1]];
    const convexo = (v[0] * u[1] - v[1] * u[0]) * area > 0;
    if (!convexo) return;
    const angulo = Math.acos((u[0] * v[0] + u[1] * v[1]) / (Math.hypot(...u) * Math.hypot(...v)));
    assert.ok(angulo >= Math.PI / 3, `punta de ${(angulo * 180 / Math.PI).toFixed(1)}° en el vértice ${i}`);
  });
});

test('aEscena centra el lienzo', () => {
  assert.deepEqual(aEscena([100, 70]), [0, 0]);
});

test('el hueco de la U queda libre de trazo, para que la cámara lo cruce', () => {
  const d = Math.min(...puntosTrazo().map((q) => Math.hypot(CENTRO_HUECO_U[0] - q[0], CENTRO_HUECO_U[1] - q[1])));
  assert.ok(d > GROSOR, `solo ${d} de margen`);
});
