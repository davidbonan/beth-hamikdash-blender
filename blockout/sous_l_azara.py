from .primitives.parametres import Z_AZ, Z_EZN, Z_HAR
from .primitives.matieres import MAT_CEDRE, MAT_CHAUX, MAT_EAU, MAT_FER, MAT_MARBRE, MAT_SOL, braise
from .primitives.volumes import box, cyl, cyl_between, ner_sur_tablette, plage, tore
from .primitives.ouvrages import dalle_percee, escalier, escalier_a_vis, massif_evide
from .ezrat_nashim import EX1, MIKVE
from .azara import AX0, AY0, AY1, T, X_DOUKHAN
from .lishkot import BOR, PUITS_MESIBA
from .mizbeach import MX0, MY0, braises


# ----------------------------------------------------------------------------
# 20bis — SOUS L'AZARA : la mesiba du Beit HaMoked et le shit du Mizbea'h
#   Deux vides qu'aucun plan ne montre, et qu'on trouve en vol libre. Le dallage de
#   l'Azara et les masses qui le portent se posent ici, une fois ces vides connus.
# ----------------------------------------------------------------------------
# « אֵרַע קֶרִי לְאַחַד מֵהֶן, יוֹצֵא וְהוֹלֵךְ לוֹ בַּמְּסִבָּה הַהוֹלֶכֶת תַּחַת הַבִּירָה, וְהַנֵּרוֹת דּוֹלְקִין מִכָּאן
# וּמִכָּאן, עַד שֶׁהוּא מַגִּיעַ לְבֵית הַטְּבִילָה » (Tamid 1:1 ; Middot 1:9). « וְכָל הַמִּקְדָּשׁ קָרוּי בִּירָה »
# (Bartenura ad loc.), et le Rambam la fait passer « תַּחַת הַמִּקְדָּשׁ כֻּלּוֹ » (Beit HaBe'hira 5:11) :
# elle court sous l'Azara, et non sous le 'Heil jusqu'à la porte Tadi comme le veut
# R. Eliezer ben Yaakov — « וְאֵין הֲלָכָה כְּרַבִּי אֱלִיעֶזֶר בֶּן יַעֲקֹב » (Bartenura ; Rambam sur Middot 1:9).
# Le baal keri peut y passer : « הַמְּחִלּוֹת הַפְּתוּחוֹת לְהַר הַבַּיִת לֹא נִתְקַדְּשׁוּ » (Beit HaBe'hira 8:7 ;
# Tamid 27b). Tracé, section, vis et écart des lampes : CHOIX, aucune source ne les donne.
PX0, PX1, PY0, PY1 = PUITS_MESIBA
Z_MESIBA_SOL = Z_HAR + 0.5
# Une demi-ama du sol de l'Ezrat Nashim reste au-dessus du tunnel : les socles du Beit
# HaMoked descendent à Z_EZN, leur dessous serait tombé dans le plafond.
Z_MESIBA_VOUTE = Z_EZN - 0.5
MESIBA_Y0 = 45                       # la branche ouest passe sous le Beit HaMitba'haïm
MESIBA_Y1 = MESIBA_Y0 + (PX1 - PX0)
# « וּמְדוּרָה הָיְתָה שָׁם, וּבֵית כִּסֵּא שֶׁל כָּבוֹד. וְזֶה הָיָה כְבוֹדוֹ, מְצָאוֹ נָעוּל, יוֹדֵעַ שֶׁיֶּשׁ שָׁם אָדָם…
# יָרַד וְטָבַל, עָלָה וְנִסְתַּפֵּג וְנִתְחַמֵּם כְּנֶגֶד הַמְּדוּרָה » (Tamid 1:1). Ni sa place ni ses cotes ne sont
# écrites : sous l'angle nord-ouest de l'Azara, au bout de la branche ouest, sept degrés
# au-dessus du tunnel pour que le mikvé touche le sol du Har HaBayit sans le percer (CHOIX).
# Le mikvé passe les quarante séa, « אַמָּה עַל אַמָּה בְּרוּם שָׁלֹשׁ אַמּוֹת » (Rambam, Mikvaot 4:1).
TEVILA = (AX0 + 2, AX0 + 27, 36, 56)
Z_TEVILA_SOL, Z_TEVILA_VOUTE = Z_MESIBA_SOL + 3.5, Z_AZ - 4
BAIN = (TEVILA[0] + 3, TEVILA[0] + 9, TEVILA[2] + 3, TEVILA[2] + 11)
MONTEE_TEVILA = (TEVILA[1] - 4, TEVILA[1], MESIBA_Y0, MESIBA_Y1)
# « לְמַטָּה בָרִצְפָה בְּאוֹתָהּ הַקֶּרֶן, מָקוֹם הָיָה שָׁם אַמָּה עַל אַמָּה, וְטַבְלָא שֶׁל שַׁיִשׁ, וְטַבַּעַת הָיְתָה
# קְבוּעָה בָהּ, שֶׁבּוֹ יוֹרְדִין לַשִּׁית וּמְנַקִּין אוֹתוֹ » (Middot 3:3), à l'angle sud-ouest de 3:2. Le shit est
# « הֶחָלָל שֶׁתַּחַת הַמִּזְבֵּחַ כְּנֶגֶד מְקוֹם הַנְּסָכִים » (Bartenura), où le vin des nessakhim « מתקבצים ג"כ
# במקום אחד תחת הארץ יקרא שית » (Rambam sur Middot 3:3). Écarté : le Tiferet Israël y voit le
# petit creux sous le yessod où coule le sang des deux trous de 3:2, d'où une rigole file
# vers le Kidron ; ni ces trous ni l'amah qui emporte le sang (Middot 3:2 ; Yoma 5:6) ne
# sont modélisés. L'échelle est la sienne, « ויורדים משם בסולם ». On verse en haut de
# l'angle sud-ouest, « עָלָה בַכֶּבֶשׁ וּפָנָה לִשְׂמֹאלוֹ » (Soucca 4:9). Place de la dalle contre
# l'angle, taille du creux, section et place du conduit : CHOIX.
SHIT_TAVLA = (MX0 - 1, MX0, MY0 - 1, MY0)
SHIT = (MX0 - 2, MX0 + 7, MY0 - 2, MY0 + 7)
Z_SHIT_FOND, Z_SHIT_VOUTE = Z_EZN + 1, Z_AZ - 3
NESEKH_X, NESEKH_Y = MX0 + 3, MY0 + 3

