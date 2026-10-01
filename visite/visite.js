import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { computeBoundsTree, acceleratedRaycast } from "three-mesh-bvh";
import { habiller, ETOFFES, HAUTEUR_IMAGE, EXPOSITION, EXPOSITION_DEHORS } from "./matieres.js";
import { nappes } from "./nappes.js";
import { cartesLumiere, cartesOcclusion, rechargerCartes } from "./occlusion.js";
import { adaptation } from "./adaptation.js";
import { DANS_HEIKHAL, separerDuHeikhal, sonderHeikhal } from "./sonde.js";
import { chaine } from "./chaine.js";
import { niveauxDeDetail } from "./detail.js";
import { brumer, domeVu, lumieresDu } from "./ciel.js";
import { epargner as epargnerOmbres, regler as reglerOmbres } from "./ombres.js";
import { PROFIL } from "./qualite.js";
import { regulerEchelle } from "./echelle.js";
import { commandes } from "./pilotage.js";
import { nomDeZone, panneau } from "./fiche.js";
import { initiation } from "./initiation.js";
import { enBoite, unirEmprises } from "./cadrage.js";
import { lieuxSouterrains, plan } from "./plan.js";
import { cinema } from "./cinema.js";
import { parcours } from "./parcours.js";
import { AMA, OEIL, marcheur } from "./marche.js";
import { ecrire, installerLangue, langue, langueChoisie, libelle, suivreLangue, texte } from "./langue.js";
import { veillerAuxPannes } from "./pannes.js";
import { laisserPeindre, rendreLaMain } from "./fil.js";
import { TROUPES, TROUPE_LIBRE, troupesDeFigurants } from "./figurants.js";
import { eclairerLeTemple } from "./eclairage.js";
import { designation } from "./designation.js";
import { vuesDuTemple } from "./vues.js";
import { conceptsEn, contenusSources, json } from "./encyclopedie.js";

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
const pannes = veillerAuxPannes({ etat, chargement: $("#chargement") });

const [textes, fiche, ...contenus] = await Promise.all([
  json("./textes.json"),
  json("./concepts.json"),
  ...contenusSources(),
]);
installerLangue(textes);
// Encadrée par l'accueil, la scène marche seule et se tait : ni barre, ni fiche, ni initiation.
const CINEMA = new URLSearchParams(location.search).has("cinema");
document.documentElement.classList.toggle("cinema", CINEMA);
const [reperes, { cadrages: CADRAGES_DU_PLAN }, haltesCinema, { parcours: PARCOURS }, ...distributions] =
  await Promise.all([json("./reperes.json"), json("./plan.json"), CINEMA ? json("./cinema.json") : null,
    json("./parcours.json"), ...Object.values(TROUPES).map((t) => json(t.json))]);
const figurants = Object.fromEntries(Object.keys(TROUPES).map((nom, i) => [nom, distributions[i]]));
// Ce que la scène du Temple cadre d'elle-même, avant que les troupes n'y ajoutent leurs figurants.
const REPERES_DU_TEMPLE = new Set([...Object.keys(reperes.emprises), ...reperes.entrees.map((e) => e.id), ...reperes.vues.map((v) => v.id)]);
// Un concept joué par plusieurs troupes — les Léviim, douze au tamid, deux en visite libre — prend la boîte de toutes.
const unirBoites = (a, b) => (a ? {
  min: a.min.map((v, k) => Math.min(v, b.min[k])),
  max: a.max.map((v, k) => Math.max(v, b.max[k])),
} : b);
for (const { emprises, vues } of distributions) {
  for (const [id, boite] of Object.entries(emprises)) reperes.emprises[id] = unirBoites(reperes.emprises[id], boite);
  reperes.vues.push(...vues.filter((vue) => !reperes.vues.some((v) => v.id === vue.id)));
}
const EMPRISES = new Map(Object.entries(reperes.emprises).map(([id, b]) => [id, enBoite(b)]));

const CONCEPTS = await conceptsEn(langue(), fiche, contenus);

