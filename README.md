# Beit HaMikdash × « Seder HaAvodah » (Ishay Ribo)

Film de ~6 min sur l'Avodah de Yom Kippour : un seul mouvement d'est en ouest (lumière → Kodesh HaKodashim) puis retour vers la lumière. Pipeline hybride : blockout Blender à l'échelle de la Mishna, stylisation IA conditionnée par la profondeur, montage sur les mesures du morceau.

Le Temple filmé est celui **à venir** : architecture hérodienne (*Middot*), et dans le Kodesh HaKodashim l'Arche revenue à sa place sur l'Even HaShetiya — celle de Moïse, cachée sous le Temple et révélée (*Yoma* 54a ; Rambam *Beit HaBe'hira* 4:1), avec la kaporet et ses deux keruvim (fiche §8h).

## Fichiers

| Fichier | Rôle |
|---|---|
| `fiche_technique_beit_hamikdash.md` | Référence architecturale : cotes en amot, sources (*Middot*, *Yoma*, *Tamid*, Rambam, Josèphe), matériaux, §9 = liste des erreurs à ne jamais laisser passer. |
| `beit_hamikdash_blockout.py` | Script Blender : génère toute la scène en volumes gris + 15 caméras animées + marqueurs de timeline. |
| `shot_list_seder_haavodah.md` | Découpage en 19 plans calé sur la structure du morceau, + pipeline de production (étapes A→E). |
| `prompts_par_plan.md` | Prompt image/vidéo par plan, prompt négatif commun, réglages, checklist de vérification. |
| `beit_hamikdash.blend` | Scène générée par le script (à régénérer après toute modification du script). |
| `beit_hamikdash_export.py` | Images clés des plans : planche de contrôle en 640 × 360 (`-- --planche`), ou fichiers de production couleur + profondeur en 1920 × 1080. |
| `beit_hamikdash_analyse_plans.py` | Mesure, plan par plan, ce que les deux frames ont en commun — le chiffre qui décide si un i2v peut tenir le plan. |
| `beit_hamikdash_inspect.py` | Lit la scène sauvegardée et répond : où est un objet, ce qu'une caméra a vraiment dans le cadre, quel plan dure combien. Ne reconstruit rien. |
| `.claude/skills/blender/` | Skill Claude Code : les incantations headless des quatre scripts, et l'invariant « le script est la source, le .blend est l'artefact ». |
| `.claude/skills/fal-video/` | Skill Claude Code + client `fal_video.py` : génère un plan sur fal.ai en ligne de commande (image-to-video première + dernière frame), sans passer par le site. |
| `renders/` | Sorties, une étape du pipeline par dossier — voir ci-dessous. |

### Le dossier `renders/`

Un dossier par étape, et rien à la racine :

| Dossier | Étape | Contenu |
|---|---|---|
| `renders/blockout/` | 1 | rendus Blender 1920 × 1080 : `CAM_xx_{debut,fin}.png` et `..._profondeur.png`. Ce sont les entrées de l'i2i. |
| `renders/planche/` | 1 | planche de contrôle 640 × 360 + `planche.html` : première et dernière image des 19 plans, avec focale et frames. |
| `renders/style/` | 2 | images clés stylisées (`fal_image.py`). |
| `renders/video/` | 4 | les mp4 (`fal_video.py`). |
| `renders/archive/` | — | `style/`, `video/`, `validate/` périmés : générations faites avant les re-cadrages consignés plus bas, plus `frames_orphelines/`. Rien ne les lit. |

`frames_orphelines/` : quinze images `CAM_15_fin.png0001.png`… retrouvées dans
`renders/planche/`. Aucun des quatre scripts ne peut les écrire — aucun ne rend
d'animation —, mais l'export laissait le `.blend` avec `render.filepath` pointant sur
son dernier fichier : n'importe quel rendu d'animation lancé ensuite déverse ses
frames à cet endroit, sous ce nom suffixé du numéro d'image. L'export **remet
maintenant `filepath` à vide avant de sauvegarder**.

## Démarrage

```bash
/Applications/Blender.app/Contents/MacOS/Blender --python beit_hamikdash_blockout.py
```

Ou : Blender → onglet *Scripting* → coller le fichier → *Run Script*. Vérifié sur Blender 5.2 : **4989 objets (foule et proxys de sujet compris), 19 caméras, 8472 images à 24 fps = 353 s = 5:53**, la durée exacte du morceau. Les marqueurs de timeline changent de caméra automatiquement ; `Ctrl+Numpad0` pour activer une caméra.

Constantes en tête de fichier : `AMA = 0.48` (Rav 'Haïm Naeh), `MENORA_DROITE` (branches droites Rambam / courbes), `PORTES_HEIKHAL_OUVERTES` (battants rabattus dans l'embrasure, comme pendant l'avoda), `FPS`.

**La génération prend quelques secondes** — 2,5 à 3,5 s, chargement du .blend compris.
Elle en prenait une quinzaine de *minutes* tant que le script posait ses volumes avec
`bpy.ops.mesh.primitive_*` : chaque appel d'opérateur réévalue le graphe de
dépendances, et le coût est quadratique en nombre d'objets (mesuré : 0,44 s pour 200
cubes, 11,9 s pour 800, 52,6 s pour 1600). Les 4640 volumes se construisent
maintenant directement en `bpy.data`, sommet par sommet, à travers les helpers `box`,
`prism`, `cyl`, `cone`, `sphere`, `tore`, `cyl_between`. **Ajouter une forme, c'est
ajouter un helper, pas un opérateur.**

La scène est la même, et ça se vérifie plutôt que ça ne se croit : les 4692 objets
portent les mêmes noms, le même nombre de sommets et de faces, et chaque sommet est à
**17 µm au plus** de celui que posait la primitive (0,000035 ama, sur un bâtiment de
100 amot — c'est la résolution du float32 à 115 m de l'origine, pas un déplacement).
Aucune normale n'est rentrante, ce qui compte parce que c'est la passe Normal qui
conditionne l'i2i, et `beit_hamikdash_analyse_plans.py` redonne les mêmes dix-neuf
diagnostics.

### Interroger la scène sans la reconstruire

`beit_hamikdash_inspect.py` ouvre le .blend sauvegardé et répond — pas de
`-P beit_hamikdash_blockout.py` devant, donc pas de reconstruction :

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
    -P beit_hamikdash_inspect.py -- --voit 3
```

`--scene` (défaut) donne les collections, les 19 plans et l'étendue ; `--objets
<motif>` les bornes en amot d'un objet ; `--camera <plan>` la pose, le champ et la
vitesse aux deux frames clés ; `--voit <plan> [debut|fin]` **ce que le cadre contient
vraiment**, mesuré à la grille de rayons et par part d'écran. C'est cette dernière
qui répond aux questions du type « la fenêtre du Beit Avtinas montre-t-elle la
cour » sans y répondre à l'œil. Le numéro de plan s'écrit `9`, `9a`, `CAM_09A` ou en
entier.

Le .blend qu'il lit date du dernier export : `beit_hamikdash_export.py` est le seul
script qui appelle `wm.save_mainfile`.

### Matière et rendu

Le blockout n'est plus en volumes gris : les matières sont **procédurales et lues en
coordonnées de monde** (`Geometry > Position`), donc les assises d'un mur se
poursuivent d'une boîte à la suivante — un mur percé en est fait de cinq. Ce sont
elles, avec le **biseau** posé sur toute l'architecture (1057 modificateurs, 2 segments,
limite à 30°), qui remplissent la passe **Normal** : plate, elle laissait l'i2i
redessiner chaque arête à chaque image.

| Fonction | Ce qu'elle donne |
|---|---|
| `pierre` | calcaire en **assises** de 1 ama, chacune tirée un peu plus claire ou plus sombre que sa voisine (fiche §7), joint creusé |
| `enduit` / `enduit_noirci` | chaux des pierres non taillées (*Middot* 3:4) ; noircie au sommet du Mizbea'h par le feu (fiche §5) |
| `dallage` | dalles de 3 amot à joint creux — c'est le joint, en lumière rasante, qui donne la fuyante des cours |
| `metal` | or et bronze **vraiment métalliques**, rugosité brouillée au bruit (l'or du Temple est martelé, pas poli) |
| `marbre` | veiné, pour les huit tables du Beit HaMitba'haïm et celle de l'Oulam |
| `bois` | cèdre des plafonds, chêne des maltera'ot (*Middot* 3:7, Josèphe) |
| `etoffe` | parokhot, bigdei lavan, laine de la foule |
| `braise` | charbons émissifs de la ma'arakha, plus une lampe surfacique : l'autel n'était pas allumé |
| `nuee` | proxy de fumée — **opaque à dessein**, il doit écrire la passe Z sur laquelle l'export mesure sa plage |

Volumes : `box`, `cyl`, `cone`, `sphere`, `prism`, `tore`, `cyl_between`, et `revolution` — un profil (rayon, hauteur) tourné autour d'une verticale, paroi extérieure en montant puis intérieure en descendant, pour ce qui est creux (le kaf).

Ajouts de géométrie : les colonnes des portiques et de la Stoa ont **base et chapiteau**
(235 chapiteaux), et la nef de la Stoa un **plafond à caissons** (100 poutres) — c'est la
cadence des poutres qui donne sa vitesse au travelling du plan 2, et elle entre dans la
passe Depth.

Éclairage : soleil d'aube inchangé (4 W/m², 12° au-dessus de l'horizon), fond en
**dégradé de brume** (bleu au zénith, brume près de l'horizon, pas de ligne d'horizon).
Un vrai ciel physique (*Sky Texture*) a été essayé et écarté : mesuré, il éclaire quatre
fois plus, et il assombrit tout ce qui est sous l'horizon — comme rien n'est modélisé
au-delà du Har HaBayit, le Temple s'y lisait posé sur une mer.

Moteur : Eevee avec **ombres, raytracing écran et fast GI** (sans rebond, les intérieurs
des plans 9 à 12 tombaient en aplat : le Heikhal n'est éclairé que par la Menora et
quatre fenêtres hautes). Pour les images clés seulement, **`--cycles`** au blockout bascule
en Cycles 128 échantillons, GPU si disponible :

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
    -P beit_hamikdash_blockout.py -P beit_hamikdash_export.py -- --cycles
```

Trente-huit frames, pas 8472 : le film ne sort pas de Blender. Les deux rendus de
données par frame (mesure de la plage Z, carte de profondeur) retombent alors à un seul
échantillon — ils ne dépendent pas de l'échantillonnage. Compter large : sur Metal
(M5 Pro), le plan 9a en 640 × 360 met déjà ~2 min, chargement du .blend compris.

Planche de contrôle des 19 plans (rendu Eevee 640 × 360, début + fin de chaque caméra) :

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
    -P beit_hamikdash_blockout.py -P beit_hamikdash_export.py -- --planche
open renders/planche/planche.html
```

Le blockout n'est à rechaîner que si le **script** a changé : l'export sauvegarde le
.blend, donc pour re-rendre sur la scène déjà générée il suffit de
`-P beit_hamikdash_export.py -- --planche` (deux minutes au lieu d'un quart d'heure).

Et la mesure qui va avec — pour chaque plan, ce que ses deux frames ont en commun :

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
    -P beit_hamikdash_blockout.py -P beit_hamikdash_analyse_plans.py
```

**19 plans et non 15** : quatre se filment en deux prises. Un i2v à deux frames
n'interpole que ce que les deux frames partagent, et sur le 7 (panoramique de 142°),
le 9 (relevé de 56° pour 46° de champ), le 13 (traversée du mur est du Heikhal) et
le 14 (grue franchissant une ligne d'horizon) elles ne partageaient rien. La durée
totale ne bouge pas : chaque plan coupé garde la sienne, répartie sur ses deux
moitiés. Elles s'appellent `7a`/`7b`, `9a`/`9b`, `13a`/`13b`, `14a`/`14b` — dans les
scripts fal aussi (`--plan 9a`).

## Pipeline

1. **Blockout** — lancer le script, vérifier les 19 plans sur la planche, rendre en Eevee avec les passes **Combined + Depth + Normal** (déjà activées). Les sujets non architecturaux (kohanim, par, ma'hta) existent en volumes grossiers dans **une collection par plan**, `75_Plan03`, `75_Plan05`, `75_Plan06`… : ils stabilisent les passes Depth/Normal pour que l'i2i ne réinvente pas le sujet à chaque image, et l'export ne montre que celle du plan qu'il rend. La foule du jour vit dans `76_Foule`, à part : un proxy est le sujet d'un plan, la foule est l'état permanent (emplacements et sources : §12 de la fiche technique) — **les Léviim du Doukhan en font partie**, ils ne sont le sujet d'aucun plan.

   **Le script ne sauvegarde pas le .blend.** En headless sa géométrie est donc jetée à la sortie de Blender. Pour reconstruire *et* exporter, chaîner les deux scripts dans la même instance — c'est l'export qui appelle `wm.save_mainfile` :

   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
       -P beit_hamikdash_blockout.py \
       -P beit_hamikdash_export.py -- CAM_01_Ouverture_MontOliviers
   ```
2. **Images clés** — planche de style de 6–8 images, seed fixée. Sortir les quatre fichiers du plan (couleur + profondeur, début et fin) :

   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
       -P beit_hamikdash_blockout.py -P beit_hamikdash_export.py
   ```

   Sans argument le script exporte les 19 plans ; après `--` on lui passe les caméras à réexporter seules. Les frames viennent des propriétés `frame_debut` / `frame_fin` de chaque caméra. La carte de profondeur est normalisée 0-1 sur la plage réellement visible du frame (mesurée sur la passe Z), **échelle logarithmique, proche = blanc** : ni le proche ni le lointain n'est écrasé.

   Puis stylisation via le skill `fal-video` — entrées dans `renders/blockout/`, sortie dans `renders/style/` :

   ```bash
   python3 .claude/skills/fal-video/fal_image.py --plan 9 --frame debut
   python3 .claude/skills/fal-video/fal_image.py --plan 9 --frame fin
   ```

   Par défaut le modèle `nano-pro` (Nano Banana Pro) **repeint** le blockout sans rien y déplacer : la géométrie de la Mishna est celle de Blender, l'IA n'apporte que matière et lumière. Sortie en 2752 × 1536, donc pas d'upscale à prévoir pour un 1080p. Les modèles conditionnés par la carte de profondeur (`depth`, `pro-depth`) restent disponibles mais réinventent les ustensiles — mesures dans le SKILL.

   Deux points que le plan 9 a mis au jour, valables pour tous les plans : l'export ne laisse visible que la collection de sujet du plan rendu — une silhouette d'un autre plan traînant dans le cadre devient un objet inventé —, et une frame dont le cadre ne montre plus la scène du plan a désormais son propre plan plutôt qu'une ligne `**Prompt fin**`.
3. **Contrôle halakhique** de chaque image clé contre la §9 de la fiche technique. Corriger en inpainting avant d'animer.
4. **Mouvement** — image-to-video, en ne décrivant que la caméra et ce qui a le droit de bouger ; 5–10 s générées, ralenties à 50 % au montage. À deux frames quand le plan avance, à **une seule image + prompt de mouvement** quand la caméra est fixe (plans 6 et 15 : leurs deux frames sont la même image, mesurée à 100 % de recouvrement — un couple identique ne donne rien à interpoler et le modèle comble en dérivant).

   ```bash
   python3 .claude/skills/fal-video/fal_video.py --plan 9a --simulation      # prompt, coût, contrôle
   python3 .claude/skills/fal-video/fal_video.py --plan 9a --controle-fait   # générer
   ```

   **Contrôle avant génération, obligatoire** : le script affiche le bloc **CONTRÔLE AVANT VIDÉO** de `prompts_par_plan.md` et refuse de générer sans `--controle-fait`. Deux passes sur les deux frames stylisées — le **positionnement** de chaque élément comparé au blockout (place, échelle, orientation, nombre, cadrage) et les **zones d'accès** de la §12 de la fiche technique : le peuple ne dépasse pas les 11 amot de l'Ezrat Israël, le Doukhan est aux Léviim, l'Ezrat Cohanim et l'espace entre l'Oulam et l'autel aux cohanim, le Kodesh HaKodashim au seul Cohen Gadol. L'i2v ne corrige rien : il fait marcher la silhouette mal placée.

   Prompt et négatif viennent de `prompts_par_plan.md` (ligne **Mouvement** du plan), le mp4 arrive dans `renders/video/`. Clé `FAL_AI_KEY` dans le `.env`.
5. **Montage** (DaVinci Resolve) — poser les marqueurs de sections sur l'audio, couper sur les débuts de mesure (75 BPM, 4/4 → 3,2 s), LUT et grain uniques pour tout le film.

Ordre conseillé : plans 1-2-15 (style) → 8-9a-9b-13a-13b (cœur technique) → 11-12 → 4-5-6-14a-14b → 3-7a-7b-10.

## Règles non négociables

- Aucun visage. Le Cohen Gadol est de dos ou en silhouette ; le sujet est l'architecture et la lumière.
- Kodesh HaKodashim = obscurité, l'Arche et ses keruvim pris dans la lueur de la braise, fumée ; aucun autre décor, aucun personnage. L'Arche est **fermée**, ses deux keruvim ont des visages d'enfant tournés l'un vers l'autre, ailes au-dessus des têtes (fiche §8h) — jamais d'anges adultes, jamais de tables de la Loi visibles. Proxys : la ma'hta posée entre les deux badim, au pied de l'Arche (plan 11, *Yoma* 5:1) ; la silhouette du plan 12 est au seuil de la parokhet intérieure, de dos.
- Menora à **7** branches ; Table au **nord**, Menora au **sud** ; autel d'or au centre, sans feu à Kippour.
- Mizbea'h **blanc** (chaulé) avec **rampe**, jamais d'escalier. Oulam **sans portes**.
- Quatre vêtements de lin blanc à l'intérieur — jamais les huit vêtements d'or.
- Pas de coupole, arc en fer à cheval, minaret, statue, colonne corinthienne intérieure.
- Mouvements de caméra lents uniquement : travelling, grue, pan. Aucun zoom, aucune caméra portée. Mesuré, pas jugé à l'œil : `beit_hamikdash_analyse_plans.py` donne la glisse de l'image en largeurs de cadre par seconde, et refuse au-delà de 0,06.
- Portes de l'Azara **ouvertes**, Nikanor comprise : elles le sont dès l'aube (*Tamid* 3:7 ; *Yoma* 3:1–2). Fermées, elles bouchent l'axe est-ouest, qui est le mouvement du film.
- Personne dans une zone qui lui est fermée (fiche §12) : peuple à l'est de l'Ezrat Israël, Léviim sur le Doukhan, cohanim au-delà, Cohen Gadol seul dans le Kodesh HaKodashim ; Oulam et Heikhal vides à l'heure de l'encens. Contrôlé sur les deux frames avant toute génération vidéo, puis sur le mp4.

## Tranché

- **Portes du Heikhal** : ouvertes pendant l'avoda, battants rabattus dans l'embrasure de 6 amot (`PORTES_HEIKHAL_OUVERTES = True`). Pivoter un battant autour de son centre ne l'ouvre pas — il traverse le mur.
- **Plan 12** : l'espace d'une ama entre les deux parokhot ne peut contenir aucune caméra ; le franchissement se filme depuis le Kodesh HaKodashim, côté nord (agrafe nord, *Yoma* 5:1).
- **Plan 5** : depuis le Doukhan, l'autel masque le taureau (placé entre l'Oulam et l'autel, *Yoma* 3:8) ; la caméra vient du nord, au-dessus des anneaux.
- **Caméra du plan 1 (et du plan 15)** : sur l'axe Heikhal–Nikanor, `y = 0` (avant : 100 amot au sud). À 100 amot au sud, l'autel — 9 amot au sud de l'axe — se reprojetait sur l'ouverture de l'Oulam et la colonne de fumée semblait sortir de la porte. Sur l'axe, qui est la ligne de mire de la para adouma (*Middot* 2:4), elle tombe au ras du montant sud. Départ reculé à 1200 amot de la cible (avant : 1000), sur la même ligne de visée — même angle de plongée, donc les mêmes cours et la même foule par-dessus les murs, façade à 20 % de la largeur du cadre au lieu de 24 %, et une approche de ×1,43 au lieu de ×1,18 sur les 12 s. L'arrivée et le plan 15 ne bougent pas ; **les frames stylisées et le mp4 du plan 1 datent de l'ancien départ**.
- **Colonne de fumée** : proxy géométrique `Colonne_fumee_NN` dans le blockout (quinze volutes chevauchées au-dessus de la ma'arakha, collection `77_Fumee`, ombre portée coupée). Sans volume à cet endroit le styliseur invente la source — il a sorti un petit autel d'or à cornes posé sur le mur est de l'Azara. Depuis le mont des Oliviers l'autel lui-même n'est jamais visible : 10 amot derrière un mur de 25, il faudrait la caméra à 337 amot au-dessus du sol de l'Azara.
- **Position du Mizbea'h** : décalé de **9 amot vers le sud** par rapport à l'axe du Heikhal, bord nord à 60,5 amot du mur nord de l'Azara (*Middot* 5:2 ; Rambam *Beit HaBe'hira* 5:13–15). L'avis de R. Yehouda (*Zeva'him* 58b : autel centré face à l'ouverture) n'est pas retenu. Fiche §5 et script alignés sur cette ligne.

- **Où est l'or, et où il n'est pas.** *Middot* 4:1 : « כָּל הַבַּיִת טוּחַ בְּזָהָב, חוּץ מֵאַחַר הַדְּלָתוֹת » — tout le Bayit plaqué d'or **sauf derrière les battants**, codifié par Rambam *Beit HaBe'hira* 4:7 (« וכל ההיכל היה טפוח זהב חוץ ממקום אחורי הדלתות »). Josèphe le confirme du dehors (*Guerre* V, 5) : la façade « couverte de plaques d'or d'un grand poids » qui « au premier lever du soleil renvoyait un éclat de feu », la porte « toute couverte d'or, ainsi que tout le mur autour d'elle ». En face, *Baba Batra* 4a : Hérode bâtit en marbre blanc et vert, **une assise en débord, une en retrait**, voulut le dorer, et les Sages l'en dissuadèrent — « laisse, c'est plus beau ainsi, cela ressemble aux vagues de la mer ». Les deux tiennent ensemble parce que Josèphe dit lui-même que **seules des parties** l'étaient : « quant à celles qui n'étaient pas dorées, elles étaient extrêmement blanches ».
  → **Or** : intérieur du Heikhal (murs et plafond), Kodesh HaKodashim (« כל הבית » ne s'y arrête pas ; *Melakhim I* 6:20-22 dore le devir au Premier Temple), le mur autour de la porte du Heikhal **des deux côtés**, et la **façade est de l'Oulam**.
  → **Pas d'or** : le corps du bâtiment vu du dehors — murs nord, sud, ouest, et les épaules — en marbre d'Hérode.
  → **Pas d'or derrière les battants**, et c'est structurant : les faces de l'embrasure ne portent aucune plaque, ce qui est précisément la raison pour laquelle les portes intérieures se rabattent vers l'intérieur.
  L'or est modélisé en **plaques rapportées de 0,1 ama** sur la face intérieure, jamais comme matière du mur : une boîte ne porte qu'une matière, et dorer le mur du Heikhal aurait doré son extérieur, ce que *Baba Batra* interdit. Le sol reste en pierre (fiche §8b), non tranché par ces sources.
- **Le marbre d'Hérode est une géométrie, pas une couleur.** « Une assise en débord, une en retrait » (*Baba Batra* 4a) : les assises alternent en relief une sur deux, et la teinte est tirée par assise entre les trois marbres (*shesh*, *marmara*, *kuchla* — blanc, bleu-vert, jaune) à saturation très basse. C'est ce jeu de relief, et non un placage, qui fait « les vagues de la mer » ; et c'est lui qui entre dans la passe Normal.
- **Ordre des sept portes de l'Azara** : la Mishna les compte « סמוכים למערב », en partant de la plus **occidentale** (*Middot* 2:6 = *Shekalim* 6:3, Bartenura *ad loc.*, Tosfot Yom Tov sur *Middot* 5:3). Au sud, d'ouest en est : Delek, Bekhorot, **Mayim** — **Sha'ar HaMayim est la porte la plus orientale**. Au nord, même sens : Nitzotz, Korban, Beit HaMoked. Les portes sont nommées dans le script ; les distances entre elles ne viennent d'aucune source, seul l'ordre est halakhique.
- **Le Beit Avtinas a déménagé** : il était posé sur la porte du **milieu** du mur sud, il est sur **Sha'ar HaMayim**, donc à l'extrémité **est** (x −17..−7) — *Yerushalmi Yoma* 1:5 : « על גבי שער המים היתה וסמוך ללשכתו היתה ». Le Bavli *Yoma* 19a laisse la question ouverte (« ולא ידענא ») ; on suit le Yerushalmi, explicite. La Lishkat Parhedrin l'a suivi (contre le corps de porte, x −38..−23) et le Beit HaMoked est passé à l'extrémité est du mur nord.
- **Le Beit Avtinas flottait, et il n'était pas seul.** « על גבי שער המים » se prend au mot : la chambre est le **haut d'un bâtiment de porte**, qui n'existait pas. Elle pendait à 38,5 amot au-dessus du dallage, collée à la face sud du mur de l'Azara, sans rien dessous — c'est le bloc en l'air du plan 1. Le corps de porte de Sha'ar HaMayim (x −22..−2) est modelé **plein**, comme le Beit HaMoked l'est déjà au-dessus de la porte nord : la baie franchie reste celle du mur de l'Azara. Sa terrasse et son garde-corps portent la chambre.
- **Et l'Azara entière flottait.** L'Azara et l'Ezrat Nashim sont des **terrasses taillées dans le Har HaBayit**, mais rien ne les portait : hors de leurs murs le sol retombe à Z_HAR, et les murs, les chambres d'angle et les quatre lishkot du pourtour partaient de leur propre niveau, 13,5 amot au-dessus du dallage. Deux blocs (`Podium_har` jusqu'à Z_EZN, `Podium_azara` jusqu'à Z_AZ) les asseyent ; les lishkot du pourtour partent désormais de **Z_HAR**, puisqu'elles sont bâties sur le Har HaBayit et bordent une cour qui est 13,5 amot plus haut. Le soreg, qu'elles coupent maintenant au nord comme au sud, se construit **après** elles et s'interrompt contre elles au lieu de les traverser.
- **Une aliyah a un rez-de-chaussée, et il en manquait trois.** *Middot* 1:1 et *Tamid* 1:1 : « בֵּית אַבְטִינָס וּבֵית הַנִּיצוֹץ **הָיוּ עֲלִיּוֹת** » — ce sont des **étages**. *Middot* 1:5 en donne même le type complet, pour Sha'ar HaNitzotz : « וּכְמִין אַכְסַדְרָה הָיָה, **וַעֲלִיָּה בְנוּיָה עַל גַּבָּיו**, שֶׁהַכֹּהֲנִים שׁוֹמְרִים מִלְמַעְלָן וְהַלְוִיִּם מִלְּמַטָּן, **וּפֶתַח הָיָה לוֹ לַחֵיל** ». La scène a donc trois corps de porte de 20 amot de large débordant de 12, posés sur le Har HaBayit : Sha'ar HaMayim (aliyah = Beit Avtinas), **Sha'ar HaNitzotz** (aliyah = Beit HaNitzotz, qui manquait alors que c'est le seul décrit en entier) et le Beit HaMoked.
- **Le Beit HaMoked et la Lishkat HaGazit enjambent la limite du sacré.** *Middot* 1:6 : « שְׁתַּיִם בַּקֹּדֶשׁ וּשְׁתַּיִם בַּחֹל, וְרָאשֵׁי פִסְפָּסִין מַבְדִּילִין בֵּין קֹדֶשׁ לַחֹל » ; *Yoma* 25a sur HaGazit : « חֶצְיָהּ בַּקֹּדֶשׁ וְחֶצְיָהּ בַּחוֹל… שְׁנֵי פְתָחִים הָיוּ לָהּ ». Ils étaient posés **derrière** le mur ; ils sont maintenant centrés dessus, avec deux ouvertures opposées et un **couloir** entre elles — au Beit HaMoked on entre du 'Heil et on ressort dans l'Azara (*Middot* 1:7). Le petit percement du mur nord pour HaGazit n'est pas une huitième porte : *Middot* 1:4 compte sept **שערים**, *Yoma* 25a appelle celles-ci des **פתחים**. Restent écartés : la כִּפָּה du Beit HaMoked (*Middot* 1:8) — la coupole a déjà dû être retirée du plan 1 — et ses quatre chambres d'angle. Largeur (20) et hauteur (30 au-dessus de l'Azara) sont des CHOIX : la hauteur passe le mur de 25 pour que les deux toits ne soient pas coplanaires, la largeur laisse passer la caméra du plan 7a, qui se retrouvait **enfermée dans le bâtiment** à 30 de large.
- **Le 'Heil faisait 5 amot au lieu de 10.** *Middot* 2:3 : « לִפְנִים מִמֶּנּוּ הַחֵיל, **עֶשֶׂר אַמּוֹת** ». Le soreg était à 5 amot du mur, et les 12 marches étaient enfouies dans le podium. Les marches sont ressorties contre la face est du mur (x 145..151) et le soreg est repoussé à 10 amot de la face **bâtie** la plus saillante, corps de porte compris — mesuré depuis le mur, il traversait le Beit Avtinas et le Beit HaMoked. Il est de nouveau **continu** : ses treize פרצות ont été rebouchées (« חָזְרוּ וּגְדָרוּם »), les coupures d'une version précédente n'étaient pas elles.
- **Les deux lishkot de Sha'ar Nikanor manquaient.** « וּשְׁתֵּי לְשָׁכוֹת הָיוּ לוֹ, אַחַת מִימִינוֹ וְאַחַת מִשְּׂמֹאלוֹ, אַחַת לִשְׁכַּת פִּנְחָס הַמַּלְבִּישׁ, וְאַחַת לִשְׁכַּת עוֹשֵׂי חֲבִתִּין » (*Middot* 1:4 ; Rambam *Beit HaBe'hira* 5:17). Ajoutées dans l'Ezrat Israël de part et d'autre de la porte, elles encadrent l'axe que les plans 1, 4 et 6 regardent. CHOIX : Pin'has au nord, la cote et la hauteur, qu'aucune source ne donne.
- **Gazit au nord et Parhedrin au sud, en connaissance de cause.** Le nord de HaGazit suit la girsa de *Yoma* 19a, celle du Rambam (*Beit HaBe'hira* 5:17) et la préférence de Tosfot Yom Tov, contre le texte imprimé de *Middot* 5:4. Mais **le même Rambam identifie Lishkat HaEtz à la Lishkat Parhedrin**, que le Yerushalmi met au sud contre le Beit Avtinas ; or *Middot* 5:4 veut les trois du même côté (« וְגַג שְׁלָשְׁתָּן שָׁוֶה »). La scène tient donc que le Cohen Gadol avait **deux** lishkot — ce que *Yoma* 19a laisse ouvert (« וְלֹא יָדַעְנָא » laquelle est au nord, laquelle au sud) — et non que Parhedrin = HaEtz. C'est un arbitrage, il est écrit dans le script.
- **La façade était plate, et les sources ne la veulent pas plate.** Rambam *Beit HaBe'hira* 4:9 ceinture les murs de l'Oulam de bandeaux en saillie, de bas en haut : « אַמָּה אַחַת חָלָק וְרֹבֶד שָׁלֹשׁ אַמּוֹת… וְרֹבֶד הָעֶלְיוֹן רָחְבּוֹ אַרְבַּע ». Le Kessef Mishneh (*ad loc.*) donne la lecture du Rambam sur *Middot* 3:6 — le rovad sort du nu « כְּגוֹן כְּצוֹצְרָא », comme un balcon — et précise que le corps du Heikhal, lui, n'en porte pas (« וְלֹא שֶׁיְּהֵא מֻקָּף רְבָדִים כְּמוֹ שֶׁל אוּלָם ») : la ceinture s'arrête donc au mur du Heikhal, et ce décrochement est lui-même un repère. Sur 90 amot de mur cela fait **23 bandeaux de 4 amot de pas**, dorés sur la face est, blancs sur les deux retours — « as to those parts of it that were not gilt, they were exceeding white » (Josèphe, *Guerre* V, 5, 6). La saillie n'est chiffrée nulle part : 1 ama, CHOIX. Même direction à l'échelle de l'assise, « אַפֵּיק שָׂפָה וְעַיֵּיל שָׂפָה » (*Baba Batra* 4a ; *Soucca* 51b), déjà porté par `MAT_MARBRE_HERODE` — inutile de la bâtir deux fois.
- **Pas de colonnes, et ce n'est pas un oubli.** *Middot* 3:7-8 et 4:6-7, le Rambam, et Josèphe qui a vu le bâtiment et le décrit pierre à pierre (épaules, porte sans battants, plaques d'or, pierre blanche, pointes du faîte) : aucun ne met un fût devant cette façade. Ya'hin et Boaz (*Melakhim I* 7:21) sont du Premier Temple et *Middot* les ignore. Les seuls fûts de la zone sont les כְּלוֹנָסוֹת de cèdre tendus du mur du Heikhal à celui de l'Oulam (*Middot* 3:8) — dedans, pas devant. **Toute l'articulation que les sources donnent est horizontale**, et c'est ce qui tombe bien : au soleil de 12° presque frontal du plan 1, une verticale ne porte aucune ombre, une horizontale en porte 4,7 amot.
- **Le mur montait à 100, il devait s'arrêter à 96.** *Middot* 4:6 compte אֹטֶם 6 + 40 + 1 + 2 + 1 + 1 + 40 + 1 + 2 + 1 + 1 = 96, puis **מַעֲקֶה 3** et **כָּלֵה עוֹרֵב 1**. Le blockout montait le mur à 100 et posait la crête de bronze **au-dessus**, à 101 : le bâtiment dépassait sa propre mesure et n'avait pas de garde-corps. Le mur s'arrête maintenant à 96, le maake et les pointes tiennent dans les 100, et le pourtour suit le vrai contour du toit — il décroche à l'aplomb du mur du Heikhal, l'Oulam débordant de 15 amot au nord et au sud (*Middot* 4:7). Les pointes sont celles que Josèphe voit d'en bas : « on its top it had spikes with sharp points, to prevent any pollution of it by birds sitting upon it ».
- **Les douze marches avaient le mauvais giron.** *Middot* 3:6 : « רוּם מַעֲלָה חֲצִי אַמָּה **וְשִׁלְחָהּ אַמָּה** ». Elles étaient bâties à 0,5 ama de giron, soit un escalier deux fois trop raide occupant 6 des 22 amot qui séparent l'Oulam du Mizbea'h ; elles en occupent 12, le reste est du plat. C'est là que se tiennent les cohanim pour bénir le peuple (*Tamid* 7:2), et c'est le premier plan du plan 1. Six amot de marches en plus, ce sont six amot de plat en moins : le **Kiyor** (x −65) et les **proxys du plan 5** avaient les pieds enfouis dedans, et sont ressortis sur les 10 amot qui restent. Au passage, *Yoma* 3:8 met le Cohen Gadol **à l'est** du par, face à l'ouest (« וְהַכֹּהֵן עוֹמֵד בַּמִּזְרָח וּפָנָיו לַמַּעֲרָב ») — il était à l'ouest. Vu du nord-est il reste de dos, mais il est passé de l'autre côté de la tête, et la cible du plan 5 a suivi le taureau.
- **Toutes les frames stylisées qui montrent le bâtiment sont périmées** : la façade a changé de relief, la ligne de toit de silhouette, l'escalier de profondeur. Plans 1, 5, 8, 13b et 15 au minimum — à re-styliser depuis les nouveaux rendus.
- **Non modélisées, et c'est su** : les six lishkot de *Middot* 5:3-4 (Melah, Parva, Medi'hin, Gola, Etz). Elles existent, mais aucune source ne donne leur position le long des murs, et posées au jugé elles mangent la cour dont les plans 5, 6 et 14 ont besoin.
- **Ce qui rend une lishka lisible au plan 1.** Le soleil de l'aube y est à 12° au-dessus de l'horizon et à 15° de l'axe de la caméra, donc **dans son dos**, et les faces est que le plan regarde sont éclairées de face : un ressaut vertical n'y projette aucune ombre, un débord horizontal de 1,5 ama en jette 7 sur le mur. D'où l'appareil du helper `lishka` : socle, bandeau, corniche en saillie (trois lignes horizontales), baies de 2 amot de profondeur pour qu'elles restent noires, porte de 8 × 16, et un `maake` au-dessus de la corniche — le garde-corps de *Deut.* 22:8, dû par un toit fait pour l'habitation (Rambam, *Rotzea'h* 11:2 : « גגך » exclut ce qui ne l'est pas), ce que ces deux-là sont : les anciens dorment au Beit HaMoked (*Middot* 1:8), le Cohen Gadol habite sept jours la Lishkat Parhedrin (*Yoma* 1:1), tenue pour cela à la mezouza (*Yoma* 11a). Hauteur minimale 10 tefa'him (*Rotzea'h* 11:3) ; 3 amot est un CHOIX. **La porte des lishkot (8 × 16) est une cote inventée** : *Middot* 2:3 donne 10 × 20 à « tous les pesa'him et tous les shearim », que le Rambam (*Beit HaBe'hira* 5:5) ne rapporte qu'aux **portes de l'Azara**. Des pilastres avaient été essayés d'abord : sous une lumière frontale, un ressaut de 0,4 ama ne se distingue pas du mur, quelle que soit sa largeur.
- **Les chambres d'angle de l'Ezrat Nashim n'avaient pas de porte.** *Middot* 2:5 leur refuse le **toit** (« ולא היו מקורות », rattaché aux « חצרות קטורות » d'*Ezekiel* 46:21-22) et ne décrit **aucune porte** — mais des usages qui la supposent : les nazirs y cuisent leurs shelamim, les metzoraim s'y immergent. Quatre murs aveugles ne sont pas une lishka mais une fosse, et c'est ce que le plan 1 en montrait. Chacune s'ouvre sur la cour par la face tournée vers l'axe — **porte inventée**, 6 × 12, faute de pouvoir loger les 20 amot de *Middot* 2:3 dans un mur de 15 dont la hauteur n'a elle-même pas de source.
- **Plan 3, re-cadré.** Depuis la nouvelle position la fenêtre ne montre plus **que du ciel** et, en bas de l'ouverture, le mur nord et le mur est de l'Azara (sondage par ray-cast sur CAM_03) : le Sanctuaire est 65 amot à l'ouest, soit 38° hors de l'axe, impossible à cadrer par une baie de 3 amot vue de 10 amot en arrière. La fenêtre n'est donc plus une vue mais une **source de lumière**, et le sujet du plan redevient la chambre — les onze épices et l'homme qui les prépare. Focale passée à **20 mm** : la pièce fait 8 × 10 amot, le plus grand recul possible y est de 9,7 amot, et à 28 mm la silhouette occupait les trois quarts de la hauteur du cadre — le « petit dans le cadre » du découpage n'est pas atteignable dans une pièce de cette taille. Le mp4 et les frames stylisées du plan 3 datent de l'**ancienne** position : à refaire.
- **Fenêtre du Beit Avtinas, ce qu'elle ne montre jamais** : la cour. L'appui est à 2 amot du sol d'une chambre posée 26 amot au-dessus de l'Azara, et la caméra n'est que 1,3 ama plus haut que lui : la mire qui rase l'appui franchit le mur de l'Azara à 27 amot et n'atteindrait le sol qu'à 214 amot, bien au-delà du mur nord. Décrire « la cour » dans le prompt revient à la faire inventer.
- **Table des épices (plan 3)** : posée en travers face à la caméra, elle ne laissait qu'un liseré au bas du cadre. Elle court maintenant le long du mur ouest, en fuyante, avec onze coupes et le mortier — les onze épices sont le sujet de la chambre autant que le Cohen Gadol.

