---
name: fal-video
description: Génère l'image clé stylisée puis le plan vidéo sur fal.ai (édition IA du rendu Blender, puis image-to-video première + dernière frame) en ligne de commande, sans passer par le site fal.ai. À utiliser dès qu'il faut styliser une frame clé, animer un plan, relancer une génération, changer de modèle ou récupérer un mp4 — « stylise ce plan », « génère les deux frames », « anime CAM_03 », « refais-le en kling », « combien ça coûte ».
---

# Génération fal.ai

Deux scripts, deux étapes du pipeline :

| Script | Étape | Entrée | Sortie |
|---|---|---|---|
| `fal_image.py` | stylise une frame clé | `renders/blockout/` | `renders/style/` |
| `fal_video.py` | relie deux frames en vidéo | `renders/style/` | `renders/video/` |

Les entrées viennent du skill **camera**, qui pose le plan et exporte
`renders/blockout/<caméra>_{debut,fin}.png` et leurs `_profondeur.png`.
La plomberie commune — clé API, téléversement CDN, file d'attente — est dans
`fal_commun.py`.

**Toujours passer `--simulation` d'abord** pour relire le prompt et le coût avant de
payer une génération.

## Images clés

```bash
python3 .claude/skills/fal-video/fal_image.py --camera CAM_03_Heikhal --frame debut \
    --seed 30301 --prompt "..."
python3 .claude/skills/fal-video/fal_image.py --camera CAM_03_Heikhal --frame fin \
    --seed 30301 --prompt "..."
```

| Option | Défaut | Effet |
|---|---|---|
| `--camera` | requis | nom de la caméra, tel qu'il est dans `cameras.json` |
| `--frame debut\|fin` | `debut` | quelle frame clé styliser |
| `--prompt` | requis | ce que le cadre doit devenir — voir « Écrire le prompt » |
| `--modele` | `gpt2` | voir la table ci-dessous |
| `--seed N` | tirée au hasard | **la même seed pour les deux frames d'un plan** |
| `--controle a b c` | `1.0` | poids du conditionnement des modèles `depth*` ; une valeur = une variante |
| `--force` | `0.85` | force i2i (`depth-i2i` uniquement) |
| `--negatif` | vide | prompt négatif ; seul `general-depth` en tient compte |
| `--structure` | absent | joint la carte de profondeur en seconde image |
| `--reference <png>` | — | frame stylisée **validée** d'un plan voisin, jointe en dernière image : le modèle y prend la matière, jamais la composition |
| `--etapes` / `--guidage` | 28 / 3.5 | `num_inference_steps`, `guidance_scale` (modèles Flux) |

### Deux familles de modèles, et pourquoi l'édition gagne

**Édition** (`gpt2`, `nano-pro`, `nano2`, `seedream`, `seedream-lite`, `flux2-pro`) :
le rendu Blender part en entrée avec une instruction « repeins sans rien déplacer ».
La géométrie de la Mishna est conservée par construction — c'est la seule famille qui
passe un contrôle d'intérieur.

**Conditionnement par la profondeur** (`depth`, `depth-i2i`, `pro-depth`, `canny`) :
le modèle regénère l'image en suivant la carte de profondeur. Mesuré dans le Heikhal :
les ustensiles, trop petits et trop peu contrastés à 15-25 m, sont réinventés à chaque
fois. À garder pour les plans de matière et de ciel, pas pour les plans contrôlés.

