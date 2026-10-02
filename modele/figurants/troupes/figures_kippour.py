import math

import numpy as np
from mathutils import Matrix, Vector

import beit_hamikdash_gestes as G
from beit_hamikdash_visite import AMA, Z_AZ, Z_BAT, Z_EZN

from ..matieres import CHENE, LIN, OR, bois, lin, metal
from ..corps import Gabarit, _alea
from ..maillage import TOUR, Maillage, pave
from ..habillage import HAUT_Z, _objet, lier, porter
from ..ustensiles import mizrak, tabouret, tourner_profil, tube_simple
from ..mise_en_scene import (RECUL_ASSIS, assis, coude_ouvert, devant_poitrine, ecouter, hatava,
                             lire_le_sefer, mains_aux_genoux, mains_jointes, repere_mizrak, repere_vers,
                             saisir, tenir, tenir_le_sefer, vers_la_figure, zerika)
from ..bigdei_kehouna import cohen, cohen_gadol, cohen_gadol_en_or
from ..tenues import fidele
from ..role import Role
from ..betes import FRONT_DU_SEIR, amener_le_par, amener_le_seir, front_du_par, poser_seir


# « וְסוֹמֵךְ שְׁתֵּי יָדָיו עָלָיו וּמִתְוַדֶּה » (Yoma 6:2), « בֵּין שְׁתֵּי קַרְנָיו » (Rambam Ma'asse HaKorbanot 3:14) :
# les deux paumes sur le front de la bête, le buste penché et tourné vers elle, qui suit la confession.
def semikha(front):
    torsion = 0.28 * math.atan2(front.x, -front.y)

    def geste(h, a, horloge, t):
        souffle = 0.5 + 0.5 * horloge.onde(t, 5.5)
        poignets = front + Vector((0.02 * math.copysign(1.0, -front.x), 0.06, 0.06))
        return G.composer(G.pied(a, "l"), G.pied(a, "r"), G.respiration(horloge, t),
                          G.bassin(Vector((0.0, 0.06, -0.03)), tangage=0.12),
                          G.buste(flexion=0.34 + 0.06 * souffle, torsion=torsion), G.tete(flexion=0.24 + 0.08 * souffle),
                          G.bras(a, "l", poignets + G.GAUCHE * 0.04), G.bras(a, "r", poignets - G.GAUCHE * 0.04),
                          G.paume(a, "l", -G.HAUT), G.paume(a, "r", -G.HAUT),
                          G.doigts(a, "l", 0.12, 0.1), G.doigts(a, "r", 0.12, 0.1))
    return geste


# « הִשְׁתַּחֲוָיָה זֶה פִּשּׁוּט יָדַיִם וְרַגְלַיִם עַד שֶׁנִּמְצָא מֻטָּל עַל פָּנָיו אַרְצָה » (Rambam Tefila 5:13) :
# le bassin bascule d'un quart de tour et le corps entier le suit, étendu, les bras allongés devant la tête.
HAUTEUR_DU_BASSIN_COUCHE = 0.13


def prosternation(h, a, horloge, t):
    pivot = a.bassin
    couche = Matrix.Rotation(math.pi / 2.0, 3, G.GAUCHE)
    descente = Vector((0.0, 0.0, a.sol + HAUTEUR_DU_BASSIN_COUCHE - pivot.z))
    loin = Vector((0.0, 0.0, -1.0))

    def pointe(cote):
        return {f"foot_{cote}": lambda m, poses: G.viser(m, m.translation + couche @ (loin + G.LATERAL * 0.3)),
                f"ball_{cote}": lambda m, poses: G.viser(m, m.translation + couche @ loin)}

    def main_devant(s):
        return a.au("spine_03", Vector((s * 0.17, -0.10, h.z_tete + 0.32)))

    return G.composer(G.bassin(descente, tangage=math.pi / 2.0), G.respiration(horloge, t, ampleur=0.008),
                      G.buste(flexion=-0.06), G.tete(flexion=-0.10),
                      pointe("l"), pointe("r"),
                      G.bras(a, "l", main_devant(1.0)), G.bras(a, "r", main_devant(-1.0)),
                      G.paume(a, "l", lambda poses: a.dans("spine_03", poses, G.DEVANT)),
                      G.paume(a, "r", lambda poses: a.dans("spine_03", poses, G.DEVANT)),
                      G.doigts(a, "l", 0.08, 0.1), G.doigts(a, "r", 0.08, 0.1))


