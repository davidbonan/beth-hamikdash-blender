import math

from ..primitives.matieres import MAT_ROC_ERAFLE, MAT_ROC_TAILLE, MAT_SUIE, MAT_TERRE_CUITE_ANCIENNE
from ..primitives.volumes import alea, cyl, prism, revolution
from ..primitives.ouvrages import escalier, massif_evide
from .trace import ABATTU, ALLEGE, BISEAUX, BLOC, HAUTEUR, NICHE_PROFONDEUR, NICHES, VIDES, VOLEES, niche

COL = "10_EzratNashim"


def sens_direct(poly):
    aire = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    return poly if aire > 0 else poly[::-1]


massif_evide("Mehilot_HaAron_roc", *BLOC, VIDES, COL, MAT_ROC_TAILLE())
for volee in VOLEES:
    escalier(f"Mehilot_HaAron_volee_{volee['nom']}", *volee["emprise"], volee["z"][1], volee["z"][0],
             volee["descente"], COL, MAT_ROC_TAILLE())

# Le biseau rend au roc la moitié du carré évidé ; les barres l'ont rayé à l'épaule, et c'est la visite qui trace les sillons.
for k, ((x, y), (sx, sy), z) in enumerate(BISEAUX):
    a, b, d = (x + sx * ABATTU, y), (x, y + sy * ABATTU), (x + sx * ABATTU, y + sy * ABATTU)
    prism(f"Mehilot_HaAron_biseau_{k}", sens_direct([a, d, b]), z, z + HAUTEUR, COL, MAT_ROC_ERAFLE())

# Une lampe à coupelle, l'huile séchée en croûte au fond ; la suie au ciel de la niche. Profil : CHOIX.
COUPELLE = [(0.0, 0.0), (0.09, 0.0), (0.14, 0.05), (0.16, 0.09), (0.145, 0.09), (0.11, 0.045), (0.0, 0.03)]
for k, (mur, sens, sol) in enumerate(NICHES):
    x0, x1, y0, y1, _, z_ciel = niche(mur, sens, sol)
    cx = mur[0] + sens[0] * NICHE_PROFONDEUR * 0.45 if sens[0] else (x0 + x1) / 2 + 0.08 * (alea(f"lampe_{k}") - 0.5)
    cy = mur[1] + sens[1] * NICHE_PROFONDEUR * 0.45 if sens[1] else (y0 + y1) / 2 + 0.08 * (alea(f"lampe_{k}") - 0.5)
    ner = [revolution(f"Mehilot_HaAron_ner_{k}", cx, cy, sol + ALLEGE, COUPELLE, COL, MAT_TERRE_CUITE_ANCIENNE(), verts=14),
           cyl(f"Mehilot_HaAron_ner_{k}_shemen", cx, cy, sol + ALLEGE + 0.036, sol + ALLEGE + 0.043, 0.08, COL, MAT_SUIE(), verts=12)]
    tache = []
    for j in range(8):
        r = 0.22 * (0.8 + 0.4 * alea(f"suie_{k}", j))
        px, py = cx + r * math.cos(j * math.pi / 4), cy + r * math.sin(j * math.pi / 4)
        tache.append((min(max(px, x0 + 0.01), x1 - 0.01), min(max(py, y0 + 0.01), y1 - 0.01)))
    ner.append(prism(f"Mehilot_HaAron_ner_{k}_suie", tache, z_ciel - 0.006, z_ciel - 0.003, COL, MAT_SUIE()))
    for o in ner:
        o["sans_biseau"] = True
