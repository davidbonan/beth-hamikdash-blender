---
name: blender
description: Pilote la scène Blender du Beit HaMikdash en ligne de commande headless — reconstruire le blockout après avoir touché au script, inspecter la scène, exporter la visite 3D. À utiliser dès qu'il faut regénérer la scène ou répondre à une question sur elle — « où est le Doukhan », « regénère la scène », « la fenêtre du Beit Avtinas montre-t-elle la cour », « quelle taille fait cet objet dans la scène », « refais la visite ». Pour poser une caméra et en exporter les images clés, c'est le skill camera.
---

# Blender en ligne de commande

```
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
```

## L'invariant : le script est la source, le .blend est l'artefact

`modele/beit_hamikdash_blockout.py` et son paquet `modele/blockout/` **construisent** la scène ;
`modele/beit_hamikdash.blend` en est la sortie. Toute modification faite à la main dans l'interface de Blender est perdue
à la reconstruction suivante. Une correction se porte donc **dans le script**, jamais
dans le .blend. Même chose pour les caméras, qui vivent dans `modele/cameras.json`.

Corollaire : le .blend sur le disque date du dernier **export** —
`modele/beit_hamikdash_export.py` est le seul script qui appelle `wm.save_mainfile`. Le
blockout seul, en headless, jette sa géométrie en quittant. Pour reconstruire *et*
sauvegarder, il faut donc chaîner blockout, caméras et export dans la même instance.

## Les quinze scripts

| Script | Ce qu'il fait | Écrit |
|---|---|---|
| `modele/beit_hamikdash_blockout.py` | construit le Temple, son pays et la foule du jour, zone par zone (`modele/blockout/`, voir plus bas) | rien (mémoire) |
| `modele/beit_hamikdash_cameras.py` | pose les plans déclarés dans `modele/cameras.json` | rien (mémoire) |
| `modele/beit_hamikdash_export.py` | images clés couleur + profondeur, ou planche de contrôle | `render/blockout/` ou `render/planche/`, **et le .blend** |
| `modele/beit_hamikdash_analyse_plans.py` | recouvrement début/fin de chaque plan, glisse de l'image | rien |
| `modele/beit_hamikdash_inspect.py` | **lit** la scène sauvegardée et répond | rien |
| `modele/beit_hamikdash_marche.py` | **lit** la scène et rejoue la règle de marche de la visite : où l'on passe à pied, où l'on bute et pourquoi | `render/marche/marche.png` |
| `modele/beit_hamikdash_visite.py` | exporte la visite 3D du navigateur | `visite/temple.glb`, `visite/reperes.json`, `visite/occlusion/` |
| `modele/beit_hamikdash_occlusion.py` | cuit l'occlusion du ciel ou la lumière dans Cycles, appelé par le précédent | `visite/occlusion/*.webp`, `visite/lumiere/*.webp` |
| `modele/beit_hamikdash_recuisson.py` | ce que `--recuire` refait, et le verrou d'une cuisson à la fois | rien |
| `modele/beit_hamikdash_figures.py` | figurants de la visite, vêtus et animés, une troupe par parcours (`modele/figurants/`, voir plus bas ; gestes : `modele/beit_hamikdash_gestes.py`) | `visite/figures*.glb`, `visite/figures*.json` |
| `modele/beit_hamikdash_seir.py` | le bouc émissaire de Kippour, champ de distance polygonisé comme le bœuf (outillage commun : `modele/beit_hamikdash_champ.py`), que les figures posent à côté du Cohen Gadol | `modele/seir.blend` |
| `modele/beit_hamikdash_shor.py` | le bœuf de bronze des douze qui portent le Yam, champ de distance polygonisé (tronc lofté, membres os par os, sabots fendus), que le blockout lit et pose douze fois | `modele/shor.blend` |
| `modele/beit_hamikdash_keruvim.py` | les deux keruvim de la kaporet, corps MakeHuman agenouillés et ailes plumées, que le blockout lit | `modele/keruvim.blend` |
| `modele/beit_hamikdash_parokhet.py` | le motif tissé des Parokhot en carte (R = bombé, G/B = face du tissage, alpha = figure), composé des figures de `modele/tissages/` (guides + gpt-image-2, comme les gravures), que la matière du blockout et la visite lisent | `visite/matieres/parokhet_2048.webp`, `parokhet.json` |
| `modele/beit_hamikdash_gravures.py` | les figures des parois (keruv, palmette, timora, fleuron, bouton) : atlas de modelé et silhouettes composés des tuiles taillées de `modele/gravures/`, que le blockout lit pour poser chaque figure sur sa paroi | `visite/matieres/gravures_3072.webp`, `gravures.json` |
| `modele/beit_hamikdash_plan.py` | rend le plan de la visite vu du dessus, une image par cadrage | `visite/plans/*.webp`, `visite/plan.json` |

