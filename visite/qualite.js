/**
 * Ce que la machine peut tenir.
 *
 * Un téléphone n'est pas une station de travail plus lente : c'est un GPU à tuiles,
 * qui doit trier ses fragments AVANT de les ombrer. Tout ce qui l'en empêche — des
 * faces des deux côtés, un bruit à trois octaves par pixel — lui coûte bien plus
 * qu'au bureau. Le profil ci-dessous décide donc de ceux-là, et le reste du fichier
 * n'en sait rien.
 *
 * `?qualite=basse` force le profil léger depuis un bureau, `?qualite=minimale` le très
 * léger : c'est ainsi qu'on les vérifie sans téléphone sous la main.
 */
import { lireRetenu, retenir } from "./memoire.js";

const demande = new URLSearchParams(location.search).get("qualite");

const tactile = matchMedia("(hover: none) and (pointer: coarse)").matches;
const coeurs = navigator.hardwareConcurrency || 8;
// Seul Chrome d'Android dit sa mémoire : un iPhone faible ne se reconnaît qu'à l'usage, par `seReplier`, et le téléphone pris pour faible se dément par `seRelever`.
const faible = tactile && (navigator.deviceMemory <= 4 || coeurs <= 4);
const RETENU = "visite-profil-retenu", REPLIS = "visite-profil-replis";
// Une remontée au léger qui a échoué ce nombre de fois ne se retente plus : le profil battrait d'une visite à l'autre.
const REPLIS_MAX = 2;

function niveauDeLaMachine() {
  if (!tactile && coeurs > 4) return "haute";
  const retenu = lireRetenu(RETENU);
  if (retenu === "basse" || retenu === "minimale") return retenu;
  return faible ? "minimale" : "basse";
}

const LOURD = { dprMax: 2, definitionMax: 1.5, echelles: [1, 0.85, 0.7], echelleDepart: 1, grainLeger: false, preProfondeur: true,
  textures: { decor: Infinity, figurants: Infinity }, ecartDetail: 1,
  ombres: { taille: 2048, portee: 40, penombre: true, lointaine: 2048 }, occlusion: 12,
  halo: { force: 0.20, rayon: 0.6, seuil: 1.6 }, rayons: { densite: 0.004, prises: 40 }, sanctuaire: { ombre: true, carte: Infinity }, feux: { ombre: true, carte: Infinity }, figurants: { ombre: true },
  fumee: { pas: 48, octaves: 3 } };

// Un téléphone part à `echelleDepart` et ne monte au-dessus qu'en tenant ses 60 images : chaque iPhone trouve la sienne.
// `preProfondeur` : à 390 × 844 elle coûte plus de géométrie qu'elle n'épargne de pixels (50 → 39 ms mesurés sans elle).
const LEGER = { dprMax: 1.5, definitionMax: 1, echelles: [1.5, 1.25, 1, 0.85, 0.75], echelleDepart: 1, grainLeger: true, preProfondeur: false,
  textures: { decor: 1024, figurants: 512 }, ecartDetail: 1,
  ombres: { taille: 1024, portee: 26, penombre: false, lointaine: 1024 }, occlusion: 6,
  halo: { force: 0.16, rayon: 0.6, seuil: 1.6 }, rayons: { densite: 0.004, prises: 12 }, sanctuaire: { ombre: true, carte: 256 }, feux: { ombre: false, carte: 256 }, figurants: { ombre: false },
  fumee: { pas: 16, octaves: 2 } };

// `halo` et `rayons` nuls = pas de passe du tout, et pas seulement une force nulle : leurs cibles sont allouées par leur constructeur, qu'elles servent ou non.
// `occlusion` nulle épargne aussi la passe de géométrie qu'elle lisait, hors du Kodesh HaKodashim dont la fumée la lit encore.
const TRES_LEGER = { ...LEGER, dprMax: 1, echelles: [1, 0.85, 0.7, 0.55], echelleDepart: 0.7,
  textures: { decor: 512, figurants: 256 }, ecartDetail: 2,
  occlusion: 0, halo: null, rayons: null,
  fumee: { pas: 8, octaves: 1 } };

const PROFILS = { haute: LOURD, basse: LEGER, minimale: TRES_LEGER };
const force = demande in PROFILS;
const niveau = force ? demande : niveauDeLaMachine();

export const PROFIL = PROFILS[niveau];

const replis = () => Number(lireRetenu(REPLIS) ?? 0);
let bascule = false;

function basculerVers(voulu) {
  bascule = true;
  retenir(RETENU, voulu);
}

// Le profil léger qui n'a pas tenu — contexte perdu, rythme lent au dernier palier — part au très léger à la visite suivante.
export function seReplier() {
  if (force || bascule || niveau !== "basse") return;
  retenir(REPLIS, String(replis() + 1));
  basculerVers("minimale");
}

// Le très léger tenu sans peine à son premier palier repart au léger à la visite suivante.
export function seRelever() {
  if (force || bascule || niveau !== "minimale" || replis() >= REPLIS_MAX) return;
  basculerVers("basse");
}

// La mémoire GPU est ce qui fait perdre son contexte WebGL à un iPhone : au-delà de `cote`, une texture pèse sans rien montrer de plus sur un petit écran.
// Safari prémultiplie tout ImageBitmap : une carte qui écrit sous un alpha nul, comme la parokhet, ne passe pas par ici.
export async function plafonner(texture, cote) {
  const { image } = texture;
  const plus = Math.max(image.width, image.height);
  if (plus <= cote) return;
  const k = cote / plus;
  texture.image = await createImageBitmap(image, {
    resizeWidth: Math.round(image.width * k), resizeHeight: Math.round(image.height * k), resizeQuality: "high",
    imageOrientation: texture.flipY ? "flipY" : "none", premultiplyAlpha: "none", colorSpaceConversion: "none",
  });
  texture.flipY = false;
  image.close?.();
  texture.needsUpdate = true;
}