# Au nord-est de l'autel, où les boucs ont été tirés au sort (Yoma 3:9), tourné vers la porte de son départ (Yoma 4:2).
SEIR_OU = (-17.5, 10.6, Z_AZ)


# À sa droite, la tête devant lui : il se tient le long du bouc, tourné comme lui (CHOIX).
def front_du_seir(h):
    return Vector((-0.38, -0.50, h.sol + FRONT_DU_SEIR.z))


def _sair_hamishtaleach():
    nom = "sair_hamishtaleach"

    def batir():
        h = cohen_gadol(nom)
        amener_le_seir(h, front_du_seir(h))
        return h
    return Role(nom, nom, batir, lambda h, a, horloge, t: semikha(front_du_seir(h))(h, a, horloge, t), SEIR_OU, 0.0,
                famille="cohanim")


# Les cohanim dans l'Ezrat Cohanim, les Israélites dans l'Ezrat Israël (Middot 5:1), tous la tête vers le Heikhal.
# Couché, un homme tient 3,5 amot devant ses pieds et 2 derrière : ni sur le yessod, ni sous les lishkot qui flanquent Nikanor.
PROSTERNES_COHANIM = ((-17.5, 26.0), (-17.0, 18.5), (-17.8, -3.0), (-17.2, -14.0), (-17.6, -27.0))
PROSTERNES_ISRAEL = ((-4.5, -41.0), (-5.2, -33.5), (-4.2, -26.5), (-4.8, 24.5), (-4.0, 31.0), (-5.0, 37.5), (-4.4, 44.0))


def _gabarit_de_prosterne(nom):
    age = 0.35 + 0.55 * _alea(nom, 0)
    return Gabarit(1.66 + 0.16 * _alea(nom, 1), age=age, poids=0.4 + 0.3 * _alea(nom, 2),
                   peau="old_caucasian_male" if age > 0.8 else "middleage_caucasian_male")


def _prosterne(nom, batir, ou, famille=None):
    cap = 180.0 + 6.0 * (_alea(nom, 3) - 0.5)
    return Role(nom, "korim_oumishtahavim", batir, prosternation, (*ou, Z_AZ), cap, famille=famille)


def _cohen_prosterne(k):
    nom = f"korim_oumishtahavim_{k + 1}"
    gabarit = _gabarit_de_prosterne(nom)
    return _prosterne(nom, lambda: cohen(nom, gabarit, gris=gabarit.age > 0.7), PROSTERNES_COHANIM[k], "cohanim")


def _israel_prosterne(k):
    nom = f"korim_oumishtahavim_{len(PROSTERNES_COHANIM) + k + 1}"
    gabarit = _gabarit_de_prosterne(nom)
    tete = "talith" if k % 2 == 0 else "kippa"
    return _prosterne(nom, lambda: fidele(nom, "costume", gabarit, gris=gabarit.age > 0.7, tete=tete),
                      PROSTERNES_ISRAEL[k])


# « מָסְרוּ לוֹ זְקֵנִים מִזִּקְנֵי בֵית דִּין, וְקוֹרִין לְפָנָיו בְּסֵדֶר הַיּוֹם » (Yoma 1:3) : sur le banc de la Lishkat Parhedrin,
# l'un lit, l'autre écoute.
BANC_DES_ANCIENS = 1.0 * AMA


def _zaken(k, ou, lit):
    nom = f"zekenim_{k + 1}"
    gabarit = Gabarit(1.70 + 0.06 * _alea(nom, 1), age=0.88 + 0.08 * _alea(nom, 0), poids=0.45, peau="old_caucasian_male")

    def geste(h, a, horloge, t):
        corps = assis(a, horloge, t, BANC_DES_ANCIENS, 0.3 * k)
        if lit:
            return lire_le_sefer(h, a, corps, horloge, t)
        corps = G.composer(corps, G.buste(flexion=0.12))
        return G.composer(corps, G.tete(flexion=0.10 + 0.05 * horloge.onde(t, 5.3)), mains_aux_genoux(a, corps))

    def batir():
        h = fidele(nom, "costume", gabarit, gris=True, tete="talith")
        return tenir_le_sefer(h) if lit else h
    return Role(nom, "zekenim", batir, geste, ou, -90.0)


