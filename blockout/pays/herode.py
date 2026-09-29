import math
from mathutils import Vector, geometry

from ..primitives.parametres import Z_HAR
from ..primitives.pierre import pierre
from ..primitives.matieres import CALCAIRE, MAT_MURAILLE, MAT_SOL, _exposer
from ..primitives.volumes import plage
from ..har_habayit import HX0, HX1, HY0, HY1
from .calage import (APPAREILS_KOTEL, EPAISSEUR_HAR, HARAM, KOTEL, LARGEUR_PONT, MAILLE_PAYS, PARAPET_HAR,
                     PONT_MAGHREBINS, Z_PLACE_KOTEL, _dans_le_carre, _distance_a_l_anneau, sol_naturel,
                     volumes)


def _travees(anneau, pas):
    """Le dedans d'un anneau en bandes horizontales de `pas` : (y0, y1, [(x0, x1)])."""
    y_bas = HY0 - pas * math.ceil((HY0 - min(y for _, y in anneau)) / pas)
    bandes = []
    for y0 in plage(y_bas, max(y for _, y in anneau), pas):
        yc = y0 + pas / 2
        xs = sorted(x0 + (yc - ya) * (x1 - x0) / (yb - ya)
                    for (x0, ya), (x1, yb) in zip(anneau, anneau[1:] + anneau[:1])
                    if (ya > yc) != (yb > yc))
        bandes.append((y0, y0 + pas, list(zip(xs[::2], xs[1::2]))))
    return bandes


def esplanade_herode():
    """Le dallage du Haram actuel autour du carré de Middot, au niveau du sien. Les bandes
    s'arrêtent en dents contre le contour : la crête du mur les couvre."""
    pas = EPAISSEUR_HAR
    pieces = []
    for y0, y1, spans in _travees(HARAM, pas):
        for xa, xb in spans:
            coupe = [(xa, xb)]
            if HY0 <= (y0 + y1) / 2 <= HY1:
                coupe = [(a, b) for a, b in ((xa, min(xb, HX0)), (max(xa, HX1), xb)) if b > a]
            pieces += [([(a, y0), (b, y0), (b, y1), (a, y1)], [], Z_HAR - 1, Z_HAR) for a, b in coupe]
    volumes("Herode_esplanade", pieces, "00_HarHabayit", MAT_SOL())


def _pres_du_kotel(p, marge=6):
    return _distance_a_l_anneau(p, KOTEL) < marge


def _porte_des_maghrebins(a, b):
    """Où le pont des Maghrébins passe le segment a-b du mur, ou None."""
    p, q = PONT_MAGHREBINS[-2], PONT_MAGHREBINS[-1]
    au_dela = (2 * q[0] - p[0], 2 * q[1] - p[1])
    return geometry.intersect_line_line_2d(Vector(p), Vector(au_dela), Vector(a), Vector(b))


def _travees_du_mur(a, b, z1):
    """(début, fin, crête) le long du segment, en fractions : la porte des Maghrébins
    arase le mur au dallage sur la largeur du pont."""
    porte = _porte_des_maghrebins(a, b)
    if porte is None:
        return [(0, 1, z1)]
    t, demi = math.dist(a, porte) / math.dist(a, b), LARGEUR_PONT / 2 / math.dist(a, b)
    a0, a1 = max(0, t - demi), min(1, t + demi)
    return [(0, a0, z1), (a0, a1, Z_HAR), (a1, 1, z1)]


def murs_herode():
    """Le contour du Haram en mur de soutènement, du pied au-dessus du dallage — plus haut
    là où la ville dépasse l'esplanade (au nord). Le pied suit le terrain le plus bas au
    dehors, échantillonné le long du segment ; celui du Kotel descend jusqu'à sa place."""
    anneau = HARAM
    mur, kotel = [], []
    for a, b in zip(anneau, anneau[1:] + anneau[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        long_ = math.hypot(dx, dy)
        if long_ < 1e-6:
            continue
        nx, ny = -dy / long_ * EPAISSEUR_HAR, dx / long_ * EPAISSEUR_HAR
        pas = max(1, math.ceil(long_ / 10))
        dehors = [sol_naturel(a[0] + dx * k / pas - nx / EPAISSEUR_HAR * 6,
                              a[1] + dy * k / pas - ny / EPAISSEUR_HAR * 6) for k in range(pas + 1)]
        milieu = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if _dans_le_carre(*milieu):
            continue
        du_kotel = _pres_du_kotel(milieu)
        z0 = (Z_PLACE_KOTEL if du_kotel else min(dehors)) - 3
        for t0, t1, z1 in _travees_du_mur(a, b, max(Z_HAR + PARAPET_HAR, max(dehors) + 1)):
            p, q = (a[0] + dx * t0, a[1] + dy * t0), (a[0] + dx * t1, a[1] + dy * t1)
            piece = ([p, q, (q[0] + nx, q[1] + ny), (p[0] + nx, p[1] + ny)], [], z0, z1)
            (kotel if du_kotel else mur).append(piece)
    volumes("Herode_mur", mur, "00_HarHabayit", MAT_MURAILLE())
    bas = -math.inf
    for nom, appareil, haut in APPAREILS_KOTEL:
        bande = [(anneau, trous, max(z0, bas), min(z1, haut)) for anneau, trous, z0, z1 in kotel
                 if z1 > bas and z0 < haut]
        volumes(nom, bande, "00_HarHabayit", _exposer(pierre(f"Pierre_{nom.lower()}", CALCAIRE, appareil)))
        bas = haut


def _troncons_hors(points, ouvert):
    """Les suites de points consécutifs où `ouvert` est faux."""
    troncons, courant = [], []
    for p in points:
        if not ouvert(p):
            courant.append(p)
            continue
        if len(courant) > 1:
            troncons.append(courant)
        courant = []
    return troncons + ([courant] if len(courant) > 1 else [])


def soutenement(anneau, z_pied, ouvert, epaisseur=MAILLE_PAYS, portee=12):
    """Un massif contre chaque côté d'une place creusée, du pied jusqu'au terrain que le
    relief garde à `portee` amot au dehors — sans lui, un talus de terre. Interrompu là
    où `ouvert` : contre le mur d'Hérode, une salle ou un escalier."""
    pieces = []
    for a, b in zip(anneau, anneau[1:] + anneau[:1]):
        long_ = math.dist(a, b)
        if long_ < 1e-6:
            continue
        ux, uy = (b[1] - a[1]) / long_, -(b[0] - a[0]) / long_
        n = math.ceil(long_)
        points = [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n + 1)]
        for troncon in _troncons_hors(points, ouvert):
            p, q = troncon[0], troncon[-1]
            haut = max(sol_naturel(x + ux * portee, y + uy * portee) for x, y in (p, troncon[len(troncon) // 2], q))
            if haut <= z_pied + 1:
                continue
            pieces.append(([p, q, (q[0] + ux * epaisseur, q[1] + uy * epaisseur),
                            (p[0] + ux * epaisseur, p[1] + uy * epaisseur)], [], z_pied, haut + 0.5))
    return pieces
