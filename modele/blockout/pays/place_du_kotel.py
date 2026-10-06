import math
from typing import NamedTuple
from mathutils import Vector, geometry

from ..primitives.parametres import AMA, Z_HAR
from ..primitives.noeuds import material
from ..primitives.matieres import (MAT_ACIER_BLANC, MAT_BOIS_DU_PONT, MAT_BORNE_INCENDIE, MAT_BRONZE, MAT_CHENE,
                                   MAT_DALLAGE_DE_PRIERE, MAT_DALLAGE_KOTEL, MAT_FER_BRUN, MAT_INOX, MAT_MEHITSA,
                                   MAT_MURAILLE, MAT_OR, MAT_PIERRE, MAT_PIERRE_DE_JERUSALEM, MAT_PLASTIQUE,
                                   MAT_PORTIQUE, MAT_RELIURES, MAT_SOL, MAT_TOILE, MAT_TOLE, MAT_VITRE)
from ..primitives.volumes import FACES_BOITE, _cercle, alea, mesh_from_pydata, plage, revolution
from .calage import (CLE_WILSON, CONTREMARCHE, CUVETTE_KOTEL, ESCALIER_PLACE, GARDE_CORPS, HARAM, KOTEL, LARGEUR_ESCALIER,
                     LARGEUR_PONT, MAILLE_PAYS, PARAPET_DE_PRIERE, PAYS_DONNEES, PLACE_KOTEL, PONT_MAGHREBINS,
                     PORTEE_WILSON, SALLES_WILSON, Z_HAUT_ESCALIER, Z_PLACE_HAUTE, Z_PLACE_KOTEL,
                     _abscisses, _dans, _direct, _distance_a_l_anneau, _distance_a_la_trace,
                     _distance_au_segment, _fraction_sur_le_segment, _plus_proche_sur_la_trace,
                     _point_a_l_abscisse, _z_escalier, sol_naturel, vers_scene, volumes)
from .herode import soutenement


def _contre(*anneaux):
    return lambda p: any(_distance_a_l_anneau(p, anneau) < 3 for anneau in anneaux)


def _z_pont(abscisse):
    """Le tablier monte de la place au dallage ; son dernier tronçon passe la porte à plat."""
    montee = _abscisses(PONT_MAGHREBINS)[-2]
    return Z_PLACE_HAUTE + (Z_HAR - Z_PLACE_HAUTE) * min(abscisse / montee, 1)


def place_du_kotel():
    volumes("Kotel_place_aire_de_priere", [(AIRE_DE_PRIERE, [], Z_PLACE_KOTEL - 1, Z_PLACE_KOTEL),
                                           (_direct(SOUS_LE_PONT), [], Z_PLACE_KOTEL - 1, Z_PLACE_KOTEL)], "00_HarHabayit",
            MAT_DALLAGE_DE_PRIERE())
    volumes("Kotel_place", [(PLACE_HAUTE, [], Z_PLACE_KOTEL - 1, Z_PLACE_HAUTE),
                            (ESPLANADE_SUD, [], Z_PLACE_KOTEL - 1, Z_PLACE_HAUTE)], "00_HarHabayit", MAT_DALLAGE_KOTEL())
    ouvert = lambda p: (_contre(HARAM, SALLES_WILSON)(p)
                        or _distance_a_la_trace(p, BORD_NORD) < 3    # la cuvette est tracée au mètre : à une ama près, un massif restait debout devant le porche de la Fondation
                        or _distance_a_la_trace(p, ESCALIER_PLACE) < MAILLE_PAYS
                        or any(math.dist(p, b.centre) < LARGEUR_PASSAGE / 2 for b in BOUCHES))
    bords = soutenement(CUVETTE_KOTEL, Z_PLACE_KOTEL - 1, ouvert)
    pieces = bords + soutenement(SALLES_WILSON, Z_PLACE_KOTEL - 1, _contre(HARAM, PLACE_KOTEL))
    volumes("Kotel_place_soutenement", pieces, "00_HarHabayit", MAT_PIERRE_DE_JERUSALEM())
    marches_de_l_aire_de_priere()
    passages_de_la_place(bords)
    pont_des_maghrebins()
    salles_de_wilson()
    escalier_de_la_place()
    interieur_de_wilson()
    muret_de_priere()
    mobilier_de_la_place()
    arret_de_bus()
    menora_d_or()
    return bords


def _poutre(a, b, za, zb, gauche, droite, hauteur):
    """Les huit sommets d'une boîte le long de a-b, sous FACES_BOITE : de `droite` à `gauche`
    en travers (à gauche du sens de marche), d'une sous-face qui va de `za` à `zb`."""
    long_ = max(math.dist(a, b), 1e-9)
    nx, ny = -(b[1] - a[1]) / long_, (b[0] - a[0]) / long_
    bas = [(a, za, droite), (b, zb, droite), (b, zb, gauche), (a, za, gauche)]
    return ([(p[0] + nx * d, p[1] + ny * d, z) for p, z, d in bas]
            + [(p[0] + nx * d, p[1] + ny * d, z + hauteur) for p, z, d in bas])


def _fondre(morceaux):
    """Des (sommets, faces) mis dans un seul maillage."""
    verts, faces = [], []
    for v, f in morceaux:
        faces += [[len(verts) + i for i in face] for face in f]
        verts += v
    return verts, faces


def _assembler(boites):
    return _fondre((huit, FACES_BOITE) for huit in boites)


