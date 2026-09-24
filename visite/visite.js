import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { computeBoundsTree, acceleratedRaycast } from "three-mesh-bvh";
import { habiller, assombrir, ETOFFES, HAUTEUR_IMAGE, EXPOSITION } from "./matieres.js";
import { nappes } from "./nappes.js";
import { cartesLumiere, cartesOcclusion, rechargerCartes } from "./occlusion.js";
import { adaptation } from "./adaptation.js";
import { DANS_HEIKHAL, separerDuHeikhal, sonderHeikhal } from "./sonde.js";
import { chaine } from "./chaine.js";
import { niveauxDeDetail } from "./detail.js";
import { astreDu, brumer, domeVu, environnement, peindreDome, teinterAir } from "./ciel.js";
import { epargner as epargnerOmbres, regler as reglerOmbres } from "./ombres.js";
import { PROFIL, plafonner } from "./qualite.js";
import { regulerEchelle } from "./echelle.js";
import { commandes } from "./pilotage.js";
import { nomDeZone, panneau } from "./fiche.js";
import { initiation } from "./initiation.js";
import { oeilQuiCadre, unirEmprises } from "./cadrage.js";
import { lieuxSouterrains, plan } from "./plan.js";
import { cinema } from "./cinema.js";
import { parcours } from "./parcours.js";
import { TEMPS_FLAMME, flamme } from "./flamme.js";
import { LANGUE_SOURCE, ecrire, installerLangue, langue, langueChoisie, libelle, suivreLangue, texte } from "./langue.js";

const AMA = 0.48;
const OEIL = 1.55;        // yeux d'un homme de l'époque (1,65 m), sous les 1,75 m des silhouettes
const RAYON = 0.38;       // demi-largeur du marcheur
// Les degrés du 'Heil, de Nikanor et de l'Oulam font tous 1/2 ama — 0,24 m de haut
// comme de giron. La garde se place juste au-dessus de MONTEE et ne porte qu'à une
// peau : la première contremarche qu'elle voit est deux girons plus loin, jamais
// celle qu'on s'apprête à gravir.
// MONTEE suit la plus haute marche du parcours : celle d'une ama qui porte le Doukhan
// (Middot 2:6, selon R. Eliézer ben Yaakov), sur toute la largeur de la cour. À 0,28 m, l'Azara restait hors d'atteinte.
const MARCHE = 0.5 * 0.48; // 1/2 ama
const MONTEE = AMA + 0.02;
const CHUTE = 0.60;        // au-delà, il n'y a pas de sol : le pas est refusé
const FENTE = 0.25;        // un pied : le vide plus étroit que lui s'enjambe sans y penser
// Ce qu'un repère d'entrée peut manquer son sol, en plus ou en moins. Il donne sa
// hauteur à la main, et la fenêtre de la marche est celle d'un pas : trois des neuf
// étaient 2,5 amot au-dessus de leur dallage, et on s'y posait en l'air.
const APLOMB = 1.5;
const PAS = 3.4;          // m/s
const COURSE = 2.4;       // multiplicateur
const GARDE = 0.06;       // peau du rayon de garde, devant le marcheur
const SOUS_PAS = 0.12;    // MARCHE - GARDE : le pas d'intégration qui ne saute rien
const VOL = 9.0;          // m/s en vol libre
// Le pas ne s'établit ni ne s'éteint d'un coup : une vitesse qui bascule de 0 à 3,4
// m/s à l'image près se lit en saccade, et c'est elle qu'on prend pour un manque de
// framerate. 0,09 s, c'est trente centimètres de glissé à l'arrêt — le pied qui se pose.
const REPONSE = 0.09;
const LISSAGE_REGARD = 0.045;

// Une étoffe ne barre pas le passage. La parokhet en particulier : le Cohen Gadol la
// franchit, et une visite qui s'arrête devant elle n'atteint jamais le Kodesh
// HaKodashim. Elles restent visibles et interrogeables, seulement traversables.
// Le Soreg y figure pour une autre raison : le blockout le pose continu sur tout le
// pourtour, sans les ouvertures qu'il avait (Middot 2:3). S'y cogner, ce serait buter
// sur un manque du modèle, pas sur l'architecture.
const TRAVERSABLES = new Set(["parokhet", "chaines_devir", "soreg"]);

// Un rayon de three teste la sphère puis la boîte englobantes du maillage, et sinon
// TOUS ses triangles. Il ne borne pas ces deux tests par sa portée : un rayon de garde
// de 18 cm tourné vers la vigne d'or de l'Oulam — 221 884 triangles à elle seule —
// les essaie tous avant de les rejeter sur la distance. La marche tire jusqu'à trente
// rayons par image, et c'est ce qu'on prend pour un manque de framerate. L'arbre les
// ramène à quelques dizaines de triangles chacun ; il se construit une fois, au
// chargement, et sert aussi au rayon qui interroge sous le curseur.
THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;

// ---------------------------------------------------------------------------
// données
// ---------------------------------------------------------------------------
const $ = (s) => document.querySelector(s);
const etat = $("#etat"), jauge = $("#jauge i");

// Une erreur de chargement laissait l'écran figé sur son dernier état sans rien dire :
// le voile ne se lève qu'en fin de module, et un module qui jette ne lève rien.
const echouer = (quoi) => {
  if (contexte?.isContextLost()) return quandContextePerdu();
  etat.textContent = `${texte("echec")} ${quoi}`;
  etat.style.color = "#e0836a";
};
addEventListener("error", (e) => echouer(e.message || e.error));
addEventListener("unhandledrejection", (e) => echouer(e.reason?.message || e.reason));

// Un iPhone à court de mémoire retire son contexte à la page : plus rien ne se dessine, et la compilation en cours
// jetait « shaderSource … must be an instance of WebGLShader ». Visite lancée, on attend que le navigateur le rende
// et on renvoie ce que three ne sait pas refaire seul (reprendre) ; pendant le chargement, ou s'il ne revient pas,
// la page se recharge d'elle-même. Une rechute aussitôt après ne boucle pas : elle le dit et attend qu'on touche l'écran.
let contexte = null;
let visiteLancee = false;
let derniereReprise = -Infinity;
let enReprise = false;
let contexteAbandonne = false;
const PERTE = "visite-contexte-perdu";
const RECHUTE_MS = 120000;
const ATTENTE_RESTITUTION_MS = 5000;
function lireStockage(cle) {
  try { return sessionStorage.getItem(cle); } catch { return null; }
}
function ecrireStockage(cle, valeur) {
  try { sessionStorage.setItem(cle, valeur); } catch { /* navigation privée : la page rechargera, sans garde-fou */ }
}
let contexteEnPerte = false;
function quandContextePerdu() {
  if (contexteEnPerte) return;
  contexteEnPerte = true;
  if (!visiteLancee || Date.now() - derniereReprise < RECHUTE_MS) return abandonnerContexte();
  attendreRestitution();
}
function attendreRestitution() {
  setTimeout(() => {
    if (!contexte.isContextLost()) return;
    if (document.hidden) return document.addEventListener("visibilitychange", attendreRestitution, { once: true });
    abandonnerContexte();
  }, ATTENTE_RESTITUTION_MS);
}
async function quandContexteRendu() {
  if (!contexteEnPerte || contexteAbandonne) return;
  contexteEnPerte = false;
  derniereReprise = Date.now();
  enReprise = true;
  try {
    await reprendre();
  } finally {
    enReprise = false;
  }
}
function abandonnerContexte() {
  contexteAbandonne = true;
  const rechute = Date.now() - Number(lireStockage(PERTE) ?? 0) < RECHUTE_MS;
  ecrireStockage(PERTE, String(Date.now()));
  if (!rechute) return location.reload();
  document.documentElement.classList.add("perdu");
  ecrire(etat, "contexte_perdu");
  etat.style.color = "";
  $("#chargement").onclick = () => location.reload();
}

// Le cachet que le build appose sur ./visite.js voyage jusqu'ici : les données qu'on
// demande par un nom construit le portent comme celles qu'il a pu réécrire.
const VERSION = new URL(import.meta.url).search;

async function json(chemin, obligatoire = true) {
  const r = await fetch(chemin + VERSION);
  if (!r.ok) {
    if (obligatoire) throw new Error(`${chemin} : ${r.status}`);
    return null;                                  // encyclopédie encore incomplète
  }
  return r.json();
}

const FICHIERS_CONTENU = ["a", "b", "c"];
const [textes, fiche, ...contenus] = await Promise.all([
  json("./textes.json"),
  json("./concepts.json"),
  ...FICHIERS_CONTENU.map((f) => json(`./contenu_${f}.json`, false)),
]);
installerLangue(textes);
// Encadrée par l'accueil, la scène marche seule et se tait : ni barre, ni fiche, ni initiation.
const CINEMA = new URLSearchParams(location.search).has("cinema");
document.documentElement.classList.toggle("cinema", CINEMA);
// Une troupe pour la visite libre, une par parcours : chacune descend la première fois qu'on la demande.
// Chemins écrits en entier : empreintes.py ne signe que ceux qu'il lit.
const TROUPES = {
  figures: { glb: "./figures.glb", json: "./figures.json" },
  figures_tamid: { glb: "./figures_tamid.glb", json: "./figures_tamid.json" },
  figures_kippour: { glb: "./figures_kippour.glb", json: "./figures_kippour.json" },
  figures_shoeva: { glb: "./figures_shoeva.glb", json: "./figures_shoeva.json" },
};
const TROUPE_LIBRE = "figures";
const [reperes, { cadrages: CADRAGES_DU_PLAN }, haltesCinema, { parcours: PARCOURS }, ...distributions] =
  await Promise.all([json("./reperes.json"), json("./plan.json"), CINEMA ? json("./cinema.json") : null,
    json("./parcours.json"), ...Object.values(TROUPES).map((t) => json(t.json))]);
