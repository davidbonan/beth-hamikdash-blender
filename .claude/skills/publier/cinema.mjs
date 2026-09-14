// node cinema_film.mjs <url> <dossier> <largeur>x<hauteur> <echelle> [--affiche t1,t2 | --film [fin_s]]
// Rend le parcours image par image (24/s) sous Metal, ou seulement des affiches aux temps donnés.
import { mkdirSync, writeFileSync, readdirSync } from "node:fs";
import { chromium } from "playwright-core";

const [url, dossier, taille, echelle] = process.argv.slice(2);
const affiche = process.argv.indexOf("--affiche");
const film = process.argv.indexOf("--film");
const [largeur, hauteur] = taille.split("x").map(Number);
mkdirSync(dossier, { recursive: true });

const cache = `${process.env.HOME}/Library/Caches/ms-playwright`;
const version = readdirSync(cache).filter((d) => d.startsWith("chromium-")).sort().pop();
const mac = `${cache}/${version}/chrome-mac-arm64`;
const app = readdirSync(mac).find((d) => d.endsWith(".app"));
const binaire = `${mac}/${app}/Contents/MacOS/${readdirSync(`${mac}/${app}/Contents/MacOS`)[0]}`;

const navigateur = await chromium.launch({
  executablePath: binaire, args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"],
});
const page = await navigateur.newPage({ viewport: { width: largeur, height: hauteur }, deviceScaleFactor: Number(echelle) });
page.on("pageerror", (e) => console.log("[erreur]", String(e).slice(0, 300)));
const cdp = await page.context().newCDPSession(page);
const capturer = async (chemin, format) => {
  const { data } = await cdp.send("Page.captureScreenshot", format);
  writeFileSync(chemin, Buffer.from(data, "base64"));
};

await page.goto(url, { waitUntil: "load", timeout: 90000 });
await page.waitForFunction(() => window.__pret === true, null, { timeout: 180000 });
await page.evaluate(() => window.__figurants);
await page.evaluate(() => window.__cinema.figer());
const duree = await page.evaluate(() => window.__cinema.duree);
console.log("prete, duree", duree);

const PAS = 1 / 24;
if (affiche > 0) {
  const voulus = process.argv[affiche + 1].split(",").map(Number).sort((a, b) => a - b);
  let t = 0;
  for (const cible of voulus) {
    while (t < cible - 1e-6) { await page.evaluate((dt) => window.__cinema.avancer(dt), PAS); t += PAS; }
    // Quelques images de plus sur place : les ombres et la lampe se posent.
    for (let i = 0; i < 6; i++) await page.evaluate(() => window.__rendre());
    await capturer(`${dossier}/affiche_${cible}.png`, { format: "png" });
    console.log("affiche", cible);
  }
} else {
  const fin = Number(process.argv[film + 1] || duree);
  const total = Math.round(fin / PAS);
  const debut = Date.now();
  for (let i = 0; i < total; i++) {
    await page.evaluate((dt) => window.__cinema.avancer(dt), PAS);
    await page.evaluate(() => window.__rendre());
    await capturer(`${dossier}/${String(i).padStart(5, "0")}.jpg`, { format: "jpeg", quality: 92 });
    if (i % 240 === 0) console.log(`${i}/${total} images, ${((Date.now() - debut) / 1000).toFixed(0)} s`);
  }
}
await navigateur.close();
