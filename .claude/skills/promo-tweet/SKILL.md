---
name: promo-tweet
description: Rédige en anglais les posts X (Twitter) qui font connaître la visite du Beit HaMikdach (bethhamikdach.com) depuis le compte personnel de l'utilisateur — tweet seul, thread, post vidéo, histoire d'un service du Temple, coulisses du projet —, planifie la semaine sur le calendrier juif, publie via Chrome quand l'utilisateur le demande et tient le journal des posts. À utiliser dès qu'il est question de promotion du projet sur X/Twitter — « écris un tweet », « prépare les tweets de la semaine », « un thread sur Yom Kippour », « poste la vidéo », « envoie le post », « tweet sur l'autel », « comment marchent mes tweets », "draft a tweet", "plan this week's posts".
---

# Posts X

Fichiers dans `promo/` (gitignoré) : `tweets/<date>-<slug>.md` (un par post), `journal.md` (une ligne par post publié).

Publier seulement sur demande explicite de l'utilisateur, texte final montré avant : Chrome (skill **chrome-browser**), compte `@david_bonan`, post puis premier reply sous le post. Une vidéo de plus de 10 Mo ne passe pas par l'outil d'envoi : l'utilisateur la glisse dans le compositeur, puis Claude poste.

## Voix

Donner envie d'entrer dans le Beit HaMikdash, pas le décrire. Lecteur d'abord : le juif qui prie et qui apprend — le Beit HaMikdash qu'il demande dans la Amida, vers lequel il se tourne, dont il lit l'avoda. Ensuite : passionnés d'histoire et d'archéologie, devs 3D / WebGL. Anglais.

- **Le post est une accroche de 1–2 lignes** ; la vidéo ou l'image porte le lieu. Pas de liste de cotes. Modèle : "You've asked for it in every Amidah. / Here is the Beit HaMikdash, amah by amah from the Mishnah. Walk inside it."
- **Nommer le Beit HaMikdash** et puiser dans la tefila, l'avoda, le texte ; « walk inside » est l'atout : on y entre, ce n'est pas une maquette.
- **Sources, détail et lien vont dans le premier reply.**
- Le sujet est le Beit HaMikdash, ni un personnage mis en scène, ni le projet ou son auteur (Coulisses exceptés).
- Interdits : *stunning, breathtaking, game-changer, revolutionary, epic, excited to announce*, "🚀", "🧵👇". ≤ 1 emoji, aucun hashtag, aucun appât à engagement.
- Le Temple modélisé est celui à venir — plan de *Middot*, Arche revenue (en-tête de `fiche_technique_beit_hamikdash.md`) : jamais « Second Temple ».
- Les noms comme sur le site (Beit HaMikdash, Mizbeach, Heikhal, Kodesh HaKodashim, Azara, amah/amot).
- Un post qui commence par de l'hébreu s'affiche de droite à gauche : le préfixer d'un LRM (U+200E, compte 1).

## Ce qui ne se négocie pas

- **Chaque fait, post ou reply, a sa source exacte** (traité, chapitre, michna ; Talmud, Rambam ; siddur pour la tefila), vérifiée par le skill **mikdash** — jamais de mémoire. Une machloket se présente comme sur le site : l'avis retenu, l'avis écarté, sans trancher plus que le site.
- **Chaque fonction annoncée est en ligne** : vérifier la visite, `git log`, le skill **publier**.
- **Rien sur la politique, le Har HaBayit d'aujourd'hui ni les polémiques** ; ne pas répondre à ce terrain-là en commentaire.
- **Aucun post du vendredi coucher du soleil à la sortie de Chabbat, ni un jour de Yom Tov** (heure d'Israël et de Paris).
- Images et vidéos : la visite réelle seulement (skill **promo-video**), jamais un plan stylisé par IA.

## Types de posts

Mélanger sur une semaine ; une vidéo environ par semaine (`promo-video` la fait).

| Type | Forme |
|---|---|
| Clip | Accroche de 1–2 lignes + la vidéo. Source et lien en premier reply. |
| Un lieu | Une image fixe de la visite (`promo/footage/vues/`) + une accroche ; la cote sourcée en reply. |
| Le service | Thread, 4–8 posts : un rite pas à pas (le tamid, le seder ha'avoda de Yom Kippour, Sim'hat Beit HaSho'éva…), un post par station du parcours guidé, une image chacun, la source à chaque post. Calé sur le calendrier. |
| Question | Une question de texte que la 3D tranche ou rend visible : "Where did the Kohen Gadol first immerse on Yom Kippur? On a roof over the Water Gate (Yoma 31a)." |
| Coulisses | Pour les devs : une mesure, un bug, une décision — Blender → three.js, la cuisson de la lumière, la mémoire sur iPhone. Tiré de `git log`. |

## Calendrier

Avant chaque lot, regarder les fêtes des trois semaines à venir et leur parcours : Yom Kippour → `yom_kippour` ; Souccot → `simhat_beit_hashoeva`, `souccot_baboker`, `hakhel` (année de Hakhel) ; Pessa'h → `korban_pessah` ; Chavouot → `bikkourim` ; Tich'a beAv → le Temple tel qu'il se tenait, sans deuil mis en scène. Le post sort 2 à 5 jours avant la fête.

## Chaque brouillon

```markdown
# <slug> — <type>
When: <jour + heure, ex. Tue 16:00 Israel — matin US, après-midi Europe>
Sources: <chaque source citée, vérifiée par mikdash>
Media: promo/finals/<clip>.mp4 | promo/footage/vues/<id>.png | none
Alt text: <une phrase qui décrit le média>

## Post
<accroche>  (<n>/280)

## First reply
<source(s) + lien : https://bethhamikdach.com/en/, ou la vue exacte https://bethhamikdach.com/visite/?vue=<id>&lang=en — jamais dans le post, X classe les liens plus bas>

## Variant B
<une autre accroche pour le même post>
```

Compter les caractères avant d'enregistrer : une URL compte 23, un emoji 2, ≤ 280 par post. Thread : un `## Post k` par tweet.

## Lot de la semaine

1. Lire `journal.md` ; demander à l'utilisateur les stats des posts de plus de 48 h (impressions, likes, reposts, replies, bookmarks, profile visits) et les noter.
2. Matière : le calendrier, `git log` depuis le dernier lot, les clips de `promo/finals/`, les images de `promo/footage/`.
3. Proposer 3–5 posts (types mêlés, une vidéo), refaire ce qui a le mieux marché d'après le journal, essayer un angle nouveau. Écrire les brouillons.
4. Une fois publié, ajouter la ligne au journal : date, type, accroche, média, lien.

En-tête du journal : `| Date | Type | Hook | Media | Link | Impressions | Likes | Reposts | Replies | Bookmarks | Profile visits |`.