VIDES_SOUS_AZARA = [
    (PX0, PX1, MESIBA_Y0, PY0, Z_HAR, Z_MESIBA_VOUTE),
    (MONTEE_TEVILA[0], PX1, MESIBA_Y0, MESIBA_Y1, Z_HAR, Z_MESIBA_VOUTE),
    (*TEVILA, Z_TEVILA_SOL - 0.5, Z_TEVILA_VOUTE),
    (*BAIN, Z_HAR, Z_TEVILA_SOL - 0.5),
    (*SHIT, Z_SHIT_FOND, Z_SHIT_VOUTE),
    (*SHIT_TAVLA, Z_SHIT_VOUTE, Z_AZ),
    (*BOR, Z_EZN, Z_AZ),
]
massif_evide("Azara_sol", AX0 - T, X_DOUKHAN, AY0 - T, AY1 + T, Z_AZ - 1, Z_AZ,
             VIDES_SOUS_AZARA, "20_Azara", MAT_SOL())
massif_evide("Podium_azara", AX0 - T, X_DOUKHAN, AY0 - T, AY1 + T, Z_EZN, Z_AZ - 1,
             VIDES_SOUS_AZARA, "00_HarHabayit")
massif_evide("EzratNashim_sol", AX0 - T, EX1 + 5, AY0 - T, AY1 + T, Z_EZN - 1, Z_EZN,
             VIDES_SOUS_AZARA + [(*MIKVE, Z_HAR, Z_EZN)], "10_EzratNashim", MAT_SOL())
