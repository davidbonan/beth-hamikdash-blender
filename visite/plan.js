import { nomDeZone } from "./fiche.js";
import { ecrire, langue, libelle, texte } from "./langue.js";
import { gestesDuPlan } from "./gestes_du_plan.js";
import { allerA } from "./aller_a.js";

const SVG = "http://www.w3.org/2000/svg";
const TAILLE_ETIQUETTE = 13;   // px
const LONGUEUR_VISITEUR = 18;  // px, le faisceau du visiteur sur le plan entier
const RAYON_PIED = 13;         // px : le disque où la flèche d'arrivée tourne, sous l'épingle
const HAUTEUR_EPINGLE = 30 + 2 * RAYON_PIED; // px
const HAUTEUR_ETAGE = 10;      // mètres : un lieu qui commence plus haut est à l'étage
const FENETRE_MINI = 60;       // mètres : ce que la minicarte montre autour du visiteur
const VUE_OUVERTURE = 150;     // mètres : ce que le plan montre autour du visiteur à l'ouverture
const PART_ECHELLE = 0.25;     // de la largeur visible, ce que la barre d'échelle du plan couvre au plus
const LONGUEURS_ECHELLE = [100, 50, 25, 20, 10, 5, 2, 1]; // amot
const PX_PAR_AMA_MAX = 20;     // au zoom le plus serré
// Zoomé sur un bâtiment qui a sa coupe, le plan y entre ; il en ressort un peu plus loin, pour ne pas battre au seuil.
const PART_BASCULE = 0.8;
const HYSTERESE = 0.85;
const ATTENTE_ETIQUETTES_MS = 120;
const MARGE_BULLE = 8;         // px
const FLECHE = "M 1 0 L -0.6 0.65 L -0.3 0 L -0.6 -0.65 Z";
const FAISCEAU = "M 0 0 L 1.3 -0.75 A 1.5 1.5 0 0 1 1.3 0.75 Z";
const RAYON_POINT = 0.42;      // du faisceau
const EPINGLE = "M 0 0 C -2 -7 -10 -12 -10 -19 A 10 10 0 1 1 10 -19 C 10 -12 2 -7 0 0 Z";

const noeud = (nom, attributs = {}) => {
  const n = document.createElementNS(SVG, nom);
  for (const [clef, valeur] of Object.entries(attributs)) n.setAttribute(clef, valeur);
  return n;
};

const surface = (b) => (b.max.x - b.min.x) * (b.max.z - b.min.z);
const largeurDe = (cadre) => cadre.max[0] - cadre.min[0];
const hauteurDe = (cadre) => cadre.max[1] - cadre.min[1];
const contient = (cadre, x, z) => x >= cadre.min[0] && x <= cadre.max[0] && z >= cadre.min[1] && z <= cadre.max[1];
const contientAPlat = (b, x, z) => x >= b.min.x && x <= b.max.x && z >= b.min.z && z <= b.max.z;
const croiseAPlat = (a, b) => a.min.x < b.max.x && b.min.x < a.max.x && a.min.z < b.max.z && b.min.z < a.max.z;
const croise = (a, b) => a.x < b.x + b.l && b.x < a.x + a.l && a.y < b.y + b.h && b.y < a.y + a.h;

function centreDes(ids, emprises) {
  const boites = ids.map((id) => emprises.get(id)).filter(Boolean);
  if (!boites.length) return null;
  return {
    x: (Math.min(...boites.map((b) => b.min.x)) + Math.max(...boites.map((b) => b.max.x))) / 2,
    z: (Math.min(...boites.map((b) => b.min.z)) + Math.max(...boites.map((b) => b.max.z))) / 2,
  };
}

export const lieuxSouterrains = (dessin) => new Set(dessin.niveaux.filter((n) => n.souterraine).flatMap((n) => n.lieux));

