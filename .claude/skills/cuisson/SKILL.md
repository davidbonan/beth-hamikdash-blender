---
name: cuisson
description: Recuit les cartes de lumière de la visite 3D (visite/lumiere/) dans Cycles — en ciblant ce qu'une retouche touche au lieu de tout recuire pendant une heure. À utiliser dès qu'il faut recuire, relancer la cuisson, mettre à jour la lumière ou l'occlusion après une retouche du blockout, d'une matière ou d'un réglage de lumière — « recuis la Lishkat HaGazit », « la lumière du Kiyor est fausse », « relance la cuisson », « qu'est-ce qu'il faut recuire », « combien de temps va prendre la cuisson », « une cuisson tourne-t-elle déjà ». Pour exporter la visite sans cuisson ou regénérer la scène, c'est le skill blender.
---

# Cuisson de la lumière

```
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
```

`beit_hamikdash_visite.py` exporte la visite ; en chemin, `beit_hamikdash_occlusion.py` cuit
une carte par concept et `beit_hamikdash_recuisson.py` décide lesquelles refaire. `reperes.json`
garde sous `empreintes` celle de **chaque** concept, cuit ou non — maillage après séparation des
faces collées, taille, couches UV, matières, réglages de lumière (soleil, ciel, lampes,
échantillons…) — et chaque carte sa durée de cuisson en `secondes`.

## Règle 1 — recuire ciblé, avec ses impacts

```bash
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_visite.py -- --recuire                               # le recuit
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_visite.py -- --recuire lishkat_hagazit,azara        # + ces concepts, qui doivent se cuire
```

`--recuire` recuit en lumière :

| Raison | Quand |
|---|---|
| `modifié` | son empreinte a changé depuis la dernière cuisson, ou sa carte manque — détecté seul |
| `demandé` | nommé après `--recuire` : pour ce que l'empreinte ne voit pas |
| `voisin de X` | sa géométrie passe à moins de `PORTEE_IMPACT` (4 m) de X, avant ou après la retouche : les rebonds de X changent sa lumière |

X peut être un concept sans carte (Kiyor, Menora, ustensiles, trop petits pour cuire) ou disparu :
la sortie le liste sous « modifiés sans carte à eux » et recuit ses voisins.

Toutes les autres cartes restent telles quelles. Un réglage de lumière changé change toutes
les empreintes : `--recuire` recuit alors tout, sans qu'on le demande.

Lancer `--recuire` directement, sans simulation préalable.

Nommer un concept après `--recuire` seulement pour ce que l'empreinte ne voit pas : une retouche
de `matieres.js` ou d'un nuanceur de la visite, ou une carte qu'on juge fausse.

Les voisins ne sont recuits que sur un rang : le rebond du rebond reste. Après beaucoup de
retouches cumulées, ou avant une publication importante, recuire tout :

```bash
$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_visite.py -- --lumiere tout      # ~1 h
```

Première cuisson avec ce mécanisme : aucune carte n'a encore d'empreinte, `--recuire` recuit tout.

## Règle 2 — une seule cuisson à la fois sur la machine

Worktrees compris : elles se disputent le GPU, et deux cuissons ensemble sont plus lentes qu'en
file. Le script le garantit : il prend `cuisson.lock` dans le `.git` commun (`flock`, relâché
à la mort du processus, même tué). Une seconde cuisson s'arrête aussitôt :

```
  cuisson déjà en cours, rien n'est lancé : <worktree> · pid <pid> · depuis <HH:MM> · <options>
```

Alors : ne pas tuer la cuisson en cours, ne pas contourner le verrou. Dire à l'utilisateur qui
cuit, depuis quand, et attendre qu'elle finisse ou qu'il décide. `cat "$(git rev-parse --git-common-dir)/cuisson.lock"`
dit qui tient le verrou (vide : personne). `--sans-occlusion` ne cuit pas et
ne le prend pas.

## Lancer

Une cuisson dure de quelques minutes à une heure : la lancer en arrière-plan
(`run_in_background`), sortie dans un fichier, et attendre sa notification sans sonder.
Filtrer le bruit : `grep -vE "Deprecation|use_nodes|Read blend|Blender quit|^Blender 5|volumes$"`.
Blender sort en code 0 même sur une erreur Python : chercher `Traceback` dans la sortie.

La visite servie garde ses cartes pendant la cuisson : `livrer` ne remplace `visite/` qu'à la fin.
Les lignes `lumière <concept> … s` disent l'avancement ; la dernière, le total.

Après : `git status visite/` montre les cartes recuites et `reperes.json`. Commiter les deux
ensemble — sans les empreintes, la prochaine recuisson referait tout.
