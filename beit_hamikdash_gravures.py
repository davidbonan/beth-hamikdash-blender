"""Grave les figures des parois du Bayit : une carte de relief et leurs silhouettes.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_gravures.py                       # l'atlas
    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_gravures.py -- --guides           # les guides
    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_gravures.py -- --tailler timora   # une tuile

« כְּרוּבִים וְתִמֹרֹת וּפְטוּרֵי צִצִּים » (Melakhim I 6:29), « וְצִפָּה זָהָב מְיֻשָּׁר עַל־הַמְּחֻקֶּה »
(6:35) : la figure est CREUSÉE, et l'or épouse le creusé. Un bas-relief se lit à son
modelé — les volumes qui bombent, les plans qui s'étagent, les sillons qui séparent une
penne de la suivante — et non à sa découpe : une plaque plate au contour parfait reste
un emporte-pièce. Le blockout ne taille donc qu'UN fond par figure, à sa
silhouette ; tout le modelé est ici, dans une carte que ce fond lit par ses UV.

Le modelé lui-même n'est plus dessiné ici. Des contours lissés et des dômes, si juste
soit le motif, sortent en clip-art : chaque partie bombe de la même parabole, chaque
bord est parfait, rien n'est taillé. Ce script DESSINE donc des guides — la composition,
l'iconographie, le cadrage, en dômes et sillons — et les fait tailler par gpt-image-2
(fal.ai, ~0,08 $ la tuile) dans la manière de l'ornement judéen du Second Temple —
ossuaires, portes de 'Houlda, frises hérodiennes — ; les tuiles taillées, dans
`gravures/`, sont la SOURCE : versionnées, parce qu'un modèle ne rend jamais deux fois
la même image. `--guides` redessine les guides dans `gravures/guides/`, `--tailler`
en fait tailler un — avec l'esquisse validée du motif, s'il en a une —, et sans argument
l'atlas se compose des tuiles.

Une tuile taillée est un rendu ombré, pas une hauteur : la luminance en donne les
creux et les arêtes (les sillons sont sombres, les crêtes claires), et c'est la
distance au bord qui donne le volume d'ensemble — le bombé de la silhouette.

Deux motifs ne passent par aucun modèle et restent tels que ce script les dessine : le
cordon et la tresse. Leur manière est géométrique — un compas la dit exactement —, et
surtout une tuile qui se RÉPÈTE le long d'une paroi doit s'aboucher au pixel avec sa
voisine, ce qu'aucun modèle ne garantit deux fois de suite.

Écrit `visite/matieres/gravures_3072.webp` — un atlas de trois tuiles de 1024 sur trois :
gris = hauteur du modelé, alpha = masque — et `visite/matieres/gravures.json` : pour chaque
motif, le cadre réel que sa tuile couvre, sa place dans l'atlas, et sa silhouette,
tracée sur le masque même de la carte, pour que la plaque et le modelé coïncident au
pixel. Tout se donne dans le repère de la figure : hauteur 1, axe en u = 0, pied en z = 0.

Le blockout lit le JSON (`_relief_grave`), `visite/matieres.js` lit l'atlas (GRAVURE).
Demande `cwebp` sur le PATH, et FAL_AI_KEY (`.env`) pour tailler. À relancer après
toute modification d'une tuile, puis reconstruire la scène.
"""
import json
import math
import pathlib
import sys
import typing

import bpy
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from beit_hamikdash_carte import (RACINE, SORTIE, Planche, bombe, cadrer, distance, ecrire,  # noqa: E402
                                  figure, flouter, lire, silhouette)
from beit_hamikdash_contours import (AILES_DRESSEES, AILES_HAUTES, CROISURE, DATTE, EPIS,  # noqa: E402
                                     GAINE_KERUV, JAMBE, LARGEUR_JAMBE, MAINS, PALMES,
                                     REDUCTION_DRESSE, REDUCTION_HAUTE, SABOT, TRONC, aile,
                                     bezier, bouton, chevrons, corolle, ellipse, epi, folioles,
                                     guilloche, largeurs_palme, lisser, meches_de_criniere,
                                     palme, plumage, poser_lame, reduire, ruban, symetrique,
                                     tete_keruv, torsade)

TUILE_PX = 1024
# Trois tuiles de côté : les quatre figures du champ ne suffisaient plus à le tenir, et
# le cordon, la tresse et le bouton entrent sans rien coûter aux keruvim — chaque tuile
# garde ses 1024 pixels. `visite/matieres.js` en tient les deux constantes (TAILLE_TUILE,
# TEXEL_GRAVURE) et `visite/nappes.js` le nom du fichier.
GRILLE = 3
ATLAS_PX = GRILLE * TUILE_PX
NOM = f"gravures_{ATLAS_PX}"
TUILES = RACINE / "gravures"
GUIDES = TUILES / "guides"
# L'esquisse validée d'un motif, quand il en a une : montrée au modèle avec le guide, elle
# donne la manière — le dessin des plumes, les proportions — que le guide ne porte pas.
# Celle des keruvim est le keruv TISSÉ de la parokhet : c'est son dessin, et non une frise
# d'ailes tendues, qui donne la manière retenue. (Le tissage, lui, a pour esquisse le keruv
# taillé du vantail : les deux figures se tiennent l'une l'autre, chacune par un fichier.)
ESQUISSES = {"keruv": RACINE / "tissages" / "keruv.png",
             "keruv_dresse": RACINE / "tissages" / "keruv.png"}
