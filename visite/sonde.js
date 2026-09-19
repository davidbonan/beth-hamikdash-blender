// Le Heikhal ne voit pas le ciel : son or reflète la salle, rendue une fois à la seule lumière de la Menora.
import * as THREE from "three";

export const DANS_HEIKHAL = new Set(["heikhal", "portes_heikhal", "sculptures_murs", "menora", "shulchan",
                                     "mizbeach_hazahav", "parokhet"]);
const INTENSITE = 0.5;
const HAUTEUR = 3;
const RESOLUTION = 256;
// L'épaisseur d'une parokhet : l'extérieure, tournée vers la salle, en est ; l'intérieure non.
const MARGE = 0.25;

// sculptures_murs court aussi dans le Kodesh HaKodashim : ce qui sort de la salle devient un maillage frère.
export function separerDuHeikhal(maillages, salle) {
  const boite = salle.clone().expandByScalar(MARGE);
  const centre = new THREE.Vector3();
  const sommet = new THREE.Vector3();
  for (const maillage of maillages) {
    const { index, attributes } = maillage.geometry;
    const dedans = [];
    const dehors = [];
    for (let i = 0; i < index.count; i += 3) {
      const triangle = [index.getX(i), index.getX(i + 1), index.getX(i + 2)];
      centre.set(0, 0, 0);
      for (const s of triangle) centre.add(sommet.fromBufferAttribute(attributes.position, s));
      centre.divideScalar(3).applyMatrix4(maillage.matrixWorld);
      (boite.containsPoint(centre) ? dedans : dehors).push(...triangle);
    }
    if (dehors.length === 0) continue;
    const frere = new THREE.Mesh(partie(maillage.geometry, dehors), maillage.material);
    frere.name = maillage.name;
    frere.userData = { ...maillage.userData };
    frere.matrix.copy(maillage.matrix).decompose(frere.position, frere.quaternion, frere.scale);
    maillage.parent.add(frere);
    frere.updateMatrixWorld();
    maillage.geometry = partie(maillage.geometry, dedans);
  }
  return maillages;
}

function partie(geometrie, indices) {
  const extrait = new THREE.BufferGeometry();
  for (const [nom, attribut] of Object.entries(geometrie.attributes)) extrait.setAttribute(nom, attribut);
  extrait.setIndex(indices);
  return extrait;
}

// La salle se rend à la Menora seule en ÉTEIGNANT le reste, sans l'ôter : un soleil retiré ou un ciel
// nul change les nuanceurs, et la sonde en compilait un jeu entier qui ne servait qu'à elle.
export function sonderHeikhal(renderer, scene, { kelim, materiaux, lumieres, caches }) {
  const cible = new THREE.WebGLCubeRenderTarget(RESOLUTION, { type: THREE.HalfFloatType });
  const camera = new THREE.CubeCamera(0.1, 80, cible);
  camera.position.copy(kelim.getCenter(new THREE.Vector3())).setY(kelim.min.y + HAUTEUR);
  camera.updateMatrixWorld();

  const intensites = lumieres.map((l) => l.intensity);
  const visibles = caches.map((o) => o.visible);
  const densite = scene.fog.density;
  const reflets = new Map();
  scene.traverse((o) => {
    if (o.isMesh && !reflets.has(o.material)) reflets.set(o.material, o.material.envMapIntensity);
  });
  lumieres.forEach((l) => { l.intensity = 0; });
  caches.forEach((o) => { o.visible = false; });
  scene.fog.density = 0;
  for (const m of reflets.keys()) m.envMapIntensity = 0;
  camera.update(renderer, scene);
  lumieres.forEach((l, i) => { l.intensity = intensites[i]; });
  caches.forEach((o, i) => { o.visible = visibles[i]; });
  scene.fog.density = densite;
  for (const [m, intensite] of reflets) m.envMapIntensity = intensite;

  const pmrem = new THREE.PMREMGenerator(renderer);
  const reflet = pmrem.fromCubemap(cible.texture).texture;
  pmrem.dispose();
  cible.dispose();
  for (const materiau of materiaux) {
    materiau.envMap = reflet;
    materiau.envMapIntensity = INTENSITE;
    materiau.needsUpdate = true;
  }
}
