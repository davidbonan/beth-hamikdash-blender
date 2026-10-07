// Ce qui tourne mal : une erreur de chargement, et le contexte WebGL qu'un téléphone à court de mémoire retire à la page.
import { ecrire, texte } from "./langue.js";
import { seReplier } from "./qualite.js";

const PERTE = "visite-contexte-perdu";
const RECHUTE_MS = 120000;
const ATTENTE_RESTITUTION_MS = 5000;

function lireStockage(cle) {
  try { return sessionStorage.getItem(cle); } catch { return null; }
}
function ecrireStockage(cle, valeur) {
  try { sessionStorage.setItem(cle, valeur); } catch { /* navigation privée : la page rechargera, sans garde-fou */ }
}

export function veillerAuxPannes({ etat, chargement }) {
  // Un iPhone à court de mémoire retire son contexte à la page : plus rien ne se dessine, et la compilation en cours
  // jetait « shaderSource … must be an instance of WebGLShader ». Visite lancée, on attend que le navigateur le rende
  // et on renvoie ce que three ne sait pas refaire seul (reprendre) ; pendant le chargement, ou s'il ne revient pas,
  // la page se recharge d'elle-même. Une rechute aussitôt après ne boucle pas : elle le dit et attend qu'on touche l'écran.
  let contexte = null;
  let reprendre = null;
  let visiteLancee = false;
  let derniereReprise = -Infinity;
  let enReprise = false;
  let contexteAbandonne = false;
  let contexteEnPerte = false;

  function quandContextePerdu() {
    if (contexteEnPerte) return;
    contexteEnPerte = true;
    seReplier();
    if (!visiteLancee || Date.now() - derniereReprise < RECHUTE_MS) return abandonnerContexte();
    attendreRestitution();
  }
  function attendreRestitution() {
    setTimeout(() => {
      if (!contexte.isContextLost()) return;
      if (document.hidden) return document.addEventListener("visibilitychange", attendreRestitution, { once: true });
      abandonnerContexte();
    }, ATTENTE_RESTITUTION_MS);
  }
  async function quandContexteRendu() {
    if (!contexteEnPerte || contexteAbandonne) return;
    contexteEnPerte = false;
    derniereReprise = Date.now();
    enReprise = true;
    try {
      await reprendre();
    } finally {
      enReprise = false;
    }
  }
  function abandonnerContexte() {
    contexteAbandonne = true;
    const rechute = Date.now() - Number(lireStockage(PERTE) ?? 0) < RECHUTE_MS;
    ecrireStockage(PERTE, String(Date.now()));
    if (!rechute) return location.reload();
    document.documentElement.classList.add("perdu");
    ecrire(etat, "contexte_perdu");
    etat.style.color = "";
    chargement.onclick = () => location.reload();
  }

  // Une erreur de chargement laissait l'écran figé sur son dernier état sans rien dire :
  // le voile ne se lève qu'en fin de module, et un module qui jette ne lève rien.
  const echouer = (quoi) => {
    if (contexte?.isContextLost()) return quandContextePerdu();
    etat.textContent = `${texte("echec")} ${quoi}`;
    etat.style.color = "#e0836a";
  };
  addEventListener("error", (e) => echouer(e.message || e.error));
  addEventListener("unhandledrejection", (e) => echouer(e.reason?.message || e.reason));

  return {
    surveiller(renderer, refaire) {
      contexte = renderer.getContext();
      reprendre = refaire;
      renderer.domElement.addEventListener("webglcontextlost", quandContextePerdu);
      renderer.domElement.addEventListener("webglcontextrestored", quandContexteRendu);
    },
    lancer() { visiteLancee = true; },
    get enReprise() { return enReprise; },
    get contextePerdu() { return contexteEnPerte; },
  };
}