// ---------------------------------------------------------------------------
// scène
// ---------------------------------------------------------------------------
// Pas de profondeur logarithmique : écrite depuis le nuanceur, elle éteint le test de
// profondeur anticipé, et tout ce que les murs cachent passait par la matière — le
// Heikhal ombrait la cour entière derrière lui. Le tampon linéaire départage encore les
// 4,8 cm du placage d'or à trois cents mètres.
const renderer = new THREE.WebGLRenderer({ powerPreference: "high-performance" });
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = EXPOSITION_DEHORS;
renderer.shadowMap.enabled = true;
// Le profil lourd ne s'en sert pas : `ombres.js` y remplace la lecture de la carte
// par une pénombre variable. Il reste le réglage du profil léger, qui garde celle-ci.
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);
pannes.surveiller(renderer, () => reprendre());

const scene = new THREE.Scene();
const brume = brumer(scene);
const AIR_DEHORS = brume.density;

// L'ambiance ne doit PAS peser autant que le soleil. À 0,75 contre 1,9, chaque face
// recevait presque autant de lumière sans direction que de lumière du matin : le
// calcaire y perdait sa teinte et le modelé avec, et les murs rendaient un aplat gris.
// Le rapport compte plus que les niveaux — même arbitrage que le ciel du blockout.
// Elle descend une seconde fois, avec `ambiance` dans ciel.js : ce que ce réglage-ci
// corrigeait pour les parements, il restait à le corriger pour tout ce qui est à plat.
const cielAmbiant = new THREE.HemisphereLight(0xd5dbe0, 0x9c8b6c, lumieresDu("jour").ciel);
scene.add(cielAmbiant);
// Matin, à l'est : l'axe de l'avoda, et la lumière qui rase la façade. Plus bas sur
// l'horizon, le soleil traverse plus d'atmosphère : il perd de la force et gagne de
// l'ambre, et c'est ce qui empêche un rasant de rendre le calcaire crayeux.
const soleil = new THREE.DirectionalLight(lumieresDu("jour").astre.couleur, lumieresDu("jour").astre.intensite);
reglerOmbres(soleil);
epargnerOmbres();
scene.add(soleil, soleil.target);
const appoint = new THREE.DirectionalLight(0xb9c6d4, lumieresDu("jour").appoint);  // rebond du ciel à l'ouest
appoint.position.set(-140, 70, -40);
scene.add(appoint);

const ciel = domeVu(5700);
scene.add(ciel);

// Le champ est fixé à l'HORIZONTALE, pas à la verticale. Un champ vertical constant
// vaut 94° de large en 16/9 et 31° sur un téléphone tenu debout : on y visiterait le
// Temple par une paille. Le vertical est donc déduit du format, et seulement borné —
// au-delà de 80° un portrait étroit tournerait au fisheye.
const FOV_HORIZONTAL = 94;
const FOV_VERTICAL = [50, 80];
const camera = new THREE.PerspectiveCamera(62, innerWidth / innerHeight, 0.12, 6000);
// La lampe de tête, là seulement où la lumière cuite laisse noir ; l'emprise du Heikhal couvre aussi ses cellules.
const LAMPE_TETE = 6;
// HaGola et les chambres sous l'Ezrat Israël ne voient le jour que par leur porte, et HaKelim, fermée, par la baie du don.
const LAMPE_PAR_LIEU = { heikhal: 0.6, kodesh_hakodashim: 0.5, taim: LAMPE_TETE, lishkat_hagola: LAMPE_TETE,
  lishkat_hakelim: LAMPE_TETE, lishkot_haleviim: LAMPE_TETE, lishkat_chashaim: LAMPE_TETE,
  ...Object.fromEntries([...lieuxSouterrains(CADRAGES_DU_PLAN)].map((lieu) => [lieu, LAMPE_TETE])) };
const lampe = new THREE.PointLight(0xffe9c4, 0, 26, 1.7);
camera.add(lampe);
scene.add(camera);

// Le dôme n'entre pas dans la passe de géométrie : il enveloppe la scène, et il l'occluerait
// tout entière. Les flammes de la Menora non plus : elles ne sont pas une surface à ombrer.
const horsGeometrie = [ciel];
const rendu = chaine(renderer, scene, camera, horsGeometrie);
const detail = niveauxDeDetail(scene, camera);
// Le film veut chaque image au plein détail, sans qu'un allègement arrivé en cours de prise ne la change.
function maillagesDe(racine) {
  const maillages = [];
  racine.traverse((o) => { if (o.isMesh) maillages.push(o); });
  return maillages;
}

