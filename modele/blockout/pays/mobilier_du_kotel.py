import math

from ..primitives.parametres import AMA
from ..primitives.matieres import (MAT_ACIER_BLANC, MAT_BETON, MAT_BOIS_DU_PONT, MAT_BOUGAINVILLEE, MAT_CAPRIER, MAT_CAPRIER_SEC,
                                   MAT_CHENE, MAT_DRAPEAU_BLANC, MAT_DRAPEAU_BLEU, MAT_FER, MAT_FER_BRUN, MAT_FEUILLAGE,
                                   MAT_INOX, MAT_OR, MAT_PALME, MAT_PIERRE, MAT_PLASTIQUE, MAT_PORTIQUE,
                                   MAT_TABLE_DE_PRIERE, MAT_TOILE, MAT_TRONC, MAT_VELOURS, MAT_VERRE_DE_LAMPE)
from ..primitives.volumes import FACES_BOITE, alea, plage, sphere
from .calage import HARAM, KOTEL, Z_PLACE_HAUTE, Z_PLACE_KOTEL, _plus_proche_sur_l_anneau, vers_scene
from .facades_du_kotel import (ANGLE_DE_LA_FONDATION, BOUT_DE_LA_FONDATION, H_FONDATION, H_MAKHKAMA, H_PAVILLON,
                               RETRAIT_DU_PAVILLON, garde_corps)
from .parc_de_police import voitures_de_police
from .place_du_kotel import (BRECHE_DES_FEMMES, BRECHE_DES_HOMMES, MEHITSA, MURET_DE_PRIERE, PONT_MAGHREBINS, _cap,
                             _dans_l_aire_de_priere, _devant, _fut, _pave, _point_de_wilson, _poser, _poutre, _pyramide,
                             _trace_osm, _vers_l_aire_de_priere)
from .second_oeuvre import repere_de_projecteur


# Ce qui meuble la place et que les photos montrent (Wikimedia Commons, 2019–2025), sans
# qu'OSM en dise la place : leur nombre et leur position sont des CHOIX.


def _ruban(points, largeurs, face):
    """Une lanière qui suit `points`, large de `largeurs` à chacun, tournée vers `face`."""
    verts, faces = [], []
    for k, (p, largeur) in enumerate(zip(points, largeurs)):
        a, b = points[max(k - 1, 0)], points[min(k + 1, len(points) - 1)]
        d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        w = (d[1] * face[2] - d[2] * face[1], d[2] * face[0] - d[0] * face[2], d[0] * face[1] - d[1] * face[0])
        norme = math.sqrt(sum(c * c for c in w)) or 1.0
        verts += [tuple(p[i] - w[i] / norme * largeur / 2 for i in range(3)),
                  tuple(p[i] + w[i] / norme * largeur / 2 for i in range(3))]
    for k in range(len(points) - 1):
        faces.append([2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2])
    return verts, faces


def _rameau(pied, vers, travers, longueur, graine):
    """Un rameau qui sort du joint, part de côté et retombe."""
    de_cote, elan = 1.6 * (alea(graine, 1) - 0.5), 0.15 + 0.5 * alea(graine, 2)
    points = []
    for k in range(5):
        t = k / 4
        avance = longueur * (0.12 + 0.22 * t)
        points.append((pied[0] + travers[0] * de_cote * longueur * t + vers[0] * avance,
                       pied[1] + travers[1] * de_cote * longueur * t + vers[1] * avance,
                       pied[2] + longueur * (elan * t - (0.55 + elan) * t * t)))
    largeur = longueur * (0.035 + 0.03 * alea(graine, 3))
    return _ruban(points, [largeur * f for f in (0.35, 1.0, 0.9, 0.6, 0.15)], (*vers, 0.0))


