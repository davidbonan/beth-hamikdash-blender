import bpy
import math
from typing import NamedTuple

from .primitives.parametres import TEFAH, Z_AZ, Z_EZI, Z_EZN, m
from .primitives.pierre import ASSISE
from .primitives.matieres import (MAT_AVNET, MAT_BRONZE, MAT_CEDRE, MAT_CEDRE_LAMBRIS, MAT_CHAUX, MAT_CHENE,
                                  MAT_EAU, MAT_FER, MAT_KETORET, MAT_KLAF, MAT_LAINE, MAT_LECHEM, MAT_LIN,
                                  MAT_MARBRE, MAT_OR, MAT_OR_PLAQUE, MAT_PEAU, MAT_SEL, MAT_SOL, MAT_SOLET,
                                  MAT_TERRE_CUITE, MAT_TEVEN, braise)
from .primitives.volumes import (alea, box, cone, cyl, cyl_between, empty, graver, lampe, mesh_from_pydata,
                                 ner_sur_tablette, plaque, prism, revolution, sphere, tore)
from .primitives.gravures import petur_tzitz
from .primitives.ouvrages import (ECART_LISHKA, LISHKA_CORNICHE, LISHKA_DEBORD, LISHKA_PAREMENT, MESIBA_PORTE,
                                  PORTE_LISHKA, PORTE_SHAAR, Porte, aliyah, battants, dalle_percee,
                                  dalle_trouee, escalier, escalier_a_vis, lishka, maake, moulure,
                                  paroi_percee, puits_de_mesiba, terrasse_de_porte)
from .azara import (AX1, AXE_MUR_N, AY0, AY1, GAZIT_X0, GAZIT_X1, GOLA_X0, GOLA_X1, H_PISHPESH, MOKED_X0,
                    MOKED_X1, NORD_INT, NORD_Y0, NORD_Y1, PISHPESHIM, PORTE_MAYIM, PORTE_MOKED, PORTE_NITZOTZ,
                    SAILLIE, SAILLIE_INT, T, X_DOUKHAN)


# Chambres du pourtour — 80_Lishkot. Elles sont adossées aux murs de l'Azara mais
# posées sur la terrasse du 'Heil (plus bas) : leur pied est à Z_EZN, dix amot sous le sol
# de la cour qu'elles bordent. Les faire partir de Z_AZ les laissait en l'air. Middot 1:7 le dit
# du Beit HaMoked : « אֶחָד פָּתוּחַ לַחֵיל וְאֶחָד פָּתוּחַ לָעֲזָרָה » — une porte à chaque
# niveau, donc un bâtiment qui les enjambe.

# Beit HaMoked : sur la porte nord la plus orientale, la troisième que compte
# Middot 1:5. Il est à cheval sur la limite du sacré et non posé derrière le mur —
# « אַרְבַּע לְשָׁכוֹת הָיוּ בְּבֵית הַמּוֹקֵד… שְׁתַּיִם בַּקֹּדֶשׁ וּשְׁתַּיִם בַּחֹל, וְרָאשֵׁי
# פִסְפָּסִין מַבְדִּילִין בֵּין קֹדֶשׁ לַחֹל » (Middot 1:6). D'où deux שערים opposés
# (Middot 1:7), et le mur de l'Azara s'interrompt sur sa largeur. CHOIX : ni la largeur
# (20 amot, comme les deux autres corps de porte) ni la hauteur (30 au-dessus de l'Azara)
# n'ont de source ; la hauteur passe le mur de 25, sans quoi les deux toits seraient
# coplanaires.
# La salle est au niveau de l'Azara, où ouvre le שער que Middot 2:3 change en or ; celui du
# 'Heil est en haut de vingt degrés, comme Sha'ar HaKorban. CHOIX : pris dedans, ces degrés
# couperaient la salle, et les quatre chambres de Middot 1:6 n'y tiendraient plus.
lishka("Beit_HaMoked", MOKED_X0, MOKED_X1, NORD_Y0, NORD_Y1, Z_EZN, Z_AZ + 30, "80_Lishkot",
       [Porte("N", *PORTE_SHAAR, Z_AZ), Porte("S", *PORTE_SHAAR, Z_AZ, metal=MAT_OR())])
battants("Beit_HaMoked_S_battants", PORTE_MOKED - 5, PORTE_MOKED + 5, NORD_Y0,
         NORD_Y0 + LISHKA_PAREMENT, Z_AZ, PORTE_SHAAR[1], "80_Lishkot", MAT_OR())
maake("Beit_HaMoked", MOKED_X0, MOKED_X1, NORD_Y0, NORD_Y1, Z_AZ + 30, "80_Lishkot")
escalier("Beit_HaMoked_escalier", PORTE_MOKED - 5, PORTE_MOKED + 5, NORD_Y1, NORD_Y1 + 10,
         Z_EZN, Z_AZ, "+y", "80_Lishkot")
MK_X0, MK_X1 = MOKED_X0 + LISHKA_PAREMENT, MOKED_X1 - LISHKA_PAREMENT
MK_Y0, MK_Y1 = NORD_Y0 + LISHKA_PAREMENT, NORD_Y1 - LISHKA_PAREMENT
# Le sol de la salle : la cour le donne jusqu'à la face extérieure du mur, sauf au-dessus de
# l'Ezrat Israël, deux amot et demie plus bas ; au-delà, la terrasse du 'Heil est à dix amot.
PUITS_MESIBA = (MK_X0, MK_X0 + 3.5, AY1 + T, AY1 + T + 3.5)
dalle_percee("Beit_HaMoked_sol_hol", MK_X0, MK_X1, AY1 + T, MK_Y1, Z_EZN, Z_AZ, "80_Lishkot",
             MAT_SOL(), [PUITS_MESIBA])
box("Beit_HaMoked_sol_ezrat_israel", X_DOUKHAN, MK_X1, MK_Y0, AY1 + T, Z_EZI - 1, Z_AZ,
    "80_Lishkot", MAT_SOL())
# « אַרְבַּע לְשָׁכוֹת… כְּקִיטוֹנוֹת פְּתוּחוֹת לִטְרַקְלִין, שְׁתַּיִם בַּקֹּדֶשׁ וּשְׁתַּיִם בַּחֹל » (Middot 1:6) : quatre
# chambrettes qui ouvrent sur la salle, deux de chaque côté de la limite, rangées le long
# des murs est et ouest entre les deux vestibules des שערים. Cotes : CHOIX. La profondeur laisse
# au nord-ouest un palier derrière le puits : la première marche de la vis y est, contre la cloison.
KITON_L, KITON_P, KITON_H, CLOISON = 4.5, 7, 6, 0.5
KITONOT_Y = ((AXE_MUR_N - CLOISON - KITON_P, AXE_MUR_N - CLOISON),
             (AXE_MUR_N + CLOISON, AXE_MUR_N + CLOISON + KITON_P))
KITONOT_Y0, KITONOT_Y1 = KITONOT_Y[0][0] - CLOISON, KITONOT_Y[1][1] + CLOISON
for cote, mur, sens in (("O", MK_X0, 1), ("E", MK_X1, -1)):
    salle = mur + sens * KITON_L
    paroi_percee(f"Beit_HaMoked_kitonot_{cote}", *sorted((salle, salle + sens * CLOISON)),
                 KITONOT_Y0, KITONOT_Y1, Z_AZ, Z_AZ + KITON_H, "80_Lishkot", None,
                 [(sum(ky) / 2 - 1, sum(ky) / 2 + 1, Z_AZ, Z_AZ + KITON_H - 1) for ky in KITONOT_Y])
    for k, (ya, yb) in enumerate(((KITONOT_Y0, KITONOT_Y[0][0]), (KITONOT_Y[0][1], KITONOT_Y[1][0]),
                                  (KITONOT_Y[1][1], KITONOT_Y1))):
        box(f"Beit_HaMoked_kitonot_{cote}_cloison_{k}", *sorted((mur, salle)), ya, yb,
            Z_AZ, Z_AZ + KITON_H, "80_Lishkot")
    box(f"Beit_HaMoked_kitonot_{cote}_plafond", *sorted((mur, salle + sens * CLOISON)),
        KITONOT_Y0, KITONOT_Y1, Z_AZ + KITON_H, Z_AZ + KITON_H + CLOISON, "80_Lishkot")
KITON_SUD_Y0, KITON_SUD_Y1 = KITONOT_Y[0]
KITON_BAIE_Y = (KITON_SUD_Y0 + KITON_SUD_Y1) / 2
# Sud-ouest, « לִשְׁכַּת טְלָאֵי קָרְבָּן » : « אֵין פּוֹחֲתִין מִשִּׁשָּׁה טְלָאִים הַמְבֻקָּרִין בְּלִשְׁכַּת הַטְּלָאִים »
# (Arakhin 2:5). La scène n'a pas d'animaux : l'enclos seul — mangeoire de pierre, paille, barrière
# basse dans la baie. CHOIX. Tamid 3:3 met la chambre au nord-ouest ; la scène suit Middot 1:6.
EVUS = (MK_X0 + 0.25, MK_X0 + 1.05, KITON_SUD_Y0 + 0.75, KITON_SUD_Y1 - 0.75)
dalle_trouee("Beit_HaMoked_kiton_SO_evus", MK_X0, MK_X0 + 1.3, KITON_SUD_Y0 + 0.5, KITON_SUD_Y1 - 0.5,
             Z_AZ, Z_AZ + 1.3, EVUS, "80_Lishkot")
box("Beit_HaMoked_kiton_SO_evus_teven", *EVUS, Z_AZ, Z_AZ + 1.1, "80_Lishkot", MAT_TEVEN())
for k in range(5):
    cle = f"Beit_HaMoked_kiton_SO_teven_{k}"
    x, y, cote = MK_X0 + 1.6 + 2.2 * alea(cle), KITON_SUD_Y0 + 0.3 + 5.2 * alea(cle, 1), 1 + 0.8 * alea(cle, 2)
    box(cle, x, x + cote, y, y + cote, Z_AZ, Z_AZ + 0.05, "80_Lishkot", MAT_TEVEN())
BARRIERE_X = MK_X0 + KITON_L + CLOISON / 2
for k, z in enumerate((0.5, 1.1, 1.7)):
    cyl_between(f"Beit_HaMoked_kiton_SO_barriere_{k}", (BARRIERE_X, KITON_BAIE_Y - 1, Z_AZ + z),
                (BARRIERE_X, KITON_BAIE_Y + 1, Z_AZ + z), 0.08, "80_Lishkot", MAT_CHENE(), verts=8)
# Sud-est, « לִשְׁכַּת עוֹשֵׂי לֶחֶם הַפָּנִים », du côté du קדש : « לִישָׁתָן וַעֲרִיכָתָן בַּחוּץ, וַאֲפִיָּתָן בִּפְנִים »
# (Mena'hot 11:2) — le four est ici, le pétrin ailleurs. « וּבִטְפוּס הָיָה עוֹשֶׂה אוֹתָן. וּכְשֶׁהוּא רָדָן, נוֹתְנָן
# בִּטְפוּס » (11:1) : deux moules sur la table, au format du pain, « אָרְכָּן עֲשָׂרָה וְרָחְבָּן חֲמִשָּׁה, וְקַרְנוֹתָיו
# שֶׁבַע אֶצְבָּעוֹת » (11:4), et la pelle qui le retire. Four, pelle, fer des moules : CHOIX.
box("Beit_HaMoked_kiton_SE_table", MK_X1 - 1.5, MK_X1, KITON_SUD_Y0 + 0.3, KITON_SUD_Y0 + 4.1,
    Z_AZ, Z_AZ + 1.5, "80_Lishkot", MAT_MARBRE())
TFUS_L, TFUS_P, TFUS_H, TFUS_EP = 10 * TEFAH, 5 * TEFAH, 7 / 4 * TEFAH, 0.04
TFUS_X = MK_X1 - 0.75
for k in range(2):
    y0 = KITON_SUD_Y0 + 0.45 + k * (TFUS_L + 0.2)
    box(f"Beit_HaMoked_kiton_SE_tfus_{k}", TFUS_X - TFUS_P / 2, TFUS_X + TFUS_P / 2, y0, y0 + TFUS_L,
        Z_AZ + 1.5, Z_AZ + 1.5 + TFUS_EP, "80_Lishkot", MAT_FER())
    for cote, s in (("O", -1), ("E", 1)):
        xp = TFUS_X + s * TFUS_P / 2
        box(f"Beit_HaMoked_kiton_SE_tfus_{k}_paroi_{cote}", xp, xp - s * TFUS_EP, y0, y0 + TFUS_L,
            Z_AZ + 1.5, Z_AZ + 1.5 + TFUS_H, "80_Lishkot", MAT_FER())
TANUR_X, TANUR_Y = MK_X1 - 1.9, KITON_SUD_Y1 - 1.4
revolution("Beit_HaMoked_kiton_SE_tanur", TANUR_X, TANUR_Y, Z_AZ,
           [(0.0, 0.0), (1.1, 0.0), (1.0, 1.6), (0.72, 2.2), (0.52, 2.2), (0.8, 1.6), (0.9, 0.25), (0.0, 0.25)],
           "80_Lishkot", MAT_TERRE_CUITE(), verts=20)
cyl("Beit_HaMoked_kiton_SE_tanur_gahalim", TANUR_X, TANUR_Y, Z_AZ + 0.25, Z_AZ + 0.45, 0.8,
    "80_Lishkot", braise("Braise"), verts=16)