# Assis devant eux, il écoute ; le siège est un CHOIX. En habits d'or : il les porte « בְּיוֹם עֲבוֹדָתוֹ וַאֲפִלּוּ שֶׁלֹּא
# בִּשְׁעַת עֲבוֹדָה » (Rambam Klei HaMikdash 8:11), et ces sept jours il sert (Yoma 1:2) — l'habit de l'étude, CHOIX.
SIEGE_DU_COHEN_GADOL = 0.46


def _parhedrin(nom, ou, cap):
    def geste(h, a, horloge, t):
        corps = assis(a, horloge, t, SIEGE_DU_COHEN_GADOL)
        return G.composer(corps, G.tete(flexion=0.10 + 0.04 * horloge.onde(t, 6.1)), mains_aux_genoux(a, corps))

    def batir():
        h = cohen_gadol_en_or(nom)
        mm = Maillage()
        tabouret(mm, Vector((0.0, RECUL_ASSIS, h.sol)), SIEGE_DU_COHEN_GADOL)
        porter(h, mm, f"{nom}_kisse")
        return h
    return Role(nom, "bigdei_zahav", batir, geste, ou, cap, famille="cohanim")


# « הוּא פוֹרֵשׁ וּבוֹכֶה, וְהֵן פּוֹרְשִׁין וּבוֹכִין » (Yoma 1:5) : chacun détourné, la tête basse, la droite sur les yeux.
def pleurer(h, a, horloge, t):
    sanglot = 0.5 + 0.5 * horloge.onde(t, 3.4)
    yeux = a.au("spine_03", Vector((0.0, -0.21, h.z_epaule + 0.18)))
    return G.composer(G.debout(a, horloge, t, 0.5, regard=0.0), G.buste(flexion=0.10 + 0.04 * sanglot),
                      G.tete(flexion=0.30 + 0.06 * sanglot), G.bras(a, "r", yeux, coude_ouvert(a, "r")),
                      G.paume(a, "r", lambda poses: a.dans("spine_03", poses, -G.DEVANT + G.HAUT * 0.3)),
                      G.doigts(a, "r", 0.20, 0.1), G.doigts(a, "l", 0.35, 0.15))


# Les anciens de la kehouna qui le reçoivent au Beit Avtinas (Yoma 1:5), hors service : vêtus comme ceux du Beit Din.
def _zaken_kehuna(k, ou, cap):
    nom = f"zikenei_kehuna_{k + 1}"
    gabarit = Gabarit(1.70 + 0.06 * _alea(nom, 1), age=0.86 + 0.08 * _alea(nom, 0), poids=0.45, peau="old_caucasian_male")
    return Role(nom, "zikenei_kehuna", lambda: fidele(nom, "costume", gabarit, gris=True, tete="talith"), pleurer,
                ou, cap, famille="cohanim")


# « פֵּרְסוּ סָדִין שֶׁל בּוּץ בֵּינוֹ לְבֵין הָעָם » (Yoma 3:4, 3:6) : deux cohanim le tendent par ses coins hauts, face à face.
# Qui le tient, et à hauteur d'épaule — la tête du Cohen Gadol passe au-dessus — : CHOIX.
COIN_DU_DRAP = Vector((0.0, -0.24, 1.50))


# Du coin de celui qui le porte, droit devant lui sur `largeur`, dans son repère.
def sadin(mm, largeur, bas=0.12, colonnes=20, rangs=10):
    anneaux = []
    for i in range(rangs):
        v = i / (rangs - 1)
        rang = []
        for j in range(colonnes):
            u = j / (colonnes - 1)
            fleche = 0.08 * math.sin(math.pi * u) * (1.0 - 0.6 * v)
            pli = 0.03 * math.sin(TOUR * 3.0 * u) * v
            rang.append(Vector((pli, COIN_DU_DRAP.y - largeur * u, COIN_DU_DRAP.z - (COIN_DU_DRAP.z - bas) * v - fleche)))
        anneaux.append(rang)
    mm.nappe(anneaux, LIN, "objet", ferme=False)


