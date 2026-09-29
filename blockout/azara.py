from .primitives.parametres import Z_AZ, Z_EZI, Z_EZN
from .primitives.matieres import (MAT_ARGENT, MAT_BRONZE, MAT_CEDRE, MAT_CHENE, MAT_NEHOSHET, MAT_OR,
                                  MAT_PIERRE, MAT_SOL)
from .primitives.volumes import alea, box, cone, crochet, cyl, mur_perce, revolution
from .primitives.ouvrages import CORNICHE, LISHKA_DEBORD, battants, massif_evide, shaar


# ----------------------------------------------------------------------------
# 20 — AZARA (187 × 135), Middot 5:1–2
# ----------------------------------------------------------------------------
AX0, AX1, AY0, AY1 = -187, 0, -67.5, 67.5
X_DOUKHAN = AX1 - 13.5       # pied de la volée : marche d'une ama puis trois demies, sur 2,5 amot de large
H_MUR = 25
T = 5   # épaisseur des murs
# Un cadre de porte s'arrête sous le couronnement du mur : au-dessus, c'est le larmier
# qui sort le plus et lui qui porte l'ombre. `CORNICHE` se cote depuis la crête.
SOUS_CORNICHE = Z_AZ + H_MUR + min(zb for zb, _, _ in CORNICHE)
box("EzratIsrael_sol", X_DOUKHAN, AX1, AY0, AY1, Z_EZI - 1, Z_EZI, "20_Azara", MAT_SOL())
# L'Azara et l'Ezrat Nashim sont des terrasses taillées dans le Har HaBayit, pas des
# dalles posées en l'air : hors de leurs murs le sol retombe à Z_HAR. Sans la masse
# qui les porte, les murs, les chambres d'angle et les quatre lishkot du pourtour
# flottaient — 13,5 amot au-dessus du dallage, visible plein cadre au plan 1.
# Deux blocs et non un : le mur est de l'Azara (x 0..5) descend déjà à Z_EZN, une
# masse qui monterait à Z_AZ sous lui lui donnerait une face coplanaire.
# Chaque podium s'arrête UNE AMA sous sa terrasse, et le dallage fait sa croûte sur
# toute son emprise, murs compris. Deux faces coplanaires ne se départagent pas : le
# rayon qui repart du dallage retombe aussitôt sur la face jumelle, et Cycles rendait
# l'Azara et l'Ezrat Nashim en noir plein. Le podium de l'Ezrat Israël le faisait
# déjà juste ; les deux autres montaient au ras de leur sol.
# Le dallage de l'Azara, les deux podiums et le sol de l'Ezrat Nashim sont posés plus bas,
# « SOUS L'AZARA », une fois connus les vides qu'y creusent la mesiba et le shit.
# Chambres sous l'Ezrat Israël : « וּלְשָׁכוֹת הָיוּ תַחַת עֶזְרַת יִשְׂרָאֵל, וּפְתוּחוֹת לְעֶזְרַת הַנָּשִׁים,
# שֶׁשָּׁם הַלְוִיִּם נוֹתְנִים כִּנּוֹרוֹת וּנְבָלִים וּמְצִלְתַּיִם וְכָל כְּלֵי שִׁיר » (Middot 2:6). Avec elles,
# les deux de Shekalim 5:6, que nul ne situe — « צְרִיכָה עִיּוּן בְּאֵיזֶה מָקוֹם הָיְתָה עוֹמֶדֶת » (Raavad,
# dans Melekhet Shelomoh sur Tamid 3:5) : CHOIX, sur « אולי גם הן נפתחו לעזרת נשים » (Mishnat
# Eretz Israël). Les Léviim de part et d'autre des marches, où ils montent avec leurs
# instruments ; HaKelim au nord, 'Hashaïm au sud, au-delà : CHOIX.
# Sous l'Ezrat Israël seulement — « מְקוֹם דְּרִיסַת יִשְׂרָאֵל אַחַת עֶשְׂרֵה אַמָּה » (Middot 5:1) ; le
# Doukhan et ses marches commencent à l'ouest —, du sol de l'Ezrat Nashim au dallage d'au-dessus.
# Chacune a ses murs d'une demi-ama : taillée dans le podium, elle n'aurait pour parois que
# ses blocs, et la visite ne saurait pas qu'on y est entré.
# Portes 3 × 6 : la cote de Middot 2:3 n'est pas pour elles (voir PORTE_LISHKA) ; CHOIX.
X_EZI = AX1 - 11
MUR_LISHKA_EZI = 0.5
H_PORTE_EZI = 6
# Un cadre de porte prend `cadre` + 0,9 de chaque côté : à CADRE_LISHKA_EN, celui des Léviim
# entrait dans la plus basse marche et chevauchait celui de HaKelim.
CADRE_LISHKA_EZI = 0.6
# Nom, emprise en y murs compris, centre de la porte.
LISHKOT_EZI = (("Leviim_N", 13.5, 20.5, 16.5), ("HaKelim", 20.5, 32.5, 23.0),
               ("Leviim_S", -20.5, -13.5, -16.5), ("Chashaim", -32.5, -20.5, -23.0))
