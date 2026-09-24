// La définition suit ce que la machine tient, par paliers, et ne retente pas à chaque instant un palier qu'elle vient de rater.
const LISSAGE = 0.05;
const IMAGES_ENTRE_CHANGEMENTS = 120;
// Lue contre la synchro à 60 Hz : une image dure 16,7 ms ou 33,3 ms, jamais entre les deux.
const LENT_MS = 26;
const VIF_MS = 18;
// Une remontée suivie d'une descente dans ces secondes-là a échoué : la suivante attend deux fois plus.
const ESSAI_S = 10;
const PAUSE_S = 15;
const PAUSE_MAX_S = 120;

export function regulerEchelle(minimum) {
  const paliers = [1, 0.85, minimum];
  let palier = 0, moyenne = 16, images = 0;
  let montee = -Infinity, remontee = 0, pause = PAUSE_S;
  return {
    // L'échelle nouvelle, ou null si elle ne change pas.
    suivre(dt, maintenant) {
      moyenne += (dt * 1000 - moyenne) * LISSAGE;
      if (++images < IMAGES_ENTRE_CHANGEMENTS) return null;
      if (moyenne > LENT_MS && palier < paliers.length - 1) {
        pause = maintenant - montee < ESSAI_S ? Math.min(pause * 2, PAUSE_MAX_S) : PAUSE_S;
        remontee = maintenant + pause;
        palier++;
      } else if (moyenne < VIF_MS && palier > 0 && maintenant >= remontee) {
        montee = maintenant;
        palier--;
      } else {
        return null;
      }
      images = 0;
      return paliers[palier];
    },
  };
}
