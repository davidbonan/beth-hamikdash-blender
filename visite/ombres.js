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
 * Deux cartes font cette largeur. La fenêtre qui suit le visiteur, à quatre centimètres
 * le texel, donne le bord net ; la carte de tout le Har HaBayit, tracée une fois par
 * moment, donne le bord large, et dit à quelle distance se tient ce qui bouche le soleil.
 * C'est cette distance qui fait passer de l'une à l'autre. Les deux se lisent sur un carré
 * de texels pondérés en tente, ancré dans le monde : des prises tournées au hasard du
 * pixel donnaient la pénombre en trame, et la trame glissait sur la pierre à chaque pas.
 * Hors de la fenêtre, la carte lointaine reste seule.
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
// La part du bord de chaque carte où elle cède à la suivante : sans elle, l'ombre naissait d'un trait à quarante mètres.
const FONDU = 0.15, FONDU_LOINTAIN = 0.05;

// Le décor seul porte une ombre lointaine : un figurant y resterait figé à la pose du tracé.
const CALQUE_LOINTAIN = 1;
const COTE_LOINTAIN = { x: PROFIL.ombres.lointaine, y: PROFIL.ombres.lointaine / 2 };
// De l'astre au dernier dallage que l'ombre du Heikhal atteint sous une lune à treize degrés.
const COURSE_LOINTAINE = 700;
// Un tiers de texel de la carte lointaine : plus fin, le détail d'une tuile ne s'y lit pas.
export const FINESSE_LOINTAINE = 0.05;
const fenetre = new THREE.OrthographicCamera(-PROFIL.ombres.portee, PROFIL.ombres.portee, PROFIL.ombres.portee, -PROFIL.ombres.portee,
  PROFONDEUR.pres, PROFONDEUR.loin);
const lointaine = new THREE.OrthographicCamera();
lointaine.layers.set(CALQUE_LOINTAIN);
const cibleLointaine = new THREE.WebGLRenderTarget(COTE_LOINTAIN.x, COTE_LOINTAIN.y,
  { minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter });
// La face tournée vers l'astre : par l'arrière, comme three, l'ombre d'un bandeau plus mince qu'un texel sortait en pointillé.
const PROFONDEUR_SEULE = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, side: THREE.FrontSide });
const VERS_UNITE = new THREE.Matrix4().set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1);
export const OMBRE_LOINTAINE = {
  uCarteLointaine: { value: cibleLointaine.texture },
  uOmbreLointaine: { value: new THREE.Matrix4() },
  uPenteLointaine: { value: new THREE.Matrix3() },
  uPenteProche: { value: new THREE.Matrix3() },
};

export function porterAuLoin(maillage) {
  maillage.layers.enable(CALQUE_LOINTAIN);
}
export const profondeurLointaine = (maillage) => (maillage.layers.test(lointaine.layers) ? PROFONDEUR_SEULE : null);

// Les arêtes du Temple courent d'est en ouest et du nord au sud : en biais dans la grille des texels, l'ombre d'un bandeau sortait en dents de scie.
function grilleSurLesMurs(regard) {
  const e = regard.elements;
  const est = new THREE.Vector2(e[0], e[1]).normalize(), sud = new THREE.Vector2(e[8], e[9]).normalize();
  const aire = est.cross(sud), sens = Math.sign(aire), echelle = 1 / Math.sqrt(Math.abs(aire));
  return new THREE.Matrix4().set(
    sens * sud.y * echelle, -sens * sud.x * echelle, 0, 0,
    -est.y * echelle, est.x * echelle, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1);
}

const QUART_DE_TOUR = new THREE.Matrix4().set(0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1);

// three refait la projection de l'œil en créant sa carte : la grille s'y repose à chaque fois.
function projeterSur(oeil, grille) {
  oeil.updateProjectionMatrix = () => {
    THREE.OrthographicCamera.prototype.updateProjectionMatrix.call(oeil);
    oeil.projectionMatrix.multiply(grille);
    oeil.projectionMatrixInverse.copy(oeil.projectionMatrix).invert();
  };
  oeil.updateProjectionMatrix();
}

