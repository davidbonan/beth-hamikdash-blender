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
const visions = [...scene.querySelectorAll(".vision")];

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

// À chaque halte, l'image du film prise de ce point se fond sur la scène, puis s'efface
// avant que la marche reprenne : la scène et l'image sont le même lieu.
const ATTENTE_S = 0.8, FONDU_S = 1.4;
let minuteries = [];
function montrerVision(degre) {
  for (const img of visions) img.classList.toggle("visible", img.dataset.degre === degre);
}
function rythmerLaHalte(li) {
  for (const m of minuteries) clearTimeout(m);
  montrerVision(null);
  minuteries = [
    setTimeout(() => montrerVision(li.dataset.degre), ATTENTE_S * 1000),
    setTimeout(() => montrerVision(null), (Number(li.dataset.pause) - FONDU_S) * 1000),
  ];
}

// Un téléphone reçoit le parcours enregistré : la scène pèse vingt mégaoctets, et son
// rendu y coûte la batterie. Ailleurs, c'est la scène elle-même qui marche.
const immobile = matchMedia("(prefers-reduced-motion: reduce)").matches || navigator.connection?.saveData === true;
const telephone = matchMedia("(max-width: 720px), (hover: none) and (pointer: coarse)").matches;

function suivreLaVideo() {
  const t = video.currentTime;
  const atteint = degres.filter((li) => Number(li.dataset.temps) <= t).pop() ?? degres[0];
  if (!atteint.hasAttribute("aria-current")) montrerDegre(atteint.dataset.degre, atteint.dataset.vue);
  const depuis = t - Number(atteint.dataset.temps);
  montrerVision(depuis >= ATTENTE_S && depuis <= Number(atteint.dataset.pause) - FONDU_S ? atteint.dataset.degre : null);
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
    for (const m of minuteries) clearTimeout(m);
    montrerVision(null);
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
    if (!e.data.degre) return;
    montrerDegre(e.data.degre, e.data.vue);
    rythmerLaHalte(degres.find((li) => li.dataset.degre === e.data.degre));
  });
  cadre.src = "/visite/?cinema";
  cadre.hidden = false;
}
