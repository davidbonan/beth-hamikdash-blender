import math

import numpy as np
from mathutils import Matrix, Vector

import beit_hamikdash_gestes as G
from beit_hamikdash_visite import AMA, Z_AZ, Z_EZI, Z_EZN

from ..matieres import ARGENT, OR, metal
from ..corps import _alea
from ..maillage import TOUR, Maillage, pave
from ..habillage import HAUT_Z, lier, materiau_de, porter
from ..ustensiles import tourner_profil, tube_simple
from ..mise_en_scene import Accessoire, devant_poitrine, ecouter, repere_vers, tenir, vers_la_figure
from ..role import LEVIIM_INSTRUMENTS, Role, _israelite, _levi, _un_cohen
from ..betes import NUQUE_DU_PAR, amener_le_par


# Les bikkourim (Bikkourim 3:2–8) : une étape, ses figurants.
# « בְּסַלֵּי נְצָרִים שֶׁל עֲרָבָה קְלוּפָה » (Bikkourim 3:8), « קֻפּוֹת מְצֻפּוֹת כֶּסֶף וְזָהָב » (Bartenoura) ; forme et taille : CHOIX.
OSIER = (0.72, 0.62, 0.42)
PROFIL_DU_SAL = ((0.000, 0.002), (0.004, 0.105), (0.030, 0.125), (0.180, 0.155), (0.195, 0.160), (0.200, 0.155))
HAUT_DU_SAL, BORD_DU_SAL = 0.195, 0.160


def sal(couleur):
    return lambda mm, repere: tourner_profil(mm, repere, PROFIL_DU_SAL, couleur)


# « שְׂעוֹרִים מִלְּמַטָּה … וּתְאֵנִים לְמַעְלָה מִן הַכְּלִי » (Rambam Bikkourim 3:7) : des figues au-dessus, quelques grenades au
# bord. Leur nombre et leur teinte : CHOIX.
FIGUE, FIGUE_VERTE, ROUGE_GRENADE = (0.28, 0.16, 0.24), (0.42, 0.46, 0.20), (0.55, 0.09, 0.07)


def fruit(mm, repere, centre, rayon, couleur):
    profil = [(rayon * math.sin(a), rayon * math.cos(a) + 0.001) for a in np.linspace(-math.pi / 2, math.pi / 2, 5)]
    tourner_profil(mm, repere @ Matrix.Translation(centre), profil, couleur, n=8)


def fruits(mm, repere):
    for k in range(4):
        a = TOUR * k / 4 + 0.4
        fruit(mm, repere, Vector((0.105 * math.cos(a), 0.105 * math.sin(a), HAUT_DU_SAL - 0.005)), 0.040, ROUGE_GRENADE)
    for k in range(13):
        r, a = 0.115 * math.sqrt((k + 0.5) / 13), k * 2.39996
        couleur = FIGUE if k % 3 else FIGUE_VERTE
        fruit(mm, repere, Vector((r * math.cos(a), r * math.sin(a), HAUT_DU_SAL + 0.022 - 0.12 * r)), 0.026, couleur)


# « הַגּוֹזָלוֹת שֶׁעַל גַּבֵּי הַסַּלִּים » (Bikkourim 3:5) : « תּוֹלִים מֵאֲחוֹרֵי הַסַּלִּים … וְלֹא עַל גַּבֵּי הַסַּלִּים מַמָּשׁ » (Bartenoura) ;
# pendu par les pattes, le long du z du repère jusqu'à la tête. Teinte et taille : CHOIX.
TOR = (0.40, 0.35, 0.30)


def gozal(mm, repere):
    tourner_profil(mm, repere, ((0.0, 0.004), (0.020, 0.016), (0.050, 0.030), (0.090, 0.029), (0.120, 0.017),
                                (0.135, 0.019), (0.155, 0.015), (0.166, 0.003)), TOR, n=10)


# Une corbeille pleine, posée à `repere` ; `oiseaux` pendus à son bord, derrière (−y du repère).
def corbeille(couleur, oiseaux=0):
    def construire(mm, repere):
        sal(couleur)(mm, repere)
        for k in range(oiseaux):
            a = -math.pi / 2 + 0.45 * (k - (oiseaux - 1) / 2)
            bord = Vector(((BORD_DU_SAL + 0.02) * math.cos(a), (BORD_DU_SAL + 0.02) * math.sin(a), HAUT_DU_SAL - 0.01))
            gozal(mm, repere @ repere_vers(bord, -HAUT_Z, Vector((math.cos(a), math.sin(a), 0.0))))
    return construire


