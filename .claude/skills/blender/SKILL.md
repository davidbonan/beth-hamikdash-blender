---
name: blender
description: Pilote la scène Blender du Beit HaMikdash en ligne de commande headless — reconstruire le blockout après avoir touché au script, inspecter la scène, exporter la visite 3D. À utiliser dès qu'il faut regénérer la scène ou répondre à une question sur elle — « où est le Doukhan », « regénère la scène », « la fenêtre du Beit Avtinas montre-t-elle la cour », « quelle taille fait cet objet dans la scène », « refais la visite ». Pour poser une caméra et en exporter les images clés, c'est le skill camera.
---

# Blender en ligne de commande

```
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
```

## L'invariant : le script est la source, le .blend est l'artefact

`beit_hamikdash_blockout.py` **construit** la scène ; `beit_hamikdash.blend` en est
la sortie. Toute modification faite à la main dans l'interface de Blender est perdue
à la reconstruction suivante. Une correction se porte donc **dans le script**, jamais
dans le .blend. Même chose pour les caméras, qui vivent dans `cameras.json`.

Corollaire : le .blend sur le disque date du dernier **export** —
`beit_hamikdash_export.py` est le seul script qui appelle `wm.save_mainfile`. Le
blockout seul, en headless, jette sa géométrie en quittant. Pour reconstruire *et*
sauvegarder, il faut donc chaîner blockout, caméras et export dans la même instance.

## Les huit scripts

| Script | Ce qu'il fait | Écrit |
|---|---|---|
| `beit_hamikdash_blockout.py` | construit le Temple, son pays et la foule du jour | rien (mémoire) |
| `beit_hamikdash_cameras.py` | pose les plans déclarés dans `cameras.json` | rien (mémoire) |
| `beit_hamikdash_export.py` | images clés couleur + profondeur, ou planche de contrôle | `renders/blockout/` ou `renders/planche/`, **et le .blend** |
| `beit_hamikdash_analyse_plans.py` | recouvrement début/fin de chaque plan, glisse de l'image | rien |
| `beit_hamikdash_inspect.py` | **lit** la scène sauvegardée et répond | rien |
| `beit_hamikdash_visite.py` | exporte la visite 3D du navigateur | `visite/temple.glb`, `visite/reperes.json` |
| `beit_hamikdash_figures.py` | figurants de la visite, vêtus et animés (gestes : `beit_hamikdash_gestes.py`) | `visite/figures.glb`, `visite/figures.json` |
| `beit_hamikdash_plan.py` | rend le plan de la visite vu du dessus, une image par cadrage | `visite/plans/*.webp`, `visite/plan.json` |

Les trois du milieu sont pilotés par le skill **camera**, qui les chaîne dans une
seule commande. Ce qui suit sert quand on veut les lancer soi-même.

## Où atterrissent les sorties

Un dossier par étape du pipeline, et **rien à la racine de `renders/`** :

| Dossier | Écrit par | Contenu |
|---|---|---|
| `renders/blockout/` | `beit_hamikdash_export.py` | couleur + profondeur 1920 × 1080, entrées de l'i2i |
| `renders/planche/` | `beit_hamikdash_export.py -- --planche` | contrôle 640 × 360 + `planche.html` + `planche.jpg` (mosaïque du README, versionnée) |
| `renders/style/` | `fal_image.py` | images clés stylisées |
| `renders/video/` | `fal_video.py` | mp4 |

Les chemins sont des constantes : `SOUS_DOSSIER_BLOCKOUT` / `SOUS_DOSSIER_PLANCHE`
dans l'export, `DOSSIER_IMAGES` / `DOSSIER_SORTIE` dans les scripts fal. En déplacer
un se fait là, pas en déplaçant les fichiers.

## Répondre à une question sur la scène — `inspect`

C'est le point d'entrée par défaut. Il ne reconstruit rien : il ouvre le .blend et
répond en une seconde. Ne pas mettre `-P beit_hamikdash_blockout.py` devant.

```bash
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --scene
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --objets Doukhan
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --camera CAM_03_Heikhal
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --voit heikhal
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --voit heikhal fin
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --foule 01
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

Après toute modification de `beit_hamikdash_blockout.py`. Compte ~5 s.

```bash
# vérifier que le script tourne (rien n'est sauvegardé)
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_blockout.py

# reconstruire ET sauvegarder le .blend (c'est l'export qui sauvegarde)
$BLENDER -b beit_hamikdash.blend \
    -P beit_hamikdash_blockout.py \
    -P beit_hamikdash_cameras.py \
    -P beit_hamikdash_export.py -- --planche
```

Le blockout annonce en dernière ligne son compte d'objets et de collections — la
vérification la plus rapide qu'il n'a rien cassé.

`FOULE = True` en tête du blockout ajoute les figures de Yom Kippour : le peuple dans
l'Ezrat Israël, les cohanim dans l'Ezrat Kohanim, les Léviim et leurs instruments sur
le Doukhan, les masses de l'Ezrat Nashim et du Har HaBayit. `False` (défaut) ne bâtit
que l'architecture : 9 178 objets contre 18 913.

## Exporter la visite 3D

```bash
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_visite.py
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_plan.py [-- heikhal sous_terrain]
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

## Les figurants

`beit_hamikdash_figures.py` lit le .blend et écrit `visite/figures.glb` et `visite/figures.json`
(emprises et vues de `cohanim`, `leviim`, `fideles`, que la visite ajoute à `reperes.json`).
Rien n'entre dans le .blend ni dans `temple.glb` : le film ne les voit pas.

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend -P beit_hamikdash_figures.py                         # les 22 rôles, une douzaine de minutes
/Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend -P beit_hamikdash_figures.py -- cohanim_1 fideles_3   # un essai
```

Un essai réécrit `figures.glb` avec ses seuls rôles : relancer les 22 avant de committer.
Rôles, places et gestes se déclarent dans `roles()`.

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
  `prism`, `tore`, `cyl_between` — s'il manque une forme, écrire un helper de plus,
  pas un opérateur.
- **1 ama = `AMA` mètres**, et le .blend porte la valeur en propriété de scène
  (`scene["AMA_metres"]`). Les helpers convertissent : **tout se donne en amot**
  dans le script, jamais en mètres.
