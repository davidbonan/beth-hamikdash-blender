import math

import bmesh
from mathutils import Vector

from ..primitives.matieres import MAT_CALCITE, MAT_FIL_D_ARAIGNEE, MAT_ROC_TAILLE
from ..primitives.volumes import alea, cone, mesh_from_pydata, revolution
from .trace import CHAMBRE, EFFONDREMENT, IMPASSE, X_G2, Y_G1, Y_G3, Z_CHAMBRE, Z_TETE

COL = "10_EzratNashim"
# Ce que les siècles ont laissé dans les galeries fermées : toiles, éboulis, calcite. Tout : CHOIX.


def maillage(nom, morceaux, mat, lisse=False):
    sommets, faces = [], []
    for points, indices in morceaux:
        faces += [[len(sommets) + i for i in face] for face in indices]
        sommets += points
    o = mesh_from_pydata(nom, sommets, faces, COL, mat)
    if lisse:
        o.data.shade_smooth()
    return o


def fil(points, rayon, cotes=3):
    """Un tube sans fond le long de la polyligne, ses normales parties de l'axe : la visite les suit pour le tenir à un pixel."""
    anneaux = []
    for k, p in enumerate(points):
        t = (points[min(k + 1, len(points) - 1)] - points[max(k - 1, 0)]).normalized()
        u = t.cross(Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))).normalized()
        v = t.cross(u)
        anneaux += [tuple(p + rayon * (math.cos(a) * u + math.sin(a) * v)) for a in (2 * math.pi * c / cotes for c in range(cotes))]
    faces = [[k * cotes + c, k * cotes + (c + 1) % cotes, (k + 1) * cotes + (c + 1) % cotes, (k + 1) * cotes + c]
             for k in range(len(points) - 1) for c in range(cotes)]
    return anneaux, faces


# Une vieille toile de cave : des fils tendus d'une paroi à l'autre près de l'angle, alourdis de poussière, d'autres qui pendent.
RAYON_FIL = 0.003
TOILES = [((CHAMBRE[0], CHAMBRE[2], Z_CHAMBRE + 8), (1, 1, -1), 1.3), ((CHAMBRE[1], CHAMBRE[2], Z_CHAMBRE + 8), (-1, 1, -1), 1.0),
          ((CHAMBRE[0], CHAMBRE[3], Z_CHAMBRE + 8), (1, -1, -1), 1.2), ((CHAMBRE[1], CHAMBRE[3], Z_CHAMBRE + 8), (-1, -1, -1), 0.9),
          ((X_G2[0], Y_G1[0], -20), (1, 1, -1), 0.9), ((X_G2[0], Y_G3[1], -25), (1, -1, -1), 1.0), ((134, Y_G3[1], -30), (-1, -1, -1), 0.8),
          ((124, 41.316, Z_TETE), (-1, 1, -1), 1.1), ((124, 49.316, Z_TETE), (-1, -1, -1), 0.9),
          ((106.6, IMPASSE[2], -25), (0, 1, -1), 0.8)]


def ancre(cle, coin, sens, rayon):
    parois = [axe for axe in range(3) if sens[axe]]
    paroi = parois[int(alea(cle) * len(parois))]
    p = list(coin)
    for axe in range(3):
        u = alea(cle, axe + 1)
        if axe != paroi:
            p[axe] += sens[axe] * rayon * u ** 2.2 if sens[axe] else (u - 0.5) * 1.6 * rayon
    return paroi, Vector(p)


def toile(n, coin, sens, rayon):
    fils = []
    for k in range(int(70 * rayon + 20)):
        cle = f"toile_{n}_{k}"
        portee = rayon * (0.4 if k % 2 else 1.0)
        (pa, a), (pb, b) = ancre(cle, coin, sens, portee), ancre(cle + "_b", coin, sens, portee)
        if pa == pb:
            continue
        fleche = (a - b).length * (0.04 + 0.12 * alea(cle, 7))
        courbe = [a.lerp(b, t) - Vector((0, 0, 4 * fleche * t * (1 - t))) for t in (i / 4 for i in range(5))]
        fils.append(fil(courbe, RAYON_FIL))
        if alea(cle, 8) < 0.3:
            longueur = 0.12 + 0.45 * alea(cle, 9)
            balan = Vector((alea(cle, 10) - 0.5, alea(cle, 11) - 0.5, 0)) * 0.12
            fils.append(fil([courbe[2] + balan * (i / 3) ** 2 - Vector((0, 0, longueur * i / 3)) for i in range(4)], RAYON_FIL))
    maillage(f"Mehilot_HaAron_toile_{n}", fils, MAT_FIL_D_ARAIGNEE(RAYON_FIL), lisse=True)["sans_biseau"] = True


