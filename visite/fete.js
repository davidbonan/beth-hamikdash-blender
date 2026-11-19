// Ce que l'autel ne porte qu'un jour de l'année : à Kippour, la quatrième ma'arakha (Yoma 4:6) et son feu.
import * as THREE from "three";

function garder(liste, maillage, present) {
  const rang = liste.indexOf(maillage);
  if (present && rang < 0) liste.push(maillage);
  if (!present && rang >= 0) liste.splice(rang, 1);
}

// Un concept qui déclare une `fete` n'est là que ce jour-là ; les autres, tous les jours.
export function fetesDuTemple({ maillages, concepts, foyers, rendu, obstacles, murs }) {
  const feteDe = (concept) => concepts.get(concept)?.fete ?? null;
  // Rangé sous un groupe à lui : les tuiles du détail, qui remplacent le maillage, regardent la visibilité de ses parents.
  const propresALaFete = maillages.filter((o) => feteDe(o.userData.concept)).map((maillage) => {
    const groupe = new THREE.Group();
    maillage.parent.add(groupe);
    groupe.add(maillage);
    return { groupe, maillage, fete: feteDe(maillage.userData.concept), estUnMur: murs.includes(maillage) };
  });
  const lits = foyers.map(({ min, max, concept }) =>
    ({ fete: feteDe(concept), boite: new THREE.Box3(new THREE.Vector3(...min), new THREE.Vector3(...max)) }));

  return {
    celebrer(fete = null) {
      for (const { groupe, maillage, fete: laSienne, estUnMur } of propresALaFete) {
        const present = laSienne === fete;
        groupe.visible = present;
        garder(obstacles, maillage, present);
        if (estUnMur) garder(murs, maillage, present);
      }
      rendu.embraser(lits.filter((lit) => lit.fete === null || lit.fete === fete).map((lit) => lit.boite));
    },
  };
}
