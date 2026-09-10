/**
 * Ce que le navigateur retient d'une visite à l'autre.
 *
 * Le stockage peut être refusé — navigation privée, réglage du navigateur — et son
 * accès jette alors au lieu de répondre vide. Rien de ce qu'il retient n'est
 * indispensable : sans lui, la visite repart simplement comme au premier passage.
 */
export function lireRetenu(clef) {
  try { return localStorage.getItem(clef); } catch { return null; }
}

export function retenir(clef, valeur) {
  try { localStorage.setItem(clef, valeur); } catch { /* stockage refusé : ne vaut que pour cette visite */ }
}
