import math

import numpy as np
from mathutils import Vector

import beit_hamikdash_gestes as G
from beit_hamikdash_visite import AMA, Z_EZN

from ..matieres import ARGAMAN, CHENE, LIN, OR, metal
from ..etoffes import Habit
from ..corps import Gabarit, Humain, _alea
from ..maillage import Maillage, _angles, _lisser_cercle, _vers, enveloppe, pave
from ..habillage import HAUT_Z, ROBE, _crane_et_cheveux, _poils, appliquer_visibilite, lier, porter
from ..ustensiles import sefer, tabouret
from ..mise_en_scene import (RECUL_ASSIS, assis, devant_poitrine, ecouter, lire_le_sefer, repere_vers, tenir,
                             tenir_le_sefer, vers_la_figure)
from ..bigdei_kehouna import cohen_gadol_en_or
from ..tenues import fidele
from ..role import Role


# « וּמְבִיאִין בִּימָה גְּדוֹלָה וְשֶׁל עֵץ הָיְתָה וּמַעֲמִידִין אוֹתָהּ בְּאֶמְצַע עֶזְרַת נָשִׁים » (Rambam 'Haguiga 3:4) : la cour va de
# x 5 à 140. Six amot de côté, trois de haut, cinq marches à l'ouest : CHOIX.
BIMA_OU = (72.5, 0.0, Z_EZN)
COTE_DE_LA_BIMA = 6.0
HAUT_DE_LA_BIMA = 3.0
MARCHES_DE_LA_BIMA = 5
LARGEUR_DES_MARCHES = 3.0
SUR_LA_BIMA = Z_EZN + HAUT_DE_LA_BIMA


def _bloc(mm, vers_ici, x0, x1, y0, y1, z0, z1):
    est, nord = vers_ici((1.0, 0.0, 0.0)) - vers_ici((0.0, 0.0, 0.0)), vers_ici((0.0, 1.0, 0.0)) - vers_ici((0.0, 0.0, 0.0))
    centre = vers_ici(((x0 + x1) / 2, (y0 + y1) / 2, z0))
    pave(mm, centre, est.normalized(), nord.normalized(), ((x1 - x0) * AMA, (y1 - y0) * AMA), (z1 - z0) * AMA, CHENE, "objet")


# La bima dans le repère d'une figure posée en `ou`, tournée vers `cap`.
def bimat_etz(mm, ou, cap, sol):
    cx, cy, z = BIMA_OU

    def vers_ici(p):
        return vers_la_figure(ou, cap, (cx + p[0], cy + p[1], z + p[2]), sol)
    d, haut, planche = COTE_DE_LA_BIMA / 2, HAUT_DE_LA_BIMA, 0.25
    _bloc(mm, vers_ici, -d, d, -d, d, haut - planche, haut)
    for x0, x1, y0, y1 in ((-d, d, -d, -d + planche), (-d, d, d - planche, d), (-d, -d + planche, -d, d), (d - planche, d, -d, d)):
        _bloc(mm, vers_ici, x0, x1, y0, y1, 0.0, haut - planche)
    marche = haut / (MARCHES_DE_LA_BIMA + 1)
    for k in range(MARCHES_DE_LA_BIMA):
        _bloc(mm, vers_ici, -d - MARCHES_DE_LA_BIMA + k, -d, -LARGEUR_DES_MARCHES / 2, LARGEUR_DES_MARCHES / 2, 0.0, (k + 1) * marche)


def sur_la_marche(k, y=0.0):
    return (BIMA_OU[0] - COTE_DE_LA_BIMA / 2 - MARCHES_DE_LA_BIMA + k + 0.5, y, Z_EZN + (k + 1) * HAUT_DE_LA_BIMA / (MARCHES_DE_LA_BIMA + 1))


