/**
 * Matières procédurales, lues en coordonnées de MONDE.
 *
 * Le blockout définit ses matières comme des arbres de nœuds Blender branchés sur
 * `Geometry > Position` : un mur percé est fait de cinq boîtes, et des coordonnées
 * d'objet y recadreraient la pierre cinq fois. glTF ne transporte pas de nœuds, et
 * l'export n'en garde que la couleur de base — d'où ces volumes uniformément gris.
 *
 * Ce fichier remet le relief là où il était, avec les mêmes entrées : la position du
 * point dans le monde, et rien d'autre. Aucune image, aucune UV — les maillages n'en
 * ont pas. Les assises d'une ama, leur alternance et leur grain sont donc calculés
 * ici comme ils l'étaient dans Blender, et se poursuivent d'un objet au suivant sans
 * saut de motif.
 */
import * as THREE from "three";

// Familles : le nom de la matière exportée décide du traitement.
const PIERRE = 1, MARBRE = 2, METAL = 3, BOIS = 4, ETOFFE = 5, EAU = 6, ENDUIT = 7, SUIE = 8;
const FAMILLES = {
  Pierre_claire: PIERRE, Sol: PIERRE, Maisons: PIERRE,
  Marbre_blanc: MARBRE, Marbre_Herode: PIERRE,
  Or: METAL, Or_plaque: METAL, Bronze: METAL, Fer: METAL,
  Cedre: BOIS, Chene: BOIS, Chene_sculpte: BOIS,
  Parokhet_tissee: ETOFFE, Lin_blanc: ETOFFE, Tekhelet_meil: ETOFFE,
  Eau_Kiyor: EAU,
  Chaux_blanche: ENDUIT, Sikra: ENDUIT,
  Chaux_noircie: SUIE, Braise: SUIE,
};

const COMMUN = /* glsl */`
varying vec3 vMonde;
varying vec3 vNMonde;
uniform int uFamille;
uniform float uTemps;
uniform float uRelief;

float alea1(float p){ p = fract(p * 0.1031); p *= p + 33.33; p *= p + p; return fract(p); }
float alea3(vec3 p){ p = fract(p * 0.1031); p += dot(p, p.zyx + 31.32); return fract((p.x + p.y) * p.z); }
float bruit(vec3 x){
  vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(alea3(i), alea3(i + vec3(1,0,0)), f.x),
                 mix(alea3(i + vec3(0,1,0)), alea3(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(alea3(i + vec3(0,0,1)), alea3(i + vec3(1,0,1)), f.x),
                 mix(alea3(i + vec3(0,1,1)), alea3(i + vec3(1,1,1)), f.x), f.y), f.z);
}
float grain(vec3 p){ return 0.5 * bruit(p) + 0.25 * bruit(p * 2.03) + 0.125 * bruit(p * 4.01); }

// Aucune dérivée d'écran dans ce fichier, et c'est délibéré. Aux angles rasants — un
// mur vu presque par la tranche, ce qui est la moitié des cadres dans un couloir de
// 40 amot — deux pixels voisins tombent sur des points du monde très éloignés : toute
// dérivée y explose, et ce qu'elle pilote se met à clignoter d'un pixel à l'autre. Le
// détail se fond donc sur la DISTANCE à l'œil, qui varie doucement.
float bande(float x, float largeur){
  float f = fract(x);
  return smoothstep(0.0, largeur, f) * smoothstep(0.0, largeur, 1.0 - f);
}

const float AMA = 0.48;

// Assises d'une ama, une saillante une rentrante : le אבן יוצא ואבן נכנס de Baba
// Batra 4a. C'est ce jeu-là, et non un placage, qui donne l'échelle d'un mur de
// 100 amot — et la raison pour laquelle Hérode a renoncé à dorer le bâtiment.
void appareil(vec3 P, vec3 N, out float teinte, out float relief, out float rugo){
  float g = grain(P * 7.0);
  if (abs(N.y) > 0.7) {                       // dallage : les assises n'ont pas de sens à plat
    vec2 d = P.xz / (1.5 * AMA);
    float joint = bande(d.x, 0.045) * bande(d.y, 0.045);
    float tirage = alea3(vec3(floor(d), 0.0));
    teinte = (1.0 + (tirage - 0.5) * 0.13 + (g - 0.5) * 0.12) * mix(0.70, 1.0, joint);
    relief = joint * 0.5 + g * 0.30;
    rugo = (g - 0.5) * 0.10;
    return;
  }
  float rang = P.y / AMA;
  float num = floor(rang);
  float parite = mod(num, 2.0);
  float tirageAssise = alea1(num * 1.7 + 3.1);
  float jointH = bande(rang, 0.055);
  float u = abs(N.x) > abs(N.z) ? P.z : P.x;      // la face décide de l'axe des joints
  float colonne = u / (2.0 * AMA) + parite * 0.5 + tirageAssise * 0.25;
  float jointV = bande(colonne, 0.030);
  float tiragePierre = alea1(floor(colonne) * 13.7 + num * 4.3);
  teinte = (1.0 + (parite - 0.5) * 0.075 + (tiragePierre - 0.5) * 0.15 + (g - 0.5) * 0.18)
         * mix(0.52, 1.0, jointH * jointV);
  relief = jointH * jointV * 0.9 + (parite - 0.5) * 0.35 + g * 0.38;
  rugo = (g - 0.5) * 0.10;
}

void matiere(vec3 P, vec3 N, out float teinte, out float relief, out float rugo){
  teinte = 1.0; relief = 0.0; rugo = 0.0;
  float nettete = 1.0 - smoothstep(14.0, 45.0, distance(P, cameraPosition));
  if (uFamille == 1) { appareil(P, N, teinte, relief, rugo); }
  else if (uFamille == 2) {                                   // marbre : veines lentes
    float v = grain(P * vec3(2.2, 5.0, 2.2) + grain(P * 1.1) * 2.0);
    teinte = 1.0 + (v - 0.5) * 0.13;
    relief = v * 0.18;
    rugo = (v - 0.5) * 0.06;
  }
  else if (uFamille == 3) {                                   // métal battu au marteau
    // Large et discret : l'or du Heikhal est une feuille martelée, pas du sable.
    float g = grain(P * 5.0);
    teinte = 1.0 + (g - 0.5) * 0.05;
    relief = g * 0.16;
    rugo = (g - 0.5) * 0.10;
  }
  else if (uFamille == 4) {                                   // bois : fil étiré
    float f = grain(P * vec3(9.0, 1.1, 9.0));
    float veine = fract(f * 7.0);
    teinte = 1.0 + (f - 0.5) * 0.18 - veine * 0.06;
    relief = f * 0.4 + veine * 0.15;
    rugo = (f - 0.5) * 0.10;
  }
  else if (uFamille == 5) {                                   // étoffe : la trame
    float trame = sin(P.x * 240.0) * sin(P.y * 240.0);
    float duvet = grain(P * 45.0);
    teinte = 1.0 + trame * 0.045 + (duvet - 0.5) * 0.10;
    relief = trame * 0.35 + duvet * 0.25;
    rugo = -0.03;
  }
  else if (uFamille == 6) {                                   // eau : ride lente
    float r = grain(P * 5.5 + vec3(0.0, uTemps * 0.12, 0.0));
    teinte = 1.0 + (r - 0.5) * 0.08;
    relief = r * 1.3;
    rugo = -0.02;
  }
  else if (uFamille == 7) {                                   // enduit à la chaux
    float g = grain(P * 11.0), fin = grain(P * 47.0);
    teinte = 1.0 + (g - 0.5) * 0.20 + (fin - 0.5) * 0.09;
    relief = g * 0.7 + fin * 0.35;
    rugo = (g - 0.5) * 0.12;
  }
  else if (uFamille == 8) {                                   // chaux noircie par le feu
    float s = grain(P * 4.0);
    float haut = smoothstep(0.4, 2.6, P.y);
    teinte = mix(1.0, 0.30, haut * (0.55 + 0.45 * s));
    relief = s * 0.4;
    rugo = 0.06;
  }
  teinte = mix(1.0, teinte, nettete);
  relief *= nettete;
  rugo *= nettete;
}
`;

