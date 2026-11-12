// Les vues : où poser le visiteur, et vers quoi le tourner, pour une entrée, une vue de repères ou un élément.
import * as THREE from "three";
import { oeilQuiCadre, unirEmprises } from "./cadrage.js";
import { OEIL } from "./marche.js";

const RECUL_AUTO = 60;
// Le premier côté d'où l'élément se voit sans mur devant ; l'est d'abord, l'axe du parcours.
const CAPS_AUTO = [180, 0, 90, 270];
const HAUTEUR_LIBRE = OEIL + 0.25;   // m : sous moins, la tête touche
const MARGE_PLANCHER = 0.1;          // m : le sol d'un lieu affleure le bas de son emprise
// Plus haut au-dessus du bas d'une emprise, c'est le dessus d'un mur ou d'un toit : les murs sont du concept de leur cour.
const HAUSSE_MAX = 6;
// Un sommet de mur : de part et d'autre, à moins de la plus large épaisseur de mur, le sol tombe de plus d'un mètre.
const PORTEES_CRETE = [0.8, 1.6, 2.4, 3.2];
const CHUTE_CRETE = 1;
const AXES_CRETE = [[[1, 0], [-1, 0]], [[0, 1], [0, -1]]];
const PIED = 0.3;                    // m : la demi-largeur d'un homme debout
const MONTEE_APPUI = 0.5;            // m : une marche sous le pied d'à côté le porte encore
const APPUIS = [[1, 0], [-1, 0], [0, 1], [0, -1]];
const RAYON_RECALAGE = 3;            // m : au-delà, le point visé est inaccessible
const PAS_RECALAGE = 0.3;
const ECART_CAP = 1;                 // m : plus près, le saut n'a pas de sens, le regard reste
// Du plus proche au plus lointain, les points où chercher un sol quand celui qu'on vise n'en a pas.
const RECALAGES = (() => {
  const n = Math.ceil(RAYON_RECALAGE / PAS_RECALAGE), points = [];
  for (let i = -n; i <= n; i++) {
    for (let j = -n; j <= n; j++) {
      const d = Math.hypot(i, j) * PAS_RECALAGE;
      if (d > 0 && d <= RAYON_RECALAGE) points.push([i * PAS_RECALAGE, j * PAS_RECALAGE, d]);
    }
  }
  return points.sort((a, b) => a[2] - b[2]);
})();
const centreDe = (boite) => boite.getCenter(new THREE.Vector3());
const contientAPlat = (boite, x, z) => x >= boite.min.x && x <= boite.max.x && z >= boite.min.z && z <= boite.max.z;