MARDE_X = MK_X1 - KITON_L + 0.4
cyl_between("Beit_HaMoked_kiton_SE_marde", (MARDE_X, KITON_SUD_Y1 - 0.2, Z_AZ + 0.9),
            (MARDE_X, KITON_SUD_Y1 - 0.1, Z_AZ + 4.2), 0.05, "80_Lishkot", MAT_CHENE(), verts=8)
box("Beit_HaMoked_kiton_SE_marde_kaf", MARDE_X - 0.3, MARDE_X + 0.3, KITON_SUD_Y1 - 0.25, KITON_SUD_Y1 - 0.15,
    Z_AZ + 0.05, Z_AZ + 0.95, "80_Lishkot", MAT_CHENE())
# Nord-est, « בָּהּ גָּנְזוּ בְנֵי חַשְׁמוֹנַאי אֶת אַבְנֵי הַמִּזְבֵּחַ שֶׁשִּׁקְּצוּם מַלְכֵי יָוָן » : les pierres entassées.
for k, (dx, dy, dz) in enumerate(((0.0, 0.0, 0), (1.8, 0.1, 0), (0.3, 1.2, 0), (1.6, 1.3, 0),
                                  (0.1, 0.3, 1), (1.6, 1.1, 1), (0.8, 0.8, 2))):
    x, y = MK_X1 - 3.3 + dx, KITONOT_Y[1][1] - 3 + dy
    box(f"Beit_HaMoked_kiton_NE_even_{k}", x, x + 1.4, y, y + 1, Z_AZ + dz, Z_AZ + dz + 1,
        "80_Lishkot", MAT_CHAUX())
# Nord-ouest, « בָּהּ יוֹרְדִים לְבֵית הַטְּבִילָה » : le sol s'ouvre sur le puits de la « מְסִבָּה הַהוֹלֶכֶת
# תַּחַת הַבִּירָה » (Middot 1:9), bâtie avec le tunnel « SOUS L'AZARA ».
# « מֻקָּף רוֹבָדִין שֶׁל אֶבֶן » (Middot 1:8) — Bartenura : « אִצְטַבָּאוֹת… מְשֻׁקָּעוֹת בַּכֹּתֶל… כְּעֵין מַעֲלוֹת
# זוֹ עַל זוֹ ». Deux gradins le long des murs, où dorment les anciens ; ils bordent les deux
# vestibules, cotes CHOIX.
for cote, mur, sens in (("O", MK_X0, 1), ("E", MK_X1, -1)):
    for vestibule, va, vb in (("S", MK_Y0, KITONOT_Y0), ("N", KITONOT_Y1, MK_Y1)):
        for rang, (saillie, zb, zh) in enumerate(((1.5, 0, 1), (0.75, 1, 2))):
            box(f"Beit_HaMoked_rovad_{vestibule}{cote}_{rang}", *sorted((mur, mur + sens * saillie)),
                va, vb, Z_AZ + zb, Z_AZ + zh, "80_Lishkot")
# « וְזִקְנֵי בֵית אָב יְשֵׁנִים שָׁם… וּפִרְחֵי כְהֻנָּה אִישׁ כִּסְתּוֹ בָאָרֶץ » (Tamid 1:1) : les anciens sur les
# rovadim, les jeunes à terre sur leurs « כָּרִים וּכְסָתוֹת » (Bartenura ad loc.). En plein jour la literie
# est roulée — les anciens sur leur gradin, les jeunes en piles contre les kitonot. Côté 'hol, nombre,
# laine : CHOIX.
for cote, mur, sens in (("O", MK_X0, 1), ("E", MK_X1, -1)):
    cyl_between(f"Beit_HaMoked_keset_zaken_{cote}", (mur + sens * 1.125, KITONOT_Y1 + 0.4, Z_AZ + 1.3),
                (mur + sens * 1.125, MK_Y1 - 0.4, Z_AZ + 1.3), 0.3, "80_Lishkot", MAT_LAINE(), verts=12)
    box(f"Beit_HaMoked_kar_zaken_{cote}", mur, mur + sens * 0.7, KITONOT_Y1 + 1, KITONOT_Y1 + 3,
        Z_AZ + 2, Z_AZ + 2.25, "80_Lishkot", MAT_LAINE())
    face = mur + sens * (KITON_L + CLOISON)
    for pile, (ya, yb) in enumerate(((AXE_MUR_N + 0.8, AXE_MUR_N + 2.8), (KITONOT_Y1 - 2.8, KITONOT_Y1 - 0.8))):
        for rouleau, (d, z) in enumerate(((0.3, 0.28), (0.86, 0.28), (0.58, 0.76))):
            cyl_between(f"Beit_HaMoked_keset_perach_{cote}{pile}{rouleau}", (face + sens * d, ya, Z_AZ + z),
                        (face + sens * d, yb, Z_AZ + z), 0.28, "80_Lishkot", MAT_LAINE(), verts=12)
# « מָקוֹם הָיָה שָׁם, אַמָּה עַל אַמָּה, וְטַבְלָא שֶׁל שַׁיִשׁ וְטַבַּעַת הָיְתָה קְבוּעָה בָהּ » (Middot 1:9) :
# la dalle sous laquelle pendent les clefs de l'Azara. Sa place, près du שער : CHOIX.
TAVLA_X, TAVLA_Y = PORTE_MOKED, MK_Y0 + 3
box("Beit_HaMoked_tavla", TAVLA_X - 0.5, TAVLA_X + 0.5, TAVLA_Y - 0.5, TAVLA_Y + 0.5,
    Z_AZ, Z_AZ + 0.05, "80_Lishkot", MAT_MARBRE())
tore("Beit_HaMoked_tavla_tabaat", TAVLA_X, TAVLA_Y, Z_AZ + 0.09, 0.2, 0.04, "80_Lishkot", MAT_FER())
# « וְרָאשֵׁי פִסְפָּסִין מַבְדִּילִין בֵּין קֹדֶשׁ לַחֹל » (Middot 1:6) : la limite tracée au sol de la salle,
# sur l'axe du mur. Filet de marbre : CHOIX.
box("Beit_HaMoked_rashei_pispasin", MK_X0 + KITON_L + CLOISON, MK_X1 - KITON_L - CLOISON,
    AXE_MUR_N - 0.1, AXE_MUR_N + 0.1, Z_AZ, Z_AZ + 0.03, "80_Lishkot", MAT_MARBRE())
# --- Les trois lishkot du nord (Middot 5:3-4 ; Rambam, Beit HaBe'hira 5:17) : HaGazit,
#     HaGola, HaEtz, « וְגַג שְׁלָשְׁתָּן שָׁוֶה » — un seul niveau de toit pour les trois, à 30
#     au-dessus de l'Azara. Leur disposition est celle que Tosfot Yom Tov (Middot 5:4,
#     d'après Shiltei HaGiborim) tire de « אֲחוֹרֵי שְׁתֵּיהֶן » : HaGazit à l'est, devant les
#     deux autres ; HaGola et HaEtz derrière elle, l'une DANS la cour — « שֵׁשׁ לְשָׁכוֹת הָיוּ
#     בָעֲזָרָה » (5:3) —, l'autre au nord, dos au 'Heil — « לִשְׁכַּת הַגּוֹלָה לְדָרוֹם… וְלִשְׁכַּת הָעֵץ
#     בְּצָפוֹן… נִמְצָא שֶׁלִּשְׁכַּת הָעֵץ אֲחוֹרֶיהָ לְצָפוֹן ». Le mur nord passe entre les deux, comme
#     il passe au milieu de HaGazit. Le groupe demande 44 amot de mur continu, et la portée
#     à l'ouest de Sha'ar HaNitzotz est la seule qui les offre : à l'est, les escaliers de
#     Sha'ar HaKorban et le Beit HaMoked ne laissent que 37,5. Aucune source ne donne
#     ces x (CHOIX) ; l'ORDRE, lui, est tenu — d'est en ouest, HaGazit puis HaGola.
#     OUVERT — le nord des trois suit la girsa de Yoma 19a, celle du Rambam et la
#     préférence de Tosfot Yom Tov sur Middot 5:3 (« ונראה בעיני שגירסת הספר נשתבשה »),
#     contre le texte imprimé de Middot 5:4 qui les met au SUD. Mais le même Rambam
#     identifie Lishkat HaEtz à la Lishkat Parhedrin, que la scène place au sud d'après
#     le Yerushalmi (voir plus bas) : la scène tient l'avis que le Cohen Gadol avait
#     DEUX lishkot — ce que Yoma 19a laisse ouvert (« וְלֹא יָדַעְנָא » laquelle est au nord,
#     laquelle au sud) — et non que Parhedrin = HaEtz.
# Lishkat HaGazit, même parti que le Beit HaMoked : à cheval, la salle au niveau de la cour,
# un פתח sur le sacré et un sur le 'hol (Yoma 25a). Celui du 'hol est à l'est, et ses
# degrés descendent dans les cinq amot qui la séparent de Sha'ar HaNitzotz. CHOIX,
# comme sa cote.
PETAH_HOL_GAZIT = (4, 8)
# « לִשְׁכַּת הַגָּזִית כְּמִין בְּסִילְקִי גְדוֹלָה הָיְתָה » (Yoma 25a) : une grande salle, dont aucune
# source ne décrit le décor. Il se prend au Tanakh, pas à l'archéologie hérodienne : ni
# colonne, ni entablement, ni fronton. Les murs sont de gazit, coupés de rangs de poutres,
# « שְׁלֹשָׁה טוּרֵי גָזִית וְטוּר כְּרֻתֹת אֲרָזִים » (Melakhim I 6:36 ; 7:12). La moitié de 'hol est la
# salle de jugement : son sol est de cèdre comme celui de l'« אֻלָם הַמִּשְׁפָּט », « וְסָפוּן בָּאֶרֶז
# מֵהַקַּרְקַע עַד הַקַּרְקָע » (Melakhim I 7:7), que Rashi et Radak lisent du sol, « מְחֻפֶּה קַרְקַע
# הָרִצְפָּה בַּאֲרָזִים ». Seul le mur derrière le tribunal est revêtu de cèdre, en panneaux cadrés
# dont les traverses portent les « פְּקָעִים וּפְטוּרֵי צִצִּים » du Bayit (Melakhim I 6:18). Ces
# emprunts sont des analogies : CHOIX, comme les hauteurs des rangs et des traverses.
GAZIT_NUS = {"O": GAZIT_X0 + LISHKA_PAREMENT, "E": GAZIT_X1 - LISHKA_PAREMENT,
             "S": NORD_Y0 + LISHKA_PAREMENT, "N": NORD_Y1 - LISHKA_PAREMENT}
GAZIT_PLAFOND = Z_AZ + 30 - LISHKA_CORNICHE
# Un rang de poutres de cèdre après trois assises de pierre, deux fois : à mi-hauteur et
# sous le plafond, sur le sud, l'est et l'ouest ; le nord est revêtu.
ASSISES_PAR_RANG = 3
RANGS_CEDRE = (Z_AZ + ASSISES_PAR_RANG * ASSISE, GAZIT_PLAFOND - 1)
# Le revêtement du nord, du sol au plafond : un fond, quatre travées de montants, et des
# traverses qui passent devant eux. Chaque case entre montants et traverses porte un panneau.
LAMBRIS_Y = GAZIT_NUS["N"]
FOND, MONTANT, TRAVERSE, PANNEAU = 0.25, 0.15, 0.22, 0.08    # saillies successives sur le mur
LAMBRIS_X = [GAZIT_NUS["O"] + (GAZIT_NUS["E"] - GAZIT_NUS["O"]) * k / 4 for k in range(5)]
LARGEUR_MONTANT = 0.6
# Traverses : (bas, haut, sculptée). La plus basse est le dossier du dernier gradin, qui vient
# s'y adosser ; la première sculptée passe au-dessus du dossier du Nasi, la deuxième tombe sur
# le rang de cèdre des murs voisins.
GRADINS_H = (0.9, 1.5, 2.1)
DOSSIER_DES_JUGES = Z_AZ + GRADINS_H[-1] + 1.2
TRAVERSES = ((Z_AZ, DOSSIER_DES_JUGES, False), (Z_AZ + 7.0, Z_AZ + 9.0, True),
             (RANGS_CEDRE[0] - 0.5, RANGS_CEDRE[0] + 1.5, True), (Z_AZ + 19.0, Z_AZ + 21.0, True),
             (RANGS_CEDRE[1] - 0.2, GAZIT_PLAFOND, False))
# « חַלּוֹנֵי שְׁקֻפִים אֲטֻמִים » (Melakhim I 6:4), les fenêtres du Bayit, en claire-voie : la salle n'a de
# ciel qu'au nord, sur le 'Heil — à l'est et à l'ouest, Sha'ar HaNitzotz, HaGola et HaEtz la serrent de
# trop près. Le troisième rang de panneaux du lambris s'y ouvre, case pour case, au-dessus du tribunal. CHOIX.
CLAIRE_VOIE = [(xa + LARGEUR_MONTANT / 2 + 0.35, xb - LARGEUR_MONTANT / 2 - 0.35, TRAVERSES[2][1] + 0.35, TRAVERSES[3][0] - 0.35)
               for xa, xb in zip(LAMBRIS_X, LAMBRIS_X[1:])]
