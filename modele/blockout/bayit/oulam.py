import math
from mathutils import Vector

from ..primitives.parametres import Z_AZ, Z_BAT
from ..primitives.matieres import (MAT_BRONZE, MAT_CEDRE, MAT_CHENE_SCULPTE, MAT_FER_LAME, MAT_MARBRE,
                                   MAT_MARBRE_HERODE, MAT_OR)
from ..primitives.volumes import (alea, box, chaine, cone, courbe, cyl, cyl_between, limbe, plage, plaque,
                                  revolution, sphere, tore)
from ..primitives.ouvrages import (EPAISSEUR_PLACAGE, MAAKE_H, ROVAD_SAILLIE, couches_middot, escalier,
                                   massif_evide, paroi_percee, rovadim)
from ..azara import H_PISHPESH


# ----------------------------------------------------------------------------
# 40/50/60 — LE BÂTIMENT (100 × 100 × 100), Middot 4
#   x : -76 (façade est) → -176 (arrière ouest)
#   Oulam mur 5 | Oulam 11 | mur 6 | Heikhal 40 | Traksin 1 | KhK 20 | mur 6 | cellule 6 | mur 5
# ----------------------------------------------------------------------------
BX_E, BX_O = -76, -176
H_BAT = 100
# Décomposition verticale de Middot 4:6 : אֹטֶם 6, גֹּבַהּ 40, כִּיּוּר 1, בֵּית דִּלְפָה 2, תִּקְרָה 1,
# מַעֲזִיבָה 1, עֲלִיָּה 40, puis de nouveau 1 + 2 + 1 + 1 — soit 96 depuis le sol de l'Azara.
# Les 4 amot qui manquent aux 100 ne sont pas du mur : מַעֲקֶה 3 et כָּלֵה עוֹרֵב 1.
Z_FAITE = Z_AZ + H_BAT              # 100 : le faîte, pointes comprises
Z_TOIT = Z_FAITE - MAAKE_H - 1      # 96 : là où s'arrête le mur
# Plateforme (sol surélevé de 6 amot) et 12 marches devant l'Oulam
# L'אֹטֶם suit le plan du bâtiment, « צַר מֵאֲחוֹרָיו וְרָחָב מִלְּפָנָיו » (Middot 4:7) : 100 sous l'Oulam, 70 derrière.
box("Batiment_socle_oulam", BX_E - 16, BX_E, -50, 50, Z_AZ, Z_BAT, "40_Ulam", MAT_MARBRE_HERODE())
box("Batiment_socle_corps", BX_O, BX_E - 16, -35, 35, Z_AZ, Z_BAT, "40_Ulam", MAT_MARBRE_HERODE())
# « רוּם מַעֲלָה חֲצִי אַמָּה, וְשִׁלְחָהּ אַמָּה. אַמָּה אַמָּה וְרֹבֶד שָׁלֹשׁ, וְאַמָּה אַמָּה וְרֹבֶד שָׁלֹשׁ.
# וְהָעֶלְיוֹנָה, אַמָּה אַמָּה וְרֹבֶד אַרְבַּע » (Middot 3:6) : le giron fait une ama, sauf trois
# rovadim. Bartenura ad loc. les compte depuis le bas — la 4e et la 7e de trois amot, la
# 12e de quatre jusqu'à l'Oulam : 19 amot de marches, et 3 de plat au pied du Mizbea'h.
GIRONS_ULAM = (1, 1, 1, 3, 1, 1, 3, 1, 1, 1, 1, 4)
_x = BX_E + sum(GIRONS_ULAM)
for i, giron in enumerate(GIRONS_ULAM):
    box(f"Marche_Ulam_{i:02d}", _x - giron, _x, -11, 11, Z_AZ, Z_AZ + 0.5 * (i + 1), "40_Ulam")
    _x -= giron

