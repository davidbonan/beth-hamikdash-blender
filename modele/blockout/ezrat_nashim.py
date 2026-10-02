import math

from .primitives.parametres import CANDELABRES_SHOEVA, Z_EZN, Z_HAR
from .primitives.matieres import (MAT_BOIS_MAARAKHA, MAT_BRONZE, MAT_CEDRE, MAT_CHENE, MAT_EAU, MAT_ECHELLE,
                                  MAT_LECHEM, MAT_OR, MAT_PIERRE, MAT_TERRE_CUITE, braise)
from .primitives.volumes import (BALUSTRE, alea, box, colonne_cannelee, cone, cyl, cyl_between, graver,
                                 mur_perce, plage, prism, revolution, tube_between)
from .primitives.gravures import bandeau_fleurons
from .primitives.ouvrages import (BANDEAU, CORNICHE, ENCADREMENT_SHAAR, FILET_OR, PILASTRE_CHAPITEAU,
                                  SAILLIE_BANDEAU, SAILLIE_MOULURE, SOCLE, battants, ceinture, moulure,
                                  pilastre, shaar)
from .har_habayit import HX1, MUR_HAR


# ----------------------------------------------------------------------------
# 10 — EZRAT NASHIM (135 × 135), Middot 2:5
# ----------------------------------------------------------------------------
EX0, EX1 = 5, 140          # commence après le mur est de l'Azara (0..5)
# « כָּל הַשְּׁעָרִים שֶׁהָיוּ שָׁם, הָיוּ לָהֶן שְׁקוֹפוֹת » (Middot 2:3) : chaque שער a son linteau, et
# la même michna donne vingt amot à la baie. Un mur de vingt n'en laisse donc AUCUN —
# la porte est n'avait plus qu'un linteau d'un centième d'ama, ce qui est un artefact de
# modèle et non une porte. Aucune source ne donne la hauteur de ce mur : il prend celle
# de l'Azara, qui est le premier nombre disponible qui laisse la michna tenir.
H_MUR_EN = 25
box("EzratNashim_mur_nord", EX0, EX1 + 5, 67.5, 72.5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_mur_sud", EX0, EX1 + 5, -72.5, -67.5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_mur_est_S", EX1, EX1 + 5, -72.5, -5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_mur_est_N", EX1, EX1 + 5, 5, 72.5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_porte_est_linteau", EX1, EX1 + 5, -5, 5, Z_EZN + 20, Z_EZN + H_MUR_EN, "10_EzratNashim")
# Quatre chambres d'angle 40 × 40, sans toit (murs de MUR_LISHKA_EN amot, CHOIX) — « ולא היו מקורות »
# (Middot 2:5, qui les rattache aux « חצרות קטורות » d'Ezekiel 46:21-22). Affectations
# par angle : Middot 2:5. CHOIX : la Mishna ne décrit aucune porte, seulement des
# usages qui la supposent (les nazirs y cuisent, les metzoraim s'y immergent) ;
# quatre murs aveugles ne sont pas une lishka mais une fosse. Chacune s'ouvre donc
# sur la cour, par la face tournée vers l'axe. Cote inventée (6 × 12) : Middot 2:3
# donne 10 × 20 à « tous les pesa'him et tous les shearim », mais une porte de 20 ne
# tient pas dans un mur de 15 — la hauteur de ces murs n'est elle-même dans aucune
# source.
#
# Elles restent DÉCOUVERTES, et c'est la seule chose ici qui ne soit pas un choix :
# « וְלֹא הָיוּ מְקוֹרוֹת. וְכָךְ הֵם עֲתִידִים לִהְיוֹת » (Middot 2:5) — pas de toit, et pas
# davantage dans le Temple à venir, qui est celui que le film bâtit. Ce qu'on peut leur
# donner, c'est le couronnement de leurs murs : les quatre crêtes s'arrêtaient net et
# se lisaient en boîtes découpées, ce que le reste de l'enceinte ne fait nulle part.
H_LISHKA_EN = 15
MUR_LISHKA_EN = 3
SOUS_CORNICHE_LISHKA_EN = Z_EZN + H_LISHKA_EN + min(zb for zb, _, _ in CORNICHE)
# Le cadre d'une porte de chambre porte ses deux timorot à l'échelle de son jambage
# (TIMORA_SUR_CADRE) : à 1,5 ama de cadre elles ne se voyaient pas de la cour.
CADRE_LISHKA_EN = 2.5
CRETE_LISHKA_EN = Z_EZN + H_LISHKA_EN + max(zh for _, zh, _ in CORNICHE)
PAREMENT_LIBRE_LISHKA_EN = (Z_EZN + max(zh for _, zh, _ in SOCLE), SOUS_CORNICHE_LISHKA_EN - PILASTRE_CHAPITEAU)
Z_BANDEAU_LISHKA_EN = (sum(PAREMENT_LIBRE_LISHKA_EN) - max(zh for _, zh, _ in BANDEAU)) / 2
for nm, xa, ya, cour in (("Nezirim_SE", EX1 - 40, -67.5, "N"), ("Etzim_NE", EX1 - 40, 27.5, "S"),
                         ("Metzoraim_NO", EX0, 27.5, "S"), ("Shemanya_SO", EX0, -67.5, "N")):
    xb, yb = xa + 40, ya + 40
    parois = {"S": ("x", ya, -1), "N": ("x", yb, 1), "O": ("y", xa, -1), "E": ("y", xb, 1)}
    e = MUR_LISHKA_EN
    for a, b, c, d, side in ((xa, xb, ya, ya + e, "S"), (xa, xb, yb - e, yb, "N"),
                             (xa, xa + e, ya, yb, "O"), (xb - e, xb, ya, yb, "E")):
        nom = f"Lishkat_{nm}_{side}"
        if side == cour:
            mur_perce(nom, a, b, c, d, Z_EZN, Z_EZN + H_LISHKA_EN, "10_EzratNashim",
                      [((a + b) / 2, 6)], 12)
            # Un פתח de chambre n'est pas un שער : Middot 2:3 ne le change pas en or, et
            # il ne reçoit qu'un cadre de pierre.
            shaar(f"{nom}_cadre", parois[side], (a + b) / 2, Z_EZN, SOUS_CORNICHE_LISHKA_EN, e,
                  "10_EzratNashim", MAT_PIERRE(), largeur=6, hauteur=12, cadre=CADRE_LISHKA_EN)
        else:
            box(nom, a, b, c, d, Z_EZN, Z_EZN + H_LISHKA_EN, "10_EzratNashim")
    ceinture(f"Lishkat_{nm}_couronnement", xa, xb, ya, yb, e,
             Z_EZN + H_LISHKA_EN, CORNICHE, "10_EzratNashim",
             filet=MAT_OR() if FILET_OR else None)
    milieu = (xa + xb) / 2 if cour in "SN" else (ya + yb) / 2
    ceinture(f"Lishkat_{nm}_socle", xa, xb, ya, yb, e, Z_EZN, SOCLE, "10_EzratNashim",
             baies={cour: [(milieu - 3, milieu + 3)]})
    # Le bandeau partage le parement libre en deux panneaux égaux. Calé sur la gezuztra, il
    # tombait aux deux tiers d'un mur de quinze amot et se collait aux chapiteaux.
    ceinture(f"Lishkat_{nm}_bandeau", xa, xb, ya, yb, e, Z_BANDEAU_LISHKA_EN, BANDEAU, "10_EzratNashim",
             saillie=SAILLIE_BANDEAU, baies={cour: [(milieu - 3, milieu + 3)]})
    # Pilastres aux deux bouts des deux faces tournées vers la cour, et au milieu de celle
    # qui n'a pas de porte.
    axe_cour = "O" if xa > EX0 else "E"
    for side in (cour, axe_cour):
        u0, u1 = (xa, xb) if side in "SN" else (ya, yb)
        positions = [u0 + 1.25, u1 - 1.25] + ([(u0 + u1) / 2] if side != cour else [])
        for k, u in enumerate(positions):
            pilastre(f"Lishkat_{nm}_pilastre_{side}{k}", parois[side], u, Z_EZN,
                     SOUS_CORNICHE_LISHKA_EN, "10_EzratNashim")