Les trois du milieu sont pilotés par le skill **camera**, qui les chaîne dans une
seule commande. Ce qui suit sert quand on veut les lancer soi-même.

## Où vit le code du blockout et des figurants

Les deux gros scripts ne sont plus que des points d'entrée ; leur code est dans deux paquets
à côté d'eux. L'incantation ne change pas : `-P modele/beit_hamikdash_blockout.py`,
`-P modele/beit_hamikdash_figures.py`.

```
modele/blockout/
  primitives/   parametres (AMA, Z_*, FOULE, RACINE, m) · noeuds · pierre · tissage · matieres (MAT_*)
                volumes (box, cyl, revolution…) · gravures · ouvrages (lishka, shaar, moulure, escalier…)
  nettoyage · har_habayit · ezrat_nashim · azara · lishkot · heil · modenature_azara
  mizbeach · sous_l_azara
  bayit/        oulam · heikhal · kelim · parokhot · parois_d_or · kodesh_hakodashim
  pays/         calage · herode · place_du_kotel · second_oeuvre · facades_du_kotel · parc_de_police · mobilier_du_kotel · ville · jerusalem (celui qui bâtit le pays)
  foule · finitions (dessus foulés, biseau, tailles) · eclairage
modele/figurants/
  matieres · etoffes (MPFB) · corps (Gabarit, Humain) · maillage · habillage · ustensiles
  mise_en_scene (gestes, reperes, Accessoire) · bigdei_kehouna · tenues (levi, fidele)
  danse · role (Role et les rôles partagés) · betes (seir, par, seh) · animation
  troupes/      figures · figures_tamid · figures_kippour · … · figures_nazir
```

- **Un module de zone bâtit à l'import.** `SECTIONS`, dans `modele/beit_hamikdash_blockout.py`,
  les importe dans l'ordre de construction — c'est lui la table des matières. Une zone
  nouvelle, c'est un module de plus et une ligne dans `SECTIONS`, à sa place : l'ordre
  compte, `finitions` biseaute et creuse ce qui existe déjà.
- **Chaque module importe nommément ce qu'il lit des autres** (`from .azara import AX0, …`).
  Une cote d'une zone voisine s'importe de la zone qui la pose, jamais ne se recopie.
- **Les points d'entrée purgent leur paquet de `sys.modules`** avant de l'importer :
  Blender garde les modules d'un *Run Script* à l'autre, et sans purge le second ne
  bâtirait rien.
- Les figurants : une troupe = un module de `modele/figurants/troupes/`, qui porte ses rôles
  (`roles_kippour()`…) ; la table `TROUPES` et `main()` restent dans
  `modele/beit_hamikdash_figures.py`. Ce que deux troupes partagent descend dans un module commun
  (`role`, `mise_en_scene`, `ustensiles`, `betes`), jamais d'une troupe à l'autre — seule
  `troupes/figures`, la visite libre, reprend ses rôles au tamid.

## Où atterrissent les sorties

Un dossier par étape du pipeline, et **rien à la racine de `render/`** :

| Dossier | Écrit par | Contenu |
|---|---|---|
| `render/blockout/` | `modele/beit_hamikdash_export.py` | couleur + profondeur 1920 × 1080, entrées de l'i2i |
| `render/planche/` | `modele/beit_hamikdash_export.py -- --planche` | contrôle 640 × 360 + `planche.html` + `planche.jpg` (mosaïque du README, versionnée) |
| `render/style/` | `fal_image.py` | images clés stylisées |
| `render/video/` | `fal_video.py` | mp4 |

