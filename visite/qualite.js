/**
 * Ce que la machine peut tenir.
 *
 * Un téléphone n'est pas une station de travail plus lente : c'est un GPU à tuiles,
 * qui doit trier ses fragments AVANT de les ombrer. Tout ce qui l'en empêche — des
 * faces des deux côtés, un bruit à trois octaves par pixel — lui coûte bien plus
 * qu'au bureau. Le profil ci-dessous décide donc de ceux-là, et le reste du fichier
 * n'en sait rien.
 *
 * Un appareil tactile ne dit rien de lui : au premier passage, un banc lie un vrai
 * programme de matière dans un contexte jetable — 10 ms sur un iPhone, 60 ms et bien
 * plus sur l'iPad qui perdrait son contexte au cinquantième — et le lent part en sobre.
 * Le visiteur peut aussi choisir son profil dans la barre, hors ceux qui sont tombés.
 *
 * `?qualite=basse` force le profil léger depuis un bureau, `?qualite=minimale` le très
 * léger, `?qualite=sobre` le sobre : c'est ainsi qu'on les vérifie sans téléphone sous la main.
 */
import { suivreLangue, texte } from "./langue.js";
import { lireRetenu, oublier, retenir } from "./memoire.js";

const demande = new URLSearchParams(location.search).get("qualite");

const tactile = matchMedia("(hover: none) and (pointer: coarse)").matches;
const coeurs = navigator.hardwareConcurrency || 8;
// Seul Chrome d'Android dit sa mémoire : un iPhone faible ne se reconnaît qu'à l'usage, par `seReplier`, et le téléphone pris pour faible se dément par `seRelever`.
const faible = tactile && (navigator.deviceMemory <= 4 || coeurs <= 4);
const RETENU = "visite-profil-retenu", REPLIS = "visite-profil-replis", CHOISI = "visite-profil-choisi", TOMBE = "visite-profil-tombe";
// Du plus riche au plus pauvre.
export const NIVEAUX = ["haute", "basse", "minimale", "sobre"];
// Un téléphone descend et remonte d'un cran à la fois, jamais jusqu'au profil lourd.
const REPLIABLES = NIVEAUX.slice(1);
// Une remontée qui a échoué ce nombre de fois ne se retente plus : le profil battrait d'une visite à l'autre.
const REPLIS_MAX = 2;
// Mesuré sur le programme du banc, contexte froid : 10 à 20 ms sur un iPhone et le simulateur, 60 à 4 800 sur l'iPad qui tombe.
const LIAISON_LENTE_MS = 40;
const VERSION = new URL(import.meta.url).search;

async function niveauDeLaMachine() {
  if (!tactile && coeurs > 4) return "haute";
  const retenu = lireRetenu(RETENU);
  if (REPLIABLES.includes(retenu)) return retenu;
  if (await liaisonLente()) {
    retenir(RETENU, "sobre");
    return "sobre";
  }
  return faible ? "minimale" : "basse";
}

// Avec KHR_parallel_shader_compile on n'attend pas la fin de la liaison : pas liée au délai, elle est lente.
// Sans elle, la question bloque jusqu'à la liaison, et c'est sa durée qui juge.
async function liaisonLente() {
  const gl = document.createElement("canvas").getContext("webgl2");
  if (!gl) return false;
  let sommet, fragment;
  try { ({ sommet, fragment } = await (await fetch("./banc.json" + VERSION)).json()); } catch { return false; }
  if (document.hidden) await new Promise((r) => document.addEventListener("visibilitychange", r, { once: true }));
  const debut = performance.now();
  const programme = gl.createProgram();
  for (const [type, source] of [[gl.VERTEX_SHADER, sommet], [gl.FRAGMENT_SHADER, fragment]]) {
    const nuanceur = gl.createShader(type);
    gl.shaderSource(nuanceur, source);
    gl.compileShader(nuanceur);
    gl.attachShader(programme, nuanceur);
  }
  gl.linkProgram(programme);
  const parallele = gl.getExtension("KHR_parallel_shader_compile");
  const liee = () => gl.getProgramParameter(programme, parallele ? parallele.COMPLETION_STATUS_KHR : gl.LINK_STATUS);
  let finie = liee();
  while (parallele && !finie && performance.now() - debut < LIAISON_LENTE_MS) {
    await new Promise((r) => setTimeout(r, 4));
    finie = liee();
  }
  const duree = performance.now() - debut;
  gl.getExtension("WEBGL_lose_context")?.loseContext();
  const lente = !finie || duree >= LIAISON_LENTE_MS;
  window.__banc = { ms: Math.round(duree), parallele: !!parallele, lente };
  return lente;
}

