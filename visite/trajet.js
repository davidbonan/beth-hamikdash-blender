// Le pas du marcheur et le trajet d'une caméra qui marche seule : la marche libre, les parcours et le cinéma s'y accordent.
import * as THREE from "three";

export const PAS = 3.4;            // m/s
export const SOUS_PAS = 0.12;      // m : sous la demi-ama d'une contremarche, la sonde de sol n'en saute aucune
export const REPONSE_SOL = 0.22;   // s : une marche de 1/2 ama se glisse, elle ne se saute pas
export const lisse = (u) => u * u * (3 - 2 * u);

export const pointEnM = (ama, [x, z, y = 0]) => new THREE.Vector3(x * ama, y * ama, z * ama);
export const cibleEnM = (ama, [x, y, z]) => new THREE.Vector3(x * ama, y * ama, z * ama);

export function polyligne(points) {
  const longueurs = [0];
  for (let i = 1; i < points.length; i++) longueurs.push(longueurs[i - 1] + points[i].distanceTo(points[i - 1]));
  const total = longueurs[longueurs.length - 1];
  return (u) => {
    const d = u * total;
    let i = 1;
    while (i < points.length - 1 && longueurs[i] < d) i++;
    const part = (d - longueurs[i - 1]) / (longueurs[i] - longueurs[i - 1] || 1);
    return new THREE.Vector3().lerpVectors(points[i - 1], points[i], THREE.MathUtils.clamp(part, 0, 1));
  };
}