def tenir_le_drap(h, a, horloge, t):
    return G.composer(G.debout(a, horloge, t, 0.4, regard=0.02),
                      G.bras(a, "l", COIN_DU_DRAP + G.GAUCHE * 0.06), G.bras(a, "r", COIN_DU_DRAP - G.GAUCHE * 0.06),
                      G.paume(a, "l", G.DEVANT), G.paume(a, "r", G.DEVANT),
                      G.doigts(a, "l", 1.1, 0.7), G.doigts(a, "r", 1.1, 0.7))


# Deux tenants face à face, de `a` à `b` en amot : le premier porte le drap.
def _tenants(k, a, b, z):
    largeur = (Vector(b) - Vector(a)).length * AMA + 2.0 * COIN_DU_DRAP.y
    cap = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    roles = []
    for j, (ou, regard) in enumerate(((a, cap), (b, cap + 180.0))):
        nom = f"sadin_shel_butz_{k + j}"
        gabarit = Gabarit(1.72 + 0.08 * _alea(nom, 1), age=0.35 + 0.3 * _alea(nom, 0))

        def batir(nom=nom, gabarit=gabarit, porte=j == 0):
            h = cohen(nom, gabarit)
            if porte:
                drap = Maillage()
                sadin(drap, largeur)
                _objet(h, drap, f"{nom}_sadin", lin())
            return h
        roles.append(Role(nom, "sadin_shel_butz", batir, tenir_le_drap, (*ou, z), regard, famille="cohanim"))
    return roles


# Derrière le drap, vêtu, il attend de sanctifier mains et pieds (Yoma 3:4, 3:6, 7:3) : seule la tête dépasse, coiffée
# de l'habit du moment.
def _derriere_le_drap(nom, habiller, concept, ou, cap):
    return Role(nom, concept, lambda: habiller(nom),
                lambda h, a, horloge, t: G.composer(G.debout(a, horloge, t, 0.6, regard=0.05), mains_jointes(h, a)),
                ou, cap, famille="cohanim")


def _viduy_rishon(nom, ou):
    def batir():
        h = cohen_gadol(nom)
        amener_le_par(h, front_du_par(h), 0.0)
        return h
    return Role(nom, "bigdei_lavan", batir, lambda h, a, horloge, t: semikha(front_du_par(h))(h, a, horloge, t), ou,
                180.0, famille="cohanim")


# « מַעֲמִידִין שְׁנֵי הַשְּׂעִירִים פְּנֵיהֶן לַמַּעֲרָב … וּשְׁנֵי הַשְּׂעִירִים לְפָנָיו אֶחָד לִימִינוֹ וְאֶחָד לִשְׂמֹאלוֹ » (Rambam Avodat
# Yom HaKippourim 3:2) ; la kalpi de bois où entrent ses deux mains, deux sorts d'or pareils (3:1). Le socle : CHOIX.
KALPI = (0.26, 0.17, 0.15)
SOCLE_DE_LA_KALPI = 0.80
DEVANT_LA_KALPI = -0.42


def kalpi(mm, sol):
    x, y, z = KALPI
    centre = Vector((0.0, DEVANT_LA_KALPI, sol))
    mm.nappe(tube_simple([centre, centre + HAUT_Z * SOCLE_DE_LA_KALPI], 0.05, 10), CHENE, "objet")
    plateau = centre + HAUT_Z * SOCLE_DE_LA_KALPI
    pave(mm, plateau, G.GAUCHE.copy(), G.LATERAL.copy(), (x + 0.06, y + 0.06), 0.02, CHENE, "objet")
    milieu = plateau + HAUT_Z * (0.02 + z / 2)
    for s in (-1.0, 1.0):
        pave(mm, milieu + G.LATERAL * (s * y / 2), G.GAUCHE * s, HAUT_Z.copy(), (x, z), 0.012, CHENE, "objet")
        pave(mm, milieu + G.GAUCHE * (s * x / 2), -G.LATERAL * s, HAUT_Z.copy(), (y, z), 0.012, CHENE, "objet")


def goral(mm, repere):
    pave(mm, repere @ Vector(), repere.to_3x3() @ G.GAUCHE, repere.to_3x3() @ G.LATERAL, (0.05, 0.035), 0.004, OR, "objet")


def repere_du_goral(a, cote):
    centre = a.poignet[cote] + a.jointure[cote] * 0.085 + a.paume[cote] * 0.022
    return repere_vers(centre, a.paume[cote], a.jointure[cote])