const figurants = Object.fromEntries(Object.keys(TROUPES).map((nom, i) => [nom, distributions[i]]));
// Un concept joué par plusieurs troupes — les Léviim, douze au tamid, deux en visite libre — prend la boîte de toutes.
const unirBoites = (a, b) => (a ? {
  min: a.min.map((v, k) => Math.min(v, b.min[k])),
  max: a.max.map((v, k) => Math.max(v, b.max[k])),
} : b);
for (const { emprises, vues } of distributions) {
  for (const [id, boite] of Object.entries(emprises)) reperes.emprises[id] = unirBoites(reperes.emprises[id], boite);
  reperes.vues.push(...vues.filter((vue) => !reperes.vues.some((v) => v.id === vue.id)));
}
const enBoite = (b) => new THREE.Box3(new THREE.Vector3(...b.min), new THREE.Vector3(...b.max));
const EMPRISES = new Map(Object.entries(reperes.emprises).map(([id, b]) => [id, enBoite(b)]));

const traductions = new Map();
function contenusTraduits(code) {
  if (!traductions.has(code)) {
    traductions.set(code, Promise.all(FICHIERS_CONTENU.map((f) => json(`./contenu_${f}.${code}.json`, false))));
  }
  return traductions.get(code);
}

const apport = (contenusDuFichier, id) => contenusDuFichier.find((x) => x && x[id])?.[id] || {};

async function conceptsEn(code) {
  const traduits = code === LANGUE_SOURCE ? [] : await contenusTraduits(code);
  return new Map(fiche.concepts.map((c) =>
    [c.id, { ...c, ...apport(contenus, c.id), ...apport(traduits, c.id) }]));
}

const CONCEPTS = await conceptsEn(langue());

// ---------------------------------------------------------------------------
// scène
// ---------------------------------------------------------------------------
// Pas de profondeur logarithmique : écrite depuis le nuanceur, elle éteint le test de
// profondeur anticipé, et tout ce que les murs cachent passait par la matière — le
// Heikhal ombrait la cour entière derrière lui. Le tampon linéaire départage encore les
// 4,8 cm du placage d'or à trois cents mètres.
const renderer = new THREE.WebGLRenderer({ powerPreference: "high-performance" });
renderer.toneMapping = THREE.ACESFilmicToneMapping;
const EXPOSITION_DEHORS = 0.68;
renderer.toneMappingExposure = EXPOSITION_DEHORS;
EXPOSITION.value = renderer.toneMappingExposure;
renderer.shadowMap.enabled = true;
// Le profil lourd ne s'en sert pas : `ombres.js` y remplace la lecture de la carte
// par une pénombre variable. Il reste le réglage du profil léger, qui garde celle-ci.
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);
contexte = renderer.getContext();
renderer.domElement.addEventListener("webglcontextlost", quandContextePerdu);
renderer.domElement.addEventListener("webglcontextrestored", quandContexteRendu);

const scene = new THREE.Scene();
const brume = brumer(scene);
const AIR_DEHORS = brume.density;

// La lumière de chaque moment qu'un parcours demande. La nuit est celle de Sim'hat Beit HaSho'éva
// (Soucca 5:2) : le 16 Tishri, la lune pleine se lève à l'est, là où la visite pose son soleil du matin.
// La lumière cuite est celle du ciel de jour : la nuit n'en garde que ce que la lune en laisse.
// Au chant du coq, la même lune, couchante à l'ouest (ciel.js).
// Avant l'aube, sans lune, et à l'aube, sans soleil, l'astre n'est plus que la lueur de l'est.
// `feu` : le feu de l'autel, qui brûle toute la nuit (Vayikra 6:2) et que le jour noie.
const ECLAIRAGES = {
  jour: { astre: { couleur: 0xffd6a0, intensite: 4.9 }, appoint: 0.12, ciel: 0.16, cuite: 1, shoeva: false, feu: false },
  nuit: { astre: { couleur: 0xa9bde0, intensite: 0.35 }, appoint: 0, ciel: 0.008, cuite: 0.05, shoeva: true, feu: true },
  fin_de_nuit: { astre: { couleur: 0xa9bde0, intensite: 0.35 }, appoint: 0, ciel: 0.008, cuite: 0.05, shoeva: true, feu: true },
  avant_l_aube: { astre: { couleur: 0xa9bde0, intensite: 0 }, appoint: 0, ciel: 0.05, cuite: 0.12, shoeva: false, feu: true },
  aube: { astre: { couleur: 0xb4c0d8, intensite: 0.6 }, appoint: 0.03, ciel: 0.05, cuite: 0.25, shoeva: false, feu: true },
};

// L'ambiance ne doit PAS peser autant que le soleil. À 0,75 contre 1,9, chaque face
// recevait presque autant de lumière sans direction que de lumière du matin : le
// calcaire y perdait sa teinte et le modelé avec, et les murs rendaient un aplat gris.
// Le rapport compte plus que les niveaux — même arbitrage que le ciel du blockout.
// Elle descend une seconde fois, avec `ambiance` dans ciel.js : ce que ce réglage-ci
// corrigeait pour les parements, il restait à le corriger pour tout ce qui est à plat.
const cielAmbiant = new THREE.HemisphereLight(0xd5dbe0, 0x9c8b6c, ECLAIRAGES.jour.ciel);
scene.add(cielAmbiant);
// Matin, à l'est : l'axe de l'avoda, et la lumière qui rase la façade. Plus bas sur
// l'horizon, le soleil traverse plus d'atmosphère : il perd de la force et gagne de
// l'ambre, et c'est ce qui empêche un rasant de rendre le calcaire crayeux.
const soleil = new THREE.DirectionalLight(ECLAIRAGES.jour.astre.couleur, ECLAIRAGES.jour.astre.intensite);
reglerOmbres(soleil);
epargnerOmbres();
scene.add(soleil, soleil.target);
const appoint = new THREE.DirectionalLight(0xb9c6d4, ECLAIRAGES.jour.appoint);  // rebond du ciel à l'ouest
appoint.position.set(-140, 70, -40);
scene.add(appoint);

// Le soleil est posé loin devant la caméra, pas à sa hauteur : la fenêtre d'ombre le
// suit, et il faut que ce qui la surplombe — la façade fait cinquante mètres — tienne
// entre son `near` et son `far`.
const RECUL_SOLEIL = 200;

const ciel = domeVu(5700);
scene.add(ciel);
// L'or est métallique : sans environnement à réfléchir, il rend noir.
const reflets = { jour: environnement(renderer) };
scene.environment = reflets.jour.texture;

// Le champ est fixé à l'HORIZONTALE, pas à la verticale. Un champ vertical constant
// vaut 94° de large en 16/9 et 31° sur un téléphone tenu debout : on y visiterait le
// Temple par une paille. Le vertical est donc déduit du format, et seulement borné —
// au-delà de 80° un portrait étroit tournerait au fisheye.
const FOV_HORIZONTAL = 94;
const FOV_VERTICAL = [50, 80];
const camera = new THREE.PerspectiveCamera(62, innerWidth / innerHeight, 0.12, 6000);
// La lampe de tête, là seulement où la lumière cuite laisse noir ; l'emprise du Heikhal couvre aussi ses cellules.
const LAMPE_TETE = 6;
const LAMPE_PAR_LIEU = { heikhal: 0.6, kodesh_hakodashim: 0.5, taim: LAMPE_TETE,
  ...Object.fromEntries([...lieuxSouterrains(CADRAGES_DU_PLAN)].map((lieu) => [lieu, LAMPE_TETE])) };
const lampe = new THREE.PointLight(0xffe9c4, 0, 26, 1.7);
camera.add(lampe);
scene.add(camera);

// L'Arche éclaire le Kodesh HaKodashim : « עד שלא ניטל הארון היה נכנס ויוצא לאורו של ארון »
// (Yerushalmi Yoma 5:3, fiche §8e) — une lumière posée entre les keruvim, qui ne vacille
// pas et dont la portée meurt avant les murs. Les braises de la ma'hta, elles, vacillent à
// la mesure d'un bassin de charbons — pas d'une flamme : deux sinus incommensurables et un
// peu de hasard, jamais une période. Elles ne sont plus que le point chaud de la pièce.
const ARCHE = { couleur: 0xffeed2, intensite: 9, portee: 6, carte: 512 };
// Remonter `intensite` rallume les stries d'auto-ombre sur la calotte des keruvim : les regarder avant de conclure.
const BRAISE = { couleur: 0xff7a2a, intensite: 6, portee: 8, carte: 512 };
let braise = null;
let vacillement = 0;
// Le feu de l'autel, une lampe au-dessus des ma'arakhot : de nuit, la seule lumière de l'Azara (Tamid 1:4).
const FEU = { couleur: 0xff8a3a, intensite: 600, portee: 60, carte: 1024, hauteur: 3.0 };
let feuDeLAutel = null;

