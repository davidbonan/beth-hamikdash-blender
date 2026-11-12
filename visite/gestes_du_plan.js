// Le plan se manie comme une carte : glisser, pincer, molette, double appui, flèches ; un appui bref vise un point.
const APPUI_PX = { mouse: 5, pen: 5, touch: 10 };
const APPUI_MS = 500;
const DOUBLE_MS = 280;            // un appui attend ce temps qu'un second en fasse un double, qui zoome
const DOUBLE_PX = 30;
const FACTEUR_DOUBLE = 2;
const MOLETTE = 0.0015;           // par pixel de défilement
const MOLETTE_PINCEE = 0.01;      // le pincé d'un pavé tactile arrive en molette, à petits pas
const LIGNE_PX = 33;
const INERTIE_S = 0.325;
const ELAN_MIN = 20;              // px/s
const ECHANTILLONS_MS = 100;
const ANIMATION_MS = 400;
const PAS_CLAVIER = 0.15;         // de la largeur visible

const borner = (v, min, max) => Math.min(Math.max(v, min), max);
const adoucir = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

// `bornes` : { min: [x, z], max: [x, z] } en mètres ; `echelleMax` en px par mètre.
export function gestesDuPlan(svg, { bornes, echelleMax, quandBouge, quandVise }) {
  let vue = { x: (bornes.min[0] + bornes.max[0]) / 2, z: (bornes.min[1] + bornes.max[1]) / 2, echelle: 1 };
  let mouvement = null;
  const doigts = new Map();
  let geste = null;
  let viseEnAttente = null, dernierAppui = null;

  const largeur = () => svg.clientWidth || 1;
  const hauteur = () => svg.clientHeight || 1;
  const echelleMin = () => Math.min(largeur() / (bornes.max[0] - bornes.min[0]), hauteur() / (bornes.max[1] - bornes.min[1]));

  // Plus étroite que les bornes, la vue y reste entière ; plus large, elle les centre.
  function axeBorne(centre, demi, min, max) {
    return 2 * demi >= max - min ? (min + max) / 2 : borner(centre, min + demi, max - demi);
  }

  function bornee({ x, z, echelle }) {
    const e = borner(echelle, echelleMin(), Math.max(echelleMax, echelleMin()));
    return {
      x: axeBorne(x, largeur() / 2 / e, bornes.min[0], bornes.max[0]),
      z: axeBorne(z, hauteur() / 2 / e, bornes.min[1], bornes.max[1]),
      echelle: e,
    };
  }

  function appliquer(voulue) {
    vue = bornee(voulue);
    const l = largeur() / vue.echelle, h = hauteur() / vue.echelle;
    svg.setAttribute("viewBox", `${vue.x - l / 2} ${vue.z - h / 2} ${l} ${h}`);
    quandBouge();
  }

  const relatif = (clientX, clientY) => {
    const cadre = svg.getBoundingClientRect();
    return [clientX - cadre.left, clientY - cadre.top];
  };
  const versMonde = (px, py) => [vue.x + (px - largeur() / 2) / vue.echelle, vue.z + (py - hauteur() / 2) / vue.echelle];
  const versEcran = (x, z) => [(x - vue.x) * vue.echelle + largeur() / 2, (z - vue.z) * vue.echelle + hauteur() / 2];

  // Le point du monde sous (px, py) y reste quand l'échelle change.
  function zoomAutour(echelle, px, py, depuis = vue) {
    const e = borner(echelle, echelleMin(), Math.max(echelleMax, echelleMin()));
    const wx = depuis.x + (px - largeur() / 2) / depuis.echelle, wz = depuis.z + (py - hauteur() / 2) / depuis.echelle;
    return { x: wx - (px - largeur() / 2) / e, z: wz - (py - hauteur() / 2) / e, echelle: e };
  }

  function arreter() {
    if (mouvement) cancelAnimationFrame(mouvement.image);
    mouvement = null;
  }

  function animerVers(voulue, duree = ANIMATION_MS) {
    arreter();
    const depart = vue, arrivee = bornee(voulue), debut = performance.now();
    // La dernière image n'est plus une animation : qui suit la vue y juge la carte arrivée.
    const pas = (maintenant) => {
      const t = Math.min((maintenant - debut) / duree, 1), k = adoucir(t);
      mouvement = t < 1 ? { anime: true, image: requestAnimationFrame(pas) } : null;
      appliquer({
        x: depart.x + (arrivee.x - depart.x) * k,
        z: depart.z + (arrivee.z - depart.z) * k,
        echelle: depart.echelle * (arrivee.echelle / depart.echelle) ** k,
      });
    };
    mouvement = { anime: true, image: requestAnimationFrame(pas) };
  }

  function lancerInertie(vx, vy) {
    arreter();
    let avant = performance.now();
    const pas = (maintenant) => {
      const dt = (maintenant - avant) / 1000;
      avant = maintenant;
      appliquer({ x: vue.x - (vx * dt) / vue.echelle, z: vue.z - (vy * dt) / vue.echelle, echelle: vue.echelle });
      const amorti = Math.exp(-dt / INERTIE_S);
      vx *= amorti;
      vy *= amorti;
      mouvement = Math.hypot(vx, vy) > ELAN_MIN ? { image: requestAnimationFrame(pas) } : null;
    };
    mouvement = { image: requestAnimationFrame(pas) };
  }

  // ---- doigts et souris ----
  const ecart = ([a, b]) => Math.hypot(a.x - b.x, a.y - b.y);
  const milieu = ([a, b]) => [(a.x + b.x) / 2, (a.y + b.y) / 2];

  const glisseDepuis = (doigt) => ({ type: "glisse", t0: performance.now(), parcours: 0, echantillons: [{ t: performance.now(), x: doigt.x, y: doigt.y }], appui: true });

  function commencerPince() {
    const paire = [...doigts.values()];
    geste = { type: "pince", ecart0: ecart(paire) || 1, milieu0: milieu(paire), depuis: vue };
  }

  svg.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    arreter();
    svg.setPointerCapture(e.pointerId);
    const [x, y] = relatif(e.clientX, e.clientY);
    doigts.set(e.pointerId, { x, y, type: e.pointerType });
    if (doigts.size === 1) geste = glisseDepuis(doigts.get(e.pointerId));
    else if (doigts.size === 2) commencerPince();
  });

  svg.addEventListener("pointermove", (e) => {
    const doigt = doigts.get(e.pointerId);
    if (!doigt) return;
    const [x, y] = relatif(e.clientX, e.clientY);
    const dx = x - doigt.x, dy = y - doigt.y;
    Object.assign(doigt, { x, y });
    if (geste?.type === "pince" && doigts.size === 2) {
      const paire = [...doigts.values()], [mx, my] = milieu(paire);
      const zoome = zoomAutour(geste.depuis.echelle * ecart(paire) / geste.ecart0, geste.milieu0[0], geste.milieu0[1], geste.depuis);
      appliquer({ ...zoome, x: zoome.x - (mx - geste.milieu0[0]) / zoome.echelle, z: zoome.z - (my - geste.milieu0[1]) / zoome.echelle });
      return;
    }
    if (geste?.type !== "glisse") return;
    geste.parcours += Math.abs(dx) + Math.abs(dy);
    const maintenant = performance.now();
    geste.echantillons.push({ t: maintenant, x, y });
    while (geste.echantillons.length > 2 && maintenant - geste.echantillons[0].t > ECHANTILLONS_MS) geste.echantillons.shift();
    appliquer({ x: vue.x - dx / vue.echelle, z: vue.z - dy / vue.echelle, echelle: vue.echelle });
  });

  function relacher(e) {
    const doigt = doigts.get(e.pointerId);
    if (!doigt) return;
    doigts.delete(e.pointerId);
    if (svg.hasPointerCapture(e.pointerId)) svg.releasePointerCapture(e.pointerId);
    if (geste?.type === "pince") {
      // Le doigt qui reste reprend la carte sans la faire sauter, et ne vise rien en se levant.
      const reste = [...doigts.values()][0];
      geste = reste ? { ...glisseDepuis(reste), appui: false } : null;
      return;
    }
    if (geste?.type !== "glisse") return;
    const fini = geste;
    geste = null;
    const bref = performance.now() - fini.t0 < APPUI_MS && fini.parcours < (APPUI_PX[doigt.type] ?? APPUI_PX.mouse);
    if (e.type === "pointerup" && fini.appui && bref) return appuyer(doigt);
    const [premier, dernier] = [fini.echantillons[0], fini.echantillons.at(-1)];
    const duree = dernier && premier ? (dernier.t - premier.t) / 1000 : 0;
    if (duree > 0 && performance.now() - dernier.t < ECHANTILLONS_MS)
      lancerInertie((dernier.x - premier.x) / duree, (dernier.y - premier.y) / duree);
  }

  function appuyer({ x, y }) {
    const maintenant = performance.now();
    if (dernierAppui && maintenant - dernierAppui.t < DOUBLE_MS && Math.hypot(x - dernierAppui.x, y - dernierAppui.y) < DOUBLE_PX) {
      clearTimeout(viseEnAttente);
      dernierAppui = null;
      animerVers(zoomAutour(vue.echelle * FACTEUR_DOUBLE, x, y));
      return;
    }
    dernierAppui = { t: maintenant, x, y };
    clearTimeout(viseEnAttente);
    viseEnAttente = setTimeout(() => quandVise(...versMonde(x, y)), DOUBLE_MS);
  }

  svg.addEventListener("pointerup", relacher);
  svg.addEventListener("pointercancel", relacher);

  svg.addEventListener("wheel", (e) => {
    e.preventDefault();
    arreter();
    const [x, y] = relatif(e.clientX, e.clientY);
    const pixels = e.deltaY * (e.deltaMode === 1 ? LIGNE_PX : 1);
    appliquer(zoomAutour(vue.echelle * Math.exp(-pixels * (e.ctrlKey ? MOLETTE_PINCEE : MOLETTE)), x, y));
  }, { passive: false });

  // ---- clavier ----
  const DEPLACEMENTS = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  const ZOOMS = { "+": FACTEUR_DOUBLE, "=": FACTEUR_DOUBLE, "-": 1 / FACTEUR_DOUBLE, _: 1 / FACTEUR_DOUBLE };
  svg.addEventListener("keydown", (e) => {
    const [dx, dy] = DEPLACEMENTS[e.key] ?? [0, 0];
    if (dx || dy) {
      const pas = PAS_CLAVIER * largeur() / vue.echelle;
      animerVers({ x: vue.x + dx * pas, z: vue.z + dy * pas, echelle: vue.echelle }, ANIMATION_MS / 2);
    } else if (ZOOMS[e.key]) zoomer(ZOOMS[e.key]);
    else return;
    e.preventDefault();
  });

  function zoomer(facteur) {
    animerVers(zoomAutour(vue.echelle * facteur, largeur() / 2, hauteur() / 2));
  }

  function oublierAppui() {
    clearTimeout(viseEnAttente);
    dernierAppui = null;
    doigts.clear();
    geste = null;
    arreter();
  }

  return {
    get vue() { return vue; },
    get anime() { return !!mouvement?.anime; },
    regler: appliquer,
    animerVers,
    zoomer,
    versEcran,
    // L'échelle où la boîte tient dans la vue.
    echellePour: (largeurM, hauteurM) => Math.min(largeur() / largeurM, hauteur() / hauteurM),
    oublierAppui,
  };
}
