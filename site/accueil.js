// La visite retient la langue sous cette clef : arriver depuis l'accueil évite de la redemander.
for (const lien of document.querySelectorAll("a[data-langue]")) {
  lien.addEventListener("click", () => {
    try { localStorage.setItem("visite.langue", lien.dataset.langue); } catch {}
  });
}

// L'échelle et la scène suivent la lecture : le degré au milieu de l'écran est le courant, ceux d'avant sont gravis.
const echelons = [...document.querySelectorAll(".echelle li")];
const ordre = echelons.map((li) => li.dataset.degre);
const marques = [...document.querySelectorAll("[data-degre]")];
const lieux = ordre.map((degre) => document.getElementById(degre)).filter(Boolean);

function marquer(degre) {
  const rang = ordre.indexOf(degre);
  for (const el of marques) {
    const sien = ordre.indexOf(el.dataset.degre);
    el.classList.toggle("courant", sien === rang);
    el.classList.toggle("gravi", sien < rang);
  }
  for (const li of echelons) li.firstElementChild.toggleAttribute("aria-current", li.dataset.degre === degre);
}
marquer(ordre[0]);

const guetteur = new IntersectionObserver((entrees) => {
  for (const e of entrees) if (e.isIntersecting) marquer(e.target.id);
}, { rootMargin: "-45% 0px -45% 0px" });
for (const lieu of lieux) guetteur.observe(lieu);

// Les lishkot : un repère choisi montre sa chambre ; tant qu'on n'a touché à rien, la plongée les parcourt d'elle-même.
const lishkot = document.querySelector(".lishkot");
if (lishkot) {
  const reperes = [...lishkot.querySelectorAll(".repere")];
  const cartes = [...lishkot.querySelectorAll(".chambres li")];
  let courante = 0;
  let parcours = null;
  let choisie = false;

  function montrer(rang) {
    courante = (rang + reperes.length) % reperes.length;
    reperes.forEach((r, i) => r.toggleAttribute("aria-current", i === courante));
    cartes.forEach((c, i) => c.classList.toggle("courant", i === courante));
  }

  function arreterParcours() {
    clearInterval(parcours);
    parcours = null;
  }

  function choisir(rang) {
    choisie = true;
    arreterParcours();
    montrer(rang);
  }

  reperes.forEach((repere, rang) => {
    repere.addEventListener("click", (e) => { e.preventDefault(); choisir(rang); });
    repere.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") choisir(rang); });
    repere.addEventListener("focus", () => choisir(rang));
  });
  lishkot.classList.add("vivante");
  montrer(0);

  if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
    new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return arreterParcours();
      if (!choisie && !parcours) parcours = setInterval(() => montrer(courante + 1), 4500);
    }, { threshold: 0.5 }).observe(lishkot);
  }
}
