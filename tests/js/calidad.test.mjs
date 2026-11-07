import { test } from 'node:test';
import assert from 'node:assert/strict';
import { elegirCalidad } from '../../app/static/animaciones/calidad.js';
import { crearMonitorFps, conTiempoLimite } from '../../app/static/animaciones/rendimiento.js';

const pick = ({ modo, textura, arcos, pixelRatioMax, parallax }) => ({ modo, textura, arcos, pixelRatioMax, parallax });

test('movimiento reducido → modo estatico', () => {
  assert.equal(elegirCalidad({ ancho: 1920, tactil: false, reducido: true, webgl: true }).modo, 'estatico');
});

test('sin WebGL → modo estatico', () => {
  assert.equal(elegirCalidad({ ancho: 1920, tactil: false, reducido: false, webgl: false }).modo, 'estatico');
});

test('escritorio', () => {
  assert.deepEqual(
    pick(elegirCalidad({ ancho: 1920, tactil: false, reducido: false, webgl: true })),
    { modo: 'completo', textura: 4096, arcos: 36, pixelRatioMax: 2, parallax: true },
  );
});

test('celular', () => {
  assert.deepEqual(
    pick(elegirCalidad({ ancho: 375, tactil: true, reducido: false, webgl: true })),
    { modo: 'ligero', textura: 2048, arcos: 12, pixelRatioMax: 1.5, parallax: false },
  );
});

test('tablet táctil ancha también es ligera y sin parallax', () => {
  const c = elegirCalidad({ ancho: 1280, tactil: true, reducido: false, webgl: true });
  assert.equal(c.modo, 'ligero');
  assert.equal(c.parallax, false);
});

test('el monitor avisa tras 3 s bajo 40 fps, una sola vez por tanda', () => {
  let avisos = 0;
  const registrar = crearMonitorFps({ alBajar: () => { avisos += 1; } });
  for (let i = 0; i < 60; i++) registrar(0.05); // 3 s a 20 fps
  assert.equal(avisos, 1);
  for (let i = 0; i < 30; i++) registrar(0.05); // 1,5 s más: aún no toca otro aviso
  assert.equal(avisos, 1);
  for (let i = 0; i < 30; i++) registrar(0.05);
  assert.equal(avisos, 2);
});

test('el monitor no avisa con 60 fps', () => {
  let avisos = 0;
  const registrar = crearMonitorFps({ alBajar: () => { avisos += 1; } });
  for (let i = 0; i < 1000; i++) registrar(1 / 60);
  assert.equal(avisos, 0);
});

test('el monitor ignora pausas largas, como volver de otra pestaña', () => {
  let avisos = 0;
  const registrar = crearMonitorFps({ alBajar: () => { avisos += 1; } });
  registrar(30);
  assert.equal(avisos, 0);
});

test('conTiempoLimite resuelve si la promesa llega a tiempo', async () => {
  assert.equal(await conTiempoLimite(Promise.resolve('ok'), 50), 'ok');
});

test('conTiempoLimite rechaza si la promesa tarda demasiado', async () => {
  await assert.rejects(conTiempoLimite(new Promise(() => {}), 10), /tiempo/i);
});
