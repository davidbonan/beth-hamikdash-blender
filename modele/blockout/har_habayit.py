from .primitives.parametres import Z_HAR, Z_ROCHE
from .primitives.matieres import MAT_CEDRE, MAT_MURAILLE, MAT_SOL
from .primitives.volumes import box, colonne, mur_perce, plage
from .primitives.gravures import _relief_profil
from .primitives.ouvrages import (BANDEAU, ENCADREMENT_SHAAR, SAILLIE_BANDEAU, creneaux, moulure,
                                  ordre_de_pilastres, shaar)


# ----------------------------------------------------------------------------
# 00 — HAR HABAYIT (500 × 500), Middot 2:1 : sud > est > nord > ouest
# ----------------------------------------------------------------------------
# « רֻבּוֹ מִן הַדָּרוֹם, שֵׁנִי לוֹ מִן הַמִּזְרָח, שְׁלִישִׁי לוֹ מִן הַצָּפוֹן, מִעוּטוֹ מִן הַמַּעֲרָב » (Middot 2:1),
# du mur du Har HaBayit à celui de l'Azara, « חומת העזרה » (Rambam, Bartenura), l'Ezrat Nashim
# comptant dans l'est (Tosfot Yom Tov) : sud 234,5 > est 221 > nord 120,5 > ouest 82. Le
# bâtiment est centré d'est en ouest (81 devant l'Ezrat Nashim, 82 derrière l'Azara) ; seul
# le nord-sud est décentré, comme l'ordre l'exige. Écarté : R. Yehosef Ashkenazi (Melekhet
# Shelomoh), qui mesure l'est depuis l'Ezrat Nashim — avec 163 amot libres d'est en ouest,
# il coince le Temple dans l'angle nord-ouest. Les valeurs sont un CHOIX, l'ordre non.
HX0, HX1 = -274, 226      # ouest 82 derrière l'Azara ; est 81 devant l'Ezrat Nashim
HY0, HY1 = -307, 193      # sud 234,5 ; nord 120,5
box("HarHabayit_sol", HX0, HX1, HY0, HY1, Z_HAR - 1, Z_HAR, "00_HarHabayit", MAT_SOL())
# Cinq portes (Middot 1:3) : deux Houlda au sud, Kiponus à l'ouest, Tadi au nord,
# la porte est sur l'axe. Middot 2:3 leur donne à toutes 20 amot de haut sur 10 de
# large ; leurs abscisses sont un CHOIX.
# Le mur EST est le seul à être bas (Middot 2:4) : le kohen qui brûle la para se tient
# au sommet du mont des Oliviers et doit voir l'ouverture du Heikhal au moment de
# l'aspersion. La ligne de mire passe donc par la porte est, Nikanor et l'Oulam — tous
# centrés sur y = 0 — et rien ne doit s'y trouver.
H_HAR, H_HAR_EST = 30, 24
MUR_HAR = 3                             # épaisseur de l'enceinte
TADI_X, KIPONUS_Y, MIZRAHI_Y = -100, 0, 0
# Les cinq portes, et l'enceinte percée pour elles. `paroi` est la face de l'ESPLANADE :
# c'est de là qu'on les voit, le revers d'un mur de soutènement tombant sur le Kidron ou
# sur la ville. Aucune source ne dore ces שערים-là — Middot 2:3 parle des portes que le
# Temple a fait changer en or, et la fiche ne les compte pas ici : leur cadre et leurs
# timorim se taillent dans la pierre du mur.
PORTES_HAR = (
    ("sud", (HX0, HX1, HY0, HY0 + 3), ("x", HY0 + 3, 1), H_HAR,
     [("Houlda_ouest", -60, 10), ("Houlda_est", 20, 10)]),
    ("nord", (HX0, HX1, HY1 - 3, HY1), ("x", HY1 - 3, -1), H_HAR,
     [("Tadi", TADI_X, 10)]),
    ("ouest", (HX0, HX0 + 3, HY0, HY1), ("y", HX0 + 3, 1), H_HAR,
     [("Kiponus", KIPONUS_Y, 10)]),
    ("est", (HX1 - 3, HX1, HY0, HY1), ("y", HX1 - 3, -1), H_HAR_EST,
     [("Mizrahi", MIZRAHI_Y, 10)]),
)
for _nm, _bornes, _paroi, _h, _portes in PORTES_HAR:
    mur_perce(f"HarHabayit_mur_{_nm}", *_bornes, Z_HAR, Z_HAR + _h,
              "00_HarHabayit", [(c, l) for _, c, l in _portes], 20, MAT_MURAILLE())
    for _porte, _c, _l in _portes:
        shaar(f"HarHabayit_porte_{_porte}", _paroi, _c, Z_HAR, Z_HAR + _h - 3, MUR_HAR,
              "00_HarHabayit", MAT_MURAILLE(), largeur=_l)
