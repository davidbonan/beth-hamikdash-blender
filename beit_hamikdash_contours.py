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


def reduire(contour, k):
    """Le contour à l'échelle `k` autour de l'origine de la figure, le pied."""
    return [(u * k, z * k) for u, z in contour]


def ellipse(u, z, ru, rz, points=32):
    return [(u + ru * math.cos(2 * math.pi * k / points), z + rz * math.sin(2 * math.pi * k / points))
            for k in range(points)]


def corolle(u, z, r, lobes=8):
    """Une fleur épanouie : `lobes` pétales arrondis autour d'un cœur."""
    return [(u + rk * math.cos(a), z + rk * math.sin(a))
            for a, rk in ((a, r * (0.60 + 0.40 * abs(math.cos(lobes * a / 2)) ** 0.65))
                          for a in (2 * math.pi * k / (lobes * 8) for k in range(lobes * 8)))]


def volute(u, z, r, depart=0.0, tours=1.15):
    """La spirale d'épaule ou de hanche des figures d'Orient : un fil qui s'enroule vers
    son centre, à donner à `ruban` — c'est un trait, pas une silhouette."""
    points = 44
    return [(u + r * (1.0 - 0.82 * t) * math.cos(2 * math.pi * tours * t + depart),
             z + r * (1.0 - 0.82 * t) * math.sin(2 * math.pi * tours * t + depart))
            for t in (k / (points - 1) for k in range(points))]


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


# Le keruv est la 'haya de la vision, « וָאֵדַע כִּי כְרוּבִים הֵמָּה » (Ye'hezkel 10:20) : ni
# robe ni corps d'homme, deux ailes qui couvrent le corps, « וּשְׁתַּיִם מְכַסּוֹת אֵת
# גְּוִיֹּתֵיהֶנָה » (1:11), des mains d'homme sous les ailes (1:8), et UNE jambe, « וְרַגְלֵיהֶם
# רֶגֶל יְשָׁרָה » — « נראין כרגל אחת » (Rashi sur Berakhot 10b) —, au pied rond, « רֶגֶל עָגוֹל »
# (Rashi sur 1:7). Les deux autres ailes, levées, sont posées par chaque figure.
# Moitié droite de la gaine des ailes croisées, de l'attache du cou au haut de la jambe.
GAINE_KERUV = symetrique([
    (0.000, 0.850), (0.080, 0.845), (0.135, 0.805), (0.150, 0.700), (0.140, 0.560),
    (0.115, 0.420), (0.085, 0.290), (0.055, 0.190), (0.000, 0.170)])
# La lisière de l'aile du dessus, qui croise la gaine de l'épaule gauche vers la jambe.
CROISURE = ((-0.140, 0.760), (-0.020, 0.560), (0.050, 0.330), (0.040, 0.200))
# Les deux mains posées sur la gaine, l'une au-dessus de l'autre : (u, z, ru, rz).
MAINS = ((-0.050, 0.640, 0.038, 0.030), (0.045, 0.580, 0.038, 0.030))
JAMBE = ((0.0, 0.180), (0.0, 0.060))
LARGEUR_JAMBE = 0.050
SABOT = (0.0, 0.035, 0.036, 0.035)

# La tête : UN SEUL crâne, « וּשְׁנַיִם פָּנִים לַכְּרוּב » (Ye'hezkel 41:18), le profil d'homme
# vers les u négatifs, celui du jeune lion vers les u positifs (41:19) — et AUCUN TRAIT
# dans le profil (§9 de la fiche). Le lion se donne par sa MASSE : front bombé, museau
# court et carré qui avance, mâchoire profonde, crinière qui déborde le crâne en arrière.
# Un crâne à deux bosses sortait en deux têtes accolées, et deux profils d'homme en
# miroir en une tête à deux nez. Du sommet du crâne, dans le sens des aiguilles.
TETE_KERUV = [
    (0.00, 1.00), (0.52, 0.97), (0.98, 0.82), (1.22, 0.52), (1.32, 0.26), (1.58, 0.12),
    (1.62, -0.04), (1.44, -0.12), (1.52, -0.30), (1.32, -0.48), (0.86, -0.63),
    (0.30, -0.75), (0.00, -0.78), (-0.30, -0.75), (-0.80, -0.62), (-1.24, -0.44),
    (-1.36, -0.24), (-1.22, -0.14), (-1.44, -0.02), (-1.20, 0.18), (-1.30, 0.36),
    (-1.06, 0.62), (-0.54, 0.92)]
