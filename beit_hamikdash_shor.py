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
import pathlib
import sys

import bpy

RACINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
from beit_hamikdash_champ import Champ, maillage, surface_nets  # noqa: E402

SORTIE = RACINE / "shor.blend"
PAS = 0.008
BORNES = ((-0.16, 2.34), (-0.40, 0.40), (-0.01, 1.46))
FACES = 12000


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


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    c = Champ(BORNES, PAS)
    corps(c)
    tete(c)
    pattes(c)
    queue(c)
    c.sol()
    me = maillage(*surface_nets(c), "Shor", FACES)
    me.name = "Shor"
    me.shade_smooth()
    xs, ys, zs = zip(*(v.co[:] for v in me.vertices))
    print(f"Shor : {len(me.polygons)} faces, de x = {min(xs):.2f} à {max(xs):.2f} m, "
          f"{max(ys) - min(ys):.2f} m de large, {max(zs):.2f} m de haut")
    bpy.data.libraries.write(str(SORTIE), {me}, fake_user=True, compress=True)
    print(f"écrit {SORTIE}")


if __name__ == "__main__":
    main()
