/**
 * Ce que la machine peut tenir.
 *
 * Un téléphone n'est pas une station de travail plus lente : c'est un GPU à tuiles,
 * qui doit trier ses fragments AVANT de les ombrer. Tout ce qui l'en empêche — des
 * faces des deux côtés, un bruit à trois octaves par pixel — lui coûte bien plus
 * qu'au bureau. Le profil ci-dessous décide donc de ceux-là, et le reste du fichier
 * n'en sait rien.
 *
 * `?qualite=basse` force le profil léger depuis un bureau : c'est ainsi qu'on le
 * vérifie sans téléphone sous la main.
 */
const demande = new URLSearchParams(location.search).get("qualite");

const tactile = matchMedia("(hover: none) and (pointer: coarse)").matches;

const leger = demande === "basse"
  || (demande !== "haute" && (tactile || (navigator.hardwareConcurrency || 8) <= 4));

// Un téléphone part à `echelleDepart` et ne monte au-dessus qu'en tenant ses 60 images : chaque iPhone trouve la sienne.
// `preProfondeur` : à 390 × 844 elle coûte plus de géométrie qu'elle n'épargne de pixels (50 → 39 ms mesurés sans elle).
// `halo` absent = pas de passe du tout, et pas seulement une force nulle : les cinq
// niveaux de flou de la passe sont alloués par son constructeur, qu'elle serve ou non.
export const PROFIL = leger
  ? { dprMax: 1.5, definitionMax: 1, echelles: [1.5, 1.25, 1, 0.85, 0.75], echelleDepart: 1, grainLeger: true, preProfondeur: false,
      textures: { decor: 1024, figurants: 512 },
      ombres: { taille: 1024, portee: 26, penombre: false }, occlusion: 6,
      halo: { force: 0.16, rayon: 0.6, seuil: 1.6 }, sanctuaire: { ombre: true, carte: 256 }, feux: { ombre: false, carte: 256 }, figurants: { ombre: false },
      fumee: { pas: 16, octaves: 2 } }
  : { dprMax: 2, definitionMax: 1.5, echelles: [1, 0.85, 0.7], echelleDepart: 1, grainLeger: false, preProfondeur: true,
      textures: { decor: Infinity, figurants: Infinity },
      ombres: { taille: 2048, portee: 40, penombre: true }, occlusion: 12,
      halo: { force: 0.20, rayon: 0.6, seuil: 1.6 }, sanctuaire: { ombre: true, carte: Infinity }, feux: { ombre: true, carte: Infinity }, figurants: { ombre: true },
      fumee: { pas: 48, octaves: 3 } };

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
