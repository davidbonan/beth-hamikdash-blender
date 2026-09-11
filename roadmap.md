# Roadmap — la visite

Issue de l'analyse du 10 septembre 2026 : lecture du code de `visite/`, des JSON de
contenu et du README, plus neuf captures headless (bureau 1280 × 800, mobile 390 × 844)
par le Chromium SwiftShader du projet. Non vérifié : fluidité et toucher sur vrai appareil.

Chaque point porte un état : `todo`, `inprogress`, `done`, ou `backlog` pour ce qu'on
ne fait pas dans un premier temps. Chaque point dit ce qu'on
constate, ce qu'on touche, et comment on saura que c'est fait.

## Majeur

### 1. Cadrages des points d'entrée — `done`
- **Constat.** « Devant le Mizbea'h » (`reperes.json`, position `[-8.16, 0, 4.32]`) pose l'œil à 2,4 m de la face est de l'autel, haute de 4,8 m : l'écran est plein de pierre, avec le 'hout hasikra en travers. « Kodesh HaKodashim » coupe l'Aron en bas de cadre, tangage 0. « Har HaBayit » donne la moitié du cadre en dalles grises.
- **Touche.** Les entrées sont écrites par `beit_hamikdash_visite.py` (ligne ~69 et suivantes). Donner à chaque entrée un point visé (`vise`) en plus du cap, et un recul calculé pour que l'élément tienne dans le champ horizontal de 94°. `poser()` fait déjà le `lookAt` (`visite/visite.js`).
- **Fait quand.** Une planche des 13 entrées (10 entrées + 3 souterrains) sortie par `verifier.mjs`, comme la planche du film, et chaque vignette montre l'élément entier.

### 2. « Un élément… » n'encadre jamais les concepts majeurs — `done`
- **Constat.** `allerA` (`visite/visite.js:597-599`) cherche d'abord dans `entrees` et `souterrains`, puis seulement dans `emprises`. Huit ids sont partagés entre entrées et concepts : azara, ezrat_nashim, heikhal, kiyor, kodesh_hakodashim, mizbeach, oulam, quinze_marches. Choisir « Mizbea'h » dans l'encyclopédie donne le mur du point précédent.
- **Touche.** Séparer les deux menus : « Aller à… » prend les entrées, « Un élément… » prend toujours l'emprise, avec le cadrage curé du point précédent pour les gros volumes (le Heikhal fait 44 m de haut, le recul automatique de 1,3× ne tient pas dans l'Azara). Le plus simple : une entrée dédiée par concept majeur, nommée `vue_<id>`, référencée depuis l'emprise.
- **Fait quand.** Les huit concepts partagés donnent une vue où l'élément est visible en entier.

### 3. Parcours narré — `backlog`
- **Constat.** Visite libre sans fil : le visiteur atterrit face à la porte est et ne sait ni où aller ni pourquoi. Le mp3 de `audio/` (Ishay Ribo, Seder HaAvoda) n'est utilisé nulle part.
- **Touche.** Nouveau module `visite/parcours.js` : liste de stations `{ entree, concept, texte }` dans un `parcours.json` traduit comme `textes.json`. Entre deux stations, le pilote automatique existant (`cible` dans `vitesseVoulue`, `visite/visite.js`) marche à pied ; à l'arrivée, `montrer(concept)` ouvre la fiche et un bouton « Suivant » apparaît dans la barre. Premier parcours : le Tamid du matin (Tamid 1–7), du Beit HaMoked au Doukhan, 8 à 10 stations.
- **Fait quand.** Un visiteur qui ne touche que « Suivant » traverse le Temple dans l'ordre du service et lit une fiche à chaque arrêt.

### 4. Échelle humaine — `backlog`
- **Constat.** `FOULE = False` dans le blockout (README:590) : ni cohanim ni peuple. Rien ne dit que l'Oulam fait 100 amot de haut ou que l'autel dépasse deux hommes.
- **Touche.** Une poignée de silhouettes statiques exportées avec le glb : deux cohanim au Kiyor, un au kevesh, des Léviim sur le Doukhan, quelques figures dans l'Ezrat Nashim. Concept `figures` dans `concepts.json`, non interrogeable ou avec une fiche « ce que portent les cohanim » (Bigdei Kehouna, sources Shemot 28).
- **Fait quand.** Capture depuis l'Ezrat Israël : une silhouette au pied de l'autel donne l'échelle sans qu'on ait à lire une cote.

