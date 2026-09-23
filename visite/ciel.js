/**
 * Le ciel : d'où vient la lumière, ce que la scène réfléchit, et ce qui l'éloigne.
 *
 * Deux dômes, pas un. Celui qu'on VOIT porte le disque solaire à sa taille vraie —
 * un demi-degré — sur le dégradé d'un matin de Jérusalem : un ciel d'où vient une
 * ombre franche sans qu'on voie d'où elle vient se lit en éclairage de studio.
 *
 * Celui qui ÉCLAIRE, filtré en PMREM, n'a pas les mêmes couleurs. Il n'y a pas de
 * rebond dans cette scène : sous un portique la seule lumière serait celle du bleu du
 * zénith, et le dallage à l'ombre y virait au bleu franc. Le ciel de l'éclairage est
 * donc désaturé vers le haut, et sa moitié basse porte le calcaire ensoleillé de
 * l'esplanade, qui est le vrai rebond de tout ce qui est à l'ombre ici.
 *
 * Son soleil, lui, est ÉLARGI, et son horizon RESSERRÉ. Un disque d'un demi-degré ne
 * survit pas au filtrage : il ne couvre pas un texel de la cube-map. Sans lui l'or ne
 * réfléchit qu'un dégradé lisse — un métal qui n'a pas d'image dans son reflet se lit
 * en plastique jaune, et c'est ce qu'on voyait. Étalé sur trois degrés il traverse le
 * filtrage, et la ligne d'horizon lui donne la seconde chose qu'un métal doit
 * réfléchir pour en être un : une arête.
 */
import * as THREE from "three";

// Vingt degrés au-dessus de l'horizon, à l'est : l'axe de l'avoda, et l'heure du
// tamid du matin. L'angle n'est pas un détail d'ambiance — c'est lui qui décide si la
// lumière RASE la pierre ou l'écrase. À 38°, l'assise, le joint, le chanfrein et le
// grain des nappes recevaient tous la même clarté et le relief disparaissait. Plus bas
// que vingt, en revanche, le dallage ne reçoit plus qu'un quart du soleil et l'ambiance
// reprend le dessus : la cour repasse en aplat pâle, l'inverse de ce qu'on cherche.
export const SOLEIL = new THREE.Vector3(150, 58, 55).normalize();

// L'AIR, et pas un brouillard. Un brouillard linéaire pose la même teinte à la même
// distance dans toutes les directions : un calque gris sur l'image. L'air est plus dense
// en bas qu'en haut, et ce qu'il ajoute à une chose lointaine est le ciel qu'on voit
// derrière elle. Chaque fragment reçoit donc l'épaisseur d'air traversée depuis l'œil —
// une densité qui décroît en exponentielle avec la hauteur, intégrée le long du rayon —,
// et ce qu'elle cache se remplace par le dôme VU dans la direction regardée.
//
// `densite` est celle du dallage de l'Azara (y = 0), par mètre : 0,004 laisse 80 % d'un mur
// à soixante mètres et 40 % des portiques d'en face. À 0,0018 l'Oulam vu de l'Ezrat Nashim
// gardait le contraste du premier plan : c'est cette perte de contraste, pas la teinte du
// voile, qui sépare les plans d'une cour. `epaisseur` est la hauteur où l'air a perdu les
// deux tiers de sa densité : vu d'en haut, le pied des portiques se voile plus que leur
// faîte. `effacement` finit le travail avant que la caméra ne coupe à 6 km : un bord
// tranché net sur le ciel se lirait en décor.
//
// Le voile n'a pas la même couleur des deux côtés du ciel. La brume diffuse vers l'avant :
// regardée dans l'axe du soleil elle est plus claire et ambrée, dos à lui plus froide que
// le ciel qui la nourrit. Cet écart ne vaut que pour l'air proche et s'éteint au loin, où
// le voile rejoint le dôme exactement : c'est ce qui fond l'horizon au lieu d'y tracer
// une ligne.
// `lointain` : passé `pres` mètres, l'épaisseur croît `lointain` fois moins vite. Réglée pour
// les cours, la densité noyait tout au-delà de cinq cents mètres, la ville autour avec, et le
// Heikhal vu de la place du Kotel, vingt-cinq mètres plus bas dans un air plus dense.
const AIR = { densite: 4e-3, epaisseur: 110, effacement: [3800, 5600], pres: 150, lointain: 0.05,
              froid: [0.90, 0.94, 1.06], chaud: [1.20, 1.08, 0.92] };

const HALO_DU_SOLEIL = [1.00, 0.84, 0.58];
const VU = { haut: 0x4d7fb8, bas: 0xd8dcd4, sol: 0xa89c86, ambiance: 1.0,
             soleil: 2.2, etendue: 7e-5, horizon: 6.0, halo: HALO_DU_SOLEIL, etoiles: 0 };