TETE = (0.0, 0.905, 0.145)   # u, z, taille
# Les mèches de la crinière, dans le repère de la tête : le contour seul ne suffit pas à
# nommer le lion, ce sont elles qui le font lire.
CRINIERE = (((0.30, 0.86), (0.62, 1.02)), ((0.72, 0.74), (1.00, 0.94)),
            ((0.98, 0.54), (1.28, 0.70)), ((1.06, 0.26), (1.34, 0.36)))


def tete_keruv():
    """La tête posée sur la gaine, lissée UNE fois : c'est le nez et le menton de chaque
    profil qui la font lire, trois passes en faisaient une miche."""
    return lisser(poser(TETE_KERUV, *TETE), passes=1)


def meches_de_criniere():
    """Les mèches de la crinière, posées comme la tête : des traits à graver."""
    return [[(TETE[0] + u * TETE[2], TETE[1] + z * TETE[2]) for u, z in meche]
            for meche in CRINIERE]


# L'aile penne par penne : cinq rangs, des rémiges aux petites couvertures, dans le repère
# de la lame (p le long de la nervure, q en travers, positif vers le bord d'attaque) :
# (nombre, p de la première, p de la dernière, q du talon, longueur, avance de la pointe,
# demi-largeur). C'est l'étagement des rangs et la pointe de chaque penne qui font l'aile ;
# une lame rainurée n'en est que l'ombre, et des pennes en travers de la nervure la
# peignent en arête de poisson — elles se couchent vers la pointe.
RANGS_PENNES = ((9, 0.16, 0.92, -0.06, 0.30, 0.30, 0.052),
                (9, 0.13, 0.86, -0.02, 0.23, 0.24, 0.046),
                (8, 0.10, 0.76, 0.03, 0.16, 0.18, 0.040),
                (7, 0.08, 0.62, 0.07, 0.11, 0.13, 0.034),
                (6, 0.06, 0.50, 0.10, 0.08, 0.09, 0.029))


def penne(talon, pointe, demi):
    """Une penne lancéolée, du talon à la pointe : ventrue au tiers, effilée au bout."""
    (p0, q0), (p1, q1) = talon, pointe
    dp, dq = p1 - p0, q1 - q0
    n = math.hypot(dp, dq) or 1.0
    nu, nq = -dq / n, dp / n
    profil = ((0.10, 0.55), (0.34, 1.00), (0.66, 0.92), (0.88, 0.52))
    cote = [(p0 + dp * t + nu * demi * w, q0 + dq * t + nq * demi * w) for t, w in profil]
    revers = [(p0 + dp * t - nu * demi * w, q0 + dq * t - nq * demi * w)
              for t, w in reversed(profil)]
    return lisser([talon] + cote + [pointe] + revers, passes=1)


def plumage():
    """Les pennes d'une aile, dans le repère de la lame : (contour, rang), du rang le plus
    bas — les rémiges — au plus haut. Les rémiges s'allongent vers la pointe de l'aile,
    les couvertures gardent leur taille."""
    plumes = []
    for rang, (nombre, debut, fin, q, longueur, avance, demi) in enumerate(RANGS_PENNES):
        for n in range(nombre):
            t = n / (nombre - 1)
            part = 0.55 + 0.45 * t if rang < 2 else 1.0
            p = debut + (fin - debut) * t
            plumes.append((penne((p, q), (p + avance, q - longueur * part), demi), rang))
    return plumes


