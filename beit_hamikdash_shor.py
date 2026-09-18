"""Blender -b -P beit_hamikdash_shor.py — écrit shor.blend : le bœuf de bronze qui porte le Yam.

« עֹמֵד עַל שְׁנֵי עָשָׂר בָּקָר » (Melakhim I 7:25) : douze fois le même bœuf, que le blockout
pose en quatre rangs de trois, croupe vers le centre. Le texte ne dit ni leur taille ni leur
race : un taureau de trait du pays, un mètre trente au garrot, cornes en lyre — CHOIX.

Le bœuf est un champ de distance : un tronc lofté sur ses profils (dessus, dessous, largeur),
et autour, fondus par une union douce dont le rayon dit le modelé, l'encolure, le fanon, la
tête, les membres tirés os par os du coude au sabot fendu, les cornes et la queue. Le champ
se polygonise en « surface nets » sur une grille de huit millimètres, puis se décime.

Le maillage est dans le repère du bœuf — origine au sol sous la pointe des fesses, +x vers
le mufle, z vers le haut, en mètres.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_shor.py
"""
import math
import pathlib

import bpy
import numpy as np
from mathutils import Euler

SORTIE = pathlib.Path(__file__).resolve().parent / "shor.blend"
PAS = 0.008
BORNES = ((-0.16, 2.34), (-0.40, 0.40), (-0.01, 1.46))
FACES = 12000
LOIN = 1.0


class Champ:
    """Distance signée sur la grille, chaque forme calculée dans sa seule boîte."""

    def __init__(self):
        self.axes = [np.arange(a, b + PAS, PAS) for a, b in BORNES]
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


def corps(c):
    c.tronc([(0.00, 1.12, 0.90, 0.10), (0.08, 1.19, 0.78, 0.17), (0.25, 1.24, 0.70, 0.22),
             (0.45, 1.24, 0.64, 0.24), (0.70, 1.23, 0.56, 0.27), (0.95, 1.24, 0.53, 0.28),
             (1.15, 1.28, 0.55, 0.26), (1.30, 1.32, 0.58, 0.23), (1.45, 1.27, 0.64, 0.19),
             (1.55, 1.12, 0.74, 0.12)])
    for s in (-1, 1):
        c.ellipsoide((0.30, s * 0.19, 1.16), (0.08, 0.04, 0.035), k=0.09)         # hanche
        c.ellipsoide((0.03, s * 0.08, 1.08), (0.04, 0.035, 0.04), k=0.07)         # ischion
        c.ellipsoide((0.22, s * 0.13, 0.86), (0.21, 0.12, 0.28), (0, 18, 0), k=0.08)  # cuisse
        c.ellipsoide((1.32, s * 0.16, 0.92), (0.19, 0.09, 0.30), (0, -22, 0), k=0.07)  # épaule
        c.ellipsoide((1.40, s * 0.14, 0.72), (0.10, 0.08, 0.10), k=0.05)          # pointe de l'épaule
    # Encolure épaisse, crête du taureau au garrot, fanon jusqu'au poitrail.
    c.cone((1.32, 0, 1.12), (1.86, 0, 1.05), 0.19, 0.12, k=0.08)
    c.cone((1.42, 0, 0.84), (1.90, 0, 0.93), 0.17, 0.09, k=0.08)
    c.ellipsoide((1.50, 0, 1.22), (0.22, 0.10, 0.07), (0, 15, 0), k=0.08)
    c.ellipsoide((1.70, 0, 0.80), (0.23, 0.03, 0.09), (0, -38, 0), k=0.06)
    c.ellipsoide((1.50, 0, 0.68), (0.09, 0.11, 0.07), k=0.08)                 # poitrail


def tete(c):
    """Front large et plat, chanfrein droit, mufle carré, face penchée à 55°."""
    c.ellipsoide((1.93, 0, 1.05), (0.09, 0.125, 0.12), (0, 30, 0), k=0.05)       # front, chignon
    c.cone((1.95, 0, 1.00), (2.12, 0, 0.78), 0.10, 0.085, k=0.04)               # chanfrein
    c.ellipsoide((2.13, 0, 0.76), (0.065, 0.095, 0.07), (0, 35, 0), k=0.04)      # mufle
    c.ellipsoide((2.02, 0, 0.82), (0.10, 0.07, 0.05), (0, 40, 0), k=0.04)        # mâchoire
    for s in (-1, 1):
        c.ellipsoide((1.93, s * 0.075, 0.92), (0.09, 0.05, 0.065), (0, 45, 0), k=0.04)  # joue
        c.ellipsoide((1.975, s * 0.105, 1.00), (0.025, 0.02, 0.018), k=0.02)             # arcade
        c.creuser((2.185, s * 0.045, 0.775), 0.017, k=0.01)                             # naseau
        c.ellipsoide((1.89, s * 0.18, 1.03), (0.05, 0.075, 0.018), (s * 25, 0, s * 15), k=0.025)  # oreille
        c.chaine([(1.90, s * 0.08, 1.10, 0.042), (1.91, s * 0.19, 1.13, 0.036),
                  (1.97, s * 0.27, 1.20, 0.027), (2.04, s * 0.29, 1.30, 0.016),
                  (2.06, s * 0.26, 1.37, 0.005)], k=0.01)                                 # corne