# Ce que la Michna met DANS ces chambres. Elles étaient quatre boîtes vides : leurs
# usages sont pourtant donnés un par un (Middot 2:5), et ce sont eux qui apportent à
# l'Ezrat Nashim les quatre matières qu'elle n'a pas — l'eau, le bois, le feu, la terre
# cuite. Les cotes du mobilier sont partout des CHOIX : aucune source ne les donne.
#
# NORD-EST, Lishkat HaEtzim : « הַכֹּהֲנִים בַּעֲלֵי מוּמִין מַתְלִיעִין הָעֵצִים, וְכָל עֵץ שֶׁנִּמְצָא
# בּוֹ תּוֹלַעַת פָּסוּל מֵעַל גַּבֵּי הַמִּזְבֵּחַ ». Le bois trié est celui de la ma'arakha —
# figuier, noyer et עֵץ שָׁמֶן (Tamid 2:3) —, d'où MAT_BOIS_MAARAKHA et pas le chêne clair.
for _s, _x in enumerate((105.5, 116.0, 126.5)):
    for _l in range(5):
        _z = Z_EZN + 0.3 + _l * 0.62
        for _k in range(5):
            if _l % 2 == 0:
                _y = 58.0 + _k * 0.65
                cyl_between(f"Lishkat_Etzim_NE_bois_{_s}{_l}{_k}", (_x, _y, _z), (_x + 8, _y, _z),
                            0.3, "10_EzratNashim", MAT_BOIS_MAARAKHA(), verts=6)
            else:
                _xk = _x + 0.6 + _k * 1.8
                cyl_between(f"Lishkat_Etzim_NE_bois_{_s}{_l}{_k}", (_xk, 57.7, _z), (_xk, 60.9, _z),
                            0.3, "10_EzratNashim", MAT_BOIS_MAARAKHA(), verts=6)