massif_evide("Podium_ezrat_israel", X_DOUKHAN, AX1, AY0 - T, AY1 + T, Z_EZN, Z_EZI - 1,
             [(X_EZI, AX1, y0, y1, Z_EZN, Z_EZI - 1) for _, y0, y1, _ in LISHKOT_EZI], "00_HarHabayit")
# Le seuil de Nikanor : le sol de l'Ezrat Israël continue dans l'épaisseur du mur, sinon la
# baie ouvre sur le vide entre ses deux vantaux.
box("Nikanor_seuil", AX1, AX1 + T, -5, 5, Z_EZN, Z_EZI, "20_Azara", MAT_SOL())
# Mur est avec la porte de Nikanor (10 × 20) au centre, et au pied les portes des chambres
# sous l'Ezrat Israël.
for _nom, _y0, _y1 in (("Azara_mur_est_S", AY0 - T, -5), ("Azara_mur_est_N", 5, AY1 + T)):
    mur_perce(_nom, AX1, AX1 + T, _y0, _y1, Z_EZN, Z_AZ + H_MUR, "20_Azara",
              [(porte, 3) for _, _, _, porte in LISHKOT_EZI if _y0 < porte < _y1], H_PORTE_EZI)
box("Nikanor_linteau", AX1, AX1 + T, -5, 5, Z_EZI + 20, Z_AZ + H_MUR, "20_Azara")
# Battants rabattus dans l'embrasure, comme ceux du Heikhal : les portes de l'Azara
# sont ouvertes dès l'aube (Tamid 3:7 ; Yoma 3:1-2), et à Kippour pendant l'avoda.
# Fermés, ils bouchaient l'axe est-ouest — la colonne vertébrale du film : les plans
# 6, 13 et 14 finissaient sur deux vantaux de bronze là où le découpage demande
# l'ouverture de l'Oulam au fond. Ils contredisaient aussi la ligne de mire de la
# para adouma (Middot 2:4), que le mur est bas est fait pour dégager.
# Le שער de Nikanor se regarde des DEUX côtés, et c'est le seul du Temple dans ce cas :
# de l'Ezrat Nashim par les quinze marches, et de toute l'Azara par la mire est-ouest
# que Middot 2:4 dégage. Son encadrement est celui des six autres ; ce qui l'en sépare
# est son métal — « חוּץ מִשַּׁעֲרֵי נִיקָנוֹר… מִפְּנֵי שֶׁנְּחֻשְׁתָּן מַצְהִיב » (Middot 2:3).
for _cote, _nu, _sens in (("est", AX1 + T, 1), ("ouest", AX1, -1)):
    shaar(f"Nikanor_{_cote}", ("y", _nu, _sens), 0, Z_EZI, SOUS_CORNICHE, T / 2,
          "20_Azara", metal=MAT_NEHOSHET())
