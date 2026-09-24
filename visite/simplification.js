// Les niveaux allégés de chaque tuile d'un maillage, hors du fil de la page : `detail.js` en choisit un par image.
import { MeshoptSimplifier } from "https://cdn.jsdelivr.net/npm/meshoptimizer@1.2.0/meshopt_simplifier.js";

const PALIERS = [0.01, 0.04, 0.16, 0.64, 2.56, 10.24];
// Un niveau qui garde plus de 80 % du précédent ne vaut pas sa place en mémoire.
const GAIN = 0.8;
const PROTEGE = 2;
// Ce que coûte une normale qui tourne, en mètres par unité : sans lui l'or des arêtes repliées changeait d'éclat.
const POIDS_NORMALE = 0.1;

function lire({ tableau, nombre, taille, pas, decalage, normalise }) {
  const signe = tableau instanceof Int8Array || tableau instanceof Int16Array || tableau instanceof Int32Array;
  const echelle = normalise ? 2 ** (tableau.BYTES_PER_ELEMENT * 8 - (signe ? 1 : 0)) - 1 : 1;
  const sortie = new Float32Array(nombre * taille);
  for (let i = 0; i < nombre; i++) {
    for (let c = 0; c < taille; c++) sortie[i * taille + c] = tableau[i * pas + decalage + c] / echelle;
  }
  return sortie;
}

// La lumière cuite est rangée en îlots : un triangle qui enjamberait une couture d'UV irait la lire ailleurs.
function coutures(positions, uvs) {
  const n = positions.length / 3;
  const verrous = new Uint8Array(n);
  if (uvs.length === 0) return verrous;
  const jumeau = MeshoptSimplifier.generatePositionRemap(positions, 3);
  const decousu = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    const j = jumeau[i];
    if (j !== i && uvs.some((uv) => uv[i * 2] !== uv[j * 2] || uv[i * 2 + 1] !== uv[j * 2 + 1])) decousu[j] = 1;
  }
  for (let i = 0; i < n; i++) if (decousu[jumeau[i]]) verrous[i] = PROTEGE;
  return verrous;
}

function sphere(positions, indices) {
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  for (const s of indices) {
    for (let c = 0; c < 3; c++) {
      min[c] = Math.min(min[c], positions[s * 3 + c]);
      max[c] = Math.max(max[c], positions[s * 3 + c]);
    }
  }
  const centre = min.map((m, c) => (m + max[c]) / 2);
  let rayon = 0;
  for (const s of indices) {
    rayon = Math.max(rayon, Math.hypot(positions[s * 3] - centre[0], positions[s * 3 + 1] - centre[1], positions[s * 3 + 2] - centre[2]));
  }
  return { centre, rayon };
}

// Bord verrouillé : la tuile voisine, à un autre niveau, le partage sommet pour sommet, sans fente.
function niveaux(tuile, { positions, normales, verrous }, metre) {
  const poids = Array(3).fill(POIDS_NORMALE * metre);
  const suite = [];
  let courant = tuile, ecart = 0;
  for (const palier of PALIERS) {
    const [allege, obtenu] = MeshoptSimplifier.simplifyWithAttributes(courant, positions, 3, normales, 3, poids,
      verrous, 0, palier * metre - ecart, ["ErrorAbsolute", "Permissive", "LockBorder"]);
    if (allege.length > courant.length * GAIN) continue;
    ecart += obtenu;
    suite.push({ indices: allege, ecart: ecart / metre });
    courant = allege;
    if (allege.length === 0) break;
  }
  return suite;
}

onmessage = async ({ data: { positions, normales, uvs, index, tuiles, metre } }) => {
  await MeshoptSimplifier.ready;
  const sommets = lire(positions);
  const maillage = {
    positions: sommets,
    normales: normales ? lire(normales) : new Float32Array(sommets.length),
    verrous: coutures(sommets, uvs.map(lire)),
  };
  const index32 = Uint32Array.from(index);
  const calculees = tuiles.map(({ debut, nombre }) => {
    const plage = index32.subarray(debut * 3, (debut + nombre) * 3);
    return { ...sphere(sommets, plage), debut, nombre, niveaux: niveaux(plage, maillage, metre) };
  });
  const total = calculees.reduce((n, t) => n + t.niveaux.reduce((m, v) => m + v.indices.length, 0), 0);
  const allege = sommets.length / 3 > 0xffff ? new Uint32Array(total) : new Uint16Array(total);
  let curseur = 0;
  const reponse = calculees.map(({ niveaux: suite, ...tuile }) => ({
    ...tuile,
    niveaux: suite.map(({ indices, ecart }) => {
      allege.set(indices, curseur);
      curseur += indices.length;
      return { debut: curseur - indices.length, nombre: indices.length, ecart };
    }),
  }));
  postMessage({ allege, tuiles: reponse }, [allege.buffer]);
};
