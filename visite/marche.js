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
const GLISSE_MIN = 0.25;  // part du pas qui longe le mur : en deçà, on le prend de face et l'on s'arrête
// Dans une vis, le regard tourne avec le pas : à 3,4 m/s autour d'un noyau, il faisait 400°/s.
const VIS_PAS = 1.2;      // m/s
const VIS_MARGE = 0.2;    // m : l'épaule ne frotte ni le noyau ni la paroi
const VOL = 9.0;          // m/s en vol libre
// Le pas ne s'établit ni ne s'éteint d'un coup : une vitesse qui bascule de 0 à 3,4
// m/s à l'image près se lit en saccade, et c'est elle qu'on prend pour un manque de
// framerate. 0,09 s, c'est trente centimètres de glissé à l'arrêt — le pied qui se pose.
const REPONSE = 0.09;
const LISSAGE_REGARD = 0.045;

export function marcheur(camera, murs, vis) {
  const BAS = new THREE.Vector3(0, -1, 0);
  const versLeBas = new THREE.Raycaster();
  const versLAvant = new THREE.Raycaster();

  const sonde = new THREE.Vector3();
  const normale = new THREE.Vector3(), glisse = new THREE.Vector3(), ecart = new THREE.Vector3();

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
      const [touche] = versLAvant.intersectObjects(murs, false);
      if (touche) return touche;
    }
    return null;
  }

  let piedsY = 0;
  const avant = new THREE.Vector3(), droite = new THREE.Vector3();
  const HAUT = new THREE.Vector3(0, 1, 0), pas = new THREE.Vector3();
  // Le clavier et le pouce aboutissent tous deux à `voulu` : la marche n'en connaît
  // qu'un, et ses collisions valent donc pour les deux.
  const voulu = new THREE.Vector3(), lisse = new THREE.Vector3();

  // Le Temple ne se laisse pas traverser n'importe où : on monte à l'Ezrat Nashim par
  // les douze degrés du 'Heil, à l'Azara par les quinze marches, et l'autel se contourne.
  // C'est l'architecture, pas un défaut — mais un modèle se regarde aussi d'ailleurs que
  // d'où l'on a le droit de se tenir : le vol libre est là pour ça.
  let vol = false;

  function basculerVol() {
    if (vol && !atterrir()) return false;
    vol = !vol;
    return true;
  }

  function tenirLeVol(enVol) {
    if (vol === enVol) return false;
    vol = enVol;
    return true;
  }

  function vitesseVoulue(manette) {
    const vitesse = (vol ? VOL : PAS) * (manette.course ? COURSE : 1);
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

  function poserLePas(direction, distance) {
    const x = camera.position.x + direction.x * distance, z = camera.position.z + direction.z * distance;
    const sol = solEnjambe(x, z, piedsY, direction);
    if (sol === null) return false;
    piedsY = sol;
    camera.position.set(x, sol + OEIL, z);
    return true;
  }

  function pasLibre(direction, distance) {
    return !murDevant(camera.position, piedsY, direction, distance) && poserLePas(direction, distance);
  }

  // Un mur pris de biais se longe : seule la part du pas qui pousse dedans est perdue.
  function avancerOuGlisser(direction, distance) {
    const mur = murDevant(camera.position, piedsY, direction, distance);
    if (!mur) return poserLePas(direction, distance) || longerLeBord(direction, distance);
    if (!mur.face) return false;
    normale.copy(mur.face.normal).transformDirection(mur.object.matrixWorld).setY(0);
    if (normale.lengthSq() < 1e-4) return false;
    normale.normalize();
    glisse.copy(direction).addScaledVector(normale, -direction.dot(normale));
    const part = glisse.length();
    if (part < GLISSE_MIN) return false;
    glisse.divideScalar(part);
    return pasLibre(glisse, distance * part);
  }

  // Le bord d'un vide n'a pas de face à longer, mais ceux du Temple suivent ses axes : le
  // pas garde celle de ses deux composantes qui reste sur le sol.
  function longerLeBord(direction, distance) {
    const composantes = [[direction.x, 0], [0, direction.z]]
      .sort(([ax, az], [bx, bz]) => Math.abs(bx + bz) - Math.abs(ax + az));
    for (const [x, z] of composantes) {
      const part = Math.abs(x + z);
      if (part < GLISSE_MIN) continue;
      glisse.set(Math.sign(x), 0, Math.sign(z));
      if (pasLibre(glisse, distance * part)) return true;
    }
    return false;
  }

  const rayonDans = (v) => Math.hypot(camera.position.x - v.centre[0], camera.position.z - v.centre[1]);
  const angleDans = (v) => Math.atan2(camera.position.z - v.centre[1], camera.position.x - v.centre[0]);

  // Sur un degré de vis, le sol d'en bas comme le palier d'en haut exclus.
  function visSous() {
    return vis.find((v) => rayonDans(v) < v.rayon && piedsY > v.bas + 0.05 && piedsY < v.haut - 0.05);
  }

  // Au palier d'en haut, la fente laisse le pied au-dessus du puits, face au trou : un pas
  // bloqué l'en écarte vers le dallage plein.
  function sortirDuPuits(distance) {
    const v = vis.find((w) => Math.abs(piedsY - w.haut) < 0.05 && rayonDans(w) < w.rayon + FENTE);
    return v !== undefined && allerEn(v, angleDans(v), rayonDans(v) + distance);
  }

  function allerEn(v, angle, rayon) {
    ecart.set(v.centre[0] + Math.cos(angle) * rayon - camera.position.x, 0,
      v.centre[1] + Math.sin(angle) * rayon - camera.position.z);
    const distance = ecart.length();
    if (distance < 1e-6) return true;
    return pasLibre(ecart.divideScalar(distance), distance);
  }

  // Ce qu'on pousse le long du degré fait le tour du noyau, ce qu'on pousse vers la paroi
  // ou le noyau s'en rapproche, et le regard tourne d'autant : ce qui était devant le reste.
  function tournerDansLaVis(v, distance) {
    const r = rayonDans(v), angle = angleDans(v);
    const tour = (pas.z * Math.cos(angle) - pas.x * Math.sin(angle)) * distance / r;
    const voulu = r + (pas.x * Math.cos(angle) + pas.z * Math.sin(angle)) * distance;
    const exterieur = v.rayon - VIS_MARGE;
    // Vers la paroi, le pas est d'abord tenté tel quel : au dernier degré, il sort sur le dallage.
    const rayons = voulu > exterieur ? [voulu, exterieur] : [Math.max(voulu, v.noyau + VIS_MARGE)];
    // Passé le dernier degré, il n'y a plus de degré où tourner : le pas sort droit vers le palier.
    if (!rayons.some((rayon) => allerEn(v, angle + tour, rayon))) return allerEn(v, angle, r + distance);
    regard.y -= tour;
    capVise.lacet -= tour;
    lisse.applyAxisAngle(HAUT, -tour);
    pas.applyAxisAngle(HAUT, -tour);
    return true;
  }

  function marcher(dt) {
    pas.set(lisse.x, 0, lisse.z);
    const vitesse = pas.length();
    if (vitesse < 0.02) return;
    pas.divideScalar(vitesse);
    // Le pas se découpe : à bas framerate un seul bond franchirait la garde.
    let reste = Math.min((visSous() ? Math.min(vitesse, VIS_PAS) : vitesse) * dt, 1.2);
    while (reste > 1e-4) {
      const distance = Math.min(reste, SOUS_PAS);
      reste -= distance;
      const dansLaVis = visSous();
      const avance = dansLaVis ? tournerDansLaVis(dansLaVis, distance)
        : avancerOuGlisser(pas, distance) || sortirDuPuits(distance);
      if (!avance) {
        lisse.set(0, 0, 0);                          // un mur de face, ou le vide : le pas est refusé,
        return;                                      // et l'élan avec, sinon il pousse contre
      }
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
    basculerVol, tenirLeVol,
    suivreLaCamera() { piedsY = camera.position.y - OEIL; },
    get piedsY() { return piedsY; },
    get vol() { return vol; },
    get elan() { return lisse.lengthSq(); },
  };
}