### 6. Désigner ce qui est interrogeable — `backlog`
- **Constat.** Au bureau l'étiquette au survol suit le curseur. Au doigt, rien ne signale qu'un élément a une fiche ; les 80 concepts ne se découvrent que par le `<select>`.
- **Touche.** Deux choses. Un surlignage de l'élément visé au centre du cadre (teinte émissive légère sur le matériau, ou passe de contour dans `chaine.js`). Un mode « repères » basculable : étiquettes 3D (`CSS2DRenderer`) posées sur le centre des emprises des concepts à moins de 40 m, cliquables, qui ouvrent la fiche.
- **Fait quand.** Sur mobile, sans initiation, un visiteur trouve et ouvre trois fiches en une minute.

### 7. Initiation plus courte, carte déplacée — `done`
- **Constat.** Cinq étapes (`visite/initiation.js:16-22`) dont « voler » et « monter » avant « interroger » : deux étapes sur une fonction secondaire retardent le contenu. La carte est posée en haut au centre (`visite/index.html:249`), exactement sur l'axe est-ouest qui traverse toutes les portes.
- **Touche.** Garder regarder, avancer, interroger. Déclencher l'apprentissage du vol la première fois qu'on appuie sur V ou le bouton « Vol libre » (même mécanique, deux étapes, lancée à la demande). Descendre la carte en bas de l'écran, au-dessus du rappel.
- **Fait quand.** Première fiche ouverte en moins de trente secondes au premier passage, et l'axe reste visible pendant l'initiation.

### 8. Plan — `done`
- **Constat.** Le `<select>` de 80 entrées groupées par zone est le seul accès à l'encyclopédie ; sur mobile il est pénible et « Un élémen » est tronqué.
- **Touche.** Une minicarte SVG du plan de Middot (Har HaBayit 500 × 500, Azara 187 × 135, Beit 100 × 70) générée depuis les emprises de `reperes.json`, avec le point du visiteur et son cap, zones cliquables qui téléportent, dépliable en plein écran. Le plan est lui-même un objet pédagogique : chaque zone y porte son nom hébreu.
- **Fait quand.** On peut aller partout sans ouvrir un `<select>`, et on sait toujours où l'on est.

## Mineur

### 9. Premier écran — `done`
- **Constat.** Trois drapeaux sur fond noir, aucune phrase sur ce qu'on va voir.
- **Touche.** `apercu.jpg` en fond, un sous-titre (« Le Temple d'après la Mishna Middot, à l'échelle »), langue devinée par `navigator.language` dans `langue.js` ; les drapeaux restent pour changer.
- **Fait quand.** Un inconnu sait avant de cliquer qu'il va marcher dans le Temple.