lishka("Lishkat_HaGazit", GAZIT_X0, GAZIT_X1, NORD_Y0, NORD_Y1, Z_EZN, Z_AZ + 30, "80_Lishkot",
       [Porte("S", *PORTE_SHAAR, Z_AZ),
        Porte("E", *PETAH_HOL_GAZIT, Z_AZ, centre=AY1 + T + PETAH_HOL_GAZIT[0] / 2)],
       fenetres={"N": CLAIRE_VOIE})
maake("Lishkat_HaGazit", GAZIT_X0, GAZIT_X1, NORD_Y0, NORD_Y1, Z_AZ + 30, "80_Lishkot")
box("Lishkat_HaGazit_sol_hol", GAZIT_X0 + LISHKA_PAREMENT, GAZIT_X1 - LISHKA_PAREMENT, AY1 + T,
    NORD_Y1 - LISHKA_PAREMENT, Z_EZN, Z_AZ, "80_Lishkot", MAT_SOL())
# « וְרָאשֵׁי פִסְפָּסִין מַבְדִּילִין בֵּין קֹדֶשׁ לַחֹל » est dit du Beit HaMoked (Middot 1:6) ; la même
# limite tracée ici, sur l'axe du mur, est une analogie : CHOIX.
box("Lishkat_HaGazit_rashei_pispasin", GAZIT_X0 + LISHKA_PAREMENT, GAZIT_X1 - LISHKA_PAREMENT,
    AXE_MUR_N - 0.1, AXE_MUR_N + 0.1, Z_AZ, Z_AZ + 0.03, "80_Lishkot", MAT_MARBRE())
GAZIT_PORTE_S = ((GAZIT_X0 + GAZIT_X1 - PORTE_SHAAR[0]) / 2, (GAZIT_X0 + GAZIT_X1 + PORTE_SHAAR[0]) / 2)
GAZIT_PORTE_E = (AY1 + T, AY1 + T + PETAH_HOL_GAZIT[0])
SOL_CEDRE = 0.04

for n, z in enumerate(RANGS_CEDRE):
    for face, bornes, cotes, mitres, reserve in (
            ("S", (GAZIT_NUS["O"], GAZIT_NUS["E"], GAZIT_NUS["S"], GAZIT_NUS["S"]), (False, True),
             ("libre", "libre"), [GAZIT_PORTE_S] if z < Z_AZ + PORTE_SHAAR[1] else []),
            ("O", (GAZIT_NUS["O"], GAZIT_NUS["O"], GAZIT_NUS["S"], GAZIT_NUS["N"]), (False, True), ("bute", "libre"), []),
            ("E", (GAZIT_NUS["E"], GAZIT_NUS["E"], GAZIT_NUS["S"], GAZIT_NUS["N"]), (True, False), ("bute", "libre"), [])):
        moulure(f"Lishkat_HaGazit_keroutot_{n}_{face}", *bornes, z, ((0.0, 1.0, 1.0),), "80_Lishkot",
                MAT_CEDRE(), saillie=0.3, mitres=mitres, cotes=cotes, reserve=reserve)

box("Lishkat_HaGazit_sol_cedre", GAZIT_NUS["O"], GAZIT_NUS["E"], AXE_MUR_N + 0.1, GAZIT_NUS["N"],
    Z_AZ, Z_AZ + SOL_CEDRE, "80_Lishkot", MAT_CEDRE_LAMBRIS())

paroi_percee("Lishkat_HaGazit_lambris_fond", GAZIT_NUS["O"], GAZIT_NUS["E"], LAMBRIS_Y - FOND, LAMBRIS_Y,
             Z_AZ, GAZIT_PLAFOND, "80_Lishkot", MAT_CEDRE_LAMBRIS(), CLAIRE_VOIE)
for k, x in enumerate(LAMBRIS_X):
    x0 = min(max(x - LARGEUR_MONTANT / 2, GAZIT_NUS["O"]), GAZIT_NUS["E"] - LARGEUR_MONTANT)
    box(f"Lishkat_HaGazit_lambris_montant_{k}", x0, x0 + LARGEUR_MONTANT,
        LAMBRIS_Y - FOND - MONTANT, LAMBRIS_Y - FOND, Z_AZ, GAZIT_PLAFOND, "80_Lishkot", MAT_CEDRE_LAMBRIS())
NU_TRAVERSE = LAMBRIS_Y - FOND - MONTANT - TRAVERSE
FLEUR_R, FLEUR_PAS, PEKA_R, PEKA_PAS = 0.42, 1.3, 0.16, 0.55
for k, (z0, z1, sculptee) in enumerate(TRAVERSES):
    box(f"Lishkat_HaGazit_lambris_traverse_{k}", GAZIT_NUS["O"], GAZIT_NUS["E"], NU_TRAVERSE,
        LAMBRIS_Y - FOND - MONTANT, z0, z1, "80_Lishkot", MAT_CEDRE_LAMBRIS())
    if not sculptee:
        continue
    paroi, milieu = ("x", NU_TRAVERSE, -1), (z0 + z1) / 2
    u0, u1 = GAZIT_NUS["O"] + 0.4, GAZIT_NUS["E"] - 0.4
    fleurs = round((u1 - u0) / FLEUR_PAS)
    for i in range(fleurs):
        petur_tzitz(f"Lishkat_HaGazit_lambris_traverse_{k}_fleur_{i:02d}", paroi,
                    u0 + (u1 - u0) * (i + 0.5) / fleurs, milieu, FLEUR_R, "80_Lishkot", MAT_CEDRE_LAMBRIS())
    pekaim = int((u1 - u0) / PEKA_PAS)
    for rang, zp in enumerate((z0 + 0.3, z1 - 0.3)):
        for i in range(pekaim):
            sphere(f"Lishkat_HaGazit_lambris_traverse_{k}_peka_{rang}_{i:02d}",
                   u0 + (u1 - u0) * (i + 0.5) / pekaim, NU_TRAVERSE + 0.04, zp, PEKA_R,
                   "80_Lishkot", MAT_CEDRE_LAMBRIS(), segs=8)
# Les panneaux : un par case, en retrait des montants et des traverses qui les cadrent, sauf au rang de la claire-voie.
for j, ((_, bas, _), (haut, _, _)) in enumerate(zip(TRAVERSES, TRAVERSES[1:])):
    for k, (xa, xb) in enumerate(zip(LAMBRIS_X, LAMBRIS_X[1:]) if j != 2 else ()):
        box(f"Lishkat_HaGazit_lambris_panneau_{j}{k}", xa + LARGEUR_MONTANT / 2 + 0.35, xb - LARGEUR_MONTANT / 2 - 0.35,
            LAMBRIS_Y - FOND - PANNEAU, LAMBRIS_Y - FOND, bas + 0.35, haut - 0.35, "80_Lishkot", MAT_CEDRE_LAMBRIS())

# « וַיִּסְפֹּן אֶת הַבַּיִת גֵּבִים וּשְׂדֵרֹת בָּאֲרָזִים » (Melakhim I 6:9) : poutres et planches de cèdre.
PLAFOND_POUTRES = 5
box("Lishkat_HaGazit_plafond_planches", GAZIT_NUS["O"], GAZIT_NUS["E"], GAZIT_NUS["S"], GAZIT_NUS["N"],
    GAZIT_PLAFOND - 0.15, GAZIT_PLAFOND, "80_Lishkot", MAT_CEDRE_LAMBRIS())
for k in range(PLAFOND_POUTRES):
    y = GAZIT_NUS["S"] + (GAZIT_NUS["N"] - GAZIT_NUS["S"]) * (k + 1) / (PLAFOND_POUTRES + 1)
    box(f"Lishkat_HaGazit_plafond_poutre_{k}", GAZIT_NUS["O"] + 0.3, GAZIT_NUS["E"] - 0.3,
        y - 0.45, y + 0.45, GAZIT_PLAFOND - 1.4, GAZIT_PLAFOND - 0.15, "80_Lishkot", MAT_CEDRE())

# « וּבַחֵצִי שֶׁל חֹל הָיוּ הַסַּנְהֶדְרִין יוֹשְׁבִין » (Rambam, Beit HaBe'hira 5:17) — « אֵין יְשִׁיבָה בָּעֲזָרָה
# אֶלָּא לְמַלְכֵי בֵית דָּוִד » (Yoma 25a) : tout ce qui s'assied est au nord de la limite.
# « כַּחֲצִי גֹרֶן עֲגֻלָּה, כְּדֵי שֶׁיְּהוּ רוֹאִין זֶה אֶת זֶה » (Sanhedrin 4:3) : trois gradins en
# demi-cercle, ouvert vers le sud. Son diamètre passe au nord du פתח de 'hol, pour que les
# pointes de l'arc ne le bouchent pas. Entre l'arc et la limite, ceux qui sont « לִפְנֵיהֶם ».
# La salle, vingt amot, tient la disposition, pas le nombre : ni soixante et onze juges ni
# trois rangs d'élèves n'y ont chacun leur place. Des tablettes de marbre, comme les
# « שֻׁלְחָנוֹת… שֶׁל שַׁיִשׁ » du Mikdash (Shekalim 6:4). Gradins, rayons, rangs : CHOIX.
SANHEDRIN_X = (GAZIT_X0 + GAZIT_X1) / 2
SANHEDRIN_Y = AY1 + T + PETAH_HOL_GAZIT[0] + 0.5
SANHEDRIN_R0 = 2.2
ARC_PAS = math.pi / 48
PLAT = 0.12                    # épaisseur des tablettes de marbre
NEZ = 0.08                     # ce que la tablette déborde vers le centre
MARGELLE = 0.6                 # le marbre au bord du dernier gradin, devant le cèdre
# Le tribunal est bâti dans la salle, pas posé dedans : le dernier gradin court jusqu'aux murs,
# le dos à la traverse basse du lambris, qui lui sert de dossier. L'estrade du Nasi est ce même
# dernier gradin, avancé au milieu de l'arc, et on y monte par les deux premiers, resserrés.
TRIBUNAL_NORD = NU_TRAVERSE
ESTRADE = (math.radians(45), math.radians(135))
MARCHES_ESTRADE = ((SANHEDRIN_R0 - 0.5, SANHEDRIN_R0, 0.45), (SANHEDRIN_R0, SANHEDRIN_R0 + 0.5, GRADINS_H[0]),
                   (SANHEDRIN_R0 + 0.5, SANHEDRIN_R0 + 1.0, GRADINS_H[1]))
ESTRADE_R0 = SANHEDRIN_R0 + 1.0


def gazit_point(r, angle, t=0.0):
    """Point à `r` du centre de l'arc dans la direction `angle`, décalé de `t` en travers."""
    return (SANHEDRIN_X + r * math.cos(angle) - t * math.sin(angle),
            SANHEDRIN_Y + r * math.sin(angle) + t * math.cos(angle))


def gazit_nu(angle):
    """Distance du centre de l'arc au nu de la salle dans la direction `angle` : le lambris au nord, la pierre à l'est et à l'ouest."""
    dx, dy = math.cos(angle), math.sin(angle)
    portees = [(TRIBUNAL_NORD - SANHEDRIN_Y) / dy] if dy > 1e-9 else []
    if abs(dx) > 1e-9:
        portees.append((GAZIT_NUS["E" if dx > 0 else "O"] - SANHEDRIN_X) / dx)
    return min(portees)


def gazit_angles(a0, a1):
    """Les angles du secteur au pas de l'arc, et ceux des coins de la salle qui y tombent."""
    coins = (math.atan2(TRIBUNAL_NORD - SANHEDRIN_Y, GAZIT_NUS[c] - SANHEDRIN_X) for c in "EO")
    n = max(1, round((a1 - a0) / ARC_PAS))
    return sorted({a0 + (a1 - a0) * i / n for i in range(n + 1)} | {a for a in coins if a0 < a < a1})


def couronne(name, r0, r1, secteur, z0, z1, mat=None):
    """Le secteur de couronne entre les rayons `r0` et `r1`, d'un seul tenant ; `r1` à None, il
    court jusqu'aux murs. Posé en tronçons, l'arc cuisait une lumière par tronçon et se lisait en
    dalles dépareillées."""
    angles = gazit_angles(*secteur)
    n = len(angles)
    dedans = [gazit_point(r0, a) for a in angles]
    dehors = [gazit_point(gazit_nu(a) if r1 is None else r1, a) for a in angles]
    verts = [(x, y, z) for z in (z0, z1) for x, y in dedans + dehors]
    ib, ob, it, ot = 0, n, 2 * n, 3 * n
    faces = [[ob, ot, it, ib], [ib + n - 1, it + n - 1, ot + n - 1, ob + n - 1]]
    for i in range(n - 1):
        j = i + 1
        faces += [[it + i, ot + i, ot + j, it + j], [ib + j, ob + j, ob + i, ib + i],
                  [ib + j, ib + i, it + i, it + j], [ob + i, ob + j, ot + j, ot + i]]
    return mesh_from_pydata(name, verts, faces, "80_Lishkot", mat)


def gradin(name, r0, r1, secteur, h):
    """Corps de pierre et tablette de marbre, dont le nez déborde vers le centre."""
    couronne(f"{name}_corps", r0, r1, secteur, Z_AZ, Z_AZ + h - PLAT)
    couronne(f"{name}_tablette", r0 - NEZ, r1, secteur, Z_AZ + h - PLAT, Z_AZ + h, MAT_MARBRE())


