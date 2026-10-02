import math

import numpy as np
from mathutils import Vector

import beit_hamikdash_gestes as G
from beit_hamikdash_visite import AMA, Z_EZI, Z_EZN

from ..matieres import BRONZE
from ..corps import Gabarit, Humain
from ..habillage import BRUN, COSTUME, HAUT_Z, _poils, appliquer_visibilite
from ..ustensiles import PANSE_DE_LA_TZELOHIT, PROFIL_DE_LA_TZELOHIT, tourner_profil
from ..mise_en_scene import devant_poitrine, ecouter, repere_vers, tenir, tenir_la_coupe, vers_la_figure
from ..role import Role, _un_cohen


def rase(nom, gabarit, barbe, sourcils):
    poils = _poils(nom, False)
    poils.update(cheveux=None, sourcils=sourcils and poils["sourcils"])
    if not barbe:
        poils["barbe"] = None
    h = Humain(nom, gabarit, **poils)
    h.vetir_mpfb(COSTUME)
    h.detendre()
    appliquer_visibilite(h, h.visible & ~h.efface)
    return h


# « הָיָה נוֹטֵל שְׂעַר רֹאשׁ נִזְרוֹ וּמְשַׁלֵּחַ תַּחַת הַדּוּד » (Nazir 6:8), mouillé du bouillon de ses shelamim (Rambam Nezirout 8:2) :
# à l'ouest du foyer de la lishka (120, −48), la main au-dessus du mur, où le feu paraît sous le chaudron. La place : CHOIX.
NAZIR_OU = (115.0, -47.5, Z_EZN)
SOUS_LE_DOUD = (117.6, -47.5, Z_EZN + 2.9)


def touffe(mm, repere):
    profil = [(0.018 * math.sin(a) + 0.018, 0.034 * math.cos(a) + 0.002) for a in np.linspace(-math.pi / 2, math.pi / 2, 6)]
    tourner_profil(mm, repere, profil, BRUN, n=10)


def repere_de_la_touffe(h):
    a = G.Acteur(h.squelette, h.sol)
    return repere_vers(a.poignet["r"] + a.jointure["r"] * 0.075 + a.paume["r"] * 0.012, a.paume["r"], a.jointure["r"])


def jeter_le_sear(h, a, horloge, t):
    lache = 0.5 - 0.5 * horloge.onde(t, 5.3)
    feu = vers_la_figure(NAZIR_OU, 0.0, SOUS_LE_DOUD, a.sol) + HAUT_Z * (0.05 * lache)
    return G.composer(G.debout(a, horloge, t, 0.4, regard=0.0), G.buste(flexion=0.14), G.tete(flexion=0.32),
                      G.bras(a, "r", feu), G.paume(a, "r", -G.HAUT), G.doigts(a, "r", 0.55 - 0.25 * lache, 0.3))


def _nazir():
    nom = "nazir"

    def batir():
        h = rase(nom, Gabarit(1.74, age=0.40), barbe=True, sourcils=True)
        tenir(h, "sear", touffe, "hand_r", repere_de_la_touffe(h))
        return h
    return Role(nom, nom, batir, jeter_le_sear, NAZIR_OU, 0.0)


# « יְגַלַּח אֶת כָּל שְׂעָרוֹ אֶת רֹאשׁוֹ וְאֶת זְקָנוֹ וְאֵת גַּבֹּת עֵינָיו » (Vayikra 14:9) : rasé la veille, il remonte du mikve de la
# lishka (Nega'im 14:8), habillé ; au bord sud de la cuve, tourné vers la porte : CHOIX.
GABARIT_DU_METZORA = Gabarit(1.72, age=0.50)


def le_metzora(nom):
    return rase(nom, GABARIT_DU_METZORA, barbe=False, sourcils=False)


# « הִכְנִיס רֹאשׁוֹ, וְנָתַן עַל תְּנוּךְ אָזְנוֹ » (Nega'im 14:9) ; « הַכֹּהֵן מִבִּפְנִים וְהַמְצֹרָע מִבַּחוּץ… וּפָנָיו לְמַעֲרָב » (Rambam
# Me'houssrei Kappara 4:2) : sur le seuil de Nikanor, le metzora penche la tête dans l'Azara ; le cohen, le sang dans la paume
# gauche, en touche du doigt droit le lobe de l'oreille droite — au nord du metzora tourné vers l'ouest. Les places : CHOIX.
METZORA_AU_SEUIL = (0.45, 0.0, Z_EZI)
PENCHE = 0.45
OREILLE_DU_METZORA = (METZORA_AU_SEUIL[0] - 0.26 / AMA, 0.08 / AMA, Z_EZI + 1.52 / AMA)
COHEN_A_L_OREILLE = (-1.3, 0.5, Z_EZI)
SANG = (0.30, 0.015, 0.015)
SHEMEN = (0.62, 0.50, 0.12)


def passer_la_tete(h, a, horloge, t):
    return G.composer(G.debout(a, horloge, t, 0.2, regard=0.0), G.buste(flexion=PENCHE), G.tete(flexion=-0.10),
                      G.bras_ballant(a, "l"), G.bras_ballant(a, "r"))