Les chemins sont des constantes : `SOUS_DOSSIER_BLOCKOUT` / `SOUS_DOSSIER_PLANCHE`
dans l'export, `DOSSIER_IMAGES` / `DOSSIER_SORTIE` dans les scripts fal. En déplacer
un se fait là, pas en déplaçant les fichiers.

## Répondre à une question sur la scène — `inspect`

C'est le point d'entrée par défaut. Il ne reconstruit rien : il ouvre le .blend et
répond en une seconde. Ne pas mettre `-P modele/beit_hamikdash_blockout.py` devant.

```bash
$BLENDER -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_inspect.py -- --scene
$BLENDER -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_inspect.py -- --objets Doukhan
$BLENDER -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_inspect.py -- --camera CAM_03_Heikhal
$BLENDER -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_inspect.py -- --voit heikhal
$BLENDER -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_inspect.py -- --voit heikhal fin
$BLENDER -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_inspect.py -- --foule 01
```

| Commande | Répond à |
|---|---|
| `--scene` (défaut) | combien d'objets par collection, quels plans, quelle durée, quelle étendue |
| `--objets <motif>` | où se trouve un objet — bornes en amot, collection |
| `--camera <plan>` | focale, champ, frames, pose et cible aux deux frames clés, vitesse |
| `--voit <plan> [debut\|fin]` | ce que le cadre contient **vraiment**, par part d'écran et distance |
| `--foule <plan> [debut\|fin]` | combien de figures de `76_Foule` le plan voit, et leur hauteur écran |

`--voit` tire une grille de rayons dans le cadre : c'est la seule réponse fiable à
« est-ce que ce plan montre X », et elle tient compte de l'occultation. Un plan qui
ne renvoie aucune géométrie a sa caméra dans un mur.

Le plan se nomme comme on veut : `CAM_03_Heikhal`, `3`, `03`, ou `heikhal`.

## Reconstruire la scène

Après toute modification de `modele/blockout/` ou de `modele/beit_hamikdash_blockout.py`. Compte ~5 s.

```bash
# vérifier que le script tourne (rien n'est sauvegardé)
$BLENDER -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_blockout.py

# reconstruire ET sauvegarder le .blend (c'est l'export qui sauvegarde)
$BLENDER -b modele/beit_hamikdash.blend \
    -P modele/beit_hamikdash_blockout.py \
    -P modele/beit_hamikdash_cameras.py \
    -P modele/beit_hamikdash_export.py -- --planche
```

Le blockout annonce en dernière ligne son compte d'objets et de collections — la
vérification la plus rapide qu'il n'a rien cassé.

Les keruvim de la kaporet ne sont pas bâtis par le blockout : il lit `modele/keruvim.blend`, écrit
par `modele/beit_hamikdash_keruvim.py` (MakeHuman, ~2 min, sans .blend en entrée). Après toute
modification de ce script, le relancer puis reconstruire la scène :

```bash
$BLENDER -b -P modele/beit_hamikdash_keruvim.py
```

Même chose pour les douze bœufs du Yam : le blockout lit `modele/shor.blend`, écrit par
`modele/beit_hamikdash_shor.py` (~5 s, numpy de Blender). Après toute retouche du bœuf :

```bash
$BLENDER -b -P modele/beit_hamikdash_shor.py
```

Même logique pour le motif des Parokhot : il n'est pas de la géométrie mais une carte,
`visite/matieres/parokhet_2048.webp` (et `parokhet.json`, la palette des quatre laines),
écrite par `modele/beit_hamikdash_parokhet.py` (~20 s, numpy de Blender, `cwebp` sur le PATH) et
lue par `parokhet()` du blockout comme par le nuanceur étoffe de la visite. Les figures —
lion, keruv — sont tissées par gpt-image-2 depuis des guides, comme les gravures :
`modele/tissages/` est la source versionnée, `--guides` redessine les guides, `--tisser <nom>` fait
tisser une figure (FAL_AI_KEY dans `.env`). Les contours des guides — les siens et ceux des
parois du Bayit — vivent dans `modele/beit_hamikdash_contours.py`. Après toute modification :

