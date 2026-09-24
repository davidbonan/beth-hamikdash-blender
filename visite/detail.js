// Le décor se rend par tuiles, chacune au niveau le plus léger dont l'écart tient sous un pixel : un téléphone ne peut pas trier dix millions de triangles par image.
import * as THREE from "three";

const ECART_PIXELS = 1;
// Sous un pixel et demi de rayon, une silhouette lointaine ne se lit plus : elle ne vaut pas son appel de dessin.
const RAYON_VISIBLE = 1.5;
// Assez de triangles pour qu'une tuile vaille son appel de dessin, assez de tuiles pour que le lointain s'allège.
const TRIANGLES_MIN = 16384;
const TUILES_MAX = 16;
const UVS = ["uv", "uv1", "uv2", "uv3"];
// Deux calculs de front : le téléphone a des cœurs de reste, pas le fil de la page.
const OUVRIERS = 2;

function copie(attribut) {
  const entrelace = attribut.isInterleavedBufferAttribute;
  return {
    tableau: (entrelace ? attribut.data.array : attribut.array).slice(),
    nombre: attribut.count,
    taille: attribut.itemSize,
    pas: entrelace ? attribut.data.stride : attribut.itemSize,
    decalage: entrelace ? attribut.offset : 0,
    normalise: attribut.normalized,
  };
}

// L'arbre de collision a trié l'index par voisinage : une tranche contiguë de triangles est un morceau d'un seul tenant.
function plages(geometrie) {
  const total = geometrie.index.count / 3;
  const nombre = Math.max(TRIANGLES_MIN, Math.ceil(total / TUILES_MAX));
  return Array.from({ length: Math.ceil(total / nombre) }, (_, i) =>
    ({ debut: i * nombre, nombre: Math.min(nombre, total - i * nombre) }));
}

function demande(maillage) {
  const { attributes, index } = maillage.geometry;
  return {
    positions: copie(attributes.position),
    normales: attributes.normal && copie(attributes.normal),
    uvs: UVS.filter((nom) => attributes[nom]).map((nom) => copie(attributes[nom])),
    index: index.array.slice(),
    tuiles: plages(maillage.geometry),
    metre: 1 / maillage.matrixWorld.getMaxScaleOnAxis(),
  };
}

function partage(source, index, sphere) {
  const geometrie = new THREE.BufferGeometry();
  for (const [nom, attribut] of Object.entries(source.attributes)) geometrie.setAttribute(nom, attribut);
  geometrie.setIndex(index);
  geometrie.boundingSphere = sphere;
  return geometrie;
}

// Une troupe d'un autre moment est cachée par son groupe, que la tuile, rangée ailleurs, ne voit pas.
function present(maillage) {
  for (let o = maillage.parent; o; o = o.parent) if (!o.visible) return false;
  return true;
}

export function niveauxDeDetail(scene, camera) {
  const groupe = new THREE.Group();
  // Les tuiles ne bougent pas : leur matrice est posée une fois, et three ne la recalcule plus à chaque image.
  groupe.updateMatrixWorld = () => {};
  scene.add(groupe);
  const tuiles = [];
  const file = [];
  let ouvriers = null;

  // La tuile lit sur son maillage ce que la visite y règle : sa matière, et ses ombres la nuit.
  function tuileDe(maillage, geometrie) {
    const tuile = maillage.isSkinnedMesh
      ? new THREE.SkinnedMesh(geometrie, maillage.material)
      : new THREE.Mesh(geometrie, maillage.material);
    tuile.matrixWorld.copy(maillage.matrixWorld);
    if (maillage.isSkinnedMesh) {
      tuile.bind(maillage.skeleton, maillage.bindMatrix);
      tuile.bindMatrixInverse.copy(maillage.bindMatrixInverse);
      tuile.boundingSphere = maillage.boundingSphere;
    }
    for (const cle of ["material", "castShadow", "receiveShadow"]) Object.defineProperty(tuile, cle, { get: () => maillage[cle] });
    groupe.add(tuile);
    return tuile;
  }

  function installer(maillage, { allege, tuiles: calculees }) {
    const source = maillage.geometry;
    const index = new THREE.BufferAttribute(allege, 1);
    const echelle = maillage.matrixWorld.getMaxScaleOnAxis();
    for (const { centre, rayon, debut, nombre, niveaux } of calculees) {
      const sphere = new THREE.Sphere(new THREE.Vector3(...centre), rayon);
      const pleine = partage(source, source.index, sphere);
      pleine.setDrawRange(debut * 3, nombre * 3);
      tuiles.push({
        source: maillage, maille: tuileDe(maillage, pleine), pleine, allegee: partage(source, index, sphere),
        centre: sphere.center.clone().applyMatrix4(maillage.matrixWorld), rayon: rayon * echelle,
        niveaux: [{ ecart: 0, nombre: nombre * 3 }, ...niveaux],
      });
    }
    maillage.visible = false;
  }

  function envoyer() {
    if (file.length === 0) return;
    ouvriers ??= Array.from({ length: OUVRIERS }, demarrer);
    for (const ouvrier of ouvriers) {
      if (ouvrier.maillage || file.length === 0) continue;
      ouvrier.maillage = file.shift();
      ouvrier.calcul.postMessage(demande(ouvrier.maillage));
    }
  }

  function demarrer() {
    const ouvrier = { calcul: new Worker(new URL("./simplification.js", import.meta.url), { type: "module" }), maillage: null };
    ouvrier.calcul.onmessage = ({ data }) => {
      installer(ouvrier.maillage, data);
      ouvrier.maillage = null;
      envoyer();
    };
    return ouvrier;
  }

  const oeil = new THREE.Vector3();
  return {
    // Les plus lourds d'abord : ce sont eux qui font ramer.
    confier(maillages) {
      file.push(...maillages.filter((m) => m.visible && m.geometry.index));
      file.sort((a, b) => b.geometry.index.count - a.geometry.index.count);
      envoyer();
    },
    choisir(hauteurImage) {
      const focale = hauteurImage / 2 / Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
      camera.getWorldPosition(oeil);
      for (const t of tuiles) {
        const distance = Math.max(oeil.distanceTo(t.centre) - t.rayon, 1e-3);
        const admis = ECART_PIXELS * distance / focale;
        let n = 0;
        while (n + 1 < t.niveaux.length && t.niveaux[n + 1].ecart <= admis) n++;
        const niveau = t.niveaux[n];
        t.maille.visible = niveau.nombre > 0 && t.rayon * focale / distance >= RAYON_VISIBLE && present(t.source);
        t.maille.geometry = n === 0 ? t.pleine : t.allegee;
        if (n > 0) t.allegee.setDrawRange(niveau.debut, niveau.nombre);
      }
    },
  };
}
