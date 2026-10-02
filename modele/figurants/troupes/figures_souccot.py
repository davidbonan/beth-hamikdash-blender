import numpy as np
from mathutils import Matrix, Vector

import beit_hamikdash_gestes as G
from beit_hamikdash_visite import AMA, Z_AZ, Z_EZN

from ..maillage import Maillage, pave, tube
from ..habillage import porter
from ..ustensiles import PANSE_DE_LA_TZELOHIT, PROFIL_DE_LA_TZELOHIT, tourner_profil, tzelohit
from ..mise_en_scene import (Stade, devant_poitrine, repere_mizrak, repere_vers, tenir, tenir_la_coupe,
                             vers_la_figure)
from ..role import Role, _tokea, _un_cohen


# Souccot au matin (Soucca 4:5, 4:9) : une étape, ses figurants.
# « הִגִּיעוּ לְשַׁעַר הַמַּיִם, תָּקְעוּ וְהֵרִיעוּ וְתָקְעוּ » (Soucca 4:9) : le cohen passe la porte, la tzelo'hit devant lui ;
# deux cohanim sonnent sur le seuil. Qui sonne, et où : CHOIX.
def _shaar_hamayim():
    nom = "nissoukh_hamayim_1"

    def batir():
        h = _un_cohen(nom, (0.40, 0.30))
        tenir(h, "tzelohit", tzelohit, "spine_03", repere_mizrak(h))
        return h
    return [Role(nom, "nissoukh_hamayim", batir, tenir_la_coupe(PANSE_DE_LA_TZELOHIT + 0.015), (-12.0, -86.8, Z_EZN), 90.0,
                 famille="cohanim"),
            _tokea("tekiot_shaar_hamayim_1", "tekiot_shaar_hamayim", (-15.0, -83.6, Z_EZN), -80.0),
            _tokea("tekiot_shaar_hamayim_2", "tekiot_shaar_hamayim", (-9.0, -83.6, Z_EZN), -100.0)]


# « עָלָה בַכֶּבֶשׁ וּפָנָה לִשְׂמֹאלוֹ … וְלַמְנַסֵּךְ אוֹמְרִים לוֹ, הַגְבַּהּ יָדֶךָ » (Soucca 4:9) : face à l'ouest, derrière le sefel du
# vin, la main levée au-dessus de celui de l'eau, « מַעֲרָבִי שֶׁל מַיִם » ; la hauteur du geste : CHOIX.
SEFEL_HAMAYIM = (-50.5, -22.5, 9.3)
MENASEKH_OU = (-48.9, -22.5, 9.0)


def _nissoukh_hamayim():
    nom = "nissoukh_hamayim_2"

    def tzelohit_penchee(h):
        bouche = vers_la_figure(MENASEKH_OU, 180.0, SEFEL_HAMAYIM, h.sol) + Vector((0.0, 0.0, 1.40))
        axe = Vector((0.0, -0.45, -0.89)).normalized()
        return repere_vers(bouche - axe * PROFIL_DE_LA_TZELOHIT[-1][0], axe, G.GAUCHE)

    def batir():
        h = _un_cohen(nom, (0.40, 0.30))
        mm = Maillage()
        tzelohit(mm, tzelohit_penchee(h))
        porter(h, mm, f"{nom}_tzelohit")
        return h

    def geste(h, a, horloge, t):
        panse = tzelohit_penchee(h) @ Vector((-(PANSE_DE_LA_TZELOHIT + 0.035), 0.0, 0.07))
        return G.composer(G.debout(a, horloge, t, 0.3, regard=0.0), G.tete(flexion=0.18), G.buste(flexion=0.05),
                          G.bras(a, "r", panse), G.paume(a, "r", G.GAUCHE), G.doigts(a, "r", 0.6, 0.4),
                          G.bras_ballant(a, "l"), G.doigts(a, "l", 0.35, 0.15))
    return [Role(nom, "nissoukh_hamayim", batir, geste, MENASEKH_OU, 180.0, famille="cohanim")]


# « וּבָאִין וְזוֹקְפִין אוֹתָן בְּצִדֵּי הַמִּזְבֵּחַ, וְרָאשֵׁיהֶן כְּפוּפִין עַל גַּבֵּי הַמִּזְבֵּחַ » (Soucca 4:5) : « גְּבוֹהוֹת אַחַת עֶשְׂרֵה אַמָּה,
# כְּדֵי שֶׁיְּהוּ גּוֹחוֹת עַל הַמִּזְבֵּחַ אַמָּה », « עַל הַיְּסוֹד מַנַּח לְהוּ » (Soucca 45a) — le long du yessod nord et ouest ;
# leur nombre, leur écart et le feuillage : CHOIX.
SAULE, BOIS_DE_SAULE = (0.32, 0.40, 0.20), (0.36, 0.22, 0.13)
ARAVOT_NORD = [(x, 6.4) for x in np.arange(-51.5, -23.0, 1.25)]
ARAVOT_OUEST = [(-53.35, y) for y in np.arange(4.5, -21.0, -1.25)]