box("Nikanor_porte_S", AX1 + 1, AX1 + 4.5, -5, -4.7, Z_EZI, Z_EZI + 20, "20_Azara", MAT_NEHOSHET())
box("Nikanor_porte_N", AX1 + 1, AX1 + 4.5, 4.7, 5, Z_EZI, Z_EZI + 20, "20_Azara", MAT_NEHOSHET())
# « שְׁנֵי פִשְׁפְּשִׁין הָיוּ לוֹ לְשַׁעַר נִיקָנוֹר, אֶחָד בִּימִינוֹ וְאֶחָד בִּשְׂמֹאלוֹ » (Middot 2:6) : deux
# guichets de bronze de part et d'autre de la grande porte, côté Azara. Cote (3 × 8) :
# CHOIX. Les vantaux sont posés sur le nu du mur — la baie n'est pas percée, et la face
# est, dix amot au-dessus du sol de l'Ezrat Nashim, n'en reçoit pas.
PISHPESHIM = (("S", -14.5, -11.5), ("N", 11.5, 14.5))
H_PISHPESH = 8
for cote, y0, y1 in PISHPESHIM:
    box(f"Nikanor_pishpesh_{cote}", AX1 - 0.25, AX1, y0, y1, Z_EZI, Z_EZI + H_PISHPESH, "20_Azara", MAT_NEHOSHET())
    box(f"Nikanor_pishpesh_{cote}_linteau", AX1 - 0.25, AX1, y0 - 0.3, y1 + 0.3, Z_EZI + H_PISHPESH, Z_EZI + H_PISHPESH + 0.4, "20_Azara", MAT_NEHOSHET())
# Les chambres sous l'Ezrat Israël : leurs murs, et un cadre de pierre sur chaque porte,
# comme aux chambres d'angle — un פתח de chambre n'est pas un שער.
for _nom, _y0, _y1, _porte in LISHKOT_EZI:
    massif_evide(f"Lishkat_{_nom}_murs", X_EZI, AX1, _y0, _y1, Z_EZN, Z_EZI - 1,
                 [(X_EZI + MUR_LISHKA_EZI, AX1, _y0 + MUR_LISHKA_EZI, _y1 - MUR_LISHKA_EZI, Z_EZN, Z_EZI - 1)],
                 "10_EzratNashim")
    shaar(f"Lishkat_{_nom}_cadre", ("y", AX1 + T, 1), _porte, Z_EZN, Z_EZI, T, "10_EzratNashim", MAT_PIERRE(),
          largeur=3, hauteur=H_PORTE_EZI, cadre=CADRE_LISHKA_EZI)


def instrument_range(nom, genre, x, y, z0, le_long, col):
    """Instrument de Lévi rangé, et non tenu comme dans `instrument_de_levi` : kinor ou nevel
    debout, son cadre parallèle à la paroi qui court le long de l'axe `le_long` ; tziltzal
    couché, ses deux disques l'un sur l'autre."""
    if genre == "tziltzal":
        for k in range(2):
            cyl(f"{nom}_{k}", x, y, z0 + 0.05 * k, z0 + 0.05 * k + 0.04, 0.28, col, MAT_BRONZE(), verts=12)
        return
    bois = MAT_CHENE()

    def piece(suffixe, a0, a1, b0, b1, zb, zh):
        bornes = (x + a0, x + a1, y + b0, y + b1) if le_long == "x" else (x + b0, x + b1, y + a0, y + a1)
        box(f"{nom}_{suffixe}", *bornes, zb, zh, col, bois)

    large, haut = (0.30, 1.10) if genre == "kinor" else (0.42, 1.70)
    if genre == "kinor":
        piece("caisse", -large, large, -0.06, 0.06, z0, z0 + 0.30)
    else:
        cone(f"{nom}_caisse", x, y, z0, z0 + 0.70, 0.36, 0.26, col, bois, verts=10)   # tient dans l'étagère
    for s in (-1, 1):
        a = s * (large - 0.04)
        cyl(f"{nom}_bras{s:+d}", x + (a if le_long == "x" else 0), y + (0 if le_long == "x" else a),
            z0 + (0.30 if genre == "kinor" else 0.70), z0 + haut, 0.04, col, bois, verts=6)
    piece("joug", -large - 0.01, large + 0.01, -0.04, 0.04, z0 + haut - 0.08, z0 + haut)