def goutte(couleur):
    def construire(mm, repere):
        tourner_profil(mm, repere, ((0.0, 0.028), (0.004, 0.024), (0.006, 0.0)), couleur, n=12)
    return construire


def repere_du_creux(h, cote):
    a = G.Acteur(h.squelette, h.sol)
    return repere_vers(a.poignet[cote] + a.jointure[cote] * 0.055 + a.paume[cote] * 0.012, a.paume[cote], a.jointure[cote])


PAUME_OUVERTE = 0.32


def paume_ouverte(h, a):
    return G.composer(G.bras(a, "l", devant_poitrine(h, 0.30, PAUME_OUVERTE, 0.10)), G.paume(a, "l", G.HAUT), G.doigts(a, "l", 0.12, 0.1))


def toucher_l_oreille(h, a, horloge, t):
    oreille = vers_la_figure(COHEN_A_L_OREILLE, 0.0, OREILLE_DU_METZORA, a.sol)
    main = oreille + Vector((0.03, 0.13, -0.02))
    return G.composer(G.debout(a, horloge, t, 0.5, regard=0.0), G.tete(flexion=0.10), paume_ouverte(h, a),
                      G.bras(a, "r", main), G.paume(a, "r", G.GAUCHE), G.doigts(a, "r", 0.45, 0.35))


def _cohen_et_sa_paume(nom, couleur, ages):
    def batir():
        h = _un_cohen(nom, ages)
        tenir(h, "creux", goutte(couleur), "hand_l", repere_du_creux(h, "l"))
        return h
    return batir


# « טוֹבֵל אֶצְבָּעוֹ הַיְמָנִית בַּשֶּׁמֶן שֶׁבְּכַפּוֹ וּמַזֶּה שֶׁבַע פְּעָמִים כְּנֶגֶד בֵּית קֹדֶשׁ הַקֳּדָשִׁים » (Rambam Me'houssrei Kappara 4:2) :
# l'huile versée dans la paume gauche du compagnon, c'est lui qui trempe — « מִן הַשֶּׁמֶן אֲשֶׁר עַל כַּפּוֹ הַשְּׂמָאלִית » (Vayikra 14:16).
# Tourné vers l'ouest dans l'Ezrat Israël, près de Nikanor ; celui qui a versé tient le log. Places et forme du vase : CHOIX.
DUREE_DES_HAZAOT = 14.0


def repere_du_log(h):
    return repere_vers(devant_poitrine(h, 0.30, 0.38), G.HAUT, G.GAUCHE)


def log(mm, repere):
    tourner_profil(mm, repere, tuple((z * 0.7, r * 0.7) for z, r in PROFIL_DE_LA_TZELOHIT), BRONZE)


def mazeh(h, a, horloge, t):
    periode = horloge.duree / 7
    u = (t % periode) / periode
    trempe = 1.0 - G.lisse(u / 0.35)
    fouet = G.lisse((u - 0.55) / 0.15) * (1.0 - G.lisse((u - 0.85) / 0.15))
    creux = a.au("spine_03", devant_poitrine(h, 0.30, PAUME_OUVERTE, 0.10) + HAUT_Z * 0.07)
    vise = a.au("spine_03", devant_poitrine(h, 0.50, 0.12, -0.04))

    def droite(poses):
        return creux(poses).lerp(vise(poses), 1.0 - trempe) + G.DEVANT * (0.06 * fouet) - HAUT_Z * (0.08 * fouet)
    return G.composer(G.debout(a, horloge, t, 0.1, regard=0.0), G.tete(flexion=0.04), paume_ouverte(h, a),
                      G.bras(a, "r", droite), G.paume(a, "r", -G.HAUT), G.doigts(a, "r", 0.45, 0.4))


def _taharat_hametzora():
    return [Role("taharat_hametzora_1", "taharat_hametzora", lambda: le_metzora("taharat_hametzora_1"), passer_la_tete,
                 METZORA_AU_SEUIL, 180.0),
            Role("taharat_hametzora_2", "taharat_hametzora", _cohen_et_sa_paume("taharat_hametzora_2", SANG, (0.40, 0.35)),
                 toucher_l_oreille, COHEN_A_L_OREILLE, 0.0, famille="cohanim")]


def _log_hashemen():
    def yotzek():
        h = _un_cohen("log_hashemen_1", (0.50, 0.35))
        tenir(h, "log", log, "spine_03", repere_du_log(h))
        return h
    return [Role("log_hashemen_1", "log_hashemen", yotzek, tenir_la_coupe(0.7 * PANSE_DE_LA_TZELOHIT + 0.015), (-3.4, 2.1, Z_EZI),
                 -120.0, famille="cohanim"),
            Role("log_hashemen_2", "log_hashemen", _cohen_et_sa_paume("log_hashemen_2", SHEMEN, (0.35, 0.30)), mazeh,
                 (-4.2, 0.4, Z_EZI), 180.0, duree=DUREE_DES_HAZAOT, famille="cohanim")]


def roles_nazir():
    return [_nazir(),
            Role("metzora", "metzora", lambda: le_metzora("metzora"), ecouter, (25.0, 46.4, Z_EZN), -90.0),
            *_taharat_hametzora(), *_log_hashemen()]
