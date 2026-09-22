"""Les contours des figures du Bayit : ce qui se dessine à plat avant de sortir d'une paroi.

Une palme, un bouton, un cordon se donnent en quelques points de construction, dans le
repère (u, z) de la figure et à l'échelle de sa hauteur ; ce qui en fait une silhouette
est le lissage de Chaikin, qui coupe chaque angle en deux jusqu'à ce que le contour
soit une courbe. Dix points de construction en font quatre-vingts au troisième passage.

Ni bpy ni numpy : `beit_hamikdash_gravures.py` (relief taillé dans l'or) le lit.
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


def ellipse(u, z, ru, rz, points=32):
    return [(u + ru * math.cos(2 * math.pi * k / points), z + rz * math.sin(2 * math.pi * k / points))
            for k in range(points)]


def corolle(u, z, r, lobes=8):
    """Une fleur épanouie : `lobes` pétales arrondis autour d'un cœur."""
    return [(u + rk * math.cos(a), z + rk * math.sin(a))
            for a, rk in ((a, r * (0.60 + 0.40 * abs(math.cos(lobes * a / 2)) ** 0.65))
                          for a in (2 * math.pi * k / (lobes * 8) for k in range(lobes * 8)))]


# --- La palme : la foliole découpée. ---------------------------------------------------

# La foliole : son écart le long de la nervure, ce qui reste de la demi-largeur au creux
# entre deux, ce dont sa pointe avance, et la demi-largeur du RACHIS que le creux ne
# descend jamais sous. Trois contraintes s'y croisent. La pointe avance MOINS que l'écart :
# le remplissage est pair-impair (beit_hamikdash_carte.py), deux folioles qui se
# croiseraient perceraient un trou dans la palme. La dent monte PLUS haut qu'elle n'est
# large, sinon la découpe sort en merlons de créneau. Et le creux s'arrête au rachis :
# entaillée jusqu'à la nervure, la palme se défait en fanions détachés.
PAS_FOLIOLE, ENTAILLE, COUCHE_FOLIOLE, RACHIS = 0.052, 0.18, 0.90, 0.016


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


# --- Le bouton et le cordon : « מִקְלַעַת פְּקָעִים וּפְטוּרֵי צִצִּים » (Melakhim I 6:18). ------

# Le verset du lambris de cèdre donne DEUX choses que celui des parois (6:29) ne
# répète pas, et que le champ ne montrait pas : des פְּקָעִים et une מִקְלַעַת.
# פְּקָעִים : « כְּמִין כַּפְתּוֹרִים » (Rashi), « חֵיזוּ בֵיעִין » (Targum Yonatan), « צוּרוֹת
# פְּקוּעוֹת שָׂדֶה » (Radak) — et Ralbag les dessine : « בִּיצִים שֶׁשְּׁנֵי רָאשֵׁיהֶם חַדִּים »,
# le bouton AVANT qu'il s'ouvre, qu'il rattache aux גְּבִיעִים כַּפְתֹּרִים וּפְרָחִים de la
# Menora — « וְלַסִּבָּה בְּעֵינָהּ שֶׁהָיוּ אֵלּוּ הַצִּיּוּרִים בַּמְּנוֹרָה הָיוּ בְּזֶה הַמָּקוֹם ».
# C'est le cycle, et non une corolle répétée, que le bandeau porte donc.
def bouton(u, z, r):
    """Le bouton fermé : un œuf effilé aux deux bouts, ventru sous son milieu, sur un
    calice de trois sépales courts. `r` est sa demi-largeur ; il monte à 2,6 r."""
    oeuf = lisser(symetrique([(0.00, 2.60), (0.30, 2.16), (0.62, 1.62), (0.86, 1.10),
                              (0.92, 0.70), (0.74, 0.30), (0.38, 0.08), (0.00, 0.00)]), passes=2)
    calice = lisser(symetrique([(0.00, 0.46), (0.52, 0.34), (0.86, -0.02), (0.40, -0.22),
                                (0.00, -0.26)]), passes=2)
    return ([(u + du * r, z + dz * r) for du, dz in oeuf],
            [(u + du * r, z + dz * r) for du, dz in calice])


# מִקְלַעַת / « קְלִיעַן » (Targum 6:29), « וַחֲבָלִים » (Rashi 6:29), « אָטוּנִין » : le champ est
# TRESSÉ, et ce sont ces cordes qui le tiennent. Elles se dessinent ici et ne passent
# par aucun modèle : une torsade est une figure géométrique, que des dômes disent
# exactement — c'est le vivant (une penne, une foliole) qui demandait la taille.
def torsade(torsades, axe=0.5, epaisseur=0.86, penche=1.15, recouvrement=1.55):
    """Les brins d'un cordon horizontal traversant le carré unité, de u = 0 à u = 1, sur
    `axe` : `torsades` mèches en fuseau, chacune couchée de `penche` fois sa hauteur, qui
    déborde de `recouvrement` sur sa voisine. C'est ce chevauchement, pris dans l'ordre,
    qui fait lire une corde tordue plutôt qu'une file de grains — et c'est la PENTE de la
    mèche qui fait la torsion : droites, les fuseaux sortaient en barreaux.

    Le cordon est PÉRIODIQUE de pas 1/`torsades` et se referme donc sur le carré : deux
    tuiles posées bout à bout n'ont pas de couture — c'est pour ça qu'il se dessine ici au
    lieu de se faire tailler. Les mèches débordent des deux bords, et s'y retrouvent.
    """
    pas = 1.0 / torsades
    demi = epaisseur / 2
    largeur = pas * recouvrement / 2
    meches = []
    for k in range(-2, torsades + 2):
        u = (k + 0.5) * pas
        bas, haut = (u - penche * demi, axe - demi), (u + penche * demi, axe + demi)
        meches.append(lisser(_fuseau(bas, haut, largeur), passes=2))
    return meches


def _fuseau(depart, arrivee, demi):
    """Le contour d'une mèche : une lentille du départ à l'arrivée, la plus large au
    milieu, effilée aux deux bouts."""
    du, dz = arrivee[0] - depart[0], arrivee[1] - depart[1]
    n = math.hypot(du, dz) or 1.0
    nu, nz = -dz / n, du / n
    profil = [(t, demi * math.sin(math.pi * t) ** 0.62)
              for t in (k / 12 for k in range(1, 12))]
    cote = [(depart[0] + du * t + nu * w, depart[1] + dz * t + nz * w) for t, w in profil]
    revers = [(depart[0] + du * t - nu * w, depart[1] + dz * t - nz * w)
              for t, w in reversed(profil)]
    return [depart] + cote + [arrivee] + revers


def guilloche(brins, points=144, amplitude=0.27, croise=2):
    """Les axes des brins d'une tresse traversant le carré unité : `brins` sinusoïdes
    décalées, qui se croisent `croise` fois. Un brin passe DESSUS là où il monte : les
    dessiner dans l'ordre des hauteurs à chaque croisement est ce qui les entrelace,
    une superposition franche les empilerait."""
    return [[(k / (points - 1),
              0.5 + amplitude * math.sin(2 * math.pi * croise * k / (points - 1)
                                         + 2 * math.pi * b / brins))
             for k in range(points)]
            for b in range(brins)]
