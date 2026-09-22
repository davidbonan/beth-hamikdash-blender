/**
 * Commandes du visiteur.
 *
 * Le clavier et les deux pouces aboutissent au MÊME état : trois axes, un cran de
 * course, et trois gestes — regarder, interroger, s'y rendre. Rien ici ne connaît la
 * scène ; la marche, ses collisions et le regard restent dans visite.js.
 *
 * Au doigt, le bas gauche de l'écran est un manche qui naît sous le pouce : un
 * manche posé d'avance oblige à viser un cercle qu'on ne regarde pas. Tout le reste
 * tourne la tête ; couché, le pouce gauche monte plus haut et le manche avec. Un appui
 * bref reste un appui bref des deux côtés, sans quoi la moitié gauche du Temple ne
 * s'interrogerait plus.
 */
const SENSIBILITE = { mouse: 0.0022, pen: 0.0022 };
// Au doigt, un glissé d'un bord à l'autre fait demi-tour, que le téléphone soit debout ou couché.
const sensibilite = (type) => type === "touch" ? Math.PI / innerWidth : SENSIBILITE[type] ?? SENSIBILITE.mouse;
const ZONE_MANCHE = 0.46;      // fraction gauche de l'écran
const ZONE_MANCHE_DEBOUT = 0.5; // fraction basse de l'écran, téléphone debout
const RAYON = 58;              // px : la course du pouce
const MORT = 0.14;             // en deçà, le pouce n'a pas encore décidé
const POUSSEE = 1.32;          // pousser au-delà du cercle, c'est courir
// Un doigt dérive toujours de quelques pixels et se relève moins vite qu'une souris
// ne clique : sans ces deux seuils-là, tout appui tactile se lit en glissé.
const APPUI_MS = 320;
const APPUI_PX = { mouse: 5, pen: 5, touch: 16 };
const DOUBLE_MS = 330, DOUBLE_PX = 48;

const AVANT = ["KeyW", "KeyZ", "ArrowUp"], ARRIERE = ["KeyS", "ArrowDown"];
const GAUCHE = ["KeyA", "KeyQ", "ArrowLeft"], DROITE = ["KeyD", "ArrowRight"];
const CAPTEES = ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space"];

const borner = (v, min, max) => Math.min(Math.max(v, min), max);

