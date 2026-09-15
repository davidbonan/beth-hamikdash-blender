"""Les contours des figures du Bayit : ce qui se dessine à plat avant de sortir d'une paroi.

Un keruv, un lion, une aile se donnent en quelques points de construction, dans le
repère (u, z) de la figure et à l'échelle de sa hauteur ; ce qui en fait une silhouette
est le lissage de Chaikin, qui coupe chaque angle en deux jusqu'à ce que le contour
soit une courbe. Dix points de construction en font quatre-vingts au troisième passage.

Ni bpy ni numpy : le blockout (relief taillé dans l'or) et `beit_hamikdash_parokhet.py`
(motif tissé dans l'étoffe) lisent tous deux ce fichier.
"""
import math


def lisser(contour, passes=3):
    """Chaikin sur un contour FERMÉ : chaque arête garde son quart et ses trois quarts."""
    points = list(contour)
    for _ in range(passes):
        n = len(points)
        coupe = []
        for i in range(n):
            (u0, z0), (u1, z1) = points[i], points[(i + 1) % n]
            coupe.append((0.75 * u0 + 0.25 * u1, 0.75 * z0 + 0.25 * z1))
            coupe.append((0.25 * u0 + 0.75 * u1, 0.25 * z0 + 0.75 * z1))
        points = coupe
    return points


def symetrique(demi):
    """Le contour entier d'une figure symétrique, depuis sa moitié droite donnée du haut
    de l'axe au bas de l'axe : la moitié gauche est son miroir, parcourue en remontant."""
    return list(demi) + [(-u, z) for u, z in reversed(demi[1:-1])]


def poser(contour, u, z, taille, sens=1):
    """Le contour à l'échelle `taille`, posé en (u, z), regardant vers `sens`."""
    return [(u + sens * du * taille, z + dz * taille) for du, dz in contour]


def poser_lame(contour, u, z, angle, taille, sens=1):
    """Une lame — aile, palme — attachée en (u, z), penchée de `angle` degrés sur la
    verticale vers `sens`. Le contour se donne le long de sa nervure (a, de 0 à 1) et en
    travers (b, positif du côté du bord d'attaque, qui regarde le haut)."""
    a = math.radians(angle)
    du, dz = sens * math.sin(a), math.cos(a)
    nu, nz = -sens * math.cos(a), math.sin(a)
    return [(u + taille * (p * du + q * nu), z + taille * (p * dz + q * nz)) for p, q in contour]


def ellipse(u, z, ru, rz, points=32):
    return [(u + ru * math.cos(2 * math.pi * k / points), z + rz * math.sin(2 * math.pi * k / points))
            for k in range(points)]


def corolle(u, z, r, lobes=8):
    """Une fleur épanouie : `lobes` pétales autour d'un cœur. Sert aussi de crinière."""
    return [(u + rk * math.cos(a), z + rk * math.sin(a))
            for a, rk in ((a, r * (0.60 + 0.40 * abs(math.cos(lobes * a / 2)) ** 0.65))
                          for a in (2 * math.pi * k / (lobes * 8) for k in range(lobes * 8)))]


# Une aile levée, vue à plat : bord d'attaque en arc, bord de fuite en rémiges. Six
# pennes est un CHOIX ; c'est leur découpe, et rien d'autre, qui fait lire une aile
# plutôt qu'une feuille. Les pennes s'allongent vers la pointe — les primaires — et se
# couchent le long de la nervure : droites et égales, elles se lisaient en marches
# d'escalier dès que l'aile se levait contre le corps.
def aile(pennes=6, passes=3):
    attaque = [(0.0, 0.06), (0.18, 0.17), (0.45, 0.21), (0.75, 0.17), (0.96, 0.08), (1.0, 0.0)]
    fuite = []
    for k in range(pennes):
        a = 1.0 - (k + 0.5) / pennes
        longueur = 0.18 + 0.26 * a
        couche = 0.55 * longueur
        fuite.append((a + 0.05 + couche * 0.4, -longueur * 0.42))   # l'entaille entre deux pennes
        fuite.append((a + couche, -longueur))                       # la pointe de la penne
        fuite.append((a - 0.04 + couche * 0.9, -longueur * 0.94))
    return lisser(attaque + fuite + [(0.0, -0.10)], passes=passes)


# Le corps dressé d'une figure debout, à plat, sans bras détachés : encolure, épaule,
# bras le long du corps, taille, hanche, robe évasée jusqu'à l'ourlet. Moitié droite,
# du haut de l'axe (l'attache du cou) au bas de l'axe (l'ourlet).
CORPS_DRESSE = symetrique([
    (0.000, 0.820), (0.055, 0.820), (0.065, 0.790), (0.150, 0.770), (0.175, 0.700),
    (0.150, 0.600), (0.095, 0.520), (0.130, 0.420), (0.165, 0.220), (0.185, 0.030),
    (0.170, 0.000), (0.000, 0.000)])

# La tête double du keruv — « וּשְׁנַיִם פָּנִים לַכְּרוּב » (Ye'hezkel 41:18) : un seul crâne,
# un profil de chaque côté, museau vers l'extérieur, et AUCUN TRAIT (§9 de la fiche).
# Deux têtes posées côte à côte se chevauchaient en lunettes ; un crâne à deux faces
# est ce que le verset décrit. Moitié droite, du sommet du crâne à l'attache du cou.
TETE_DOUBLE = symetrique([
    (0.00, 0.90), (0.35, 0.88), (0.90, 0.62), (1.20, 0.35), (1.35, 0.10), (1.25, -0.15),
    (0.75, -0.30), (0.15, -0.42), (0.00, -0.45)])
