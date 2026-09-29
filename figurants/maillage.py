import math
from typing import NamedTuple

import numpy as np
from mathutils import Vector

import beit_hamikdash_gestes as G

from .matieres import TUILE
from .corps import BRAS


TOUR = 2.0 * math.pi
N_ANNEAU = 64


class Maillage:
    def __init__(self):
        self.sommets, self.faces, self.couleurs, self.zones, self.uvs = [], [], [], [], []
        self.epingles = {}

    def nappe(self, anneaux, couleur, zone, ferme=True, pole_fin=None, epingle=None):
        choisir = couleur if callable(couleur) else (lambda i, j: couleur)
        n, base = len(anneaux[0]), len(self.sommets)
        for i, anneau in enumerate(anneaux):
            self.sommets.extend(anneau)
            self.zones.extend([zone(i) if callable(zone) else zone] * n)
            poids = epingle(i) if epingle else 0.0
            if poids:
                self.epingles.update({base + i * n + k: poids for k in range(n)})
        longueurs = []
        for anneau in anneaux:
            tour = anneau + anneau[:1] if ferme else anneau
            cumul = [0.0]
            for a, b in zip(tour, tour[1:]):
                cumul.append(cumul[-1] + (b - a).length)
            longueurs.append(cumul)
        hauteurs = [0.0]
        for a, b in zip(anneaux, anneaux[1:]):
            hauteurs.append(hauteurs[-1] + sum((q - p).length for p, q in zip(a, b)) / n)

        def uv(i, j):
            return longueurs[i][j] / TUILE, hauteurs[i] / TUILE

        cotes = n if ferme else n - 1
        for i in range(len(anneaux) - 1):
            for j in range(cotes):
                a, b = base + i * n + j, base + i * n + (j + 1) % n
                self.faces.append((a, b, b + n, a + n))
                self.uvs.append((uv(i, j), uv(i, j + 1), uv(i + 1, j + 1), uv(i + 1, j)))
                self.couleurs.append(choisir(i, j))
        if pole_fin is not None:
            p, i = len(self.sommets), len(anneaux) - 1
            dernier = base + i * n
            self.sommets.append(pole_fin)
            self.zones.append(self.zones[-1])
            centre = (longueurs[i][-1] / 2 / TUILE, hauteurs[i] / TUILE + 0.5)
            for j in range(cotes):
                self.faces.append((dernier + j, dernier + (j + 1) % n, p))
                self.uvs.append((uv(i, j), uv(i, j + 1), centre))
                self.couleurs.append(choisir(i - 1, j))


def _angles(n=N_ANNEAU):
    return np.linspace(0.0, TOUR, n, endpoint=False)


def _vers(th):
    return math.sin(th), -math.cos(th)


# θ = 0 devant, θ = π/2 à gauche ; les creux sont comblés.
def enveloppe(points_xy, centre, n=N_ANNEAU, minimum=0.02):
    if len(points_xy) < 3:
        return np.full(n, minimum)
    x = points_xy[:, 0] - centre[0]
    y = points_xy[:, 1] - centre[1]
    th = np.arctan2(x, -y)
    r = np.hypot(x, y)
    ecart = (th[None, :] - _angles(n)[:, None] + math.pi) % TOUR - math.pi
    appui = np.where(np.abs(ecart) < math.pi / 2, r[None, :] * np.cos(ecart), 0.0)
    return np.maximum(appui.max(axis=1), minimum)


def _lisser_cercle(r, fois=2):
    for _ in range(fois):
        r = 0.25 * np.roll(r, 1) + 0.5 * r + 0.25 * np.roll(r, -1)
    return r


def tranche(humain, masque, z, epaisseur=0.018, extra=None):
    sel = masque & (np.abs(humain.co[:, 2] - z) < epaisseur)
    points = humain.co[sel, :2]
    if extra is not None and len(extra):
        points = np.vstack([points, extra[np.abs(extra[:, 2] - z) < epaisseur][:, :2]])
    return points


# La ceinture : un cylindre sur le tronc, à la hauteur `z`, qui ramène la robe sur le corps.
class Ceinture:
    def __init__(self, humain, z, largeur=0.07, jeu=0.012):
        h = humain
        points = tranche(h, h.visible & ~h.bras & ~h.main, z, largeur / 2)
        self.z, self.largeur = z, largeur
        self.cy = 0.5 * (points[:, 1].min() + points[:, 1].max())
        self.rayons = _lisser_cercle(enveloppe(points, (0.0, self.cy)), 4) + jeu

    def rayon(self, th):
        j = th % TOUR / TOUR * N_ANNEAU
        j0, u = int(j) % N_ANNEAU, j - int(j)
        return self.rayons[j0] * (1 - u) + self.rayons[(j0 + 1) % N_ANNEAU] * u

    def point(self, th, z, ecart=0.0):
        r = self.rayon(th) + ecart
        return Vector((r * _vers(th)[0], self.cy + r * _vers(th)[1], z))

    def serrer(self, humain, objet, portee=0.10):
        passage = humain.rig.matrix_world.inverted() @ objet.matrix_world
        retour = passage.inverted()
        for v in objet.data.vertices:
            if sum(e.weight for e in v.groups if objet.vertex_groups[e.group].name.startswith(BRAS)) > 0.5:
                continue
            p = passage @ v.co
            dx, dy = p.x, p.y - self.cy
            r = math.hypot(dx, dy)
            cible = self.rayon(math.atan2(dx, -dy)) - 0.004
            hors = abs(p.z - self.z) - self.largeur / 2
            if r <= cible or hors > portee:
                continue
            k = 1.0 - (1.0 - G.lisse(hors / portee)) * (1.0 - cible / r)
            v.co = retour @ Vector((dx * k, self.cy + dy * k, p.z))


def tube(chemin, rayons, n):
    anneaux = []
    reference = Vector((0.0, -1.0, 0.0))
    for k, (p, r) in enumerate(zip(chemin, rayons)):
        t = (chemin[min(k + 1, len(chemin) - 1)] - chemin[max(k - 1, 0)]).normalized()
        f = reference - t * reference.dot(t)
        if f.length < 1e-5:
            f = t.orthogonal()
        f.normalize()
        g = t.cross(f)
        anneaux.append([p + (f * math.cos(a) + g * math.sin(a)) * r for a in np.linspace(0, TOUR, n, endpoint=False)])
    return anneaux


# Avnet de trois doigts, tour sur tour (Klei HaMikdash 8:19), brodé (8:1), aux coudes (Rashi Shemot 28:7) ; rayures : CHOIX.
class Teintes(NamedTuple):
    bandes: tuple
    raies: tuple


# Une plaque `largeurs` posée en `centre`, dans le plan (u, v), levée de `epaisseur` le long de u × v.
def pave(mm, centre, u, v, largeurs, epaisseur, couleur, zone):
    n = u.cross(v)
    coins = [centre + u * (a * largeurs[0] / 2) + v * (b * largeurs[1] / 2) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    mm.nappe([coins, [c + n * epaisseur for c in coins]], couleur, zone, pole_fin=centre + n * epaisseur)