# Lishkot HaLéviim : « שֶׁשָּׁם הַלְוִיִּם נוֹתְנִים כִּנּוֹרוֹת וּנְבָלִים וּמְצִלְתַּיִם » (Middot 2:6). Des
# rayonnages de cèdre le long des deux grands murs — les nevalim en bas, les kinorot au-dessus,
# les metziltayim en haut — et trois kinorot aux crochets du fond. Pas de 'hatzotzrot : la michna
# ne les nomme pas, et les cohanim en sonnent (« וּבְנֵי אַהֲרֹן הַכֹּהֲנִים יִתְקְעוּ בַּחֲצֹצְרוֹת », Bamidbar
# 10:8) ; Soucca 5:4 en met pourtant aux Léviim à Sim'hat Beit HaSho'éva. Tout : CHOIX.
PLANCHES_LEVIIM = (-9.7, -7.7, -6.0, -4.6)      # dessous de chaque planche
MONTANTS_LEVIIM = [X_EZI + 0.7 + k * 2.5 for k in range(5)]
for _nom, _s in (("Leviim_N", 1), ("Leviim_S", -1)):
    for _mur, _nu in (("a", 14.0), ("b", 20.0)):
        _dedans = 1 if _mur == "a" else -1       # sens de la paroi vers la chambre
        _y0, _y1 = sorted((_s * _nu, _s * (_nu + _dedans * 0.8)))
        _y = (_y0 + _y1) / 2
        for k, x in enumerate(MONTANTS_LEVIIM):
            box(f"Lishkat_{_nom}_etagere_{_mur}_montant_{k}", x, x + 0.12, _y0, _y1, Z_EZN, PLANCHES_LEVIIM[-1] + 0.1,
                "10_EzratNashim", MAT_CEDRE())
        for k, (xa, xb) in enumerate(zip(MONTANTS_LEVIIM, MONTANTS_LEVIIM[1:])):
            for j, z in enumerate(PLANCHES_LEVIIM):
                box(f"Lishkat_{_nom}_etagere_{_mur}_planche_{k}{j}", xa + 0.12, xb, _y0, _y1, z, z + 0.1,
                    "10_EzratNashim", MAT_CEDRE())
            xc = (xa + 0.12 + xb) / 2
            instrument_range(f"Lishkat_{_nom}_{_mur}_nevel_{k}", "nevel", xc, _y, PLANCHES_LEVIIM[0] + 0.1,
                             "x", "10_EzratNashim")
            for i, u in enumerate((-0.55, 0.55)):
                instrument_range(f"Lishkat_{_nom}_{_mur}_kinor_{k}{i}", "kinor", xc + u, _y,
                                 PLANCHES_LEVIIM[1] + 0.1, "x", "10_EzratNashim")
            for i, u in enumerate((-0.7, 0.0, 0.7)):
                instrument_range(f"Lishkat_{_nom}_{_mur}_tziltzal_{k}{i}", "tziltzal", xc + u, _y,
                                 PLANCHES_LEVIIM[2] + 0.1, "x", "10_EzratNashim")
    for i, y in enumerate((15.6, 17.0, 18.4)):
        crochet(f"Lishkat_{_nom}_crochet_{i}", X_EZI + MUR_LISHKA_EZI, _s * y, -6.3, 1, "10_EzratNashim")
        instrument_range(f"Lishkat_{_nom}_fond_kinor_{i}", "kinor", X_EZI + MUR_LISHKA_EZI + 0.2, _s * y, -7.4,
                         "y", "10_EzratNashim")