def pont_des_maghrebins(epaisseur=0.4, entraxe=8, travee=2 / AMA, sous_toit=2.3 / AMA, latte=0.22 / AMA):
    """Le pont de bois de 2007, de la place à la porte des Maghrébins, sur la trace OSM : un
    tablier qui monte d'un trait, des poteaux jusqu'au toit de tôle à deux pentes et à joints
    debout, et sur chaque flanc, du tablier au toit, un rang serré de lattes toutes penchées du
    même côté ; devant la porte, deux pans de planches sous un toit plus haut ;
    des palées d'acier blanc contreventées en croix ; au pied, la cabane de lattes où l'on
    contrôle ceux qui montent ; et la palissade — blanche sur un soubassement de planches,
    entre des poteaux d'acier — qui ferme l'échafaudage côté place tant qu'il ne survole pas
    l'aire des femmes. Travée, hauteur sous toit, lattes : lues sur les photos de 2019 à 2025."""
    trace = PONT_MAGHREBINS
    s = _abscisses(trace)
    demi = LARGEUR_PONT / 2
    tablier, bois, toit, palissade, couverture = [], [], [], [], []
    sol = Z_PLACE_HAUTE - 0.5
    for k, (a, b) in enumerate(zip(trace, trace[1:])):
        za, zb = _z_pont(s[k]), _z_pont(s[k + 1])
        tablier.append(_poutre(a, b, za - epaisseur, zb - epaisseur, demi, -demi, epaisseur))
        couverture.append(_toit_a_deux_pentes(a, b, za + sous_toit, zb + sous_toit, demi + 1.6, 0.7 / AMA))
        toit += [_poutre(a, b, za + sous_toit + 0.7 / AMA * (1 - abs(f)), zb + sous_toit + 0.7 / AMA * (1 - abs(f)),
                         (demi + 1.6) * f + 0.04 / AMA, (demi + 1.6) * f - 0.04 / AMA, 0.06 / AMA) for f in (-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1)]
        for cote in (-1, 1):
            bois += [_poutre(a, b, za + h, zb + h, cote * demi + 0.1, cote * demi - 0.1, 0.2) for h in (0, GARDE_CORPS, sous_toit - 0.2)]
        if s[k + 1] <= s[2] + 1e-6:
            haut = min(za, zb) - epaisseur + (max(za, zb) - min(za, zb)) / 2
            for cote in (-1, 1):
                palissade.append(_poutre(a, b, sol, sol, cote * demi + 0.06, cote * demi - 0.06, haut - sol))
                bois.append(_poutre(a, b, sol, sol, cote * demi + 0.1, cote * demi - 0.1, min(haut - sol, 0.5 + 1.3 / AMA)))
    for depart in plage(0, s[-1] - travee, travee):
        (p, _), (q, _) = _point_a_l_abscisse(trace, depart), _point_a_l_abscisse(trace, depart + travee)
        zp, zq = _z_pont(depart), _z_pont(depart + travee)
        for cote in (-1, 1):
            lat = (cote * demi + 0.06, cote * demi - 0.06)
            bois.append(_poutre(p, _devant(p, _cap(p, q), 0.25), zp, zp, *lat, sous_toit))
            if depart + travee <= s[2]:
                toit.append(_poutre(p, _devant(p, _cap(p, q), 0.2), sol, sol, cote * demi + 0.16, cote * demi - 0.16, zp - epaisseur - sol))
    for depart in plage(0, s[-1] - 2 * latte, latte):
        (p, _), (q, _) = _point_a_l_abscisse(trace, depart), _point_a_l_abscisse(trace, depart + 1.5 * latte)
        zp, zq = _z_pont(depart), _z_pont(depart + 1.5 * latte)
        bois += [_poutre(p, q, zp + 0.2, zq + sous_toit - 0.4, cote * demi + 0.05, cote * demi - 0.05, 0.16 / AMA) for cote in (-1, 1)]
    piles = []
    for abscisse in plage(entraxe / 2, s[-2], entraxe):
        (x, y), (tx, ty) = _point_a_l_abscisse(trace, abscisse)
        pied = Z_PLACE_KOTEL - 1
        haut = _z_pont(abscisse) - epaisseur - pied
        for cote in (-1, 1):
            p = (x + ty * cote * (demi - 0.4), y - tx * cote * (demi - 0.4))
            piles.append(_poutre((p[0] - tx * 0.2, p[1] - ty * 0.2), (p[0] + tx * 0.2, p[1] + ty * 0.2), pied, pied, 0.2, -0.2, haut))
        gauche, droite = (x + ty * (demi - 0.4), y - tx * (demi - 0.4)), (x - ty * (demi - 0.4), y + tx * (demi - 0.4))
        niveaux = [pied + haut * f for f in (0.35, 0.7, 0.97)]
        piles += [_poutre(gauche, droite, z, z, 0.12, -0.12, 0.25) for z in niveaux]
        for bas, tete in zip(niveaux, niveaux[1:]):
            piles += [_poutre(gauche, droite, bas, tete, 0.05, -0.05, 0.12), _poutre(gauche, droite, tete, bas, 0.05, -0.05, 0.12)]
    # Au pied du pont, la cabane de lattes où l'on contrôle ceux qui montent, sous un toit à une pente.
    cap = _cap(trace[1], trace[0])
    cabane = _devant(trace[0], cap, 2.2 / AMA)
    bois.append(_pave(cabane, cap, 4 / AMA, LARGEUR_PONT + 1, Z_PLACE_HAUTE, Z_PLACE_HAUTE + 2.6 / AMA)[0])
    bois += [_pave(cabane, cap, 4.06 / AMA, LARGEUR_PONT + 1 + 0.06 / AMA, Z_PLACE_HAUTE + h / AMA, Z_PLACE_HAUTE + (h + 0.16) / AMA)[0]
             for h in plage(0.1, 2.4, 0.3)]
    toit.append(_poutre(_devant(cabane, cap, -2.4 / AMA), _devant(cabane, cap, 2.4 / AMA), Z_PLACE_HAUTE + 3.1 / AMA, Z_PLACE_HAUTE + 2.6 / AMA,
                        LARGEUR_PONT / 2 + 1.2, -LARGEUR_PONT / 2 - 1.2, 0.1 / AMA))
    # Devant la porte, la guérite du dernier tronçon : deux pans de planches sous un toit plus haut (photo de décembre 2025).
    seuil, entree = _z_pont(s[-1]), _devant(trace[-1], _cap(trace[-1], trace[-2]), 5 / AMA)
    bois += [_poutre(entree, trace[-1], seuil, seuil, cote * (demi + 0.5) + 0.05, cote * (demi + 0.5) - 0.05, sous_toit + 0.9 / AMA) for cote in (-1, 1)]
    couverture.append(_toit_a_deux_pentes(_devant(entree, _cap(trace[-1], entree), 0.6 / AMA), trace[-1], seuil + sous_toit + 0.9 / AMA,
                                          seuil + sous_toit + 0.9 / AMA, demi + 1.4, 0.9 / AMA))
    mesh_from_pydata("Maghrebins_pont", *_assembler(tablier + bois), "00_HarHabayit", MAT_BOIS_DU_PONT())
    mesh_from_pydata("Maghrebins_pont_toit", *_fondre([(huit, FACES_BOITE) for huit in toit] + couverture), "00_HarHabayit", MAT_TOLE())
    mesh_from_pydata("Maghrebins_pont_palees", *_assembler(piles), "00_HarHabayit", MAT_ACIER_BLANC())
    mesh_from_pydata("Maghrebins_pont_palissade", *_assembler(palissade), "00_HarHabayit", MAT_TOILE())


def _toit_a_deux_pentes(a, b, za, zb, demi, fleche):
    """Un comble plein le long de a-b : deux rives à `demi` de l'axe, un faîte `fleche` plus haut."""
    long_ = max(math.dist(a, b), 1e-9)
    nx, ny = -(b[1] - a[1]) / long_, (b[0] - a[0]) / long_
    verts = [(p[0] + nx * d, p[1] + ny * d, z + h) for p, z in ((a, za), (b, zb)) for d, h in ((demi, 0), (0, fleche), (-demi, 0))]
    return verts, [[0, 1, 4, 3], [1, 2, 5, 4], [0, 3, 5, 2], [0, 2, 1], [3, 4, 5]]


def _face_du_kotel(anneau):
    """Le côté de l'anneau le long du Kotel, orienté de la place vers le nord : (a, b)."""
    a, b = min(zip(anneau, anneau[1:] + anneau[:1]),
               key=lambda e: _distance_a_l_anneau(((e[0][0] + e[1][0]) / 2, (e[0][1] + e[1][1]) / 2), HARAM))
    return (a, b) if _distance_a_l_anneau(a, PLACE_KOTEL) < _distance_a_l_anneau(b, PLACE_KOTEL) else (b, a)


def _extrusion(profil, origine, u, v, longueur):
    """Un profil (v, z) fermé, sens direct, extrudé de `longueur` le long de u : flancs et
    deux bouts."""
    def monde(pv, pz, pu):
        return (origine[0] + u[0] * pu + v[0] * pv, origine[1] + u[1] * pu + v[1] * pv, pz)
    n = len(profil)
    verts = [monde(pv, pz, 0) for pv, pz in profil] + [monde(pv, pz, longueur) for pv, pz in profil]
    faces = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    for a, b, c in geometry.tessellate_polygon([[Vector((pv, pz, 0)) for pv, pz in profil]]):
        direct = ((profil[b][0] - profil[a][0]) * (profil[c][1] - profil[a][1])
                  - (profil[b][1] - profil[a][1]) * (profil[c][0] - profil[a][0])) > 0
        faces += [[a, c, b], [n + a, n + b, n + c]] if direct else [[a, b, c], [n + a, n + c, n + b]]
    if u[0] * v[1] - u[1] * v[0] < 0:
        faces = [f[::-1] for f in faces]
    return verts, faces


def _repere_de_wilson():
    """Le coin des salles au Kotel côté place, u le long du Kotel vers le nord, v vers l'ouest :
    (coin, u, v, longueur, largeur)."""
    a, b = _face_du_kotel(SALLES_WILSON)
    longueur = math.dist(a, b)
    u = ((b[0] - a[0]) / longueur, (b[1] - a[1]) / longueur)
    v = (-u[1], u[0])
    if _dans((a[0] + v[0] * 5, a[1] + v[1] * 5), HARAM):
        v = (u[1], -u[0])
    return a, u, v, longueur, max((p[0] - a[0]) * v[0] + (p[1] - a[1]) * v[1] for p in SALLES_WILSON)


