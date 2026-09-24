"""Blender -b -P beit_hamikdash_seir.py — écrit seir.blend : le bouc émissaire de Yom Kippour.

« שְׂעִיר עִזִּים » (Vayikra 16:5) : un bouc. La Mishna n'en dit que la paire, pareille de
couleur, de taille et de prix (Yoma 6:1). La race est un CHOIX : la chèvre noire du pays, à
poil long, barbe, oreilles tombantes et cornes en cimeterre, soixante-quinze centimètres au
garrot.

Deux maillages, parce que deux matières : `Seir`, le corps et son poil, et `Seir_cornes`.
Le repère est celui du bœuf de la Mer (`beit_hamikdash_shor.py`) : origine au sol sous la
pointe des fesses, +x vers le museau, z vers le haut, en mètres.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_seir.py
"""
import pathlib
import sys

import bpy

RACINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
from beit_hamikdash_champ import Champ, maillage, surface_nets  # noqa: E402

SORTIE = RACINE / "seir.blend"
PAS = 0.005
BORNES = ((-0.12, 1.24), (-0.22, 0.22), (-0.01, 1.20))
FACES = 9000
FACES_CORNES = 1600


def corps(c):
    c.tronc([(0.00, 0.64, 0.50, 0.06), (0.05, 0.69, 0.44, 0.10), (0.15, 0.71, 0.40, 0.13),
             (0.30, 0.70, 0.37, 0.15), (0.45, 0.70, 0.35, 0.16), (0.60, 0.72, 0.36, 0.15),
             (0.70, 0.75, 0.38, 0.13), (0.78, 0.76, 0.42, 0.10), (0.84, 0.72, 0.50, 0.06)])
    for s in (-1, 1):
        c.ellipsoide((0.13, s * 0.09, 0.56), (0.11, 0.06, 0.13), (0, 15, 0), k=0.05)   # cuisse
        c.ellipsoide((0.72, s * 0.09, 0.56), (0.08, 0.05, 0.14), (0, -20, 0), k=0.05)  # épaule
    # Encolure mince, poitrail étroit : une chèvre, pas un bœuf.
    c.cone((0.72, 0, 0.68), (0.92, 0, 0.85), 0.090, 0.060, k=0.06)
    c.ellipsoide((0.80, 0, 0.52), (0.06, 0.07, 0.06), k=0.05)                          # poitrail


def tete(c):
    """Front bombé, chanfrein droit, museau fin, la face penchée à 50° ; barbe sous le menton."""
    c.ellipsoide((0.96, 0, 0.90), (0.065, 0.055, 0.060), (0, 25, 0), k=0.03)
    c.cone((0.97, 0, 0.88), (1.10, 0, 0.76), 0.050, 0.030, k=0.03)
    c.ellipsoide((1.10, 0, 0.755), (0.030, 0.028, 0.026), (0, 40, 0), k=0.02)          # museau
    c.ellipsoide((1.03, 0, 0.78), (0.055, 0.035, 0.025), (0, 45, 0), k=0.02)           # mâchoire
    c.cone((1.04, 0, 0.75), (1.03, 0, 0.64), 0.028, 0.008, k=0.02)                     # barbe
    for s in (-1, 1):
        c.creuser((1.125, s * 0.016, 0.755), 0.008, k=0.005)                            # naseau
        c.ellipsoide((0.975, s * 0.052, 0.905), (0.014, 0.010, 0.010), k=0.01)         # arcade
        c.ellipsoide((0.93, s * 0.095, 0.83), (0.028, 0.012, 0.085), (s * -30, 15, 0), k=0.015)  # oreille tombante


def sabot(c, x, y):
    for o in (-1, 1):
        c.cone((x - 0.012, y + o * 0.011, 0.028), (x + 0.022, y + o * 0.010, 0.010), 0.014, 0.009, k=0)


def pattes(c):
    """Membres secs : genou, canon, boulet ; à l'arrière le jarret coudé."""
    for s in (-1, 1):
        y = s * 0.075
        c.chaine([(0.73, s * 0.085, 0.50, 0.050), (0.72, s * 0.08, 0.34, 0.032), (0.72, y, 0.22, 0.020)], k=0.03)
        c.ellipsoide((0.72, y, 0.215), (0.022, 0.021, 0.024), k=0.01)                  # genou
        c.chaine([(0.72, y, 0.21, 0.015), (0.725, y, 0.06, 0.014)], k=0.01)
        c.cone((0.725, y, 0.06), (0.735, y, 0.03), 0.015, 0.014, k=0.008)
        sabot(c, 0.745, y)

        c.chaine([(0.16, s * 0.09, 0.50, 0.065), (0.10, s * 0.085, 0.36, 0.045), (0.05, y, 0.27, 0.020)], k=0.035)
        c.ellipsoide((0.045, y, 0.265), (0.018, 0.016, 0.020), k=0.01)                 # pointe du jarret
        c.chaine([(0.05, y, 0.26, 0.016), (0.08, y, 0.06, 0.014)], k=0.01)
        c.cone((0.08, y, 0.06), (0.09, y, 0.03), 0.015, 0.014, k=0.008)
        sabot(c, 0.10, y)


def queue(c):
    c.chaine([(0.01, 0, 0.63, 0.022), (-0.03, 0, 0.68, 0.016), (-0.04, 0, 0.73, 0.010)], k=0.01)


def cornes(c):
    """En cimeterre : elles partent du front, filent vers l'arrière et s'écartent en montant."""
    for s in (-1, 1):
        c.chaine([(0.965, s * 0.025, 0.945, 0.022), (0.945, s * 0.035, 1.005, 0.018),
                  (0.905, s * 0.050, 1.050, 0.014), (0.850, s * 0.068, 1.075, 0.010),
                  (0.790, s * 0.085, 1.075, 0.006), (0.745, s * 0.098, 1.060, 0.002)], k=0.004)


def modeler(nom, faces, *formes):
    c = Champ(BORNES, PAS)
    for forme in formes:
        forme(c)
    c.sol()
    me = maillage(*surface_nets(c), nom, faces)
    me.name = nom
    me.shade_smooth()
    xs, ys, zs = zip(*(v.co[:] for v in me.vertices))
    print(f"{nom} : {len(me.polygons)} faces, de x = {min(xs):.2f} à {max(xs):.2f} m, "
          f"{max(ys) - min(ys):.2f} m de large, {max(zs):.2f} m de haut")
    return me


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    maillages = {modeler("Seir", FACES, corps, tete, pattes, queue), modeler("Seir_cornes", FACES_CORNES, cornes)}
    bpy.data.libraries.write(str(SORTIE), maillages, fake_user=True, compress=True)
    print(f"écrit {SORTIE}")


if __name__ == "__main__":
    main()
