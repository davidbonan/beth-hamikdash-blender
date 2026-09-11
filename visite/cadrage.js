import * as THREE from "three";

const MARGE = 0.9;          // part du cadre, en coordonnées normalisées, que l'élément peut occuper
const RECUL_MIN = 1.2;
const PAS_RECUL = 0.4;

const essai = new THREE.PerspectiveCamera();
const coin = new THREE.Vector3();

export function unirEmprises(emprises, ids) {
  const boite = new THREE.Box3();
  for (const id of ids) {
    const b = emprises.get(id);
    if (b) boite.union(b);
  }
  return boite;
}

function tientDansLeCadre(boite) {
  essai.updateMatrixWorld();
  for (let i = 0; i < 8; i++) {
    coin.set(i & 1 ? boite.max.x : boite.min.x, i & 2 ? boite.max.y : boite.min.y, i & 4 ? boite.max.z : boite.min.z)
      .applyMatrix4(essai.matrixWorldInverse);
    if (coin.z > -essai.near) return false;
    coin.applyMatrix4(essai.projectionMatrix);
    if (Math.abs(coin.x) > MARGE || Math.abs(coin.y) > MARGE) return false;
  }
  return true;
}

// L'œil le plus proche d'où la boîte tient entière dans le champ de `camera`, à rebours du cap.
export function oeilQuiCadre(camera, boite, { cap, hauteur, reculMax }) {
  essai.copy(camera, false);
  essai.updateProjectionMatrix();
  const centre = boite.getCenter(new THREE.Vector3());
  const a = THREE.MathUtils.degToRad(cap);
  const versX = Math.cos(a), versZ = -Math.sin(a);
  let recul = RECUL_MIN;
  for (; recul < reculMax; recul += PAS_RECUL) {
    essai.position.set(centre.x - versX * recul, hauteur, centre.z - versZ * recul);
    essai.lookAt(centre);
    if (tientDansLeCadre(boite)) break;
  }
  recul = Math.min(recul, reculMax);
  return new THREE.Vector3(centre.x - versX * recul, hauteur, centre.z - versZ * recul);
}
