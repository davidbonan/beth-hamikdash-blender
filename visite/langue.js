import { lireRetenu, retenir } from "./memoire.js";

const CLEF = "visite.langue";
export const LANGUE_SOURCE = "fr";

let textes = null;
let courante = LANGUE_SOURCE;
const suiveurs = [];
let signalerChoix;
// Tant que l'accueil demande la langue, rien d'autre ne doit s'adresser au visiteur.
export const langueChoisie = new Promise((resoudre) => { signalerChoix = resoudre; });

export const langue = () => courante;
// Avant `installerLangue`, une erreur de chargement doit encore pouvoir s'afficher.
export const texte = (clef) => textes?.[courante].interface[clef] ?? clef;
export const libelle = (famille, clef) => textes[courante][famille]?.[clef];
export const suivreLangue = (suiveur) => suiveurs.push(suiveur);

export function ecrire(element, clef) {
  element.dataset.texte = clef;
  element.textContent = texte(clef);
}

function traduirePage() {
  const racine = document.documentElement;
  racine.lang = courante;
  racine.dir = textes[courante].sens;
  document.title = texte("titre");
  for (const el of document.querySelectorAll("[data-texte]")) el.textContent = texte(el.dataset.texte);
  for (const el of document.querySelectorAll("[data-texte-html]")) el.innerHTML = texte(el.dataset.texteHtml);
  for (const el of document.querySelectorAll("[data-titre]")) {
    el.title = texte(el.dataset.titre);
    if (el.hasAttribute("aria-label")) el.setAttribute("aria-label", el.title);
  }
  document.querySelector("#langue-courante use").setAttribute("href", `#drapeau-${courante}`);
}

function choisirLangue(code) {
  retenir(CLEF, code);
  if (code === courante) return;
  courante = code;
  traduirePage();
  for (const suiveur of suiveurs) suiveur(code);
}

function boutonsDeLangue() {
  return Object.entries(textes).map(([code, { nom }]) => {
    const bouton = document.createElement("button");
    bouton.type = "button";
    bouton.lang = code;
    bouton.dataset.langue = code;
    bouton.innerHTML =
      `<svg class="drapeau" aria-hidden="true"><use href="#drapeau-${code}"></use></svg><span>${nom}</span>`;
    return bouton;
  });
}

function brancherSelecteur() {
  const bouton = document.querySelector("#langue-courante");
  const menu = document.querySelector("#langue-menu");
  const ouvrirMenu = () => { menu.hidden = false; bouton.setAttribute("aria-expanded", "true"); };
  const fermerMenu = () => { menu.hidden = true; bouton.setAttribute("aria-expanded", "false"); };

  menu.append(...boutonsDeLangue());
  bouton.onclick = () => (menu.hidden ? ouvrirMenu() : fermerMenu());
  menu.onclick = (e) => {
    const choix = e.target.closest("[data-langue]");
    if (!choix) return;
    fermerMenu();
    document.activeElement?.blur();             // la barre garde sinon le clavier de la marche
    choisirLangue(choix.dataset.langue);
  };
  addEventListener("pointerdown", (e) => { if (!e.target.closest?.("#langue")) fermerMenu(); });
  addEventListener("keydown", (e) => { if (e.key === "Escape") fermerMenu(); });
}

function accueillir() {
  const accueil = document.querySelector("#accueil");
  const choix = accueil.querySelector(".choix");
  choix.append(...boutonsDeLangue());
  accueil.hidden = false;
  choix.onclick = (e) => {
    const bouton = e.target.closest("[data-langue]");
    if (!bouton) return;
    bouton.blur();
    choisirLangue(bouton.dataset.langue);
    accueil.classList.add("parti");
    signalerChoix();
  };
}

export function installerLangue(tous) {
  textes = tous;
  const retenue = lireRetenu(CLEF);
  const connue = retenue !== null && Object.hasOwn(textes, retenue);
  if (connue) courante = retenue;
  traduirePage();
  brancherSelecteur();
  if (connue) signalerChoix(); else accueillir();
}