export function vuesDuTemple({ camera, marche, emprises, reperes, obstacles, tenirLeVol }) {
  const viseur = new THREE.Raycaster();

  function piedsDe(vue) {
    if (vue.position) return vue.position;
    const oeil = oeilQuiCadre(camera, unirEmprises(emprises, vue.cadre),
      { cap: vue.cap, hauteur: vue.sol + OEIL, reculMax: vue.recul_max ?? RECUL_AUTO });
    return [oeil.x, vue.sol, oeil.z];
  }

  function prendreVue(vue) {
    tenirLeVol(!!vue.vol);
    marche.poser(piedsDe(vue));
    if (vue.cadre) marche.orienterVers(centreDe(unirEmprises(emprises, vue.cadre)));
    else marche.orienterCap(vue);
  }

  function voitLeConcept(oeil, centre, id) {
    viseur.set(oeil, centre.clone().sub(oeil).normalize());
    viseur.far = oeil.distanceTo(centre);
    const [touche] = viseur.intersectObjects(obstacles, false);
    return !touche || touche.object.userData.concept === id;
  }

  function piedsQuiVoient(id, boite) {
    const centre = centreDe(boite);
    let repli = null;
    for (const cap of CAPS_AUTO) {
      const approche = oeilQuiCadre(camera, boite, { cap, hauteur: centre.y, reculMax: RECUL_AUTO });
      const sol = marche.solSous(new THREE.Vector3(approche.x, centre.y + OEIL, approche.z), Infinity);
      if (sol === null) continue;
      const oeil = oeilQuiCadre(camera, boite, { cap, hauteur: sol + OEIL, reculMax: RECUL_AUTO });
      const pieds = [oeil.x, sol, oeil.z];
      repli ??= pieds;
      if (voitLeConcept(oeil, centre, id)) return pieds;
    }
    if (repli) return repli;
    const oeil = oeilQuiCadre(camera, boite, { cap: CAPS_AUTO[0], hauteur: centre.y, reculMax: RECUL_AUTO });
    return [oeil.x, centre.y - OEIL, oeil.z];
  }

  const vueDeLElement = (id) => reperes.vues.find((v) => v.id === `vue_${id}`);

  function piedsDeLElement(id) {
    const vue = vueDeLElement(id);
    if (vue) return piedsDe(vue);
    const boite = emprises.get(id);
    return boite ? piedsQuiVoient(id, boite) : null;
  }

  // « Un élément… » montre toujours l'élément, jamais l'entrée qui porterait le même nom.
  function allerElement(id) {
    const vue = vueDeLElement(id);
    if (vue) {
      prendreVue(vue);
      return true;
    }
    const boite = emprises.get(id);
    if (!boite) return false;
    tenirLeVol(false);
    marche.poser(piedsQuiVoient(id, boite));
    marche.orienterVers(centreDe(boite));
    return true;
  }

  const lieuSous = (x, z, lieux) => lieux.find((id) => contientAPlat(emprises.get(id), x, z));

  // Le sol d'un lieu est le plus bas de ceux qui ont de l'air au-dessus, dans son emprise : le toit d'une lishka n'en est pas un.
  function solAuPoint(x, z, niveau) {
    const lieu = lieuSous(x, z, niveau.lieux);
    if (!lieu && niveau.ailleurs) return solAuPoint(x, z, niveau.ailleurs);
    if (!lieu && !niveau.horsDesLieux) return null;
    const plancher = lieu ? (niveau.planchers?.get(lieu) ?? emprises.get(lieu).min.y) - MARGE_PLANCHER : -Infinity;
    const plafond = Math.min(niveau.plafond, plancher + HAUSSE_MAX);
    const sol = marche.solsLibres(x, z)
      .filter(({ y, libre }) => y >= plancher && y < plafond && libre >= HAUTEUR_LIBRE)
      .reverse()
      .find(({ y }) => tientDebout(x, z, y) && !surUneCrete(x, z, y));
    return sol ? sol.y : null;
  }

  const solPres = (x, z, y, ecart) => marche.solsLibres(x, z).some((sol) => Math.abs(sol.y - y) <= ecart);

  // Le pied porte tout autour du point : ni au ras d'un mur, ni dans le vide d'un mur creux.
  const tientDebout = (x, z, y) => APPUIS.every(([dx, dz]) => solPres(x + dx * PIED, z + dz * PIED, y, MONTEE_APPUI));

  const chuteVers = (x, z, y) => !marche.solsLibres(x, z).some((sol) => sol.y >= y - CHUTE_CRETE);

  function surUneCrete(x, z, y) {
    const tombe = ([dx, dz]) => PORTEES_CRETE.some((portee) => chuteVers(x + dx * portee, z + dz * portee, y));
    return AXES_CRETE.some(([un, autre]) => tombe(un) && tombe(autre));
  }

  // Les pieds au sol du point visé, ou du plus proche qui en ait un ; null si rien ne porte à moins de RAYON_RECALAGE.
  function piedsAuPoint(x, z, niveau) {
    const sol = solAuPoint(x, z, niveau);
    if (sol !== null) return [x, sol, z];
    for (const [dx, dz] of RECALAGES) {
      const proche = solAuPoint(x + dx, z + dz, niveau);
      if (proche !== null) return [x + dx, proche, z + dz];
    }
    return null;
  }

  // On arrive tourné dans le sens du trajet, comme si on avait marché jusque-là.
  function capDuTrajet([x, , z]) {
    const dx = x - camera.position.x, dz = z - camera.position.z;
    return Math.hypot(dx, dz) < ECART_CAP ? null : THREE.MathUtils.radToDeg(Math.atan2(-dz, dx));
  }

  function allerAuPoint(pieds) {
    const cap = capDuTrajet(pieds);
    tenirLeVol(false);
    marche.poser(pieds);
    if (cap !== null) marche.orienterCap({ cap });
  }

  function allerVers(id) {
    const vue = [...reperes.entrees, ...reperes.vues].find((v) => v.id === id);
    if (!vue) return allerElement(id);
    prendreVue(vue);
    return true;
  }

  return { piedsDe, piedsDeLElement, prendreVue, allerElement, allerVers, piedsAuPoint, capDuTrajet, allerAuPoint };
}
