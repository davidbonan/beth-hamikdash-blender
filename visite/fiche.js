/**
 * La fiche d'un concept : ce qu'on lit quand on interroge un élément.
 *
 * Au bureau c'est un panneau latéral ; au doigt un tiroir qui monte du bas, en deux
 * crans — un aperçu qui laisse voir ce qu'on vient de toucher, et le plein écran pour
 * les sources. Un panneau de 400 px sur un téléphone recouvre le Temple entier, et
 * l'élément dont il parle avec.
 */
import { LANGUE_SOURCE, langue, libelle, texte } from "./langue.js";
import { lienSefaria } from "./sefaria.js";

export const nomDeZone = (zone) => libelle("zones", zone) ?? zone;

// La page de la fiche hors de la visite : le français à la racine du site, les autres langues sous leur code.
const adresseDeFiche = (id) => `${location.origin}/${langue() === LANGUE_SOURCE ? "" : `${langue()}/`}fiche/${id}/`;

const echappe = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Au-delà, le tiroir est lâché vers l'état visé, quelle que soit la distance parcourue.
const ELAN = 0.55;                                // px/ms
// Le même seuil que la feuille de style : hors de lui la fiche est un panneau, pas
// un tiroir, et sa poignée n'a rien à tirer.
const TIROIR = matchMedia("(max-width: 720px) and (min-height: 521px)");

export function panneau(concepts) {
  const cadre = document.querySelector("#fiche");
  const corps = document.querySelector("#corps");

  let affiche = null;

  const fermer = () => cadre.classList.remove("ouverte", "pleine");

  function remplir(c) {
    const src = (c.sources || []).map((s) => {
      const lien = lienSefaria(s.oeuvre, s.ref);
      const tete = `${echappe(libelle("oeuvres", s.oeuvre) ?? s.oeuvre)} <bdi>${echappe(s.ref)}</bdi>`;
      const citation = texte("guillemet_ouvrant") + s.citation + texte("guillemet_fermant");
      return `<li>${lien ? `<a href="${lien}" target="_blank" rel="noopener">${tete}</a>` : tete}` +
             `${s.citation ? `<em>${echappe(citation)}</em>` : ""}</li>`;
    }).join("");
    // En hébreu le titre est déjà le nom hébreu, et la translittération ne sert à personne.
    const nomSeul = langue() === "he";

    corps.innerHTML = `
      <p class="zone">${echappe(nomDeZone(c.zone))}</p>
      <h2>${echappe(c.nom)}</h2>
      ${c.he && !nomSeul ? `<p class="heb">${echappe(c.he)}</p>` : ""}
      ${c.translit && !nomSeul ? `<p class="translit">${echappe(c.translit)}</p>` : ""}
      ${c.resume
        ? `<p class="resume">${echappe(c.resume)}</p>`
        : `<p class="vide">${echappe(texte("non_documente"))}</p>`}
      ${c.cotes?.length ? `<h3>${echappe(texte("cotes"))}</h3><ul class="cotes">${
        c.cotes.map((x) => `<li>${echappe(x)}</li>`).join("")}</ul>` : ""}
      ${src ? `<h3>${echappe(texte("sources"))}</h3><ul class="sources">${src}</ul>` : ""}
      ${c.note ? `<p class="note"><b>${echappe(texte("arbitrage"))}</b>${echappe(c.note)}</p>` : ""}`;
  }

  function montrer(id) {
    const c = concepts.get(id);
    if (!c) return;
    affiche = id;
    remplir(c);
    cadre.scrollTop = 0;
    cadre.classList.remove("pleine");             // toujours rouvert sur l'aperçu
    cadre.classList.add("ouverte");
  }

  function rafraichir() {
    if (affiche) remplir(concepts.get(affiche));
  }

  document.querySelector("#fermer").onclick = fermer;

  const copier = document.querySelector("#copier");
  let finCopie;
  const titrerCopier = (clef) => {
    copier.title = texte(clef);
    copier.setAttribute("aria-label", copier.title);
  };
  copier.onclick = async (e) => {
    e.currentTarget.blur();
    await navigator.clipboard.writeText(adresseDeFiche(affiche));
    copier.classList.add("copie");
    titrerCopier("lien_copie");
    clearTimeout(finCopie);
    finCopie = setTimeout(() => {
      copier.classList.remove("copie");
      titrerCopier("copier_lien");
    }, 2000);
  };
  addEventListener("keydown", (e) => { if (e.key === "Escape") fermer(); });

  // ---- le tiroir se tire au doigt ----
  const poignee = document.querySelector("#poignee");
  let tire = null;

  poignee.addEventListener("pointerdown", (e) => {
    if (!TIROIR.matches) return;
    tire = { id: e.pointerId, y: e.clientY, y0: e.clientY, t: performance.now(),
             depart: cadre.getBoundingClientRect().top, hauteur: cadre.offsetHeight };
    cadre.style.transition = "none";
    poignee.setPointerCapture(e.pointerId);
  });

  poignee.addEventListener("pointermove", (e) => {
    if (!tire || e.pointerId !== tire.id) return;
    tire.y = e.clientY;
    const offset = Math.min(Math.max(tire.depart + (e.clientY - tire.y0), 0), innerHeight);
    cadre.style.transform = `translateY(${offset - (innerHeight - tire.hauteur)}px)`;
  });

  function lacher(e) {
    if (!tire || e.pointerId !== tire.id) return;
    const course = tire.y - tire.y0;
    const elan = course / Math.max(performance.now() - tire.t, 1);
    const plein = cadre.classList.contains("pleine");
    tire = null;
    cadre.style.transition = "";
    cadre.style.transform = "";
    if (elan > ELAN || course > innerHeight * 0.25) {
      if (plein) cadre.classList.remove("pleine"); else fermer();
    } else if (elan < -ELAN || course < -60) {
      cadre.classList.add("pleine");
    }
  }
  poignee.addEventListener("pointerup", lacher);
  poignee.addEventListener("pointercancel", lacher);

  return { montrer, fermer, rafraichir };
}