# « חוּץ מִשַּׁעַר טָדִי, שֶׁהָיוּ שָׁם שְׁתֵּי אֲבָנִים מֻטּוֹת זוֹ עַל גַּב זוֹ » (Middot 2:3) : la seule
# tête de baie du Temple qui ne soit pas une שְׁקוֹפָה. Deux dalles penchées l'une contre
# l'autre, et non un arc — la michna les compte, et elles se rejoignent sur l'axe. Elles
# se posent DANS la baie, sous le plein du mur : ce qu'on voit en passant est le triangle
# qu'elles laissent. La pente et la portée du sommet sont un CHOIX ; le nombre et
# l'appui l'un sur l'autre ne le sont pas.
TADI_NAISSANCE, TADI_APPUI = 12, 0.3
for _sens in (-1, 1):
    _cote = "O" if _sens < 0 else "E"
    _relief_profil(f"HarHabayit_porte_Tadi_pierre_{_cote}", ("x", HY1, 1),
                   [(TADI_X + _sens * 5, Z_HAR + TADI_NAISSANCE),
                    (TADI_X + _sens * 5, Z_HAR + 20),
                    (TADI_X + _sens * TADI_APPUI, Z_HAR + 20),
                    (TADI_X + _sens * TADI_APPUI, Z_HAR + 20 - 0.6)],
                   -MUR_HAR, 0.0, "00_HarHabayit", MAT_MURAILLE())
# « שַׁעַר הַמִּזְרָחִי, עָלָיו שׁוּשַׁן הַבִּירָה צוּרָה » (Middot 1:3) : le dessin de Suse au-dessus
# de la porte est, tourné vers le mont des Oliviers. Un bas-relief : rempart et trois
# tours crénelées, dans la pierre du mur.
SHUSHAN_Z = Z_HAR + 20.4
box("Shushan_plaque", HX1, HX1 + 0.15, -4.5, 4.5, SHUSHAN_Z, SHUSHAN_Z + 3.2,
    "00_HarHabayit", MAT_MURAILLE())
box("Shushan_rempart", HX1 + 0.15, HX1 + 0.35, -3.8, 3.8, SHUSHAN_Z + 0.3, SHUSHAN_Z + 1.3,
    "00_HarHabayit", MAT_MURAILLE())
for k, y in enumerate((-3.0, 0.0, 3.0)):
    h = 2.6 if y == 0 else 2.0
    box(f"Shushan_tour_{k}", HX1 + 0.15, HX1 + 0.4, y - 0.6, y + 0.6, SHUSHAN_Z + 0.3,
        SHUSHAN_Z + h, "00_HarHabayit", MAT_MURAILLE())
    for j, yc in enumerate((y - 0.45, y, y + 0.45)):
        box(f"Shushan_tour_{k}_merlon_{j}", HX1 + 0.15, HX1 + 0.4, yc - 0.12, yc + 0.12,
            SHUSHAN_Z + h, SHUSHAN_Z + h + 0.25, "00_HarHabayit", MAT_MURAILLE())
# Crête des murs : merlons (CHOIX, appareil hérodien — les stylisations des plans 1 et
# 14b crénelaient d'elles-mêmes cette enceinte, autant que le blockout le fixe).
for nm, xa, xb, ya, yb, h in (("sud", HX0, HX1, HY0, HY0 + 3, H_HAR),
                              ("nord", HX0, HX1, HY1 - 3, HY1, H_HAR),
                              ("ouest", HX0, HX0 + 3, HY0 + 3, HY1 - 3, H_HAR),
                              ("est", HX1 - 3, HX1, HY0 + 3, HY1 - 3, H_HAR_EST)):
    creneaux(f"HarHabayit_creneaux_{nm}", xa, xb, ya, yb, Z_HAR + h, "00_HarHabayit",
             MAT_MURAILLE())
