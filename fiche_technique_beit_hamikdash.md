# Fiche technique — Beit HaMikdash (le Temple à venir : plan de la Mishna, mobilier du Tanakh, Arche revenue)

Document de référence pour la modélisation 3D (blockout Blender) et la direction artistique.
Le bâtiment modélisé n'est **ni le Premier ni le Second Temple** : c'est le **troisième**. Le plan et les cotes viennent de *Middot* — c'est la seule description mesurée que le corpus donne d'un bâtiment debout. Ce que le Premier Temple avait et que *Middot* ne répète pas, mais que le Tanakh décrit et que rien n'abroge, revient à sa place : l'Arche sur l'Even HaShetiya (§8h), Ya'hin et Boaz dans l'Oulam (§8a). Quand les deux Temples se contredisent sur une même pièce, *Middot* décide, et l'écart est noté.
Sources principales : Mishna *Middot* (plan et dimensions), *Melakhim I* 6–7 et *Divrei HaYamim II* 3–4 (Premier Temple), *Yoma* (service de Yom Kippour), *Tamid* (service quotidien), *Soucca* 51b (matériaux), *Pesa'him* 13b (les portiques de l'esplanade), Rambam *Hilkhot Beit HaBe'hira* ch. 1–8.
**Flavius Josèphe est écarté du dossier.** Ce qu'il décrit, le corpus le dit ; là où il le contredit, c'est le corpus qui décide. Rien dans cette fiche ne repose sur lui. Le §10 garde des références *visuelles* modernes — ce sont des aides au dessin, pas des sources.
Quand les sources divergent, la ligne retenue est indiquée ; à faire valider par un rav si besoin.

---

## 0. Conventions de modélisation

| Paramètre | Valeur retenue | Remarque |
|---|---|---|
| Unité de base | 1 ama = 6 tefa'him | |
| Conversion | **1 ama = 0,48 m** (Rav 'Haïm Naeh) — **gelée** | Alternatives écartées : 0,525 m (Ritmeyer, archéologie), 0,576 m (Hazon Ish). La valeur ne change aucun cadrage : toute la géométrie passe par `m()` et la perspective est invariante d'échelle. Elle ne touche que deux choses, à re-dériver ensemble si elle bougeait un jour — `H_HOMME = 3.65` (l'homme est défini en mètres, 1,75 m ÷ 0,48) et les trois lampes ponctuelles en watts (ma'arakha 1500, flammes de la Menora 15, ma'hta 8 ; l'éclairement varie en 1/ama², le soleil en W/m² est invariant). À l'image, la seule différence est la taille d'un homme contre le bâtiment : 3,65 % de la façade de 100 amot ici, 3,04 % à 0,576 — et le plan 6 n'a pas besoin d'une foule 20 % plus petite. |
| Orientation | Le Heikhal est à l'**ouest**, l'entrée principale à l'**est**. Le Cohen entre en marchant vers l'ouest. | Axe est-ouest = axe de la caméra pour le parcours du Cohen Gadol. |
| Origine Blender | Coin sud-est du Heikhal (bâtiment) ou centre du Mizbea'h | Le Mizbea'h n'est pas centré sur l'axe du Heikhal : il est décalé de **9 amot vers le sud** (voir §5). Ne pas « corriger » cela. |
| Portes du Heikhal | **Ouvertes**, battants rabattus dans l'embrasure de 6 amot, contre les jambages (`PORTES_HEIKHAL_OUVERTES = True`) | Elles sont ouvertes pendant l'avoda et, fermées, bouchent l'axe est-ouest. Pivoter un battant autour de son centre ne l'ouvre pas : il traverse le mur. `False` pour la version fermée. |
| Collections | `00_HarHabayit`, `10_EzratNashim`, `20_Azara`, `30_Mizbeach`, `40_Ulam`, `50_Heikhal`, `60_KodeshHakodashim`, `65_Aron`, `70_Kelim`, `76_Foule`, `77_Fumee`, `80_Lishkot`, `90_Cameras` | `65_Aron` : l'Arche, permanente comme les kelim, avec le biseau fin des orfèvreries (badim de 0,06 ama de rayon). |

---

## 1. Har HaBayit (Mont du Temple, enceinte sacrée)

- **500 × 500 amot** (*Middot* 2:1) ≈ 240 × 240 m à 0,48 m. (L'esplanade hérodienne réelle est plus grande ; la Mishna décrit l'enceinte sacrée.)
- Le complexe du Temple n'est **pas centré** : le plus grand espace libre est au **sud**, puis à l'**est**, puis au **nord**, le plus petit à l'**ouest** (*Middot* 2:1). Utile pour le plan large d'ouverture.
- **Cinq portes** (*Middot* 1:3) : deux portes de 'Houlda au sud (entrée/sortie principale des fidèles), Kiponos à l'ouest, Tadi au nord (non utilisée par le public), porte de l'Est (Shushan) ornée d'une représentation de Suse.
- Circulation : on entre par la droite et on sort par la gauche, sauf les personnes en deuil ou frappées d'un malheur, qui tournent à gauche (*Middot* 2:2).
- **Le mur est est le seul mur bas** (*Middot* 2:4) : « tous les murs qui étaient là étaient hauts, sauf le mur oriental, car le cohen qui brûle la para se tient au sommet du mont des Oliviers, vise, et voit l'ouverture du Heikhal au moment de l'aspersion du sang. » La ligne de mire mont des Oliviers → porte est → Nikanor → ouverture de l'Oulam → porte du Heikhal est donc **alignée sur l'axe** et doit rester dégagée (ni colonne de portique, ni foule). C'est l'axe du plan 1 et du plan 15.
- Le sol de la montagne est en pierre ; l'esplanade est bordée de **portiques doubles** : « אָמַר רַחֲבָא אָמַר רַבִּי יְהוּדָה: **הַר הַבַּיִת סְטָיו כָּפוּל הָיָה**… רַבִּי יְהוּדָה אוֹמֵר: אִיסְטְווֹנִית הָיְתָה נִקְרֵאת — **סְטָיו לִפְנִים מִסְּטָיו** » (*Pesa'him* 13b). Ils sont **couverts** : la même page parle du « גַּג הָאִיצְטְבָא », le toit de la colonnade, sur lequel on posait les deux hallot. Nombre de rangs, entraxe, profil des colonnes et matière du plafond : **CHOIX**, la guemara ne donne que le principe. À traiter comme décor de fond.

## 2. Soreg et 'Heil

- **Soreg** : clôture en treillis de bois de **10 tefa'him** de haut (≈ 0,8 m), entourant tout le complexe (*Middot* 2:3). Élément visuel discret mais authentique : séparation légère, pas un mur.
- **'Heil** : bande de **10 amot** entre le Soreg et le mur de l'Ezrat Nashim, avec **12 marches** (chaque marche : ½ ama de haut, ½ ama de profondeur) (*Middot* 2:3). Script : les corps de porte débordent des murs de 12 amot, et la Lishkat HaEtz se pose en second rang derrière eux ; les 10 amot se mesurent donc depuis la face bâtie la plus saillante — la sienne —, sinon le Soreg passe au travers. Le tracé reste un rectangle : la dissymétrie nord-sud du bâti se lit dans la largeur du 'Heil, pas dans le Soreg. Les 12 marches sont posées hors du mur est (x 145..151), dans la bande du 'Heil.

## 3. Ezrat Nashim (Cour des Femmes)

- **135 × 135 amot** (≈ 65 × 65 m), à ciel ouvert (*Middot* 2:5).
- **Quatre chambres d'angle de 40 × 40 amot**, sans toit — « וְלֹא הָיוּ מְקוֹרוֹת. **וְכָךְ הֵם עֲתִידִים לִהְיוֹת** » (*Middot* 2:5, sur Ye'hezkel 46:21-22 : « חֲצֵרוֹת קְטֻרוֹת », « וְאֵין קְטֻרוֹת אֶלָּא שֶׁאֵינָן מְקוֹרוֹת »). La michna le dit du Temple **à venir**, qui est celui du film : **jamais de toit ni de couverture sur ces quatre-là**. Ce qu'on peut leur donner est le couronnement de leurs murs, comme en porte tout le reste de l'enceinte. Affectations :
  - SE — Lishkat HaNezirim (les nazirs cuisent leurs offrandes)
  - NE — Lishkat HaEtzim (tri du bois, les Cohanim inaptes au service y travaillent)
  - NO — Lishkat HaMetzoraïm (immersion des metzoraïm)
  - SO — Lishkat Beit Shemanya (huile et vin)
- Une **galerie / balcon** (gezuztra) courait le long des murs, ajoutée pour Sim'hat Beit HaShoeva (*Middot* 2:5, *Soucca* 51b) — au repos elle est vide.
- **Les menorot de Sim'hat Beit HaShoeva** (*Soucca* 5:2 ; 52b) : « וּמְנוֹרוֹת שֶׁל זָהָב הָיוּ שָׁם, וְאַרְבָּעָה סְפָלִים שֶׁל זָהָב בְּרָאשֵׁיהֶן, **וְאַרְבָּעָה סֻלָּמוֹת לְכָל אֶחָד וְאֶחָד** ». Hauteur **50 amot**, de source : « תָּנָא גָּבְהָהּ שֶׁל מְנוֹרָה חֲמִשִּׁים אַמָּה » (*Soucca* 52b). Leur **nombre** n'est pas donné — la Mishna dit « des menorot » : **quatre est un CHOIX**. Les quatre échelles par mât, elles, sont de source, et la guemara y fait monter des enfants des פִּרְחֵי כְהֻנָּה avec trente log d'huile chacun, en opposant l'échelle **raide** au kevesh qui ne l'est pas (« הָתָם בְּכֶבֶשׁ דְּנִיחָא, הָכָא בְּסוּלָּמוֹת », *Soucca* 52b).
  → **Une échelle où l'on ne peut pas monter se lit en échafaudage.** Le barreau était pris toutes les deux amot, presque un mètre : le mât rendait un étai de chantier au milieu d'une cour finie. Il se prend aux trois quarts d'ama (36 cm), ce que la guemara suppose puisqu'on la gravit chargé. Leur matière n'est dite nulle part — cèdre, comme tout le bois du Bayit (*Melakhim I* 6:9), est un CHOIX.
- Portes : on y accède par l'est ; à l'ouest, la **porte de Nikanor** donne sur l'Ezrat Israël.

## 4. Les quinze marches et la porte de Nikanor

- **15 marches semi-circulaires** (« comme la moitié d'une aire ronde ») montent de l'Ezrat Nashim vers l'Ezrat Israël (*Middot* 2:5). Les Léviim y chantent les 15 Shir HaMaalot lors de Sim'hat Beit HaShoeva : lieu idéal pour un plan « musique ».
- **Porte de Nikanor** : la seule des portes de l'Azara restée en **bronze** (les autres furent plaquées d'or), en souvenir du miracle des portes venues d'Alexandrie (*Yoma* 3:10, *Middot* 2:3). Dimensions standard des portes de l'Azara : **20 amot de haut × 10 de large** (*Middot* 2:3). Deux petites portes latérales (pishpeshin).
- **Ouverte pendant le service** : les portes de l'Azara s'ouvrent dès l'aube (*Tamid* 3:7 ; *Yoma* 3:1–2) et le restent pendant l'avoda. Battants rabattus dans l'embrasure, comme ceux du Heikhal. Fermée, Nikanor bouche la ligne de mire de §3 — celle que le mur est bas existe précisément pour dégager — et coupe en deux le mouvement d'est en ouest qui est le film entier.
- Sous les marches : chambres où les Léviim rangeaient les instruments (*Middot* 2:6).