def _touffe(centre, z, rayon, vers, graine, cotes=7, rangs=5):
    """Un buisson qui pend d'un joint : une goutte aplatie contre le mur, large en haut, effilée en bas."""
    cx, cy = centre
    travers = (-vers[1], vers[0])
    anneaux = []
    for r in range(1, rangs):
        f = r / rangs
        large, epais, haut = rayon * math.sin(math.pi * f) ** 0.6 * (1.15 - 0.6 * f), rayon * 0.35 * math.sin(math.pi * f), z - rayon * 2.2 * f
        anneaux.append([(cx + travers[0] * large * e * math.cos(a) + vers[0] * epais * (1 + math.sin(a)),
                         cy + travers[1] * large * e * math.cos(a) + vers[1] * epais * (1 + math.sin(a)), haut - rayon * 0.5 * (e - 0.8))
                        for a, e in ((2 * math.pi * i / cotes, 0.55 + 0.9 * alea(graine, 10 * r + i)) for i in range(cotes))])
    verts = [(cx, cy, z)] + [p for anneau in anneaux for p in anneau] + [(cx, cy, z - rayon * 2.2)]
    faces = [[0, 1 + i, 1 + (i + 1) % cotes] for i in range(cotes)]
    for r in range(len(anneaux) - 1):
        b = 1 + r * cotes
        faces += [[b + i, b + cotes + i, b + cotes + (i + 1) % cotes, b + (i + 1) % cotes] for i in range(cotes)]
    b, bout = 1 + (len(anneaux) - 1) * cotes, len(verts) - 1
    return verts, faces + [[b + i, bout, b + (i + 1) % cotes] for i in range(cotes)]


def capriers_du_kotel(touffes=46, brins=90):
    """Les câpriers, jusquiames et gueules-de-loup qui poussent dans les joints du Kotel
    (Wikipedia, « Western Wall ») : de grosses touffes — un cœur broussailleux d'où des rameaux retombent —, surtout
    entre la cinquième et la douzième assise, et partout des brins isolés. Les touffes de
    l'an passé restent sèches à côté des vertes."""
    nord, sud = KOTEL[0], KOTEL[2]
    cap = _cap(nord, sud)
    cote = _vers_l_aire_de_priere(_devant(nord, cap, 10 / AMA), cap)
    vers, travers = (-math.sin(cap) * cote, math.cos(cap) * cote), (math.cos(cap), math.sin(cap))
    longueur_du_mur = math.dist(nord, sud) * AMA - 3
    verts, secs = [], []
    for k in range(touffes + brins):
        nom = f"Kotel_caprier_{k}"
        grosse = k < touffes
        pied = _plus_proche_sur_l_anneau(_devant(nord, cap, (1.5 + longueur_du_mur * alea(nom)) / AMA), HARAM)
        z = Z_PLACE_KOTEL + ((3.2 + 9.5 * alea(nom, 1) ** 1.4) if grosse else (1.5 + 15 * alea(nom, 1))) / AMA
        taille = ((0.5 + 1.1 * alea(nom, 2) ** 2) if grosse else (0.2 + 0.25 * alea(nom, 2))) / AMA
        rameaux = [_rameau((*pied, z), vers, travers, taille * (0.6 + 0.8 * alea(nom, 20 + i)), f"{nom}_{i}")
                   for i in range(int(26 + 16 * alea(nom, 3)) if grosse else 5)]
        if grosse:
            rameaux.append(_touffe(pied, z + taille * 0.15, taille * 0.5, vers, nom))
        (secs if alea(nom, 4) < 0.45 else verts).extend(rameaux)
    _poser("Kotel_capriers", verts, MAT_CAPRIER())
    _poser("Kotel_capriers_secs", secs, MAT_CAPRIER_SEC())


def _table_de_priere(p, cap, z):
    """La table roulante de l'aire de prière, sous sa nappe : (nappe, chariot d'acier)."""
    nappe = [_pave(p, cap, 0.76 / AMA, 1.16 / AMA, z + 0.78 / AMA, z + 1.03 / AMA)]
    chariot = [_pave(_devant(p, cap, sa * 0.3 / AMA, st * 0.5 / AMA), cap, 0.04 / AMA, 0.04 / AMA, z + 0.1 / AMA, z + 0.98 / AMA)
               for sa in (-1, 1) for st in (-1, 1)]
    chariot += [_pave(p, cap, 0.64 / AMA, 1.04 / AMA, z + 0.3 / AMA, z + 0.33 / AMA)]
    chariot += [_pave(_devant(p, cap, sa * 0.3 / AMA, st * 0.5 / AMA), cap, 0.1 / AMA, 0.04 / AMA, z, z + 0.1 / AMA)
                for sa in (-1, 1) for st in (-1, 1)]
    return nappe, chariot


