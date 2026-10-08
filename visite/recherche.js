// La recherche : la liste des éléments du Temple, par zone, qu'un mot tapé resserre.
import { nomDeZone } from "./fiche.js";
import { langue, texte } from "./langue.js";

const sansAccent = (s) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
// Au doigt, le clavier qui monte cacherait la liste : on ne le lève que si le visiteur touche le champ.
const CLAVIER_PHYSIQUE = matchMedia("(hover: hover) and (pointer: fine)");

export function recherche({ concepts, choisir }) {
  const fenetre = document.querySelector("#recherche");
  const champ = fenetre.querySelector("input");
  const resultats = fenetre.querySelector(".resultats");
  const ouvert = () => !fenetre.hidden;

  function trouves() {
    const mot = sansAccent(champ.value.trim());
    return [...concepts.values()]
      .filter((c) => [c.nom, c.he, c.translit].some((nom) => nom && sansAccent(nom).includes(mot)))
      .sort((a, b) => nomDeZone(a.zone).localeCompare(nomDeZone(b.zone), langue()) || a.nom.localeCompare(b.nom, langue()));
  }

  function lister() {
    resultats.replaceChildren();
    let zone = null;
    for (const c of trouves()) {
      if (c.zone !== zone) {
        zone = c.zone;
        resultats.append(Object.assign(document.createElement("h3"), { textContent: nomDeZone(zone) }));
      }
      const bouton = Object.assign(document.createElement("button"), { type: "button", textContent: c.nom });
      bouton.dataset.concept = c.id;
      resultats.append(bouton);
    }
    if (zone === null) resultats.append(Object.assign(document.createElement("p"), { className: "rien", textContent: texte("recherche_vide") }));
  }

  function rafraichir() {
    champ.placeholder = texte("recherche_champ");
    if (ouvert()) lister();
  }

  function ouvrir() {
    fenetre.hidden = false;
    champ.value = "";
    lister();
    resultats.scrollTop = 0;
    if (CLAVIER_PHYSIQUE.matches) champ.focus();
  }

  function fermer() {
    fenetre.hidden = true;
    document.activeElement?.blur();
  }

  champ.oninput = lister;
  resultats.onclick = (e) => {
    const bouton = e.target.closest("[data-concept]");
    if (!bouton) return;
    fermer();
    choisir(bouton.dataset.concept);
  };
  fenetre.querySelector(".fermer").onclick = fermer;
  document.querySelector("#chercher").onclick = (e) => { e.currentTarget.blur(); ouvrir(); };
  addEventListener("keydown", (e) => { if (e.key === "Escape" && ouvert()) fermer(); });
  rafraichir();

  return { rafraichir };
}
