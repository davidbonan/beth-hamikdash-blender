"""Grave les trois figures des parois du Bayit : une carte de relief et leurs silhouettes.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_gravures.py

« כְּרוּבִים וְתִמֹרֹת וּפְטוּרֵי צִצִּים » (Melakhim I 6:29), « וְצִפָּה זָהָב מְיֻשָּׁר עַל־הַמְּחֻקֶּה »
(6:35) : la figure est CREUSÉE, et l'or épouse le creusé. Un bas-relief se lit à son
modelé — les volumes qui bombent, les plans qui s'étagent, les sillons qui séparent une
penne de la suivante — et non à sa découpe : une plaque plate au contour parfait reste
un emporte-pièce. Le blockout ne pose donc plus qu'UNE plaque par figure, à sa
silhouette ; tout le modelé est ici, dans une carte que la plaque lit par ses UV.

Écrit `visite/matieres/gravures_2048.webp` — un atlas de trois tuiles de 1024 : gris =
hauteur du modelé, alpha = masque — et `visite/matieres/gravures.json` : pour chaque
motif, le cadre réel que sa tuile couvre, sa place dans l'atlas, et sa silhouette,
tracée sur le masque même de la carte, pour que la plaque et le modelé coïncident au
pixel. Tout se donne dans le repère de la figure : hauteur 1, axe en u = 0, pied en z = 0.

Le blockout lit le JSON (`_relief_grave`), `visite/matieres.js` lit l'atlas (GRAVURE).
Demande `cwebp` sur le PATH. À relancer après toute modification de ce script ou de
`beit_hamikdash_contours.py`, puis reconstruire la scène.
"""
import json
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from beit_hamikdash_carte import SORTIE, Planche, ecrire  # noqa: E402
from beit_hamikdash_contours import (TETE_DOUBLE, aile, corolle, ellipse, lisser,  # noqa: E402
                                     poser, poser_lame, symetrique)

TUILE_PX = 1024
ATLAS_PX = 2 * TUILE_PX
NOM = f"gravures_{ATLAS_PX}"
# Le cadre d'une figure debout : un peu plus large qu'elle, du dessous du pied au
# dessus de la tête, pour que le fondu du bord n'atteigne jamais la tuile voisine.
CADRE_DEBOUT = (-0.6, -0.1, 0.6, 1.1)
FONDU = 0.005            # en part de la hauteur : 2 cm sur un keruv de paroi
# Simplification de la silhouette, en part de la hauteur : 1,5 cm sur un keruv de paroi,
# 1 cm sur la timora d'un jambage. Le fleuron fait 22 cm et court par centaines : le
# chanfrein et l'export dédoublent chaque sommet, et c'est là que le glb se gagne.
TOLERANCE = {"keruv": 0.005, "timora": 0.005, "fleuron": 0.02}


# --- Les rubans : bras, palmes. ------------------------------------------------------

def bezier(p0, p1, p2, n=24):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (k / (n - 1) for k in range(n))]


def normales(axe):
    """La normale unitaire en chaque point d'une ligne brisée, moyenne des deux segments."""
    n = []
    for k, (u, z) in enumerate(axe):
        (u0, z0), (u1, z1) = axe[max(0, k - 1)], axe[min(len(axe) - 1, k + 1)]
        du, dz = u1 - u0, z1 - z0
        l = math.hypot(du, dz) or 1.0
        n.append((-dz / l, du / l))
    return n


def ruban(axe, largeurs):
    """Le contour d'un ruban le long de `axe`, de demi-largeur `largeurs[k]` au point k."""
    n = normales(axe)
    gauche = [(u + nu * w, z + nz * w) for (u, z), (nu, nz), w in zip(axe, n, largeurs)]
    droite = [(u - nu * w, z - nz * w) for (u, z), (nu, nz), w in zip(axe, n, largeurs)]
    return gauche + droite[::-1]


# --- Le keruv : debout, de face, deux ailes levées, un crâne à deux profils. ------------

# Le corps vêtu, sans les bras : cou, épaules, poitrine, taille, hanches, robe évasée
# jusqu'à l'ourlet. Moitié droite, du haut du cou à l'axe de l'ourlet. Le
# CORPS_DRESSE du rideau était sans épaules ni cou : une figure de trois mètres se
# lisait en mannequin de couturière. Le cou monte DANS le crâne, qui le recouvre :
# arrêté dessous, le lissage le rognait et la tête flottait.
CORPS_KERUV = symetrique([
    (0.000, 0.900), (0.050, 0.900), (0.055, 0.800), (0.170, 0.780), (0.190, 0.720),
    (0.165, 0.620), (0.135, 0.550), (0.150, 0.470), (0.175, 0.400), (0.205, 0.250),
    (0.225, 0.100), (0.230, 0.030), (0.000, 0.030)])