/**
 * Branche le calcul procédural sur une matière standard, sans la remplacer : le
 * modèle d'éclairage, les ombres et le tonemapping de three restent ceux d'origine.
 */
export function habiller(materiau, horloges) {
  const famille = FAMILLES[materiau.name];
  if (!famille) return;
  const uniformes = { uFamille: { value: famille }, uTemps: { value: 0 },
                      uRelief: { value: famille === 5 ? 0.012 : 0.03 } };
  materiau.userData.uniformes = uniformes;
  if (famille === EAU) horloges.push(uniformes.uTemps);

  materiau.onBeforeCompile = (nuanceur) => {
    Object.assign(nuanceur.uniforms, uniformes);
    nuanceur.vertexShader = nuanceur.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vMonde;\nvarying vec3 vNMonde;")
      .replace("#include <begin_vertex>",
               "#include <begin_vertex>\nvMonde = (modelMatrix * vec4(transformed, 1.0)).xyz;\n" +
               "vNMonde = normalize(mat3(modelMatrix) * objectNormal);");

    nuanceur.fragmentShader = nuanceur.fragmentShader
      .replace("#include <common>", "#include <common>\n" + COMMUN)
      // Les maillages sont exportés sans normales : three les tire des dérivées.
      // La normale de monde se prend donc au même endroit, pas d'un attribut absent.
      // La normale vient de l'attribut, pas des dérivées de la position : c'est elle
      // qui décide si la face est un sol ou un mur, et sur quel axe courent les
      // joints. Tirée des dérivées, elle devenait aléatoire aux angles rasants et
      // chaque pixel changeait d'avis — la pierre grouillait.
      .replace("#include <clipping_planes_fragment>", /* glsl */`
        #include <clipping_planes_fragment>
        float mTeinte, mRelief, mRugo;
        matiere(vMonde, normalize(vNMonde), mTeinte, mRelief, mRugo);`)
      .replace("#include <color_fragment>",
               "#include <color_fragment>\ndiffuseColor.rgb *= mTeinte;")
      .replace("#include <roughnessmap_fragment>",
               "#include <roughnessmap_fragment>\nroughnessFactor = clamp(roughnessFactor + mRugo, 0.03, 1.0);")
      // Le creux du joint passe par la couleur et la rugosite, pas par la normale :
      // le relief geometrique est deja modelise (les rovadim de la facade, le jeu
      // d'assises saillante/rentrante), et la seule facon de simuler le reste sans
      // UV ni tangentes passait par les derivees d'ecran, instables aux angles
      // rasants. Mieux vaut une pierre stable qu'un relief qui grouille.
      ;
  };
  materiau.customProgramCacheKey = () => `mikdash-${famille}`;
}

/** L'orge du feu : la braise éclaire, elle ne fait pas que rougeoyer. */
export function attiser(materiau) {
  if (materiau.name === "Braise") {
    materiau.emissive = new THREE.Color(0xff5a12);
    materiau.emissiveIntensity = 1.6;
  }
}