const LOURD = { dprMax: 2, definitionMax: 1.5, echelles: [1, 0.85, 0.7], echelleDepart: 1, antiCrenelage: 4, grainLeger: false, preProfondeur: true,
  habillageEssentiel: false, paysage: true,
  textures: { decor: Infinity, figurants: Infinity, nappes: true }, ecartDetail: 1, porteeDetail: Infinity,
  ombres: { taille: 2048, portee: 40, penombre: true, lointaine: 2048 }, occlusion: 12,
  halo: { force: 0.20, rayon: 0.6, seuil: 1.6 }, rayons: { densite: 0.004, prises: 40 }, sanctuaire: { ombre: true, carte: Infinity }, feux: { ombre: true, carte: Infinity }, figurants: { presents: true, ombre: true },
  fumee: { pas: 48, octaves: 3 } };

// Un téléphone part à `echelleDepart` et ne monte au-dessus qu'en tenant ses 60 images : chaque iPhone trouve la sienne.
// `preProfondeur` : à 390 × 844 elle coûte plus de géométrie qu'elle n'épargne de pixels (50 → 39 ms mesurés sans elle).
const LEGER = { dprMax: 1.5, definitionMax: 1, echelles: [1.5, 1.25, 1, 0.85, 0.75], echelleDepart: 1, antiCrenelage: 4, grainLeger: true, preProfondeur: false,
  habillageEssentiel: false, paysage: true,
  textures: { decor: 1024, figurants: 512, nappes: true }, ecartDetail: 1, porteeDetail: Infinity,
  ombres: { taille: 1024, portee: 26, penombre: false, lointaine: 1024 }, occlusion: 6,
  halo: { force: 0.16, rayon: 0.6, seuil: 1.6 }, rayons: { densite: 0.004, prises: 12 }, sanctuaire: { ombre: true, carte: 256 }, feux: { ombre: false, carte: 256 }, figurants: { presents: true, ombre: false },
  fumee: { pas: 16, octaves: 2 } };

// `halo` et `rayons` nuls = pas de passe du tout, et pas seulement une force nulle : leurs cibles sont allouées par leur constructeur, qu'elles servent ou non.
// `occlusion` nulle épargne aussi la passe de géométrie qu'elle lisait, hors du Kodesh HaKodashim dont la fumée la lit encore.
const TRES_LEGER = { ...LEGER, dprMax: 1, echelles: [1, 0.85, 0.7, 0.55], echelleDepart: 0.7,
  textures: { decor: 512, figurants: 256, nappes: true }, ecartDetail: 2,
  occlusion: 0, halo: null, rayons: null,
  fumee: { pas: 8, octaves: 1 } };

// Un vieil iPad perd son contexte en compilant les nuanceurs de matière, passé la quarantaine : seules les familles qui couvrent l'écran gardent leur appareil, sans pays ni figurants, qui ont les leurs.
// Sans nappes ni ombre des lampes : sur son GPU l'image passait de 80-106 ms à 52-57, les nappes pour moitié.
// `antiCrenelage` nul : la cible de la scène n'est plus multi-échantillonnée, le FXAA de la chaîne reste seul sur les arêtes.
// `porteeDetail` : du parvis, le Kotel et ses abords, derrière les murs, faisaient encore un quart des triangles tracés.
const SOBRE = { ...TRES_LEGER, antiCrenelage: 0, habillageEssentiel: true, paysage: false, figurants: { presents: false, ombre: false },
  textures: { decor: 512, figurants: 256, nappes: false }, sanctuaire: { ombre: false, carte: 256 }, porteeDetail: 150 };

const PROFILS = { haute: LOURD, basse: LEGER, minimale: TRES_LEGER, sobre: SOBRE };
const force = demande in PROFILS;
const choisi = lireRetenu(CHOISI);
let manuel = !force && choisi in PROFILS;

export const NIVEAU = force ? demande : manuel ? choisi : await niveauDeLaMachine();
export const PROFIL = PROFILS[NIVEAU];

const replis = () => Number(lireRetenu(REPLIS) ?? 0);
let bascule = false;

