// Les sondes de reflet. Le Heikhal ne voit pas le ciel : son or reflète la salle, rendue une fois à la seule lumière
// de la Menora. Les cours le voient, mais pas seulement lui : leur or reflète la cour au soleil, ses murs et son ciel
// bleu, là où le dôme éclairant, beige et uniforme, ne lui donnait qu'un aplat.
import * as THREE from "three";
import { filtrePMREM } from "./ciel.js";

export const DANS_HEIKHAL = new Set(["heikhal", "portes_heikhal", "sculptures_murs", "menora", "shulchan",
                                     "mizbeach_hazahav", "parokhet"]);
export const COURS = ["azara", "ezrat_nashim"];
// `voitLeCiel` : sous un toit, le reflet d'une cour suit encore la part de ciel que la carte cuite a reçue ; celui de la salle est déjà la salle.
const SALLE = { intensite: 0.5, hauteur: 3, portee: 80, voitLeCiel: false };
// Plus haut que l'œil : l'or des candélabres et des façades monte à vingt mètres, et la sonde doit voir les deux faces de la cour.
// La portée passe le dôme, posé à 5 700 m.
const COUR = { intensite: 1, hauteur: 6, portee: 6000, voitLeCiel: true };
const RESOLUTION = 256;
const CIEL_DE_LA_BOITE = 1000;
// L'épaisseur d'une parokhet : l'extérieure, tournée vers la salle, en est ; l'intérieure non.
const MARGE = 0.25;
const reflets = new Map();

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

// La cour dont un maillage reflète la sonde : celle qui contient son centre, vu d'en haut — l'or d'une façade monte au-dessus de l'emprise.
export function courDe(maillage, boites) {
  const centre = new THREE.Box3().setFromObject(maillage).getCenter(new THREE.Vector3());
  for (const [cour, { min, max }] of boites) {
    if (centre.x >= min.x && centre.x <= max.x && centre.z >= min.z && centre.z <= max.z) return cour;
  }
  return null;
}

// La salle se rend à la Menora seule en ÉTEIGNANT le reste, sans l'ôter : un soleil retiré ou un ciel
// nul change les nuanceurs, et la sonde en compilait un jeu entier qui ne servait qu'à elle.
export function sonderHeikhal(renderer, scene, { kelim, materiaux, lumieres, caches }) {
  const position = kelim.getCenter(new THREE.Vector3()).setY(kelim.min.y + SALLE.hauteur);
  sonder(renderer, scene, { cle: "heikhal", position, materiaux, lumieres, caches, reglage: SALLE });
}

// Prise au centre de la cour, la sonde y montre le mur d'en face là où le dallage, près d'un bord, doit refléter le mur
// voisin : chaque matière recoupe son rayon réfléchi avec la boîte de sa cour. Elle monte au ciel, qui est à l'infini.
// Les cours se suivent d'ouest en est, et l'emprise de l'Ezrat Nashim court jusqu'au fond de l'Azara : chacune commence
// où finit la précédente. `sols` : la cote du dallage de chaque cour.
export function boitesDesSondes(emprises, sols) {
  let ouest = -Infinity;
  return new Map(COURS.map((cour) => {
    const { min, max } = emprises.get(cour);
    const boite = new THREE.Box3(min.clone().setX(Math.max(min.x, ouest)), max.clone().setY(CIEL_DE_LA_BOITE));
    ouest = max.x;
    const centre = boite.getCenter(new THREE.Vector3()).setY(sols[cour] + COUR.hauteur);
    return [cour, { min: boite.min, max: boite.max, centre }];
  }));
}

// La cour se rend telle qu'on la voit, soleil et ciel compris ; à refaire quand le moment change.
export function sonderLaCour(renderer, scene, { cour, boite, materiaux }) {
  sonder(renderer, scene, { cle: cour, position: boite.centre, materiaux, lumieres: [], caches: [], reglage: COUR });
}

// Sans air ni reflet pendant la prise : le reflet d'avant s'y verrait, et l'air voilerait deux fois.
// Refaite après une perte de contexte ou un changement de moment, la sonde remplace son reflet sans changer de nuanceur.
function sonder(renderer, scene, { cle, position, materiaux, lumieres, caches, reglage }) {
  const cible = new THREE.WebGLCubeRenderTarget(RESOLUTION, { type: THREE.HalfFloatType });
  const camera = new THREE.CubeCamera(0.1, reglage.portee, cible);
  camera.position.copy(position);
  camera.updateMatrixWorld();

  const intensites = lumieres.map((l) => l.intensity);
  const visibles = caches.map((o) => o.visible);
  const densite = scene.fog.density;
  const intensitesDesReflets = new Map();
  scene.traverse((o) => {
    if (o.isMesh && !intensitesDesReflets.has(o.material)) intensitesDesReflets.set(o.material, o.material.envMapIntensity);
  });
  lumieres.forEach((l) => { l.intensity = 0; });
  caches.forEach((o) => { o.visible = false; });
  scene.fog.density = 0;
  for (const m of intensitesDesReflets.keys()) m.envMapIntensity = 0;
  try {
    camera.update(renderer, scene);
  } finally {
    lumieres.forEach((l, i) => { l.intensity = intensites[i]; });
    caches.forEach((o, i) => { o.visible = visibles[i]; });
    scene.fog.density = densite;
    for (const [m, intensite] of intensitesDesReflets) m.envMapIntensity = intensite;
  }

  const ancien = reflets.get(cle);
  const reflet = filtrePMREM(renderer).fromCubemap(cible.texture);
  reflets.set(cle, reflet);
  cible.dispose();
  for (const materiau of materiaux) {
    materiau.needsUpdate = materiau.envMap === null;
    materiau.envMap = reflet.texture;
    materiau.envMapIntensity = reglage.intensite;
    materiau.userData.refletVoitLeCiel = reglage.voitLeCiel;
  }
  ancien?.dispose();
}
