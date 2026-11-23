// Précalcule visite/visibilite.json : de chaque cellule où l'œil marche, les tuiles du Temple qu'aucun regard n'atteint.
import { readdirSync, existsSync, readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const options = process.argv.slice(2)
const drapeau = (nom) => {
  const i = options.indexOf(nom)
  return i < 0 ? null : options.splice(i, 2)[1] ?? ''
}
const verifier = drapeau('--verifier')
const sortie = resolve(drapeau('--sortie') ?? `${dirname(fileURLToPath(import.meta.url))}/../../../visite/visibilite.json`)
const [url] = options
if (!url) {
  console.error('usage: node visibilite.mjs <url de la visite> [--sortie visibilite.json] [--verifier <nombre d\'yeux>]   (playwright-core installé dans le dossier courant)')
  process.exit(2)
}

// playwright-core s'installe dans un dossier jetable : le résoudre depuis là, pas depuis le skill.
const { chromium } = createRequire(`${process.cwd()}/`)('playwright-core')

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

// Dans la page : les yeux d'où regarder, et ce que chacun voit. Rien d'ici n'y est visible, tout y est réimporté.
async function regarderDepuisLaPage({ verifier, cuite }) {
  const THREE = await import('three')
  const { CELLULE, celluleDe, empreinte, occulte } = await import('./visibilite.js')
  const { AMA, OEIL, HAUTEUR_LIBRE } = await import('./marche.js')
  const { renderer, scene, detail, temple } = window.__moteur
  const DIVISIONS = 4, PAS = CELLULE.cote / DIVISIONS
  // Sur une pente, les yeux voisins d'un marcheur sont à moins de cette hauteur du sien : ils comptent pour son étage.
  const DEBORD_D_ETAGE = 0.5
  const FACE = 1024, LARGEUR = 64
  const pause = () => new Promise((suite) => setTimeout(suite))

  window.__figer()
  // Jérusalem descend après le Temple : hors de l'enceinte, c'est sur elle qu'on marche.
  for (let avant = -1, stable = 0; stable < 4;) {
    await new Promise((suite) => setTimeout(suite, 2000))
    const nombre = detail.fixesSous(scene).length
    stable = nombre === avant ? stable + 1 : 0
    avant = nombre
  }
  detail.niveler(0)
  const occultantes = detail.fixesSous(temple).filter((tuile) => tuile.maille.visible && occulte(tuile))
  const parEmpreinte = new Map(occultantes.map((tuile) => [empreinte(tuile), tuile]))
  if (parEmpreinte.size < occultantes.length) throw new Error('deux tuiles de même empreinte : visibilite.js ne saurait plus les distinguer')
  // Les ouvriers de detail.js rendent leurs tuiles dans un ordre qui change d'une ouverture à l'autre : la vérification reprend celui du fichier.
  const empreintes = cuite ? cuite.tuiles : [...parEmpreinte.keys()]
  const tuiles = empreintes.map((cle) => parEmpreinte.get(cle))
  if (tuiles.length !== occultantes.length || tuiles.includes(undefined)) throw new Error('visibilite.json ne décrit plus ces tuiles : à recuire avant de vérifier')

  const HAUTEUR = Math.ceil((tuiles.length + 1) / LARGEUR)
  const rangs = new THREE.Scene()
  tuiles.forEach((tuile, rang) => {
    const maille = new THREE.Mesh(tuile.maille.geometry, new THREE.ShaderMaterial({
      side: tuile.source.material.side,
      uniforms: { uRang: { value: new THREE.Vector2((rang + 1) & 255, (rang + 1) >> 8).divideScalar(255) } },
      vertexShader: 'void main(){ gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: 'uniform vec2 uRang; void main(){ gl_FragColor = vec4(uRang, 0.0, 1.0); }',
    }))
    maille.matrixAutoUpdate = false
    maille.matrix.copy(tuile.maille.matrixWorld)
    rangs.add(maille)
  })
  const face = new THREE.WebGLRenderTarget(FACE, FACE, { minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter })
  const casier = new THREE.WebGLRenderTarget(LARGEUR, HAUTEUR, { depthBuffer: false })
  const pixels = new THREE.BufferGeometry()
  pixels.setAttribute('position', new THREE.BufferAttribute(new Float32Array(FACE * FACE), 1))
  // Chaque pixel de la face va marquer la case de la tuile qu'il montre : rapatrier les six faces coûtait le double.
  // Sans mélange : additionnés, un million de points sur la même case prenaient 230 ms par œil.
  const marques = new THREE.Points(pixels, new THREE.ShaderMaterial({
    uniforms: { tRangs: { value: face.texture } },
    vertexShader: `
      uniform sampler2D tRangs;
      void main(){
        vec4 c = texelFetch(tRangs, ivec2(gl_VertexID % ${FACE}, gl_VertexID / ${FACE}), 0);
        int rang = int(c.r * 255.0 + 0.5) + 256 * int(c.g * 255.0 + 0.5);
        gl_PointSize = 1.0;
        gl_Position = rang == 0 ? vec4(2.0, 2.0, 2.0, 1.0)
          : vec4((vec2(rang % ${LARGEUR}, rang / ${LARGEUR}) + 0.5) / vec2(${LARGEUR}.0, ${HAUTEUR}.0) * 2.0 - 1.0, 0.0, 1.0);
      }`,
    fragmentShader: 'void main(){ gl_FragColor = vec4(1.0); }',
    depthTest: false, depthWrite: false,
  }))
  marques.frustumCulled = false
  const marquage = new THREE.Scene().add(marques)
  const nulle = new THREE.Camera()
  // Le plan proche et le fond de l'œil de la visite ; un rien de plus que le quart de tour, pour que les faces se recouvrent.
  const regard = new THREE.PerspectiveCamera(92, 1, 0.12, 6000)
  const AXES = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]].map((axe) => new THREE.Vector3(...axe))
  const cible = new THREE.Vector3()
  renderer.autoClear = false
  renderer.setClearColor(0x000000, 0)

  function regarder(oeil, relever) {
    regard.position.copy(oeil)
    for (const axe of AXES) {
      regard.up.set(0, axe.y === 0 ? 1 : 0, axe.y === 0 ? 0 : 1)
      regard.lookAt(cible.copy(oeil).add(axe))
      renderer.setRenderTarget(face)
      renderer.clear()
      renderer.render(rangs, regard)
      relever()
    }
  }

  const cases = new Uint8Array(LARGEUR * HAUTEUR * 4)
  // Les tuiles vues de cet œil, tous regards confondus.
  function tuilesVues(oeil) {
    renderer.setRenderTarget(casier)
    renderer.clear()
    regarder(oeil, () => {
      renderer.setRenderTarget(casier)
      renderer.render(marquage, nulle)
    })
    renderer.readRenderTargetPixels(casier, 0, 0, LARGEUR, HAUTEUR, cases)
    return tuiles.map((_, rang) => cases[(rang + 1) * 4] > 0)
  }

  const rapatries = new Uint8Array(FACE * FACE * 4)
  // Le nombre de pixels où chaque tuile se voit : ce que pèse une tuile voilée à tort.
  function pixelsVus(oeil) {
    const nombres = new Uint32Array(tuiles.length + 1)
    regarder(oeil, () => {
      renderer.readRenderTargetPixels(face, 0, 0, FACE, FACE, rapatries)
      for (let i = 0; i < rapatries.length; i += 4) nombres[rapatries[i] + 256 * rapatries[i + 1]]++
    })
    return nombres.subarray(1)
  }

  // L'enceinte du Har HaBayit : au-delà, le décor se trace entier.
  const enceinte = new THREE.Box3()
  temple.traverse((o) => { if (o.isMesh && o.userData.concept === 'mur_har_habayit') enceinte.expandByObject(o) })
  const yeuxEn = (x, z) => window.__sols(x, z).filter(({ libre }) => libre >= HAUTEUR_LIBRE).map(({ y }) => new THREE.Vector3(x, y + OEIL, z))
  const CAPS = [[1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1]]
  // Le plan proche de l'œil, et un centimètre : plus près, il voit au travers du mur.
  const DEVANT_LE_MUR = 0.13
  const murVers = (oeil, cap, portee) => [oeil.y, oeil.y - OEIL + AMA + 0.04]
    .map((y) => window.__mur([oeil.x, y, oeil.z], cap, portee)?.distance ?? Infinity)
    .reduce((a, b) => Math.min(a, b))

  if (verifier) {
    const hasard = (min, max) => min + Math.random() * (max - min)
    const manques = []
    let yeux = 0, voilees = 0, auRasDUnMur = 0
    while (yeux < verifier) {
      for (const oeil of yeuxEn(hasard(enceinte.min.x, enceinte.max.x), hasard(enceinte.min.z, enceinte.max.z))) {
        const [bas, haut, bits] = cuite.cellules[celluleDe(oeil)] ?? []
        if (!bits || oeil.y < bas || oeil.y > haut) continue
        // Plus près d'un mur que le plan proche, l'œil voit au travers : ce qu'il y voit n'est pas ce que la cuisson promet.
        if (Array.from({ length: 16 }, (_, k) => [Math.cos(k * Math.PI / 8), 0, Math.sin(k * Math.PI / 8)]).some((cap) => murVers(oeil, cap, DEVANT_LE_MUR) < Infinity)) {
          auRasDUnMur++
          continue
        }
        const octets = atob(bits), vus = pixelsVus(oeil)
        yeux++
        tuiles.forEach((tuile, rang) => {
          if (!(octets.charCodeAt(rang >> 3) & (1 << (rang & 7)))) return
          voilees++
          if (vus[rang] > 0) manques.push({ oeil: oeil.toArray().map((c) => +c.toFixed(2)), tuile: tuile.source.userData.concept ?? tuile.source.name, pixels: vus[rang] })
        })
      }
      if (yeux % 50 === 0) await pause()
    }
    return { yeux, voilees, auRasDUnMur, manques }
  }

  const cellules = new Map()
  const debut = performance.now()
  // Un œil sur le bord d'une cellule compte pour ses deux voisines : aucune n'a de lisière qui ne soit regardée.
  const rangsDe = (metres) => {
    const rang = metres / CELLULE.cote, bord = Math.round(rang)
    return Math.abs(rang - bord) < 1e-6 ? [bord - 1, bord] : [Math.floor(rang)]
  }
  let yeux = 0
  function regarderDe(oeil) {
    const vues = tuilesVues(oeil)
    yeux++
    const etages = new Set([-DEBORD_D_ETAGE, DEBORD_D_ETAGE].map((debord) => Math.floor((oeil.y + debord) / CELLULE.etage)))
    for (const cx of rangsDe(oeil.x)) for (const cz of rangsDe(oeil.z)) for (const cy of etages) {
      const cle = `${cx},${cy},${cz}`
      const cellule = cellules.get(cle) ?? { bas: Infinity, haut: -Infinity, vues: new Uint8Array(tuiles.length) }
      cellules.set(cle, cellule)
      cellule.bas = Math.min(cellule.bas, oeil.y)
      cellule.haut = Math.max(cellule.haut, oeil.y)
      vues.forEach((vue, rang) => { if (vue) cellule.vues[rang] = 1 })
    }
  }

  // Jusqu'où l'œil s'avance vers son voisin de grille : un mur l'arrête devant lui, le vide au bord de son sol.
  function avancee(oeil, cap) {
    const mur = murVers(oeil, cap, PAS)
    if (mur < Infinity) return Math.max(0, mur - DEVANT_LE_MUR)
    const porte = (pas) => yeuxEn(oeil.x + cap[0] * pas, oeil.z + cap[2] * pas).some(({ y }) => Math.abs(y - oeil.y) < PAS)
    if (porte(PAS)) return PAS
    let sur = 0, hors = PAS
    for (let tour = 0; tour < 6; tour++) {
      const milieu = (sur + hors) / 2
      if (porte(milieu)) sur = milieu
      else hors = milieu
    }
    return sur
  }

  // La grille s'arrête jusqu'à un pas avant chaque mur, chaque parapet, chaque bord de toit : c'est de là, au ras, qu'on voit par-dessus.
  function yeuxAuRas(oeil) {
    const [est, ouest, sud, nord] = CAPS.map((cap) => avancee(oeil, cap))
    const ecarts = []
    for (const x of [est, -ouest]) if (Math.abs(x) < PAS) ecarts.push([x, 0])
    for (const z of [sud, -nord]) if (Math.abs(z) < PAS) ecarts.push([0, z])
    for (const x of [est, -ouest]) for (const z of [sud, -nord]) if (Math.abs(x) < PAS && Math.abs(z) < PAS) ecarts.push([x, z])
    return ecarts.filter(([x, z]) => Math.hypot(x, z) > 0.05).flatMap(([x, z]) => {
      const sol = window.__sol(oeil.x + x, oeil.z + z, oeil.y - OEIL)
      return sol === null ? [] : [new THREE.Vector3(oeil.x + x, sol + OEIL, oeil.z + z)]
    })
  }

  const colonnes = { de: Math.ceil(enceinte.min.x / PAS), a: Math.floor(enceinte.max.x / PAS) }
  const rangees = { de: Math.ceil(enceinte.min.z / PAS), a: Math.floor(enceinte.max.z / PAS) }
  for (let i = colonnes.de; i <= colonnes.a; i++) {
    for (let k = rangees.de; k <= rangees.a; k++) {
      for (const oeil of yeuxEn(i * PAS, k * PAS)) {
        regarderDe(oeil)
        yeuxAuRas(oeil).forEach(regarderDe)
      }
    }
    console.log(`colonne ${i - colonnes.de + 1}/${colonnes.a - colonnes.de + 1} — ${yeux} yeux, ${cellules.size} cellules, ${Math.round((performance.now() - debut) / 1000)} s`)
    await pause()
  }

  const cachees = (vues) => {
    const octets = new Uint8Array(Math.ceil(vues.length / 8))
    vues.forEach((vue, rang) => { if (!vue) octets[rang >> 3] |= 1 << (rang & 7) })
    return btoa(String.fromCharCode(...octets))
  }
  const centimetre = (metres) => Math.round(metres * 100) / 100
  return {
    tuiles: empreintes,
    cellules: Object.fromEntries([...cellules].map(([cle, { bas, haut, vues }]) => [cle, [centimetre(bas), centimetre(haut), cachees(vues)]])),
  }
}

