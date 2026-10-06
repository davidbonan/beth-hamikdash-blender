import math

from ..primitives.parametres import AMA
from ..primitives.matieres import (MAT_BLEU_POLICE, MAT_CARROSSERIE_SOMBRE, MAT_INOX, MAT_PLASTIQUE, MAT_PNEU, MAT_VITRE)
from ..primitives.volumes import FACES_BOITE, alea
from .calage import Z_PLACE_HAUTE, vers_scene
from .place_du_kotel import _cap, _devant, _extrusion, _pave, _poser, _poutre


# Les silhouettes de profil (avance depuis le milieu, hauteur), en mètres pour une longueur L
# et une hauteur H : un fourgon à capot court, une berline à trois volumes. Leurs cotes : CHOIX,
# au gabarit des véhicules que les photos de 2016 à 2025 montrent au sud de la place.
def _silhouette_du_fourgon(L, H):
    return [(-L / 2, 0.35), (L / 2, 0.35), (L / 2, 0.95), (L / 2 - 0.3, 1.08), (L / 2 - 1.0, H - 0.06), (L / 2 - 1.25, H), (-L / 2, H)]


def _silhouette_de_la_berline(L, H):
    return [(-L / 2, 0.3), (L / 2, 0.3), (L / 2, 0.72), (L / 2 - 0.95, 0.86), (L / 2 - 1.75, H), (-L / 2 + 1.15, H), (-L / 2 + 0.45, 0.95),
            (-L / 2, 0.9)]


def _en_travers(p, cap, profil, largeur, travers=0.0):
    """Un profil (avance, hauteur) en mètres au-dessus de la place, extrudé sur `largeur` en travers du cap, centré à `travers` à gauche."""
    amot = [(x / AMA, Z_PLACE_HAUTE + z / AMA) for x, z in profil]
    return _extrusion(amot, _devant(p, cap, 0, travers + largeur / 2), (math.sin(cap), -math.cos(cap)), (math.cos(cap), math.sin(cap)), largeur)


def _roue(p, cap, avance, travers, rayon=0.34, cotes=10):
    """(pneu, enjoliveur) d'une roue à `avance` du milieu, son flanc extérieur à `travers`."""
    disque = lambda r: [(avance + r * math.cos(2 * math.pi * k / cotes), rayon + r * math.sin(2 * math.pi * k / cotes)) for k in range(cotes)]
    dedans = travers - math.copysign(0.11 / AMA, travers)
    return _en_travers(p, cap, disque(rayon), 0.22 / AMA, dedans), _en_travers(p, cap, disque(rayon * 0.55), 0.24 / AMA, dedans)