def plateau(name, r0, secteur, h):
    """Le dernier gradin, jusqu'aux murs : le marbre n'en borde que le nez, et derrière lui le
    plancher de cèdre de la salle remonte à ce niveau — tout de marbre, il se lisait en scène."""
    couronne(f"{name}_corps", r0, None, secteur, Z_AZ, Z_AZ + h - PLAT)
    couronne(f"{name}_tablette", r0 - NEZ, r0 + MARGELLE, secteur, Z_AZ + h - PLAT, Z_AZ + h, MAT_MARBRE())
    couronne(f"{name}_plancher", r0 + MARGELLE, None, secteur, Z_AZ + h - PLAT, Z_AZ + h, MAT_CEDRE_LAMBRIS())


RAYONS = [SANHEDRIN_R0 + rang for rang in range(len(GRADINS_H))]
for cote, secteur in (("E", (0.0, ESTRADE[0])), ("O", (ESTRADE[1], math.pi))):
    for rang, h in enumerate(GRADINS_H[:-1]):
        gradin(f"Lishkat_HaGazit_sanhedrin_{rang}_{cote}", RAYONS[rang], RAYONS[rang + 1], secteur, h)
    plateau(f"Lishkat_HaGazit_sanhedrin_{len(RAYONS) - 1}_{cote}", RAYONS[-1], secteur, GRADINS_H[-1])
plateau("Lishkat_HaGazit_estrade", ESTRADE_R0, ESTRADE, GRADINS_H[-1])
for marche, (r0, r1, h) in enumerate(MARCHES_ESTRADE):
    gradin(f"Lishkat_HaGazit_estrade_marche_{marche}", r0, r1, ESTRADE, h)
# Les pointes de l'arc se ferment sur des joues de pierre chaperonnées de marbre, qui suivent
# les gradins en escalier jusqu'au mur.
for cote, angle in (("E", 0.0), ("O", math.pi)):
    marches = [(RAYONS[rang] - 0.15 * (rang == 0), RAYONS[rang + 1] if rang + 1 < len(RAYONS) else gazit_nu(angle),
                h + 0.3) for rang, h in enumerate(GRADINS_H)]
    for rang, (r0, r1, h) in enumerate(marches):
        (xa, _), (xb, _) = gazit_point(r0, angle), gazit_point(r1, angle)
        nom = f"Lishkat_HaGazit_joue_{cote}_{rang}"
        box(nom, min(xa, xb), max(xa, xb), SANHEDRIN_Y - 0.25, SANHEDRIN_Y, Z_AZ, Z_AZ + h - PLAT, "80_Lishkot")
        box(f"{nom}_chaperon", min(xa, xb), max(xa, xb), SANHEDRIN_Y - 0.25, SANHEDRIN_Y, Z_AZ + h - PLAT, Z_AZ + h,
            "80_Lishkot", MAT_MARBRE())
# « כַּחֲצִי גֹרֶן עֲגֻלָּה » : l'aire que l'arc enferme, marquée sur le cèdre d'un demi-disque de marbre
# cerclé de bronze, là où se tiennent les parties devant le tribunal. CHOIX.
GOREN_R = SANHEDRIN_R0 - 0.9
GOREN_Z = Z_AZ + SOL_CEDRE
prism("Lishkat_HaGazit_goren", [gazit_point(GOREN_R, math.pi * i / 16) for i in range(17)],
      GOREN_Z, GOREN_Z + 0.02, "80_Lishkot", MAT_MARBRE())
for k in range(8):
    a0, a1 = math.pi * k / 8, math.pi * (k + 1) / 8
    prism(f"Lishkat_HaGazit_goren_cercle_{k}",
          [gazit_point(GOREN_R, a0), gazit_point(GOREN_R + 0.12, a0),
           gazit_point(GOREN_R + 0.12, a1), gazit_point(GOREN_R, a1)],
          GOREN_Z, GOREN_Z + 0.025, "80_Lishkot", MAT_BRONZE())


class Siege(NamedTuple):
    """Siège tourné vers le centre de l'arc. `r` : rayon du devant de l'assise ; `demi` :
    demi-largeur ; `sol` : la cote où il pose ; `dossier` : hauteur du dossier au-dessus du
    sol ; `matiere` : ce dont il est fait ou plaqué."""
    r: float
    demi: float
    sol: float
    dossier: float
    matiere: bpy.types.Material


def pave(name, angle, bornes, mat):
    """Pavé orienté sur l'arc : `bornes` = (r0, r1, t0, t1, z0, z1), r le long du rayon."""
    r0, r1, t0, t1, z0, z1 = bornes
    prism(name, [gazit_point(r0, angle, t0), gazit_point(r1, angle, t0),
                 gazit_point(r1, angle, t1), gazit_point(r0, angle, t1)], z0, z1, "80_Lishkot", mat)


def dossier_arrondi(name, angle, bornes, mat):
    """Dossier debout de `r0` à `r1`, large de deux `demi`, de `z0` à `z1`, sommé d'un demi-cercle.
    `bornes` = (r0, r1, demi, z0, z1). Profil tracé en sens direct dans le plan (travers, z)."""
    r0, r1, d, z0, z1 = bornes
    zc = z1 - d
    profil = [(-d, z0), (d, z0)] + [(d * math.cos(math.pi * i / 12), zc + d * math.sin(math.pi * i / 12))
                                    for i in range(13)]
    n = len(profil)
    avant = [(*gazit_point(r0, angle, t), z) for t, z in profil]
    arriere = [(*gazit_point(r1, angle, t), z) for t, z in profil]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    return mesh_from_pydata(name, avant + arriere, faces, "80_Lishkot", mat)


def kisse(name, angle, siege):
    """Sur le trône de Shlomo : « וְרֹאשׁ עָגֹל לַכִּסֵּה מֵאַחֲרָיו וְיָדֹת מִזֶּה וּמִזֶּה אֶל מְקוֹם הַשָּׁבֶת »
    (Melakhim I 10:19), des accoudoirs « כְּמִין מַקְלוֹת… לִסְמוֹךְ זְרוֹעוֹתָיו » (Rashi sur Divrei
    HaYamim II 9:18). Sans les lions : ce sont des figures, et c'est le trône d'un roi."""
    r0, d, z, h, mat = siege.r, siege.demi, siege.sol, siege.dossier, siege.matiere
    r1 = r0 + 1.1
    pave(f"{name}_assise", angle, (r0, r1, -d, d, z, z + 1.0), mat)
    dossier_arrondi(f"{name}_dossier", angle, (r1, r1 + 0.3, d, z, z + h), mat)
    for cote, s in (("d", 1), ("g", -1)):
        pave(f"{name}_montant_{cote}", angle, (r0 + 0.05, r0 + 0.25, *sorted((s * (d - 0.2), s * d)),
             z + 1.0, z + 1.75), mat)
        pave(f"{name}_accoudoir_{cote}", angle, (r0, r1, *sorted((s * (d - 0.2), s * d)), z + 1.75, z + 1.9), mat)


# « הַנָּשִׂיא יוֹשֵׁב בָּאֶמְצַע וּזְקֵנִים יוֹשְׁבִים מִימִינוֹ וּשְׂמֹאלוֹ » (Tosefta Sanhedrin 8:1) : le Nasi
# sur l'estrade, son siège plaqué d'or comme celui de Shlomo, « וַיְצַפֵּהוּ זָהָב מוּפָז » (Melakhim I
# 10:18). L'Av Beit Din « יוֹשֵׁב מִימִינוֹ » (Rambam, Sanhedrin 1:3), au même niveau, sur
# l'estrade, le même siège en marbre. Le Nasi regarde le sud : sa droite est à l'ouest,
# l'angle qui croît. Les deux dossiers à un dixième d'ama du lambris. Estrade, formes et matières : CHOIX.
SIEGE_R = gazit_nu(math.pi / 2) - 1.5
kisse("Lishkat_HaGazit_kisse_nasi", math.pi / 2, Siege(SIEGE_R, 0.85, Z_AZ + GRADINS_H[-1], 4.6, MAT_OR_PLAQUE()))
kisse("Lishkat_HaGazit_kisse_av_beit_din", math.radians(122),
      Siege(SIEGE_R, 0.7, Z_AZ + GRADINS_H[-1], 3.4, MAT_MARBRE()))

# « וּשְׁנֵי סוֹפְרֵי הַדַּיָּנִין עוֹמְדִין לִפְנֵיהֶם, אֶחָד מִיָּמִין וְאֶחָד מִשְּׂמֹאל » (Sanhedrin 4:3) :
# debout, donc un pupitre chacun, au pied des deux pointes de l'arc. Pupitre tourné : CHOIX.
PIED_DE_PUPITRE = ((0.35, 0.0), (0.35, 0.12), (0.22, 0.22), (0.12, 0.35), (0.09, 1.25), (0.15, 1.4),
                   (0.09, 1.55), (0.09, 1.95), (0.22, 2.08), (0.22, 2.2), (0.0, 2.2))
SOFRIM_Y = SANHEDRIN_Y - 1.4
for cote, x in (("O", SANHEDRIN_X - SANHEDRIN_R0 - 2.6), ("E", SANHEDRIN_X + SANHEDRIN_R0 + 2.6)):
    nom = f"Lishkat_HaGazit_sofer_{cote}"
    revolution(f"{nom}_pied", x, SOFRIM_Y, Z_AZ, PIED_DE_PUPITRE, "80_Lishkot", MAT_CEDRE(), verts=16)
    plaque(f"{nom}_pupitre",
           [(x - 0.5, SOFRIM_Y - 0.35, Z_AZ + 2.05), (x + 0.5, SOFRIM_Y - 0.35, Z_AZ + 2.05),
            (x + 0.5, SOFRIM_Y + 0.35, Z_AZ + 2.35), (x - 0.5, SOFRIM_Y + 0.35, Z_AZ + 2.35)],
           0.06, "80_Lishkot", MAT_CEDRE())
    box(f"{nom}_rebord", x - 0.5, x + 0.5, SOFRIM_Y - 0.41, SOFRIM_Y - 0.35, Z_AZ + 2.02, Z_AZ + 2.16,
        "80_Lishkot", MAT_CEDRE())
# « וְשָׁלֹשׁ שׁוּרוֹת שֶׁל תַּלְמִידֵי חֲכָמִים יוֹשְׁבִין לִפְנֵיהֶם » (Sanhedrin 4:4), « גְּדוֹלִים בָּרִאשׁוֹנָה »
# (Tosefta Sanhedrin 8:1) : trois bancs de marbre face aux juges, le premier le plus près d'eux.
# Ils laissent à l'est un passage le long du mur, devant le פתח.
for rang in range(3):
    y1 = SOFRIM_Y - 1.0 - 1.5 * rang
    nom = f"Lishkat_HaGazit_talmidim_{rang}"
    for k, x in enumerate((SANHEDRIN_X - 3.8, SANHEDRIN_X - 0.3, SANHEDRIN_X + 3.2)):
        box(f"{nom}_pied_{k}", x, x + 0.6, y1 - 0.7, y1 - 0.1, Z_AZ, Z_AZ + 0.68, "80_Lishkot")
    box(f"{nom}_assise", SANHEDRIN_X - 4, SANHEDRIN_X + 4, y1 - 0.8, y1, Z_AZ + 0.68, Z_AZ + 0.85,
        "80_Lishkot", MAT_MARBRE())
# Le jour de la claire-voie ne descend pas jusqu'aux juges : deux lampes de terre sur chaque mur de
# pierre, l'une au-dessus du tribunal, l'autre au milieu de la salle, à hauteur de main levée. Leur
# lueur est une lampe de la scène, que la visite allume et dont la cuisson prend le rebond. CHOIX.
LUEURS_Y, LUEURS_Z = (SANHEDRIN_Y + 2.5, GAZIT_NUS["S"] + 5.5), Z_AZ + 6
for cote, x, normale in (("E", GAZIT_NUS["E"], (-1, 0)), ("O", GAZIT_NUS["O"], (1, 0))):
    for k, y in enumerate(LUEURS_Y):
        nom = f"Lishkat_HaGazit_ner_{cote}{k}"
        ner_sur_tablette(nom, x, y, normale, LUEURS_Z, "80_Lishkot")
        lueur = lampe(f"Lishkat_HaGazit_lueur_{cote}{k}", 'POINT', (m(x + normale[0] * 0.2), m(y), m(LUEURS_Z + 0.35)))
        lueur.data.energy = 50.0
        lueur.data.color = (1.0, 0.85, 0.63)
        lueur.data.shadow_soft_size = m(0.1)
# La boîte que ces lueurs éclairent dans la visite, faces intérieures des murs comprises.
salle = empty("Lishkat_HaGazit_salle", (GAZIT_NUS["O"] + GAZIT_NUS["E"]) / 2, (GAZIT_NUS["S"] + GAZIT_NUS["N"]) / 2,
              (Z_AZ + GAZIT_PLAFOND) / 2, "80_Lishkot")
salle.empty_display_type = 'CUBE'
salle.empty_display_size = 1.0
salle.scale = (m((GAZIT_NUS["E"] - GAZIT_NUS["O"]) / 2 + 0.3), m((GAZIT_NUS["N"] - GAZIT_NUS["S"]) / 2 + 0.3),
               m((GAZIT_PLAFOND - Z_AZ) / 2 + 0.3))
