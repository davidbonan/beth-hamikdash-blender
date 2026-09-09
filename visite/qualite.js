/**
 * Ce que la machine peut tenir.
 *
 * Un téléphone n'est pas une station de travail plus lente : c'est un GPU à tuiles,
 * qui doit trier ses fragments AVANT de les ombrer. Tout ce qui l'en empêche — une
 * profondeur écrite par le nuanceur, des faces des deux côtés, un bruit à trois
 * octaves par pixel — lui coûte bien plus qu'au bureau. Le profil ci-dessous décide
 * donc de ceux-là, et le reste du fichier n'en sait rien.
 *
 * `?qualite=basse` force le profil léger depuis un bureau : c'est ainsi qu'on le
 * vérifie sans téléphone sous la main.
 */
const demande = new URLSearchParams(location.search).get("qualite");

const tactile = matchMedia("(hover: none) and (pointer: coarse)").matches;

const leger = demande === "basse"
  || (demande !== "haute" && (tactile || (navigator.hardwareConcurrency || 8) <= 4));

// Les nappes sont servies en deux définitions : 1,8 Mo contre 428 ko, et surtout
// 5,6 Mo de mémoire vidéo par carte contre 1,4. `macro` est la seconde échelle de
// couleur, celle qui casse la répétition du carreau — trois prises de texture de plus.
export const PROFIL = leger
  ? { dprMax: 1.5, echelleMin: 0.55, profondeurLog: false, grainLeger: true,
      ombres: { taille: 1024, portee: 26, doux: false }, occlusion: 6,
      nappes: { taille: 512, anisotropie: 4, macro: false } }
  : { dprMax: 2, echelleMin: 0.7, profondeurLog: true, grainLeger: false,
      ombres: { taille: 2048, portee: 40, doux: true }, occlusion: 12,
      nappes: { taille: 1024, anisotropie: 8, macro: true } };