class Parc:
    """Les véhicules du parc, rangés par matière."""

    def __init__(self):
        self.blanches, self.sombres, self.vitres, self.pneus, self.chromes, self.bleus = [], [], [], [], [], []

    def garer(self, nom, p, cap):
        """Un véhicule au point p, le nez vers le cap : un fourgon de police blanc, ou une berline claire ou sombre."""
        fourgon = alea(nom, 5) < 0.55
        L, H, largeur = (4.9 + 0.7 * alea(nom, 2), 1.95 + 0.3 * alea(nom, 3), 1.95 / AMA) if fourgon else (4.3 + 0.4 * alea(nom, 2), 1.45, 1.78 / AMA)
        profil = _silhouette_du_fourgon(L, H) if fourgon else _silhouette_de_la_berline(L, H)
        (self.blanches if fourgon or alea(nom, 6) < 0.4 else self.sombres).append(_en_travers(p, cap, profil, largeur))
        z, demi = Z_PLACE_HAUTE, largeur / 2
        pare_brise = (profil[3], profil[4])
        vitrages = [pare_brise] + ([] if fourgon else [(profil[6], profil[5])])
        for (x0, z0), (x1, z1) in vitrages:
            a, b = sorted(((x0, z0), (x1, z1)))
            self.vitres.append((_poutre(_devant(p, cap, a[0] / AMA), _devant(p, cap, b[0] / AMA), z + (a[1] + 0.02) / AMA, z + (b[1] + 0.02) / AMA,
                                        demi - 0.12 / AMA, -demi + 0.12 / AMA, 0.03 / AMA), FACES_BOITE))
        ceinture = 1.12 if fourgon else 0.92
        baie = (L / 2 - 1.25 - (L * 0.62), L / 2 - 1.3) if fourgon else (-L / 2 + 1.1, L / 2 - 1.8)
        for cote in (-1, 1):
            flanc = _devant(p, cap, (baie[0] + baie[1]) / 2 / AMA, cote * demi)
            self.vitres.append(_pave(flanc, cap, (baie[1] - baie[0]) / AMA, 0.03 / AMA, z + ceinture / AMA, z + (H - 0.14) / AMA))
            self.chromes += [_pave(_devant(p, cap, (baie[0] + (baie[1] - baie[0]) * f) / AMA, cote * demi), cap, 0.06 / AMA, 0.04 / AMA,
                                   z + ceinture / AMA, z + (H - 0.14) / AMA) for f in ((0.35, 0.7) if fourgon else (0.5,))]
            if fourgon:
                self.bleus.append(_pave(_devant(p, cap, -0.3 / AMA, cote * demi), cap, (L - 1.2) / AMA, 0.03 / AMA, z + 0.72 / AMA, z + 0.92 / AMA))
            for avance in (L / 2 - 0.95, -L / 2 + 0.9):
                pneu, enjoliveur = _roue(p, cap, avance, cote * (demi + 0.01 / AMA))
                self.pneus.append(pneu)
                self.chromes.append(enjoliveur)
            self.chromes.append(_pave(_devant(p, cap, (L / 2 - 0.02) / AMA, cote * (demi - 0.28 / AMA)), cap, 0.06 / AMA, 0.34 / AMA,
                                      z + 0.68 / AMA, z + 0.84 / AMA))
        self.pneus += [_pave(_devant(p, cap, bout * (L / 2 + 0.03) / AMA), cap, 0.14 / AMA, largeur + 0.04 / AMA, z + 0.32 / AMA, z + 0.56 / AMA)
                       for bout in (-1, 1)]
        if fourgon:
            self.bleus.append(_pave(_devant(p, cap, (L / 2 - 1.6) / AMA), cap, 0.3 / AMA, 1.2 / AMA, z + H / AMA, z + (H + 0.14) / AMA))

    def poser(self, nom):
        _poser(nom, self.blanches, MAT_PLASTIQUE())
        _poser(f"{nom}_sombres", self.sombres, MAT_CARROSSERIE_SOMBRE())
        _poser(f"{nom}_vitres", self.vitres, MAT_VITRE())
        _poser(f"{nom}_pneus", self.pneus, MAT_PNEU())
        _poser(f"{nom}_chromes", self.chromes, MAT_INOX())
        _poser(f"{nom}_bandes", self.bleus, MAT_BLEU_POLICE())


def voitures_de_police(par_rang=8, entraxe=2.9 / AMA):
    """Le parc au sud de la place, derrière les bornes : deux rangs de fourgons blancs de la
    police — bande bleue au flanc, rampe lumineuse sur le toit — et de berlines, claires ou
    sombres, tels que les photos de 2016 à 2025 les montrent. Leur nombre : CHOIX."""
    parc = Parc()
    depart, cap = vers_scene(-169, -224), _cap(vers_scene(-169, -224), vers_scene(-148, -220))
    for rang in range(2):
        for k in range(par_rang):
            nom = f"Kotel_voiture_{rang}_{k}"
            if alea(nom) >= 0.2:
                parc.garer(nom, _devant(depart, cap, k * entraxe, -rang * 13 / AMA - 0.4 * alea(nom, 1)), cap + math.pi / 2)
    parc.poser("Kotel_voitures")