BAIES_HAR = {_nm: [(_c, _l) for _, _c, _l in _portes] for _nm, _, _, _, _portes in PORTES_HAR}
# Face extérieure : un bandeau au niveau de l'esplanade, puis des pilastres jusqu'aux
# merlons. CHOIX (Rambam, Beit HaBe'hira 1:11), dans le parti de l'enceinte hérodienne de
# Hébron, pilastrée au-dessus d'un soubassement nu. Les murs sud et nord prennent les angles.
for nm, bornes, dehors, paroi, h in (
        ("sud", (HX0, HX1, HY0, HY0 + 3), (True, False), ("x", HY0, -1), H_HAR),
        ("nord", (HX0, HX1, HY1 - 3, HY1), (False, True), ("x", HY1, 1), H_HAR),
        ("ouest", (HX0, HX0 + 3, HY0 + 3, HY1 - 3), (True, False), ("y", HX0, -1), H_HAR),
        ("est", (HX1 - 3, HX1, HY0 + 3, HY1 - 3), (False, True), ("y", HX1, 1), H_HAR_EST)):
    angles = ("deborde", "deborde") if nm in ("sud", "nord") else ("libre", "libre")
    moulure(f"HarHabayit_bandeau_{nm}", *bornes, Z_HAR, BANDEAU, "00_HarHabayit", MAT_MURAILLE(),
            saillie=SAILLIE_BANDEAU, mitres=angles, cotes=dehors,
            reserve=[(c - l / 2, c + l / 2) for c, l in BAIES_HAR[nm]])
    travee = (HX0, HX1) if nm in ("sud", "nord") else (HY0, HY1)
    ordre_de_pilastres(f"HarHabayit_pilastre_{nm}", paroi, travee, (Z_HAR, Z_HAR + h),
                       "00_HarHabayit", mat=MAT_MURAILLE(), largeur=3.0, saillie=1.0,
                       reserve=[(c - l / 2 - ENCADREMENT_SHAAR, c + l / 2 + ENCADREMENT_SHAAR)
                                for c, l in BAIES_HAR[nm]])
# Murs de soutènement : l'esplanade est une terrasse bâtie au-dessus du Kidron et du
# Tyropéon, ses murs descendent jusqu'au rocher. Sans lui, le pays passait sous le
# dallage et l'esplanade flottait au-dessus de ses propres vallées.
box("HarHabayit_soubassement", HX0, HX1, HY0, HY1, Z_ROCHE, Z_HAR - 1, "00_HarHabayit",
    MAT_MURAILLE())
pas = 10
# « הַר הַבַּיִת סְטָיו כָּפוּל הָיָה… סְטָיו לִפְנִים מִסְּטָיו » (Pesa'him 13b), que Rashi lit « האיצטבא
# סביב סביב מקפת ובתוך אותו הקף עוד אחר » : deux rangs de colonnes en anneaux, sur les quatre
# côtés — pas un second rang réservé au sud. Distances au mur et rayon : CHOIX.
RANGS_PORTIQUE, R_PORTIQUE = (15, 30), 1.5
# Le portique est est le seul bas, comme son mur (Middot 2:4) : colonnes et toit
# tiennent sous la crête de 24 amot.
H_PORTIQUE, H_PORTIQUE_EST = 25, 21

def _jalons(debut, fin):
    """Bornes incluses, pas ajusté au plus près de `pas` : les angles portent une colonne."""
    n = max(1, round((fin - debut) / pas))
    return [debut + (fin - debut) * i / n for i in range(n + 1)]

def _devant_une_porte(cote, c):
    # Aucune colonne dans l'axe d'une des cinq portes ; celle de l'est garde en plus la
    # ligne de mire de la para (Middot 2:4).
    return any(abs(c - _c) < _l / 2 + R_PORTIQUE for _c, _l in BAIES_HAR[cote])