| `--modele` | Endpoint | Prix | Mesuré |
|---|---|---|---|
| `gpt2` | `openai/gpt-image-2/edit` | ~0,08 $ (facturé au token, `quality: high`) | **retenu** : le meilleur verrou de cadrage des six. Sortie à l'aspect de l'entrée, 1920 × 1072 |
| `nano-pro` | `fal-ai/nano-banana-pro/edit` | 0,15 $/image | second : tient les cadrages testés, mais invente une colonnade sur une façade plane. Sortie 2752 × 1536 |
| `nano2` | `fal-ai/nano-banana-2/edit` | 0,08 $ | recompose : un mur devenu pylône isolé, un animal de premier plan **supprimé** |
| `seedream` | `bytedance/seedream/v5/pro/edit` | 0,0675 $ | visages de face au premier plan ; l'Oulam repeint en temple grec |
| `seedream-lite` | `fal-ai/bytedance/seedream/v5/lite/edit` | ~0,03 $ | keffiehs dans la foule, colonnade gréco-romaine inventée, le moins détaillé |
| `flux2-pro` | `fal-ai/flux-2-pro/edit` | 0,03 $ | ramène le site actuel — tuiles rouges, paraboles, voitures — et vide les plans de toute figure |
| `depth` | `fal-ai/flux-control-lora-depth` | ~0,04 $ | à `--controle 1.0` le style est là, la géométrie flotte ; 1.2 → granité doré ; 1.5 → bruit |
| `depth-i2i` | `.../image-to-image` | ~0,04 $ | inutile : sortie = blockout à peine retouché, à 0,50 comme à 1,00 de force |
| `pro-depth` / `pro-depth-rendu` | `fal-ai/flux-pro/v1/depth` | ~0,05 $ | arc brisé, statues, tableaux, foule |
| `canny` | `fal-ai/flux-control-lora-canny` | ~0,04 $ | belle lumière, mobilier inventé, keruv figuré |
| `general-depth` | `fal-ai/flux-general` + ControlNet Union | — | **indisponible** : « Could not load pipeline » sur 5 chemins de poids (InstantX, Shakker-Labs, jasperai, XLabs). Le compte ne charge pas de ControlNet externe |

`gpt2` n'a **ni seed ni prompt négatif** : la seed passée est ignorée, elle ne sert
qu'à nommer le fichier. Deux appels identiques ne donnent donc pas la même image, et
la frame de fin d'un plan quasi immobile se **dérive** de la frame de début (voir plus
bas) plutôt que de se regénérer.

Le verrou de cadrage est ce qui sépare les modèles, pas le rendu. Sur une façade
**plane** dans le blockout, `gpt2` est le seul des six à la laisser plane : les autres
y collent une colonnade à chapiteaux dorés. En échange il sort en 1920 × 1072 quand
`nano-pro` monte à 2752 × 1536 — sans importance, les modèles i2v rendent en 1080p.

## Écrire le prompt d'édition

Le prompt se donne en entier sur la ligne de commande. Aucun modèle d'édition ne
prend de prompt négatif : les interdits se plient dans l'instruction
(« Never show any of these: … »). Un prompt qui tient réunit, **dans cet ordre** :

1. **La consigne d'édition** — repeindre sans rien déplacer, sans rien ajouter, sans
   recomposer le cadre.
2. **Le style** — Temple debout, neuf et intact ; grand appareil hérodien en gros blocs
   fraîchement taillés, face lisse à marge ciselée, assises de niveau, joints
   filiformes ; ancrage « vraie photo 35 mm, jamais un rendu 3D ».
3. **Ce que le cadre contient**, et lui seul.
4. **Qui est là et où** — tenue et place des figures que la caméra voit.
5. **Les interdits**, retournés en ancrages positifs quand c'est possible.
6. **Le verrou de cadrage, en dernier.**

L'ordre n'est pas cosmétique : une instruction longue dilue ce qu'elle porte au
milieu. Mesuré — une clause de cadrage noyée à 2 500 caractères a donné un Sanctuaire
décentré et deux fois trop gros ; la même remise en **dernière position**, précédée de
« LAST AND MOST IMPORTANT, above every other instruction », a tenu. Une contrainte
structurelle se met à la fin. Et une seule : mises au même endroit, la troisième se
dilue à son tour.

**Les ancrages positifs battent les négatifs.** Sur une esplanade, `minaret` était
déjà dans les interdits et le modèle a quand même sorti un minaret à balcon, une
façade à arcades et une barrière métallique. C'est la phrase positive qui a réglé le
problème : « beyond the colonnade the esplanade stays bare pale pavement under open
sky, nothing later than the Second Temple ever enters the frame ». Même chose sur une
ligne de crête : « nothing breaks that skyline: no tower, spire, belfry, minaret, dome
or pointed roof ».

**Une consigne ne nomme que ce que la caméra voit.** Décrire une foule qu'un mur
occulte, ou des ustensiles sortis du cadre, c'est demander au modèle de les inventer —
et il refabrique la pièce entière. Avant d'écrire le prompt d'une frame, vérifier le
cadre : `inspect.py -- --voit <plan> [debut|fin]` (skill **blender**).

