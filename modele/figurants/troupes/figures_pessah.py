import numpy as np
from mathutils import Matrix, Vector

import beit_hamikdash_gestes as G
from beit_hamikdash_visite import AMA, Z_AZ, Z_EZN

from ..matieres import ARGENT, CHENE, OR
from ..corps import _alea
from ..maillage import Maillage, pave
from ..habillage import porter
from ..ustensiles import tourner_profil, tube_simple
from ..mise_en_scene import (Accessoire, assis, dans_la_poigne, ecouter, incliner_la_coupe, mains_aux_genoux,
                             repere_mizrak, repere_vers, tenir, tenir_la_coupe, vers_la_figure, zerika)
from ..role import LEVIIM_INSTRUMENTS, Role, _israelite, _levi, _tokea, _un_cohen
from ..betes import DEMI_EPAISSEUR_DU_SEH, VENTRE_DU_PENDU, poser_seh, seh_couche, seh_debout, seh_pendu


# Le korban Pessa'h (Pesa'him 5:5–10) : une étape, ses figurants.
# « וְלֹא הָיוּ לַבָּזִיכִין שׁוּלַיִם » (Pesa'him 5:5) : « רְחָבִים הָיוּ מִלְמַעְלָה וְתַחְתֵּיהֶם חַדִּים » (Bartenoura) ; profil et taille : CHOIX.
def bazikh(couleur):
    profil = ((0.000, 0.002), (0.030, 0.030), (0.060, 0.062), (0.085, 0.086), (0.100, 0.096), (0.106, 0.094))
    return lambda mm, repere: tourner_profil(mm, repere, profil, couleur)


# « נְתָנוֹ בְמָגִיס » (Pesa'him 5:10) : un plat creux ; forme et métal : CHOIX.
RAYON_DU_MAGIS = 0.175


def magis(mm, repere):
    tourner_profil(mm, repere, ((0.000, 0.010), (0.010, 0.090), (0.030, 0.150), (0.045, RAYON_DU_MAGIS),
                                (0.048, RAYON_DU_MAGIS - 0.003)), ARGENT)


# Le couteau de la she'hita, la lame sortant du poing côté petit doigt ; tout : CHOIX.
RAYON_DU_MANCHE_DE_SAKIN = 0.012


def sakin(mm, repere):
    manche = [Vector((0.0, 0.0, z)) for z in np.linspace(-0.05, 0.06, 4)]
    mm.nappe([[repere @ p for p in a] for a in tube_simple(manche, RAYON_DU_MANCHE_DE_SAKIN)], CHENE, "objet")
    pave(mm, repere @ Vector((0.0, 0.0, -0.17)), repere.to_3x3() @ Vector((0.0, 1.0, 0.0)),
         repere.to_3x3() @ Vector((0.0, 0.0, 1.0)), (0.028, 0.23), 0.003, ARGENT, "objet")


# « מַקְלוֹת דַּקִּים חֲלָקִים » (Pesa'him 5:9) : le long du z du repère, centrée ; longueur et section : CHOIX.
def makel(mm, repere, longueur=1.90):
    chemin = [Vector((0.0, 0.0, z)) for z in np.linspace(-longueur / 2, longueur / 2, 5)]
    mm.nappe([[repere @ p for p in a] for a in tube_simple(chemin, 0.014)], CHENE, "objet")


# « שָׁחַט יִשְׂרָאֵל וְקִבֵּל הַכֹּהֵן » (Pesa'him 5:6) : penché sur l'agneau, le bazikh tenu sous la gorge — « שֶׁמָּא יַנִּיחוּם ».
def recevoir_le_sang(coupe):
    def geste(h, a, horloge, t):
        return G.composer(G.pied(a, "l", G.GAUCHE * 0.08), G.pied(a, "r", -G.GAUCHE * 0.08), G.respiration(horloge, t),
                          G.bassin(Vector((0.0, 0.16, -0.32)), tangage=0.42), G.buste(flexion=0.62), G.tete(flexion=0.30),
                          G.bras(a, "l", coupe + G.GAUCHE * 0.09), G.bras(a, "r", coupe - G.GAUCHE * 0.09),
                          G.paume(a, "l", -G.GAUCHE), G.paume(a, "r", G.GAUCHE), G.doigts(a, "l", 0.3), G.doigts(a, "r", 0.3))
    return geste


