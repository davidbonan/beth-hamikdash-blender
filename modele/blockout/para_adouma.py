from .primitives.parametres import Z_HAR
from .primitives.matieres import MAT_BOIS_MAARAKHA, MAT_CEDRE, MAT_EAU, MAT_MURAILLE, MAT_PIERRE, MAT_ROC_TAILLE
from .primitives.volumes import arc, box, extrusion, mesh_from_pydata, plage, revolution, revolution_axe
from .primitives.ouvrages import PORTE_LISHKA, Porte, escalier, lishka, massif_evide
from .har_habayit import HX1, MIZRAHI_Y, MUR_HAR
from .heil import HEIL_MARCHES, SX1, SY1
from .ezrat_nashim import EX1
from .pays.calage import sol_naturel


# ----------------------------------------------------------------------------
# 21 — LE CHEMIN DE LA PARA ADOUMA, du Beit Even au mont des Oliviers
# ----------------------------------------------------------------------------
COL = "00_HarHabayit"

# « מַפְרִישִׁין כֹּהֵן הַשּׂוֹרֵף אֶת הַפָּרָה מִבֵּיתוֹ לַלִּשְׁכָּה שֶׁעַל פְּנֵי הַבִּירָה, צָפוֹנָה מִזְרָחָה, וּבֵית אֶבֶן
# הָיְתָה נִקְרֵאת » (Para 3:1) ; « לְפִי שֶׁכָּל מַעֲשֶׂיהָ הָיוּ בִכְלֵי גְלָלִים כְּלֵי אֲבָנִים » (Bartenura). La בירה
# étant le Mikdash (Bartenura, second avis), la chambre fait face à son angle nord-est, au-delà du
# Soreg. Place, taille, porte et mobilier de pierre : CHOIX.
EVEN_X0, EVEN_X1 = SX1 + 11, SX1 + 31
EVEN_Y0, EVEN_Y1 = SY1 + 8, SY1 + 24
lishka("Beit_Even", EVEN_X0, EVEN_X1, EVEN_Y0, EVEN_Y1, Z_HAR, Z_HAR + 20, COL,
       [Porte("S", *PORTE_LISHKA, Z_HAR)], mat=MAT_PIERRE())
box("Beit_Even_banc", EVEN_X0 + 3, EVEN_X0 + 9, EVEN_Y1 - 5, EVEN_Y1 - 2.5, Z_HAR, Z_HAR + 1.2, COL, MAT_PIERRE())
box("Beit_Even_tablette", EVEN_X1 - 6, EVEN_X1 - 2, EVEN_Y1 - 3, EVEN_Y1 - 2, Z_HAR, Z_HAR + 1.8, COL, MAT_PIERRE())
JARRE = [(0.35, 0), (0.55, 0.4), (0.6, 1.0), (0.45, 1.5), (0.25, 1.7), (0.3, 1.85), (0.22, 1.85), (0.18, 1.6), (0, 1.6)]
for k, x in enumerate((EVEN_X1 - 9, EVEN_X1 - 7.6)):
    revolution(f"Beit_Even_jarre_{k}", x, EVEN_Y1 - 3.2, Z_HAR, JARRE, COL, MAT_PIERRE(), verts=20)
for k, x in enumerate(plage(EVEN_X1 - 5.6, EVEN_X1 - 2.4, 1.0)):
    revolution(f"Beit_Even_coupe_{k}", x, EVEN_Y1 - 2.5, Z_HAR + 1.8,
               [(0.12, 0), (0.2, 0.25), (0.16, 0.25), (0.1, 0.05), (0, 0.05)], COL, MAT_PIERRE(), verts=16)