const navigateur = await chromium.launch({ executablePath: trouverChrome(), args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist'] })
const page = await navigateur.newPage({ viewport: { width: 640, height: 360 } })
await page.addInitScript(() => {
  localStorage.setItem('visite.langue', 'fr')
  localStorage.setItem('visite.initiation', 'suivie')
})
page.on('console', (m) => m.type() === 'log' && console.log(m.text().slice(0, 200)))
page.on('pageerror', (e) => console.log('[erreur]', String(e).slice(0, 300)))
await page.goto(url)
await page.waitForFunction(() => window.__pret === true, null, { timeout: 240000 })

if (verifier) {
  const { yeux, voilees, auRasDUnMur, manques } = await page.evaluate(regarderDepuisLaPage, { verifier: Number(verifier), cuite: JSON.parse(readFileSync(sortie, 'utf8')) })
  console.log(`${yeux} yeux au hasard (${auRasDUnMur} écartés, au ras d'un mur), ${voilees} tuiles voilées, ${manques.length} vues à tort`)
  for (const { oeil, tuile, pixels } of manques.sort((a, b) => b.pixels - a.pixels).slice(0, 40)) console.log(`  ${tuile} — ${pixels} pixels de ${oeil.join(' ; ')}`)
} else {
  const cuite = await page.evaluate(regarderDepuisLaPage, {})
  writeFileSync(sortie, JSON.stringify(cuite))
  console.log(`${sortie} : ${cuite.tuiles.length} tuiles, ${Object.keys(cuite.cellules).length} cellules`)
}
await navigateur.close()
