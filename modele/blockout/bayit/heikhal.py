from ..primitives.parametres import PORTES_HEIKHAL_OUVERTES, Z_BAT
from ..primitives.matieres import MAT_CEDRE, MAT_FER_LAME, MAT_MARBRE_HERODE, MAT_OR, MAT_OR_PLAQUE
from ..primitives.volumes import box, cyl, plage, rampe
from ..primitives.gravures import vantail_sculpte
from ..primitives.ouvrages import (EPAISSEUR_PLACAGE, MAAKE_EP, MAAKE_H, couches_middot, dalle_percee,
                                   paroi_percee)
from .oulam import BX_E, BX_O, Z_FAITE, Z_TOIT


# --- Mur est du Heikhal (6 amot) avec porte 10 × 20, quatre portes plaquées d'or
HX_E = BX_E - 16      # -92
# « וּשְׁנֵי פִשְׁפָּשִׁין הָיוּ לוֹ לַשַּׁעַר הַגָּדוֹל, אֶחָד בַּצָּפוֹן וְאֶחָד בַּדָּרוֹם. שֶׁבַּדָּרוֹם, לֹא נִכְנַס
# בּוֹ אָדָם מֵעוֹלָם… נָטַל אֶת הַמַּפְתֵּחַ וּפָתַח אֶת הַפִּשְׁפָּשׁ, וְנִכְנַס לְהַתָּא, וּמֵהַתָּא לַהֵיכָל »
# (Middot 4:2) : deux guichets de part et d'autre du grand portail, ouvrant sur le tא du
# coin. Celui du sud ne s'ouvre jamais (Yehezkel 44:2) ; il est bâti, pas percé.
PISHPASH = (6, 8, Z_BAT, Z_BAT + 4)        # largeur et hauteur : CHOIX, Middot n'en donne pas
paroi_percee("Heikhal_mur_est_N", HX_E - 6, HX_E, 5, 35, Z_BAT, Z_TOIT,
             "50_Heikhal", MAT_MARBRE_HERODE(), [PISHPASH])
