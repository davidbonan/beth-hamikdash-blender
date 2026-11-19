// La jauge de la barre : son aiguille dit le profil pris, et elle déroule la ma'arakha qui en change.
import { suivreLangue, texte } from "./langue.js";
import { AUTOMATIQUE, NIVEAU, NIVEAUX, chargeDe, choisir, niveauTenu } from "./qualite.js";

// Du plus pauvre au plus riche : la braise d'abord, le grand feu en dernier.
const CRANS = [...NIVEAUX].reverse();
const applique = { automatique: AUTOMATIQUE, niveau: NIVEAU };

const bouton = document.querySelector("#qualite-courante");
const fenetre = document.querySelector("#qualite-choix");

const long = (x, y, l) => `<rect class="trait bois" x="${x}" y="${y}" width="${l}" height="5" rx="2.5"/><path class="trait fil" d="M${x + 3} ${y + 2.6}H${x + l * 0.55}M${x + l * 0.64} ${y + 2.1}H${x + l - 3}"/>`;
const bout = (x, y) => `<circle class="trait bois" cx="${x}" cy="${y}" r="2.5"/><circle class="trait fil" cx="${x}" cy="${y}" r="1"/>`;
const langue = (x, base, l, h, penche, delai) => `<g class="vif langue" style="animation-delay:-${delai}s"><path d="M${x - l / 2} ${base}C${x - l / 2} ${base - h * 0.5} ${x + l * 0.3} ${base - h * 0.55} ${x + penche} ${base - h}C${x + l * 0.15} ${base - h * 0.62} ${x + l / 2} ${base - h * 0.4} ${x + l / 2} ${base}"/><path class="veine" d="M${x} ${base}C${x - l * 0.15} ${base - h * 0.35} ${x + l * 0.1} ${base - h * 0.5} ${x + penche * 0.6} ${base - h * 0.72}"/></g>`;
const lueur = (x, y, r) => `<circle class="vif lueur" cx="${x}" cy="${y}" r="${r}" fill="url(#qualite-lueur)"/>`;
const volute = (x, delai) => `<path class="vif volute" style="animation-delay:-${delai}s" d="M${x} 55C${x - 2.5} 52 ${x + 2.5} 49.5 ${x} 46.5C${x - 2} 44 ${x + 1.8} 42 ${x + 0.6} 39.5"/>`;
const etincelle = (x, y, delai) => `<circle class="vif etincelle" cx="${x}" cy="${y}" r=".6" style="animation-delay:-${delai}s"/>`;
const SOL = `<path class="trait sol" d="M6 57.5H54"/>`;
const PETITE = `${long(20, 52, 20)}${bout(25, 49)}${bout(35, 49)}`;
const GRANDE = `${long(12, 52, 36)}${[18, 26, 34, 42].map((x) => bout(x, 49)).join("")}${long(15, 41.5, 30)}${[22, 30, 38].map((x) => bout(x, 38.5)).join("")}`;

// La braise qui fume, la petite ma'arakha, la grande qui rougeoie, la grande en plein feu.
const MAARAKHA = {
  sobre: `${lueur(30, 56, 7)}${volute(30, 0)}${volute(28.8, 1.1)}${volute(31.4, 2.2)}${SOL}<path class="trait" d="M24.5 56.6l3-1.3M29 56.9l3.6-1.7M33.6 56.5l2-.9"/>`,
  minimale: `${lueur(30, 48, 12)}${langue(30, 47, 5, 11, 1, 0)}${langue(26.5, 47.5, 3, 6, -1, 0.5)}${SOL}${PETITE}`,
  basse: `${lueur(30, 46, 18)}${langue(30, 36.5, 5, 9, 0.8, 0)}${langue(24.5, 37, 3.5, 6, -1, 0.6)}${SOL}${GRANDE}`,
  haute: `${lueur(30, 38, 26)}${langue(30, 37, 9, 28, 1.2, 0)}${langue(23, 37.5, 6, 19, -2, 0.4)}${langue(37, 37.5, 6, 21, 2, 0.8)}${langue(18.5, 40, 3.5, 10, -1.5, 0.2)}${langue(41.5, 40, 3.5, 11, 1.5, 0.6)}${SOL}${GRANDE}${etincelle(26, 10, 0)}${etincelle(34, 7, 0.7)}${etincelle(30, 13, 1.2)}`,
};

const nomDuNiveau = (niveau) => texte(`qualite_${niveau}`);
const nomApplique = () => (applique.automatique ? `${texte("qualite_auto_court")} · ${nomDuNiveau(applique.niveau)}` : nomDuNiveau(applique.niveau));
const angleDe = (niveau) => ((CRANS.indexOf(niveau) + 0.5) / CRANS.length - 0.5) * 180;
const changeLeProfil = (choix) => choix.automatique !== applique.automatique || (!choix.automatique && choix.niveau !== applique.niveau);

