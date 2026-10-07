/**
 * Ce que le navigateur retient d'une visite à l'autre, et ce qu'une page confie
 * à celle qui la recharge dans le même onglet.
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

export function oublier(clef) {
  try { localStorage.removeItem(clef); } catch { /* stockage refusé : rien n'y était */ }
}

export function lireConfie(clef) {
  try { return sessionStorage.getItem(clef); } catch { return null; }
}

export function confier(clef, valeur) {
  try { sessionStorage.setItem(clef, valeur); } catch { /* stockage refusé : la page suivante repart de zéro */ }
}

export function oublierConfie(clef) {
  try { sessionStorage.removeItem(clef); } catch { /* stockage refusé : rien n'y était */ }
}
