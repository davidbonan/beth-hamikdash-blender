// L'écran de chargement : une frise d'étapes, le plan du Har HaBayit qui se trace au fil d'elles, et les gestes de la visite.
import { ecrire, texte } from "./langue.js";
import { laisserPeindre } from "./fil.js";

export const remplir = (trait, part) => { trait.style.transform = `scaleX(${part})`; };
// Lancée avant un gel de la page, la glissade se poursuit pendant lui, sur le compositeur.
export async function glisser(trait, part, duree) {
  trait.style.transition = `transform ${duree}ms linear`;
  remplir(trait, part);
  await laisserPeindre();
}

// Chaque travail nourrit une étape de la frise. Les poids de la préparation sont sa part de l'attente dans Safari
// d'iPhone, où elle dure ; le téléchargement en vaut 60 % (choix : sa durée suit le réseau, le reste l'appareil).
const TRAVAUX = {
  telechargement: { etape: "pierres", poids: 33 },
  arbres: { etape: "murs", poids: 1 },
  textures: { etape: "matieres", poids: 1 },
  nuanceurs: { etape: "matieres", poids: 10 },
  reflet: { etape: "lumiere", poids: 3 },
  detail: { etape: "decor", poids: 3 },
  image: { etape: "image", poids: 4 },
};
// Le reflet et la première image figent la page : leur durée s'estime en parts de celle de la compilation.
const GELS = { reflet: 0.3, image: 0.35 };
// L'aperçu net ne couvre jamais tout le flou : le texte doit rester lisible sur l'or.
const NETTETE_MAX = 0.75;
const MEGA_OCTET = 1e6;
// Chaque couche du plan se trace pendant une étape ; l'image n'en trace aucune, l'aperçu net monte à sa place.
const COUCHES = { mur: "pierres", cour: "murs", bati: "matieres", autel: "lumiere", sanctuaire: "lumiere", esplanade: "decor" };
// Les morceaux d'une couche partent l'un après l'autre, de l'est vers le Heikhal.
const DEPART_DU_DERNIER = 0.55;
const MARGE_DU_PLAN = 0.03;
const DUREE_D_UN_GESTE = 4500;
const SVG = "http://www.w3.org/2000/svg";

const borner = (x) => Math.min(1, Math.max(0, x));

function morceauxDe(d) {
  return d.split(/(?=M)/).map((morceau) => {
    const points = [...morceau.matchAll(/(-?[\d.]+) (-?[\d.]+)/g)].map(([, x, z]) => [+x, +z]);
    const xs = points.map(([x]) => x), zs = points.map(([, z]) => z);
    return { d: morceau, min: [Math.min(...xs), Math.min(...zs)], max: [Math.max(...xs), Math.max(...zs)] };
  });
}

function partDuMorceau({ rang, nombre }, partEtape) {
  if (nombre === 1) return partEtape;
  const depart = (rang / (nombre - 1)) * DEPART_DU_DERNIER;
  return borner((partEtape - depart) / (1 - DEPART_DU_DERNIER));
}

// Le cadre est l'emprise du mur du Har HaBayit, en mètres du repère de la scène, celui du dessin.
function dessinerLePlan(svg, dessin, cadre) {
  const marge = MARGE_DU_PLAN * (cadre.max.x - cadre.min.x);
  const min = [cadre.min.x - marge, cadre.min.z - marge], max = [cadre.max.x + marge, cadre.max.z + marge];
  svg.setAttribute("viewBox", `${min[0]} ${min[1]} ${max[0] - min[0]} ${max[1] - min[1]}`);
  const dedans = (m) => m.max[0] > min[0] && m.min[0] < max[0] && m.max[1] > min[1] && m.min[1] < max[1];
  const traces = [];
  for (const { categorie, d } of dessin.couches) {
    const etape = COUCHES[categorie];
    if (!etape) continue;
    const morceaux = morceauxDe(d).filter(dedans).sort((a, b) => b.max[0] + b.min[0] - a.max[0] - a.min[0]);
    morceaux.forEach((morceau, rang) => {
      const path = document.createElementNS(SVG, "path");
      path.setAttribute("d", morceau.d);
      path.setAttribute("pathLength", "1");
      path.setAttribute("class", categorie);
      svg.append(path);
      traces.push({ path, etape, rang, nombre: morceaux.length });
    });
  }
  return traces;
}

function faireTournerLesGestes(ecran) {
  const points = ecran.querySelector(".gestes .points");
  // Clavier ou doigt, c'est la feuille de style qui choisit le jeu : ne tournent que les gestes qu'elle montre.
  const gestes = [...ecran.querySelectorAll(".geste")].filter((geste) => geste.offsetParent !== null);
  let rang = 0, minuterie = 0;
  function montrer(nouveau) {
    gestes[rang]?.classList.remove("actif");
    rang = nouveau % gestes.length;
    gestes[rang].classList.add("actif");
    [...points.children].forEach((point, i) => point.setAttribute("aria-current", String(i === rang)));
    clearTimeout(minuterie);
    minuterie = setTimeout(() => montrer(rang + 1), DUREE_D_UN_GESTE);
  }
  points.replaceChildren(...gestes.map((geste, i) => {
    const titre = geste.querySelector("h2");
    titre.id = `geste-${i}`;
    const point = document.createElement("button");
    point.type = "button";
    point.setAttribute("aria-labelledby", titre.id);
    point.addEventListener("click", () => montrer(i));
    return point;
  }));
  montrer(0);
  return () => clearTimeout(minuterie);
}