/** Tourne les deux cartes vers l'astre, et serre la lointaine sur l'enceinte (Box3, mètres). */
export function cadrerLesOmbres(versLAstre, enceinte) {
  enceinte.getCenter(lointaine.position);
  lointaine.lookAt(lointaine.position.clone().sub(versLAstre));
  lointaine.updateMatrixWorld();
  const grille = grilleSurLesMurs(lointaine.matrixWorldInverse);
  projeterSur(fenetre, grille);
  const vueDe = (g) => enceinte.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(g, lointaine.matrixWorldInverse));
  const taille = vueDe(grille).getSize(new THREE.Vector3());
  // Le grand côté de l'enceinte prend le grand côté de la carte.
  const grilleLointaine = taille.y > taille.x ? grille.clone().premultiply(QUART_DE_TOUR) : grille;
  const vue = vueDe(grilleLointaine);
  // L'enceinte tient en deçà du fondu : c'est hors les murs que l'ombre s'efface.
  const bord = vue.getSize(new THREE.Vector3()).multiplyScalar(FONDU_LOINTAIN / (1 - FONDU_LOINTAIN) / 2).setZ(0);
  vue.expandByVector(bord);
  Object.assign(lointaine, { left: vue.min.x, right: vue.max.x, bottom: vue.min.y, top: vue.max.y,
    near: -vue.max.z, far: -vue.max.z + COURSE_LOINTAINE });
  projeterSur(lointaine, grilleLointaine);
  OMBRE_LOINTAINE.uOmbreLointaine.value.copy(VERS_UNITE).multiply(lointaine.projectionMatrix).multiply(lointaine.matrixWorldInverse);
  OMBRE_LOINTAINE.uPenteLointaine.value.getNormalMatrix(OMBRE_LOINTAINE.uOmbreLointaine.value);
  // La fenêtre proche regarde du même œil : seule son échelle change.
  OMBRE_LOINTAINE.uPenteProche.value.getNormalMatrix(
    new THREE.Matrix4().copy(VERS_UNITE).multiply(fenetre.projectionMatrix).multiply(lointaine.matrixWorldInverse));
}

// Une scène à part, sans brume : tracée sur la vraie, la carte y laissait un éclairage vide dont three tirait d'autres nuanceurs d'ombre, compilés page figée.
const decorLointain = Object.assign(new THREE.Scene(), { overrideMaterial: PROFONDEUR_SEULE });
export function tracerOmbreLointaine(renderer, scene) {
  const cible = renderer.getRenderTarget();
  const fond = renderer.getClearColor(new THREE.Color()), alphaFond = renderer.getClearAlpha();
  decorLointain.children = scene.children;
  try {
    renderer.setClearColor(0xffffff, 1);
    renderer.setRenderTarget(cibleLointaine);
    renderer.render(decorLointain, lointaine);
  } finally {
    renderer.setClearColor(fond, alphaFond);
    renderer.setRenderTarget(cible);
  }
}

// Les lampes gardent la face arrière de three : leur carte se lit sans le plan de la face, et s'ombrerait elle-même.
function tournerVersLAstre(_renderer, _objet, _camera, oeilDeLOmbre, _geometrie, profondeur) {
  if (oeilDeLOmbre.isOrthographicCamera && this.material.side === THREE.FrontSide) profondeur.side = THREE.FrontSide;
}

export function regler(soleil) {
  if (PROFIL.ombres.penombre) THREE.Mesh.prototype.onBeforeShadow = tournerVersLAstre;
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
  soleil.shadow.camera = fenetre;
}

// Le côté du carré de texels lu dans chaque carte, pondérés en tente.
const GRILLE_PROCHE = 4, GRILLE_LOINTAINE = PROFIL.ombres.penombre ? 4 : 2;
// En mètres : la pente qu'une face rasante peut réclamer d'une prise à l'autre, et ce qui la décolle de la carte, le long du rayon puis de sa normale.
const PENTE_MAX = 4, BIAIS_LOINTAIN = 0.05, RETRAIT_LOINTAIN = 0.03;
// En mètres, la pénombre que chaque carte sait rendre : trois texels de la fenêtre, trois de la carte lointaine.
const PENOMBRE_PROCHE = 3 * 2 * PROFIL.ombres.portee / PROFIL.ombres.taille, PENOMBRE_LOINTAINE = 0.45;

