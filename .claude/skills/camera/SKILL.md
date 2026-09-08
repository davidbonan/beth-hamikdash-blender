---
name: camera
description: Pose une caméra dans la scène Blender du Beit HaMikdash et en exporte la première et la dernière image, prêtes pour la stylisation (fal-retouche, fal-video) puis l'animation. À utiliser dès qu'il s'agit de cadrer quelque chose dans le Temple — « ajoute un plan sur la rampe », « je veux filmer le Kodesh HaKodashim », « fais un travelling dans le Heikhal », « une grue au-dessus de l'Azara », « rends les frames du plan 3 », « ce plan passe-t-il en i2v », « supprime ce plan », « liste les plans ».
---

# Poser un plan

```
python3 .claude/skills/camera/camera.py ajouter --nom CAM_04_Rampe --focale 35 \
    --duree 12 --camera "-38,-62,3" "-38,-57,3" --cible "-38,-28,9"
```

Un plan est un nom, une focale, une durée, et deux courses en amot : celle de
l'objectif (`--camera`) et celle du point qu'il vise (`--cible`). La caméra regarde
sa cible en permanence — un panoramique se décrit en bougeant la cible, pas la
caméra.

| Points donnés | Ce que ça fait |
|---|---|
| un seul | ne bouge pas |
| deux | une droite, à vitesse constante |
| plus | une polyligne : orbite, courbe de grue, trajectoire dans une allée |

`--orbite "cx,cy,z,rayon,deg_debut,deg_fin"` écrit la polyligne d'une course
circulaire à la place de `--camera` — angle 0 = est, positif vers le nord.

Le repère est celui du blockout : **+X est, +Y nord, +Z haut**, origine au mur est de
l'Azara sur l'axe du Heikhal, au niveau du sol de la cour. **Tout est en amot**
(1 ama = 0,48 m). Les sols : Har HaBayit -16, Ezrat Nashim -10, Azara 0, Oulam et
Heikhal +6.

## Les quatre commandes

| Commande | Ce qu'elle fait |
|---|---|
| `lister` | les plans déclarés, leur focale, leur durée |
| `ajouter` | déclare le plan **et** rend ses deux images clés **et** mesure son recouvrement |
| `rendre [--nom X]` | rebâtit la scène et rend les images clés (tous les plans sans `--nom`) |
| `supprimer --nom X` | retire le plan de la déclaration |

Options d'`ajouter` et de `rendre` : `--planche` rend en 640 × 360 sans carte de
profondeur (repérage rapide), `--sans-rendu` déclare sans lancer Blender,
`--remplacer` écrase un plan du même nom — c'est ainsi qu'on corrige un cadrage.

## Où ça atterrit

`renders/blockout/<caméra>_debut.png`, `_fin.png`, et leurs `_profondeur.png`
en 1920 × 1080. Ce sont exactement les entrées du skill **fal-video** :

```bash
python3 .claude/skills/fal-video/fal_image.py --camera CAM_04_Rampe --frame debut \
    --prompt "..." --seed 4041
python3 .claude/skills/fal-video/fal_image.py --camera CAM_04_Rampe --frame fin \
    --prompt "..." --seed 4041
python3 .claude/skills/fal-video/fal_video.py --camera CAM_04_Rampe \
    --depart renders/style/..._debut_....png --fin renders/style/..._fin_....png \
    --prompt "the camera rises along the ramp"
```

## Lire la mesure avant de payer une génération

`ajouter` et `rendre` finissent par le tableau de
`beit_hamikdash_analyse_plans.py`. Un image-to-video à deux frames n'interpole que ce
que les deux images ont en commun ; ce que la frame de fin montre et que celle de
début ne montrait pas, le modèle doit l'inventer.

| Colonne | Ce qu'elle dit |
|---|---|
| **couvert** | part de la frame de fin déjà visible au début. **Sous 40 %, couper le plan en deux.** |
| **zoom** | de combien le décor commun grossit. Au-delà de 2,5×, la matière est à inventer. |
| **cadre/s** | glisse de l'image. Au-delà de 0,06, le mouvement n'est plus lent. |
| **gardé** | part de la frame de début encore visible à la fin. Basse sur tout travelling avant — ce n'est pas un défaut. |

Un plan qui ne renvoie aucune géométrie a sa caméra dans un mur.

## Vérifier ce que le cadre contient vraiment

Avant de styliser, `beit_hamikdash_inspect.py` répond sur la scène sauvegardée, en
une seconde, sans rien reconstruire (skill **blender**) :

```bash
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --voit CAM_04_Rampe
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --camera CAM_04_Rampe
```

`--voit` tire une grille de rayons dans le cadre en tenant compte de l'occultation :
c'est la seule réponse fiable à « est-ce que ce plan montre X ». Deux erreurs qu'il
attrape à tous les coups : une caméra posée dans un mur ou dans une silhouette, et un
sujet qu'un volume intermédiaire masque entièrement — l'autel de 10 amot cache tout
ce qui est derrière lui depuis le sol de la cour.

## La déclaration est le fichier

`cameras.json`, à la racine, est la source ; le .blend en est l'artefact, réécrit à
chaque rendu. Une caméra ajoutée à la main dans l'interface de Blender est perdue à
la reconstruction suivante. `camera.py` écrit ce fichier, mais il s'édite aussi
directement — c'est du JSON, un objet par plan, `capteur` et `clip_fin` en champs
facultatifs.

L'ordre des plans dans le fichier est celui de la timeline : chaque plan occupe
`duree_s × 24` images à la suite du précédent.
