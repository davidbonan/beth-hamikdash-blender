// L'œil qui s'habitue : la lumière cuite est physique, l'exposition monte donc à mesure que le ciel se ferme autour de lui.
// La fermeture qu'il mesure sert aussi à l'air de ciel.js, qui n'a rien à rendre là où le ciel ne se voit plus.
import * as THREE from "three";

const DIRECTIONS = 48;
const RAYONS_PAR_IMAGE = 3;
const PORTEE = 40;
const OUVERTURE_FERMEE = 0.02;
const OUVERTURE_DEHORS = 0.2;
const ADAPTATION_MAX = 5;
const CONSTANTE_DE_TEMPS = 1.2;

// La demi-sphère haute, horizon compris : une salle s'éclaire par sa porte autant que par son ciel.
const directions = Array.from({ length: DIRECTIONS }, (_, i) => {
  const hauteur = (i + 0.5) / DIRECTIONS;
  const azimut = i * Math.PI * (3 - Math.sqrt(5));
  const rayon = Math.sqrt(1 - hauteur * hauteur);
  return new THREE.Vector3(Math.cos(azimut) * rayon, hauteur, Math.sin(azimut) * rayon);
});

export function adaptation(obstacles) {
  const rayon = new THREE.Raycaster();
  rayon.far = PORTEE;
  rayon.firstHitOnly = true;
  const ouverts = new Uint8Array(DIRECTIONS).fill(1);
  let suivante = 0;
  let facteur = 1;
  let fermeture = 0;

  function ouvertureEn(oeil) {
    for (let n = 0; n < RAYONS_PAR_IMAGE; n++, suivante = (suivante + 1) % DIRECTIONS) {
      rayon.set(oeil, directions[suivante]);
      ouverts[suivante] = rayon.intersectObjects(obstacles, false).length === 0 ? 1 : 0;
    }
    return ouverts.reduce((somme, ouvert) => somme + ouvert, 0) / DIRECTIONS;
  }

  function tendreVers(voulu, dt) {
    facteur += (voulu - facteur) * (1 - Math.exp(-dt / CONSTANTE_DE_TEMPS));
    return facteur;
  }

  return {
    get facteur() { return facteur; },
    // 0 à ciel ouvert, 1 sous un toit : relevée à chaque image, quoi que l'exposition en fasse ensuite.
    get fermeture() { return fermeture; },
    mesurer(oeil) {
      fermeture = 1 - THREE.MathUtils.smoothstep(ouvertureEn(oeil), OUVERTURE_FERMEE, OUVERTURE_DEHORS);
      return fermeture;
    },
    accorder: (dt) => tendreVers(ADAPTATION_MAX ** fermeture, dt),
    relacher: (dt) => tendreVers(1, dt),
  };
}