const NETTE = /* glsl */`
float ombreProche(sampler2D carte, vec2 taille, float biais, vec4 coord, vec3 normale){
  coord.xyz /= coord.w;
  coord.z += biais;
  vec2 pente = penteDe(uPenteProche * normale);
  vec2 grille = coord.xy * taille - 0.5;
  vec2 coin = floor(grille) - ${(GRILLE_PROCHE / 2 - 1).toFixed(1)}, reste = fract(grille);
  float ombre = 0.0;
  for (int j = 0; j < ${GRILLE_PROCHE}; j++) for (int i = 0; i < ${GRILLE_PROCHE}; i++) {
    vec2 centre = (coin + vec2(i, j) + 0.5) / taille;
    float attendue = coord.z + clamp(dot(pente, centre - coord.xy), ${(-PENTE_MAX / (PROFONDEUR.loin - PROFONDEUR.pres)).toFixed(6)}, ${(PENTE_MAX / (PROFONDEUR.loin - PROFONDEUR.pres)).toFixed(6)});
    ombre += poidsDeTente(i, ${GRILLE_PROCHE - 1}, reste.x) * poidsDeTente(j, ${GRILLE_PROCHE - 1}, reste.y)
      * texture2DCompare(carte, centre, attendue);
  }
  return ombre / ${((GRILLE_PROCHE - 1) ** 2).toFixed(1)};
}
`;

// Ce qui bouche le soleil de loin étale son ombre : la fenêtre proche cède à la carte lointaine à mesure que la pénombre dépasse ce qu'elle sait rendre.
const PENOMBRE = (pointMonde, normaleMonde) => /* glsl */`
float getShadow(sampler2D carte, vec2 taille, float biais, float rayon, vec4 coord){
  vec2 loin = ombreLointaine(${pointMonde}, ${normaleMonde});
  float sortie = sortieDe(vec3(coord.xy, coord.z + biais) / coord.w, ${FONDU.toFixed(2)});
  if (sortie >= 1.0) return loin.x;
  float etale = smoothstep(${PENOMBRE_PROCHE.toFixed(3)}, ${PENOMBRE_LOINTAINE.toFixed(3)}, loin.y * ${DIAMETRE_SOLEIL});
  return mix(ombreProche(carte, taille, biais, coord, ${normaleMonde}), loin.x, max(sortie, etale));
}
`;

const SANS_PENOMBRE = (pointMonde, normaleMonde) => /* glsl */`
float getShadow(sampler2D carte, vec2 taille, float biais, float rayon, vec4 coord){
  float sortie = sortieDe(vec3(coord.xy, coord.z + biais) / coord.w, ${FONDU.toFixed(2)});
  float ombre = sortie < 1.0 ? ombreProche(carte, taille, biais, rayon, coord) : 1.0;
  return sortie > 0.0 ? mix(ombre, ombreLointaine(${pointMonde}, ${normaleMonde}).x, sortie) : ombre;
}
`;

