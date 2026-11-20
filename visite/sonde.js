// Les sondes de reflet. Le Heikhal reflète la salle, rendue à la Menora et au jour de ses fenêtres et de sa porte,
// sans soleil ni ciel ambiant, qui n'y entrent pas. Les cours le voient, mais pas seulement lui : leur or reflète la cour au soleil, ses murs et son ciel
// bleu, là où le dôme éclairant, beige et uniforme, ne lui donnait qu'un aplat.
import * as THREE from "three";
import { filtrePMREM } from "./ciel.js";

export const DANS_HEIKHAL = new Set(["heikhal", "portes_heikhal", "sculptures_murs", "menora", "shulchan",
                                     "mizbeach_hazahav", "parokhet"]);
const COURS = ["azara", "ezrat_nashim"];
// `voitLeCiel` : sous un toit, le reflet d'une cour suit encore la part de ciel que la carte cuite a reçue ; celui de la salle est déjà la salle.
// `rebonds` : prise à la Menora seule, la salle d'or ne montrait que ses reflets directs et restait noire ailleurs ; chaque
// prise de plus voit l'or refléter la précédente, un rebond de lumière de plus.
// La portée passe le dôme, posé à 5 700 m, que la salle voit par ses fenêtres.
const SALLE = { intensite: 0.3, hauteur: 3, portee: 6000, voitLeCiel: false, rebonds: 2 };
// Plus haut que l'œil : l'or des candélabres et des façades monte à vingt mètres, et la sonde doit voir les deux faces de la cour.
const COUR = { intensite: 1, hauteur: 6, portee: 6000, voitLeCiel: true };
// `pan` et `retrait`, en mètres : plus grand que la baie, et assez au fond pour qu'elle seule en laisse voir.
const JOUR_DES_FENETRES = { couleur: 0xcfdcff, eclat: 40, pan: 3, retrait: 0.05 };
const RESOLUTION = 256;
const CIEL_DE_LA_BOITE = 1000;
// L'épaisseur d'une parokhet : l'extérieure, tournée vers la salle, en est ; l'intérieure non.
const MARGE = 0.25;
const reflets = new Map();

// sculptures_murs court aussi dans le Kodesh HaKodashim : ce qui sort de la salle devient un maillage frère.
export function separerDuHeikhal(maillages, salle) {
  const boite = salle.clone().expandByScalar(MARGE);
  separer(maillages, (centre) => boite.containsPoint(centre));
  return maillages;
}

// Les portes ferment la salle au fond d'une embrasure de six amot, ouverte sur l'Oulam : la face qui regarde l'embrasure
// devient un maillage frère, qui reflète l'Oulam. `faceDeLaSalle` : la cote x du mur oriental, côté salle.
export function separerLesPortes(portes, faceDeLaSalle) {
  return separer(portes, (centre, normale) => centre.x + MARGE * normale.x < faceDeLaSalle);
}

// `resteDedans(centre, normale)` : ce que le maillage garde de chaque triangle, en repère monde ; le reste part dans un frère, rendu.
function separer(maillages, resteDedans) {
  const freres = [];
  const [a, b, c] = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()];
  const centre = new THREE.Vector3();
  const normale = new THREE.Vector3();
  const arete = new THREE.Vector3();
  for (const maillage of maillages) {
    const { index, attributes } = maillage.geometry;
    const dedans = [];
    const dehors = [];
    for (let i = 0; i < index.count; i += 3) {
      const triangle = [index.getX(i), index.getX(i + 1), index.getX(i + 2)];
      [a, b, c].forEach((sommet, k) => sommet.fromBufferAttribute(attributes.position, triangle[k]).applyMatrix4(maillage.matrixWorld));
      centre.copy(a).add(b).add(c).divideScalar(3);
      normale.subVectors(b, a).cross(arete.subVectors(c, a)).normalize();
      (resteDedans(centre, normale) ? dedans : dehors).push(...triangle);
    }
    if (dehors.length === 0) continue;
    const frere = new THREE.Mesh(partie(maillage.geometry, dehors), maillage.material);
    frere.name = maillage.name;
    frere.userData = { ...maillage.userData };
    frere.matrix.copy(maillage.matrix).decompose(frere.position, frere.quaternion, frere.scale);
    maillage.parent.add(frere);
    frere.updateMatrixWorld();
    maillage.geometry = partie(maillage.geometry, dedans);
    freres.push(frere);
  }
  return freres;
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