// La scène ne bouge pas : la carte cubique se calcule une fois, au premier rendu.
function poserLampe(reglage, position, ombrage) {
  const carte = Math.min(reglage.carte, ombrage.carte);
  const lumiere = new THREE.PointLight(reglage.couleur, reglage.intensite, reglage.portee, 2);
  lumiere.position.copy(position);
  lumiere.castShadow = ombrage.ombre;
  lumiere.shadow.autoUpdate = false;
  lumiere.shadow.needsUpdate = true;
  lumiere.shadow.mapSize.set(carte, carte);
  lumiere.shadow.camera.near = 0.05;
  lumiere.shadow.camera.far = reglage.portee;
  lumiere.shadow.bias = -0.002;
  // Pas de `normalBias` ici, contrairement au soleil : ces trois lampes éclairent des
  // objets plus fins que le décalage qu'il faudrait. Une penne d'aile fait 2,5 mm, et
  // 2 cm — l'ordre de grandeur qui vaut pour le soleil — la traversent : la lumière
  // passe sous les ailes, les keruvim perdent l'ombre propre de leur visage et les
  // marches du Heikhal voient la leur se décoller du sol.
  scene.add(lumiere);
  return lumiere;
}

function eclairerKodeshHakodashim(arche, braises) {
  if (!arche?.length || !braises?.length) return;
  const lumiereArche = poserLampe(ARCHE, new THREE.Vector3(...arche[0]), PROFIL.sanctuaire);
  braise = poserLampe(BRAISE, new THREE.Vector3(...braises[0]), PROFIL.sanctuaire);
  // La pièce n'a aucune ouverture, mais le ciel y entrait quand même — par l'ambiance, par
  // le rebond, par l'or qui le réfléchit. La pénombre est dans la pièce, pas dans le
  // temps : elle se lit sur la position de chaque point, et la fumée y prend la lumière
  // des deux sources.
  assombrir(EMPRISES.get("kodesh_hakodashim"));
  rendu.enfumer(EMPRISES.get("kodesh_hakodashim"), braise.position, lumiereArche.position);
}

function vaciller(dt) {
  vacillement += dt;
  const t = vacillement;
  TEMPS_FLAMME.value = t;
  const eclat = ECLAIRAGES[moment].shoeva ? SHOEVA.intensite : 0;
  shoeva?.lampes.forEach((l, i) => {
    l.intensity = eclat * (0.93 + 0.04 * Math.sin(t * 7.3 + i) + 0.03 * Math.sin(t * 17.9 + i * 2.1));
  });
  if (shoeva?.lueur) shoeva.lueur.intensity = eclat ? LUEUR.intensite * (0.9 + 0.1 * Math.sin(t * 11.3)) : 0;
  if (lumiereMenora) {
    lumiereMenora.intensity = MENORA.intensite * (0.95 + 0.03 * Math.sin(t * 9.1) + 0.02 * Math.sin(t * 23.0 + 2.0));
  }
  if (feuDeLAutel) {
    feuDeLAutel.intensity = ECLAIRAGES[moment].feu ? FEU.intensite * (0.9 + 0.06 * Math.sin(t * 2.3) + 0.04 * Math.sin(t * 6.1 + 1.3)) : 0;
  }
  if (!braise) return;
  const souffle = 0.86 + 0.09 * Math.sin(t * 1.7) + 0.05 * Math.sin(t * 4.3 + 1.0) + 0.04 * (Math.random() - 0.5);
  braise.intensity = BRAISE.intensite * souffle;
}

// L'or est métallique, il ne diffuse rien : sous 150 cd l'environnement couvre l'ombre du Shoulkhan, à 600 le mur brûle.
const MENORA = { couleur: 0xffe1aa, intensite: 150, portee: 18, carte: 512 };
let lumiereMenora = null;

function allumerMenora(flammes) {
  if (!flammes?.length) return;
  const centre = new THREE.Vector3();
  flammes.forEach((p, i) => {
    const meche = flamme(i * 2.39);
    meche.position.set(...p);
    scene.add(meche);
    horsGeometrie.push(meche);
    centre.add(meche.position);
  });
  // Au-dessus des mèches et non entre elles : à un doigt de la lampe du milieu, son or brûlait.
  const point = centre.divideScalar(flammes.length).add(new THREE.Vector3(0, 0.35, 0));
  lumiereMenora = poserLampe(MENORA, point, PROFIL.sanctuaire);
}

// Les mâts d'or de l'Ezrat Nashim, qui ne brûlent que la nuit de Sim'hat Beit HaSho'éva (Soucca 5:2).
const SHOEVA = { couleur: 0xffc58a, intensite: 600, portee: 200, carte: 1024 };
const HAUTEUR_FLAMME_SHOEVA = 1.2;
// Les torches de la ronde, en une lueur sans ombre : une lampe par torche, c'est un nuanceur par torche.
const LUEUR = { couleur: 0xffa860, intensite: 40, portee: 16, hauteur: 1.5 };   // m : des mèches de caleçons et de ceintures de cohanim (Soucca 5:3)
let moment = "jour";
let directionDeLAstre = astreDu(moment);
let shoeva = null;
let lumiereCuiteDuCiel = null;

// Le Heikhal et le Kodesh HaKodashim ont leur lumière cuite à leurs propres lampes, que la nuit n'éteint pas.
function eclaireParSesLampes(maillage) {
  if (sousSonde.has(maillage)) return true;
  const centre = maillage.geometry.boundingBox.getCenter(new THREE.Vector3()).applyMatrix4(maillage.matrixWorld);
  return EMPRISES.get("kodesh_hakodashim").containsPoint(centre);
}

// De proche en proche : deux points à moins de `pas` l'un de l'autre sont du même groupe.
function centresDesGroupes(points, pas) {
  let groupes = [];
  for (const p of points) {
    const voisins = groupes.filter((g) => g.some((q) => q.distanceTo(p) < pas));
    groupes = [...groupes.filter((g) => !voisins.includes(g)), [p, ...voisins.flat()]];
  }
  return groupes.map((g) => g.reduce((somme, p) => somme.add(p), new THREE.Vector3()).divideScalar(g.length));
}

// Le bord des coupes est le plus haut du mât : ses sommets, groupés, donnent le centre de chacune.
function coupesDeLaShoeva(candelabres) {
  const sommets = [];
  for (const o of candelabres) {
    const position = o.geometry.attributes.position;
    for (let i = 0; i < position.count; i++) {
      sommets.push(new THREE.Vector3().fromBufferAttribute(position, i).applyMatrix4(o.matrixWorld));
    }
  }
  const haut = sommets.reduce((max, p) => Math.max(max, p.y), -Infinity);
  return centresDesGroupes(sommets.filter((p) => p.y > haut - 0.02), 0.25);
}

// Une lampe par mât, au milieu de ses quatre coupes : seize lampes à carte d'ombre, c'est seize cubes à rendre.
function poserShoeva() {
  const candelabres = [];
  gltf.scene.traverse((o) => { if (o.isMesh && o.userData.concept === "candelabres_shoeva") candelabres.push(o); });
  const coupes = coupesDeLaShoeva(candelabres);
  const flammes = coupes.map((coupe, i) => {
    const meche = flamme(i * 2.39, HAUTEUR_FLAMME_SHOEVA);
    meche.position.copy(coupe).y -= 0.1;
    scene.add(meche);
    horsGeometrie.push(meche);
    return meche;
  });
  const lampes = centresDesGroupes(coupes, 2).map((mat) =>
    poserLampe(SHOEVA, mat.add(new THREE.Vector3(0, HAUTEUR_FLAMME_SHOEVA / 2, 0)), PROFIL.feux));
  return { candelabres, flammes, lampes, lueur: eclairerLaRonde(EMPRISES.get("hassidim_veanshei_maase")) };
}

function eclairerLaRonde(ronde) {
  if (!ronde) return null;
  const lueur = new THREE.PointLight(LUEUR.couleur, 0, LUEUR.portee, 2);
  ronde.getCenter(lueur.position).y += LUEUR.hauteur;
  scene.add(lueur);
  return lueur;
}

// L'intensité de jour de chaque lumière cuite au ciel seul, celle que le moment module.
function lumieresCuitesAuCiel() {
  const intensites = new Map();
  gltf.scene.traverse((o) => {
    if (o.isMesh && o.material.lightMap && !eclaireParSesLampes(o)) intensites.set(o.material, o.material.lightMapIntensity);
  });
  return intensites;
}

function allumerLeFeu() {
  const dessus = EMPRISES.get("maarakhot");
  const foyer = dessus.getCenter(new THREE.Vector3()).setY(dessus.max.y + FEU.hauteur);
  return poserLampe(FEU, foyer, PROFIL.feux);
}

// Les mâts et le feu ne sont posés qu'à la première nuit : le visiteur de jour n'en paie ni les lampes ni les nuanceurs.
async function passerAu(voulu) {
  if (voulu === moment) return;
  const quitte = moment;
  moment = voulu;
  const eclairage = ECLAIRAGES[voulu];
  soleil.color.set(eclairage.astre.couleur);
  soleil.intensity = eclairage.astre.intensite;
  directionDeLAstre = astreDu(voulu);
  ANCRE_OMBRE.set(Infinity, Infinity, Infinity);
  appoint.intensity = eclairage.appoint;
  cielAmbiant.intensity = eclairage.ciel;
  peindreDome(ciel, voulu);
  teinterAir(brume, voulu);
  reflets[voulu] ??= environnement(renderer, voulu);
  scene.environment = reflets[voulu].texture;
  // Le ciel de jour revient à la fin de chaque parcours ; celui d'un autre moment se refait en un fondu s'il revient.
  if (quitte !== "jour") {
    reflets[quitte].dispose();
    delete reflets[quitte];
  }
  lumiereCuiteDuCiel ??= lumieresCuitesAuCiel();
  for (const [materiau, intensite] of lumiereCuiteDuCiel) materiau.lightMapIntensity = intensite * eclairage.cuite;
  const feuAllume = feuDeLAutel === null && eclairage.feu;
  if (feuAllume) feuDeLAutel = allumerLeFeu();
  const premiere = shoeva === null && eclairage.shoeva;
  if (premiere) shoeva = poserShoeva();
  if (shoeva !== null) {
    for (const f of shoeva.flammes) f.visible = eclairage.shoeva;
    // Les coupes sont sous la lampe de leur mât : leur ombre posait quatre disques noirs sur les murs.
    for (const o of shoeva.candelabres) o.castShadow = !eclairage.shoeva;
  }
  if (premiere || feuAllume) await rendu.compiler();
}

