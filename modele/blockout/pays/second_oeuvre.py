import math

from ..primitives.parametres import AMA
from ..primitives.matieres import MAT_CHENE, MAT_FER_BRUN, MAT_VITRE
from ..primitives.volumes import FACES_BOITE, empty, plage
from .place_du_kotel import _baie, _cap, _devant, _extrusion, _fut, _pave, _poser, _poutre


# Ce qui habille un mur une fois le gros œuvre monté : chambranles, appuis, croisées, grilles,
# archivoltes, descentes d'eau, climatiseurs, appliques, paraboles. Un mur p→q montre sa face
# à gauche du sens p→q ; `s` est l'abscisse depuis p. Sections et saillies : lues sur les
# photos (Wikimedia Commons, 2016–2025), à l'échelle d'une assise de quarante centimètres.
BANDE, SAILLIE = 0.16 / AMA, 0.09 / AMA


def _unitaire(p, q):
    long_ = math.dist(p, q)
    return ((q[0] - p[0]) / long_, (q[1] - p[1]) / long_)


def _a_droite(p, q, d):
    """Le vecteur de longueur d à droite de p→q."""
    t = _unitaire(p, q)
    return (t[1] * d, -t[0] * d)


def _decale(p, v):
    return (p[0] + v[0], p[1] + v[1])


def _arc(centre, demi, naissance, fleche, segments=8):
    """L'intrados d'une arche de gauche à droite : plein cintre si la flèche vaut la demi-portée,
    surbaissé en dessous."""
    rayon = (demi ** 2 + fleche ** 2) / (2 * fleche)
    ouverture = math.asin(min(1, demi / rayon))
    return [(centre + rayon * math.sin(-ouverture + 2 * ouverture * k / segments),
             naissance + fleche - rayon + rayon * math.cos(-ouverture + 2 * ouverture * k / segments))
            for k in range(segments + 1)]


def _plaque(p, q, s, z0, largeur, hauteur, saillie):
    """Un panneau droit plaqué sur le mur p→q, à gauche, centré à `s` de p."""
    t = _unitaire(p, q)
    a, b = (p[0] + t[0] * (s - largeur / 2), p[1] + t[1] * (s - largeur / 2)), (p[0] + t[0] * (s + largeur / 2), p[1] + t[1] * (s + largeur / 2))
    return _poutre(a, b, z0, z0, saillie, -0.02, hauteur), FACES_BOITE


def _bandeau(p, q, z, hauteur=0.25 / AMA, saillie=0.08 / AMA):
    """Un cordon de pierre sur toute la longueur du mur."""
    return _plaque(p, q, math.dist(p, q) / 2, z, math.dist(p, q) + 2 * saillie, hauteur, saillie)


def _encadrement(p, q, s, z0, dehors, dedans, saillie):
    """La bande de pierre entre deux contours (v, z) parcourus de gauche à droite, plaquée sur le mur."""
    profil = dehors[::-1] + dedans
    return _extrusion([(v, z0 + z) for v, z in profil], _devant(p, _cap(p, q), s, -0.02), _a_droite(p, q, -1), _unitaire(p, q), saillie + 0.02)


def _contour(demi, hauteur, cintre, segments=6):
    """Le tour d'une baie depuis son pied gauche jusqu'à son pied droit."""
    if not cintre:
        return [(-demi, 0), (-demi, hauteur), (demi, hauteur), (demi, 0)]
    return [(-demi, 0)] + _arc(0, demi, hauteur - demi, demi, segments) + [(demi, 0)]


def _chambranle(p, q, s, seuil, largeur, hauteur, cintre):
    return _encadrement(p, q, s, seuil, _contour(largeur / 2 + BANDE, hauteur + BANDE, cintre), _contour(largeur / 2, hauteur, cintre), SAILLIE)