// La salle se rend en ÉTEIGNANT le soleil et le ciel ambiant, sans les ôter : un soleil retiré ou un ciel
// nul change les nuanceurs, et la sonde en compilait un jeu entier qui ne servait qu'à elle. À refaire quand le moment change.
// `jour` : la part du ciel de jour que le moment garde, dont les fenêtres s'allument le temps de la prise.
export function sonderHeikhal(renderer, scene, { boite, materiaux, lumieres, fenetres, jour }) {
  fenetres.children[0]?.material.color.set(JOUR_DES_FENETRES.couleur).multiplyScalar(JOUR_DES_FENETRES.eclat * jour);
  fenetres.visible = true;
  try {
    sonder(renderer, scene, { cle: "heikhal", position: boite.centre, materiaux, lumieres, reglage: SALLE });
  } finally {
    fenetres.visible = false;
  }
}

// Le jour des fenêtres hautes ne passe qu'en reflet : les ta'im s'interposent, et le ciel ne s'y voit pas. CHOIX : un pan froid
// enfoncé dans chaque baie, que l'embrasure découpe à sa mesure, n'existe que pour la sonde.
export function fenetresDuHeikhal(points) {
  const materiau = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide, fog: false });
  const fenetres = new THREE.Group();
  fenetres.visible = false;
  for (const [x, y, z] of points) {
    const pan = new THREE.Mesh(new THREE.PlaneGeometry(JOUR_DES_FENETRES.pan, JOUR_DES_FENETRES.pan), materiau);
    pan.position.set(x, y, z + Math.sign(z) * JOUR_DES_FENETRES.retrait);
    fenetres.add(pan);
  }
  return fenetres;
}

// La salle se recoupe comme une cour : sans boîte, chaque point du mur voyait la même salle, et l'or en sortait d'un aplat.
// `foyer` : le haut de la Menora, d'où vient toute la lumière que la salle se renvoie.
export function boiteDuHeikhal(salle, kelim, menora) {
  const boite = salle.clone().expandByScalar(MARGE);
  const centre = kelim.getCenter(new THREE.Vector3()).setY(kelim.min.y + SALLE.hauteur);
  const foyer = menora.getCenter(new THREE.Vector3()).setY(menora.max.y);
  return { min: boite.min, max: boite.max, centre, foyer };
}

// L'Oulam s'ouvre sur l'Azara sans porte : son or reflète la salle au jour qui entre, et non la cour, prise au loin.
export function boiteDeLOulam(salle) {
  const boite = salle.clone().expandByScalar(MARGE);
  const centre = salle.getCenter(new THREE.Vector3()).setY(salle.min.y + COUR.hauteur);
  return { min: boite.min, max: boite.max, centre };
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
  sonder(renderer, scene, { cle: cour, position: boite.centre, materiaux, lumieres: [], reglage: COUR });
}

// Sans air ni reflet pendant la prise : le reflet d'avant s'y verrait, et l'air voilerait deux fois.
// Refaite après une perte de contexte ou un changement de moment, la sonde remplace son reflet sans changer de nuanceur.
function sonder(renderer, scene, { cle, position, materiaux, lumieres, reglage }) {
  for (let prise = 0; prise < (reglage.rebonds ?? 1); prise++) {
    const refletes = new Set(prise > 0 ? materiaux : []);
    prendre(renderer, scene, { cle, position, materiaux, lumieres, reglage, refletes });
  }
}

// `refletes` : les matières qui gardent pendant la prise le reflet de la prise d'avant.
function prendre(renderer, scene, { cle, position, materiaux, lumieres, reglage, refletes }) {
  const cible = new THREE.WebGLCubeRenderTarget(RESOLUTION, { type: THREE.HalfFloatType });
  const camera = new THREE.CubeCamera(0.1, reglage.portee, cible);
  camera.position.copy(position);
  camera.updateMatrixWorld();

  const intensites = lumieres.map((l) => l.intensity);
  const densite = scene.fog.density;
  const intensitesDesReflets = new Map();
  scene.traverse((o) => {
    if (o.isMesh && !intensitesDesReflets.has(o.material)) intensitesDesReflets.set(o.material, o.material.envMapIntensity);
  });
  lumieres.forEach((l) => { l.intensity = 0; });
  scene.fog.density = 0;
  for (const m of intensitesDesReflets.keys()) if (!refletes.has(m)) m.envMapIntensity = 0;
  try {
    camera.update(renderer, scene);
  } finally {
    lumieres.forEach((l, i) => { l.intensity = intensites[i]; });
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
