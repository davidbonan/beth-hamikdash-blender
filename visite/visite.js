import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { habiller, attiser } from "./matieres.js";

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

// Une étoffe ne barre pas le passage. La parokhet en particulier : le Cohen Gadol la
// franchit, et une visite qui s'arrête devant elle n'atteint jamais le Kodesh
// HaKodashim. Elles restent visibles et interrogeables, seulement traversables.
// Le Soreg y figure pour une autre raison : le blockout le pose continu sur tout le
// pourtour, sans les ouvertures qu'il avait (Middot 2:3). S'y cogner, ce serait buter
// sur un manque du modèle, pas sur l'architecture.
const TRAVERSABLES = new Set(["parokhet", "chaines_devir", "soreg"]);

const ZONES = {
  har_habayit: "Har HaBayit", ezrat_nashim: "Ezrat Nashim", azara: "Azara",
  mizbeach: "Mizbea'h", oulam: "Oulam", heikhal: "Heikhal",
  kodesh_hakodashim: "Kodesh HaKodashim", lishkot: "Lishkot",
};

// Sefaria distingue la michna du folio : `Middot 2:1` est une michna, `Yoma 54a` un
// folio de guemara. Le nom du traité est le même, le préfixe non — d'où le test sur
// la forme de la cote plutôt qu'une table à double entrée.
const TRAITES = {
  middot: "Middot", tamid: "Tamid", yoma: "Yoma", shekalim: "Shekalim",
  soucca: "Sukkah", souccah: "Sukkah", sukkah: "Sukkah", succa: "Sukkah",
  kelim: "Kelim", arakhin: "Arakhin", erakhin: "Arakhin",
  zevahim: "Zevachim", zevachim: "Zevachim",
  menahot: "Menachot", menachot: "Menachot",
  "baba batra": "Bava Batra", "bava batra": "Bava Batra",
  houlin: "Chullin", chullin: "Chullin", horayot: "Horayot",
  "yerushalmi yoma": "Jerusalem Talmud Yoma",
  pesachim: "Pesachim", pesahim: "Pesachim", "pessahim": "Pesachim",
};
const OUVRAGES = {
  "rambam beit habehira": "Mishneh Torah, The Chosen Temple",
  "beit habehira": "Mishneh Torah, The Chosen Temple",
  "rambam klei hamikdash": "Mishneh Torah, Vessels of the Sanctuary and Those Who Serve Therein",
  "rambam biat hamikdash": "Mishneh Torah, Admission into the Sanctuary",
  "melakhim i": "I Kings", "i rois": "I Kings", "rois i": "I Kings", "i melakhim": "I Kings",
  "divrei hayamim ii": "II Chronicles", "ii chroniques": "II Chronicles",
  yechezkel: "Ezekiel", ezechiel: "Ezekiel",
  shemot: "Exodus", exode: "Exodus",
  vayikra: "Leviticus", levitique: "Leviticus",
  devarim: "Deuteronomy", deuteronome: "Deuteronomy",
  bamidbar: "Numbers", nombres: "Numbers",
  "i samuel": "I Samuel", "shmuel i": "I Samuel",
  yirmeyahou: "Jeremiah", jeremie: "Jeremiah",
  yehezkel: "Ezekiel",
  "rambam temidin": "Mishneh Torah, Daily Offerings and Additional Offerings",
  "rashi exode": "Rashi on Exodus", "rashi shemot": "Rashi on Exodus",
  "rambam sur middot": "Rambam on Mishnah Middot",
};