# Le métal d'une corbeille plaquée et ses fruits font deux objets : la matière suit la couleur.
def poser_la_corbeille(h, nom, repere, couleur, oiseaux=0, os_=None):
    for partie, construire in (("sal", corbeille(couleur, oiseaux)), ("peri", fruits)):
        mm = Maillage()
        construire(mm, repere)
        if os_:
            lier(h, mm, f"{nom}_{partie}", materiau_de(mm), os_)
        else:
            porter(h, mm, f"{nom}_{partie}")


# « נוֹטֵל הַסַּל עַל כְּתֵפוֹ » (Bikkourim 3:4) : sur l'épaule droite, penchée en dehors, la droite à son bord ; la gauche pend.
def repere_du_sal_a_l_epaule(a):
    return (Matrix.Translation(a.epaule["r"] + Vector((-0.12, 0.02, 0.075))) @ Matrix.Rotation(math.radians(-10.0), 4, "Y"))


def sal_a_l_epaule(h, a, horloge, t):
    repere = a.repere("spine_03", repere_du_sal_a_l_epaule(a))
    bord = lambda poses: repere(poses) @ Vector((-(BORD_DU_SAL + 0.045), 0.0, HAUT_DU_SAL - 0.035))
    return G.composer(G.debout(a, horloge, t, _alea(h.nom, 7), regard=0.05), G.bras(a, "r", bord),
                      G.paume(a, "r", lambda poses: a.dans("spine_03", poses, G.GAUCHE)), G.doigts(a, "r", 0.75, 0.45),
                      G.bras_ballant(a, "l"), G.doigts(a, "l", 0.35, 0.15))


def _porteur(nom, concept, ou, cap, couleur=OSIER, oiseaux=0, apres=None):
    def avec_sa_corbeille(h):
        a = G.Acteur(h.squelette, h.sol)
        poser_la_corbeille(h, nom, repere_du_sal_a_l_epaule(a), couleur, oiseaux, os_="spine_03")
        return apres(h) if apres else h
    return _israelite(nom, sal_a_l_epaule, ou, cap, concept, apres=avec_sa_corbeille)


# « וְהַשּׁוֹר הוֹלֵךְ לִפְנֵיהֶם, וְקַרְנָיו מְצֻפּוֹת זָהָב, וַעֲטֶרֶת שֶׁל זַיִת בְּרֹאשׁוֹ » (Bikkourim 3:3) : les cornes dorées de leur
# base à la pointe ; la couronne posée sur le haut de la tête, autour des cornes. Tresse et feuilles : CHOIX.
OLIVIER = (0.30, 0.34, 0.20)
COURONNE_CENTRE, COURONNE_RAYONS = Vector((1.88, 0.0, 1.19)), (0.16, 0.08)
DESSUS_DE_LA_TETE = Vector((0.866, 0.0, -0.5))


def dorer_les_cornes(objet):
    me = objet.data
    me.materials.append(metal())
    couleurs = me.color_attributes["Color"]
    for poly in me.polygons:
        if all(abs(me.vertices[i].co.y) > 0.13 and me.vertices[i].co.z > 1.08 and me.vertices[i].co.x > 1.85
               for i in poly.vertices):
            poly.material_index = 1
            for boucle in poly.loop_indices:
                couleurs.data[boucle].color = (*OR, 1.0)


def couronne_d_olivier(mm, repere):
    haut = Vector((0.0, 1.0, 0.0)).cross(DESSUS_DE_LA_TETE).normalized()
    anneau = [COURONNE_CENTRE + DESSUS_DE_LA_TETE * (COURONNE_RAYONS[1] * math.cos(a)) + Vector((0.0, COURONNE_RAYONS[0] * math.sin(a), 0.0))
              for a in np.linspace(0.0, TOUR, 25)]
    mm.nappe([[repere @ p for p in cercle] for cercle in tube_simple(anneau, 0.010, 6)], OLIVIER, "objet")
    for p, q in zip(anneau, anneau[1:]):
        tangente = (q - p).normalized()
        for s in (-1.0, 1.0):
            feuille = (tangente + haut.cross(tangente) * (0.8 * s)).normalized()
            pave(mm, repere @ (p + feuille * 0.028), repere.to_3x3() @ feuille, repere.to_3x3() @ haut.cross(feuille),
                 (0.055, 0.014), 0.002, OLIVIER, "objet")


