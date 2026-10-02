---
name: elevenlabs-musique
description: Génère un chant liturgique hébreu sur elevenlabs.io (Music v2.5) dans le style d'une chanson de référence — voix de garçon, piano, cordes, un seul chant aux variations légères — à partir d'un texte translittéré découpé en sections. À utiliser dès qu'il faut mettre un texte en musique ou refaire un chant — « fais une musique du Pitum haketoret », « mets ce texte en chanson », « refais un tirage de la musique », « génère une musique émouvante de ce passage ».
---

# Musique d'un texte

`elevenlabs_musique.py` chante un texte hébreu dans le style d'une chanson de référence.
La recette est celle de `render/audio/musique/pitum_haketoret_complet_direct_translittere_accent_hebreu.mp3`,
retenue après une trentaine d'essais ; le texte, son découpage, le ton et l'arrangement
de chaque section viennent d'un fichier.

```bash
# 1. vérifier le plan et le coût sans payer
python3 .claude/skills/elevenlabs-musique/elevenlabs_musique.py --texte .claude/skills/elevenlabs-musique/textes/pitum_haketoret_complet.txt --simulation

# 2. générer — plusieurs tirages d'un coup pour choisir
python3 .claude/skills/elevenlabs-musique/elevenlabs_musique.py --texte .claude/skills/elevenlabs-musique/textes/pitum_haketoret_complet.txt --tirages 2

# 3. ré-étiqueter un mp3 retouché ou renommé hors du skill, sans rien générer
python3 .claude/skills/elevenlabs-musique/elevenlabs_musique.py --texte .claude/skills/elevenlabs-musique/textes/pitum_haketoret_complet.txt \
    --etiqueter ~/Downloads/"Pitum Haketoret.mp3"
```

Sortie : `render/audio/musique/<nom>.mp3` (puis `<nom>_2.mp3`…, jamais écrasé), avec à côté
le `.json` exact envoyé à ElevenLabs. `render/` est hors git.

Chaque mp3 sort étiqueté, prêt pour Musique : ID3 v2.3 (UTF-16, pour l'hébreu) avec
titre, artiste et artiste de l'album, album (= titre, piste 1/1), genre « Jewish
Music », année, langue, **paroles** (en hébreu) et source en commentaire.
L'étiquette remplace celle du mp3 ; le son n'est pas touché.

Il faut : `ELEVENLABS_API_KEY` dans l'environnement ou le `.env` de la racine, un
abonnement payant (le plan gratuit répond 402), et `ffmpeg`.

## Le texte

Un fichier par chant, dans `textes/` :

```
# commentaire
titre: Pitum Haketoret
artiste: David Bonan
source: Pitum haketoret — Keritot 6a

[Verse 1 | 30 | calm storytelling, steady like the daily rhythm | gentle opening, piano and voice with light strings, soft dynamics]
Tanu rabanan pitum haketoret keitsad
תָּנוּ רַבָּנָן פִּטּוּם הַקְּטֹרֶת כֵּיצַד
…
```

- `titre`, `artiste`, `source` avant la première section, tous facultatifs : ils
  font l'étiquette du mp3. Titre absent → tiré du nom du fichier.
- En-tête `[nom | durée en s | ton | arrangement]` : nom, ton et arrangement
  s'écrivent en anglais (le modèle les suit mieux). Durée absente → 6 s par ligne
  chantée ; ton et arrangement sont facultatifs.
- **Une ligne en lettres latines est chantée ; une ligne en lettres hébraïques ne
  part jamais au modèle, elle fait les paroles de l'étiquette.** Écrire chaque ligne
  translittérée et, dessous, son hébreu. Sans hébreu, l'étiquette prend les lignes
  chantées.
- Chaque ligne est chantée une fois, dans l'ordre ; couper aux virgules.
- Limites ElevenLabs, vérifiées avant tout envoi : 28 sections, 3 à 120 s chacune,
  30 lignes chantées de 200 caractères au plus, 600 s en tout.

### Translittérer

Le modèle chante ce qui est écrit, lu à peu près comme de l'anglais. Écrire le son,
pas l'orthographe hébraïque :

- Prononciation séfarade / israélienne : kamats `a`, tsere et segol `e`, holam `o`.
- `ch` pour ח et כ sans daguesh, `sh`, `ts` pour צ, `k` pour כּ et ק, `v` pour ו et ב
  sans daguesh, `y` pour י consonne, `ei` pour tsere-yod (`lifnei`, `heitev`).
- Le shva muet ne s'écrit pas (`ushchelet`, `yaktirena`), le shva prononcé s'écrit `e`
  (`ketoret`, `shelosh`).
- Le hé final muet ne s'écrit pas (`Moshe`, `mane`) ; le hé avec mappiq s'écrit `h`
  (`vah`, `pesalah`).
- Apostrophe entre deux voyelles qui se suivent ou pour ע / א en tête de syllabe
  (`me'ot`, `ha'arbayim`, `Shim'on`).
- Consonnes doubles non redoublées (`samim`, `kipurim`). Aucun accent ni diacritique.
- Le Nom s'écrit `Adonai`, comme il se chante.

## Écrire un bon chant

Ce qui a fait la version retenue, et qui se règle dans le fichier texte :

- **Un seul chant, pas un medley.** Tempo, tonalité, chanteur et thème mélodique ne
  changent jamais : le script l'impose à chaque section (« one continuous song, same
  melody theme throughout », rejet de « tempo change », « genre change », « different
  singer »). Demander par section un autre tempo ou un autre genre donnait un medley
  et faisait dériver la voix.
