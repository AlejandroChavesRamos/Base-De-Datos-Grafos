import { test } from 'node:test';
import assert from 'node:assert/strict';
import { latLonAVec3, rotacionYParaLon, puntoArco } from '../../app/static/animaciones/planeta/geo.js';

const largo = (p) => Math.hypot(p.x, p.y, p.z);

function casi(a, b, eps = 1e-9) {
  for (const k of ['x', 'y', 'z']) assert.ok(Math.abs(a[k] - b[k]) < eps, `${k}: ${a[k]} vs ${b[k]}`);
}

test('lon 0 está en +x y lon 90 en -z', () => {
  casi(latLonAVec3(0, 0, 1), { x: 1, y: 0, z: 0 });
  casi(latLonAVec3(0, 90, 1), { x: 0, y: 0, z: -1 });
});

test('el polo norte está en +y', () => {
  casi(latLonAVec3(90, 0, 2), { x: 0, y: 2, z: 0 });
});

test('rotacionYParaLon deja Barranquilla de frente', () => {
  const p = latLonAVec3(0, -74.8, 1);
  const g = rotacionYParaLon(-74.8);
  assert.ok(Math.abs(p.x * Math.cos(g) + p.z * Math.sin(g)) < 1e-9);
  assert.ok(-p.x * Math.sin(g) + p.z * Math.cos(g) > 0.999);
});

test('el arco parte y llega a la superficie', () => {
  const a = latLonAVec3(10.96, -74.8, 5);
  const b = latLonAVec3(40.42, -3.7, 5);
  casi(puntoArco(a, b, 0, 5, 1), a);
  casi(puntoArco(a, b, 1, 5, 1), b);
});

test('el arco se eleva en medio exactamente la altura pedida', () => {
  const a = latLonAVec3(10.96, -74.8, 5);
  const b = latLonAVec3(40.42, -3.7, 5);
  assert.ok(Math.abs(largo(puntoArco(a, b, 0.5, 5, 1)) - 6) < 1e-9);
});

test('puntoArco con a == b no produce NaN', () => {
  const a = latLonAVec3(10.96, -74.8, 5);
  const m = puntoArco(a, a, 0.5, 5, 1);
  assert.ok(Number.isFinite(m.x) && Number.isFinite(m.y) && Number.isFinite(m.z));
});

test('puntoArco entre antípodas no produce NaN', () => {
  const m = puntoArco({ x: 5, y: 0, z: 0 }, { x: -5, y: 0, z: 0 }, 0.5, 5, 1);
  assert.ok(Number.isFinite(m.x) && Number.isFinite(m.y) && Number.isFinite(m.z));
});
