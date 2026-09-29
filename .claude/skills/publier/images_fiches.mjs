// node images_fiches.mjs <url de la visite> <dossier> [--seulement id,id]
// L'image de chaque fiche : la vue que « Voir dans la visite » ouvre (`__demande`, comme `?vue=`), 1200 × 630, sous Metal.
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";

const options = process.argv.slice(2);
const i = options.indexOf("--seulement");
const seulement = i < 0 ? null : options.splice(i, 2)[1].split(",");
const [url, dossier] = options;
if (!url || !dossier) {
  console.error("usage: node images_fiches.mjs <url de la visite> <dossier> [--seulement id,id]   (playwright-core installé dans le dossier courant)");
  process.exit(2);
}
mkdirSync(dossier, { recursive: true });

const visite = new URL("../../../visite/", import.meta.url);
const ids = ["a", "b", "c"].flatMap((f) => Object.keys(JSON.parse(readFileSync(new URL(`contenu_${f}.json`, visite)))))
  .filter((id) => !seulement || seulement.includes(id));

const { chromium } = createRequire(`${process.cwd()}/`)("playwright-core");
const cache = `${process.env.HOME}/Library/Caches/ms-playwright`;
const version = readdirSync(cache).filter((d) => d.startsWith("chromium-")).sort((a, b) => a.localeCompare(b, "en", { numeric: true })).pop();
const mac = `${cache}/${version}/chrome-mac-arm64`;
const app = readdirSync(mac).find((d) => d.endsWith(".app"));
const binaire = `${mac}/${app}/Contents/MacOS/${readdirSync(`${mac}/${app}/Contents/MacOS`)[0]}`;

const navigateur = await chromium.launch({
  executablePath: process.env.CHROME ?? binaire, args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"],
});
const page = await navigateur.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
await page.addInitScript(() => {
  localStorage.setItem("visite.langue", "fr");
  localStorage.setItem("visite.initiation", "suivie");
});
page.on("pageerror", (e) => console.log("[erreur]", String(e).slice(0, 300)));
const cdp = await page.context().newCDPSession(page);

// Le voile tombe à chaque fondu et se relève en 0,34 s ; une troupe neuve le tient noir le temps de descendre.
async function attendreLaScene() {
  await page.waitForFunction(() => !document.querySelector("#voile.noir, #voile.attente"), null, { timeout: 180000 });
  await page.evaluate(() => window.__figurants);
  await page.waitForTimeout(450);
}

await page.goto(url, { waitUntil: "load", timeout: 90000 });
await page.waitForFunction(() => window.__pret === true, null, { timeout: 180000 });
// La classe du cinéma cache toute l'interface ; la visite, elle, reste en marche libre.
await page.evaluate(() => document.documentElement.classList.add("cinema"));

for (const id of ids) {
  await page.evaluate(() => { if (window.__parcours.ouvert()) window.__parcours.fermer(); });
  await attendreLaScene();
  await page.evaluate((id) => window.__demande(id), id);
  await page.waitForTimeout(250);
  await attendreLaScene();
  await page.evaluate(() => {
    window.__temps(3);
    for (let k = 0; k < 6; k++) window.__rendre();
  });
  const { data } = await cdp.send("Page.captureScreenshot", { format: "jpeg", quality: 80 });
  writeFileSync(`${dossier}/${id}.jpg`, Buffer.from(data, "base64"));
  console.log(id, JSON.stringify(await page.evaluate(() => ({ lieu: window.__etat().lieu, station: window.__parcours.ouvert() && window.__parcours.station() }))));
}
await navigateur.close();