// Le plan de surface, puis une coupe par bâtiment ou souterrain.
function niveauxDu(dessin, tousLesLieux, emprises) {
  const souterrains = lieuxSouterrains(dessin);
  // Du plus petit au plus grand au sol : le premier qui contient un point est le lieu qu'on y lit. Au volume,
  // l'esplanade d'Hérode, mince, passerait avant l'Azara qu'elle entoure.
  const lieux = [...tousLesLieux].sort((a, b) => surface(emprises.get(a)) - surface(emprises.get(b)));
  // En plein air, ce qui se voit d'en haut et tient tout entier dans le plan.
  const lieuxDeSurface = lieux.filter((id) => {
    const b = emprises.get(id);
    return !souterrains.has(id) && b.min.y <= HAUTEUR_ETAGE
      && contient(dessin, b.min.x, b.min.z) && contient(dessin, b.max.x, b.max.z);
  });
  // Un lieu qui descend aux tunnels a, en surface, son plancher au-dessus d'eux : son escalier n'est pas son sol.
  const planchers = new Map(dessin.niveaux.filter((n) => n.souterraine).flatMap((n) => n.acces.map((id) => [id,
    Math.max(...n.lieux.map((l) => emprises.get(l)).filter((b) => croiseAPlat(b, emprises.get(id))).map((b) => b.max.y))])));
  const solDeSurface = { plafond: HAUTEUR_ETAGE, lieux: lieuxDeSurface, horsDesLieux: true, planchers };
  // En surface, un bâtiment qui a sa coupe ne porte que son nom : ses salles se nomment dans la coupe.
  const salles = new Set(dessin.niveaux.filter((n) => !n.souterraine).flatMap((n) => n.lieux.filter((id) => id !== n.id)));
  const deSurface = { id: "surface", coupe: null, lieux: lieuxDeSurface, nommes: lieuxDeSurface.filter((id) => !salles.has(id)), sol: solDeSurface };
  const coupes = dessin.niveaux.map((coupe) => {
    const lieuxDeLaCoupe = lieux.filter((id) => coupe.lieux.includes(id));
    const souterraine = !!coupe.souterraine;
    return {
      id: coupe.id, coupe, souterraine,
      lieux: souterraine ? lieuxDeLaCoupe : lieuxDeSurface,
      nommes: souterraine ? lieuxDeLaCoupe : lieuxDeSurface,
      lieuxDeLaCoupe,
      sol: { plafond: coupe.coupe, lieux: lieuxDeLaCoupe, horsDesLieux: false, ailleurs: souterraine ? null : solDeSurface },
    };
  });
  return [deSurface, ...coupes];
}

// Une couche par catégorie, dans l'ordre du dessin : la feuille de style en donne les teintes.
function couches(liste, classe) {
  const groupe = noeud("g", { class: classe });
  for (const { categorie, d } of liste) groupe.append(noeud("path", { d, class: categorie }));
  return groupe;
}

function fondDeVille(ville) {
  const groupe = noeud("g", { class: "ville" });
  groupe.append(noeud("path", { d: ville.batiments, class: "batiments" }), noeud("path", { d: ville.murailles, class: "murailles" }));
  return groupe;
}

function visiteurDessine() {
  const visiteur = noeud("g", { class: "visiteur" });
  visiteur.append(noeud("path", { class: "faisceau", d: FAISCEAU }), noeud("circle", { class: "point", r: RAYON_POINT }));
  return visiteur;
}