- **Quatre plans coupés en deux, sur mesure et non à l'œil.** `beit_hamikdash_analyse_plans.py` tire une grille de rayons à travers chaque frame et reprojette les points touchés dans l'autre caméra, occultation comprise. Deux chiffres : ce que le mouvement chasse hors champ, et — celui qui décide — la part de la frame de fin **déjà visible au début**, car ce qu'elle laisse de côté, le modèle doit l'inventer. Sous 40 %, le plan est coupé. Mesures d'origine : plan 7 **0 %** (la cible traversait l'axe de la caméra, 142° de panoramique), plan 9 **7 %** (56° de relevé pour 46° de champ vertical), plan 13 **17 %** (la caméra traversait le mur est du Heikhal et changeait de pièce), plan 14 **0 %** (grue de 54 amot balayant la cible de 70). Les dix-neuf plans sont aujourd'hui au-dessus du seuil.
- **Un travelling avant n'est pas un panoramique.** La première version de la mesure prenait le plus faible des deux sens et condamnait la Stoa du plan 2 à 0 % : dans un couloir, aucune pierre n'est commune aux deux frames alors que l'image d'arrivée est l'agrandissement du centre de l'image de départ — exactement ce qu'un i2v sait faire. Ce qui compte n'est pas ce qui sort du cadre, c'est ce qui y entre sans avoir été annoncé. Corollaire : l'occultation doit être testée, sinon une grue qui se lève au-dessus d'un mur passe à 100 % de couverture pour un pays qu'elle n'avait jamais vu (mesuré sur le plan 14).
- **Le plan 6 ne montrait pas son sujet.** Posée à 6 amot au-dessus du sol de l'Oulam, la caméra avait le Mizbea'h — 32 × 32 × 10, à 24 amot et à cheval sur l'axe (y −25..7) — exactement en travers : la ligne de visée passait sous son couronnement et toute la cour prosternée était derrière. Il faut **35 amot** de hauteur pour raser l'angle nord-est de l'autel et rattraper le sol à Nikanor ; l'ouverture de l'Oulam en fait 40, la caméra y tient. Et il faut se décaler au bord **nord** de l'ouverture, sinon la colonne de fumée — qui monte de l'autel à y −9 — coupe le cadre en deux. Même correction au départ du plan 14a.
- **La prosternation se comptait en trois colonnes.** 33 silhouettes couchées pour « toute l'Azara » : à 35 amot de haut et 80 de distance, trois traits sur un dallage vide. Le champ couvre maintenant l'emprise exacte de la foule debout — Ezrat Israël *et* Ezrat Cohanim sur toute la largeur, puis l'Ezrat Nashim —, la prosternation concernant les deux cours (*Yoma* 6:2).
- **Les Léviim n'étaient pas où on croyait.** Rangés avec les proxys de sujet, ils disparaissaient du Doukhan chaque fois qu'un plan masquait les sujets d'un autre — le plan 1 se rendait avec un Doukhan vide. Ils sont l'état permanent du jour, pas le sujet d'un plan : ils vivent avec la foule. Et les proxys de sujet ont désormais **une collection par plan**, au lieu d'un fourre-tout qu'il fallait masquer d'un bloc.
- **La colonne de fumée était une tour.** 12 amot de large sur 80 de haut : elle barrait le plan 6 de haut en bas et couvrait la façade au plan 1. Ramenée à 7 amot au sommet sur 45 de haut. Un proxy doit dire « de la fumée, ici », pas devenir le sujet.
- **Puis une colonne de pierre.** Le tronc de cône lisse, même évasé, gardait un bord droit et une section constante — le styliseur y voyait un fût. Quinze sphères chevauchées, de plus en plus larges et écartées de l'axe en montant, dérive au sud en haut : silhouette bosselée, passe Z toujours écrite (`nuee` reste opaque).
- **Israël, Lévi, Cohen ne se distinguaient pas.** Une seule silhouette pour tous, et Léviim comme cohanim en `MAT_LIN` : à vingt amot le styliseur ne lit qu'un corps. Trois tenues (`silhouette(..., tenue=)`) : le peuple en talith rabattu sur la tête (capuche, six sur dix) ou tête nue ; les Léviim en robe de lin **avec leur instrument** — neuf kinorot, deux nevalim, un tziltzal (*Arakhin* 2:5, 2:3 ; *Tamid* 7:3), les ketanim sans (*Arakhin* 2:6) ; les cohanim en lin, coiffe plate et avnet (*Yoma* 7:5), sans couleur (bloc FIGURES).
- **La foule était au garde-à-vous.** Grille à pas de 2 amot et jitter d'un quart de pas : des rangs. `foule()` défait la grille par trois tirages — écart de plus de la moitié du pas, lacet ±20° (les pièces sont bâties à l'origine et posées avec `rotation_euler`), et des vides : une case de 3 × 3 sur trois clairsemée. Léviim en rang, sans lacet : un chœur. Le portique sud passe par le même `figurant()`.
- **Le sol ne se lisait ni en relief ni en dallage.** Joint de 1,2 cm invisible passé vingt amot, et ±5 % de valeur tirés par dalle : des taches. Joint à 0,05 ama, plus creusé dans la passe Normal ; dalles à ±1,5 %.
- **Le kaf était un tambour.** Tronc de cône plus anneau plus galette de ketoret. Bol de révolution à paroi mince — pied, panse, lèvre évasée — et ketoret en dôme ; pas de manche, aucune source n'en donne (*Tamid* 5:4 le compare à un tarkav, *Yoma* 5:1 y fait verser deux poignées).
- **`inspect --foule` comptait les pièces.** Depuis que la silhouette a sept pièces, chaque objet comptait pour une figure et les groupes tombaient sous le seuil de cinq. Les pièces sont regroupées par figure (`figure_de_foule`), boîte enveloppante par figure.
- **Ce qui reste illisible en couleur se stylise avec `--structure`.** La rampe du plan 7b — chaulée, contre un autel chaulé, sur un dallage clair, en lumière ambiante — ne donne aucune arête au rendu couleur, quel que soit le poste de caméra : trois cadrages essayés, aucun ne la détache. C'est le cas de la Stoa du plan 2, et la réponse est la même : joindre la carte de profondeur. Un défaut de matière ne se corrige pas en déplaçant la caméra.
- **Valeur de l'ama : 0,48 m, gelée.** Elle ne change aucun cadrage — toute la géométrie passe par `m()` et la perspective est invariante d'échelle. Elle ne touche que deux choses : `H_HOMME = 3.65`, où l'homme est défini en mètres (1,75 m ÷ 0,48), et les trois lampes ponctuelles en watts (ma'arakha 1500, flammes de la Menora 15, ma'hta 8), dont l'éclairement varie en 1/ama² quand le soleil, en W/m², est invariant. À l'image, la seule différence est la taille d'un homme contre le bâtiment : 3,65 % de la façade de 100 amot ici, 3,04 % à 0,576 — et le plan 6 n'a pas besoin d'une foule 20 % plus petite.
- **Branches de la Menora : droites, en diagonale** (Rambam, Rashi ; `MENORA_DROITE = True`). Le choix ne vit pas dans la géométrie : au plan 9a, sur 920 rayons, seules les deux marches de pierre touchent l'écran — la tige, les branches et les coupes tiennent sous 0,1 % du cadre. C'est le styliseur qui dessine les branches, et sans consigne il peint la courbe de l'Arc de Titus. La forme est donc écrite dans les prompts 9a et 13a et dans le NÉGATIF commun ; sans cela le réglage du script ne décide de rien.
- **Couronne d'Hélène, sortie du mur.** Posée à x −92,5, l'anneau de 2,4 amot s'enfonçait de 1,9 dans le linteau du mur est du Heikhal (x −98..−92) : le plan 8 ne la touchait d'aucun rayon alors que son prompt la décrit. Centre reporté à **x −90,6**, à l'est de la face du mur d'au moins son rayon, sous la vigne (vigne z 29,7..36,3, couronne 27,9..28,1).

## À trancher avant de produire

- **Timecodes** : ceux du shot list sont estimés. Poser les marqueurs sur l'audio réel et remplir la colonne « Vrai timecode » avant tout rendu.

## Diffusion

Le morceau appartient à Ishay Ribo et à son label : toute diffusion publique, événementielle ou commerciale demande une autorisation de synchronisation. Créditer les sources (*Mishna Middot*, *Yoma*, Rambam) et les références visuelles (Machon HaMikdash, Ritmeyer). Faire relire le film par une personne compétente en *Kodashim* avant publication.
