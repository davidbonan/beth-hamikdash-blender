import { nomDeZone } from "./fiche.js";
import { libelle } from "./langue.js";

const SVG = "http://www.w3.org/2000/svg";
const TAILLE_ETIQUETTE = 13;   // px
const RAYON_ENTREE = 6;        // px
const LONGUEUR_VISITEUR = 18;  // px, la flèche du plan entier
const HAUTEUR_ETAGE = 10;      // mètres : un lieu qui commence plus haut est à l'étage
const PART_MINI = 0.5;         // du plus petit côté de la zone, ce que la minicarte montre autour du visiteur
const FENETRE_MINI_MIN = 28;   // mètres
const FLECHE = "M 1 0 L -0.6 0.65 L -0.3 0 L -0.6 -0.65 Z";

const noeud = (nom, attributs = {}) => {
  const n = document.createElementNS(SVG, nom);
  for (const [clef, valeur] of Object.entries(attributs)) n.setAttribute(clef, valeur);
  return n;
};

const surface = (b) => (b.max.x - b.min.x) * (b.max.z - b.min.z);
const largeurDe = (cadrage) => cadrage.max[0] - cadrage.min[0];
const hauteurDe = (cadrage) => cadrage.max[1] - cadrage.min[1];
const englobe = (b, autre) => surface(autre) < surface(b)
  && b.min.x <= (autre.min.x + autre.max.x) / 2 && (autre.min.x + autre.max.x) / 2 <= b.max.x
  && b.min.z <= (autre.min.z + autre.max.z) / 2 && (autre.min.z + autre.max.z) / 2 <= b.max.z;
const contient = (cadrage, x, z) =>
  x >= cadrage.min[0] && x <= cadrage.max[0] && z >= cadrage.min[1] && z <= cadrage.max[1];