for n, (coin, sens, rayon) in enumerate(TOILES):
    toile(n, coin, sens, rayon)


def caillou(cle, x, y, sol, taille):
    bm = bmesh.new()
    for k in range(10):
        theta, phi = 2 * math.pi * alea(cle, k), math.acos(2 * alea(cle, k + 20) - 1)
        r = taille * (0.65 + 0.35 * alea(cle, k + 40))
        bm.verts.new((r * math.sin(phi) * math.cos(theta), r * math.sin(phi) * math.sin(theta), 0.6 * r * math.cos(phi)))
    enveloppe = bmesh.ops.convex_hull(bm, input=bm.verts[:])
    bmesh.ops.delete(bm, geom=[v for v in enveloppe["geom_interior"] if isinstance(v, bmesh.types.BMVert)], context="VERTS")
    bm.verts.index_update()
    bas = min(v.co.z for v in bm.verts)
    points = [(x + v.co.x, y + v.co.y, sol + v.co.z - bas - 0.15 * taille) for v in bm.verts]
    faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    return points, faces


# Le pan tombé au fond de l'impasse : un cône d'éboulis sous la cicatrice du plafond, gros blocs en bas.
X0, X1, Y0, Y1 = EFFONDREMENT[0][:4]
CENTRE, RAYON_TAS, HAUTEUR_TAS = ((X0 + X1) / 2, (Y0 + Y1) / 2), 1.6, 1.1
tas = []
for k in range(80):
    cle = f"eboulis_{k}"
    r, a = RAYON_TAS * math.sqrt(alea(cle, 50)), 2 * math.pi * alea(cle, 51)
    taille = 0.10 + 0.45 * alea(cle, 52) * (1 - 0.6 * r / RAYON_TAS)
    x = max(CENTRE[0] + r * math.cos(a), IMPASSE[0] + taille)
    y = min(max(CENTRE[1] + r * math.sin(a), IMPASSE[2] + taille), IMPASSE[3] - taille)
    tas.append(caillou(cle, x, y, -30 + HAUTEUR_TAS * (1 - r / RAYON_TAS) ** 1.3 * (0.5 + 0.5 * alea(cle, 53)), taille))
maillage("Mehilot_HaAron_eboulis_impasse", tas, MAT_ROC_TAILLE())

# Des éclats détachés des parois, au pied des murs.
ECLATS = [((108.4, 44.3), -25), ((116.0, 59.35), -30), ((135.5, 30.6), Z_CHAMBRE), ((124.5, 31.8), Z_CHAMBRE), ((133.6, 60.0), -35)]
for n, ((x, y), sol) in enumerate(ECLATS):
    eclats = maillage(f"Mehilot_HaAron_eclats_{n}",
             [caillou(f"eclat_{n}_{k}", x + 0.5 * (alea(f"eclat_{n}_{k}", 60) - 0.5), y + 0.5 * (alea(f"eclat_{n}_{k}", 61) - 0.5),
                      sol, 0.04 + 0.09 * alea(f"eclat_{n}_{k}", 62)) for k in range(5)], MAT_ROC_TAILLE())
    eclats["sans_biseau"] = True

# Une goutte, au même point du plafond de la chambre, depuis des siècles : fistuleuses, une stalactite, son pendant au sol.
GOUTTE, Z_PLAFOND = (126.2, 36.2), Z_CHAMBRE + 8
calcite = [cone("Mehilot_HaAron_stalactite", *GOUTTE, Z_PLAFOND - 0.6, Z_PLAFOND, 0.008, 0.07, COL, MAT_CALCITE(), verts=8)]
for k in range(10):
    cle = f"fistuleuse_{k}"
    r, a = 0.12 + 0.3 * alea(cle), 2 * math.pi * alea(cle, 1)
    calcite.append(cone(f"Mehilot_HaAron_fistuleuse_{k}", GOUTTE[0] + r * math.cos(a), GOUTTE[1] + r * math.sin(a),
                        Z_PLAFOND - 0.08 - 0.4 * alea(cle, 2), Z_PLAFOND, 0.011, 0.02, COL, MAT_CALCITE(), verts=6))
calcite.append(revolution("Mehilot_HaAron_stalagmite", *GOUTTE, Z_CHAMBRE,
                          [(0.26, 0.0), (0.22, 0.07), (0.14, 0.16), (0.07, 0.22), (0.0, 0.24)], COL, MAT_CALCITE(), verts=12))
for o in calcite:
    o["sans_biseau"] = True