ESQUISSE = "The second image is the approved design of this figure, woven in wool: carve " \
           "THAT drawing in stone — the same crossed feather sheath, the same slender " \
           "proportions, the same restraint. Ignore its colours, its green background and " \
           "its woven texture; ignore its hands, and ignore the way its head is drawn. The " \
           "first image gives the composition and framing to keep."
# Le relief d'une tuile taillée : la silhouette bombe sur RONDEUR (en part de la hauteur)
# depuis son bord, et la luminance, floutée de GRAIN pour ôter le grain du modèle, y
# ajoute le modelé pour PART_MODELE du tout. Un fond plus noir que SEUIL_FOND est le mur.
# GRAIN est au pixel près : un sillon de la taille en fait trois, et floutés de quatre les
# deux profils du keruv et les pennes de ses ailes sortaient en plis sans dessin.
RONDEUR, GRAIN, PART_MODELE, SEUIL_FOND = 0.05, 0.0015, 0.5, 0.02
# Le cadre d'une figure debout : un peu plus large qu'elle, du dessous du pied au
# dessus de la tête, pour que le fondu du bord n'atteigne jamais la tuile voisine.
CADRE_DEBOUT = (-0.6, -0.1, 0.6, 1.1)
FONDU = 0.005            # en part de la hauteur : 2 cm sur un keruv de paroi
# Simplification de la silhouette, en part de la hauteur : 1,5 cm sur un keruv de paroi,
# 2 cm sur la timora d'un jambage. Le fleuron fait 22 cm et court par centaines : le
# chanfrein et l'export dédoublent chaque sommet, et c'est là que le glb se gagne.
# Les palmes de la timora sont découpées en folioles, et sa silhouette a quintuplé : 0,010
# en ôte un tiers sans en perdre une. Au-delà, les dents s'effacent palme par palme — à
# 0,014 la moitié des palmes est ressortie en lame lisse.
# Un motif DESSINÉ (`corde`, `tresse`) a pour silhouette le carré de son cadre : c'est
# le fond de la taille, et deux tuiles voisines doivent s'aboucher au pixel.
TOLERANCE = {"keruv": 0.005, "keruv_dresse": 0.005, "timora": 0.010, "fleuron": 0.02,
             "bouton": 0.02, "dekel": 0.010, "corde": 0.05, "tresse": 0.05,
             "panneau": 0.05}


# --- Le keruv : la 'haya de Ye'hezkel, quatre ailes, une jambe, une tête à deux faces. ---

# La gaine des ailes croisées, la jambe, la tête et les pennes sont dans
# beit_hamikdash_contours.py : le guide du keruv tissé du rideau est bâti sur le même corps.

# Les niveaux, en unités libres : ce qui est devant est plus haut. L'atlas les ramène
# tous ensemble à [0, 1], et la visite les lit à la même échelle sur tous les motifs.
NIVEAU_AILE, NIVEAU_JAMBE, NIVEAU_GAINE, NIVEAU_TETE = 0.0, 0.30, 0.35, 0.65
NIVEAU_MAIN = 0.58        # les mains PAR-DESSUS la gaine : elles en sortent


def ailes_hautes(planche, attache, angle, taille, k=1.0):
    """Les deux ailes levées, taillées penne par penne : la lame de l'aile, puis ses rangs
    de plumes posés dessus en tuiles, des rémiges aux petites couvertures."""
    (u, z) = attache
    for sens in (-1, 1):
        def poser_aile(contour):
            return reduire(poser_lame(contour, sens * u, z, angle, taille, sens), k)
        planche.bomber(poser_aile(aile(8)), NIVEAU_AILE, 1.0, 0.05 * k)
        for contour, rang in plumage():
            planche.bomber(poser_aile(contour), NIVEAU_AILE + 0.04 + 0.05 * rang, 0.55, 0.018 * k)


def corps_de_keruv(planche, k=1.0):
    planche.bomber(reduire(ellipse(*SABOT), k), NIVEAU_JAMBE + 0.1, 0.8, 0.02 * k)
    planche.bomber(reduire(ruban(JAMBE, LARGEUR_JAMBE), k), NIVEAU_JAMBE, 0.8, 0.02 * k)
    planche.bomber(reduire(lisser(GAINE_KERUV), k), NIVEAU_GAINE, 1.0, 0.08 * k)
    planche.graver(reduire(CROISURE, k), 0.014 * k, 0.5)
    # Les rangs de plumes de la gaine, en chevrons qui descendent vers la jambe.
    for z in (0.74, 0.64, 0.54, 0.44, 0.34, 0.26):
        planche.graver(reduire([(-0.12, z + 0.03), (0.0, z - 0.02), (0.12, z + 0.03)], k), 0.008 * k, 0.3)
    # « וִידֵי אָדָם מִתַּחַת כַּנְפֵיהֶם » (Ye'hezkel 1:8) : les mains rendues à la paroi. Le
    # keruv TISSÉ de la parokhet, dont celui-ci est repris, ne les avait jamais perdues ;
    # et à 4,2 amot dans un registre plein, c'est la seule forme qui rompe la gaine de
    # plumes — sans elles la figure entière se lit en un seul massif de pennes.
    for main in MAINS:
        planche.bomber(reduire(ellipse(*main), k), NIVEAU_MAIN, 0.9, 0.012 * k)
    planche.bomber(reduire(tete_keruv(), k), NIVEAU_TETE, 1.2, 0.022 * k)
    for meche in meches_de_criniere():
        planche.graver(reduire(meche, k), 0.010 * k, 0.35)