WILSON = _repere_de_wilson()
NAISSANCE_WILSON = Z_PLACE_KOTEL + CLE_WILSON - PORTEE_WILSON / 2


def _point_de_wilson(pu, pv):
    a, u, v, _, _ = WILSON
    return (a[0] + u[0] * pu + v[0] * pv, a[1] + u[1] * pu + v[1] * pv)


def _sous_la_voute(pv):
    """La cote de l'intrados à `pv` du Kotel."""
    rayon = PORTEE_WILSON / 2
    return NAISSANCE_WILSON + math.sqrt(max(0.0, rayon ** 2 - (pv - rayon) ** 2))


def salles_de_wilson(segments=16):
    """Les salles de prière couvertes au nord de la place, sous la chaussée qui mène à la
    porte de la Chaîne : l'arche de Wilson y part du Kotel, treize mètres de portée, et sa
    clé est à 6,1 m du sol d'aujourd'hui ; sa voûte court sur toute la longueur des salles.
    Le reste de leur emprise, jusqu'au dallage, est plein."""
    a, u, v, longueur, largeur = WILSON
    rayon, pied = PORTEE_WILSON / 2, Z_PLACE_KOTEL - 1
    arche = [(rayon - rayon * math.cos(math.pi * k / segments), NAISSANCE_WILSON + rayon * math.sin(math.pi * k / segments))
             for k in range(segments + 1)]
    profil = [(PORTEE_WILSON, pied), (largeur, pied), (largeur, Z_HAR), (0, Z_HAR)] + arche
    mesh_from_pydata("Wilson_arche", *_extrusion(profil, a, u, v, longueur), "00_HarHabayit", MAT_MURAILLE())
    coin = _point_de_wilson
    sol =[coin(0, 0), coin(longueur, 0), coin(longueur, PORTEE_WILSON), coin(0, PORTEE_WILSON)]
    fond = [coin(longueur - 1, 0), coin(longueur, 0), coin(longueur, PORTEE_WILSON), coin(longueur - 1, PORTEE_WILSON)]
    volumes("Wilson_sol", [(sol, [], pied, Z_PLACE_KOTEL)], "00_HarHabayit", MAT_SOL())
    volumes("Wilson_fond", [(fond, [], pied, Z_PLACE_KOTEL + CLE_WILSON)], "00_HarHabayit", MAT_MURAILLE())


def escalier_de_la_place(pas_des_murs=2):
    """Du coin nord-ouest de la place au quartier juif, sur la trace OSM : des degrés pleins
    entre deux murs qui retiennent le relief, jusqu'au sol où la trace arrive."""
    trace = ESCALIER_PLACE
    longueur = _abscisses(trace)[-1]
    n = max(1, round((Z_HAUT_ESCALIER - Z_PLACE_HAUTE) / CONTREMARCHE))
    demi = LARGEUR_ESCALIER / 2
    boites = []
    for k in range(n):
        (p, _), (q, _) = (_point_a_l_abscisse(trace, longueur * k / n),
                          _point_a_l_abscisse(trace, longueur * (k + 1) / n))
        z = Z_PLACE_HAUTE + (Z_HAUT_ESCALIER - Z_PLACE_HAUTE) * (k + 1) / n
        boites.append(_poutre(p, q, Z_PLACE_KOTEL - 1, Z_PLACE_KOTEL - 1, demi, -demi, z - Z_PLACE_KOTEL + 1))
    mesh_from_pydata("Kotel_place_escalier", *_assembler(boites), "00_HarHabayit", MAT_SOL())
    murs = []
    for s0 in plage(0, longueur, pas_des_murs):
        s1 = min(longueur, s0 + pas_des_murs)
        if s1 - s0 < 1e-6:
            continue
        (p, _), (q, _) = _point_a_l_abscisse(trace, s0), _point_a_l_abscisse(trace, s1)
        for bord, dehors in ((demi, demi + MAILLE_PAYS), (-demi - MAILLE_PAYS, -demi)):
            huit = _poutre(p, q, 0, 0, dehors, bord, 0)
            terrain = max(sol_naturel(x, y) for x, y, _ in huit[:4])
            haut = max(terrain + 0.5, _z_escalier(s1) + GARDE_CORPS)
            murs.append(([(x, y) for x, y, _ in huit[:4]], [], Z_PLACE_KOTEL - 1, haut))
    volumes("Kotel_place_escalier_murs", murs, "00_HarHabayit", MAT_PIERRE_DE_JERUSALEM())
    _poser("Kotel_place_escalier_rampe", _main_courante(trace, lambda s: _z_escalier(s)), MAT_FER_BRUN())


# Ce qui meuble la place et ses bords, chaque chose à son point OSM. Là où OSM ne dit que
# « il y a un robinet ici », la forme est un CHOIX, dit dans la fonction qui la construit.
ABORDS = PAYS_DONNEES["abords_kotel"]
MENORA = "n3971775380"           # l'autre nœud « המנורה » tombe dans l'emprise d'un bâtiment
MURET_DE_PRIERE, MEHITSA, CLOTURE_DES_FEMMES = "w45081552", "w45081551", "w394161620"
CLOTURE_DEVANT_LA_FONDATION = "w1549528750"    # qu'aucune photo de 2025 ne montre : elle n'est pas bâtie
MUR_ANTIBRUIT = "w288016728"
PORAT_YOSEF = "w290726629"
ETAGE, REZ, BAIE = 3.2 / AMA, 4.2 / AMA, 3.5 / AMA


def _abords(genre):
    return [[vers_scene(*p) for p in a["points"]] for a in ABORDS if a["genre"] == genre]


def _trace_osm(osm):
    return next([vers_scene(*p) for p in a["points"]] for a in ABORDS if a["osm"] == osm)


def _coupe_par_le_muret():
    """La place coupée le long du muret de prière — sans son dernier tronçon, qui file vers les
    salles de Wilson le long de la pente des hommes —, prolongé au sud jusqu'au coin de la
    clôture des femmes et au nord tout droit jusqu'au bord : (aire de prière, place haute,
    brèche des femmes, brèche des hommes). Les brèches sont les trouées qu'OSM laisse entre le
    muret et ce qui le prolonge."""
    ligne = _trace_osm(MURET_DE_PRIERE)[:-1]
    anneau, n = PLACE_KOTEL, len(PLACE_KOTEL)
    sud = min(range(n), key=lambda i: math.dist(anneau[i], ligne[0]))
    haut = ligne[-1]
    (x0, y0), (x1, y1) = vers_scene(0, 0), vers_scene(0, 1000)
    loin = Vector((haut[0] + x1 - x0, haut[1] + y1 - y0))
    croisements = [(k, geometry.intersect_line_line_2d(Vector(haut), loin, Vector(anneau[k]), Vector(anneau[(k + 1) % n])))
                   for k in range(n)]
    k, nord = min(((k, tuple(x)) for k, x in croisements if x is not None), key=lambda e: math.dist(haut, e[1]))
    avant = [anneau[(sud + i) % n] for i in range((k - sud) % n + 1)] + [nord]
    arriere = [anneau[(sud - i) % n] for i in range((sud - k - 1) % n + 1)] + [nord]
    pres_du_kotel = lambda cote: min(_distance_a_la_trace(p, KOTEL) for p in cote)
    priere, haute = sorted((avant, arriere), key=pres_du_kotel)
    retour = ligne[::-1]
    return priere + retour, haute + retour, (ligne[0], anneau[sud]), (haut, nord)


AIRE_DE_PRIERE, PLACE_HAUTE, BRECHE_DES_FEMMES, BRECHE_DES_HOMMES = _coupe_par_le_muret()
# L'aire des femmes ne s'arrête pas à la clôture d'OSM : elle passe sous le pont jusqu'au mur de
# l'ancienne rampe des Maghrébins (vue plongeante de 2017, où l'on prie entre les palées). Relevée
# sur le plan OSM, de cette clôture aux ruines de la rampe (w…61626) : nord-ouest, nord-est, deux
# sommets de la place au pied du Kotel, puis le pied du mur de la rampe d'est en ouest.
SOUS_LE_PONT = [vers_scene(*p) for p in ((-119.6, -171.0), (-97.1, -166.7), (-95.0, -175.0), (-91.0, -174.0), (-90.5, -177.0),
                                         (-97.0, -177.2), (-118.4, -177.6))]