# Penché, la gauche sur la tête de l'agneau, la droite mène le couteau à la gorge.
def shechita(gorge):
    def geste(h, a, horloge, t):
        va = horloge.onde(t, 1.4)
        return G.composer(G.pied(a, "l", G.GAUCHE * 0.10), G.pied(a, "r", -G.GAUCHE * 0.10), G.respiration(horloge, t),
                          G.bassin(Vector((0.0, 0.16, -0.30)), tangage=0.40), G.buste(flexion=0.58), G.tete(flexion=0.35),
                          G.bras(a, "l", gorge + Vector((0.16, 0.05, 0.10))),
                          G.bras(a, "r", gorge + Vector((-0.10, 0.04 * va, 0.08))),
                          G.paume(a, "l", -G.HAUT), G.paume(a, "r", -G.GAUCHE), G.doigts(a, "l", 0.35),
                          G.poigne(a, "r", RAYON_DU_MANCHE_DE_SAKIN))
    return geste


# « תּוֹלִין וּמַפְשִׁיטִין » (Pesa'him 5:9) : les mains au ventre de la bête pendue, qui tirent la peau tour à tour ;
# `main_libre`, s'il y en a une, fait autre chose.
def depouiller(ventre, main_libre=None):
    def geste(h, a, horloge, t):
        l, r = horloge.onde(t, 2.2), horloge.onde(t, 2.2, 0.5)
        regles = [G.debout(a, horloge, t, 0.2, regard=0.0), G.buste(flexion=0.14), G.tete(flexion=0.20),
                  G.bras(a, "l", ventre + Vector((0.07, 0.03 * l, -0.05 + 0.06 * l))),
                  G.paume(a, "l", G.DEVANT - G.GAUCHE), G.doigts(a, "l", 0.55)]
        if main_libre is None:
            regles += [G.bras(a, "r", ventre + Vector((-0.07, 0.03 * r, 0.02 + 0.06 * r))),
                       G.paume(a, "r", G.DEVANT + G.GAUCHE), G.doigts(a, "r", 0.55)]
        else:
            regles += main_libre(a)
        return G.composer(*regles)
    return geste


# La main sur la baguette, devant l'épaule `cote` qui la porte.
def main_sur_la_baguette(cote):
    def regles(a):
        s = 1.0 if cote == "l" else -1.0
        return [G.bras(a, cote, a.epaule[cote] + Vector((s * 0.02, -0.12, 0.10))), G.paume(a, cote, -G.HAUT),
                G.doigts(a, cote, 0.8, 0.5)]
    return regles


def porter_la_baguette(cote):
    autre = "r" if cote == "l" else "l"

    def geste(h, a, horloge, t):
        return G.composer(G.debout(a, horloge, t, 0.6, regard=0.03), G.tete(flexion=0.10), *main_sur_la_baguette(cote)(a),
                          G.bras_ballant(a, autre), G.doigts(a, autre, 0.35, 0.15))
    return geste


# « כַּת רִאשׁוֹנָה יָצְתָה וְיָשְׁבָה לָהּ בְּהַר הַבַּיִת, שְׁנִיָּה בַחֵיל » (Pesa'him 5:10) : sur la dernière marche du 'Heil.
MARCHE_DU_HEIL = 0.5 * AMA


def assis_sur_la_marche(h, a, horloge, t):
    corps = G.composer(assis(a, horloge, t, MARCHE_DU_HEIL, _alea(h.nom, 4)), G.buste(flexion=0.08))
    return G.composer(corps, G.tete(flexion=0.06 + 0.04 * horloge.onde(t, 6.7)), mains_aux_genoux(a, corps))


# Le deuxième groupe attend dans l'Ezrat Nashim, chacun près de son agneau : l'attente et la place, CHOIX.
def _kat_shniya(k, ou, cap):
    nom = f"kat_shniya_{k + 1}"

    def avec_son_seh(h):
        poser_seh(h, f"{nom}_seh", seh_debout(Vector((0.40, -0.10, h.sol)), -90.0 + 20.0 * _alea(nom, 5)))
        return h
    return _israelite(nom, ecouter, ou, cap, "kat_shniya", apres=avec_son_seh)


def _cohen_au_bazikh(nom, concept, ou, cap, metal, geste):
    def batir():
        h = _un_cohen(nom)
        tenir(h, "bazikh", bazikh(metal), "spine_03", repere_mizrak(h))
        return h
    return Role(nom, concept, batir, geste, ou, cap, famille="cohanim")


