import { readdirSync, existsSync, writeFileSync, mkdirSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve } from 'node:path'

const options = process.argv.slice(2)
const drapeau = (nom) => {
  const i = options.indexOf(nom)
  return i < 0 ? null : options.splice(i, 2)[1] ?? ''
}
const mobile = options.includes('--mobile') && options.splice(options.indexOf('--mobile'), 1)
const planche = drapeau('--planche')
const parcours = drapeau('--parcours')
const seulement = drapeau('--seulement')?.split(',')
const [url, capture = 'visite.png'] = options
if (!url) {
  console.error('usage: node verifier.mjs <url> [capture.png] [--mobile] [--planche <dossier>] [--parcours <dossier>] [--seulement id,id]   (playwright-core installé dans le dossier courant)')
  process.exit(2)
}

// playwright-core s'installe dans un dossier jetable : le résoudre depuis là, pas depuis le skill.
const requis = createRequire(`${process.cwd()}/`)
const { chromium } = requis('playwright-core')

function trouverChrome() {
  if (process.env.CHROME) return process.env.CHROME
  const cache = `${process.env.HOME}/Library/Caches/ms-playwright`
  const versions = existsSync(cache)
    ? readdirSync(cache).filter((d) => d.startsWith('chromium-')).sort((a, b) => a.localeCompare(b, 'en', { numeric: true }))
    : []
  for (const version of versions.reverse()) {
    const mac = `${cache}/${version}/chrome-mac-arm64`
    const app = existsSync(mac) && readdirSync(mac).find((d) => d.endsWith('.app'))
    if (!app) continue
    const macos = `${mac}/${app}/Contents/MacOS`
    const binaire = readdirSync(macos)[0]
    if (binaire) return `${macos}/${binaire}`
  }
  throw new Error(`aucun Chromium sous ${cache} — poser CHROME=<binaire>`)
}

const navigateur = await chromium.launch({
  executablePath: trouverChrome(),
  args: ['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader'],
})
const page = await navigateur.newPage(mobile
  ? { viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true }
  : { viewport: { width: 1280, height: 800 } })
// Sans langue retenue, l'écran du choix de langue recouvrirait la capture.
// Même raison pour la carte de l'initiation.
await page.addInitScript(() => {
  localStorage.setItem('visite.langue', 'fr')
  localStorage.setItem('visite.initiation', 'suivie')
})
const bruit = /GL Driver Message|GPU stall/
page.on('console', (m) => bruit.test(m.text()) || console.log('[console]', m.type(), m.text().slice(0, 200)))
page.on('pageerror', (e) => console.log('[erreur]', String(e).slice(0, 300)))
page.on('requestfailed', (r) => console.log('[echec]', r.url().slice(0, 120), r.failure()?.errorText))

// La capture passe par CDP et non par `page.screenshot` : celle-ci attend une image
// stable, et une scène qui rend en continu — quelques images par seconde sous
// SwiftShader — ne lui en donne jamais. Elle expirait à trente secondes sur une page
// pourtant prête, et emportait le code de sortie avec elle.
async function capturer(chemin, cible = page, format = { format: 'png' }) {
  const cdp = await cible.context().newCDPSession(cible)
  const { data } = await cdp.send('Page.captureScreenshot', format)
  writeFileSync(chemin, Buffer.from(data, 'base64'))
}

// La barre ne relit le lieu que toutes les quatre images : sans attente, la vignette porte le nom de la vue précédente.
const laisserRendre = () => page.evaluate(() => new Promise((fin) => {
  let images = 8
  const suivante = () => (--images ? requestAnimationFrame(suivante) : fin())
  requestAnimationFrame(suivante)
}))

// Une vignette par entrée et par vue, puis la mosaïque, comme la planche du film.
async function tirerPlanche(dossier) {
  mkdirSync(dossier, { recursive: true })
  const ids = await page.evaluate(() => window.__vues())
  for (const id of ids.filter((v) => !seulement || seulement.includes(v))) {
    await page.evaluate((v) => window.__vue(v), id)
    await laisserRendre()
    const etat = await page.evaluate(() => window.__etat())
    await capturer(`${dossier}/${id}.png`)
    console.log('vue', id, JSON.stringify(etat))
  }
  const html = `<!doctype html><meta charset="utf-8"><style>
    body{margin:0;padding:12px;background:#0d0c0b;color:#e8e0d0;font:13px Georgia,serif;display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
    figure{margin:0}img{width:100%;display:block}figcaption{padding:4px 0}</style>
    ${ids.map((id) => `<figure><img src="${id}.png"><figcaption>${id}</figcaption></figure>`).join('')}`
  const index = resolve(dossier, 'planche.html')
  writeFileSync(index, html)
  const mosaique = await navigateur.newPage({ viewport: { width: 1600, height: 900 } })
  await mosaique.goto(`file://${index}`)
  await mosaique.waitForFunction(() => [...document.images].every((i) => i.complete))
  const hauteur = await mosaique.evaluate(() => document.documentElement.scrollHeight)
  await mosaique.setViewportSize({ width: 1600, height: hauteur })
  await capturer(resolve(dossier, 'planche.jpg'), mosaique, { format: 'jpeg', quality: 82 })
  console.log('planche', index)
}

