// Le marcheur : ses pieds sur le dallage, ses collisions, son vol libre, et la tête qu'il tourne.
import * as THREE from "three";
import { PAS, SOUS_PAS } from "./trajet.js";

export const AMA = 0.48;
export const OEIL = 1.55;        // yeux d'un homme de l'époque (1,65 m), sous les 1,75 m des silhouettes
// Les degrés du 'Heil, de Nikanor et de l'Oulam font tous 1/2 ama — 0,24 m de haut
// comme de giron. La garde se place juste au-dessus de MONTEE et ne porte qu'à une
// peau : la première contremarche qu'elle voit est deux girons plus loin, jamais
// celle qu'on s'apprête à gravir.
// MONTEE suit la plus haute marche du parcours : celle d'une ama qui porte le Doukhan
// (Middot 2:6, selon R. Eliézer ben Yaakov), sur toute la largeur de la cour. À 0,28 m, l'Azara restait hors d'atteinte.
const MONTEE = AMA + 0.02;
const CHUTE = 0.60;        // au-delà, il n'y a pas de sol : le pas est refusé
const FENTE = 0.25;        // un pied : le vide plus étroit que lui s'enjambe sans y penser
// Ce qu'un repère d'entrée peut manquer son sol, en plus ou en moins. Il donne sa
// hauteur à la main, et la fenêtre de la marche est celle d'un pas : trois des neuf
// étaient 2,5 amot au-dessus de leur dallage, et on s'y posait en l'air.
const APLOMB = 1.5;
const COURSE = 2.4;       // multiplicateur
const GARDE = 0.06;       // peau du rayon de garde, devant le marcheur
const VOL = 9.0;          // m/s en vol libre
// Le pas ne s'établit ni ne s'éteint d'un coup : une vitesse qui bascule de 0 à 3,4
// m/s à l'image près se lit en saccade, et c'est elle qu'on prend pour un manque de
// framerate. 0,09 s, c'est trente centimètres de glissé à l'arrêt — le pied qui se pose.
const REPONSE = 0.09;
const LISSAGE_REGARD = 0.045;

