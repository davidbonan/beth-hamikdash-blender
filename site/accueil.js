// La visite retient la langue sous cette clef : arriver depuis l'accueil évite de la redemander.
for (const lien of document.querySelectorAll("a[data-langue]")) {
  lien.addEventListener("click", () => {
    try { localStorage.setItem("visite.langue", lien.dataset.langue); } catch {}
  });
}

const scene = document.querySelector(".scene");
const cadre = scene.querySelector("iframe");
const video = scene.querySelector("video");
const entrees = scene.querySelectorAll("a.entrer");
const degres = [...scene.querySelectorAll(".degres li")];

function montrerDegre(id, vue) {
  for (const li of degres) li.toggleAttribute("aria-current", li.dataset.degre === id);
  for (const a of entrees) a.href = vue ? `/visite/?vue=${vue}` : "/visite/";
}
montrerDegre(degres[0].dataset.degre, degres[0].dataset.vue);

// Un téléphone reçoit le parcours enregistré : la scène pèse vingt mégaoctets, et son
// rendu y coûte la batterie. Ailleurs, c'est la scène elle-même qui marche.
const immobile = matchMedia("(prefers-reduced-motion: reduce)").matches || navigator.connection?.saveData === true;
const telephone = matchMedia("(max-width: 720px), (hover: none) and (pointer: coarse)").matches;

function suivreLaVideo() {
  const t = video.currentTime;
  const atteint = degres.filter((li) => Number(li.dataset.temps) <= t).pop() ?? degres[0];
  if (!atteint.hasAttribute("aria-current")) montrerDegre(atteint.dataset.degre, atteint.dataset.vue);
}

if (immobile) {
  // L'affiche suffit.
} else if (telephone) {
  video.src = video.dataset.src;
  video.hidden = false;
  video.addEventListener("playing", () => scene.classList.add("vivante"), { once: true });
  video.addEventListener("timeupdate", suivreLaVideo);
  video.play().catch(() => {});
} else {
  addEventListener("message", (e) => {
    if (e.origin !== location.origin || e.data?.type !== "cinema") return;
    if (e.data.pret) scene.classList.add("vivante");
    if (e.data.degre) montrerDegre(e.data.degre, e.data.vue);
  });
  cadre.src = "/visite/?cinema";
  cadre.hidden = false;
}
