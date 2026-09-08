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
const PIERRE = 1, MARBRE = 2, METAL = 3, BOIS = 4, ETOFFE = 5, EAU = 6, ENDUIT = 7, SUIE = 8,
      GAZIT = 9, TAMBOUR = 10;
const FAMILLES = {
  Pierre_claire: PIERRE, Sol: PIERRE, Maisons: PIERRE, Pierre_colonne: TAMBOUR,
  Marbre_blanc: MARBRE, Marbre_Herode: GAZIT,
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
const float JOINT = 0.06;      // largeur du joint entre deux blocs, en amot
const float LISERE = 0.25;     // liseré ciselé qui le borde
// Ce que devient la pierre au fond du joint : plus sombre et PLUS CHAUDE. Multiplier
// vers le noir suffisait à creuser, mais un calcaire assombri sans teinte vire au gris
// et le mur se retrouvait quadrillé de traits grisâtres. Un joint est de la pierre à
// l'ombre. Même valeur que OMBRE_JOINT dans le blockout.
const vec3 OMBRE_JOINT = vec3(0.50, 0.40, 0.29);

// Les quatre bancs du calcaire de Jérusalem, en écart multiplicatif : le meleke n'est
// pas d'une couleur mais d'une bande, du gris froid au doré. Mêmes valeurs que
// BANCS_CALCAIRE du blockout — un mur dont les blocs ne diffèrent qu'en clarté rend un
// aplat sali, jamais de la pierre.
// La bande va du crème pâle à l'ocre, JAMAIS au froid : rouge ≥ vert ≥ bleu dans
// chaque banc. Le plus clair partait plus bleu que rouge — au soleil il passait, mais à
// l'ombre, où la seule lumière est celle d'un ciel bleu, il rendait du béton.
vec3 banc(float t){
  vec3 a = vec3(0.82, 0.79, 0.74), b = vec3(0.93, 0.90, 0.86),
       c = vec3(1.04, 1.00, 0.94), d = vec3(1.18, 1.09, 0.89);
  t = clamp(t, 0.0, 1.0) * 3.0;
  return t < 1.0 ? mix(a, b, t) : (t < 2.0 ? mix(b, c, t - 1.0) : mix(c, d, t - 2.0));
}

// Distance au joint le plus proche, en amot, le long d'une coordonnée de monde.
float ecart(float coord, float taille, out float rang){
  rang = coord / (taille * AMA);
  float f = fract(rang);
  return min(f, 1.0 - f) * taille;
}

// Appareil de gazit. Le Tanakh mesure ces pierres : « אַבְנֵי עֶשֶׂר אַמּוֹת וְאַבְנֵי שְׁמֹנֶה
// אַמּוֹת » (Melakhim I 7:10) — deux longueurs, l'assise en tire une —, et les dit sciées
// lisses dedans et dehors, « מְגֹרָרוֹת בַּמְּגֵרָה מִבַּיִת וּמִחוּץ » (7:9). Tout le relief tient
// donc au joint creusé et au liseré ciselé qui le borde, jamais à un bossage éclaté.
// L'assise saillante et l'assise rentrante sont le אבן יוצא ואבן נכנס de Baba Batra 4a :
// c'est ce jeu-là, et non un placage, qui a fait renoncer Hérode à dorer le bâtiment.
// Le paramètre bloc : la longueur d'un bloc en amot, ou 0 pour laisser l'assise tirer
// entre dix et huit. Un tambour de colonne est UNE pierre : il prend une longueur
// énorme, qui supprime le joint vertical et ne laisse que le lit d'un tambour au suivant.
void appareil(vec3 P, vec3 N, float assise, float calcaire, float bloc,
              out vec3 teinte, out float relief, out float rugo){
  float g = grain(P * 7.0);
  if (abs(N.y) > 0.7) {                       // dallage : les assises n'ont pas de sens à plat
    vec2 d = P.xz / (3.0 * AMA);              // dalles de 3 amot, comme le blockout
    float joint = bande(d.x, 0.018) * bande(d.y, 0.018);
    float patine = grain(P / (20.0 * AMA));
    teinte = vec3((1.0 + (g - 0.5) * 0.10) * mix(0.68, 1.0, joint))
           * mix(vec3(1.0), OMBRE_JOINT, 0.45 * patine);
    relief = joint * 0.5 + g * 0.30;
    rugo = (g - 0.5) * 0.10;
    return;
  }
  float rang;
  float dz = ecart(P.y, assise, rang);
  float num = floor(rang);
  float parite = mod(num, 2.0);
  float tireAssise = alea1(num * 1.7 + 3.1);
  float longueur = bloc > 0.0 ? bloc : (tireAssise > 0.5 ? 10.0 : 8.0);
  float u = abs(N.x) > abs(N.z) ? P.z : P.x;      // la face décide de l'axe des joints
  // Les joints verticaux se décalent d'une assise à la suivante : alignés, ils font un
  // damier, que ne montre aucun appareil de pierre de taille.
  u += (parite * 0.5 + tireAssise * 0.37) * longueur * AMA;
  float colonne;
  float du = ecart(u, longueur, colonne);
  float tireBloc = alea3(vec3(floor(colonne), num, 0.0));
  float d = min(dz, du);
  // Le profil du bloc, en trois pentes : le joint, le liseré presque plat, le champ.
  // 0,62 de la course descend dans le joint, et il ne reste que 0,32 pour la marche du
  // bloc — une pierre sciée n'est proéminente que d'un cheveu. Plus haut, le relief
  // cernait chaque bloc d'un jonc clair et le mur rendait un carrelage.
  float profil = 0.62 * clamp(d / JOINT, 0.0, 1.0)
               + 0.06 * clamp((d - JOINT) / LISERE, 0.0, 1.0)
               + 0.32 * clamp((d - JOINT - LISERE) / 0.06, 0.0, 1.0);
  // Le JOINT seul, sans le liseré : l'ombre s'arrête au fond de la rainure. Étalée sur
  // le liseré, elle cerne chaque bloc d'un cadre sombre que ne montre aucun mur ; le
  // liseré est de la pierre en plein soleil et ne doit rien perdre.
  float creux = clamp(d / (JOINT * 1.6), 0.0, 1.0);
  // Une coulure, pas une tache : un bruit étiré à la verticale. Une tache sur un mur se
  // lit en défaut de matière ; une coulure se lit en pierre. Et une moucheture par-
  // dessus : le banc donne au bloc SA couleur, mais un bloc d'une seule couleur est un
  // échantillon de nuancier — le calcaire est nué à l'intérieur de chaque pierre.
  float coulure = 0.16 * smoothstep(0.52, 0.88, grain(vec3(P.x, P.y / 12.0, P.z) / (3.0 * AMA)));
  float mouchete = grain(P / (1.5 * AMA)) * 0.22 + grain(P / (0.45 * AMA)) * 0.10;
  // Le drapeau sépare les deux pierres du chantier : le calcaire du pourtour tire son
  // banc, le marbre du bâtiment ne tire qu'une nuance — sa couleur lui vient du rang.
  float f = parite * 0.10 + grain(P / (30.0 * AMA)) * 0.22 + tireBloc * 0.68;
  vec3 base = (calcaire > 0.5 ? banc(f) : mix(vec3(0.84, 0.85, 0.88), vec3(1.10, 1.08, 1.02), clamp(f, 0.0, 1.0)))
            * mix(vec3(1.0), OMBRE_JOINT, coulure + mouchete);
  teinte = mix(base * OMBRE_JOINT, base, creux);
  relief = profil;
  // La rugosité varie DANS le bloc, pas seulement d'un bloc à l'autre : sous un soleil
  // rasant c'est le lustre qui donne la surface, la teinte ne fait que la colorer.
  rugo = (tireBloc - 0.5) * 0.18 + (grain(P / (0.35 * AMA)) - 0.5) * 0.16;
}

void matiere(vec3 P, vec3 N, out vec3 teinte, out float relief, out float rugo){
  teinte = vec3(1.0); relief = 0.0; rugo = 0.0;
  // Le détail se fond sur la distance à l'oeil. La borne a suivi l'appareil : des blocs
  // de huit à dix amot tiennent à deux cents mètres, là où le module d'une ama
  // scintillait passé quarante et laissait la moitié des cadres en volumes gris.
  float nettete = 1.0 - smoothstep(60.0, 200.0, distance(P, cameraPosition));
  if (uFamille == 1) { appareil(P, N, 2.5, 1.0, 0.0, teinte, relief, rugo); }
  else if (uFamille == 10) {          // tambour de colonne : pas de joint vertical
    // Sur un cylindre le joint vertical était pire qu'inutile : la face choisit son axe
    // sur la normale, qui bascule quatre fois autour du fût, et la trame sautait quatre
    // fois par colonne.
    appareil(P, N, 1.4, 1.0, 1.0e4, teinte, relief, rugo);
  }
  else if (uFamille == 9) {           // le bâtiment : assise de 2 amot, trois marbres
    // « בְּאַבְנֵי שֵׁישָׁא כּוּחְלָא וּמַרְמְרָא » (Soucca 51b ; Baba Batra 4a). Le rang entier tire
    // sa pierre — par bloc, les trois marbres feraient une mosaïque et non les vagues
    // que les Sages ont préférées à l'or. Écarts relatifs au shesh, qui est la couleur
    // de base exportée. L'assise de 2 amot tombe juste sur les rovadim, qui vont par 4.
    appareil(P, N, 2.0, 0.0, 0.0, teinte, relief, rugo);
    float t = alea1(floor(P.y / (2.0 * AMA)) * 1.7 + 3.1);
    teinte *= t < 0.3333 ? vec3(1.00, 1.00, 1.00)
            : (t < 0.6667 ? vec3(0.81, 0.91, 0.93) : vec3(0.98, 0.91, 0.70));
  }
  else if (uFamille == 2) {                                   // marbre : veines lentes
    float v = grain(P * vec3(2.2, 5.0, 2.2) + grain(P * 1.1) * 2.0);
    teinte = vec3(1.0 + (v - 0.5) * 0.13);
    relief = v * 0.18;
    rugo = (v - 0.5) * 0.06;
  }
  else if (uFamille == 3) {                                   // métal battu au marteau
    // Large et discret : l'or du Heikhal est une feuille martelée, pas du sable.
    float g = grain(P * 5.0);
    teinte = vec3(1.0 + (g - 0.5) * 0.05);
    relief = g * 0.16;
    rugo = (g - 0.5) * 0.10;
  }
  else if (uFamille == 4) {                                   // bois : fil étiré
    float f = grain(P * vec3(9.0, 1.1, 9.0));
    float veine = fract(f * 7.0);
    teinte = vec3(1.0 + (f - 0.5) * 0.18 - veine * 0.06);
    relief = f * 0.4 + veine * 0.15;
    rugo = (f - 0.5) * 0.10;
  }
  else if (uFamille == 5) {                                   // étoffe : la trame
    float trame = sin(P.x * 240.0) * sin(P.y * 240.0);
    float duvet = grain(P * 45.0);
    teinte = vec3(1.0 + trame * 0.045 + (duvet - 0.5) * 0.10);
    relief = trame * 0.35 + duvet * 0.25;
    rugo = -0.03;
  }
  else if (uFamille == 6) {                                   // eau : ride lente
    float r = grain(P * 5.5 + vec3(0.0, uTemps * 0.12, 0.0));
    teinte = vec3(1.0 + (r - 0.5) * 0.08);
    relief = r * 1.3;
    rugo = -0.02;
  }
  else if (uFamille == 7) {                                   // enduit à la chaux
    float g = grain(P * 11.0), fin = grain(P * 47.0);
    teinte = vec3(1.0 + (g - 0.5) * 0.20 + (fin - 0.5) * 0.09);
    relief = g * 0.7 + fin * 0.35;
    rugo = (g - 0.5) * 0.12;
  }
  else if (uFamille == 8) {                                   // chaux noircie par le feu
    float s = grain(P * 4.0);
    float haut = smoothstep(0.4, 2.6, P.y);
    teinte = vec3(mix(1.0, 0.30, haut * (0.55 + 0.45 * s)));
    relief = s * 0.4;
    rugo = 0.06;
  }
  teinte = mix(vec3(1.0), teinte, nettete);
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
        vec3 mTeinte; float mRelief, mRugo;
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
