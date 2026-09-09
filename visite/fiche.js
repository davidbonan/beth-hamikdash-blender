/**
 * La fiche d'un concept : ce qu'on lit quand on interroge un élément.
 *
 * Au bureau c'est un panneau latéral ; au doigt un tiroir qui monte du bas, en deux
 * crans — un aperçu qui laisse voir ce qu'on vient de toucher, et le plein écran pour
 * les sources. Un panneau de 400 px sur un téléphone recouvre le Temple entier, et
 * l'élément dont il parle avec.
 */
export const ZONES = {
  har_habayit: "Har HaBayit", ezrat_nashim: "Ezrat Nashim", azara: "Azara",
  mizbeach: "Mizbea'h", oulam: "Oulam", heikhal: "Heikhal",
  kodesh_hakodashim: "Kodesh HaKodashim", lishkot: "Lishkot",
};

// Sefaria distingue la michna du folio : `Middot 2:1` est une michna, `Yoma 54a` un
// folio de guemara. Le nom du traité est le même, le préfixe non — d'où le test sur
// la forme de la cote plutôt qu'une table à double entrée.
const TRAITES = {
  middot: "Middot", tamid: "Tamid", yoma: "Yoma", shekalim: "Shekalim",
  soucca: "Sukkah", souccah: "Sukkah", sukkah: "Sukkah", succa: "Sukkah",
  kelim: "Kelim", arakhin: "Arakhin", erakhin: "Arakhin",
  zevahim: "Zevachim", zevachim: "Zevachim",
  menahot: "Menachot", menachot: "Menachot",
  "baba batra": "Bava Batra", "bava batra": "Bava Batra",
  houlin: "Chullin", chullin: "Chullin", horayot: "Horayot",
  "yerushalmi yoma": "Jerusalem Talmud Yoma",
  pesachim: "Pesachim", pesahim: "Pesachim", "pessahim": "Pesachim",
};
const OUVRAGES = {
  "rambam beit habehira": "Mishneh Torah, The Chosen Temple",
  "beit habehira": "Mishneh Torah, The Chosen Temple",
  "rambam klei hamikdash": "Mishneh Torah, Vessels of the Sanctuary and Those Who Serve Therein",
  "rambam biat hamikdash": "Mishneh Torah, Admission into the Sanctuary",
  "melakhim i": "I Kings", "i rois": "I Kings", "rois i": "I Kings", "i melakhim": "I Kings",
  "divrei hayamim ii": "II Chronicles", "ii chroniques": "II Chronicles",
  yechezkel: "Ezekiel", ezechiel: "Ezekiel",
  shemot: "Exodus", exode: "Exodus",
  vayikra: "Leviticus", levitique: "Leviticus",
  devarim: "Deuteronomy", deuteronome: "Deuteronomy",
  bamidbar: "Numbers", nombres: "Numbers",
  "i samuel": "I Samuel", "shmuel i": "I Samuel",
  yirmeyahou: "Jeremiah", jeremie: "Jeremiah",
  yehezkel: "Ezekiel",
  "rambam temidin": "Mishneh Torah, Daily Offerings and Additional Offerings",
  "rashi exode": "Rashi on Exodus", "rashi shemot": "Rashi on Exodus",
  "rambam sur middot": "Rambam on Mishnah Middot",
};

const pele = (s) => (s || "").toLowerCase().normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "").replace(/['’.,]/g, "").replace(/\s+/g, " ").trim();

const url = (tref) => "https://www.sefaria.org/" +
  encodeURIComponent(tref.replace(/ /g, "_")).replace(/%2C/g, ",").replace(/%3A/g, ":");

function lienSefaria(oeuvre, ref) {
  const clef = pele(oeuvre);
  const direct = OUVRAGES[clef];
  if (direct) return url(`${direct} ${ref}`);
  const traite = TRAITES[clef.replace(/^(mishna|mishnah|talmud) /, "")];
  if (!traite) return null;                       // archéologie, choix du projet : pas de cote Sefaria
  const folio = /^\d+[ab]$/.test((ref || "").trim());
  return url(`${folio ? traite : "Mishnah " + traite} ${ref}`);
}

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

  const fermer = () => cadre.classList.remove("ouverte", "pleine");

  function montrer(id) {
    const c = concepts.get(id);
    if (!c) return;
    const src = (c.sources || []).map((s) => {
      const lien = lienSefaria(s.oeuvre, s.ref);
      const tete = `${echappe(s.oeuvre)} ${echappe(s.ref)}`;
      return `<li>${lien ? `<a href="${lien}" target="_blank" rel="noopener">${tete}</a>` : tete}` +
             `${s.citation ? `<em>« ${echappe(s.citation)} »</em>` : ""}</li>`;
    }).join("");

    corps.innerHTML = `
      <p class="zone">${echappe(ZONES[c.zone] || c.zone)}</p>
      <h2>${echappe(c.nom)}</h2>
      ${c.he ? `<p class="heb">${echappe(c.he)}</p>` : ""}
      ${c.translit ? `<p class="translit">${echappe(c.translit)}</p>` : ""}
      ${c.resume
        ? `<p class="resume">${echappe(c.resume)}</p>`
        : `<p class="vide">Cet élément est modélisé mais pas encore documenté : aucune
           source n'a été relevée pour lui dans la fiche technique. Plutôt qu'une cote
           plausible, la visite n'affiche rien.</p>`}
      ${c.cotes?.length ? `<h3>Cotes</h3><ul class="cotes">${
        c.cotes.map((x) => `<li>${echappe(x)}</li>`).join("")}</ul>` : ""}
      ${src ? `<h3>Sources</h3><ul class="sources">${src}</ul>` : ""}
      ${c.note ? `<p class="note"><b>Arbitrage du projet</b>${echappe(c.note)}</p>` : ""}`;
    cadre.scrollTop = 0;
    cadre.classList.remove("pleine");             // toujours rouvert sur l'aperçu
    cadre.classList.add("ouverte");
  }

  document.querySelector("#fermer").onclick = fermer;
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

  return { montrer, fermer };
}
