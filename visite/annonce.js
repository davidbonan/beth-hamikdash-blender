// L'annonce : au doigt rien ne survole, alors l'objet devant lequel on s'arrête dit une fois son nom, puis se tait.
const ATTENTE_MS = 250;    // l'arrêt doit en être un
const DUREE_MS = 2500;
const FONDU_MS = 500;      // la marque reste accrochée à son objet le temps de s'effacer

export function annonce({ objetsRegardes, placeALEcran, nomDe }) {
  const marque = document.querySelector("#annonce");
  const nom = marque.querySelector(".nom");
  const connus = new Set();
  let guette = null, depuis = 0, point = null, fin = 0;

  function taire() {
    guette = point = null;
    marque.classList.remove("vue");
  }

  const patienter = () => { guette = null; };

  function suivre() {
    if (!point) return;
    const reste = fin - performance.now();
    const place = reste > -FONDU_MS && placeALEcran(point);
    if (!place) return taire();
    if (reste <= 0) marque.classList.remove("vue");
    marque.style.transform = `translate3d(${place.clientX}px, ${place.clientY}px, 0)`;
  }

  function guetter() {
    if (point) return;
    const objets = objetsRegardes().filter((o) => !connus.has(o.id));
    const tenu = objets.find((o) => o.id === guette);
    const maintenant = performance.now();
    if (!tenu) { guette = objets[0]?.id ?? null; depuis = maintenant; return; }
    if (maintenant - depuis < ATTENTE_MS) return;
    connus.add(tenu.id);
    point = tenu.point;
    fin = maintenant + DUREE_MS;
    nom.textContent = nomDe(tenu.id);
    marque.classList.add("vue");
    suivre();
  }

  return { guetter, patienter, suivre, taire, tenirPourConnu: (id) => connus.add(id) };
}