# Lishkat HaGola : « שָׁם הָיָה בוֹר קָבוּעַ, וְהַגַּלְגַּל נָתוּן עָלָיו, וּמִשָּׁם מַסְפִּיקִים מַיִם
# לְכָל הָעֲזָרָה » (Middot 5:4). Elle alimente la cour et s'ouvre dessus : DANS l'Azara,
# contre la face intérieure du mur nord, comme les trois du sud — « שֵׁשׁ לְשָׁכוֹת הָיוּ
# בָעֲזָרָה » (Middot 5:3), et Tosfot Yom Tov (5:4) la met au sud de HaEtz, côté cour.
# Porte au sud, sur la cour (PORTE_LISHKA, CHOIX). Derrière le Kodesh HaKodashim, la bande
# entre le mur et le Bâtiment n'est pas le « nord » de l'abattage, qui s'arrête au mur de
# l'Oulam (Rambam, Beit HaBe'hira 5:15) : dix amot de profondeur n'y gênent rien.
lishka("Lishkat_HaGola", GOLA_X0, GOLA_X1, *NORD_INT, Z_AZ, Z_AZ + 30, "80_Lishkot",
       [Porte("S", *PORTE_LISHKA, Z_AZ)], adossee="N")
maake("Lishkat_HaGola", GOLA_X0, GOLA_X1, *NORD_INT, Z_AZ + 30, "80_Lishkot")
# Le בּוֹר au milieu du sol, creusé dans le dallage et le podium (VIDES_SOUS_AZARA), et le
# גַּלְגַּל posé dessus : margelle, potence et roue sur le modèle du mukhni du Kiyor, formes CHOIX.
BOR_X, BOR_Y = (GOLA_X0 + GOLA_X1) / 2, (NORD_INT[0] + LISHKA_PAREMENT + NORD_INT[1]) / 2
BOR = (BOR_X - 1.5, BOR_X + 1.5, BOR_Y - 1.5, BOR_Y + 1.5)
cyl("Lishkat_HaGola_bor_eau", BOR_X, BOR_Y, Z_EZN, Z_EZN + 2, 1.5, "80_Lishkot", MAT_EAU(), verts=24)
revolution("Lishkat_HaGola_bor_margelle", BOR_X, BOR_Y, Z_AZ,
           [(2.4, 0.0), (2.4, 1.1), (2.2, 1.3), (1.4, 1.3), (1.2, 1.1), (1.2, -0.3)],
           "80_Lishkot", verts=24, capots=False)
GALGAL_Z = Z_AZ + 4.6
for s in (-1, 1):
    cyl(f"Lishkat_HaGola_galgal_poteau_{s:+d}", BOR_X, BOR_Y + s * 2.8, Z_AZ, GALGAL_Z + 0.4, 0.22,
        "80_Lishkot", MAT_CEDRE(), verts=12)
cyl_between("Lishkat_HaGola_galgal_essieu", (BOR_X, BOR_Y - 2.8, GALGAL_Z), (BOR_X, BOR_Y + 2.8, GALGAL_Z),
            0.07, "80_Lishkot", MAT_FER(), verts=8)
tore("Lishkat_HaGola_galgal", BOR_X, BOR_Y, GALGAL_Z, 0.9, 0.1, "80_Lishkot", MAT_CEDRE(),
     rotation=(math.pi / 2, 0, 0))
for k in range(6):
    a = math.pi * k / 6
    cyl_between(f"Lishkat_HaGola_galgal_rayon_{k}",
                (BOR_X + 0.85 * math.cos(a), BOR_Y, GALGAL_Z + 0.85 * math.sin(a)),
                (BOR_X - 0.85 * math.cos(a), BOR_Y, GALGAL_Z - 0.85 * math.sin(a)),
                0.04, "80_Lishkot", MAT_CEDRE(), verts=6)
cyl_between("Lishkat_HaGola_galgal_corde", (BOR_X + 0.9, BOR_Y, GALGAL_Z), (BOR_X + 0.9, BOR_Y, Z_EZN + 2.5),
            0.04, "80_Lishkot", MAT_CHENE(), verts=6)
# « וּמְמַלְּאִים מִבּוֹר הַגּוֹלָה… בַּגַּלְגַּל בְּשַׁבָּת » (Erouvin 10:14) ; son eau est « מַיִם מְתוּקִים לִשְׁתִיָּה »,
# l'amma servant au rinçage (R. Shemaya sur Middot 5:4). Le seau posé sur la margelle, l'auge où on le
# vide, les cruches qu'on y remplit pour la cour. Seau, auge, cruches : CHOIX.
revolution("Lishkat_HaGola_dli", BOR_X - 1.7, BOR_Y, Z_AZ + 1.3,
           [(0.0, 0.0), (0.3, 0.0), (0.36, 0.6), (0.32, 0.6), (0.26, 0.05), (0.0, 0.05)],
           "80_Lishkot", MAT_CHENE(), verts=16)
GL_X0, GL_Y0, GL_Y1 = GOLA_X0 + LISHKA_PAREMENT, NORD_INT[0] + LISHKA_PAREMENT, NORD_INT[1]
SHOKET = (GL_X0 + 0.25, GL_X0 + 1.15, GL_Y0 + 1.75, GL_Y1 - 1.75)
dalle_trouee("Lishkat_HaGola_shoket", GL_X0, GL_X0 + 1.4, GL_Y0 + 1.5, GL_Y1 - 1.5, Z_AZ, Z_AZ + 1.3,
             SHOKET, "80_Lishkot")
box("Lishkat_HaGola_shoket_mayim", *SHOKET, Z_AZ, Z_AZ + 1.1, "80_Lishkot", MAT_EAU())
for k in range(4):
    revolution(f"Lishkat_HaGola_kad_{k}", GL_X0 + 2.2, GL_Y0 + 2 + 1.6 * k, Z_AZ,
               [(0.0, 0.0), (0.22, 0.0), (0.35, 0.4), (0.3, 0.75), (0.12, 0.95), (0.15, 1.02), (0.0, 1.0)],
               "80_Lishkot", MAT_TERRE_CUITE(), verts=14)
# Lishkat HaEtz, « וְהִיא הָיְתָה אֲחוֹרֵי שְׁתֵּיהֶן » (Middot 5:4) : derrière HaGola, dos au nord,
# à l'ouest de HaGazit — la face est à l'est, l'arrière au nord (Tosfot Yom Tov ibid.).
# Elle est donc de l'autre côté du mur, sur la terrasse du 'Heil, entière dans le 'hol : la
# Mishna ne le dit pas d'elle (« שֵׁשׁ לְשָׁכוֹת הָיוּ בָעֲזָרָה », 5:3), et l'écart est écrit
# ici — derrière HaGola, il n'y a que le mur. R. Eliezer ben Yaakov : « שָׁכַחְתִּי מֶה הָיְתָה
# מְשַׁמֶּשֶׁת » — sans usage connu, pas d'ouverture connue non plus ; CHOIX, une porte sur le
# 'Heil. Même toit que HaGola et HaGazit, le mur de 25 passant sous les 30 des trois.
lishka("Lishkat_HaEtz", GOLA_X0, GOLA_X1, AY1 + T, NORD_Y1,
       Z_EZN, Z_AZ + 30, "80_Lishkot", [Porte("N", *PORTE_LISHKA, Z_EZN)], adossee="S")
maake("Lishkat_HaEtz", GOLA_X0, GOLA_X1, AY1 + T, NORD_Y1, Z_AZ + 30, "80_Lishkot")

# Sha'ar HaNitzotz, la porte nord la plus occidentale — le seul corps de porte que la
# Mishna décrive en entier : « וּכְמִין אַכְסַדְרָה הָיָה, וַעֲלִיָּה בְנוּיָה עַל גַּבָּיו,
# שֶׁהַכֹּהֲנִים שׁוֹמְרִים מִלְמַעְלָן וְהַלְוִיִּם מִלְּמַטָּן, וּפֶתַח הָיָה לוֹ לַחֵיל »
# (Middot 1:5). Le Beit HaNitzotz est l'un des trois postes de garde des Cohanim
# (Middot 1:1 ; Tamid 1:1), et son aliyah regarde l'Azara.
NZ_X0, NZ_X1 = PORTE_NITZOTZ - 10, PORTE_NITZOTZ + 10
NZ_Y0, NZ_Y1, NZ_Z0 = AY1 + T, NORD_Y1, Z_AZ + 25
# La porte de l'Azara est au niveau de la cour, celle du 'Heil dix amot plus bas : le corps
# de porte est une cage d'escalier, ses vingt degrés sur ce que la mesiba lui laisse.
NZ_VIS = puits_de_mesiba(NZ_X1 - LISHKA_PAREMENT, NZ_Y0, NZ_Y1 - LISHKA_PAREMENT)
lishka("Beit_ShaarHaNitzotz", NZ_X0, NZ_X1, NZ_Y0, NZ_Y1, Z_EZN, NZ_Z0, "80_Lishkot",
       [Porte("N", *PORTE_SHAAR, Z_EZN)], adossee="S", tremies=[NZ_VIS])
escalier("Beit_ShaarHaNitzotz_escalier", NZ_X0 + LISHKA_PAREMENT, NZ_VIS[0],
         NZ_Y0, NZ_Y1 - LISHKA_PAREMENT, Z_EZN, Z_AZ, "+y", "80_Lishkot")
box("Beit_ShaarHaNitzotz_mesiba_palier", NZ_VIS[0], NZ_VIS[1], NZ_Y0, NZ_Y1 - LISHKA_PAREMENT,
    Z_EZN, Z_AZ, "80_Lishkot", MAT_SOL())
escalier_a_vis("Beit_ShaarHaNitzotz_mesiba", (NZ_VIS[0] + NZ_VIS[1]) / 2, (NZ_VIS[2] + NZ_VIS[3]) / 2,
               MESIBA_PORTE / 2, NZ_Z0 + 1, Z_AZ, 180, "80_Lishkot")
# Les degrés du פתח de 'hol de la Lishkat HaGazit, entre elle et ce corps de porte, à deux
# dixièmes de son socle : jointifs, leurs faces se confondraient.
GAZIT_PALIER_Y = AY1 + T + PETAH_HOL_GAZIT[0]
GAZIT_DEGRES_X1 = NZ_X0 - LISHKA_DEBORD - 0.2
box("Lishkat_HaGazit_palier", GAZIT_X1, GAZIT_DEGRES_X1, AY1 + T, GAZIT_PALIER_Y, Z_EZN, Z_AZ,
    "80_Lishkot", MAT_SOL())
escalier("Lishkat_HaGazit_escalier", GAZIT_X1, GAZIT_DEGRES_X1, GAZIT_PALIER_Y, GAZIT_PALIER_Y + 10,
         Z_EZN, Z_AZ, "+y", "80_Lishkot")
terrasse_de_porte("ShaarHaNitzotz", NZ_X0, NZ_X1, NZ_Y0, NZ_Y1, NZ_Z0,
                  (PORTE_NITZOTZ - 5, PORTE_NITZOTZ + 5), "80_Lishkot", tremies=[NZ_VIS])
# La porte de la chambre est à côté du puits, non en face : en face, elle ouvrirait sur le vide.
aliyah("BeitHaNitzotz", PORTE_NITZOTZ - 5, PORTE_NITZOTZ + 5, NZ_Y0, NZ_Y1, NZ_Z0, 12,
       "80_Lishkot", ("sud", PORTE_NITZOTZ - 1.5, PORTE_NITZOTZ + 1.5),
       ("est", NZ_VIS[3], NZ_VIS[3] + MESIBA_PORTE))

# Beit Avtinas : l'aliyah du corps de porte de Sha'ar HaMayim — la plus ORIENTALE des
# trois portes du sud —, creuse, murs d'une ama, fenêtre 3 x 4 au nord sur l'Azara.
# Source : Yerushalmi Yoma 1:5 (halakha)
# « על גבי שער המים היתה וסמוך ללשכתו היתה » — elle était au-dessus de Sha'ar HaMayim
# et contre sa lishka (celle du Cohen Gadol). Le Bavli Yoma 19a laisse la question
# ouverte (« ולא ידענא ») et sa baraïta situe la première tevila « בחול, על גבי שער
# המים, ובצד לשכתו » ; on suit le Yerushalmi, explicite.
# « על גבי » se prend au mot : la chambre est le haut d'un bâtiment de porte, et il
# fallait le bâtir. Sans lui elle pendait à 38,5 amot au-dessus du dallage, collée à
# la face sud du mur, sans rien dessous — le bloc qui flottait au plan 1. Son rez-de-
# chaussée est la cage d'escalier de la porte, comme à Sha'ar HaNitzotz.
BA_X0, BA_X1 = PORTE_MAYIM - 5, PORTE_MAYIM + 5
BA_Y0, BA_Y1, BA_Z0 = AY0 - T - SAILLIE, AY0 - T, Z_AZ + 25
SM_X0, SM_X1 = PORTE_MAYIM - 10, PORTE_MAYIM + 10
SM_VIS = puits_de_mesiba(SM_X1 - LISHKA_PAREMENT, BA_Y0 + LISHKA_PAREMENT, BA_Y1)
lishka("Beit_ShaarHaMayim", SM_X0, SM_X1, BA_Y0, BA_Y1, Z_EZN, BA_Z0, "80_Lishkot",
       [Porte("S", *PORTE_SHAAR, Z_EZN)], adossee="N", tremies=[SM_VIS])
