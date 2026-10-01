// La désignation : ce que le curseur ou le doigt vise dans la scène, et l'élément que l'initiation montre du doigt.
import * as THREE from "three";

const PORTEE = 140;       // ce qu'un clic peut interroger
const SONDES = [[0, 0], [0.3, 0], [-0.3, 0], [0, -0.3], [0.3, -0.3], [-0.3, -0.3], [0.6, 0], [-0.6, 0]];
const CADRE = 0.85;
const RECONTROLE = 15;     // images entre deux contrôles, ou deux recherches vaines

export function designation({ camera, obstacles, concepts }) {
  const viseur = new THREE.Raycaster();
  const ecran = new THREE.Vector2();

  const normaliser = (clientX, clientY) =>
    ecran.set((clientX / innerWidth) * 2 - 1, -(clientY / innerHeight) * 2 + 1);

  // En coordonnées normalisées de l'écran.
  function conceptSous(x, y) {
    viseur.setFromCamera(ecran.set(x, y), camera);
    viseur.far = PORTEE;
    const touche = viseur.intersectObjects(obstacles, false);
    return touche.length ? touche[0].object.userData.concept || null : null;
  }

  function conceptTouche(clientX, clientY) {
    const { x, y } = normaliser(clientX, clientY);
    return conceptSous(x, y);
  }

  function pointTouche(cibles, portee, [clientX, clientY]) {
    viseur.setFromCamera(normaliser(clientX, clientY), camera);
    viseur.far = portee;
    const [touche] = viseur.intersectObjects(cibles, false);
    return touche?.point ?? null;
  }

  // L'initiation désigne un élément réellement à l'écran : « touchez un élément » ne dit
  // rien à qui ne sait pas encore ce qui s'interroge. La marque reste accrochée à son
  // point du monde, et on en cherche une autre quand il sort du cadre ou passe derrière
  // un mur. Seul un élément documenté se montre : la première fiche n'est pas un manque.
  const montre = { id: null, point: new THREE.Vector3(), images: 0, prochaineRecherche: 0 };
  const projete = new THREE.Vector3();

  function reperer() {
    viseur.far = PORTEE;
    for (const [x, y] of SONDES) {
      viseur.setFromCamera(ecran.set(x, y), camera);
      const [touche] = viseur.intersectObjects(obstacles, false);
      const id = touche?.object.userData.concept;
      if (id && concepts.get(id)?.resume) {
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
    return { nom: concepts.get(montre.id).nom,
             clientX: ((projete.x + 1) / 2) * innerWidth, clientY: ((1 - projete.y) / 2) * innerHeight };
  }

  return { conceptSous, conceptTouche, pointTouche, elementAMontrer };
}