def keruv(planche):
    ailes_hautes(planche, *AILES_HAUTES, REDUCTION_HAUTE)
    corps_de_keruv(planche, REDUCTION_HAUTE)


def keruv_dresse(planche):
    ailes_hautes(planche, *AILES_DRESSEES, REDUCTION_DRESSE)
    corps_de_keruv(planche, REDUCTION_DRESSE)


# --- La timora : une palmette, sept palmes en éventail sur une base en cloche. ----------

# « כּוֹתֶרֶת, דּוֹמֶה לְדֶקֶל » (Rashi sur Ye'hezkel 40:16) et « דמות ענפי אילן וחריותיו »
# (Ralbag sur Melakhim I 6:29) : l'ornement peut n'être que les palmes, sans fût ni
# régimes. Le dattier entier, à 2,9 amot entre deux keruvim, se lisait en dessin d'arbre.
# Chaque palme part droite de la naissance puis s'ouvre en fontaine : (point de contrôle,
# pointe) de la demi-palmette droite, la palme du milieu d'abord. Des palmes en rayons
# droits se lisaient en feuille de chanvre. La dernière paire retombe vers le pied, sous
# les 0,36 de demi-largeur que le dattier tenait.
NAISSANCE = (0.0, 0.18)
BASE = symetrique([(0.0, NAISSANCE[1] + 0.02), (0.05, NAISSANCE[1] + 0.02), (0.035, 0.09),
                   (0.07, 0.0), (0.0, 0.0)])
PALMETTE = (((0.0, 0.60), (0.0, 0.97)), ((0.10, 0.98), (0.26, 0.78)),
            ((0.20, 0.82), (0.36, 0.48)), ((0.26, 0.56), (0.36, 0.20)))
NIVEAU_BASE, NIVEAU_PALME, NIVEAU_COLLIER = 0.4, 0.25, 0.52
# Le collier de bractées d'où les palmes partent : « כּוֹתֶרֶת, דּוֹמֶה לְדֶקֶל » (Rashi sur
# Ye'hezkel 40:16) est un CHAPITEAU, et un chapiteau a un départ. Sans lui les sept
# palmes sortaient toutes d'un même point sur une clochette nue, et l'éventail se lisait
# posé sur son pied au lieu d'en naître. Demi-collier, du milieu vers la droite :
# (pointe, demi-largeur) de chaque bractée, en part de la taille de la figure.
BRACTEES = ((0.000, 0.335, 0.042), (0.055, 0.305, 0.038), (0.100, 0.265, 0.033))


def _collier():
    """Les bractées courtes et engainantes du départ des palmes, la médiane d'abord."""
    for u, z, demi in BRACTEES:
        for sens in ((1,) if u == 0 else (-1, 1)):
            pointe = (sens * u, z)
            yield lisser([(sens * u * 0.35, NAISSANCE[1] - 0.015),
                          (sens * (u - demi) * 1.1 - sens * 0.012, NAISSANCE[1] + 0.05),
                          (sens * (u - demi * 0.45), z - 0.045), pointe,
                          (sens * (u + demi * 0.45), z - 0.045),
                          (sens * (u + demi) * 1.1 + sens * 0.012, NAISSANCE[1] + 0.05)],
                         passes=2)


def timora(planche):
    for (u1, z1), (u2, z2) in PALMETTE[::-1]:
        for sens in ((1,) if u2 == 0 else (-1, 1)):
            axe = bezier(NAISSANCE, (sens * u1, z1), (sens * u2, z2), 32)
            planche.bomber(folioles(axe, largeurs_palme(len(axe))), NIVEAU_PALME, 1.0, 0.035)
            # La nervure seule : les folioles ne sont plus des arêtes de poisson gravées
            # dans un bord lisse, c'est le contour lui-même qui les découpe.
            planche.graver(axe[3:-9], 0.005, 0.3)
    planche.bomber(BASE, NIVEAU_BASE, 1.0, 0.03)
    for bractee in _collier():
        planche.bomber(bractee, NIVEAU_COLLIER, 0.7, 0.022)


# --- Le dattier des PAROIS : « צוּרַת דִּקְלִין » (Targum Yonatan sur Melakhim I 6:29). -------

# Sur les parois, le Targum ne dit pas « chapiteau » mais des PALMIERS, et Rashi le cite
# lui-même — « כִּי בְּמַשְׁכְּנָא דִשְׁלֹמֹה הֵן מְתֻרְגָּמוֹת צוּרַת דִּיקְלִין ». Le כּוֹתֶרֶת de Rashi
# (« דּוֹמֶה לְדֶקֶל ») est dit sur Ye'hezkel 40:16, qui parle des JAMBAGES de portes : `timora`
# le garde pour eux. La palmette sur les parois laissait 40 % de la hauteur du registre en
# or nu au-dessus de chaque figure — c'est ce vide, autant que la composition, qui faisait
# le champ fade.
# C'est le dattier que la parokhet TISSE déjà (beit_hamikdash_parokhet.py), comme le keruv
# des parois est celui du rideau : fût droit à cicatrices, sept palmes, deux régimes — les
# monnaies de Bar Kokhba, et non la palmette assyrienne.
NIVEAU_FUT, NIVEAU_REGIME = 0.34, 0.30