def _shor_des_bikkourim(h):
    shor = amener_le_par(h, Vector((0.30, -2.90, h.sol + NUQUE_DU_PAR.z)), -90.0)
    dorer_les_cornes(shor)
    mm = Maillage()
    couronne_d_olivier(mm, shor.matrix_basis)
    porter(h, mm, f"{h.nom}_atara")
    return h


# Sur le Har HaBayit, devant le 'Heil : le bœuf devant eux, chacun son panier à l'épaule. Leur nombre et leur place : CHOIX.
def _maalei_bikkourim():
    places = ((166.0, -6.0, 180.0), (168.5, -3.0, 175.0), (170.5, -8.5, 185.0), (173.0, -4.5, 178.0),
              (172.0, -11.5, 182.0))
    return [_porteur(f"maalei_bikkourim_{k + 1}", "maalei_bikkourim", (x, y, Z_EZN - 6.0), cap,
                     ARGENT if k == 3 else OSIER, oiseaux=2 if k in (1, 4) else 0,
                     apres=_shor_des_bikkourim if k == 0 else None)
            for k, (x, y, cap) in enumerate(places)]


# « הִגִּיעַ לָעֲזָרָה וְדִבְּרוּ הַלְוִיִּם בַּשִּׁיר » (Bikkourim 3:4) : les Léviim sur le Doukhan, avec les instruments du tamid, CHOIX ;
# deux porteurs entrent dans l'Ezrat Israël.
def _shir_habikkourim():
    return [_levi(k, genre) for k, genre in enumerate(LEVIIM_INSTRUMENTS)] + [
        _porteur("shir_habikkourim_1", "shir_habikkourim", (-10.0, -3.0, Z_EZI), 178.0),
        _porteur("shir_habikkourim_2", "shir_habikkourim", (-8.0, -0.5, Z_EZI), 183.0, OR)]


# À la corne sud-ouest de l'autel, là où la corbeille sera posée (Rambam Bikkourim 3:12) : le cohen face au porteur.
# Le lieu de la lecture, et ses gestes : CHOIX.
PORTEUR_OU, COHEN_OU = (-58.0, -29.3, Z_AZ), (-58.0, -27.8, Z_AZ)
SAL_DE_LA_TENOUFA = Vector((-58.0, -28.55, Z_AZ + 1.0 / AMA))


def _mikra_bikkourim():
    return [_porteur("mikra_bikkourim_1", "mikra_bikkourim", PORTEUR_OU, 90.0),
            Role("mikra_bikkourim_2", "mikra_bikkourim", lambda: _un_cohen("mikra_bikkourim_2"), ecouter, COHEN_OU, -90.0,
                 famille="cohanim"),
            _porteur("mikra_bikkourim_3", "mikra_bikkourim", (-58.5, -32.5, Z_AZ), 92.0, oiseaux=2),
            _porteur("mikra_bikkourim_4", "mikra_bikkourim", (-57.0, -34.2, Z_AZ), 98.0, ARGENT)]


# « וְכֹהֵן מַנִּיחַ יָדוֹ תַחְתָּיו וּמְנִיפוֹ » (Bikkourim 3:6) : « מוֹלִיךְ וּמֵבִיא, מַעֲלֶה וּמוֹרִיד » (Mena'hot 5:6) — vers le cohen et
# retour, puis de haut en bas ; à l'ouest de l'autel, « וְכָל שֶׁכֵּן בְּמַעֲרָבוֹ » (Bartenoura). L'ampleur : CHOIX.
def sal_agite(horloge, t):
    u = t / horloge.duree
    va_et_vient = 0.07 * horloge.onde(t, 2.0) * (1.0 - G.lisse((u - 0.40) / 0.10))
    haut_et_bas = 0.05 * horloge.onde(t, 2.0) * G.lisse((u - 0.45) / 0.10) * (1.0 - G.lisse((u - 0.90) / 0.08))
    return SAL_DE_LA_TENOUFA + Vector((0.0, va_et_vient, haut_et_bas)) / AMA


def _sal_de(ou, cap):
    return lambda horloge, t, sol: vers_la_figure(ou, cap, sal_agite(horloge, t), sol)


def tenir_par_les_bords(sal_ici):
    def geste(h, a, horloge, t):
        centre = sal_ici(horloge, t, a.sol)
        return G.composer(G.debout(a, horloge, t, 0.3, regard=0.02), G.tete(flexion=0.10),
                          G.bras(a, "l", centre + Vector((BORD_DU_SAL + 0.045, 0.0, HAUT_DU_SAL - 0.04))),
                          G.bras(a, "r", centre + Vector((-(BORD_DU_SAL + 0.045), 0.0, HAUT_DU_SAL - 0.04))),
                          G.paume(a, "l", -G.GAUCHE), G.paume(a, "r", G.GAUCHE), G.doigts(a, "l", 0.7, 0.4),
                          G.doigts(a, "r", 0.7, 0.4))
    return geste


