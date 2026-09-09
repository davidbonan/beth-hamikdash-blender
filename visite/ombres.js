/**
 * Les ombres portées, et leur pénombre.
 *
 * Une carte d'ombre lue au PCF donne la même dureté partout : le pied d'une colonne et
 * la crête d'un mur à quarante mètres y ont un bord aussi net l'un que l'autre, et c'est
 * ce bord constant qui se lit en « carte d'ombre » plutôt qu'en ombre. Le soleil n'est
 * pas un point : il fait un demi-degré, et l'ombre qu'il porte s'élargit d'environ un
 * centimètre par mètre séparant l'objet de ce qui le reçoit. Un contact reste donc
 * tranchant, l'ombre d'une façade de cinquante mètres sur le dallage ne l'est plus.
 *
 * Le calcul est en deux temps, la méthode ordinaire : on cherche d'abord ce qui bouche
 * le soleil dans un voisinage, on en tire la distance moyenne, et c'est elle qui donne
 * le rayon du filtrage. Les douze prises de chaque temps tournent d'un angle tiré du
 * pixel : le bord de pénombre se dithere au lieu de se strier, et l'étalonnage qui
 * termine la chaîne pose de toute façon son grain par-dessus.
 *
 * three n'offre pas de point d'entrée pour ça. On renomme donc SA fonction dans son
 * propre morceau de nuanceur et on définit la nôtre sous le nom qu'appelle le reste —
 * `assemblage` échoue bruyamment si trois change ce nom, plutôt que de rendre en dur.
 */
import * as THREE from "three";
import { PROFIL } from "./qualite.js";

// La fenêtre suit le visiteur ; ce couple-là borne ce qui peut porter une ombre
// AU-DESSUS de lui, et la façade fait cinquante mètres.
const PROFONDEUR = { pres: 1, loin: 260 };
// Un demi-degré, en radians : le diamètre apparent du soleil, d'où sort toute la
// largeur de pénombre de ce fichier.
const DIAMETRE_SOLEIL = 0.0093;
// Assez large pour contenir la pénombre la plus grande que la fenêtre puisse produire,
// assez serré pour que douze prises la couvrent sans trous.
const RECHERCHE = 12.0;

export function regler(soleil) {
  soleil.castShadow = true;
  // La carte n'est plus refaite à chaque image : `suivreSoleil` la redemande quand la
  // fenêtre a assez bougé pour que ça se voie.
  soleil.shadow.autoUpdate = false;
  soleil.shadow.mapSize.set(PROFIL.ombres.taille, PROFIL.ombres.taille);
  soleil.shadow.bias = -0.0002;
  soleil.shadow.normalBias = 0.04;
  // Fenêtre serrée : 2048 texels sur 80 m donnent 4 cm de résolution — assez fin pour
  // l'arête d'une assise, ce qu'une fenêtre couvrant tout le Har HaBayit ne donnerait
  // jamais. Le profil léger rétrécit la fenêtre en même temps que la carte, pour garder
  // cette résolution-là.
  const portee = PROFIL.ombres.portee;
  Object.assign(soleil.shadow.camera, { near: PROFONDEUR.pres, far: PROFONDEUR.loin,
    left: -portee, right: portee, top: portee, bottom: -portee });
}

// De l'écart de profondeur lu dans la carte (0 à 1 sur toute sa course) au rayon de
// filtrage en texels. Les deux bouts du calcul sont ici : la course en mètres, et ce
// que vaut un texel en mètres.
const metresParTexel = 2 * PROFIL.ombres.portee / PROFIL.ombres.taille;
const PENOMBRE = (PROFONDEUR.loin - PROFONDEUR.pres) * DIAMETRE_SOLEIL / metresParTexel;

const PCSS = /* glsl */`
float alea2(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

float getShadow(sampler2D carte, vec2 taille, float biais, float rayon, vec4 coord){
  coord.xyz /= coord.w;
  coord.z += biais;
  if (coord.z > 1.0 || any(lessThan(coord.xy, vec2(0.0))) || any(greaterThan(coord.xy, vec2(1.0))))
    return 1.0;

  vec2 texel = 1.0 / taille;
  float tour = alea2(gl_FragCoord.xy) * 6.28318;
  float somme = 0.0, compte = 0.0;
  for (int i = 0; i < 12; i++) {
    float a = tour + float(i) * 2.39996;                 // l'angle d'or, comme l'occlusion
    vec2 o = vec2(cos(a), sin(a)) * sqrt((float(i) + 0.5) / 12.0);
    float d = unpackRGBAToDepth(texture2D(carte, coord.xy + o * ${RECHERCHE.toFixed(1)} * texel));
    if (d < coord.z) { somme += d; compte += 1.0; }
  }
  if (compte < 0.5) return 1.0;                          // rien devant : plein soleil

  // Un texel de rayon au minimum : sous cette taille il n'y a plus de pénombre à
  // filtrer, seulement le crénelage de la carte elle-même.
  float large = clamp((coord.z - somme / compte) * ${PENOMBRE.toFixed(2)}, 1.0, ${RECHERCHE.toFixed(1)});
  float ombre = 0.0;
  for (int i = 0; i < 12; i++) {
    float a = tour + float(i) * 2.39996;
    vec2 o = vec2(cos(a), sin(a)) * sqrt((float(i) + 0.5) / 12.0);
    ombre += texture2DCompare(carte, coord.xy + o * large * texel, coord.z);
  }
  return ombre / 12.0;
}
`;

/** Le morceau de three, sa fonction mise de côté, la nôtre à sa place. */
export function assemblage() {
  const morceau = THREE.ShaderChunk.shadowmap_pars_fragment;
  const ecarte = morceau.replace("float getShadow(", "float getShadowDur(");
  if (ecarte === morceau) throw new Error("three a renommé getShadow : pénombre perdue");
  return ecarte + PCSS;
}