def _shtender(p, cap, z):
    """Le pupitre où l'on pose son siddour, tourné vers le cap : (plateau incliné, pied)."""
    plateau = (_poutre(_devant(p, cap, -0.2 / AMA), _devant(p, cap, 0.2 / AMA), z + 1.0 / AMA, z + 1.14 / AMA,
                       0.28 / AMA, -0.28 / AMA, 0.03 / AMA), FACES_BOITE)
    return plateau, [_pave(p, cap, 0.04 / AMA, 0.04 / AMA, z, z + 1.05 / AMA), _pave(p, cap, 0.4 / AMA, 0.4 / AMA, z, z + 0.03 / AMA)]


def _aron(p, cap, cote, z):
    """Un aron de bois sombre contre le Kotel, ses portes sous une parokhet de velours brodée
    d'or, un fronton à degrés : (menuiserie, velours, or)."""
    bois = [_pave(p, cap, 1.8 / AMA, 0.95 / AMA, z, z + 0.3 / AMA), _pave(p, cap, 1.55 / AMA, 0.8 / AMA, z + 0.3 / AMA, z + 2.5 / AMA),
            _pave(p, cap, 1.85 / AMA, 1.0 / AMA, z + 2.5 / AMA, z + 2.68 / AMA), _pave(p, cap, 1.2 / AMA, 0.5 / AMA, z + 2.68 / AMA, z + 2.95 / AMA),
            _pave(p, cap, 0.6 / AMA, 0.3 / AMA, z + 2.95 / AMA, z + 3.15 / AMA)]
    bois += [_pave(_devant(p, cap, t * 0.72 / AMA, cote * 0.4 / AMA), cap, 0.12 / AMA, 0.12 / AMA, z + 0.3 / AMA, z + 2.5 / AMA) for t in (-1, 1)]
    devant = _devant(p, cap, 0, cote * 0.41 / AMA)
    velours = [_pave(devant, cap, 1.2 / AMA, 0.03 / AMA, z + 0.55 / AMA, z + 2.3 / AMA)]
    bord = _devant(p, cap, 0, cote * 0.425 / AMA)
    dorure = [_pave(bord, cap, 1.2 / AMA, 0.02 / AMA, z + h / AMA, z + (h + 0.05) / AMA) for h in (0.55, 2.25)]
    dorure += [_pave(_devant(bord, cap, t * 0.58 / AMA), cap, 0.05 / AMA, 0.02 / AMA, z + 0.55 / AMA, z + 2.3 / AMA) for t in (-1, 1)]
    dorure += [_pave(bord, cap, 0.5 / AMA, 0.02 / AMA, z + 1.5 / AMA, z + 1.9 / AMA),
               _pave(_devant(p, cap, 0, cote * 0.26 / AMA), cap, 0.9 / AMA, 0.02 / AMA, z + 2.72 / AMA, z + 2.9 / AMA)]
    return bois, velours, dorure


def _parasol(p, z, ouvert, tourne):
    """(toile, mât et lest)."""
    toile = (_pyramide(p, z + 2.3 / AMA, z + 2.95 / AMA, 2.3 / AMA, 4, tourne) if ouvert
             else _pyramide(p, z + 0.9 / AMA, z + 3.0 / AMA, 0.2 / AMA, 6))
    return toile, [_fut(p, z, z + 3.0 / AMA, 0.03 / AMA, 6), _pave(p, tourne, 0.7 / AMA, 0.7 / AMA, z, z + 0.12 / AMA)]


def _pile_de_chaises(p, cap, z, combien):
    assise = 0.45 / AMA
    pile = [_pave(_devant(p, cap, sa * assise * 0.42, st * assise * 0.42), cap, 0.03 / AMA, 0.03 / AMA, z, z + 0.42 / AMA)
            for sa in (-1, 1) for st in (-1, 1)]
    for k in range(combien):
        haut = z + (0.42 + 0.07 * k) / AMA
        pile += [_pave(_devant(p, cap, 0.012 * k / AMA), cap, assise, assise, haut, haut + 0.04 / AMA),
                 _pave(_devant(p, cap, -assise / 2 + 0.012 * k / AMA), cap, 0.04 / AMA, assise, haut + 0.04 / AMA, haut + 0.44 / AMA)]
    return pile