def dekel(planche):
    planche.bomber(TRONC, NIVEAU_FUT, 0.52, 0.035)
    for chevron in chevrons():
        planche.graver(chevron, 0.011, 0.34)
    for inclinaison, longueur, retombee in PALMES[::-1]:
        for sens in ((1,) if inclinaison == 0 else (-1, 1)):
            axe, largeurs = palme(sens * inclinaison, longueur, retombee)
            planche.bomber(folioles(axe, largeurs), NIVEAU_PALME, 1.0, 0.035)
            planche.graver(axe[3:-9], 0.005, 0.3)
    # Les régimes PAR-DESSUS les palmes : ils pendent de la couronne, devant le fût.
    for sens in (-1, 1):
        for ecart, longueur in EPIS:
            fil, dattes = epi(ecart, longueur)
            planche.bomber(ruban([(sens * u, z) for u, z in fil], 0.011), NIVEAU_REGIME, 0.45, 0.006)
            for u, z in dattes:
                planche.bomber(ellipse(sens * u, z, *DATTE), NIVEAU_REGIME, 0.75, 0.011)


# --- Le fleuron : la rosette à six pétales, celle des ossuaires de Jérusalem. -----------

# « פְּטוּרֵי צִצִּים » (Melakhim I 6:29), des fleurs qui s'ouvrent. La fleur de l'ornement
# judéen du Second Temple est la rosette tracée au compas — six pétales, sur les
# ossuaires et les linteaux des tombes de Jérusalem. Six, donc, et non huit.
LOBES = 6


def fleuron(planche):
    # Lissée : `corolle` échantillonne huit points par lobe, et six lobes sortaient en
    # polygone — le modèle a taillé les facettes telles quelles.
    planche.bomber(lisser(corolle(0.0, 0.5, 0.5, LOBES), passes=1), 0.0, 1.0, 0.12)
    for k in range(LOBES):
        a = math.pi * (2 * k + 1) / LOBES
        planche.graver([(0.10 * math.cos(a), 0.5 + 0.10 * math.sin(a)),
                        (0.40 * math.cos(a), 0.5 + 0.40 * math.sin(a))], 0.022, 0.5)
        # La nervure du pétale : sans elle chaque lobe sortait en galet lisse, et la
        # rosette, qui revient par centaines dans les bandeaux, était le motif le moins
        # taillé du champ pour être le plus répété.
        milieu = math.pi * 2 * k / LOBES
        planche.graver([(0.16 * math.cos(milieu), 0.5 + 0.16 * math.sin(milieu)),
                        (0.44 * math.cos(milieu), 0.5 + 0.44 * math.sin(milieu))], 0.008, 0.28)
    planche.graver(ellipse(0.0, 0.5, 0.175, 0.175), 0.016, 0.34)
    planche.bomber(ellipse(0.0, 0.5, 0.13, 0.13), 0.6, 1.0, 0.10)


# --- Le bouton : « פְּקָעִים » (Melakhim I 6:18), ce que la fleur est avant de s'ouvrir. ---

# Rashi « כְּמִין כַּפְתּוֹרִים », Targum « חֵיזוּ בֵיעִין », Ralbag « בִּיצִים שֶׁשְּׁנֵי רָאשֵׁיהֶם
# חַדִּים », qui le rattache aux גְּבִיעִים כַּפְתֹּרִים וּפְרָחִים de la Menora. Le bandeau porte
# donc le CYCLE — bouton, fleur ouverte — et non une seule corolle répétée.
RAYON_BOUTON = 0.345
NERVURES_BOUTON = 3


def bouton_ferme(planche):
    oeuf, calice = bouton(0.0, 0.05, RAYON_BOUTON)
    planche.bomber(calice, 0.0, 0.7, 0.05)
    planche.bomber(oeuf, 0.35, 1.0, 0.085)
    for k in range(NERVURES_BOUTON):
        u = (k - (NERVURES_BOUTON - 1) / 2) * RAYON_BOUTON * 0.52
        planche.graver([(u * 0.35, 0.05 + RAYON_BOUTON * 0.30),
                        (u, 0.05 + RAYON_BOUTON * 1.30),
                        (u * 0.30, 0.05 + RAYON_BOUTON * 2.40)], 0.012, 0.30)


# --- Le cordon et la tresse : « קְלִיעַן » (Targum 6:29), « וַחֲבָלִים » (Rashi 6:29). -------

# Ces deux-là ne passent par aucun modèle : une torsade est une figure géométrique, que
# des dômes disent exactement. La taille par gpt-image-2 existe pour le vivant — une
# penne, une foliole, un profil —, pas pour ce qu'un compas trace. Et surtout : une tuile
# qui se RÉPÈTE le long d'une paroi doit s'aboucher au pixel avec sa voisine, ce qu'aucun
# modèle ne garantit deux fois de suite.
# Leur cadre est le carré unité : la silhouette est le fond de la taille, et le motif
# bombe dedans. Deux tuiles posées bout à bout ne font qu'une bande.
# Le bombé monte sur `rondeur` depuis le bord puis s'aplatit (`bombe`) : au-dessous de la
# demi-largeur du brin, la mèche sort en limace plate à sommet blanc. La rondeur d'un
# cordon vaut donc sa demi-largeur, pour que le dôme culmine sur la nervure et nulle part
# ailleurs.
CARRE = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
# Deux torsions par tuile, et non six : la tuile est CARRÉE, donc une bande de 0,33 ama
# de haut la reparcourt tous les 0,33 amot — à six mèches, chaque torsion tombait à
# 2,6 cm et le cordon rendait un filet lisse à dix mètres. Le pas d'une torsion vaut à
# peu près le diamètre de la corde, et c'est ce qui la fait lire comme une corde.
TORSADES, BRINS = 2, 2
LARGEUR_BRIN = 0.17
CROISEMENTS = 1
DEBORD_ARCHE = 7
EPAISSEUR_CORDE = 0.72     # le cordon laisse voir le fond de la taille au-dessus et au-dessous :
                           # à 0,88 les mèches touchent les deux bords, la gorge se réduit
                           # à un filet et la corde sort en rang de tuiles penchées