# Les ailes hautes, (u, z) de l'attache, inclinaison sur la verticale, taille. Aux parois
# comme sur un vantail elles se lèvent au-dessus de la tête — à peine ouvertes aux parois,
# droites sur un vantail et sur le rideau. Tendues à l'horizontale, elles sortaient en aile
# d'Isis quel que soit le dessin des plumes ; la jonction des pointes d'un keruv à l'autre
# au-dessus de la timora (« חֹבְרֹת אִישׁ אֶל אָחִיו », Ye'hezkel 1:9) est abandonnée avec elles.
AILES_HAUTES = ((0.130, 0.745), 26, 0.52)
AILES_DRESSEES = ((0.09, 0.78), 12, 0.42)
# Les ailes levées montent au-dessus de la tête, jusqu'à 1,25 : le keruv est dessiné
# réduit d'autant, pour que la pointe de ses ailes tienne à 1.
REDUCTION_HAUTE = 0.78
REDUCTION_DRESSE = 0.80


# --- Le lion : « וּפְנֵי כְפִיר » (Ye'hezkel 41:19). -----------------------------------------

# La seconde face du keruv, et le lion du revers d'un maassé 'hoshev (Rashi sur Yoma 72b).
# Sa forme est celle du SCEAU DE SHEMA, serviteur de Yarovam (Megiddo, VIIIe s.) — le lion
# royal hébreu —, et non celle du lion héraldique, qui est européen et de mille ans plus
# tard : de profil, rugissant gueule grande ouverte, poitrail profond, flanc creusé,
# croupe massive, la queue dressée en S au-dessus du dos. Il regarde vers les u croissants.
#
# Les tracés suivent la convention de `cadrer` (beit_hamikdash_carte.py) : les pattes en
# z = 0, le sommet du toupet en z = 1, la boîte englobante centrée sur u = 0 — le guide
# montré au modèle cadre alors la figure exactement comme le tissage sera relu.

# Les proportions valent le dessin : hauteur au garrot 0,69 ; profondeur du corps 0,35 ;
# pattes 0,35 — une patte au moins aussi longue que le corps n'est profond, sinon c'est un
# basset. Corps long de 1,46 fois la hauteur au garrot : l'allongement du Fer, pas plus.
# Dos creusé, croupe haute, brechet descendu, flanc remonté devant la cuisse : c'est ce
# creux et cette masse arrière qui font le fauve.
LION_CORPS = ((0.252, 0.690), (0.055, 0.676), (-0.162, 0.668), (-0.369, 0.686),
              (-0.526, 0.676), (-0.625, 0.621), (-0.659, 0.537), (-0.635, 0.455),
              (-0.556, 0.402), (-0.438, 0.433), (-0.255, 0.402), (-0.083, 0.369),
              (0.084, 0.343), (0.242, 0.357), (0.323, 0.422), (0.348, 0.512),
              (0.333, 0.609), (0.291, 0.678))
# Le crâne et la mâchoire SUPÉRIEURE d'un seul tenant : arcade, stop, chanfrein court,
# truffe, babine retroussée sur la canine, puis le palais qui recule jusqu'à la
# commissure. Tête COURTE et profonde — 0,34 de long pour 0,39 de haut gueule ouverte ;
# un museau long sort en tête de cheval.
LION_TETE = ((0.429, 0.749), (0.493, 0.793), (0.572, 0.796), (0.636, 0.770),
             (0.664, 0.731), (0.705, 0.711), (0.745, 0.690), (0.762, 0.658),
             (0.756, 0.627), (0.720, 0.609), (0.685, 0.607), (0.672, 0.564),
             (0.652, 0.605), (0.575, 0.619), (0.493, 0.642), (0.441, 0.690))
# La mâchoire inférieure est une pièce à part : c'est l'ÉCART entre les deux, et lui seul,
# qui ouvre la gueule. Un seul contour n'aurait su que la fermer.
LION_MACHOIRE = ((0.488, 0.638), (0.557, 0.567), (0.646, 0.527), (0.717, 0.520),
                 (0.729, 0.485), (0.676, 0.465), (0.587, 0.467), (0.508, 0.498),
                 (0.454, 0.554))
