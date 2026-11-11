---
name: promo-video
description: Monte les vidéos promo de la visite du Beit HaMikdach pour X (Twitter) — images captées dans la visite 3D réelle (vues fixes, marche d'un parcours guidé avec ses figurants, caméra libre), montage Remotion avec recadrages, sources citées à l'écran et carte de fin du site, musique / voix / bruitages ElevenLabs, rendu en MP4 prêt pour X. Textes à l'écran en anglais. À utiliser dès qu'il faut une vidéo promo ou un clip de la visite — « fais une vidéo promo », « monte un clip pour twitter », « une vidéo sur Yom Kippour », « filme le parcours du tamid », « un clip sur l'autel », « refais le rendu du clip », "make a promo video".
---

# Vidéo promo

Tout atterrit dans `promo/` (gitignoré) : `footage/` (bibliothèque partagée), `clips/<date>-<nom>/` (un dossier par clip : `storyboard.json` + ses médias), `drafts/`, `finals/<date>-<nom>.mp4` (prêt à poster, rien d'autre).

`s=.claude/skills/promo-video/scripts`. Une fois par machine : `npm ci` dans `studio/`. Clé `ELEVENLABS_API_KEY` dans l'environnement ou le `.env` de la racine.

Appels payants (ElevenLabs) : `--dry-run` d'abord, annoncer le coût du lot, attendre le feu vert, puis lancer. Capture, montage et rendus sont gratuits.

## Faire un clip

1. **Brief** : une ligne — la promesse, le format, la série (`references/formats.md`). Écrire 3 accroches, garder la plus forte. Chaque fait à l'écran a sa source exacte, vérifiée par le skill **mikdash** ; chaque fonction montrée est en ligne.
2. **Images — la visite réelle seulement.** Jamais un plan stylisé par IA (`render/style/`, `render/video/`, fal.ai) : décision de l'utilisateur. La visite servie depuis la racine du dépôt (`python3 -m http.server 8766 --bind 127.0.0.1`, s'il ne tourne pas déjà), `v=http://127.0.0.1:8766/visite/` :
   ```bash
   node $s/capter.mjs $v vue mizbeach,heikhal promo/footage/vues                     # une image par vue (ids : window.__vues())
   node $s/capter.mjs $v parcours yom_kippour 7 promo/footage/parcours/yk_07           # la marche de la station 6 à 7, puis 3 s de halte
   node $s/capter.mjs $v plan promo/footage/plans/boucs.json promo/footage/plans/boucs # caméra libre
   ```
   Options : `--taille 1920x1080` (`1080x1080` carré, `1080x1920` portrait), `--fps 30`, `--halte <s>`, `--moment jour|nuit|aube|avant_l_aube|fin_de_nuit`, `--interface` (garde la carte du parcours, les boutons — pour montrer l'outil). Une séquence sort en images dans le dossier et en `<dossier>.mp4`.
   - **Parcours** : stations et ids dans `visite/parcours.json`. Une station `fondu` (un toit) se rejoint sous le voile : le script refuse, il n'y a pas de marche — filmer un `plan` sur place.
   - **Plan** (le format des beaux plans) : `{"parcours"?, "station"?, "moment"?, "focale"?, "cles": [{"t", "oeil": [x, hauteur, z], "cible": [x, hauteur, z]}]}`, en amot, repère de `visite/cinema.json` et `parcours.json` (+x est, z+ sud, Azara au sol 0) ; `parcours` + `station` amènent la troupe, l'heure et les figurants de cette station, `moment` l'heure, `focale` les mm sur un 24 × 36. Partir du `point`/`sol`/`cible` d'une station ; une seule course de caméra par plan, lente (`formats.md`, Grammaire visuelle). Capter d'abord une image fixe (`cles` à `t` 0 seulement) pour juger le cadre.
   - Regarder chaque source en planche avant d'écrire le storyboard : `ffmpeg -i <vidéo> -vf fps=1,scale=480:-2,tile=5x4 -frames:v 1 <planche>.png`.
   - Copier ce que le clip utilise dans `clips/<clip>/footage/`.
3. **Storyboard** : `clips/<clip>/storyboard.json` depuis `references/example-storyboard.json`, sur la trame de `formats.md`. Champs : `references/storyboard.md`.
4. **Brouillon muet** : `python3 $s/render.py promo/clips/<clip> --draft`. Lire `clips/<clip>/contact.png` : cadrage, recadrage sur le bon élément, textes lisibles et jamais sur le sujet, source affichée sur le plan qui la montre. Corriger et refaire jusqu'à ce que le clip se lise sans le son.
5. **Son**, sur le montage arrêté :
   - Musique instrumentale : `clips/<clip>/music.txt` (`references/example-music.txt`), sections aux durées du montage. `python3 $s/music.py --track promo/clips/<clip>/music.txt --out-dir promo/clips/<clip>/music --takes 2`. Mesurer chaque prise (`sound.py energy --in …`), garder celle dont la montée tombe sur le début de l'histoire, l'aligner par `music.at` / `music.start`, puis `sound.py even`. Un air connu (un niggun) : `--reference <enregistrement libre de droits> --window 1-31` conditionne chaque section sur 11–30 s de l'air (téléversé une fois, facturé comme une génération de sa durée) ; sans référence, le modèle invente l'air. Un texte hébreu chanté : ses lignes translittérées sous l'en-tête de leur section (l'hébreu dessous n'est pas envoyé), `voice:` décrit les chanteurs, une section sans ligne reste instrumentale ; voix de garçon et piano, c'est le skill **elevenlabs-musique**, dont les mp3 de `render/audio/musique/` servent aussi. **Jamais un morceau du commerce** (celui d'Ishay Ribo dans `render/audio/` compris) : X coupe le son ou retire la vidéo.
   - Voix (facultative) : une phrase par fichier, `python3 $s/sound.py voice --text "…" --out promo/clips/<clip>/voice/v1.mp3` ; placer chaque `at` d'après la longueur de la phrase.
   - Bruitages : `sound.py effect --text "…" --seconds …` — pas sur la pierre, feu de l'autel, vent sur l'esplanade.
6. **Final** : `python3 $s/render.py promo/clips/<clip>` → `finals/<clip>.mp4` (-14 LUFS, crête < -1 dBTP) + `contact.png`.
7. **Contrôle** : planche propre (textes nets, source lisible, carte de fin lisible) ; `sound.py energy --in promo/finals/<clip>.mp4` ne montre aucun trou sous -25 dB avant la carte de fin. Le rythme et la voix se jugent à l'oreille seulement : le dire à l'utilisateur et lui donner le chemin.

Puis passer le clip à **promo-tweet** pour le post.

## Pannes

- Rendu Remotion bloqué sur « Waiting for root component to load » : `REMOTION_BROWSER=~/Library/Caches/ms-playwright/chromium_headless_shell-<n>/chrome-headless-shell-mac-arm64/chrome-headless-shell` devant `render.py`.
- `capter.mjs` prend le Chromium du cache playwright (`~/Library/Caches/ms-playwright/chromium-*`) et rend sous Metal ; sans cache, `npx playwright install chromium` dans `studio/`.

## Coûts

Musique ≈ 12,5 crédits ElevenLabs par seconde (375 pour 30 s, par prise). Voix et bruitages : quelques dizaines de crédits par phrase. ElevenLabs refuse plus de 2 requêtes simultanées (429). Remotion est gratuit pour un particulier.