def _coin(est, nord):
    """Le sommet de la place le plus proche d'un point d'OSM, en mètres."""
    return min(PLACE_KOTEL, key=lambda p: math.dist(p, vers_scene(est, nord)))


# Le bord nord de la place, de la Ma'hkama à l'escalier du quartier juif : la galerie à
# arcades sur ses trois premiers côtés, le bâtiment de la Fondation sur le dernier.
BORD_NORD = [_coin(-122, -127), _coin(-134, -130), _coin(-145, -132), _coin(-149, -132), _coin(-184, -140)]
# Au sud de la place, le parc des voitures de police et les contrôles de la porte des
# Ordures, de plain-pied jusqu'à la muraille : relevé sur le plan OSM, entre le mur du
# quartier juif (w288016750) et celui du parc archéologique (w394161622).
ESPLANADE_SUD = [vers_scene(*p) for p in (
    (-172, -225), (-166, -218), (-150, -215), (-145, -214), (-139, -247), (-133, -246), (-130, -255), (-128, -269),
    (-119, -319), (-116, -345), (-165, -345), (-170, -300), (-186, -262), (-185, -241), (-177, -233))]
PENTE_DES_HOMMES = 12    # longueur pour un de hauteur, la pente des rampes accessibles : CHOIX
LARGEUR_PASSAGE, HAUTEUR_PASSAGE, PROFONDEUR_PASSAGE = 3.5 / AMA, 3.2 / AMA, 4 / AMA


class Bouche(NamedTuple):
    centre: tuple
    dehors: tuple


def _bouche(trace, marge=1 / AMA):
    """Où un passage d'OSM quitte la place : sur le côté le plus proche de sa trace, assez long
    pour la porte, sans mordre sur ses coins."""
    anneau = PLACE_KOTEL
    cotes = [(a, b) for a, b in zip(anneau, anneau[1:] + anneau[:1]) if math.dist(a, b) > LARGEUR_PASSAGE + 2 * marge]
    points = [_point_a_l_abscisse(trace, s)[0] for s in plage(0, _abscisses(trace)[-1], 1)] + [trace[-1]]
    a, b = min(cotes, key=lambda e: min(_distance_au_segment(p, *e) for p in points))
    p = min(points, key=lambda p: _distance_au_segment(p, a, b))
    long_ = math.dist(a, b)
    s = min(max(_fraction_sur_le_segment(p, a, b) * long_, LARGEUR_PASSAGE / 2 + marge), long_ - LARGEUR_PASSAGE / 2 - marge)
    t = ((b[0] - a[0]) / long_, (b[1] - a[1]) / long_)
    centre = (a[0] + t[0] * s, a[1] + t[1] * s)
    dehors = (t[1], -t[0]) if not _dans((centre[0] + t[1], centre[1] - t[0]), anneau) else (-t[1], t[0])
    return Bouche(centre, dehors)


BOUCHES = [_bouche([vers_scene(*p) for p in trace]) for trace in PAYS_DONNEES["passages_place"].values()]


def _vers_l_aire(breche):
    """La brèche orientée l'aire de prière à sa gauche."""
    a, b = breche
    milieu = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return (a, b) if _dans(_devant(milieu, _cap(a, b), 0, 1), AIRE_DE_PRIERE) else (b, a)


def _pente_des_hommes():
    """L'axe de la pente, du haut de la brèche vers l'aire de prière : (haut, bas)."""
    a, b = _vers_l_aire(BRECHE_DES_HOMMES)
    milieu = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return milieu, _devant(milieu, _cap(a, b), 0, (Z_PLACE_HAUTE - Z_PLACE_KOTEL) * PENTE_DES_HOMMES)


def marches_de_l_aire_de_priere(contremarche=0.15 / AMA, giron=0.35 / AMA):
    """Des degrés descendent à l'aire de prière par la brèche des femmes, une pente par celle
    des hommes. Le giron : CHOIX."""
    n = round((Z_PLACE_HAUTE - Z_PLACE_KOTEL) / contremarche)
    a, b = _vers_l_aire(BRECHE_DES_FEMMES)
    boites = []
    for k in range(n - 1):
        z = Z_PLACE_HAUTE - (Z_PLACE_HAUTE - Z_PLACE_KOTEL) * (k + 1) / n
        boites.append(_poutre(a, b, Z_PLACE_KOTEL - 1, Z_PLACE_KOTEL - 1, (k + 1) * giron, k * giron, z - Z_PLACE_KOTEL + 1))
    mesh_from_pydata("Kotel_place_marches", *_assembler(boites), "00_HarHabayit", MAT_DALLAGE_DE_PRIERE())
    haut, bas = _pente_des_hommes()
    demi = math.dist(*BRECHE_DES_HOMMES) / 2
    pente = _poutre(haut, bas, Z_PLACE_HAUTE - 1, Z_PLACE_KOTEL - 1, demi, -demi, 1)
    mesh_from_pydata("Kotel_place_pente", *_assembler([pente]), "00_HarHabayit", MAT_DALLAGE_DE_PRIERE())


def passages_de_la_place(bords, recouvrement=2):
    """Les passages d'OSM vers la rue HaGaï, Batei Ma'hasse et la porte des Ordures, percés
    dans le soutènement : couverts sur la profondeur d'une porte, bouchés au-delà — le relief du
    modèle, qui met la place elle-même treize mètres trop haut, ne dit pas à quelle cote ils
    rejoignent la ville. Largeur, hauteur, profondeur : CHOIX."""
    demi, cote = LARGEUR_PASSAGE / 2, LARGEUR_PASSAGE / 2 + recouvrement
    murs, sols = [], []
    for bouche in BOUCHES:
        tetes = [z1 for anneau, _, _, z1 in bords if _distance_a_l_anneau(bouche.centre, anneau) < LARGEUR_PASSAGE]
        if not tetes:
            continue
        haut = max(tetes)
        entree = bouche.centre
        fond = _devant(entree, _cap((0, 0), bouche.dehors), PROFONDEUR_PASSAGE)
        bout = _devant(entree, _cap((0, 0), bouche.dehors), MAILLE_PAYS)
        pied = Z_PLACE_KOTEL - 1
        sols.append(_poutre(entree, fond, pied, pied, demi, -demi, Z_PLACE_HAUTE - pied))
        murs += [_poutre(entree, fond, pied, pied, cote, demi, haut - pied),
                 _poutre(entree, fond, pied, pied, -demi, -cote, haut - pied),
                 _poutre(fond, bout, pied, pied, cote, -cote, haut - pied)]
        if haut > Z_PLACE_HAUTE + HAUTEUR_PASSAGE:
            linteau = Z_PLACE_HAUTE + HAUTEUR_PASSAGE
            murs.append(_poutre(entree, fond, linteau, linteau, cote, -cote, haut - linteau))
    mesh_from_pydata("Kotel_place_passages", *_assembler(murs), "00_HarHabayit", MAT_MURAILLE())
    mesh_from_pydata("Kotel_place_passages_sol", *_assembler(sols), "00_HarHabayit", MAT_SOL())


def _sur_la_place(p):
    return _dans(p, PLACE_KOTEL) or _dans(p, SOUS_LE_PONT) or _distance_a_l_anneau(p, PLACE_KOTEL) < 2


def _sol_de_la_place(p):
    en_bas = _dans(p, AIRE_DE_PRIERE) or _dans(p, SOUS_LE_PONT) or _distance_a_l_anneau(p, AIRE_DE_PRIERE) < 0.5
    return Z_PLACE_KOTEL if en_bas else Z_PLACE_HAUTE


def _sol_du_detail(p):
    return _sol_de_la_place(p) if _sur_la_place(p) else sol_naturel(*p)