# Le fond de la gueule, posé sous les deux mâchoires : ce qui reste à découvert entre
# elles est le rouge du rugissement.
LION_GUEULE = ((0.479, 0.650), (0.705, 0.611), (0.754, 0.552), (0.695, 0.471),
               (0.469, 0.537))
# L'oreille a sa base DANS le crâne, qui la recouvre : posée dessus, elle flotte en boule.
LION_OREILLE = ((0.487, 0.746), (0.499, 0.834), (0.560, 0.848), (0.570, 0.775))
# Le collier de mèches, assez grand pour ceindre le crâne et retomber sur le poitrail :
# une crinière qui ne mord pas sur la tête se lit en fleur posée sur le cou.
LION_CRINIERE = (0.405, 0.655, 0.271)
# Les deux rangs de mèches lus en creux sur la crinière — c'est l'étagement qui la fait
# lire, une masse pleine ne dit rien.
LION_RANGS = (((0.324, 0.796), (0.242, 0.655), (0.324, 0.514), (0.460, 0.502)),
              ((0.293, 0.847), (0.183, 0.655), (0.293, 0.463), (0.498, 0.454)))
LION_QUEUE = ((-0.610, 0.611), (-0.706, 0.690), (-0.733, 0.808), (-0.664, 0.899),
              (-0.556, 0.926))
LARGEURS_QUEUE = (0.0512, 0.0374, 0.0296, 0.0236, 0.0187)
# Le toupet MORD sur la fin de la queue : détaché, il se lisait en ballon au bout d'un fil.
LION_HOUPPE = (-0.523, 0.934, 0.075)
# Les quatre pattes, chacune à son angle : (axe de l'os, demi-largeurs). L'antérieure du
# côté vu est avancée, la postérieure du même côté pousse, jarret fléchi ; les deux du
# côté caché passent derrière le corps. Quatre copies d'un même tube droit se lisaient en
# pieds de table.
LION_PATTES_VUES = ((((0.208, 0.552), (0.240, 0.355), (0.291, 0.197), (0.343, 0.049)),
                     (0.0837, 0.0512, 0.0394, 0.0374)),
                    (((-0.438, 0.537), (-0.369, 0.360), (-0.477, 0.202), (-0.416, 0.049)),
                     (0.1064, 0.0631, 0.0414, 0.0374)))
LION_PATTES_CACHEES = ((((0.158, 0.542), (0.134, 0.350), (0.109, 0.192), (0.086, 0.049)),
                        (0.0768, 0.0473, 0.0365, 0.0345)),
                       (((-0.487, 0.532), (-0.438, 0.355), (-0.556, 0.212), (-0.587, 0.049)),
                        (0.0985, 0.0571, 0.0384, 0.0345)))
# Le pied, posé au bout de l'axe d'une patte : il porte à plat et déborde vers l'avant.
LION_PIED = ((-0.045, 0.057), (0.054, 0.057), (0.063, 0.020), (0.055, 0.0), (-0.039, 0.0),
             (-0.051, 0.024))
# Le dessin intérieur, en fils du fond : trois côtes COURTES et franchement cintrées —
# longues et droites, elles sortaient en barreaux de zèbre —, le pli de l'aine, et les
# spirales d'épaule et de hanche des lions d'Orient. Un corps laissé vide ramène le
# modèle à son gentil animal.
LION_COTES = (((0.168, 0.638), (0.214, 0.552), (0.181, 0.465)),
              ((0.055, 0.642), (0.102, 0.554), (0.067, 0.463)),
              ((-0.058, 0.640), (-0.012, 0.550), (-0.046, 0.457)))
LION_FLANC = ((-0.339, 0.670), (-0.308, 0.542), (-0.369, 0.438))
# L'épaule se dessine JUSTE derrière le bord de la crinière : dessous, la spirale se
# serait posée sur les mèches.
LION_VOLUTE_EPAULE = (0.139, 0.463, 0.069)
LION_VOLUTE_HANCHE = (-0.467, 0.532, 0.097)
LION_SOURCIL = ((0.607, 0.778), (0.652, 0.767), (0.668, 0.735))
LION_NASEAU = ((0.741, 0.668), (0.756, 0.658))
LION_OEIL = (0.630, 0.718, 0.024, 0.016)


