// node mode_emploi.mjs <url de la visite> <dossier visite/>
// Les deux captures que l'écran de chargement annote ; imprime chaque repère en % de l'image, à reporter dans visite/index.html.
import { readdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";

const [url, dossier] = process.argv.slice(2);
if (!url || !dossier) {
  console.error("usage: node mode_emploi.mjs <url de la visite> <dossier visite/>   (playwright-core installé dans le dossier courant)");
  process.exit(2);
}

const { chromium } = createRequire(`${process.cwd()}/`)("playwright-core");
const cache = `${process.env.HOME}/Library/Caches/ms-playwright`;
const version = readdirSync(cache).filter((d) => d.startsWith("chromium-")).sort((a, b) => a.localeCompare(b, "en", { numeric: true })).pop();
const mac = `${cache}/${version}/chrome-mac-arm64`;
const app = readdirSync(mac).find((d) => d.endsWith(".app"));
const binaire = `${mac}/${app}/Contents/MacOS/${readdirSync(`${mac}/${app}/Contents/MacOS`)[0]}`;
const navigateur = await chromium.launch({
  executablePath: process.env.CHROME ?? binaire, args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"],
});

// La Menora depuis l'entrée du Heikhal, au bureau puis au téléphone : relevée à l'œil, à refaire si le cadrage de `heikhal` bouge.
const MENORA = { x: 370, y: 380 };
const MENORA_AU_DOIGT = { x: 65, y: 405 };

const MODES = {
  clavier: {
    ecran: { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 },
    agir: (page) => page.mouse.click(MENORA.x, MENORA.y),
    reperes: { menora: MENORA, fiche: "#fiche h2", parcours: "#parcours-choix", vol: "#vol", marcher: { x: 470, y: 660 } },
  },
  doigt: {
    ecran: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true },
    agir: () => {},
    reperes: { marcher: "#manche", regarder: { x: 300, y: 560 }, toucher: MENORA_AU_DOIGT, parcours: "#parcours-choix", plan: "#minicarte svg" },
  },
};

const positions = {};
for (const [mode, { ecran, agir, reperes }] of Object.entries(MODES)) {
  const page = await navigateur.newPage(ecran);
  await page.addInitScript(() => {
    localStorage.setItem("visite.langue", "fr");
    localStorage.setItem("visite.initiation", "suivie");
  });
  page.on("pageerror", (e) => console.log("[erreur]", String(e).slice(0, 300)));
  await page.goto(url, { waitUntil: "load", timeout: 90000 });
  await page.waitForFunction(() => window.__pret === true, null, { timeout: 180000 });
  await page.evaluate(() => window.__vue("heikhal"));
  await page.waitForFunction(() => !document.querySelector("#voile.noir, #voile.attente"), null, { timeout: 60000 });
  // Le rappel des commandes dirait deux fois ce que les repères disent.
  await page.evaluate(() => document.querySelector("#aide").classList.add("parti"));
  await page.waitForTimeout(2500);
  await agir(page);
  await page.waitForTimeout(1500);
  const { width, height } = ecran.viewport;
  positions[mode] = {};
  for (const [nom, cible] of Object.entries(reperes)) {
    const point = typeof cible === "string"
      ? await page.$eval(cible, (e) => { const r = e.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })
      : cible;
    positions[mode][nom] = `--x: ${(100 * point.x / width).toFixed(1)}%; --y: ${(100 * point.y / height).toFixed(1)}%`;
  }
  const cdp = await page.context().newCDPSession(page);
  const { data } = await cdp.send("Page.captureScreenshot", { format: "webp", quality: 80 });
  writeFileSync(`${dossier}/mode_emploi_${mode}.webp`, Buffer.from(data, "base64"));
  await page.close();
}
await navigateur.close();
console.log(JSON.stringify(positions, null, 2));
