// La désignation : ce que le curseur ou le doigt vise dans la scène, et l'élément que l'initiation montre du doigt.
import * as THREE from "three";

const PORTEE = 140;       // ce qu'un clic peut interroger
const PROCHE = 20;        // en deçà, un objet regardé s'annonce
// Du centre vers les bords : l'objet n'a pas à être visé juste.
const REGARD = [[0, 0], [0.2, 0], [-0.2, 0], [0, 0.15], [0, -0.15], [0.4, 0], [-0.4, 0],
                [0.3, 0.25], [-0.3, 0.25], [0.3, -0.25], [-0.3, -0.25]];
const SONDES = [[0, 0], [0.3, 0], [-0.3, 0], [0, -0.3], [0.3, -0.3], [-0.3, -0.3], [0.6, 0], [-0.6, 0]];
const CADRE = 0.85;
const RECONTROLE = 15;     // images entre deux contrôles, ou deux recherches vaines

export function designation({ camera, obstacles, concepts }) {
  const viseur = new THREE.Raycaster();
  const ecran = new THREE.Vector2();

  const normaliser = (clientX, clientY) =>
    ecran.set((clientX / innerWidth) * 2 - 1, -(clientY / innerHeight) * 2 + 1);

  // En coordonnées normalisées de l'écran.
  function toucheSous(x, y, portee = PORTEE) {
    viseur.setFromCamera(ecran.set(x, y), camera);
    viseur.far = portee;
    return viseur.intersectObjects(obstacles, false)[0];
  }

  const conceptSous = (x, y) => toucheSous(x, y)?.object.userData.concept || null;
  const documente = (id) => !!concepts.get(id)?.resume;

  function conceptTouche(clientX, clientY) {
    const { x, y } = normaliser(clientX, clientY);
    return conceptSous(x, y);
  }

  // L'initiation désigne un élément réellement à l'écran : « touchez un élément » ne dit
  // rien à qui ne sait pas encore ce qui s'interroge. La marque reste accrochée à son
  // point du monde, et on en cherche une autre quand il sort du cadre ou passe derrière
  // un mur. Seul un élément documenté se montre : la première fiche n'est pas un manque.
  const montre = { id: null, point: new THREE.Vector3(), images: 0, prochaineRecherche: 0 };
  const projete = new THREE.Vector3();

  function reperer() {
    for (const [x, y] of SONDES) {
      const touche = toucheSous(x, y);
      const id = touche?.object.userData.concept;
      if (id && documente(id)) {
        montre.id = id;
        montre.point.copy(touche.point);
        return;
      }
    }
    montre.id = null;
  }

  function projeter(point) {
    projete.copy(point).project(camera);
    return projete.z < 1 && Math.abs(projete.x) < CADRE && Math.abs(projete.y) < CADRE;
  }

  const enPixels = () =>
    ({ clientX: ((projete.x + 1) / 2) * innerWidth, clientY: ((1 - projete.y) / 2) * innerHeight });
  const placeALEcran = (point) => projeter(point) ? enPixels() : null;

  // Un lieu a déjà son nom sous le plan, et son dallage est partout sous le regard.
  function objetsRegardes() {
    const objets = new Map();
    for (const [x, y] of REGARD) {
      const touche = toucheSous(x, y, PROCHE);
      const id = touche?.object.userData.concept;
      if (id && !objets.has(id) && documente(id) && !concepts.get(id).lieu) objets.set(id, { id, point: touche.point });
    }
    return [...objets.values()];
  }

  function elementAMontrer() {
    const image = ++montre.images;
    const toujoursVu = montre.id !== null && projeter(montre.point) &&
      (image % RECONTROLE !== 0 || conceptSous(projete.x, projete.y) === montre.id);
    if (!toujoursVu) {
      if (image < montre.prochaineRecherche) return null;
      reperer();
      if (montre.id === null || !projeter(montre.point)) {
        montre.id = null;
        montre.prochaineRecherche = image + RECONTROLE;
        return null;
      }
    }
    return { nom: concepts.get(montre.id).nom, ...enPixels() };
  }

  return { conceptSous, conceptTouche, elementAMontrer, objetsRegardes, placeALEcran };
}
