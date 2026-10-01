// L'encyclopédie : les concepts de la charnière, ce que les trois relevés en disent, et leurs traductions.
import { LANGUE_SOURCE } from "./langue.js";

// Le cachet que le build appose sur chaque module voyage jusqu'ici : les données qu'on
// demande par un nom construit le portent comme celles qu'il a pu réécrire.
const VERSION = new URL(import.meta.url).search;

export async function json(chemin, obligatoire = true) {
  const r = await fetch(chemin + VERSION);
  if (!r.ok) {
    if (obligatoire) throw new Error(`${chemin} : ${r.status}`);
    return null;                                  // encyclopédie encore incomplète
  }
  return r.json();
}

const FICHIERS_CONTENU = ["a", "b", "c"];
export const contenusSources = () => FICHIERS_CONTENU.map((f) => json(`./contenu_${f}.json`, false));

const traductions = new Map();
function contenusTraduits(code) {
  if (!traductions.has(code)) {
    traductions.set(code, Promise.all(FICHIERS_CONTENU.map((f) => json(`./contenu_${f}.${code}.json`, false))));
  }
  return traductions.get(code);
}

const apport = (contenusDuFichier, id) => contenusDuFichier.find((x) => x && x[id])?.[id] || {};

export async function conceptsEn(code, fiche, contenus) {
  const traduits = code === LANGUE_SOURCE ? [] : await contenusTraduits(code);
  return new Map(fiche.concepts.map((c) =>
    [c.id, { ...c, ...apport(contenus, c.id), ...apport(traduits, c.id) }]));
}
