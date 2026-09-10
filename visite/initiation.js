/**
 * L'initiation : les gestes de la visite, appris en les faisant.
 *
 * Un rappel des commandes suppose qu'on sait déjà ce qu'est un manche ou un glissé.
 * Ici chaque étape montre le geste à l'endroit de l'écran où il se fait, et n'avance
 * que lorsque le visiteur l'a fait lui-même. Rien ici ne connaît la scène : visite.js
 * rapporte ce qui s'est passé, et désigne l'élément à montrer.
 */
import { ecrire } from "./langue.js";
import { lireRetenu, retenir } from "./memoire.js";

const CLEF = "visite.initiation";
const DENIVELE = 3;            // mètres à monter, puis à redescendre
// `bouton` : ce que l'étape fait toucher dans l'interface plutôt que dans la scène.
// La fiche vient en dernier : ouverte plus tôt, son tiroir recouvrait les flèches du vol.
const ETAPES = [
  { nom: "regarder", seuil: 1.2 },                                // radians de tête tournée
  { nom: "avancer", seuil: 10 },                                  // mètres parcourus
  { nom: "voler", seuil: 1, bouton: "#vol" },                     // passage en vol libre
  { nom: "monter", seuil: 2 * DENIVELE, bouton: "#vertical" },
  { nom: "interroger", seuil: 1 },                                // fiche ouverte
];
const SALUT_MS = 900;          // le temps de voir l'étape réussie avant la suivante
const REPRISE_MS = 1400;       // un geste interrompu : la démonstration revient
// La dernière carte s'efface quand on reprend la visite, mais pas sur l'élan d'un
// geste commencé avant qu'elle ne paraisse.
const LECTURE_MS = 1500;

export function initiation({ elementAMontrer, estEnVol, revenirAPied }) {
  const racine = document.querySelector("#initiation");
  const carte = racine.querySelector(".carte");
  const sections = racine.querySelectorAll("[data-etape]");
  const gestes = racine.querySelectorAll("[data-geste]");
  const points = racine.querySelectorAll(".points i");
  const jauge = racine.querySelector(".progres i");
  const bouton = racine.querySelector(".passer");
  const cible = racine.querySelector(".cible");
  const nomCible = cible.querySelector(".nom");

  let rang = 0, acquis = 0, reussie = false, finieDepuis = 0;
  let reprise = 0, enchainement = 0, suivi = 0;

  const enCours = () => !racine.hidden && !racine.classList.contains("parti");
  const finie = () => rang === ETAPES.length;
  // La jauge de l'altitude se remplit en montant, puis seulement en redescendant.
  const deniveleUtile = (dy) =>
    acquis < DENIVELE ? Math.min(Math.max(dy, 0), DENIVELE - acquis) : Math.max(-dy, 0);

  function afficher(nom) {
    for (const s of sections) s.hidden = s.dataset.etape !== nom;
    for (const g of gestes) g.hidden = g.dataset.geste !== nom;
    points.forEach((p, i) => {
      p.classList.toggle("faite", i < rang);
      p.classList.toggle("courante", i === rang);
    });
  }

  function designer(selecteur) {
    for (const el of document.querySelectorAll(".designe")) el.classList.remove("designe");
    if (selecteur) document.querySelector(selecteur).classList.add("designe");
  }

  function suivreCible() {
    if (!enCours() || ETAPES[rang]?.nom !== "interroger") return;
    const element = elementAMontrer();
    cible.classList.toggle("vue", !!element);
    if (element) {
      cible.style.left = `${element.clientX}px`;
      cible.style.top = `${element.clientY}px`;
      nomCible.textContent = element.nom;
    }
    suivi = requestAnimationFrame(suivreCible);
  }

  function commencerEtape(i) {
    rang = i;
    acquis = 0;
    reussie = false;
    jauge.style.width = "0";
    afficher(ETAPES[i].nom);
    designer(ETAPES[i].bouton);
    cible.classList.remove("vue");
    if (ETAPES[i].nom === "interroger") suivi = requestAnimationFrame(suivreCible);
    if (ETAPES[i].nom === "voler" && estEnVol()) reussir();
  }

  function conclure() {
    rang = ETAPES.length;
    finieDepuis = performance.now();
    carte.classList.add("finie");
    afficher("fin");
    designer(null);
    revenirAPied();
    ecrire(bouton, "initiation_visiter");
    retenir(CLEF, "suivie");
  }

  function reussir() {
    reussie = true;
    jauge.style.width = "100%";
    carte.classList.add("reussie");
    enchainement = setTimeout(() => {
      carte.classList.remove("reussie");
      racine.classList.remove("agit");
      if (rang + 1 < ETAPES.length) commencerEtape(rang + 1); else conclure();
    }, SALUT_MS);
  }

  function signalerGeste() {
    racine.classList.add("agit");
    clearTimeout(reprise);
    reprise = setTimeout(() => racine.classList.remove("agit"), REPRISE_MS);
  }

  function terminer() {
    retenir(CLEF, "suivie");
    clearTimeout(enchainement);
    cancelAnimationFrame(suivi);
    designer(null);
    // L'initiation a fait voler ; la visite, elle, se fait à pied.
    revenirAPied();
    racine.classList.add("parti");
    setTimeout(() => { if (racine.classList.contains("parti")) racine.hidden = true; }, 400);
  }

  function progresser(nom, quantite) {
    if (!enCours() || quantite <= 0) return;
    if (finie()) {
      if (performance.now() - finieDepuis > LECTURE_MS) terminer();
      return;
    }
    const etape = ETAPES[rang];
    if (etape.nom !== nom || reussie) return;
    acquis += quantite;
    jauge.style.width = `${Math.min(acquis / etape.seuil, 1) * 100}%`;
    signalerGeste();
    if (acquis >= etape.seuil) reussir();
  }

  function lancerInitiation() {
    clearTimeout(enchainement);
    cancelAnimationFrame(suivi);
    carte.classList.remove("reussie", "finie");
    racine.classList.remove("parti", "agit");
    ecrire(bouton, "initiation_passer");
    racine.hidden = false;
    commencerEtape(0);
  }

  bouton.onclick = (e) => { e.currentTarget.blur(); terminer(); };

  return {
    lancerInitiation,
    initiationSuivie: () => lireRetenu(CLEF) !== null,
    noterRegard: (angle) => progresser("regarder", angle),
    noterDeplacement: (metres) => progresser("avancer", metres),
    noterInterrogation: () => progresser("interroger", 1),
    noterEnvol: () => progresser("voler", 1),
    noterAltitude: (dy) => progresser("monter", deniveleUtile(dy)),
  };
}
