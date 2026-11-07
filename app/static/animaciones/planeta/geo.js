// Cálculos geográficos puros, sin Three.js. Convención igual al mapeo de SphereGeometry:
// longitud 0 en +x, longitud 90° E en -z, polo norte en +y.

const RAD = Math.PI / 180;

export function latLonAVec3(lat, lon, r) {
  const fi = lat * RAD;
  const lam = lon * RAD;
  return {
    x: r * Math.cos(fi) * Math.cos(lam),
    y: r * Math.sin(fi),
    z: -r * Math.cos(fi) * Math.sin(lam),
  };
}

// Giro sobre Y que deja esa longitud de frente a la cámara (+z).
export function rotacionYParaLon(lon) {
  return -(lon + 90) * RAD;
}

const unitario = (p) => {
  const l = Math.hypot(p.x, p.y, p.z) || 1;
  return { x: p.x / l, y: p.y / l, z: p.z / l };
};

function direccionEsferica(a, b, t) {
  const coseno = Math.min(1, Math.max(-1, a.x * b.x + a.y * b.y + a.z * b.z));
  const omega = Math.acos(coseno);
  const seno = Math.sin(omega);
  if (seno < 1e-6) {
    if (coseno > 0) return a;
    // Antípodas: hay infinitos caminos, se toma uno perpendicular cualquiera.
    const eje = Math.abs(a.y) < 0.9 ? { x: 0, y: 1, z: 0 } : { x: 1, y: 0, z: 0 };
    const perp = unitario({
      x: a.y * eje.z - a.z * eje.y,
      y: a.z * eje.x - a.x * eje.z,
      z: a.x * eje.y - a.y * eje.x,
    });
    const g = t * Math.PI;
    return {
      x: a.x * Math.cos(g) + perp.x * Math.sin(g),
      y: a.y * Math.cos(g) + perp.y * Math.sin(g),
      z: a.z * Math.cos(g) + perp.z * Math.sin(g),
    };
  }
  const f1 = Math.sin((1 - t) * omega) / seno;
  const f2 = Math.sin(t * omega) / seno;
  return { x: a.x * f1 + b.x * f2, y: a.y * f1 + b.y * f2, z: a.z * f1 + b.z * f2 };
}

// Punto del arco entre a y b: sigue el círculo máximo y se eleva hasta `altura` en el centro.
export function puntoArco(a, b, t, r, altura) {
  const d = direccionEsferica(unitario(a), unitario(b), t);
  const radio = r + altura * Math.sin(Math.PI * t);
  return { x: d.x * radio, y: d.y * radio, z: d.z * radio };
}