escalier("Beit_ShaarHaMayim_escalier", SM_X0 + LISHKA_PAREMENT, SM_VIS[0],
         BA_Y0 + LISHKA_PAREMENT, BA_Y1, Z_EZN, Z_AZ, "-y", "80_Lishkot")
box("Beit_ShaarHaMayim_mesiba_palier", SM_VIS[0], SM_VIS[1], BA_Y0 + LISHKA_PAREMENT, BA_Y1,
    Z_EZN, Z_AZ, "80_Lishkot", MAT_SOL())
escalier_a_vis("Beit_ShaarHaMayim_mesiba", (SM_VIS[0] + SM_VIS[1]) / 2, (SM_VIS[2] + SM_VIS[3]) / 2,
               MESIBA_PORTE / 2, BA_Z0 + 1, Z_AZ, 180, "80_Lishkot")
# La baie déborde sur l'Ezrat Israël : sous le mur, le podium laisserait un trou au pied des degrés.
box("Beit_ShaarHaMayim_seuil", X_DOUKHAN, PORTE_MAYIM + 5, AY0 - T, AY0, Z_EZI - 1, Z_AZ,
    "80_Lishkot", MAT_SOL())
terrasse_de_porte("ShaarHaMayim", SM_X0, SM_X1, BA_Y0, BA_Y1, BA_Z0,
                  (BA_X0, BA_X1), "80_Lishkot", tremies=[SM_VIS])
aliyah("BeitAvtinas", BA_X0, BA_X1, BA_Y0, BA_Y1, BA_Z0, 12,
       "80_Lishkot", ("nord", PORTE_MAYIM - 1.5, PORTE_MAYIM + 1.5),
       ("est", SM_VIS[2] - MESIBA_PORTE, SM_VIS[2]))
# « היו מחזירין אותה למכתשת… וכשהוא שוחק אומר הדק היטב » (Keritot 6b), « מכתשת של בית אבטינס »
# (Avot deRabbi Natan 41:12) ; les sammanim pesés « במשקל מכוון », chacun pilé à part (Rambam
# Klei HaMikdash 2:2, 2:5). Table, balance, bols, formes et matières : CHOIX.
AV_X0, AV_X1, AV_Y0, AV_Z = BA_X0 + 1, BA_X1 - 1, BA_Y0 + 1, BA_Z0 + 1
box("BeitAvtinas_table", AV_X0 + 0.2, AV_X0 + 2.2, AV_Y0 + 2, AV_Y0 + 8, AV_Z, AV_Z + 1.5,
    "80_Lishkot", MAT_MARBRE())
for k in range(11):
    x, y = AV_X0 + 0.7, AV_Y0 + 2.5 + 0.5 * k
    revolution(f"BeitAvtinas_sam_{k:02d}", x, y, AV_Z + 1.5,
               [(0.0, 0.0), (0.16, 0.0), (0.21, 0.2), (0.17, 0.2), (0.0, 0.07)],
               "80_Lishkot", MAT_TERRE_CUITE(), verts=16)
    cone(f"BeitAvtinas_sam_{k:02d}_poudre", x, y, AV_Z + 1.64, AV_Z + 1.78, 0.12, 0.03,
         "80_Lishkot", MAT_KETORET(), verts=16)
BAL_X, BAL_Y, BAL_Z = AV_X0 + 1.6, AV_Y0 + 7, AV_Z + 2.8
cyl("BeitAvtinas_moznayim_pied", BAL_X, BAL_Y, AV_Z + 1.5, BAL_Z, 0.05, "80_Lishkot",
    MAT_BRONZE(), verts=12)
cyl_between("BeitAvtinas_moznayim_fleau", (BAL_X, BAL_Y - 0.6, BAL_Z), (BAL_X, BAL_Y + 0.6, BAL_Z),
            0.03, "80_Lishkot", MAT_BRONZE(), verts=8)
for s in (-1, 1):
    y = BAL_Y + 0.6 * s
    cyl_between(f"BeitAvtinas_moznayim_corde_{s:+d}", (BAL_X, y, BAL_Z), (BAL_X, y, BAL_Z - 0.85),
                0.01, "80_Lishkot", MAT_BRONZE(), verts=6)
    revolution(f"BeitAvtinas_moznayim_plateau_{s:+d}", BAL_X, y, BAL_Z - 0.95,
               [(0.0, 0.0), (0.3, 0.1), (0.26, 0.1), (0.0, 0.03)], "80_Lishkot", MAT_BRONZE(), verts=16)
MORT_X, MORT_Y = (AV_X0 + AV_X1) / 2, AV_Y0 + 4
revolution("BeitAvtinas_makhteshet", MORT_X, MORT_Y, AV_Z,
           [(0.0, 0.0), (0.75, 0.0), (0.85, 1.3), (0.7, 1.3), (0.5, 0.45), (0.0, 0.4)],
           "80_Lishkot", MAT_BRONZE())
cone("BeitAvtinas_ketoret", MORT_X, MORT_Y, AV_Z + 0.4, AV_Z + 0.95, 0.5, 0.12, "80_Lishkot",
     MAT_KETORET())
cyl_between("BeitAvtinas_eli", (MORT_X + 0.1, MORT_Y, AV_Z + 0.7),
            (MORT_X + 0.45, MORT_Y + 0.35, AV_Z + 2.9), 0.12, "80_Lishkot", MAT_BRONZE(), verts=12)

# « וסמוך ללשכתו היתה » (Yerushalmi Yoma 1:5) : la lishka du Cohen Gadol touche le
# Beit Avtinas — donc à l'ouest de Sha'ar HaMayim, et non à l'ouest du mur sud. Elle
# s'en approche à ECART_LISHKA, ce qui laisse une ama d'air entre les deux socles :
# à une seule, les débords s'interpénétraient et leurs faces supérieures, coplanaires,
# clignotaient.
PARHEDRIN_X1 = SM_X0 - ECART_LISHKA
lishka("Lishkat_Parhedrin", PARHEDRIN_X1 - 15, PARHEDRIN_X1, BA_Y0, BA_Y1,
       Z_EZN, Z_AZ + 15, "80_Lishkot", [Porte("S", *PORTE_LISHKA, Z_EZN)], adossee="N")
maake("Lishkat_Parhedrin", PARHEDRIN_X1 - 15, PARHEDRIN_X1, BA_Y0, BA_Y1, Z_AZ + 15, "80_Lishkot")
# « שֶׁהַלִּשְׁכָּה הַזֹּאת הָיְתָה בֵּית דִּירָה לְכֹהֵן גָּדוֹל בְּשִׁבְעַת יְמֵי הַהַפְרָשָׁה » (Rambam, Mezouza 6:6) : la
# seule chambre du Mikdash à mezouza, « בַּטֶּפַח הַסָּמוּךְ לַחוּץ בִּתְחִלַּת שְׁלִישׁ הָעֶלְיוֹן שֶׁל גֹּבַהּ הַשַּׁעַר…
# עַל יְמִין הַנִּכְנָס » (6:12) — qui entre par le sud l'a à sa droite, sur le jambage est —, dans un tuyau
# de bois (5:6). Un logement, donc un lit. « מָסְרוּ לוֹ זְקֵנִים… וְקוֹרִין לְפָנָיו » (Yoma 1:3) : le banc des
# anciens. « בְּאִיּוֹב וּבְעֶזְרָא וּבְדִבְרֵי הַיָּמִים » et Daniel (1:6) : quatre rouleaux, l'un ouvert sur le
# pupitre. On l'y garde éveillé jusqu'au matin (1:7) : deux lampes. Formes, places, cotes : CHOIX.
PH_X0, PH_X1 = PARHEDRIN_X1 - 15 + LISHKA_PAREMENT, PARHEDRIN_X1 - LISHKA_PAREMENT
PH_Y0, PH_Y1 = BA_Y0 + LISHKA_PAREMENT, BA_Y1
MEZUZA_X = PARHEDRIN_X1 - 7.5 + PORTE_LISHKA[0] / 2 - 0.06
MEZUZA_Y, MEZUZA_Z = BA_Y0 + TEFAH / 2, Z_EZN + PORTE_LISHKA[1] * 2 / 3
cyl("Lishkat_Parhedrin_mezuza", MEZUZA_X, MEZUZA_Y, MEZUZA_Z, MEZUZA_Z + 0.5, 0.05,
    "80_Lishkot", MAT_CEDRE(), verts=8)
MITA = (PH_X0, PH_X0 + 1.8, PH_Y0 + 2, PH_Y0 + 6)
for k, (x, y) in enumerate(((MITA[0] + 0.15, MITA[2] + 0.15), (MITA[1] - 0.15, MITA[2] + 0.15),
                            (MITA[0] + 0.15, MITA[3] - 0.15), (MITA[1] - 0.15, MITA[3] - 0.15))):
    cyl(f"Lishkat_Parhedrin_mita_regel_{k}", x, y, Z_EZN, Z_EZN + 0.9, 0.08, "80_Lishkot", MAT_CEDRE(), verts=8)
box("Lishkat_Parhedrin_mita", *MITA, Z_EZN + 0.9, Z_EZN + 1.15, "80_Lishkot", MAT_CEDRE())
box("Lishkat_Parhedrin_mita_keset", MITA[0] + 0.05, MITA[1] - 0.05, MITA[2] + 0.05, MITA[3] - 0.05,
    Z_EZN + 1.15, Z_EZN + 1.4, "80_Lishkot", MAT_LAINE())
box("Lishkat_Parhedrin_mita_kar", MITA[0] + 0.3, MITA[1] - 0.3, MITA[3] - 0.7, MITA[3] - 0.15,
    Z_EZN + 1.4, Z_EZN + 1.6, "80_Lishkot", MAT_LIN())
box("Lishkat_Parhedrin_safsal_zekenim", PH_X0 + 3.5, PH_X1 - 2.5, PH_Y1 - 1, PH_Y1, Z_EZN, Z_EZN + 1, "80_Lishkot")
PUPITRE_X, PUPITRE_Y, PUPITRE_Z = (PH_X0 + PH_X1) / 2, PH_Y1 - 3.5, Z_EZN + 2.3
cyl("Lishkat_Parhedrin_pupitre_pied", PUPITRE_X, PUPITRE_Y, Z_EZN, PUPITRE_Z, 0.08, "80_Lishkot", MAT_CEDRE(), verts=8)
box("Lishkat_Parhedrin_pupitre", PUPITRE_X - 0.5, PUPITRE_X + 0.5, PUPITRE_Y - 0.4, PUPITRE_Y + 0.4,
    PUPITRE_Z, PUPITRE_Z + 0.06, "80_Lishkot", MAT_CEDRE())
box("Lishkat_Parhedrin_megila_iyov_yeria", PUPITRE_X - 0.3, PUPITRE_X + 0.3, PUPITRE_Y - 0.3, PUPITRE_Y + 0.3,
    PUPITRE_Z + 0.06, PUPITRE_Z + 0.07, "80_Lishkot", MAT_KLAF())
for cote, s in (("O", -1), ("E", 1)):
    cyl_between(f"Lishkat_Parhedrin_megila_iyov_{cote}", (PUPITRE_X + s * 0.35, PUPITRE_Y - 0.32, PUPITRE_Z + 0.13),
                (PUPITRE_X + s * 0.35, PUPITRE_Y + 0.32, PUPITRE_Z + 0.13), 0.07, "80_Lishkot", MAT_KLAF(), verts=10)
MADAF_Y, MADAF_Z = PH_Y0 + 2.5, Z_EZN + 2.8
box("Lishkat_Parhedrin_madaf", PH_X1 - 0.6, PH_X1, MADAF_Y - 1, MADAF_Y + 1, MADAF_Z - 0.1, MADAF_Z,
    "80_Lishkot", MAT_CEDRE())
for k, sefer in enumerate(("ezra", "divrei_hayamim", "daniel")):
    y = MADAF_Y - 0.6 + 0.6 * k
    cyl_between(f"Lishkat_Parhedrin_megila_{sefer}", (PH_X1 - 0.55, y, MADAF_Z + 0.11),
                (PH_X1 - 0.05, y, MADAF_Z + 0.11), 0.11, "80_Lishkot", MAT_KLAF(), verts=10)
for cote, x, normale in (("O", PH_X0, (1, 0)), ("E", PH_X1, (-1, 0))):
    ner_sur_tablette(f"Lishkat_Parhedrin_ner_{cote}", x, PH_Y1 - 2, normale, Z_EZN + 5, "80_Lishkot")

# Les deux lishkot de Sha'ar Nikanor, dans l'Ezrat Israël, de part et d'autre de la
# porte est : « וּשְׁתֵּי לְשָׁכוֹת הָיוּ לוֹ, אַחַת מִימִינוֹ וְאַחַת מִשְּׂמֹאלוֹ, אַחַת לִשְׁכַּת
# פִּנְחָס הַמַּלְבִּישׁ, וְאַחַת לִשְׁכַּת עוֹשֵׂי חֲבִתִּין » (Middot 1:4 ; Rambam, Beit
# HaBe'hira 5:17). CHOIX : Pin'has au nord (la droite de qui entre), leur cote et leur
# hauteur, qu'aucune source ne donne. Elles s'ouvrent à l'ouest, sur la cour.
LISHKA_NIKANOR_X0 = -8
LISHKOT_NIKANOR = {"Pinchas_HaMalbish": (5, 20), "Osei_Chavitin": (-20, -5)}
for nm, (ny0, ny1) in LISHKOT_NIKANOR.items():
    lishka(f"Lishkat_{nm}", LISHKA_NIKANOR_X0, AX1, ny0, ny1, Z_EZI, Z_AZ + 20, "80_Lishkot",
           [Porte("O", *PORTE_LISHKA, Z_EZI)], adossee="E")
    maake(f"Lishkat_{nm}", LISHKA_NIKANOR_X0, AX1, ny0, ny1, Z_AZ + 20, "80_Lishkot")