def ruban_effile(axe, largeurs):
    """Le contour fermé d'un trait ARRONDI qui s'effile : `courbe` multiplie les points de
    l'axe, et les demi-largeurs données aux points de départ s'interpolent le long de lui.
    Passer les mêmes largeurs à `ruban` n'en aurait couvert que les premiers points —
    `zip` s'arrête au plus court — et le trait se serait arrêté là."""
    fil = courbe(axe)
    dernier, portees = len(fil) - 1, len(largeurs) - 1
    demi = []
    for k in range(len(fil)):
        t = k / dernier * portees
        i = min(int(t), portees - 1)
        demi.append(largeurs[i] + (largeurs[i + 1] - largeurs[i]) * (t - i))
    return ruban(fil, demi)


def pied(axe):
    """Le pied posé au bout de l'axe d'une patte, à plat sur le sol."""
    return [(axe[-1][0] + du, dz) for du, dz in LION_PIED]


def criniere(u, z, r, meches=16, creux=0.62):
    """Le collier de mèches du lion : des POINTES, non les pétales d'une corolle. La
    crinière des lions d'Orient est un rang de mèches qui se couchent toutes du même
    côté, plus longues sous la gorge et le poitrail que sur le crâne. Sert aussi au
    toupet de la queue, avec un `creux` plus haut : entaillé comme la crinière, il
    sortait en étoile plantée sur un fil."""
    couche = math.pi / meches * 0.6        # la mèche se couche, sans mordre sur la suivante
    contour = []
    for k in range(meches):
        a = 2 * math.pi * k / meches
        pointe = r * (1.0 + 0.18 * max(0.0, -math.sin(a)))
        contour.append((u + r * creux * math.cos(a - math.pi / meches),
                        z + r * creux * math.sin(a - math.pi / meches)))
        contour.append((u + pointe * math.cos(a + couche), z + pointe * math.sin(a + couche)))
    return contour


# --- La timora : le dattier, tel que la tradition le lit et le frappe. -----------------

# « וְתִמֹרֹת » (Melakhim I 6:29) : Rashi et Radak lisent דקלים, des palmiers-dattiers, et
# la fiche (§8c-bis) en fixe sept palmes. Son image juive est celle des monnaies de
# Bar Kokhba : un fût droit à écailles, sept palmes — celle du milieu dressée, les
# paires suivantes qui ploient en arc —, et deux régimes de dattes qui pendent de la
# couronne, de part et d'autre du fût. Ni volutes ni collier : c'était la palmette
# assyrienne, étrangère à cette tradition.
FUT = 0.56
TRONC = symetrique([(0.0, FUT), (0.045, FUT), (0.052, 0.10), (0.065, 0.035), (0.09, 0.0), (0.0, 0.0)])
ECAILLE = 0.045                          # pas des cicatrices du fût
COURONNE = (0.0, FUT - 0.01)
# (inclinaison sur la verticale, longueur, retombée) : la palme du milieu se dresse, les
# paires suivantes ploient de plus en plus, la dernière retombe sous l'horizontale.
PALMES = ((0, 0.42, 0.0), (28, 0.42, 0.18), (60, 0.40, 0.42), (95, 0.34, 0.55))
# La foliole : son écart le long de la nervure, ce qui reste de la demi-largeur au creux
# entre deux, ce dont sa pointe avance, et la demi-largeur du RACHIS que le creux ne
# descend jamais sous. Trois contraintes s'y croisent. La pointe avance MOINS que l'écart :
# le remplissage est pair-impair (beit_hamikdash_carte.py), deux folioles qui se
# croiseraient perceraient un trou dans la palme. La dent monte PLUS haut qu'elle n'est
# large, sinon la découpe sort en merlons de créneau. Et le creux s'arrête au rachis :
# entaillée jusqu'à la nervure, la palme se défait en fanions détachés.
PAS_FOLIOLE, ENTAILLE, COUCHE_FOLIOLE, RACHIS = 0.052, 0.18, 0.90, 0.016
# Le régime pend de la couronne en ÉPIS : (écart de la pointe, longueur) de chacun, et
# les demi-axes d'une datte. Neuf dattes en pyramide se lisaient en grappe de raisin ;
# ce qui fait un régime de dattier, c'est la retombée de rachilles chargées.
ATTACHE_REGIME = (0.085, FUT - 0.05)
EPIS = ((-0.030, 0.185), (0.022, 0.225), (0.070, 0.190))
DATTE = (0.012, 0.019)


