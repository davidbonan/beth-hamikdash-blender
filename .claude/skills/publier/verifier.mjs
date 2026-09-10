import { readdirSync, existsSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'

const url = process.argv[2]
const capture = process.argv[3] ?? 'visite.png'
if (!url) {
  console.error('usage: node verifier.mjs <url> [capture.png]   (playwright-core installé dans le dossier courant)')
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
const page = await navigateur.newPage({ viewport: { width: 1280, height: 800 } })
// Sans langue retenue, l'écran du choix de langue recouvrirait la capture.
// Même raison pour la carte de l'initiation, posée sur le haut de l'image.
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
async function capturer(chemin) {
  const cdp = await page.context().newCDPSession(page)
  const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' })
  writeFileSync(chemin, Buffer.from(data, 'base64'))
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
await navigateur.close()
process.exit(code)