def mobilier_de_priere():
    """Ce que les photos montrent dans l'aire de prière : deux arons contre le Kotel, des tables
    roulantes sous leur nappe brun-rouge, des shtenders, des parasols blancs — ouverts près du
    mur et le long du muret, ficelés en rang le long de la mehitsa du côté des femmes — et des
    piles de chaises au pied de la Ma'hkama."""
    nord, sud = KOTEL[0], KOTEL[1]
    cap = _cap(nord, sud)
    cote = _vers_l_aire_de_priere(_devant(nord, cap, 10 / AMA), cap)
    z = Z_PLACE_KOTEL
    bois, velours, dorure = [], [], []
    for s in (14, 30):
        b, v, d = _aron(_devant(nord, cap, s / AMA, cote * 1.6 / AMA), cap, cote, z)
        bois, velours, dorure = bois + b, velours + v, dorure + d
    nappes, chariots, pupitres, pieds = [], [], [], []
    for k in range(30):
        nom = f"Kotel_place_table_{k}"
        p = _devant(nord, cap, (3 + 34 * alea(nom)) / AMA, cote * (4 + 24 * alea(nom, 1)) / AMA)
        if _dans_l_aire_de_priere(p):
            nappe, chariot = _table_de_priere(p, cap + math.pi / 2 + 0.5 * (alea(nom, 2) - 0.5), z)
            nappes, chariots = nappes + nappe, chariots + chariot
    for k in range(60):
        nom = f"Kotel_place_shtender_{k}"
        p = _devant(nord, cap, (2 + 50 * alea(nom)) / AMA, cote * (2.5 + 22 * alea(nom, 1) ** 1.5) / AMA)
        if _dans_l_aire_de_priere(p):
            plateau, pied = _shtender(p, cap + cote * math.pi / 2 + 0.6 * (alea(nom, 2) - 0.5), z)
            pupitres.append(plateau)
            pieds += pied
    _poser("Kotel_place_arons", bois + pupitres, MAT_CHENE())
    _poser("Kotel_place_arons_parokhet", velours, MAT_VELOURS())
    _poser("Kotel_place_arons_dorure", dorure, MAT_OR())
    _poser("Kotel_place_tables", nappes, MAT_TABLE_DE_PRIERE())
    _poser("Kotel_place_tables_pieds", chariots + pieds, MAT_INOX())

    toiles, mats = [], []
    muret = _trace_osm(MURET_DE_PRIERE)[2:4]
    cap_muret = _cap(*muret)
    vers_l_aire = _vers_l_aire_de_priere(_devant(muret[0], cap_muret, math.dist(*muret) / 2), cap_muret)
    parasols = [(_devant(muret[0], cap_muret, s, vers_l_aire * 3 / AMA), k % 3 != 2, cap_muret + math.pi / 4)
                for k, s in enumerate(plage(2.5 / AMA, math.dist(*muret) - 2 / AMA, 3.6 / AMA))]
    mehitsa = _trace_osm(MEHITSA)
    cap_mehitsa = _cap(*mehitsa)
    cote_des_femmes = min((1, -1), key=lambda t: math.dist(_devant(mehitsa[0], cap_mehitsa, 5 / AMA, t * 3 / AMA), PONT_MAGHREBINS[3]))
    parasols += [(_devant(mehitsa[0], cap_mehitsa, (5 + 1.3 * k) / AMA, cote_des_femmes * 1.1 / AMA), False, 0.0) for k in range(9)]
    parasols += [(_devant(mehitsa[1], cap_mehitsa, -(4 + 4.2 * k) / AMA, cote_des_femmes * 3.2 / AMA), True, cap_mehitsa + math.pi / 4)
                 for k in range(4)]
    for p, ouvert, tourne in parasols:
        toile, mat = _parasol(p, z, ouvert, tourne)
        toiles.append(toile)
        mats += mat
    _poser("Kotel_place_parasols", toiles, MAT_TOILE())
    _poser("Kotel_place_parasols_mats", mats, MAT_INOX())
    piles = [piece for k in range(7)
             for piece in _pile_de_chaises(_point_de_wilson(-(1.0 + 0.7 * (k % 2)) / AMA, (5.2 + 0.62 * k) / AMA), cap, z, 9 + k % 4)]
    _poser("Kotel_place_piles_de_chaises", piles, MAT_PLASTIQUE())
    # Au milieu de l'aire des hommes, l'estrade de bois où l'on range tables et bima (vue plongeante de 2017).
    estrade = _devant(nord, cap, 22 / AMA, cote * 17 / AMA)
    bima = [_pave(estrade, cap, 7 / AMA, 5 / AMA, z, z + 0.35 / AMA)]
    bima += [_pave(_devant(estrade, cap, (i - 2) * 1.3 / AMA, (j - 1) * 1.4 / AMA), cap, 1.1 / AMA, 1.2 / AMA, z + 0.35 / AMA, z + 1.15 / AMA)
             for i in range(5) for j in range(3) if (i + j) % 3]
    _poser("Kotel_place_estrade", bima, MAT_BOIS_DU_PONT())