function basculerVers(voulu) {
  bascule = true;
  retenir(RETENU, voulu);
}

const rang = REPLIABLES.indexOf(NIVEAU);

// Le profil qui n'a pas tenu — contexte perdu, rythme lent au dernier palier — part au cran du dessous à la visite suivante.
export function seReplier() {
  if (force || manuel || bascule || rang < 0 || rang === REPLIABLES.length - 1) return;
  retenir(REPLIS, String(replis() + 1));
  basculerVers(REPLIABLES[rang + 1]);
}

// Le profil tenu sans peine à son premier palier repart au cran du dessus à la visite suivante.
export function seRelever() {
  if (force || manuel || bascule || rang < 1 || replis() >= REPLIS_MAX) return;
  basculerVers(REPLIABLES[rang - 1]);
}

// Le contexte perdu condamne le profil et ceux au-dessus : la barre ne les offre plus. Un choix manuel qui tombe rend la main.
export function tomber() {
  if (NIVEAUX.indexOf(NIVEAU) > NIVEAUX.indexOf(lireRetenu(TOMBE))) retenir(TOMBE, NIVEAU);
  if (manuel) {
    manuel = false;
    oublier(CHOISI);
  }
  seReplier();
}

const estTombe = (niveau) => NIVEAUX.indexOf(niveau) <= NIVEAUX.indexOf(lireRetenu(TOMBE));

// "" : l'automatique.
function choisir(niveau) {
  if (niveau) retenir(CHOISI, niveau);
  else oublier(CHOISI);
}

function boutonsDeNiveau() {
  const courant = manuel ? NIVEAU : "";
  return ["", ...NIVEAUX].map((niveau) => {
    const bouton = document.createElement("button");
    bouton.type = "button";
    bouton.dataset.niveau = niveau;
    bouton.setAttribute("aria-pressed", String(niveau === courant));
    bouton.textContent = niveau ? texte(`qualite_${niveau}`)
      : manuel ? texte("qualite_auto") : `${texte("qualite_auto")} (${texte(`qualite_${NIVEAU}`).toLowerCase()})`;
    if (niveau && estTombe(niveau)) {
      bouton.disabled = true;
      bouton.append(` — ${texte("qualite_tombee")}`);
    }
    return bouton;
  });
}

// Le profil est figé au chargement, lu par toute la visite : en changer, c'est la recharger.
export function brancherChoix({ recharger }) {
  const bouton = document.querySelector("#qualite-courante");
  const menu = document.querySelector("#qualite-menu");
  const ouvrirMenu = () => { menu.hidden = false; bouton.setAttribute("aria-expanded", "true"); };
  const fermerMenu = () => { menu.hidden = true; bouton.setAttribute("aria-expanded", "false"); };
  const remplir = () => {
    const note = document.createElement("small");
    note.textContent = texte("qualite_recharge");
    menu.replaceChildren(...boutonsDeNiveau(), note);
  };

  remplir();
  suivreLangue(remplir);
  bouton.onclick = () => (menu.hidden ? ouvrirMenu() : fermerMenu());
  menu.onclick = (e) => {
    const choix = e.target.closest("[data-niveau]");
    if (!choix) return;
    fermerMenu();
    if (choix.getAttribute("aria-pressed") === "true") return;
    choisir(choix.dataset.niveau);
    recharger();
  };
  addEventListener("pointerdown", (e) => { if (!e.target.closest?.("#qualite")) fermerMenu(); });
  addEventListener("keydown", (e) => { if (e.key === "Escape") fermerMenu(); });
}

// La mémoire GPU est ce qui fait perdre son contexte WebGL à un iPhone : au-delà de `cote`, une texture pèse sans rien montrer de plus sur un petit écran.
// Safari prémultiplie tout ImageBitmap : une carte qui écrit sous un alpha nul, comme la parokhet, ne passe pas par ici.
export async function plafonner(texture, cote) {
  const { image } = texture;
  const plus = Math.max(image.width, image.height);
  if (plus <= cote) return;
  const k = cote / plus;
  texture.image = await createImageBitmap(image, {
    resizeWidth: Math.round(image.width * k), resizeHeight: Math.round(image.height * k), resizeQuality: "high",
    imageOrientation: texture.flipY ? "flipY" : "none", premultiplyAlpha: "none", colorSpaceConversion: "none",
  });
  texture.flipY = false;
  image.close?.();
  texture.needsUpdate = true;
}