// Le dôme ÉCLAIRANT tient trois réglages que la scène ne sait pas calculer seule.
//
// `ambiance` pèse sur le dégradé et jamais sur le disque : c'est le rapport du soleil à
// ce qui n'en vient pas, et sur une face horizontale il était renversé. Une dalle au
// soleil ne devait qu'un cinquième de sa clarté au soleil et quatre cinquièmes au ciel
// — mesurée à 1,13 fois l'ombre voisine, quand une cour de Jérusalem en rend deux et
// demie. C'est ce rapport-là, et pas la teinte, qui donnait le chantier : une ombre
// qu'on ne voit pas est une scène sans soleil, donc sans heure et sans relief.
//
// `haut` n'est pas le bleu du ciel. Sous un soleil de 20°, une face horizontale ne
// reçoit du soleil qu'un tiers de ce qu'en prend un parement : c'est le zénith qui
// décide de la couleur du dallage, et à 0x8fa5bd il en faisait du béton — un chroma
// mesuré à 1/255, du côté froid du gris, sur la moitié basse de chaque cadre. Il n'est
// pas neutre pour autant : une dalle à l'ombre, dans une cour dont les murs sont au
// soleil, reçoit d'eux un rebond chaud qu'aucune passe ne calcule ici, et sans lui elle
// retombe en béton une seconde fois. Le bleu, lui, reste au dôme qu'on VOIT.
//
// `sol` est le rebond du dallage, et rien d'autre : il suit le dallage quand il change.
// Il a porté 0xc9b795 quand la cour était ocre, puis 0xc4bcae le temps qu'elle soit
// grise ; le rovad est revenu dans le meleke des murs (MAT_SOL), son rebond avec.
const ECLAIRANT = { haut: 0xb2aa9c, bas: 0xe0d9c9, sol: 0xcdc0a8, ambiance: 0.45,
                    soleil: 3.5, etendue: 1.6e-3, horizon: 26.0, halo: HALO_DU_SOLEIL, etoiles: 0 };

// La nuit après le premier jour de Souccot (Soucca 5:2) : le 16 Tishri, la lune est pleine et
// se lève à l'est au coucher du soleil. Elle prend donc la place du soleil du matin, disque compris.
const VU_NUIT = { haut: 0x0a1222, bas: 0x1a2436, sol: 0x121212, ambiance: 1.0,
                  soleil: 1.4, etendue: 7e-5, horizon: 6.0, halo: [0.05, 0.06, 0.08], etoiles: 0.8 };
const ECLAIRANT_NUIT = { haut: 0x1e2636, bas: 0x262e3c, sol: 0x2a2620, ambiance: 0.45,
                         soleil: 0.25, etendue: 1.6e-3, horizon: 26.0, halo: [0.02, 0.02, 0.03], etoiles: 0 };
const CIELS = { jour: { vu: VU, eclairant: ECLAIRANT }, nuit: { vu: VU_NUIT, eclairant: ECLAIRANT_NUIT } };

// Le dégradé des deux dômes, et le ciel que l'air ajoute à ce qu'il éloigne.
const DEGRADE = /* glsl */`
  vec3 degradeCiel(float h, float s, vec3 haut, vec3 bas, vec3 sol, float ambiance, float horizon, vec3 halo){
    vec3 c = ambiance * (h > 0.0 ? mix(bas, haut, pow(h, 0.55))
                                 : mix(bas, sol, min(-h * horizon, 1.0)));
    // Trois portées : la moitié du ciel se réchauffe vers le soleil, le halo se
    // resserre autour, le disque tient dans son étendue.
    return c + halo * (0.10 * pow(s, 4.0) + 0.45 * pow(s, 160.0));
  }`;