# Le tri lui-même : le vrac qui arrive près de la porte, les billots des cohanim qui l'examinent
# — hors de l'Azara, rien n'interdit de s'asseoir —, et le bois véreux écarté à part. CHOIX :
# places, nombres, et que le rebut attende là.
for _tas, (_cx, _cy, _n) in (("vrac", (112.0, 42.0, 14)), ("pasoul", (130.0, 38.0, 8))):
    for _k in range(_n):
        _cle = f"Lishkat_Etzim_NE_{_tas}_{_k}"
        _a, _r = math.tau * alea(_cle), 2.5 * alea(_cle, 1)
        _cap, _long = math.pi * alea(_cle, 2), 3 + 3 * alea(_cle, 3)
        _x, _y, _z = _cx + _r * math.cos(_a), _cy + _r * math.sin(_a), Z_EZN + 0.3 + 0.55 * (_k // 5)
        _dx, _dy = _long / 2 * math.cos(_cap), _long / 2 * math.sin(_cap)
        cyl_between(_cle, (_x - _dx, _y - _dy, _z), (_x + _dx, _y + _dy, _z),
                    0.3, "10_EzratNashim", MAT_BOIS_MAARAKHA(), verts=6)
for _k in range(3):
    _a = math.radians(200 + 70 * _k)
    cyl(f"Lishkat_Etzim_NE_billot_{_k}", 112 + 6.5 * math.cos(_a), 42 + 6.5 * math.sin(_a),
        Z_EZN, Z_EZN + 1.2, 0.7, "10_EzratNashim", MAT_CHENE(), verts=12)
# SUD-EST, Lishkat HaNezirim : « מְבַשְּׁלִין אֶת שַׁלְמֵיהֶן, וּמְגַלְּחִין אֶת שְׂעָרָן,
# וּמְשַׁלְּחִים תַּחַת הַדּוּד » — le chaudron et son foyer. C'est le seul feu de l'Ezrat
# Nashim en dehors de Simhat Beit HaShoeva.
DOUD_X, DOUD_Y = 120.0, -48.0
for _nm, _a, _b, _c, _d in (("S", -4, 4, -4, -3), ("N", -4, 4, 3, 4),
                            ("O", -4, -3, -3, 3), ("E", 3, 4, -3, 3)):
    box(f"Lishkat_Nezirim_SE_foyer_{_nm}", DOUD_X + _a, DOUD_X + _b, DOUD_Y + _c, DOUD_Y + _d,
        Z_EZN, Z_EZN + 2.4, "10_EzratNashim")
box("Lishkat_Nezirim_SE_braises", DOUD_X - 3, DOUD_X + 3, DOUD_Y - 3, DOUD_Y + 3,
    Z_EZN + 0.1, Z_EZN + 0.5, "10_EzratNashim", braise("Braise"))
revolution("Lishkat_Nezirim_SE_doud", DOUD_X, DOUD_Y, Z_EZN + 2.4,
           [(0.0, 0.0), (1.8, 0.4), (2.6, 1.6), (2.7, 2.4), (2.5, 2.45),
            (2.4, 1.7), (1.6, 0.5), (0.0, 0.15)], "10_EzratNashim", MAT_BRONZE(), verts=24)
# « וְסַל מַצּוֹת סֹלֶת חַלֹּת… וּרְקִיקֵי מַצּוֹת » (Bamidbar 6:15), dix de chaque — « חוּץ מֵחַלּוֹת
# תּוֹדָה וְהַנְּזִירוּת, שֶׁהֵן בָּאוֹת עֶשֶׂר עֶשֶׂר » (Mena'hot 6:5). Le panier sur une table de pierre, les
# galettes épaisses en deux piles, les minces en deux autres. Table, panier, formes : CHOIX.
box("Lishkat_Nezirim_SE_table", 108, 114, -40, -37.5, Z_EZN, Z_EZN + 1.5, "10_EzratNashim")
SAL_X, SAL_Y, SAL_Z = 111.0, -38.75, Z_EZN + 1.5
revolution("Lishkat_Nezirim_SE_sal", SAL_X, SAL_Y, SAL_Z,
           [(0.0, 0.0), (0.8, 0.0), (0.95, 0.5), (0.88, 0.5), (0.74, 0.06), (0.0, 0.06)],
           "10_EzratNashim", MAT_CHENE(), verts=20)
for _k, (_dx, _dy, _genre, _r, _ep) in enumerate(((-0.3, -0.3, "halla", 0.26, 0.09), (0.3, -0.3, "halla", 0.26, 0.09),
                                                  (-0.3, 0.3, "rakik", 0.28, 0.03), (0.3, 0.3, "rakik", 0.28, 0.03))):
    for _p in range(5):
        _z = SAL_Z + 0.06 + _p * _ep
        cyl(f"Lishkat_Nezirim_SE_{_genre}_{_k}{_p}", SAL_X + _dx, SAL_Y + _dy, _z, _z + _ep, _r,
            "10_EzratNashim", MAT_LECHEM(), verts=12)
# NORD-OUEST, Lishkat HaMetzoraïm : la Michna ne lui donne qu'un nom, mais une autre
# le meuble — « וְהַמְּצֹרָע טָבַל בְּלִשְׁכַּת הַמְּצֹרָעִים, בָּא וְעָמַד בְּשַׁעַר נִקָּנוֹר »
# (Negaïm 14:8). C'est un mikvé, et la seule eau de la cour. Sa cote minimale est
# « אַמָּה עַל אַמָּה בְּרוּם שָׁלֹשׁ אַמּוֹת » = quarante séa (Rambam, Mikvaot 4:1) ; les
# 10 × 8 × 3 d'ici sont un CHOIX, comme la volée qui y descend — dont la marche reprend
# le « רוּם מַעֲלָה חֲצִי אַמָּה וְשִׁלְחָהּ חֲצִי אַמָּה » de toutes les marches du Temple
# (Middot 2:3).
MIKVE = (19.0, 31.0, 48.0, 58.0)     # l'emprise que le dallage et le podium lui cèdent
MIKVE_FOND, MIKVE_EAU = Z_EZN - 4.5, Z_EZN - 1.5
for _nm, _a, _b, _c, _d in (("S", 0, 12, 0, 1), ("N", 0, 12, 9, 10),
                            ("O", 0, 1, 1, 9), ("E", 11, 12, 1, 9)):
    box(f"Lishkat_Metzoraim_NO_cuve_{_nm}", MIKVE[0] + _a, MIKVE[0] + _b,
        MIKVE[2] + _c, MIKVE[2] + _d, Z_EZN - 5, Z_EZN, "10_EzratNashim")
box("Lishkat_Metzoraim_NO_cuve_fond", *MIKVE, Z_EZN - 5, MIKVE_FOND, "10_EzratNashim")
for _k in range(9):
    box(f"Lishkat_Metzoraim_NO_marche_{_k}", MIKVE[0] + 1, MIKVE[1] - 1,
        MIKVE[2] + 1, MIKVE[2] + 1 + 0.5 * (_k + 1), MIKVE_FOND, Z_EZN - 0.5 * _k,
        "10_EzratNashim")
box("Lishkat_Metzoraim_NO_eau", MIKVE[0] + 1, MIKVE[1] - 1, MIKVE[2] + 1, MIKVE[3] - 1,
    MIKVE_FOND, MIKVE_EAU, "10_EzratNashim", MAT_EAU())
# SUD-OUEST, Beit Shemanya : « שָׁם הָיוּ נוֹתְנִין יַיִן וָשֶׁמֶן » — mais c'est Abba Shaoul ;
# R. Eliezer ben Yaakov dit « שָׁכַחְתִּי מֶה הָיְתָה מְשַׁמֶּשֶׁת ». Le film suit Abba Shaoul,
# seul avis qui donne un contenu (fiche §3).
JARRE = [(0.0, 0.0), (0.35, 0.06), (0.78, 0.7), (0.86, 1.3), (0.58, 2.0),
         (0.34, 2.2), (0.44, 2.35), (0.36, 2.42), (0.0, 2.36)]
PORTE_SHEMANYA_X, PANSE_JARRE = EX0 + 20, max(r for r, _ in JARRE)
for _r, (_y, _n, _devant_porte) in enumerate(((-62.0, 10, False), (-59.4, 10, False),
                                              (-35.6, 9, True), (-33.0, 9, True))):
    for _k in range(_n):
        _x = PORTE_SHEMANYA_X + (_k - (_n - 1) / 2) * 3.2
        if _devant_porte and abs(_x - PORTE_SHEMANYA_X) < 3 + PANSE_JARRE:
            continue
        revolution(f"Lishkat_Shemanya_SO_jarre_{_r}{_k}", _x, _y, Z_EZN,
                   JARRE, "10_EzratNashim", MAT_TERRE_CUITE(), verts=14)
# Le vin et l'huile se mesurent : « שֶׁבַע מִדּוֹת שֶׁל לַח הָיוּ בַמִּקְדָּשׁ. הִין, וַחֲצִי הַהִין, וּשְׁלִישִׁית הַהִין,
# וּרְבִיעִית הַהִין, לֹג, וַחֲצִי לֹג, וּרְבִיעִית לֹג » (Mena'hot 9:2). Le hin vaut douze log ; les sept
# mesures ont donc le rayon de la racine cubique de leur contenance. Qu'elles soient rangées ici,
# leur bronze et la taille du hin : CHOIX — la Michna dit seulement qu'elles étaient au Mikdash.
box("Lishkat_Shemanya_SO_table", 9.7, 11.5, -50.5, -42.5, Z_EZN, Z_EZN + 1.5, "10_EzratNashim")
for _k, _log in enumerate((12, 6, 4, 3, 1, 0.5, 0.25)):
    _r = 0.22 * (_log / 12) ** (1 / 3)
    revolution(f"Lishkat_Shemanya_SO_mida_{_k}", 10.6, -49.8 + 1.1 * _k, Z_EZN + 1.5,
               [(0.0, 0.0), (_r, 0.0), (_r, 1.3 * _r), (0.88 * _r, 1.3 * _r), (0.88 * _r, 0.05), (0.0, 0.05)],
               "10_EzratNashim", MAT_BRONZE(), verts=16)
# Gezuztra : « וַחֲלָקָה הָיְתָה בָּרִאשׁוֹנָה, וְהִקִּיפוּהָ כְצוֹצְרָה » (Middot 2:5) — « הִקִּיפוּ סָבִיב
# לְעֶזְרַת נָשִׁים » (Bartenura ad loc.) : elle fait le tour de la cour. Aucune source n'en donne la
# hauteur : CHOIX, à la crête des chambres d'angle, dont elle longe les murs côté cour sans les
# couvrir — « וְלֹא הָיוּ מְקוֹרוֹת ». Au droit d'une chambre, le mur et son couronnement la
# portent, et elle déborde de 1,5 dont 0,84 sur la corniche ; entre les chambres, des colonnes.
# Ouverte à l'ouest, où monte Nikanor, et coupée à l'est, où la porte monte plus haut qu'elle.
# Aucune source ne dit par où l'on y montait : pas d'escalier.
# Avis écarté, Rashi sur Soucca 51b : « נָתְנוּ זִיזִין בַּכְּתָלִים בּוֹלְטִין מִן הַכּוֹתֶל סָבִיב סָבִיב
# וְכָל שָׁנָה מְסַדְּרִין שָׁם גְּזוּזְטְרָאוֹת לְוָוחִין » — des corbeaux à demeure, un plancher de bois
# posé chaque année.
# Colonnes, architrave, corniche et balustrade sont des CHOIX (Rambam, Beit HaBe'hira 1:11) ; la
# frise de fleurons reprend les « פְּטוּרֵי צִצִּים » du Bayit (Melakhim I 6:29), en pierre.
Z_GEZ = CRETE_LISHKA_EN       # sous-face de la dalle
Z_ARCHITRAVE = Z_GEZ - 1.4
SOUS_CORNICHE_EN = Z_EZN + H_MUR_EN + min(zb for zb, _, _ in CORNICHE)
Y_BOUT_GEZ = 5 + ENCADREMENT_SHAAR
# Moitié nord. Les dalles se partagent les angles sans se recouvrir ; chaque rive est une
# polyligne qui laisse la dalle à sa gauche. La moitié sud est le miroir.
NU_LISHKA_EN = 40 - MUR_LISHKA_EN         # nu intérieur d'une chambre d'angle, depuis l'angle
Y_NU_LISHKA_EN = 27.5 + MUR_LISHKA_EN
GEZ_DALLES = ((EX0, EX0 + 41.5, 26, Y_NU_LISHKA_EN), (EX0 + NU_LISHKA_EN, EX0 + 41.5, Y_NU_LISHKA_EN, 67.5),
              (EX0 + 41.5, EX1 - 41.5, 64, 67.5), (EX1 - 41.5, EX1 - NU_LISHKA_EN, Y_NU_LISHKA_EN, 67.5),
              (EX1 - 41.5, EX1, 26, Y_NU_LISHKA_EN), (EX1 - 3.5, EX1, Y_BOUT_GEZ, 26))
GEZ_RIVE_COUR = ((EX0, 26), (EX0 + 41.5, 26), (EX0 + 41.5, 64), (EX1 - 41.5, 64), (EX1 - 41.5, 26),
                 (EX1 - 3.5, 26), (EX1 - 3.5, Y_BOUT_GEZ), (EX1, Y_BOUT_GEZ))
# Le dos des bandes qui longent une chambre donne sur son vide : une balustrade là aussi,
# sans cymaise ni larmier — le couronnement de la chambre en tient lieu. CHOIX.
GEZ_RIVES_CHAMBRE = (((EX0 + NU_LISHKA_EN, 67.5), (EX0 + NU_LISHKA_EN, Y_NU_LISHKA_EN), (EX0, Y_NU_LISHKA_EN)),
                     ((EX1, Y_NU_LISHKA_EN), (EX1 - NU_LISHKA_EN, Y_NU_LISHKA_EN), (EX1 - NU_LISHKA_EN, 67.5)))
R_COLONNE_GEZ = 0.7           # un dixième de sa hauteur
X_COLONNES_GEZ = [EX0 + 45.5 + k * (EX1 - EX0 - 91) / 7 for k in range(8)]
# Le long du mur est, une colonne entre deux shofarot sur deux : au droit d'un shofar, elle le heurtait.
Y_COLONNES_GEZ_EST = (11.2, 18.0, 24.8)
X_COLONNES_GEZ_EST = EX1 - 3.5 + 0.9


def _onglets(trace, d):
    """Les sommets de `trace` décalés de `d` vers sa gauche, en onglet."""
    gauches = []
    for (xa, ya), (xb, yb) in zip(trace, trace[1:]):
        longueur = math.hypot(xb - xa, yb - ya)
        gauches.append((-(yb - ya) / longueur, (xb - xa) / longueur))
    points = []
    for k, (x, y) in enumerate(trace):
        na, nb = gauches[max(k - 1, 0)], gauches[min(k, len(gauches) - 1)]
        s = d / (1 + na[0] * nb[0] + na[1] * nb[1])
        points.append((x + s * (na[0] + nb[0]), y + s * (na[1] + nb[1])))
    return points


def bande_le_long(nom, trace, d0, d1, z0, z1, col, mat=None):
    """Bande entre les décalages `d0` < `d1` de `trace`, un quadrilatère par segment : les
    onglets s'aboutent sans se recouvrir, et aucun n-gone n'est concave."""
    a, b = _onglets(trace, d0), _onglets(trace, d1)
    for k in range(len(trace) - 1):
        prism(f"{nom}_{k}", [a[k], a[k + 1], b[k + 1], b[k]], z0, z1, col, mat)


def balustrade(nom, trace, z, col, colonnes=()):
    """Plinthe, balustres, main courante sur la dalle dont `z` est le dessus, et un dé aux
    bouts, à chaque sommet et au droit de chaque colonne."""
    bande_le_long(f"{nom}_plinthe", trace, 0.0, 0.6, z, z + 0.25, col)
    bande_le_long(f"{nom}_main_courante", trace, -0.05, 0.65, z + 1.75, z + 2.0, col)
    axe_des = _onglets(trace, 0.3)
    des = axe_des[1:-1]
    for (x, y), (xa, ya), (xb, yb) in ((axe_des[0], trace[0], trace[1]), (axe_des[-1], trace[-1], trace[-2])):
        longueur = math.hypot(xb - xa, yb - ya)
        des.append((x + 0.4 * (xb - xa) / longueur, y + 0.4 * (yb - ya) / longueur))
    for k, ((xa, ya), (xb, yb)) in enumerate(zip(trace, trace[1:])):
        longueur = math.hypot(xb - xa, yb - ya)
        ux, uy = (xb - xa) / longueur, (yb - ya) / longueur
        abscisses = [(xc - xa) * ux + (yc - ya) * uy for xc, yc in colonnes
                     if abs((xc - xa) * uy - (yc - ya) * ux) < 2 and 0 < (xc - xa) * ux + (yc - ya) * uy < longueur]
        des += [(xa + s * ux - 0.3 * uy, ya + s * uy + 0.3 * ux) for s in abscisses]
        arrets = [0.0, longueur] + abscisses
        for i, s in enumerate(plage(0.9, longueur - 0.9, 0.7)):
            if min(abs(s - a) for a in arrets) < 0.7:
                continue
            revolution(f"{nom}_balustre_{k}_{i:03d}", xa + s * ux - 0.3 * uy, ya + s * uy + 0.3 * ux,
                       z + 0.25, BALUSTRE, col, verts=10)
    for i, (x, y) in enumerate(des):
        box(f"{nom}_de_{i:02d}", x - 0.4, x + 0.4, y - 0.4, y + 0.4, z, z + 2.1, col)


def entablement(nom, trace, col):
    """Architrave à deux fasces, la haute au nu de la dalle, et sa frise, sous `trace`, un
    segment droit de la rive côté cour."""
    bande_le_long(f"{nom}_architrave_basse", trace, 0.2, 1.6, Z_ARCHITRAVE, Z_ARCHITRAVE + 0.7, col)
    bande_le_long(f"{nom}_architrave_haute", trace, 0.0, 1.8, Z_ARCHITRAVE + 0.7, Z_GEZ, col)
    (xa, ya), (xb, yb) = trace
    paroi, u0, u1 = ((("x", ya, 1 if xa > xb else -1), *sorted((xa, xb))) if ya == yb else
                     (("y", xa, 1 if yb > ya else -1), *sorted((ya, yb))))
    bandeau_fleurons(f"{nom}_frise", paroi, u0 + 1, u1 - 1, Z_ARCHITRAVE + 0.775, col, MAT_PIERRE())


def miroir(trace, sens):
    """La rive de la moitié sud : les points en miroir, dans l'ordre inverse pour garder
    la dalle à gauche."""
    return list(trace) if sens > 0 else [(x, -y) for x, y in reversed(trace)]


for nm, sens in (("nord", 1), ("sud", -1)):
    for k, (xa, xb, ya, yb) in enumerate(GEZ_DALLES):
        box(f"Gezuztra_{nm}_dalle_{k}", xa, xb, *sorted((sens * ya, sens * yb)), Z_GEZ, Z_GEZ + 1,
            "10_EzratNashim")
    colonnes = ([(x, sens * 64.9) for x in X_COLONNES_GEZ] +
                [(X_COLONNES_GEZ_EST, sens * y) for y in Y_COLONNES_GEZ_EST])
    for i, (x, y) in enumerate(colonnes):
        colonne_cannelee(f"Gezuztra_{nm}_colonne_{i:02d}", x, y, Z_EZN, Z_ARCHITRAVE, R_COLONNE_GEZ,
                         "10_EzratNashim")
    rive = miroir(GEZ_RIVE_COUR, sens)
    # Corniche au nu de la dalle, côté cour : cymaise puis larmier, sous la balustrade. Pas sur
    # le bout qui regarde la porte est : elle y entrait dans le liseré du cadre.
    face_cour = miroir(GEZ_RIVE_COUR[:-1], sens)
    bande_le_long(f"Gezuztra_{nm}_cymaise", face_cour, -0.3, 0.0, Z_GEZ, Z_GEZ + 0.35, "10_EzratNashim")
    bande_le_long(f"Gezuztra_{nm}_larmier", face_cour, -0.6, 0.0, Z_GEZ + 0.35, Z_GEZ + 0.9, "10_EzratNashim")
    balustrade(f"Gezuztra_{nm}_balustrade", rive, Z_GEZ + 1, "10_EzratNashim", colonnes)
    for k, trace in enumerate(GEZ_RIVES_CHAMBRE):
        balustrade(f"Gezuztra_{nm}_balustrade_dos_{k}", miroir(trace, sens), Z_GEZ + 1, "10_EzratNashim")
    # L'entablement ne court qu'où des colonnes portent la dalle : le long du mur nord ou sud,
    # et le long du mur est.
    entablement(f"Gezuztra_{nm}", miroir(GEZ_RIVE_COUR[2:4], sens), "10_EzratNashim")
    entablement(f"Gezuztra_{nm}_est", miroir(GEZ_RIVE_COUR[5:7], sens), "10_EzratNashim")
    # Au droit de chaque colonne, un pilastre sur le mur du fond, sous la galerie et au-dessus.
    for mur, fond, positions in (("", ("x", 67.5 * sens, -sens), X_COLONNES_GEZ),
                                 ("_est", ("y", EX1, -1), [sens * y for y in Y_COLONNES_GEZ_EST])):
        for i, u in enumerate(positions):
            pilastre(f"EzratNashim_pilastre_{nm}{mur}_bas_{i:02d}", fond, u, Z_EZN, Z_ARCHITRAVE,
                     "10_EzratNashim", largeur=2.0, saillie=0.7)
            pilastre(f"EzratNashim_pilastre_{nm}{mur}_haut_{i:02d}", fond, u, Z_GEZ + 1, SOUS_CORNICHE_EN,
                     "10_EzratNashim", largeur=2.0, saillie=0.7)
# Couronnement des murs de l'Ezrat Nashim, et les battants d'or de sa porte est :
# « כָּל הַשְּׁעָרִים שֶׁהָיוּ שָׁם נִשְׁתַּנּוּ לִהְיוֹת שֶׁל זָהָב, חוּץ מִשַּׁעֲרֵי נִיקָנוֹר » (Middot 2:3).
# Socle, bandeau et couronnement se posent aux mêmes bouts, avec les mêmes mitres : le pied à
# Z_EZN, la crête vingt-cinq amot plus haut, et entre les deux le plancher de la gezuztra
# (Middot 2:5). Le bandeau n'est donc pas un ornement posé à mi-hauteur : c'est le niveau de
# la galerie, lu du dehors. Il ne sort que sur la face extérieure : dedans, la galerie le
# dit elle-même, et il entrerait dans sa dalle. Seule la porte est interrompt les deux
# moulures basses.
OR_CORNICHE = MAT_OR() if FILET_OR else None
for _ouvrage, _profil, _z, _s, _dehors in (("socle", SOCLE, Z_EZN, SAILLIE_MOULURE, False),
                                           ("bandeau", BANDEAU, Z_GEZ, SAILLIE_BANDEAU, True),
                                           ("couronnement", CORNICHE, Z_EZN + H_MUR_EN, SAILLIE_MOULURE, False)):
    _baie = () if _ouvrage == "couronnement" else [(-5, 5)]
    _filet = OR_CORNICHE if _ouvrage == "couronnement" else None
    moulure(f"EzratNashim_{_ouvrage}_nord", EX0, EX1, 67.5, 72.5, _z, _profil, "10_EzratNashim",
            saillie=_s, mitres=("deborde", "bute"), filet=_filet, cotes=(not _dehors, True))
    moulure(f"EzratNashim_{_ouvrage}_sud", EX0, EX1, -72.5, -67.5, _z, _profil, "10_EzratNashim",
            saillie=_s, mitres=("deborde", "bute"), filet=_filet, cotes=(True, not _dehors))
    moulure(f"EzratNashim_{_ouvrage}_est", EX1, EX1 + 5, -72.5, 72.5, _z, _profil, "10_EzratNashim",
            saillie=_s, mitres=("deborde", "deborde"), reserve=_baie, filet=_filet,
            cotes=(not _dehors, True))
battants("EzratNashim_porte_est", EX1, EX1 + 5, -5, 5, Z_EZN, 20, "10_EzratNashim", MAT_OR())
# « כָּל הַשְּׁעָרִים שֶׁהָיוּ שָׁם נִשְׁתַּנּוּ לִהְיוֹת שֶׁל זָהָב » (Middot 2:3) : la michna dit le
# ŠAʿAR, pas ses vantaux — et elle dit deux michnayot plus haut que chaque שער avait sa
# שְׁקוֹפָה. L'or déborde donc des battants sur les jambages et sur elle. ARBITRAGE : lire
# « שער » comme la baie entière et non comme ses seules portes.
# C'est la porte par laquelle le peuple entre : elle se cadre des deux côtés, en venant
# du 'Heil comme en la regardant de la cour.
for _cote, _nu, _sens in (("est", EX1 + 5, 1), ("ouest", EX1, -1)):
    shaar(f"EzratNashim_porte_{_cote}", ("y", _nu, _sens), 0, Z_EZN,
          Z_EZN + H_MUR_EN + min(zb for zb, _, _ in CORNICHE), 2.5,
          "10_EzratNashim", metal=MAT_OR())
# Treize shofarot (Shekalim 6:5) : les troncs « en forme de shofar » — étroits en haut,
# larges en bas, pour qu'on n'y glisse pas la main (Bartenura) — le long du mur est, de
# part et d'autre de la porte. Bronze : CHOIX, la Mishna n'en dit pas la matière.
SHOFAR = [(0.62, 0.0), (0.60, 0.12), (0.40, 0.60), (0.24, 1.35), (0.20, 1.55), (0.14, 1.55), (0.12, 1.2), (0.0, 1.1)]
# « וְכָתוּב עֲלֵיהֶם » (Shekalim 6:5) : la destination de chaque tronc est écrite dessus,
# et la michna en donne les treize libellés. Sans voyelles — la ponctuation est
# postérieure au Temple. Lettres dorées sur le bronze : CHOIX.
SHOFAROT = ["תקלין חדתין", "תקלין עתיקין", "קנין", "גוזלי עולה", "עצים", "לבונה",
            "זהב לכפרת"] + ["לנדבה"] * 6
_gravures = []
for k, y in enumerate([-26.5 + 3.4 * i for i in range(7)] + [6.1 + 3.4 * i for i in range(6)]):
    revolution(f"Shofar_{k:02d}", EX1 - 1.4, y, Z_EZN, SHOFAR, "10_EzratNashim", MAT_BRONZE(), verts=20)
    _gravures.append((f"Shofar_{k:02d}_gravure", SHOFAROT[k], EX1 - 1.894, y, Z_EZN + 0.35))
graver(_gravures, "10_EzratNashim", MAT_OR(), taille=0.11, saillie=0.04, courbure=0.494)
# Simhat Beit HaShoeva (Soucca 5:2-3 ; 52b) : « מְנוֹרוֹת שֶׁל זָהָב הָיוּ שָׁם, וְאַרְבָּעָה סְפָלִים
# שֶׁל זָהָב בְּרָאשֵׁיהֶן, וְאַרְבָּעָה סֻלָּמוֹת לְכָל אֶחָד וְאֶחָד » — cinquante amot de haut
# (« תָּנָא גָּבְהָהּ שֶׁל מְנוֹרָה חֲמִשִּׁים אַמָּה », Soucca 52b), dans l'Ezrat Nashim. Quatre mâts
# (nombre : CHOIX, la Mishna dit « des menorot »), quatre coupes et quatre échelles chacun.
# Le barreau se prend tous les trois quarts d'ama et pas toutes les deux : à un mètre
# d'écart on n'y monte pas, et une échelle qu'on ne peut pas gravir se lit en étai
# d'échafaudage — or la guemara y fait justement monter des enfants avec trente log
# d'huile, en opposant l'échelle raide au kevesh qui ne l'est pas (Soucca 52b).
if CANDELABRES_SHOEVA:
    H_CANDELABRE = 50
    R_MONTANT, R_BARREAU = 0.07, 0.04
    for k, (x, y) in enumerate(((EX0 + 30, -20), (EX0 + 30, 20), (EX1 - 30, -20), (EX1 - 30, 20))):
        nom = f"Candelabre_Shoeva_{k}"
        cyl(f"{nom}_socle", x, y, Z_EZN, Z_EZN + 1.0, 1.6, "10_EzratNashim", MAT_OR(), verts=24)
        cone(f"{nom}_mat", x, y, Z_EZN + 1.0, Z_EZN + H_CANDELABRE, 0.55, 0.35, "10_EzratNashim", MAT_OR(), verts=16)
        for j in range(4):
            a = math.pi / 2 * j
            dx, dy = math.cos(a), math.sin(a)
            cyl_between(f"{nom}_bras_{j}", (x, y, Z_EZN + H_CANDELABRE - 0.6),
                        (x + 1.8 * dx, y + 1.8 * dy, Z_EZN + H_CANDELABRE - 0.2), 0.12, "10_EzratNashim", MAT_OR(), verts=8)
            revolution(f"{nom}_sefel_{j}", x + 1.8 * dx, y + 1.8 * dy, Z_EZN + H_CANDELABRE - 0.2,
                       [(0.25, 0.0), (0.7, 0.55), (0.75, 0.7), (0.62, 0.7), (0.0, 0.25)], "10_EzratNashim", MAT_OR(), verts=16)
            pied = (x + 4.0 * dx, y + 4.0 * dy, Z_EZN)
            haut = (x + 0.5 * dx, y + 0.5 * dy, Z_EZN + H_CANDELABRE - 1.5)
            lat = (-dy * 0.5, dx * 0.5)
            for s, cote in ((-1, "a"), (1, "b")):
                tube_between(f"{nom}_echelle_{j}_montant_{cote}", (pied[0] + s * lat[0], pied[1] + s * lat[1], pied[2]),
                             (haut[0] + s * lat[0], haut[1] + s * lat[1], haut[2]), R_MONTANT, "10_EzratNashim",
                             MAT_ECHELLE("montant", R_MONTANT), verts=6)
            for i, t in enumerate(plage(0.02, 0.98, 0.75 / (H_CANDELABRE - 1.5))):
                px, py, pz = (pied[c] + (haut[c] - pied[c]) * t for c in range(3))
                tube_between(f"{nom}_echelle_{j}_barreau_{i:02d}", (px - lat[0], py - lat[1], pz), (px + lat[0], py + lat[1], pz),
                             R_BARREAU, "10_EzratNashim", MAT_ECHELLE("barreau", R_BARREAU), verts=6)
# Quinze marches semi-circulaires vers la porte de Nikanor (Middot 2:5), 0.5 × 0.5,
# centrées sur l'axe, rayon décroissant en montant
for i in range(15):
    r = 7.5 - i * 0.5 + 6
    poly = [(EX0 + r * math.cos(t), r * math.sin(t))
            for t in [-math.pi / 2 + math.pi * k / 24 for k in range(0, 25)]]
    prism(f"Marche_Nikanor_{i:02d}", poly, Z_EZN, Z_EZN + 0.5 * (i + 1), "10_EzratNashim")
# Deux tribunaux de vingt-trois : « שְׁלֹשָׁה בָתֵּי דִינִין הָיוּ שָׁם, אֶחָד יוֹשֵׁב עַל פֶּתַח הַר הַבַּיִת,
# וְאֶחָד יוֹשֵׁב עַל פֶּתַח הָעֲזָרָה, וְאֶחָד יוֹשֵׁב בְּלִשְׁכַּת הַגָּזִית » (Sanhedrin 11:2). Chacun au seuil
# d'une porte, comme les juges du Tanakh (« וּבֹעַז עָלָה הַשַּׁעַר וַיֵּשֶׁב שָׁם », Ruth 4:1), et chacun
# au-dedans : « מבפנים לשער מזרח של חומת הר הבית », « מבפנים לשער מזרח של עזרת
# נשים » (Tiferet Israël, Yakhin sur Sanhedrin 11:9-10). Le premier sous le portique, derrière la
# porte de Shushan (Hagahot Ya'avetz sur Sanhedrin 88b) ; « אחד בהר הבית » (Tossefta Sanhedrin
# 7:1) le dit aussi. Avis écartés : Rashi (Sanhedrin 86b), qui met les deux dans l'Ezrat Nashim, le
# second devant l'Ezrat Israël ; la Tossefta, qui met le second « בחיל », dix amot déjà prises
# par les douze marches, et ne leur donne que trois juges.
# « וְהַגָּדוֹל בְּחָכְמָה שֶׁבְּכֻלָּן רֹאשׁ עֲלֵיהֶן וְהַשְּׁאָר יוֹשְׁבִין בְּעִגּוּל כְּמוֹ חֲצִי גֹּרֶן כְּדֵי שֶׁיְּהֵא הָרֹאשׁ
# רוֹאֶה אֶת כֻּלָּן » (Rambam, Sanhedrin 1:3) : deux gradins en demi-cercle, le chef au milieu de
# l'arc, et deux greffiers debout aux pointes (Sanhedrin 4:3). Devant eux, « שָׁלֹשׁ שׁוּרוֹת שֶׁל
# תַּלְמִידֵי חֲכָמִים… שׁוּרָה רִאשׁוֹנָה קְרוֹבָה לַסַּנְהֶדְרִין וְשׁוּרָה שְׁנִיָּה לְמַטָּה הֵימֶנָּה » (ibid. 1:7),
# « לְמַטָּה » lu « plus loin ». Vingt-trois par rang n'y tiennent pas : la scène montre la
# disposition, pas le nombre. Côtés, cotes et sièges : CHOIX.
BEIT_DIN_R = (2.2, 3.2, 4.2)          # bords des deux gradins
BEIT_DIN_H = (0.9, 1.5)               # dessus de chaque gradin
BEIT_DIN_DOSSIER = (0.5, 2.3, 3.2)    # épaisseur ; hauteur derrière les juges, derrière le chef
BEIT_DIN_CHEF = math.pi / 12          # demi-ouverture du siège du chef
BEIT_DIN_TRONCONS = 11                # de chaque côté du chef
BANCS_BEIT_DIN = (2.0, 3.5, 5.0)      # distance du centre de l'arc au bord de chaque banc
BANC_BEIT_DIN = (9.0, 0.7, 0.9)       # longueur, profondeur, hauteur


def beit_din_katan(nom, centre, ouverture, col):
    """Un tribunal de vingt-trois, l'arc centré en `centre` (x, y, sol) et ouvert vers
    l'angle `ouverture` : les juges sur le demi-cercle d'en face, les élèves devant eux."""
    cx, cy, z = centre

    def au(r, a):
        return cx + r * math.cos(a), cy + r * math.sin(a)

    def secteur(suffixe, r0, r1, a0, a1, h, mat):
        prism(f"{nom}_{suffixe}", [au(r0, a0), au(r1, a0), au(r1, a1), au(r0, a1)], z, z + h, col, mat)

    def rectangle(suffixe, x, y, a, demi_long, demi_large, z0, z1, mat):
        ux, uy, nx, ny = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
        prism(f"{nom}_{suffixe}", [(x + su * demi_long * ux + sn * demi_large * nx,
                                    y + su * demi_long * uy + sn * demi_large * ny)
                                   for su, sn in ((-1, -1), (1, -1), (1, 1), (-1, 1))], z0, z1, col, mat)

    fond = ouverture + math.pi
    pas = (math.pi / 2 - BEIT_DIN_CHEF) / BEIT_DIN_TRONCONS
    for cote, depart in (("g", ouverture + math.pi / 2), ("d", fond + BEIT_DIN_CHEF)):
        for k in range(BEIT_DIN_TRONCONS):
            a0, a1 = depart + k * pas, depart + (k + 1) * pas
            for rang, h in enumerate(BEIT_DIN_H):
                secteur(f"gradin_{rang}_{cote}{k:02d}", BEIT_DIN_R[rang], BEIT_DIN_R[rang + 1], a0, a1, h,
                        MAT_PIERRE())
            secteur(f"dossier_{cote}{k:02d}", BEIT_DIN_R[-1], BEIT_DIN_R[-1] + BEIT_DIN_DOSSIER[0], a0, a1,
                    BEIT_DIN_DOSSIER[1], MAT_PIERRE())
    # Le chef : un siège plus profond, un marchepied, un dossier plus haut. Ni trône ni or.
    for k, (a0, a1) in enumerate(((fond - BEIT_DIN_CHEF, fond), (fond, fond + BEIT_DIN_CHEF))):
        secteur(f"chef_siege_{k}", BEIT_DIN_R[0], BEIT_DIN_R[-1], a0, a1, BEIT_DIN_H[-1], MAT_PIERRE())
        secteur(f"chef_marchepied_{k}", BEIT_DIN_R[0] - 0.5, BEIT_DIN_R[0], a0, a1, BEIT_DIN_H[-1] / 3, MAT_PIERRE())
        secteur(f"chef_dossier_{k}", BEIT_DIN_R[-1], BEIT_DIN_R[-1] + BEIT_DIN_DOSSIER[0], a0, a1,
                BEIT_DIN_DOSSIER[2], MAT_PIERRE())
    # « וּשְׁנֵי סוֹפְרֵי הַדַּיָּנִין עוֹמְדִין לִפְנֵיהֶם, אֶחָד מִיָּמִין וְאֶחָד מִשְּׂמֹאל » (Sanhedrin 4:3).
    for cote, s in (("g", 1), ("d", -1)):
        x, y = au(BEIT_DIN_R[1], ouverture + s * math.pi / 2)
        x, y = x + math.cos(ouverture), y + math.sin(ouverture)
        cyl(f"{nom}_sofer_{cote}_pied", x, y, z, z + 2.0, 0.1, col, MAT_CEDRE(), verts=8)
        rectangle(f"sofer_{cote}_pupitre", x, y, ouverture, 0.3, 0.45, z + 2.0, z + 2.1, MAT_CEDRE())
    longueur, profondeur, h = BANC_BEIT_DIN
    for rang, d in enumerate(BANCS_BEIT_DIN):
        x, y = au(d + profondeur / 2, ouverture)
        rectangle(f"banc_{rang}_siege", x, y, ouverture, profondeur / 2, longueur / 2, z + h - 0.1, z + h,
                  MAT_CEDRE())
        for i, t in enumerate((-0.45, 0.0, 0.45)):
            rectangle(f"banc_{rang}_pied_{i}", x - t * longueur * math.sin(ouverture),
                      y + t * longueur * math.cos(ouverture), ouverture, profondeur / 2 - 0.05, 0.1,
                      z, z + h - 0.1, MAT_CEDRE())


# Au sud de chaque porte. Au Har HaBayit, entre le mur et le premier rang de colonnes, ouvert
# sur le passage de la porte ; dans l'Ezrat Nashim, dos à la colonnade de la galerie, un
# passage laissé devant les shofarot, ouvert vers Nikanor : CHOIX.
beit_din_katan("Beit_Din_Har_HaBayit", (HX1 - MUR_HAR - 5, -16, Z_HAR), math.pi / 2, "00_HarHabayit")
beit_din_katan("Beit_Din_HaAzara", (129, -17, Z_EZN), math.pi, "10_EzratNashim")