## Quand le rendu couleur ne porte plus rien : `--structure`

Dans un volume fermé — une colonnade couverte, un couloir — toutes les surfaces du
blockout sont blanches et l'ambiante les met au même gris : la structure est
**invisible** en couleur alors qu'elle est nette en profondeur. `--structure` joint la
carte de profondeur en seconde image et dit au modèle d'y lire la géométrie et
d'éclairer lui-même. À réserver aux plans dont le rendu couleur est plat : en
extérieur, le soleil sculpte déjà les masses.

## Trois leçons de géométrie qui ne se rattrapent pas au prompt

### Ce que la caméra regarde doit exister dans la géométrie

Un gros plan sur deux mains, sans mains dans le blockout : trois seeds et **douze
retouches** — dont six sur les mains seules — n'ont jamais rendu autre chose qu'une
moufle lisse sans un doigt. Deux proxys de mains ajoutés à la scène (masse, quatre
doigts, pouce) et les mains sont sorties **justes du premier coup, sans une retouche**.

Un modèle d'édition repeint ce qu'on lui donne ; il n'invente bien que ce qui est
petit et vague. Le sujet d'un plan n'est ni l'un ni l'autre. Corollaire inverse :
ajouter de la géométrie qu'aucune caméra ne voit ne corrige jamais un prompt.

### Deux objets alignés sur l'axe de vue ne se séparent pas en les éloignant

Un poing disparaissait derrière la vasque de l'ustensile qu'il tenait ; reculer la
vasque le long de son manche n'y a rien changé. La caméra regardait **le long du
manche** (produit scalaire −1,01 entre l'axe de vue et l'axe du manche) : la vasque se
projetait sur le poing à toute distance. Seul l'**écart latéral** les a séparés.

Avant de déplacer un objet qui en masque un autre, mesurer l'angle entre l'axe de vue
et l'axe qui les joint. S'il est proche de 0, la distance ne sert à rien.

### L'échelle des figures ne se devine pas

Sur un plan large, six modèles ont peint la foule du premier plan à **60 px** de haut
quand la géométrie en imposait **14**, avec des maisons deux fois plus petites que les
hommes debout devant elles. Le test qui tranche, avant d'accuser un modèle :

```bash
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_inspect.py -- --foule <plan>
```

Mesuré sur ce plan large, sur 1 621 figures : **0 / 462** sur l'esplanade — le mur les
cache toutes —, 24/576 à l'Ezrat Nashim, 9/129 cohanim, 2/12 Léviim. **35 figures
visibles, médiane 12,4 px sur 1080.** À ce compte le blockout ne porte aucune
référence humaine lisible : tout ce que le modèle peint en foule est inventé, et il
l'invente au cadrage photo. Un plan qui en voit 96 à 190 px de médiane sort juste sans
qu'on ait rien à lui dire.

C'est la **médiane** qui compte, pas le maximum : une figure qui frôle l'objectif
monte à 3 000 px et fausse tout.

Là où le blockout ne donne pas l'échelle, **la dire en chiffres**, et dans la dernière
clause : « la façade fait 100 amot, un homme 3,65, donc un homme = 1/27 de la façade,
et aucune figure ne dépasse 1/60 de la hauteur d'image ». Après quoi les maisons du
premier plan sont ressorties à 50 px pour 50 px prédits.

## Deux frames, une seule image, ou une coupe

`beit_hamikdash_analyse_plans.py` mesure, pour chaque plan, la part de la frame de fin
**déjà visible au début** — ce qu'elle laisse de côté, le modèle doit l'inventer.
Trois régimes, trois conduites :

| Mesure | Conduite |
|---|---|
| **100 % / caméra fixe** | **Une seule image + prompt de mouvement** (`--sans-fin`). Deux frames identiques ne donnent rien à interpoler ; le modèle comble en inventant une dérive. Ce qui bouge est dans les corps, la fumée, les tissus |
| **couverture ≥ 40 %** | Deux frames. La frame de fin porte un contenu qu'on veut contrôler et qu'il ne faut pas laisser inventer |
| **couverture < 40 %** | Le plan se coupe **dans Blender**, il ne se rattrape pas au prompt : deux caméras dans `cameras.json` au lieu d'une |