// Le dôme n'entre pas dans la passe de géométrie : il enveloppe la scène, et il l'occluerait
// tout entière. Les flammes de la Menora non plus : elles ne sont pas une surface à ombrer.
const horsGeometrie = [ciel];
const rendu = chaine(renderer, scene, camera, horsGeometrie);
const detail = niveauxDeDetail(scene, camera);
// Le film veut chaque image au plein détail, sans qu'un allègement arrivé en cours de prise ne la change.
function alleger(racine) {
  if (CINEMA) return;
  const maillages = [];
  racine.traverse((o) => { if (o.isMesh) maillages.push(o); });
  detail.confier(maillages);
}

// La résolution suit ce que la machine tient. Baisser la définition d'un tiers coûte
// une image plus douce ; la garder coûte le mouvement, qui est ce qu'on est venu voir.
const DPR = Math.min(devicePixelRatio, PROFIL.dprMax);
let echelle = PROFIL.echelleDepart;

function dimensionner() {
  camera.aspect = innerWidth / innerHeight;
  const vertical = THREE.MathUtils.radToDeg(
    2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(FOV_HORIZONTAL) / 2) / camera.aspect));
  camera.fov = THREE.MathUtils.clamp(vertical, FOV_VERTICAL[0], FOV_VERTICAL[1]);
  camera.updateProjectionMatrix();
  // Taille d'abord : sans largeur CSS, la toile vaut 300 px × DPR et élargit la page sur mobile.
  renderer.setSize(innerWidth, innerHeight);
  renderer.setPixelRatio(DPR * Math.min(echelle, 1));
  const definition = Math.min(DPR, PROFIL.definitionMax) * echelle;
  HAUTEUR_IMAGE.value = Math.round(innerHeight * definition);
  rendu.redimensionner(innerWidth, innerHeight, definition);
}
dimensionner();
addEventListener("resize", dimensionner);

// ---------------------------------------------------------------------------
// modèle
// ---------------------------------------------------------------------------
const obstacles = [];

// Par tranches, et non d'un bloc : une seconde de calcul figeait la page, et un téléphone en met plusieurs.
const TRANCHE_MS = 30;
const rendreLaMain = () => new Promise((reprise) => {
  const canal = new MessageChannel();
  canal.port1.onmessage = () => reprise();
  canal.port2.postMessage(null);
});
async function construireArbres(maillages) {
  let debut = performance.now();
  for (const maillage of maillages) {
    maillage.geometry.computeBoundsTree({ maxLeafTris: 24 });
    if (performance.now() - debut < TRANCHE_MS) continue;
    await rendreLaMain();
    debut = performance.now();
  }
}
const restant = $("#restant");
const enMegaoctets = (octets) =>
  new Intl.NumberFormat(langue(), { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(octets / 1e6);
// Les nappes descendent PENDANT le .glb : elles pèsent la moitié de son poids, et les
// attendre ensuite doublerait l'attente d'un visiteur en 4G.
const chargeur = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const [gltf, jeux, occlusions, lumieres] = await Promise.all([
  chargeur.loadAsync("./temple.glb", (e) => {
      if (!e.lengthComputable) return;
      jauge.style.width = `${(e.loaded / e.total) * 100}%`;
      restant.textContent = e.loaded < e.total ? texte("restant").replace("{mo}", enMegaoctets(e.total - e.loaded)) : "";
    }),
  nappes(),
  cartesOcclusion(reperes.occlusion),
  cartesLumiere(reperes.lumiere),
]);
ecrire(etat, "preparation");
// Sans cette image, « préparation… » ne s'affichait jamais ; un onglet caché n'en donne aucune, d'où le délai.
await new Promise((suite) => {
  requestAnimationFrame(() => setTimeout(suite));
  setTimeout(suite, 200);
});
scene.add(gltf.scene);
// Three ne calcule les matrices monde qu'au premier rendu, et un rayon ne les calcule
// pas : sans ça le tout premier `poser` sonde une scène encore à l'origine, ne trouve
// aucun sol, et la visite s'ouvrait un mètre au-dessus du dallage.
gltf.scene.updateMatrixWorld(true);
allumerMenora(reperes.flammes);
eclairerKodeshHakodashim(reperes.arche, reperes.braises);

const murs = [];                        // collision : les étoffes en sont exclues
const horloges = [];                    // uniformes de temps à faire avancer
const brut = new URLSearchParams(location.search).has("brut");
const IDS = new Set(CONCEPTS.keys());
const habillees = new Set();
const materiauxHeikhal = [];

function conceptDe(objet) {
  for (let n = objet; n; n = n.parent) {
    const nom = n.name.replace(/_\d+$/, "");
    if (IDS.has(nom)) return nom;
  }
  return undefined;
}

const maillages = [];
gltf.scene.traverse((o) => {
  if (!o.isMesh) return;
  o.userData.concept = conceptDe(o);
  maillages.push(o);
});
const sousSonde = new Set(brut ? [] : separerDuHeikhal(
  maillages.filter((o) => DANS_HEIKHAL.has(o.userData.concept)), EMPRISES.get("heikhal")));

gltf.scene.traverse((o) => {
  if (!o.isMesh) return;
  o.geometry.computeBoundingBox();
  o.geometry.computeBoundingSphere();
  // Tout volume du blockout est une boîte fermée aux normales sortantes : ses faces
  // arrière ne sont jamais celles qu'on voit. Les afficher doublait le travail de
  // fragment, et faisait battre la face arrière du placage d'or contre la face avant
  // de la pierre qu'il couvre, qui sont exactement coplanaires. Seules les étoffes,
  // qu'on traverse, se regardent des deux côtés.
  o.material.side = ETOFFES.has(o.material.name) ? THREE.DoubleSide : THREE.FrontSide;
  o.castShadow = true;
  o.receiveShadow = true;
  if (!brut) {
    const occlusion = occlusions.get(o.userData.concept);
    const lumiere = lumieres.get(o.userData.concept);
    // Une matière est partagée entre concepts ; ses cartes cuites et son reflet ne le sont pas.
    if (occlusion || lumiere || sousSonde.has(o)) o.material = o.material.clone();
    if (occlusion) o.material.aoMap = occlusion;
    if (lumiere) Object.assign(o.material, { lightMap: lumiere.texture, lightMapIntensity: lumiere.echelle });
    if (sousSonde.has(o)) materiauxHeikhal.push(o.material);
  }
  if (!brut && !habillees.has(o.material.uuid)) {
    habillees.add(o.material.uuid);
    habiller(o.material, horloges, jeux);
  }
  obstacles.push(o);
  if (!TRAVERSABLES.has(o.userData.concept)) murs.push(o);
});
const oeilAdapte = adaptation(obstacles);

// Les nuanceurs se compilent hors du fil de la page pendant que les arbres s'y construisent.
await Promise.all([rendu.compiler(), construireArbres(obstacles)]);
if (!brut) {
  sonderHeikhal(renderer, scene, {
    kelim: unirEmprises(EMPRISES, ["menora", "shulchan", "mizbeach_hazahav"]),
    materiaux: materiauxHeikhal,
    lumieres: [soleil, appoint, lampe, cielAmbiant],
    caches: [ciel],
  });
  await rendu.compiler();                 // le reflet de la salle change les nuanceurs de son or
}

// Les figurants descendent après le Temple : la visite s'ouvre sans les attendre, et on les traverse.
const troupes = {};
const chargements = {};
const MARGE_GESTE = 0.35;
const EMPRISES_FIGURANTS = Object.fromEntries(Object.entries(figurants).map(([nom, { emprises }]) =>
  [nom, Object.values(emprises).map(enBoite)]));
// La voulue change à la demande, la présente sous le voile du fondu qui suit.
let troupeVoulue = TROUPE_LIBRE, troupePresente = TROUPE_LIBRE;
const PRISE = new THREE.MeshBasicMaterial();
const HAUTEUR_FLAMME_TORCHE = 0.3;

// Le clic vise une boîte portée par le figurant : un rayon sur un corps animé transforme chaque sommet en JavaScript.
function prendreEnMain(figurant) {
  const emprise = new THREE.Box3();
  figurant.traverse((o) => {
    if (!o.isMesh) return;
    o.material.side = ETOFFES.has(o.material.name) ? THREE.DoubleSide : THREE.FrontSide;
    o.castShadow = PROFIL.figurants.ombre;
    o.receiveShadow = true;
    if (!o.isSkinnedMesh) return;
    o.computeBoundingSphere();
    o.boundingSphere.radius += MARGE_GESTE;
    o.computeBoundingBox();
    emprise.union(o.boundingBox.clone().applyMatrix4(o.matrix));
  });
  const prise = new THREE.Mesh(new THREE.BoxGeometry(...emprise.getSize(new THREE.Vector3()).toArray()), PRISE);
  emprise.getCenter(prise.position);
  prise.visible = false;
  prise.userData.concept = conceptDe(figurant);
  figurant.add(prise);
  return prise;
}

// La tête d'étoupe est au bout du manche, sur l'axe y du maillage : la flamme s'y pose, droite, quoi que fasse la torche.
function allumerTorches(troupe) {
  const torches = [];
  troupe.traverse((o) => { if (o.isMesh && /_avouka(_\d+)?$/.test(o.name)) torches.push(o); });
  return torches.map((torche, i) => {
    torche.geometry.computeBoundingBox();
    const meche = flamme(i * 1.93, HAUTEUR_FLAMME_TORCHE);
    scene.add(meche);
    horsGeometrie.push(meche);
    return { torche, meche, bout: new THREE.Vector3(0, torche.geometry.boundingBox.max.y - 0.06, 0) };
  });
}

function suivreTorches(troupe) {
  if (!troupe.torches.length) return;
  troupe.scene.updateMatrixWorld();
  for (const { torche, meche, bout } of troupe.torches) meche.position.copy(bout).applyMatrix4(torche.matrixWorld);
}

// Les autres troupes se cachent, et leurs prises sortent de ce que le doigt vise.
function montrerTroupes() {
  for (const [nom, troupe] of Object.entries(troupes)) {
    const presente = nom === troupePresente;
    troupe.scene.visible = presente;
    for (const { meche } of troupe.torches) meche.visible = presente;
    for (const prise of troupe.prises) {
      const rang = obstacles.indexOf(prise);
      if (presente && rang < 0) obstacles.push(prise);
      if (!presente && rang >= 0) obstacles.splice(rang, 1);
    }
  }
}

// Un figurant se lit sur quelques centaines de pixels au plus : le profil léger ramène ses textures à cette mesure.
async function plafonnerTextures(racine) {
  const textures = new Set();
  racine.traverse((o) => {
    if (o.isMesh) for (const valeur of Object.values(o.material)) if (valeur?.isTexture) textures.add(valeur);
  });
  await Promise.all([...textures].map((t) => plafonner(t, PROFIL.textures.figurants)));
}

function rendreLaMemoire(maillages) {
  const materiaux = new Set(maillages.map((m) => m.material));
  for (const maillage of maillages) {
    maillage.geometry.dispose();
    maillage.skeleton?.dispose();
  }
  for (const materiau of materiaux) {
    for (const valeur of Object.values(materiau)) if (valeur?.isTexture) valeur.dispose();
    materiau.dispose();
  }
}

// Compilés avant d'entrer en scène : sinon la première image qui les voit fige la marche le temps de leurs nuanceurs.
async function poserFigurants({ scene: troupe, animations }) {
  await plafonnerTextures(troupe);
  const melangeur = new THREE.AnimationMixer(troupe);
  for (const clip of animations) melangeur.clipAction(clip).play();
  melangeur.update(0);
  troupe.updateMatrixWorld(true);
  const prises = troupe.children.map(prendreEnMain);
  const torches = allumerTorches(troupe);
  await rendu.compiler(troupe);
  return { scene: troupe, melangeur, prises, torches };
}

// Une troupe renvoyée pendant sa descente est libérée à l'arrivée, sans entrer en scène.
function chargerTroupe(nom) {
  if (chargements[nom]) return chargements[nom];
  const chargement = chargeur.loadAsync(TROUPES[nom].glb).then(poserFigurants).then((troupe) => {
    if (chargements[nom] !== chargement) return libererTroupe(troupe);
    scene.add(troupe.scene);
    troupe.scene.updateMatrixWorld(true);
    troupes[nom] = troupe;
    alleger(troupe.scene);
    suivreTorches(troupe);
    montrerTroupes();
  });
  chargements[nom] = chargement;
  return chargement;
}
chargerTroupe(TROUPE_LIBRE);

// Chaque troupe de parcours pèse des dizaines de textures : gardées toutes, les trois parcours menaient la mémoire GPU de 0,7 à 1,2 Go.
function libererTroupe({ scene: troupe, melangeur, prises, torches }) {
  scene.remove(troupe);
  for (const { meche } of torches) {
    scene.remove(meche);
    horsGeometrie.splice(horsGeometrie.indexOf(meche), 1);
    meche.material.dispose();
  }
  for (const prise of prises) {
    const rang = obstacles.indexOf(prise);
    if (rang >= 0) obstacles.splice(rang, 1);
    prise.geometry.dispose();
  }
  melangeur.stopAllAction();
  melangeur.uncacheRoot(troupe);
  const maillages = [];
  troupe.traverse((o) => { if (o.isMesh && o.material !== PRISE) maillages.push(o); });
  detail.oublier(maillages);
  rendreLaMemoire(maillages);
}

function renvoyerTroupe(nom) {
  const troupe = troupes[nom];
  delete chargements[nom];
  delete troupes[nom];
  if (troupe) libererTroupe(troupe);
}

function presenterTroupe(voulue) {
  troupePresente = voulue;
  montrerTroupes();
  for (const nom of Object.keys(chargements)) if (nom !== voulue && nom !== TROUPE_LIBRE) renvoyerTroupe(nom);
}

// Jérusalem autour du Temple descend en dernier : on s'y pose aussi, et on s'y cogne.
async function poserPays({ scene: pays }) {
  pays.updateMatrixWorld(true);
  const maisons = [];
  pays.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = true;
    o.receiveShadow = true;
    if (!brut && !habillees.has(o.material.uuid)) {
      habillees.add(o.material.uuid);
      habiller(o.material, horloges, jeux);
    }
    maisons.push(o);
  });
  await Promise.all([rendu.compiler(pays), construireArbres(maisons)]);
  obstacles.push(...maisons);
  murs.push(...maisons);
  scene.add(pays);
  alleger(pays);
}
chargeur.loadAsync("./pays.glb").then(poserPays);