const pele = (s) => (s || "").toLowerCase().normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "").replace(/['’.,]/g, "").replace(/\s+/g, " ").trim();

function lienSefaria(oeuvre, ref) {
  const clef = pele(oeuvre);
  const direct = OUVRAGES[clef];
  if (direct) return url(`${direct} ${ref}`);
  const traite = TRAITES[clef.replace(/^(mishna|mishnah|talmud) /, "")];
  if (!traite) return null;                       // archéologie, choix du projet : pas de cote Sefaria
  const folio = /^\d+[ab]$/.test((ref || "").trim());
  return url(`${folio ? traite : "Mishnah " + traite} ${ref}`);
}
const url = (tref) => "https://www.sefaria.org/" +
  encodeURIComponent(tref.replace(/ /g, "_")).replace(/%2C/g, ",").replace(/%3A/g, ":");

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
// l'esplanade. Un tampon linéaire y fait clignoter les deux surfaces l'une dans l'autre.
const renderer = new THREE.WebGLRenderer({
  antialias: true, powerPreference: "high-performance", logarithmicDepthBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.62;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0xc9cec8, 120, 560);

// L'or est métallique : sans environnement à réfléchir, il rend noir.
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

// L'ambiance ne doit PAS peser autant que le soleil. À 0,75 contre 1,9, chaque face
// recevait presque autant de lumière sans direction que de lumière du matin : le
// calcaire y perdait sa teinte et le modelé avec, et les murs rendaient un aplat gris.
// Le rapport compte plus que les niveaux — même arbitrage que le ciel du blockout.
scene.add(new THREE.HemisphereLight(0xcddcec, 0x8a7d66, 0.42));
// Matin, à l'est : l'axe de l'avoda, et la lumière qui creuse la façade de face.
const soleil = new THREE.DirectionalLight(0xfff2dc, 2.7);
soleil.castShadow = true;
soleil.shadow.mapSize.set(2048, 2048);
soleil.shadow.bias = -0.0002;
soleil.shadow.normalBias = 0.04;
// Fenêtre serrée : elle suit le visiteur, et 2048 texels sur 80 m donnent 4 cm de
// résolution — assez fin pour l'arête d'une assise, ce qu'une fenêtre couvrant tout
// le Har HaBayit ne donnerait jamais.
Object.assign(soleil.shadow.camera, { near: 1, far: 260, left: -40, right: 40, top: 40, bottom: -40 });
scene.add(soleil, soleil.target);
const appoint = new THREE.DirectionalLight(0xb9c6d4, 0.22);  // rebond du ciel à l'ouest
appoint.position.set(-140, 70, -40);
scene.add(appoint);

// Un dôme dégradé plutôt qu'un aplat : sans horizon, le Har HaBayit flotte.
const ciel = new THREE.Mesh(
  new THREE.SphereGeometry(760, 32, 16),
  new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { hautCiel: { value: new THREE.Color(0x4d7fb8) },
                basCiel: { value: new THREE.Color(0xd8dcd4) },
                solCiel: { value: new THREE.Color(0xa89c86) } },
    vertexShader: `varying vec3 vD; void main(){ vD = position;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform vec3 hautCiel, basCiel, solCiel; varying vec3 vD;
      void main(){ float h = normalize(vD).y;
        vec3 c = h > 0.0 ? mix(basCiel, hautCiel, pow(h, 0.55)) : mix(basCiel, solCiel, min(-h * 6.0, 1.0));
        gl_FragColor = vec4(c, 1.0); }`,
  }));
ciel.frustumCulled = false;
scene.add(ciel);

const camera = new THREE.PerspectiveCamera(62, innerWidth / innerHeight, 0.12, 1400);
// Une lampe discrète accrochée à la tête : sans elle le Heikhal, qui n'a pas de
// fenêtre ouvrante dans le blockout, est une pièce noire.
const lampe = new THREE.PointLight(0xffe9c4, 6, 26, 1.7);
camera.add(lampe);
scene.add(camera);

// ---------------------------------------------------------------------------
// modèle
// ---------------------------------------------------------------------------
const obstacles = [];
const gltf = await new GLTFLoader().loadAsync("./temple.glb", (e) => {
  if (e.lengthComputable) jauge.style.width = `${(e.loaded / e.total) * 100}%`;
});
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
  o.material.side = THREE.DoubleSide;   // murs et voiles sont des boîtes fines
  o.castShadow = true;
  o.receiveShadow = true;
  if (!brut && !habillees.has(o.material.uuid)) {
    habillees.add(o.material.uuid);
    habiller(o.material, horloges);
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

// Le regard suit le glissé, pas le curseur : bouton relâché, la souris redevient
// libre pour la barre du haut et la fiche.
const SENSIBILITE = 0.0022;
const TANGAGE_MAX = Math.PI / 2 - 0.02;
const SEUIL_CLIC = 5;                     // px parcourus au-delà desquels c'est un glissé
const toile = renderer.domElement;
const regard = new THREE.Euler(0, 0, 0, "YXZ");
const souris = new THREE.Vector2();
let glisse = null, surLaToile = false;

function tourner(dx, dy) {
  regard.setFromQuaternion(camera.quaternion);
  regard.y -= dx * SENSIBILITE;
  regard.x = THREE.MathUtils.clamp(regard.x - dy * SENSIBILITE, -TANGAGE_MAX, TANGAGE_MAX);
  regard.z = 0;
  camera.quaternion.setFromEuler(regard);
}

toile.addEventListener("pointerdown", (e) => {
  if (e.button !== 0) return;
  glisse = { id: e.pointerId, x: e.clientX, y: e.clientY, parcours: 0 };
  toile.setPointerCapture(e.pointerId);
  toile.classList.add("tourne");
});

toile.addEventListener("pointermove", (e) => {
  surLaToile = true;
  souris.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  survol.style.left = `${e.clientX}px`;
  survol.style.top = `${e.clientY + 20}px`;
  if (!glisse || e.pointerId !== glisse.id) return;
  const dx = e.clientX - glisse.x, dy = e.clientY - glisse.y;
  glisse.x = e.clientX; glisse.y = e.clientY;
  glisse.parcours += Math.abs(dx) + Math.abs(dy);
  tourner(dx, dy);
});

function lacher(e) {
  if (!glisse || e.pointerId !== glisse.id) return null;
  const parcours = glisse.parcours;
  glisse = null;
  toile.classList.remove("tourne");
  if (toile.hasPointerCapture(e.pointerId)) toile.releasePointerCapture(e.pointerId);
  return parcours;
}

toile.addEventListener("pointerup", (e) => {
  const parcours = lacher(e);
  if (parcours === null || parcours >= SEUIL_CLIC) return;
  if (vise) montrer(vise); else fermer();
});
toile.addEventListener("pointercancel", lacher);
toile.addEventListener("pointerleave", () => { surLaToile = false; });
toile.addEventListener("contextmenu", (e) => e.preventDefault());

const touches = new Set();
const AVANT = ["KeyW", "KeyZ", "ArrowUp"], ARRIERE = ["KeyS", "ArrowDown"];
const GAUCHE = ["KeyA", "KeyQ", "ArrowLeft"], DROITE = ["KeyD", "ArrowRight"];
const enfoncee = (l) => l.some((c) => touches.has(c));
const dansLaBarre = () => !!document.activeElement?.closest?.("#barre, #fiche");
addEventListener("keydown", (e) => {
  if (dansLaBarre()) return;
  touches.add(e.code);
  if (e.code === "KeyV") basculerVol();
  if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space"].includes(e.code)) e.preventDefault();
});
addEventListener("keyup", (e) => touches.delete(e.code));
addEventListener("blur", () => touches.clear());

let piedsY = 0;
const avant = new THREE.Vector3(), droite = new THREE.Vector3();
const HAUT = new THREE.Vector3(0, 1, 0), pas = new THREE.Vector3();

// Le Temple ne se laisse pas traverser n'importe où : on monte à l'Ezrat Nashim par
// les douze degrés du 'Heil, à l'Azara par les quinze marches, et l'autel se contourne.
// C'est l'architecture, pas un défaut — mais un modèle se regarde aussi d'ailleurs que
// d'où l'on a le droit de se tenir : le vol libre est là pour ça.
let vol = false;

function voler(dt) {
  const long = (enfoncee(AVANT) ? 1 : 0) - (enfoncee(ARRIERE) ? 1 : 0);
  const lat = (enfoncee(DROITE) ? 1 : 0) - (enfoncee(GAUCHE) ? 1 : 0);
  const vert = (touches.has("Space") ? 1 : 0) - (touches.has("KeyC") ? 1 : 0);
  if (!long && !lat && !vert) return;
  camera.getWorldDirection(avant);
  droite.crossVectors(avant, HAUT).normalize();
  pas.set(0, 0, 0).addScaledVector(avant, long).addScaledVector(droite, lat).normalize()
     .addScaledVector(HAUT, vert);
  const vitesse = VOL * (touches.has("ShiftLeft") || touches.has("ShiftRight") ? COURSE : 1);
  camera.position.addScaledVector(pas, vitesse * dt);
  piedsY = camera.position.y - OEIL;
}

function avancer(dt) {
  if (vol) return voler(dt);
  const long = (enfoncee(AVANT) ? 1 : 0) - (enfoncee(ARRIERE) ? 1 : 0);
  const lat = (enfoncee(DROITE) ? 1 : 0) - (enfoncee(GAUCHE) ? 1 : 0);
  if (!long && !lat) return;

  camera.getWorldDirection(avant); avant.y = 0; avant.normalize();
  droite.crossVectors(avant, HAUT).normalize();
  pas.set(0, 0, 0).addScaledVector(avant, long).addScaledVector(droite, lat).normalize();

  const vitesse = PAS * (touches.has("ShiftLeft") || touches.has("ShiftRight") ? COURSE : 1);
  // Le pas se découpe : à bas framerate un seul bond franchirait la garde.
  let reste = Math.min(vitesse * dt, 1.2);
  while (reste > 1e-4) {
    const distance = Math.min(reste, SOUS_PAS);
    reste -= distance;
    if (murDevant(camera.position, piedsY, pas, distance)) return;
    const x = camera.position.x + pas.x * distance, z = camera.position.z + pas.z * distance;
    const sol = solEn(x, z, piedsY);
    if (sol === null) return;                      // le vide : on refuse le pas
    piedsY = sol;
    camera.position.set(x, sol + OEIL, z);
  }
}

function poser(x, y, z, cap) {
  const sol = vol ? null : solEn(x, z, y + 0.3);
  piedsY = sol === null ? y : sol;
  camera.position.set(x, piedsY + OEIL, z);
  if (cap !== undefined) {
    // Cap en degrés dans le repère de la fiche : 0 = est, 180 = ouest, l'axe du
    // parcours du Cohen Gadol. Le nord de Blender devient -Z une fois passé en Y-haut.
    const a = THREE.MathUtils.degToRad(cap);
    camera.lookAt(x + Math.cos(a) * 10, piedsY + OEIL, z - Math.sin(a) * 10);
  }
}

// ---------------------------------------------------------------------------
// interrogation
// ---------------------------------------------------------------------------
const viseur = new THREE.Raycaster();
const survol = $("#survol");
let vise = null;

function conceptVise() {
  viseur.setFromCamera(souris, camera);
  viseur.far = 140;
  const touche = viseur.intersectObjects(obstacles, false);
  return touche.length ? touche[0].object.userData.concept || null : null;
}

const corps = $("#corps"), panneau = $("#fiche");
const echappe = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function montrer(id) {
  const c = CONCEPTS.get(id);
  if (!c) return;
  const src = (c.sources || []).map((s) => {
    const lien = lienSefaria(s.oeuvre, s.ref);
    const tete = `${echappe(s.oeuvre)} ${echappe(s.ref)}`;
    return `<li>${lien ? `<a href="${lien}" target="_blank" rel="noopener">${tete}</a>` : tete}` +
           `${s.citation ? `<em>« ${echappe(s.citation)} »</em>` : ""}</li>`;
  }).join("");

  corps.innerHTML = `
    <p class="zone">${echappe(ZONES[c.zone] || c.zone)}</p>
    <h2>${echappe(c.nom)}</h2>
    ${c.he ? `<p class="heb">${echappe(c.he)}</p>` : ""}
    ${c.translit ? `<p class="translit">${echappe(c.translit)}</p>` : ""}
    ${c.resume
      ? `<p class="resume">${echappe(c.resume)}</p>`
      : `<p class="vide">Cet élément est modélisé mais pas encore documenté : aucune
         source n'a été relevée pour lui dans la fiche technique. Plutôt qu'une cote
         plausible, la visite n'affiche rien.</p>`}
    ${c.cotes?.length ? `<h3>Cotes</h3><ul class="cotes">${
      c.cotes.map((x) => `<li>${echappe(x)}</li>`).join("")}</ul>` : ""}
    ${src ? `<h3>Sources</h3><ul class="sources">${src}</ul>` : ""}
    ${c.note ? `<p class="note"><b>Arbitrage du projet</b>${echappe(c.note)}</p>` : ""}`;
  panneau.classList.add("ouverte");
}

const fermer = () => panneau.classList.remove("ouverte");
$("#fermer").onclick = fermer;

// ---------------------------------------------------------------------------
// barre
// ---------------------------------------------------------------------------
const aller = $("#aller"), chercher = $("#chercher"), position = $("#position");
for (const e of reperes.entrees) {
  aller.append(new Option(e.nom, e.id));
}
aller.onchange = () => {
  const e = reperes.entrees.find((x) => x.id === aller.value);
  if (e) poser(e.position[0], e.position[1], e.position[2], e.cap);
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
  allerA(id);
  chercher.value = "";
  chercher.blur();
};

// ---------------------------------------------------------------------------
// boucle
// ---------------------------------------------------------------------------
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

const mode = $("#mode");
function basculerVol() {
  vol = !vol;
  mode.textContent = vol ? "vol libre" : "à pied";
  mode.classList.toggle("vole", vol);
  if (!vol) {                                   // en reprenant pied, retrouver le sol
    const sol = solEn(camera.position.x, camera.position.z, camera.position.y - OEIL + 0.3);
    if (sol !== null) { piedsY = sol; camera.position.y = sol + OEIL; }
  }
}
$("#vol").onclick = (e) => { basculerVol(); e.currentTarget.blur(); };

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
  return true;
}

const demande = new URLSearchParams(location.search).get("vue");
const depart = reperes.entrees.find((e) => e.id === "azara") || reperes.entrees[0];
poser(depart.position[0], depart.position[1], depart.position[2], depart.cap);
if (demande) allerA(demande);

const horloge = new THREE.Clock();
let image = 0;

// L'ombre portée est une fenêtre de 110 amot ; à l'échelle du Har HaBayit une seule
// carte figée serait illisible. Elle suit donc le visiteur.
const SOLEIL = new THREE.Vector3(150, 125, 55);
function suivreSoleil() {
  soleil.target.position.copy(camera.position);
  soleil.position.copy(camera.position).add(SOLEIL);
  soleil.target.updateMatrixWorld();
}

function dessiner(dt) {
  for (const u of horloges) u.value += dt;
  suivreSoleil();
  ciel.position.copy(camera.position);
  renderer.render(scene, camera);
}

renderer.setAnimationLoop(() => {
  const dt = Math.min(horloge.getDelta(), 0.1);
  avancer(dt);

  if (++image % 4 === 0) {                        // le survol n'a pas besoin de 60 Hz
    vise = surLaToile && !glisse ? conceptVise() : null;
    const c = vise && CONCEPTS.get(vise);
    survol.classList.toggle("vu", !!c);
    if (c) survol.textContent = c.nom;
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
  camera.position.set(x, y, z); camera.lookAt(cx, cy, cz); piedsY = y - OEIL; dessiner(0);
};
window.__rendre = () => dessiner(0);
window.__etat = () => {
  const e = new THREE.Euler(0, 0, 0, "YXZ").setFromQuaternion(camera.quaternion);
  const d = 180 / Math.PI;
  return { lacet: +(e.y * d).toFixed(2), tangage: +(e.x * d).toFixed(2), roulis: +(e.z * d).toFixed(4),
           x: +camera.position.x.toFixed(3), z: +camera.position.z.toFixed(3),
           piedsY: +piedsY.toFixed(3), vise, glisse: !!glisse };
};
window.__ombres = (actives) => {
  renderer.shadowMap.enabled = actives;
  scene.traverse((o) => { if (o.isMesh) o.material.needsUpdate = true; });
  dessiner(0);
};
window.__pret = true;
