// node capter.mjs <url de la visite> vue <id,id…> <dossier>        une image fixe par vue (?vue=)
// node capter.mjs <url de la visite> parcours <id> <n> <dossier>    la marche de la station n-1 à n, puis la halte
// node capter.mjs <url de la visite> plan <plan.json> <dossier>     une caméra libre, clés en amot
// Options : --taille 1920x1080, --fps 30, --halte 3 (s, parcours), --moment jour|nuit|aube…, --interface (garde l'interface),
//   --echelle 1.5 (l'interface grossie d'autant, l'image garde sa --taille).
// Rend sous Metal, boucle figée, à pas fixe ; une séquence sort en images dans <dossier>/ et en <dossier>.mp4.
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";

const AMA = 0.48;
const OPTIONS = { "--taille": "1920x1080", "--fps": "30", "--halte": "3", "--moment": null, "--echelle": "1" };
const MARCHE_MAX_S = 180;

const args = process.argv.slice(2);
const option = (nom) => {
  const i = args.indexOf(nom);
  return i < 0 ? OPTIONS[nom] : args.splice(i, 2)[1];
};
const taille = option("--taille"), fps = Number(option("--fps")), halteS = Number(option("--halte")), moment = option("--moment");
const grossi = Number(option("--echelle"));
const avecInterface = args.includes("--interface");
if (avecInterface) args.splice(args.indexOf("--interface"), 1);
const [url, mode, ...reste] = args;
const MODES = { vue: 2, parcours: 3, plan: 2 };
if (!url || MODES[mode] !== reste.length) {
  console.error(readFileSync(new URL(import.meta.url), "utf8").split("\n").slice(0, 5).join("\n"));
  process.exit(2);
}
const dossier = reste.at(-1);
mkdirSync(dossier, { recursive: true });
const [largeur, hauteur] = taille.split("x").map(Number);
const pas = 1 / fps;

const { chromium } = createRequire(new URL("../studio/package.json", import.meta.url))("playwright-core");
const cache = `${process.env.HOME}/Library/Caches/ms-playwright`;
const version = readdirSync(cache).filter((d) => /^chromium-\d+$/.test(d)).sort((a, b) => a.localeCompare(b, "en", { numeric: true })).pop();
const mac = `${cache}/${version}/chrome-mac-arm64`;
const app = readdirSync(mac).find((d) => d.endsWith(".app"));
const binaire = `${mac}/${app}/Contents/MacOS/${readdirSync(`${mac}/${app}/Contents/MacOS`)[0]}`;