# Lishkat HaKelim : « כָּל מִי שֶׁהוּא מִתְנַדֵּב כְּלִי, זוֹרְקוֹ לְתוֹכָהּ. וְאַחַת לִשְׁלשִׁים יוֹם, גִּזְבָּרִין
# פּוֹתְחִין אוֹתָהּ » (Shekalim 5:6). Fermée : deux vantaux de bronze sous une traverse, et
# au-dessus une baie où l'on jette le don ; dedans, ce qui y est tombé. Tout : CHOIX.
_porte = next(p for n, _, _, p in LISHKOT_EZI if n == "HaKelim")
box("Lishkat_HaKelim_traverse", AX1, AX1 + T, _porte - 1.5, _porte + 1.5, Z_EZN + 4.5, Z_EZN + 5,
    "10_EzratNashim")
for _cote, (_ya, _yb) in (("S", (_porte - 1.5, _porte - 0.01)), ("N", (_porte + 0.01, _porte + 1.5))):
    box(f"Lishkat_HaKelim_vantail_{_cote}", AX1 + T / 2 - 0.15, AX1 + T / 2 + 0.15, _ya, _yb,
        Z_EZN, Z_EZN + 4.5, "10_EzratNashim", MAT_BRONZE())
_metaux = (MAT_ARGENT, MAT_OR, MAT_BRONZE, MAT_BRONZE)
for k in range(18):
    _n = f"Lishkat_HaKelim_keli_{k:02d}"
    x, y = AX1 - 0.5 - 2.2 * alea(_n, 0), _porte - 1.3 + 2.6 * alea(_n, 1)
    z, r, mat = Z_EZN + 0.3 * alea(_n, 2), 0.15 + 0.2 * alea(_n, 3), _metaux[k % 4]()
    forme = k % 3
    if forme == 0:      # plat
        cyl(_n, x, y, z, z + 0.04, r + 0.1, "10_EzratNashim", mat, verts=16)
    elif forme == 1:    # coupe
        cone(_n, x, y, z, z + 0.25, 0.5 * r, r, "10_EzratNashim", mat, verts=16)
    else:               # cruche
        revolution(_n, x, y, z, [(0.0, 0.0), (0.6 * r, 0.0), (r, 0.3), (0.5 * r, 0.75), (0.6 * r, 0.9),
                                 (0.5 * r, 0.9), (0.0, 0.85)], "10_EzratNashim", mat, verts=16)
# Lishkat 'Hashaïm : « יִרְאֵי חֵטְא נוֹתְנִים לְתוֹכָהּ בַּחֲשַׁאי, וַעֲנִיִּים בְּנֵי טוֹבִים מִתְפַּרְנְסִים מִתוֹכָהּ
# בַּחֲשַׁאי » (Shekalim 5:6). Ouverte, un coffre au milieu, où l'on dépose et d'où l'on prend. CHOIX.
_y = next(p for n, _, _, p in LISHKOT_EZI if n == "Chashaim") - 3.5
box("Lishkat_Chashaim_coffre", -6.5, -4.5, _y - 0.6, _y + 0.6, Z_EZN, Z_EZN + 1.1, "10_EzratNashim", MAT_CEDRE())
box("Lishkat_Chashaim_coffre_couvercle", -6.55, -4.45, _y - 0.65, _y + 0.65, Z_EZN + 1.1, Z_EZN + 1.3,
    "10_EzratNashim", MAT_CEDRE())
for k, x in enumerate((-6.0, -5.0)):
    box(f"Lishkat_Chashaim_coffre_bande_{k}", x - 0.08, x + 0.08, _y - 0.67, _y + 0.67, Z_EZN, Z_EZN + 1.32,
        "10_EzratNashim", MAT_BRONZE())
