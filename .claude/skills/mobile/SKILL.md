---
name: mobile
description: Teste la visite 3D dans Safari d'iPhone (simulateur iOS de Xcode) et la pilote depuis le terminal — erreurs, pertes de contexte WebGL, rythme d'images, mémoire GPU, empreinte des processus WebKit, captures d'écran, parcours guidés joués en temps réel. À utiliser dès qu'il est question du téléphone — « la visite plante sur iPhone », « ça rame sur mobile », « teste sur le simulateur », « combien de mémoire sur iPhone », « l'ombre est bizarre sur téléphone », « vérifie le profil léger », « rejoue les parcours sur mobile ». Pour le rendu bureau ou la planche des vues, c'est le vérificateur du skill publier.
---

# La visite sur iPhone, depuis le terminal

Tout se trouve dans ce dossier. Le simulateur partage le loopback du Mac : le serveur
n'écoute que sur 127.0.0.1.

| Fichier | Rôle |
|---|---|
| `serveur.py` | Sert l'arbre de travail (`/visite/` → `visite/`, `/` → `site/`), sans cache, et injecte `sonde.js` dans la page. Reçoit le journal (`--journal x.jsonl`), relaie les ordres. Une page qui démarre éteint ses aînées du même appareil (`about:blank`) : deux visites ouvertes se partagent la mémoire qu'on mesure. |
| `sonde.js` | Dans la page : console, erreurs, rejets, `webglcontextlost`, `createShader` nul, mémoire GPU estimée à chaque allocation (`__allocations(n)` liste les plus grosses), rythme toutes les 2 s (`__rythme`), appels et triangles (`__compter(__rendre)`), coût d'une image en régime GPU compris (`__chrono(n)`), perte de contexte à la demande (`__perdreContexte()`, ou `?perte=<n>` au n-ième nuanceur, en pleine compilation). |
| `ordre.py '<corps async>'` | Exécute du JavaScript dans la page la plus récente et imprime le retour. Les crochets de `visite.js` y sont : `__vue`, `__etat`, `__rendre`, `__parcours`, `__moteur` (`renderer`, `scene`). |
| `parcourir.py <dossier> [--vues a,b] [--requete qualite=haute]` | Ouvre la visite, attend `__pret`, passe l'accueil, capture chaque vue (`simctl io screenshot`) et relève rythme et état dans `mesures.json`. |
| `promenade.py <dossier> [--parcours tamid] [--stations n]` | Ce qu'un visiteur fait : chaque parcours guidé, station par station, en marchant à l'allure réelle. Capture à chaque arrivée, relevé toutes les 2 s dans `promenade.json` — c'est ce qui voit une fuite de mémoire ou une saccade. |
| `memoire.sh` | Empreinte (celle que jetsam juge sur iPhone) des processus WebContent (JavaScript) et GPU (textures) du simulateur. Demande de sortir du bac à sable (`footprint`). |

## Démarrer

```bash
m=.claude/skills/mobile
xcrun simctl boot "iPhone 17"                             # une fois ; il tourne sans fenêtre
python3 $m/serveur.py --journal "$TMPDIR/journal.jsonl" &  # en tâche de fond
python3 $m/parcourir.py "$TMPDIR/vues" --vues face_porte_est,azara
python3 $m/ordre.py 'return __rythme.at(-1)'
```

Pour une mesure de mémoire propre, fermer Safari d'abord (`xcrun simctl terminate booted
com.apple.mobilesafari`) : ses onglets gardent leurs processus.

## Ce que le simulateur dit, et ce qu'il tait

- **Fiable** : erreurs et comportements de WebKit iOS (même moteur que l'iPhone), mémoire
  GPU allouée par la page, empreinte des processus, fuites au fil d'une promenade,
  déterministe (triangles, appels, passes).
- **Pas fiable** : le temps par image. Le GPU est celui du Mac (M5 Pro, ~4 à 6 fois un
  iPhone), et d'une mesure à l'autre `__chrono` varie de ±30 %. Comparer des variantes
  en alternance, en médiane sur plusieurs tours, et ne rien conclure sous 20 % d'écart.
  Le vrai temps se lit sur un iPhone.
- **Absent** : la limite de mémoire de l'iPhone. Rien n'y est tué ; c'est l'empreinte
  mesurée qu'il faut garder basse.

## Repères mesurés (profil léger, iPhone 17 simulé)

| | avant | après |
|---|---|---|
| mémoire GPU au départ | 690 Mo | 480 Mo |
| mémoire GPU après les trois parcours | 1 218 Mo | 595 Mo |
| WebContent au repos | 830 Mo | 430 Mo |
| WebContent au pic du chargement | 1 003 Mo | 660 Mo |
