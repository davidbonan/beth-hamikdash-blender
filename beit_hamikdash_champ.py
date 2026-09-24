"""Modelé en champ de distance signée : des formes fondues par union douce sur une grille, polygonisées en « surface nets ».

Importé par `beit_hamikdash_shor.py` (le bœuf de la Mer) et `beit_hamikdash_seir.py` (le bouc émissaire).
"""
import math

import bpy
import numpy as np
from mathutils import Euler

LOIN = 1.0


class Champ:
    """Distance signée sur la grille, chaque forme calculée dans sa seule boîte."""

    def __init__(self, bornes, pas):
        self.pas = pas
        self.axes = [np.arange(a, b + pas, pas) for a, b in bornes]
        self.d = np.full([len(a) for a in self.axes], LOIN, dtype=np.float32)

    def _boite(self, bas, haut):
        tranches = []
        for axe, b, h in zip(self.axes, bas, haut):
            i0 = max(0, int(np.searchsorted(axe, b)) - 1)
            i1 = min(len(axe), int(np.searchsorted(axe, h)) + 1)
            tranches.append(slice(i0, i1))
        x, y, z = np.meshgrid(*(a[t] for a, t in zip(self.axes, tranches)), indexing="ij")
        return tuple(tranches), x, y, z

    def ajouter(self, bas, haut, forme, k):
        """Union douce (polynôme de Quilez) : `k` est la largeur du congé."""
        t, x, y, z = self._boite(np.array(bas) - k, np.array(haut) + k)
        a, b = self.d[t], forme(x, y, z)
        if k <= 0:
            self.d[t] = np.minimum(a, b)
            return
        h = np.maximum(k - np.abs(a - b), 0) / k
        self.d[t] = np.minimum(a, b) - h * h * k * 0.25

    def creuser(self, c, r, k):
        """Différence douce d'une boule : le naseau."""
        t, x, y, z = self._boite(np.array(c) - r - k, np.array(c) + r + k)
        a = self.d[t]
        b = r - np.sqrt((x - c[0]) ** 2 + (y - c[1]) ** 2 + (z - c[2]) ** 2)
        h = np.maximum(k - np.abs(a - b), 0) / k
        self.d[t] = np.maximum(a, b) + h * h * k * 0.25

    def ellipsoide(self, c, demi, rotation=(0, 0, 0), k=0.03):
        """`rotation` : Euler XYZ en degrés, appliquée à l'ellipsoïde."""
        rot = np.array(Euler([math.radians(a) for a in rotation]).to_matrix(), dtype=np.float32)
        r = np.array(demi, dtype=np.float32)
        g = max(demi)

        def forme(x, y, z):
            p = np.stack([x - c[0], y - c[1], z - c[2]], -1) @ rot
            k0 = np.linalg.norm(p / r, axis=-1)
            k1 = np.linalg.norm(p / (r * r), axis=-1)
            return k0 * (k0 - 1) / np.maximum(k1, 1e-6)
        self.ajouter(np.array(c) - g, np.array(c) + g, forme, k)

    def cone(self, a, b, ra, rb, k=0.02):
        """Cône arrondi de `a` (rayon `ra`) à `b` (rayon `rb`) — sdRoundCone de Quilez."""
        a, b = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
        ba = b - a
        l2 = float(ba @ ba)
        rr = ra - rb
        a2 = l2 - rr * rr
        il2 = 1.0 / l2

        def forme(x, y, z):
            pa = np.stack([x - a[0], y - a[1], z - a[2]], -1)
            yv = pa @ ba
            zv = yv - l2
            xv = pa * l2 - yv[..., None] * ba
            x2 = np.sum(xv * xv, -1)
            y2 = yv * yv * l2
            z2 = zv * zv * l2
            kk = np.sign(rr) * rr * rr * x2
            d = np.where(np.sign(zv) * a2 * z2 > kk, np.sqrt(x2 + z2) * il2 - rb,
                         np.where(np.sign(yv) * a2 * y2 < kk, np.sqrt(x2 + y2) * il2 - ra,
                                  (np.sqrt(x2 * a2 * il2) + yv * rr) * il2 - ra))
            return d
        m = max(ra, rb)
        self.ajouter(np.minimum(a, b) - m, np.maximum(a, b) + m, forme, k)

    def chaine(self, points, k=0.02):
        """Cônes arrondis bout à bout le long de (x, y, z, rayon)."""
        for p, q in zip(points, points[1:]):
            self.cone(p[:3], q[:3], p[3], q[3], k)

    def tronc(self, profil, n=2.6, k=0.0):
        """Loft de sections superelliptiques : `profil` = (x, dessus, dessous, demi-largeur),
        x croissant. Hors de ses bouts, la distance au bout le plus proche."""
        xs, dessus, dessous, larg = (np.array(c, dtype=np.float32) for c in zip(*profil))

        def forme(x, y, z):
            xc = np.clip(x, xs[0], xs[-1])
            zh, zb, w = (np.interp(xc, xs, c) for c in (dessus, dessous, larg))
            h = (zh - zb) / 2
            q = ((np.abs(y) / w) ** n + (np.abs(z - (zh + zb) / 2) / h) ** n) ** (1 / n)
            dsec = (q - 1) * np.minimum(w, h)
            return np.sqrt(np.maximum(dsec, 0) ** 2 + (x - xc) ** 2) + np.minimum(dsec, 0)
        self.ajouter((xs[0] - 0.3, -max(larg), min(dessous)), (xs[-1] + 0.3, max(larg), max(dessus)),
                     forme, k)

    def sol(self):
        """Rien sous le sol : le sabot pose à plat."""
        z = self.axes[2]
        self.d = np.maximum(self.d, -(z[None, None, :] - 0.0))