def main_dessous(sal_ici):
    def geste(h, a, horloge, t):
        dessous = sal_ici(horloge, t, a.sol) + Vector((-0.02, 0.07, -0.035))
        return G.composer(G.debout(a, horloge, t, 0.6, regard=0.02), G.buste(flexion=0.06), G.tete(flexion=0.14),
                          G.bras(a, "r", dessous), G.paume(a, "r", G.HAUT), G.doigts(a, "r", 0.15, 0.1),
                          G.bras_ballant(a, "l"), G.doigts(a, "l", 0.35, 0.15))
    return geste


def _tenoufat_bikkourim():
    porteur, cohen_ = _sal_de(PORTEUR_OU, 90.0), _sal_de(COHEN_OU, -90.0)

    def corbeille_agitee(h, a, horloge, t, poses):
        return Matrix.Translation(porteur(horloge, t, a.sol))

    return [_israelite("tenoufat_bikkourim_1", tenir_par_les_bords(porteur), PORTEUR_OU, 90.0, "tenoufat_bikkourim")._replace(
                accessoires=(Accessoire("sal", corbeille(OSIER, 2), corbeille_agitee), Accessoire("peri", fruits, corbeille_agitee))),
            Role("tenoufat_bikkourim_2", "tenoufat_bikkourim", lambda: _un_cohen("tenoufat_bikkourim_2"), main_dessous(cohen_),
                 COHEN_OU, -90.0, famille="cohanim")]


# « וּמַנִּיחוֹ בְּצַד הַמִּזְבֵּחַ, בְּקֶרֶן דְּרוֹמִית מַעֲרָבִית, בִּדְרוֹמָהּ שֶׁל קֶרֶן » (Rambam Bikkourim 3:12) : les corbeilles posées à
# terre au sud de la corne, à l'ouest du petit kevesh du yessod ; un cohen en emporte une (3:8). Leur nombre : CHOIX.
CORBEILLES = ((-55.0, -26.5, OSIER, 2), (-54.6, -27.3, OSIER, 0), (-55.3, -27.9, ARGENT, 0), (-54.5, -28.4, OSIER, 2),
              (-55.4, -29.0, OR, 0), (-54.6, -29.6, OSIER, 1))
GOZALOT_OU = (-56.3, -26.2, Z_AZ)


def _salei_bikkourim():
    nom = "salei_bikkourim_1"

    def batir():
        h = _un_cohen(nom)
        for k, (x, y, couleur, oiseaux) in enumerate(CORBEILLES):
            place = vers_la_figure(GOZALOT_OU, -20.0, (x, y, Z_AZ), h.sol)
            poser_la_corbeille(h, f"{nom}_{k + 1}", Matrix.Translation(place) @ Matrix.Rotation(1.3 * k, 4, "Z"), couleur,
                               oiseaux)
        tenir(h, "sal", corbeille(OSIER), "spine_03", repere_du_sal_tenu(h))
        tenir(h, "peri", fruits, "spine_03", repere_du_sal_tenu(h))
        return h

    def geste(h, a, horloge, t):
        centre = a.repere("spine_03", repere_du_sal_tenu(h))
        cote = lambda s: lambda poses: centre(poses) @ Vector((s * (BORD_DU_SAL + 0.04), 0.0, HAUT_DU_SAL * 0.45))
        return G.composer(G.debout(a, horloge, t, 0.2, regard=0.06), G.tete(flexion=0.12),
                          G.bras(a, "l", cote(1.0)), G.bras(a, "r", cote(-1.0)),
                          G.paume(a, "l", lambda poses: a.dans("spine_03", poses, -G.GAUCHE)),
                          G.paume(a, "r", lambda poses: a.dans("spine_03", poses, G.GAUCHE)),
                          G.doigts(a, "l", 0.45), G.doigts(a, "r", 0.45))
    return [Role(nom, "salei_bikkourim", batir, geste, GOZALOT_OU, -20.0, famille="cohanim")]


def repere_du_sal_tenu(h):
    return Matrix.Translation(devant_poitrine(h, 0.30, 0.48))


def roles_bikkourim():
    return [*_maalei_bikkourim(), *_shir_habikkourim(), *_mikra_bikkourim(), *_tenoufat_bikkourim(), *_salei_bikkourim()]
