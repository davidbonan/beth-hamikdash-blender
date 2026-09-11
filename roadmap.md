# Roadmap — la visite

Issue de l'analyse du 10 septembre 2026 : lecture du code de `visite/`, des JSON de
contenu et du README, plus neuf captures headless (bureau 1280 × 800, mobile 390 × 844)
par le Chromium SwiftShader du projet. Non vérifié : fluidité et toucher sur vrai appareil.

Chaque point porte un état : `todo`, `inprogress`, `done`, ou `backlog` pour ce qu'on
ne fait pas dans un premier temps. Chaque point dit ce qu'on
constate, ce qu'on touche, et comment on saura que c'est fait.

## Majeur

### 3. Parcours narré — `backlog`
- **Constat.** Visite libre sans fil : le visiteur atterrit face à la porte est et ne sait ni où aller ni pourquoi. Le mp3 de `audio/` (Ishay Ribo, Seder HaAvoda) n'est utilisé nulle part.
- **Touche.** Nouveau module `visite/parcours.js` : liste de stations `{ entree, concept, texte }` dans un `parcours.json` traduit comme `textes.json`. Entre deux stations, le pilote automatique existant (`cible` dans `vitesseVoulue`, `visite/visite.js`) marche à pied ; à l'arrivée, `montrer(concept)` ouvre la fiche et un bouton « Suivant » apparaît dans la barre. Premier parcours : le Tamid du matin (Tamid 1–7), du Beit HaMoked au Doukhan, 8 à 10 stations.
- **Fait quand.** Un visiteur qui ne touche que « Suivant » traverse le Temple dans l'ordre du service et lit une fiche à chaque arrêt.

### 4. Échelle humaine — `done`
- **Constat.** `FOULE = False` dans le blockout (README:590) : ni cohanim ni peuple. Rien ne dit que l'Oulam fait 100 amot de haut ou que l'autel dépasse deux hommes.
- **Touche.** Une poignée de silhouettes statiques exportées avec le glb : deux cohanim au Kiyor, un au kevesh, des Léviim sur le Doukhan, quelques figures dans l'Ezrat Nashim. Concept `figures` dans `concepts.json`, non interrogeable ou avec une fiche « ce que portent les cohanim » (Bigdei Kehouna, sources Shemot 28). Attention à la modélisation, ça ne doit pas juste ressembler à des cubes et ronds empilés mais à des figures réalistes.
- **Fait quand.** Capture depuis l'Ezrat Israël : une silhouette au pied de l'autel donne l'échelle sans qu'on ait à lire une cote.

## Mineur

### 18. Lien partageable — `backlog`
- **Constat.** `?vue=<id>` fonctionne mais rien ne l'expose.
- **Touche.** Bouton « copier le lien » dans la poignée de la fiche, qui écrit `?vue=<id>&lang=<code>` ; lire `lang` au chargement dans `langue.js`.

### 19. A. Visite narrée — recommandé — `backlog`
- **Idée.** La visite devient le jumeau interactif du film : chapitres du seder haavoda, marche automatique, voix ou texte, fiche à chaque station. La visite libre reste un mode, pas la porte d'entrée.
- **Pourquoi.** Réutilise tout : moteur, contenu, traductions, entrées. Le contenu sourcé est le vrai actif, le parcours est ce qui le fait lire.
- **Ordre.** Cadrages et nom de zone (un jour). Parcours Tamid (quelques jours). Son. Silhouettes. Puis un second parcours, Yom Kippour.

### 20. B. Atlas 2D de Middot — `backlog`
- **Idée.** En homepage ne plus avoir la visite directement mais un plan interactif et fiches, la 3D en illustration (captures fixes par concept) avec un bouton visite sur chaque fiche et un bouton central de visite global.
- **Pourquoi.** Pas de WebGL, pas de 12 Mo, lisible sur tout, meilleur pour l'étude et le partage d'une fiche. Les JSON de contenu servent tels quels.
- **Coût.** Perd le « waouh » et la marche. À ne retenir que si l'usage réel est l'étude, pas la découverte.

### 21. C. Simulation du rituel — `backlog`
- **Idée.** Cohanim animés, service en temps réel.
- **Pourquoi pas maintenant.** Collection Foule à bâtir, rig et animation, budget GPU mobile. Après A, si le parcours narré prouve l'intérêt.

### 22. Bug de défilement sur mobile en mode portrait, les fiches ouvertes en dropdown depuis le bas de l'écran ne sont pas scrollable jusqu'au bout — `done`
