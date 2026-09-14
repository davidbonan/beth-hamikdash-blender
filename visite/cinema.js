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
 * ligne droite, sans sol.
 */
import * as THREE from "three";

const PAUSE_S = 3;
const REPONSE_SOL = 0.22;      // s : une marche de 1/2 ama se glisse, elle ne se saute pas
const lisse = (u) => u * u * (3 - 2 * u);

function polyligne(points) {
  const longueurs = [0];
  for (let i = 1; i < points.length; i++) longueurs.push(longueurs[i - 1] + points[i].distanceTo(points[i - 1]));
  const total = longueurs[longueurs.length - 1];
  return (u) => {
    const d = u * total;
    let i = 1;
    while (i < points.length - 1 && longueurs[i] < d) i++;
    const part = (d - longueurs[i - 1]) / (longueurs[i] - longueurs[i - 1] || 1);
    return new THREE.Vector3().lerpVectors(points[i - 1], points[i], THREE.MathUtils.clamp(part, 0, 1));
  };
}

export function cinema({ parcours, camera, sol, oeil, ama, voile, signaler }) {
  const enM = ([x, z]) => new THREE.Vector3(x * ama, 0, z * ama);
  const cibleEnM = ([x, y, z]) => new THREE.Vector3(x * ama, y * ama, z * ama);
  const oeilA = (halte) => (halte.hauteur ?? halte.sol) * ama + (halte.hauteur == null ? oeil : 0);
  const fondu = parcours.fondu_s ?? 1;

  // Chaque halte devient un segment de temps : le trajet qui y mène, puis la pause.
  const segments = [];
  let debut = 0;
  parcours.haltes.forEach((halte, i) => {
    const precedente = parcours.haltes[i - 1];
    const trajet = i === 0 ? 0 : halte.duree_s;
    const pause = halte.pause_s ?? PAUSE_S;
    segments.push({
      halte, debut, trajet, fin: debut + trajet + pause,
      chemin: i === 0 ? () => enM(halte.point) : polyligne([precedente.point, ...(halte.via ?? []), halte.point].map(enM)),
      regardDe: precedente ? cibleEnM(precedente.cible) : cibleEnM(halte.cible),
      regardVers: cibleEnM(halte.cible),
      enLAir: halte.hauteur != null || precedente?.hauteur != null,
      oeilDe: oeilA(precedente ?? halte), oeilVers: oeilA(halte),
    });
    debut = segments[segments.length - 1].fin;
  });
  const duree = debut;

  let temps = 0;
  let pieds = parcours.haltes[0].sol * ama;
  let hauteurOeil = pieds + oeil;
  let annoncee = -1;
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
      hauteurOeil = THREE.MathUtils.lerp(s.oeilDe, s.oeilVers, u);
      pieds = hauteurOeil - oeil;
    } else {
      const sonde = sol(point.x, point.z, pieds);
      if (sonde !== null) pieds = sonde;
      if (u === 1 && Math.abs(pieds - s.halte.sol * ama) > 1) pieds = s.halte.sol * ama;
      const k = dt > 0 ? 1 - Math.exp(-dt / REPONSE_SOL) : 1;
      hauteurOeil += (pieds + oeil - hauteurOeil) * k;
    }
    camera.position.set(point.x, hauteurOeil, point.z);
    camera.lookAt(regard);

    // Noir sur le dernier temps de la dernière pause, sur le premier du départ, et au
    // passage d'un seuil qu'on ne voit pas au travers — la parokhet.
    const versLaFin = duree - temps, depuisLeDebut = temps;
    let noir = 1 - Math.min(versLaFin, depuisLeDebut) / fondu;
    if (s.halte.seuil) noir = Math.max(noir, 1 - Math.abs(point.x / ama - s.halte.seuil[0]) / s.halte.seuil[1]);
    voile.style.opacity = String(Math.max(0, noir));

    if (u === 1 && annoncee !== i) {
      annoncee = i;
      signaler({ degre: s.halte.degre, vue: s.halte.vue });
    }
  }

  return {
    duree,
    avancer: (dt) => poser(temps + dt, dt),
    aller: (t) => { annoncee = -1; poser(t, 0); },
  };
}