# `vers` : d'un point du Temple, en amot, au repère de la figure qui les porte.
def arava(mm, vers, pied, dedans):
    x, y = pied
    d = Vector((*dedans, 0.0))
    base = Vector((x, y, Z_AZ + 1.0))
    chemin = [vers(base + d * dx + Vector((0.0, 0.0, dz))) for dx, dz in
              ((0.0, 0.0), (1.0, 8.5), (1.35, 10.0), (2.0, 10.7), (2.6, 10.3))]
    mm.nappe(tube(chemin, [0.020, 0.013, 0.010, 0.007, 0.003], 6), BOIS_DE_SAULE, "objet")
    for k in range(26):
        u = 0.35 + 0.63 * k / 25
        i = min(int(u * (len(chemin) - 1)), len(chemin) - 2)
        f = u * (len(chemin) - 1) - i
        p = chemin[i].lerp(chemin[i + 1], f)
        tige = (chemin[i + 1] - chemin[i]).normalized()
        cote = tige.cross(Vector((0.0, 0.0, 1.0)) if abs(tige.z) < 0.9 else Vector((1.0, 0.0, 0.0))).normalized()
        cote = Matrix.Rotation(2.4 * k, 3, tige) @ cote
        feuille = (tige * 0.5 + cote).normalized()
        pave(mm, p + feuille * 0.045, feuille, tige.cross(feuille).normalized(), (0.085, 0.013), 0.002, SAULE, "objet")


def aravot(mm, vers):
    for pied in ARAVOT_NORD:
        arava(mm, vers, pied, (0.0, -1.0))
    for pied in ARAVOT_OUEST:
        arava(mm, vers, pied, (1.0, 0.0))


# « וּבְעֵת שֶׁהָיוּ מְבִיאִין אוֹתָהּ וְסוֹדְרִין אוֹתָהּ תּוֹקְעִין וּמְרִיעִין וְתוֹקְעִין » (Rambam Loulav 7:21) : un cohen dresse la
# dernière branche au nord, deux sonnent ; leur place : CHOIX.
DRESSEUR_OU = (-30.25, 7.7, Z_AZ)


def _aravot():
    nom = "aravot_1"

    def batir():
        h = _un_cohen(nom)
        mm = Maillage()
        aravot(mm, lambda p: vers_la_figure(DRESSEUR_OU, -90.0, p, h.sol))
        porter(h, mm, f"{nom}_aravot")
        return h

    def geste(h, a, horloge, t):
        tige = vers_la_figure(DRESSEUR_OU, -90.0, (DRESSEUR_OU[0], 6.4, Z_AZ + 1.0), a.sol)
        vers = Vector((0.0, -1.0, 8.5)).normalized()
        return G.composer(G.debout(a, horloge, t, 0.2, regard=0.02), G.tete(flexion=-0.25), G.buste(flexion=0.08),
                          G.bras(a, "l", tige + vers * 1.30 + Vector((0.04, 0.04, 0.0))),
                          G.bras(a, "r", tige + vers * 0.90 + Vector((-0.04, 0.04, 0.0))),
                          G.paume(a, "l", -G.GAUCHE + G.DEVANT), G.paume(a, "r", G.GAUCHE + G.DEVANT),
                          G.doigts(a, "l", 0.8, 0.5), G.doigts(a, "r", 0.8, 0.5))
    return [Role(nom, "aravot", batir, geste, DRESSEUR_OU, -90.0, famille="cohanim"),
            _tokea("aravot_2", "aravot", (-27.0, 11.5, Z_AZ), -100.0),
            _tokea("aravot_3", "aravot", (-34.0, 11.5, Z_AZ), -80.0)]