function dome(rayon, teintes) {
  return new THREE.Mesh(
    new THREE.SphereGeometry(rayon, 64, 32),
    new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { hautCiel: { value: new THREE.Color(teintes.haut) },
                  basCiel: { value: new THREE.Color(teintes.bas) },
                  solCiel: { value: new THREE.Color(teintes.sol) },
                  dirSoleil: { value: SOLEIL },
                  ambiance: { value: teintes.ambiance },
                  soleil: { value: teintes.soleil },
                  etendue: { value: teintes.etendue },
                  horizon: { value: teintes.horizon },
                  halo: { value: new THREE.Vector3(...teintes.halo) },
                  etoiles: { value: teintes.etoiles } },
      vertexShader: /* glsl */`
        varying vec3 vD;
        void main(){ vD = position;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: /* glsl */`
        uniform vec3 hautCiel, basCiel, solCiel, dirSoleil;
        uniform vec3 halo;
        uniform float ambiance, soleil, etendue, horizon, etoiles;
        varying vec3 vD;
        ${DEGRADE}
        void main(){
          vec3 d = normalize(vD);
          float s = max(dot(d, dirSoleil), 0.0);
          vec3 c = degradeCiel(d.y, s, hautCiel, basCiel, solCiel, ambiance, horizon, halo);
          c += vec3(1.00, 0.95, 0.86) * soleil
             * smoothstep(1.0 - etendue, 1.0 - 0.3 * etendue, s);
          vec3 q = d * 420.0;
          float tirage = fract(sin(dot(floor(q), vec3(127.1, 311.7, 74.7))) * 43758.5453);
          float etoile = max(tirage - 0.996, 0.0) * 250.0 * smoothstep(0.35, 0.0, length(fract(q) - 0.5));
          c += etoiles * etoile * smoothstep(0.0, 0.2, d.y) * vec3(0.85, 0.92, 1.0);
          gl_FragColor = vec4(c, 1.0);
        }`,
    }));
}

export function domeVu(rayon) {
  const m = dome(rayon, VU);
  m.frustumCulled = false;
  return m;
}

export function environnement(renderer, moment = "jour") {
  const pmrem = new THREE.PMREMGenerator(renderer);
  const cible = pmrem.fromScene(new THREE.Scene().add(dome(20, CIELS[moment].eclairant)), 0.04, 0.1, 200);
  pmrem.dispose();
  return cible.texture;
}

export function peindreDome(domeVu, moment) {
  const teintes = CIELS[moment].vu;
  const { uniforms } = domeVu.material;
  for (const cle of ["haut", "bas", "sol"]) uniforms[`${cle}Ciel`].value.set(teintes[cle]);
  for (const cle of ["ambiance", "soleil", "etendue", "horizon", "etoiles"]) uniforms[cle].value = teintes[cle];
  uniforms.halo.value.set(...teintes.halo);
}

// Le voile est tiré du ciel de jour ; la couleur de la brume le ramène à celui du moment.
export function teinterAir(brume, moment) {
  const jour = new THREE.Color(VU.bas), voulu = new THREE.Color(CIELS[moment].vu.bas);
  brume.color.setRGB(voulu.r / jour.r, voulu.g / jour.g, voulu.b / jour.b);
}

const litteral = (c) => `vec3(${c.map((x) => x.toFixed(4)).join(", ")})`;

// La brume de three remplacée à la source : toute matière qui la reçoit — pierre, or,
// étoffes, figurants — passe par le même air, et `scene.fog = null` l'éteint encore.
// Le rayon vient de la position vue, que toute matière écrit, skinnée ou non.
export function brumer(scene) {
  const teinte = (hex) => litteral(new THREE.Color(hex).toArray());
  Object.assign(THREE.ShaderChunk, {
    fog_pars_vertex: "#ifdef USE_FOG\nvarying vec3 vRayonAir;\n#endif",
    fog_vertex: "#ifdef USE_FOG\nvRayonAir = mvPosition.xyz * mat3(viewMatrix);\n#endif",
    fog_pars_fragment: /* glsl */`
      #ifdef USE_FOG
        uniform float fogDensity;
        uniform vec3 fogColor;
        varying vec3 vRayonAir;
        ${DEGRADE}
        vec3 voiler(vec3 couleur, vec3 rayon){
          float longueur = length(rayon);
          vec3 d = rayon / max(longueur, 1e-4);
          // Moyenne de e^(-y/H) le long du rayon : (1 - e^-m)/m avec m = Δy/H, 1 - m/2 à plat.
          float m = rayon.y / ${AIR.epaisseur.toFixed(1)};
          float moyenne = abs(m) > 1e-3 ? (1.0 - exp(-m)) / m : 1.0 - 0.5 * m;
          float traversee = min(longueur, ${AIR.pres.toFixed(1)}) + max(longueur - ${AIR.pres.toFixed(1)}, 0.0) * ${AIR.lointain.toFixed(3)};
          float epaisseur = fogDensity * exp(-cameraPosition.y / ${AIR.epaisseur.toFixed(1)}) * traversee * moyenne;
          float transmis = exp(-epaisseur)
            * (1.0 - smoothstep(${AIR.effacement[0].toFixed(1)}, ${AIR.effacement[1].toFixed(1)}, longueur));
          float versSoleil = dot(d, ${litteral(SOLEIL.toArray())});
          vec3 ciel = fogColor * degradeCiel(d.y, max(versSoleil, 0.0), ${teinte(VU.haut)}, ${teinte(VU.bas)},
                                 ${teinte(VU.sol)}, ${VU.ambiance.toFixed(3)}, ${VU.horizon.toFixed(3)}, ${litteral(VU.halo)});
          float cote = versSoleil * 0.5 + 0.5;
          vec3 air = mix(${litteral(AIR.froid)}, ${litteral(AIR.chaud)}, cote * cote);
          return mix(ciel * mix(vec3(1.0), air, transmis), couleur, transmis);
        }
      #endif`,
    fog_fragment: "#ifdef USE_FOG\ngl_FragColor.rgb = voiler(gl_FragColor.rgb, vRayonAir);\n#endif",
  });
  scene.fog = new THREE.FogExp2(0xffffff, AIR.densite);
  return scene.fog;
}