RONDEUR_CORDE = 1.55 / (2 * TORSADES) / 2


def corde(planche):
    """Le cordon tordu : des mèches obliques qui se recouvrent l'une l'autre, toutes du
    même sens. `bomber` recouvre au lieu d'ajouter, et c'est ce recouvrement, pris dans
    l'ordre, qui donne son pas à la torsion."""
    planche.bomber(CARRE, 0.0, 0.0, 0.01)
    for meche in torsade(TORSADES, epaisseur=EPAISSEUR_CORDE):
        planche.bomber(meche, 0.0, 1.0, RONDEUR_CORDE)


def tresse(planche):
    """Deux brins qui s'entrelacent : chaque brin passe DESSUS sur une arche sur deux.
    Posés l'un après l'autre, le second serait au-dessus partout et la tresse se lirait
    en deux fils superposés ; ce sont les arches hautes, reposées ensuite, qui croisent."""
    planche.bomber(CARRE, 0.0, 0.0, 0.01)
    axes = guilloche(BRINS, croise=CROISEMENTS)
    for axe in axes:
        planche.bomber(ruban(axe, LARGEUR_BRIN), 0.0, 1.0, LARGEUR_BRIN / 2)
    for axe in axes:
        for arche in _arches_hautes(axe):
            planche.bomber(ruban(arche, LARGEUR_BRIN), 0.0, 1.0, LARGEUR_BRIN / 2)


# --- Le panneau du lambris : « לוֹחוֹת עֵץ עֲשׂוּיוֹת בְּמִדָּה אַחַת זֶה כָּזֶה » (Metzudat David
#     sur Ye'hezkel 41:17), et ce qui y est taillé — « מִקְלַעַת פְּקָעִים וּפְטוּרֵי צִצִּים »
#     (Melakhim I 6:18), le verset du lambris lui-même, « הַכֹּל אֶרֶז, אֵין אֶבֶן נִרְאָה ».
#     Le bouton et la fleur ouverte sont donc dans la source de la zone haute, et non
#     empruntés au champ d'en bas : c'est le même couple, au rang que 6:18 leur donne.
MARGE_PANNEAU = 0.11       # l'or plein autour du champ, en part de la tuile
FEUILLURE = 0.055          # la montée du fond depuis le trait du cadre
NIVEAU_CHAMP = 0.56        # le fond du panneau, sous l'or plein qui l'entoure
RAYON_PECAIM = 0.105
RAYON_COROLLE = 0.180
COEUR_COROLLE = 0.050
CREUX_COROLLE = 0.60       # le rayon de `corolle` entre deux lobes, en part de son rayon


def panneau(planche):
    """Un panneau de la mesure et la brindille qui y est taillée : le bouton, son brin, la
    fleur ouverte.

    La tuile est le panneau ET l'or qui l'entoure, chaque bord pris à mi-largeur de ce
    plein — deux tuiles bout à bout rendent une file de panneaux séparés, sans couture.
    Le cadre ne se grave pas, il se BOMBE : le fond descend d'un seul coup au trait du
    cadre puis remonte en feuillure, et ce sont ses deux épaulements qui font voir le
    panneau. Un rectangle creusé d'une seule marche de 1,5 cm ne rendait rien de face.
    """
    dedans = 1.0 - MARGE_PANNEAU
    planche.bomber(CARRE, 0.0, 1.0, 0.01)
    planche.bomber(((MARGE_PANNEAU, MARGE_PANNEAU), (dedans, MARGE_PANNEAU),
                    (dedans, dedans), (MARGE_PANNEAU, dedans)), 0.0, NIVEAU_CHAMP, FEUILLURE)
    planche.bomber(ruban([(0.5, 0.38), (0.5, 0.62)], 0.026), NIVEAU_CHAMP, 0.22, 0.013)
    oeuf, calice = bouton(0.5, 0.15, RAYON_PECAIM)
    planche.bomber(calice, NIVEAU_CHAMP, 0.16, 0.020)
    planche.bomber(oeuf, NIVEAU_CHAMP, 0.40, 0.034)
    for k in range(NERVURES_BOUTON):
        u = 0.5 + (k - (NERVURES_BOUTON - 1) / 2) * RAYON_PECAIM * 0.52
        planche.graver([(0.5 + (u - 0.5) * 0.35, 0.15 + RAYON_PECAIM * 0.30),
                        (u, 0.15 + RAYON_PECAIM * 1.30),
                        (0.5 + (u - 0.5) * 0.30, 0.15 + RAYON_PECAIM * 2.40)], 0.010, 0.30)
    planche.bomber(lisser(corolle(0.5, 0.68, RAYON_COROLLE, LOBES), passes=1),
                   NIVEAU_CHAMP, 0.42, 0.050)
    # Les séparations s'arrêtent DANS le creux entre deux lobes : plus longues, elles
    # sortaient de la corolle et griffaient le fond du panneau, qui est figure lui aussi.
    for k in range(LOBES):
        creux = math.pi * (2 * k + 1) / LOBES
        milieu = math.pi * 2 * k / LOBES
        for angle, bout, large in ((creux, CREUX_COROLLE * 0.88, 0.011),
                                   (milieu, 0.82, 0.008)):
            planche.graver([(0.5 + COEUR_COROLLE * math.cos(angle), 0.68 + COEUR_COROLLE * math.sin(angle)),
                            (0.5 + RAYON_COROLLE * bout * math.cos(angle),
                             0.68 + RAYON_COROLLE * bout * math.sin(angle))], large, 0.40)
    planche.bomber(ellipse(0.5, 0.68, COEUR_COROLLE, COEUR_COROLLE), NIVEAU_CHAMP + 0.30, 0.15, 0.034)


