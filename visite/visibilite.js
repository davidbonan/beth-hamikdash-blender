// D'où l'œil marche, les tuiles du Temple qu'aucun regard n'atteint ne se tracent pas : leur liste est précalculée par cellule dans visibilite.json.
import { json } from "./encyclopedie.js";

// En mètres : le côté d'une cellule au sol, et la hauteur de son étage.
export const CELLULE = { cote: 3.84, etage: 2 };
// Ce dont l'œil peut s'écarter des hauteurs d'où sa cellule a été regardée.
const ECART_DE_L_OEIL = 0.3;

export const celluleDe = ({ x, y, z }) => [x / CELLULE.cote, y / CELLULE.etage, z / CELLULE.cote].map(Math.floor).join(",");

const centimetres = (metres) => Math.round(metres * 100);
// Les maillages du .glb n'ont pas de nom unique : une tuile se reconnaît à sa géométrie.
export const empreinte = (tuile) =>
  [tuile.niveaux[0].nombre, ...tuile.centre.toArray().map(centimetres), centimetres(tuile.rayon)].join(":");

// Ce qu'on voit au travers ne cache rien.
export const occulte = ({ source: { material } }) => !material.transparent && !material.alphaTest && material.depthWrite;

// Une seule tuile cuite absente, changée ou devenue transparente, et ce qu'elle cachait se verrait : rien ne se voile.
function tuilesCuites(empreintes, fixes) {
  const parEmpreinte = new Map(fixes.map((tuile) => [empreinte(tuile), tuile]));
  const tuiles = empreintes.map((cuite) => parEmpreinte.get(cuite));
  return tuiles.every((tuile) => tuile && occulte(tuile)) ? tuiles : null;
}

function cacheesDe(bits, tuiles) {
  const octets = atob(bits);
  return tuiles.filter((_, rang) => octets.charCodeAt(rang >> 3) & (1 << (rang & 7)));
}

export async function voilerLInvisible({ renderer, scene, camera, marche, detail, temple }) {
  const cuite = await json("./visibilite.json", false);
  const tuiles = cuite && tuilesCuites(cuite.tuiles, detail.fixesSous(temple));
  if (!tuiles) return;

  let occupee = null, cellule = null;
  function celluleDeLOeil() {
    const cle = celluleDe(camera.position);
    if (cle === occupee) return cellule;
    occupee = cle;
    const [bas, haut, bits] = cuite.cellules[cle] ?? [];
    cellule = bits ? { bas: bas - ECART_DE_L_OEIL, haut: haut + ECART_DE_L_OEIL, cachees: cacheesDe(bits, tuiles) } : null;
    return cellule;
  }

  scene.onBeforeRender = (_renderer, _scene, vue) => {
    if (vue !== camera || marche.vol) return;
    const ici = celluleDeLOeil();
    if (ici && camera.position.y >= ici.bas && camera.position.y <= ici.haut) detail.voiler(ici.cachees);
  };
  const tracerLesOmbres = renderer.shadowMap.render;
  // Three dresse la liste de l'œil avant de tracer les ombres : elles, puis le miroir et les sondes, veulent le décor entier.
  renderer.shadowMap.render = (...tracees) => {
    detail.devoiler();
    tracerLesOmbres.apply(renderer.shadowMap, tracees);
  };
}
