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
const seulement = drapeau('--seulement')?.split(',')
const [url, capture = 'visite.png'] = options
if (!url) {
  console.error('usage: node verifier.mjs <url> [capture.png] [--mobile] [--planche <dossier> [--seulement id,id]]   (playwright-core installé dans le dossier courant)')
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
await navigateur.close()
process.exit(code)