// ---------------------------------------------------------------------------
// marche
// ---------------------------------------------------------------------------
const BAS = new THREE.Vector3(0, -1, 0);
const versLeBas = new THREE.Raycaster();
const versLAvant = new THREE.Raycaster();

const sonde = new THREE.Vector3();

function solSous(origine, portee) {
  versLeBas.set(origine, BAS);
  versLeBas.far = portee;
  // Une face tournée vers le bas — le dessous d'un mur posé sur la dalle — n'est pas
  // un sol : sans ce filtre on marche à l'intérieur des murs.
  for (const t of versLeBas.intersectObjects(murs, false)) {
    if (!t.face || t.face.normal.y > 0.25) return t.point.y;
  }
  return null;
}

function solEn(x, z, piedsY) {
  return solSous(sonde.set(x, piedsY + MONTEE, z), MONTEE + CHUTE);
}

// Le pas qui arrive sur du vide regarde un pied plus loin dans le même sens : une fente
// plus étroite qu'un pied ne fait tomber personne. Un quart d'ama d'air sépare la tête
// du kevesh de l'autel (Zeva'him 62b), un cheveu le petit kevesh du sovev — et le rayon
// de sol, tiré en un point, y tombait à chaque fois : l'autel ne se montait pas.
function solEnjambe(x, z, piedsY, direction) {
  return solEn(x, z, piedsY) ?? solEn(x + direction.x * FENTE, z + direction.z * FENTE, piedsY);
}

// Le rayon de garde part AU-DESSUS de ce qui est franchissable. Plus bas, il heurtait
// la deuxième marche avant qu'on ait gravi la première : les degrés du 'Heil et de
// Nikanor font 1/2 ama — 0,24 m — et un corps de 0,38 m de rayon en couvre deux. Tout
// ce qui est sous MONTEE se monte ; la garde ne juge donc que ce qui est au-dessus,
// et sa portée se limite à une peau, pas au rayon du corps.
function murDevant(depuis, piedsY, direction, distance) {
  versLAvant.far = distance + GARDE;
  for (const hauteur of [MONTEE + 0.02, 1.55]) {
    versLAvant.set(new THREE.Vector3(depuis.x, piedsY + hauteur, depuis.z), direction);
    if (versLAvant.intersectObjects(murs, false).length) return true;
  }
  return false;
}

let piedsY = 0;
const avant = new THREE.Vector3(), droite = new THREE.Vector3();
const HAUT = new THREE.Vector3(0, 1, 0), pas = new THREE.Vector3();
// Le clavier, le pouce et le pilote automatique aboutissent tous à `voulu` : la marche
// n'en connaît qu'un, et ses collisions valent donc pour les trois.
const voulu = new THREE.Vector3(), lisse = new THREE.Vector3();
let cible = null;

// Le Temple ne se laisse pas traverser n'importe où : on monte à l'Ezrat Nashim par
// les douze degrés du 'Heil, à l'Azara par les quinze marches, et l'autel se contourne.
// C'est l'architecture, pas un défaut — mais un modèle se regarde aussi d'ailleurs que
// d'où l'on a le droit de se tenir : le vol libre est là pour ça.
let vol = false;