massif_evide("Podium_har", AX0 - T, EX1 + 5, AY0 - T, AY1 + T, Z_HAR, Z_EZN - 1,
             VIDES_SOUS_AZARA + [(*MIKVE, Z_HAR, Z_EZN)], "00_HarHabayit")


escalier_a_vis("Mesiba_bira_vis", (PX0 + PX1) / 2, (PY0 + PY1) / 2, (PX1 - PX0) / 2,
               Z_AZ, Z_MESIBA_SOL, -90, "80_Lishkot")
box("Mesiba_bira_dallage_sud", PX0, PX1, MESIBA_Y0, PY1, Z_HAR, Z_MESIBA_SOL, "80_Lishkot", MAT_SOL())
box("Mesiba_bira_dallage_ouest", MONTEE_TEVILA[1], PX0, MESIBA_Y0, MESIBA_Y1, Z_HAR, Z_MESIBA_SOL,
    "80_Lishkot", MAT_SOL())
for k, x in enumerate(plage(PX0 - 6, MONTEE_TEVILA[1] + 6, -8)):
    ner_sur_tablette(f"Mesiba_bira_ner_ouest_S{k:02d}", x, MESIBA_Y0, (0, 1), Z_MESIBA_SOL + 2, "80_Lishkot")
    ner_sur_tablette(f"Mesiba_bira_ner_ouest_N{k:02d}", x, MESIBA_Y1, (0, -1), Z_MESIBA_SOL + 2, "80_Lishkot")
for k, y in enumerate(plage(MESIBA_Y1 + 4, PY0 - 2, 8)):
    ner_sur_tablette(f"Mesiba_bira_ner_sud_O{k}", PX0, y, (1, 0), Z_MESIBA_SOL + 2, "80_Lishkot")
    ner_sur_tablette(f"Mesiba_bira_ner_sud_E{k}", PX1, y, (-1, 0), Z_MESIBA_SOL + 2, "80_Lishkot")

dalle_percee("Beit_HaTevila_sol", *TEVILA, Z_TEVILA_SOL - 0.5, Z_TEVILA_SOL, "80_Lishkot", MAT_SOL(),
             [BAIN, MONTEE_TEVILA])
escalier("Beit_HaTevila_montee", *MONTEE_TEVILA, Z_HAR, Z_TEVILA_SOL, "+x", "80_Lishkot")
escalier("Beit_HaTevila_mikve_marches", BAIN[0], BAIN[1], BAIN[3] - 4, BAIN[3], Z_HAR, Z_TEVILA_SOL,
         "-y", "80_Lishkot")
box("Beit_HaTevila_mikve_eau", *BAIN, Z_HAR, Z_TEVILA_SOL - 1, "80_Lishkot", MAT_EAU())
MEDURA = (TEVILA[0] + 13, TEVILA[0] + 16, TEVILA[3] - 6, TEVILA[3] - 3)
for nm, a, b, c, d in (("S", 0, 3, 0, 0.5), ("N", 0, 3, 2.5, 3), ("O", 0, 0.5, 0.5, 2.5), ("E", 2.5, 3, 0.5, 2.5)):
    box(f"Beit_HaTevila_medura_{nm}", MEDURA[0] + a, MEDURA[0] + b, MEDURA[2] + c, MEDURA[2] + d,
        Z_TEVILA_SOL, Z_TEVILA_SOL + 0.6, "80_Lishkot")
braises("Beit_HaTevila_medura_braises", MEDURA[0] + 0.5, MEDURA[1] - 0.5, MEDURA[2] + 0.5,
        MEDURA[3] - 0.5, Z_TEVILA_SOL + 0.35, "80_Lishkot", braise("Braise"))