# « טָרַף בַּקַּלְפִּי וְהֶעֱלָה שְׁנֵי הַגּוֹרָלוֹת בִּשְׁתֵּי יָדָיו … וּפוֹתֵחַ יָדָיו … הַגְבֵּהַּ יְמִינְךָ » (Rambam Avodat Yom HaKippourim 3:3) :
# les mains dans la kalpi, levées ensemble, ouvertes, la droite plus haut — le sort du Nom y est monté, CHOIX —, redescendues.
def tirer_au_sort(h, a, horloge, t):
    u = t / horloge.duree
    leve = G.lisse((u - 0.22) / 0.12) * (1.0 - G.lisse((u - 0.86) / 0.10))
    droite_haute = G.lisse((u - 0.45) / 0.10) * (1.0 - G.lisse((u - 0.76) / 0.10))
    secoue = 0.015 * math.sin(TOUR * 6.0 * u) * (1.0 - G.lisse(u / 0.2))
    fond = Vector((0.0, DEVANT_LA_KALPI + 0.02, a.sol + SOCLE_DE_LA_KALPI + 0.10))
    poitrine = devant_poitrine(h, 0.34, 0.20)

    def main(s):
        levee = poitrine + G.GAUCHE * (s * 0.16)
        cible = (fond + G.GAUCHE * (s * 0.05 + secoue)).lerp(levee, leve)
        return cible.lerp(levee + HAUT_Z * 0.42 + G.GAUCHE * 0.04, droite_haute) if s < 0 else cible

    ouverte = G.HAUT * leve - G.HAUT * (1.0 - leve)
    return G.composer(G.debout(a, horloge, t, 0.2, regard=0.03), G.buste(flexion=0.22 * (1.0 - leve)),
                      G.tete(flexion=0.22 * (1.0 - leve) + 0.05),
                      G.bras(a, "l", main(1.0)), G.bras(a, "r", main(-1.0)),
                      G.paume(a, "l", ouverte + G.GAUCHE * 0.01), G.paume(a, "r", ouverte - G.GAUCHE * 0.01),
                      G.doigts(a, "l", 0.45 * (1.0 - leve) + 0.12, 0.2), G.doigts(a, "r", 0.45 * (1.0 - leve) + 0.12, 0.2))


# Les boucs devant lui, croupe vers lui, face à l'ouest comme lui.
def _goral(nom, ou):
    def batir():
        h = cohen_gadol(nom)
        a = G.Acteur(h.squelette, h.sol)
        for cote in "lr":
            tenir(h, f"goral_{cote}", goral, f"hand_{cote}", repere_du_goral(a, cote))
        for s, cote in ((-1.0, "yamin"), (1.0, "smol")):
            poser_seir(h, f"{nom}_seir_{cote}", Matrix.Translation((s * 0.50, -0.60, h.sol))
                       @ Matrix.Rotation(-math.pi / 2.0, 4, "Z"))
        mm = Maillage()
        kalpi(mm, h.sol)
        porter(h, mm, f"{nom}_kalpi")
        return h
    return Role(nom, "bigdei_lavan", batir, tirer_au_sort, ou, 180.0, duree=12.0, famille="cohanim")


# « הַסְּגָן מִימִינוֹ וְרֹאשׁ בֵּית אָב מִשְּׂמֹאלוֹ » (Yoma 4:1) : ils regardent ses mains.
def _aupres_du_goral(k, ou):
    nom = f"goral_{k + 1}"
    gabarit = Gabarit(1.74 + 0.05 * _alea(nom, 1), age=0.55 + 0.3 * _alea(nom, 0))
    vers_lui = 0.35 if k == 0 else -0.35
    return Role(nom, "goral", lambda: cohen(nom, gabarit, gris=gabarit.age > 0.7),
                lambda h, a, horloge, t: G.composer(ecouter(h, a, horloge, t), G.tete(flexion=0.14, lacet=vers_lui)),
                ou, 180.0, famille="cohanim")


# « עָלָה לְרֹאשׁ הַמִּזְבֵּחַ, וּפִנָּה גֶחָלִים אֵילָךְ וְאֵילָךְ, וְחוֹתֶה מִן הַמְאֻכָּלוֹת הַפְּנִימִיּוֹת » (Yoma 4:3) ; la ma'hta
# d'or au long manche (4:4), dans la droite (5:1). Cotes de la fiche §8g : bassin de 0,56 ama sur 0,16, manche de 1,1 ama.
RAYON_DU_MANCHE = 0.011
DUREE_DE_LA_PELLETEE = 8.0
BRAISE = (0.34, 0.05, 0.015)