def _cap(de, vers):
    return math.atan2(vers[1] - de[1], vers[0] - de[0])


def _devant(p, cap, avant, travers=0.0):
    """Le point à `avant` sur le cap et `travers` à sa gauche."""
    c, s = math.cos(cap), math.sin(cap)
    return (p[0] + c * avant - s * travers, p[1] + s * avant + c * travers)


def _pave(centre, cap, longueur, largeur, z0, z1):
    """Une boîte de z0 à z1, `longueur` le long du cap (radians), `largeur` en travers."""
    a, b = _devant(centre, cap, -longueur / 2), _devant(centre, cap, longueur / 2)
    return _poutre(a, b, z0, z0, largeur / 2, -largeur / 2, z1 - z0), FACES_BOITE


def _fut(centre, z0, z1, r, cotes=8):
    anneau = _cercle(*centre, r, cotes)
    n = len(anneau)
    verts = [(x, y, z0) for x, y in anneau] + [(x, y, z1) for x, y in anneau]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    return verts, faces + [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]


def _coupole(centre, z, r, cotes=12, rangs=4):
    anneaux = [[(x, y, z + r * math.sin(math.pi / 2 * k / rangs))
                for x, y in _cercle(*centre, r * math.cos(math.pi / 2 * k / rangs), cotes)] for k in range(rangs)]
    verts = [p for anneau in anneaux for p in anneau] + [(*centre, z + r)]
    faces = [[k * cotes + i, k * cotes + (i + 1) % cotes, (k + 1) * cotes + (i + 1) % cotes, (k + 1) * cotes + i]
             for k in range(rangs - 1) for i in range(cotes)]
    sommet, dernier = len(verts) - 1, (rangs - 1) * cotes
    return verts, faces + [[dernier + i, dernier + (i + 1) % cotes, sommet] for i in range(cotes)]


def _pyramide(centre, z0, z1, rayon, cotes=4, tourne=0.0):
    anneau = [(centre[0] + rayon * math.cos(tourne + 2 * math.pi * i / cotes), centre[1] + rayon * math.sin(tourne + 2 * math.pi * i / cotes), z0)
              for i in range(cotes)]
    return anneau + [(*centre, z1)], [list(range(cotes))[::-1]] + [[i, (i + 1) % cotes, cotes] for i in range(cotes)]


def _baie(p, q, s, z0, largeur, hauteur, saillie):
    """Une baie cintrée plaquée sur le mur p→q, à `s` de p, de son seuil z0 à sa clé, tournée
    du côté gauche de p→q ; `saillie` devant le parement."""
    t = ((q[0] - p[0]) / math.dist(p, q), (q[1] - p[1]) / math.dist(p, q))
    n = (-t[1], t[0])
    r = largeur / 2
    contour = [(-r, 0), (r, 0)] + [(r * math.cos(math.pi * k / 6), hauteur - r + r * math.sin(math.pi * k / 6))
                                   for k in range(7)]
    def monde(ds, dz, d):
        return (p[0] + t[0] * (s + ds) + n[0] * d, p[1] + t[1] * (s + ds) + n[1] * d, z0 + dz)
    k = len(contour)
    verts = [monde(ds, dz, saillie) for ds, dz in contour] + [monde(ds, dz, -0.02) for ds, dz in contour]
    faces = [list(range(k))[::-1], list(range(k, 2 * k))]
    return verts, faces + [[i, (i + 1) % k, k + (i + 1) % k, k + i] for i in range(k)]


def _chaise(p, cap, z):
    """Fauteuil monobloc de plastique blanc tourné vers le cap : assise, dossier, accoudoirs, quatre pieds."""
    assise, pied = 0.45 / AMA, 0.03 / AMA
    morceaux = [_pave(p, cap, assise, assise, z + 0.42 / AMA, z + 0.46 / AMA),
                _pave(_devant(p, cap, -assise / 2), cap, 0.04 / AMA, assise, z + 0.46 / AMA, z + 0.9 / AMA)]
    for st in (-1, 1):
        morceaux += [_pave(_devant(p, cap, -0.02 / AMA, st * assise * 0.52), cap, assise, 0.05 / AMA, z + 0.64 / AMA, z + 0.67 / AMA),
                     _pave(_devant(p, cap, assise * 0.42, st * assise * 0.52), cap, pied, pied, z + 0.46 / AMA, z + 0.64 / AMA)]
    return morceaux + [_pave(_devant(p, cap, sa * assise * 0.42, st * assise * 0.42), cap, pied, pied, z, z + 0.42 / AMA)
                       for sa in (-1, 1) for st in (-1, 1)]


def _table(p, cap, z):
    plateau = [_pave(p, cap, 0.5 / AMA, 0.8 / AMA, z + 0.72 / AMA, z + 0.76 / AMA)]
    return plateau + [_pave(_devant(p, cap, sa * 0.2 / AMA, st * 0.35 / AMA), cap, 0.04 / AMA, 0.04 / AMA, z, z + 0.72 / AMA)
                      for sa in (-1, 1) for st in (-1, 1)]


def _bibliotheque(nom, p, cap, longueur, hauteur, z, rayon=0.4 / AMA, profondeur=0.35 / AMA):
    """Un meuble ouvert vers le cap : (planches, [livres de chaque reliure]). Les livres vont par
    paquets d'une même reliure, d'une hauteur chacun."""
    planche = 0.03 / AMA
    bois = [_pave(_devant(p, cap, -profondeur / 2), cap, planche, longueur, z, z + hauteur)]
    bois += [_pave(_devant(p, cap, 0, t * longueur / 2), cap, profondeur, planche, z, z + hauteur) for t in (-1, 1)]
    niveaux = plage(0, hauteur - rayon, rayon)
    bois += [_pave(p, cap, profondeur, longueur, z + h, z + h + planche) for h in niveaux + [hauteur - planche]]
    livres = [[] for _ in MAT_RELIURES]
    for i, h in enumerate(niveaux):
        x = -longueur / 2 + planche
        while True:
            k = f"{nom}_{i}_{x:.2f}"
            paquet = (0.1 + 0.25 * alea(k)) / AMA
            if x + paquet > longueur / 2 - planche:
                break
            haut = min(rayon - 0.06 / AMA, (0.2 + 0.12 * alea(k, 1)) / AMA)
            livres[int(alea(k, 2) * len(livres))].append(
                _pave(_devant(p, cap, 0, -(x + paquet / 2)), cap, 0.22 / AMA, paquet - 0.01 / AMA,
                      z + h + planche, z + h + planche + haut))
            x += paquet
    return bois, livres


def _poser(nom, morceaux, mat, col="00_HarHabayit"):
    if morceaux:
        mesh_from_pydata(nom, *_fondre(morceaux), col, mat)


def _poser_les_livres(nom, livres, col="00_HarHabayit"):
    for k, (paquets, mat) in enumerate(zip(livres, MAT_RELIURES)):
        _poser(f"{nom}_{k}", paquets, mat(), col)