function vitesseVoulue() {
  const vitesse = (vol ? VOL : PAS) * (manette.course ? COURSE : 1);
  const manuel = Math.abs(manette.long) + Math.abs(manette.lat) + Math.abs(manette.vert);
  if (manuel > 0.02) cible = null;
  if (cible) {
    voulu.copy(cible).sub(camera.position);
    if (!vol) voulu.y = 0;
    if (voulu.lengthSq() < (vol ? 1.4 : 0.36)) { cible = null; return voulu.set(0, 0, 0); }
    return voulu.normalize().multiplyScalar(vitesse);
  }
  camera.getWorldDirection(avant);
  if (!vol) avant.y = 0;
  avant.normalize();
  droite.crossVectors(avant, HAUT).normalize();
  voulu.set(0, 0, 0).addScaledVector(avant, manette.long).addScaledVector(droite, manette.lat);
  if (vol) voulu.addScaledVector(HAUT, manette.vert);
  // La diagonale ne va pas plus vite que le droit devant, mais un pouce à mi-course
  // marche à mi-vitesse : c'est la longueur qui est bridée, pas normalisée.
  const force = Math.min(voulu.length(), 1);
  return force < 1e-3 ? voulu.set(0, 0, 0) : voulu.normalize().multiplyScalar(vitesse * force);
}

function marcher(dt) {
  pas.set(lisse.x, 0, lisse.z);
  const vitesse = pas.length();
  if (vitesse < 0.02) return;
  pas.divideScalar(vitesse);
  // Le pas se découpe : à bas framerate un seul bond franchirait la garde.
  let reste = Math.min(vitesse * dt, 1.2);
  while (reste > 1e-4) {
    const distance = Math.min(reste, SOUS_PAS);
    reste -= distance;
    const x = camera.position.x + pas.x * distance, z = camera.position.z + pas.z * distance;
    const sol = murDevant(camera.position, piedsY, pas, distance) ? null : solEnjambe(x, z, piedsY, pas);
    if (sol === null) {                            // un mur, ou le vide : le pas est refusé
      lisse.set(0, 0, 0);                          // et l'élan avec, sinon il pousse contre
      cible = null;
      return;
    }
    piedsY = sol;
    camera.position.set(x, sol + OEIL, z);
  }
}

function avancer(dt) {
  vitesseVoulue();
  lisse.lerp(voulu, 1 - Math.exp(-dt / REPONSE));
  if (lisse.lengthSq() < 4e-4) {
    lisse.set(0, 0, 0);
    return;
  }
  if (!vol) return marcher(dt);
  camera.position.addScaledVector(lisse, dt);
  piedsY = camera.position.y - OEIL;
}

function poser([x, y, z]) {
  const sol = vol ? null : solSous(sonde.set(x, y + APLOMB, z), APLOMB * 2);
  piedsY = sol === null ? y : sol;
  camera.position.set(x, piedsY + OEIL, z);
  lisse.set(0, 0, 0);
  cible = null;
}

// Cap en degrés dans le repère de la fiche : 0 = est, 180 = ouest, l'axe du parcours du
// Cohen Gadol. Le nord de Blender devient -Z une fois passé en Y-haut.
function orienterCap({ cap, tangage = 0 }) {
  const a = THREE.MathUtils.degToRad(cap);
  const t = THREE.MathUtils.degToRad(tangage);
  const { x, y, z } = camera.position;
  camera.lookAt(x + Math.cos(a) * 10, y + Math.tan(t) * 10, z - Math.sin(a) * 10);
  accorderRegard();
}

function orienterVers(point) {
  camera.lookAt(point);
  accorderRegard();
}

function atterrir() {
  const { x, y, z } = camera.position;
  // Une marche au-dessus de l'œil : en rasant la dalle en vol, il a pu passer dessous.
  const sol = solSous(sonde.set(x, y + MONTEE, z), Infinity);
  if (sol === null) return false;
  piedsY = sol;
  camera.position.y = sol + OEIL;
  return true;
}

// ---------------------------------------------------------------------------
// regard
// ---------------------------------------------------------------------------
// Le regard suit le glissé, pas le curseur : bouton relâché, la souris redevient
// libre pour la barre du haut et la fiche. Il rejoint sa consigne au lieu d'y sauter :
// à 45 ms le retard ne se sent pas, et le tremblement du doigt ne passe plus.
const TANGAGE_MAX = Math.PI / 2 - 0.02;
const regard = new THREE.Euler(0, 0, 0, "YXZ");
const capVise = { lacet: 0, tangage: 0 };

function tourner(dLacet, dTangage) {
  capVise.lacet -= dLacet;
  capVise.tangage = THREE.MathUtils.clamp(capVise.tangage - dTangage, -TANGAGE_MAX, TANGAGE_MAX);
  noterRegard(Math.abs(dLacet) + Math.abs(dTangage));
}

// Après un `lookAt`, la consigne est ce que la caméra montre : sans ça le lissage
// ramènerait aussitôt le regard là où il était avant le déplacement.
function accorderRegard() {
  regard.setFromQuaternion(camera.quaternion);
  regard.z = 0;
  capVise.lacet = regard.y;
  capVise.tangage = regard.x;
}

function lisserRegard(dt) {
  const k = 1 - Math.exp(-dt / LISSAGE_REGARD);
  regard.y += (capVise.lacet - regard.y) * k;
  regard.x += (capVise.tangage - regard.x) * k;
  regard.z = 0;
  camera.quaternion.setFromEuler(regard);
}

// ---------------------------------------------------------------------------
// interrogation
// ---------------------------------------------------------------------------
const viseur = new THREE.Raycaster();
const PORTEE = 140;       // ce qu'un clic peut interroger
const ecran = new THREE.Vector2();
const survol = $("#survol");
const { montrer, fermer, rafraichir } = panneau(CONCEPTS);
let survole = null;

const normaliser = (clientX, clientY) =>
  ecran.set((clientX / innerWidth) * 2 - 1, -(clientY / innerHeight) * 2 + 1);

function conceptSous(coords) {
  viseur.setFromCamera(coords, camera);
  viseur.far = PORTEE;
  const touche = viseur.intersectObjects(obstacles, false);
  return touche.length ? touche[0].object.userData.concept || null : null;
}

function interroger(clientX, clientY) {
  const id = conceptSous(normaliser(clientX, clientY));
  if (!id) {
    fermer();
    return;
  }
  montrer(id);
  noterInterrogation();
}

// Le pilote automatique n'ouvre aucun passage : il pousse le marcheur vers le point
// visé avec la même commande qu'un pouce, donc les mêmes murs l'arrêtent. Un point
// qui n'a pas de sol sous lui — un mur, une corniche — ne se demande pas.
function seRendreA(clientX, clientY) {
  viseur.setFromCamera(normaliser(clientX, clientY), camera);
  viseur.far = 120;
  const [touche] = viseur.intersectObjects(murs, false);
  if (!touche) return;
  if (vol) { cible = touche.point.clone(); return; }
  const sol = solEn(touche.point.x, touche.point.z, touche.point.y);
  if (sol !== null) cible = new THREE.Vector3(touche.point.x, sol, touche.point.z);
}

// L'initiation désigne un élément réellement à l'écran : « touchez un élément » ne dit
// rien à qui ne sait pas encore ce qui s'interroge. La marque reste accrochée à son
// point du monde, et on en cherche une autre quand il sort du cadre ou passe derrière
// un mur. Seul un élément documenté se montre : la première fiche n'est pas un manque.
const SONDES = [[0, 0], [0.3, 0], [-0.3, 0], [0, -0.3], [0.3, -0.3], [-0.3, -0.3], [0.6, 0], [-0.6, 0]];
const CADRE = 0.85;
const RECONTROLE = 15;     // images entre deux contrôles, ou deux recherches vaines
const montre = { id: null, point: new THREE.Vector3(), images: 0, prochaineRecherche: 0 };
const projete = new THREE.Vector3();

function reperer() {
  viseur.far = PORTEE;
  for (const [x, y] of SONDES) {
    viseur.setFromCamera(ecran.set(x, y), camera);
    const [touche] = viseur.intersectObjects(obstacles, false);
    const id = touche?.object.userData.concept;
    if (id && CONCEPTS.get(id)?.resume) {
      montre.id = id;
      montre.point.copy(touche.point);
      return;
    }
  }
  montre.id = null;
}

function projeter(point) {
  projete.copy(point).project(camera);
  return projete.z < 1 && Math.abs(projete.x) < CADRE && Math.abs(projete.y) < CADRE;
}

function elementAMontrer() {
  const image = ++montre.images;
  const toujoursVu = montre.id !== null && projeter(montre.point) &&
    (image % RECONTROLE !== 0 || conceptSous(ecran.set(projete.x, projete.y)) === montre.id);
  if (!toujoursVu) {
    if (image < montre.prochaineRecherche) return null;
    reperer();
    if (montre.id === null || !projeter(montre.point)) {
      montre.id = null;
      montre.prochaineRecherche = image + RECONTROLE;
      return null;
    }
  }
  return { nom: CONCEPTS.get(montre.id).nom,
           clientX: ((projete.x + 1) / 2) * innerWidth, clientY: ((1 - projete.y) / 2) * innerHeight };
}

// ---------------------------------------------------------------------------
// commandes
// ---------------------------------------------------------------------------
const mode = $("#mode"), boutonVol = $("#vol");
function afficherMode() {
  ecrire(mode, vol ? "en_vol" : "a_pied");
  mode.classList.toggle("vole", vol);
  ecrire(boutonVol, vol ? "pied" : "vol");
  manette.modeVol(vol);
}

function basculerVol() {
  if (vol && !atterrir()) return;
  vol = !vol;
  afficherMode();
  cible = null;
  if (vol) noterEnvol(); else noterAtterrissage();
}
boutonVol.onclick = (e) => { basculerVol(); e.currentTarget.blur(); };