# Le bras droit, le long du corps et un peu fléchi : épaule, coude, poignet.
BRAS = ((0.155, 0.760), (0.205, 0.610), (0.165, 0.450))
LARGEURS_BRAS = (0.052, 0.046, 0.036)
# Les plis de la robe partent de la ceinture et s'écartent vers l'ourlet.
PLIS = (-1.0, -0.5, 0.0, 0.5, 1.0)

# Les niveaux, en unités libres : ce qui est devant est plus haut. L'atlas les ramène
# tous ensemble à [0, 1], et la visite les lit à la même échelle sur les trois motifs.
NIVEAU_AILE, NIVEAU_CORPS, NIVEAU_BRAS, NIVEAU_TETE = 0.0, 0.35, 0.65, 0.65
# Les ailes s'ouvrent à 40° : serrées contre le corps elles se cachaient derrière la tête
# et se lisaient en bois de cerf. Leur pointe reste sous le haut de la tuile.
ANGLE_AILE, TAILLE_AILE = 40, 0.40


def keruv(planche):
    for sens in (-1, 1):
        u_aile, z_aile = sens * 0.12, 0.70
        contour = poser_lame(aile(), u_aile, z_aile, ANGLE_AILE, TAILLE_AILE, sens)
        planche.bomber(contour, NIVEAU_AILE, 1.0, 0.05)
        # Les rémiges : un sillon de chaque entaille du bord de fuite jusqu'au poignet,
        # et l'arc des couvertures qui les recouvre à la racine.
        for k in range(6):
            a = 1.0 - (k + 0.5) / 6
            longueur = 0.18 + 0.26 * a
            entaille = (a + 0.05 + 0.55 * longueur * 0.4, -longueur * 0.42)
            sillon = poser_lame([entaille, (0.14, -0.02)], u_aile, z_aile, ANGLE_AILE, TAILLE_AILE, sens)
            planche.graver(sillon, 0.012, 0.45)
        couvertures = poser_lame([(0.10, -0.12), (0.40, -0.14), (0.70, -0.12), (0.96, -0.05)],
                                 u_aile, z_aile, ANGLE_AILE, TAILLE_AILE, sens)
        planche.graver(couvertures, 0.010, 0.35)
    for sens in (-1, 1):
        planche.bomber(ellipse(sens * 0.075, 0.02, 0.05, 0.03), NIVEAU_CORPS, 0.8, 0.02)
    planche.bomber(lisser(CORPS_KERUV), NIVEAU_CORPS, 1.0, 0.10)
    planche.graver([(-0.14, 0.50), (0.0, 0.49), (0.14, 0.50)], 0.014, 0.5)
    for s in PLIS:
        planche.graver([(0.09 * s, 0.47), (0.15 * s, 0.25), (0.20 * s, 0.04)], 0.012, 0.45)
    for sens in (-1, 1):
        axe = [(sens * u, z) for u, z in BRAS]
        planche.bomber(lisser(ruban(axe, LARGEURS_BRAS), passes=2), NIVEAU_BRAS, 0.9, 0.04)
        planche.bomber(ellipse(sens * 0.150, 0.415, 0.038, 0.048), NIVEAU_BRAS, 0.9, 0.03)
    # Le crâne à deux profils, un peu resserré, et lissé UNE fois : trois passes en
    # faisaient une miche, et c'est le nez et le menton de chaque profil qui le font lire.
    t = 0.118
    tete = [(0.85 * u, z) for u, z in TETE_DOUBLE]
    planche.bomber(lisser(poser(tete, 0.0, 0.894, t), passes=1), NIVEAU_TETE, 1.2, 0.05)
    planche.graver([(-0.09, 0.935), (0.0, 0.945), (0.09, 0.935)], 0.010, 0.4)


# --- La timora : fût annelé, couronne de palmes qui retombent, deux régimes. ------------

# (inclinaison sur la verticale, longueur, retombée) : les palmes du fond montent, celles
# du devant retombent en arc. Neuf est un CHOIX. Ce qui distingue un palmier d'un
# éventail, c'est que la palme PLOIE.
PALMES = ((0, 0.46, 0.12), (32, 0.44, 0.30), (-32, 0.44, 0.30), (62, 0.40, 0.55),
          (-62, 0.40, 0.55), (92, 0.36, 0.80), (-92, 0.36, 0.80), (118, 0.30, 0.65),
          (-118, 0.30, 0.65))
FUT = 0.56
COURONNE = (0.0, FUT - 0.02)
NIVEAU_FUT, NIVEAU_PALME, NIVEAU_REGIME = 0.4, 0.25, 0.55