# « קִילוּלִים שֶׁל אֶבֶן הָיוּ קְבוּעִים בְּכֹתֶל מַעֲלוֹת שֶׁל עֶזְרַת נָשִׁים, וְכִסּוּיֵיהֶם שֶׁל אֶבֶן נִרְאוֹת בַּחֵיל, וּבְתוֹכָן
# אֵפֶר מִכָּל פָּרָה וּפָרָה » (Tosefta, citée par le Rash et Tosfot Yom Tov sur Para 3:3) ; « וְכֵן הָיוּ מַצְנִיעִין
# מֵאֵפֶר כָּל פָּרָה וּפָרָה שֶׁשּׂוֹרְפִין בַּחֵיל » (Rambam Para Adouma 3:4). Un couvercle par para — « וְתֵשַׁע פָּרוֹת
# אֲדֻמּוֹת נַעֲשׂוּ » (ibid.) —, dans la contremarche du premier degré du 'Heil, au nord de la porte de
# l'Ezrat Nashim. Nombre, taille et place : CHOIX ; les jarres restent dans la pierre.
KELAL_X = EX1 + 5 + 0.5 * HEIL_MARCHES
for k in range(9):
    revolution_axe(f"Kelal_{k}", (KELAL_X, 8.0 + k, Z_HAR + 0.25), (1, 0, 0),
                   [(0.2, 0), (0.2, 0.03), (0.08, 0.05), (0.08, 0.1), (0, 0.1)], COL, MAT_PIERRE(), verts=20)

# « הַר הַבַּיִת וְהָעֲזָרוֹת, תַּחְתֵּיהֶם חָלוּל מִפְּנֵי קֶבֶר הַתְּהוֹם » (Para 3:3) : « הָיוּ בוֹנִים אוֹתוֹ עַל גַּבֵּי כִפִּין, שֶׁאֲפִלּוּ
# יֵשׁ קֶבֶר תַּחְתֵּיהֶן הֶחָלָל מַפְסִיקוֹ » (Bartenura sur 3:2). Le vide court sous tout le Har HaBayit ; la scène
# n'en ouvre qu'un tronçon, sous l'axe, entre le Soreg et Sha'ar Shushan : trois nefs voûtées sur
# deux arcades. Comme la galerie de Parva, une doublure posée dans le soubassement plein. Tronçon,
# nefs, hauteurs : CHOIX.
CH_X0, CH_X1 = SX1 + 5, HX1 - MUR_HAR - 3
CH_NEF, CH_PILE, CH_EP = 10, 1.5, 0.5
CH_Y = 1.5 * CH_NEF
CH_HAUT = Z_HAR - 1.5            # sous le soubassement, qui s'arrête une ama sous le dallage
CH_NAISSANCE = CH_HAUT - 2.5     # les berceaux surbaissés de deux amot de flèche
CH_SOL = Z_HAR - 12


def doublure(nom, x0, x1, y0, y1, z0, z1):
    box(nom, x0, x1, y0, y1, z0, z1, COL, MAT_ROC_TAILLE())


def profil_d_arcade(x0, x1, bas, haut, portee, pile, pied, decalage=0.0):
    """Le profil (x, z), sens direct, d'un mur d'arches de x0 à x1 entre `bas(x)` et `haut(x)` : des
    baies en plein cintre de `portee`, au pas de portée + pile depuis x0 + `decalage`, qui naissent
    `pied` au-dessus de la base. Une baie dont la clé ne tient pas sous `haut` n'est pas percée."""
    pas, r = portee + pile, portee / 2
    baies = [c for c in plage(x0 + decalage + pas / 2, x1, pas) if x0 + pile / 2 <= c - r and c + r <= x1 - pile / 2]
    contour = [(x0, bas(x0))]
    for c in baies:
        naissance = bas(c) + pied
        if naissance + r > haut(c) - 0.25:
            continue
        contour += [(c - r, bas(c - r))] + arc(c, r, naissance, r) + [(c + r, bas(c + r))]
    return contour + [(x1, bas(x1)), (x1, haut(x1)), (x0, haut(x0))]


def mur_d_arcades(nom, profil, y0, y1, mat):
    """Le profil (x, z) épaissi de y0 à y1 : ses baies traversent le mur."""
    mesh_from_pydata(nom, *extrusion(profil, (0.0, y0), (0.0, 1.0), (1.0, 0.0), y1 - y0), COL, mat)


doublure("Chalal_sol", CH_X0 - CH_EP, CH_X1 + CH_EP, -CH_Y - CH_EP, CH_Y + CH_EP, CH_SOL - CH_EP, CH_SOL)
for cote, x0, x1 in (("O", CH_X0 - CH_EP, CH_X0), ("E", CH_X1, CH_X1 + CH_EP)):
    doublure(f"Chalal_fond_{cote}", x0, x1, -CH_Y, CH_Y, CH_SOL, CH_HAUT)