def _arches_hautes(axe):
    """Les tronçons d'un brin où il est au-dessus de l'axe médian — c'est là, et là
    seulement, qu'il passe par-dessus l'autre —, débordant de DEBORD_ARCHE points de
    part et d'autre du croisement : sans ce débord le bout du ruban tombe au MILIEU du
    brin qu'il croise et y laisse une marche au lieu de passer dessus."""
    hauts = [k for k, (_, z) in enumerate(axe) if z >= 0.5]
    for k, indice in enumerate(hauts):
        if k == 0 or indice != hauts[k - 1] + 1:
            debut = indice
        if k == len(hauts) - 1 or hauts[k + 1] != indice + 1:
            yield axe[max(0, debut - DEBORD_ARCHE):indice + 1 + DEBORD_ARCHE]


# --- Les guides, la taille, l'atlas. ------------------------------------------------------

# Ce que l'on demande au modèle pour chaque motif : l'iconographie, mot à mot, parce que
# c'est elle que le guide ne porte qu'à moitié — un crâne à deux profils sans traits
# ne se devine pas d'un dôme.
# La manière est celle de l'ornement judéen du Second Temple — ossuaires, linteaux et
# plafonds des portes de 'Houlda, frises hérodiennes — : plans plats, contours en sillon
# net, arrondi doux, ni muscles ni tiare ni barbe assyrienne.
TAILLE = "Re-sculpt this {sujet} as a genuine hand-carved stone bas-relief in the manner " \
         "of Judean ornament of the Second Temple period (Jerusalem ossuaries, the Huldah " \
         "Gates ceilings, Herodian friezes): flat carved planes, clean grooved outlines, " \
         "gentle rounding, restrained and geometric, no Assyrian, Egyptian or Greek " \
         "traits. Keep exactly this composition and framing: {iconographie} Fine tool " \
         "marks, slightly worn. Pure grayscale on a flat pure black background, " \
         "orthographic front view, no colour, no text."
KERUV = ("an awe-inspiring heavenly being of Ezekiel's vision, NOT a human in clothes and NOT "
         "a Christian angel: no tunic, no garment, no belt, no visible torso. The body is a "
         "tall sheath of feathers made by two lower wings wrapped down and crossed in front "
         "from the shoulders to the shins. Just below the shoulders TWO small human HANDS "
         "come out from under the wings, one on each side, laid flat against the feather "
         "sheath, palm outwards, fingers together and pointing down — hands ONLY, no arms, "
         "no wrists, no shoulders, nothing else of a human body anywhere. Below the sheath "
         "ONE single straight rigid leg without knee, ending in ONE calf's hoof, CLOVEN — "
         "split down the middle into two blunt toes like an ox's foot, never a ball and "
         "never a human foot. THE WINGS ARE THE GLORY OF THE FIGURE and must be "
         "magnificent: each wing is built of individual feathers — three graded rows of small "
         "rounded coverts overlapping like roof tiles at the root, then a row of longer "
         "secondaries, then long slender primaries carved one by one to the tip, each with "
         "its own outline and central shaft, five graded rows at least. EVERY feather ends in "
         "a POINT, and the tips stay slightly apart, so the edge of the wing is a row of "
         "sharp points and not a smooth border. {ailes} THE HEAD IS THE HARD PART, read it "
         "twice: there is ONE SINGLE HEAD, one skull only, and it carries TWO FACES looking "
         "in opposite directions, a man's profile on the left and a young lion's profile on "
         "the right, sharing the same cranium back to back, like a janiform head on a coin. "
         "It must NOT be two heads side by side, NOT two necks, NOT two separate skulls "
         "touching, NOT one head behind the other. Both faces are BLANK featureless "
         "silhouettes — no eye, no eyebrow, no nostril, no mouth, nothing carved inside the "
         "profile, only the outline of brow, nose and chin. The LEFT profile is a man's: "
         "straight nose, smooth skull, no beard, no wig. The RIGHT profile must be "
         "unmistakably a YOUNG LION: bulging forehead, short square muzzle jutting forward, "
         "deep heavy jaw, a small round ear set high, and a short mane carved in separate "
         "locks running around the back of the skull down to the neck. Majestic, hieratic, "
         "severe; no halo, no crown, no beard, no palm trees, a single figure alone.")
class Taille(typing.NamedTuple):
    """Ce qu'on demande au modèle pour un motif : son sujet, et son iconographie mot à
    mot — c'est elle que le guide ne porte qu'à moitié."""
    sujet: str
    iconographie: str


class Motif(typing.NamedTuple):
    """Un motif de l'atlas : ce qui le dessine, le cadre réel qu'il couvre, sa case dans
    la grille, et la taille qu'un modèle en fait. `taille` vide = motif DESSINÉ, dont la
    planche est la tuile : sa manière est géométrique, il n'y a rien à apprendre d'un
    modèle, et lui seul est sûr de se répéter sans couture."""
    guide: typing.Callable
    cadre: tuple
    case: tuple
    taille: Taille = None