// Chaque prise se compare au plan de la face, au centre de son texel : le biais constant qu'il faudrait au dallage décollerait les ombres de leur pied.
const fondues = (pointMonde, normaleMonde) => /* glsl */`
#ifdef USE_SHADOWMAP
uniform sampler2D uCarteLointaine;
uniform mat4 uOmbreLointaine;
uniform mat3 uPenteLointaine, uPenteProche;
const vec2 TEXEL_LOINTAIN = vec2(${(1 / COTE_LOINTAIN.x).toFixed(8)}, ${(1 / COTE_LOINTAIN.y).toFixed(8)});

// Le poids d'un texel de la grille le long d'un axe : les deux du bord se relaient, ceux du milieu comptent entiers.
float poidsDeTente(int rang, int dernier, float reste){
  return rang == 0 ? 1.0 - reste : rang == dernier ? reste : 1.0;
}

// Ce que la profondeur d'une face gagne d'un bord à l'autre de la carte, sur chacun de ses deux axes.
vec2 penteDe(vec3 plan){
  return -plan.xy / min(plan.z, -1e-4);
}

// 0 au cœur de la carte, 1 à son bord et au-delà.
float sortieDe(vec3 coord, float fondu){
  vec2 ecart = abs(coord.xy - 0.5) * 2.0;
  return coord.z > 1.0 ? 1.0 : smoothstep(1.0 - fondu, 1.0, max(ecart.x, ecart.y));
}

// x : la part de soleil ; y : en mètres, l'éloignement moyen de ce qui le bouche, nul si rien ne le bouche.
vec2 ombreLointaine(vec3 point, vec3 normale){
  vec3 coord = (uOmbreLointaine * vec4(point + normale * ${RETRAIT_LOINTAIN.toFixed(2)}, 1.0)).xyz;
  float sortie = sortieDe(coord, ${FONDU_LOINTAIN.toFixed(2)});
  if (sortie >= 1.0) return vec2(1.0, 0.0);
  vec2 pente = penteDe(uPenteLointaine * normale);
  vec2 grille = coord.xy / TEXEL_LOINTAIN - 0.5;
  vec2 coin = floor(grille) - ${(GRILLE_LOINTAINE / 2 - 1).toFixed(1)}, reste = fract(grille);
  float soleil = 0.0, bouche = 0.0, recul = 0.0;
  for (int j = 0; j < ${GRILLE_LOINTAINE}; j++) for (int i = 0; i < ${GRILLE_LOINTAINE}; i++) {
    vec2 centre = (coin + vec2(i, j) + 0.5) * TEXEL_LOINTAIN;
    float attendue = coord.z + clamp(dot(pente, centre - coord.xy), ${(-PENTE_MAX / COURSE_LOINTAINE).toFixed(6)}, ${(PENTE_MAX / COURSE_LOINTAINE).toFixed(6)}) - ${(BIAIS_LOINTAIN / COURSE_LOINTAINE).toFixed(6)};
    float lue = unpackRGBAToDepth(texture2D(uCarteLointaine, centre));
    float poids = poidsDeTente(i, ${GRILLE_LOINTAINE - 1}, reste.x) * poidsDeTente(j, ${GRILLE_LOINTAINE - 1}, reste.y);
    if (lue < attendue) { bouche += poids; recul += poids * (attendue - lue); }
    else soleil += poids;
  }
  float eloignement = bouche > 0.0 ? recul / bouche * ${COURSE_LOINTAINE.toFixed(1)} * (1.0 - sortie) : 0.0;
  return vec2(mix(soleil / ${((GRILLE_LOINTAINE - 1) ** 2).toFixed(1)}, 1.0, sortie), eloignement);
}

${PROFIL.ombres.penombre ? NETTE + PENOMBRE(pointMonde, normaleMonde) : SANS_PENOMBRE(pointMonde, normaleMonde)}
#endif
`;

const APPORT = "RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );";

// La lumière de `info`, son ombre et son apport ne se calculent que sous `garde` : ailleurs l'apport est nul, ombre ou pas.
function brancher(morceau, info, garde) {
  const debut = morceau.indexOf(info) + info.length;
  const fin = morceau.indexOf(APPORT, debut) + APPORT.length;
  const corps = morceau.slice(debut, fin)
    .replace(/directLight\.color \*= \( directLight\.visible && receiveShadow \) \? (.*) : 1\.0;/,
             "if ( receiveShadow ) directLight.color *= $1;");
  if (debut < info.length || fin < APPORT.length || corps === morceau.slice(debut, fin)) {
    throw new Error("three a changé lights_fragment_begin : ombres lues partout");
  }
  return `${morceau.slice(0, debut)}\n\t\tif ( ${garde} ) {${corps}\n\t\t}${morceau.slice(fin)}`;
}

// Le ternaire de three est aplati à la compilation : les ombres des lampes se lisaient sur toute l'esplanade, la pénombre sur les faces dos au soleil.
export function epargner() {
  THREE.ShaderChunk.lights_fragment_begin = brancher(brancher(THREE.ShaderChunk.lights_fragment_begin,
    "getPointLightInfo( pointLight, geometryPosition, directLight );", "directLight.visible"),
    "getDirectionalLightInfo( directionalLight, directLight );", "dot( nonPerturbedNormal, directLight.direction ) > 0.0");
}

/** Le morceau de three, sa fonction devenue la lecture de la fenêtre proche du profil léger, la nôtre à sa place. */
export function assemblage(pointMonde, normaleMonde) {
  const morceau = THREE.ShaderChunk.shadowmap_pars_fragment;
  const ecarte = morceau.replace("float getShadow(", PROFIL.ombres.penombre ? "float getShadowDur(" : "float ombreProche(");
  if (ecarte === morceau) throw new Error("three a renommé getShadow : pénombre perdue");
  return ecarte + fondues(pointMonde, normaleMonde);
}