def palme(inclinaison, longueur, retombee):
    """(axe, demi-largeurs) d'une palme : la nervure, depuis la couronne, et la portée des
    folioles le long d'elle — large à la base, effilée à la pointe."""
    a = math.radians(inclinaison)
    p0 = COURONNE
    p1 = (p0[0] + 0.5 * longueur * math.sin(a), p0[1] + 0.5 * longueur * math.cos(a))
    p2 = (p0[0] + longueur * math.sin(a), p0[1] + longueur * (math.cos(a) - retombee))
    axe = bezier(p0, p1, p2, 32)
    return axe, largeurs_palme(len(axe))


def largeurs_palme(points):
    """La portée des folioles en chacun des `points` d'une nervure, de la base à la
    pointe : large à la base, effilée à la pointe."""
    n = points - 1
    return [0.005 + 0.070 * (1.0 - k / n) ** 0.55 * min(1.0, 0.45 + 4.0 * k / n)
            for k in range(points)]


def folioles(axe, largeurs):
    """Le contour fermé d'une palme DÉCOUPÉE : une dent par foliole, de part et d'autre de
    la nervure. C'est la découpe, et rien d'autre, qui fait lire une palme — une lentille
    lisse, si juste soit son arc, se lit en pétale de fleur."""
    arcs = [0.0]
    for (u0, z0), (u1, z1) in zip(axe, axe[1:]):
        arcs.append(arcs[-1] + math.hypot(u1 - u0, z1 - z0))
    dents = [k for k in range(1, len(axe) - 1)
             if int(arcs[k] / PAS_FOLIOLE) > int(arcs[k - 1] / PAS_FOLIOLE)]
    n = normales(axe)
    bords = []
    for cote in (1, -1):
        bord = [axe[0]]
        for k in dents:
            (u, z), (nu, nz), w = axe[k], n[k], largeurs[k]
            tu, tz = nz, -nu                                  # la tangente : la normale d'un quart
            avance = PAS_FOLIOLE * COUCHE_FOLIOLE
            creux = min(w, max(w * ENTAILLE, RACHIS))
            bord.append((u + cote * nu * creux, z + cote * nz * creux))
            bord.append((u + cote * nu * w + tu * avance, z + cote * nz * w + tz * avance))
        bord.append(axe[-1])
        bords.append(bord)
    return bords[0] + bords[1][::-1]


def chevrons():
    """Les cicatrices des pétioles coupés qui montent le long du fût, en chevrons empilés.
    Le treillis de losanges d'avant se lisait en écaille d'ananas."""
    demi, creux = 0.046, 0.030
    return [[(-demi, z + creux), (0.0, z), (demi, z + creux)]
            for z in (ECAILLE * k + 0.03 for k in range(int((FUT - 0.08) / ECAILLE) + 1))]


def epi(ecart, longueur):
    """(rachille, dattes) d'un épi du régime, du côté droit du fût : le fil qui pend de
    l'attache, et les dattes qui l'alourdissent, une de chaque côté tour à tour."""
    u0, z0 = ATTACHE_REGIME
    fil = bezier((u0, z0), (u0 + ecart * 0.3, z0 - longueur * 0.6),
                 (u0 + ecart, z0 - longueur), 16)
    dattes = [(u + (-1) ** k * DATTE[0] * 0.75, z) for k, (u, z) in enumerate(fil[5::4])]
    return fil, dattes