// Une vue dit comment on s'y tient : une cour se montre d'en haut, le reste depuis le dallage.
function tenirLaVue(enVol) {
  if (vol === enVol) return;
  vol = enVol;
  afficherMode();
  cible = null;
}

const { lancerInitiation, initiationSuivie, noterRegard, noterDeplacement, noterInterrogation,
        noterEnvol, noterAtterrissage, noterAltitude } = initiation({
  elementAMontrer, estEnVol: () => vol,
});

const manette = commandes(renderer.domElement, {
  regarder: tourner, interroger, allerAu: seRendreA, basculerVol,
});
afficherMode();

// ---------------------------------------------------------------------------
// barre
// ---------------------------------------------------------------------------
const voile = $("#voile");
// Une téléportation qui coupe net laisse le visiteur sans savoir d'où il vient. Le
// délai est celui de la transition du voile, à l'aller seulement : on repart de noir.
// Deux fondus qui se chevauchent — une station et le moment de son parcours — ne lèvent le voile qu'au dernier.
let fondus = 0;
function fondu(action) {
  fondus++;
  voile.classList.add("noir");
  setTimeout(async () => {
    await action();
    if (--fondus === 0) voile.classList.remove("noir");
  }, 170);
}

const aller = $("#aller"), chercher = $("#chercher"), position = $("#position");

function remplirAller() {
  aller.replaceChildren(aller.options[0]);
  for (const e of reperes.entrees) {
    aller.append(new Option(libelle("entrees", e.id) ?? e.nom, e.id));
  }
}
aller.onchange = () => {
  const id = aller.value;
  fondu(() => allerVers(id));
  aller.value = "";
  aller.blur();
};

const choixParcours = $("#parcours-choix");
function remplirParcours() {
  choixParcours.replaceChildren(choixParcours.options[0]);
  for (const p of PARCOURS) choixParcours.append(new Option(p.titre[langue()] ?? p.titre.fr, p.id));
}

function remplirChercher() {
  const parZone = [...CONCEPTS.values()].sort((a, b) =>
    nomDeZone(a.zone).localeCompare(nomDeZone(b.zone), langue()) || a.nom.localeCompare(b.nom, langue()));
  chercher.replaceChildren(chercher.options[0]);
  let zoneCourante = null;
  for (const c of parZone) {
    if (c.zone !== zoneCourante) {
      zoneCourante = c.zone;
      chercher.append(Object.assign(document.createElement("optgroup"), { label: nomDeZone(c.zone) }));
    }
    chercher.lastElementChild.append(new Option(c.nom, c.id));
  }
}
chercher.onchange = () => {
  const id = chercher.value;
  if (!id) return;
  montrer(id);
  fondu(() => allerElement(id));
  chercher.value = "";
  chercher.blur();
};

// ---------------------------------------------------------------------------
// vues
// ---------------------------------------------------------------------------
const RECUL_AUTO = 60;
// Le premier côté d'où l'élément se voit sans mur devant ; l'est d'abord, l'axe du parcours.
const CAPS_AUTO = [180, 0, 90, 270];
const centreDe = (boite) => boite.getCenter(new THREE.Vector3());

function piedsDe(vue) {
  if (vue.position) return vue.position;
  const oeil = oeilQuiCadre(camera, unirEmprises(EMPRISES, vue.cadre),
    { cap: vue.cap, hauteur: vue.sol + OEIL, reculMax: vue.recul_max ?? RECUL_AUTO });
  return [oeil.x, vue.sol, oeil.z];
}

function prendreVue(vue) {
  tenirLaVue(!!vue.vol);
  poser(piedsDe(vue));
  if (vue.cadre) orienterVers(centreDe(unirEmprises(EMPRISES, vue.cadre)));
  else orienterCap(vue);
}

function voitLeConcept(oeil, centre, id) {
  viseur.set(oeil, centre.clone().sub(oeil).normalize());
  viseur.far = oeil.distanceTo(centre);
  const [touche] = viseur.intersectObjects(obstacles, false);
  return !touche || touche.object.userData.concept === id;
}

function piedsQuiVoient(id, boite) {
  const centre = centreDe(boite);
  let repli = null;
  for (const cap of CAPS_AUTO) {
    const approche = oeilQuiCadre(camera, boite, { cap, hauteur: centre.y, reculMax: RECUL_AUTO });
    const sol = solSous(sonde.set(approche.x, centre.y + OEIL, approche.z), Infinity);
    if (sol === null) continue;
    const oeil = oeilQuiCadre(camera, boite, { cap, hauteur: sol + OEIL, reculMax: RECUL_AUTO });
    const pieds = [oeil.x, sol, oeil.z];
    repli ??= pieds;
    if (voitLeConcept(oeil, centre, id)) return pieds;
  }
  if (repli) return repli;
  const oeil = oeilQuiCadre(camera, boite, { cap: CAPS_AUTO[0], hauteur: centre.y, reculMax: RECUL_AUTO });
  return [oeil.x, centre.y - OEIL, oeil.z];
}

// « Un élément… » montre toujours l'élément, jamais l'entrée qui porterait le même nom.
function allerElement(id) {
  const vue = reperes.vues.find((v) => v.id === `vue_${id}`);
  if (vue) {
    prendreVue(vue);
    return true;
  }
  const boite = EMPRISES.get(id);
  if (!boite) return false;
  tenirLaVue(false);
  poser(piedsQuiVoient(id, boite));
  orienterVers(centreDe(boite));
  return true;
}

function allerVers(id) {
  const vue = [...reperes.entrees, ...reperes.vues].find((v) => v.id === id);
  if (!vue) return allerElement(id);
  prendreVue(vue);
  return true;
}

// ---------------------------------------------------------------------------
// lieux et plan
// ---------------------------------------------------------------------------
const volume = (b) => {
  const t = b.getSize(new THREE.Vector3());
  return t.x * t.y * t.z;
};
// Du plus petit au plus grand : le premier qui contient le visiteur est celui où il se tient.
const LIEUX = fiche.concepts.filter((c) => c.lieu && EMPRISES.has(c.id)).map((c) => c.id)
  .sort((a, b) => volume(EMPRISES.get(a)) - volume(EMPRISES.get(b)));
const lieuEn = (point) => LIEUX.find((id) => EMPRISES.get(id).containsPoint(point)) ?? null;

const planMiddot = plan({
  cadrages: CADRAGES_DU_PLAN, emprises: EMPRISES, lieux: LIEUX, concepts: CONCEPTS,
  entrees: reperes.entrees.map((e) => ({ ...e, position: piedsDe(e) })),
  allerLieu: (id) => fondu(() => allerElement(id)),
  allerEntree: (id) => fondu(() => allerVers(id)),
});

async function accorderLangue(code) {
  const traduits = await conceptsEn(code);
  if (code !== langue()) return;                // un choix plus récent est passé pendant le chargement
  for (const [id, concept] of traduits) CONCEPTS.set(id, concept);
  remplirAller();
  remplirChercher();
  remplirParcours();
  rafraichir();
  planMiddot.rafraichir();
}
suivreLangue(accorderLangue);
// Le choix du premier passage tombe le plus souvent pendant le chargement du modèle.
await accorderLangue(langue());

// ---------------------------------------------------------------------------
// boucle
// ---------------------------------------------------------------------------
const demande = new URLSearchParams(location.search).get("vue");
// La visite s'ouvre au-delà du Soreg, dans l'axe de la porte orientale : le 'Heil et
// la porte de l'Ezrat Nashim se franchissent à pied, avant tout le reste.
const depart = reperes.entrees.find((e) => e.id === "face_porte_est") || reperes.entrees[0];
prendreVue(depart);
if (demande) allerVers(demande);

const horloge = new THREE.Clock();
let image = 0;

// L'ombre portée est une fenêtre de 110 amot ; à l'échelle du Har HaBayit une seule
// carte figée serait illisible. Elle suit donc le visiteur — mais par sauts, pas à
// chaque image : la refaire coûte une passe de géométrie entière, la troisième de
// l'image après la principale et celle de l'occlusion, et la fenêtre fait cinquante
// mètres de large quand on n'avance que d'une douzaine de centimètres par image, en
// courant. Tant qu'on ne la rafraîchit pas, three garde aussi la matrice qui va avec :
// carte et matrice restent d'accord, et l'ombre reste juste — elle est simplement
// calculée depuis un pas en arrière.
const ANCRE_OMBRE = new THREE.Vector3(Infinity, Infinity, Infinity);
const PAS_OMBRE = PROFIL.ombres.portee / 10;

// Une carte figée garderait l'ombre des figurants à leur pose de départ.
const figurantsDansLOmbre = () => PROFIL.figurants.ombre && troupePresente in troupes
  && EMPRISES_FIGURANTS[troupePresente].some((b) => b.distanceToPoint(ANCRE_OMBRE) < PROFIL.ombres.portee);

function suivreSoleil() {
  if (figurantsDansLOmbre()) soleil.shadow.needsUpdate = true;
  if (camera.position.distanceToSquared(ANCRE_OMBRE) < PAS_OMBRE * PAS_OMBRE) return;
  ANCRE_OMBRE.copy(camera.position);
  soleil.target.position.copy(camera.position);
  soleil.position.copy(camera.position).addScaledVector(directionDeLAstre, RECUL_SOLEIL);
  soleil.target.updateMatrixWorld();
  soleil.shadow.needsUpdate = true;
}