MOTIFS = {
    "keruv": Motif(keruv, CADRE_DEBOUT, (0, 1), Taille(
        "four-winged cherub",
        KERUV.format(ailes="Its two upper wings are very large, rising from the "
                           "shoulders and opening a little outwards, their tips well "
                           "above the head."))),
    "keruv_dresse": Motif(keruv_dresse, CADRE_DEBOUT, (1, 0), Taille(
        "four-winged cherub",
        KERUV.format(ailes="Its two upper wings rise straight up from the "
                           "shoulders, tall and narrow like two flames, their "
                           "tips high above the head, the flight feathers long, "
                           "straight and parallel."))),
    "timora": Motif(timora, CADRE_DEBOUT, (1, 1), Taille(
        "palmette of palm fronds",
        "a fan of exactly seven palm fronds springing from a small bell-shaped base, "
        "with no trunk and no dates: the middle frond upright, the three pairs on "
        "either side curving outward and drooping more and more, the lowest pair "
        "falling back down to the level of the base. "
        "READ THIS TWICE, it is the part that gets dropped: between the bell base and "
        "the fronds there is a COLLAR, carved IN FRONT of them and clearly visible, of "
        "five short broad bracts that sheathe the neck like the leaf-scales at the top "
        "of a palm trunk — one upright in the middle, two laid over it on each side, "
        "each a stubby pointed scale about a fifth of the height of a frond, overlapping "
        "like tiles. Without that collar the fan sits on a bare bell; with it, it grows "
        "out of a capital. The bell itself is girdled by two carved rings. "
        "IMPORTANT: every frond is deeply "
        "CUT INTO SEPARATE POINTED LEAFLETS along both sides of a grooved midrib, like "
        "a feather or a comb, never a smooth leaf, never a flower petal and never a "
        "stiff Greek anthemion; the leaflets are narrow, straight and angled towards "
        "the tip.")),
    "fleuron": Motif(fleuron, CADRE_DEBOUT, (0, 0), Taille(
        "six-petal rosette",
        "an open six-petal compass-drawn rosette filling the frame, as on Jerusalem "
        "ossuaries, a round raised heart in the centre ringed by a cut groove, each petal "
        "a carved lobe with a sharp grooved rib down its middle and a clean cut outline "
        "separating it from its neighbours.")),
    "bouton": Motif(bouton_ferme, CADRE_DEBOUT, (2, 0), Taille(
        "closed flower bud",
        "a single closed bud standing upright, shaped like an egg with BOTH ENDS DRAWN "
        "TO A POINT, widest below its middle, seated in a short calyx of three sepals "
        "that wrap its foot. Three shallow ribs run up the bud from the calyx to the "
        "point. It is shut: no petal is open, nothing flares out at the top.")),
    "dekel": Motif(dekel, CADRE_DEBOUT, (2, 2), Taille(
        "date palm tree",
        "a single upright date palm seen flat from the front, as on the Bar Kokhba coins: "
        "a straight slender trunk rising the lower half of the frame, its whole length "
        "covered in the CHEVRON leaf-scars of cut-off fronds, stacked one above the other "
        "like a braid, never smooth and never a ring-banded column. "
        "From its top springs a crown of exactly seven fronds — the middle one upright, "
        "the three pairs on either side bending outward and drooping more and more, the "
        "lowest pair falling back below the horizontal. "
        "IMPORTANT: every frond is deeply CUT INTO SEPARATE POINTED LEAFLETS along both "
        "sides of a grooved midrib, like a feather or a comb, never a smooth leaf and "
        "never a stiff Greek anthemion; the leaflets are narrow, straight and angled "
        "towards the tip. "
        "READ THIS TWICE, it is the part that gets dropped: TWO clusters of dates hang "
        "from the crown, one on each side of the trunk, each a few slack strands weighed "
        "down with small oval fruit, hanging DOWN in front of the trunk and clearly "
        "separate from the fronds — not a bunch of grapes, not a pinecone. "
        "No capital, no collar of bracts, no volutes: this is a tree, not an ornament.")),
    "corde": Motif(corde, (0.0, 0.0, 1.0, 1.0), (2, 1)),
    "tresse": Motif(tresse, (0.0, 0.0, 1.0, 1.0), (0, 2)),
    "panneau": Motif(panneau, (0.0, 0.0, 1.0, 1.0), (1, 2)),
}


def ombrer(relief, masque):
    """Le guide tel qu'on le montre au modèle : le relief éclairé de haut à gauche, en
    or sur un fond brun — un rendu, que le modèle lit mieux qu'une carte de gris."""
    hauteur = relief * 0.03 * relief.shape[1]
    gz, gu = np.gradient(hauteur)
    normale = np.stack([-gu, -gz, np.ones_like(hauteur)], -1)
    normale /= np.linalg.norm(normale, axis=-1, keepdims=True)
    lumiere = np.array([-0.5, 0.6, 0.62])
    ombre = np.clip(normale @ (lumiere / np.linalg.norm(lumiere)), 0, 1)
    rgb = (0.25 + 0.75 * ombre)[..., None] * np.array([1.0, 0.78, 0.38])
    return np.where(masque[..., None] > 0.5, rgb, np.array([0.40, 0.32, 0.18]))


