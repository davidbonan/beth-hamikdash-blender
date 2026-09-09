/**
 * Les nappes photographiques, que `matieres.js` projette en triplanaire.
 *
 * Le blockout n'a pas d'UV — `export_texcoords=False` — et n'en aura pas : ses volumes
 * sont fusionnés par concept à chaque export, et aucun dépliage ne survivrait à une
 * modification dans Blender. Les nappes se posent donc sur la position de MONDE, comme
 * tout le reste du fichier voisin : rien à déplier, rien à repeindre, et une retouche
 * de la scène ne demande que de réexporter.
 *
 * Deux fichiers par nappe. La couleur porte la rugosité dans son canal alpha : l'alpha
 * du WebP est codé à part et à pleine définition, là où le bleu part en 4:2:0 avec le
 * reste de la chrominance. La normale est en convention OpenGL, vert vers le haut.
 */
import * as THREE from "three";
import { PROFIL } from "./qualite.js";

// La moyenne LINÉAIRE de la nappe, et sa rugosité moyenne. La photo est appliquée en
// RAPPORT à elles, jamais en remplacement : Blender garde le dernier mot sur la teinte
// — le meleke reste le meleke, le tekhelet reste bleu — et la photo n'apporte que ce
// qu'elle sait, l'écart d'un point au suivant.
// L'étoffe n'a pas de couleur : la sienne est dictée, pas photographiée.
const JEUX = {
  pierre: { moyenne: [0.3967, 0.2754, 0.1448], rugosite: 0.8485 },
  enduit: { moyenne: [0.3404, 0.2594, 0.1878], rugosite: 0.6211 },
  bois: { moyenne: [0.3205, 0.1855, 0.0867], rugosite: 0.9154 },
  metal: { moyenne: [0.5607, 0.3127, 0.0823], rugosite: 0.1592 },
  etoffe: {},
};

export async function nappes() {
  const { taille, anisotropie } = PROFIL.nappes;
  const chargeur = new THREE.TextureLoader().setPath("./matieres/");

  const regler = (texture, espace) => {
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.colorSpace = espace;
    // Un dallage vu en enfilade est le cas normal ici, pas l'exception : sans
    // anisotropie sa nappe se réduit en bouillie dès trois mètres.
    texture.anisotropy = anisotropie;
    return texture;
  };

  const jeux = new Map();
  await Promise.all(Object.entries(JEUX).map(async ([nom, jeu]) => {
    const [couleur, normale] = await Promise.all([
      jeu.moyenne ? chargeur.loadAsync(`${nom}_c_${taille}.webp`) : null,
      chargeur.loadAsync(`${nom}_n_${taille}.webp`),
    ]);
    jeux.set(nom, {
      normale: regler(normale, THREE.NoColorSpace),
      couleur: couleur && regler(couleur, THREE.SRGBColorSpace),
      moyenne: jeu.moyenne && new THREE.Vector3(...jeu.moyenne),
      rugosite: jeu.rugosite,
    });
  }));
  return jeux;
}
