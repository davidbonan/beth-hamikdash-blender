---
name: fal-retouche
description: Corrige un détail d'une image déjà générée (gpt-image-2 ou Nano Banana sur fal.ai) sans regénérer le reste du cadre — le hors-zone ressort pixel pour pixel identique. À utiliser dès qu'une image validée porte un défaut localisé : « corrige la Menora du plan 9 », « enlève la coupole du plan 1 », « retouche juste le visage au premier plan », « refais cette zone sans tout regénérer », « inpainting », « la façade est en or, remets-la en pierre ».
---

# Retouche ciblée

`retouche.py` reprend **une zone** d'une image et laisse tout le reste intact. À
utiliser après `fal-video/fal_image.py` : quand une frame stylisée est bonne à 95 %,
la regénérer perd les 95 % — le modèle n'a aucune mémoire d'un appel à l'autre (le
plan 1 est ressorti en marbre blanc puis tout en or à seed et prompt identiques).

```bash
# 1. lire les coordonnées de la zone sur une copie quadrillée
python3 .claude/skills/fal-retouche/retouche.py --image renders/style/CAM_09A_debut_….png --reperes

# 2. vérifier la zone et l'instruction sans payer
python3 .claude/skills/fal-retouche/retouche.py --image renders/style/CAM_09A_debut_….png \
    --zone 38%,22%,18%,44% --instruction "la Menora a sept branches, pas neuf" --simulation

# 3. générer
python3 .claude/skills/fal-retouche/retouche.py --image renders/style/CAM_09A_debut_….png \
    --zone 38%,22%,18%,44% --instruction "la Menora a sept branches, pas neuf"
```

**Toujours passer `--simulation` d'abord** : il écrit le masque et la découpe dans
`travail/` sans rien générer, de quoi voir la zone avant de payer.

## Le hors-zone ne repasse pas par le modèle

C'est la garantie du script, et elle est mécanique, pas déclarative : la sortie du
modèle est **recomposée** sur l'original avec un masque flouté (`maskedmerge`), donc
hors de la zone et de son fondu, le fichier de sortie est **bit à bit** celui d'entrée
(vérifié : même md5 sur la bande hors zone). Sans `--zone`, il n'y a rien à recomposer
et l'image entière est celle du modèle.

Ne pas compter sur la seule instruction pour cela : « ne change rien d'autre » est
posé dans le prompt, mais aucun modèle d'édition ne le tient au pixel — c'est la
recomposition qui le tient.

## Trois méthodes

| `--methode` | Ce qui part au modèle | Modèles | Quand |
|---|---|---|---|
| `masque` | le cadre entier **+ un masque alpha** qui ouvre la zone | `gpt2` seul | défaut avec `--zone` sur `gpt2` : le modèle voit tout le cadre et ne repeint que la zone |
| `decoupe` | la zone seule, élargie de `--marge` (25 % par défaut) | tous | défaut avec `--zone` sur `nano*` ; aussi le recours quand une petite zone manque de résolution — le modèle y travaille à pleine échelle |
| `plein` | le cadre entier, sans masque ni découpe | tous | défaut sans `--zone` ; avec une `--zone`, recours si les deux autres échouent |

`auto` (défaut) choisit : pas de zone → `plein` ; zone + `gpt2` → `masque` ; zone +
`nano*` → `decoupe`.

Ces trois chemins **n'ont pas encore été comparés** sur une vraie retouche de ce film.
Ce qui est établi : `openai/gpt-image-2/edit` est le seul des endpoints d'édition à
accepter un `mask_url` (schéma OpenAPI fal), les Nano Banana n'ont pas de champ de
masque.

## Modèles

| `--modele` | Endpoint | Prix | Masque | Seed |
|---|---|---|---|---|
| `gpt2` (défaut) | `openai/gpt-image-2/edit` | ~0,08 $ (au token, `quality: high`) | oui | non — deux appels identiques ne donnent pas la même image |
| `nano-pro` | `fal-ai/nano-banana-pro/edit` | 0,15 $ | non | oui |
| `nano2` | `fal-ai/nano-banana-2/edit` | 0,08 $ | non | oui |

Prix et caractère : voir la table complète du skill `fal-video`, mesurée sur les plans
1, 4 et 5. `gpt2` y est retenu pour son verrou de cadrage — c'est aussi ce qu'on veut
d'une retouche. `nano2` recompose (mur devenu pylône, taureau supprimé) : à ne sortir
que si `gpt2` refuse la correction.

## Options

| Option | Défaut | Effet |
|---|---|---|
| `--image` | requis | l'image à retoucher ; une retouche se rechaîne en la repassant ici |
| `--reference` | — | une frame **déjà validée** portant le même objet : sa matière et son dessin sont copiés, jamais son cadrage ni sa lumière. Part en seconde image au modèle |
| `--instruction` | requis | la correction, en une phrase. **Ce qui n'est pas nommé ne doit pas être décrit** |
| `--zone x,y,l,h` | — | en pixels ou en % du cadre (`38%,22%,18%,44%`), les deux mélangeables |
| `--methode` | `auto` | voir la table ci-dessus |
| `--modele` | `gpt2` | voir la table ci-dessus |
| `--marge` | `0.25` | contexte ajouté autour de la zone en `decoupe`, en part de sa taille |
| `--portee` | `detail` | `detail` : une correction locale, tout le reste figé ; `matiere` : voir ci-dessous |
| `--fondu` | `12` | rayon du raccord en pixels ; monter sur une matière continue (ciel, mur), descendre sur un contour franc |
| `--sans-recomposition` | absent | garde la sortie brute du modèle, sans recoller |
| `--sortie` | dossier de l'image | où écrire |
| `--reperes` | absent | écrit une copie quadrillée tous les 10 %, médianes en cyan, et s'arrête |
| `--simulation` | absent | prépare masque et découpe, affiche la charge utile, ne génère pas |

