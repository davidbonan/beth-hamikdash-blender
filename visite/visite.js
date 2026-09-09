import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { habiller, attiser, ETOFFES } from "./matieres.js";
import { nappes } from "./nappes.js";
import { chaine } from "./occlusion.js";
import { PROFIL } from "./qualite.js";
import { commandes } from "./pilotage.js";
import { ZONES, panneau } from "./fiche.js";

const AMA = 0.48;
const OEIL = 1.75;        // H_HOMME de la fiche : 1,75 m
const RAYON = 0.38;       // demi-largeur du marcheur
// Les degrés du 'Heil, de Nikanor et de l'Oulam font tous 1/2 ama — 0,24 m — et
// c'est cette valeur qui commande les trois suivantes. MONTEE doit la dépasser de
// peu : la garde se place juste au-dessus, et sa portée doit rester plus courte
// qu'une marche n'est profonde, sans quoi elle heurte la marche d'après avant qu'on
// ait gravi celle d'avant.
const MARCHE = 0.5 * 0.48; // 1/2 ama
const MONTEE = 0.28;       // franchissable sans escalader
const CHUTE = 0.60;        // au-delà, il n'y a pas de sol : le pas est refusé
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

// ---------------------------------------------------------------------------
// données
// ---------------------------------------------------------------------------
const $ = (s) => document.querySelector(s);
const etat = $("#etat"), jauge = $("#jauge i");

// Une erreur de chargement laissait l'écran figé sur son dernier état sans rien dire :
// le voile ne se lève qu'en fin de module, et un module qui jette ne lève rien.
const echouer = (quoi) => {
  etat.textContent = `échec : ${quoi}`;
  etat.style.color = "#e0836a";
};
addEventListener("error", (e) => echouer(e.message || e.error));
addEventListener("unhandledrejection", (e) => echouer(e.reason?.message || e.reason));

async function json(chemin, obligatoire = true) {
  const r = await fetch(chemin);
  if (!r.ok) {
    if (obligatoire) throw new Error(`${chemin} : ${r.status}`);
    return null;                                  // encyclopédie encore incomplète
  }
  return r.json();
}

const [fiche, ...contenus] = await Promise.all([
  json("./concepts.json"),
  json("./contenu_a.json", false),
  json("./contenu_b.json", false),
  json("./contenu_c.json", false),
]);
const reperes = await json("./reperes.json");

const CONCEPTS = new Map();
for (const c of fiche.concepts) {
  const apport = contenus.find((x) => x && x[c.id]) || {};
  CONCEPTS.set(c.id, { ...c, ...(apport[c.id] || {}) });
}

// ---------------------------------------------------------------------------
// scène
// ---------------------------------------------------------------------------
// Profondeur logarithmique : le plaquage d'or du Heikhal est posé exactement sur la
// pierre qu'il couvre, et la scène va du centimètre d'une flamme aux 240 m de
// l'esplanade. Un tampon linéaire y fait clignoter les deux surfaces l'une dans
// l'autre. Elle écrit en revanche la profondeur depuis le nuanceur, ce qui prive les
// GPU à tuiles de leur tri préalable : le profil léger s'en passe, et compte pour ça
// sur le seul écart qui reste à départager, les 4,8 cm du placage.
const renderer = new THREE.WebGLRenderer({
  antialias: true, powerPreference: "high-performance",
  logarithmicDepthBuffer: PROFIL.profondeurLog });
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.62;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = PROFIL.ombres.doux ? THREE.PCFSoftShadowMap : THREE.PCFShadowMap;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
// Le brouillard porte la couleur du BAS du ciel, et pas une autre : accordé au dôme
// il éloigne, désaccordé il salit. À 0xc9cec8 sur 120 m il repeignait en gris-vert
// tout ce qui passait le milieu de l'esplanade, laquelle fait 500 amot de côté.
scene.fog = new THREE.Fog(0xd8dcd4, 220, 900);

