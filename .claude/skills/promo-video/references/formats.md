# Formats et métier

## Contraintes de X

- MP4 H.264 + AAC (ce qu'écrit `render.py`), ≤ 2 min 20 s, ≤ 512 Mo. Viser **15–40 s**.
- Le fil lit en lecture automatique **muette** : l'histoire se lit sans le son. L'accroche, les libellés et la source la portent ; le son est un bonus.
- `landscape` pour un lieu large, une marche dans une cour. `square` prend plus de place dans un fil de téléphone : un seul objet, recadré. `portrait` pour une marche qui monte (Kodesh HaKodashim, degrés, rampe).

## Trame (45 s)

Rythme lent : des plans longs qui respirent, comme un documentaire. Un montage haché et rapide a été refusé.

| Temps | Rôle | Règle |
|---|---|---|
| 0–5 s | Accroche | L'image la plus forte d'abord, l'accroche en texte, un coup de son à 0. Jamais un logo ni un titre en ouverture. |
| 5–12 s | Contexte | Une ligne : ce qui se passe et où. |
| 12–38 s | Histoire | 3–4 plans, un lieu ou un geste chacun, une source chacun. |
| 38–44 s | Chute | Ce qu'on voit au bout : le Kodesh HaKodashim, l'autel allumé, la foule sur les degrés. |
| 44–48 s | Carte de fin | `{"kind": "end", "duration": 4}`. |

L'angle est toujours le Temple et l'avoda — le lieu, le geste, sa source —, jamais un personnage mis en scène : « Once a year. One man. One room. » a été refusé, « The Yom Kippur service in the Temple » retenu.

## Séries

Tester un format nouveau par lot ; garder ce qui retient l'attention (journal, `promo-tweet`).

- **Un lieu** (10–15 s, `square`) : un `plan` lent sur un seul lieu, une cote sourcée. Accroche = la cote : "32 cubits square. Middot 3:1."
- **Le service** (40–50 s, le fleuron) : un rite en 5–6 plans, une source par plan. Calé sur le calendrier (Yom Kippour, Souccot, Pessa'h, Chavouot).
- **L'architecture** (45–50 s) : 5–6 lieux, du dehors vers le dedans, une cote sourcée par lieu.
- **Les dix degrés** (30 s) : le parcours `esser_kedushot`, du Har HaBayit au Kodesh HaKodashim, un degré par plan, Kelim 1:6–9.
- **Le saviez-vous** (15 s) : un détail que la 3D rend visible — le mikvé sur le toit de Sha'ar HaMayim, les rashei pispasin du Beit HaMoked. Tiré de `git log`.
- **Jour / nuit** (10 s) : la même vue de jour puis de nuit (`--moment nuit`), un `cut` sur le temps fort.
- **Coulisses** (15–20 s) : pour les devs — la scène Blender puis la visite, une mesure, une correction. Captures de l'outil seulement.

## Grammaire visuelle

- **Visite réelle seulement.** Toutes les images sortent de `capter.mjs` ; aucune image générée par IA.
- **Toujours en mouvement.** Aucun plan figé : au moins une poussée lente (`zoom` 1 → 1,06). Un seul mouvement de caméra par plan.
- **Cadrer à la capture, pas au montage.** `plan` en focale réelle (`focale` 28–45 mm ; la focale de la visite, ≈ 17 mm, fait jeu vidéo), capté en `--taille 2560x1440`. Au montage, `camera` 1 → 1,05 au plus.
- **Plans de 6–9 s**, une course lente et continue (travelling, grue, poussée) avec un premier plan qui défile pour la profondeur. Regarder la planche : le sujet ne sort pas du cadre, le plan ne finit ni dans le noir ni sur un mur.
- **Mots.** Un plan sur deux sans libellé ; un libellé n'est jamais sur le sujet. ≤ 7 mots, majuscule en début de phrase seulement, verbes concrets, pas de point sauf sur la chute. Aucun mot de pub (*stunning, epic, breathtaking*). Aucun emoji. Les noms comme sur le site (Mizbeach, Heikhal), glosés une fois si l'accroche ne le fait pas.
- **La source à l'écran.** `cite` sur le plan qui montre ce que la source dit : "Mishnah Middot 3:1", "Yoma 31a", "Rambam, Beit HaBechirah 2:5".
- **Charte du site seulement.** Nuit `#100E0B`, lin `#F6F1E6`, or `#C9A04A`. Marcellus pour les titres, Source Serif 4 pour le texte, Frank Ruhl Libre pour l'hébreu.
- **Transitions.** `fade` de 1–1,5 s par défaut. `cut` seulement sur un coup de musique ; pas de `flash`, `zoom` ni `slide`.

## Son

- **Musique** : sacrée et retenue — oud, ney, cordes chaudes, tambour sur cadre, vocalise sans paroles ; une montée nette quand l'histoire commence, pas de « drop » électronique. `example-music.txt`. Sections aux durées de la trame, puis alignement par `sound.py energy`, jamais par le fichier de piste (le modèle dérive de 1–2 s).
- **Voix** (facultative) : première personne, calme, en anglais. "I rebuilt the Temple to the measurements of the Mishnah." Une phrase par fichier, ≤ 12 mots. Choisir la voix par format dans la bibliothèque ElevenLabs (`--voice <id>`) ; par défaut un narrateur britannique.
- **Bruitages** : pas sur la pierre, crépitement du feu de l'autel, vent sur l'esplanade, rumeur lointaine d'une foule. Mesurer chacun (`ffmpeg -i <f> -af ebur128 -f null -`) : sous -35 LUFS il est inaudible, le remonter par `loudnorm=I=-20` ou le regénérer.