# Mur ouest
box("Azara_mur_ouest", AX0 - T, AX0, AY0 - T, AY1 + T, Z_AZ, Z_AZ + H_MUR, "20_Azara")
# Murs nord et sud avec trois portes chacun (10 × 20). Positions : CHOIX (Middot 1:4)
# Les trois portes de chaque mur, nommées. La Mishna les compte « סמוכים למערב »,
# c'est-à-dire en partant de la plus occidentale (Middot 2:6 = Shekalim 6:3 : « les
# portes du sud, à partir de celle qui est près de l'ouest : Sha'ar HaElyon, Sha'ar
# HaDelek, Sha'ar HaBekhorot, Sha'ar HaMayim » ; Bartenura sur Shekalim 6:3 : « la
# porte proche de l'ouest est Sha'ar HaElyon, et APRÈS elle Sha'ar HaDelek » ;
# Tosfot Yom Tov sur Middot 5:3 : c'est l'absence de « סמוכים למערב » qui fait
# compter les lishkot d'est en ouest, sa présence fait compter les portes de l'ouest
# vers l'est). La liste des sept portes (Middot 1:4-5) donne les mêmes trois portes
# du sud dans le même ordre : Sha'ar HaMayim est donc la plus ORIENTALE.
PORTE_DELEK, PORTE_BEKHOROT, PORTE_MAYIM = -120, -66, -12       # sud, ouest -> est
PORTE_NITZOTZ, PORTE_KORBAN, PORTE_MOKED = -120, -66, -12       # nord, ouest -> est
# La Lishkat HaGazit est à cheval sur la limite du sacré, avec deux ouvertures —
# « חֶצְיָהּ בַּקֹּדֶשׁ וְחֶצְיָהּ בַּחוֹל… שְׁנֵי פְתָחִים הָיוּ לָהּ, אֶחָד פָּתוּחַ בַּקֹּדֶשׁ וְאֶחָד
# פָּתוּחַ בַּחוֹל » (Yoma 25a ; Rambam, Beit HaBe'hira 5:17). Elle enjambe
# le mur, qui s'interrompt sur sa largeur. Ce ne sont pas des portes de plus : Middot 1:4
# compte sept **שערים**, et Yoma 25a appelle celles-ci des פתחים.
# Les x du groupe du nord (Gazit, Gola, HaEtz) sont un CHOIX : voir plus bas, c'est la
# seule portée de mur assez longue pour les deux corps. HaGazit est la plus orientale, les
# lishkot se comptant d'est en ouest (Tosfot Yom Tov sur Middot 5:3, « מִדְּלֹא תְּנַן הָכָא
# סְמוּכִין לַמַּעֲרָב… שְׁמַעִינַן דְּהָכָא מִמִּזְרָח לְמַעֲרָב קָא חָשֵׁיב דֶּרֶךְ כְּנִיסַת הָעֲזָרָה »).
GAZIT_X0, GAZIT_X1 = -158, -138
GOLA_X0, GOLA_X1 = -182, -162
MOKED_X0, MOKED_X1 = PORTE_MOKED - 10, PORTE_MOKED + 10
# Le Beit HaMoked et la Lishkat HaGazit enjambent le mur : il s'interrompt sur leur
# largeur, et leurs baies sont dans leurs propres faces. Un mur qui les traverserait en
# ferait deux culs-de-sac de dix amot.
TRAVERSEES = {"nord": [(MOKED_X0, MOKED_X1), (GAZIT_X0, GAZIT_X1)], "sud": []}
OUVERTURES = {"nord": [PORTE_KORBAN, PORTE_NITZOTZ],
              "sud": [PORTE_MAYIM, PORTE_BEKHOROT, PORTE_DELEK]}
