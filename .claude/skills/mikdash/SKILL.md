---
name: mikdash
description: Répond aux questions sur l'architecture du Beit HaMikdash et le service du Temple (seder haavodah) en citant la source exacte — Mishna Middot, Tamid, Yoma, Talmud, Rambam — plutôt que de mémoire. Banque de sources qui dit où trouver la cote, l'ustensile, le vêtement, l'ordre du service, qui se tient où. À utiliser dès qu'une question porte sur le Temple, ses dimensions, ses portes, ses chambres, ses ustensiles, ses cohanim ou son rituel — « quelle taille fait l'autel », « où est le kiyor », « que fait le Cohen Gadol à Kippour », « le peuple peut-il entrer dans l'Azara », « combien de Léviim sur le Doukhan », « vérifie cette source », « où c'est écrit ».
---

# Beit HaMikdash — banque de sources

Ce skill ne contient **pas** les réponses. Il contient l'endroit exact où elles sont
écrites, et la méthode pour les en sortir. Une affirmation sur le Temple sans
référence n'a pas de valeur ici : la 3D, les prompts et la mise en scène du film
sont construits dessus, et une cote inventée traverse tout le pipeline.

## Règle

**Aucune affirmation sans référence.** Chaque fait donné en réponse porte sa source
sous la forme *œuvre chapitre:michna* (« *Middot* 3:1 ») ou *fichier:ligne* pour la
ligne du projet. Si la source n'est pas vérifiée, la réponse le dit : « je n'ai pas
vérifié » vaut mieux qu'une cote plausible.

Trois cas à ne jamais confondre :

1. **Ce que dit la source** — la michna, la guemara, le Rambam.
2. **Ce que le projet a retenu** — `fiche_technique_beit_hamikdash.md`, qui arbitre
   les divergences pour le film.
3. **Ce qui est réellement modélisé** — `beit_hamikdash_blockout.py`, la géométrie
   construite, qui peut avoir pris du retard sur la fiche.

Une réponse utile dit lequel des trois elle décrit. Quand ils divergent, le dire est
l'information principale.

## Ordre de consultation

1. **`fiche_technique_beit_hamikdash.md`** d'abord — grep le terme. Le projet a déjà
   tranché la plupart des questions, avec sa source à côté. §9 liste ce qu'une image
   ne doit jamais montrer, §12 qui se tient où.
2. **`references/index-thematique.md`** — la question → la michna exacte.
3. **`sefaria.py`** — lire le texte, ne pas le citer de mémoire.
4. **`references/corpus.md`** — quelle œuvre fait autorité sur quoi, et les
   reconstitutions modernes (Machon HaMikdash, archéologie) avec leurs liens.

Pour une question de géométrie construite, le skill `blender` ; pour ce qu'un cadre
montre vraiment, `beit_hamikdash_inspect.py -- --voit <plan>`.

## Lire les sources

```bash
S=.claude/skills/mikdash/sefaria.py

python3 $S ref "Mishnah Middot 3:1"              # hébreu + anglais + URL
python3 $S ref "Mishnah Yoma 5:1" --lang en
python3 $S ref "Mishneh Torah, The Chosen Temple 5:1"
python3 $S ref "Yoma 33b"                        # une page de guemara

python3 $S search "מקום דריסת ישראל"              # retrouver une source oubliée
python3 $S search "laver" --book "Mishnah" -n 5  # filtre par chemin de la biblio

python3 $S links "Mishnah Middot 3:1" --category Commentary   # ce qui commente ce passage
python3 $S links "Mishnah Middot 3:1" --category Talmud       # les parallèles
```

`search` prend l'hébreu comme le français translittéré ; l'hébreu donne toujours de
meilleurs résultats. `--book` accepte un chemin de la bibliothèque Sefaria
(`Mishnah`, `Mishnah/Seder Kodashim/Mishnah Middot`, `Halakhah/Mishneh Torah`).

Toute référence lue est citable telle quelle : `https://www.sefaria.org/Mishnah_Middot_3:1`.

## Divergences — les nommer, ne pas les lisser

Le corpus n'est pas unanime, et le film a dû choisir. Quand une question tombe sur un
désaccord connu, donner l'avis retenu **et** l'avis écarté, avec les deux sources :

- **Position du Mizbea'h** — décalé de 9 amot au sud selon *Middot* 5:1–2 ; R. Yehouda
  (*Zeva'him* 58b) le place au centre. Le film suit *Middot* (fiche §6).
- **Josèphe est hors corpus** — décision du projet, pas un arbitrage entre avis : le
  dépôt ne cite aucune source non juive sur le Temple. Ne pas le proposer, même en
  appui. Ce qu'on allait y chercher, le corpus le donne : les portiques de l'esplanade
  sont *Pesa'him* 13b (« הַר הַבַּיִת סְטָיו כָּפוּל הָיָה »), le cèdre des plafonds
  *Melakhim I* 6:9, le kaleh orev le Rambam sur *Middot* 4:6, la taille des pierres de
  taille *Melakhim I* 7:10.
- **Rambam vs Raavad** sur *Beit HaBe'hira* — les *Hasagot HaRa'avad* sont la première
  chose à lire quand une reconstitution moderne ne colle pas au Rambam.
- **Premier / Second / futur Temple** — Ézéchiel 40–43 et I Rois 6–7 ne décrivent pas
  le même bâtiment que *Middot*. Le film construit le **troisième** : plan et cotes de
  *Middot*, plus ce que le Premier Temple avait et que *Middot* ne répète pas (Ya'hin et
  Boaz, l'Arche). Une cote du Premier Temple est donc utilisable, jamais en silence :
  dire d'où elle vient, et si *Middot* dit autre chose sur la même pièce, *Middot* décide.
- **Ama** — le projet fixe 0,48 m (fiche §0) ; les sources vont de 0,45 à 0,58 m. Une
  conversion en mètres est toujours une convention, pas une donnée de la Mishna.

## Répondre

Format court, sourcé, dans l'ordre : la réponse, la référence, puis seulement si
elle diffère, la ligne du film.

> **32 × 32 amot à la base**, réduit à 24 × 24 pour le foyer par les retraits
> successifs (yesod, sovev, keranot) — *Middot* 3:1. Rampe au sud, 32 × 16 —
> *Middot* 3:3. Le film retient l'ama à 0,48 m, soit 15,4 m de côté (fiche §6).

Ne pas transformer une question en cours : répondre à ce qui est demandé, avec la
source. Ce qui déborde tient en une ligne, offerte, pas déroulée.

## Limites

Ce skill route vers des textes ; il ne rend pas de décision halakhique. Sur une
question qui engage la pratique, il donne les sources et le désaccord, et renvoie à un
rav — c'est aussi ce que dit l'en-tête de la fiche technique.