```bash
$BLENDER -b -P modele/beit_hamikdash_parokhet.py
```

Et pour les figures gravées des parois du Bayit — keruvim, timorot, fleurons, sur les murs
d'or, les vantaux du Heikhal et les jambages des portes des cours — `modele/beit_hamikdash_gravures.py`
(~5 s) compose l'atlas de modelé `visite/matieres/gravures_3072.webp` **et** `gravures.json`,
la silhouette de chaque figure tracée sur la carte même, à partir des tuiles taillées
de `modele/gravures/` (keruv et palmette des murs et des vantaux, timora des jambages, fleuron, bouton : des bas-reliefs rendus par gpt-image-2 sur fal.ai,
versionnés parce qu'un modèle ne rend jamais deux fois la même image — la luminance donne le
modelé, la distance au bord le volume). Le blockout **lit ce JSON** pour poser chaque
figure à sa silhouette — en saillie sur l'or du Bayit, taillée dans la pierre des jambages —, une face dont les UV visent la tuile ; sans lui il s'arrête net.
La rasterisation commune aux deux cartes est `modele/beit_hamikdash_carte.py`.

```bash
$BLENDER -b -P modele/beit_hamikdash_gravures.py                        # l'atlas, depuis modele/gravures/
$BLENDER -b -P modele/beit_hamikdash_gravures.py -- --guides            # redessine les guides (modele/gravures/guides/)
$BLENDER -b -P modele/beit_hamikdash_gravures.py -- --tailler timora    # fait retailler une tuile (~0,08 $, FAL_AI_KEY)
```

Le guide d'un motif est son dessin procédural — composition, iconographie, cadrage —
ombré ; c'est lui que le modèle retaille, avec l'esquisse validée du motif quand
`modele/gravures/esquisses/` en a une. Le keruv et la palmette n'ont pas de guide : leur esquisse seule
en porte la composition (`ESQUISSES`). Changer un motif, c'est corriger son guide ou
son prompt (`MOTIFS`), retailler, regarder la tuile, puis recomposer l'atlas et reconstruire.

`FOULE = True` dans `modele/blockout/primitives/parametres.py` ajoute les figures de Yom Kippour : le peuple dans
l'Ezrat Israël, les cohanim dans l'Ezrat Kohanim, les Léviim et leurs instruments sur
le Doukhan, les masses de l'Ezrat Nashim et du Har HaBayit. `False` (défaut) ne bâtit
que l'architecture : 9 178 objets contre 18 913.

## Exporter la visite 3D

```bash
$BLENDER -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_visite.py
$BLENDER -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_plan.py [-- heikhal sous_terrain]
open visite/index.html
```