def interieur_de_wilson():
    """La salle sous l'arche : l'aron qui garde plus de cent sifrei Torah, la bibliothèque et
    les rayonnages de la rénovation de 2005–2008, le ner tamid allumé en 2010, et le puits qui
    montre quatorze assises sous le sol (Wikipedia, « Wilson's Arch » ; thekotel.org). Leur
    place dans la salle, le mobilier et ses mesures : CHOIX."""
    _, u, v, longueur, _ = WILSON
    vers_kotel, le_long, en_travers = math.atan2(-v[1], -v[0]), math.atan2(u[1], u[0]), math.atan2(v[1], v[0])
    z = Z_PLACE_KOTEL
    # Contre le Kotel, la voûte descend sous le mètre : l'aron est au fond, sous la clé.
    fond, axe = longueur - 1, PORTEE_WILSON / 2
    aron = _point_de_wilson(fond - 0.55 / AMA, axe)
    _poser("Wilson_aron", [_pave(aron, en_travers, 5.4 / AMA, 1.1 / AMA, z, z + 0.3 / AMA),
                           _pave(aron, en_travers, 5 / AMA, 0.9 / AMA, z + 0.3 / AMA, z + 3.2 / AMA),
                           _pave(aron, en_travers, 5.4 / AMA, 1.1 / AMA, z + 3.2 / AMA, z + 3.45 / AMA)], MAT_CHENE())
    ner = _point_de_wilson(fond - 1.8 / AMA, axe)
    _poser("Wilson_ner_tamid", [_fut(ner, z + 3.7 / AMA, z + 3.95 / AMA, 0.12 / AMA),
                                _fut(ner, z + 3.95 / AMA, _sous_la_voute(axe), 0.01 / AMA, 4)], MAT_BRONZE())

    puits = _point_de_wilson(longueur * 0.25, 2.8 / AMA)
    cote = 2 / AMA
    _poser("Wilson_puits", [_pave(puits, le_long, cote, cote, z, z + 0.01 / AMA)], material("Puits", (0.02, 0.02, 0.02)))
    garde = [_pave(_devant(puits, le_long + a, cote / 2), le_long + a + math.pi / 2, cote, 0.05 / AMA,
                   z + 1.0 / AMA, z + 1.05 / AMA) for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    garde += [_fut(_devant(puits, le_long, sa * cote / 2, st * cote / 2), z, z + 1.05 / AMA, 0.03 / AMA, 6)
              for sa in (-1, 1) for st in (-1, 1)]
    _poser("Wilson_puits_garde_corps", garde, MAT_INOX())

    bois, livres = [], [[] for _ in MAT_RELIURES]
    for k, pu in enumerate(plage(1.5 / AMA, longueur - 2.5 / AMA, 2.2 / AMA)):
        b, l = _bibliotheque(f"Wilson_biblio_{k}", _point_de_wilson(pu, PORTEE_WILSON - 1.2 / AMA),
                             vers_kotel, 2 / AMA, 1.9 / AMA, z)
        bois += b
        livres = [a + c for a, c in zip(livres, l)]
    _poser("Wilson_bibliotheque", bois, MAT_CHENE())
    _poser_les_livres("Wilson_livres", livres)

    chaises, tables = [], []
    for pu in plage(2 / AMA, longueur - 2 / AMA, 1.6 / AMA):
        for pv in plage(2.6 / AMA, PORTEE_WILSON - 2.4 / AMA, 1.4 / AMA):
            p = _point_de_wilson(pu, pv)
            if pu > fond - 3 / AMA or math.dist(p, puits) < 2.5 / AMA:
                continue
            nom = f"Wilson_chaise_{pu:.0f}_{pv:.0f}"
            if alea(nom) < 0.12:
                tables += _table(p, vers_kotel, z)
            elif alea(nom, 1) < 0.75:
                chaises += _chaise(p, vers_kotel + 0.4 * (alea(nom, 2) - 0.5), z)
    _poser("Wilson_chaises", chaises, MAT_PLASTIQUE())
    _poser("Wilson_tables", tables, MAT_PLASTIQUE())


def _ligne(trace, hauteur, epaisseur):
    return [(_poutre(a, b, _sol_du_detail(a) - 0.3, _sol_du_detail(b) - 0.3, epaisseur / 2, -epaisseur / 2,
                     hauteur + 0.3), FACES_BOITE) for a, b in zip(trace, trace[1:]) if math.dist(a, b) > 1e-6]


def _main_courante(trace, z_a_l_abscisse, hauteur=0.95 / AMA, pas=2 / AMA):
    """La rampe au milieu d'un escalier : une lisse et ses potelets, à la cote que donne `z_a_l_abscisse`."""
    longueur = _abscisses(trace)[-1]
    stations = [(s, _point_a_l_abscisse(trace, s)[0], z_a_l_abscisse(s)) for s in plage(0, longueur, pas) + [longueur]]
    pieces = [_fut(p, z, z + hauteur, 0.025 / AMA, 4) for _, p, z in stations]
    return pieces + [(_poutre(p, q, zp + hauteur, zq + hauteur, 0.025 / AMA, -0.025 / AMA, 0.05 / AMA), FACES_BOITE)
                     for (_, p, zp), (_, q, zq) in zip(stations, stations[1:]) if math.dist(p, q) > 1e-6]


def _grille(trace, hauteur=1.1 / AMA, pas=0.5 / AMA):
    """Un garde-corps de fer brun qui suit le sol : deux lisses hautes, une basse, des barreaux
    et un potelet tous les quatre barreaux."""
    pieces = []
    for a, b in zip(trace, trace[1:]):
        za, zb = _sol_du_detail(a), _sol_du_detail(b)
        pieces += [(_poutre(a, b, za + h, zb + h, 0.02 / AMA, -0.02 / AMA, 0.04 / AMA), FACES_BOITE)
                   for h in (0.1 / AMA, hauteur - 0.2 / AMA, hauteur - 0.04 / AMA)]
    longueur = _abscisses(trace)[-1]
    for k, abscisse in enumerate(plage(0, longueur, pas) + [longueur]):
        p, _ = _point_a_l_abscisse(trace, abscisse)
        z = _sol_du_detail(p)
        pieces.append(_fut(p, z, z + hauteur, (0.035 if k % 4 == 0 else 0.012) / AMA, 4))
    return pieces


def _treillis(a, b, z0, z1, pas, saillie):
    """Des fers plats croisés à 45° entre a et b, de z0 à z1, qui dépassent de `saillie` de part et d'autre."""
    longueur, haut = math.dist(a, b), z1 - z0
    cap = _cap(a, b)
    fers = []
    for c in plage(-haut + pas / 2, longueur, pas):
        x0, x1 = max(0.0, c), min(longueur, c + haut)
        if x1 - x0 < pas / 4:
            continue
        p, q = _devant(a, cap, x0), _devant(a, cap, x1)
        fers += [(_poutre(p, q, z0 + x0 - c, z0 + x1 - c, saillie, -saillie, 0.04 / AMA), FACES_BOITE),
                 (_poutre(p, q, z1 - (x0 - c), z1 - (x1 - c), saillie, -saillie, 0.04 / AMA), FACES_BOITE)]
    return fers


def _poteaux(trace, pas, hauteur, r):
    s = _abscisses(trace)
    return [_fut(p, _sol_du_detail(p), _sol_du_detail(p) + hauteur, r, 6)
            for p, _ in (_point_a_l_abscisse(trace, a) for a in plage(0, s[-1], pas))]


def _dans_l_aire_de_priere(p):
    """À l'est du muret de pierre qui sépare la place haute de l'aire de prière, au nord de la
    clôture de bois du côté des femmes ou sous le pont, et pas contre le Kotel."""
    if _dans(p, SOUS_LE_PONT):
        return _distance_a_la_trace(p, KOTEL) >= 1.5 / AMA
    if not _dans(p, PLACE_KOTEL) or _dans(p, SALLES_WILSON) or _distance_a_la_trace(p, KOTEL) < 1.5 / AMA:
        return False
    muret = _trace_osm(MURET_DE_PRIERE)
    a, b = next(((a, b) for a, b in zip(muret, muret[1:]) if min(a[1], b[1]) <= p[1] <= max(a[1], b[1])), (None, None))
    if a is None or p[0] < a[0] + (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1] or 1e-9):
        return False
    femmes = _trace_osm(CLOTURE_DES_FEMMES)
    return all(p[1] > a[1] + (b[1] - a[1]) * (p[0] - a[0]) / (b[0] - a[0] or 1e-9)
               for a, b in zip(femmes, femmes[1:]) if min(a[0], b[0]) <= p[0] <= max(a[0], b[0]))