def palme(inclinaison, longueur, retombee):
    a = math.radians(inclinaison)
    p0 = COURONNE
    p1 = (p0[0] + 0.55 * longueur * math.sin(a), p0[1] + 0.55 * longueur * math.cos(a))
    p2 = (p0[0] + longueur * math.sin(a), p0[1] + longueur * math.cos(a) - retombee * longueur)
    axe = bezier(p0, p1, p2)
    largeurs = [0.004 + 0.062 * (1.0 - k / (len(axe) - 1)) ** 0.6 * min(1.0, 0.25 + 3.0 * k / len(axe))
                for k in range(len(axe))]
    return axe, largeurs


def timora(planche):
    for k in range(9):
        z = FUT * k / 8
        w = 0.055 * (1.0 - 0.22 * k / 8)
        planche.bomber([(-w, z), (w, z), (w, z + FUT / 8 + 0.01), (-w, z + FUT / 8 + 0.01)]
                       if k < 8 else [(-w, z - 0.02), (w, z - 0.02), (w, z + 0.03), (-w, z + 0.03)],
                       NIVEAU_FUT, 1.0, 0.05)
    for k in range(1, 13):
        z = FUT * k / 13
        w = 0.055 * (1.0 - 0.22 * k / 13)
        planche.graver([(-w, z + 0.004), (0.0, z - 0.004), (w, z + 0.004)], 0.010, 0.5)
    for inclinaison, longueur, retombee in PALMES:
        axe, largeurs = palme(inclinaison, longueur, retombee)
        planche.bomber(lisser(ruban(axe, largeurs), passes=1), NIVEAU_PALME, 1.0, 0.03)
        n = normales(axe)
        for k in range(3, len(axe) - 1, 2):
            (u, z), (nu, nz), w = axe[k], n[k], largeurs[k]
            (u1, z1) = axe[k + 1]
            tu, tz = u1 - u, z1 - z
            l = math.hypot(tu, tz) or 1.0
            tu, tz = tu / l * 0.02, tz / l * 0.02
            for cote in (-1, 1):
                planche.graver([(u, z), (u + cote * nu * w * 0.95 + tu, z + cote * nz * w * 0.95 + tz)],
                               0.007, 0.4)
    for sens in (-1, 1):
        for du, dz, r in ((0.0, 0.0, 0.028), (-0.03, -0.035, 0.024), (0.03, -0.035, 0.024),
                          (-0.045, -0.075, 0.020), (0.0, -0.07, 0.022), (0.045, -0.075, 0.020),
                          (-0.02, -0.108, 0.017), (0.02, -0.108, 0.017)):
            planche.bomber(ellipse(sens * 0.085 + du, COURONNE[1] - 0.02 + dz, r, r * 1.15),
                           NIVEAU_REGIME, 0.7, 0.015)


# --- Le fleuron : la corolle épanouie, huit pétales autour d'un cœur. --------------------

LOBES = 8


def fleuron(planche):
    planche.bomber(corolle(0.0, 0.5, 0.5, LOBES), 0.0, 1.0, 0.12)
    for k in range(LOBES):
        a = math.pi * (2 * k + 1) / LOBES
        planche.graver([(0.10 * math.cos(a), 0.5 + 0.10 * math.sin(a)),
                        (0.40 * math.cos(a), 0.5 + 0.40 * math.sin(a))], 0.022, 0.5)
    planche.bomber(ellipse(0.0, 0.5, 0.13, 0.13), 0.6, 1.0, 0.10)


MOTIFS = {"keruv": (keruv, CADRE_DEBOUT, (0, 1)),
          "timora": (timora, CADRE_DEBOUT, (1, 1)),
          "fleuron": (fleuron, (-0.6, -0.1, 0.6, 1.1), (0, 0))}


def graver():
    atlas = np.zeros((ATLAS_PX, ATLAS_PX), dtype=np.float32)
    masque = np.zeros((ATLAS_PX, ATLAS_PX), dtype=np.float32)
    fiche = {"pixels": ATLAS_PX, "motifs": {}}
    for nom, (tailler, cadre, (colonne, ligne)) in MOTIFS.items():
        planche = Planche(cadre, TUILE_PX)
        tailler(planche)
        relief, dedans = planche.relief(FONDU)
        l0, c0 = ligne * TUILE_PX, colonne * TUILE_PX
        atlas[l0:l0 + TUILE_PX, c0:c0 + TUILE_PX] = relief
        masque[l0:l0 + TUILE_PX, c0:c0 + TUILE_PX] = dedans
        silhouette = planche.silhouette(TOLERANCE[nom])
        fiche["motifs"][nom] = {"cadre": cadre, "tuile": [colonne * 0.5, ligne * 0.5, 0.5],
                                "silhouette": [[round(u, 4), round(z, 4)] for u, z in silhouette]}
        print(f"  {nom:8s} silhouette : {len(silhouette)} sommets, modelé jusqu'à {relief.max():.2f}")
    atlas /= atlas.max()
    ecrire(NOM, atlas, masque)
    (SORTIE / "gravures.json").write_text(json.dumps(fiche, separators=(",", ":")), encoding="utf-8")


graver()