## 5. Azara (la cour intérieure) — plan général

- Dimensions totales : **187 amot (E-O) × 135 amot (N-S)** (*Middot* 5:1) ≈ 90 × 65 m.
- **Découpage est → ouest (187 amot)** (*Middot* 5:1) :
  1. Ezrat Israël : 11 amot
  2. Ezrat Cohanim : 11 amot
  3. Mizbea'h : 32 amot
  4. Entre le Mizbea'h et l'Oulam : 22 amot
  5. Le bâtiment (Oulam + Heikhal + Kodesh HaKodashim + murs) : 100 amot
  6. Derrière le Kodesh HaKodashim (ouest) : 11 amot
- **Découpage nord → sud (135 amot)** — *Middot* 5:2, détaillé par le Rambam (*Beit HaBe'hira* 5:13–15), du mur nord vers le mur sud :

| # | Bande | Amot | Cumul depuis le mur nord | y dans le script (axe du Heikhal = 0) |
|---|---|---|---|---|
| 1 | Mur nord → Beit HaMitba'haïm | 8 | 8 | +67,5 → +59,5 |
| 2 | Beit HaMitba'haïm (les 8 piliers *ninnasin*) | 12,5 | 20,5 | +59,5 → +47 |
| 3 | Place des tables de marbre | 8 | 28,5 | +47 → +39 |
| 4 | Place des 24 anneaux (abattage) | 24 | 52,5 | +39 → +15 |
| 5 | Anneaux → Mizbea'h | 8 | 60,5 | +15 → +7 |
| 6 | **Mizbea'h** | 32 | 92,5 | **+7 → −25** |
| 7 | Kevesh (rampe) | 30 | 122,5 | −25 → −55 |
| 8 | Rampe → mur sud | 12,5 | 135 | −55 → −67,5 |

  La Mishna donne « le kevesh et le Mizbea'h : 62 » puis 8 / 24 / 4 / 4 / 8, et laisse **25 amot de reste** à répartir entre la place des *ninnasin* et l'espace rampe → mur sud ; le Rambam partage ce reste en 12,5 + 12,5 (et fusionne les 4 + 4 de la Mishna en « place des tables : 8 »).

- **Conséquence : le Mizbea'h est décalé de 9 amot vers le sud.** Son bord nord est à **60,5 amot du mur nord** — le Rambam le dit explicitement (*Beit HaBe'hira* 5:15 : « מכותל צפוני של עזרה עד כותל המזבח שהוא רוחב ששים ומחצה ») — donc son centre est à 76,5, contre 67,5 pour l'axe du Heikhal (135 / 2). L'ouverture du Heikhal (10 amot, ±5 autour de l'axe) tombe dans le tiers **nord** de l'autel. La rampe (kevesh) est au sud du Mizbea'h, dans son prolongement.
- **Pourquoi ce décalage** : le rectangle 60,5 (N-S) × 76 (E-O) qui va du mur nord au bord nord de l'autel et du mur de l'Oulam au mur est de l'Azara est le « **nord** » halakhique, lieu d'abattage des *kodshei kodashim* (Rambam 5:15–16). Selon R. Eliézer ben Yaakov (*Zeva'him* 59a), « צפונה — que le nord soit libre de tout, **même de l'autel** » : l'autel doit donc être entièrement hors de cette zone, ce qui le pousse vers le sud.
- **Avis contraire, à ne pas suivre ici** : R. Yehouda (*Zeva'him* 58b) — « מזבח ממוצע ועומד באמצע העזרה », 10 amot face à l'ouverture du Heikhal, 11 de chaque côté, donc autel exactement aligné sur l'axe. C'est cet avis que reproduisent beaucoup d'images IA et de maquettes populaires. La ligne retenue est celle de la Mishna *Middot* / Rambam (décalage sud).
- **Sept portes** (*Middot* 1:4–5) : trois au **sud**, une à l'**est** (Nikanor), trois au **nord**. Certains comptent 13 portes (*Shekalim* 6:3) ; retenir 7 pour la 3D.
  - **Ordre — tranché, et dans ce sens** : la Mishna compte les portes « סְמוּכִים לַמַּעֲרָב », en partant de la **plus occidentale**. *Middot* 2:6 = *Shekalim* 6:3 : « שְׁעָרִים דְּרוֹמִיִּים סְמוּכִין לַמַּעֲרָב, שַׁעַר הָעֶלְיוֹן, שַׁעַר הַדֶּלֶק, שַׁעַר הַבְּכוֹרוֹת, **שַׁעַר הַמָּיִם** ». Bartenura *ad loc.* : « la porte proche de l'ouest est Sha'ar HaElyon, **et après elle** Sha'ar HaDelek ». Tosfot Yom Tov sur *Middot* 5:3 fait de cette formule le marqueur du sens : c'est parce qu'elle **manque** à la liste des lishkot que celles-ci se comptent d'est en ouest. La liste des sept portes (*Middot* 1:4, reprise *Yoma* 19a) donne les trois portes du sud dans le **même ordre** que celle des treize : la conclusion vaut pour les deux listes.
  - **Sud, d'ouest en est** : Sha'ar HaDelek (script x −120) · Sha'ar HaBekhorot (−66) · **Sha'ar HaMayim (−12, la plus orientale)**.
  - **Nord, d'ouest en est** : Sha'ar HaNitzotz (−120) · Sha'ar HaKorban (−66) · Sha'ar Beit HaMoked (−12). Même convention : *Middot* 2:6 dit des portes du nord « וּלְעֻמָּתָן בַּצָּפוֹן סְמוּכִים לַמַּעֲרָב », et *Middot* 1:5 les énumère avec les mêmes « שֵׁנִי לוֹ / שְׁלִישִׁי לוֹ » que la liste du sud.
  - **Ce qui n'est pas dans les sources** : aucune distance entre portes. Les x du script sont une répartition régulière ; seul l'**ordre** est halakhique.
  - **Girsa des noms** : *Yoma* 19a lit au sud « שַׁעַר הַדְלָקָה, שֵׁנִי לוֹ שַׁעַר הַקָּרְבָּן, שְׁלִישִׁי לוֹ שַׁעַר הַמַּיִם » — Sha'ar HaKorban au lieu de HaBekhorot. Le rang de Sha'ar HaMayim ne change pas.
- **Ezrat Israël / Ezrat Cohanim** : séparées par une marche d'une ama (*Middot* 2:6) ; selon d'autres, par des saillies (rashei pispesin). Le **Doukhan** (estrade des Léviim, 3 marches de ½ ama) est à cet endroit.
- **Sol en RANGÉES de dalles, pas en carreaux** : « כָּל שׁוּרָה וְשׁוּרָה שֶׁל אַבְנֵי הָרִצְפָּה קְרוּיָה רֹבֶד » (Bartenura sur *Yoma* 4:3 ; Penei Moshe sur le Yerushalmi *Yoma* 4:3 : « מוֹנֶה הָרְבָדִין וְהֵן הַשּׁוּרוֹת שֶׁל אַבְנֵי הָרִצְפָּה »). On les **compte** en sortant du Heikhal — *Yoma* 4:3 pose le ממרס « עַל הָרֹבֶד הָרְבִיעִי שֶׁבָּעֲזָרָה » —, donc les joints de rangée courent nord-sud, en travers de l'axe du bâtiment. **Largeur d'une rangée : 4 amot**, « וְרֹבֶד אַרְבַּע » (*Middot* 3:6, où Bartenura *ad loc.* glose le rovad en « שׁוּרַת הָרִצְפָּה » ; la michna donne aussi 3, et 5 selon R. Yehouda). La **longueur** des dalles dans la rangée n'est dans aucune source : le blockout leur donne celle des blocs de gazit, 8 ou 10 amot — un CHOIX. Les Cohanim servent pieds nus.

### Chambres (lishkot) autour de l'Azara — les plus utiles pour la mise en scène

| Chambre | Emplacement | Fonction (utile pour Yom Kippour) |
|---|---|---|
| **Lishkat Parhedrin** (ou Palhedrin) | Sud, **collée au Beit Avtinas**, à l'ouest de Sha'ar HaMayim — *Yerushalmi Yoma* 1:5 : la chambre d'Avtinas « וְסָמוּךְ לְלִישְׁכָּתוֹ הָיְתָה », contre sa lishka. Script : x −41..−26, à une ama d'air du socle du corps de porte de Sha'ar HaMayim. **Ouvert** : *Yoma* 19a (« וְלֹא יָדַעְנָא ») ne sait pas laquelle des deux lishkot du Cohen Gadol est au nord et laquelle au sud, et son *mistabra* mettrait Parhedrin au sud, Avtinas au **nord** — raisonnement aussitôt repoussé | Le Cohen Gadol y réside les 7 jours avant Kippour (*Yoma* 1:1). Selon Abba Shaul (*Middot* 5:4) c'est la Lishkat HaEtz |
| **Lishkat Beit Avtinas** | **Au-dessus de Sha'ar HaMayim**, donc à l'**extrémité est** du mur sud (x −17..−7) — *Yerushalmi Yoma* 1:5, halakha : « עַל גַּבֵּי שַׁעַר הַמַּיִם הָיְיתָה וְסָמוּךְ לְלִישְׁכָּתוֹ הָיְתָה » ; la baraïta de *Yoma* 19a situe au même endroit la première tevila, « בַּחוֹל, עַל גַּבֵּי שַׁעַר הַמַּיִם, וּבְצַד לִשְׁכָּתוֹ ». Script : chambre **creuse** posée sur la terrasse du corps de porte de Sha'ar HaMayim (z 25–37) — « עַל גַּבֵּי » se prend au mot, et *Middot* 1:1 / *Tamid* 1:1 en font une **עלייה**, un étage, qui exige donc un rez-de-chaussée, murs d'une ama, **fenêtre 3 × 4 au nord** sur l'Azara — c'est l'intérieur du plan 3 | Préparation de l'encens ; le Cohen Gadol y est conduit la veille de Kippour ; premier bain rituel du jour (*Yoma* 1:5, 3:3) |
| **Lishkat HaGazit** | **Nord** (girsa de *Yoma* 19a / Rambam ; le texte imprimé de *Middot* 5:4 dit sud), à moitié dans le sacré. Script : **à cheval sur le mur nord** (x −158..−138, y 55,5..84,5), deux פתחים opposés et un couloir entre eux — « חֶצְיָהּ בַּקֹּדֶשׁ וְחֶצְיָהּ בַּחוֹל… שְׁנֵי פְתָחִים הָיוּ לָהּ » (*Yoma* 25a ; Rambam *Beit HaBe'hira* 5:17). Celui du sud perce le mur ; ce n'est pas une huitième porte, *Yoma* 25a l'appelle פתח et non שער | Siège du Sanhédrin ; tirage au sort des Cohanim |
| **Beit HaMoked** | Nord, **à l'extrémité est du mur nord** : c'est la troisième porte comptée depuis l'ouest (*Middot* 1:5). Script : **à cheval sur le mur** (x −22..−2, y 55,5..84,5) — « שְׁתַּיִם בַּקֹּדֶשׁ וּשְׁתַּיִם בַּחֹל, וְרָאשֵׁי פִסְפָּסִין מַבְדִּילִין » (*Middot* 1:6) —, deux שערים opposés (*Middot* 1:7) et un couloir entre eux. **Non modélisé** : la כִּפָּה de *Middot* 1:8, écartée exprès (la coupole a déjà dû être retirée du plan 1), et les quatre chambres d'angle |  Feu permanent, Cohanim dorment ; escalier vers le bain rituel (*Middot* 1:6–9, *Tamid* 1:1) |
| **Lishkat HaGola** | **Nord** avec HaEtz et HaGazit : c'est la girsa de *Yoma* 19a, celle du Rambam (*Beit HaBe'hira* 5:17) et celle que préfère Tosfot Yom Tov sur *Middot* 5:3 (« נ"א שבדרום… ונראה בעיני שגירסת הספר נשתבשה »), contre le texte imprimé de la Mishna qui inverse les deux murs. Script : x −182..−162, sur la terrasse du 'Heil (y 72,5..84,5), **un seul** פתח, qui perce le mur et ouvre sur l'Azara — « וּמִשָּׁם מַסְפִּיקִים מַיִם לְכָל הָעֲזָרָה » : une chambre qui alimente la cour s'ouvre dessus. Bâtie dans le 'hol et ouverte au קדש, son intérieur est sanctifié, son toit ne l'est pas (Tosfot Yom Tov *ad loc.*, d'après *Maasser Sheni* 3:8) | Puits et roue pour l'eau (*Middot* 5:4) |
| **Lishkat HaEtz** | Nord, **derrière** HaGola et HaGazit, même toit pour les trois (*Middot* 5:4 : « אֲחוֹרֵי שְׁתֵּיהֶן… וְגַג שְׁלָשְׁתָּן שָׁוֶה »). Script : x −182..−138, y 88,5..100,5, second rang sur la terrasse du 'Heil ; c'est elle qui fixe désormais où se pose le soreg. **Écart assumé** : la Mishna donne les six lishkot « בָּעֲזָרָה », et celle-ci est entière dans le 'hol — dans la cour il ne reste que 17,5 amot entre le mur nord et le socle du Sanctuaire (135 − 100, moitié), pas de quoi loger un corps derrière un autre | Ra'bi Eliézer ben Yaakov : « j'ai oublié à quoi elle servait » ; Abba Shaul : c'est la lishka du Cohen Gadol — identification que le Rambam reprend (Parhedrin = HaEtz) et que la scène ne suit pas |
| **Lishkat HaMelah** | **Sud** (même girsa), et la plus **orientale** des trois : les lishkot se comptent d'est en ouest (Tosfot Yom Tov sur *Middot* 5:3, « מִמִּזְרָח לְמַעֲרָב קָא חָשֵׁיב דֶּרֶךְ כְּנִיסַת הָעֲזָרָה », appuyé sur le schéma du commentaire du Rambam). Script : **dans** l'Azara, contre la face intérieure du mur (x −44..−26, y −67,5..−57,5), séparée des deux autres par Sha'ar HaBekhorot | Le sel des korbanot (*Middot* 5:3) |
| **Lishkat HaParva** | Sud, deuxième. Script : x −92..−74, dans l'Azara. C'est elle qui décide de l'emplacement des trois : son **toit** porte le bain rituel, et « וְכֻלָּן בַּקֹּדֶשׁ עַל בֵּית הַפַּרְוָה » (*Yoma* 3:3), « הֱבִיאוּהוּ לְבֵית הַפַּרְוָה, **וּבַקֹּדֶשׁ הָיְתָה** » (*Yoma* 3:6). Or le toit d'un bâtiment élevé dans le 'hol n'est pas sanctifié, même quand son intérieur l'est : posée dehors comme celles du nord, elle mettrait l'avoda dans le 'hol | Salaison des peaux ; **quatre des cinq immersions** du Cohen Gadol à Kippour, sur son toit, derrière un drap de lin (*Middot* 5:3 ; *Yoma* 3:3, 3:4, 3:6) |
| **Lishkat HaMedi'hin** | Sud, la plus **occidentale**. Script : x −113..−96, accolée au Beit HaParva. La **mesiba** qui monte au toit de la Parva est la tour ronde engagée entre les deux corps (x −94) : Tosfot Yom Tov *ad loc.* la veut du côté de la Parva, « שֶׁלֹּא יִתָּכֵן… שֶׁהַכֹּהֵן גָּדוֹל יַעֲלֶה לְבֵית טְבִילָתוֹ דֶּרֶךְ מָקוֹם שֶׁמְּדִיחִין בּוֹ ». **Non modélisée** : sa seconde ouverture sur l'Azara, que Tosfot Yom Tov lui donne | Rinçage des entrailles ; la montée au bain du Cohen Gadol (*Middot* 5:3) |

## 6. Le Mizbea'h HaNe'hoshet (autel extérieur)

Référence : *Middot* 3:1–4 ; Rambam *Beit HaBe'hira* 2.

- **Yessod (base)** : 32 × 32 amot, 1 ama de haut. Le yessod ne fait le tour complet que sur les côtés **nord et ouest** ; à l'est et au sud il n'y a qu'une ama à chaque angle (*Middot* 3:1).
- Retrait de 1 ama → **30 × 30**, jusqu'au **Sovev** (pourtour praticable) à **6 amot** de hauteur (1 yessod + 5).
- Retrait de 1 ama → **28 × 28** jusqu'à la surface (**Ma'arakha**).
- **Keranot** (cornes) : quatre blocs de 1 × 1 × 1 ama aux angles ; à l'intérieur, une ama de passage (makom hilukh haregel), puis la zone du feu 24 × 24.
- Hauteur totale : **10 amot** (≈ 4,8 m), 9 amot à la surface + 1 ama de corne (avis majoritaire).
- **Kevesh (rampe)** : au **sud**, **32 amot de long × 16 de large**, part du sol et atteint la surface ; deux petites rampes latérales (vers le yessod et le sovev). Pas d'escalier (*Shemot* 20:23).
- Deux trous (**shitin**) à l'angle **sud-ouest** de la base recueillent le sang et le vin. Une ligne rouge (**'hout hasikra**) fait le tour au milieu de la hauteur pour distinguer sangs « hauts » et « bas ».
- **Matière** : pierres **non taillées par le fer**, jointes au plâtre, **blanchies à la chaux** deux fois l'an (*Middot* 3:4). Rendu : masse blanche, presque monolithique, noircie au sommet par le feu.
- Trois feux sur la ma'arakha (quatre à Kippour selon un avis, *Yoma* 4:6). Toujours de la fumée qui monte droit.

## 7. Autour de l'autel

- **Kiyor (bassin)** : entre l'Oulam et le Mizbea'h, **décalé vers le sud** (*Middot* 3:6). Bronze, sur pied. Douze robinets (perfectionnement de Ben Katin, *Yoma* 3:10) et système (mukhani) pour le plonger dans le puits la nuit.
- **Beit HaMitba'haïm (aire d'abattage)** : **nord** du Mizbea'h, en trois bandes successives (voir le tableau du §5) : les 8 piliers bas (*ninnasin*) en pierre surmontés de blocs de cèdre à trois rangées de crochets de fer, puis les 8 tables de **marbre**, puis les **24 anneaux** fixés au sol — « six rangées de quatre, et certains disent quatre rangées de six » (*Middot* 3:5 ; bandes de *Middot* 5:2). Pour Kippour : le taureau et le bouc sont abattus là (au nord de l'autel).
- Une cuvette (**amma**) traverse l'Azara pour évacuer l'eau et le sang vers le Kidron.