def mobilier_de_la_place():
    """Le mobilier d'OSM, sur la place et à ses entrées."""
    bronze, inox = [], []
    for k, (p,) in enumerate(_abords("netilat_yadayim")):
        # Les postes posés à la fin des années 2010 : une vasque de pierre à six pans sur un
        # pied, ses flancs garnis de rinceaux de bronze, autour d'un fût à six pans coiffé en
        # pointe qui porte les robinets, les natlot posées sur le bord. Cotes : CHOIX.
        z = _sol_du_detail(p)
        revolution(f"Kotel_place_netilat_{k}_vasque", *p, z,
                   [(0.38 / AMA, 0), (0.38 / AMA, 0.5 / AMA), (1.0 / AMA, 0.62 / AMA), (1.0 / AMA, 0.98 / AMA), (0.86 / AMA, 0.98 / AMA),
                    (0.86 / AMA, 0.74 / AMA), (0.24 / AMA, 0.74 / AMA), (0.24 / AMA, 1.75 / AMA), (0.3 / AMA, 1.8 / AMA), (0, 2.05 / AMA)],
                   "00_HarHabayit", MAT_PIERRE(), verts=6)
        bronze.append(_fut(p, z + 0.67 / AMA, z + 0.93 / AMA, 1.02 / AMA, 6))
        for i in range(6):
            a = 2 * math.pi * (i + 0.5) / 6
            inox.append(_pave(_devant(p, a, 0.3 / AMA), a, 0.22 / AMA, 0.04 / AMA, z + 1.25 / AMA, z + 1.29 / AMA))
            inox.append(_fut(_devant(p, a + 0.3, 0.9 / AMA), z + 0.98 / AMA, z + 1.13 / AMA, 0.06 / AMA, 6))
    _poser("Kotel_place_netilat_rinceaux", bronze, MAT_BRONZE())
    _poser("Kotel_place_netilat_robinets", inox, MAT_INOX())

    fontaines, becs = [], []
    for (p,) in _abords("fontaine"):
        if _sur_la_place(p):
            z = _sol_de_la_place(p)
            fontaines.append(_pave(p, 0, 0.45 / AMA, 0.45 / AMA, z, z + 0.95 / AMA))
            becs.append(_fut(p, z + 0.95 / AMA, z + 1.0 / AMA, 0.2 / AMA))
    _poser("Kotel_place_fontaines", fontaines, MAT_PIERRE())
    _poser("Kotel_place_fontaines_becs", becs, MAT_INOX())
    _poser("Kotel_place_poubelles", [_pave(p, 0, 0.45 / AMA, 0.45 / AMA, _sol_de_la_place(p), _sol_de_la_place(p) + 0.9 / AMA)
                                     for (p,) in _abords("poubelle") if _sur_la_place(p)], MAT_INOX())
    _poser("Kotel_place_borne_incendie", [_fut(p, _sol_de_la_place(p), _sol_de_la_place(p) + 0.7 / AMA, 0.1 / AMA)
                                          for (p,) in _abords("borne_incendie") if _sur_la_place(p)],
           MAT_BORNE_INCENDIE())

    # La mehitsa : deux mètres de fers dorés croisés devant un fond sombre, entre des montants
    # (OSM la dit de métal ; son dessin et sa hauteur se lisent sur les photos). La clôture du
    # côté des femmes est de bois ; elle ne commence qu'à l'ouest du prolongement de leur aire sous le pont.
    # Les autres clôtures sont les garde-corps de fer brun de
    # la place ; leurs hauteurs et celles des murets : CHOIX.
    mehitsa = _trace_osm(MEHITSA)
    _poser("Kotel_place_mehitsa_fond", _ligne(mehitsa, 1.95 / AMA, 0.03 / AMA), MAT_FER_BRUN())
    _poser("Kotel_place_mehitsa", [fer for a, b in zip(mehitsa, mehitsa[1:])
                                   for fer in _treillis(a, b, _sol_du_detail(a) + 0.1 / AMA, _sol_du_detail(a) + 1.95 / AMA, 0.3 / AMA, 0.03 / AMA)],
           MAT_MEHITSA())
    _poser("Kotel_place_mehitsa_montants", _poteaux(mehitsa, 1.6 / AMA, 2.08 / AMA, 0.05 / AMA), MAT_FER_BRUN())
    _poser("Kotel_place_cloture_bois", _ligne(_trace_osm(CLOTURE_DES_FEMMES)[2:], 1.8 / AMA, 0.08 / AMA), MAT_CHENE())
    a_part = (MEHITSA, CLOTURE_DES_FEMMES, CLOTURE_DEVANT_LA_FONDATION)
    clotures = [piece for a in ABORDS if a["genre"] == "cloture" and a["osm"] not in a_part for piece in _grille(_trace_osm(a["osm"]))]
    murets = [piece for a in ABORDS if a["genre"] == "muret" and a["osm"] != MURET_DE_PRIERE
              for piece in _ligne(_trace_osm(a["osm"]), (2.5 if a["osm"] == MUR_ANTIBRUIT else 0.9) / AMA, 0.45 / AMA)]
    _poser("Kotel_place_clotures", clotures, MAT_FER_BRUN())
    _poser("Kotel_place_bornes", [p for t in _abords("bornes") for p in _poteaux(t, 1.5 / AMA, 0.9 / AMA, 0.1 / AMA)], MAT_INOX())
    _poser("Kotel_place_murets", murets, MAT_PIERRE())

    # Aux entrées, un portique détecteur et le tunnel à rayons X des sacs (Times of Israel),
    # tournés vers la place.
    centre = (sum(x for x, _ in PLACE_KOTEL) / len(PLACE_KOTEL), sum(y for _, y in PLACE_KOTEL) / len(PLACE_KOTEL))
    portiques = []
    for (p,) in _abords("controle"):
        z, cap = _sol_du_detail(p), _cap(p, centre)
        portiques += [_pave(_devant(p, cap, 0, t * 0.5 / AMA), cap, 0.6 / AMA, 0.15 / AMA, z, z + 2.2 / AMA) for t in (-1, 1)]
        portiques += [_pave(p, cap, 0.6 / AMA, 1.15 / AMA, z + 2.2 / AMA, z + 2.45 / AMA),
                      _pave(_devant(p, cap, 0, 1.5 / AMA), cap, 2.2 / AMA, 0.9 / AMA, z, z + 1.3 / AMA)]
    _poser("Kotel_place_controles", portiques, MAT_PORTIQUE())

    # Chaises et tables de plastique blanc : un millier livrées en 2020 (thekotel.org) ; leur
    # nombre et leur désordre ici : CHOIX. Les étagères de siddourim au bord de l'aire de prière.
    muret = _trace_osm(MURET_DE_PRIERE)
    etageres = []
    for f in (0.15, 0.45, 0.75):
        p, (tx, ty) = _point_a_l_abscisse(muret, f * _abscisses(muret)[-1])
        cap = math.atan2(tx, -ty)
        if not _dans_l_aire_de_priere(_devant(p, cap, 2)):
            cap += math.pi
        etageres.append((_devant(p, cap, 0.45 / AMA), cap))
    bois, livres = [], [[] for _ in MAT_RELIURES]
    for k, (p, cap) in enumerate(etageres):
        b, l = _bibliotheque(f"Kotel_place_siddourim_{k}", p, cap, 1.8 / AMA, 1.6 / AMA, Z_PLACE_KOTEL)
        bois += b
        livres = [a + c for a, c in zip(livres, l)]
    _poser("Kotel_place_etageres", bois, MAT_CHENE())
    _poser_les_livres("Kotel_place_siddourim", livres)
    obstacles = [p for p, *_ in etageres] + [p for (p,) in _abords("netilat_yadayim")]
    chaises = []
    xs, ys = [x for x, _ in PLACE_KOTEL], [y for _, y in PLACE_KOTEL]
    pas = 1.7 / AMA
    for x in plage(min(xs), max(xs), pas):
        for y in plage(min(ys), max(ys), pas):
            nom = f"Kotel_place_chaise_{x:.0f}_{y:.0f}"
            p = (x + pas * 0.6 * (alea(nom, 3) - 0.5), y + pas * 0.6 * (alea(nom, 4) - 0.5))
            if (alea(nom) > 0.45 or not _dans_l_aire_de_priere(p) or any(math.dist(p, o) < 3 / AMA for o in obstacles)
                    or min(_distance_a_la_trace(p, _trace_osm(osm)) for osm in (MEHITSA, CLOTURE_DES_FEMMES, MURET_DE_PRIERE)) < 1 / AMA
                    or _distance_au_segment(p, *BRECHE_DES_FEMMES) < 2 / AMA
                    or _distance_au_segment(p, *_pente_des_hommes()) < math.dist(*BRECHE_DES_HOMMES) / 2 + 1 / AMA):
                continue
            vers_kotel = _cap(p, _plus_proche_sur_la_trace(p, KOTEL))
            chaises += _chaise(p, vers_kotel + 0.9 * (alea(nom, 2) - 0.5), Z_PLACE_KOTEL)
    _poser("Kotel_place_chaises", chaises, MAT_PLASTIQUE())