# « וּפִנְחָס עַל הַמַּלְבּוּשׁ » (Shekalim 5:1), et « שִׁשָּׁה וְתִשְׁעִים חַלּוֹן הָיוּ בַּמִּקְדָּשׁ לְהָנִיחַ בָּהֶן
# הַבְּגָדִים… וְכֻלָּן סְתוּמוֹת » (Rambam, Klei HaMikdash 8:8). Le Rambam ne dit pas où : la scène en
# garnit la chambre de Pin'has, sur ce que ses murs tiennent autour du guichet de Nikanor.
# Placards fermés d'une ama : CHOIX.
CHALON, PAS_CHALON = 1.0, 1.35
PC_X0 = LISHKA_NIKANOR_X0 + LISHKA_PAREMENT
PC_Y0, PC_Y1 = (LISHKOT_NIKANOR["Pinchas_HaMalbish"][0] + LISHKA_PAREMENT,
                LISHKOT_NIKANOR["Pinchas_HaMalbish"][1] - LISHKA_PAREMENT)
CHALONOT_OUVERTES = {(1, 6): ("mikhnasayim", "מכנסים"), (1, 7): ("avnet", "אבנט"),
                     (2, 6): ("kutonot", "כתנות"), (2, 7): ("mitznafot", "מצנפות")}
for r in range(6):
    z = Z_EZI + 0.6 + PAS_CHALON * r
    for k in range(4):
        x = PC_X0 + 0.6 + PAS_CHALON * k
        box(f"Lishkat_Pinchas_HaMalbish_chalon_S{r}{k}", x, x + CHALON, PC_Y0, PC_Y0 + 0.15,
            z, z + CHALON, "80_Lishkot", MAT_CEDRE())
        box(f"Lishkat_Pinchas_HaMalbish_chalon_N{r}{k}", x, x + CHALON, PC_Y1 - 0.15, PC_Y1,
            z, z + CHALON, "80_Lishkot", MAT_CEDRE())
    for k in range(8):
        y = PC_Y0 + 0.4 + PAS_CHALON * k
        devant_guichet = any(y < b + 0.3 and y + CHALON > a - 0.3 for _, a, b in PISHPESHIM)
        if devant_guichet and z < Z_EZI + H_PISHPESH + 0.4:
            continue
        if (r, k) in CHALONOT_OUVERTES:
            continue
        box(f"Lishkat_Pinchas_HaMalbish_chalon_E{r}{k}", AX1 - 0.15, AX1, y, y + CHALON,
            z, z + CHALON, "80_Lishkot", MAT_CEDRE())
# « וּכְשֶׁיִּכָּנְסוּ אַנְשֵׁי מִשְׁמָר לַעֲבוֹדָה… פּוֹתְחִין חַלּוֹנוֹתֵיהֶן כָּל יְמֵי שַׁבָּתָן » (Klei HaMikdash 8:8) : les
# quatre du mishmar de service sont ouverts, un vêtement par placard, « כָּל הַמִּכְנָסַיִם בְּחַלּוֹן אֶחָד וְכָתוּב
# עָלָיו מִכְנְסַיִם » (8:9), et « שֵׁם כָּל מִשְׁמָר כָּתוּב עַל חַלּוֹנוֹתָיו » (8:8). Seuls ces quatre portent leurs
# inscriptions. CHOIX : Yehoyariv, premier des mishmarot (Divrei HaYamim I 24:7), et quel placard garde quoi.
MISHMAR_DE_SERVICE = "יהויריב"
for (r, k), (vetement, _) in CHALONOT_OUVERTES.items():
    nom = f"Lishkat_Pinchas_HaMalbish_chalon_E{r}{k}"
    y, z = PC_Y0 + 0.4 + PAS_CHALON * k, Z_EZI + 0.6 + PAS_CHALON * r
    for cote, bornes in (("bas", (y, y + CHALON, z, z + 0.06)), ("haut", (y, y + CHALON, z + CHALON - 0.06, z + CHALON)),
                         ("S", (y, y + 0.06, z, z + CHALON)), ("N", (y + CHALON - 0.06, y + CHALON, z, z + CHALON))):
        box(f"{nom}_{cote}", AX1 - 0.6, AX1, bornes[0], bornes[1], bornes[2], bornes[3], "80_Lishkot", MAT_CEDRE())
    box(f"{nom}_delet", AX1 - 1.6, AX1 - 0.6, y + CHALON, y + CHALON + 0.08, z, z + CHALON, "80_Lishkot", MAT_CEDRE())
    fond = z + 0.06
    if vetement == "avnet":
        for i in range(3):
            tore(f"{nom}_avnet_{i}", AX1 - 0.3, y + CHALON / 2, fond + 0.05 + 0.1 * i, 0.2, 0.05,
                 "80_Lishkot", MAT_AVNET(), majeur=16, mineur=6)
        continue
    for i in range(4):
        box(f"{nom}_{vetement}_{i}", AX1 - 0.5, AX1 - 0.1, y + 0.15, y + CHALON - 0.15,
            fond + 0.09 * i, fond + 0.09 * i + 0.08, "80_Lishkot", MAT_LIN())
graver([(f"Lishkat_Pinchas_HaMalbish_ketav_E{r}{k}", ketav, AX1, PC_Y0 + 0.4 + PAS_CHALON * k + CHALON / 2,
         Z_EZI + 0.6 + PAS_CHALON * r - 0.17) for (r, k), (_, ketav) in CHALONOT_OUVERTES.items()]
       + [("Lishkat_Pinchas_HaMalbish_ketav_mishmar", MISHMAR_DE_SERVICE, AX1,
           PC_Y0 + 0.4 + PAS_CHALON * 6.5 + CHALON / 2, Z_EZI + 0.6 + PAS_CHALON * 3 - 0.17)],
       "80_Lishkot", taille=0.12, saillie=0.01)
# « חביתי כהן גדול לישתן ועריכתן ואפייתן בפנים » (Mena'hot 11:3), « עַל־מַחֲבַת בַּשֶּׁמֶן תֵּעָשֶׂה »
# (Vayikra 6:14), « וְהַמַּחֲבַת אֵין לָהּ כִּסּוּי » (Mena'hot 5:8) : la table où l'on pétrit, le foyer
# et la ma'havat plate posée sur ses braises. Formes et cotes : CHOIX.
OC_Y0, OC_Y1 = (LISHKOT_NIKANOR["Osei_Chavitin"][0] + LISHKA_PAREMENT,
                LISHKOT_NIKANOR["Osei_Chavitin"][1] - LISHKA_PAREMENT)
box("Lishkat_Osei_Chavitin_foyer", AX1 - 2.4, AX1 - 0.2, OC_Y0 + 0.4, OC_Y0 + 2.6,
    Z_EZI, Z_EZI + 1.1, "80_Lishkot")
box("Lishkat_Osei_Chavitin_braises", AX1 - 2.2, AX1 - 0.4, OC_Y0 + 0.6, OC_Y0 + 2.4,
    Z_EZI + 1.1, Z_EZI + 1.25, "80_Lishkot", braise("Braise"))
revolution("Lishkat_Osei_Chavitin_machvat", AX1 - 1.3, OC_Y0 + 1.5, Z_EZI + 1.25,
           [(0.0, 0.0), (0.85, 0.0), (0.9, 0.1), (0.84, 0.1), (0.0, 0.04)],
           "80_Lishkot", MAT_BRONZE(), verts=24)
# Le Rambam détaille le geste (Ma'asse HaKorbanot 13:2-4) : « מֵבִיא עִשָּׂרוֹן שָׁלֵם… וְחוֹצֵהוּ בַּחֲצִי עִשָּׂרוֹן
# שֶׁבַּמִּקְדָּשׁ », « שְׁלֹשֶׁת לוֹגִין שֶׁמֶן », « וְחוֹלְטָהּ בְּרוֹתְחִין » — un second feu, et l'eau qui bout dessus —,
# « מְחַלֵּק הַשְּׁלֹשָׁה לוֹגִין בִּרְבִיעִית שֶׁבַּמִּקְדָּשׁ », « נִמְצְאוּ שְׁתֵּים עֶשְׂרֵה חַלּוֹת », puis « קוֹלֶה אוֹתָהּ עַל
# הַמַּחֲבַת ». Sur la table : les douze galettes, les deux mesures, la jarre des trois log ; une galette
# sur la ma'havat. Formes, bronze des mesures, places : CHOIX.
box("Lishkat_Osei_Chavitin_table", AX1 - 1.6, AX1 - 0.2, OC_Y0 + 3.4, OC_Y0 + 7,
    Z_EZI, Z_EZI + 1.5, "80_Lishkot", MAT_MARBRE())
cyl("Lishkat_Osei_Chavitin_machvat_halla", AX1 - 1.3, OC_Y0 + 1.5, Z_EZI + 1.29, Z_EZI + 1.36, 0.3,
    "80_Lishkot", MAT_LECHEM(), verts=16)