// Le rythme est resté lent au dernier palier de définition : la jauge le dit, quel que soit le profil.
export function signalerSaccade() {
  bouton.dataset.saccade = "";
}

// Le profil est figé au chargement, lu par toute la visite : en changer, c'est la recharger.
export function brancherJauge({ recharger }) {
  const interrupteur = fenetre.querySelector(".interrupteur");
  const rangee = fenetre.querySelector(".maarakha");
  const curseur = rangee.querySelector("input");
  const crans = CRANS.map((niveau) => {
    const cran = document.createElement("i");
    cran.innerHTML = `<svg viewBox="0 0 60 60" preserveAspectRatio="xMidYMax meet" aria-hidden="true">${MAARAKHA[niveau]}</svg>`;
    return cran;
  });
  rangee.prepend(...crans);
  const reperes = CRANS.map(() => document.createElement("span"));
  fenetre.querySelector(".reperes").append(...reperes);
  const message = fenetre.querySelector(".message");
  const application = fenetre.querySelector(".application");
  let choix = { ...applique };

  function montrerApplique() {
    bouton.querySelector(".aiguille").style.transform = `rotate(${angleDe(applique.niveau)}deg)`;
    bouton.querySelector(".nom").textContent = nomApplique();
  }

  function montrerChoix() {
    const rang = CRANS.indexOf(choix.niveau);
    interrupteur.setAttribute("aria-checked", String(choix.automatique));
    curseur.value = String(rang);
    curseur.setAttribute("aria-valuetext", nomDuNiveau(choix.niveau));
    crans.forEach((cran, i) => cran.classList.toggle("allume", i <= rang));
    reperes.forEach((repere, i) => repere.classList.toggle("actif", i === rang));
    const charge = choix.automatique ? "fluide" : chargeDe(choix.niveau);
    message.dataset.charge = charge;
    message.textContent = texte(choix.automatique ? "qualite_auto_choisie" : `qualite_${charge}`);
    application.hidden = !changeLeProfil(choix);
  }

  function nommerLesCrans() {
    reperes.forEach((repere, i) => {
      const charge = chargeDe(CRANS[i]);
      repere.textContent = nomDuNiveau(CRANS[i]);
      if (charge === "fluide") delete repere.dataset.charge;
      else repere.dataset.charge = charge;
    });
  }

  function choisirLeCran(rang) {
    choix = { automatique: false, niveau: CRANS[rang] };
    montrerChoix();
  }

  // Sous la jauge au large ; toute la largeur sur un téléphone debout, que la feuille de style décide.
  function placer() {
    const cadre = bouton.getBoundingClientRect();
    fenetre.style.setProperty("--qualite-haut", `${cadre.bottom + 6}px`);
    fenetre.style.setProperty("--qualite-ancre", `${document.dir === "rtl" ? innerWidth - cadre.right : cadre.left}px`);
  }

  function ouvrir() {
    choix = { ...applique };
    montrerChoix();
    placer();
    fenetre.hidden = false;
    bouton.setAttribute("aria-expanded", "true");
  }

  function fermer() {
    fenetre.hidden = true;
    bouton.setAttribute("aria-expanded", "false");
  }

  // Le doigt vise une ma'arakha et glisse de l'une à l'autre ; le curseur natif, invisible, garde le clavier.
  function viser(e) {
    const cadre = rangee.getBoundingClientRect();
    const part = (e.clientX - cadre.left) / cadre.width;
    const rang = Math.min(CRANS.length - 1, Math.max(0, Math.floor((document.dir === "rtl" ? 1 - part : part) * CRANS.length)));
    choisirLeCran(rang);
  }

  nommerLesCrans();
  montrerApplique();
  suivreLangue(() => { nommerLesCrans(); montrerApplique(); if (!fenetre.hidden) montrerChoix(); });

  bouton.onclick = (e) => { e.currentTarget.blur(); if (fenetre.hidden) ouvrir(); else fermer(); };
  interrupteur.onclick = () => {
    choix = choix.automatique ? { ...choix, automatique: false } : { automatique: true, niveau: niveauTenu() };
    montrerChoix();
  };
  curseur.oninput = () => choisirLeCran(Number(curseur.value));
  rangee.onpointerdown = (e) => {
    e.preventDefault();
    rangee.setPointerCapture(e.pointerId);
    viser(e);
  };
  rangee.onpointermove = (e) => { if (rangee.hasPointerCapture(e.pointerId)) viser(e); };
  fenetre.querySelector(".appliquer").onclick = () => {
    fermer();
    choisir(choix.automatique ? "" : choix.niveau);
    recharger();
  };
  addEventListener("pointerdown", (e) => { if (!e.target.closest?.("#qualite-choix, #qualite-courante")) fermer(); });
  addEventListener("keydown", (e) => { if (e.key === "Escape") fermer(); });
  addEventListener("resize", fermer);
}
