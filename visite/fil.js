// Le fil de la page : le rendre au navigateur entre deux tranches de calcul, ou le temps qu'il peigne une image.
export const rendreLaMain = () => new Promise((reprise) => {
  const canal = new MessageChannel();
  canal.port1.onmessage = () => reprise();
  canal.port2.postMessage(null);
});
// Sans cette image, « préparation… » ne s'affichait jamais ; un onglet caché n'en donne aucune, d'où le délai.
export const laisserPeindre = () => new Promise((suite) => {
  requestAnimationFrame(() => setTimeout(suite));
  setTimeout(suite, 200);
});