export function marcheur(camera, murs) {
  const BAS = new THREE.Vector3(0, -1, 0);
  const versLeBas = new THREE.Raycaster();
  const versLAvant = new THREE.Raycaster();

  const sonde = new THREE.Vector3();

  function solSous(origine, portee) {
    versLeBas.set(origine, BAS);
    versLeBas.far = portee;
    // Une face tournée vers le bas — le dessous d'un mur posé sur la dalle — n'est pas
    // un sol : sans ce filtre on marche à l'intérieur des murs.
    for (const t of versLeBas.intersectObjects(murs, false)) {
      if (!t.face || t.face.normal.y > 0.25) return t.point.y;
    }
    return null;
  }

  function solEn(x, z, piedsY) {
    return solSous(sonde.set(x, piedsY + MONTEE, z), MONTEE + CHUTE);
  }

  // Le pas qui arrive sur du vide regarde un pied plus loin dans le même sens : une fente
  // plus étroite qu'un pied ne fait tomber personne. Un quart d'ama d'air sépare la tête
  // du kevesh de l'autel (Zeva'him 62b), un cheveu le petit kevesh du sovev — et le rayon
  // de sol, tiré en un point, y tombait à chaque fois : l'autel ne se montait pas.
  function solEnjambe(x, z, piedsY, direction) {
    return solEn(x, z, piedsY) ?? solEn(x + direction.x * FENTE, z + direction.z * FENTE, piedsY);
  }

  // Le rayon de garde part AU-DESSUS de ce qui est franchissable. Plus bas, il heurtait
  // la deuxième marche avant qu'on ait gravi la première : les degrés du 'Heil et de
  // Nikanor font 1/2 ama — 0,24 m — et un corps de 0,38 m de rayon en couvre deux. Tout
  // ce qui est sous MONTEE se monte ; la garde ne juge donc que ce qui est au-dessus,
  // et sa portée se limite à une peau, pas au rayon du corps.
  function murDevant(depuis, piedsY, direction, distance) {
    versLAvant.far = distance + GARDE;
    for (const hauteur of [MONTEE + 0.02, 1.55]) {
      versLAvant.set(new THREE.Vector3(depuis.x, piedsY + hauteur, depuis.z), direction);
      if (versLAvant.intersectObjects(murs, false).length) return true;
    }
    return false;
  }

  let piedsY = 0;
  const avant = new THREE.Vector3(), droite = new THREE.Vector3();
  const HAUT = new THREE.Vector3(0, 1, 0), pas = new THREE.Vector3();
  // Le clavier, le pouce et le pilote automatique aboutissent tous à `voulu` : la marche
  // n'en connaît qu'un, et ses collisions valent donc pour les trois.
  const voulu = new THREE.Vector3(), lisse = new THREE.Vector3();
  let cible = null;

  // Le Temple ne se laisse pas traverser n'importe où : on monte à l'Ezrat Nashim par
  // les douze degrés du 'Heil, à l'Azara par les quinze marches, et l'autel se contourne.
  // C'est l'architecture, pas un défaut — mais un modèle se regarde aussi d'ailleurs que
  // d'où l'on a le droit de se tenir : le vol libre est là pour ça.
  let vol = false;

  function basculerVol() {
    if (vol && !atterrir()) return false;
    vol = !vol;
    cible = null;
    return true;
  }

  function tenirLeVol(enVol) {
    if (vol === enVol) return false;
    vol = enVol;
    cible = null;
    return true;
  }

  // Le pilote automatique n'ouvre aucun passage : il pousse le marcheur vers le point
  // visé avec la même commande qu'un pouce, donc les mêmes murs l'arrêtent. Un point
  // qui n'a pas de sol sous lui — un mur, une corniche — ne se demande pas.
  function seRendreVers(point) {
    if (vol) { cible = point.clone(); return; }
    const sol = solEn(point.x, point.z, point.y);
    if (sol !== null) cible = new THREE.Vector3(point.x, sol, point.z);
  }

  function vitesseVoulue(manette) {
    const vitesse = (vol ? VOL : PAS) * (manette.course ? COURSE : 1);
    const manuel = Math.abs(manette.long) + Math.abs(manette.lat) + Math.abs(manette.vert);
    if (manuel > 0.02) cible = null;
    if (cible) {
      voulu.copy(cible).sub(camera.position);
      if (!vol) voulu.y = 0;
      if (voulu.lengthSq() < (vol ? 1.4 : 0.36)) { cible = null; return voulu.set(0, 0, 0); }
      return voulu.normalize().multiplyScalar(vitesse);
    }
    camera.getWorldDirection(avant);
    if (!vol) avant.y = 0;
    avant.normalize();
    droite.crossVectors(avant, HAUT).normalize();
    voulu.set(0, 0, 0).addScaledVector(avant, manette.long).addScaledVector(droite, manette.lat);
    if (vol) voulu.addScaledVector(HAUT, manette.vert);
    // La diagonale ne va pas plus vite que le droit devant, mais un pouce à mi-course
    // marche à mi-vitesse : c'est la longueur qui est bridée, pas normalisée.
    const force = Math.min(voulu.length(), 1);
    return force < 1e-3 ? voulu.set(0, 0, 0) : voulu.normalize().multiplyScalar(vitesse * force);
  }

  function marcher(dt) {
    pas.set(lisse.x, 0, lisse.z);
    const vitesse = pas.length();
    if (vitesse < 0.02) return;
    pas.divideScalar(vitesse);
    // Le pas se découpe : à bas framerate un seul bond franchirait la garde.
    let reste = Math.min(vitesse * dt, 1.2);
    while (reste > 1e-4) {
      const distance = Math.min(reste, SOUS_PAS);
      reste -= distance;
      const x = camera.position.x + pas.x * distance, z = camera.position.z + pas.z * distance;
      const sol = murDevant(camera.position, piedsY, pas, distance) ? null : solEnjambe(x, z, piedsY, pas);
      if (sol === null) {                            // un mur, ou le vide : le pas est refusé
        lisse.set(0, 0, 0);                          // et l'élan avec, sinon il pousse contre
        cible = null;
        return;
      }
      piedsY = sol;
      camera.position.set(x, sol + OEIL, z);
    }
  }

  function avancer(dt, manette) {
    vitesseVoulue(manette);
    lisse.lerp(voulu, 1 - Math.exp(-dt / REPONSE));
    if (lisse.lengthSq() < 4e-4) {
      lisse.set(0, 0, 0);
      return;
    }
    if (!vol) return marcher(dt);
    camera.position.addScaledVector(lisse, dt);
    piedsY = camera.position.y - OEIL;
  }

  function poser([x, y, z]) {
    const sol = vol ? null : solSous(sonde.set(x, y + APLOMB, z), APLOMB * 2);
    piedsY = sol === null ? y : sol;
    camera.position.set(x, piedsY + OEIL, z);
    lisse.set(0, 0, 0);
    cible = null;
  }

  // Cap en degrés dans le repère de la fiche : 0 = est, 180 = ouest, l'axe du parcours du
  // Cohen Gadol. Le nord de Blender devient -Z une fois passé en Y-haut.
  function orienterCap({ cap, tangage = 0 }) {
    const a = THREE.MathUtils.degToRad(cap);
    const t = THREE.MathUtils.degToRad(tangage);
    const { x, y, z } = camera.position;
    camera.lookAt(x + Math.cos(a) * 10, y + Math.tan(t) * 10, z - Math.sin(a) * 10);
    accorderRegard();
  }

  function orienterVers(point) {
    camera.lookAt(point);
    accorderRegard();
  }

  function atterrir() {
    const { x, y, z } = camera.position;
    // Une marche au-dessus de l'œil : en rasant la dalle en vol, il a pu passer dessous.
    const sol = solSous(sonde.set(x, y + MONTEE, z), Infinity);
    if (sol === null) return false;
    piedsY = sol;
    camera.position.y = sol + OEIL;
    return true;
  }

  // Le regard suit le glissé, pas le curseur : bouton relâché, la souris redevient
  // libre pour la barre du haut et la fiche. Il rejoint sa consigne au lieu d'y sauter :
  // à 45 ms le retard ne se sent pas, et le tremblement du doigt ne passe plus.
  const TANGAGE_MAX = Math.PI / 2 - 0.02;
  const regard = new THREE.Euler(0, 0, 0, "YXZ");
  const capVise = { lacet: 0, tangage: 0 };

  function tourner(dLacet, dTangage) {
    capVise.lacet -= dLacet;
    capVise.tangage = THREE.MathUtils.clamp(capVise.tangage - dTangage, -TANGAGE_MAX, TANGAGE_MAX);
  }

  // Après un `lookAt`, la consigne est ce que la caméra montre : sans ça le lissage
  // ramènerait aussitôt le regard là où il était avant le déplacement.
  function accorderRegard() {
    regard.setFromQuaternion(camera.quaternion);
    regard.z = 0;
    capVise.lacet = regard.y;
    capVise.tangage = regard.x;
  }

  function lisserRegard(dt) {
    const k = 1 - Math.exp(-dt / LISSAGE_REGARD);
    regard.y += (capVise.lacet - regard.y) * k;
    regard.x += (capVise.tangage - regard.x) * k;
    regard.z = 0;
    camera.quaternion.setFromEuler(regard);
  }

  return {
    solSous, solEn, avancer, poser, orienterCap, orienterVers, tourner, accorderRegard, lisserRegard,
    basculerVol, tenirLeVol, seRendreVers,
    suivreLaCamera() { piedsY = camera.position.y - OEIL; },
    get piedsY() { return piedsY; },
    get vol() { return vol; },
    get elan() { return lisse.lengthSq(); },
  };
}
