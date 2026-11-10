from .primitives.parametres import Z_HAR, Z_ROCHE
from .primitives.matieres import MAT_BRONZE, MAT_CEDRE, MAT_MURAILLE, MAT_SOL
from .primitives.volumes import box, colonne, cyl, mur_perce, plage
from .primitives.gravures import _relief_profil
from .primitives.ouvrages import (BANDEAU, ENCADREMENT_SHAAR, EPAISSEUR_PLACAGE, SAILLIE_BANDEAU, VANTAIL_CADRE,
                                  VANTAIL_CLOU, VANTAIL_EP, VANTAIL_PIVOT, VANTAIL_RELIEF, battants, creneaux,
                                  moulure, ordre_de_pilastres, shaar)


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
              "00_HarHabayit", MAT_MURAILLE(), largeur=_l, ressauts=1)
        _axe, _nu, _sens = _paroi
        _dehors = _nu - _sens * MUR_HAR
        # Le même cadre de pierre sur la face qu'on aborde du dehors : les pilastres lui réservent déjà sa place.
        shaar(f"HarHabayit_porte_{_porte}_dehors", (_axe, _dehors, -_sens), _c, Z_HAR, Z_HAR + _h - 3, MUR_HAR,
              "00_HarHabayit", MAT_MURAILLE(), largeur=_l, ressauts=1)
        if _porte == "Tadi":
            continue
        # Plus épais que le mur, les vantaux pivotent à sa face extérieure et débordent sur l'esplanade.
        battants(f"HarHabayit_porte_{_porte}_battants", _axe, _c, _dehors,
                 _dehors + _sens * _l / 2, Z_HAR, 20, "00_HarHabayit", MAT_BRONZE(), largeur=_l)
# « חוּץ מִשַּׁעַר טָדִי, שֶׁהָיוּ שָׁם שְׁתֵּי אֲבָנִים מֻטּוֹת זוֹ עַל גַּב זוֹ » (Middot 2:3) : la seule
# tête de baie du Temple qui ne soit pas une שְׁקוֹפָה. Deux dalles penchées l'une contre
# l'autre, et non un arc — la michna les compte, et elles se rejoignent sur l'axe. Elles
# se posent DANS la baie, sous le plein du mur, et ses vantaux fermés épousent le triangle
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
# « טָדִי מִן הַצָּפוֹן, לֹא הָיָה מְשַׁמֵּשׁ כְּלוּם » (Middot 1:3) : ses vantaux sont fermés, taillés à la baie sous les deux pierres.
TADI_Y, TADI_JEU = HY1 - MUR_HAR / 2, 0.1
TADI_SOMMET = 20 - 0.6 - TADI_JEU


def _tadi_hauteur(u):
    """La hauteur libre de la baie de Tadi à `u` amot de son axe, sous les pierres penchées."""
    pente = (TADI_SOMMET + TADI_JEU - TADI_NAISSANCE) / (5 - TADI_APPUI)
    return min(TADI_SOMMET, TADI_NAISSANCE - TADI_JEU + pente * (5 - abs(u)))