def drapeau(hauteur=13 / AMA, guindant=2.2 / AMA, battant=3.2 / AMA):
    """Le mât du drapeau d'Israël, sur la place haute au bord du muret, à peu près au droit
    de la mehitsa. Hauteur du mât et taille du drapeau : CHOIX."""
    muret = _trace_osm(MURET_DE_PRIERE)[2:4]
    cap_muret = _cap(*muret)
    p = _devant(muret[0], cap_muret, 3 / AMA, -_vers_l_aire_de_priere(_devant(muret[0], cap_muret, 3 / AMA), cap_muret) * 1.6 / AMA)
    z, cap = Z_PLACE_HAUTE, -0.6
    _poser("Kotel_place_mat_du_drapeau", [_fut(p, z, z + hauteur, 0.07 / AMA, 8), _fut(p, z, z + 0.5 / AMA, 0.2 / AMA, 8)], MAT_INOX())
    bas, milieu = z + hauteur - guindant - 0.1 / AMA, _devant(p, cap, battant / 2 + 0.08 / AMA)
    _poser("Kotel_place_drapeau", [_pave(milieu, cap, battant, 0.02 / AMA, bas, bas + guindant)], MAT_DRAPEAU_BLANC())
    bleu = [_pave(milieu, cap, battant, 0.1 / AMA, bas + f * guindant, bas + (f + 0.13) * guindant) for f in (0.1, 0.77)]
    rayon, centre = guindant * 0.19, bas + guindant / 2
    for sens in (1, -1):
        sommets = [(rayon * math.sin(2 * math.pi * i / 3), centre + sens * rayon * math.cos(2 * math.pi * i / 3)) for i in range(3)]
        for (xa, za), (xb, zb) in zip(sommets, sommets[1:] + sommets[:1]):
            (xa, za), (xb, zb) = sorted(((xa, za), (xb, zb)))
            bleu.append((_poutre(_devant(milieu, cap, xa), _devant(milieu, cap, xb), za, zb, 0.05 / AMA, -0.05 / AMA, 0.07 / AMA), FACES_BOITE))
    _poser("Kotel_place_drapeau_bleu", bleu, MAT_DRAPEAU_BLEU())


def mats_d_eclairage(hauteur=14 / AMA):
    """Les grands mâts sombres de la place haute, une couronne de projecteurs en tête et une
    autre à mi-hauteur. Leur place : CHOIX, sur ses bords."""
    pieces, verres = [], []
    for k, (est, nord) in enumerate(((-166, -190), (-143, -205), (-137, -190))):
        p = vers_scene(est, nord)
        z = Z_PLACE_HAUTE
        pieces += [_fut(p, z, z + hauteur, 0.1 / AMA, 8), _fut(p, z, z + 0.8 / AMA, 0.2 / AMA, 8)]
        for tete, combien in ((hauteur, 6), (hauteur - 1.4 / AMA, 4)):
            pieces.append(_fut(p, z + tete - 0.25 / AMA, z + tete - 0.15 / AMA, 0.55 / AMA, 8))
            pieces += [_pave(_devant(p, 2 * math.pi * i / combien, 0.6 / AMA), 2 * math.pi * i / combien, 0.22 / AMA, 0.42 / AMA,
                             z + tete - 0.2 / AMA, z + tete + 0.15 / AMA) for i in range(combien)]
            verres += [_pave(_devant(p, 2 * math.pi * i / combien, 0.72 / AMA), 2 * math.pi * i / combien, 0.02 / AMA, 0.36 / AMA,
                             z + tete - 0.15 / AMA, z + tete + 0.1 / AMA) for i in range(combien)]
        repere_de_projecteur(f"mat_{k}", p, z + hauteur)
    _poser("Kotel_place_mats", pieces, MAT_FER())
    _poser("Kotel_place_mats_verres", verres, MAT_VERRE_DE_LAMPE())