def sabot(c, x, y):
    """Deux onglons, sans congé entre eux : c'est la fente qui fait le pied du bœuf."""
    for o in (-1, 1):
        c.cone((x - 0.02, y + o * 0.024, 0.055), (x + 0.045, y + o * 0.020, 0.018), 0.030, 0.018, k=0)
    c.cone((x - 0.03, y, 0.10), (x - 0.01, y, 0.06), 0.033, 0.036, k=0.015)      # couronne


def pattes(c):
    """Avant : avant-bras, genou, canon, boulet, paturon. Arrière : grasset, jambe, jarret
    coudé vers l'arrière, canon un peu penché vers l'avant."""
    for s in (-1, 1):
        y = s * 0.15
        c.chaine([(1.36, s * 0.16, 0.86, 0.10), (1.30, s * 0.16, 0.62, 0.080),
                  (1.29, y, 0.36, 0.046)], k=0.05)
        c.ellipsoide((1.33, s * 0.16, 0.52), (0.06, 0.06, 0.11), (0, -5, 0), k=0.04)   # muscle de l'avant-bras
        c.ellipsoide((1.295, y, 0.34), (0.05, 0.047, 0.05), k=0.02)                     # genou
        c.chaine([(1.29, y, 0.33, 0.033), (1.30, y, 0.14, 0.031)], k=0.02)
        c.ellipsoide((1.30, y, 0.125), (0.045, 0.040, 0.038), k=0.02)                    # boulet
        c.cone((1.30, y, 0.12), (1.33, y, 0.07), 0.030, 0.031, k=0.015)
        sabot(c, 1.35, y)

        c.chaine([(0.40, s * 0.16, 0.74, 0.10), (0.26, s * 0.155, 0.60, 0.085),
                  (0.11, y, 0.48, 0.045)], k=0.06)                                       # jambe
        c.cone((0.10, s * 0.15, 0.84), (0.055, y, 0.50), 0.11, 0.030, k=0.06)            # tendon d'Achille
        c.ellipsoide((0.07, y, 0.47), (0.04, 0.035, 0.045), k=0.02)                      # pointe du jarret
        c.chaine([(0.10, y, 0.45, 0.040), (0.15, y, 0.14, 0.031)], k=0.02)
        c.ellipsoide((0.155, y, 0.125), (0.043, 0.038, 0.037), k=0.02)
        c.cone((0.155, y, 0.12), (0.18, y, 0.07), 0.030, 0.031, k=0.015)
        sabot(c, 0.20, y)


def queue(c):
    c.chaine([(0.05, 0, 1.13, 0.034), (-0.02, 0, 1.08, 0.026), (-0.05, 0, 0.95, 0.018),
              (-0.055, 0, 0.75, 0.014), (-0.05, 0, 0.56, 0.013)], k=0.015)
    c.ellipsoide((-0.05, 0, 0.47), (0.045, 0.04, 0.13), (0, 4, 0), k=0.03)               # toupet


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
    sommets = (cellules + somme[actives] / compte[actives][:, None]) * PAS + ox
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


def maillage(sommets, faces):
    me = bpy.data.meshes.new("Shor_brut")
    me.from_pydata(sommets.tolist(), [], faces.tolist())
    me.validate()
    o = bpy.data.objects.new("Shor_brut", me)
    bpy.context.scene.collection.objects.link(o)
    lisse = o.modifiers.new("Lisser", 'SMOOTH')
    lisse.factor, lisse.iterations = 0.5, 2
    d = o.modifiers.new("Decimer", 'DECIMATE')
    d.ratio = min(1.0, FACES / (2 * len(me.polygons)))
    leger = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(o)
    bpy.data.meshes.remove(me)
    return leger


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    c = Champ()
    corps(c)
    tete(c)
    pattes(c)
    queue(c)
    c.sol()
    me = maillage(*surface_nets(c))
    me.name = "Shor"
    me.shade_smooth()
    xs, ys, zs = zip(*(v.co[:] for v in me.vertices))
    print(f"Shor : {len(me.polygons)} faces, de x = {min(xs):.2f} à {max(xs):.2f} m, "
          f"{max(ys) - min(ys):.2f} m de large, {max(zs):.2f} m de haut")
    bpy.data.libraries.write(str(SORTIE), {me}, fake_user=True, compress=True)
    print(f"écrit {SORTIE}")


if __name__ == "__main__":
    main()