for _sens in (-1, 1):
    _cote = "O" if _sens < 0 else "E"
    _nom = f"HarHabayit_porte_Tadi_vantail_{_cote}"
    _jambage, _milieu = TADI_X + _sens * (5 - EPAISSEUR_PLACAGE), TADI_X + _sens * 0.02
    _relief_profil(_nom, ("x", TADI_Y, 1),
                   [(_jambage, Z_HAR), (_milieu, Z_HAR), (_milieu, Z_HAR + TADI_SOMMET),
                    (TADI_X + _sens * TADI_APPUI, Z_HAR + TADI_SOMMET),
                    (_jambage, Z_HAR + _tadi_hauteur(5))],
                   -VANTAIL_EP / 2, VANTAIL_EP / 2, "00_HarHabayit", MAT_BRONZE())
    cyl(f"{_nom}_pivot", _jambage, TADI_Y, Z_HAR, Z_HAR + _tadi_hauteur(5), VANTAIL_PIVOT, "00_HarHabayit",
        MAT_BRONZE(), verts=12)
    _u0, _u1 = sorted((_jambage, _milieu))
    for _face, _f in (("S", -1), ("N", 1)):
        _nu = TADI_Y + _f * (VANTAIL_EP / 2 + VANTAIL_RELIEF)
        for _k, _z in enumerate((1.0, 5.5, 10.0)):
            box(f"{_nom}_{_face}_bande_{_k}", _u0, _u1, *sorted((TADI_Y + _f * VANTAIL_EP / 2, _nu)),
                Z_HAR + _z, Z_HAR + _z + VANTAIL_CADRE, "00_HarHabayit", MAT_BRONZE())
            for _j in range(4):
                _u = _u0 + 0.6 + (_u1 - _u0 - 1.2) * _j / 3
                box(f"{_nom}_{_face}_clou_{_k}{_j}", _u - VANTAIL_CLOU, _u + VANTAIL_CLOU, *sorted((_nu, _nu + _f * 0.08)),
                    Z_HAR + _z + VANTAIL_CADRE / 2 - VANTAIL_CLOU, Z_HAR + _z + VANTAIL_CADRE / 2 + VANTAIL_CLOU,
                    "00_HarHabayit", MAT_BRONZE())
# « שַׁעַר הַמִּזְרָחִי, עָלָיו שׁוּשַׁן הַבִּירָה צוּרָה » (Middot 1:3) : Suse au-dessus de la porte est, vers le mont des Oliviers.
# Un bas-relief dans la pierre, entre le cadre de la porte et les merlons : rempart, six tours, porte, et la בירה au milieu. Tout : CHOIX.
SHUSHAN_Z, SHUSHAN_H, SHUSHAN_L = Z_HAR + 21.05, 2.9, 8.5


def _shushan(nom, y0, y1, zb, zh, saillie):
    box(f"Shushan_{nom}", HX1, HX1 + saillie, y0, y1, SHUSHAN_Z + zb, SHUSHAN_Z + zh, "00_HarHabayit", MAT_MURAILLE())


def _merlons(nom, y0, y1, z, saillie, pas=0.6):
    n = max(1, round((y1 - y0) / pas))
    for k in range(n):
        yc = y0 + (y1 - y0) * (k + 0.5) / n
        _shushan(f"{nom}_merlon_{k}", yc - pas / 4, yc + pas / 4, z, z + 0.22, saillie)


_shushan("plaque", -SHUSHAN_L, SHUSHAN_L, 0, SHUSHAN_H, 0.15)
for _nom, _zb, _zh in (("cadre_bas", 0, 0.15), ("cadre_haut", SHUSHAN_H - 0.15, SHUSHAN_H)):
    _shushan(_nom, -SHUSHAN_L, SHUSHAN_L, _zb, _zh, 0.3)
for _nom, _y in (("cadre_S", -SHUSHAN_L), ("cadre_N", SHUSHAN_L - 0.15)):
    _shushan(_nom, _y, _y + 0.15, 0.15, SHUSHAN_H - 0.15, 0.3)
_shushan("rempart", -7.6, 7.6, 0.3, 1.2, 0.35)
_merlons("rempart", -7.6, 7.6, 1.2, 0.35)
for _k, _y in enumerate((-7.0, -4.6, -2.2, 2.2, 4.6, 7.0)):
    _shushan(f"tour_{_k}", _y - 0.5, _y + 0.5, 0.3, 1.7, 0.45)
    _merlons(f"tour_{_k}", _y - 0.5, _y + 0.5, 1.7, 0.45, pas=0.5)
for _cote, _y in (("S", -1.3), ("N", 1.3)):
    _shushan(f"porte_tour_{_cote}", _y - 0.4, _y + 0.4, 0.3, 1.9, 0.5)
    _merlons(f"porte_tour_{_cote}", _y - 0.4, _y + 0.4, 1.9, 0.5, pas=0.4)
_shushan("porte_linteau", -0.9, 0.9, 1.0, 1.15, 0.45)
_shushan("bira", -2.0, 2.0, 1.2, 2.2, 0.3)
_merlons("bira", -2.0, 2.0, 2.2, 0.3, pas=0.5)
_shushan("bira_etage", -1.0, 1.0, 2.2, 2.6, 0.3)
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