# « לֹא בְּכִתְרוֹ » (Rambam Melakhim 2:1) : le roi a sa couronne ; un cercle d'or à six fleurons, CHOIX.
def atara(h, fleurons=6, n=48):
    yeux = h.points_objet(h.accessoires[0]).mean(axis=0)
    z = float(yeux[2]) + 0.055
    points = _crane_et_cheveux(h)
    bande = points[np.abs(points[:, 2] - z) < 0.01]
    cy = 0.5 * (bande[:, 1].min() + bande[:, 1].max())
    r = _lisser_cercle(enveloppe(bande, (0.0, cy), n), 3) + 0.006
    th = _angles(n)

    def anneau(dehors, hauteur):
        return [Vector(((a + dehors) * _vers(t)[0], cy + (a + dehors) * _vers(t)[1], z + hauteur(t))) for t, a in zip(th, r)]
    pointe = lambda t: 0.026 + 0.024 * max(0.0, math.cos(fleurons * t)) ** 6
    mm = Maillage()
    mm.nappe([anneau(0.0, lambda t: 0.0), anneau(0.004, lambda t: 0.0), anneau(0.004, pointe), anneau(0.0, pointe),
              anneau(0.0, lambda t: 0.0)], OR, "head")
    lier(h, mm, f"{h.nom}_atara", metal(), "head")


# L'argaman du « תַכְרִיךְ בּוּץ וְאַרְגָּמָן » de Mordekhaï (Esther 8:15), sur la robe longue : CHOIX.
ROBE_ROYALE = Habit("punkduck_medieval_dress", "Figure_Robe_Royale", ARGAMAN, longue=True)


def melekh(nom, qui, gabarit):
    h = Humain(nom, gabarit, qui=qui, **_poils(qui, False))
    h.vetir_mpfb(ROBE_ROYALE)
    h.detendre()
    atara(h)
    appliquer_visibilite(h, h.visible & ~h.efface)
    return h


# « יוֹצְאָה וְרֹאשָׁהּ פָּרוּעַ » est contre la dat yehoudit (Ketoubot 7:6) : la tête sous un voile.
VOILE = Habit("elvs_charity_veil1", "Figure_Voile", LIN)


def femme(nom, gabarit):
    h = Humain(nom, gabarit, sourcils=1 + int(_alea(nom, 6) * 9))
    h.vetir_mpfb(ROBE)
    h.vetir_mpfb(VOILE)
    h.detendre()
    appliquer_visibilite(h, h.visible & ~h.efface)
    return h


MELEKH = "melekh"
GABARIT_DU_MELEKH = Gabarit(1.76, age=0.55)
SIEGE_DU_MELEKH = 0.46


def _avec_la_bima(h, ou, cap):
    mm = Maillage()
    bimat_etz(mm, ou, cap, h.sol)
    porter(h, mm, f"{h.nom}_bima")
    return h


# « וְהוּא יוֹשֵׁב עָלֶיהָ » (Sota 7:8) : il lit assis, tourné vers l'est où le peuple entre ; le siège et le cap sont des CHOIX.
def _melekh_yoshev():
    nom, ou = "parashat_hamelekh_1", (*BIMA_OU[:2], SUR_LA_BIMA)

    def geste(h, a, horloge, t):
        return lire_le_sefer(h, a, assis(a, horloge, t, SIEGE_DU_MELEKH), horloge, t)

    def batir():
        h = tenir_le_sefer(_avec_la_bima(melekh(nom, MELEKH, GABARIT_DU_MELEKH), ou, 0.0))
        mm = Maillage()
        tabouret(mm, Vector((0.0, RECUL_ASSIS, h.sol)), SIEGE_DU_MELEKH)
        porter(h, mm, f"{nom}_kisse")
        return h
    return Role(nom, "parashat_hamelekh", batir, geste, ou, 0.0, sol_porte=True)


# « אַגְרִיפָּס הַמֶּלֶךְ עָמַד וְקִבֵּל וְקָרָא עוֹמֵד » (Sota 7:8) : debout, la tête plus basse — il pleure (CHOIX du geste).
def _agrippas():
    nom, ou = "agrippas", (*BIMA_OU[:2], SUR_LA_BIMA)

    def geste(h, a, horloge, t):
        return G.composer(lire_le_sefer(h, a, G.debout(a, horloge, t, 0.3, regard=0.0), horloge, t), G.tete(flexion=0.45))

    return Role(nom, "agrippas", lambda: tenir_le_sefer(_avec_la_bima(melekh(nom, "agrippas", Gabarit(1.73, age=0.45)), ou, 0.0)),
                geste, ou, 0.0, sol_porte=True)


