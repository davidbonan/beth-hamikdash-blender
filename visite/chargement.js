// L'écran de chargement : les étapes se cochent une à une, et le Temple qu'on attend se précise derrière elles.
import { langue, texte } from "./langue.js";
import { laisserPeindre } from "./fil.js";

export const remplir = (trait, part) => { trait.style.transform = `scaleX(${part})`; };
// Lancée avant un gel de la page, la glissade se poursuit pendant lui, sur le compositeur.
export async function glisser(trait, part, duree) {
  trait.style.transition = `transform ${duree}ms linear`;
  remplir(trait, part);
  await laisserPeindre();
}

// Chaque travail nourrit une étape de la liste. Les poids de la préparation sont sa part de l'attente dans Safari
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

export function ecranDeChargement(ecran) {
  const avancement = Object.fromEntries(Object.keys(TRAVAUX).map((travail) => [travail, 0]));
  const etapes = new Map([...ecran.querySelectorAll("[data-etape]")].map((li) => [li.dataset.etape, {
    li, trait: li.querySelector(".jauge i"), mesure: li.querySelector(".mesure"), debut: null,
  }]));
  const apercuNet = ecran.querySelector(".apercu-net");
  let dureeCompilation = 0;

  const partDe = (travaux) => {
    const poids = travaux.reduce((somme, travail) => somme + TRAVAUX[travail].poids, 0);
    return travaux.reduce((somme, travail) => somme + TRAVAUX[travail].poids * avancement[travail], 0) / poids;
  };
  const travauxDe = (etape) => Object.keys(TRAVAUX).filter((travail) => TRAVAUX[travail].etape === etape);

  function commencer(etape) {
    const e = etapes.get(etape);
    if (e.debut !== null) return;
    e.debut = performance.now();
    e.li.classList.add("en-cours");
  }

  function finir(etape) {
    commencer(etape);
    const e = etapes.get(etape);
    if (e.li.classList.contains("faite")) return;
    e.li.classList.replace("en-cours", "faite");
    const secondes = (performance.now() - e.debut) / 1000;
    e.mesure.textContent = texte("secondes")
      .replace("{n}", secondes.toLocaleString(langue(), { minimumFractionDigits: 1, maximumFractionDigits: 1 }));
  }

  function montrer(travail) {
    const { etape } = TRAVAUX[travail];
    commencer(etape);
    apercuNet.style.opacity = NETTETE_MAX * partDe(Object.keys(TRAVAUX));
    return partDe(travauxDe(etape));
  }

  function avancer(travail, part = 1) {
    avancement[travail] = Math.max(avancement[travail], part);
    const partEtape = montrer(travail);
    remplir(etapes.get(TRAVAUX[travail].etape).trait, partEtape);
    if (partEtape === 1) finir(TRAVAUX[travail].etape);
  }

  commencer("pierres");
  return {
    // La taille d'abord : le dernier octet coche l'étape, qui affiche alors sa durée.
    telecharger(recus, total) {
      etapes.get("pierres").mesure.textContent = texte("mega_octets")
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
    // L'étape reste en cours pendant le gel : c'est `avancer`, une fois la page rendue, qui la coche.
    glisserPendantLeGel(travail) {
      avancement[travail] = 1;
      const partEtape = montrer(travail);
      return glisser(etapes.get(TRAVAUX[travail].etape).trait, partEtape, GELS[travail] * dureeCompilation);
    },
    lever() {
      for (const etape of etapes.keys()) finir(etape);
      ecran.classList.add("parti");
    },
  };
}