Z_TABLE_CHAVITIN = Z_EZI + 1.5
for k in range(12):
    cyl(f"Lishkat_Osei_Chavitin_halla_{k:02d}", AX1 - 1.45 + 0.33 * (k % 4), OC_Y0 + 3.7 + 0.35 * (k // 4),
        Z_TABLE_CHAVITIN, Z_TABLE_CHAVITIN + 0.06, 0.15, "80_Lishkot", MAT_LECHEM(), verts=12)
for nom, y, r, h in (("chatzi_isaron", OC_Y0 + 5.6, 0.2, 0.3), ("reviit", OC_Y0 + 6.3, 0.07, 0.1)):
    revolution(f"Lishkat_Osei_Chavitin_{nom}", AX1 - 0.6, y, Z_TABLE_CHAVITIN,
               [(0.0, 0.0), (r, 0.0), (r, h), (0.88 * r, h), (0.88 * r, 0.03), (0.0, 0.03)],
               "80_Lishkot", MAT_BRONZE(), verts=16)
cone("Lishkat_Osei_Chavitin_chatzi_isaron_solet", AX1 - 0.6, OC_Y0 + 5.6, Z_TABLE_CHAVITIN + 0.03,
     Z_TABLE_CHAVITIN + 0.36, 0.17, 0.05, "80_Lishkot", MAT_SOLET(), verts=12)
revolution("Lishkat_Osei_Chavitin_kad_shemen", AX1 - 1.2, OC_Y0 + 6.0, Z_TABLE_CHAVITIN,
           [(0.0, 0.0), (0.18, 0.02), (0.3, 0.3), (0.27, 0.55), (0.11, 0.7), (0.13, 0.78), (0.0, 0.76)],
           "80_Lishkot", MAT_TERRE_CUITE(), verts=14)
box("Lishkat_Osei_Chavitin_foyer_rotchin", AX1 - 2.4, AX1 - 0.2, OC_Y1 - 2.6, OC_Y1 - 0.4,
    Z_EZI, Z_EZI + 1.1, "80_Lishkot")
box("Lishkat_Osei_Chavitin_braises_rotchin", AX1 - 2.2, AX1 - 0.4, OC_Y1 - 2.4, OC_Y1 - 0.6,
    Z_EZI + 1.1, Z_EZI + 1.25, "80_Lishkot", braise("Braise"))
revolution("Lishkat_Osei_Chavitin_yora", AX1 - 1.3, OC_Y1 - 1.5, Z_EZI + 1.25,
           [(0.0, 0.0), (0.45, 0.02), (0.65, 0.35), (0.62, 0.8), (0.56, 0.8), (0.58, 0.36), (0.42, 0.08), (0.0, 0.08)],
           "80_Lishkot", MAT_BRONZE(), verts=20)
cyl("Lishkat_Osei_Chavitin_yora_mayim", AX1 - 1.3, OC_Y1 - 1.5, Z_EZI + 1.9, Z_EZI + 1.95, 0.54,
    "80_Lishkot", MAT_EAU(), verts=20)

# --- Les trois lishkot du sud (Middot 5:3) : HaMelah, HaParva, HaMedi'hin. Elles sont
#     DANS l'Azara, contre la face intérieure du mur, et non sur la terrasse du 'Heil
#     comme celles du nord. Ce n'est pas une inconséquence, c'est le Beit HaParva qui
#     l'impose : « חָמֵשׁ טְבִילוֹת… וְכֻלָּן בַּקֹּדֶשׁ עַל בֵּית הַפַּרְוָה » (Yoma 3:3),
#     « הֱבִיאוּהוּ לְבֵית הַפַּרְוָה, וּבַקֹּדֶשׁ הָיְתָה » (Yoma 3:6). Quatre des cinq immersions
#     du Cohen Gadol se font sur son TOIT, et un toit bâti dans le 'hol n'est pas
#     sanctifié quand bien même l'intérieur l'est (Tosfot Yom Tov sur Middot 5:3,
#     d'après Maaser Sheni 3:8). Une Parva posée dehors mettrait l'avoda dans le 'hol.
#     Les deux autres suivent : Medi'hin par la mesiba qui monte au toit de Parva, et
#     Melah parce que Middot 5:3 les donne comme un même groupe.
#     Ordre d'est en ouest — Melah, Parva, Medi'hin — Tosfot Yom Tov, ibid. : « וְכֵן
#     רָאִיתִי בְּצִיּוּרוֹ שֶׁל פֵּירוּשׁ הָרַמְבַּ"ם שֶׁמְּסַדֵּר לִשְׁכַּת הַמֶּלַח סָמוּךְ לַמִּזְרָח ». Les x sont
#     un CHOIX : aucune source n'en donne, et ce qui reste libre le long du mur sud est
#     fixé par ses trois portes, par le kevesh et par la Mer. Melah est séparée des deux
#     autres par Sha'ar HaBekhorot — rien ne demande que les trois se touchent, sauf
#     Medi'hin et Parva, que la mesiba relie.
H_LISHKA_INT = 22         # CHOIX : sous les 25 amot du mur, qui continue de se lire.
SUD_INT = (AY0, AY0 + SAILLIE_INT)
MELACH_X, PARVA_X, MEDICHIN_X = (-44, -26), (-92, -74), (-113, -96)
# La Lishkat HaMela'h ouvre à l'est : le pied du kevesh passe à une ama de son socle
# (Rambam, Beit HaBe'hira 5:15), et une porte nord ne donnait que sur le talus. Six amot,
# la face n'en ayant que huit entre le mur de l'Azara et le parement nord : CHOIX.
PORTES_SUD = {"HaMelach": Porte("E", 6, PORTE_LISHKA[1], Z_AZ),
              "HaParva": Porte("N", *PORTE_LISHKA, Z_AZ),
              "HaMedichin": Porte("N", *PORTE_LISHKA, Z_AZ)}
for nm, (x0, x1) in (("HaMelach", MELACH_X), ("HaParva", PARVA_X), ("HaMedichin", MEDICHIN_X)):
    lishka(f"Lishkat_{nm}", x0, x1, *SUD_INT, Z_AZ, Z_AZ + H_LISHKA_INT, "80_Lishkot",
           [PORTES_SUD[nm]], adossee="S")
# Ce que Middot 5:3 met dans chacune ; formes et cotes du mobilier : CHOIX.
# HaMela'h, « שָׁם הָיוּ נוֹתְנִים מֶלַח לַקָּרְבָּן » : le sel en tas contre le mur.
for k in range(4):
    cle = f"Lishkat_HaMelach_sel_{k}"
    cone(cle, MELACH_X[0] + LISHKA_PAREMENT + 1.6 + 3 * k, SUD_INT[0] + 1.7, Z_AZ,
         Z_AZ + 1.2 + 0.5 * alea(cle, 1), 1.1 + 0.4 * alea(cle), 0.2, "80_Lishkot", MAT_SEL(), verts=16)
# « וּבִשְׁלֹשָׁה מְקוֹמוֹת הָיוּ נוֹתְנִין הַמֶּלַח. בְּלִשְׁכַּת הַמֶּלַח. וְעַל גַּבֵּי הַכֶּבֶשׁ. וּבְרֹאשׁוֹ שֶׁל מִזְבֵּחַ », et ce sel
# est « מִשֶּׁל צִבּוּר » (Rambam, Issourei Mizbea'h 5:13) : ce qui monte au kevesh et à l'autel part d'ici.
# Trois paniers remplis, près de la porte. Le Rambam met ici la salaison des peaux, que Middot 5:3
# donne à la Parva ; la scène suit Middot. Paniers et places : CHOIX.
for k in range(3):
    x, y = MELACH_X[1] - LISHKA_PAREMENT - 1.5 - 1.2 * k, SUD_INT[1] - LISHKA_PAREMENT - 0.6
    revolution(f"Lishkat_HaMelach_kuppa_{k}", x, y, Z_AZ,
               [(0.0, 0.0), (0.4, 0.0), (0.52, 0.6), (0.46, 0.6), (0.36, 0.06), (0.0, 0.06)],
               "80_Lishkot", MAT_CHENE(), verts=16)
    cone(f"Lishkat_HaMelach_kuppa_{k}_melach", x, y, Z_AZ + 0.06, Z_AZ + 0.75, 0.47, 0.08,
         "80_Lishkot", MAT_SEL(), verts=16)
# HaParva, « שָׁם הָיוּ מוֹלְחִין עוֹרוֹת קָדָשִׁים » : les peaux empilées sur une banquette, et le sel.
PV_X0, PV_X1 = PARVA_X[0] + LISHKA_PAREMENT, PARVA_X[1] - LISHKA_PAREMENT
box("Lishkat_HaParva_banquette", PV_X0 + 1, PV_X1 - 3, SUD_INT[0], SUD_INT[0] + 2.5,
    Z_AZ, Z_AZ + 1, "80_Lishkot")
for pile in range(3):
    for couche in range(6):
        cle = f"Lishkat_HaParva_peau_{pile}{couche}"
        x = PV_X0 + 1.6 + 3.2 * pile + (alea(cle) - 0.5) * 0.4
        y = SUD_INT[0] + 0.3 + (alea(cle, 1) - 0.5) * 0.3
        box(cle, x, x + 2.4, y, y + 1.9, Z_AZ + 1 + 0.09 * couche, Z_AZ + 1.08 + 0.09 * couche,
            "80_Lishkot", MAT_PEAU())
cone("Lishkat_HaParva_sel", PV_X1 - 2, SUD_INT[0] + 5, Z_AZ, Z_AZ + 1.1, 1.3, 0.2,
     "80_Lishkot", MAT_SEL(), verts=16)
# Le geste lui-même : une peau étendue au sol sous son sel, deux autres qui sèchent sur une perche contre
# le mur ouest. Les peaux sont aux cohanim, « וְעוֹרוֹת קָדְשֵׁי קָדָשִׁים לַכֹּהֲנִים » (Zeva'him 12:3), d'où les
# piles. Perche, tréteaux, places : CHOIX.
box("Lishkat_HaParva_peau_meluha", PV_X0 + 1.5, PV_X0 + 5.5, SUD_INT[0] + 3.7, SUD_INT[0] + 6.5,
    Z_AZ, Z_AZ + 0.06, "80_Lishkot", MAT_PEAU())
box("Lishkat_HaParva_peau_meluha_melach", PV_X0 + 1.8, PV_X0 + 5.2, SUD_INT[0] + 4, SUD_INT[0] + 6.2,
    Z_AZ + 0.06, Z_AZ + 0.09, "80_Lishkot", MAT_SEL())
MOT_X, MOT_Y0, MOT_Y1, MOT_Z = PV_X0 + 0.7, SUD_INT[0] + 3, SUD_INT[0] + 7.6, Z_AZ + 3
for cote, y in (("S", MOT_Y0), ("N", MOT_Y1)):
    cyl(f"Lishkat_HaParva_mot_amud_{cote}", MOT_X, y, Z_AZ, MOT_Z + 0.1, 0.1, "80_Lishkot", MAT_CHENE(), verts=8)
cyl_between("Lishkat_HaParva_mot", (MOT_X, MOT_Y0, MOT_Z), (MOT_X, MOT_Y1, MOT_Z), 0.08, "80_Lishkot", MAT_CHENE(), verts=8)
for k, y in enumerate((MOT_Y0 + 0.4, MOT_Y0 + 2.5)):
    for cote, s in (("O", -1), ("E", 1)):
        box(f"Lishkat_HaParva_peau_tluya_{k}{cote}", MOT_X + s * 0.1, MOT_X + s * 0.16, y, y + 1.8,
            MOT_Z - 1.6, MOT_Z, "80_Lishkot", MAT_PEAU())
# HaMedi'hin, « שֶׁשָּׁם הָיוּ מְדִיחִין קִרְבֵי הַקֳּדָשִׁים » : une auge d'eau contre le mur, deux tables.
MD_X0, MD_X1 = MEDICHIN_X[0] + LISHKA_PAREMENT, MEDICHIN_X[1] - LISHKA_PAREMENT
AUGE = (MD_X0 + 2, MD_X1 - 2, SUD_INT[0] + 0.5, SUD_INT[0] + 1.7)
dalle_trouee("Lishkat_HaMedichin_auge", MD_X0 + 1.5, MD_X1 - 1.5, SUD_INT[0], SUD_INT[0] + 2.2,
             Z_AZ, Z_AZ + 1.2, AUGE, "80_Lishkot")
box("Lishkat_HaMedichin_auge_eau", *AUGE, Z_AZ, Z_AZ + 0.9, "80_Lishkot", MAT_EAU())
for cote, xa in (("O", MD_X0), ("E", MD_X1 - 1.5)):
    box(f"Lishkat_HaMedichin_table_{cote}", xa, xa + 1.5, SUD_INT[0] + 3.5, SUD_INT[0] + 7,
        Z_AZ, Z_AZ + 1.5, "80_Lishkot", MAT_MARBRE())
    for k in range(2):
        revolution(f"Lishkat_HaMedichin_table_{cote}_keara_{k}", xa + 0.75, SUD_INT[0] + 4.3 + 1.9 * k, Z_AZ + 1.5,
                   [(0.0, 0.0), (0.3, 0.0), (0.55, 0.3), (0.5, 0.3), (0.27, 0.05), (0.0, 0.05)],
                   "80_Lishkot", MAT_BRONZE(), verts=16)
# « וְהַכֶּרֶס מְדִיחִין אוֹתָהּ בְּבֵית מְדִיחִין כָּל צָרְכָּהּ » (Tamid 4:2), et c'est l'eau de l'amma qui rince,
# celle du puits de la Gola étant bue (R. Shemaya sur Middot 5:4) : l'eau arrive dans l'auge par un bec.
# Bec et bassines : CHOIX.
cyl_between("Lishkat_HaMedichin_tzinor", ((MD_X0 + MD_X1) / 2, SUD_INT[0], Z_AZ + 2.3),
            ((MD_X0 + MD_X1) / 2, SUD_INT[0] + 1.1, Z_AZ + 2.05), 0.1, "80_Lishkot", MAT_BRONZE(), verts=10)
# Le bain rituel sur le toit du Beit HaParva — « וְעַל גַּגָּהּ הָיָה בֵית הַטְּבִילָה לְכֹהֵן
# גָּדוֹל בְּיוֹם הַכִּפּוּרִים » (Middot 5:3). Maake parce que ce toit est un lieu de service
# (Rambam, Rotzea'h 11:2). Le drap de bouts tendu entre lui et le peuple (Yoma 3:4)
# n'est pas modélisé, non plus que les marches de la cuve : cote inventée, CHOIX.
Z_TOIT_PARVA = Z_AZ + H_LISHKA_INT
maake("Lishkat_HaParva", *PARVA_X, *SUD_INT, Z_TOIT_PARVA, "80_Lishkot")
MIKVE_L, MIKVE_P, MIKVE_MARGELLE = 8, 6, 1        # cuve au centre du toit, margelle d'une ama
MX_C, MY_C = sum(PARVA_X) / 2, sum(SUD_INT) / 2
MKX0, MKX1 = MX_C - MIKVE_L / 2, MX_C + MIKVE_L / 2
MKY0, MKY1 = MY_C - MIKVE_P / 2, MY_C + MIKVE_P / 2
e = MIKVE_MARGELLE
for cote, a, b, c, d in (("S", MKX0, MKX1, MKY0, MKY0 + e), ("N", MKX0, MKX1, MKY1 - e, MKY1),
                         ("O", MKX0, MKX0 + e, MKY0 + e, MKY1 - e),
                         ("E", MKX1 - e, MKX1, MKY0 + e, MKY1 - e)):
    box(f"Mikve_Parva_margelle_{cote}", a, b, c, d, Z_TOIT_PARVA, Z_TOIT_PARVA + 2, "80_Lishkot")
box("Mikve_Parva_eau", MKX0 + e, MKX1 - e, MKY0 + e, MKY1 - e,
    Z_TOIT_PARVA, Z_TOIT_PARVA + 1.7, "80_Lishkot", MAT_EAU())
# « וּמִשָּׁם מְסִבָּה עוֹלָה לְגַג בֵּית הַפַּרְוָה » (Middot 5:3 ; Rambam, Beit HaBe'hira 5:17) :
# la montée part de la Lishkat HaMedi'hin et débouche sur le toit du Beit HaParva.
# Tosfot Yom Tov (ibid.) la veut du côté de la Parva et à l'écart de l'endroit où l'on
# rince les entrailles — « שֶׁלֹּא יִתָּכֵן… שֶׁהַכֹּהֵן גָּדוֹל יַעֲלֶה לְבֵית טְבִילָתוֹ דֶּרֶךְ מָקוֹם
# שֶׁמְּדִיחִין בּוֹ ». D'où la tour engagée entre les deux corps, et ronde : מסיבה est une
# vis, un escalier droit ne porterait pas ce nom.
MESIBA_X = (MEDICHIN_X[1] + PARVA_X[0]) / 2
MESIBA_Y = SUD_INT[1] + 1        # la tour engage les deux corps et ressort dans la cour
cyl("Mesiba_Parva", MESIBA_X, MESIBA_Y, Z_AZ, Z_TOIT_PARVA + 1, 3.5, "80_Lishkot", verts=24)
cyl("Mesiba_Parva_corniche", MESIBA_X, MESIBA_Y, Z_TOIT_PARVA - 1, Z_TOIT_PARVA + 0.5, 4,
    "80_Lishkot", verts=24)