# En amot : une boucle fermée par `sommets`, coins arrondis de `rayon` ; `depart` fait partir la figure plus loin sur la boucle.
class Boucle(Stade):
    def __init__(self, sommets, rayon, depart=0.0, pas=0.04):
        sommets, r = [Vector(s) * AMA for s in sommets], rayon * AMA
        points = []
        for i, coin in enumerate(sommets):
            avant, apres = sommets[i - 1], sommets[(i + 1) % len(sommets)]
            debut, fin = coin + (avant - coin).normalized() * r, coin + (apres - coin).normalized() * r
            points += [debut * (1 - u) ** 2 + coin * (2 * u * (1 - u)) + fin * u * u for u in np.linspace(0.0, 1.0, 8, endpoint=False)]
            suivant = apres + (coin - apres).normalized() * r
            m = max(2, int((suivant - fin).length / pas))
            points += [fin.lerp(suivant, j / m) for j in range(m)]
        self.points = points
        self.cumul = [0.0]
        for p, q in zip(points, points[1:] + points[:1]):
            self.cumul.append(self.cumul[-1] + (q - p).length)
        self.longueur = self.cumul[-1]
        self.decalage = depart * AMA

    def en(self, s):
        return super().en(s + self.decalage)


# « בְּכָל יוֹם וָיוֹם הָיוּ מַקִּיפִין אֶת הַמִּזְבֵּחַ בְּלוּלְבֵיהֶן בִּידֵיהֶן » (Rambam Loulav 7:23) ; les cohanim seuls, car
# l'Israélite n'entre pas entre l'Oulam et l'autel (Tosfot Yom Tov sur Soucca 4:5). Autour de l'autel et de son kevesh, au sol ;
# le sens, le nombre et l'etrog dans la gauche : CHOIX.
TOUR_DE_L_AUTEL = ((-21.0, 9.0), (-55.2, 9.0), (-55.2, -55.5), (-25.5, -55.5), (-25.5, -26.0), (-21.0, -23.0))
MAKIFIM = 6
LOULAV, HADAS, ETROG = (0.46, 0.50, 0.25), (0.14, 0.30, 0.12), (0.85, 0.70, 0.18)


def loulav(mm, repere):
    tige = [Vector((0.0, 0.0, z)) for z in np.linspace(-0.12, 0.95, 6)]
    mm.nappe([[repere @ p for p in a] for a in tube(tige, [0.012, 0.012, 0.011, 0.010, 0.008, 0.003], 6)], LOULAV, "objet")
    for s in (-1.0, 1.0):
        for k, z in enumerate(np.linspace(0.02, 0.32, 7)):
            p = Vector((s * 0.018, 0.0, z))
            pave(mm, repere @ (p + Vector((0.0, 0.0, 0.08))), repere.to_3x3() @ Vector((0.15 * s, 0.0, 1.0)).normalized(),
                 repere.to_3x3() @ Vector((0.0, 1.0, 0.0)), (0.18, 0.02), 0.003, HADAS if k % 2 else SAULE, "objet")


def etrog(mm, repere):
    tourner_profil(mm, repere, ((-0.060, 0.004), (-0.050, 0.030), (-0.020, 0.042), (0.020, 0.042), (0.050, 0.028),
                                (0.065, 0.006)), ETROG, n=12)


def repere_du_loulav(h):
    return repere_vers(devant_poitrine(h, 0.26, 0.34, -0.07), G.HAUT + G.DEVANT * 0.15, G.GAUCHE)


def repere_de_l_etrog(h):
    return repere_vers(devant_poitrine(h, 0.27, 0.38, 0.06), G.GAUCHE, G.HAUT)


def loulav_et_etrog(h, a, horloge, t):
    loulav_ = a.repere("spine_03", repere_du_loulav(h))
    etrog_ = a.repere("spine_03", repere_de_l_etrog(h))
    return G.composer(G.bras(a, "r", lambda poses: loulav_(poses) @ Vector((-0.03, 0.02, 0.0))),
                      G.bras(a, "l", lambda poses: etrog_(poses) @ Vector((0.0, 0.03, 0.05))),
                      G.paume(a, "r", lambda poses: a.dans("spine_03", poses, G.GAUCHE)),
                      G.paume(a, "l", lambda poses: a.dans("spine_03", poses, G.HAUT - G.GAUCHE)),
                      G.doigts(a, "r", 0.85, 0.5), G.doigts(a, "l", 0.55, 0.3))


def _makif(k):
    nom = f"hakafot_hamizbeach_{k + 1}"

    def batir():
        h = _un_cohen(nom)
        tenir(h, "loulav", loulav, "spine_03", repere_du_loulav(h))
        tenir(h, "etrog", etrog, "spine_03", repere_de_l_etrog(h))
        return h
    depart = Boucle(TOUR_DE_L_AUTEL, 2.5).longueur / AMA * k / MAKIFIM
    return Role(nom, "hakafot_hamizbeach", batir, loulav_et_etrog, trajet=Boucle(TOUR_DE_L_AUTEL, 2.5, depart), vitesse=1.0,
                famille="cohanim")


def roles_souccot():
    return [*_shaar_hamayim(), *_nissoukh_hamayim(), *_aravot(), *[_makif(k) for k in range(MAKIFIM)]]