### 10. Chargement aveugle — `done`
- **Constat.** 12,2 Mo de glb derrière une jauge seule.
- **Touche.** Même aperçu flouté derrière `#chargement`, taille restante affichée. Voir aussi si le glb se coupe en deux (extérieur d'abord, intérieur du Beit ensuite) pour ouvrir la visite plus tôt.
- **Fait quand.** L'écran n'est jamais noir plus d'une seconde.

### 11. README périmé — `done`
- **Constat.** README:88 annonce 6,7 Mo pour `temple.glb` ; il en fait 12,2.
- **Touche.** Corriger le chiffre, ou le retirer puisqu'il bouge à chaque export.

### 12. Position en amot — `done`
- **Constat.** « 165 · 0 · -16 amot » (`visite/visite.js:700`) ne parle à personne.
- **Touche.** Remplacer par le nom de la zone courante, trouvée en testant la position contre les emprises de `reperes.json` (la plus petite qui contient le point). Garder les coordonnées derrière `?brut`.
- **Fait quand.** La barre dit « Ezrat Nashim » quand on y est.

### 13. Barre mobile tronquée — `done`
- **Constat.** À 390 px, « Un élémen… » est coupé.
- **Touche.** Deux icônes (porte pour « Aller à », loupe pour « Un élément ») avec libellé en `title`, ou un seul bouton menu qui ouvre les deux listes. Disparaît si le plan remplace les `<select>`.

### 14. Rappel des commandes mobile — `done`
- **Constat.** Sept lignes au centre de l'écran (`visite/index.html:503-506`), par-dessus la scène.
- **Touche.** Deux lignes (« pouce gauche : marcher · pouce droit : regarder · toucher : lire »), ou supprimer puisque l'initiation couvre.

### 15. Éclairage intérieur — `done`
- **Constat.** Une lampe accrochée à la caméra (`visite/visite.js:172`) éclaire le Heikhal : parois plates, sans direction, l'or ne joue pas.
- **Touche.** Faire de la Menora la source : sept petites `PointLight` chaudes ou une seule au centre, flammes émissives reprises par le halo de `chaine.js`. Garder une lampe faible pour l'Oulam et les ta'im. Coût GPU à mesurer sur le profil léger.
- **Fait quand.** Dans le Heikhal, l'ombre du Shoulkhan tombe du côté opposé à la Menora.

### 16. Carte d'initiation sur mobile — `backlog`
- **Constat.** Absente de la capture mobile 08 alors que la démonstration du geste s'affiche. Peut-être l'animation `paraitre` non rendue par SwiftShader.
- **Touche.** Vérifier sur un vrai téléphone avant de chercher.

### 17. Interroger au clavier — `backlog`
- **Constat.** Seul le clic ouvre une fiche.
- **Touche.** Entrée ou E interroge l'élément au centre du cadre (`conceptSous(ecran.set(0, 0))` existe déjà pour le survol).

### 18. Lien partageable — `backlog`
- **Constat.** `?vue=<id>` fonctionne mais rien ne l'expose.
- **Touche.** Bouton « copier le lien » dans la poignée de la fiche, qui écrit `?vue=<id>&lang=<code>` ; lire `lang` au chargement dans `langue.js`.

### 19. A. Visite narrée — recommandé — `backlog`
- **Idée.** La visite devient le jumeau interactif du film : chapitres du seder haavoda, marche automatique, voix ou texte, fiche à chaque station. La visite libre reste un mode, pas la porte d'entrée.
- **Pourquoi.** Réutilise tout : moteur, contenu, traductions, entrées. Le contenu sourcé est le vrai actif, le parcours est ce qui le fait lire.
- **Ordre.** Cadrages et nom de zone (un jour). Parcours Tamid (quelques jours). Son. Silhouettes. Puis un second parcours, Yom Kippour.

### 20. B. Atlas 2D de Middot — `backlog`
- **Idée.** Plan interactif et fiches, la 3D en illustration (captures fixes par concept).
- **Pourquoi.** Pas de WebGL, pas de 12 Mo, lisible sur tout, meilleur pour l'étude et le partage d'une fiche. Les JSON de contenu servent tels quels.
- **Coût.** Perd le « waouh » et la marche. À ne retenir que si l'usage réel est l'étude, pas la découverte.

### 22. Plan dessiné — `done`
- **Constat.** Le plan et la minicarte ne montrent que des rectangles orange tirés des emprises ; deux cadrages seulement (Har HaBayit, Azara), rien pour l'intérieur du Beit ni pour les souterrains.
- **Touche.** Le Temple vu du dessus, rendu en orthographique par Blender à l'export, une image par cadrage : Har HaBayit, Ezrat Nashim, Azara, Heikhal (coupe sous le toit), sous-terrain (coupe sous le sol, tunnels posés sur le plan de l'Azara pâli). Noms hébreux, entrées et visiteur par-dessus ; la minicarte prend l'image de la zone où l'on est.
- **Fait quand.** Au premier coup d'œil on reconnaît le Temple sur le plan, et on sait où l'on est même dans le Heikhal ou la mesiba.

### 23. Barre en paysage sur téléphone — `done`
- **Constat.** En paysage (844 × 390), la barre reprend la mise en page du bureau et occupe tout le haut de l'écran, alors que la barre du portrait tient.
- **Touche.** Même barre compacte qu'en portrait dès que l'écran est bas.

### 24. Cohérence de la barre — `done`
- **Constat.** Au bureau et en paysage, les `<select>` sont moins hauts que les boutons, et « Vol libre » passe sur deux lignes quand la largeur manque.
- **Touche.** Une seule hauteur, une seule police, pas de retour à la ligne ; ce qui ne tient pas se replie en icône.

### 21. C. Simulation du rituel — `backlog`
- **Idée.** Cohanim animés, service en temps réel.
- **Pourquoi pas maintenant.** Collection Foule à bâtir, rig et animation, budget GPU mobile. Après A, si le parcours narré prouve l'intérêt.