def machta(mm, braises, repere):
    manche = [Vector((0.0, 0.0, z)) for z in np.linspace(-0.35, 0.18, 5)]
    mm.nappe([[repere @ p for p in a] for a in tube_simple(manche, RAYON_DU_MANCHE, 8)], OR, "objet")
    fond = repere @ Matrix.Translation((0.0, 0.0, 0.18 + 0.135)) @ Matrix.Rotation(math.pi / 2.0, 4, "Y")
    tourner_profil(mm, fond, ((0.0, 0.004), (0.006, 0.118), (0.077, 0.135), (0.080, 0.137)), OR, 24)
    tourner_profil(braises, fond, ((0.010, 0.0), (0.012, 0.11), (0.030, 0.12), (0.036, 0.09), (0.040, 0.0)), BRAISE, 16)


# Le bassin du côté du pouce, ouvert vers le ciel quand la main a pris sa pose `poses`.
def repere_machta(a, poses):
    _, centre, axe = G.prise(a, "r", RAYON_DU_MANCHE)
    haut = a.sq.repos["hand_r"].to_3x3() @ (poses["hand_r"].to_3x3().inverted() @ HAUT_Z)
    return repere_vers(centre, axe, haut)


def puiser(h, a, horloge, t):
    va = 0.5 - 0.5 * math.cos(TOUR * t / horloge.duree)
    corps = G.composer(G.pied(a, "l", G.DEVANT * 0.12), G.pied(a, "r", G.DEVANT * -0.08), G.respiration(horloge, t),
                       G.bassin(Vector((0.0, 0.10 + 0.04 * va, -0.10 - 0.05 * va)), tangage=0.30 + 0.10 * va),
                       G.buste(flexion=0.40 + 0.12 * va), G.tete(flexion=0.10),
                       G.bras_ballant(a, "l", avance=0.10, ecart=0.08), G.doigts(a, "l", 0.35))
    poing = Vector((-0.14, -0.40 - 0.10 * va, h.z_hanche - 0.05 - 0.10 * va))
    return saisir(a, corps, RAYON_DU_MANCHE, {"r": poing}, {"r": Vector((0.1, -1.0, -0.45 - 0.25 * va))})


def _machta(nom, ou):
    def batir():
        h = cohen_gadol(nom)
        a = G.Acteur(h.squelette, h.sol)
        poses = a.sq.resoudre(puiser(h, a, G.Horloge(DUREE_DE_LA_PELLETEE), 0.0))[0]
        pelle, braises = Maillage(), Maillage()
        machta(pelle, braises, repere_machta(a, poses))
        lier(h, pelle, f"{nom}_machta", metal(), "hand_r")
        lier(h, braises, f"{nom}_gehalim", bois(), "hand_r")
        return h
    return Role(nom, "bigdei_lavan", batir, puiser, ou, 180.0, duree=DUREE_DE_LA_PELLETEE, famille="cohanim")


# Le mizrak dans la gauche ; le doigt de la droite y trempe et fouette, « כְּמַצְלִיף » (Yoma 5:3), une fois vers le haut
# et sept vers le bas, sur la parokhet face à l'Arche (5:4).
def repere_mizrak_gauche(h):
    return repere_vers(devant_poitrine(h, 0.30, 0.36, 0.10), G.HAUT, G.GAUCHE)


def tenir_le_mizrak(h, a, coupe):
    return G.composer(G.bras(a, "l", lambda poses: coupe(poses) @ Vector((0.10, 0.0, 0.03))),
                      G.paume(a, "l", lambda poses: a.dans("spine_03", poses, G.HAUT - G.GAUCHE)), G.doigts(a, "l", 0.3))