Le plan se rend à part, ~20 s pour les cinq cadrages : une caméra orthographique au-dessus
de chacun, tranchée à la hauteur `coupe` pour le Heikhal et les souterrains. Les caméras
du film sont liées aux repères de la timeline ; le script les en détache, sinon le rendu
prendrait le plan du film au lieu du plan du dessus. Pour les souterrains, `caches` retire
sol, podium, Heil et relief, `plancher` coupe tout sous le fond des tunnels : ils sortent
sur fond transparent, et la visite pose dessous le plan `dessous` (l'Azara) pâli.

Ce script **lit** le .blend sauvegardé : il fusionne les volumes par concept — les
milliers de volumes de dix collections deviennent 68 maillages — et écrit `visite/temple.glb`
avec `visite/reperes.json`. Le lien géométrie ↔ encyclopédie passe par
`visite/concepts.json`, où chaque concept déclare les préfixes de noms d'objets qui
lui appartiennent. Un ajout au blockout que `concepts.json` ne déclare pas ressort en
fin de sortie sous « volumes sans concept » : c'est la liste de ce qu'il reste à
nommer.

L'export **cuit l'occlusion du ciel** avant d'aplatir les matières
(`modele/beit_hamikdash_occlusion.py`) : chaque concept d'architecture — aire ≥ 50 m², au moins 10
texels par face, hors Kodesh HaKodashim qui a sa pénombre — perd d'abord ses faces collées
contre une autre, ou les fait reculer d'1 cm si le recouvrement n'est que partiel (cachées, elles
cuisaient noires), puis reçoit une couche UV `Occlusion` et une carte `visite/occlusion/<concept>.webp`,
que `reperes.json` liste sous `occlusion` et que la visite pose en `aoMap`. Cuite au double
puis réduite en WebP à perte (`cwebp` sur le PATH), portée 8 m, 3 m dans le Heikhal où la
sonde de `visite/sonde.js` écarte déjà le ciel. C'est l'essentiel du temps de l'export :

```bash
$BLENDER -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_visite.py -- --sans-occlusion   # itération rapide
```

Sans cuisson, le .glb sort sans couche `Occlusion` et `reperes.json` sans cartes : la visite
reste cohérente, simplement sans occlusion cuite. À relancer sans l'option avant de publier.

`-- --sans-recuire` ne cuit rien non plus mais garde la carte de chaque concept que la scène n'a pas
changé : seuls les concepts retouchés sortent sans carte, jusqu'au prochain `--recuire`.

Un concept peut cuire sa **lumière indirecte** à la place de son occlusion : le ciel vu de la
visite (ramené au tiers du soleil au sol, `DIFFUS`) et tout ce qui rebondit, soleil compris,
sur la même couche UV. Carte `visite/lumiere/<concept>.webp` (irradiance ÷ `echelle`, en sRGB),
listée sous `lumiere` dans `reperes.json`, posée en `lightMap` : elle remplace dans `matieres.js`
l'hémisphère, le diffus de l'environnement et l'occlusion. Le soleil direct reste calculé.

Toute cuisson — ciblée (`--recuire`) ou complète (`--lumiere tout`) — passe par le skill
**cuisson** : il dit quoi recuire après une retouche, et qu'une seule cuisson tourne à la fois.

## Les figurants

`modele/beit_hamikdash_figures.py` lit le .blend et écrit une **troupe** : `visite/<troupe>.glb` et `visite/<troupe>.json`
(emprises et vues, une par rôle plus les familles `cohanim` et `leviim`, que la visite ajoute à `reperes.json`).
Chaque rôle porte le nom de son concept — `zerika`, `leviim_3`, `anshei_maamad_1` — et c'est par ce nom que la visite
ouvre sa fiche au clic. Rien n'entre dans le .blend ni dans `temple.glb` : le film ne les voit pas.

Neuf troupes (`TROUPES`) ; la visite libre charge `figures`, chaque parcours la sienne (`troupe` dans `parcours.json`),
à la première demande :

| Troupe | Rôles | Qui |
|---|---|---|
| `figures` | `roles_de_la_visite()`, 5 | la zerika, deux Léviim, un anshei ma'amad, le Lévi de garde à Nikanor |
| `figures_tamid` | `roles_du_tamid()`, 22 | les gestes du tamid du matin, douze Léviim, deux enfants, deux anshei ma'amad |
| `figures_kippour` | `roles_kippour()`, 39 | le Cohen Gadol une fois par étape du seder ha'avoda — habits d'or (`bigdei_zahav_*`) ou de lin (`bigdei_lavan_*`), taureau (`modele/shor.blend`), boucs (`modele/seir.blend`), kalpi, ma'hta, mizrak, sefer —, les anciens du Beit Din et ceux de la kehouna, les tenants du drap, le segan et le chef de maison, ceux qui passent le rouleau, cinq cohanim et sept Israélites prosternés |
| `figures_shoeva` | `roles_shoeva()`, 26 | la nuit de l'Ezrat Nashim : Léviim des quinze marches, trompettes, ronde aux torches |
| `figures_pessah` | `roles_pessah()`, 37 | le korban Pessa'h : le deuxième groupe et ses agneaux, les rangées de bazikhin d'or et d'argent, la she'hita et le sang de main en main, le Hallel des Léviim, les crochets et la baguette, le magis, le troisième groupe assis sur le 'Heil |
| `figures_bikkourim` | `roles_bikkourim()`, 26 | les porteurs et le taureau aux cornes dorées, les Léviim d'« Aromimkha », la lecture et la tenoufa, les corbeilles et les tourterelles |
| `figures_souccot` | `roles_souccot()`, 13 | Souccot au matin : la tzelo'hit à Sha'ar HaMayim, la libation de l'eau, les aravot sur le yessod, le tour de l'autel |
| `figures_hakhel` | `roles_hakhel()`, 29 | Hakhel : le roi sur la bima de bois (`sol_porte`), assis ou debout, Agrippas, le rouleau de main en main, les hommes et les enfants autour, les femmes à la gezuztra |
| `figures_nazir` | `roles_nazir()`, 6 | le nazir au foyer de sa lishka, le metzora au mikve puis sur le seuil de Nikanor, le sang à l'oreille, les sept aspersions d'huile |

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_figures.py                            # la visite libre
/Applications/Blender.app/Contents/MacOS/Blender -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_figures.py -- --troupe figures_tamid  # un quart d'heure
/Applications/Blender.app/Contents/MacOS/Blender -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_figures.py -- --troupe figures_kippour zerika   # un essai
```

Un essai réécrit le .glb de sa troupe avec ses seuls rôles : relancer la troupe entière avant de committer.

Une troupe peut jouer plusieurs fois le même homme : chaque étape d'un parcours dit ses `figurants` (`parcours.json`,
noms de rôles ou de concepts) et la visite ne montre qu'eux — le Cohen Gadol de Kippour a quatorze rôles, jamais deux à
la fois. `le_cohen_gadol(nom)` leur donne une seule stature, un seul teint (`Humain(…, qui=)`) et une seule peau.
Le bouc se regénère à part (`$BLENDER -b -P modele/beit_hamikdash_seir.py`, quelques secondes), avant la troupe de Kippour.

Torches et trompettes ne sont pas liées à la peau : `Accessoire` les anime objet par objet, et la visite allume la
tête de chaque `*_avouka`.

Corps, peaux, yeux, cheveux, barbes et vêtements viennent de MakeHuman (extension MPFB) : la
kutonet est la robe de moine `donitz_monk_robe` (CC0) sans pèlerine ni cordon, la robe et le
voile de la fidèle `punkduck_medieval_dress` et `elvs_charity_veil1` (CC BY), teints par
`reteindre`. Avnet, migba'at, kippot, talith (étole drapée par simulation) et instruments sont
générés par le script. Une fois par machine :

```sh
/Applications/Blender.app/Contents/MacOS/Blender --online-mode -c extension install mpfb --enable
```

puis décompresser dans `~/Library/Application Support/Blender/5.2/extensions/.user/blender_org/mpfb/data` :
`https://files2.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip`
et, pour les barbes, `https://files2.makehumancommunity.org/asset_packs/bodyparts05/bodyparts05_cc0.zip`.
Les trois vêtements se copient seuls dans `data/clothes/`, depuis `suits02/suits02_cc0.zip`,
`dress03/dress03_cc-by.zip` et `hats03/hats03_cc-by.zip` (même adresse, `asset_packs/`).

## Détails de plomberie

- **Tout après `--`** va aux scripts, pas à Blender. Sans `--`, les arguments sont
  lus par Blender lui-même et le script ne voit rien.
- **Le bruit de Blender** (bannière, `DeprecationWarning`, `Read blend`) noie la
  sortie utile : filtrer avec
  `2>&1 | grep -vE "Deprecation|use_nodes|Read blend|Blender quit|^Blender 5"`.
- **`-b`** (background, sans interface) est obligatoire ici : sans lui Blender ouvre
  une fenêtre et n'en sort pas.
- **Pas de `bpy.ops` pour créer de la géométrie** dans le blockout : chaque appel
  d'opérateur réévalue le graphe de dépendances, coût quadratique en nombre d'objets.
  Les volumes se posent en `bpy.data` via les helpers `box`, `cyl`, `cone`, `sphere`,
  `prism`, `tore`, `cyl_between` (`modele/blockout/primitives/volumes.py`) — s'il manque une
  forme, écrire un helper de plus, pas un opérateur.
- **1 ama = `AMA` mètres**, et le .blend porte la valeur en propriété de scène
  (`scene["AMA_metres"]`). Les helpers convertissent : **tout se donne en amot**
  dans le script, jamais en mètres.
