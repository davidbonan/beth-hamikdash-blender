---
name: fal-video
description: Génère les images clés stylisées et le plan vidéo du film sur fal.ai (édition du blockout par IA, puis image-to-video première + dernière frame) en ligne de commande, sans passer par le site fal.ai. À utiliser dès qu'il faut styliser une frame clé, animer un plan, relancer une génération, changer de modèle ou récupérer un mp4 — « stylise le plan 9 », « génère le plan 9 », « anime CAM_08 », « refais le plan 12 en kling ».
---

# Génération fal.ai

Deux scripts, deux étapes du pipeline (README) :

| Script | Étape | Sortie |
|---|---|---|
| `fal_image.py` | 2 — images clés stylisées à partir du blockout | `renders/style/` |
| `fal_video.py` | 4 — image-to-video première + dernière frame | `renders/video/` |

La plomberie commune (clé API, téléversement CDN, file d'attente, lecture de
`prompts_par_plan.md`) est dans `fal_commun.py`.

**Toujours passer `--simulation` d'abord** pour relire le prompt et le coût avant
de payer une génération.

## Images clés

```bash
python3 .claude/skills/fal-video/fal_image.py --plan 9a --frame debut --seed 90901
python3 .claude/skills/fal-video/fal_image.py --plan 9a --frame fin --seed 90901
```

| Option | Défaut | Effet |
|---|---|---|
| `--plan N` | requis | plan 1-15, lettre comprise pour un plan coupé (`9a`) ; détermine la caméra, le prompt et la force |
| `--frame debut\|fin` | `debut` | quelle frame clé styliser |
| `--modele` | `gpt2` | voir la table ci-dessous |
| `--seed N` | tirée au hasard | **la même seed pour les deux frames d'un plan** ; à noter dans le journal |
| `--controle a b c` | `1.0` | poids du conditionnement des modèles `depth*` ; une valeur = une variante |
| `--force` | ligne **Force** du plan | force i2i (`depth-i2i` uniquement) |
| `--etapes` / `--guidage` | 28 / 3.5 | `num_inference_steps`, `guidance_scale` (modèles Flux) |

Entrées : `renders/blockout/CAM_xx_{debut,fin}.png` (rendu couleur) et `..._profondeur.png`
(carte de profondeur), produits par `beit_hamikdash_export.py`.

**Les plans coupés portent une lettre** : `--plan 9a`, `--plan 9b`, et de même pour
7, 13 et 14. Le numéro nu d'un plan coupé est refusé plutôt que deviné.

### Deux familles de modèles, et pourquoi l'édition gagne

**Édition** (`gpt2`, `nano-pro`, `nano2`, `seedream`, `seedream-lite`, `flux2-pro`) : le rendu Blender part en
entrée avec une instruction « repeins sans rien déplacer » (bloc ÉDITION de
`prompts_par_plan.md`). La géométrie de la Mishna est conservée par construction —
c'est la seule famille qui passe le contrôle du plan 9.

**Conditionnement par la profondeur** (`depth`, `depth-i2i`, `pro-depth`, `canny`) :
le modèle regénère l'image en suivant la carte de profondeur. Mesuré sur le plan 9 :
les ustensiles, trop petits et trop peu contrastés à 15-25 m, sont réinventés à chaque
fois. À garder pour les plans de matière et de ciel, pas pour les plans contrôlés.