# « וְכֹהֵן גָּדוֹל נוֹתְנָהּ לַמֶּלֶךְ, וְהַמֶּלֶךְ עוֹמֵד וּמְקַבֵּל » (Sota 7:8) : le rouleau fermé, droit, passe d'une paire de mains à
# l'autre ; le roi tourné vers l'ouest, d'où il vient. Les places sur la bima et ses marches : CHOIX.
MELEKH_OMED_OU = (*BIMA_OU[:2], SUR_LA_BIMA)
COHEN_GADOL_A_LA_BIMA = (BIMA_OU[0] - 1.6, BIMA_OU[1], SUR_LA_BIMA)
SEFER_FERME = 0.12
SEFER_TENDU = 0.30


def repere_du_sefer_tendu(h):
    return repere_vers(devant_poitrine(h, SEFER_TENDU, 0.30), HAUT_Z, G.GAUCHE)


def _mains_au_rouleau(a, cibles):
    return G.composer(G.bras(a, "l", cibles["l"]), G.bras(a, "r", cibles["r"]),
                      G.paume(a, "l", lambda poses: a.dans("spine_03", poses, -G.GAUCHE)),
                      G.paume(a, "r", lambda poses: a.dans("spine_03", poses, G.GAUCHE)),
                      G.doigts(a, "l", 0.9, 0.6), G.doigts(a, "r", 0.9, 0.6))


def tendre_le_sefer(h, a, horloge, t):
    rouleau = a.repere("spine_03", repere_du_sefer_tendu(h))
    return G.composer(G.debout(a, horloge, t, 0.6, regard=0.0), G.tete(flexion=0.15),
                      _mains_au_rouleau(a, {c: (lambda poses, s=s: rouleau(poses) @ Vector((s * SEFER_FERME / 2, 0.02, -0.10)))
                                            for c, s in (("l", 1.0), ("r", -1.0))}))


def recevoir_le_sefer(h, a, horloge, t):
    loin = (MELEKH_OMED_OU[0] - COHEN_GADOL_A_LA_BIMA[0]) * AMA - SEFER_TENDU
    return G.composer(G.debout(a, horloge, t, 0.6, regard=0.0), G.tete(flexion=0.15),
                      _mains_au_rouleau(a, {c: devant_poitrine(h, loin - 0.02, 0.20, s * SEFER_FERME / 2)
                                            for c, s in (("l", 1.0), ("r", -1.0))}))


def _haavarat_hasefer():
    def cohen_gadol_et_le_sefer():
        h = cohen_gadol_en_or("haavarat_hasefer_1")
        tenir(h, "sefer", lambda mm, r: sefer(mm, r, ecart=SEFER_FERME), "spine_03", repere_du_sefer_tendu(h))
        return h

    def passeur(nom, ou, gabarit, tete):
        return Role(nom, "haavarat_hasefer", lambda: fidele(nom, "costume", gabarit, gris=gabarit.age > 0.7, tete=tete), ecouter,
                    ou, 0.0, sol_porte=ou[2] > Z_EZN)
    return [Role("haavarat_hasefer_5", "haavarat_hasefer",
                 lambda: _avec_la_bima(melekh("haavarat_hasefer_5", MELEKH, GABARIT_DU_MELEKH), MELEKH_OMED_OU, 180.0),
                 recevoir_le_sefer, MELEKH_OMED_OU, 180.0, sol_porte=True),
            # En habits d'or : il les porte « בְּיוֹם עֲבוֹדָתוֹ וַאֲפִלּוּ שֶׁלֹּא בִּשְׁעַת עֲבוֹדָה » (Rambam Klei HaMikdash 8:11), CHOIX.
            Role("haavarat_hasefer_1", "haavarat_hasefer", cohen_gadol_et_le_sefer, tendre_le_sefer, COHEN_GADOL_A_LA_BIMA, 0.0,
                 famille="cohanim", sol_porte=True),
            # Le segan hors de son service n'a pas l'avnet, qui est de sha'atnez (8:11) : en habit à lui, CHOIX.
            passeur("haavarat_hasefer_2", sur_la_marche(2, 0.3), Gabarit(1.74, age=0.58), "talith"),
            passeur("haavarat_hasefer_3", (BIMA_OU[0] - 9.2, 0.7, Z_EZN), Gabarit(1.69, age=0.78, peau="old_caucasian_male"),
                    "talith"),
            passeur("haavarat_hasefer_4", (BIMA_OU[0] - 11.0, -0.9, Z_EZN), Gabarit(1.72, age=0.42), "kippa")]


