---
name: blender
description: Pilote la scène Blender du film (blockout, export des images clés, inspection de la scène) en ligne de commande headless. À utiliser dès qu'il faut regénérer le blockout après avoir touché au script, exporter les frames ou la planche de contrôle, mesurer le recouvrement des plans, ou simplement répondre à une question sur la scène — « où est le Doukhan », « que voit la caméra du plan 9 », « la fenêtre du Beit Avtinas montre-t-elle la cour », « regénère la scène », « refais la planche », « exporte le plan 12 ».
---

# Blender en ligne de commande

```
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
```

## L'invariant : le script est la source, le .blend est l'artefact

`beit_hamikdash_blockout.py` **construit** la scène ; `beit_hamikdash.blend` en est
la sortie. Toute modification faite à la main dans l'interface de Blender est perdue
à la reconstruction suivante. Une correction se porte donc **dans le script**, jamais
dans le .blend.

Corollaire : le .blend sur le disque date du dernier **export** —
`beit_hamikdash_export.py` est le seul script qui appelle `wm.save_mainfile`. Le
blockout seul, en headless, jette sa géométrie en quittant. Pour reconstruire *et*
sauvegarder, il faut donc chaîner blockout puis export dans la même instance.

## Les quatre scripts

| Script | Ce qu'il fait | Écrit |
|---|---|---|
| `beit_hamikdash_blockout.py` | construit toute la scène + 19 caméras + marqueurs | rien (mémoire) |
| `beit_hamikdash_export.py` | images clés couleur + profondeur, ou planche de contrôle | `renders/blockout/` ou `renders/planche/`, **et le .blend** |
| `beit_hamikdash_analyse_plans.py` | recouvrement début/fin de chaque plan, glisse de l'image | rien |
| `beit_hamikdash_inspect.py` | **lit** la scène sauvegardée et répond | rien |

## Où atterrissent les sorties

Un dossier par étape du pipeline, et **rien à la racine de `renders/`** :

| Dossier | Écrit par | Contenu |
|---|---|---|
| `renders/blockout/` | `beit_hamikdash_export.py` | couleur + profondeur 1920 × 1080, entrées de l'i2i |
| `renders/planche/` | `beit_hamikdash_export.py -- --planche` | contrôle 640 × 360 + `planche.html` |
| `renders/style/` | `fal_image.py` | images clés stylisées |
| `renders/video/` | `fal_video.py` | mp4 |
| `renders/archive/` | personne | générations périmées, gardées, jamais relues |

Les chemins sont des constantes : `SOUS_DOSSIER_BLOCKOUT` / `SOUS_DOSSIER_PLANCHE`
dans l'export, `DOSSIER_IMAGES` / `DOSSIER_SORTIE` dans les scripts fal. En déplacer
un se fait là, pas en déplaçant les fichiers.

## Répondre à une question sur la scène — `inspect`

C'est le point d'entrée par défaut. Il ne reconstruit rien : il ouvre le .blend et
répond en une seconde. Ne pas mettre `-P beit_hamikdash_blockout.py` devant.

```bash
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --scene
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --objets Doukhan
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --camera 9a
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --voit 3
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --voit 9a fin
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --foule 1
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

Le numéro de plan s'écrit comme on veut : `9`, `09`, `9a`, `CAM_09A`, ou le nom complet.

## Reconstruire la scène

Après toute modification de `beit_hamikdash_blockout.py`. Compte ~5 s.

```bash
# vérifier que le script tourne (rien n'est sauvegardé)
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_blockout.py

# reconstruire ET sauvegarder le .blend (c'est l'export qui sauvegarde)
$BLENDER -b beit_hamikdash.blend \
    -P beit_hamikdash_blockout.py \
    -P beit_hamikdash_export.py -- --planche
```

Le blockout annonce en dernière ligne son compte d'objets, de caméras et d'images —
la vérification la plus rapide qu'il n'a rien cassé.

## Exporter les images clés

```bash
# planche de contrôle des 19 plans, 640 × 360 + index HTML
$BLENDER -b beit_hamikdash.blend \
    -P beit_hamikdash_blockout.py -P beit_hamikdash_export.py -- --planche
open renders/planche/planche.html

# production : couleur + profondeur, 1920 × 1080, les 19 plans
$BLENDER -b beit_hamikdash.blend \
    -P beit_hamikdash_blockout.py -P beit_hamikdash_export.py

# un ou plusieurs plans seulement
$BLENDER -b beit_hamikdash.blend \
    -P beit_hamikdash_blockout.py -P beit_hamikdash_export.py -- CAM_09A_Heikhal_Kelim
```

L'export ne laisse visible que la collection de sujet du plan rendu (`75_PlanNN`) :
une silhouette d'un autre plan restée dans le cadre devient un objet inventé par le
styliseur.

## Mesurer les plans

```bash
$BLENDER -b beit_hamikdash.blend \
    -P beit_hamikdash_blockout.py -P beit_hamikdash_analyse_plans.py
```

Colonne « couvert » = la part de la frame de fin déjà visible au début. Sous 40 %,
le plan est à couper en deux. Colonne « cadre/s » = la glisse de l'image ; au-delà
de 0,06, le mouvement n'est plus lent.

## Détails de plomberie

- **Tout après `--`** va aux scripts, pas à Blender. Sans `--`, les arguments sont
  lus par Blender lui-même et le script ne voit rien.
- **Le bruit de Blender** (bannière, `DeprecationWarning`, `Read blend`) noie la
  sortie utile : filtrer avec
  `2>&1 | grep -vE "Deprecation|use_nodes|Read blend|Blender quit|^Blender 5"`.
- **`-b`** (background, sans interface) est obligatoire ici : sans lui Blender ouvre
  une fenêtre et n'en sort pas.
- **Pas de `bpy.ops` pour créer de la géométrie** dans le blockout : chaque appel
  d'opérateur réévalue le graphe de dépendances, coût quadratique en nombre d'objets
  (la scène en a 4692). Les volumes se posent en `bpy.data` via les helpers `box`,
  `cyl`, `cone`, `sphere`, `prism`, `tore`, `cyl_between` — s'il manque une forme,
  écrire un helper de plus, pas un opérateur.
- **1 ama = `AMA` mètres**, et le .blend porte la valeur en propriété de scène
  (`scene["AMA_metres"]`). Les helpers convertissent : **tout se donne en amot**
  dans le script, jamais en mètres.