- **La variété vient de l'arrangement** (4ᵉ champ de l'en-tête) : quels instruments
  entrent ou sortent, la densité, la dynamique — jamais le tempo. Exemples retenus :
  « plucked oud joins the piano », « light frame drum joins softly », « percussion
  drops out, lighter arrangement at the same tempo », « full ensemble, strongest
  dynamics ».
- **Une courbe, pas une rampe.** Ouvrir doux (piano, voix, cordes légères), faire
  entrer un instrument à la fois, retomber une ou deux fois en cours de route (une
  section sans percussion, un pont dépouillé) pour que la montée suivante s'entende,
  garder l'ensemble complet et la dynamique la plus forte pour la fin. La montée
  continue « intensity i of N » de l'ancienne recette donnait une piste presque
  toute sur le même ton.
- **Deux sections voisines ne portent jamais le même arrangement** ; une variation
  reste légère (un instrument, un cran de dynamique).
- **Le ton se tire du sens du passage** (3ᵉ champ) : les 11 épices « chaque nom comme
  un trésor », le broyage « hadek heitev » rythmé comme un pilon, la mise en garde
  « solennelle ». L'arrangement peut l'appuyer (qanun sur les noms d'épices, tambour
  sur cadre qui marque le pilon).
- **Durées** : compter 5 à 6 s par ligne chantée.
- Ne rien écrire dans ton ou arrangement qui contredise la recette : pas de « slow »,
  pas de BPM, pas de voix d'adulte ou de chœur.

`textes/pitum_haketoret_complet.txt` est le modèle à suivre : 13 sections, c'est lui
qui a été retenu. `textes/pitum_haketoret.txt` (3 min) a été converti au même format
mais n'a pas été tiré avec cette recette.

## La recette (ne pas retoucher sans raison)

| Élément | Valeur |
|---|---|
| Appel | `POST https://api.elevenlabs.io/v1/music?output_format=mp3_48000_192`, `model_id: music_v2_5`, `composition_plan.chunks` ; le mp3 revient dans la réponse (une quarantaine de secondes pour 7 min) |
| Référence | `reference.mp3`, 0:50–1:20, `condition_strength: medium`, sur l'intro et chaque section chantée |
| Paroles | translittérées en lettres latines, plus le style « Hebrew accent » |
| Styles | voix de garçon d'environ 6 ans, mélodie de prière séfarade, 136 BPM, mi♭ mineur, piano, cordes, oud et ney |
| Intro / outro | 10 s strictement instrumentales (voix, fredonnement, chœur rejetés) / 8 s piano seul |
| Unité | même mélodie et même chanteur demandés à chaque section ; changement de tempo, de genre ou de chanteur rejeté |
| Coût | 12,5 crédits la seconde, à la seconde — 5 166 crédits pour les 6 min 53 du Pitum complet |

Pas de seed : chaque tirage est une voix nouvelle, la même requête donne des résultats
inégaux. Tirer deux ou trois fois et choisir à l'oreille.

## Ce qui a été essayé et rejeté

Jugé à l'écoute sur le Pitum haketoret :

- **Texte en lettres hébraïques** (vocalisé, hé muet et shva muet retirés ou non) :
  voix légèrement robotique, comme passée au vocodeur, en `high` ; rejeté aussi en
  `medium` et en `low`. La translittération sonne plus propre.
- **Référence en `high`** : effet robot plus marqué qu'en `medium`. Fenêtre de
  référence, réencodage de la référence, sortie PCM, `music_v2` : sans effet dessus.
- **Accent anglais de la translittération** : accents toniques écrits (`Vayómer`)
  avec « native Israeli Hebrew pronunciation » et rejet de « English accent » → trop
  accentué et plus anglais par endroits ; orthographe à l'allemande ou à l'espagnole →
  pas mieux. Le seul ajout « Hebrew accent » a suffi.
- **Un tempo ou un genre par section** : medley, voix qui dérive.
- **Montée continue « intensity i of N »** : piste monotone.
- **Intro avec les styles de voix** : mots inventés chantés avant la première ligne.
- **fal.ai** (même modèle) : 0,60 $ la minute entamée, environ cinq fois le prix du
  direct au plan Starter.
- **MiniMax Music 3 et Lyria 3.5** : nettement en dessous d'ElevenLabs. Lyria ne
  compte pas l'hébreu parmi ses langues ; MiniMax s'arrête avant la fin du texte.
- **Sans référence audio** (tempo 68 BPM, voix de ténor) : trop lent, voix d'adulte.
- **Fenêtres où la voix de la référence est la plus exposée** (0:00–0:15, 1:35–1:55) :
  moins bon que 0:50–1:20.
- **Voix d'enfant sans « boy »** (« child soloist », puis « about 6 years old ») : voix
  d'adolescente puis de femme, même en rejetant « woman singer ». Le mot « boy » tient la voix.

## La référence : à fournir soi-même

`.claude/skills/elevenlabs-musique/reference.mp3` est ignoré par git : chacun y dépose
sa propre chanson, ou passe `--reference`. À la première génération, la fenêtre
(`--fenetre`, 11 à 30 s) est découpée sans réencodage et téléversée sur ElevenLabs,
ce qui coûte autant de crédits qu'une génération de sa durée (375 pour 30 s) et passe
un contrôle de droits d'auteur. Le `song_id` reçu est retenu dans
`references_televersees.json` (hors git, propre au compte) : les tirages suivants ne
retéléversent rien. Si ElevenLabs ne reconnaît plus un `song_id`, supprimer ce fichier.

Les styles de la recette décrivent la référence d'origine : chant liturgique en
mi♭ mineur à 136 BPM, voix de garçon soliste, piano et cordes. Avec une autre
référence, choisir dans `--fenetre` 30 s où voix et accompagnement sont tous deux
présents, et ajuster les `STYLES_*` dans `elevenlabs_musique.py` s'ils la contredisent.