| `--modele` | Endpoint | Prix | Mesuré |
|---|---|---|---|
| `gpt2` | `openai/gpt-image-2/edit` | ~0,08 $ (facturé au token, `quality: high`) | **retenu** : le meilleur verrou de cadrage des six. Sortie à l'aspect de l'entrée, 1920 × 1072 |
| `nano-pro` | `fal-ai/nano-banana-pro/edit` | 0,15 $/image | second : tient les trois plans testés, mais invente une colonnade sur une façade plane. Sortie 2752 × 1536 |
| `nano2` | `fal-ai/nano-banana-2/edit` | 0,08 $ | recompose : mur devenu pylône isolé au plan 4, **taureau supprimé** au plan 5 |
| `seedream` | `bytedance/seedream/v5/pro/edit` | 0,0675 $ | visages de face au premier plan ; Oulam repeint en temple grec au plan 5 |
| `seedream-lite` | `fal-ai/bytedance/seedream/v5/lite/edit` | ~0,03 $ | keffiehs dans la foule, colonnade gréco-romaine inventée, le moins détaillé |
| `flux2-pro` | `fal-ai/flux-2-pro/edit` | 0,03 $ | ramène le site actuel — tuiles rouges, paraboles, voitures — et vide les plans de toute figure |
| `depth` | `fal-ai/flux-control-lora-depth` | ~0,04 $ | à `--controle 1.0` le style est là, la géométrie flotte ; 1.2 → granité doré ; 1.5 → bruit |
| `depth-i2i` | `.../image-to-image` | ~0,04 $ | inutile : sortie = blockout à peine retouché, à 0,50 comme à 1,00 de force |
| `pro-depth` / `pro-depth-rendu` | `fal-ai/flux-pro/v1/depth` | ~0,05 $ | arc brisé, statues, tableaux, foule |
| `canny` | `fal-ai/flux-control-lora-canny` | ~0,04 $ | belle lumière, mobilier inventé, keruv figuré |
| `general-depth` | `fal-ai/flux-general` + ControlNet Union | — | **indisponible** : « Could not load pipeline » sur 5 chemins de poids (InstantX, Shakker-Labs, jasperai, XLabs). Le compte ne charge pas de ControlNet externe |

Les six lignes de la famille édition ont été mesurées ensemble sur les frames de début
des plans 1, 4 et 5, à seed commune par plan ; les lignes `depth*` datent du plan 9.

`gpt2` n'a **ni seed ni prompt négatif** : la seed passée est ignorée, elle ne sert
qu'à nommer le fichier. Deux appels identiques ne donnent donc pas la même image, et
la frame de fin d'un plan quasi immobile se **dérive** de la frame de début (voir plus
bas) plutôt que de se regénérer.

### Ce que le plan 1 a montré sur le cadrage

Le verrou de cadrage est ce qui sépare les modèles, pas le rendu. Sur une façade
**plane** dans le blockout, `gpt2` est le seul des six à la laisser plane : les autres
y collent une colonnade à chapiteaux dorés. Même chose au plan 4, où le mur qui
remplit le cadre reste un mur chez `gpt2` et devient un pylône isolé sur fond de ciel
chez `nano2`.

En échange, `gpt2` sort en 1920 × 1072 quand `nano-pro` monte à 2752 × 1536. Sans
importance pour la suite : les modèles i2v rendent en 1080p.

### Trois pièges appris sur le plan 9

1. **Aucun modèle d'édition ne prend de prompt négatif.** Le script plie donc le bloc
   NÉGATIF dans l'instruction (« Never show any of these: … »). Sans ça, les keruvim du
   parokhet sortent en anges à visage humain.
2. **Une frame dont le cadre ne montre plus la scène du plan a sa propre ligne
   `**Prompt fin**`** dans `prompts_par_plan.md` (le tilt final du plan 9 ne montre que
   le haut du rideau et le plafond). Décrire les kelim quand ils sont hors cadre revient
   à demander au modèle de les réinventer : il refabrique la pièce entière.
3. **Les proxys de sujet doivent sortir du cadre.** Une silhouette d'un autre plan qui
   traîne au fond devient un second candélabre. Chaque plan a désormais sa collection
   de sujet (`75_Plan09`, `75_Plan12`…) et `beit_hamikdash_export.py` ne laisse
   visible que celle du plan qu'il rend. La foule, elle, reste : c'est l'état
   permanent du jour, Léviim du Doukhan compris.

## Quand le rendu couleur ne porte plus rien : `--structure`

Dans un volume fermé — la Stoa du plan 2 — toutes les surfaces du blockout sont
blanches et l'ambiante les met au même gris : la colonnade est **invisible** en couleur
alors qu'elle est nette en profondeur. `--structure` joint la carte de profondeur en
seconde image et dit au modèle d'y lire la géométrie et d'éclairer lui-même.

```bash
python3 .claude/skills/fal-video/fal_image.py --plan 2 --frame debut --structure --seed 20201
```

À réserver aux plans dont le rendu couleur est plat. Les extérieurs (plans 1, 15) n'en
ont pas besoin : le soleil y sculpte déjà les masses.

## Deux inventions à couper d'entrée

