/**
 * Le parcours de l'accueil : la caméra marche seule d'un degré au suivant, de
 * l'esplanade au Kodesh HaKodashim, et dit à la page qui l'encadre où elle en est.
 *
 * Le parcours est `cinema.json` : des haltes en amot, chacune avec ce qu'on regarde,
 * la durée du trajet qui y mène, et le temps qu'on y reste. Entre deux haltes la
 * marche s'ouvre et se ferme en douceur ; les points de passage d'une halte (`via`)
 * contournent ce qui barre la ligne droite — l'autel. Le sol se sonde à chaque
 * image, comme sous le marcheur : les degrés se gravissent, ils ne se traversent pas.
 * Une halte qui donne une `hauteur` est en l'air : on y descend, ou on en descend, en
 * ligne droite, sans sol, et ses points de passage portent leur hauteur en troisième
 * valeur. Une halte peut poser son `oeil` (hauteur du regard au-dessus
 * du sol, en amot) et sa `focale` (en mm sur 36) : ce sont les cadrages des images du
 * film, que l'accueil fond sur la scène à l'arrivée. La page qui encadre peut demander
 * de sauter à une halte : on y arrive au noir, et la marche reprend de là.
 */
import * as THREE from "three";
import { REPONSE_SOL, cibleEnM, lisse, pointEnM, polyligne } from "./trajet.js";

const PAUSE_S = 3;
const FILM = 16 / 9;

export function cinema({ parcours, camera, sol, oeil, ama, voile, signaler }) {
  const enM = (point) => pointEnM(ama, point);
  const cible = (point) => cibleEnM(ama, point);
  const oeilAuSol = (halte) => (halte.oeil != null ? halte.oeil * ama : oeil);
  const oeilA = (halte) => (halte.hauteur != null ? halte.hauteur * ama : halte.sol * ama + oeilAuSol(halte));
  const fovDe = (halte) => halte.focale ? 2 * THREE.MathUtils.radToDeg(Math.atan(18 / halte.focale)) : null;
  const fondu = parcours.fondu_s ?? 1;

  // Chaque halte devient un segment de temps : le trajet qui y mène, puis la pause.
  const segments = [];
  let debut = 0;
  parcours.haltes.forEach((halte, i) => {
    const precedente = parcours.haltes[i - 1];
    const trajet = i === 0 ? 0 : halte.duree_s;
    const pause = halte.pause_s ?? PAUSE_S;
    const enLAir = halte.hauteur != null || precedente?.hauteur != null;
    const etapes = i === 0 ? [] : [precedente.point, ...(halte.via ?? []), halte.point].map(enM);
    if (enLAir && etapes.length) {
      etapes[0].y = oeilA(precedente);
      etapes[etapes.length - 1].y = oeilA(halte);
    }
    segments.push({
      halte, debut, trajet, fin: debut + trajet + pause,
      chemin: i === 0 ? () => enM(halte.point).setY(oeilA(halte)) : polyligne(etapes),
      regardDe: cible((precedente ?? halte).cible),
      regardVers: cible(halte.cible),
      enLAir,
      oeilSolDe: oeilAuSol(precedente ?? halte), oeilSolVers: oeilAuSol(halte),
      fovDe: fovDe(precedente ?? halte), fovVers: fovDe(halte),
    });
    debut = segments[segments.length - 1].fin;
  });
  const duree = debut;

  let temps = 0;
  let pieds = parcours.haltes[0].sol * ama;
  let hauteurOeil = pieds + oeil;
  let annoncee = -1;
  let depuisLaCoupe = Infinity;
  const regard = new THREE.Vector3();
  voile.style.transition = "none";

  function poser(t, dt) {
    temps = ((t % duree) + duree) % duree;
    const i = segments.findIndex((s) => temps < s.fin);
    const s = segments[i];
    const u = s.trajet ? lisse(THREE.MathUtils.clamp((temps - s.debut) / s.trajet, 0, 1)) : 1;
    const point = s.chemin(u);
    regard.lerpVectors(s.regardDe, s.regardVers, u);

    if (s.enLAir) {
      hauteurOeil = point.y;
      pieds = hauteurOeil - oeil;
    } else {
      const sonde = sol(point.x, point.z, pieds);
      if (sonde !== null) pieds = sonde;
      if (u === 1 && Math.abs(pieds - s.halte.sol * ama) > 1) pieds = s.halte.sol * ama;
      const k = dt > 0 ? 1 - Math.exp(-dt / REPONSE_SOL) : 1;
      hauteurOeil += (pieds + THREE.MathUtils.lerp(s.oeilSolDe, s.oeilSolVers, u) - hauteurOeil) * k;
    }
    camera.position.set(point.x, hauteurOeil, point.z);
    camera.lookAt(regard);
    if (s.fovVers) cadrer(THREE.MathUtils.lerp(s.fovDe ?? s.fovVers, s.fovVers, u));

    // Noir sur le dernier temps de la dernière pause, sur le premier du départ, et au
    // passage d'un seuil qu'on ne voit pas au travers — la parokhet.
    const versLaFin = duree - temps, depuisLeDebut = temps;
    let noir = 1 - Math.min(versLaFin, depuisLeDebut, depuisLaCoupe) / fondu;
    if (s.halte.seuil) noir = Math.max(noir, 1 - Math.abs(point.x / ama - s.halte.seuil[0]) / s.halte.seuil[1]);
    voile.style.opacity = String(Math.max(0, noir));

    if (u === 1 && annoncee !== i) {
      annoncee = i;
      signaler({ degre: s.halte.degre, vue: s.halte.vue });
    }
  }

  // La focale du film est horizontale sur 36 mm, pour une image en 16/9 ; three compte
  // l'angle vertical. L'accueil couvre l'écran avec l'image du film : sur un écran plus
  // large qu'elle on en voit toute la largeur, sur un plus haut toute la hauteur.
  function cadrer(fovHorizontal) {
    const demi = Math.tan(THREE.MathUtils.degToRad(fovHorizontal) / 2);
    const vertical = 2 * THREE.MathUtils.radToDeg(Math.atan(demi / Math.max(camera.aspect, FILM)));
    if (Math.abs(camera.fov - vertical) < 0.01) return;
    camera.fov = vertical;
    camera.updateProjectionMatrix();
  }

  function sauter(degre) {
    const s = segments.find((s) => s.halte.degre === degre);
    if (!s) return;
    pieds = s.halte.sol * ama;
    hauteurOeil = oeilA(s.halte);
    depuisLaCoupe = 0;
    annoncee = -1;
    poser(s.fin - (s.halte.pause_s ?? PAUSE_S), 0);
  }

  addEventListener("message", (e) => {
    if (e.source === parent && e.origin === location.origin && e.data?.type === "cinema" && e.data.aller) sauter(e.data.aller);
  });

  return {
    duree,
    avancer: (dt) => { depuisLaCoupe += dt; poser(temps + dt, dt); },
    aller: (t) => { annoncee = -1; poser(t, 0); },
    sauter,
  };
}