def _barriere(p, cap, z, longueur=2.4 / AMA):
    """Une barrière de police : un cadre, des barreaux, deux patins."""
    a, b = _devant(p, cap, -longueur / 2), _devant(p, cap, longueur / 2)
    pieces = [(_poutre(a, b, z + h, z + h, 0.02 / AMA, -0.02 / AMA, 0.04 / AMA), FACES_BOITE) for h in (0.2 / AMA, 1.06 / AMA)]
    pieces += [_fut(_devant(a, cap, longueur * k / 12), z + 0.2 / AMA, z + 1.06 / AMA, 0.01 / AMA if 0 < k < 12 else 0.02 / AMA, 4)
               for k in range(13)]
    return pieces + [_pave(q, cap + math.pi / 2, 0.5 / AMA, 0.04 / AMA, z, z + 0.22 / AMA) for q in (a, b)]


def _palmier(nom, p, z, hauteur):
    """(stipe, palmes)."""
    stipe = [_fut(p, z, z + hauteur, 0.22 / AMA, 8), _fut(p, z + hauteur - 0.6 / AMA, z + hauteur + 0.2 / AMA, 0.38 / AMA, 8)]
    palmes = []
    for k in range(18):
        cap, elan, longueur = 2 * math.pi * (k + alea(nom, k)) / 18, 0.2 + 1.1 * alea(nom, 30 + k), (2.6 + 1.2 * alea(nom, 60 + k)) / AMA
        nervure = [(p[0] + math.cos(cap) * longueur * t, p[1] + math.sin(cap) * longueur * t,
                    z + hauteur + longueur * (elan * t - (0.5 + elan * 0.8) * t * t)) for t in (0, 0.25, 0.5, 0.75, 1)]
        palmes.append(_ruban(nervure, [f * 0.9 / AMA for f in (0.3, 1.0, 1.0, 0.7, 0.1)], (0.0, 0.0, 1.0)))
    return stipe, palmes