## Quand toute la frame sent le rendu 3D : `--portee matiere`

Une frame validée dans son dessin peut sortir en « jeu vidéo » : or des murs en texture
plate et uniforme, sol sans veinage, lumière égale, aucune brume, tout net bord à bord
(mesuré sur 9a et 9b). L'enveloppe `detail` interdit justement de changer matière et
lumière ; `--portee matiere` la remplace par une enveloppe qui fige le **dessin** — cadrage,
place, échelle et nombre des objets, motifs et registres du rideau — et libère matière,
lumière, atmosphère et optique. À passer en `--methode plein`, l'instruction ne nommant
que la matière voulue (feuilles d'or martelé à joints et clous, dalles veinées, faisceau
dans la brume, grain, halo sur les flammes).

```bash
python3 .claude/skills/fal-retouche/retouche.py --image renders/style/CAM_09B_debut_….png \
    --methode plein --portee matiere --instruction "The gold walls are sheets of hammered gold nailed over cedar, …"
```

Mesuré sur 9b puis 9a (`gpt2`) : parokhet ressortie motif pour motif, kelim en place, or
martelé à clous, sol veiné, faisceau volumétrique. Sur la seconde frame d'une paire,
passer la première en `--reference` pour que les deux se montent. Ce que la passe
**amplifie** : un artefact déjà en germe (deux taches rondes sur le rideau du 9b) ressort
plus net — à reprendre ensuite en `detail` masqué.

## Raccorder un objet d'un plan à l'autre : `--reference`

Rien dans `prompts_par_plan.md` ne fige le **dessin** d'une étoffe ou d'une façade : deux plans
qui la décrivent avec les mêmes mots en sortent deux versions différentes. Mesuré sur la
parokhet — quatre grandes ailes isolées sur indigo uni au plan 9a, trame d'aigles répétés sur
larges bandes roses au plan 9b, à partir de la même ligne `**Prompt**`. C'est un faux raccord
sur l'objet central de deux plans qui se suivent.

`--reference` joint la frame validée en **seconde image** et demande d'en copier le dessin, la
matière et les couleurs — rien d'autre : ni son cadrage, ni sa lumière, ni ses objets, que la
zone corrigée garde de l'image en cours. La parokhet du 9b a été réalignée sur celle du 9a en
un seul passage.

```bash
python3 .claude/skills/fal-retouche/retouche.py --image renders/style/CAM_09B_debut_….png \
    --reference renders/style/CAM_09A_debut_gpt2_c1.00_g3.5_seed90902.png \
    --zone 29%,0%,42%,75% --instruction "the curtain is rewoven with the very same design as the reference frame: …"
```

L'instruction reste nécessaire : elle nomme **quel** objet raccorder, sans quoi le modèle prend
la référence pour un second cadre à fondre. La décrire en clair sert aussi de garde-fou si le
modèle ignore la seconde image.

## Écrire l'instruction

Le prompt envoyé est l'instruction **enveloppée** dans une consigne de conservation
(même cadrage, même lumière, mêmes matières, rien d'autre ne bouge) que le script
ajoute seul. Donc :

- **Nommer le défaut et l'état voulu**, pas la scène : « la Menora a sept branches,
  pas neuf », pas une redescription du Heikhal. Décrire ce qui est déjà juste, c'est
  demander au modèle de le refaire — et il le refera autrement.
- **Une correction par appel.** Deux défauts dans la même zone se font en deux passes
  rechaînées ; le modèle en lâche une sur deux quand elles sont dans la même phrase.
- Les interdits du film (coupole, minaret, site actuel) restent utiles ici : les
  reprendre en clair dans l'instruction si la retouche risque de les ramener.

## Sorties

- `<image>_retouche<N>_<modele>.png` — le résultat recomposé, l'index s'incrémente.
- `<image>_retouche<N>_<modele>_brut.png` — la sortie du modèle avant recomposition,
  à regarder quand le raccord surprend.
- `travail/` — masque alpha, découpe, masque de fondu, recollage, repères.

Après retouche, refaire les deux contrôles de `fal-video` sur l'image corrigée
(positions et zones d'accès) avant de l'envoyer en i2v : l'i2v amplifie la frame de
départ et n'a aucun plan de correction.

## Clé API et dépendances

`FAL_AI_KEY` (environnement puis `.env` à la racine), lue par `fal_commun.py` du skill
`fal-video`, dont ce script importe toute la plomberie fal.ai. Ne jamais l'afficher.

`ffmpeg` / `ffprobe` font le masque, la découpe et la recomposition ; Python n'utilise
que la bibliothèque standard.
