/**
 * Les parcours guidés : la visite marche seule d'une station à la suivante, dans
 * l'ordre d'un service — le tamid du matin (Tamid 1–7), le seder ha'avoda de Yom
 * Kippour (Yoma 1–7), la nuit de Sim'hat Beit HaSho'éva (Soucca 5:1–4) —, et dit à
 * chaque arrêt ce qu'on y voit ; la fiche du concept attend derrière le lien « Lire la
 * fiche » de la carte, elle ne couvre pas le texte de l'étape.
 *
 * Les parcours sont `parcours.json`, en amot comme `cinema.json` : pour chaque station,
 * où l'on se tient, ce qu'on regarde, les points de passage qui contournent l'autel,
 * et le concept à lire. La marche est celle du cinéma — polyligne, sol sondé à chaque
 * image — mais elle s'arrête : « Suivant » repart, « Précédent » rebrousse, et un clic
 * pendant la marche saute à l'arrivée. Rien ici ne connaît la scène : visite.js prête
 * la caméra le temps du trajet, pose ou oriente le visiteur quand on le lui demande, et
 * passe au `moment` que la station, sinon le parcours, déclare — le jour, s'ils n'en
 * disent rien — et à la `troupe` du parcours, les figurants de son service ; en sortant,
 * à ceux de la visite libre.
 */
import * as THREE from "three";
import { polyligne } from "./cinema.js";
import { ecrire, langue, libelle, suivreLangue } from "./langue.js";
import { lireRetenu, retenir } from "./memoire.js";

const VITESSE = 3.4;           // m/s : le pas de la marche libre (PAS de visite.js), sans courir
const RAMPE = 1.2;             // s : on part et on s'arrête sans à-coup
const REPONSE_SOL = 0.22;      // s : une marche de 1/2 ama se glisse, elle ne se saute pas
const SOUS_PAS = 0.12;         // m : la sonde de sol ne saute aucune contremarche, quel que soit le framerate ou l'allure
const ECART_DEPART = 2;        // m : plus loin de sa station, on y est reposé avant de repartir
const PORTEE_REGARD = 6;       // m : en marchant, on regarde le chemin devant soi
const TOURNER_DEPART = 3;      // m : le temps de quitter des yeux ce qu'on regardait
const TOURNER_ARRIVEE = 8;     // m : le temps de se tourner vers ce que la station montre
const ALLURES = [1, 2, 4];     // la marche au pas, ou le temps qui s'accélère
const MEMOIRE_ALLURE = "visite.parcours.allure";
// Sur un téléphone la carte couvre la moitié basse de la scène : pendant la marche elle se replie d'elle-même.
const ECRAN_ETROIT = matchMedia("(max-width: 720px), (max-height: 520px)");
const CHEVRON_GAUCHE = "M8.5 2 2.5 8l6 6", CHEVRON_DROIT = "M3.5 2l6 6-6 6", COCHE = "M1 8.5l3.5 4L11 3";
const lisse = (u) => u * u * (3 - 2 * u);
const part = (x, de, longueur) => lisse(Math.min(Math.max((x - de) / longueur, 0), 1));

