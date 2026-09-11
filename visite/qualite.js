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

// `halo` absent = pas de passe du tout, et pas seulement une force nulle : les cinq
// niveaux de flou de la passe sont alloués par son constructeur, qu'elle serve ou non.
export const PROFIL = leger
  ? { dprMax: 1.5, echelleMin: 0.75, profondeurLog: false, grainLeger: true,
      ombres: { taille: 1024, portee: 26, penombre: false }, occlusion: 6,
      halo: { force: 0.16, rayon: 0.6, seuil: 1.6 }, menora: { ombre: false }, figurants: { ombre: false } }
  : { dprMax: 2, echelleMin: 0.7, profondeurLog: true, grainLeger: false,
      ombres: { taille: 2048, portee: 40, penombre: true }, occlusion: 12,
      halo: { force: 0.20, rayon: 0.6, seuil: 1.6 }, menora: { ombre: true }, figurants: { ombre: true } };