def _archivolte(p, q, s, z0, arche, bande=0.3 / AMA, saillie=0.07 / AMA):
    """Les claveaux d'une arche (portée, hauteur à la clé, flèche) et ses piédroits, en léger relief."""
    portee, cle, fleche = arche
    dedans = [(-portee / 2, 0)] + _arc(0, portee / 2, cle - fleche, fleche) + [(portee / 2, 0)]
    dehors = [(-portee / 2 - bande, 0)] + _arc(0, portee / 2 + bande, cle - fleche, fleche + bande) + [(portee / 2 + bande, 0)]
    return _encadrement(p, q, s, z0, dehors, dedans, saillie)


def _barreaux(p, q, s, seuil, largeur, hauteur, pas=0.14 / AMA):
    """La grille d'une fenêtre : des barreaux droits et trois traverses, en avant du chambranle."""
    fers = [_plaque(p, q, s + d, seuil, 0.02 / AMA, hauteur, SAILLIE + 0.03 / AMA) for d in plage(-largeur / 2 + pas / 2, largeur / 2, pas)]
    return fers + [_plaque(p, q, s, seuil + hauteur * f, largeur, 0.025 / AMA, SAILLIE + 0.035 / AMA) for f in (0.08, 0.5, 0.9)]


class Percements:
    """Les baies d'une façade, rangées par matière : la pierre des chambranles et des appuis,
    les vitres, le fer des croisées et des grilles, le bois des vantaux."""

    def __init__(self):
        self.pierres, self.vitres, self.fers, self.bois = [], [], [], []

    def fenetre(self, p, q, s, seuil, largeur, hauteur, cintre=True, grille=False):
        """Une fenêtre dans son chambranle, sur son appui, avec sa croisée."""
        self.pierres += [_chambranle(p, q, s, seuil, largeur, hauteur, cintre),
                         _plaque(p, q, s, seuil - 0.12 / AMA, largeur + 2 * BANDE + 0.12 / AMA, 0.12 / AMA, SAILLIE + 0.06 / AMA)]
        self.vitres.append(_baie(p, q, s, seuil, largeur, hauteur, 0.02 / AMA) if cintre
                           else _plaque(p, q, s, seuil, largeur, hauteur, 0.02 / AMA))
        imposte = hauteur - largeur / 2 if cintre else hauteur * 0.68
        self.fers += [_plaque(p, q, s, seuil, 0.05 / AMA, imposte, 0.045 / AMA), _plaque(p, q, s, seuil + imposte, largeur, 0.05 / AMA, 0.045 / AMA)]
        if grille:
            self.fers += _barreaux(p, q, s, seuil, largeur, imposte if cintre else hauteur)

    def jumelles(self, p, q, s, seuil, largeur, hauteur, cintre=True):
        """Deux fenêtres côte à côte de part et d'autre d'un meneau de pierre."""
        for t in (-1, 1):
            self.fenetre(p, q, s + t * (largeur / 2 + BANDE), seuil, largeur, hauteur, cintre)

    def porte(self, p, q, s, seuil, largeur, hauteur, cintre=False):
        """Une porte de bois à deux vantaux dans son chambranle."""
        self.pierres.append(_chambranle(p, q, s, seuil, largeur, hauteur, cintre))
        self.bois.append(_baie(p, q, s, seuil, largeur, hauteur, 0.03 / AMA) if cintre else _plaque(p, q, s, seuil, largeur, hauteur, 0.03 / AMA))
        self.fers += [_plaque(p, q, s, seuil, 0.03 / AMA, hauteur - (largeur / 2 if cintre else 0), 0.05 / AMA),
                      _plaque(p, q, s + 0.12 / AMA, seuil + 1.0 / AMA, 0.04 / AMA, 0.18 / AMA, 0.08 / AMA)]

    def arche(self, p, q, s, z0, arche):
        self.pierres.append(_archivolte(p, q, s, z0, arche))

    def poser(self, nom, pierre, col="00_HarHabayit"):
        _poser(f"{nom}_chambranles", self.pierres, pierre, col)
        _poser(f"{nom}_vitres", self.vitres, MAT_VITRE(), col)
        _poser(f"{nom}_croisees", self.fers, MAT_FER_BRUN(), col)
        _poser(f"{nom}_vantaux", self.bois, MAT_CHENE(), col)