Un travelling **avant** garde une couverture haute même quand plus une pierre n'est
commune aux deux frames : l'image d'arrivée est l'agrandissement du centre de l'image
de départ, ce qu'un i2v sait faire. Ce qui tue un plan n'est pas ce qui sort du cadre,
c'est ce qui y entre sans avoir été annoncé — panoramique, relevé, grue qui franchit
un mur.

## Frame de fin : éditer ou dériver

Deux éditions indépendantes de deux blockouts **quasi identiques** ne convergent pas :
sur un plan large, la façade est ressortie en marbre blanc au début et tout en or à la
fin, avec la même seed et le même prompt. Le modèle n'a aucune mémoire d'un appel à
l'autre.

- **Mouvement franc** : deux éditions ; la géométrie diffère assez pour que chacune
  tienne debout.
- **Quasi-immobile** (moins de ~15 % d'échelle entre les deux frames) : **dériver** la
  frame de fin de la frame de début validée, par zoom géométrique. Le facteur est le
  rapport des distances caméra → cible, et la continuité de matière est alors exacte.

```bash
# facteur = |C_debut - cible| / |C_fin - cible|, ici 1,1768
ffmpeg -i renders/style/CAM_01_debut_….png -vf "scale=3239:1808,crop=2752:1536" \
       renders/style/CAM_01_fin_derive.png
```

Corollaire : un travelling qui ne change pas l'échelle d'au moins ~15 % ne se **voit**
pas sur 8 s. Corriger la course dans `cameras.json`, pas au montage.

## Vidéo

```bash
python3 .claude/skills/fal-video/fal_video.py --camera CAM_03_Heikhal --duree 8 \
    --depart renders/style/CAM_03_Heikhal_debut_gpt2_c1.00_g3.5_seed30301.png \
    --fin    renders/style/CAM_03_Heikhal_fin_gpt2_c1.00_g3.5_seed30301.png \
    --prompt "the camera glides slowly forward down the hall; nothing else moves"
```

| Option | Défaut | Effet |
|---|---|---|
| `--camera` | requis | nom de la caméra ; sert aux chemins par défaut et au nom du mp4 |
| `--prompt` | requis | **le mouvement de caméra, et lui seul** |
| `--modele` | `veo-lite` | voir la table ci-dessous |
| `--duree N` | max du modèle | secondes générées |
| `--depart` / `--fin` | `renders/blockout/<caméra>_{debut,fin}.png` | **pointer sur `renders/style/`** pour animer les frames stylisées |
| `--negatif` | vide | pour les endpoints qui en prennent un |
| `--sans-fin` | absent | n'impose aucune frame de fin (endpoints image-to-video seuls) |
| `--seed N` | — | `veo*`, `seedance` |

Le prompt i2v ne décrit **que la caméra**. Ce qui est dans le cadre est déjà dans les
deux images ; le redécrire pousse le modèle à le réinventer, et sur les modèles sans
prompt négatif à le **peupler**.

### Le contrôle qui précède toute génération

L'i2v n'a aucun plan de correction : il amplifie la frame de départ. Un objet déplacé
y reste huit secondes, et une silhouette posée dans une zone qui lui est fermée se met
à y **marcher**. Avant de payer, deux passes sur les **deux frames stylisées** :

1. **Positions** — frame stylisée à côté du rendu Blender de la même caméra, objet par
   objet : même place, même échelle, même orientation, même nombre, même cadrage.
2. **Zones d'accès** (§12 de `fiche_technique_beit_hamikdash.md`) — pour chaque
   silhouette : a-t-elle le droit d'être là ? Le peuple s'arrête aux 11 amot de
   l'Ezrat Israël, le Doukhan est aux Léviim (douze au moins), l'Ezrat Cohanim et
   l'entre-Oulam-et-autel aux cohanim, l'Oulam et le Heikhal sont **vides** à l'heure
   de l'encens, le Kodesh HaKodashim n'a que le Cohen Gadol.

Ce qui est en défaut se reprend par ré-édition ou par le skill **fal-retouche** —
jamais par un négatif ajouté au prompt vidéo, que les modèles i2v tiennent mal.

| `--modele` | Endpoint | Durées | Prix (audio coupé) | Négatif | Mesuré |
|---|---|---|---|---|---|
| `veo-lite` | `fal-ai/veo3.1/lite/first-last-frame-to-video` | **8 s seulement** | 0,05 $/s en 1080p | oui | **retenu** : dolly puis tilt exactement comme demandé, rien d'autre ne bouge, 1920 × 1080 |
| `flux3` | `blackforestlabs/flux-3/first-last-frame-to-video` | 5 à 20 s | 0,29 $/s en 1080p, 0,17 en 720p | non | propre, mais traverse un rideau en gros plan au milieu du plan ; 3,6 × le prix de `veo-lite` |
| `kling3` | `fal-ai/kling-video/v3/pro/image-to-video` | 3 à 15 s | 0,112 $/s | oui | **écarte les pans d'un rideau** — une action que personne ne lui a demandée ; sortie en 1928 × 1072 |
| `veo` | `fal-ai/veo3.1/fast/first-last-frame-to-video` | 4, 6, 8 s | 0,10 $/s | oui | même famille que `veo-lite` au double du prix |
| `kling` | `fal-ai/kling-video/o1/image-to-video` | 3 à 10 s | 0,112 $/s | non | travelling le plus lent, architecture stable ; ajoute des flammes sur les portes |
| `h3-turbo` | `minimax/h3-max-turbo/image-to-video` | 5 à 15 s | 0,04 $/s (768p) ; 0,025 en 480p | non | **768p maximum**, lit le prompt comme un contenu à peindre : une salle vide se remplit de figures ; réduit au seul mouvement il **arrache le rideau** vers 4,5 s |
| `seedance` | `fal-ai/bytedance/seedance/v1.5/pro/image-to-video` | 4 à 12 s | 0,052 $/s (720p) | non | dolly propre mais **fait marcher** les silhouettes : viole « nothing else moves » |
| `veo-hq` | `fal-ai/veo3.1/first-last-frame-to-video` | 4, 6, 8 s | 0,20 $/s | oui | non testé |
| `seedance2` | `bytedance/seedance-2.5/image-to-video` | 4 à 30 s | 0,473 $/s en 720p ; 0,2205 en 480p, 1,164 en 1080p | non | tient un intérieur **une fois le prompt réécrit pour lui** ; dix fois `veo-lite` |

Écarté aussi : `minimax/h3-max` (768p maximum, comme sa variante turbo).

### Les modèles sans prompt négatif se pilotent autrement

Mesuré sur `seedance2`, 8 s, 3,78 $ pour une sortie **inutilisable** : « very slow
dolly backward » a reculé de trente amot **à travers la pierre** — à 4 s la caméra
était sortie de la chambre, à 8 s dehors au plein soleil — et le prompt de figures a
été lu comme un contenu à peindre, remplissant d'agenouillés un plan qui devait
montrer un homme seul. Même frame, même durée, même prix, **prompt réécrit** : la
caméra est restée dans la chambre du premier au dernier plan. Le modèle n'était pas en
cause.

1. **Ne pas décrire les figures.** Ce qui tient les gens à leur place chez `veo` les
   **fait naître** chez `seedance2` comme chez MiniMax.
2. **Borner la course en distance, pas en adjectif.** « a few centimetres only, the
   camera stays inside this small dark chamber for the whole shot » a tenu là où
   « very slow » a traversé un mur.
3. **Nommer ce qui doit rester dans le cadre**, mur par mur : « the hammered gold wall
   keeps filling the left, the woven curtain keeps filling the right ». Chaque interdit
   se retourne en ancrage positif.

`kling3` et `flux3` montent à 15 et 20 s : de quoi couvrir un plan entier au lieu de
générer 8 s et de ralentir au montage.

## Après la génération

1. Contrôle contre la §9 de `fiche_technique_beit_hamikdash.md` — sept branches à la
   Menora, Table au nord, rideau du sol au plafond, aucune coupole, aucun visage.
2. Repasser sur le mp4 les deux contrôles d'avant génération : un objet que le modèle a
   fait dériver au fil du plan, et surtout une silhouette qui franchit une frontière
   que la frame de départ respectait.
3. Noter la seed, le modèle image, le modèle vidéo et la version retenue — le script
   les écrit dans le nom du fichier, c'est le seul journal qui ne se périme pas.

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
