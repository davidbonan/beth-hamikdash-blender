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
const degres = [...scene.querySelectorAll(".degres ul li")];
const echelons = [...scene.querySelectorAll(".echelle button")];

function montrerDegre(id, vue) {
  for (const li of degres) li.toggleAttribute("aria-current", li.dataset.degre === id);
  for (const a of entrees) a.href = vue ? `/visite/?vue=${vue}` : "/visite/";
  let gravi = true;
  for (const bouton of echelons) {
    const courant = bouton.dataset.degre === id;
    bouton.toggleAttribute("aria-current", courant);
    bouton.classList.toggle("gravi", gravi && !courant);
    if (courant) gravi = false;
  }
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

// Un échelon cliqué mène la scène à son degré : le film y saute, la vidéo s'y cale.
function sauterA(degre) {
  const li = degres.find((li) => li.dataset.degre === degre);
  montrerDegre(li.dataset.degre, li.dataset.vue);
  if (immobile) return;
  if (telephone) {
    video.currentTime = Number(li.dataset.temps);
    video.play().catch(() => {});
  } else {
    cadre.contentWindow?.postMessage({ type: "cinema", aller: degre }, location.origin);
  }
}
for (const bouton of echelons) bouton.addEventListener("click", () => sauterA(bouton.dataset.degre));

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
