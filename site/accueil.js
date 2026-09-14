// La visite retient la langue sous cette clef : arriver depuis l'accueil évite de la redemander.
for (const lien of document.querySelectorAll("a[data-langue]")) {
  lien.addEventListener("click", () => {
    try { localStorage.setItem("visite.langue", lien.dataset.langue); } catch {}
  });
}

// L'échelle suit la lecture : le degré au milieu de l'écran est le courant, ceux d'avant sont gravis.
const echelons = [...document.querySelectorAll(".echelle li")];
const lieux = echelons.map((li) => document.getElementById(li.dataset.degre)).filter(Boolean);

function marquer(degre) {
  let gravi = true;
  for (const li of echelons) {
    const courant = li.dataset.degre === degre;
    li.classList.toggle("courant", courant);
    li.classList.toggle("gravi", gravi && !courant);
    li.firstElementChild.toggleAttribute("aria-current", courant);
    if (courant) gravi = false;
  }
}
marquer(echelons[0]?.dataset.degre);

const guetteur = new IntersectionObserver((entrees) => {
  for (const e of entrees) if (e.isIntersecting) marquer(e.target.id);
}, { rootMargin: "-45% 0px -45% 0px" });
for (const lieu of lieux) guetteur.observe(lieu);
