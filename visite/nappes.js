/**
 * Les nappes photographiques, que `matieres.js` projette en triplanaire.
 *
 * Le blockout n'a pas d'UV dépliées à la main, et n'en aura pas : ses volumes sont
 * fusionnés par concept à chaque export, et aucun dépliage ne survivrait à une
 * modification dans Blender. Les nappes se posent donc sur la position de MONDE, comme
 * tout le reste du fichier voisin : rien à déplier, rien à repeindre, et une retouche
 * de la scène ne demande que de réexporter. La seule exception est écrite par le
 * blockout lui-même : les plaques gravées des parois visent par leurs UV l'atlas de
 * `beit_hamikdash_gravures.py`.
 *
 * Deux fichiers par nappe. La couleur porte la rugosité dans son canal alpha : l'alpha
 * du WebP est codé à part et à pleine définition, là où le bleu part en 4:2:0 avec le
 * reste de la chrominance. La normale est en convention OpenGL, vert vers le haut.
 */
import * as THREE from "three";
import { PROFIL, plafonner } from "./qualite.js";

// La moyenne LINÉAIRE de la nappe, et sa rugosité moyenne. La photo est appliquée en
// RAPPORT à elles, jamais en remplacement : Blender garde le dernier mot sur la teinte
// — le meleke reste le meleke, le tekhelet reste bleu — et la photo n'apporte que ce
// qu'elle sait, l'écart d'un point au suivant.
// L'étoffe n'a pas de couleur : la sienne est dictée, pas photographiée.
const JEUX = {
  pierre: { moyenne: [0.3967, 0.2754, 0.1448], rugosite: 0.8485 },
  enduit: { moyenne: [0.3404, 0.2594, 0.1878], rugosite: 0.6211 },
  bois: { moyenne: [0.1528, 0.1284, 0.1008], rugosite: 0.5094 },
  placage: { moyenne: [0.3597, 0.2106, 0.0983], rugosite: 0.5303 },
  ecorce: { moyenne: [0.2461, 0.1935, 0.1513], rugosite: 0.6939 },
  metal: { moyenne: [0.5607, 0.3127, 0.0823], rugosite: 0.1592 },
  marbre: { moyenne: [0.7442, 0.7243, 0.6827], rugosite: 0.1722 },
  etoffe: {},
};
const FINES = {
  meleke: { moyenne: [0.7944, 0.6925, 0.5849], rugosite: 0.8110 },
  dallage: { moyenne: [0.7890, 0.6751, 0.5412], rugosite: 0.6961 },
};
const SANS_COULEUR = new Set(["etoffe"]);
const COTE_DES_FINES = 2048;
// Les noms que `beit_hamikdash_nappes.py` écrit : `c` la couleur, `n` la normale.
const carte = (nom, sorte, cote) => `matieres/${nom}_${sorte}_${cote}.webp`;

export async function nappes() {
  const chargeur = new THREE.TextureLoader();

  const regler = (texture, espace) => {
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.colorSpace = espace;
    // Un dallage vu en enfilade est le cas normal ici, pas l'exception : sans
    // anisotropie sa nappe se réduit en bouillie dès trois mètres.
    texture.anisotropy = 8;
    return texture;
  };

  const jeux = new Map();
  const cote = PROFIL.textures.nappes;
  const aCharger = cote ? [
    ...Object.entries(JEUX).map(([nom, jeu]) => [nom, jeu, cote]),
    ...(PROFIL.textures.fines ? Object.entries(FINES).map(([nom, jeu]) => [nom, jeu, COTE_DES_FINES]) : []),
  ] : [];
  await Promise.all(aCharger.map(async ([nom, jeu, coteDuJeu]) => {
    const [couleur, normale] = await Promise.all([
      SANS_COULEUR.has(nom) ? null : chargeur.loadAsync(carte(nom, "c", coteDuJeu)),
      chargeur.loadAsync(carte(nom, "n", coteDuJeu)),
    ]);
    jeux.set(nom, {
      normale: regler(normale, THREE.NoColorSpace),
      couleur: couleur && regler(couleur, THREE.SRGBColorSpace),
      moyenne: jeu.moyenne && new THREE.Vector3(...jeu.moyenne),
      rugosite: jeu.rugosite,
    });
  }));
  // Le motif tissé des Parokhot, que `beit_hamikdash_parokhet.py` écrit : r = hauteur
  // du bombé, (g, b) = face du tissage qui affleure, alpha = figure. Une seule carte
  // aux dimensions du rideau, lue en coordonnées de rideau et jamais répétée.
  const motif = regler(await chargeur.loadAsync(`matieres/parokhet_${PROFIL.textures.parokhet}.webp`), THREE.NoColorSpace);
  motif.wrapS = motif.wrapT = THREE.ClampToEdgeWrapping;
  jeux.set("parokhet", { motif });
  // Les gravures des parois, que `beit_hamikdash_gravures.py` écrit : neuf tuiles de
  // 1024 — keruv, keruv dressé, timora, fleuron, bouton, cordon, tresse, panneau — lues par les UV
  // de chaque plaque. Gris = hauteur du modelé. La grille est dans `TAILLE_TUILE`
  // (matieres.js) : changer l'une sans l'autre aplatit ou exagère tout le modelé.
  const gravures = regler(await chargeur.loadAsync("matieres/gravures_3072.webp"), THREE.NoColorSpace);
  gravures.wrapS = gravures.wrapT = THREE.ClampToEdgeWrapping;
  await plafonner(gravures, PROFIL.textures.decor);
  jeux.set("gravures", { motif: gravures });
  return jeux;
}