export function parcours({ parcours: liste, camera, sol, oeil, ama, poserA, marcher, arriver, changerDeMoment, changerDeTroupe, ouvrirFiche, fermerFiche }) {
  const racine = document.querySelector("#parcours");
  const carte = racine.querySelector(".carte");
  const nom = carte.querySelector(".nom"), rang = carte.querySelector(".rang"), source = carte.querySelector(".source");
  const titre = carte.querySelector("h2"), texte = carte.querySelector(".texte");
  const precedent = carte.querySelector(".precedent"), suivant = carte.querySelector(".suivant");
  const allure = carte.querySelector(".allure"), fiche = carte.querySelector(".fiche");
  const motSuivant = suivant.querySelector("span"), traceSuivant = suivant.querySelector("path"), tracePrecedent = precedent.querySelector("path");

  const enM = ([x, z]) => new THREE.Vector3(x * ama, 0, z * ama);
  const cibleEnM = ([x, y, z]) => new THREE.Vector3(x * ama, y * ama, z * ama);
  const piedsDe = (station) => [station.point[0] * ama, station.sol * ama, station.point[1] * ama];
  const traduit = (champ) => champ[langue()] ?? champ.fr;
  const momentDe = (station) => station.moment ?? guide.moment ?? "jour";

  let guide = null, stations = [];
  let courante = -1, origine = -1;
  let trajet = null;
  let facteur = ALLURES.includes(+lireRetenu(MEMOIRE_ALLURE)) ? +lireRetenu(MEMOIRE_ALLURE) : 1;
  let repliee = false, deplieeEnMarche = false;
  const ouvert = () => !racine.hidden;
  const derniere = () => courante === stations.length - 1;

  function afficher() {
    const station = stations[courante];
    nom.textContent = traduit(guide.titre);
    rang.textContent = `${courante + 1} / ${stations.length}`;
    source.textContent = `${libelle("oeuvres", station.source.oeuvre) ?? station.source.oeuvre} ${station.source.ref}`;
    titre.textContent = traduit(station.titre);
    texte.textContent = traduit(station.texte);
    precedent.disabled = courante === 0;
    const clefSuivant = derniere() ? "parcours_terminer" : "parcours_suivant";
    ecrire(motSuivant, clefSuivant);
    suivant.dataset.titre = clefSuivant;
    suivant.title = motSuivant.textContent;
    const [arriere, avant] = document.documentElement.dir === "rtl" ? [CHEVRON_DROIT, CHEVRON_GAUCHE] : [CHEVRON_GAUCHE, CHEVRON_DROIT];
    tracePrecedent.setAttribute("d", arriere);
    traceSuivant.setAttribute("d", derniere() ? COCHE : avant);
    allure.textContent = `×${facteur}`;
    fiche.disabled = trajet !== null || !station.concept;
    carte.classList.toggle("en-marche", trajet !== null);
    carte.classList.toggle("repliee", estRepliee());
  }

  // Replier la carte à la main tient jusqu'à ce qu'on la redéplie ; la déplier pendant une marche ne vaut que pour elle.
  const estRepliee = () => repliee || (trajet !== null && !deplieeEnMarche && ECRAN_ETROIT.matches);
  function basculerCarte() {
    if (estRepliee()) { repliee = false; deplieeEnMarche = true; } else repliee = true;
    carte.classList.toggle("repliee", estRepliee());
  }

  // Aller en avant suit les points de passage de la station visée ; revenir les
  // reprend à l'envers, ceux de la station qu'on quitte.
  function etapesVers(i) {
    const depart = camera.position.clone();
    const via = i > courante ? (stations[i].via ?? []) : [...(stations[courante].via ?? [])].reverse();
    return [depart, ...via.map(enM), enM(stations[i].point)];
  }

  // La hauteur des étapes ne compte pas : l'œil suit le sol sondé, comme au cinéma. Le
  // regard quitte ce qu'il fixait, suit le chemin, et se tourne vers la cible en arrivant.
  // L'allure multiplie le temps, pas la vitesse : le pas reste le même, il s'enchaîne plus vite.
  // Le temps se découpe en sous-pas : la sonde ne voit le sol qu'à MONTEE au-dessus des
  // pieds, et une image de 0,1 s à l'allure ×4 franchissait deux contremarches d'un coup —
  // l'œil arrivait sous le dallage de l'Azara, ou restait en l'air au-dessus de l'Ezrat Nashim.
  function partirVers(i) {
    const station = stations[i];
    const etapes = etapesVers(i);
    const chemin = polyligne(etapes);
    const longueur = etapes.reduce((d, p, k) => d + (k ? p.distanceTo(etapes[k - 1]) : 0), 0);
    const duree = longueur / VITESSE + RAMPE;   // chaque rampe coûte la moitié de sa durée
    const regardDe = camera.getWorldDirection(new THREE.Vector3()).multiplyScalar(10).add(camera.position);
    const regardVers = cibleEnM(station.cible);
    const regard = new THREE.Vector3(), devant = new THREE.Vector3();
    let temps = 0, parcouru = 0;
    let pieds = camera.position.y - oeil;
    let hauteurOeil = camera.position.y;

    function pas(dt) {
      temps += dt;
      const cadence = lisse(Math.min(temps / RAMPE, 1)) * lisse(Math.min(Math.max(duree - temps, 0) / RAMPE, 1));
      parcouru = Math.min(parcouru + VITESSE * cadence * dt, longueur);
      const u = temps >= duree ? 1 : parcouru / longueur;
      const point = chemin(u);
      const sonde = sol(point.x, point.z, pieds);
      if (sonde !== null) pieds = sonde;
      const k = dt > 0 ? 1 - Math.exp(-dt / REPONSE_SOL) : 1;
      hauteurOeil += (pieds + oeil - hauteurOeil) * k;
      camera.position.set(point.x, hauteurOeil, point.z);
      devant.copy(chemin(Math.min(u + PORTEE_REGARD / longueur, 1))).setY(hauteurOeil);
      regard.lerpVectors(regardDe, devant, part(parcouru, 0, TOURNER_DEPART));
      regard.lerp(regardVers, part(parcouru, longueur - TOURNER_ARRIVEE, TOURNER_ARRIVEE));
      camera.lookAt(regard);
      return temps >= duree;
    }

    trajet = {
      avancer(dtReel) {
        let reste = dtReel * facteur;
        while (reste > 0) {
          const dt = Math.min(reste, SOUS_PAS / VITESSE);
          reste -= dt;
          if (pas(dt)) return finir(i);
        }
      },
    };
    origine = courante;
    courante = i;
    deplieeEnMarche = false;
    changerDeMoment(momentDe(station));
    fermerFiche();
    afficher();
    marcher(trajet);
  }

  function finir(i) {
    trajet = null;
    courante = i;
    arriver();
    afficher();
  }

  // Loin de sa station — le visiteur a marché de lui-même —, la ligne droite traverserait
  // un mur : on le repose d'abord là où le parcours l'a laissé.
  function aller(i) {
    if (camera.position.distanceTo(new THREE.Vector3(...piedsDe(stations[courante]))) > ECART_DEPART) {
      poserA(piedsDe(stations[courante]), cibleEnM(stations[courante].cible));
    }
    partirVers(i);
  }

  function sauter(i) {
    if (trajet) marcher(null);
    trajet = null;
    courante = i;
    fermerFiche();
    changerDeMoment(momentDe(stations[i]));
    poserA(piedsDe(stations[i]), cibleEnM(stations[i].cible));
    afficher();
  }

  function ouvrir(id) {
    guide = liste.find((p) => p.id === id) ?? liste[0];
    stations = guide.stations;
    racine.hidden = false;
    changerDeTroupe(guide.troupe);
    sauter(0);
  }

  function fermer() {
    if (trajet) marcher(null);
    trajet = null;
    racine.hidden = true;
    changerDeMoment("jour");
    changerDeTroupe();
  }

  function accelerer() {
    facteur = ALLURES[(ALLURES.indexOf(facteur) + 1) % ALLURES.length];
    retenir(MEMOIRE_ALLURE, String(facteur));
    allure.textContent = `×${facteur}`;
  }

  // Pendant la marche, `courante` est déjà la station visée : « Suivant » y saute, « Précédent » revient d'où l'on part.
  precedent.onclick = (e) => {
    e.currentTarget.blur();
    if (trajet) sauter(origine); else if (courante > 0) aller(courante - 1);
  };
  suivant.onclick = (e) => {
    e.currentTarget.blur();
    if (trajet) sauter(courante); else if (derniere()) fermer(); else aller(courante + 1);
  };
  allure.onclick = (e) => { e.currentTarget.blur(); accelerer(); };
  fiche.onclick = (e) => { e.currentTarget.blur(); ouvrirFiche(stations[courante].concept); };
  carte.querySelector(".etape").onclick = basculerCarte;
  titre.onclick = () => { if (estRepliee()) basculerCarte(); };
  carte.querySelector(".quitter").onclick = (e) => { e.currentTarget.blur(); fermer(); };
  suivreLangue(() => { if (ouvert()) afficher(); });

  // `trajet` et `ecartSol` servent la vérification headless : elle fait avancer la marche
  // sans attendre les images, puis compare l'œil au dallage que la station déclare.
  const ecartSol = () => camera.position.y - oeil - stations[courante].sol * ama;
  return {
    ouvrir, fermer, aller: sauter, ouvert, liste: () => liste.map((p) => p.id),
    station: () => courante, nombre: () => stations.length, trajet: () => trajet, ecartSol,
  };
}
