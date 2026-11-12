// « Aller à un lieu » : un champ dans le plan, qui resserre la liste des entrées et des lieux, groupés par zone.
import { nomDeZone } from "./fiche.js";
import { langue, texte } from "./langue.js";
import { sansAccent } from "./recherche.js";

// `destinations()` : [{ id, nom, zone }] dans la langue du moment ; `choisir(id)` reçoit celle qu'on prend.
export function allerA(racine, { destinations, choisir }) {
  const champ = racine.querySelector("input");
  const liste = racine.querySelector(".trouves");
  const ouverte = () => !liste.hidden;

  function trouvees() {
    const mot = sansAccent(champ.value.trim());
    return destinations()
      .filter((d) => sansAccent(d.nom).includes(mot))
      .sort((a, b) => nomDeZone(a.zone).localeCompare(nomDeZone(b.zone), langue()) || a.nom.localeCompare(b.nom, langue()));
  }

  function lister() {
    liste.replaceChildren();
    let zone = null;
    for (const d of trouvees()) {
      if (d.zone !== zone) {
        zone = d.zone;
        liste.append(Object.assign(document.createElement("h3"), { textContent: nomDeZone(zone) }));
      }
      const bouton = Object.assign(document.createElement("button"), { type: "button", textContent: d.nom });
      bouton.dataset.destination = d.id;
      liste.append(bouton);
    }
    if (zone === null) liste.append(Object.assign(document.createElement("p"), { className: "rien", textContent: texte("aller_vide") }));
    liste.hidden = false;
    liste.scrollTop = 0;
  }

  function refermer() {
    liste.hidden = true;
  }

  function prendre(id) {
    refermer();
    champ.value = "";
    champ.blur();
    choisir(id);
  }

  champ.addEventListener("focus", lister);
  champ.addEventListener("input", lister);
  champ.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const premiere = liste.querySelector("[data-destination]");
    if (premiere) prendre(premiere.dataset.destination);
  });
  liste.addEventListener("click", (e) => {
    const bouton = e.target.closest("[data-destination]");
    if (bouton) prendre(bouton.dataset.destination);
  });
  addEventListener("pointerdown", (e) => { if (ouverte() && !racine.contains(e.target)) refermer(); });

  return {
    ouverte,
    refermer,
    rafraichir() {
      champ.placeholder = texte("aller");
      if (ouverte()) lister();
    },
  };
}
