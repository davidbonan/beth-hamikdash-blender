// La visite retient la langue sous cette clef : arriver depuis l'accueil évite de la redemander.
for (const lien of document.querySelectorAll("a[data-langue]")) {
  lien.addEventListener("click", () => {
    try { localStorage.setItem("visite.langue", lien.dataset.langue); } catch {}
  });
}

const paliers = [...document.querySelectorAll("[data-degre]")].filter((el) => el !== document.body);
const observateur = new IntersectionObserver(
  (entrees) => {
    const visible = entrees.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (visible) document.body.dataset.degre = visible.target.dataset.degre;
  },
  { rootMargin: "-40% 0px -40% 0px", threshold: [0, 0.25, 0.5, 0.75, 1] },
);
for (const palier of paliers) observateur.observe(palier);