export function commandes(toile, { regarder, interroger, allerAu, basculerVol }) {
  const etat = {
    long: 0, lat: 0, vert: 0, course: false, tourne: false,
    pointeur: { x: 0, y: 0, clientX: 0, clientY: 0, survole: false },
    modeVol: (actif) => document.documentElement.classList.toggle("vol", actif),
  };

  // ---- clavier ----
  const touches = new Set();
  const enfoncee = (liste) => liste.some((c) => touches.has(c));
  const horsDeLaScene = () => !!document.activeElement?.closest?.("#barre, #fiche, #accueil, #initiation, #plan");

  addEventListener("keydown", (e) => {
    if (horsDeLaScene()) return;
    touches.add(e.code);
    if (e.code === "KeyV") basculerVol();
    if (CAPTEES.includes(e.code)) e.preventDefault();
    recomposer();
  });
  addEventListener("keyup", (e) => { touches.delete(e.code); recomposer(); });
  addEventListener("blur", () => { touches.clear(); recomposer(); });

  // ---- manche ----
  const cercle = document.querySelector("#manche");
  const bouton = cercle.firstElementChild;
  const manche = { long: 0, lat: 0, course: false };

  // Le cercle est là où le pouce s'est posé, même à cheval sur le bord : recentré, il
  // décalerait le zéro du geste et un pouce qui pousse droit devant partirait de côté.
  function poserManche(x, y) {
    cercle.style.left = `${x}px`;
    cercle.style.top = `${y}px`;
    bouton.style.transform = "translate(-50%, -50%)";
    cercle.classList.add("vu");
  }

  function bougerManche(dx, dy) {
    const d = Math.hypot(dx, dy) || 1;
    const bride = Math.min(d, RAYON);
    bouton.style.transform =
      `translate(calc(-50% + ${(dx / d) * bride}px), calc(-50% + ${(dy / d) * bride}px))`;
    const u = Math.max(0, bride / RAYON - MORT) / (1 - MORT);
    manche.lat = (dx / d) * u;
    manche.long = (-dy / d) * u;
    manche.course = d > RAYON * POUSSEE;
    cercle.classList.toggle("court", manche.course);
    recomposer();
  }

  function rangerManche() {
    manche.long = manche.lat = 0;
    manche.course = false;
    cercle.classList.remove("vu", "court");
  }

  // ---- montée et descente en vol ----
  let vertical = 0;
  for (const [selecteur, signe] of [["#monter", 1], ["#descendre", -1]]) {
    const b = document.querySelector(selecteur);
    b.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      vertical = signe;
      recomposer();
      b.setPointerCapture(e.pointerId);
    });
    const lever = () => { if (vertical === signe) { vertical = 0; recomposer(); } };
    b.addEventListener("pointerup", lever);
    b.addEventListener("pointercancel", lever);
  }

  function recomposer() {
    const clavierLong = (enfoncee(AVANT) ? 1 : 0) - (enfoncee(ARRIERE) ? 1 : 0);
    const clavierLat = (enfoncee(DROITE) ? 1 : 0) - (enfoncee(GAUCHE) ? 1 : 0);
    etat.long = borner(clavierLong + manche.long, -1, 1);
    etat.lat = borner(clavierLat + manche.lat, -1, 1);
    etat.vert = borner((touches.has("Space") ? 1 : 0) - (touches.has("KeyC") ? 1 : 0) + vertical, -1, 1);
    etat.course = manche.course || touches.has("ShiftLeft") || touches.has("ShiftRight");
  }

  // ---- glissés ----
  const glisses = new Map();
  let idManche = null, idRegard = null;
  let dernier = { t: 0, x: 0, y: 0 };

  function appuyer(x, y) {
    const t = performance.now();
    if (t - dernier.t < DOUBLE_MS && Math.hypot(x - dernier.x, y - dernier.y) < DOUBLE_PX) {
      dernier = { t: 0, x: 0, y: 0 };
      allerAu(x, y);
      return;
    }
    dernier = { t, x, y };
    interroger(x, y);
  }

  const sousLePouceGauche = (x, y) =>
    x < innerWidth * ZONE_MANCHE && (innerWidth > innerHeight || y > innerHeight * ZONE_MANCHE_DEBOUT);

  toile.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    const g = { role: null, x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY,
                t: performance.now(), parcours: 0 };
    if (e.pointerType === "touch" && idManche === null && sousLePouceGauche(e.clientX, e.clientY)) {
      idManche = e.pointerId;
      g.role = "manche";
      poserManche(e.clientX, e.clientY);
    } else if (idRegard === null) {
      idRegard = e.pointerId;
      g.role = "regard";
      etat.tourne = true;
      toile.classList.add("tourne");
    } else return;
    glisses.set(e.pointerId, g);
    toile.setPointerCapture(e.pointerId);
  });

  toile.addEventListener("pointermove", (e) => {
    if (e.pointerType !== "touch") {
      const p = etat.pointeur;
      p.survole = true;
      p.clientX = e.clientX; p.clientY = e.clientY;
      p.x = (e.clientX / innerWidth) * 2 - 1;
      p.y = -(e.clientY / innerHeight) * 2 + 1;
    }
    const g = glisses.get(e.pointerId);
    if (!g) return;
    const dx = e.clientX - g.x, dy = e.clientY - g.y;
    g.x = e.clientX; g.y = e.clientY;
    g.parcours += Math.abs(dx) + Math.abs(dy);
    if (g.role === "regard") {
      const s = sensibilite(e.pointerType);
      regarder(dx * s, dy * s);
    } else {
      bougerManche(e.clientX - g.x0, e.clientY - g.y0);
    }
  });

  function relacher(e) {
    const g = glisses.get(e.pointerId);
    if (!g) return;
    glisses.delete(e.pointerId);
    if (toile.hasPointerCapture(e.pointerId)) toile.releasePointerCapture(e.pointerId);
    if (g.role === "manche") { idManche = null; rangerManche(); }
    else { idRegard = null; etat.tourne = false; toile.classList.remove("tourne"); }
    recomposer();
    const bref = performance.now() - g.t < APPUI_MS;
    if (e.type === "pointerup" && bref && g.parcours < (APPUI_PX[e.pointerType] ?? APPUI_PX.mouse))
      appuyer(e.clientX, e.clientY);
  }

  toile.addEventListener("pointerup", relacher);
  toile.addEventListener("pointercancel", relacher);
  toile.addEventListener("pointerleave", (e) => {
    if (e.pointerType !== "touch") etat.pointeur.survole = false;
  });
  toile.addEventListener("contextmenu", (e) => e.preventDefault());

  return etat;
}
