// Le fil de la page : le rendre au navigateur entre deux tranches de calcul, ou le temps qu'il peigne une image.
const rendreLaMain = () => new Promise((reprise) => {
  const canal = new MessageChannel();
  canal.port1.onmessage = () => reprise();
  canal.port2.postMessage(null);
});
// Par tranches, et non d'un bloc : une seconde de calcul figeait la page, et un téléphone en met plusieurs.
const TRANCHE_MS = 30;
export async function parTranches(elements, traiter) {
  let debut = performance.now();
  for (const element of elements) {
    traiter(element);
    if (performance.now() - debut < TRANCHE_MS) continue;
    await rendreLaMain();
    debut = performance.now();
  }
}
// Sans cette image, « préparation… » ne s'affichait jamais ; un onglet caché n'en donne aucune, d'où le délai.
export const laisserPeindre = () => new Promise((suite) => {
  requestAnimationFrame(() => setTimeout(suite));
  setTimeout(suite, 200);
});
