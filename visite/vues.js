// Les vues : où poser le visiteur, et vers quoi le tourner, pour une entrée, une vue de repères ou un élément.
import * as THREE from "three";
import { oeilQuiCadre, unirEmprises } from "./cadrage.js";
import { OEIL } from "./marche.js";

const RECUL_AUTO = 60;
// Le premier côté d'où l'élément se voit sans mur devant ; l'est d'abord, l'axe du parcours.
const CAPS_AUTO = [180, 0, 90, 270];
const centreDe = (boite) => boite.getCenter(new THREE.Vector3());

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

  // « Un élément… » montre toujours l'élément, jamais l'entrée qui porterait le même nom.
  function allerElement(id) {
    const vue = reperes.vues.find((v) => v.id === `vue_${id}`);
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

  function allerVers(id) {
    const vue = [...reperes.entrees, ...reperes.vues].find((v) => v.id === id);
    if (!vue) return allerElement(id);
    prendreVue(vue);
    return true;
  }

  return { piedsDe, prendreVue, allerElement, allerVers };
}