// Les parcours guidés, station par station : une capture à chaque arrêt, et la marche
// vers la suivante avancée à la main, sans attendre les images. Un pas qui perd le sol
// — un point de passage à côté d'un escalier — se voit à l'arrivée : l'œil n'est plus à
// la hauteur du dallage que la station déclare. Un pas qui traverse un mur, ou le frôle
// à moins d'un tiers de mètre — la caméra coupe à 0,12 m —, se voit pas à pas, au rayon.
const DEGAGEMENT = 0.3
async function suivreParcours(dossier) {
  await page.evaluate(() => window.__figurants)
  let fautes = 0
  for (const id of (await page.evaluate(() => window.__parcours.liste())).filter((p) => !seulement || seulement.includes(p))) {
    mkdirSync(`${dossier}/${id}`, { recursive: true })
    const n = await page.evaluate((id) => { window.__parcours.ouvrir(id); return window.__parcours.nombre() }, id)
    console.log('parcours', id, n, 'stations')
    for (let i = 0; i < n; i++) {
      await page.evaluate((i) => window.__parcours.aller(i), i)
      await page.waitForTimeout(500)
      await page.evaluate((t) => window.__temps(t), 3 + i)
      await laisserRendre()
      await capturer(`${dossier}/${id}/station_${i}.png`)
      const carte = await page.evaluate(() => ({
        titre: document.querySelector('#parcours h2').textContent, fiche: document.querySelector('#fiche h2')?.textContent,
        ouverte: document.querySelector('#fiche').classList.contains('ouverte') }))
      console.log('station', i, JSON.stringify(carte))
      if (i + 1 === n) break
      const marche = await page.evaluate((DEGAGEMENT) => {
        document.querySelector('#parcours .suivant').click()
        const trajet = window.__parcours.trajet()
        const autour = []
        for (let k = 0; k < 16; k++) autour.push([Math.cos(k * Math.PI / 8), 0, Math.sin(k * Math.PI / 8)])
        let pas = 0, dernier = null, sauts = 0, traverse = null, serre = null
        while (window.__parcours.trajet() && pas++ < 5000) {
          trajet.avancer(1 / 30)
          const { x, y, z } = window.__etat()
          if (dernier !== null) {
            if (Math.abs(y - dernier.y) > 0.3) sauts++
            const segment = [x - dernier.x, y - dernier.y, z - dernier.z]
            const longueur = Math.hypot(...segment)
            const mur = longueur > 1e-4 && window.__mur([dernier.x, dernier.y, dernier.z], segment, longueur)
            if (mur && !traverse) traverse = { concept: mur.concept, amot: [+(x / 0.48).toFixed(1), +(z / 0.48).toFixed(1)] }
          }
          for (const direction of autour) {
            const mur = window.__mur([x, y, z], direction, DEGAGEMENT)
            if (mur && (!serre || mur.distance < serre.distance)) {
              serre = { distance: +mur.distance.toFixed(2), concept: mur.concept, amot: [+(x / 0.48).toFixed(1), +(z / 0.48).toFixed(1)] }
            }
          }
          dernier = { x, y, z }
        }
        return { pas, sauts, ecart: +window.__parcours.ecartSol().toFixed(2), traverse, serre }
      }, DEGAGEMENT)
      // La même marche à grands pas — une image de 0,1 s à l'allure ×4 — : l'escalier doit se gravir quand même.
      // Le retour à la station passe par le fondu : on lui laisse le temps de poser la caméra.
      await page.evaluate((i) => window.__parcours.aller(i), i)
      await page.waitForTimeout(300)
      marche.ecartVite = await page.evaluate(() => {
        document.querySelector('#parcours .suivant').click()
        const trajet = window.__parcours.trajet()
        let pas = 0
        while (window.__parcours.trajet() && pas++ < 5000) trajet.avancer(0.4)
        return +window.__parcours.ecartSol().toFixed(2)
      })
      const faute = marche.sauts || Math.abs(marche.ecart) > 0.3 || Math.abs(marche.ecartVite) > 0.3 || marche.traverse || marche.serre
      fautes += faute ? 1 : 0
      console.log(`marche ${i} -> ${i + 1}`, JSON.stringify(marche),
        marche.traverse ? 'MUR TRAVERSE' : marche.serre ? 'MUR FROLE' : faute ? 'SOL PERDU' : 'ok')
    }
  }
  return fautes
}

let code = 0
await page.goto(url, { waitUntil: 'load', timeout: 60000 })
try {
  await page.waitForFunction(
    () => document.querySelector('#chargement')?.classList.contains('parti'),
    null,
    { timeout: 90000 }
  )
  console.log('scene prete')
  console.log('etat', JSON.stringify(await page.evaluate(() => window.__etat())))
} catch {
  code = 1
  console.log('BLOQUE :', (await page.textContent('#chargement').catch(() => '?')).trim())
}
await capturer(capture)
console.log('capture', capture)
if (planche !== null && code === 0) await tirerPlanche(planche || 'planche')
if (parcours !== null && code === 0 && await suivreParcours(parcours || 'parcours')) code = 1
await navigateur.close()
process.exit(code)
