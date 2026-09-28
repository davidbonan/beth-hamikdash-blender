"""Blender -b -P beit_hamikdash_seh.py — écrit seh.blend : l'agneau du korban Pessa'h.

« שֶׂה תָמִים זָכָר בֶּן שָׁנָה … מִן הַכְּבָשִׂים וּמִן הָעִזִּים תִּקָּחוּ » (Shemot 12:5) : un mâle
de l'année, agneau ou chevreau. La visite prend l'agneau ; la race est un CHOIX : le mouton
du pays à queue grasse, laine crème, tête fine, oreilles tombantes, sans cornes, soixante
centimètres au garrot.

Deux maillages, deux attitudes : `Seh`, debout, et `Seh_etire`, les membres tendus dans l'axe
du corps — suspendu par les pattes arrière au crochet (Pesa'him 5:9), ou porté dans sa peau.
Le repère est celui du bouc (`beit_hamikdash_seir.py`) : origine au sol sous la pointe des
fesses, +x vers le museau, z vers le haut, en mètres.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_seh.py
"""
import pathlib
import sys

import bpy

RACINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
from beit_hamikdash_champ import Champ, maillage, surface_nets  # noqa: E402

SORTIE = RACINE / "seh.blend"
PAS = 0.005
FACES = 7000


def corps(c):
    c.tronc([(0.00, 0.55, 0.36, 0.08), (0.05, 0.60, 0.30, 0.13), (0.15, 0.62, 0.27, 0.16),
             (0.30, 0.62, 0.25, 0.17), (0.45, 0.62, 0.25, 0.17), (0.58, 0.64, 0.27, 0.16),
             (0.68, 0.66, 0.31, 0.13), (0.75, 0.65, 0.38, 0.09)])
    for s in (-1, 1):
        c.ellipsoide((0.13, s * 0.08, 0.46), (0.11, 0.07, 0.12), (0, 15, 0), k=0.05)   # cuisse
        c.ellipsoide((0.64, s * 0.08, 0.46), (0.08, 0.06, 0.12), (0, -20, 0), k=0.05)  # épaule
    c.cone((0.66, 0, 0.56), (0.80, 0, 0.70), 0.085, 0.060, k=0.06)
    c.ellipsoide((0.71, 0, 0.40), (0.06, 0.08, 0.07), k=0.05)                          # poitrail


def tete(c):
    """Chanfrein busqué, museau étroit, oreilles tombantes."""
    c.ellipsoide((0.83, 0, 0.74), (0.070, 0.060, 0.066), (0, 25, 0), k=0.03)
    c.cone((0.84, 0, 0.72), (0.95, 0, 0.62), 0.054, 0.032, k=0.03)
    c.ellipsoide((0.955, 0, 0.615), (0.032, 0.030, 0.028), (0, 40, 0), k=0.02)         # museau
    for s in (-1, 1):
        c.creuser((0.975, s * 0.013, 0.615), 0.007, k=0.004)                           # naseau
        c.ellipsoide((0.80, s * 0.095, 0.68), (0.030, 0.010, 0.060), (s * -75, 10, 0), k=0.012)  # oreille


def queue(c, etiree):
    """Queue grasse, large à la base ; pendante sur l'agneau debout, dans l'axe s'il est étiré."""
    if etiree:
        c.ellipsoide((-0.07, 0, 0.44), (0.09, 0.09, 0.06), k=0.03)
        return
    c.ellipsoide((-0.03, 0, 0.44), (0.05, 0.09, 0.11), (0, -10, 0), k=0.03)


def membre(c, y, haut, genou, bas, rayons):
    c.chaine([(*haut, rayons[0]), (*genou, rayons[1])], k=0.03)
    c.ellipsoide(genou, (0.018, 0.017, 0.020), k=0.01)
    c.chaine([(*genou, rayons[2]), (*bas, rayons[3])], k=0.01)


def pattes(c, etiree):
    """Debout, les membres sous le corps ; étirées, les postérieurs vers l'arrière, les antérieurs vers l'avant."""
    for s in (-1, 1):
        y = s * 0.065
        if etiree:
            membre(c, y, (0.62, y, 0.40), (0.78, y, 0.30), (0.98, y, 0.28), (0.050, 0.030, 0.018, 0.016))
            membre(c, y, (0.12, y, 0.40), (-0.06, y, 0.36), (-0.26, y, 0.38), (0.060, 0.034, 0.019, 0.016))
            continue
        membre(c, y, (0.64, y, 0.40), (0.64, y, 0.18), (0.645, y, 0.02), (0.050, 0.030, 0.018, 0.016))
        membre(c, y, (0.12, y, 0.40), (0.05, y, 0.22), (0.07, y, 0.02), (0.060, 0.034, 0.019, 0.016))


def modeler(nom, etiree):
    bornes = ((-0.32, 1.05), (-0.20, 0.20), (-0.01, 0.82)) if etiree else ((-0.16, 1.02), (-0.20, 0.20), (-0.01, 0.82))
    c = Champ(bornes, PAS)
    corps(c)
    tete(c)
    queue(c, etiree)
    pattes(c, etiree)
    if not etiree:
        c.sol()
    me = maillage(*surface_nets(c), nom, FACES)
    me.name = nom
    me.shade_smooth()
    xs, ys, zs = zip(*(v.co[:] for v in me.vertices))
    print(f"{nom} : {len(me.polygons)} faces, de x = {min(xs):.2f} à {max(xs):.2f} m, "
          f"{max(ys) - min(ys):.2f} m de large, {max(zs):.2f} m de haut")
    return me


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    maillages = {modeler("Seh", False), modeler("Seh_etire", True)}
    bpy.data.libraries.write(str(SORTIE), maillages, fake_user=True, compress=True)
    print(f"écrit {SORTIE}")


if __name__ == "__main__":
    main()