# « וְכָל יִשְׂרָאֵל הָעוֹלִים לָחֹג מִתְקַבְּצִין סְבִיבָיו » (Rambam 'Haguiga 3:4) ; « הָאֲנָשִׁים וְהַנָּשִׁים וְהַטַּף » (Devarim 31:12).
# Les hommes et les enfants autour de la bima, l'ouest laissé aux marches ; les femmes à la gezuztra, « שֶׁהַנָּשִׁים רוֹאוֹת
# מִלְמַעְלָן וְהָאֲנָשִׁים מִלְּמַטָּן » (Middot 2:5). Les places : CHOIX.
HOMMES_DU_KAHAL = ((80.0, 3.0), (80.5, -2.5), (79.0, 6.5), (78.6, -6.8), (82.8, 0.6), (76.2, 9.2), (75.2, -9.6), (83.2, 5.6),
                   (83.6, -5.0), (71.0, 9.6), (70.0, -9.2), (85.8, -1.6))
ENFANTS_DU_KAHAL = ((81.4, -0.9), (77.6, 8.0), (77.2, -8.4), (84.6, 3.4))
# Sur la dalle nord de la gezuztra (y 64 à 67,5, dessus à 6,6), entre les dés de sa balustrade.
FEMMES_DU_KAHAL = (65.0, 67.4, 71.6, 73.6, 78.0, 80.2)
Y_DES_FEMMES, Z_DE_LA_GEZUZTRA = 65.3, 6.6


def cap_vers_la_bima(x, y):
    return math.degrees(math.atan2(BIMA_OU[1] - y, BIMA_OU[0] - x))


def _ish(k, x, y):
    nom = f"kahal_{k + 1}"
    age = 0.30 + 0.60 * _alea(nom, 0)
    gabarit = Gabarit(1.64 + 0.18 * _alea(nom, 1), age=age, poids=0.35 + 0.35 * _alea(nom, 2),
                      peau="old_caucasian_male" if age > 0.8 else "middleage_caucasian_male")
    return Role(nom, "kahal", lambda: fidele(nom, "costume", gabarit, gris=age > 0.7), ecouter, (x, y, Z_EZN),
                cap_vers_la_bima(x, y) + 12.0 * (_alea(nom, 4) - 0.5))


def _tinok(k, x, y):
    nom = f"kahal_{len(HOMMES_DU_KAHAL) + k + 1}"
    gabarit = Gabarit(1.12 + 0.16 * _alea(nom, 1), age=0.10 + 0.06 * _alea(nom, 0), peau="young_caucasian_male")
    return Role(nom, "kahal", lambda: fidele(nom, "robe", gabarit, barbe=False), ecouter, (x, y, Z_EZN),
                cap_vers_la_bima(x, y) + 16.0 * (_alea(nom, 4) - 0.5))


def _isha(k, x):
    nom = f"kahal_{len(HOMMES_DU_KAHAL) + len(ENFANTS_DU_KAHAL) + k + 1}"
    age = 0.25 + 0.60 * _alea(nom, 0)
    peau = "young_caucasian_female" if age < 0.4 else "old_caucasian_female" if age > 0.75 else "middleage_caucasian_female"
    gabarit = Gabarit(1.55 + 0.10 * _alea(nom, 1), genre=0.0, age=age, muscle=0.4, poids=0.35 + 0.3 * _alea(nom, 2), peau=peau)
    return Role(nom, "kahal", lambda: femme(nom, gabarit), ecouter, (x, Y_DES_FEMMES, Z_DE_LA_GEZUZTRA),
                cap_vers_la_bima(x, Y_DES_FEMMES) + 10.0 * (_alea(nom, 4) - 0.5))


def roles_hakhel():
    return [_melekh_yoshev(), _agrippas(), *_haavarat_hasefer(),
            *[_ish(k, x, y) for k, (x, y) in enumerate(HOMMES_DU_KAHAL)],
            *[_tinok(k, x, y) for k, (x, y) in enumerate(ENFANTS_DU_KAHAL)],
            *[_isha(k, x) for k, x in enumerate(FEMMES_DU_KAHAL)]]