def surface_nets(c):
    """Un sommet par cellule traversée, au barycentre des croisements de ses arêtes ; une
    face par arête de grille traversée, entre les quatre cellules qui la partagent."""
    d = c.d
    ox = np.array([a[0] for a in c.axes], dtype=np.float32)
    nx, ny, nz = d.shape
    coins = [(i, j, k) for i in (0, 1) for j in (0, 1) for k in (0, 1)]
    aretes = [(a, b) for a in range(8) for b in range(a + 1, 8)
              if sum(abs(p - q) for p, q in zip(coins[a], coins[b])) == 1]
    somme = np.zeros((nx - 1, ny - 1, nz - 1, 3), dtype=np.float32)
    compte = np.zeros((nx - 1, ny - 1, nz - 1), dtype=np.float32)
    val = [d[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k] for i, j, k in coins]
    for a, b in aretes:
        va, vb = val[a], val[b]
        coupe = (va < 0) != (vb < 0)
        t = np.where(coupe, va / np.where(coupe, va - vb, 1), 0)
        pa, pb = np.array(coins[a], dtype=np.float32), np.array(coins[b], dtype=np.float32)
        somme += np.where(coupe[..., None], pa + t[..., None] * (pb - pa), 0)
        compte += coupe
    actives = compte > 0
    indice = np.full(actives.shape, -1, dtype=np.int64)
    indice[actives] = np.arange(int(actives.sum()))
    cellules = np.argwhere(actives)
    sommets = (cellules + somme[actives] / compte[actives][:, None]) * c.pas + ox
    faces = []
    dedans = d < 0
    for axe in range(3):
        u, v = (axe + 1) % 3, (axe + 2) % 3
        pas_axe = [0, 0, 0]
        pas_axe[axe] = 1
        lo = [slice(1, n - 1) for n in d.shape]
        lo[axe] = slice(0, d.shape[axe] - 1)
        hi = list(lo)
        hi[axe] = slice(1, d.shape[axe])
        change = dedans[tuple(lo)] != dedans[tuple(hi)]
        sens = dedans[tuple(lo)][change]
        p = np.argwhere(change)
        p[:, u] += 1
        p[:, v] += 1

        def cellule(du, dv):
            q = p.copy()
            q[:, u] += du
            q[:, v] += dv
            return indice[q[:, 0], q[:, 1], q[:, 2]]
        quad = np.stack([cellule(-1, -1), cellule(0, -1), cellule(0, 0), cellule(-1, 0)], 1)
        quad[~sens] = quad[~sens][:, ::-1]
        faces.append(quad)
    return sommets, np.concatenate(faces)


def maillage(sommets, faces, nom, faces_voulues):
    me = bpy.data.meshes.new(f"{nom}_brut")
    me.from_pydata(sommets.tolist(), [], faces.tolist())
    me.validate()
    o = bpy.data.objects.new(f"{nom}_brut", me)
    bpy.context.scene.collection.objects.link(o)
    lisse = o.modifiers.new("Lisser", 'SMOOTH')
    lisse.factor, lisse.iterations = 0.5, 2
    d = o.modifiers.new("Decimer", 'DECIMATE')
    d.ratio = min(1.0, faces_voulues / (2 * len(me.polygons)))
    leger = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(o)
    bpy.data.meshes.remove(me)
    return leger