export function ecranDeChargement(ecran) {
  const avancement = Object.fromEntries(Object.keys(TRAVAUX).map((travail) => [travail, 0]));
  const etapes = new Map([...ecran.querySelectorAll(".frise [data-etape]")].map((segment) => [segment.dataset.etape, {
    trait: segment.querySelector("i"), debutee: false, faite: false, part: 0,
  }]));
  const nom = ecran.querySelector(".etat .nom");
  const detail = ecran.querySelector(".etat-detail");
  const mesure = ecran.querySelector(".etat .mesure");
  const apercuNet = ecran.querySelector(".apercu-net");
  const plan = ecran.querySelector(".plan");
  let traces = [];
  let annoncee = null;
  let dureeCompilation = 0;
  const arreterLesGestes = faireTournerLesGestes(ecran);

  const partDe = (travaux) => {
    const poids = travaux.reduce((somme, travail) => somme + TRAVAUX[travail].poids, 0);
    return travaux.reduce((somme, travail) => somme + TRAVAUX[travail].poids * avancement[travail], 0) / poids;
  };
  const travauxDe = (etape) => Object.keys(TRAVAUX).filter((travail) => TRAVAUX[travail].etape === etape);

  function tracer(etape) {
    const { part } = etapes.get(etape);
    for (const trace of traces) {
      if (trace.etape !== etape) continue;
      const partTracee = partDuMorceau(trace, part);
      trace.path.style.strokeDashoffset = 1 - partTracee;
      trace.path.classList.toggle("rempli", partTracee === 1);
    }
  }

  // Deux étapes peuvent tourner ensemble : la ligne d'état dit la première qui n'est pas finie.
  function annoncer() {
    const etape = [...etapes].find(([, e]) => e.debutee && !e.faite)?.[0] ?? [...etapes.keys()].at(-1);
    if (etape === annoncee) return;
    annoncee = etape;
    ecrire(nom, `etape_${etape}`);
    ecrire(detail, `etape_${etape}_detail`);
    if (etape !== "pierres") mesure.textContent = "";
    for (const ligne of [nom, detail]) {
      ligne.classList.remove("change");
      void ligne.offsetWidth;
      ligne.classList.add("change");
    }
  }

  function montrer(travail) {
    const { etape } = TRAVAUX[travail];
    const e = etapes.get(etape);
    e.debutee = true;
    e.part = partDe(travauxDe(etape));
    apercuNet.style.opacity = NETTETE_MAX * partDe(Object.keys(TRAVAUX));
    tracer(etape);
    return e;
  }

  function avancer(travail, part = 1) {
    avancement[travail] = Math.max(avancement[travail], part);
    const e = montrer(travail);
    e.faite = e.part === 1;
    remplir(e.trait, e.part);
    annoncer();
  }

  // Un segment est large de sa part de l'attente.
  for (const [etape, { trait }] of etapes) {
    trait.parentElement.style.setProperty("--poids", travauxDe(etape).reduce((somme, t) => somme + TRAVAUX[t].poids, 0));
  }
  // Le balisage dit déjà la première étape : les textes ne sont pas encore chargés pour la redire.
  etapes.get("pierres").debutee = true;
  annoncee = "pierres";
  return {
    tracerLePlan(dessin, cadre) {
      traces = dessinerLePlan(plan, dessin, cadre);
      plan.closest(".cadre-plan").style.setProperty("--nord", `${dessin.nord}deg`);
      for (const etape of etapes.keys()) tracer(etape);
    },
    telecharger(recus, total) {
      mesure.textContent = texte("mega_octets")
        .replace("{recus}", Math.round(recus / MEGA_OCTET)).replace("{total}", Math.round(total / MEGA_OCTET));
      avancer("telechargement", recus / total);
    },
    // Sans taille annoncée par le serveur, le téléchargement ne s'est pas mesuré : fini, il compte plein.
    async preparer() {
      avancer("telechargement");
      avancer("arbres", 0);
      await laisserPeindre();
    },
    avancer,
    enJaugeant(travail, nombre, traiter) {
      let faits = 0;
      return (element) => {
        traiter(element);
        avancer(travail, ++faits / nombre);
      };
    },
    async compiler(compilation) {
      avancer("nuanceurs", 0);
      const debut = performance.now();
      await compilation((part) => avancer("nuanceurs", part));
      dureeCompilation = performance.now() - debut;
    },
    // L'étape reste en cours pendant le gel : c'est `avancer`, une fois la page rendue, qui la finit.
    glisserPendantLeGel(travail) {
      avancement[travail] = 1;
      const e = montrer(travail);
      annoncer();
      return glisser(e.trait, e.part, GELS[travail] * dureeCompilation);
    },
    lever() {
      arreterLesGestes();
      for (const { trait } of etapes.values()) remplir(trait, 1);
      ecran.classList.add("parti");
    },
  };
}