// L'ambiance ne doit PAS peser autant que le soleil. À 0,75 contre 1,9, chaque face
// recevait presque autant de lumière sans direction que de lumière du matin : le
// calcaire y perdait sa teinte et le modelé avec, et les murs rendaient un aplat gris.
// Le rapport compte plus que les niveaux — même arbitrage que le ciel du blockout.
scene.add(new THREE.HemisphereLight(0xd5dbe0, 0x9c8b6c, 0.42));
// Matin, à l'est : l'axe de l'avoda, et la lumière qui creuse la façade de face.
const soleil = new THREE.DirectionalLight(0xfff2dc, 2.7);
soleil.castShadow = true;
soleil.shadow.mapSize.set(PROFIL.ombres.taille, PROFIL.ombres.taille);
soleil.shadow.bias = -0.0002;
soleil.shadow.normalBias = 0.04;
// Fenêtre serrée : elle suit le visiteur, et 2048 texels sur 80 m donnent 4 cm de
// résolution — assez fin pour l'arête d'une assise, ce qu'une fenêtre couvrant tout
// le Har HaBayit ne donnerait jamais. Le profil léger rétrécit la fenêtre en même
// temps que la carte, pour garder cette résolution-là.
const PORTEE_OMBRE = PROFIL.ombres.portee;
Object.assign(soleil.shadow.camera, { near: 1, far: 260, left: -PORTEE_OMBRE,
  right: PORTEE_OMBRE, top: PORTEE_OMBRE, bottom: -PORTEE_OMBRE });
scene.add(soleil, soleil.target);
const appoint = new THREE.DirectionalLight(0xb9c6d4, 0.22);  // rebond du ciel à l'ouest
appoint.position.set(-140, 70, -40);
scene.add(appoint);