def descente_d_eau(p, q, s, z0, z1, rayon=0.05 / AMA):
    """Un tuyau de descente plaqué sur le mur, tenu par un collier tous les deux mètres."""
    axe = _devant(p, _cap(p, q), s, rayon + 0.03 / AMA)
    return [_fut(axe, z0, z1, rayon, 6)] + [_fut(axe, z, z + 0.04 / AMA, rayon + 0.02 / AMA, 6) for z in plage(z0 + 1 / AMA, z1, 2 / AMA)]


def climatiseur(p, q, s, z):
    """Le groupe extérieur d'un climatiseur sur ses deux équerres : (caisson, équerres)."""
    cap = _cap(p, q)
    caisson = _pave(_devant(p, cap, s, 0.2 / AMA), cap, 0.8 / AMA, 0.3 / AMA, z, z + 0.55 / AMA)
    return caisson, [_plaque(p, q, s + t * 0.3 / AMA, z - 0.04 / AMA, 0.03 / AMA, 0.04 / AMA, 0.38 / AMA) for t in (-1, 1)]


def applique(p, q, s, z):
    """Une lanterne au bout de sa potence : (verre, ferronnerie)."""
    cap = _cap(p, q)
    lanterne = _devant(p, cap, s, 0.5 / AMA)
    return (_pave(lanterne, cap, 0.2 / AMA, 0.2 / AMA, z - 0.32 / AMA, z - 0.04 / AMA),
            [_plaque(p, q, s, z, 0.03 / AMA, 0.03 / AMA, 0.55 / AMA), _pave(lanterne, cap, 0.26 / AMA, 0.26 / AMA, z - 0.04 / AMA, z)])


def projecteur(centre, z, cap):
    """Un projecteur sur son étrier, tourné vers le cap."""
    return [_pave(_devant(centre, cap, 0.12 / AMA), cap, 0.18 / AMA, 0.4 / AMA, z, z + 0.3 / AMA), _fut(centre, z - 0.25 / AMA, z + 0.05 / AMA, 0.02 / AMA, 4)]


def verre_de_projecteur(centre, z, cap):
    """La glace d'un projecteur, devant son caisson."""
    return _pave(_devant(centre, cap, 0.22 / AMA), cap, 0.02 / AMA, 0.34 / AMA, z + 0.03 / AMA, z + 0.27 / AMA)


def repere_de_projecteur(nom, centre, z):
    """Le point d'où la visite éclaire la place, de nuit, pour une rampe de projecteurs."""
    return empty(f"Kotel_projecteur_{nom}", *centre, z, "00_HarHabayit")


def parabole(centre, z, cap, rayon=0.42 / AMA, site=0.6, cotes=10):
    """Une antenne parabolique sur son mât court, pointée vers le cap."""
    axe = (math.cos(cap) * math.cos(site), math.sin(cap) * math.cos(site), math.sin(site))
    travers, haut = (-math.sin(cap), math.cos(cap), 0.0), (-math.cos(cap) * math.sin(site), -math.sin(cap) * math.sin(site), math.cos(site))
    coeur = (centre[0], centre[1], z + 0.7 / AMA)
    verts = [tuple(coeur[i] - axe[i] * rayon * 0.25 for i in range(3))]
    verts += [tuple(coeur[i] + rayon * (math.cos(2 * math.pi * k / cotes) * travers[i] + math.sin(2 * math.pi * k / cotes) * haut[i]) for i in range(3))
              for k in range(cotes)]
    faces = [[0, 1 + k, 1 + (k + 1) % cotes] for k in range(cotes)] + [[0, 1 + (k + 1) % cotes, 1 + k] for k in range(cotes)]
    return [(verts, faces), _fut(centre, z, z + 0.7 / AMA, 0.025 / AMA, 4)]