for k, d in enumerate(RANGS_PORTIQUE):
    xs, ys = _jalons(HX0 + d, HX1 - d), _jalons(HY0 + d, HY1 - d)
    for cote, y in (("sud", ys[0]), ("nord", ys[-1])):
        for i, x in enumerate(xs):
            if not _devant_une_porte(cote, x):
                colonne(f"Portique_{cote}_{k}_{i:03d}", x, y, Z_HAR, Z_HAR + H_PORTIQUE, R_PORTIQUE)
    for cote, x, h in (("ouest", xs[0], H_PORTIQUE), ("est", xs[-1], H_PORTIQUE_EST)):
        for i, y in enumerate(ys[1:-1]):
            if not _devant_une_porte(cote, y):
                colonne(f"Portique_{cote}_{k}_{i:03d}", x, y, Z_HAR, Z_HAR + h, R_PORTIQUE)
# Les portiques sont couverts : la guemara parle du « גַּג הָאִיצְטְבָא » (Pesa'him 13b), le
# TOIT de la colonnade, sur lequel on posait les deux hallot — il y a donc un toit. Du
# mur au rang intérieur, chapiteau compris. À ciel ouvert, les colonnes se
# lisaient d'en haut en rangées de bornes sur le dallage. Cèdre : CHOIX, c'est le bois
# dont le Tanakh couvre le Bayit (Melakhim I 6:9).
PROFONDEUR_PORTIQUE = RANGS_PORTIQUE[-1] + R_PORTIQUE * 1.45 + 0.7
for nm, xa, xb, ya, yb, zt in (
        ("nord", HX0 + 3, HX1 - 3, HY1 - PROFONDEUR_PORTIQUE, HY1 - 3, Z_HAR + H_PORTIQUE),
        ("ouest", HX0 + 3, HX0 + PROFONDEUR_PORTIQUE, HY0 + 32, HY1 - PROFONDEUR_PORTIQUE, Z_HAR + H_PORTIQUE),
        ("est", HX1 - PROFONDEUR_PORTIQUE, HX1 - 3, HY0 + 32, HY1 - PROFONDEUR_PORTIQUE, Z_HAR + H_PORTIQUE_EST),
        ("sud", HX0 + 3, HX1 - 3, HY0 + 3, HY0 + 13, Z_HAR + H_PORTIQUE)):
    box(f"Portique_{nm}_plafond", xa, xb, ya, yb, zt, zt + 1.4, "00_HarHabayit", MAT_CEDRE())
    box(f"Portique_{nm}_toit", xa, xb, ya, yb, zt + 1.4, zt + 2, "00_HarHabayit")
# Le dessus du plafond de la nef sud est de la pierre aussi : vu d'en haut (plans 1, 1b,
# 15), un toit de cèdre faisait une bande brune de cinq cents amot.
box("Portique_sud_nef_toit", HX0, HX1, HY0 + 13, HY0 + 32, Z_HAR + 27, Z_HAR + 27.6, "00_HarHabayit")
# Plafond de la nef du portique sud, entre ses deux rangs. Sans lui la colonnade est
# ouverte au ciel : CAM_02 ne filmait que du fond de monde entre des piliers, et le
# plafond de cèdre du prompt n'avait aucune géométrie à habiller.
box("Portique_sud_nef_plafond", HX0, HX1, HY0 + 13, HY0 + 32, Z_HAR + 25, Z_HAR + 27,
    "00_HarHabayit", MAT_CEDRE())
# Caissons : poutres au pas de la moitié d'une travée, deux sablières sur les axes de
# colonnade. Un plafond lisse ne donnait aucune cadence au travelling du plan 2 —
# c'est la fuite des poutres qui dit la vitesse, et elle est dans la passe Depth.
for i, x in enumerate(plage(HX0 + 2.5, HX1 - 2.5, 5)):
    box(f"Portique_sud_poutre_{i:03d}", x - 0.5, x + 0.5, HY0 + 13, HY0 + 32,
        Z_HAR + 24, Z_HAR + 25, "00_HarHabayit", MAT_CEDRE())
for y in (HY0 + 15, HY0 + 30):
    box(f"Portique_sud_sabliere_{y:+.0f}", HX0, HX1, y - 0.6, y + 0.6,
        Z_HAR + 23.8, Z_HAR + 25, "00_HarHabayit", MAT_CEDRE())
