import { nomDeZone } from "./fiche.js";
import { libelle } from "./langue.js";

const SVG = "http://www.w3.org/2000/svg";
const FENETRE_MINI = 110;      // mètres de terrain montrés autour du visiteur
const COUR = 1500;             // m² : au-delà, un lieu se dessine en cour
const MARGE = 6;               // mètres autour d'un cadrage
const TAILLE_ETIQUETTE = 13;   // px
const RAYON_ENTREE = 6;        // px
const HAUTEUR_ETAGE = 10;      // mètres : un lieu qui commence plus haut est à l'étage
const CADRAGES = {
  har_habayit: ["sol_har_habayit"],
  azara: ["azara", "porte_est_ezrat_nashim"],
};

const noeud = (nom, attributs = {}) => {
  const n = document.createElementNS(SVG, nom);
  for (const [clef, valeur] of Object.entries(attributs)) n.setAttribute(clef, valeur);
  return n;
};

const surface = (b) => (b.max.x - b.min.x) * (b.max.z - b.min.z);

export function plan({ emprises, lieux, entrees, concepts, allerLieu, allerEntree }) {
  const bouton = document.querySelector("#minicarte");
  const fenetre = document.querySelector("#plan");
  const mini = bouton.querySelector("svg");
  const entier = fenetre.querySelector("svg");
  const choixCadrage = fenetre.querySelectorAll("[data-cadrage]");
  let cadrage = "har_habayit";

  const parSurface = lieux.filter((id) => emprises.has(id))
    .sort((a, b) => surface(emprises.get(b)) - surface(emprises.get(a)));
  const nomDe = (id) => concepts.get(id)?.nom ?? id;
  const nomHebreu = (id) => concepts.get(id)?.he || nomDe(id);

  function dessiner(svg) {
    const groupeLieux = noeud("g", { class: "lieux" });
    const etiquettes = noeud("g", { class: "etiquettes" });
    for (const id of parSurface) {
      const b = emprises.get(id);
      const rect = noeud("rect", {
        x: b.min.x, y: b.min.z, width: b.max.x - b.min.x, height: b.max.z - b.min.z,
        class: surface(b) > COUR ? "cour" : "batiment", "data-lieu": id });
      rect.append(noeud("title"));
      groupeLieux.append(rect);
      etiquettes.append(noeud("text", {
        x: (b.min.x + b.max.x) / 2, y: (b.min.z + b.max.z) / 2, "data-lieu": id, lang: "he" }));
    }
    const groupeEntrees = noeud("g", { class: "entrees" });
    for (const e of entrees) {
      const [x, , z] = e.position;
      const point = noeud("circle", { cx: x, cy: z, r: 3, "data-entree": e.id });
      point.append(noeud("title"));
      groupeEntrees.append(point);
    }
    const visiteur = noeud("g", { class: "visiteur" });
    visiteur.append(noeud("path", { d: "M 7 0 L -4 4.5 L -2 0 L -4 -4.5 Z" }));
    svg.replaceChildren(groupeLieux, groupeEntrees, etiquettes, visiteur);
  }

  function nommer(svg) {
    for (const rect of svg.querySelectorAll("rect[data-lieu]")) rect.firstChild.textContent = nomDe(rect.dataset.lieu);
    for (const point of svg.querySelectorAll("[data-entree]")) {
      const e = entrees.find((x) => x.id === point.dataset.entree);
      point.firstChild.textContent = libelle("entrees", e.id) ?? e.nom;
    }
    for (const t of svg.querySelectorAll("text[data-lieu]")) t.textContent = nomHebreu(t.dataset.lieu);
  }

  // Un nom ne s'écrit que dans un lieu assez large et libre d'un nom plus grand, à l'échelle du cadrage affiché.
  function etiqueter() {
    const [, , largeur, hauteur] = entier.getAttribute("viewBox").split(" ").map(Number);
    const echelle = Math.min(entier.clientWidth / largeur, entier.clientHeight / hauteur);
    if (!echelle) return;
    for (const point of entier.querySelectorAll("[data-entree]")) point.setAttribute("r", RAYON_ENTREE / echelle);
    const poses = [...entier.querySelectorAll("[data-entree]")].map((point) => point.getBBox());
    const chevauche = (r) => poses.some((p) =>
      r.x < p.x + p.width && p.x < r.x + r.width && r.y < p.y + p.height && p.y < r.y + r.height);
    for (const t of entier.querySelectorAll("text[data-lieu]")) {
      const b = emprises.get(t.dataset.lieu);
      t.setAttribute("font-size", TAILLE_ETIQUETTE / echelle);
      // Une cour contient d'autres lieux en son centre : son nom se pose sur son bord sud.
      if (surface(b) > COUR) t.setAttribute("y", b.max.z - (TAILLE_ETIQUETTE * 1.1) / echelle);
      const place = (b.max.x - b.min.x) * echelle;
      // Un plan est au sol : l'Aliyah prendrait sinon le nom du Heikhal qu'elle surplombe.
      const aLEtage = b.min.y > HAUTEUR_ETAGE;
      t.classList.toggle("tue", aLEtage || place < t.textContent.length * TAILLE_ETIQUETTE * 0.62);
      if (t.classList.contains("tue")) continue;
      const cadre = t.getBBox();
      if (chevauche(cadre)) t.classList.add("tue");
      else poses.push(cadre);
    }
  }

  function cadrer(nom) {
    cadrage = nom;
    const ids = CADRAGES[nom].filter((id) => emprises.has(id));
    const min = { x: Infinity, z: Infinity }, max = { x: -Infinity, z: -Infinity };
    for (const id of ids) {
      const b = emprises.get(id);
      min.x = Math.min(min.x, b.min.x); min.z = Math.min(min.z, b.min.z);
      max.x = Math.max(max.x, b.max.x); max.z = Math.max(max.z, b.max.z);
    }
    entier.setAttribute("viewBox",
      `${min.x - MARGE} ${min.z - MARGE} ${max.x - min.x + 2 * MARGE} ${max.z - min.z + 2 * MARGE}`);
    for (const b of choixCadrage) b.setAttribute("aria-pressed", String(b.dataset.cadrage === nom));
    etiqueter();
  }

  const ouvert = () => !fenetre.hidden;

  function ouvrir() {
    fenetre.hidden = false;
    cadrer(cadrage);
  }

  function fermer() {
    fenetre.hidden = true;
    document.activeElement?.blur();
  }

  function rafraichir() {
    for (const svg of [mini, entier]) nommer(svg);
    for (const b of choixCadrage) b.textContent = nomDeZone(b.dataset.cadrage);
    if (ouvert()) etiqueter();
  }

  function suivre(position, direction) {
    const angle = Math.atan2(direction.z, direction.x) * 180 / Math.PI;
    const pose = `translate(${position.x.toFixed(2)} ${position.z.toFixed(2)}) rotate(${angle.toFixed(1)})`;
    for (const svg of [mini, entier]) svg.querySelector(".visiteur").setAttribute("transform", pose);
    mini.setAttribute("viewBox",
      `${position.x - FENETRE_MINI / 2} ${position.z - FENETRE_MINI / 2} ${FENETRE_MINI} ${FENETRE_MINI}`);
  }

  dessiner(mini);
  dessiner(entier);
  cadrer(cadrage);
  rafraichir();

  bouton.onclick = (e) => { e.currentTarget.blur(); ouvrir(); };
  fenetre.querySelector(".fermer").onclick = fermer;
  for (const b of choixCadrage) b.onclick = () => cadrer(b.dataset.cadrage);
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