- **Le site actuel remonte.** Sur le plan 2, veo a fait apparaître un minaret à balcon,
  une façade de mosquée à arcades, des silhouettes en vêtements modernes et une barrière
  métallique — alors que `minaret` était déjà dans le NÉGATIF. Les modèles vidéo tiennent
  mal les négatifs : il faut un **ancrage positif** (« beyond the colonnade the esplanade
  stays bare pale pavement under open sky, nothing later than the Second Temple ever
  enters the frame »). Le négatif commun a été complété, mais c'est la phrase positive
  qui a réglé le problème.
- **Les ornements inventés.** Bandeaux d'or à anneaux sur chaque fût de la Stoa, venus de
  nulle part. Un négatif propre au plan suffit (`gold bands around the columns, bronze
  rings or hooks on the columns`).

## L'échelle des figures ne se devine pas

Sur le plan 1, les six modèles ont peint la foule du premier plan à **60 px** de haut
quand la géométrie en impose **14** — quatre fois trop grand, avec des maisons à toit
plat deux fois plus petites que les hommes debout devant elles.

La cause n'est pas le modèle, c'est une ligne `**Édition**` qui décrivait une foule
**hors champ**. Le test qui tranche, et qu'il faut faire avant d'accuser un modèle :

```bash
# combien de figures ce plan voit-il vraiment, et sur combien de pixels
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --foule 1
```

Mesuré sur CAM_01 début, sur 1621 figures : **0 / 462** sur l'esplanade — le mur est
du Har HaBayit les cache toutes —, 24/576 à l'Ezrat Nashim, 9/129 cohanim, 2/12
Léviim. **35 figures visibles, médiane 12,4 px sur 1080.** À ce compte, le blockout
ne porte aucune référence humaine lisible : tout ce que le modèle peint en foule est
inventé, et il l'invente au cadrage photo. À comparer au plan 4 début, qui en voit 96
à 190 px de médiane — et qui sort juste sans qu'on ait rien à lui dire.

C'est la **médiane** qui compte, pas le maximum : à la fin du plan 4 la caméra
traverse la foule de l'Ezrat Nashim et un bloc frôle l'objectif à 3 000 px.

Deux règles en sortent :

1. **Une ligne `**Édition**` ne nomme que ce que la caméra voit.** Décrire des blocs
   de foule que le mur occulte, c'est demander une foule inventée — exactement le
   piège déjà connu pour les kelim hors cadre du plan 9.
2. **Là où le blockout ne donne pas l'échelle, il faut la dire en chiffres**, et dans
   la ligne `**Édition finale**` où elle tient. Sur le plan 1 : « la façade fait
   100 amot, un homme 3,65, donc un homme = 1/27 de la façade, et aucune figure ne
   dépasse 1/60 de la hauteur d'image ». Après quoi les maisons du premier plan sont
   ressorties à 50 px pour 50 px prédits.

Corollaire pour le blockout : peupler l'esplanade n'aurait rien changé — le mur la
cache. Ajouter de la géométrie qu'aucune caméra ne voit ne corrige jamais un prompt.

## Deux frames, une seule image, ou une coupe

`beit_hamikdash_analyse_plans.py` mesure, pour chaque plan, la part de la frame de
fin **déjà visible au début** — ce qu'elle laisse de côté, le modèle doit l'inventer.
Trois régimes, trois conduites :

| Mesure | Plans | Conduite |
|---|---|---|
| **100 % / caméra fixe** | 6, 15 | **Une seule image + prompt de mouvement.** Deux frames identiques ne donnent rien à interpoler ; le modèle comble en inventant une dérive. Ce qui bouge est dans les corps, la fumée, les tissus — pas dans la caméra |
| **couverture ≥ 40 %** | tous les autres | Deux frames. La frame de fin porte un contenu qu'on veut contrôler (le taureau, la vigne d'or, la porte de Nikanor) et qu'il ne faut pas laisser inventer |
| **couverture < 40 %** | plus aucun | Le plan se coupe dans Blender, il ne se rattrape pas au prompt. C'est ce qui a donné 7a/7b, 9a/9b, 13a/13b, 14a/14b |

Un travelling **avant** garde une couverture haute même quand plus une pierre n'est
commune aux deux frames : l'image d'arrivée est l'agrandissement du centre de l'image
de départ, ce qu'un i2v sait faire. Ce qui tue un plan n'est pas ce qui sort du
cadre, c'est ce qui y entre sans avoir été annoncé — panoramique, relevé, grue qui
franchit un mur.

## Frame de fin : éditer ou dériver

