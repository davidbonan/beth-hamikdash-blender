"""Les faces collées de la scène : deux faces tournées du même côté qui se disputent la profondeur, l'une retirée ou reculée derrière l'autre."""
import math
import pathlib

import bmesh
import numpy as np
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

from beit_hamikdash_memoire import cle_de, garder, reprendre

# Deux faces collées se disputent la profondeur : la cachée cuit noire et perce, mouchetée, sur les GPU mobiles.
COLLEE = 0.01
PARALLELE = 0.99
TOLERANCE = 0.0005
RETRAIT = 0.98
PAS_TEMOIN = 0.25
PAS_MAX = 128


def points_temoins(triangle):
    centre = sum(triangle, triangle[0] * 0) / 3
    a, b, c = (centre.lerp(coin, RETRAIT) for coin in triangle)
    pas = min(PAS_MAX, max(1, math.ceil(max((b - a).length, (c - a).length) / PAS_TEMOIN)))
    for i in range(pas + 1):
        for j in range(pas + 1 - i):
            yield a + (b - a) * (i / pas) + (c - a) * (j / pas)


# Seules les faces tournées du même côté se disputent la profondeur ; dos à dos, chacune est dans le volume de l'autre.
class Collees:
    def __init__(self, objets):
        self.faces, self.face_de, self.origines, self.coins, sommets, triangles = [], [], [], [], [], []
        centres = []
        for obj in objets:
            maillage = obj.data
            maillage.calc_loop_triangles()
            base, premiere = len(sommets), len(self.faces)
            sommets += [obj.matrix_world @ v.co for v in maillage.vertices]
            self.faces += [([], geometry.normal([sommets[base + i] for i in poly.vertices])) for poly in maillage.polygons]
            centres += [sum((sommets[base + i] for i in poly.vertices), Vector()) / len(poly.vertices)
                        for poly in maillage.polygons]
            self.origines += [(obj, poly.index) for poly in maillage.polygons]
            self.coins += [frozenset(base + i for i in poly.vertices) for poly in maillage.polygons]
            for tri in maillage.loop_triangles:
                triangles.append([base + i for i in tri.vertices])
                self.face_de.append(premiere + tri.polygon_index)
                self.faces[premiere + tri.polygon_index][0].append([sommets[i] for i in triangles[-1]])
        self.aires = [sum(geometry.area_tri(*t) for t in triangles_) for triangles_, _ in self.faces]
        self.arbre = BVHTree.FromPolygons(sommets, triangles)
        self.retirees = set()
        # La boucle lit `retirees` pendant qu'elle le remplit : l'ordre décide donc qui des deux
        # faces d'une paire tombe. Pris sur l'indice, cet ordre était CUMULÉ sur toute la scène —
        # un maillage qui changeait de nombre de faces décalait tous les suivants et faisait
        # basculer des décisions à l'autre bout du Har HaBayit, donc recuire leurs cartes. La clé
        # ci-dessous ne tient qu'à la face elle-même : aire, centre, et son rang DANS son objet.
        self.cles = [(round(self.aires[k], 9), *(round(c, 6) for c in centres[k]),
                      self.origines[k][0].name, self.origines[k][1])
                     for k in range(len(self.faces))]
        self.ordre = sorted(range(len(self.faces)), key=self.cles.__getitem__)

    def temoins(self, k):
        return (point for triangle in self.faces[k][0] for point in points_temoins(triangle))

    def couverte(self, k):
        return self.faces[k][1].length > 0 and all(any(self.couvrantes(point, k)) for point in self.temoins(k))

    # Recouverte en partie seulement, elle reste ; la plus petite des deux recule derrière l'autre.
    def a_reculer(self, k):
        return self.faces[k][1].length > 0 and not self.mince(k) and any(
            devant <= TOLERANCE and self.cles[g] > self.cles[k]
            for point in self.temoins(k) for g, devant in self.couvrantes(point, k))

    def mince(self, k):
        triangle, normale = self.faces[k][0][0], self.faces[k][1]
        centre = sum(triangle, triangle[0] * 0) / 3
        return self.arbre.ray_cast(centre - normale * TOLERANCE, -normale, 2 * COLLEE)[0] is not None

    # Toutes, pas la première : l'ordre de `find_nearest_range` suit le BVH de la scène entière.
    def couvrantes(self, point, k):
        normale = self.faces[k][1]
        for position, _, t, _ in self.arbre.find_nearest_range(point, COLLEE):
            g = self.face_de[t]
            # Une voisine du même maillage n'est pas collée : les témoins d'une petite face frôlent ses arêtes.
            if g == k or g in self.retirees or normale.dot(self.faces[g][1]) < PARALLELE or not self.coins[k].isdisjoint(self.coins[g]):
                continue
            ecart = position - point
            devant = ecart.dot(normale)
            if -TOLERANCE <= devant <= COLLEE and (ecart - normale * devant).length <= TOLERANCE:
                yield g, abs(devant)