# Deux rangées face à face, du lieu de la she'hita au nord de l'autel : l'une d'argent à l'ouest, l'autre d'or. Leur place
# dans l'Azara — le pessa'h s'égorge « בְּכָל מָקוֹם בָּעֲזָרָה » (Zeva'him 5:8) — et leur nombre : CHOIX.
RANGEES = ((ARGENT, -33.0, 0.0), (OR, -29.0, 180.0))
RANG_Y = (23.0, 19.0, 15.0, 11.0)


def _rangees():
    return [_cohen_au_bazikh(f"bazikhin_{r * len(RANG_Y) + k + 1}", "bazikhin", (x, y, Z_AZ), cap, couleur, tenir_la_coupe(0.09))
            for r, (couleur, x, cap) in enumerate(RANGEES) for k, y in enumerate(RANG_Y)]


# « כֹּהֵן הַקָּרוֹב אֵצֶל הַמִּזְבֵּחַ זוֹרְקוֹ זְרִיקָה אַחַת כְּנֶגֶד הַיְסוֹד » (Pesa'him 5:6) : au bout des rangées, face au yessod nord.
ZOREK_OU = (-31.0, 8.6, Z_AZ)
GORGE_OU = (-31.0, 27.1, Z_AZ)
SHOCHET_OU, SHOCHET_CAP = (-30.4, 28.4, Z_AZ), -120.0
MEKABEL_OU, MEKABEL_CAP = (-31.7, 26.1, Z_AZ), 60.0


def _shechitat_hapessah():
    shochet = "shechitat_hapessah_1"

    def gorge_de(ou, cap, sol):
        return vers_la_figure(ou, cap, GORGE_OU, sol) + Vector((0.0, 0.0, DEMI_EPAISSEUR_DU_SEH))

    def avec_le_seh(h):
        poser_seh(h, f"{shochet}_seh", seh_couche(gorge_de(SHOCHET_OU, SHOCHET_CAP, h.sol), 20.0))
        return h

    mekabel = "shechitat_hapessah_2"

    def mekabel_batir():
        h = _un_cohen(mekabel)
        mm = Maillage()
        bazikh(OR)(mm, Matrix.Translation(gorge_de(MEKABEL_OU, MEKABEL_CAP, h.sol) + Vector((0.0, 0.08, 0.03))))
        porter(h, mm, f"{mekabel}_bazikh")
        return h

    def mekabel_geste(h, a, horloge, t):
        return recevoir_le_sang(gorge_de(MEKABEL_OU, MEKABEL_CAP, a.sol) + Vector((0.0, 0.08, 0.06)))(h, a, horloge, t)

    return [_israelite(shochet, lambda h, a, horloge, t: shechita(gorge_de(SHOCHET_OU, SHOCHET_CAP, a.sol))(h, a, horloge, t),
                       SHOCHET_OU, SHOCHET_CAP, "shechitat_hapessah", tete="kippa", apres=avec_le_seh)._replace(
                accessoires=(Accessoire("sakin", sakin, dans_la_poigne("r", RAYON_DU_MANCHE_DE_SAKIN)),)),
            Role(mekabel, "shechitat_hapessah", mekabel_batir, mekabel_geste, MEKABEL_OU, MEKABEL_CAP, famille="cohanim"),
            _cohen_au_bazikh("shechitat_hapessah_3", "shechitat_hapessah", ZOREK_OU, -90.0, OR, zerika)]


# « עַל כָּל קְרִיאָה וּקְרִיאָה תּוֹקְעִין שָׁלֹשׁ תְּקִיעוֹת » (Rambam Korban Pessa'h 1:12) ; leur place, au pied du Doukhan : CHOIX.
def _hallel():
    return [_levi(k, genre) for k, genre in enumerate(LEVIIM_INSTRUMENTS)] + [
        _tokea("hallel_bepessah_1", "hallel_bepessah", (-16.0, 3.5, Z_AZ), 180.0),
        _tokea("hallel_bepessah_2", "hallel_bepessah", (-16.0, -3.5, Z_AZ), 180.0)]


