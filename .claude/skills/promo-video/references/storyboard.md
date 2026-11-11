# storyboard.json

Un par clip, à la racine de `promo/clips/<date>-<nom>/`. Tout chemin est relatif à ce dossier (Remotion le sert tel quel). Exemple complet : `example-storyboard.json`.

| Champ | Contenu |
|---|---|
| `format` | `landscape` (1920×1080, défaut), `square` (1080×1080) ou `portrait` (1080×1920). |
| `hook` | Ligne d'ouverture, bandeau du bas, les mots apparaissent un à un. ≤ 7 mots. |
| `hookSeconds` | Durée de l'accroche, 2,2 s par défaut. |
| `shots` | Dans l'ordre. Durée du clip = somme de leurs `duration`. |
| `voice` | `{audio, at, volume?}` : une phrase et sa seconde de départ. Le `.json` voisin (écrit par `sound.py voice`) donne les sous-titres mot à mot et baisse la musique. |
| `effects` | `{audio, at, volume?}`. |
| `music` | `{audio, at?, start?, volume, underVoice}` : `at` = départ dans le clip, `start` = décalage dans le fichier, `underVoice` = niveau pendant la voix. Fondu sur les 1,2 dernières secondes. |

## Plan

Commun : `kind`, `duration` (de coupe à coupe), `label` (texte du bandeau du bas pour ce plan, ≤ 7 mots, jamais sur un plan avec voix), `transition` `{type, duration}` centrée sur la coupe : `cut`, `fade`, `slide`, `wipe`, `zoom` (traverse vers le plan suivant), `flash` (éclair or, sur un coup de musique).

| `kind` | Champs en plus |
|---|---|
| `full` | La capture plein cadre. `source`, `start`, `speed`, `camera`, `filter`, `cite`. |
| `window` | Mêmes champs, la capture en fenêtre flottante sur le fond de la charte — pour montrer l'outil (`capter.mjs --interface`). |
| `title` | `title` (≤ 5 mots, en Marcellus), `kicker` (petites capitales or au-dessus, ex. `Yom Kippur`). |
| `end` | Carte de fin : la marque du site, *Beit HaMikdach*, *Every stone cites its source.*, pastille `cta` (défaut `bethhamikdach.com`). 3 s. |

Champs d'image :

| Champ | Contenu |
|---|---|
| `source` | Image `.png` / `.jpg` ou vidéo `.mp4`, copiée dans le dossier du clip (`footage/…`). |
| `start` | Seconde de la source au début du plan. |
| `speed` | `2` pour ×2, `[4, 1]` passe de ×4 à ×1 sur le plan, `0` fige. |
| `camera` | Clés `{t, x, y, zoom}` : `t` secondes dans le plan, `x`/`y` le point du cadre (0–1) amené au centre, `zoom` ≥ 1. Lissé, ne sort jamais du cadre. Sur un plan `window`, le cadre inclut le fond. |
| `filter` | Filtre CSS. |
| `cite` | La source de ce que le plan montre, en haut à gauche pendant tout le plan : `"Mishnah Middot 3:1"`. |