for cote, s in (("S", -1), ("N", 1)):
    doublure(f"Chalal_paroi_{cote}", CH_X0, CH_X1, *sorted((s * CH_Y, s * (CH_Y + CH_EP))), CH_SOL, CH_NAISSANCE)
    y = s * CH_NEF / 2
    mur_d_arcades(f"Chalal_arcade_{cote}",
                  profil_d_arcade(CH_X0, CH_X1, lambda x: CH_SOL, lambda x: CH_NAISSANCE, 8.5, CH_PILE, 3.25),
                  y - CH_PILE / 2, y + CH_PILE / 2, MAT_ROC_TAILLE())
for k, (y0, y1) in enumerate(((-CH_Y, -CH_NEF / 2), (-CH_NEF / 2, CH_NEF / 2), (CH_NEF / 2, CH_Y))):
    intrados = arc((y0 + y1) / 2, (y1 - y0) / 2, CH_NAISSANCE, 2.0, segments=10)
    mesh_from_pydata(f"Chalal_voute_{k}",
                     *extrusion([(y1, CH_HAUT + CH_EP), (y0, CH_HAUT + CH_EP)] + intrados,
                                (CH_X0, 0.0), (1.0, 0.0), (0.0, 1.0), CH_X1 - CH_X0), COL, MAT_ROC_TAILLE())


# « וְכֶבֶשׁ הָיוּ עוֹשִׂין מֵהַר הַבַּיִת לְהַר הַמִּשְׁחָה, כִּפִּין עַל גַּבֵּי כִפִּין, וְכִפָּה כְנֶגֶד הָאֹטֶם, מִפְּנֵי קֶבֶר הַתְּהוֹם »
# (Para 3:6), par la porte est, « שֶׁבּוֹ כֹּהֵן גָּדוֹל הַשּׂוֹרֵף אֶת הַפָּרָה… יוֹצְאִים לְהַר הַמִּשְׁחָה » (Middot 1:3).
# « כִּפָּה עַל כָּל שְׁנֵי כִפִּין כְּדֵי שֶׁיִּהְיוּ שְׁנֵי רַגְלֵי הַכִּפָּה עַל גַּג שְׁנֵי כִפִּין שֶׁתַּחְתֶּיהָ » (Rambam Para Adouma 3:1) :
# chaque étage décalé d'une demi-travée, ses piles sur les clés de celui du dessous. Le tablier part du
# seuil de Sha'ar Shushan et monte en ligne droite, toujours DEGAGEMENT au-dessus du relief, jusqu'au
# lieu de la sereifa ; il tient sous la ligne de mire du cohen vers le Heikhal (Middot 2:4), qui part
# plus haut et descend moins vite. Largeur (celle de la porte), travée, étages, garde-corps : CHOIX.
KEVESH_Y0, KEVESH_Y1 = MIZRAHI_Y - 5, MIZRAHI_Y + 5
LARGEUR_KEVESH = KEVESH_Y1 - KEVESH_Y0
KEVESH_X0 = HX1
DEGAGEMENT = 10
ETAGE, PORTEE, PILE, PIED = 16, 12, 4, 8
# Au sommet, sur l'axe, le point haut du mont des Oliviers en face de la porte est.
SEREIFA_X0, SEREIFA_X1, SEREIFA_Y = 1620, 1700, 20
_PAS_DU_RELIEF = 5


def _sol_sous(x, y0, y1):
    return max(sol_naturel(x, y) for y in plage(y0, y1 + 0.01, (y1 - y0) / 4))


Z_SEREIFA = max(_sol_sous(x, -SEREIFA_Y, SEREIFA_Y) for x in plage(SEREIFA_X0, SEREIFA_X1 + 0.01, _PAS_DU_RELIEF)) + 12


def _enveloppe(points):
    """L'enveloppe convexe supérieure de points rangés par x croissant."""
    haut = []
    for p in points:
        while len(haut) >= 2 and ((haut[-1][0] - haut[-2][0]) * (p[1] - haut[-2][1])
                                  - (haut[-1][1] - haut[-2][1]) * (p[0] - haut[-2][0])) >= 0:
            haut.pop()
        haut.append(p)
    return haut


TABLIER = _enveloppe([(KEVESH_X0, Z_HAR)]
                     + [(x, _sol_sous(x, KEVESH_Y0, KEVESH_Y1) + DEGAGEMENT)
                        for x in plage(KEVESH_X0 + _PAS_DU_RELIEF, SEREIFA_X0, _PAS_DU_RELIEF)]
                     + [(SEREIFA_X0, Z_SEREIFA)])