## 8. Le Bâtiment (Beit) — Oulam, Heikhal, Kodesh HaKodashim

Référence : *Middot* 4:1–7 ; Rambam *Beit HaBe'hira* 4.

- Vu de face (est) : un bloc de **100 amot de large × 100 de haut** (≈ 48 × 48 m). Le corps derrière l'Oulam n'a que **70 amot** de large : « étroit derrière et large devant, comme un lion » (*Middot* 4:7). L'Oulam déborde donc de 15 amot de chaque côté (les « épaules »).
- **Les 100 amot de haut ne sont pas 100 amot de mur** (*Middot* 4:6) : אֹטֶם 6, גֹּבַהּ 40, כִּיּוּר 1, בֵּית דִּלְפָה 2, תִּקְרָה 1, מַעֲזִיבָה 1, עֲלִיָּה 40, puis 1 + 2 + 1 + 1 — le mur s'arrête à **96**, et les 4 dernières amot sont le **מַעֲקֶה** (3) et le **כָּלֵה עוֹרֵב** (1). Le Rambam décrit ce dernier sur place (commentaire sur *Middot* 4:6) : « שֶׁהָיָה מַקִּיף הַהֵיכָל לְמַעְלָה מִן הַמַּעֲקֶה מֵאַרְבַּע רוּחוֹתָיו **בְּחֶשֶׁק שֶׁל בַּרְזֶל** גֹּבַהּ אַמָּה **חַד כְּמוֹ הַסַּיִף**, כְּדֵי שֶׁלֹּא יֵשֵׁב עָלָיו שׁוּם עוֹף עַל הַהֵיכָל, מִפְּנֵי שֶׁנֶּחְתָּכִים רַגְלָיו בְּאוֹתוֹ הַסַּיִף » — un **cerclage de fer continu** d'une ama, affilé comme une épée, et non une rangée de pointes. R. Yehouda (*Middot* 4:6) ne compte pas le kaleh orev et donne 4 amot au maake ; le film suit le tana kama. Le pourtour du toit n'est pas un rectangle : il décroche à l'aplomb du mur du Heikhal, l'Oulam débordant de 15 amot de chaque côté.
- Longueur totale E-O : 100 amot (murs compris) : mur de l'Oulam 5, Oulam 11, mur du Heikhal 6, Heikhal 40, Amah Traksin 1, Kodesh HaKodashim 20, mur 6, cellule 6, mur 5.
- **Élévation (Middot 4:6)** : אֹטֶם 6, hauteur intérieure 40, puis **1 כִּיּוּר + 2 בֵּית דִּלְפָה + 1 תִּקְרָה + 1 מַעֲזִיבָה** = 5 de plancher, **עֲלִיָּה 40**, les mêmes 5 au-dessus, **מַעֲקֶה 3**, dispositif anti-corbeaux (**kaleh orev**, cerclage de fer continu affilé, Rambam sur *Middot* 4:6) 1 — total 100. Les cotes en Z dans le blockout : sol du bâtiment 6, plafond du rez 46, **sol de l'étage 51, haut de ses murs 91**, fin de la maçonnerie 96, faîte 100 (§8b-bis).
- **Matériaux (*Soucca* 51b ; *Baba Batra* 4a)** : « בְּאַבְנֵי כּוּחְלָא, שִׁישָׁא וּמַרְמְרָא » — Hérode le construisit en trois marbres, disposés en assises alternées ; il voulut le plaquer d'or, on lui conseilla de laisser la pierre visible car « cela ressemble aux vagues de la mer ». **Les trois sont FROIDS** : Rashi les nomme *ad loc.* — « שישא — שיש ירוק » (**vert**), « מרמרא — שיש לבן » (**blanc**), « כוחלא — שיש צבוע כעין כחול » (**bleu**). Aucune source ne met de jaune sur ce bâtiment ; le troisième marbre en portait un jusqu'ici, et c'est lui qui faisait lire la façade en assises de brique.
- **Appareil (Melakhim I 7:9-12)** : le Temple est bâti d'**אַבְנֵי גָזִית**, et le Tanakh les mesure — « וּמְיֻסָּד אֲבָנִים יְקָרוֹת אֲבָנִים גְּדֹלוֹת **אַבְנֵי עֶשֶׂר אַמּוֹת וְאַבְנֵי שְׁמֹנֶה אַמּוֹת** » (7:10). Deux longueurs, pas une ; le verset les nomme toutes deux. Elles valent pour le bâtiment comme pour l'enceinte : « וְלַחֲצַר בֵּית ה' הַפְּנִימִית וּלְאֻלָם הַבָּיִת » (7:12). Les faces sont **sciées lisses** : « אֲבָנִים יְקָרֹת כְּמִדּוֹת גָּזִית **מְגֹרָרוֹת בַּמְּגֵרָה מִבַּיִת וּמִחוּץ** » (7:9) — donc pas de bossage rustique ; le relief tient au joint et au liseré ciselé qui le borde.
  → La **hauteur** d'assise n'est dans aucune source : **4 amot**, un CHOIX, et le même pour l'enceinte et le bâtiment. Une assise vaut alors le pas d'un rovad de l'Oulam (§8a), et le haut de chaque bandeau tombe sur un lit. Le blockout est passé par un module d'une ama, qui se lisait en brique, puis par 2,5 / 2 — encore cinquante lits sur les 100 amot de la façade.
  → **La façade n'est pas plaquée d'or.** Ce qui fait l'extérieur est l'assise elle-même — shesh, marmara et kuchla en assises alternées, une en débord une en retrait (« אַפֵּיק שָׂפָה וְעַיֵּיל שָׂפָה », *Baba Batra* 4a), et les rovadim de l'Oulam sont de la même pierre. L'or reste où les sources le mettent : à l'intérieur du Bayit (« שֶׁכָּל הַבַּיִת טוּחַ בְּזָהָב, חוּץ מֵאַחַר הַדְּלָתוֹת », *Middot* 4:1), sur les portes du Heikhal, sur le mur du fond de l'Oulam autour de leur entrée, sur la vigne et sur la couronne d'Hélène.
  → **Palette 3D** : calcaire de Jérusalem très clair, assises légèrement contrastées, bronze pour Nikanor et les ustensiles, **fer** pour le kaleh orev, cèdre pour les plafonds, or **dedans seulement**.
  → **L'échelle des blancs, et son ordre** : chaux du Mizbea'h (0,95 — blanchie deux fois l'an, *Middot* 3:4) > les trois marbres du bâtiment (0,94 / 0,81 / 0,82) > le calcaire du pourtour (0,75, ses blocs de 0,65 à 0,83) > le dallage des cours (0,64). Quatre rangs, et aucun ne double son voisin : le pourtour est passé par 0,81, où ses blocs les plus clairs brillaient autant que le Bayit. La ville (0,64 chaud) et le pays restent seuls dans l'ocre — c'est d'eux que le Temple doit se détacher.
  → **Le pourtour n'est PAS ocre.** Le doré des assises d'Hérode est une patine de vingt siècles, l'état d'une ruine ; un meleke scié de frais est crème presque neutre (`CALCAIRE` dans le blockout). C'est aussi ce qui rend l'or aux six portes de l'Azara (*Middot* 2:3) : sur un mur beige, il n'était plus de l'or.
  → **Le dallage est sous les murs en valeur, mais dans LEUR pierre.** Aucune source ne donne au rovad une autre roche que le mur ; ce qui l'en sépare est l'usure et le lavage, pas la carrière. Le sortir de la teinte des murs a été une erreur, et elle se mesure : à 0,57 neutre il rendait 62 % de la clarté du parement avec le quart de son chroma et du côté FROID du gris — la moitié basse de chaque cadre passait en dalle de béton sous des murs finis, et c'est de là que venait le « chantier non terminé ». À 0,64 chaud son rang tient toujours : à plat sous un soleil de 20°, une dalle ne prend qu'un tiers de ce que reçoit un parement, et cette assiette-là suffit à lui faire céder la clarté du lin des Cohanim (0,88) et de la chaux du Mizbea'h.
  → **Le dallage est LUSTRÉ, pas mat.** Il était à 0,85 de rugosité, c'est-à-dire une terrasse de grès ; une cour lavée et foulée pieds nus rend son soleil, et une seule usure de vingt amot la donne — là où la cour est passée, la dalle est plus sombre ET plus lisse (0,60 à 0,42 de rugosité, moyenne 0,51 emportée dans le .glb). Ce lustre sépare une cour d'une esplanade mieux qu'aucune teinte.
  → **Ce que la pluie laisse dépend de qui lave.** Le Temple est en service : sa coulure est de moitié (`COULURE_ENTRETENUE`), une enceinte entièrement coulée se lit en ruine. La muraille des 500 amot et son soubassement (`MAT_MURAILLE`, `Pierre_muraille`) et la ville gardent la pleine coulure — personne ne les lave. Même pierre, deux états de surface.
  → **Le rebond du ciel suit le dallage.** La moitié basse du ciel ÉCLAIRANT (`ECLAIRANT.sol` dans `visite/ciel.js`) n'est rien d'autre que le sol qui renvoie le soleil : elle a porté 0xc9b795 tant que la cour était ocre, puis 0xc4bcae le temps qu'elle soit grise — et ce gris-là éteignait tout ce que le soleil ne touche pas de face. Le rovad revenu dans le meleke des murs, son rebond avec (0xcdc0a8).
  → **Le débord d'assise porte la vague, pas la teinte.** « אַפֵּיק שָׂפָה וְעַיֵּיל שָׂפָה » est la moitié de la sougia, et c'est la moitié qui fait le moiré : trois teintes tranchées sur des assises plates rendent des rayures, un relief franc sur trois teintes voisines rend une mer. Le débord n'est chiffré nulle part — CHOIX —, et il est plus fort sur le bâtiment que sur l'enceinte parce que c'est de sa façade que parle la guemara (`DEBORD_ASSISE` / `DEBORD_BATIMENT` dans le blockout, `DEBORD` / `DEBORD_BATIMENT` dans `visite/matieres.js`). Les deux encodages diffèrent — bump sur la parité de l'assise côté Blender, lit dissymétrique côté visite, faute de dérivée d'écran — et seul leur rapport est commun.
  → **Le kaleh orev est du fer AFFÛTÉ, donc poli** : « חַד כְּמוֹ הַסַּיִף » (Rambam sur *Middot* 4:6), « חַד כְּמִין סַיִף » (Bartenura *ad loc.*), et c'est l'emploi du fer voué au Temple — « בַּרְזֶל… לֹא יִפְחוֹת מֵאַמָּה עַל אַמָּה. לְמַאי חַזְיָא? … לְכָלְיָה עוֹרֵב » (*Mena'hot* 107a). Au fer forgé des crochets, l'ama du faîte se lisait en barre noire sur les cent amot de la façade ; polie, elle prend le ciel et se lit en arête. `MAT_FER_LAME`, distinct de `MAT_FER` — la matière ne change pas, son état de surface oui. **Aucune source ne met d'or au sommet** : la couronne d'or de l'Oulam est la vigne, les עֲטָרוֹת et la נִבְרֶשֶׁת, toutes dans l'ouverture (§8a).
  → **Le calcaire n'est pas d'une couleur mais d'une bande** : le meleke va du gris de cendre à l'ivoire — jamais à l'ocre —, chaque banc restant plus chaud que froid (rouge ≥ bleu ; parti plus bleu que rouge, le plus clair rendait du béton à l'ombre). Ce qui change d'un bloc au suivant, c'est de combien il est chaud, et c'est le BLOC qui tire son banc, pas l'assise — dans un mur de gazit deux pierres voisines diffèrent plus que deux assises. Un mur dont les blocs ne diffèrent qu'en clarté rend un aplat sali (`BANCS_CALCAIRE` dans le blockout, `banc()` dans `visite/matieres.js` — mêmes valeurs des deux côtés).
  → **La lumière fait autant que la matière.** Le soleil du matin est chaud, son ombre est froide, et c'est cet écart qui fait lire une pierre. Un ciel d'ambiance blanc et fort l'annule : il éclaire chaque face d'autant que le soleil, sans direction et sans couleur, et le calcaire y devient gris quelle que soit sa teinte. Dans la visite, `scene.environment` est cuit depuis le dôme de ciel et non depuis un studio neutre : c'est lui qui tient les faces à l'ombre du côté chaud, faute de rebond calculé.
  → **Le rapport se mesure à l'ombre portée, pas au niveau des lampes.** Une dalle au soleil ne doit être qu'en partie éclairée par le ciel : réglée à quatre cinquièmes, elle ne rendait que 1,13 fois l'ombre voisine, et une cour dont on ne voit pas l'ombre est une scène sans heure ni relief — le « très terne » du chantier. Le levier est `ambiance` dans `visite/ciel.js`, qui pèse sur le dégradé du dôme éclairant SANS toucher son disque solaire (lequel est ce qui fait lire l'or comme un métal). À 0,45, avec `HemisphereLight` 0,16, soleil 4,9 et exposition 0,68, la dalle au soleil rend 2,1 fois son ombre et le parement 4,3 fois la sienne.
  → **Les deux éclairages ne sont PAS les mêmes, et c'est voulu jusqu'ici.** Blender rend une **aube** — soleil à 12° (`Soleil_AUBE_est`, énergie 3,2), ciel à 0,30 dont la rampe est bleue jusqu'au zénith (0,26 / 0,40 / 0,66) ; la visite rend un **matin** à 20°. Conséquence non arbitrée : la correction ci-dessus n'a été portée que côté visite, et le rendu Blender garde le zénith bleu sur les faces horizontales — CAM_02 y mesure 7,3 de chroma moyen, contre 16,4 pour le même sujet dans la visite. Les MATIÈRES, elles, restent communes aux deux (`MAT_SOL`, `CALCAIRE`, `BANCS_CALCAIRE`).
  → **Le haut du ciel ÉCLAIRANT n'est pas le bleu du ciel VU.** Sous un soleil de 20°, c'est le zénith qui décide de la couleur d'un sol. Bleu (0x8fa5bd), il en faisait du béton — 1/255 de chroma mesuré, du côté froid. Neutre, il l'y laissait presque : une dalle à l'ombre, dans une cour dont les murs sont au soleil, reçoit d'eux un rebond chaud que la visite ne calcule pas. `ECLAIRANT.haut` est donc un gris CHAUD (0xb2aa9c) ; le bleu reste au dôme qu'on regarde.
  → **Le relief du joint se dérive, il ne s'échantillonne pas.** La hauteur est une fonction écrite de la position dans le monde — profil linéaire par morceaux pour le bloc, produit de `smoothstep` pour le dallage : sa pente s'obtient à la main, et la normale est perturbée sans jamais lire le pixel voisin. C'est la seule façon d'avoir du relief sans UV et sans dérivée d'écran, laquelle explose aux angles rasants.
  → **L'occlusion ambiante n'est pas un supplément.** Le rendu Blender l'a par le lancer de rayons d'EEVEE ; la visite ne l'avait pas, et une colonne y semblait collée sur son dallage. `visite/chaine.js` la rend depuis une passe de géométrie qui écrit normale et distance EN MÈTRES : le tampon de profondeur de la visite est logarithmique et ne se relit pas. Elle a DEUX rayons : 1,8 m pour l'angle rentrant, 8 cm pour le trait de contact — c'est le second que l'œil lit comme « photographié ».
  → **Un bloc scié porte la scie.** « מְגֹרָרוֹת בַּמְּגֵרָה מִבַּיִת וּמִחוּץ » (*Melakhim I* 7:9) : des stries parallèles de quatre centimètres de pas sur le champ, en LUSTRE seulement — un parement scié est plat, et rien n'y creuse. C'est au soleil rasant qu'elles séparent un parement travaillé d'un aplat bruité, là où la teinte ne peut rien.
  → **Un mur d'enceinte n'a ni pied ni sommet tant qu'on ne lui en donne pas.** Le blockout le disait déjà des lishkot de l'Azara — « posée en boîte nue, une lishka ne se lit pas : à 750 amot elle n'a ni pied, ni sommet, ni ombre sur elle-même, et le styliseur en fait un rocher » — et leur donnait socle, bandeau et corniche. L'enceinte et les cours n'en avaient jamais eu : leurs murs sortaient du dallage sans pied et s'arrêtaient sur une arête vive, ce qui les faisait lire en gros œuvre non fini. Ils portent maintenant les trois mêmes lignes (`SOCLE`, `BANDEAU`, `CORNICHE` dans le blockout).
  → **Une moulure se lit à ses ombres, donc il en faut au moins deux assises.** Une seule assise en débord n'élargit que la boîte : ce qui fait une corniche, c'est le larmier qui déborde le plus PUIS la couvertine qui se retire — deux lignes d'ombre. Et la saillie est calée sur celle des lishkot (1,4 ama contre `LISHKA_DEBORD` 1,5), pour la même raison chiffrée là-bas : au-dessous, sous un soleil rasant, une moulure ne jette plus d'ombre et redevient un filet sale au sommet du mur.
  → **Le bandeau n'est pas un ornement à mi-hauteur : c'est un niveau.** Dans l'Ezrat Nashim il tombe sur le plancher de la gezuztra (*Middot* 2:5), qui est de plain-pied avec le dallage de l'Azara ; sur la face est du mur de l'Azara, il porte ce même dallage, lu du dehors. Les trois moulures y tombent donc tous les dix amot. **Aucune source ne moulure l'enceinte** — CHOIX, mais dans la langue que les sources donnent au Temple : le כַּרְכֹּב du Mizbea'h (*Middot* 3:1), les rovadim de l'Oulam (Rambam *Beit HaBe'hira* 4:9), l'assise en débord du Bayit (« אַפֵּיק שָׂפָה וְעַיֵּיל שָׂפָה », *Baba Batra* 4a).
  → **Un socle se pose sur le sol qu'il touche, et pas sur une cote.** Les murs de l'Azara soutiennent dix amot de remblai : leur pied est sur le dallage à l'intérieur et sur la terrasse du 'Heil à l'extérieur. Le socle y sort donc d'une seule face à la fois (`cotes` dans `moulure`), et il saute les baies — une porte n'a pas de pied de mur en travers.
  → **Le joint est une ombre chaude et étroite.** Elle s'arrête au fond de la rainure : étalée sur le liseré, elle cerne chaque bloc d'un cadre grisâtre que ne montre aucun mur de pierre. Et le bloc scié n'est proéminent que d'un centimètre et demi — plus haut, le relief dessine un jonc clair autour de chaque pierre et le mur rend un carrelage.

### 8a. Oulam (vestibule)

- Ouverture : **40 amot de haut × 20 de large**, **sans portes** (*Middot* 3:7) — l'intérieur reste visible de la cour.
- Au-dessus de l'ouverture : **cinq poutres de chêne** (maltera'ot) de longueur croissante, séparées par des assises de pierre (*Middot* 3:7). Bartenura les dit « קוֹרוֹת מְצֻיָּרוֹת וּמְכֻיָּרוֹת » — sculptées, pas nues.
- **La façade est bandée, pas plate, et sans une seule colonne.** Rambam *Beit HaBe'hira* 4:9 : « וְכֵן סָבִיב לְכָתְלֵי הָאוּלָם מִלְּמַטָּה עַד לְמַעְלָה… אַמָּה אַחַת חָלָק וְרֹבֶד שָׁלֹשׁ אַמּוֹת… וְרֹבֶד הָעֶלְיוֹן רָחְבּוֹ אַרְבַּע » — 1 ama de nu, 3 de saillie, jusqu'en haut, le dernier de 4. Le Kessef Mishneh (*ad loc.*) rapporte que le Rambam lit ainsi *Middot* 3:6 et que le rovad sort du mur « כְּגוֹן כְּצוֹצְרָא », comme un balcon ; il ajoute que le corps du Heikhal, lui, **n'est pas** ceinturé de la sorte (« וְלֹא שֶׁיְּהֵא מֻקָּף רְבָדִים כְּמוֹ שֶׁל אוּלָם »). Même direction à l'échelle de l'assise : « אַפֵּיק שָׂפָה וְעַיֵּיל שָׂפָה » (*Baba Batra* 4a ; *Soucca* 51b). **Toute l'articulation donnée par les sources est horizontale.** Aucune source ne met de colonne **devant** ce bâtiment : ni *Middot* 3:7-8 et 4:6-7, ni le Rambam. Ya'hin et Boaz sont **dedans** (§8a-bis). La saillie du rovad n'est chiffrée nulle part : **1 ama est un CHOIX**, calé sur le pas des maltera'ot.
- **Vigne d'or** suspendue sur des poteaux au-dessus de l'entrée du Heikhal, à laquelle on ajoutait des feuilles et grappes offertes (*Middot* 3:8) — motif visuel fort et authentique.
- Intérieur : **11 amot** de profondeur (E-O) × 100 de large. Deux **tables** près de l'entrée du Heikhal : une de marbre (pour poser les pains frais), une d'or (pour les pains sortants) (*Middot* 3:8 ; *Shekalim* 6:4).
- Une couronne d'or (**nivreshet**) offerte par la reine Hélène au-dessus de l'entrée du Heikhal, reflétant le soleil levant (*Yoma* 3:10).

### 8a-bis. Ya'hin et Boaz (Premier Temple, restituées)

*Middot* ne les mentionne pas ; le Tanakh les décrit trois fois et rien ne les abroge. Le troisième Temple les remet en place. Toutes les cotes ci-dessous sont **de source**, aucune n'est un CHOIX.

- **Fût : 18 amot.** Donné trois fois sans divergence — *Melakhim I* 7:15, *Yirmiyahou* 52:21, *Melakhim II* 25:17.
- **Les 35 amot de *Divrei HaYamim II* 3:15 ne sont pas la hauteur d'une colonne.** C'est la mesure des deux couchées au moment de la coulée, d'où « אֹרֶךְ » et non « קוֹמָה » : 18 + 18 = 36, moins l'ama que les deux demi-fûts perdent dans les kotarot. Radak *ad loc.* (« על מדת שני העמודים הוא אומר… שהיה חצי אמה מכל אחת נכנסת בתוך הכותרות »), Rashi *ad loc.*, Metsoudat David (« של שניהם יחד »). **Ne pas relire ces 35 amot comme une élévation** — c'est l'erreur qui donnait des colonnes de 70 amot.
- **Kotéret : 5 amot** (*Melakhim I* 7:16 ; *DH II* 3:15). Les 3 amot de *Melakhim II* 25:17 sont les seules décorées : « שְׁתֵּי אַמּוֹת הַתַּחְתּוֹנוֹת… הָיוּ שָׁווֹת לָעַמּוּד שֶׁלֹּא הָיָה בָּהֶם צוּרָה, וְשָׁלֹשׁ עֶלְיוֹנוֹת הֵן נִפְרָדוֹת לַחוּץ מֻקָּפוֹת שְׂבָכִים » (Baraïta des 49 Middot, citée par Radak sur 7:16). Profil : **2 amot au nu du fût, 3 en saillie**, puis la calotte de « מַעֲשֵׂה שׁוּשַׁן » qui coiffe le creux du fût sur une surface de 4 amot (*Melakhim I* 7:19-20 ; Metsoudat David *ad loc.*).
- **Hauteur totale : 23 amot** (11,04 m à 0,48).
- **Diamètre : 4 amot.** « כִּי הָעַמּוּדִים הָיוּ בְּרֹחַב אַרְבַּע אַמּוֹת » (Metsoudat David sur 7:19), confirmé par le tour de 12 amot (*Melakhim I* 7:15 ; *Yirmiyahou* 52:21) au π de trois d'*Erouvin* 76a. **Élancement 4,5:1** — du bronze coulé massif, pas une tige. Creuses, paroi de 4 doigts = 1 téfa'h (*Yirmiyahou* 52:21, « וְעׇבְיוֹ אַרְבַּע אֶצְבָּעוֹת נָבוּב ») : invisible sous la kotéret, non modélisé.
- **Décor** : sevakha en réseau et **sept chaînettes** par kotéret (*Melakhim I* 7:17) ; **200 grenades, cent par rang sur deux rangs**, enfilées sur les chaînettes comme des perles (*Melakhim I* 7:20 ; Metsoudat David *ad loc.*, « חרוזים בשני טורים »). *Yirmiyahou* 52:23 en compte 96 tournées vers le dehors sur les 100 d'un rang.
- **Place : dans l'Oulam, pas devant.** « וַיָּקֶם אֶת הָעַמֻּדִים לְאֻלָם הַהֵיכָל » (*Melakhim I* 7:21), lu **בְּאוּלָם** par Radak *ad loc.*, Ralbag (« שהקימם בו ») et Metsoudat David (« באולם שלפני ההיכל » ; sur *DH II* 3:15, « בחלל האולם »). « מַעֲשֵׂה שׁוּשַׁן **בָּאוּלָם** » (7:19) dit la même chose. Le « עַל פְּנֵי הַהֵיכָל » de *DH II* 3:17 ne contredit pas : l'Oulam est lui-même devant le Heikhal.
- **Transposition dans le plan de *Middot*** : l'Oulam de Shlomo faisait 20 de large (*Melakhim I* 6:3), exactement la largeur de l'ouverture de *Middot* 3:7. Les colonnes tiennent donc cette ouverture **par l'intérieur**, face externe au nu du jambage (axes à ±8 de l'axe est-ouest), **12 amot de passage** au milieu — la ligne de mire mont des Oliviers → Nikanor → porte du Heikhal, large de 10, reste dégagée (*Middot* 2:4, §2). Elles montent à 23 sur une ouverture de 40 : vues de la cour, elles occupent le bas du cadre et laissent voir la vigne et la couronne au-dessus.
- **Ya'hin à droite = sud, Boaz à gauche = nord** (Metsoudat David sur 7:21 : « הימני — אשר בפאת הדרומי »).

### 8b. Heikhal (le Saint)

- Intérieur : **40 amot (E-O) × 20 (N-S) × 40 de haut** (≈ 19 × 9,6 × 19 m). Proportion à respecter : c'est **haut et étroit**, presque une nef.
- Entrée : **20 amot de haut × 10 de large**, avec **quatre portes** (deux extérieures, deux intérieures, *Middot* 4:1), plaquées d'or. Devant l'entrée, un rideau (**parokhet** extérieure) selon plusieurs sources. Dans le film elles sont **ouvertes** : battants rabattus dans l'embrasure de 6 amot, contre les jambages (§0).
- Murs et plafond **plaqués d'or** (tradition rabbinique pour le Premier Temple, *Melakhim I* 6 ; pour le Second, le Heikhal était également orné d'or — *Middot* 4:1 mentionne que tout était plaqué d'or sauf l'arrière des portes). Plafond en cèdre à caissons.
- **Fenêtres** hautes, étroites à l'intérieur, larges à l'extérieur (« émettant la lumière plutôt que la recevant », *Mena'hot* 86b) — justification d'une lumière dorée diffuse plutôt que directe.
- Sol de pierre ; le Cohen Gadol marche vers l'ouest, entre la Table (à sa droite, nord) et la Menora (à sa gauche, sud).

### 8b-bis. Aliyah (l'étage)

L'עֲלִיָּה n'est pas un comble : *Middot* 4:5-6 la meuble, et le Rambam la dit **bâtie** — « וַעֲלִיָּה בְּנוּיָה עַל גַּבָּיו, גֹּבַהּ כְּתָלֶיהָ אַרְבָּעִים אַמָּה » (*Beit HaBe'hira* 4:2).

- **40 amot de hauteur libre**, de 51 à 91 au-dessus du dallage de l'Azara.
- **Les cinq amot du plancher** (*Middot* 4:6, nommées par Bartenura *ad loc.*) : le **כִּיּוּר**, poutre basse d'une ama, ciselée et dorée, d'où son nom ; le **בֵּית דִּלְפָה**, deux amot laissées **vides** pour recevoir le dégât d'eau (Rambam 4:2, « שֶׁיִּכָּנֵס בּוֹ הַדֶּלֶף ») ; la **תִּקְרָה**, les planches, une ama ; la **מַעֲזִיבָה**, le blocage qui les couvre et fait le sol de l'étage, une ama. Les mêmes cinq au-dessus, puis maake 3 et kaleh orev 1.
- **פִּסְפָּסִין** : « רָאשֵׁי פִסְפָּסִין מַבְדִּילִים בָּעֲלִיָּה בֵּין הַקֹּדֶשׁ לְבֵין קֹדֶשׁ הַקֳּדָשִׁים » (*Middot* 4:5) — une ligne de bornes au sol de l'étage, à l'aplomb de l'ama de Traksin.
- **לוּלִין** : trappes percées dans le plancher au-dessus du Kodesh HaKodashim, « שֶׁבָּהֶן הָיוּ מְשַׁלְשְׁלִין אֶת הָאֻמָּנִים בְּתֵבוֹת, כְּדֵי שֶׁלֹּא יָזוּנוּ עֵינֵיהֶן » (*ibid.*). **Ni leur nombre ni leur place ne sont donnés : deux trémies de 2 amot sur l'axe est un CHOIX.**
- **Porte au sud**, au bout de la מְסִבָּה — « פִּתְחָהּ שֶׁל עֲלִיָּה פָּתוּחַ לַדָּרוֹם » — et deux perches de cèdre à cette porte pour monter sur son toit (*ibid.*).
- **Au-dessus du Heikhal et du Kodesh HaKodashim, pas de l'Oulam.** C'est là que *Middot* 4:5 la meuble, et **Rashi** (sur *DH II* 3:4) met les עליות du Premier Temple au-dessus de la Maison : « מִקַּרְקָעִית הַבַּיִת עַד קֵרוּי עֲלִיָּה רִאשׁוֹנָה שְׁלֹשִׁים, וּמֵעֲלִיָּה לַעֲלִיָּה עַד גַּג הָעֶלְיוֹן תִּשְׁעִים » ; Metsoudat David donne la même lecture en second. **Radak** préfère mettre les 120 amot de *DH II* 3:4 sur l'**Oulam seul**, qui contiendrait les aliyot — minoritaire, et sur le Premier Temple. Le film suit Rashi : au-dessus de l'Oulam, le bâtiment reste **plein**.
- La **מְסִבָּה** qui mène à cette porte et les **תָּאִים** qu'elle dessert sont bâtis (§8b-ter).

### 8b-ter. Ta'im et Messiba

Le corps du bâtiment portait deux bandes pleines de 15 amot de chaque côté. *Middot* 4:7 les découpe, et 4:3-4 les remplit.

**Découpage nord-sud, 70 amot** (*Middot* 4:7) : « כֹּתֶל הַמְּסִבָּה חָמֵשׁ, וְהַמְּסִבָּה שָׁלֹשׁ, כֹּתֶל הַתָּא חָמֵשׁ, וְהַתָּא שֵׁשׁ, כֹּתֶל הַהֵיכָל שֵׁשׁ, וְתוֹכוֹ עֶשְׂרִים » — puis le miroir au sud, où les trois amot sont **בֵּית הוֹרָדַת הַמַּיִם** et non la messiba. En y depuis l'axe : 10 le nu du Heikhal, 16 le nu du mur, 22 le nu des cellules, 27 le mur des ta'im, 30 le couloir, 35 le nu extérieur. **Est-ouest**, derrière le KhK : כֹּתֶל הַהֵיכָל 6, הַתָּא 6, כֹּתֶל הַתָּא 5.

**Ta'im (*Middot* 4:3-4)** : **38** — « חֲמִשָּׁה עָשָׂר בַּצָּפוֹן, חֲמִשָּׁה עָשָׂר בַּדָּרוֹם, וּשְׁמֹנָה בַּמַּעֲרָב ». Nord et sud, cinq sur cinq et cinq au-dessus ; ouest, trois sur trois et deux au-dessus. La cellule s'élargit **5 → 6 → 7** et le mur du Heikhal se retire d'une ama par étage (7 → 6 → 5), « כִּי מִגְרָעוֹת נָתַן לַבַּיִת סָבִיב חוּצָה לְבִלְתִּי אֲחֹז בְּקִירוֹת הַבָּיִת » (*Melakhim I* 6:6, cité par *Middot* 4:4) : **les 6 de mur et 6 de cellule de 4:7 sont donc l'étage du milieu.** Trois ouvertures par cellule — à droite, à gauche, et vers celle du dessus ; **cinq** pour celle du coin nord-est, dont une à la messiba, une au pishpash et une au Heikhal (4:3).

**Pishpashin (*Middot* 4:2)** : deux guichets encadrant le grand portail, un au nord, un au sud. Celui du sud **ne s'ouvre jamais** (*Yehezkel* 44:2) — il est bâti, pas percé. Celui du nord ouvre sur le ta' du coin, et du ta' on entre au Heikhal.

**Messiba (*Middot* 4:5)** : un seul circuit — coin nord-est, toute la face nord jusqu'à l'ouest, toute la face ouest jusqu'au sud, puis vers l'est dans le sud jusqu'à la porte de l'étage. Elle arrive au sol de l'étage, 51 amot au-dessus du dallage.

**CHOIX, à ne pas prendre pour des cotes** : la hauteur d'un étage de cellules (les trois remplissent les 40 amot du rez, 12 de vide et 1 de dalle, 2 pour la dernière), la longueur des cellules et l'épaisseur des refends, la pente de la messiba et la hauteur sous son plafond, la largeur des guichets. Et surtout : **à l'ouest, *Middot* 4:7 ne bande aucun couloir** — les 100 amot est-ouest sont pleines — alors que 4:5 y fait passer la messiba. Les 3 amot du couloir d'ouest sont prises sur les 5 du כֹּתֶל הַתָּא, une ama de maçonnerie de chaque côté.

### 8c. Les trois ustensiles du Heikhal (*Yoma* 33b ; *Mena'hot* 98b–99a ; Rambam *Beit HaBe'hira* 3)

| Ustensile | Position | Dimensions | Détails |
|---|---|---|---|
| **Shoul'han (Table)** | **Nord**, à 2,5 amot du mur nord, dans les deux tiers ouest du Heikhal | 2 amot long × 1 large × 1,5 haut | Bois d'acacia plaqué d'or ; bordure (zer) ; 12 pains (le'hem hapanim) en deux piles de 6 — pain de 5 × 6 tefa'him, 7 etzbaot de haut (Rambam *Temidin* 5:9), piles séparées de 2 tefa'him (*Mena'hot* 96a), soit **≈ 2 amot de pile** au-dessus de la Table ; séparés par 28 tubes d'or (kanim, Rambam *Beit HaBe'hira* 3:15) portés par **quatre montants d'or au sol (snifim)** qui dépassent les piles, ≈ 3,6 amot — plus hauts que la Menora (*Mena'hot* 11:6 ; 94b) ; deux coupes d'encens (bazikhin) sur les piles (Rambam 3:14) |
| **Menora** | **Sud**, à 2,5 amot du mur sud, face à la Table | **18 tefa'him (3 amot)** de haut ≈ 1,44 m | Or pur martelé, **7 branches** dans un même plan N-S, 22 coupes, 11 pommes, 9 fleurs ; pied à trois pieds ; **trois marches** de pierre devant, pour le Cohen qui prépare les mèches. **Forme des branches tranchée** : **droites, en diagonale** (Rambam, Rashi ; `MENORA_DROITE = True`), contre les courbes des représentations traditionnelles et de l'Arc de Titus. Le blockout ne la résout pas — mesurée au plan 9a, la Menora tient sous 0,1 % du cadre —, donc le choix vit dans les prompts 9a et 13a et dans le NÉGATIF commun, pas dans la géométrie. |
| **Mizbea'h HaZahav (autel de l'encens)** | **Au centre**, entre les deux, légèrement **vers l'est** | 1 × 1 ama × 2 de haut (Ex 30:2). **Divergence** : *Kelim* 17:10 mesure cet autel en ama de **5 tefa'him** — R. Meir et R. Yehouda d'accord (*Mena'hot* 97a) — soit 0,83 × 0,83 × 1,67 ; le film garde l'ama de 6 | Acacia plaqué d'or, quatre cornes, bordure. À Kippour l'encens n'est **pas** brûlé ici mais dans le Kodesh HaKodashim ; cet autel reçoit les aspersions de sang (*Yoma* 5:5). |

### 8d. Amah Traksin et les deux Parokhot

- Au Premier Temple : un mur d'une ama (**Amah Traksin**). Au Second Temple : les Sages, ne sachant si cette ama appartenait au Saint ou au Saint des Saints, firent **deux rideaux (parokhot) distants d'une ama** (*Yoma* 5:1).
- Le rideau extérieur est **agrafé au sud**, l'intérieur **agrafé au nord** : le Cohen Gadol entre par le côté sud, longe l'espace d'une ama vers le nord, et entre par le nord (*Yoma* 5:1). Trajet en « S » — très cinématographique.
- **Mise en scène** : l'espace d'une ama (48 cm) ne peut contenir aucune caméra sans rendre un aplat de tissu. L'entrée se filme depuis le Heikhal, côté sud (plan 10) ; la sortie depuis le Kodesh HaKodashim, côté nord (plan 12), en silhouette.
- Parokhet : **40 amot × 20**, épaisseur d'un tefa'h, tissée de 72 fils de 24 brins — **six de chaque des quatre matières, à parts égales** : bleu-violet (tekhelet), pourpre (argaman), écarlate (tola'at shani) et lin (*Shekalim* 8:5 ; Rashi Ex. 26:31). **Aucun fil d'or** : Ex. 26:31 ne liste que ces quatre. *Ma'aseh 'hoshev* = tissage à deux faces portant des images différentes, « un aigle d'un côté, un lion de l'autre » (*Yoma* 72b) ; « keruvim » = figures de créatures diverses (Rashi Ex. 26:31). Deux nouvelles chaque année.
- **Ligne du film** : étoffe lourde et plate, sans plis de drapé ; les quatre couleurs en champs larges, lin blanc compris ; frise répétée de créatures ailées et de lions tissée dans les laines, jamais en or, sans visage humain (§9).
- **Les badim de l'Arche pressent le rideau** : leurs extrémités est se voient depuis le Heikhal « comme deux seins sous l'étoffe » (*Yoma* 54a ; *Mena'hot* 98b ; I Rois 8:8). Deux bosses à hauteur des anneaux (≈ 1,5 ama au-dessus du sol), à 1,38 ama de part et d'autre de l'axe — visibles, petites, aux plans 9a et 9b.

### 8e. Kodesh HaKodashim (Saint des Saints)

- **20 × 20 amot × 40 de haut** (≈ 9,6 × 9,6 × 19 m). Aucune lumière : le Cohen Gadol s'éclaire à la braise de sa pelle.
- Au centre : **l'Even HaShetiya** (pierre de fondation), dépassant du sol de **trois doigts** (*Yoma* 5:2). Dessus, **l'Arche** (§8h) : le film montre le Temple à venir, où l'Arche cachée sous le Temple est revenue à sa place (*Yoma* 54a ; Rambam *Beit HaBe'hira* 4:1). Le Cohen Gadol pose la pelle à braises **entre les deux badim** (*Yoma* 5:1) et se tient là pour les aspersions (*Yoma* 5:3) ; la pierre nue de *Yoma* 5:2 est l'état d'après l'enlèvement de l'Arche, écarté.
- Murs plaqués d'or (traditionnel), sinon pierre nue : le choix « pierre nue + or sombre » est plus sobre.
- **Recommandation de mise en scène** : rien d'autre que l'Arche dans cet espace. Traiter en obscurité, or pris dans la lueur de la braise, et fumée ; ne jamais y placer de figure humaine détaillée. Script : l'Arche (`65_Aron`) et la ma'hta posée entre les badim (braises + lueur, `75_Plan11`) ; caméra à 1,8 ama du sol, entre les badim, à la place du Cohen Gadol.

### 8h. Aron HaBrit, kaporet, keruvim (Temple à venir)

| Élément | Source | Cote retenue |
|---|---|---|
| Caisse | Exode 25:10–11 ; *Yoma* 72b ; Rashi ad loc. | **2,5 × 1,5 × 1,5 amot**, acacia plaqué or dedans et dehors — trois caisses emboîtées (or, bois, or). Or **lisse, sans gravure** : aucune source ne décrit de ciselure |
| Zer | Exode 25:11 ; Rashi ; *Yoma* 72b | la caisse d'or extérieure est plus haute : son rebord **monte autour de la kaporet et la dépasse un peu**, « comme une couronne » — le *keter Torah*, l'une des trois couronnes du Temple |
| Devant l'Arche | Rambam *Beit HaBe'hira* 4:1 ; *Horayot* 12a | posés devant elle, entre les badim : la **fiole de manne** en terre (Ex. 16:33, Rashi), le **bâton d'Aharon** avec ses amandes et ses fleurs (Nb 17:23), la **fiole d'huile d'onction**, le **coffret des Philistins** (I Sam. 6:8). Écarté : la tablette portant le Sefer Torah (*Bava Batra* 14b, R. Yehouda) |
| Orientation | *Mena'hot* 98b | grand côté (2,5) **nord-sud** ; badim **est-ouest**, le long de la largeur |
| Anneaux | Exode 25:12 ; Rashi ad loc. | quatre anneaux d'or **aux coins supérieurs, près de la kaporet** ; deux par flanc (nord / sud) |
| Badim | Exode 25:13–15 ; Rambam *Klei HaMikdash* 2:13 | acacia plaqué or, **jamais retirés** des anneaux ; une barre sur le flanc nord, une sur le sud, 2,5 amot entre elles (deux porteurs marchent entre) |
| Badim et parokhet | *Yoma* 54a ; *Mena'hot* 98b ; I Rois 8:8 | leurs extrémités est pressent la parokhet « comme deux seins », vues du Heikhal (§8d) |
| Kaporet | Exode 25:17 ; *Soucca* 5a–b | 2,5 × 1,5 amot d'or pur, **un tefa'h** d'épaisseur ; caisse + kaporet = **10 tefa'him** |
| Keruvim | Exode 25:18–20 ; Rashi ad loc. ; *Soucca* 5b ; *Bava Batra* 99a ; *Yoma* 54a–b | **deux**, martelés **dans la masse de la kaporet** (miksha — ils en sortent, ni pieds ni socle, Rashi 25:18), à ses deux bouts (nord et sud) ; visage **d'enfant** (*Soucca* 5b, « כרביא »), d'un tefa'h au moins ; hauteur **10 tefa'him** ; **visages l'un vers l'autre, inclinés vers la kaporet** « comme l'élève devant son maître » (*Bava Batra* 99a) ; **ailes déployées au niveau des têtes, un peu au-dessus**, sans toucher le corps, en dais sur la kaporet, dix tefa'him de vide (Rashi 25:20) ; **ligne du film** : un garçon et une fille **enlacés**, « comme un homme et sa compagne » (*Yoma* 54a–b), bras tendus jusqu'à se toucher, ailes jointes au centre. Jamais d'ange drapé ni de putto bouclé : c'est l'iconographie chrétienne |
| Socle | *Yoma* 5:2 ; Rambam *Beit HaBe'hira* 4:1 | posée **sur** l'Even HaShetiya |
| Ma'hta à Kippour | *Yoma* 5:1, 5:3 | « arrivé à l'Arche, il pose la ma'hta **entre les deux badim** » ; il se tient entre les badim pour les aspersions |
| Longueur des badim | I Rois 8:8 ; *Yoma* 54a | non chiffrée. **Ligne du film** : les badim courent jusqu'à la parokhet intérieure (≈ 11 amot) — c'est ce qui rend physiques « entre les badim » et les bosses du rideau. Alternative écartée : badim courts, bosses miraculeuses (*Bava Batra* 99a : dix amot de vide de chaque côté de l'Arche) |

Divergences, à faire valider par un rav :
- **Y aura-t-il une Arche ?** Jérémie 3:16 : « on ne dira plus “l'Arche de l'alliance”… on n'en fera pas une autre ». Le film ne fabrique pas d'Arche neuve : il montre celle de Moïse, enfouie sous le Temple par Yoshiyahou et révélée (*Yoma* 54a ; Rambam *Beit HaBe'hira* 4:1).
- **Position** : Rambam *Beit HaBe'hira* 4:1 place la pierre « à l'ouest » du Kodesh HaKodashim ; la fiche garde la pierre au centre (§8e), *Yoma* 5:2 ne fixe rien.
- **Forme des keruvim** : Rashbam (Ex. 25:18) y voit de grands **oiseaux** ; le film suit *Soucca* 5b et Rashi (enfants) et applique aux keruvim de la kaporet l'enlacement de *Yoma* 54a–b, que la guemara rapporte au Premier Temple ou aux dessins des murs.
- **Keruvim de Salomon** (I Rois 6:23–28 : deux figures debout de 10 amot, ailes de 20 amot couvrant toute la largeur) : **écartés**, ils tiennent du Premier Temple ; seuls les keruvim de la kaporet sont modélisés.
- Les quatre autres choses absentes du Second Temple (*Yoma* 21b : feu du ciel, Shekhina, Roua'h HaKodesh, Ourim veToumim) ne sont pas représentées.

### 8f. Ta'im (cellules) et structures annexes

- **38 cellules** sur trois étages autour du Heikhal et du Kodesh HaKodashim (15 au nord, 15 au sud, 8 à l'ouest), reliées par des ouvertures (*Middot* 4:3).
- **Mesiba** : escalier en spirale à l'angle nord-est montant vers le toit ; **Beit Horadat HaMayim** au sud-ouest pour l'écoulement des eaux (*Middot* 4:5).
- Étage supérieur vide au-dessus du Heikhal, avec des trappes pour descendre les ouvriers en cages fermées lors des réparations du Kodesh HaKodashim (*Middot* 4:5).

---

### 8g. Les deux ustensiles portés dans le Kodesh HaKodashim — ma'hta et kaf

Ils sont le sujet des plans 10, 11 et 12, et aucune source ne donne leur diamètre : les
deux sont dimensionnés sur leur **contenance**, à 1 kav = 1,38 l (Rav 'Haïm Naeh, comme
l'ama du §0). 3 kabin = 4,14 l = 0,037 ama³.

| Ustensile | Ce que disent les sources | Ce que le film retient |
|---|---|---|
| **Ma'hta** (pelle à braises) | À Kippour elle est **d'or**, tient **3 kabin**, est **légère**, et son manche est **long** là où celui des autres jours est court, pour que l'avant-bras en porte le poids (*Yoma* 4:4) ; R. Yossi lit 6 kabin pour la pelle de chaque jour. Le Cohen Gadol la porte de la **main droite** (*Yoma* 5:1, *malgré* la règle qui voudrait la gauche : elle est lourde et chaude — Rambam, *Avodat Yom HaKippurim* 4:1) | Bassin tronconique de 0,52 à 0,60 ama de diamètre sur 0,16 de haut (4,4 l), manche rond de 1,1 ama courant le long de l'avant-bras. Posée sur la pierre, **entre les deux badim**, au pied de l'Arche, au plan 11 (*Yoma* 5:1) |
| **Kaf** (la louche de la ketoret) | « Le kaf **ressemble à un grand tarkav d'or**, il tient **3 kabin** » (*Tamid* 5:4) — donc un **bol de mesure ouvert et rond**, pas une boîte. Le bazakh posé dedans et son couvercle sont ceux du tamid de chaque jour ; à Kippour le Cohen Gadol y verse ses deux poignées et « telle était sa mesure » (*Yoma* 5:1), puis il en tient la **lèvre** du bout des doigts ou entre ses dents pour reverser la ketoret dans ses mains (Rambam, *ibid.*) | Bol tronconique évasé, 0,32 → 0,48 ama de diamètre sur 0,30 de haut (4,2 l), lèvre marquée — la seule prise que la forme donne. Porté de la **main gauche**. Pas de bazakh ni de couvercle : ils appartiennent au tamid |

## 9. Ce que la caméra ne doit PAS montrer (erreurs fréquentes des générateurs IA)

- Pas de **coupole**, pas d'arc en fer à cheval, pas de minaret, pas de croix, pas de colonnes corinthiennes à l'intérieur du Heikhal. **Aucune colonne, aucun pilastre, aucun fronton sur la façade de l'Oulam** : les seules horizontales sont les rovadim et les maltera'ot (§8a). Ya'hin et Boaz ne sont pas une exception à cette règle — elles sont **à l'intérieur** de l'Oulam, vues à travers l'ouverture de 20, jamais plaquées sur la pierre (§8a-bis).
- Pas de **façade dorée** : l'extérieur du bâtiment est en pierre, assises claires alternées, jusqu'aux rovadim de l'Oulam. Hérode voulut la plaquer d'or, les Sages l'en dissuadèrent (*Baba Batra* 4a ; *Soucca* 51b). L'or ne commence qu'au fond de l'Oulam, autour de l'entrée du Heikhal.
- Pas de **Menora à 9 branches** (c'est une 'hanoukia), pas de 6 ou 8 branches.
- L'Arche est **fermée**, jamais ouverte, aucune table de la Loi visible ; **deux** keruvim seulement, sur la kaporet, **visages d'enfant** l'un vers l'autre, ailes vers le haut (§8h) — jamais d'anges adultes, de statues au sol, de coffre second. Pas d'autres statues ni reliefs figuratifs (sauf les keruvim tissés des rideaux).
- Pas de feu sur l'autel d'or à Kippour ; le feu est sur le grand autel extérieur.
- Le Mizbea'h n'a **pas d'escalier** ; c'est une rampe.
- Pas de vêtements colorés pour le Cohen Gadol **à l'intérieur** du Kodesh HaKodashim : uniquement **quatre vêtements de lin blanc** (*Yoma* 3:6, 7:3–4). Les huit vêtements d'or (avec pectoral, éphod, tunique bleue, couronne) sont portés pour les services extérieurs.
- L'ensemble est très **clair** (calcaire blanc, chaux, or) : éviter les rendus sombres « donjon » ou trop rouges.
- Pas de **porte fermée** sur l'axe est-ouest à l'heure du service : ni Nikanor, ni les portes du Heikhal. L'Oulam, lui, n'a jamais eu de porte (*Middot* 3:7).
- Personne dans une zone qui lui est fermée (§12) : c'est l'erreur que l'image-to-video amplifie le plus — une silhouette mal placée sur la frame de départ se met à **marcher** dans la zone interdite pendant huit secondes.

## 10. Références visuelles recommandées

- Machon HaMikdash (Temple Institute), Jérusalem : maquettes, reconstitutions des ustensiles, plans selon le Rambam.
- Leen Ritmeyer, *The Quest: Revealing the Temple Mount in Jerusalem* — reconstitutions archéologiques cohérentes avec la Mishna.
- Dessins du **Tiferet Israël** (Rav Israël Lipschitz) sur *Middot* ; schémas du Rambam dans son commentaire de la Mishna.
- Modèle Holyland (Musée d'Israël) pour l'implantation urbaine et la façade hérodienne.
- Arc de Titus (Rome) pour la Menora et la Table telles que vues par les Romains.

## 11. Liste de contrôle « blockout Blender » (ordre conseillé)

1. Poser le rectangle de l'Azara (187 × 135) et le bâtiment (100 × 100 de façade, corps de 70).
2. Placer le Mizbea'h à 22 amot de l'Oulam, **bord nord à 60,5 amot du mur nord** (centre 9 amot au sud de l'axe), rampe au sud.
3. Ajouter l'Ezrat Nashim (135 × 135) à l'est, les 15 marches, la porte de Nikanor.
4. Creuser l'Oulam (ouverture 20 × 40) puis le Heikhal (20 × 40 × 40 intérieur), poser les rovadim de la façade et arrêter les murs à 96, maake et kaleh orev au-dessus (§8, §8a).
5. Placer les trois ustensiles, les deux parokhot (ama d'écart, agrafes S/N, bosses des badim), l'Even HaShetiya et l'Arche dessus (§8h).
6. Murs de l'Azara avec les 7 portes (10 × 20), **dans l'ordre d'ouest en est** (§5) : au sud Delek, Bekhorot, **Mayim** ; au nord Nitzotz, Korban, **Beit HaMoked**. Trois **corps de porte** de 20 amot de large débordant de 12 : Sha'ar HaMayim (aliyah = Beit Avtinas) et Sha'ar HaNitzotz (aliyah = Beit HaNitzotz, *Middot* 1:5) au droit de leur porte, le Beit HaMoked à cheval sur le mur. La Lishkat Parhedrin contre le corps de Sha'ar HaMayim. Les six lishkot de *Middot* 5:3-4 : au nord HaGazit (à cheval sur le mur), HaGola et, en second rang derrière elles, HaEtz ; au sud, **dans** l'Azara contre la face intérieure du mur, HaMelah, HaParva — bain rituel sur son toit — et HaMedi'hin avec sa mesiba. Dans l'Ezrat Israël, les deux lishkot de Sha'ar Nikanor (Pin'has HaMalbish, Osei 'Havitin — *Middot* 1:4).
7. Kiyor et Beit HaMitba'haïm.
8. Har HaBayit (500 × 500) et portiques en fond, Soreg et 'Heil.
9. Caméras : déclarées dans `cameras.json`, posées par `beit_hamikdash_cameras.py` — position et cible keyframées, contrainte Track To, marqueur de timeline par plan.
10. **Planche de contrôle** : rendre la première et la dernière image de chaque caméra (`renders/planche/planche.html`) avant tout rendu définitif. Une caméra posée dans un solide ou finissant dans une surface ne se voit que là, jamais dans la table des caméras.

## 12. Où se tiennent les gens (peuple, Léviim, cohanim)

Les places ne sont pas un choix de mise en scène : la Mishna les donne, et l'axe est-ouest de l'Azara est découpé au nom de ses occupants (*Middot* 5:1).

| Qui | Où | Cote | Source |
|---|---|---|---|
| **Le peuple** | Ezrat Israël, la bande la plus à l'est de l'Azara | **11 amot** sur les 135 de large | *Middot* 5:1, « מְקוֹם דְּרִיסַת יִשְׂרָאֵל אַחַת עֶשְׂרֵה אַמָּה » |
| **Les cohanim** | Ezrat Cohanim, les 11 amot suivantes vers l'ouest | **11 amot** | *Middot* 5:1, « מְקוֹם דְּרִיסַת הַכֹּהֲנִים » |
| **Les Léviim** | Sur le **Doukhan**, l'estrade posée sur la marche d'une ama qui sépare les deux cours, plus trois marches de ½ ama | — | *Middot* 2:6 (R. Eliézer ben Yaakov) |
| Les enfants Léviim | **En bas**, pas sur le Doukhan, « la tête entre les jambes des Léviim » | — | *Arakhin* 2:6 |
| Le débordement | Ezrat Nashim (135 × 135), puis le Har HaBayit | — | *Middot* 2:5 ; l'Ezrat Israël ne fait que 11 × 135 |

**Nombres.** On ne descend **pas au-dessous de douze Léviim** debout sur le Doukhan, et l'on ajoute sans limite (*Arakhin* 2:6). Une rangée de sept est une erreur.

**Barrières.** Le peuple ne franchit pas l'Ezrat Cohanim, sauf pour semikha, she'hita et tenoufa (*Kelim* 1:8). Entre l'Oulam et l'autel : cohanim **sans défaut** et coiffés seulement. Dans le Heikhal : mains et pieds lavés. Dans le Kodesh HaKodashim : **le Cohen Gadol seul, à Kippour, à l'heure du service**.

**Pendant l'encens.** « Et nul homme ne sera dans la tente d'assignation » (Lév. 16:17) : *Yoma* 5:1 ne montre que le Cohen Gadol — l'Oulam et le Heikhal sont **vides**. Aucun plan intérieur ne doit montrer une seconde silhouette.

**Prosternation.** « Les cohanim **et le peuple** qui se tiennent dans l'Azara, lorsqu'ils entendaient le Nom explicite sortir de la bouche du Cohen Gadol, se mettaient à genoux, se prosternaient et tombaient sur leur face » (*Yoma* 6:2). Les deux cours, pas seulement les cohanim.

**Bénédiction.** Pour bénir le peuple les cohanim montent et se tiennent **sur les douze marches de l'Oulam** (*Tamid* 7:2), pas dans la cour.

**Tenue — règle du film, tous les plans où figure quelqu'un.** Les fidèles sont des juifs religieux **d'aujourd'hui**, vêtus comme leur communauté s'habille pour Kippour : costumes sombres et chemise blanche, redingotes noires, kaftans, djellabas et robes claires du Maghreb et d'Orient, beaucoup enveloppés d'un **talith gadol** blanc à rayures sombres rabattu sur la tête. Tête couverte sans exception, de deux façons **et de deux seulement** : kippa posée à plat sur le crâne (velours noir, tricotée, blanche) ou le talith rabattu. Jamais de turban, de coiffe enroulée, de keffieh ni de capuche. Jamais de costume d'époque ni de toge.

**Les cohanim sont la seule exception** : eux seuls portent les *bigdei lavan*, lin blanc uni, et la coiffe de lin plate du service — ils officient, ils ne sont pas dans l'assemblée.

**Le Cohen Gadol, en or, deux gros plans.** Le lin blanc est le vêtement du service intérieur (Lév. 16:4) ; les habits d'or se revêtent entre les immersions, derrière un drap de lin tendu entre lui et le peuple (*Yoma* 3:4, 3:6 ; 7:3), sur le toit du Beit HaParva (*Middot* 5:3). Les plans 7c et 7d le montrent ainsi, sur la parole « il revêtait les habits d'or », sans visage : le 'hoshen de face cadré sous le menton, le tsits noué à la nuque de dos — forme selon Rambam *Klei HaMikdash* 8–10 : me'il tout tekhelet sans manches, éphod et 'heshev tissés d'or, 'hoshen carré d'un zeret à douze pierres en quatre rangs (Ex. 28:17–20) lié à l'éphod par des cordons de tekhelet (Ex. 28:28), pierres de shoham aux épaules, mitsnefet enroulée à plat, tsits noué à la nuque. Ces deux plans portent leur propre ligne `**Figures**`, qui remplace le bloc commun ; tous les autres restent au lin blanc.

Personne ne fait face à l'objectif : tout le monde est tourné vers le Heikhal, vu de dos.

**Où la règle est appliquée.** Dans le prompt d'édition de chaque frame, qui nomme la tenue des figures que la caméra voit — et dans celui-là seul : donnée au prompt vidéo, la même description fait *naître* des figures chez les modèles i2v sans prompt négatif (skill `fal-video`).

**Où les places sont contrôlées.** Sur les deux frames stylisées, avant toute génération vidéo, puis sur le mp4 : l'i2v n'a aucun plan de correction, et une silhouette posée dans une zone qui lui est fermée se met à y marcher (skill `fal-video`).

**Dans le blockout.** Collection `76_Foule` (`FOULE = True`) : la foule est l'état permanent du jour — **les douze Léviim du Doukhan en font partie**, postés du matin au soir et sujets d'aucun plan.