KISSE = (TEVILA[1] - 5, TEVILA[1], TEVILA[3] - 5, TEVILA[3])
PORTE_KISSE = (KISSE[0] + 1.5, KISSE[0] + 3)
Z_KISSE, H_PORTE_KISSE = Z_TEVILA_SOL + 5, 4
box("Beit_HaTevila_kisse_O", KISSE[0], KISSE[0] + 0.5, KISSE[2] + 0.5, KISSE[3], Z_TEVILA_SOL, Z_KISSE,
    "80_Lishkot")
box("Beit_HaTevila_kisse_S_O", KISSE[0], PORTE_KISSE[0], KISSE[2], KISSE[2] + 0.5, Z_TEVILA_SOL, Z_KISSE,
    "80_Lishkot")
box("Beit_HaTevila_kisse_S_E", PORTE_KISSE[1], KISSE[1], KISSE[2], KISSE[2] + 0.5, Z_TEVILA_SOL, Z_KISSE,
    "80_Lishkot")
box("Beit_HaTevila_kisse_linteau", *PORTE_KISSE, KISSE[2], KISSE[2] + 0.5,
    Z_TEVILA_SOL + H_PORTE_KISSE, Z_KISSE, "80_Lishkot")
box("Beit_HaTevila_kisse_porte", *PORTE_KISSE, KISSE[2] + 0.1, KISSE[2] + 0.4,
    Z_TEVILA_SOL, Z_TEVILA_SOL + H_PORTE_KISSE, "80_Lishkot", MAT_CEDRE())
box("Beit_HaTevila_kisse_siege", KISSE[0] + 0.5, KISSE[1], KISSE[3] - 1.5, KISSE[3],
    Z_TEVILA_SOL, Z_TEVILA_SOL + 1, "80_Lishkot")
for k, y in enumerate((TEVILA[2] + 4, TEVILA[3] - 4)):
    ner_sur_tablette(f"Beit_HaTevila_ner_{k}", TEVILA[0], y, (1, 0), Z_TEVILA_SOL + 2, "80_Lishkot")

box("Shit_tavla", *SHIT_TAVLA, Z_AZ, Z_AZ + 0.05, "30_Mizbeach", MAT_MARBRE())
tore("Shit_tavla_tabaat", SHIT_TAVLA[0] + 0.5, SHIT_TAVLA[2] + 0.5, Z_AZ + 0.09, 0.2, 0.04,
     "30_Mizbeach", MAT_FER())
SOLAM_X, SOLAM_Y = SHIT_TAVLA[0] + 0.2, (SHIT_TAVLA[2] + 0.15, SHIT_TAVLA[3] - 0.15)
for cote, y in zip("SN", SOLAM_Y):
    cyl(f"Shit_solam_{cote}", SOLAM_X, y, Z_SHIT_FOND, Z_AZ - 0.1, 0.05, "30_Mizbeach", MAT_CEDRE(), verts=8)
for k, z in enumerate(plage(Z_SHIT_FOND + 0.6, Z_AZ - 0.6, 0.6)):
    cyl_between(f"Shit_solam_barreau_{k:02d}", (SOLAM_X, SOLAM_Y[0], z), (SOLAM_X, SOLAM_Y[1], z),
                0.035, "30_Mizbeach", MAT_CEDRE(), verts=6)
# Le conduit sort d'une demi-ama dans le creux : arrêté au ras de la voûte, ses faces
# du dessous auraient été coplanaires avec elle.
for nm, a, b, c, d in (("O", -0.3, -0.2, -0.3, 0.3), ("E", 0.2, 0.3, -0.3, 0.3),
                       ("S", -0.2, 0.2, -0.3, -0.2), ("N", -0.2, 0.2, 0.2, 0.3)):
    box(f"Shit_shitin_{nm}", NESEKH_X + a, NESEKH_X + b, NESEKH_Y + c, NESEKH_Y + d,
        Z_SHIT_VOUTE - 0.5, Z_AZ + 8.9, "30_Mizbeach", MAT_CHAUX())