def tablier(x):
    """La cote du dessus du kevesh en x."""
    for (x0, z0), (x1, z1) in zip(TABLIER, TABLIER[1:]):
        if x0 <= x <= x1:
            return z0 + (z1 - z0) * (x - x0) / (x1 - x0)
    raise ValueError(f"x = {x} hors du kevesh")


SOL_DU_KEVESH = [(x, _sol_sous(x, KEVESH_Y0, KEVESH_Y1)) for x in plage(KEVESH_X0, SEREIFA_X0 + 0.01, 2)]


def _etendues(k):
    """Les x où l'étage k, compté depuis le tablier, sort du relief : (début, fin)."""
    dehors = [x for x, sol in SOL_DU_KEVESH if sol < tablier(x) - ETAGE * k - 1]
    etendues, debut = [], None
    for a, b in zip(dehors, dehors[1:] + [None]):
        debut = a if debut is None else debut
        if b is None or b - a > 2.01:
            etendues.append((debut, a))
            debut = None
    return etendues


def _cassures(x0, x1, cote):
    """Les sommets du tablier entre x0 et x1, décalés à la cote `cote(x)`, par x croissant."""
    return [(x, cote(x)) for x, _ in TABLIER if x0 < x < x1]


def _avec_cassures(profil, x0, x1, haut):
    """Le haut d'un profil d'arcade passe par les sommets du tablier qui tombent entre x0 et x1."""
    return profil[:-1] + _cassures(x0, x1, haut)[::-1] + profil[-1:]


k = 0
while etendues := _etendues(k):
    for n, (x0, x1) in enumerate(etendues):
        haut = lambda x, k=k: tablier(x) - ETAGE * k
        bas = lambda x, k=k: tablier(x) - ETAGE * (k + 1)
        profil = profil_d_arcade(x0, x1, bas, haut, PORTEE, PILE, PIED, decalage=(k % 2) * (PORTEE + PILE) / 2)
        mur_d_arcades(f"Kevesh_HaPara_etage_{k}_{n}", _avec_cassures(profil, x0, x1, haut),
                      KEVESH_Y0, KEVESH_Y1, MAT_MURAILLE())
    k += 1
for cote, y0, y1 in (("S", KEVESH_Y0, KEVESH_Y0 + 0.75), ("N", KEVESH_Y1 - 0.75, KEVESH_Y1)):
    dessus = lambda x: tablier(x) + 1
    garde = ([(KEVESH_X0, tablier(KEVESH_X0))] + _cassures(KEVESH_X0, SEREIFA_X0, tablier)
             + [(SEREIFA_X0, tablier(SEREIFA_X0)), (SEREIFA_X0, dessus(SEREIFA_X0))]
             + _cassures(KEVESH_X0, SEREIFA_X0, dessus)[::-1] + [(KEVESH_X0, dessus(KEVESH_X0))])
    mur_d_arcades(f"Kevesh_HaPara_garde_corps_{cote}", garde, y0, y1, MAT_MURAILLE())


# Au mont des Oliviers : « וּבֵית טְבִילָה הָיָה שָׁם » (Para 3:7), « וְאוֹתוֹ בֵית הַטְּבִילָה נַמִּי חָלוּל הָיָה עַל גַּבֵּי
# כִפִּין… וְאַף מְקוֹם מַעֲרַכְתָּהּ וְגִתָּהּ… כֻּלָּן עַל גַּבֵּי כִפִּין » (Bartenura). La ma'arakha « כְּמִין מִגְדָּל, וּמְפַתְּחִין
# בָּהּ חַלּוֹנוֹת, וַחֲזִיתָהּ מַעֲרָבָה » (Para 3:8), « רְחָבָה מִלְּמַטָּה וְצָרָה מִלְמַעְלָה » (Bartenura), dans sa fosse — « וְעָמַד
# חוּץ מִגִּתָּהּ » (Para 3:10). Le cohen, à l'est, égorge la para posée dessus et asperge vers le Heikhal
# (Para 3:9), puis « יָרַד וְהִצִּית » : la fosse est assez profonde pour que le haut du bûcher affleure
# la plateforme, et il y descend par l'est. Plateforme, fosse, mikve, bûcher : CHOIX.
SOUS_SEREIFA = 6
GAT = (1642.0, 1660.0, -5.0, 5.0)
MIKVE_SEREIFA = (1664.0, 1672.0, 9.0, 15.0)
_sol_bas = min(_sol_sous(x, -SEREIFA_Y, SEREIFA_Y) for x in plage(SEREIFA_X0, SEREIFA_X1 + 0.01, _PAS_DU_RELIEF))
mur_d_arcades("Sereifa_plateforme_arcades",
              profil_d_arcade(SEREIFA_X0, SEREIFA_X1, lambda x: _sol_bas - 2, lambda x: Z_SEREIFA - SOUS_SEREIFA,
                              6, 2, Z_SEREIFA - SOUS_SEREIFA - 4 - (_sol_bas - 2)),
              -SEREIFA_Y, SEREIFA_Y, MAT_MURAILLE())