Deux éditions indépendantes de deux blockouts **quasi identiques** ne convergent pas :
sur le plan 1, la façade est ressortie en marbre blanc au début et tout en or à la fin,
avec la même seed et le même prompt. Le modèle n'a aucune mémoire d'un appel à l'autre.

- **Mouvement franc** (dolly + tilt du plan 9) : deux éditions ; la géométrie diffère
  assez pour que chacune tienne debout.
- **Quasi-immobile** (plan 1 : le blockout ne bougeait que de 5 % d'échelle) : **dériver**
  la frame de fin de la frame de début validée, par zoom géométrique. Le facteur est le
  rapport des distances caméra → cible, et la continuité de matière est alors exacte.

```bash
# facteur = |C_debut - cible| / |C_fin - cible|, ici 1,1768
ffmpeg -i renders/style/CAM_01_debut_….png -vf "scale=3239:1808,crop=2752:1536" \
       renders/style/CAM_01_fin_derive_dolly_seed10101.png
```

Corollaire : un travelling qui ne change pas l'échelle d'au moins ~15 % ne se **voit**
pas sur 8 s. Sur le plan 1, les 8 frames extraites du premier essai étaient
indistinguables ; corriger la course dans le blockout, pas au montage.

## Vidéo

### Le contrôle qui précède toute génération

`fal_video.py` refuse de générer tant que `--controle-fait` n'est pas passé, et affiche
d'abord le bloc **CONTRÔLE AVANT VIDÉO** de `prompts_par_plan.md` — deux passes sur les
**deux frames stylisées** :

1. **Positions** — frame stylisée à côté du blockout de la même caméra, objet par objet :
   même place, même échelle, même orientation, même nombre, même cadrage.
2. **Zones d'accès** (fiche technique §12) — pour chaque silhouette : a-t-elle le droit
   d'être là ? Le peuple s'arrête aux 11 amot de l'Ezrat Israël, le Doukhan est aux
   Léviim (douze au moins), l'Ezrat Cohanim et l'entre-Oulam-et-autel aux cohanim,
   l'Oulam et le Heikhal sont **vides** à l'heure de l'encens, le Kodesh HaKodashim
   n'a que le Cohen Gadol.

La raison d'en faire un verrou et pas une consigne : l'i2v n'a aucun plan de correction,
il amplifie la frame de départ. Un objet déplacé y reste huit secondes, et une silhouette
posée dans une zone qui lui est fermée se met à y **marcher** (mesuré sur `seedance`, qui
fait marcher la silhouette du plan 9). Ce qui est en défaut se reprend par ré-édition ou
inpainting de la frame — jamais par un négatif ajouté au prompt vidéo, que les modèles
i2v tiennent mal. `--simulation` affiche le bloc sans rien exiger.

```bash
python3 .claude/skills/fal-video/fal_video.py --plan 9a --duree 8 --controle-fait \
    --depart renders/style/CAM_09A_debut_nano-pro_c1.00_g3.5_seed90901.png \
    --fin renders/style/CAM_09A_fin_nano-pro_c1.00_g3.5_seed90901.png
```

| Option | Défaut | Effet |
|---|---|---|
| `--plan N` | requis | plan 1-15, lettre comprise pour un plan coupé (`9a`) ; détermine la caméra, le prompt et les images |
| `--modele` | `veo-lite` | voir la table ci-dessous |
| `--duree N` | max du modèle | secondes générées |
| `--depart` / `--fin` | `renders/blockout/CAM_xx_{debut,fin}.png` | **pointer sur `renders/style/`** pour animer les frames stylisées |
| `--prompt` | ligne **Mouvement** du plan | remplace le prompt de caméra |
| `--seed N` | — | `veo*`, `seedance` |
| `--controle-fait` | absent | atteste le contrôle positions + zones ; **sans lui, rien n'est généré** |

| `--modele` | Endpoint | Durées | Prix (audio coupé) | Négatif | Mesuré sur le plan 9 |
|---|---|---|---|---|---|
| `veo-lite` | `fal-ai/veo3.1/lite/first-last-frame-to-video` | **8 s seulement** | 0,05 $/s en 1080p | oui | **retenu** : dolly puis tilt exactement comme la ligne Mouvement, kelim qui sortent par le bas, rien d'autre ne bouge, 1920 × 1080 |
| `flux3` | `blackforestlabs/flux-3/first-last-frame-to-video` | 5 à 20 s | 0,29 $/s en 1080p, 0,17 en 720p | non | propre, mais traverse la parokhet en gros plan au milieu du plan ; 3,6 × le prix de `veo-lite` |
| `kling3` | `fal-ai/kling-video/v3/pro/image-to-video` | 3 à 15 s | 0,112 $/s | oui | **écarte les pans du rideau** — une action qui appartient au plan 12 ; sortie en 1928 × 1072 |
| `veo` | `fal-ai/veo3.1/fast/first-last-frame-to-video` | 4, 6, 8 s | 0,10 $/s | oui | même famille que `veo-lite` au double du prix |
| `kling` | `fal-ai/kling-video/o1/image-to-video` | 3 à 10 s | 0,112 $/s | non | travelling le plus lent, architecture stable ; ajoute des flammes sur les portes |
| `h3-turbo` | `minimax/h3-max-turbo/image-to-video` | 5 à 15 s | 0,04 $/s (768p) ; 0,025 en 480p | non | **768p maximum**, et le prompt complet (FIGURES + PLACES) lui fait **peupler le Heikhal** d'une foule de cohanim et d'endeuillés ; réduit à la seule ligne Mouvement il garde la salle vide mais **arrache la parokhet** et la fait battre au plafond vers 4,5 s |
| `seedance` | `fal-ai/bytedance/seedance/v1.5/pro/image-to-video` | 4 à 12 s | 0,052 $/s (720p) | non | dolly propre mais **fait marcher** la silhouette : viole « nothing else moves » |
| `veo-hq` | `fal-ai/veo3.1/first-last-frame-to-video` | 4, 6, 8 s | 0,20 $/s | oui | non testé |

Écartés : `bytedance/seedance-2.5/image-to-video` (0,473 $/s en 720p, dix fois
`veo-lite` pour le même service) et `minimax/h3-max` (768p maximum, comme sa variante turbo).

La famille MiniMax coûte cinq fois moins que `veo-lite` et monte à 15 s, mais aucune de ses
sorties ne dépasse 768p et elle lit le prompt comme un **contenu à peindre**, pas comme une
contrainte : les blocs FIGURES et PLACES, qui tiennent les gens à leur place chez veo, y font
naître les gens eux-mêmes. Un modèle qui ne sait pas lire une interdiction ne peut pas porter
les plans d'intérieur.

`kling3` et `flux3` montent à 15 et 20 s : de quoi couvrir un plan entier au lieu de
générer 8 s et de ralentir au montage. Depuis le découpage en dix-neuf, les plans
font 12 à 33 s et **onze d'entre eux tiennent en 15 s** — `kling3` les couvre d'une
seule génération. Restent le 3, le 5, le 11, le 12 (25 s) et le 15 (33 s), à couvrir
en ralenti ou en deux segments.

## Règles qui valent pour tout le film

Six blocs en tête de `prompts_par_plan.md`, injectés dans **chaque** plan par les deux
scripts. Les modifier là, jamais dans le code.

| Bloc | Ce qu'il tient | Injecté |
|---|---|---|
| **STYLE** | Temple debout, **neuf et intact**, et l'endroit **majestueux** : grand appareil hérodien en gros blocs fraîchement taillés, face lisse à marge ciselée, assises de niveau et joints filiformes, pierre propre — plus l'ancrage « vraie photo 35 mm, jamais un rendu 3D ». Ville alentour habitée | préfixe du prompt image (`STYLE +`) |
| **FIGURES** | La **tenue**, trois classes : le **peuple** en tenue d'aujourd'hui (costume, redingote, kaftan, djellaba), les **Léviim** en lin blanc, les **cohanim et le Cohen Gadol** en bigdei lavan. Tête couverte par kippa, talith ou coiffe de lin — rien d'autre | suffixe image **et** vidéo |
| **PLACES** | **Qui se tient où** : peuple aux cours extérieures et aux 11 amot de l'Ezrat Israël, Léviim sur le Doukhan, cohanim à l'ouest de la marche, Oulam et Heikhal vides sauf le Cohen Gadol | suffixe image **et** vidéo |
| **NÉGATIF** | Interdits : coupole, minaret, site actuel, ruines, tourisme | `negative_prompt` vidéo, replié dans l'instruction d'édition |
| **ÉDITION** | Repeindre sans rien déplacer | préfixe de l'instruction d'édition |
| **CADRAGE** | Verrou de cadre, **en dernier** | fin de l'instruction d'édition |

`FIGURES` et `PLACES` vont aussi au prompt **vidéo** : sans eux l'i2v rhabille les gens
et les fait franchir des frontières que la frame de départ respectait.

Sur les extérieurs, deux ancrages **positifs** restent indispensables — les négatifs
seuls n'ont jamais suffi : « nothing later than the Second Temple ever enters the frame »
pour l'esplanade, et « nothing breaks that skyline: no tower, spire, belfry, minaret,
dome or pointed roof » pour la crête, qui sinon ramène un minaret et le clocher de
l'Ascension.

## La contrainte qui ne tient qu'à la fin : `**Édition finale**`

Le bloc `**Édition**` d'un plan est suivi de FIGURES, PLACES et de toute la liste des
interdits : une consigne qui y est posée se retrouve à ~1 500 caractères de la fin et le
modèle la lâche. Mesuré sur le plan 3 : la bande verticale du Sanctuaire vue par la
fenêtre, décrite dans `**Édition**` comme « une face plane, aucune colonne, aucun
chapiteau », ressortait avec une colonnade à chapiteaux dorés et une corniche à trois
seeds de suite — le journal la portait déjà en réserve.

La même phrase déplacée dans une ligne `**Édition finale**`, que le script injecte entre
les interdits et le CADRAGE, tient du premier coup. À réserver à **une** contrainte par
plan : mise au même endroit, la troisième se dilue à son tour.

## Attention à la dilution

L'instruction du plan 1 a atteint ~2 500 caractères à force d'ajouts, et le modèle a
commencé à **lâcher la clause de cadrage** noyée au milieu : Heikhal décentré et deux
fois trop gros. Remise en **dernière position**, précédée de « LAST AND MOST IMPORTANT,
above every other instruction », elle a retenu. Une contrainte structurelle se met à la
fin, pas au milieu.

## D'où viennent les prompts

`prompts_par_plan.md` est la seule source :

- **prompt image** = bloc STYLE + ligne `**Prompt**` du plan (ou `**Prompt fin**` pour
  la dernière frame quand elle existe) ;
- **instruction d'édition** = bloc ÉDITION + le prompt image + le négatif en interdits ;
- **prompt vidéo** = la ligne `**Mouvement**` du plan — jamais la ligne `**Prompt**`,
  qui produirait des personnages difformes en i2v ;
- **négatif** = bloc NÉGATIF commun + le `**Négatif**` propre au plan ;
- **`**Édition finale**`** (facultatif) = la contrainte du plan que le modèle lâche,
  réinjectée **juste avant le CADRAGE** ;
- **force i2i** = la ligne `**Force**` du plan ;
- **caméra** = le `CAM_xx` de l'en-tête du plan.

Modifier le markdown, pas les scripts.

## Après la génération

1. Contrôle halakhique de l'image et du mp4 contre la §9 de
   `fiche_technique_beit_hamikdash.md` — pour le plan 9 : 7 branches, Table à droite,
   Menora à gauche, rideau du sol au plafond, aucune coupole, aucun visage.
1. Repasser sur le mp4 les deux contrôles d'avant génération : un objet que le modèle a
   fait dériver au fil du plan, et surtout une silhouette qui **remonte vers l'ouest** et
   franchit une frontière que la frame de départ respectait.
2. Remplir la ligne du plan dans le journal de production de `prompts_par_plan.md`
   (seed, outil image, outil vidéo, force, version retenue).

## Clé API

`FAL_AI_KEY`, lue dans l'environnement puis dans le `.env` à la racine. Ne jamais
l'afficher ni la passer en argument.

## Détails techniques

Bibliothèque standard seule (`urllib`), aucune installation. Téléversement en deux
temps sur `rest.alpha.fal.ai/storage/auth/token` puis `https://v3b.fal.media/files/upload`,
génération via la file `queue.fal.run` sondée toutes les 5 s pendant 15 min au plus ;
passé ce délai le script affiche l'URL de résultat, qui reste valable.

Le catalogue fal se relit sans clé :
`curl -s "https://fal.ai/api/models?page=1&per_page=100&sort=most-popular"` pour la
liste et les prix, `curl -s "https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=<id>"`
pour le schéma d'un endpoint.