export function plan({ cadrages, emprises, lieux, entrees, concepts, allerLieu, allerEntree }) {
  const bouton = document.querySelector("#minicarte");
  const fenetre = document.querySelector("#plan");
  const mini = bouton.querySelector("svg");
  const entier = fenetre.querySelector("svg");
  const choix = fenetre.querySelector(".cadrages");
  let ici = cadrages[0];
  let pose = null;

  const souterrains = new Set(cadrages.filter((c) => c.coupe < 0).flatMap((c) => c.lieux));
  // Du plus petit au plus grand : le premier cadrage de plein air qui contient le visiteur est le plus détaillé.
  const pleinAir = cadrages.filter((c) => !c.lieux)
    .sort((a, b) => largeurDe(a) * hauteurDe(a) - largeurDe(b) * hauteurDe(b));
  const nomDe = (id) => concepts.get(id)?.nom ?? id;
  const nomHebreu = (id) => concepts.get(id)?.he || nomDe(id);

  // Une coupe dit ce qu'elle tranche ; en plein air, ce qui se voit d'en haut et tient tout entier dans le cadre.
  function lieuxDe(cadrage) {
    const ids = cadrage.lieux ?? lieux.filter((id) => {
      const b = emprises.get(id);
      return !souterrains.has(id) && b.min.y <= HAUTEUR_ETAGE
        && contient(cadrage, b.min.x, b.min.z) && contient(cadrage, b.max.x, b.max.z);
    });
    return ids.filter((id) => emprises.has(id))
      .sort((a, b) => surface(emprises.get(b)) - surface(emprises.get(a)));
  }

  const entreesDe = (cadrage) => entrees.filter((e) => (cadrage.lieux
    ? cadrage.lieux.includes(e.id)
    : !souterrains.has(e.id) && contient(cadrage, e.position[0], e.position[2])));

  const cadrageDe = (position, lieu) => cadrages.find((c) => c.lieux?.includes(lieu))
    ?? pleinAir.find((c) => contient(c, position.x, position.z)) ?? pleinAir.at(-1);

  const image = (cadrage, classe) => noeud("image", {
    href: cadrage.image, x: cadrage.min[0], y: cadrage.min[1], class: classe,
    width: largeurDe(cadrage), height: hauteurDe(cadrage), preserveAspectRatio: "none" });

  // Une coupe souterraine ne montre que ses tunnels : le plan de surface, pâli, les situe.
  function dessinerFond(svg, cadrage) {
    const visiteur = noeud("g", { class: "visiteur" });
    visiteur.append(noeud("path", { d: FLECHE }));
    const dessous = cadrages.find((c) => c.id === cadrage.dessous);
    svg.replaceChildren(...(dessous ? [image(dessous, "dessous")] : []), image(cadrage, "fond"), visiteur);
    svg.dataset.cadrage = cadrage.id;
  }

  function dessinerPlan(cadrage) {
    dessinerFond(entier, cadrage);
    const groupeLieux = noeud("g", { class: "lieux" });
    const etiquettes = noeud("g", { class: "etiquettes" });
    for (const id of lieuxDe(cadrage)) {
      const b = emprises.get(id);
      const rect = noeud("rect", {
        x: b.min.x, y: b.min.z, width: b.max.x - b.min.x, height: b.max.z - b.min.z, "data-lieu": id });
      rect.append(noeud("title"));
      groupeLieux.append(rect);
      etiquettes.append(noeud("text", {
        x: (b.min.x + b.max.x) / 2, y: (b.min.z + b.max.z) / 2, "data-lieu": id, lang: "he" }));
    }
    const groupeEntrees = noeud("g", { class: "entrees" });
    for (const e of entreesDe(cadrage)) {
      const point = noeud("circle", { cx: e.position[0], cy: e.position[2], "data-entree": e.id });
      point.append(noeud("title"));
      groupeEntrees.append(point);
    }
    entier.querySelector(".visiteur").before(groupeLieux, groupeEntrees, etiquettes);
    entier.setAttribute("viewBox", `${cadrage.min[0]} ${cadrage.min[1]} ${largeurDe(cadrage)} ${hauteurDe(cadrage)}`);
    nommer();
  }

  function nommer() {
    for (const rect of entier.querySelectorAll("rect[data-lieu]")) rect.firstChild.textContent = nomDe(rect.dataset.lieu);
    for (const point of entier.querySelectorAll("[data-entree]")) {
      const e = entrees.find((x) => x.id === point.dataset.entree);
      point.firstChild.textContent = libelle("entrees", e.id) ?? e.nom;
    }
    for (const t of entier.querySelectorAll("text[data-lieu]")) t.textContent = nomHebreu(t.dataset.lieu);
  }

  function echelleDuPlan() {
    const [, , largeur, hauteur] = (entier.getAttribute("viewBox") ?? "0 0 0 0").split(" ").map(Number);
    return Math.min(entier.clientWidth / largeur, entier.clientHeight / hauteur) || 0;
  }

  // Hors du cadre, la flèche flotterait sur le fond de la fenêtre ; une coupe ne la montre qu'à qui s'y trouve.
  function poser(svg, taille) {
    const visiteur = svg.querySelector(".visiteur");
    if (!pose || !visiteur) return;
    const cadrage = cadrages.find((c) => c.id === svg.dataset.cadrage);
    const present = cadrage.lieux ? cadrage === ici : contient(cadrage, pose.x, pose.z);
    visiteur.setAttribute("visibility", present ? "visible" : "hidden");
    visiteur.setAttribute("transform",
      `translate(${pose.x.toFixed(2)} ${pose.z.toFixed(2)}) rotate(${pose.angle.toFixed(1)}) scale(${taille.toFixed(3)})`);
  }

  // Un nom ne s'écrit que dans un lieu assez large et libre d'un nom plus grand, à l'échelle du cadrage affiché.
  function etiqueter() {
    const echelle = echelleDuPlan();
    if (!echelle) return;
    poser(entier, LONGUEUR_VISITEUR / echelle);
    for (const point of entier.querySelectorAll("[data-entree]")) point.setAttribute("r", RAYON_ENTREE / echelle);
    const poses = [...entier.querySelectorAll("[data-entree]")].map((point) => point.getBBox());
    const chevauche = (r) => poses.some((p) =>
      r.x < p.x + p.width && p.x < r.x + r.width && r.y < p.y + p.height && p.y < r.y + r.height);
    const textes = [...entier.querySelectorAll("text[data-lieu]")];
    const bornes = textes.map((t) => emprises.get(t.dataset.lieu));
    for (const t of textes) {
      const b = emprises.get(t.dataset.lieu);
      t.setAttribute("font-size", TAILLE_ETIQUETTE / echelle);
      // Une cour ou l'anneau des ta'im entoure d'autres lieux : son nom se pose sur son bord sud, pas sur eux.
      if (bornes.some((autre) => autre !== b && englobe(b, autre))) t.setAttribute("y", b.max.z - (TAILLE_ETIQUETTE * 1.1) / echelle);
      const place = (b.max.x - b.min.x) * echelle;
      t.classList.toggle("tue", place < t.textContent.length * TAILLE_ETIQUETTE * 0.62);
      if (t.classList.contains("tue")) continue;
      const cadre = t.getBBox();
      if (chevauche(cadre)) t.classList.add("tue");
      else poses.push(cadre);
    }
  }

  function cadrer(cadrage) {
    dessinerPlan(cadrage);
    for (const b of choix.children) b.setAttribute("aria-pressed", String(b.dataset.cadrage === cadrage.id));
    etiqueter();
  }

  const ouvert = () => !fenetre.hidden;

  function ouvrir() {
    fenetre.hidden = false;
    cadrer(ici);
  }

  function fermer() {
    fenetre.hidden = true;
    document.activeElement?.blur();
  }

  function rafraichir() {
    for (const b of choix.children) b.textContent = nomDeZone(b.dataset.cadrage);
    nommer();
    if (ouvert()) etiqueter();
  }

  // La minicarte prend l'image de la zone où l'on se tient, et n'en montre que les abords.
  function suivre(position, direction, lieu) {
    pose = { x: position.x, z: position.z, angle: Math.atan2(direction.z, direction.x) * 180 / Math.PI };
    const zone = cadrageDe(position, lieu);
    if (mini.dataset.cadrage !== zone.id) dessinerFond(mini, zone);
    ici = zone;
    const cote = Math.max(FENETRE_MINI_MIN, PART_MINI * Math.min(largeurDe(zone), hauteurDe(zone)));
    mini.setAttribute("viewBox", `${pose.x - cote / 2} ${pose.z - cote / 2} ${cote} ${cote}`);
    poser(mini, cote / 15);
    const echelle = ouvert() && echelleDuPlan();
    if (echelle) poser(entier, LONGUEUR_VISITEUR / echelle);
  }

  choix.replaceChildren(...cadrages.map((cadrage) => {
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.cadrage = cadrage.id;
    b.onclick = () => cadrer(cadrage);
    return b;
  }));
  dessinerFond(mini, ici);
  rafraichir();

  bouton.onclick = (e) => { e.currentTarget.blur(); ouvrir(); };
  fenetre.querySelector(".fermer").onclick = fermer;
  entier.addEventListener("click", (e) => {
    const entree = e.target.closest("[data-entree]");
    const lieu = e.target.closest("[data-lieu]");
    if (!entree && !lieu) return;
    fermer();
    if (entree) allerEntree(entree.dataset.entree);
    else allerLieu(lieu.dataset.lieu);
  });
  addEventListener("keydown", (e) => { if (e.key === "Escape" && ouvert()) fermer(); });
  addEventListener("resize", () => { if (ouvert()) etiqueter(); });

  return { suivre, rafraichir };
}