export function plan({ dessin, emprises, lieux, entrees, concepts, ama,
  piedsAuPoint, piedsDeLElement, capDuTrajet, allerAuPoint, allerVers, allerElement }) {
  const bouton = document.querySelector("#minicarte .disque");
  const fenetre = document.querySelector("#plan");
  const mini = bouton.querySelector("svg");
  const carte = fenetre.querySelector(".carte");
  const entier = carte.querySelector("svg");
  const barre = fenetre.querySelector(".echelle");
  const choixNiveau = carte.querySelector(".niveaux");
  const bulle = carte.querySelector(".bulle");
  const nomBulle = bulle.querySelector(".nom"), inaccessible = bulle.querySelector(".inaccessible");
  const allerIci = bulle.querySelector(".aller-ici"), vueDuLieu = bulle.querySelector(".vue-du-lieu");

  const niveaux = niveauxDu(dessin, lieux, emprises);
  const [deSurface] = niveaux;
  const souterrains = lieuxSouterrains(dessin);
  const nomDe = (id) => concepts.get(id)?.nom ?? id;
  const nomDeLEntree = (entree) => libelle("entrees", entree.id) ?? entree.nom;
  // La part du plan qu'une coupe couvre vraiment : ses lieux, pas son cadre.
  const foyers = new Map(niveaux.filter((n) => n.coupe).map((n) => {
    const boites = n.lieuxDeLaCoupe.map((id) => emprises.get(id));
    return [n, {
      min: { x: Math.min(...boites.map((b) => b.min.x)), z: Math.min(...boites.map((b) => b.min.z)) },
      max: { x: Math.max(...boites.map((b) => b.max.x)), z: Math.max(...boites.map((b) => b.max.z)) },
    }];
  }));

  let pose = null, lieuDuVisiteur = null;
  let niveau = deSurface, auto = true;
  let epingle = null;
  let etiquetage = null;
  // Dessinés une fois : changer de niveau ne fait que les replacer.
  const ville = fondDeVille(dessin.ville);
  const deSurfaceDessine = couches(dessin.couches, "surface");
  const coupesDessinees = new Map(niveaux.filter((n) => n.coupe).map((n) => [n, couches(n.coupe.couches, n.souterraine ? "coupe souterraine" : "coupe")]));

  const gestes = gestesDuPlan(entier, {
    bornes: dessin,
    echelleMax: PX_PAR_AMA_MAX / ama,
    quandBouge: suivreLaVue,
    quandVise: viser,
  });

  const niveauDuLieu = (lieu) => niveaux.find((n) => n.coupe && n.lieuxDeLaCoupe.includes(lieu)) ?? deSurface;
  const niveauDeLaDestination = (id) => (emprises.has(id) ? niveauDuLieu(id) : deSurface);
  const lieuNomme = (x, z) => niveau.lieux.find((id) => contientAPlat(emprises.get(id), x, z))
    ?? (niveau.sol.ailleurs && deSurface.lieux.find((id) => contientAPlat(emprises.get(id), x, z)));

  // ---- minicarte ----
  // Une coupe souterraine ne montre que ses tunnels : le plan de surface, pâli, les situe.
  function dessinerMini(voulu) {
    const fond = noeud("g", { class: voulu.souterraine ? "pale" : "" });
    fond.append(ville.cloneNode(true), deSurfaceDessine.cloneNode(true));
    mini.replaceChildren(fond, ...(voulu.souterraine ? [coupesDessinees.get(voulu).cloneNode(true)] : []), visiteurDessine());
    mini.dataset.niveau = voulu.id;
  }

  function poserVisiteur(svg, taille, present) {
    const visiteur = svg.querySelector(".visiteur");
    if (!pose || !visiteur) return;
    visiteur.setAttribute("visibility", present ? "visible" : "hidden");
    visiteur.setAttribute("transform",
      `translate(${pose.x.toFixed(2)} ${pose.z.toFixed(2)}) rotate(${pose.angle.toFixed(1)}) scale(${taille.toFixed(3)})`);
  }

  // ---- plan entier ----
  function afficherNiveau(voulu) {
    niveau = voulu;
    const dessous = noeud("g", { class: voulu.souterraine ? "pale" : "" });
    dessous.append(ville, deSurfaceDessine);
    const fond = noeud("g", { class: "fonds" });
    fond.append(dessous, ...(voulu.coupe ? [coupesDessinees.get(voulu)] : []));
    // Du plus grand au plus petit : à chaque échelle, les grands lieux se nomment d'abord.
    const etiquettes = noeud("g", { class: "etiquettes" });
    for (const id of [...voulu.nommes].sort((a, b) => surface(emprises.get(b)) - surface(emprises.get(a)))) {
      const [x, z] = pointDEtiquette(id);
      etiquettes.append(noeud("text", { x, y: z, "data-lieu": id }));
    }
    const visiteur = visiteurDessine();
    const marque = noeud("g", { class: "epingle", visibility: "hidden" });
    marque.append(noeud("circle", { class: "pied", r: RAYON_PIED }), noeud("path", { class: "apercu", d: FLECHE }),
      noeud("path", { class: "tete", d: EPINGLE, transform: `translate(0 ${-RAYON_PIED})` }));
    entier.replaceChildren(fond, etiquettes, visiteur, marque);
    for (const b of choixNiveau.children) b.setAttribute("aria-pressed", String(b.dataset.niveau === voulu.id));
    nommer();
  }

  // Au cœur de ce qu'on voit du lieu d'en haut ; un lieu couvert, au centre de son emprise.
  function pointDEtiquette(id) {
    if (dessin.etiquettes[id]) return dessin.etiquettes[id];
    const b = emprises.get(id);
    return [(b.min.x + b.max.x) / 2, (b.min.z + b.max.z) / 2];
  }

  function nommer() {
    for (const t of entier.querySelectorAll("text[data-lieu]")) t.textContent = nomDe(t.dataset.lieu);
  }

  // Un nom ne s'écrit que dans un lieu assez large et libre d'un nom déjà posé, à l'échelle affichée.
  function etiqueter() {
    const { echelle } = gestes.vue;
    const poses = [];
    for (const t of entier.querySelectorAll("text[data-lieu]")) {
      const b = emprises.get(t.dataset.lieu);
      const [cx, y] = pointDEtiquette(t.dataset.lieu);
      const l = (t.textContent.length * TAILLE_ETIQUETTE * 0.62) / echelle, h = (TAILLE_ETIQUETTE * 1.2) / echelle;
      const cadre = { x: cx - l / 2, y: y - h / 2, l, h };
      const tue = b.max.x - b.min.x < l || poses.some((p) => croise(cadre, p));
      t.classList.toggle("tue", tue);
      if (!tue) poses.push(cadre);
    }
  }

  // La plus longue barre ronde en amot qui tienne, dite aussi en mètres : le plan est à l'échelle du Temple.
  function graduer() {
    const { echelle } = gestes.vue;
    const visible = entier.clientWidth / echelle;
    const amot = LONGUEURS_ECHELLE.find((l) => l * ama <= PART_ECHELLE * visible) ?? LONGUEURS_ECHELLE.at(-1);
    const metres = new Intl.NumberFormat(langue(), { maximumFractionDigits: 1 }).format(amot * ama);
    barre.querySelector("i").style.width = `${(amot * ama * echelle).toFixed(1)}px`;
    barre.querySelector(".amot").textContent = `${amot} ${texte("amot")}`;
    barre.querySelector(".metres").textContent = `${metres} ${texte("metres")}`;
  }

  // Zoomé sur le Heikhal, le plan passe à sa coupe ; dézoomé ou sorti de lui, il revient en surface.
  function niveauVoulu() {
    const { x, z, echelle } = gestes.vue;
    for (const [coupe, foyer] of foyers) {
      if (coupe.souterraine) continue;
      const seuil = gestes.echellePour(largeurDe(coupe.coupe), hauteurDe(coupe.coupe)) * PART_BASCULE * (niveau === coupe ? HYSTERESE : 1);
      if (echelle >= seuil && contientAPlat(foyer, x, z)) return coupe;
    }
    return deSurface;
  }

  function suivreLaVue() {
    if (auto && !gestes.anime && !niveau.souterraine) {
      const voulu = niveauVoulu();
      if (voulu !== niveau) changerDeNiveau(voulu);
    }
    const { echelle } = gestes.vue;
    poserVisiteur(entier, LONGUEUR_VISITEUR / echelle, true);
    entier.querySelector(".visiteur")?.classList.toggle("ailleurs", souterrains.has(lieuDuVisiteur) !== !!niveau.souterraine);
    for (const t of entier.querySelectorAll("text[data-lieu]")) t.setAttribute("font-size", TAILLE_ETIQUETTE / echelle);
    placerEpingle();
    graduer();
    clearTimeout(etiquetage);
    etiquetage = setTimeout(etiqueter, ATTENTE_ETIQUETTES_MS);
  }

  function changerDeNiveau(voulu) {
    afficherNiveau(voulu);
    if (epingle && !epingle.destination) viser(epingle.vise.x, epingle.vise.z);
    else placerEpingle();
    etiqueter();
  }

  // Une coupe choisie dont rien n'est en vue : la carte va à ses lieux, au lieu de montrer du plan pâli.
  function montrerLeFoyer(n) {
    const foyer = foyers.get(n);
    if (!foyer) return;
    const { x, z, echelle } = gestes.vue;
    const demiL = entier.clientWidth / 2 / echelle, demiH = entier.clientHeight / 2 / echelle;
    const enVue = croise({ x: x - demiL, y: z - demiH, l: 2 * demiL, h: 2 * demiH },
      { x: foyer.min.x, y: foyer.min.z, l: foyer.max.x - foyer.min.x, h: foyer.max.z - foyer.min.z });
    if (enVue) return;
    const l = foyer.max.x - foyer.min.x, h = foyer.max.z - foyer.min.z;
    gestes.animerVers({ x: foyer.min.x + l / 2, z: foyer.min.z + h / 2, echelle: gestes.echellePour(l * 1.2, h * 1.2) });
  }

  // ---- épingle ----
  function viser(x, z) {
    const pieds = piedsAuPoint(x, z, niveau.sol);
    const [px, pz] = pieds ? [pieds[0], pieds[2]] : [x, z];
    const cap = pieds && capDuTrajet(pieds);
    epingle = { x: px, z: pz, vise: { x, z }, pieds, lieu: lieuNomme(px, pz), destination: null, angle: cap === null ? null : -cap };
    montrerEpingle();
  }

  function viserDestination(id) {
    const entree = entrees.find((e) => e.id === id);
    const pieds = entree ? entree.position : piedsDeLElement(id);
    if (!pieds) return;
    // La flèche regarde là où la vue soignée tournera le visiteur : le centre de ce qu'elle cadre, sinon son cap.
    const vise = centreDes(entree?.cadre ?? [id], emprises);
    const vers = vise && [vise.x - pieds[0], vise.z - pieds[2]];
    const angle = vers && Math.hypot(...vers) > 1 ? Math.atan2(vers[1], vers[0]) * 180 / Math.PI : (entree?.cap !== undefined ? -entree.cap : null);
    epingle = { x: pieds[0], z: pieds[2], pieds, lieu: id, destination: { id, entree: !!entree }, angle };
    montrerEpingle();
  }

  function nomDeLEpingle() {
    if (epingle.destination?.entree) return nomDeLEntree(entrees.find((e) => e.id === epingle.destination.id));
    return epingle.lieu ? nomDe(epingle.lieu) : texte("plan_ici");
  }

  function montrerEpingle() {
    nomBulle.textContent = nomDeLEpingle();
    inaccessible.hidden = !!epingle.pieds;
    allerIci.disabled = !epingle.pieds;
    vueDuLieu.hidden = !!epingle.destination || !epingle.lieu;
    bulle.hidden = false;
    placerEpingle();
  }

  function oublierEpingle() {
    epingle = null;
    bulle.hidden = true;
    placerEpingle();
  }

  function placerEpingle() {
    const marque = entier.querySelector(".epingle");
    if (!marque) return;
    marque.setAttribute("visibility", epingle ? "visible" : "hidden");
    if (!epingle) return;
    const taille = 1 / gestes.vue.echelle;
    marque.setAttribute("transform", `translate(${epingle.x.toFixed(2)} ${epingle.z.toFixed(2)}) scale(${taille.toFixed(4)})`);
    const apercu = marque.querySelector(".apercu");
    apercu.setAttribute("visibility", epingle.angle === null || !epingle.pieds ? "hidden" : "visible");
    if (epingle.angle !== null) apercu.setAttribute("transform", `rotate(${epingle.angle.toFixed(1)}) scale(${RAYON_PIED * 0.85})`);
    marque.classList.toggle("perdue", !epingle.pieds);
    placerBulle();
  }

  // Au-dessus de l'épingle, et dessous quand le haut de la carte manque ; elle suit la carte.
  function placerBulle() {
    const [sx, sy] = gestes.versEcran(epingle.x, epingle.z);
    const l = carte.clientWidth, h = carte.clientHeight;
    const dedans = sx >= 0 && sx <= l && sy >= 0 && sy <= h;
    bulle.style.visibility = dedans ? "" : "hidden";
    if (!dedans) return;
    const largeur = bulle.offsetWidth, hauteur = bulle.offsetHeight;
    const gauche = Math.min(Math.max(sx - largeur / 2, MARGE_BULLE), l - largeur - MARGE_BULLE);
    const dessus = sy - HAUTEUR_EPINGLE - hauteur - MARGE_BULLE;
    const haut = dessus >= MARGE_BULLE ? dessus : sy + MARGE_BULLE;
    bulle.style.transform = `translate(${gauche.toFixed(0)}px, ${haut.toFixed(0)}px)`;
  }

  function partirDeLEpingle() {
    if (!epingle?.pieds) return;
    const { destination, pieds } = epingle;
    fermer();
    if (!destination) allerAuPoint(pieds);
    else if (destination.entree) allerVers(destination.id);
    else allerElement(destination.id);
  }

  function voirLeLieu() {
    const { lieu } = epingle;
    fermer();
    if (entrees.some((e) => e.id === lieu)) allerVers(lieu);
    else allerElement(lieu);
  }

  // ---- aller à ----
  // Une entrée qui porte le nom d'un lieu le remplace : c'est sa vue soignée.
  function destinations() {
    const deEntrees = entrees.map((e) => ({ id: e.id, nom: nomDeLEntree(e), zone: zoneDe(e.id, e.position) }));
    const deLieux = lieux.filter((id) => !entrees.some((e) => e.id === id))
      .map((id) => ({ id, nom: nomDe(id), zone: concepts.get(id)?.zone }));
    return [...deEntrees, ...deLieux];
  }

  function zoneDe(id, [x, , z]) {
    if (concepts.get(id)?.zone) return concepts.get(id).zone;
    const lieu = deSurface.lieux.find((l) => contientAPlat(emprises.get(l), x, z));
    return lieu ? concepts.get(lieu)?.zone : undefined;
  }

  function choisirDestination(id) {
    const voulu = niveauDeLaDestination(id);
    if (voulu !== niveau) afficherNiveau(voulu);
    auto = !voulu.souterraine;
    viserDestination(id);
    const boite = emprises.get(id);
    const centre = boite ? { x: (boite.min.x + boite.max.x) / 2, z: (boite.min.z + boite.max.z) / 2 } : { x: epingle.x, z: epingle.z };
    const echelle = boite ? gestes.echellePour((boite.max.x - boite.min.x) * 1.4, (boite.max.z - boite.min.z) * 1.4) : gestes.vue.echelle;
    gestes.animerVers({ ...centre, echelle });
  }

  const aller = allerA(fenetre.querySelector(".aller"), { destinations, choisir: choisirDestination });

  // ---- ouverture ----
  const ouvert = () => !fenetre.hidden;

  function ouvrir() {
    fenetre.hidden = false;
    const visiteur = niveauDuLieu(lieuDuVisiteur);
    auto = !visiteur.souterraine;
    afficherNiveau(visiteur);
    oublierEpingle();
    const centre = pose ?? { x: (dessin.min[0] + dessin.max[0]) / 2, z: (dessin.min[1] + dessin.max[1]) / 2 };
    gestes.regler({ x: centre.x, z: centre.z, echelle: gestes.echellePour(VUE_OUVERTURE, VUE_OUVERTURE) });
    etiqueter();
    entier.focus({ preventScroll: true });
  }

  function fermer() {
    fenetre.hidden = true;
    gestes.oublierAppui();
    aller.refermer();
    oublierEpingle();
    document.activeElement?.blur();
  }

  function recentrer() {
    if (!pose) return;
    const visiteur = niveauDuLieu(lieuDuVisiteur);
    auto = !visiteur.souterraine;
    if (visiteur !== niveau) afficherNiveau(visiteur);
    gestes.animerVers({ x: pose.x, z: pose.z, echelle: Math.max(gestes.vue.echelle, gestes.echellePour(VUE_OUVERTURE, VUE_OUVERTURE)) });
  }

  function rafraichir() {
    for (const b of choixNiveau.children) {
      if (b.dataset.niveau === deSurface.id) ecrire(b, "niveau_surface");
      else b.textContent = nomDeZone(b.dataset.niveau);
    }
    nommer();
    aller.rafraichir();
    if (!ouvert()) return;
    etiqueter();
    graduer();
    if (epingle) montrerEpingle();
  }

  // La minicarte montre les abords du visiteur, sous terre les tunnels s'il y est.
  function suivre(position, direction, lieu) {
    pose = { x: position.x, z: position.z, angle: Math.atan2(direction.z, direction.x) * 180 / Math.PI };
    lieuDuVisiteur = lieu;
    const voulu = souterrains.has(lieu) ? niveauDuLieu(lieu) : deSurface;
    if (mini.dataset.niveau !== voulu.id) dessinerMini(voulu);
    mini.setAttribute("viewBox", `${pose.x - FENETRE_MINI / 2} ${pose.z - FENETRE_MINI / 2} ${FENETRE_MINI} ${FENETRE_MINI}`);
    poserVisiteur(mini, FENETRE_MINI / 9, true);
  }

  choixNiveau.replaceChildren(...niveaux.map((n) => {
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.niveau = n.id;
    b.onclick = (e) => {
      e.currentTarget.blur();
      auto = false;
      changerDeNiveau(n);
      suivreLaVue();
      montrerLeFoyer(n);
    };
    return b;
  }));
  dessinerMini(deSurface);
  rafraichir();

  bouton.onclick = (e) => { e.currentTarget.blur(); ouvrir(); };
  fenetre.querySelector(".tete .fermer").onclick = fermer;
  carte.querySelector(".zoomer").onclick = () => gestes.zoomer(2);
  carte.querySelector(".dezoomer").onclick = () => gestes.zoomer(0.5);
  carte.querySelector(".recentrer").onclick = recentrer;
  allerIci.onclick = partirDeLEpingle;
  vueDuLieu.onclick = voirLeLieu;
  bulle.querySelector(".fermer").onclick = oublierEpingle;
  entier.addEventListener("keydown", (e) => { if (e.key === "Enter") partirDeLEpingle(); });
  addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || !ouvert()) return;
    if (aller.ouverte()) aller.refermer();
    else if (epingle) oublierEpingle();
    else fermer();
  });
  addEventListener("resize", () => { if (ouvert()) gestes.regler(gestes.vue); });

  return { suivre, rafraichir, ouvert, ouvrir, viser, choisir: choisirDestination, get epingle() { return epingle; }, get niveau() { return niveau.id; } };
}