function alleger(racine) {
  if (!CINEMA) detail.confier(maillagesDe(racine));
}

// Une torche tenue bouge par sa matrice : figée à sa première image, sa tuile restait en arrière de la main et de sa flamme.
function allegerTroupe(troupe) {
  if (!CINEMA) detail.confierMobiles(maillagesDe(troupe));
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
await laisserPeindre();
scene.add(gltf.scene);
// Three ne calcule les matrices monde qu'au premier rendu, et un rayon ne les calcule
// pas : sans ça le tout premier `poser` sonde une scène encore à l'origine, ne trouve
// aucun sol, et la visite s'ouvrait un mètre au-dessus du dallage.
gltf.scene.updateMatrixWorld(true);

const murs = [];                        // collision : les étoffes en sont exclues
const marche = marcheur(camera, murs);
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

// Le groupe que l'export a cuit (ses extras) : un concept, ou `_non_classe`, dont les podiums plafonnent les salles sous l'Ezrat Israël.
function groupeCuitDe(objet) {
  for (let n = objet; n; n = n.parent) if (n.userData.concept) return n.userData.concept;
  return undefined;
}

const maillages = [];
gltf.scene.traverse((o) => {
  if (!o.isMesh) return;
  o.userData.groupeCuit = groupeCuitDe(o);
  o.userData.concept = conceptDe(o);
  maillages.push(o);
});
const sousSonde = new Set(brut ? [] : separerDuHeikhal(
  maillages.filter((o) => DANS_HEIKHAL.has(o.userData.concept)), EMPRISES.get("heikhal")));
const eclairage = eclairerLeTemple({ scene, renderer, rendu, astres: { soleil, appoint, cielAmbiant }, ciel, brume, temple: gltf.scene, sousSonde,
  emprises: EMPRISES, reperes, horsGeometrie, annoncerAttente });

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
    const occlusion = occlusions.get(o.userData.groupeCuit);
    const lumiere = lumieres.get(o.userData.groupeCuit);
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
const refleterLeHeikhal = () => sonderHeikhal(renderer, scene, {
  kelim: unirEmprises(EMPRISES, ["menora", "shulchan", "mizbeach_hazahav"]),
  materiaux: materiauxHeikhal,
  lumieres: [soleil, appoint, lampe, cielAmbiant],
  caches: [ciel],
});
if (!brut) {
  refleterLeHeikhal();
  await rendu.compiler();                 // le reflet de la salle change les nuanceurs de son or
}

// Les figurants descendent après le Temple : la visite s'ouvre sans les attendre, et on les traverse.
const troupes = troupesDeFigurants({ scene, camera, renderer, chargeur, rendu, detail, alleger: allegerTroupe, obstacles, horsGeometrie,
  distributions: figurants, conceptDe, lampesPosees: () => eclairage.lampesPosees });
troupes.charger(TROUPE_LIBRE);

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
// interrogation
// ---------------------------------------------------------------------------
const PORTEE_DU_PILOTE = 120;
const survol = $("#survol");
const { montrer, fermer, rafraichir } = panneau(CONCEPTS);
const designe = designation({ camera, obstacles, concepts: CONCEPTS });
let survole = null;

function interroger(clientX, clientY) {
  const id = designe.conceptTouche(clientX, clientY);
  if (!id) {
    fermer();
    return;
  }
  montrer(id);
  noterInterrogation();
}

function seRendreA(clientX, clientY) {
  const point = designe.pointTouche(murs, PORTEE_DU_PILOTE, [clientX, clientY]);
  if (point) marche.seRendreVers(point);
}

// ---------------------------------------------------------------------------
// commandes
// ---------------------------------------------------------------------------
const mode = $("#mode"), boutonVol = $("#vol");
function afficherMode() {
  ecrire(mode, marche.vol ? "en_vol" : "a_pied");
  mode.classList.toggle("vole", marche.vol);
  ecrire(boutonVol, marche.vol ? "pied" : "vol");
  manette.modeVol(marche.vol);
}

function basculerVol() {
  if (!marche.basculerVol()) return;
  afficherMode();
  if (marche.vol) noterEnvol(); else noterAtterrissage();
}
boutonVol.onclick = (e) => { basculerVol(); e.currentTarget.blur(); };

// Une vue dit comment on s'y tient : une cour se montre d'en haut, le reste depuis le dallage.
function tenirLaVue(enVol) {
  if (marche.tenirLeVol(enVol)) afficherMode();
}

const { lancerInitiation, initiationSuivie, noterRegard, noterDeplacement, noterInterrogation,
        noterEnvol, noterAtterrissage, noterAltitude } = initiation({
  elementAMontrer: designe.elementAMontrer, estEnVol: () => marche.vol,
});

const manette = commandes(renderer.domElement, {
  regarder(dLacet, dTangage) {
    marche.tourner(dLacet, dTangage);
    noterRegard(Math.abs(dLacet) + Math.abs(dTangage));
  },
  interroger, allerAu: seRendreA, basculerVol,
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
const FONDU_MS = 170;
async function fondu(action) {
  fondus++;
  voile.classList.add("noir");
  try {
    await new Promise((noir) => setTimeout(noir, FONDU_MS));
    await action();
  } finally {
    if (--fondus === 0) voile.classList.remove("noir");
  }
}

// Chaque lampe de nuit recompile tous les nuanceurs de la scène : Safari s'y fige jusqu'à neuf secondes, le voile dit qu'il prépare.
async function annoncerAttente(travail) {
  voile.classList.add("attente");
  try {
    await laisserPeindre();
    await travail();
  } finally {
    voile.classList.remove("attente");
  }
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
  fondu(() => vues.allerVers(id));
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
  fondu(() => vues.allerElement(id));
  chercher.value = "";
  chercher.blur();
};

const vues = vuesDuTemple({ camera, marche, emprises: EMPRISES, reperes, obstacles, tenirLeVol: tenirLaVue });

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
  cadrages: CADRAGES_DU_PLAN, emprises: EMPRISES, lieux: LIEUX, concepts: CONCEPTS, ama: AMA,
  entrees: reperes.entrees.map((e) => ({ ...e, position: vues.piedsDe(e) })),
  allerLieu: (id) => fondu(() => vues.allerElement(id)),
  allerEntree: (id) => fondu(() => vues.allerVers(id)),
});

async function accorderLangue(code) {
  const traduits = await conceptsEn(code, fiche, contenus);
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
// La visite s'ouvre au-delà du Soreg, dans l'axe de la porte orientale : le 'Heil et
// la porte de l'Ezrat Nashim se franchissent à pied, avant tout le reste.
const depart = reperes.entrees.find((e) => e.id === "face_porte_est") || reperes.entrees[0];
vues.prendreVue(depart);

const horloge = new THREE.Clock();
let image = 0;

function dessiner(dt) {
  for (const u of horloges) u.value += dt;
  eclairage.vaciller(dt);
  troupes.animer(dt);
  eclairage.suivreSoleil(camera.position, troupes.ombresPres);
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

const lieuOccupe = () => lieuEn(corps.set(camera.position.x, marche.piedsY + 1, camera.position.z));
let lieuPresent = null;
// Le lieu se relève toutes les quatre images ; la lampe et l'air le rejoignent au temps écoulé, pas à l'image.
const IMAGES_ENTRE_RELEVES = 4;
const REPONSE_LIEU = 0.23;
let depuisLeReleve = 0;
// La lampe garde l'éclat qu'on lui voyait avant que l'œil ne s'adapte.
function accorderLampe(lieu, part) {
  lampe.intensity += ((LAMPE_PAR_LIEU[lieu] ?? 0) / oeilAdapte.facteur - lampe.intensity) * part;
}
// Le Heikhal et le Kodesh HaKodashim s'éclairent à leurs lampes, réglées sans adaptation.
const SANS_ADAPTATION = new Set(["heikhal", "kodesh_hakodashim"]);
function accorderExposition(dt) {
  oeilAdapte.mesurer(camera.position);
  const facteur = SANS_ADAPTATION.has(lieuPresent) ? oeilAdapte.relacher(dt) : oeilAdapte.accorder(dt, rendu.luminance);
  renderer.toneMappingExposure = EXPOSITION.value = EXPOSITION_DEHORS * facteur;
}
// L'air ne rend que le ciel : sous un toit il n'a rien à rendre, et son voile couvrait le cèdre des lishkot.
function accorderAir(part) {
  brume.density += (AIR_DEHORS * (1 - oeilAdapte.fermeture) - brume.density) * part;
}

function releverLeLieu() {
  const part = 1 - Math.exp(-depuisLeReleve / REPONSE_LIEU);
  depuisLeReleve = 0;
  lieuPresent = lieuOccupe();
  accorderLampe(lieuPresent, part);
  accorderAir(part);
}

// Le cinéma comme le parcours prennent la caméra le temps d'un trajet : la boucle la leur prête.
let film = null;

function preterLaCamera(trajet) {
  film = trajet;
  if (trajet) return;
  marche.suivreLaCamera();
  marche.accorderRegard();
}

const guides = parcours({
  parcours: PARCOURS, camera, sol: marche.solEn, oeil: OEIL, ama: AMA,
  marcher: preterLaCamera,
  // Qui n'a pas quitté le cadre de toute la marche change à l'arrivée.
  arriver: () => {
    preterLaCamera(null);
    troupes.montrer();
  },
  poserA: (pieds, cible) => fondu(() => {
    tenirLaVue(false);
    marche.poser(pieds);
    marche.orienterVers(cible);
  }),
  changerDeMoment: (voulu) => {
    if (voulu === eclairage.moment) return;
    fondu(() => eclairage.passerAu(voulu));
  },
  changerDeTroupe: (voulue = TROUPE_LIBRE) => {
    if (troupes.demander(voulue)) fondu(() => troupes.presenter(voulue));
  },
  appelerFigurants: (noms) => fondu(() => {
    troupes.appeler(noms);
    troupes.montrer();
  }),
  relayerFigurants: troupes.appeler,
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

// Un figurant n'est dans la scène qu'avec sa troupe, à l'heure de son service : on le montre à la station qui l'appelle.
function stationQuiMontre(id) {
  const stations = PARCOURS.flatMap((p) => p.stations.map((station, rang) => ({ parcours: p.id, rang, station })));
  return stations.find(({ station }) => station.concept === id)
    ?? stations.find(({ station }) => station.figurants?.some((nom) => nom.replace(/_\d+$/, "") === id));
}

function montrerDemande(id) {
  const trouvee = !REPERES_DU_TEMPLE.has(id) && stationQuiMontre(id);
  if (!trouvee) return vues.allerVers(id);
  aide.classList.add("parti");
  guides.ouvrir(trouvee.parcours, trouvee.rang);
}
const demande = new URLSearchParams(location.search).get("vue");
if (demande) montrerDemande(demande);

// Le survol n'a pas besoin de 60 Hz.
function afficherSurvol() {
  const p = manette.pointeur;
  survole = p.survole && !manette.tourne ? designe.conceptSous(p.x, p.y) : null;
  const c = survole && CONCEPTS.get(survole);
  survol.classList.toggle("vu", !!c);
  if (!c) return;
  survol.textContent = c.nom;
  survol.style.left = `${p.clientX}px`;
  survol.style.top = `${p.clientY + 20}px`;
}

function afficherPosition() {
  position.textContent = brut
    ? `${(camera.position.x / AMA).toFixed(0)} · ` +
      `${(-camera.position.z / AMA).toFixed(0)} · ${(marche.piedsY / AMA).toFixed(0)} ${texte("amot")}`
    : (lieuPresent ? CONCEPTS.get(lieuPresent).nom : "");
  planMiddot.suivre(camera.position, camera.getWorldDirection(direction), lieuPresent);
}

function suivreLeFilm(dt) {
  film.avancer(dt);
  marche.suivreLaCamera();
}

function conduire(dt) {
  marche.lisserRegard(dt);
  avantLePas.copy(camera.position);
  marche.avancer(dt, manette);
  noterDeplacement(camera.position.distanceTo(avantLePas));
  if (marche.vol) noterAltitude(camera.position.y - avantLePas.y);
  if (entame || marche.elan <= 0.01) return;
  entame = true;                                  // le rappel a servi, il s'efface
  aide.classList.add("parti");
}

renderer.setAnimationLoop(() => {
  if (pannes.enReprise) return;
  const dt = Math.min(horloge.getDelta(), 0.1);
  const filme = film !== null;
  if (filme) suivreLeFilm(dt); else conduire(dt);
  ajusterEchelle(dt);
  depuisLeReleve += dt;
  if (++image % IMAGES_ENTRE_RELEVES === 0) {
    releverLeLieu();
    if (filme) troupes.relayerHorsDuCadre();
    else {
      afficherSurvol();
      afficherPosition();
    }
  }
  accorderExposition(dt);
  dessiner(dt);
});

$("#chargement").classList.add("parti");
pannes.lancer();
alleger(gltf.scene);

// Three renvoie seul géométries et images ; les cartes relâchées, les environnements, les ombres figées et le reflet du Heikhal sont à refaire.
async function reprendre() {
  eclairage.refaireLesReflets();
  scene.traverse((o) => { if (o.isLight && o.shadow) o.shadow.needsUpdate = true; });
  await rechargerCartes();
  if (!brut) refleterLeHeikhal();
}

// Au premier passage l'initiation remplace le rappel des commandes ; le « ? » la rejoue.
function commencerInitiation() {
  aide.classList.add("parti");
  lancerInitiation();
}
$("#rejouer").onclick = (e) => { e.currentTarget.blur(); commencerInitiation(); };
if (CINEMA) {
  film = cinema({ parcours: haltesCinema, camera, sol: marche.solEn, oeil: OEIL, ama: AMA, voile,
    signaler: (etat) => parent.postMessage({ type: "cinema", ...etat }, location.origin) });
  film.avancer(0);
  dessiner(0);
  parent.postMessage({ type: "cinema", pret: true }, location.origin);
  window.__cinema = { ...film, figer: () => renderer.setAnimationLoop(null) };
} else if (!initiationSuivie() && !guides.ouvert()) {
  // Ouverte sur une station, la carte du parcours tient la place de celle de l'initiation : elle attendra une autre visite.
  aide.classList.add("parti");
  // Le voile du chargement finit de se lever avant qu'on s'adresse au visiteur.
  langueChoisie.then(() => setTimeout(commencerInitiation, 700));
}

// Points d'accroche de la vérification headless (cdp.py) : sans eux, impossible de
// savoir depuis un terminal si la page a fini de charger ni ce qu'elle montre.
window.__vue = (id) => { vues.allerVers(id); dessiner(0); };
window.__demande = montrerDemande;
window.__vues = () => [...reperes.entrees, ...reperes.vues].map((v) => v.id);
window.__cam = (x, y, z, cx, cy, cz) => {
  camera.position.set(x, y, z); camera.lookAt(cx, cy, cz); marche.suivreLaCamera();
  marche.accorderRegard(); dessiner(0);
};
window.__rendre = () => dessiner(0);
window.__etat = () => {
  const e = new THREE.Euler(0, 0, 0, "YXZ").setFromQuaternion(camera.quaternion);
  const d = 180 / Math.PI;
  return { lacet: +(e.y * d).toFixed(2), tangage: +(e.x * d).toFixed(2), roulis: +(e.z * d).toFixed(4),
           x: +camera.position.x.toFixed(3), y: +camera.position.y.toFixed(3), z: +camera.position.z.toFixed(3),
           piedsY: +marche.piedsY.toFixed(3), vise: survole, echelle: +echelle.toFixed(2),
           fov: +camera.fov.toFixed(1), vol: marche.vol, lieu: lieuOccupe(),
           exposition: +renderer.toneMappingExposure.toFixed(3), fermeture: +oeilAdapte.fermeture.toFixed(2),
           luminance: rendu.luminance && +rendu.luminance.toFixed(4) };
};
window.__ombres = (actives) => {
  renderer.shadowMap.enabled = actives;
  soleil.shadow.needsUpdate = true;
  scene.traverse((o) => { if (o.isMesh) o.material.needsUpdate = true; });
  dessiner(0);
};
Object.defineProperty(window, "__figurants", { get: troupes.chargements });
window.__moteur = { renderer, scene };
window.__sol = marche.solEn;
window.__mur = (origine, direction, portee) => {
  const rayon = new THREE.Raycaster(new THREE.Vector3(...origine), new THREE.Vector3(...direction).normalize(), 0, portee);
  const [touche] = rayon.intersectObjects(murs, false);
  return touche ? { distance: touche.distance, concept: touche.object.userData.concept ?? touche.object.name } : null;
};
window.__parcours = guides;
window.__figurantsVus = troupes.figurantsVus;
window.__temps = (t) => { troupes.reglerLeTemps(t); dessiner(0); };
window.__pret = true;