const navigateur = await chromium.launch({ executablePath: binaire, args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"] });
const page = await navigateur.newPage({ viewport: { width: Math.round(largeur / grossi), height: Math.round(hauteur / grossi) },
  deviceScaleFactor: grossi });
await page.addInitScript(() => {
  localStorage.setItem("visite.langue", "en");
  localStorage.setItem("visite.initiation", "suivie");
  localStorage.setItem("visite.parcours.allure", "1");
});
page.on("pageerror", (e) => console.log("[erreur]", String(e).slice(0, 300)));
const cdp = await page.context().newCDPSession(page);
const capturer = async (chemin, format) => writeFileSync(chemin, Buffer.from((await cdp.send("Page.captureScreenshot", format)).data, "base64"));

// Le voile tombe à chaque fondu, se relève en 0,34 s, et une troupe neuve le tient noir le temps de descendre.
async function attendreLaScene() {
  await page.waitForFunction(() => !document.querySelector("#voile.noir, #voile.attente"), null, { timeout: 180000 });
  await page.evaluate(() => window.__figurants);
  await page.waitForTimeout(450);
}

let images = 0;
async function filmer(avancer) {
  if (await page.evaluate(() => !!document.querySelector("#voile.noir, #voile.attente"))) await attendreLaScene();
  await page.evaluate((dt) => window.__image(dt), pas);
  await avancer?.();
  await capturer(`${dossier}/${String(images++).padStart(5, "0")}.jpg`, { format: "jpeg", quality: 92 });
}

function encoder() {
  const sortie = `${dossier.replace(/\/$/, "")}.mp4`;
  execFileSync("ffmpeg", ["-v", "error", "-y", "-framerate", String(fps), "-i", `${dossier}/%05d.jpg`,
    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p", "-c:v", "libx264", "-crf", "14", "-preset", "slow", sortie]);
  console.log(`${sortie} · ${images} images · ${(images / fps).toFixed(1)} s`);
}

const lisse = (u) => u * u * (3 - 2 * u);
function cleA(cles, t) {
  const suivante = cles.findIndex((c) => c.t > t);
  if (suivante <= 0) return cles[suivante === 0 ? 0 : cles.length - 1];
  const [a, b] = [cles[suivante - 1], cles[suivante]];
  const u = lisse((t - a.t) / (b.t - a.t));
  const mele = (de, vers) => Array.isArray(de) ? de.map((v, i) => mele(v, vers[i])) : de + (vers - de) * u;
  return Object.fromEntries(Object.keys(a).map((k) => [k, mele(a[k], b[k])]));
}

// Les gestes d'un plan, sur l'interface de la visite : la souris (clés {t, x, y}, en fraction de l'écran),
// ou {t, point: [x, hauteur, z]} pour suivre un point du monde (amot, le plan donne sa focale), ses clics (secondes),
// le défilement de la fiche ouverte (clés {t, y}, 0 en haut, 1 en bas).
const CURSEUR = `<svg viewBox="0 0 16 24" width="17" height="25"><path d="M1 1v19l5-5 3.5 7.5 3-1.4L9 13.8h7z"
  fill="#fff" stroke="#111" stroke-width="1.3" stroke-linejoin="round"/></svg>`;
async function preparerLesGestes() {
  await page.addStyleTag({ content: `html.cinema.gestes #fiche, html.cinema.gestes #survol { display: block !important; }
    html.cinema.gestes canvas { pointer-events: auto; }
    #curseur { position: fixed; left: 0; top: 0; z-index: 100; pointer-events: none; display: none; }` });
  await page.evaluate((svg) => {
    document.documentElement.classList.add("gestes");
    const curseur = Object.assign(document.createElement("div"), { id: "curseur", innerHTML: svg });
    document.body.append(curseur);
    addEventListener("pointermove", (e) => {
      curseur.style.display = "block";
      curseur.style.transform = `translate(${e.clientX - 1}px, ${e.clientY - 1}px)`;
    }, true);
  }, CURSEUR);
  await cdp.send("Animation.enable");
}

// Les transitions de l'interface courent en temps réel, une image filmée prend plus que son pas : on les ralentit d'autant.
async function caleLesTransitions(debut, filmees) {
  const reel = (performance.now() - debut) / filmees / 1000;
  await cdp.send("Animation.setPlaybackRate", { playbackRate: Math.min(1, pas / reel) });
}

const moins = (a, b) => a.map((v, i) => v - b[i]);
const scalaire = (a, b) => a.reduce((s, v, i) => s + v * b[i], 0);
const norme = (a) => a.map((v) => v / Math.hypot(...a));
const vectoriel = ([a, b, c], [d, e, f]) => [b * f - c * e, c * d - a * f, a * e - b * d];
function aLEcran(point, { oeil, cible }, focale) {
  const devant = norme(moins(cible, oeil));
  const droite = norme(vectoriel(devant, [0, 1, 0]));
  const haut = vectoriel(droite, devant);
  const d = moins(point, oeil), loin = scalaire(d, devant);
  const demiLargeur = 18 / focale, demiHauteur = demiLargeur * hauteur / largeur;
  return { x: (1 + scalaire(d, droite) / loin / demiLargeur) / 2, y: (1 - scalaire(d, haut) / loin / demiHauteur) / 2 };
}

function gesteA(gestes, t, avant, regard, focale) {
  const actions = [];
  if (gestes.souris?.length && t >= gestes.souris[0].t) {
    const cles = gestes.souris.map((c) => (c.point ? { t: c.t, ...aLEcran(c.point, regard, focale) } : c));
    const { x, y } = cleA(cles, t);
    actions.push(() => page.mouse.move(x * page.viewportSize().width, y * page.viewportSize().height));
  }
  if (gestes.clics?.some((c) => c > avant && c <= t)) actions.push(async () => { await page.mouse.down(); await page.mouse.up(); });
  if (gestes.fiche?.length && t >= gestes.fiche[0].t) {
    const { y } = cleA(gestes.fiche, t);
    actions.push(() => page.evaluate((y) => {
      const fiche = document.querySelector("#fiche");
      fiche.scrollTop = y * (fiche.scrollHeight - fiche.clientHeight);
    }, y));
  }
  return actions;
}

async function ouvrirParcours(id, rang) {
  await page.evaluate(([id, rang]) => window.__parcours.ouvrir(id, rang), [id, rang]);
  await page.waitForTimeout(250);
  await attendreLaScene();
}

await page.goto(url, { waitUntil: "load", timeout: 90000 });
await page.waitForFunction(() => window.__pret === true, null, { timeout: 180000 });
if (!avecInterface) await page.evaluate(() => document.documentElement.classList.add("cinema"));
await attendreLaScene();
if (moment) {
  await page.evaluate((m) => window.__moment(m), moment);
  await attendreLaScene();
}

if (mode === "vue") {
  for (const id of reste[0].split(",")) {
    await page.evaluate((id) => window.__demande(id), id);
    await page.waitForTimeout(250);
    await attendreLaScene();
    await page.evaluate(() => { window.__temps(3); for (let k = 0; k < 6; k++) window.__rendre(); });
    await capturer(`${dossier}/${id}.png`, { format: "png" });
    console.log(`${dossier}/${id}.png`);
  }
} else if (mode === "parcours") {
  const [id, n] = [reste[0], Number(reste[1])];
  const stations = await page.evaluate((id) => window.__parcours.stations(id), id);
  if (n > 0 && (stations[n].fondu || stations[n - 1].fondu)) {
    console.error(`${id} : de la station ${n - 1} à ${n}, on passe sous le voile, il n'y a pas de marche à filmer`);
    process.exit(1);
  }
  await ouvrirParcours(id, Math.max(n - 1, 0));
  await page.evaluate(() => window.__figer());
  if (n > 0) {
    await page.evaluate(() => document.querySelector("#parcours .suivant").click());
    for (let t = 0; await page.evaluate(() => !!window.__parcours.trajet()); t += pas) {
      if (t > MARCHE_MAX_S) throw new Error(`marche de plus de ${MARCHE_MAX_S} s : station ${n} en fondu ?`);
      await filmer();
    }
  }
  for (let k = 0; k < halteS * fps; k++) await filmer();
  encoder();
} else {
  const plan = JSON.parse(readFileSync(reste[0], "utf8"));
  if (plan.parcours) await ouvrirParcours(plan.parcours, plan.station ?? 0);
  if (plan.moment) {
    await page.evaluate((m) => window.__moment(m), plan.moment);
    await attendreLaScene();
  }
  if (plan.focale) await page.evaluate((mm) => window.__focale(mm), plan.focale);
  await page.evaluate(() => window.__figer());
  if (plan.gestes) await preparerLesGestes();
  const duree = plan.cles.at(-1).t;
  const debut = performance.now();
  for (let t = 0, k = 0; t <= duree + 1e-6; t += pas, k++) {
    const { oeil, cible } = cleA(plan.cles, t);
    if (plan.gestes?.souris?.some((c) => c.point) && !plan.focale) throw new Error("une souris qui suit un point veut la focale du plan");
    if (plan.gestes && k === 10) await caleLesTransitions(debut, k);
    await filmer(async () => {
      await page.evaluate((m) => window.__cam(...m), [...oeil, ...cible].map((v) => v * AMA));
      for (const geste of plan.gestes ? gesteA(plan.gestes, t, t - pas, { oeil, cible }, plan.focale) : []) await geste();
    });
  }
  encoder();
}
await navigateur.close();