function dessiner(dt) {
  for (const u of horloges) u.value += dt;
  vaciller(dt);
  const troupe = troupes[troupePresente];
  if (troupe) {
    troupe.melangeur.update(dt);
    suivreTorches(troupe);
  }
  suivreSoleil();
  ciel.position.copy(camera.position);
  detail.choisir(HAUTEUR_IMAGE.value);
  rendu.rendre();
}

const aide = $("#aide");
let entame = false;
// Mesuré autour de la marche seule : un saut du menu n'est pas un pas.
const avantLePas = new THREE.Vector3();
// À mi-corps : un lieu se juge sur celui qui s'y tient, pas sur la dalle qu'il foule.
const corps = new THREE.Vector3(), direction = new THREE.Vector3();

const regulateur = regulerEchelle(PROFIL.echelles, PROFIL.echelleDepart);
function ajusterEchelle(dt) {
  const voulue = regulateur.suivre(dt, performance.now() / 1000);
  if (voulue === null) return;
  echelle = voulue;
  dimensionner();
}

const lieuOccupe = () => lieuEn(corps.set(camera.position.x, piedsY + 1, camera.position.z));
let lieuPresent = null;
// La lampe garde l'éclat qu'on lui voyait avant que l'œil ne s'adapte.
function accorderLampe(lieu) {
  lampe.intensity += ((LAMPE_PAR_LIEU[lieu] ?? 0) / oeilAdapte.facteur - lampe.intensity) * 0.25;
}
// Le Heikhal et le Kodesh HaKodashim s'éclairent à leurs lampes, réglées sans adaptation.
const SANS_ADAPTATION = new Set(["heikhal", "kodesh_hakodashim"]);
function accorderExposition(dt) {
  oeilAdapte.mesurer(camera.position);
  const facteur = SANS_ADAPTATION.has(lieuPresent) ? oeilAdapte.relacher(dt) : oeilAdapte.accorder(dt, rendu.luminance);
  renderer.toneMappingExposure = EXPOSITION.value = EXPOSITION_DEHORS * facteur;
}
// L'air ne rend que le ciel : sous un toit il n'a rien à rendre, et son voile couvrait le cèdre des lishkot.
function accorderAir() {
  brume.density += (AIR_DEHORS * (1 - oeilAdapte.fermeture) - brume.density) * 0.25;
}

// Le cinéma comme le parcours prennent la caméra le temps d'un trajet : la boucle la leur prête.
let film = null;

function preterLaCamera(trajet) {
  film = trajet;
  if (trajet) return;
  piedsY = camera.position.y - OEIL;
  accorderRegard();
}

const guides = parcours({
  parcours: PARCOURS, camera, sol: solEn, oeil: OEIL, ama: AMA,
  marcher: preterLaCamera,
  arriver: () => preterLaCamera(null),
  poserA: (pieds, cible) => fondu(() => {
    tenirLaVue(false);
    poser(pieds);
    orienterVers(cible);
  }),
  changerDeMoment: (voulu) => {
    if (voulu === moment) return;
    fondu(() => passerAu(voulu));
  },
  changerDeTroupe: (voulue = TROUPE_LIBRE) => {
    if (voulue === troupeVoulue) return;
    troupeVoulue = voulue;
    chargerTroupe(voulue);
    fondu(() => presenterTroupe(voulue));
  },
  ouvrirFiche: montrer,
  fermerFiche: fermer,
});
// La carte du parcours prend la place du rappel des commandes, comme l'initiation.
choixParcours.onchange = () => {
  const id = choixParcours.value;
  choixParcours.value = "";
  choixParcours.blur();
  if (!id) return;
  aide.classList.add("parti");
  guides.ouvrir(id);
};

renderer.setAnimationLoop(() => {
  if (enReprise) return;
  const dt = Math.min(horloge.getDelta(), 0.1);
  if (film) {
    film.avancer(dt);
    piedsY = camera.position.y - OEIL;
    if (++image % 4 === 0) {
      lieuPresent = lieuOccupe();
      accorderLampe(lieuPresent);
      accorderAir();
    }
    accorderExposition(dt);
    ajusterEchelle(dt);
    dessiner(dt);
    return;
  }
  lisserRegard(dt);
  avantLePas.copy(camera.position);
  avancer(dt);
  noterDeplacement(camera.position.distanceTo(avantLePas));
  if (vol) noterAltitude(camera.position.y - avantLePas.y);
  ajusterEchelle(dt);

  if (!entame && lisse.lengthSq() > 0.01) {       // le rappel a servi, il s'efface
    entame = true;
    aide.classList.add("parti");
  }

  if (++image % 4 === 0) {                        // le survol n'a pas besoin de 60 Hz
    const p = manette.pointeur;
    survole = p.survole && !manette.tourne ? conceptSous(ecran.set(p.x, p.y)) : null;
    const c = survole && CONCEPTS.get(survole);
    survol.classList.toggle("vu", !!c);
    if (c) {
      survol.textContent = c.nom;
      survol.style.left = `${p.clientX}px`;
      survol.style.top = `${p.clientY + 20}px`;
    }
    lieuPresent = lieuOccupe();
    accorderLampe(lieuPresent);
    accorderAir();
    position.textContent = brut
      ? `${(camera.position.x / AMA).toFixed(0)} · ` +
        `${(-camera.position.z / AMA).toFixed(0)} · ${(piedsY / AMA).toFixed(0)} ${texte("amot")}`
      : (lieuPresent ? CONCEPTS.get(lieuPresent).nom : "");
    planMiddot.suivre(camera.position, camera.getWorldDirection(direction), lieuPresent);
  }
  accorderExposition(dt);
  dessiner(dt);
});

$("#chargement").classList.add("parti");
visiteLancee = true;
alleger(gltf.scene);

// Three renvoie seul géométries et images ; les cartes relâchées, les environnements et les ombres figées sont à refaire.
async function reprendre() {
  for (const m of Object.keys(reflets)) {
    reflets[m].dispose();
    reflets[m] = environnement(renderer, m);
  }
  scene.environment = reflets[moment].texture;
  scene.traverse((o) => { if (o.isLight && o.shadow) o.shadow.needsUpdate = true; });
  await rechargerCartes();
}

// Au premier passage l'initiation remplace le rappel des commandes ; le « ? » la rejoue.
function commencerInitiation() {
  aide.classList.add("parti");
  lancerInitiation();
}
$("#rejouer").onclick = (e) => { e.currentTarget.blur(); commencerInitiation(); };
if (CINEMA) {
  film = cinema({ parcours: haltesCinema, camera, sol: solEn, oeil: OEIL, ama: AMA, voile,
    signaler: (etat) => parent.postMessage({ type: "cinema", ...etat }, location.origin) });
  film.avancer(0);
  dessiner(0);
  parent.postMessage({ type: "cinema", pret: true }, location.origin);
  window.__cinema = { ...film, figer: () => renderer.setAnimationLoop(null) };
} else if (!initiationSuivie()) {
  aide.classList.add("parti");
  // Le voile du chargement finit de se lever avant qu'on s'adresse au visiteur.
  langueChoisie.then(() => setTimeout(commencerInitiation, 700));
}

// Points d'accroche de la vérification headless (cdp.py) : sans eux, impossible de
// savoir depuis un terminal si la page a fini de charger ni ce qu'elle montre.
window.__vue = (id) => { allerVers(id); dessiner(0); };
window.__vues = () => [...reperes.entrees, ...reperes.vues].map((v) => v.id);
window.__cam = (x, y, z, cx, cy, cz) => {
  camera.position.set(x, y, z); camera.lookAt(cx, cy, cz); piedsY = y - OEIL;
  accorderRegard(); dessiner(0);
};
window.__rendre = () => dessiner(0);
window.__etat = () => {
  const e = new THREE.Euler(0, 0, 0, "YXZ").setFromQuaternion(camera.quaternion);
  const d = 180 / Math.PI;
  return { lacet: +(e.y * d).toFixed(2), tangage: +(e.x * d).toFixed(2), roulis: +(e.z * d).toFixed(4),
           x: +camera.position.x.toFixed(3), y: +camera.position.y.toFixed(3), z: +camera.position.z.toFixed(3),
           piedsY: +piedsY.toFixed(3), vise: survole, echelle: +echelle.toFixed(2),
           fov: +camera.fov.toFixed(1), vol, lieu: lieuEn(corps.set(camera.position.x, piedsY + 1, camera.position.z)),
           exposition: +renderer.toneMappingExposure.toFixed(3), fermeture: +oeilAdapte.fermeture.toFixed(2),
           luminance: rendu.luminance && +rendu.luminance.toFixed(4) };
};
window.__ombres = (actives) => {
  renderer.shadowMap.enabled = actives;
  soleil.shadow.needsUpdate = true;
  scene.traverse((o) => { if (o.isMesh) o.material.needsUpdate = true; });
  dessiner(0);
};
Object.defineProperty(window, "__figurants", { get: () => Promise.all(Object.values(chargements)) });
window.__moteur = { renderer, scene };
window.__sol = solEn;
window.__mur = (origine, direction, portee) => {
  const rayon = new THREE.Raycaster(new THREE.Vector3(...origine), new THREE.Vector3(...direction).normalize(), 0, portee);
  const [touche] = rayon.intersectObjects(murs, false);
  return touche ? { distance: touche.distance, concept: touche.object.userData.concept ?? touche.object.name } : null;
};
window.__parcours = guides;
window.__temps = (t) => { troupes[troupePresente]?.melangeur.setTime(t); dessiner(0); };
window.__pret = true;
