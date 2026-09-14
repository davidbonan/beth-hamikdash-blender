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
 * Deux cartes : la proche, au centimètre, pour les bords nets qu'un soleil rasant étire en escalier ; la large pour le reste.
 */
import * as THREE from "three";
import { PROFIL } from "./qualite.js";
import { SOLEIL } from "./ciel.js";

// La fenêtre suit le visiteur ; ce couple-là borne ce qui peut porter une ombre
// AU-DESSUS de lui, et la façade fait cinquante mètres.
const PROFONDEUR = { pres: 1, loin: 260 };
// Un demi-degré, en radians : le diamètre apparent du soleil, d'où sort toute la
// largeur de pénombre de ce fichier.
const DIAMETRE_SOLEIL = 0.0093;
// Assez large pour contenir la pénombre la plus grande que la fenêtre puisse produire,
// assez serré pour que douze prises la couvrent sans trous.
const RECHERCHE = 12.0;
const RECHERCHE_PROCHE = 16.0;
// Le soleil est posé loin devant la caméra, pas à sa hauteur : il faut que ce qui
// surplombe la fenêtre — la façade fait cinquante mètres — tienne entre `pres` et `loin`.
const RECUL_SOLEIL = 200;

const metresParTexel = (portee) => 2 * portee / PROFIL.ombres.taille;
// De l'écart de profondeur lu dans la carte (0 à 1 sur toute sa course) au rayon de filtrage en texels.
const penombre = (portee) => (PROFONDEUR.loin - PROFONDEUR.pres) * DIAMETRE_SOLEIL / metresParTexel(portee);

function cascade(lumiere, portee) {
  lumiere.castShadow = true;
  // La carte n'est plus refaite à chaque image : `suivre` la redemande quand la
  // fenêtre a assez bougé pour que ça se voie.
  lumiere.shadow.autoUpdate = false;
  lumiere.shadow.mapSize.set(PROFIL.ombres.taille, PROFIL.ombres.taille);
  lumiere.shadow.bias = -0.0002;
  lumiere.shadow.normalBias = metresParTexel(portee);
  Object.assign(lumiere.shadow.camera, { near: PROFONDEUR.pres, far: PROFONDEUR.loin,
    left: -portee, right: portee, top: portee, bottom: -portee });
  return { lumiere, portee, ancre: new THREE.Vector3(Infinity, Infinity, Infinity) };
}

const nombre = (x) => x.toFixed(4);