for (y0, y1, nm) in [(AY1, AY1 + T, "nord"), (AY0 - T, AY0, "sud")]:
    ouvertures = OUVERTURES[nm]
    coupures = sorted([(p - 5, p + 5) for p in ouvertures] + TRAVERSEES[nm])
    bornes = [AX0] + [u for coupure in coupures for u in coupure] + [AX1]
    for k in range(0, len(bornes) - 1, 2):
        box(f"Azara_mur_{nm}_{k // 2}", bornes[k], bornes[k + 1], y0, y1,
            Z_AZ, Z_AZ + H_MUR, "20_Azara")
    # Le cadre se pose du côté de la COUR : dehors, ces murs soutiennent dix amot de
    # remblai et leur pied est sur la terrasse du 'Heil — c'est aussi de ce côté-là que
    # le mur porte son socle et son couronnement.
    face = (AY1, -1) if nm == "nord" else (AY0, 1)
    for p in ouvertures:
        box(f"Azara_porte_{nm}_{p:+.0f}_linteau", p - 5, p + 5, y0, y1,
            Z_AZ + 20, Z_AZ + H_MUR, "20_Azara")
        # Six שערים aux battants d'or, Nikanor seule en bronze (Middot 2:3 ; Yoma 3:10) ;
        # ouverts dès l'aube (Tamid 3:7).
        shaar(f"Azara_porte_{nm}_{p:+.0f}", ("x", *face), p, Z_AZ, SOUS_CORNICHE, T,
              "20_Azara", metal=MAT_OR())
        battants(f"Azara_porte_{nm}_{p:+.0f}_battants", p - 5, p + 5, y0, y1,
                 Z_AZ, 20, "20_Azara", MAT_OR())
SAILLIE = 12          # ce que les corps débordent du mur ; = la profondeur du Beit Avtinas
SAILLIE_INT = 10      # profondeur des corps bâtis DANS la cour, contre le mur. Au-delà, au sud,
                      # le débord du socle mordrait sur le pied du kevesh : Rambam, Beit HaBe'hira
                      # 5:15, « וּבֵין הַכֶּבֶשׁ וּלְכֹתֶל דְּרוֹמִי י"ב אַמָּה וּמֶחֱצָה ».
AXE_MUR_N = AY1 + T / 2
NORD_Y1 = AY1 + T + SAILLIE
NORD_Y0 = 2 * AXE_MUR_N - NORD_Y1     # symétrique du précédent par rapport à l'axe du mur
NORD_INT = (AY1 - SAILLIE_INT, AY1)   # la Lishkat HaGola, dans la cour comme les trois du sud
POURTOUR_Y1 = NORD_Y1 + LISHKA_DEBORD   # la face bâtie la plus saillante du complexe, corps de porte compris
# Ezrat Israël → Ezrat Kohanim (Middot 2:6, R. Eliezer ben Yaakov) : « מַעֲלָה גְבוֹהָה אַמָּה
# וְהַדּוּכָן נָתוּן עָלֶיהָ וּבוֹ שָׁלֹשׁ מַעֲלוֹת שֶׁל חֲצִי חֲצִי אַמָּה, נִמְצֵאת עֶזְרַת כֹּהֲנִים גְּבוֹהָה
# מֵעֶזְרַת יִשְׂרָאֵל שְׁתֵּי אַמּוֹת וּמֶחֱצָה ». Une volée qui monte vers l'ouest, sur toute la largeur :
# la marche d'une ama, puis les trois demi-marches du Doukhan, la dernière affleurant la cour.
# Les boîtes emboîtées d'avant faisaient un mur de 2,5 amot en travers de la porte.
# Au nord, la volée s'arrête au Beit HaMoked, qui avance de douze amot dans la cour.
box("Marche_EzratIsrael_Cohanim", AX1 - 12, AX1 - 11, AY0, NORD_Y0, Z_EZI - 1, Z_EZI + 1, "20_Azara")
for i in range(3):
    box(f"Doukhan_{i}", AX1 - 12.5 - i * 0.5, AX1 - 12 - i * 0.5, AY0, NORD_Y0, Z_EZI - 1, Z_EZI + 1.5 + 0.5 * i, "20_Azara")
