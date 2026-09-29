#!/usr/bin/env node
/**
 * Écrit une page par fiche et par langue dans dist/ — /fiche/<id>/, /en/fiche/<id>/,
 * /he/fiche/<id>/ — et le plan de site qui les liste.
 *
 *     node site/fiches.mjs dist
 *
 * La fiche est celle que la visite ouvre : mêmes contenus, mêmes textes d'interface,
 * mêmes liens Sefaria (visite/sefaria.js). L'image est la vue que « Voir dans la
 * visite » ouvre, capturée par site/images_fiches.mjs.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { lienSefaria } from "../visite/sefaria.js";

const SITE = dirname(fileURLToPath(import.meta.url));
const VISITE = join(SITE, "..", "visite");
const DOMAINE = "https://bethhamikdach.com";
const LANGUE_SOURCE = "fr";
const FICHIERS_CONTENU = ["a", "b", "c"];
const DESCRIPTION_MAX = 160;

const PAGES = {
  fr: { chemin: "", voir: "Voir dans la visite", accueil: "Accueil", langue: "Langue" },
  en: { chemin: "en/", voir: "See it in the tour", accueil: "Home", langue: "Language" },
  he: { chemin: "he/", voir: "לראות בסיור", accueil: "דף הבית", langue: "שפה" },
};

const lire = (fichier) => JSON.parse(readFileSync(join(VISITE, fichier), "utf8"));
const echappe = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const cheminDeFiche = (code, id) => `/${PAGES[code].chemin}fiche/${id}/`;

function contenusEn(code) {
  const suffixe = code === LANGUE_SOURCE ? "" : `.${code}`;
  return FICHIERS_CONTENU.map((f) => lire(`contenu_${f}${suffixe}.json`));
}

const apport = (contenus, id) => contenus.find((x) => x[id])?.[id] ?? {};

function fichesEn(code, concepts, source) {
  const traduits = code === LANGUE_SOURCE ? [] : contenusEn(code);
  return concepts.filter((c) => apport(source, c.id).resume)
    .map((c) => ({ ...c, ...apport(source, c.id), ...apport(traduits, c.id) }));
}

function resumeCourt(resume) {
  if (resume.length <= DESCRIPTION_MAX) return resume;
  const coupe = resume.slice(0, DESCRIPTION_MAX - 1);
  return `${coupe.slice(0, coupe.lastIndexOf(" "))}…`;
}

function alternances(id) {
  const liens = Object.keys(PAGES).map((code) =>
    `<link rel="alternate" hreflang="${code}" href="${DOMAINE}${cheminDeFiche(code, id)}">`);
  liens.push(`<link rel="alternate" hreflang="x-default" href="${DOMAINE}${cheminDeFiche(LANGUE_SOURCE, id)}">`);
  return liens.join("\n");
}

function navLangues(code, id, textes) {
  return Object.keys(PAGES).map((autre) => {
    const courant = autre === code ? ' aria-current="page"' : "";
    return `<a href="${cheminDeFiche(autre, id)}" lang="${autre}" dir="${textes[autre].sens}"${courant}>${echappe(textes[autre].nom)}</a>`;
  }).join("\n      ");
}

function sources(fiche, t) {
  return (fiche.sources ?? []).map((s) => {
    const lien = lienSefaria(s.oeuvre, s.ref);
    const tete = `${echappe(t.oeuvres?.[s.oeuvre] ?? s.oeuvre)} <bdi>${echappe(s.ref)}</bdi>`;
    const citation = t.interface.guillemet_ouvrant + s.citation + t.interface.guillemet_fermant;
    return `<li>${lien ? `<a href="${lien}" rel="noopener">${tete}</a>` : tete}${s.citation ? `<em>${echappe(citation)}</em>` : ""}</li>`;
  }).join("\n        ");
}

function page(code, fiche, image, textes) {
  const t = textes[code];
  const p = PAGES[code];
  const url = `${DOMAINE}${cheminDeFiche(code, fiche.id)}`;
  const description = resumeCourt(fiche.resume);
  const titre = `${fiche.nom} · Beit HaMikdach`;
  // En hébreu le titre est déjà le nom hébreu, comme dans la fiche de la visite.
  const nomSeul = code === "he";
  const cotes = fiche.cotes?.length
    ? `\n      <h2>${echappe(t.interface.cotes)}</h2>\n      <ul class="cotes">${fiche.cotes.map((x) => `<li>${echappe(x)}</li>`).join("")}</ul>` : "";
  const liste = sources(fiche, t);
  return `<!doctype html>
<html lang="${code}" dir="${t.sens}">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#100e0b">
<title>${echappe(titre)}</title>
<meta name="description" content="${echappe(description)}">
<link rel="canonical" href="${url}">
${alternances(fiche.id)}
<meta property="og:type" content="article">
<meta property="og:site_name" content="Beit HaMikdach">
<meta property="og:title" content="${echappe(fiche.nom)}">
<meta property="og:description" content="${echappe(description)}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${DOMAINE}${image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Serif+4:ital,opsz,wght@0,8..60,300..600;1,8..60,300..600&family=Frank+Ruhl+Libre:wght@300;400;500&display=swap">
<link rel="stylesheet" href="/style.css">
<link rel="stylesheet" href="/fiche.css">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">

<main class="fiche">
  <div class="barre">
    <a class="maison" href="/${p.chemin}"><bdi lang="he" dir="rtl">בית המקדש</bdi> · <bdi dir="ltr">Beit HaMikdach</bdi></a>
    <nav aria-label="${echappe(p.langue)}">
      ${navLangues(code, fiche.id, textes)}
    </nav>
  </div>
  <article>
    <p class="zone">${echappe(t.zones[fiche.zone] ?? fiche.zone)}</p>
    <h1>${echappe(fiche.nom)}</h1>${fiche.he && !nomSeul ? `\n    <p class="nom-he" lang="he" dir="rtl">${echappe(fiche.he)}</p>` : ""}${fiche.translit && !nomSeul ? `\n    <p class="translit">${echappe(fiche.translit)}</p>` : ""}
    <figure class="vue">
      <a href="/visite/?vue=${fiche.id}&amp;lang=${code}"><img src="${image}" width="1200" height="630" alt="" fetchpriority="high"></a>
    </figure>
    <p class="action"><a class="entrer" href="/visite/?vue=${fiche.id}&amp;lang=${code}">${echappe(p.voir)}</a></p>
    <div class="texte">
      <p class="resume">${echappe(fiche.resume)}</p>${cotes}${liste ? `\n      <h2>${echappe(t.interface.sources)}</h2>\n      <ul class="sources">\n        ${liste}\n      </ul>` : ""}${fiche.note ? `\n      <p class="note"><b>${echappe(t.interface.arbitrage)}</b>${echappe(fiche.note)}</p>` : ""}
    </div>
  </article>
</main>

<script src="/audience.js" defer></script>
</html>
`;
}

function planDuSite(ids) {
  const urls = ids.flatMap((id) => Object.keys(PAGES).map((code) => {
    const autres = Object.keys(PAGES).map((autre) =>
      `\n    <xhtml:link rel="alternate" hreflang="${autre}" href="${DOMAINE}${cheminDeFiche(autre, id)}"/>`).join("");
    return `  <url><loc>${DOMAINE}${cheminDeFiche(code, id)}</loc>${autres}\n  </url>`;
  }));
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
${urls.join("\n")}
</urlset>
`;
}

// Une fiche dont la vue n'est pas encore capturée garde l'image de partage du site.
function imageDe(id) {
  const image = `/images/fiches/${id}.jpg`;
  if (existsSync(join(SITE, image))) return image;
  console.warn(`sans image : ${id}`);
  return "/images/partage.jpg";
}

const [dist] = process.argv.slice(2);
if (!dist) {
  console.error("usage : node site/fiches.mjs <dist>");
  process.exit(2);
}
const textes = lire("textes.json");
const { concepts } = lire("concepts.json");
const source = contenusEn(LANGUE_SOURCE);
const ids = fichesEn(LANGUE_SOURCE, concepts, source).map((f) => f.id);
const images = new Map(ids.map((id) => [id, imageDe(id)]));
for (const code of Object.keys(PAGES)) {
  for (const fiche of fichesEn(code, concepts, source)) {
    const dossier = join(dist, cheminDeFiche(code, fiche.id));
    mkdirSync(dossier, { recursive: true });
    writeFileSync(join(dossier, "index.html"), page(code, fiche, images.get(fiche.id), textes));
  }
}
writeFileSync(join(dist, "sitemap-fiches.xml"), planDuSite(ids));
console.log(`${ids.length} fiches × ${Object.keys(PAGES).length} langues dans ${dist}`);