massif_evide("Sereifa_plateforme", SEREIFA_X0, SEREIFA_X1, -SEREIFA_Y, SEREIFA_Y, Z_SEREIFA - SOUS_SEREIFA, Z_SEREIFA,
             [(*GAT, Z_SEREIFA - SOUS_SEREIFA, Z_SEREIFA), (*MIKVE_SEREIFA, Z_SEREIFA - SOUS_SEREIFA, Z_SEREIFA)],
             COL, MAT_MURAILLE())
escalier("Sereifa_gat_escalier", GAT[1] - 4, GAT[1], -2, 2, Z_SEREIFA - SOUS_SEREIFA, Z_SEREIFA, "-x", COL, MAT_MURAILLE())

MX0, MX1, MY0, MY1 = MIKVE_SEREIFA
box("Sereifa_mikve_fond", MX0, MX1, MY0, MY1, Z_SEREIFA - SOUS_SEREIFA, Z_SEREIFA - 4, COL, MAT_MURAILLE())
escalier("Sereifa_mikve_degres", MX0, MX1, MY0, MY0 + 2.5, Z_SEREIFA - 4, Z_SEREIFA, "+y", COL, MAT_MURAILLE())
box("Sereifa_mikve_eau", MX0, MX1, MY0 + 2.5, MY1, Z_SEREIFA - 4, Z_SEREIFA - 1, COL, MAT_EAU())

# Le bûcher : des lits de bûches croisés qui se resserrent en montant, cèdre et résineux en
# alternance, les vides entre les bûches pour fenêtres.
BUCHER_X, BUCHER_Y, BUCHER_H, BUCHE = GAT[0] + 6, 0.0, SOUS_SEREIFA - 0.5, 0.45
lits = round(BUCHER_H / BUCHE)
for k in range(lits):
    demi = 3.0 - 1.5 * k / (lits - 1)
    z = Z_SEREIFA - SOUS_SEREIFA + k * BUCHE
    for j, u in enumerate(plage(-demi + BUCHE / 2, demi, 2 * demi / 3.6)):
        x0, x1, y0, y1 = ((BUCHER_X - demi, BUCHER_X + demi, BUCHER_Y + u - BUCHE / 2, BUCHER_Y + u + BUCHE / 2)
                          if k % 2 else (BUCHER_X + u - BUCHE / 2, BUCHER_X + u + BUCHE / 2, BUCHER_Y - demi, BUCHER_Y + demi))
        box(f"Sereifa_maarakha_{k:02d}_{j}", x0, x1, y0, y1, z, z + BUCHE * 0.95, COL,
            (MAT_CEDRE if k % 2 else MAT_BOIS_MAARAKHA)())


def sur_le_chemin_de_la_para(anneau, marge=2.0):
    """Ce qu'un anneau de la ville moderne recouvre du kevesh ou de la plateforme de la sereifa."""
    xs, ys = [x for x, _ in anneau], [y for _, y in anneau]
    return any(min(xs) < x1 + marge and max(xs) > x0 - marge and min(ys) < y1 + marge and max(ys) > y0 - marge
               for x0, x1, y0, y1 in ((KEVESH_X0, SEREIFA_X0, KEVESH_Y0, KEVESH_Y1),
                                      (SEREIFA_X0, SEREIFA_X1, -SEREIFA_Y, SEREIFA_Y)))