// Un dôme dégradé plutôt qu'un aplat : sans horizon, le Har HaBayit flotte. Et le
// soleil y est DESSINÉ : un ciel d'où vient une ombre franche sans qu'on voie d'où
// elle vient se lit en éclairage de studio, pas en matin de Jérusalem.
const SOLEIL = new THREE.Vector3(150, 125, 55);
function domeCiel(rayon, haut = 0x4d7fb8, bas = 0xd8dcd4, sol = 0xa89c86, disque = 1.0) {
  return new THREE.Mesh(
    new THREE.SphereGeometry(rayon, 64, 32),
    new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { hautCiel: { value: new THREE.Color(haut) },
                  basCiel: { value: new THREE.Color(bas) },
                  solCiel: { value: new THREE.Color(sol) },
                  dirSoleil: { value: SOLEIL.clone().normalize() },
                  force: { value: disque } },
      vertexShader: `varying vec3 vD; void main(){ vD = position;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: `uniform vec3 hautCiel, basCiel, solCiel, dirSoleil;
        uniform float force; varying vec3 vD;
        void main(){ vec3 d = normalize(vD); float h = d.y;
          vec3 c = h > 0.0 ? mix(basCiel, hautCiel, pow(h, 0.55)) : mix(basCiel, solCiel, min(-h * 6.0, 1.0));
          float s = max(dot(d, dirSoleil), 0.0);
          // Trois portées : la moitié du ciel se réchauffe vers le soleil, le halo se
          // resserre autour, le disque tient dans un demi-degré.
          c += force * vec3(1.00, 0.84, 0.58) * (0.10 * pow(s, 4.0) + 0.45 * pow(s, 160.0));
          c += force * vec3(1.00, 0.95, 0.86) * 2.2 * smoothstep(0.99993, 0.99998, s);
          gl_FragColor = vec4(c, 1.0); }`,
    }));
}

const ciel = domeCiel(760);
ciel.frustumCulled = false;
scene.add(ciel);

// L'or est métallique : sans environnement à réfléchir, il rend noir. Cet
// environnement est le dôme lui-même et pas une pièce neutre : une pièce grise
// éclaire chaque face à l'ombre d'un gris sans teinte, et c'est ce qui rendait le
// calcaire des faces nord couleur de béton.
// Le dôme qui éclaire n'a pas les couleurs du dôme qu'on voit : il n'y a pas de
// rebond dans cette scène, et sous un portique la seule lumière serait celle du bleu
// du zénith — le dallage à l'ombre y virait au bleu franc. Le ciel de l'éclairage est
// donc désaturé vers le haut, et sa moitié basse porte le calcaire ensoleillé de
// l'esplanade, qui est le vrai rebond de tout ce qui est à l'ombre ici.
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(
  new THREE.Scene().add(domeCiel(20, 0x8fa5bd, 0xe0d9c9, 0xc9b795, 0.0)), 0.04, 0.1, 200).texture;

// Le champ est fixé à l'HORIZONTALE, pas à la verticale. Un champ vertical constant
// vaut 94° de large en 16/9 et 31° sur un téléphone tenu debout : on y visiterait le
// Temple par une paille. Le vertical est donc déduit du format, et seulement borné —
// au-delà de 80° un portrait étroit tournerait au fisheye.
const FOV_HORIZONTAL = 94;
const FOV_VERTICAL = [50, 80];
const camera = new THREE.PerspectiveCamera(62, innerWidth / innerHeight, 0.12, 900);
// Une lampe discrète accrochée à la tête : sans elle le Heikhal, qui n'a pas de
// fenêtre ouvrante dans le blockout, est une pièce noire.
const lampe = new THREE.PointLight(0xffe9c4, 6, 26, 1.7);
camera.add(lampe);
scene.add(camera);

// Le dôme est le seul objet qui n'entre pas dans la passe de géométrie : il enveloppe
// la scène, et il l'occluerait tout entière.
const rendu = chaine(renderer, scene, camera, [ciel]);

// La résolution suit ce que la machine tient. Baisser la définition d'un tiers coûte
// une image plus douce ; la garder coûte le mouvement, qui est ce qu'on est venu voir.
const DPR = Math.min(devicePixelRatio, PROFIL.dprMax);
let echelle = 1;

function dimensionner() {
  camera.aspect = innerWidth / innerHeight;
  const vertical = THREE.MathUtils.radToDeg(
    2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(FOV_HORIZONTAL) / 2) / camera.aspect));
  camera.fov = THREE.MathUtils.clamp(vertical, FOV_VERTICAL[0], FOV_VERTICAL[1]);
  camera.updateProjectionMatrix();
  renderer.setPixelRatio(DPR * echelle);
  renderer.setSize(innerWidth, innerHeight);
  rendu.redimensionner(innerWidth, innerHeight);
}
dimensionner();
addEventListener("resize", dimensionner);

// ---------------------------------------------------------------------------
// modèle
// ---------------------------------------------------------------------------
const obstacles = [];
// Les nappes descendent PENDANT le .glb : elles pèsent la moitié de son poids, et les
// attendre ensuite doublerait l'attente d'un visiteur en 4G.
const [gltf, jeux] = await Promise.all([
  new GLTFLoader().setMeshoptDecoder(MeshoptDecoder)
    .loadAsync("./temple.glb", (e) => {
      if (e.lengthComputable) jauge.style.width = `${(e.loaded / e.total) * 100}%`;
    }),
  nappes(),
]);
etat.textContent = "préparation…";
scene.add(gltf.scene);

const murs = [];                        // collision : les étoffes en sont exclues
const horloges = [];                    // uniformes de temps à faire avancer
const brut = new URLSearchParams(location.search).has("brut");
const IDS = new Set(CONCEPTS.keys());
const habillees = new Set();
gltf.scene.traverse((o) => {
  if (!o.isMesh) return;
  for (let n = o; n; n = n.parent) {
    const nom = n.name.replace(/_\d+$/, "");
    if (IDS.has(nom)) { o.userData.concept = nom; break; }
  }
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
  if (!brut && !habillees.has(o.material.uuid)) {
    habillees.add(o.material.uuid);
    habiller(o.material, horloges, jeux);
    attiser(o.material);
  }
  obstacles.push(o);
  if (!TRAVERSABLES.has(o.userData.concept)) murs.push(o);
});

// ---------------------------------------------------------------------------
// marche
// ---------------------------------------------------------------------------
const BAS = new THREE.Vector3(0, -1, 0);
const versLeBas = new THREE.Raycaster();
const versLAvant = new THREE.Raycaster();

function solEn(x, z, piedsY) {
  versLeBas.set(new THREE.Vector3(x, piedsY + MONTEE, z), BAS);
  versLeBas.far = MONTEE + CHUTE;
  // Une face tournée vers le bas — le dessous d'un mur posé sur la dalle — n'est pas
  // un sol : sans ce filtre on marche à l'intérieur des murs.
  for (const t of versLeBas.intersectObjects(murs, false)) {
    if (!t.face || t.face.normal.y > 0.25) return t.point.y;
  }
  return null;
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
    const sol = murDevant(camera.position, piedsY, pas, distance) ? null : solEn(x, z, piedsY);
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

function poser(x, y, z, cap) {
  const sol = vol ? null : solEn(x, z, y + 0.3);
  piedsY = sol === null ? y : sol;
  camera.position.set(x, piedsY + OEIL, z);
  lisse.set(0, 0, 0);
  cible = null;
  if (cap !== undefined) {
    // Cap en degrés dans le repère de la fiche : 0 = est, 180 = ouest, l'axe du
    // parcours du Cohen Gadol. Le nord de Blender devient -Z une fois passé en Y-haut.
    const a = THREE.MathUtils.degToRad(cap);
    camera.lookAt(x + Math.cos(a) * 10, piedsY + OEIL, z - Math.sin(a) * 10);
  }
  accorderRegard();
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
const ecran = new THREE.Vector2();
const survol = $("#survol");
const { montrer, fermer } = panneau(CONCEPTS);
let survole = null;

const normaliser = (clientX, clientY) =>
  ecran.set((clientX / innerWidth) * 2 - 1, -(clientY / innerHeight) * 2 + 1);

function conceptSous(coords) {
  viseur.setFromCamera(coords, camera);
  viseur.far = 140;
  const touche = viseur.intersectObjects(obstacles, false);
  return touche.length ? touche[0].object.userData.concept || null : null;
}

function interroger(clientX, clientY) {
  const id = conceptSous(normaliser(clientX, clientY));
  if (id) montrer(id); else fermer();
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

// ---------------------------------------------------------------------------
// commandes
// ---------------------------------------------------------------------------
const mode = $("#mode");
function basculerVol() {
  vol = !vol;
  mode.textContent = vol ? "vol libre" : "à pied";
  mode.classList.toggle("vole", vol);
  manette.modeVol(vol);
  cible = null;
  if (!vol) {                                   // en reprenant pied, retrouver le sol
    const sol = solEn(camera.position.x, camera.position.z, camera.position.y - OEIL + 0.3);
    if (sol !== null) { piedsY = sol; camera.position.y = sol + OEIL; }
  }
}
$("#vol").onclick = (e) => { basculerVol(); e.currentTarget.blur(); };

const manette = commandes(renderer.domElement, {
  regarder: tourner, interroger, allerAu: seRendreA, basculerVol,
});

// ---------------------------------------------------------------------------
// barre
// ---------------------------------------------------------------------------
const voile = $("#voile");
// Une téléportation qui coupe net laisse le visiteur sans savoir d'où il vient. Le
// délai est celui de la transition du voile, à l'aller seulement : on repart de noir.
function fondu(action) {
  voile.classList.add("noir");
  setTimeout(() => { action(); voile.classList.remove("noir"); }, 170);
}

const aller = $("#aller"), chercher = $("#chercher"), position = $("#position");
for (const e of reperes.entrees) {
  aller.append(new Option(e.nom, e.id));
}
aller.onchange = () => {
  const e = reperes.entrees.find((x) => x.id === aller.value);
  if (e) fondu(() => poser(e.position[0], e.position[1], e.position[2], e.cap));
  aller.value = "";
  aller.blur();
};

const parZone = [...CONCEPTS.values()].sort((a, b) =>
  (ZONES[a.zone] || a.zone).localeCompare(ZONES[b.zone] || b.zone) || a.nom.localeCompare(b.nom, "fr"));
let zoneCourante = null;
for (const c of parZone) {
  if (c.zone !== zoneCourante) {
    zoneCourante = c.zone;
    chercher.append(Object.assign(document.createElement("optgroup"),
      { label: ZONES[c.zone] || c.zone }));
  }
  chercher.lastElementChild.append(new Option(c.nom, c.id));
}
chercher.onchange = () => {
  const id = chercher.value;
  if (!id) return;
  montrer(id);
  fondu(() => allerA(id));
  chercher.value = "";
  chercher.blur();
};

function allerA(id) {
  const e = reperes.entrees.find((x) => x.id === id);
  if (e) { poser(e.position[0], e.position[1], e.position[2], e.cap); return true; }
  const b = reperes.emprises[id];
  if (!b) return false;
  const centre = new THREE.Vector3(...b.min).add(new THREE.Vector3(...b.max)).multiplyScalar(0.5);
  const taille = new THREE.Vector3(...b.max).sub(new THREE.Vector3(...b.min));
  const recul = Math.min(60, Math.max(2.8, Math.max(taille.x, taille.y, taille.z) * 1.3));
  poser(centre.x + recul, centre.y + taille.y * 0.1, centre.z);
  camera.lookAt(centre);
  accorderRegard();
  return true;
}

// ---------------------------------------------------------------------------
// boucle
// ---------------------------------------------------------------------------
const demande = new URLSearchParams(location.search).get("vue");
const depart = reperes.entrees.find((e) => e.id === "azara") || reperes.entrees[0];
poser(depart.position[0], depart.position[1], depart.position[2], depart.cap);
if (demande) allerA(demande);

const horloge = new THREE.Clock();
let image = 0;

// L'ombre portée est une fenêtre de 110 amot ; à l'échelle du Har HaBayit une seule
// carte figée serait illisible. Elle suit donc le visiteur.
function suivreSoleil() {
  soleil.target.position.copy(camera.position);
  soleil.position.copy(camera.position).add(SOLEIL);
  soleil.target.updateMatrixWorld();
}

function dessiner(dt) {
  for (const u of horloges) u.value += dt;
  suivreSoleil();
  ciel.position.copy(camera.position);
  rendu.rendre();
}

// La définition ne se règle pas sur une image mais sur une moyenne, et les deux seuils
// laissent un écart entre eux : accolés, l'échelle descendrait puis remonterait sans
// fin, ce qui se voit bien plus qu'une image un peu douce.
const aide = $("#aide");
let moyenne = 16, attente = 0, entame = false;

function ajusterEchelle(dt) {
  moyenne += (dt * 1000 - moyenne) * 0.05;
  if (++attente < 120) return;
  const precedente = echelle;
  if (moyenne > 22) echelle = Math.max(PROFIL.echelleMin, echelle - 0.15);
  else if (moyenne < 12) echelle = Math.min(1, echelle + 0.1);
  if (echelle === precedente) return;
  attente = 0;
  dimensionner();
}

renderer.setAnimationLoop(() => {
  const dt = Math.min(horloge.getDelta(), 0.1);
  lisserRegard(dt);
  avancer(dt);
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
    position.textContent = `${(camera.position.x / AMA).toFixed(0)} · ` +
      `${(-camera.position.z / AMA).toFixed(0)} · ${(piedsY / AMA).toFixed(0)} amot`;
  }
  dessiner(dt);
});

$("#chargement").classList.add("parti");

// Points d'accroche de la vérification headless (cdp.py) : sans eux, impossible de
// savoir depuis un terminal si la page a fini de charger ni ce qu'elle montre.
window.__vue = (id) => { allerA(id); dessiner(0); };
window.__cam = (x, y, z, cx, cy, cz) => {
  camera.position.set(x, y, z); camera.lookAt(cx, cy, cz); piedsY = y - OEIL;
  accorderRegard(); dessiner(0);
};
window.__rendre = () => dessiner(0);
window.__etat = () => {
  const e = new THREE.Euler(0, 0, 0, "YXZ").setFromQuaternion(camera.quaternion);
  const d = 180 / Math.PI;
  return { lacet: +(e.y * d).toFixed(2), tangage: +(e.x * d).toFixed(2), roulis: +(e.z * d).toFixed(4),
           x: +camera.position.x.toFixed(3), z: +camera.position.z.toFixed(3),
           piedsY: +piedsY.toFixed(3), vise: survole, echelle: +echelle.toFixed(2),
           fov: +camera.fov.toFixed(1) };
};
window.__ombres = (actives) => {
  renderer.shadowMap.enabled = actives;
  scene.traverse((o) => { if (o.isMesh) o.material.needsUpdate = true; });
  dessiner(0);
};
window.__pret = true;