def asperger(h, a, horloge, t):
    coupe = a.repere("spine_03", repere_mizrak_gauche(h))
    periode = horloge.duree / 8
    k, u = int(t // periode), (t % periode) / periode
    trempe = 1.0 - G.lisse(u / 0.35)
    fouet = G.lisse((u - 0.55) / 0.15) * (1.0 - G.lisse((u - 0.85) / 0.15))
    vise = a.au("spine_03", devant_poitrine(h, 0.52, -0.30 if k == 0 else 0.05))

    def droite(poses):
        dans = coupe(poses) @ Vector((0.0, 0.0, 0.06))
        return dans.lerp(vise(poses), 1.0 - trempe) + G.DEVANT * (0.06 * fouet) - HAUT_Z * (0.10 * fouet)

    return G.composer(G.debout(a, horloge, t, 0.1, regard=0.0), G.tete(flexion=-0.04 if k == 0 else 0.06),
                      tenir_le_mizrak(h, a, coupe), G.bras(a, "r", droite), G.paume(a, "r", -G.HAUT),
                      G.doigts(a, "r", 0.45, 0.4))


def _mizrak_en_main(nom, geste, ou, cap, duree):
    def batir():
        h = cohen_gadol(nom)
        tenir(h, "mizrak", mizrak, "spine_03", repere_mizrak_gauche(h))
        return h
    return Role(nom, "bigdei_lavan", batir, geste, ou, cap, duree=duree, famille="cohanim")


# « מַתְחִיל … מִקֶּרֶן מִזְרָחִית צְפוֹנִית » (Yoma 5:5) ; il fait le tour de l'autel et donne sur les cornes « מִבַּחוּץ …
# מִלְּמַטָּן לְמַעְלָן » (Rambam Avodat Yom HaKippourim 4:2) : à l'angle nord-est, le doigt monte le long de la corne.
KEREN_MIZRAHIT_TZEFONIT = (-118.55, 0.40, 8.05)
MIZBEACH_HAZAHAV_OU = (-117.6, 1.5, Z_BAT)
MIZBEACH_HAZAHAV_CAP = 215.0


def matan_keranot(h, a, horloge, t):
    coupe = a.repere("spine_03", repere_mizrak_gauche(h))
    keren = vers_la_figure(MIZBEACH_HAZAHAV_OU, MIZBEACH_HAZAHAV_CAP, KEREN_MIZRAHIT_TZEFONIT, a.sol)
    monte = 0.5 - 0.5 * math.cos(TOUR * t / horloge.duree * 2.0)
    return G.composer(G.debout(a, horloge, t, 0.5, regard=0.0), G.buste(flexion=0.12), G.tete(flexion=0.18),
                      tenir_le_mizrak(h, a, coupe), G.bras(a, "r", keren + HAUT_Z * (0.02 + 0.06 * monte)),
                      G.paume(a, "r", -G.HAUT), G.doigts(a, "r", 0.8, 0.5))


# « וְהַכֹּהֵן גָּדוֹל עוֹמֵד וּמְקַבֵּל וְקוֹרֵא » (Yoma 7:1) : debout, le rouleau ouvert ; en lin — il le peut —, CHOIX contre
# la tunique blanche à lui. Le 'hazan, le chef de la synagogue et le segan qui le lui ont passé se tiennent près.
def _keriat_hatorah(nom, ou):
    return Role(nom, "bigdei_lavan", lambda: tenir_le_sefer(cohen_gadol(nom)),
                lambda h, a, horloge, t: lire_le_sefer(h, a, G.debout(a, horloge, t, 0.7, regard=0.0), horloge, t),
                ou, 180.0, famille="cohanim")


# En habits d'or, il fait lui-même le tamid : « קְרָצוֹ … וְקִבֵּל אֶת הַדָּם וּזְרָקוֹ » (Yoma 3:4), au coin nord-est (Tamid 4:1) ;
# le soir, la ketoret et les nerot (Yoma 7:4), sur la pierre de la Menora (Tamid 3:9). Places et caps du tamid.
def _zerika_du_cohen_gadol(nom):
    def batir():
        h = cohen_gadol_en_or(nom)
        tenir(h, "mizrak", mizrak, "spine_03", repere_mizrak(h))
        return h
    return Role(nom, "bigdei_zahav", batir, zerika, (-20.5, 4.6, Z_AZ), 142.0, famille="cohanim")


def _nerot_du_cohen_gadol(nom):
    return Role(nom, "bigdei_zahav", lambda: cohen_gadol_en_or(nom), hatava, (-123.6, -7.5, Z_BAT + 0.9), 180.0,
                duree=10.0, famille="cohanim")


def _aupres_du_sefer(k, ou, cap):
    nom = f"keriat_hatorah_{k + 1}"
    gabarit = Gabarit(1.70 + 0.08 * _alea(nom, 1), age=0.50 + 0.4 * _alea(nom, 0))
    if k == 0:
        return Role(nom, "keriat_hatorah", lambda: cohen(nom, gabarit, gris=gabarit.age > 0.7), ecouter, ou, cap,
                    famille="cohanim")
    return Role(nom, "keriat_hatorah", lambda: fidele(nom, "costume", gabarit, gris=gabarit.age > 0.7, tete="talith"),
                ecouter, ou, cap)


# Le seder ha'avoda, une figure du Cohen Gadol par étape, à la place que la Mishna lui donne : la visite n'en montre
# qu'une à la fois. Nulle au Kodesh HaKodashim (fiche §8e). Les places des aides, et les caps : CHOIX.
# Sur les toits, le drap tendu du côté de l'Azara : sur le Sha'ar HaMayim au nord de lui, sur le Beit HaParva à l'est,
# lui tourné vers le mikve.
TOIT_DE_LA_PARVA = 22.0
SUR_SHAAR_HAMAYIM = 26.0
PRES_DU_MIKVE = (-78.0, -62.5, TOIT_DE_LA_PARVA)


def roles_kippour():
    return [
        _parhedrin("bigdei_zahav_1", (-31.0, -76.3, Z_EZN), 90.0),
        _zaken(0, (-34.3, -73.9, Z_EZN), True), _zaken(1, (-31.9, -73.9, Z_EZN), False),
        # Au Beit Avtinas, lui à la fenêtre sur l'Azara, eux entre le mortier et la porte est.
        Role("bigdei_zahav_4", "bigdei_zahav", lambda: cohen_gadol_en_or("bigdei_zahav_4"), pleurer,
             (-11.2, -74.8, SUR_SHAAR_HAMAYIM), 100.0, famille="cohanim"),
        _zaken_kehuna(0, (-9.3, -77.2, SUR_SHAAR_HAMAYIM), 160.0), _zaken_kehuna(1, (-9.0, -79.2, SUR_SHAAR_HAMAYIM), 120.0),
        _derriere_le_drap("bigdei_zahav_2", cohen_gadol_en_or, "bigdei_zahav", (-19.0, -76.8, SUR_SHAAR_HAMAYIM), -90.0),
        *_tenants(1, (-20.4, -75.0), (-17.7, -75.0), SUR_SHAAR_HAMAYIM),
        _zerika_du_cohen_gadol("bigdei_zahav_5"),
        _derriere_le_drap("bigdei_lavan_1", cohen_gadol, "bigdei_lavan", PRES_DU_MIKVE, 180.0),
        *_tenants(3, (-76.3, -64.6), (-76.3, -60.4), TOIT_DE_LA_PARVA),
        _viduy_rishon("bigdei_lavan_2", (-61.0, 15.2, Z_AZ)),
        _goral("bigdei_lavan_3", (-15.5, 38.0, Z_AZ)),
        _aupres_du_goral(0, (-14.0, 39.5, Z_AZ)), _aupres_du_goral(1, (-14.0, 36.5, Z_AZ)),
        _machta("bigdei_lavan_4", (-27.0, -10.5, 9.0)),
        _mizrak_en_main("bigdei_lavan_5", asperger, (-136.2, 0.0, Z_BAT), 180.0, 16.0),
        _mizrak_en_main("bigdei_lavan_6", matan_keranot, MIZBEACH_HAZAHAV_OU, MIZBEACH_HAZAHAV_CAP, 12.0),
        _sair_hamishtaleach(),
        _keriat_hatorah("bigdei_lavan_7", (37.0, 0.0, Z_EZN)),
        _aupres_du_sefer(0, (37.4, 1.9, Z_EZN), 200.0), _aupres_du_sefer(1, (38.6, -1.9, Z_EZN), 160.0),
        _aupres_du_sefer(2, (40.0, -3.3, Z_EZN), 160.0),
        _nerot_du_cohen_gadol("bigdei_zahav_6"),
        _derriere_le_drap("bigdei_zahav_3", cohen_gadol_en_or, "bigdei_zahav", PRES_DU_MIKVE, 180.0),
    ] + [_cohen_prosterne(k) for k in range(len(PROSTERNES_COHANIM))] + [
        _israel_prosterne(k) for k in range(len(PROSTERNES_ISRAEL))]