# --- Oulam : façade 100 large, ouverture 20 × 40 (Middot 3:7), « וְלֹא הָיָה לוֹ שְׁעָרִים » (Rambam Beit HaBe'hira 4:8)
box("Ulam_facade_S", BX_E - 5, BX_E, -50, -10, Z_BAT, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
box("Ulam_facade_N", BX_E - 5, BX_E, 10, 50, Z_BAT, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
box("Ulam_facade_linteau", BX_E - 5, BX_E, -10, 10, Z_BAT + 40, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
# --- La façade est n'est PAS dorée, et la guemara le raconte comme un refus : « סָבַר
#     לְמִשְׁעֲיֵיהּ בְּדַהֲבָא, אֲמַרוּ לֵיהּ רַבָּנַן שַׁבְקֵיהּ דְּהָכִי שַׁפִּיר טְפֵי דְּמִיחֲזֵי כְּאִידַּוְּותָא דְיַמָּא » — Hérode
#     voulut la plaquer d'or, les Sages l'en dissuadèrent, la pierre est plus belle
#     ainsi, « comme les vagues de la mer » (Baba Batra 4a ; Soucca 51b). Ce qui fait
#     l'extérieur est donc l'assise elle-même : shesh, marmara et kuchla en assises
#     alternées, une en débord une en retrait, déjà dans MAT_MARBRE_HERODE.
#     L'or reste où les sources le mettent : dedans (Middot 4:1), sur les portes, sur
#     la vigne et sur la nivreshet d'Hélène.
# Cinq poutres de chêne au-dessus de l'ouverture (Middot 3:7), la première couchée sur le
# linteau — « מֻשְׁכֶּבֶת עַל מַשְׁקוֹף הַפֶּתַח » (Bartenura ad loc.) —, une assise entre deux.
# Linteau d'une ama : CHOIX.
for i in range(5):
    L = 22 + i * 2
    box(f"Maltera_{i}", BX_E - 5.4, BX_E + 0.4, -L / 2, L / 2, Z_BAT + 41 + i * 2, Z_BAT + 42 + i * 2, "40_Ulam", MAT_CHENE_SCULPTE())
# --- Rovadim : les bandeaux en saillie qui ceinturent les murs de l'Oulam de bas en
#     haut (Rambam, Beit HaBe'hira 4:9). C'est la seule articulation que les sources
#     donnent à cette façade, et elle est horizontale.
#     La face du bâtiment ne porte aucune colonne : ni Middot 3:7-8 et 4:6-7, ni le
#     Rambam n'en mettent une dehors.
#     Ya'hin et Boaz sont dedans, dans l'Oulam, là où le Tanakh et ses commentateurs les
#     posent (voir plus bas). Les fûts de l'Oulam sont les כְּלוֹנָסוֹת de cèdre tendus du mur
#     du Heikhal à celui de l'Oulam (Middot 3:8).
#     Le rovad du sommet emporte les 4 dernières amot du mur, où Middot 4:6 met le
#     כִּיּוּר et la בֵּית דִּלְפָה de l'étage.
#     Deux échelles d'horizontales, et elles se confirment : celle-ci, de 4 amot, et
#     celle des assises — « אַפֵּיק שָׂפָה וְעַיֵּיל שָׂפָה » (Baba Batra 4a ; Soucca 51b), une
#     assise en débord, une en retrait. La seconde est déjà dans MAT_MARBRE_HERODE et
#     n'a pas à être bâtie deux fois.
ROVAD_X_E = BX_E                          # les bandeaux se posent sur le nu du mur
rovadim("Ulam_facade", ROVAD_X_E, (1, 0), -50, 50, Z_BAT, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE(),
        reserve=[(-10, 10, Z_BAT, Z_BAT + 40),        # la baie de 20 × 40
                 (-16, 16, Z_BAT + 40, Z_BAT + 52)])  # et la pile d'amaltraot
Y_PISHPESH_HALIFOT = (42, 45)          # |y| de la baie, dans la face ouest de chaque débord
# Les faces nord et sud portent les mêmes bandeaux, et s'arrêtent au mur du Heikhal :
# le Kessef Mishneh (sur 4:9) écarte les rovadim du corps du bâtiment,
# « וְלֹא שֶׁיְּהֵא מֻקָּף רְבָדִים כְּמוֹ שֶׁל אוּלָם ».
for cote, y, sens in (("N", 50, 1), ("S", -50, -1)):
    rovadim(f"Ulam_flanc_{cote}", y, (0, sens), BX_E - 16, ROVAD_X_E + ROVAD_SAILLIE,
            Z_BAT, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
    # « סָבִיב לְכָתְלֵי הָאוּלָם » : la face ouest des débords aussi, du corps du bâtiment à l'angle.
    rovadim(f"Ulam_flanc_retour_{cote}", BX_E - 16, (-1, 0), *sorted((sens * 35, y + sens * ROVAD_SAILLIE)),
            Z_BAT, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE(),
            reserve=[(*sorted(sens * y for y in Y_PISHPESH_HALIFOT), Z_BAT, Z_BAT + H_PISHPESH)])

# Beit HaHalifot : « הָאוּלָם עוֹדֵף עָלָיו חֲמֵשׁ עֶשְׂרֵה אַמָּה מִן הַצָּפוֹן… וְהוּא הָיָה נִקְרָא בֵּית
# הַחֲלִיפוֹת, שֶׁשָּׁם גּוֹנְזִים אֶת הַסַּכִּינִים » (Middot 4:7) — « שֶׁכֹּתֶל הָאוּלָם עָבְיוֹ חָמֵשׁ אַמָּה,
# וְהָאוּלָם עֶשֶׂר אַמּוֹת לַצָּפוֹן » (Bartenura ad loc.). Une chambre fermée de chaque côté —
# « הָיָה חֶדֶר מִכָּאן וּמִכָּאן » (Tiferet Israël, Yakhin sur Middot 4:7, 71) —, et à chacune deux
# portes : « א' לָאוּלָם, וְא' בַּזָּוִית… בְּזָוִית צְפוֹנִית מַעֲרָבִית… דְּרוֹמִית מַעֲרָבִית. וְכָל א' מִב' אֵלּוּ
# הַפְּתָחִים הָיָה גָּבוֹהַּ ח' אַמּוֹת » (ibid., 72) ; « שְׁנֵי פִּשְׁפָּשִׁין הָיוּ בְּבֵית הַחֲלִיפוֹת, וְגוֹבְהָן
# שְׁמֹנָה » (Zeva'him 55b), « וּפְתוּחִין לַמַּעֲרָב » (Rashi ad loc., citant la Tossefta).
# Avis écartés : l'Oulam lui-même, ouvert sur ses débords (Tosfot Yom Tov) ; les niches dans le
# mur ouest, du dehors — « וּבַכּוֹתֶל הַמַּעֲרָבִי… הָיוּ חַלּוֹנוֹת לִגְנוֹז סַכִּינִין מִבַּחוּץ » (Rashi sur
# Zeva'him 55b).
# Le mur qui ferme la chambre à l'ouest n'est dans aucune source : 5 amot pris dans les 16,
# CHOIX, pour garder le corps à 70. Largeur des deux portes (celle des pishpeshim de Nikanor),
# cloison d'une ama, vantail rabattu du pishpesh, et les degrés qui descendent à l'Azara, six
# amot plus bas (« כָּל הַמַּעֲלוֹת… רוּם מַעֲלָה חֲצִי אַמָּה, וְשִׁלְחָהּ חֲצִי אַמָּה », Middot 2:3) : CHOIX.
# Une niche par michmar : « חַלּוֹנוֹת הָיוּ בְּלִשְׁכַּת הַחֲלִיפוֹת שֶׁשָּׁם גּוֹנְזִין אֶת סַכִּינֵיהֶם » (Bartenura
# sur Soucca 5:8), « לכל משמר ומשמר היה שם ארגז מיוחד בכותל » (Tiferet Israël sur Middot 4:7).
# Celle de Bilga est murée, « וְחַלּוֹנָהּ סְתוּמָה » (Soucca 5:8 ; Soucca 56b). Taille, place et
# répartition : CHOIX — les 24 dans l'ordre de Divrei HaYamim I 24, les douze premiers au
# nord, Bilga quinzième (24:14), dans le mur latéral que l'on voit depuis l'Oulam.
NICHE_L, NICHE_H, NICHE_P = 1.2, 1.0, 0.8
NICHE_SEUILS = (Z_BAT + 4, Z_BAT + 2.6, Z_BAT + 1.2)
MICHMAR_BILGA = 15
# « אֵין שׁוֹחֲטִין אוֹתָן לְכַתְּחִלָּה אֶלָּא בְּסַכִּין מִכְּלֵי שָׁרֵת » (Rambam Ma'asse HaKorbanot 4:7), de
# métal : « כֻּלָּן שֶׁל כֶּסֶף וְשֶׁל זָהָב הָיוּ וּמֻתָּר לַעֲשׂוֹתָן מִשְּׁאָר מִינֵי מַתָּכוֹת » (Klei HaMikdash
# 1:13), et pas de bois — « אין עושין כלי שרת של עץ » (Tossefot sur Houlin 3a), d'où un manche
# de bronze. Longueur : « מְלֹא צַוָּאר חוּץ לַצַּוָּאר » (Houlin 31a). Forme, fer, et deux par
# niche : CHOIX.
SAKIN_LAME, SAKIN_TALON, SAKIN_MANCHE = 0.75, 0.14, 0.3


def sakin(nom, talon, sens_u, pente, y, col):
    """Couteau debout contre le fond de sa niche, pointe vers `sens_u`, le talon à `talon`."""
    d = Vector((sens_u * math.cos(pente), 0, math.sin(pente)))
    haut = Vector((-d.z * sens_u, 0, d.x * sens_u)).normalized()
    o = Vector((talon[0], y, talon[1]))
    pointe = o + d * SAKIN_LAME
    plaque(f"{nom}_lame", [tuple(o + haut * SAKIN_TALON / 2), tuple(pointe),
                           tuple(o + d * (SAKIN_LAME * 0.7) - haut * SAKIN_TALON * 0.3),
                           tuple(o - haut * SAKIN_TALON / 2)], 0.03, col, MAT_FER_LAME())
    cyl_between(f"{nom}_manche", tuple(o), tuple(o - d * SAKIN_MANCHE), 0.04, col, MAT_BRONZE(), verts=8)


for cote, sens, premier in (("N", 1, 1), ("S", -1, 13)):
    nu = sens * 45
    niches = []
    for k in range(12):
        u = BX_E - 11 + 0.15 + 1.5 * (k % 4)
        zb = NICHE_SEUILS[k // 4]
        niches.append((u, u + NICHE_L, *sorted((nu, nu + sens * NICHE_P)), zb, zb + NICHE_H))
        if premier + k == MICHMAR_BILGA:
            box("Ulam_halifot_niche_Bilga", u, u + NICHE_L, *sorted((nu + sens * 0.08, nu + sens * NICHE_P)),
                zb, zb + NICHE_H, "40_Ulam", MAT_MARBRE_HERODE())
            continue
        sakin(f"Ulam_halifot_sakin_{cote}_{k:02d}_a", (u + 0.08 + SAKIN_MANCHE, zb + 0.2), 1, math.radians(-10),
              nu + sens * 0.62, "40_Ulam")
        sakin(f"Ulam_halifot_sakin_{cote}_{k:02d}_b", (u + NICHE_L - 0.08 - SAKIN_MANCHE, zb + 0.28), -1,
              math.radians(-14), nu + sens * 0.4, "40_Ulam")
    massif_evide(f"Ulam_halifot_mur_{cote}", BX_E - 16, BX_E - 5, *sorted((sens * 45, sens * 50)),
                 Z_BAT, Z_TOIT, niches, "40_Ulam", MAT_MARBRE_HERODE())
    pishpesh = sorted(sens * y for y in Y_PISHPESH_HALIFOT)
    massif_evide(f"Ulam_halifot_fond_{cote}", BX_E - 16, BX_E - 11, *sorted((sens * 35, sens * 45)),
                 Z_BAT, Z_TOIT, [(BX_E - 16, BX_E - 11, *pishpesh, Z_BAT, Z_BAT + H_PISHPESH)],
                 "40_Ulam", MAT_MARBRE_HERODE())
    box(f"Ulam_halifot_pishpesh_{cote}_vantail", BX_E - 11, BX_E - 10.8, *sorted((sens * 39, sens * 42)),
        Z_BAT, Z_BAT + H_PISHPESH, "40_Ulam", MAT_BRONZE())
    escalier(f"Ulam_halifot_degres_{cote}", BX_E - 22, BX_E - 16, *pishpesh, Z_AZ, Z_BAT, "-x",
             "40_Ulam", MAT_MARBRE_HERODE())
    paroi_percee(f"Ulam_halifot_cloison_{cote}", BX_E - 11, BX_E - 5, *sorted((sens * 35, sens * 36)),
                 Z_BAT, Z_BAT + 40, "40_Ulam", MAT_MARBRE_HERODE(),
                 [(BX_E - 9.5, BX_E - 6.5, Z_BAT, Z_BAT + H_PISHPESH)])
    couches_middot(f"Ulam_halifot_plancher_{cote}", BX_E - 11, BX_E - 5, *sorted((sens * 35, sens * 45)),
                   Z_BAT + 40, "40_Ulam")
    box(f"Ulam_halifot_masse_{cote}", BX_E - 11, BX_E - 5, *sorted((sens * 35, sens * 45)),
        Z_BAT + 45, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
# Le plafond de l'Oulam porte les mêmes cinq amot (Middot 4:6, le bâtiment est un seul
# bloc de 100). Au-dessus, plein : aucune source ne met de pièce là — les עליות sont sur la
# Maison chez Rashi, et l'Oulam-tour de Radak est du Premier Temple (CHOIX de suivre Rashi).
couches_middot("Ulam_plancher", BX_E - 16, BX_E - 5, -35, 35, Z_BAT + 40, "40_Ulam")
box("Ulam_masse", BX_E - 16, BX_E - 5, -35, 35, Z_BAT + 45, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
# « כְּלוֹנָסוֹת שֶׁל אֶרֶז הָיוּ קְבוּעִין מִכָּתְלוֹ שֶׁל הֵיכָל לְכָתְלוֹ שֶׁל אוּלָם, כְּדֵי שֶׁלֹּא יִבְעַט »
# (Middot 3:8) : les poutres rondes de cèdre tendues d'un mur à l'autre, sous le
# plafond, et trois poutres en travers qui en font les caissons — le « coffered cedar
# ceiling of the porch » du prompt 8, qui n'était qu'une dalle.
for k, y in enumerate(plage(-31.5, 31.5, 7)):
    cyl_between(f"Ulam_klonas_{k:02d}", (BX_E - 16, y, Z_BAT + 38.4), (BX_E - 5, y, Z_BAT + 38.4),
                0.5, "40_Ulam", MAT_CEDRE(), verts=12)
for k, x in enumerate((BX_E - 13.25, BX_E - 10.5, BX_E - 7.75)):
    box(f"Ulam_plafond_poutre_{k}", x - 0.4, x + 0.4, -35, 35, Z_BAT + 39.1, Z_BAT + 40, "40_Ulam", MAT_CEDRE())
# « וְשַׁרְשְׁרוֹת שֶׁל זָהָב הָיוּ קְבוּעוֹת בְּתִקְרַת הָאוּלָם, שֶׁבָּהֶן פִּרְחֵי כְהֻנָּה עוֹלִין וְרוֹאִין אֶת
# הָעֲטָרֹת » (Middot 3:8) : fixées dans les poutres du plafond et pendantes dans le vide de
# l'Oulam — « וְתוֹלוֹת לְמַטָּה בָּאוּלָם שֶׁאוֹחֲזִין בָּהֶן פִּרְחֵי כְהֻנָּה מְפַסְּגִין וְעוֹלִין » (R. Shemaya,
# cité par le Tossefot Yom Tov ad loc.) : on s'y agrippe et on monte. Elles descendent donc
# à hauteur de main, pas à mi-hauteur. Nombre et place : CHOIX — au-delà de y ±10 pour
# laisser la mire de Middot 2:4, et à l'écart des kotarot de Ya'hin et Boaz.
# Les עֲטָרוֹת de Zekharia 6:14 qu'on monte voir ne sont pas modelées : leur place est
# disputée — aux fenêtres de l'aliyah de l'Oulam (Melekhet Shlomo ad loc.), étage que ce
# blockout ne bâtit pas, ou aux fenêtres du Heikhal (Bartenura ad loc. ; Abravanel sur
# Zekharia 6:14), qui ne sont pas visibles de l'Oulam.
for k, y in enumerate((-24, -13, 13, 24)):
    chaine(f"Ulam_sharsheret_{k}", (BX_E - 10.5, y, Z_BAT + 39.4), (BX_E - 10.5, y, Z_BAT + 3.5),
           0.24, "40_Ulam", MAT_OR(), tube=0.075, majeur=8, mineur=5)
# Deux tables de l'Oulam (marbre au nord... CHOIX : marbre à droite en entrant = nord ; or au sud)
box("Ulam_table_marbre", -90, -88, 5.5, 6.5, Z_BAT, Z_BAT + 1.5, "40_Ulam", MAT_MARBRE())
box("Ulam_table_or", -90, -88, -6.5, -5.5, Z_BAT, Z_BAT + 1.5, "40_Ulam", MAT_OR())
# Ya'hin et Boaz (Melakhim I 7:15-22 ; Yirmiyahou 52:21-23 ; Divrei HaYamim II 3:15-17).
# Fût : 18 amot, donné trois fois et sans divergence — Melakhim I 7:15, Yirmiyahou 52:21,
# Melakhim II 25:17. Les 35 amot de Divrei HaYamim II 3:15 ne sont pas la hauteur d'une
# colonne mais la mesure des deux couchées au moment de la coulée, d'où « אֹרֶךְ » et non
# « קוֹמָה » : 18 + 18 = 36, moins l'ama que les deux demi-fûts perdent dans les kotarot
# (Radak et Rashi ad loc. ; Metsoudat David, « של שניהם יחד »).
# Kotéret : 5 amot (Melakhim I 7:16 ; Divrei HaYamim II 3:15). Les 3 amot de Melakhim II
# 25:17 sont les seules décorées — « שְׁתֵּי אַמּוֹת הַתַּחְתּוֹנוֹת שֶׁל כּוֹתָרוֹת הָיוּ שָׁווֹת לָעַמּוּד שֶׁלֹּא
# הָיָה בָּהֶם צוּרָה, וְשָׁלֹשׁ עֶלְיוֹנוֹת הֵן נִפְרָדוֹת לַחוּץ מֻקָּפוֹת שְׂבָכִים » (Baraïta des 49 Middot, citée
# par Radak sur 7:16). D'où le profil : 2 amot au nu du fût, 3 en saillie, et au sommet la
# calotte de « מַעֲשֵׂה שׁוּשַׁן » qui coiffe le creux du fût (Metsoudat David sur 7:19-20).
# Largeur : « כִּי הָעַמּוּדִים הָיוּ בְּרֹחַב אַרְבַּע אַמּוֹת » (Metsoudat David sur 7:19) — 4 amot, ce
# que donne aussi le tour de 12 amot (Melakhim I 7:15 ; Yirmiyahou 52:21) au π de trois
# d'Erouvin 76a. Élancement 4,5:1 : du bronze coulé, pas une tige.
# Place : dans l'Oulam. « וַיָּקֶם אֶת הָעַמֻּדִים לְאֻלָם הַהֵיכָל » (7:21), que Radak lit « כְּמוֹ
# בְּאוּלָם הַהֵיכָל », Ralbag « שֶׁהֱקִימָם בּוֹ », Metsoudat David « בָּאוּלָם שֶׁלִּפְנֵי הַהֵיכָל » et, sur
# Divrei HaYamim II 3:15, « בַּחֲלַל הָאוּלָם ». Le « מַעֲשֵׂה שׁוּשַׁן בָּאוּלָם » de 7:19 dit la même
# chose. Elles tiennent donc l'ouverture de 20 (Middot 3:7) par l'intérieur, face externe
# au nu du jambage, 12 amot de passage au milieu : la ligne de mire du mont des Oliviers
# vers la porte du Heikhal, large de 10, reste dégagée (Middot 2:4).
# Ya'hin à droite, soit au sud, Boaz à gauche (Metsoudat David sur 7:21).
AMOUD_X, AMOUD_Y, AMOUD_R, AMOUD_H = BX_E - 8.5, 8, 2, 18
KOTERET = [(AMOUD_R, 0.0), (AMOUD_R, 2.0), (2.5, 2.35), (2.9, 3.0), (3.1, 3.8), (3.0, 4.4),
           (2.55, 4.75), (AMOUD_R, 4.95), (1.15, 4.8), (0.0, 4.5)]
# Sept chaînettes par kotéret (Melakhim I 7:17), posées sur les trois amot en saillie
SHARSHEROT = ((2.45, 2.62), (2.75, 2.82), (3.05, 2.98), (3.35, 3.06),
              (3.65, 3.14), (3.95, 3.14), (4.25, 3.08))
for nom, y in (("Yakhin", -AMOUD_Y), ("Boaz", AMOUD_Y)):
    cyl(f"{nom}_fut", AMOUD_X, y, Z_BAT, Z_BAT + AMOUD_H, AMOUD_R, "40_Ulam", MAT_BRONZE(), verts=48)
    revolution(f"{nom}_koteret", AMOUD_X, y, Z_BAT + AMOUD_H, KOTERET, "40_Ulam", MAT_BRONZE(), verts=48)
    for k, (z, R) in enumerate(SHARSHEROT):
        tore(f"{nom}_sharsheret_{k}", AMOUD_X, y, Z_BAT + AMOUD_H + z, R, 0.06, "40_Ulam", MAT_BRONZE())
    # « וְהָרִמּוֹנִים מָאתַיִם טֻרִים סָבִיב » (7:20) : cent par rang, deux rangs, enfilés sur les
    # chaînettes comme des perles — « חֲרוּזִים בִּשְׁנֵי טוּרִים » (Metsoudat David ad loc.)
    for rang, k in enumerate((3, 5)):
        z, R = SHARSHEROT[k]
        for i in range(100):
            a = 2 * math.pi * (i + 0.5 * rang) / 100
            sphere(f"{nom}_rimon_{rang}{i:02d}", AMOUD_X + (R + 0.04) * math.cos(a), y + (R + 0.04) * math.sin(a),
                   Z_BAT + AMOUD_H + z, 0.09, "40_Ulam", MAT_BRONZE(), segs=6)
# La tablette d'or d'Hélène (Yoma 3:10), « שֶׁפָּרָשַׁת סוֹטָה כְּתוּבָה עָלֶיהָ », d'où le kohen
# copie la parasha. Sur l'or du mur est de l'Oulam, côté nord : CHOIX.
TAVLA_X = BX_E - 16 + EPAISSEUR_PLACAGE   # le nu de l'or sur le mur est du Heikhal, HX_E plus bas
box("Tavla_Helene", TAVLA_X, TAVLA_X + 0.08, 18.5, 21.5, Z_BAT + 5.5, Z_BAT + 7.5, "40_Ulam", MAT_OR())
for k in range(8):
    z = Z_BAT + 7.25 - 0.22 * k
    box(f"Tavla_Helene_ligne_{k}", TAVLA_X + 0.08, TAVLA_X + 0.11, 18.75 + (0.35 if k == 7 else 0), 21.25,
        z, z + 0.06, "40_Ulam", MAT_OR())
# --- Gefen Zahav (Middot 3:8) : « גֶּפֶן שֶׁל זָהָב הָיְתָה עוֹמֶדֶת עַל פִּתְחוֹ שֶׁל הֵיכָל, וּמֻדְלָה עַל
#     גַּבֵּי כְלוֹנָסוֹת. כָּל מִי שֶׁהוּא מִתְנַדֵּב עָלֶה, אוֹ גַרְגִּיר, אוֹ אֶשְׁכּוֹל, מֵבִיא וְתוֹלֶה בָהּ ».
#     מֻדְלָה, c'est palissée : un cep, des perches, des sarments tendus dessus. L'anneau
#     de tore ceint de vingt-quatre plaques radiales se lisait en rouage, et aucune
#     source ne met de cercle ici.
#     Ce que la michna donne d'autre, c'est le désordre : chacun apporte son or « כִּדְמוּת
#     גַּרְגִּיר אוֹ עָלֶה אוֹ אֶשְׁכּוֹל » (Bartenura ad loc.) et l'accroche — donc des feuilles de
#     tailles et d'inclinaisons différentes, des grappes inégales, jamais un pas régulier.
#     Le poids d'or accumulé est ce que dit R. Eliezer b. Tsadok par ses trois cents
#     kohanim (lashon havai, Bartenura ad loc. ; Houllin 90b).
#     Le cep monte du sol de l'Oulam le long de la perche sud — CHOIX, la michna ne dit
#     pas d'où il part. Les perches se posent hors des jambages de la porte de 10 et la
#     vigne tient au-dessus du linteau : la ligne de mire du mont des Oliviers vers la
#     porte du Heikhal (Middot 2:4) reste dégagée.
CONTOUR_FEUILLE = [(0.00, 0.00), (0.03, 0.13), (0.11, 0.25), (0.20, 0.28), (0.26, 0.20),
                   (0.34, 0.31), (0.45, 0.40), (0.54, 0.36), (0.58, 0.25), (0.66, 0.29),
                   (0.78, 0.25), (0.90, 0.15), (1.00, 0.00)]


def sarment(nom, points, r0, r1):
    """Sarment : tronçons au rayon décroissant le long d'une polyligne, nœuds aux coudes."""
    n = len(points) - 1
    for k in range(n):
        r = r0 + (r1 - r0) * (k + 1) / n
        cyl_between(f"{nom}_{k:02d}", points[k], points[k + 1], r, "40_Ulam", MAT_OR(), verts=8)
        if k % 3 == 1:
            sphere(f"{nom}_noeud_{k:02d}", *points[k], r * 1.15, "40_Ulam", MAT_OR(), segs=6)
    return points


def _sur_sarment(points, t):
    """Point et tangente à la fraction t d'une polyligne."""
    k = min(int(t * (len(points) - 1)), len(points) - 2)
    u = t * (len(points) - 1) - k
    a, b = Vector(points[k]), Vector(points[k + 1])
    return a + (b - a) * u, (b - a).normalized()


def rameau(z, y0, y1, cle, n=16, ampli=0.55):
    """Course d'un sarment le long d'un lit : il ondule autour de la traverse, il ne la double pas."""
    return [(VIGNE_XL + 0.28 + 0.16 * math.sin(4.1 * t + 6 * alea(cle)),
             y0 + (y1 - y0) * t,
             z + ampli * math.sin(2.4 * math.pi * t + 6 * alea(cle, 1)))
            for t in (k / n for k in range(n + 1))]


def feuille_de_vigne(nom, attache, taille, cle):
    """Feuille à cinq lobes et son pétiole, pliée en gouttière le long de la nervure."""
    axe = Vector((0.45 + 0.5 * alea(cle, 1),
                  1.7 * (alea(cle, 2) - 0.5),
                  0.9 * (alea(cle, 3) - 0.62))).normalized()
    base = Vector(attache) + axe * 0.3 * taille
    plan = (axe.cross(Vector((0, 1, 0))) + Vector((0.6, 0, 0.4 * (alea(cle, 4) - 0.5)))).normalized()
    cyl_between(f"{nom}_petiole", attache, tuple(base), 0.03, "40_Ulam", MAT_OR(), verts=5)
    limbe(nom, CONTOUR_FEUILLE, tuple(base), tuple(axe), tuple(plan), taille, 0.022,
          "40_Ulam", MAT_OR(), courbure=0.2)


def grappe(nom, attache, longueur, cle, baies=28):
    """Grappe : rafle courte et baies en cône serré, les plus grosses en haut."""
    haut = Vector(attache) + Vector((0.1, 0, -0.22 * longueur))
    cyl_between(f"{nom}_rafle", attache, tuple(haut), 0.05, "40_Ulam", MAT_OR(), verts=6)
    for k in range(baies):
        t = k / (baies - 1)
        large = 0.22 * longueur * (1 - t) ** 0.65
        a = 2.4 * k + 6 * alea(cle, k)
        p = haut + Vector((0.6 * large * math.cos(a) * (0.4 + alea(cle, 40 + k)),
                           large * math.sin(a),
                           -0.78 * longueur * t))
        sphere(f"{nom}_{k:02d}", p.x, p.y, p.z, 0.17 - 0.06 * t, "40_Ulam", MAT_OR(), segs=8)


def vrille(nom, depart, rayon, longueur, cle, tours=2.5, n=14):
    """Vrille : la spirale par où la vigne s'accroche — c'est elle qui la dit de loin."""
    d = Vector((0.35 * (alea(cle) - 0.5), 0.5 * (alea(cle, 1) - 0.5), -1)).normalized()
    u = d.cross(Vector((1, 0, 0))).normalized()
    v = d.cross(u)
    pts = []
    for k in range(n + 1):
        t = k / n
        a = 2 * math.pi * tours * t
        r = rayon * min(1.0, 3 * t)
        pts.append(tuple(Vector(depart) + d * (longueur * t)
                         + (u * (math.cos(a) - 1) + v * math.sin(a)) * r))
    for k in range(n):
        cyl_between(f"{nom}_{k:02d}", pts[k], pts[k + 1], 0.035, "40_Ulam", MAT_OR(), verts=5)


VIGNE_X, VIGNE_Y = -91.5, 5.5        # devant le nu du mur est du Heikhal ; perches hors des jambages
VIGNE_XL = VIGNE_X + 0.3             # les lits passent devant les perches
VIGNE_LITS = (Z_BAT + 25, Z_BAT + 29.5, Z_BAT + 34)
VIGNE_Z_HAUT = Z_BAT + 37.9          # sous les klonasot du plafond de l'Oulam
for s in (-1, 1):
    cyl_between(f"Vigne_perche{s:+d}", (VIGNE_X, s * VIGNE_Y, Z_BAT),
                (VIGNE_X, s * VIGNE_Y, VIGNE_Z_HAUT), 0.16, "40_Ulam", MAT_OR(), verts=10)
for k, z in enumerate(VIGNE_LITS):
    cyl_between(f"Vigne_lit_{k}", (VIGNE_XL, -VIGNE_Y, z), (VIGNE_XL, VIGNE_Y, z),
                0.13, "40_Ulam", MAT_OR(), verts=10)
    for s in (-1, 1):
        tore(f"Vigne_lien_{k}{s:+d}", VIGNE_X + 0.15, s * VIGNE_Y, z, 0.24, 0.05,
             "40_Ulam", MAT_OR(), rotation=(0, math.pi / 2, 0), majeur=12, mineur=6)

SARMENTS = [
    sarment("Vigne_cep",
            courbe((VIGNE_X + 0.4, -VIGNE_Y + 0.7, Z_BAT), (VIGNE_X + 0.9, -VIGNE_Y - 0.6, Z_BAT + 13),
                   (VIGNE_XL + 0.1, -VIGNE_Y + 0.5, VIGNE_LITS[0]), 12), 0.55, 0.26),
    sarment("Vigne_rameau_0", rameau(VIGNE_LITS[0], -VIGNE_Y + 0.5, VIGNE_Y - 0.4, "rameau0"), 0.24, 0.1),
    sarment("Vigne_montant_S",
            courbe((VIGNE_XL + 0.15, -4.4, VIGNE_LITS[0]), (VIGNE_XL + 0.7, -5.2, (VIGNE_LITS[0] + VIGNE_LITS[1]) / 2),
                   (VIGNE_XL + 0.2, -4.5, VIGNE_LITS[1]), 8), 0.22, 0.14),
    sarment("Vigne_rameau_1", rameau(VIGNE_LITS[1], -4.5, VIGNE_Y - 0.5, "rameau1"), 0.2, 0.09),
    sarment("Vigne_montant_N",
            courbe((VIGNE_XL + 0.2, 4.3, VIGNE_LITS[1]), (VIGNE_XL + 0.75, 5.2, (VIGNE_LITS[1] + VIGNE_LITS[2]) / 2),
                   (VIGNE_XL + 0.2, 4.5, VIGNE_LITS[2]), 8), 0.18, 0.12),
    sarment("Vigne_rameau_2", rameau(VIGNE_LITS[2], 4.5, -VIGNE_Y + 0.8, "rameau2", ampli=0.4), 0.17, 0.08),
    sarment("Vigne_rameau_3",
            courbe((VIGNE_XL + 0.3, -2.6, VIGNE_LITS[0] + 0.3), (VIGNE_XL + 0.9, -1.2, VIGNE_LITS[0] + 2.6),
                   (VIGNE_XL + 0.35, 0.9, VIGNE_LITS[1] - 0.4), 9), 0.14, 0.07),
    sarment("Vigne_rameau_4",
            courbe((VIGNE_XL + 0.3, 2.2, VIGNE_LITS[1] + 0.2), (VIGNE_XL + 0.95, 3.4, VIGNE_LITS[1] + 2.5),
                   (VIGNE_XL + 0.35, 1.6, VIGNE_LITS[2] - 0.3), 9), 0.13, 0.06),
]
# Les guirlandes : ce que la vigne fait retomber entre deux points d'un même lit, et
# d'où pendent les grappes.
GUIRLANDES = []
for k, (lit, ya, yb) in enumerate(((0, -4.9, -2.3), (0, 2.2, 5.0),
                                   (1, -4.4, -1.1), (1, -0.6, 2.5), (1, 3.0, 4.9),
                                   (2, -4.1, -0.5), (2, 0.3, 4.3))):
    z = VIGNE_LITS[lit]
    creux = 1.2 + 1.3 * alea("guirlande", k)
    GUIRLANDES.append(sarment(f"Vigne_guirlande_{k:02d}",
                              courbe((VIGNE_XL + 0.15, ya, z), (VIGNE_XL + 0.75, (ya + yb) / 2, z - 2 * creux),
                                     (VIGNE_XL + 0.15, yb, z), 10), 0.13, 0.09))
for k, points in enumerate(GUIRLANDES):
    for j, t in ((0, 0.5), (1, 0.22 + 0.12 * alea("grappe", k))):
        p, _ = _sur_sarment(points, t)
        grappe(f"Vigne_grappe_{k:02d}{j}", tuple(p), 1.0 + 1.2 * alea("grappe", 10 * k + j),
               f"grappe{k}{j}")
# La feuille et le fruit poussent sur le sarment de l'année, pas sur le vieux cep —
# et une feuille sur le cep descendait sous le linteau, dans la mire de Middot 2:4.
TIGES = SARMENTS[1:] + GUIRLANDES
for k in range(54):
    points = TIGES[(5 * k + k // len(TIGES)) % len(TIGES)]
    p, _ = _sur_sarment(points, 0.06 + 0.88 * alea("feuille", k))
    feuille_de_vigne(f"Vigne_feuille_{k:02d}", tuple(p), 0.8 + 0.7 * alea("feuille", 50 + k),
                     f"feuille{k}")
for k in range(9):
    points = TIGES[(3 * k + 1) % len(TIGES)]
    p, _ = _sur_sarment(points, 0.15 + 0.7 * alea("vrille", k))
    vrille(f"Vigne_vrille_{k}", tuple(p), 0.14 + 0.08 * alea("vrille", 10 + k),
           0.7 + 0.5 * alea("vrille", 20 + k), f"vrille{k}")

# Nivreshet d'or de la reine Hélène au-dessus de l'entrée du Heikhal (Yoma 3:10) : une
# lampe — « מנורה », glose Bartenura, que Tosfot Yom Tov rapproche de la « נברשתא » de
# Daniel 5:5. « בְּשָׁעָה שֶׁהַחַמָּה זוֹרַחַת נִיצוֹצוֹת יוֹצְאִין מִמֶּנָּה, וְהַכֹּל יוֹדְעִין שֶׁהִגִּיעַ זְמַן קְרִיאַת שְׁמַע »
# (Yoma 37b) : ce qu'elle doit faire, c'est renvoyer le premier soleil pris par
# l'ouverture est de l'Oulam — une vasque d'or bombée dessous, et douze becs à huile sur
# sa lèvre. Ni la forme ni les cotes ne sont données : CHOIX. Elle pend au premier lit de
# la vigne par trois chaînes à maillons (CHOIX) : un cylindre tendu se lisait en tige.
NIVRESHET_X, NIVRESHET_Z, NIVRESHET_R = -90.6, Z_BAT + 22, 1.0
revolution("Nivreshet_Helene", NIVRESHET_X, 0, NIVRESHET_Z,
           [(0.10, 0.00), (0.30, 0.03), (0.62, 0.12), (0.88, 0.26), (NIVRESHET_R, 0.40),
            (NIVRESHET_R + 0.06, 0.46), (NIVRESHET_R - 0.04, 0.48), (0.80, 0.38), (0.0, 0.30)],
           "40_Ulam", MAT_OR(), verts=36)
cone("Nivreshet_Helene_bouton", NIVRESHET_X, 0, NIVRESHET_Z - 0.28, NIVRESHET_Z + 0.02,
     0.0, 0.12, "40_Ulam", MAT_OR(), verts=12)
for k in range(12):
    a = 2 * math.pi * (k + 0.5) / 12
    c, sn = math.cos(a), math.sin(a)
    cyl_between(f"Nivreshet_Helene_bec_{k:02d}",
                (NIVRESHET_X + (NIVRESHET_R - 0.05) * c, (NIVRESHET_R - 0.05) * sn, NIVRESHET_Z + 0.44),
                (NIVRESHET_X + (NIVRESHET_R + 0.28) * c, (NIVRESHET_R + 0.28) * sn, NIVRESHET_Z + 0.52),
                0.055, "40_Ulam", MAT_OR(), verts=8)
for k in range(3):
    a = math.radians(90 + 120 * k)
    y = (NIVRESHET_R - 0.02) * math.sin(a)
    chaine(f"Nivreshet_Helene_chaine_{k}",
           (NIVRESHET_X + (NIVRESHET_R - 0.02) * math.cos(a), y, NIVRESHET_Z + 0.46),
           (VIGNE_XL, y, VIGNE_LITS[0]), 0.075, "40_Ulam", MAT_OR())