def guider(nom):
    motif = MOTIFS[nom]
    relief, masque = _planche(motif).relief(FONDU)
    rgb = ombrer(relief / relief.max(), masque)
    image = bpy.data.images.new(nom, rgb.shape[1], rgb.shape[0], alpha=False)
    image.pixels.foreach_set(np.concatenate([rgb, np.ones(rgb.shape[:2] + (1,))], -1)
                             .astype(np.float32).ravel())
    GUIDES.mkdir(parents=True, exist_ok=True)
    image.filepath_raw = str(GUIDES / f"{nom}.png")
    image.file_format = "PNG"
    image.save()
    print(f"  {nom:8s} guide : {image.filepath_raw}")


def tailler(nom):
    """Fait tailler le guide de `nom` par gpt-image-2 et pose la tuile dans `gravures/`."""
    sys.path.insert(0, str(RACINE / ".claude" / "skills" / "fal-video"))
    import fal_commun  # noqa: E402
    sujet, iconographie = MOTIFS[nom].taille
    cle = fal_commun.cle_api()
    esquisse = ESQUISSES.get(nom)
    images = [GUIDES / f"{nom}.png"] + ([esquisse] if esquisse else [])
    prompt = TAILLE.format(sujet=sujet, iconographie=iconographie)
    corps = {"prompt": prompt + (" " + ESQUISSE if len(images) > 1 else ""),
             "image_urls": [fal_commun.televerse(str(image), cle) for image in images],
             "image_size": "square_hd", "quality": "high", "output_format": "png"}
    reponse = fal_commun.genere("openai/gpt-image-2/edit", corps, cle)
    fal_commun.telecharge(reponse["images"][0]["url"], str(TUILES / f"{nom}.png"))
    print(f"  {nom:8s} taillé : gravures/{nom}.png")


def _planche(motif):
    planche = Planche(motif.cadre, TUILE_PX)
    motif.guide(planche)
    return planche


def relief_dessine(nom):
    """(relief, masque) d'un motif dessiné : sa planche EST sa tuile. Ni recadrage sur la
    figure ni bombé depuis le bord — les deux supposent une figure isolée au milieu de sa
    tuile, quand un cordon touche ses deux bords et doit y retrouver son voisin."""
    relief, masque = _planche(MOTIFS[nom]).relief(FONDU)
    return (relief / (relief.max() or 1.0)).astype(np.float32), masque > 0.5


def relief_taille(nom):
    """(relief, masque) d'une tuile taillée, posés dans le cadre du motif."""
    cadre = MOTIFS[nom].cadre
    luminance = lire(TUILES / f"{nom}.png")
    luminance, masque = cadrer(luminance, figure(luminance > SEUIL_FOND), cadre, TUILE_PX)
    echelle = TUILE_PX / (cadre[2] - cadre[0])
    rayon = max(1, int(round(RONDEUR * echelle)))
    dedans = distance(masque, rayon)
    volume = bombe(dedans / rayon)
    modele = flouter(luminance, max(1, int(round(GRAIN * echelle))))
    # Centiles, pas extrêmes : quelques pixels du bord ou d'un reflet écrasaient tout le modelé.
    bas, haut = np.percentile(modele[masque], (1, 99))
    modele = np.clip((modele - bas) / (haut - bas), 0.0, 1.0)
    # Le bord se fond parce que le modelé y descend, non parce que la carte entière est floutée :
    # le bombé y tombe déjà de lui-même, et le flou effaçait tout le modelé pour ce seul ourlet.
    fondu = max(1, int(round(FONDU * echelle)))
    modele *= np.clip(dedans / fondu, 0.0, 1.0)
    relief = np.where(masque, (1.0 - PART_MODELE) * volume + PART_MODELE * modele, 0.0)
    return flouter(relief, 1).astype(np.float32), masque


def graver():
    atlas = np.zeros((ATLAS_PX, ATLAS_PX), dtype=np.float32)
    masque = np.zeros((ATLAS_PX, ATLAS_PX), dtype=np.float32)
    fiche = {"pixels": ATLAS_PX, "motifs": {}}
    for nom, motif in MOTIFS.items():
        cadre, (colonne, ligne) = motif.cadre, motif.case
        relief, dedans = (relief_taille if motif.taille else relief_dessine)(nom)
        l0, c0 = ligne * TUILE_PX, colonne * TUILE_PX
        atlas[l0:l0 + TUILE_PX, c0:c0 + TUILE_PX] = relief
        masque[l0:l0 + TUILE_PX, c0:c0 + TUILE_PX] = dedans
        contour = silhouette(dedans, cadre[:2], TUILE_PX / (cadre[2] - cadre[0]), TOLERANCE[nom])
        fiche["motifs"][nom] = {"cadre": cadre,
                                "tuile": [colonne / GRILLE, ligne / GRILLE, 1 / GRILLE],
                                "silhouette": [[round(u, 4), round(z, 4)] for u, z in contour]}
        print(f"  {nom:12s} silhouette : {len(contour)} sommets, modelé jusqu'à {relief.max():.2f}")
    atlas /= atlas.max()
    ecrire(NOM, atlas, masque)
    (SORTIE / "gravures.json").write_text(json.dumps(fiche, separators=(",", ":")), encoding="utf-8")


ARGUMENTS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if ARGUMENTS[:1] == ["--guides"]:
    for nom in ARGUMENTS[1:] or MOTIFS:
        guider(nom)
elif ARGUMENTS[:1] == ["--tailler"]:
    for nom in ARGUMENTS[1:] or [n for n, m in MOTIFS.items() if m.taille]:
        tailler(nom)
else:
    graver()
