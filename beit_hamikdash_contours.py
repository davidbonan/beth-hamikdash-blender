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


def courbe(fil, passes=3):
    """Chaikin sur un fil OUVERT : les deux bouts restent en place, le reste s'arrondit."""
    points = list(fil)
    for _ in range(passes):
        coupe = [points[0]]
        for (u0, z0), (u1, z1) in zip(points, points[1:]):
            coupe.append((0.75 * u0 + 0.25 * u1, 0.75 * z0 + 0.25 * z1))
            coupe.append((0.25 * u0 + 0.75 * u1, 0.25 * z0 + 0.75 * z1))
        coupe.append(points[-1])
        points = coupe
    return points


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


def ruban(axe, largeur):
    """Le contour fermé d'un trait qui suit `axe` : l'aller décalé d'un côté de la
    normale, le retour de l'autre. `largeur` est un nombre — une queue, une ceinture,
    un pli — ou la demi-largeur en chaque point — une palme, un bras."""
    demi = [largeur / 2] * len(axe) if isinstance(largeur, (int, float)) else list(largeur)
    n = normales(axe)
    gauche = [(u + nu * w, z + nz * w) for (u, z), (nu, nz), w in zip(axe, n, demi)]
    droite = [(u - nu * w, z - nz * w) for (u, z), (nu, nz), w in zip(axe, n, demi)]
    return gauche + droite[::-1]


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

# Le corps vêtu du keruv, sans les bras : cou, épaules, poitrine, taille, hanches, robe
# évasée jusqu'à l'ourlet. Moitié droite, du haut du cou à l'axe de l'ourlet. Le
# CORPS_DRESSE était sans épaules ni cou : une figure de trois mètres se lisait en
# mannequin de couturière. Le cou monte DANS le crâne, qui le recouvre : arrêté
# dessous, le lissage le rognait et la tête flottait.
# Les proportions sont celles d'un ENFANT — « כְּרוּב : כְּרַבְיָא » (Soucca 5b, Rashi Ex. 25:18) :
# la tête fait un cinquième de la hauteur, les épaules tombent à 0,74, non 0,80.
CORPS_KERUV = symetrique([
    (0.000, 0.860), (0.050, 0.860), (0.055, 0.750), (0.165, 0.730), (0.185, 0.680),
    (0.165, 0.600), (0.140, 0.540), (0.155, 0.470), (0.180, 0.400), (0.210, 0.250),
    (0.230, 0.100), (0.235, 0.030), (0.000, 0.030)])
# Le bras droit, le long du corps et un peu fléchi : épaule, coude, poignet.
BRAS = ((0.150, 0.710), (0.200, 0.580), (0.165, 0.440))
LARGEURS_BRAS = (0.052, 0.046, 0.036)
# Les plis de la robe partent de la ceinture et s'écartent vers l'ourlet.
PLIS = (-1.0, -0.5, 0.0, 0.5, 1.0)

# La tête double du keruv — « וּשְׁנַיִם פָּנִים לַכְּרוּב » (Ye'hezkel 41:18) : un seul crâne,
# un profil de chaque côté, museau vers l'extérieur, et AUCUN TRAIT (§9 de la fiche).
# Deux têtes posées côte à côte se chevauchaient en lunettes ; un crâne à deux faces
# est ce que le verset décrit. Moitié droite, du sommet du crâne à l'attache du cou.
TETE_DOUBLE = symetrique([
    (0.00, 0.90), (0.35, 0.88), (0.90, 0.62), (1.20, 0.35), (1.35, 0.10), (1.25, -0.15),
    (0.75, -0.30), (0.15, -0.42), (0.00, -0.45)])


# --- La timora : le dattier, tel que la tradition le lit et le frappe. -----------------

# « וְתִמֹרֹת » (Melakhim I 6:29) : Rashi et Radak lisent דקלים, des palmiers-dattiers, et
# la fiche (§8c-bis) en fixe sept palmes. Son image juive est celle des monnaies de
# Bar Kokhba : un fût droit à écailles, sept palmes — celle du milieu dressée, les
# paires suivantes qui ploient en arc —, et deux régimes de dattes qui pendent de la
# couronne, de part et d'autre du fût. Ni volutes ni collier : c'était la palmette
# assyrienne, étrangère à cette tradition.
FUT = 0.56
TRONC = symetrique([(0.0, FUT), (0.045, FUT), (0.052, 0.10), (0.065, 0.035), (0.09, 0.0), (0.0, 0.0)])
ECAILLE = 0.045                          # pas des losanges du fût
COURONNE = (0.0, FUT - 0.01)
# (inclinaison sur la verticale, longueur, retombée) : la palme du milieu se dresse, les
# paires suivantes ploient de plus en plus, la dernière retombe sous l'horizontale.
PALMES = ((0, 0.42, 0.0), (28, 0.42, 0.18), (60, 0.40, 0.42), (95, 0.34, 0.55))
REGIME = ((0.0, 0.0, 0.026), (-0.028, -0.030, 0.023), (0.028, -0.030, 0.023),
          (-0.040, -0.065, 0.020), (0.0, -0.060, 0.021), (0.040, -0.065, 0.020),
          (-0.018, -0.095, 0.017), (0.018, -0.095, 0.017), (0.0, -0.122, 0.014))
ATTACHE_REGIME = (0.085, FUT - 0.05)


def palme(inclinaison, longueur, retombee):
    """(axe, demi-largeurs) d'une palme : un arc depuis la couronne, large à la base,
    effilé à la pointe. La silhouette reste LISSE : les folioles ne sont que des sillons."""
    a = math.radians(inclinaison)
    p0 = COURONNE
    p1 = (p0[0] + 0.5 * longueur * math.sin(a), p0[1] + 0.5 * longueur * math.cos(a))
    p2 = (p0[0] + longueur * math.sin(a), p0[1] + longueur * (math.cos(a) - retombee))
    axe = bezier(p0, p1, p2, 32)
    n = len(axe) - 1
    largeurs = [0.005 + 0.062 * (1.0 - k / n) ** 0.55 * min(1.0, 0.45 + 4.0 * k / n)
                for k in range(len(axe))]
    return axe, largeurs