box("Heikhal_mur_est_S", HX_E - 6, HX_E, -35, -5, Z_BAT, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
box("Heikhal_mur_est_linteau", HX_E - 6, HX_E, -5, 5, Z_BAT + 20, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
if PORTES_HEIKHAL_OUVERTES:
    # « הַחִיצוֹנוֹת נִפְתָּחוֹת לְתוֹךְ הַפֶּתַח לְכַסּוֹת עָבְיוֹ שֶׁל כֹּתֶל, וְהַפְּנִימִיּוֹת נִפְתָּחוֹת לְתוֹךְ
    # הַבַּיִת לְכַסּוֹת אַחַר הַדְּלָתוֹת » (Middot 4:1) : les battants extérieurs rabattus dans
    # l'embrasure de 6 amot, contre les jambages ; les intérieurs dans le Heikhal, à plat
    # contre le mur est. Tous portent les figures que les versets leur donnent — « וְקָלַע
    # כְּרוּבִים וְתִמֹרוֹת וּפְטֻרֵי צִצִּים וְצִפָּה זָהָב » (Melakhim I 6:35 ; Ye'hezkel 41:25) : c'est le
    # seul vantail du Temple que le corpus sculpte, et il était une plaque d'or nue.
    for _cote, _y, _sens in (("S", -4.7, 1), ("N", 4.7, -1)):
        box(f"Heikhal_porte_{_cote}", HX_E - 5, HX_E - 0.3, _y - 0.3 * _sens, _y,
            Z_BAT, Z_BAT + 20, "50_Heikhal", MAT_OR())
        vantail_sculpte(f"Heikhal_porte_{_cote}_figure", ("x", _y, _sens),
                        HX_E - 4.7, HX_E - 0.6, Z_BAT + 0.6, Z_BAT + 19.4, "50_Heikhal")
    for _cote, _sens in (("S", -1), ("N", 1)):
        _u0, _u1 = sorted((_sens * 5.05, _sens * 9.85))
        box(f"Heikhal_porte_int_{_cote}", HX_E - 6.3, HX_E - 6, _u0, _u1,
            Z_BAT, Z_BAT + 20, "50_Heikhal", MAT_OR())
        vantail_sculpte(f"Heikhal_porte_int_{_cote}_figure", ("y", HX_E - 6.3, -1),
                        _u0 + 0.3, _u1 - 0.3, Z_BAT + 0.6, Z_BAT + 19.4, "50_Heikhal")
else:
    box("Heikhal_porte_S", HX_E - 0.6, HX_E - 0.3, -5, -0.3, Z_BAT, Z_BAT + 20, "50_Heikhal", MAT_OR())
    box("Heikhal_porte_N", HX_E - 0.6, HX_E - 0.3, 0.3, 5, Z_BAT, Z_BAT + 20, "50_Heikhal", MAT_OR())

# --- Corps : 70 large ; intérieur 20 large ; murs + 38 cellules = 25 de chaque côté
HK0, HK1 = HX_E - 6, HX_E - 46          # Heikhal intérieur : -98 → -138
TR0, TR1 = HK1, HK1 - 1                 # Amah Traksin : -138 → -139
KK0, KK1 = TR1, TR1 - 20                # Kodesh HaKodashim : -139 → -159
ARON_Y_BAD = 1.38                       # les badim, hors des flancs de l'Arche (1,25 + anneau)
ARON_Z_BAD = Z_BAT + 0.125 + 1.35       # à hauteur des anneaux, coins supérieurs de la caisse
ARON_X_MACHTA = (KK0 + KK1) / 2 + 2.5   # la ma'hta entre les badim, assez loin de la face est pour que ses braises montent sur les keruvim
# Les fenêtres hautes du Heikhal, « שְׁקוּפִים אֲטוּמִים » (Melakhim I 6:4 ; Mena'hot 86b) :
# étroites dedans, larges dehors, « להוציא אורה לעולם » (Rashi sur Mena'hot 86b).
# Elles étaient des boîtes de chaux noyées dans le mur, coplanaires avec ses deux
# faces : un rectangle blanc qui clignotait sur l'or du plan 9a. Ce sont maintenant
# de vraies baies, en deux épaisseurs — l'embrasure extérieure de 3 × 6, l'intérieure
# de 1,2 × 4 — percées dans le mur ET dans le placage d'or.
FENETRES_X = [HK0 - 6 - i * 9 for i in range(4)]
FENETRE_EXT, FENETRE_INT = (3.0, Z_BAT + 30, Z_BAT + 36), (1.2, Z_BAT + 31, Z_BAT + 35)


def baies_heikhal(largeur, zb, zh):
    return [(x - largeur / 2, x + largeur / 2, zb, zh) for x in FENETRES_X]


Y_INT, Y_TA, Y_MUR_TA, Y_MES, Y_EXT = 10, 22, 27, 30, 35
X_TA_O = KK1 - 12                          # -171 : le nu extérieur des cellules d'ouest
Z_ETAGE_SOL = Z_BAT + 45            # 51 : sur la מעזיבה, les cinq amot de Middot 4:6
Z_ETAGE_HAUT = Z_ETAGE_SOL + 40     # 91 : le haut de ses murs, puis les cinq amot du toit
# --- Messiba (Middot 4:5) : « וּמְסִבָּה הָיְתָה עוֹלָה מִקֶּרֶן מִזְרָחִית צְפוֹנִית לְקֶרֶן צְפוֹנִית
#     מַעֲרָבִית, שֶׁבָּהּ הָיוּ עוֹלִים לְגַגּוֹת הַתָּאִים. הָיָה עוֹלֶה בַּמְּסִבָּה וּפָנָיו לַמַּעֲרָב. הָלַךְ עַל
#     כָּל פְּנֵי הַצָּפוֹן, עַד שֶׁהוּא מַגִּיעַ לַמַּעֲרָב… וְהָפַךְ פָּנָיו לַדָּרוֹם… הָלַךְ כָּל פְּנֵי מַעֲרָב…
#     וְהָפַךְ פָּנָיו לַמִּזְרָח. הָיָה מְהַלֵּךְ בַּדָּרוֹם, עַד שֶׁהוּא מַגִּיעַ לְפִתְחָהּ שֶׁל עֲלִיָּה »
#     — un seul circuit, coin nord-est → nord → ouest → sud → la porte de l'étage.
#     Middot 4:7 donne la bande du nord (מְסִבָּה 3, כֹּתֶל הַמְּסִבָּה 5) et celle du sud
#     (בֵּית הוֹרָדַת הַמַּיִם 3), toutes deux laissées en creux ici. À l'OUEST la michna ne bande
#     rien : les cent amot est-ouest sont pleines. Les trois amot du couloir d'ouest sont
#     donc prises sur les cinq du כֹּתֶל הַתָּא, une ama de maçonnerie de chaque côté — CHOIX.
#     La pente n'est donnée nulle part : elle se répartit sur les trois branches, CHOIX.
MESIBA_L, MESIBA_EP = 3, 1
X_MES_O0, X_MES_O1 = BX_O + 1, BX_O + 4        # le couloir d'ouest, dans le mur des ta'im
X_PORTE_ALIYAH = -113                          # où la branche sud atteint le niveau de l'étage
LEGS = (abs(BX_O - HK0), 2 * Y_MES, abs(X_PORTE_ALIYAH - BX_O))
Z_MES = [Z_BAT]
for L in LEGS:
    Z_MES.append(Z_MES[-1] + (Z_ETAGE_SOL - Z_BAT) * L / sum(LEGS))
PORTE_ALIYAH = (X_PORTE_ALIYAH, X_PORTE_ALIYAH + 3, Z_ETAGE_SOL, Z_ETAGE_SOL + 10)
PORTE_TA = (HK0 - 4, HK0 - 2, Z_BAT, Z_BAT + 4)      # le ta du coin nord-est, CHOIX

# --- Découpage nord-sud du corps (Middot 4:7) : « כֹּתֶל הַמְּסִבָּה חָמֵשׁ, וְהַמְּסִבָּה שָׁלֹשׁ,
#     כֹּתֶל הַתָּא חָמֵשׁ, וְהַתָּא שֵׁשׁ, כֹּתֶל הַהֵיכָל שֵׁשׁ, וְתוֹכוֹ עֶשְׂרִים » puis le miroir au sud,
#     où les trois amot sont בֵּית הוֹרָדַת הַמַּיִם — 70 en tout. Est-ouest, derrière le KhK, la
#     même michna donne כֹּתֶל הַהֵיכָל שֵׁשׁ, הַתָּא שֵׁשׁ, כֹּתֶל הַתָּא חָמֵשׁ.
#     Le blockout portait deux bandes pleines de quinze amot : ni ta'im, ni messiba.
# --- Ta'im. « שְׁלֹשִׁים וּשְׁמֹנָה תָאִים הָיוּ שָׁם, חֲמִשָּׁה עָשָׂר בַּצָּפוֹן, חֲמִשָּׁה עָשָׂר בַּדָּרוֹם,
#     וּשְׁמֹנָה בַּמַּעֲרָב. שֶׁבַּצָּפוֹן וְשֶׁבַּדָּרוֹם, חֲמִשָּׁה עַל גַּבֵּי חֲמִשָּׁה, וַחֲמִשָּׁה עַל גַּבֵּיהֶם.
#     וְשֶׁבַּמַּעֲרָב, שְׁלֹשָׁה עַל גַּבֵּי שְׁלֹשָׁה, וּשְׁנַיִם עַל גַּבֵּיהֶם » (Middot 4:3) : 15 + 15 + 8.
#     « הַתַּחְתּוֹנָה חָמֵשׁ, וְרֹבֶד שֵׁשׁ. וְהָאֶמְצָעִית שֵׁשׁ, וְרֹבֶד שֶׁבַע. וְהָעֶלְיוֹנָה שֶׁבַע » (4:4,
#     qui le tire de Melakhim I 6:6) : la cellule s'élargit de 5 à 7 parce que le mur du
#     Heikhal se retire d'une ama par étage (מִגְרָעוֹת, Melakhim I 6:6, « לְבִלְתִּי אֲחֹז
#     בְּקִירוֹת הַבָּיִת »). Les six de mur et six de cellule de 4:7 sont l'étage du MILIEU.
#     Ce que les sources ne donnent pas, et qui est donc CHOIX : la hauteur d'un étage
#     (les trois remplissent les quarante amot du rez, 12 de vide et une de dalle, la
#     dernière de deux), la longueur des cellules et l'épaisseur des refends.
TA_VIDE = 12
TA_ETAGES = ((Z_BAT, 5, 1), (Z_BAT + 13, 6, 1), (Z_BAT + 26, 7, 2))   # (sol, largeur, dalle)
Z_TA_TOIT = Z_BAT + 40                     # 46 : le toit des ta'im, au niveau du plafond du rez
TA_REFEND, TA_PORTE_L, TA_PORTE_H = 1, 2, 4
TA_TREMIE = 2                              # « וְאֶחָד לַתָּא שֶׁעַל גַּבָּיו » (4:3)


def travees(a0, a1, n, refend):
    """Découpe le segment a0→a1 en n travées égales séparées de `refend`, dans son sens."""
    sens = 1 if a1 > a0 else -1
    L = (abs(a1 - a0) - (n - 1) * refend) / n
    return [(a0 + sens * k * (L + refend), a0 + sens * (k * (L + refend) + L)) for k in range(n)]


def refend(name, mince0, mince1, long0, long1, z0, mince_en, col, mat):
    """Cloison entre deux ta'im, percée d'une porte au milieu (Middot 4:3).

    `mince_en` dit sur quel axe la cloison est mince ; la porte s'ouvre sur l'autre.
    """
    c = (long0 + long1) / 2
    demi = TA_PORTE_L / 2

    def pose(suffixe, a, b, zb, zh):
        if b - a <= 0:
            return
        if mince_en == "x":
            box(f"{name}_{suffixe}", mince0, mince1, a, b, zb, zh, col, mat)
        else:
            box(f"{name}_{suffixe}", a, b, mince0, mince1, zb, zh, col, mat)

    pose("a", min(long0, long1), c - demi, z0, z0 + TA_VIDE)
    pose("b", c + demi, max(long0, long1), z0, z0 + TA_VIDE)
    pose("linteau", c - demi, c + demi, z0 + TA_PORTE_H, z0 + TA_VIDE)


for cote, sg in (("N", 1), ("S", -1)):
    for etage, (z0, large, dalle) in enumerate(TA_ETAGES):
        ep = 12 - large                                   # 7, 6, 5 : le mur se retire
        ya, yb = sorted((sg * (Y_INT + ep), sg * Y_TA))
        # « וּבְקֶרֶן מִזְרָחִית צְפוֹנִית הָיוּ חֲמִשָּׁה פְתָחִים… וְאֶחָד לַמְּסִבָּה, וְאֶחָד לַפִּשְׁפָּשׁ,
        # וְאֶחָד לַהֵיכָל » (Middot 4:3) : le ta du coin nord-est perce le mur du Heikhal.
        vers_heikhal = [PORTE_TA] if (cote, etage) == ("N", 0) else []
        # Les fenêtres du Heikhal (Melakhim I 6:4) traversent le mur au troisième étage des
        # ta'im, le seul dont la tranche couvre leur hauteur : étroites ici, larges dehors.
        if z0 <= FENETRE_INT[1] and FENETRE_INT[2] <= z0 + TA_VIDE + dalle:
            vers_heikhal = vers_heikhal + baies_heikhal(*FENETRE_INT)
        paroi_percee(f"Corps_mur_HK_{cote}_{etage}", KK1, HK0,
                     *sorted((sg * Y_INT, sg * (Y_INT + ep))),
                     z0, z0 + TA_VIDE + dalle, "50_Heikhal", MAT_MARBRE_HERODE(), vers_heikhal)
        cellules = travees(HK0, KK1, 5, TA_REFEND)
        for k in range(4):
            xb = cellules[k][1]
            refend(f"Ta_{cote}_{etage}_refend_{k}", xb, xb - TA_REFEND, ya, yb, z0, "x",
                   "50_Heikhal", MAT_MARBRE_HERODE())
        dalle_percee(f"Ta_{cote}_{etage}_dalle", KK1, HK0, ya, yb, z0 + TA_VIDE,
                     z0 + TA_VIDE + dalle, "50_Heikhal", MAT_CEDRE(),
                     [(min(xa, xb) + 2, min(xa, xb) + 2 + TA_TREMIE, yb - 2 - TA_TREMIE, yb - 2)
                      for xa, xb in cellules])
# Ouest : trois cellules sur trois, deux au-dessus (Middot 4:3)
for etage, (z0, large, dalle) in enumerate(TA_ETAGES):
    ep = 12 - large
    xa, xb = X_TA_O, KK1 - ep
    n = 2 if etage == 2 else 3
    box(f"Corps_mur_HK_O_{etage}", xb, KK1, -Y_TA, Y_TA, z0, z0 + TA_VIDE + dalle,
        "50_Heikhal", MAT_MARBRE_HERODE())
    cellules = travees(-Y_TA, Y_TA, n, TA_REFEND)
    for k in range(n - 1):
        yb_ = cellules[k][1]
        refend(f"Ta_O_{etage}_refend_{k}", yb_, yb_ + TA_REFEND, xa, xb, z0, "y",
               "50_Heikhal", MAT_MARBRE_HERODE())
    dalle_percee(f"Ta_O_{etage}_dalle", xa, xb, -Y_TA, Y_TA, z0 + TA_VIDE,
                 z0 + TA_VIDE + dalle, "50_Heikhal", MAT_CEDRE(),
                 [(xa + 2, xa + 2 + TA_TREMIE, ya_ + 2, ya_ + 2 + TA_TREMIE) for ya_, _ in cellules],
                 alignees="y")
# Les murs qui enferment les ta'im, pleins sur toute la hauteur, et le toit des cellules
for cote, sg in (("N", 1), ("S", -1)):
    # Au sud la porte de l'étage traverse ; au nord, le ta du coin ouvre sur la messiba (4:3)
    vers_mesiba = [PORTE_ALIYAH] if cote == "S" else [PORTE_TA]
    passage = [PORTE_ALIYAH] if cote == "S" else []
    paroi_percee(f"Corps_mur_TA_{cote}", X_MES_O1, HK0, *sorted((sg * Y_TA, sg * Y_MUR_TA)),
                 Z_BAT, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE(),
                 baies_heikhal(*FENETRE_EXT) + vers_mesiba)
    paroi_percee(f"Corps_mur_{cote}_ext", BX_O, HK0, *sorted((sg * Y_MES, sg * Y_EXT)),
                 Z_BAT, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE(), baies_heikhal(*FENETRE_EXT))
    # Au-dessus du toit des ta'im, la bande redevient pleine jusqu'au mur du Heikhal
    paroi_percee(f"Corps_masse_{cote}", KK1, HK0, *sorted((sg * Y_INT, sg * Y_TA)),
                 Z_TA_TOIT + 5, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE(), passage)
    couches_middot(f"Ta_toit_{cote}", KK1, HK0, *sorted((sg * Y_INT, sg * Y_TA)), Z_TA_TOIT,
                   "50_Heikhal")
# Le nu extérieur d'ouest court sans interruption ; le mur intérieur du couloir, lui,
# s'ouvre là où les branches nord et sud de la messiba le traversent pour tourner.
box("Corps_mur_TA_O_ext", BX_O, X_MES_O0, -Y_EXT, Y_EXT, Z_BAT, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
# Ses bouts nord et sud sont déjà dans les murs extérieurs des bandes : seul le centre reste.
box("Corps_mur_TA_O_int", X_MES_O1, X_TA_O, -Y_MUR_TA, Y_MUR_TA, Z_BAT, Z_TOIT,
    "50_Heikhal", MAT_MARBRE_HERODE())
box("Corps_masse_O", X_TA_O, KK1, -Y_TA, Y_TA, Z_TA_TOIT + 5, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
couches_middot("Ta_toit_O", X_TA_O, KK1, -Y_TA, Y_TA, Z_TA_TOIT, "50_Heikhal")
rampe("Mesiba_nord", X_MES_O0, HK0, Y_MES - MESIBA_L, Y_MES, Z_MES[1], Z_MES[0], "+x",
      "50_Heikhal", MAT_MARBRE_HERODE(), MESIBA_EP)
rampe("Mesiba_ouest", X_MES_O0, X_MES_O1, -Y_MES, Y_MES, Z_MES[2], Z_MES[1], "+y",
      "50_Heikhal", MAT_MARBRE_HERODE(), MESIBA_EP)
rampe("Mesiba_sud", X_MES_O0, X_PORTE_ALIYAH, -Y_MES, -Y_MES + MESIBA_L, Z_MES[2], Z_MES[3], "+x",
      "50_Heikhal", MAT_MARBRE_HERODE(), MESIBA_EP)
# Le couloir est couvert : sans cela il ouvre une fente de quatre-vingt-dix amot sur le
# ciel au flanc du bâtiment. La hauteur sous plafond n'est pas donnée : huit amot au-dessus
# du haut de chaque branche, le reste plein jusqu'au toit — CHOIX.
for nom, xa, xb, ya, yb, z in (
        ("nord", X_MES_O0, HK0, Y_MES - MESIBA_L, Y_MES, Z_MES[1] + 8),
        ("ouest", X_MES_O0, X_MES_O1, -Y_MES, Y_MES, Z_MES[2] + 8),
        ("sud", X_MES_O0, X_PORTE_ALIYAH, -Y_MES, -Y_MES + MESIBA_L, Z_MES[3] + 8)):
    box(f"Mesiba_{nom}_couverture", xa, xb, ya, yb, z, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
# Le bout est de la bande sud n'est pas la messiba mais בֵּית הוֹרָדַת הַמַּיִם (Middot 4:7) :
# un canal, plein au-dessus. Les trois amot du palier restent ouvertes jusqu'à la porte.
box("Beit_horadat_hamayim_masse", PORTE_ALIYAH[1], HK0, -Y_MES, -Y_MES + MESIBA_L,
    Z_BAT + 6, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
box("Mesiba_palier", *PORTE_ALIYAH[:2], -Y_MES, -Y_MUR_TA,
    PORTE_ALIYAH[3], Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
# « וּבְפִתְחָהּ שֶׁל עֲלִיָּה הָיוּ שְׁנֵי כְלוֹנָסוֹת שֶׁל אֶרֶז, שֶׁבָּהֶן הָיוּ עוֹלִין לְגַגָּהּ שֶׁל עֲלִיָּה »
# (Middot 4:5) : deux perches de cèdre à la porte, et donc une trémie dans le toit au-dessus.
for k, x in enumerate((X_PORTE_ALIYAH + 1, X_PORTE_ALIYAH + 2)):
    cyl(f"Klonas_aliyah_{k}", x, -Y_INT + 1.5, Z_ETAGE_SOL, Z_ETAGE_HAUT + 1, 0.4,
        "50_Heikhal", MAT_CEDRE(), verts=12)


# --- L'étage. Le corps montait plein de 46 à 96 ; Middot 4:5-6 y met une pièce.
#     « וְגֹבַהּ שֶׁל עֲלִיָּה אַרְבָּעִים אַמָּה » (4:6), et le Rambam la dit bâtie : « וַעֲלִיָּה בְּנוּיָה
#     עַל גַּבָּיו, גֹּבַהּ כְּתָלֶיהָ אַרְבָּעִים אַמָּה » (Beit HaBe'hira 4:3). Elle est praticable : porte
#     au sud au bout de la מְסִבָּה, deux perches de cèdre pour monter sur son toit, une ligne
#     de bornes au sol qui y rejoue la séparation d'en bas, et des trappes vers le Kodesh
#     HaKodashim par où l'on descendait les ouvriers en caisses (4:5).
#     Au-dessus du Heikhal et du Kodesh HaKodashim, pas de l'Oulam : c'est là que Middot 4:5
#     la meuble, et Rashi (sur Divrei HaYamim II 3:4) met les עליות du Premier Temple
#     au-dessus de la Maison — « מִקַּרְקָעִית הַבַּיִת עַד קֵרוּי עֲלִיָּה רִאשׁוֹנָה שְׁלֹשִׁים, וּמֵעֲלִיָּה
#     לַעֲלִיָּה עַד גַּג הָעֶלְיוֹן תִּשְׁעִים ». Metsoudat David donne la même lecture en second.
#     Radak les met dans l'Oulam seul : minorité, et sur le Premier Temple.
# Les לוּלִין percent le plancher au-dessus du Kodesh HaKodashim. Middot 4:5 n'en donne ni
# le nombre ni la place : deux trémies de deux amot sur l'axe, CHOIX.
LOULIN = [(KK1 + 6, KK1 + 8, -1, 1), (KK1 + 12, KK1 + 14, -1, 1)]
couches_middot("Corps_plancher", KK1, HK0, -10, 10, Z_BAT + 40, "50_Heikhal", LOULIN)
couches_middot("Corps_toit", KK1, HK0, -10, 10, Z_ETAGE_HAUT, "50_Heikhal",
               [(X_PORTE_ALIYAH + 0.5, X_PORTE_ALIYAH + 2.5, -Y_INT + 0.5, -Y_INT + 2.5)])
# « רָאשֵׁי פִסְפָּסִין מַבְדִּילִים בָּעֲלִיָּה בֵּין הַקֹּדֶשׁ לְבֵין קֹדֶשׁ הַקֳּדָשִׁים » (Middot 4:5) : la ligne
# de bornes qui rejoue à l'étage l'ama de Traksin, restée en creux au-dessous.
for k, y in enumerate(plage(-9.5, 9.5, 1.0)):
    box(f"Pispassin_{k:02d}", TR1, TR0, y - 0.2, y + 0.2, Z_ETAGE_SOL, Z_ETAGE_SOL + 0.3,
        "50_Heikhal", MAT_MARBRE_HERODE())
# --- « כָּל הַבַּיִת טוּחַ בְּזָהָב, חוּץ מֵאַחַר הַדְּלָתוֹת » (Middot 4:1 ; Rambam Beit
#     HaBe'hira 4:7 : « וְהַפְּנִימִיּוֹת נִפְתָּחוֹת לְתוֹךְ הַבַּיִת לְכַסּוֹת אֲחוֹרֵי הַדְּלָתוֹת »).
#     L'or est un PLACAGE sur la face intérieure, jamais la matière du mur : le corps du
#     bâtiment reste en marbre apparent au-dehors (Baba Batra 4a), et une boîte ne porte
#     pas deux matières.
#     Rien derrière les battants : les extérieurs couvrent les faces de l'embrasure, les
#     intérieurs se rabattent dans le Heikhal pour couvrir la pierre nue du mur est
#     (Middot 4:1). Ni plaque ni relief sous les vingt amot de leur hauteur.
paroi_percee("Heikhal_or_mur_N", HK1, HK0, 10 - EPAISSEUR_PLACAGE, 10, Z_BAT, Z_BAT + 40,
             "50_Heikhal", MAT_OR_PLAQUE(), baies_heikhal(*FENETRE_INT))
paroi_percee("Heikhal_or_mur_S", HK1, HK0, -10, -10 + EPAISSEUR_PLACAGE, Z_BAT, Z_BAT + 40,
             "50_Heikhal", MAT_OR_PLAQUE(), baies_heikhal(*FENETRE_INT))
box("Heikhal_or_plafond", HK1, HK0, -10, 10, Z_BAT + 40 - EPAISSEUR_PLACAGE, Z_BAT + 40, "50_Heikhal", MAT_OR_PLAQUE())


def lambris_or(piece, x0, x1, col, faces_bout):
    """Ce qui articule une salle plaquée d'or : poutres de caissons sous le plafond,
    corniche et plinthe le long des murs. Le lambris de cèdre (fiche §8b) est derrière
    l'or, « כָּל הַבַּיִת טוּחַ בְּזָהָב » (Middot 4:1) : le relief est d'or lui aussi. Le
    relevé du plan 9b finissait sur un plafond qui n'était qu'un aplat.
    `faces_bout` : les faces est/ouest à ceinturer, (suffixe, xa, xb)."""
    haut = Z_BAT + 40 - EPAISSEUR_PLACAGE
    for k, x in enumerate(plage(x0 + 4, x1 - 2, 4)):
        box(f"{piece}_caisson_poutre_{k:02d}", x - 0.5, x + 0.5, -10 + EPAISSEUR_PLACAGE, 10 - EPAISSEUR_PLACAGE,
            Z_BAT + 39, haut, col, MAT_OR_PLAQUE())
    for k, y in enumerate((-10 / 3, 10 / 3)):
        box(f"{piece}_caisson_longrine_{k}", x0, x1, y - 0.4, y + 0.4, Z_BAT + 39.2, haut, col, MAT_OR_PLAQUE())
    for cote, ya, yb in (("N", 10 - 0.5, 10 - EPAISSEUR_PLACAGE), ("S", -10 + EPAISSEUR_PLACAGE, -10 + 0.5)):
        box(f"{piece}_corniche_{cote}", x0, x1, ya, yb, Z_BAT + 38, Z_BAT + 39, col, MAT_OR_PLAQUE())
        box(f"{piece}_plinthe_{cote}", x0, x1, (ya + yb) / 2 - 0.15, (ya + yb) / 2 + 0.15, Z_BAT, Z_BAT + 0.8, col, MAT_OR_PLAQUE())
    for suffixe, xa, xb in faces_bout:
        box(f"{piece}_corniche_{suffixe}", xa, xb, -10 + 0.5, 10 - 0.5, Z_BAT + 38, Z_BAT + 39, col, MAT_OR_PLAQUE())


lambris_or("Heikhal", HK1, HK0, "50_Heikhal", [("E", HK0 - 0.5, HK0 - EPAISSEUR_PLACAGE)])
for cote, signe in (("S", -1), ("N", 1)):
    # côté Heikhal : la face ouest du mur est, sur la largeur de la nef (20 amot)
    box(f"Heikhal_or_est_{cote}", HK0 - EPAISSEUR_PLACAGE, HK0, signe * 5, signe * 10,
        Z_BAT + 20, Z_BAT + 40, "50_Heikhal", MAT_OR_PLAQUE())
    # côté Oulam : « tout le mur autour d'elle », sur les 40 amot de hauteur de l'Oulam
    box(f"Ulam_or_est_{cote}", HX_E, HX_E + EPAISSEUR_PLACAGE, signe * 5, signe * 35,
        Z_BAT, Z_BAT + 40, "40_Ulam", MAT_OR_PLAQUE())
box("Heikhal_or_est_linteau", HK0 - EPAISSEUR_PLACAGE, HK0, -5, 5, Z_BAT + 20, Z_BAT + 40, "50_Heikhal", MAT_OR_PLAQUE())
box("Ulam_or_est_linteau", HX_E, HX_E + EPAISSEUR_PLACAGE, -5, 5, Z_BAT + 20, Z_BAT + 40, "40_Ulam", MAT_OR_PLAQUE())

# --- Ligne de toit (Middot 4:6) : מַעֲקֶה de 3 amot, puis אַמָּה כָּלֵה עוֹרֵב. Les deux
#     tiennent DANS les 100 amot : le garde-corps n'est pas posé sur un mur de 100, il
#     est ce qui monte de 96 à 99. R. Yehouda (là-bas) ne compte pas le kaleh orev dans
#     la mesure et donne 4 amot au maake ; le film suit le tana kama.
#     Le pourtour n'est pas un rectangle : l'Oulam déborde de 15 amot au nord et au sud
#     (Middot 4:7), et le toit décroche donc à l'aplomb du mur du Heikhal.
POURTOUR_TOIT = [
    ("est",         BX_E - MAAKE_EP, BX_E,         -50, 50),
    ("sud_oulam",   HX_E, BX_E - MAAKE_EP,            -50, -50 + MAAKE_EP),
    ("nord_oulam",  HX_E, BX_E - MAAKE_EP,            50 - MAAKE_EP, 50),
    ("retour_sud",  HX_E, HX_E + MAAKE_EP,            -50 + MAAKE_EP, -35 + MAAKE_EP),
    ("retour_nord", HX_E, HX_E + MAAKE_EP,            35 - MAAKE_EP, 50 - MAAKE_EP),
    ("sud_corps",   BX_O, HX_E,                       -35, -35 + MAAKE_EP),
    ("nord_corps",  BX_O, HX_E,                       35 - MAAKE_EP, 35),
    ("ouest",       BX_O, BX_O + MAAKE_EP,            -35 + MAAKE_EP, 35 - MAAKE_EP),
]
# Le kaleh orev est une LAME, pas une rangée de pointes. Le Rambam le décrit sur place
# (commentaire sur Middot 4:6) : « שֶׁהָיָה מַקִּיף הַהֵיכָל לְמַעְלָה מִן הַמַּעֲקֶה מֵאַרְבַּע רוּחוֹתָיו
# בְּחֶשֶׁק שֶׁל בַּרְזֶל גֹּבַהּ אַמָּה חַד כְּמוֹ הַסַּיִף, כְּדֵי שֶׁלֹּא יֵשֵׁב עָלָיו שׁוּם עוֹף עַל הַהֵיכָל,
# מִפְּנֵי שֶׁנֶּחְתָּכִים רַגְלָיו בְּאוֹתוֹ הַסַּיִף » — un cerclage de FER d'une ama, continu sur les
# quatre côtés, affilé comme une épée. Le blockout en faisait une lisse de bronze
# hérissée d'une pointe par ama — une lecture qui ne vient d'aucune source juive.
# Le fil n'est pas modélisé : à 0,05 ama d'épaisseur la lame tient dans deux
# pixels sur la façade entière, et l'affûtage est sous le pixel.
LAME_EP = 0.10
for suffixe, xa, xb, ya, yb in POURTOUR_TOIT:
    box(f"Maake_{suffixe}", xa, xb, ya, yb, Z_TOIT, Z_TOIT + MAAKE_H, "50_Heikhal", MAT_MARBRE_HERODE())
    if (xb - xa) >= (yb - ya):
        c = (ya + yb) / 2
        box(f"Kaleh_orev_{suffixe}", xa, xb, c - LAME_EP / 2, c + LAME_EP / 2,
            Z_TOIT + MAAKE_H, Z_FAITE, "50_Heikhal", MAT_FER_LAME())
    else:
        c = (xa + xb) / 2
        box(f"Kaleh_orev_{suffixe}", c - LAME_EP / 2, c + LAME_EP / 2, ya, yb,
            Z_TOIT + MAAKE_H, Z_FAITE, "50_Heikhal", MAT_FER_LAME())