function nuanceur(proche, large) {
  const limite = RECHERCHE_PROCHE * metresParTexel(proche);
  return /* glsl */`
#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 1
float alea2(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

// x : part de lumière ; y : rayon de pénombre en texels, négatif si rien ne bouche le soleil.
vec2 penombreSoleil(sampler2D carte, vec4 coord, float recherche, float penombre){
  if (coord.z > 1.0 || any(lessThan(coord.xy, vec2(0.0))) || any(greaterThan(coord.xy, vec2(1.0))))
    return vec2(1.0, -1.0);
  vec2 texel = vec2(1.0 / ${nombre(PROFIL.ombres.taille)});
  float tour = alea2(gl_FragCoord.xy) * 6.28318;
  float somme = 0.0, compte = 0.0;
  for (int i = 0; i < 12; i++) {
    float a = tour + float(i) * 2.39996;                 // l'angle d'or, comme l'occlusion
    vec2 o = vec2(cos(a), sin(a)) * sqrt((float(i) + 0.5) / 12.0);
    float d = unpackRGBAToDepth(texture2D(carte, coord.xy + o * recherche * texel));
    if (d < coord.z) { somme += d; compte += 1.0; }
  }
  if (compte < 0.5) return vec2(1.0, -1.0);

  // Un texel de rayon au minimum : sous cette taille il n'y a plus de pénombre à
  // filtrer, seulement le crénelage de la carte elle-même.
  float large = clamp((coord.z - somme / compte) * penombre, 1.0, recherche);
  float ombre = 0.0;
  for (int i = 0; i < 12; i++) {
    float a = tour + float(i) * 2.39996;
    vec2 o = vec2(cos(a), sin(a)) * sqrt((float(i) + 0.5) / 12.0);
    ombre += texture2DCompare(carte, coord.xy + o * large * texel, coord.z);
  }
  return vec2(ombre / 12.0, large);
}

vec4 coordSoleil(vec4 c, float biais){
  c.xyz /= c.w;
  c.z += biais;
  return c;
}

float ombreSoleil(){
  vec4 cProche = coordSoleil(vDirectionalShadowCoord[0], directionalLightShadows[0].shadowBias);
  vec2 bord = smoothstep(0.0, 0.1, cProche.xy) * smoothstep(1.0, 0.9, cProche.xy);
  float fenetre = bord.x * bord.y;
  vec2 proche = fenetre > 0.0
    ? penombreSoleil(directionalShadowMap[0], cProche, ${nombre(RECHERCHE_PROCHE)}, ${nombre(penombre(proche))})
    : vec2(1.0, -1.0);
  if (fenetre >= 1.0 && proche.y > 0.0 && proche.y < ${nombre(RECHERCHE_PROCHE / 2)}) return proche.x;

  vec2 loin = penombreSoleil(directionalShadowMap[1], coordSoleil(vDirectionalShadowCoord[1], directionalLightShadows[1].shadowBias), ${nombre(RECHERCHE)}, ${nombre(penombre(large))});
  // Une pénombre plus large que la recherche proche n'y tient pas : la carte large la rend, sans escalier à cette largeur.
  float rayon = proche.y > 0.0 ? proche.y * ${nombre(metresParTexel(proche))} : max(loin.y, 0.0) * ${nombre(metresParTexel(large))};
  float poids = fenetre * (1.0 - smoothstep(${nombre(limite / 2)}, ${nombre(limite)}, rayon));
  return mix(loin.x, proche.x, poids);
}
#endif
`;
}

const LECTURE_THREE = "getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] )";
const DECLARATION_THREE = "DirectionalLight directionalLight;";

function brancherNuanceur(proche, large) {
  const lumieres = THREE.ShaderChunk.lights_fragment_begin;
  if (!lumieres.includes(LECTURE_THREE) || !lumieres.includes(DECLARATION_THREE))
    throw new Error("three a changé sa lecture des ombres directionnelles : cascades perdues");
  THREE.ShaderChunk.shadowmap_pars_fragment += nuanceur(proche, large);
  THREE.ShaderChunk.lights_fragment_begin = lumieres
    .replace(DECLARATION_THREE, `${DECLARATION_THREE}
      #if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 1
      float ombresSoleil[ NUM_DIR_LIGHT_SHADOWS ];
      ombresSoleil[ 0 ] = receiveShadow ? ombreSoleil() : 1.0;
      ombresSoleil[ 1 ] = 1.0;
      #endif`)
    .replace(LECTURE_THREE, "ombresSoleil[ i ]");
}

/** Les cartes d'ombre du soleil, de la plus fine à la plus large, lumières à ajouter à la scène. */
export function poserCascades(soleil) {
  const { portee, proche } = PROFIL.ombres;
  if (!proche) return [cascade(soleil, portee)];
  brancherNuanceur(proche, portee);
  // N'éclaire rien : elle ne sert qu'à porter la carte large, que lit `ombreSoleil`.
  const large = new THREE.DirectionalLight(0x000000, 0);
  return [cascade(soleil, proche), cascade(large, portee)];
}

// La refaire coûte une passe de géométrie entière : la carte suit le visiteur par sauts
// d'un dixième de sa fenêtre, et garde d'ici là la matrice qui va avec.
export function suivre(cascades, position) {
  for (const c of cascades) {
    if (position.distanceToSquared(c.ancre) < (c.portee / 10) ** 2) continue;
    c.ancre.copy(position);
    c.lumiere.target.position.copy(position);
    c.lumiere.position.copy(position).addScaledVector(SOLEIL, RECUL_SOLEIL);
    c.lumiere.target.updateMatrixWorld();
    c.lumiere.shadow.needsUpdate = true;
  }
}

export function redemander(cascades) {
  for (const c of cascades) c.lumiere.shadow.needsUpdate = true;
}