def _vers_l_aire_de_priere(p, cap):
    """Le côté du cap où est l'aire de prière : 1 à gauche, -1 à droite."""
    return 1 if _dans(_devant(p, cap, 0, 1.5), AIRE_DE_PRIERE) else -1


def muret_de_priere(panneau=2.4 / AMA, joint=0.3 / AMA, epaisseur=0.5 / AMA):
    """Le muret de 1979 qui tient la place haute (Bahat) : un socle continu, coiffé de panneaux
    de pierre taillés en biseau vers l'aire de prière, une grille de fer dans chaque joint sous une lisse continue, et
    un banc de pierre au pied de chaque panneau, des deux côtés. Son dernier tronçon, le long de
    la pente des hommes, n'est pas bâti. Longueur des panneaux et joints : lus sur les photos."""
    muret = _trace_osm(MURET_DE_PRIERE)[:-1]
    pied, tete = Z_PLACE_KOTEL - 0.3, Z_PLACE_HAUTE + PARAPET_DE_PRIERE + 0.25 / AMA
    socle = [(_poutre(a, b, pied, pied, epaisseur / 2, -epaisseur / 2, Z_PLACE_HAUTE + 0.1 - pied), FACES_BOITE)
             for a, b in zip(muret, muret[1:])]
    panneaux, grilles, bancs = [], [], []
    for a, b in zip(muret, muret[1:]):
        cap, longueur = _cap(a, b), math.dist(a, b)
        n = max(1, int(longueur / (panneau + joint)))
        pas = longueur / n
        cote = _vers_l_aire_de_priere(_devant(a, cap, longueur / 2), cap)
        vers_l_aire = (-math.sin(cap) * cote, math.cos(cap) * cote)
        profil = [(-epaisseur / 2, Z_PLACE_HAUTE), (epaisseur / 2, Z_PLACE_HAUTE), (epaisseur / 2, tete - 0.3 / AMA), (-epaisseur / 2, tete)]
        for k in range(n):
            panneaux.append(_extrusion(profil, _devant(a, cap, k * pas + joint / 2), (math.cos(cap), math.sin(cap)), vers_l_aire, pas - joint))
            grilles.append(_pave(_devant(a, cap, k * pas), cap, joint, 0.04 / AMA, Z_PLACE_HAUTE, tete + 0.04 / AMA))
            bancs.append(_pave(_devant(a, cap, (k + 0.5) * pas, cote * (epaisseur / 2 + 0.25 / AMA)), cap, pas * 0.6, 0.45 / AMA,
                               Z_PLACE_KOTEL, Z_PLACE_KOTEL + 0.45 / AMA))
            bancs.append(_pave(_devant(a, cap, (k + 0.5) * pas, -cote * (epaisseur / 2 + 0.22 / AMA)), cap, pas * 0.75, 0.4 / AMA,
                               Z_PLACE_HAUTE, Z_PLACE_HAUTE + 0.45 / AMA))
        grilles.append((_poutre(a, b, tete + 0.04 / AMA, tete + 0.04 / AMA, 0.04 / AMA, -0.04 / AMA, 0.06 / AMA), FACES_BOITE))
    _poser("Kotel_place_muret_socle", socle + bancs, MAT_PIERRE())
    _poser("Kotel_place_muret_panneaux", panneaux, MAT_PIERRE())
    _poser("Kotel_place_muret_grilles", grilles, MAT_FER_BRUN())


def arret_de_bus():
    """L'arrêt « הכותל המערבי » d'OSM, des lignes 1, 2, 3, 51, 83… : un abri tourné vers la
    voie des bus la plus proche. L'abri et ses mesures : CHOIX, faute de relevé."""
    (p,), = _abords("arret_bus")
    voie = min((t for t in _abords("voie_bus") if len(t) > 1), key=lambda t: _distance_a_la_trace(p, t))
    cap = _cap(p, _plus_proche_sur_la_trace(p, voie))
    z = sol_naturel(*p)
    long_ = 4 / AMA
    cadre = [_pave(_devant(p, cap, a / AMA, t * long_ / 2), cap, 0.08 / AMA, 0.08 / AMA, z, z + 2.45 / AMA)
             for a in (-0.7, 0.6) for t in (-1, 1)]
    cadre += [_pave(_devant(p, cap, -0.05 / AMA), cap, 1.6 / AMA, long_ + 0.2 / AMA, z + 2.4 / AMA, z + 2.5 / AMA),
              _pave(_devant(p, cap, -0.45 / AMA), cap, 0.4 / AMA, 2.5 / AMA, z + 0.42 / AMA, z + 0.47 / AMA),
              _fut(_devant(p, cap, 0.6 / AMA, long_ / 2 + 0.8 / AMA), z, z + 2.8 / AMA, 0.04 / AMA, 6),
              _pave(_devant(p, cap, 0.6 / AMA, long_ / 2 + 0.8 / AMA), cap + math.pi / 2, 0.5 / AMA, 0.03 / AMA,
                    z + 2.3 / AMA, z + 2.8 / AMA)]
    _poser("Arret_bus_kotel", cadre, MAT_INOX())
    _poser("Arret_bus_kotel_vitres", [_pave(_devant(p, cap, -0.7 / AMA), cap, 0.03 / AMA, long_, z + 0.2 / AMA, z + 2.3 / AMA)],
           MAT_VITRE())


def menora_d_or():
    """La menora d'or de l'Institut du Temple, sur l'escalier du quartier juif vers la place
    (OSM) : plus de deux mètres, une demi-tonne dont 45 kg d'or, trois pieds et sept branches,
    sur un socle de pierre, sous une vitrine qu'on ne modélise pas. Celle-ci a les branches
    cintrées ; l'Institut en a fait une autre, droite, d'après le dessin du Rambam (Israel365
    News). Dans le plan qui regarde le Har HaBayit."""
    p = _trace_osm(MENORA)[0]
    sol = sol_naturel(*p)
    z = sol + 1 / AMA
    travers = math.pi / 2
    _poser("Menora_d_or_socle", [_pave(p, travers, 1.4 / AMA, 0.8 / AMA, sol - 0.3 / AMA, z)], MAT_PIERRE())
    tige = 0.07 / AMA
    pieds = [_poutre(p, _devant(p, a, 0.3 / AMA), z + 0.35 / AMA, z, tige / 2, -tige / 2, tige)
             for a in (0, 2 * math.pi / 3, 4 * math.pi / 3)]
    branches = []
    for k in (1, 2, 3):
        rayon = 0.28 * k / AMA
        arc = [(rayon * math.cos(math.pi * i / 12), z + 2.0 / AMA - rayon * math.sin(math.pi * i / 12)) for i in range(13)]
        branches += [_poutre(_devant(p, travers, a), _devant(p, travers, b), za, zb, tige / 2, -tige / 2, tige)
                     for (a, za), (b, zb) in zip(arc, arc[1:])]
    lampes = [_fut(_devant(p, travers, c * 0.28 / AMA), z + 2.0 / AMA, z + 2.12 / AMA, 0.06 / AMA) for c in range(-3, 4)]
    _poser("Menora_d_or", [_pave(p, 0, tige, tige, z + 0.3 / AMA, z + 2.1 / AMA)] + lampes
           + [(huit, FACES_BOITE) for huit in pieds + branches], MAT_OR())