def mobilier_de_la_place_haute():
    """Sur la place haute : les stèles d'information de pierre à plaque sombre, les barrières
    de police qui canalisent la foule au pied du pont et devant les degrés des femmes, et les
    palmiers du jardin archéologique, derrière le pont."""
    z = Z_PLACE_HAUTE
    steles, plaques = [], []
    for est, nord, cap in ((-143, -181, 0.3), (-151, -142, 1.4), (-160, -206, 0.0)):
        p = vers_scene(est, nord)
        steles.append(_pave(p, cap, 0.5 / AMA, 0.28 / AMA, z, z + 1.9 / AMA))
        plaques += [_pave(_devant(p, cap, 0, t * 0.15 / AMA), cap, 0.4 / AMA, 0.02 / AMA, z + 0.7 / AMA, z + 1.7 / AMA) for t in (-1, 1)]
    _poser("Kotel_place_steles", steles, MAT_PIERRE())
    _poser("Kotel_place_steles_plaques", plaques, MAT_FER_BRUN())
    pied_du_pont = PONT_MAGHREBINS[0]
    cap_du_pont = _cap(PONT_MAGHREBINS[1], PONT_MAGHREBINS[0])
    barrieres = [piece for k in range(5)
                 for piece in _barriere(_devant(pied_du_pont, cap_du_pont, 6 / AMA, (k - 2) * 2.5 / AMA), cap_du_pont + math.pi / 2, z)]
    a, b = BRECHE_DES_FEMMES
    cap_breche = _cap(a, b)
    hors = -_vers_l_aire_de_priere(_devant(a, cap_breche, math.dist(a, b) / 2), cap_breche)
    barrieres += [piece for k in range(3)
                  for piece in _barriere(_devant(a, cap_breche, (1.2 + 2.5 * k) / AMA, hors * 3.5 / AMA), cap_breche + 0.15 * (k - 1), z)]
    _poser("Kotel_place_barrieres", barrieres, MAT_PORTIQUE())
    # Au-dessus des degrés des femmes et de la pente des hommes, le panneau blanc « כניסה » entre deux poteaux.
    panneaux, poteaux = [], []
    for breche in (BRECHE_DES_FEMMES, BRECHE_DES_HOMMES):
        c, d = breche
        cap_panneau = _cap(c, d)
        milieu = _devant(c, cap_panneau, math.dist(c, d) / 2)
        panneaux.append(_pave(milieu, cap_panneau, 3 / AMA, 0.03 / AMA, z + 2.3 / AMA, z + 3.0 / AMA))
        poteaux += [_fut(_devant(milieu, cap_panneau, t * 1.5 / AMA), z, z + 3.0 / AMA, 0.03 / AMA, 6) for t in (-1, 1)]
    _poser("Kotel_place_panneaux", panneaux, MAT_PLASTIQUE())
    _poser("Kotel_place_panneaux_poteaux", poteaux, MAT_PORTIQUE())
    # Devant Beit HaLiba, cinq drapeaux en rang ; au bord du parc de police, deux baraques
    # blanches, deux cabines bleues et deux tentes (photo de 2020).
    # Sur les toits de la Fondation et de la Ma'hkama, les drapeaux que toutes les vues de la place montrent.
    hampes, blancs, bleus = [], [], []
    toit_de_la_fondation = Z_PLACE_HAUTE + H_FONDATION + H_PAVILLON
    cap_de_la_fondation = _cap(ANGLE_DE_LA_FONDATION, BOUT_DE_LA_FONDATION)
    mats = [(vers_scene(-171, -196 + 2.2 * k), z, 6 / AMA) for k in range(5)]
    mats += [(_devant(ANGLE_DE_LA_FONDATION, cap_de_la_fondation, s / AMA, -RETRAIT_DU_PAVILLON - 1 / AMA), toit_de_la_fondation, 4.5 / AMA)
             for s in (4, 16, 28)]
    mats += [(_point_de_wilson((1 + 1.5 * k) / AMA, 3 / AMA), H_MAKHKAMA, 4.5 / AMA) for k in range(2)]
    for p, pied, hauteur in mats:
        haut = pied + hauteur
        hampes.append(_fut(p, pied, haut, 0.03 / AMA, 6))
        blancs.append(_pave(_devant(p, -0.4, 0.75 / AMA), -0.4, 1.4 / AMA, 0.02 / AMA, haut - 1.1 / AMA, haut - 0.1 / AMA))
        bleus += [_pave(_devant(p, -0.4, 0.75 / AMA), -0.4, 1.4 / AMA, 0.06 / AMA, haut - h / AMA, haut - (h - 0.12) / AMA) for h in (0.98, 0.34)]
        bleus.append(_pave(_devant(p, -0.4, 0.75 / AMA), -0.4, 0.3 / AMA, 0.06 / AMA, haut - 0.75 / AMA, haut - 0.45 / AMA))
    _poser("Kotel_place_hampes", hampes, MAT_INOX())
    _poser("Kotel_place_drapeaux", blancs, MAT_DRAPEAU_BLANC())
    _poser("Kotel_place_drapeaux_bleu", bleus, MAT_DRAPEAU_BLEU())
    baraques = [_pave(vers_scene(est, nord), 0.15, 6 / AMA, 2.5 / AMA, z, z + 2.6 / AMA) for est, nord in ((-176, -212), (-176, -216))]
    _poser("Kotel_place_baraques", baraques, MAT_PLASTIQUE())
    _poser("Kotel_place_cabines", [_pave(vers_scene(-170.5 + 1.3 * k, -229), 0.15, 1.2 / AMA, 1.2 / AMA, z, z + 2.3 / AMA) for k in range(2)],
           MAT_DRAPEAU_BLEU())
    tentes = [piece for est, nord in ((-141, -209), (-137, -207))
              for piece in (_pyramide(vers_scene(est, nord), z + 2.2 / AMA, z + 3.2 / AMA, 2.1 / AMA, 4, 0.6),)]
    _poser("Kotel_place_tentes", tentes, MAT_TOILE())
    _poser("Kotel_place_tentes_mats", [_fut(_devant(vers_scene(est, nord), 0.6 + math.pi / 2 * i, 2.0 / AMA), z, z + 2.2 / AMA, 0.03 / AMA, 6)
                                       for est, nord in ((-141, -209), (-137, -207)) for i in range(4)], MAT_INOX())
    stipes, palmes = [], []
    for k, (est, nord, hauteur) in enumerate(((-104, -178, 9.5), (-113, -183, 7.5), (-122, -200, 6.5))):
        s, f = _palmier(f"Kotel_palmier_{k}", vers_scene(est, nord), z, hauteur / AMA)
        stipes, palmes = stipes + s, palmes + f
    _poser("Kotel_palmiers", stipes, MAT_TRONC())
    _poser("Kotel_palmiers_palmes", palmes, MAT_PALME())