# Au crochet est d'un pilier du Beit HaMitba'hayim (Middot 3:5), un agneau qu'on dépouille ; plus à l'ouest, deux hommes
# portent la baguette, la bête pendue entre eux, et l'un dépouille (Pesa'him 5:9). Qui, et où : CHOIX.
CROCHET = (-38.8, 52.85, 3.35)
TOLE_OU = (-38.8, 51.6, Z_AZ)
BAGUETTE_Y = 47.5
BAGUETTE_A, BAGUETTE_B = (-45.6, BAGUETTE_Y, Z_AZ), (-42.4, BAGUETTE_Y, Z_AZ)
SUR_L_EPAULE = Vector((-0.18, 0.0, 0.07))


def _tolin_umafshitin():
    def crochet(sol):
        return vers_la_figure(TOLE_OU, 90.0, CROCHET, sol)

    def au_crochet(h):
        poser_seh(h, "tolin_umafshitin_1_seh", seh_pendu(crochet(h.sol), 90.0), etire=True)
        return h

    def tole(h, a, horloge, t):
        ventre = crochet(a.sol) + Vector((0.0, VENTRE_DU_PENDU + 0.02, -0.40))
        return depouiller(ventre)(h, a, horloge, t)

    # Sur l'épaule droite du premier, la gauche du second : du même côté, face à face.
    def milieu(h):
        m = vers_la_figure(BAGUETTE_A, 0.0, ((BAGUETTE_A[0] + BAGUETTE_B[0]) / 2, BAGUETTE_Y, 0.0), 0.0)
        return Vector((SUR_L_EPAULE.x, m.y, h.z_epaule + SUR_L_EPAULE.z))

    def baguette_et_seh(h):
        mm = Maillage()
        makel(mm, repere_vers(milieu(h), G.DEVANT, G.GAUCHE))
        porter(h, mm, "tolin_umafshitin_2_makel")
        poser_seh(h, "tolin_umafshitin_2_seh", seh_pendu(milieu(h) - Vector((0.0, 0.0, 0.02)), 90.0), etire=True)
        return h

    def tole_sous_la_baguette(h, a, horloge, t):
        ventre = milieu(h) + Vector((0.0, VENTRE_DU_PENDU + 0.02, -0.42))
        return depouiller(ventre, main_sur_la_baguette("r"))(h, a, horloge, t)

    return [_israelite("tolin_umafshitin_1", tole, TOLE_OU, 90.0, "tolin_umafshitin", apres=au_crochet),
            _israelite("tolin_umafshitin_2", tole_sous_la_baguette, BAGUETTE_A, 0.0, "tolin_umafshitin",
                       apres=baguette_et_seh),
            _israelite("tolin_umafshitin_3", porter_la_baguette("l"), BAGUETTE_B, 180.0, "tolin_umafshitin")]


# « וְהִקְטִירָן עַל גַּבֵּי הַמִּזְבֵּחַ » : un cohen au bord de la ma'arakha, le magis devant lui, qu'il penche vers le feu (CHOIX).
def _magis():
    nom = "magis"

    def batir():
        h = _un_cohen(nom, (0.45, 0.30))
        tenir(h, "magis", magis, "spine_03", repere_mizrak(h))
        return h
    return Role(nom, nom, batir, incliner_la_coupe(RAYON_DU_MAGIS - 0.01), (-32.0, -15.2, 9.0), 90.0, famille="cohanim")


# Le deuxième groupe sur la dernière marche du 'Heil, chacun son pessa'h près de lui, dans sa peau (Pesa'him 65b).
YOSHVIM_Y = (8.0, 11.5, 15.5, 19.0)


def _yoshev(k):
    nom = f"yoshvim_bacheil_{k + 1}"

    def avec_son_pessah(h):
        poser_seh(h, f"{nom}_seh", seh_couche(Vector((0.55, 0.10, h.sol + DEMI_EPAISSEUR_DU_SEH)), 180.0), etire=True)
        return h
    return _israelite(nom, assis_sur_la_marche, (151.8, YOSHVIM_Y[k], Z_EZN - 6.0), 8.0 * (_alea(nom, 6) - 0.5),
                      "yoshvim_bacheil", apres=avec_son_pessah)


def roles_pessah():
    return [_kat_shniya(0, (22.0, 6.5, Z_EZN), 180.0), _kat_shniya(1, (24.5, 9.0, Z_EZN), 185.0),
            _kat_shniya(2, (21.5, -7.0, Z_EZN), 175.0), _kat_shniya(3, (25.0, -5.5, Z_EZN), 180.0),
            *_rangees(), *_shechitat_hapessah(), *_hallel(), *_tolin_umafshitin(), _magis(),
            *[_yoshev(k) for k in range(len(YOSHVIM_Y))]]
