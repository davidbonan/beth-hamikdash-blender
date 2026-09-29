---
name: fal-musique
description: Génère un chant liturgique hébreu sur fal.ai (ElevenLabs Music v2.5) dans le style d'une chanson de référence — voix de garçon, piano, cordes, montée en puissance — à partir d'un texte découpé en sections. À utiliser dès qu'il faut mettre un texte en musique ou refaire un chant — « fais une musique du Pitum haketoret », « mets ce texte en chanson », « refais un tirage de la musique », « génère une musique émouvante de ce passage ».
---

# Musique d'un texte

`fal_musique.py` chante un texte hébreu dans le style d'une chanson de référence.
La recette est celle de `audio/musique/pitum_haketoret.mp3`, retenue parmi dix-huit
essais ; le texte, son découpage et le ton de chaque section viennent d'un fichier.

```bash
# 1. vérifier le plan et le prix sans payer
python3 .claude/skills/fal-musique/fal_musique.py --texte .claude/skills/fal-musique/textes/pitum_haketoret.txt --simulation

# 2. générer — plusieurs tirages d'un coup pour choisir
python3 .claude/skills/fal-musique/fal_musique.py --texte .claude/skills/fal-musique/textes/pitum_haketoret.txt --tirages 2

# 3. ré-étiqueter un mp3 retouché ou renommé hors du skill, sans rien générer
python3 .claude/skills/fal-musique/fal_musique.py --texte .claude/skills/fal-musique/textes/pitum_haketoret.txt \
    --etiqueter ~/Downloads/"Pitum Haketoret.mp3"
```

Sortie : `audio/musique/<nom>.mp3` (puis `<nom>_2.mp3`…, jamais écrasé), avec à côté
le `.json` exact envoyé à fal. `audio/` est hors git.

Chaque mp3 sort étiqueté, prêt pour Musique : ID3 v2.3 (UTF-16, pour l'hébreu) avec
titre, artiste et artiste de l'album, album (= titre, piste 1/1), genre « Jewish
Music », année, langue, **paroles** (toutes les lignes du texte) et source en
commentaire. L'étiquette remplace celle du mp3 ; le son n'est pas touché.

## Le texte

Un fichier par chant, dans `textes/` :

```
# commentaire
titre: Pitum Haketoret
artiste: David Bonan
source: Pitum haketoret — Keritot 6a

[Verse 1 | 30 | calm storytelling, steady like the daily rhythm of morning and evening]
תָּנוּ רַבָּנָן פִּטּוּם הַקְּטֹרֶת כֵּיצַד
…
```

- `titre`, `artiste`, `source` avant la première section, tous facultatifs : ils
  font l'étiquette du mp3. Titre absent → tiré du nom du fichier.
- `percussions: <style en anglais>`, facultatif : style ajouté à l'intro et à chaque
  section, et « heavy drums » n'est plus rejeté. Dans le ton d'une section, la
  percussion ne s'entendait presque pas.
- En-tête `[nom | durée en s | ton]` : le nom s'écrit en anglais, le ton aussi (en
  anglais, le modèle le suit mieux). Durée absente → 6 s par ligne ; ton absent →
  seule la montée en puissance s'applique.
- **Le ton se tire du sens du passage** : c'est ce qui a fait la meilleure version
  (les 11 épices « chaque nom comme un trésor », la fin « grave et lourde »).
- Chaque ligne est chantée une fois, dans l'ordre ; couper aux virgules.
- Limites ElevenLabs, vérifiées avant tout envoi : 28 sections, 3 à 120 s chacune,
  30 lignes de 200 caractères au plus, 600 s en tout.

## La recette (ne pas retoucher sans raison)

| Élément | Valeur |
|---|---|
| Référence | `reference.mp3`, 0:50–1:20, `strength: high`, sur l'intro et chaque section chantée |
| Styles | voix de garçon d'environ 6 ans, mélodie de prière séfarade, 136 BPM, mi♭ mineur, piano, cordes, oud et ney |
| Intro / outro | 10 s piano et cordes / 8 s piano seul |
| Montée | chaque section reçoit `intensity i of N` et « keeps building in power » ; le qanun entre au 3ᵉ palier, un tambour sur cadre léger au 4ᵉ |
| Prix | 0,60 $ la minute entamée — 1,80 $ pour les 3 min du Pitum |

Pas de seed : chaque tirage est une voix nouvelle, la même requête donne des résultats
inégaux. Tirer deux ou trois fois et choisir à l'oreille.

## Ce qui a été essayé et rejeté

Jugé à l'écoute sur le Pitum haketoret :

- **MiniMax Music 3 et Lyria 3.5** : nettement en dessous d'ElevenLabs. Lyria ne
  compte pas l'hébreu parmi ses langues ; MiniMax s'arrête avant la fin du texte.
- **Sans référence audio** (tempo 68 BPM, voix de ténor) : trop lent, voix d'adulte.
- **Accélération écrite en BPM par section** et une fenêtre de référence différente
  par section : moins bon que la montée en puissance seule.
- **Fenêtres où la voix de la référence est la plus exposée** (0:00–0:15, 1:35–1:55) :
  moins bon que 0:50–1:20.
- **Prononciation séfarade forcée** — consignes de style (« kamatz as 'a' ») ou
  kamats remplacés par des pata'h dans le texte : voix de femme ou moins enfantine,
  moins bon dans l'ensemble. Défaut connu, non résolu : le kamats sort parfois « o ».
- **Voix d'enfant sans « boy »** (« child soloist », puis « about 6 years old ») : voix
  d'adolescente puis de femme, même en rejetant « woman singer ». Le mot « boy » tient la voix.

## La référence : à fournir soi-même

`.claude/skills/fal-musique/reference.mp3` est ignoré par git : chacun y dépose sa
propre chanson, ou passe `--reference`. Elle est téléversée entière sur le CDN fal à
chaque génération (URL publique).

Les styles de la recette décrivent la référence d'origine : chant liturgique en
mi♭ mineur à 136 BPM, voix de garçon soliste, piano et cordes. Avec une autre
référence, choisir dans `--fenetre` 30 s où voix et accompagnement sont tous deux
présents, et ajuster `STYLES` dans `fal_musique.py` s'ils la contredisent.