def tribune_de_presse(longueur=12 / AMA, largeur=4 / AMA, hauteur=0.45 / AMA):
    """L'estrade des caméras que les photos de décembre 2025 montrent sur la place haute, derrière
    le muret, face au milieu du Kotel : un plancher gris, un garde-corps blanc à barreaux, deux
    marches à l'arrière, et à ses bouts deux lampadaires noirs à tête plate. Ses mesures : lues
    sur ces photos."""
    muret = _trace_osm(MURET_DE_PRIERE)[2:4]
    cap = _cap(*muret)
    hors = -_vers_l_aire_de_priere(_devant(muret[0], cap, math.dist(*muret) / 2), cap)
    centre = _devant(muret[0], cap, math.dist(*muret) * 0.62, hors * (largeur / 2 + 2.2 / AMA))
    z = Z_PLACE_HAUTE
    plancher = [_pave(centre, cap, longueur, largeur, z, z + hauteur),
                _pave(_devant(centre, cap, 0, hors * (largeur / 2 + 0.3 / AMA)), cap, 3 / AMA, 0.6 / AMA, z, z + hauteur / 2)]
    _poser("Kotel_place_tribune", plancher, MAT_BETON())
    bord = lambda avant, arriere: _devant(centre, cap, avant, arriere * hors * (largeur / 2 - 0.05 / AMA))
    demi = longueur / 2 - 0.05 / AMA
    rampes = garde_corps([bord(-1.5 / AMA, 1), bord(-demi, 1), bord(-demi, -1), bord(demi, -1), bord(demi, 1), bord(1.5 / AMA, 1)],
                         z + hauteur, 1.1 / AMA, 0.14 / AMA)
    _poser("Kotel_place_tribune_garde_corps", rampes, MAT_ACIER_BLANC())
    lampadaires = []
    for bout in (-1, 1):
        pied = _devant(centre, cap, bout * (longueur / 2 + 1.2 / AMA), -hors * largeur / 2)
        lampadaires += [_pave(pied, cap, 0.18 / AMA, 0.18 / AMA, z, z + 4.6 / AMA),
                        _pave(_devant(pied, cap, 0, -hors * 0.4 / AMA), cap, 0.3 / AMA, 1.0 / AMA, z + 4.5 / AMA, z + 4.6 / AMA)]
    _poser("Kotel_place_lampadaires", lampadaires, MAT_FER())


def vegetation_de_la_rampe():
    """Sur ce qui reste du remblai des Maghrébins, au pied de la porte : le bougainvillier en fleur
    et les buissons que montrent les photos de 2019 à 2025. Leur taille : CHOIX."""
    z = Z_PLACE_KOTEL + 5 / AMA
    massifs = (((-99, -183), 2.3, MAT_BOUGAINVILLEE), ((-102.5, -182), 1.7, MAT_BOUGAINVILLEE), ((-96, -184.5), 1.6, MAT_FEUILLAGE),
               ((-107, -183.5), 1.3, MAT_FEUILLAGE), ((-112, -182.5), 1.1, MAT_FEUILLAGE))
    for k, (metres, rayon, mat) in enumerate(massifs):
        x, y = vers_scene(*metres)
        sphere(f"Kotel_rampe_massif_{k}", x, y, z + rayon / AMA * 0.5, rayon / AMA, "00_HarHabayit", mat(), segs=8)


def mobilier_du_kotel():
    mobilier_de_priere()
    tribune_de_presse()
    vegetation_de_la_rampe()
    voitures_de_police()
    capriers_du_kotel()
    drapeau()
    mats_d_eclairage()
    mobilier_de_la_place_haute()