def positions_reculees(objets, collees, reculees):
    """Les sommets des faces `reculees`, (rang de l'objet, sommet), et leur position reculée en repère local."""
    sommets, positions = [], []
    for rang, obj in enumerate(objets):
        vers_local = obj.matrix_world.inverted_safe().to_3x3()
        deplacements = {}
        for k in reculees:
            o, i = collees.origines[k]
            if o is obj:
                for sommet in obj.data.polygons[i].vertices:
                    deplacements[sommet] = deplacements.get(sommet, Vector()) - collees.faces[k][1] * COLLEE
        for sommet, deplacement in deplacements.items():
            sommets.append((rang, sommet))
            positions.append(obj.data.vertices[sommet].co + vers_local @ deplacement)
    return np.array(sommets, dtype=np.int64).reshape(-1, 2), np.array(positions, dtype=np.float32).reshape(-1, 3)


def decider_la_separation(objets):
    """Les faces à retirer, (rang de l'objet, face), et les sommets à reculer avec leur position, sans toucher aux maillages."""
    collees = Collees(objets)
    for k in collees.ordre:
        if collees.couverte(k):
            collees.retirees.add(k)
    reculees = [k for k in collees.ordre if k not in collees.retirees and collees.a_reculer(k)]
    rang = {obj.name: r for r, obj in enumerate(objets)}
    retirees = [(rang[collees.origines[k][0].name], collees.origines[k][1]) for k in sorted(collees.retirees)]
    sommets, positions = positions_reculees(objets, collees, reculees)
    return {"retirees": np.array(retirees, dtype=np.int64).reshape(-1, 2), "sommets": sommets, "positions": positions,
            "faces": np.array(len(collees.faces)), "reculees": np.array(len(reculees))}


def appliquer_la_separation(objets, separation):
    for (rang, sommet), position in zip(separation["sommets"], separation["positions"]):
        objets[rang].data.vertices[sommet].co = position
    retirees = separation["retirees"]
    for rang, obj in enumerate(objets):
        maillage = bmesh.new()
        maillage.from_mesh(obj.data)
        maillage.faces.ensure_lookup_table()
        bmesh.ops.delete(maillage, geom=[maillage.faces[i] for i in retirees[retirees[:, 0] == rang, 1]], context="FACES_ONLY")
        maillage.to_mesh(obj.data)
        maillage.free()


# Six minutes pour décider, sur la géométrie de toute la scène : la décision se reprend tant que rien n'y a bougé.
def separer_collees(objets):
    cle = cle_de(objets, [pathlib.Path(__file__)])
    separation = reprendre("collees", cle)
    reprise = separation is not None
    if not reprise:
        separation = decider_la_separation(objets)
        garder("collees", cle, separation)
    appliquer_la_separation(objets, separation)
    print(f"  faces collées sur {int(separation['faces'])} : {len(separation['retirees'])} retirées, "
          f"{int(separation['reculees'])} reculées de {COLLEE * 100:.0f} cm{' (décision reprise)' if reprise else ''}")
