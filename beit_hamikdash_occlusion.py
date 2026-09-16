"""Cuit l'occlusion du ciel des concepts de la visite dans Cycles : couche UV « Occlusion » et visite/occlusion/<concept>.webp."""
import math
import pathlib
import subprocess
import tempfile
import time

import bmesh
import bpy
import numpy as np
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

SORTIE = pathlib.Path(__file__).resolve().parent / "visite" / "occlusion"
COUCHE = "Occlusion"

# Plus fin qu'un texel (barreaux, treillis du soreg), un objet prend l'ombre de ses faces cachées et vire au noir.
AIRE_MIN = 50.0
TEXELS_PAR_FACE_MIN = 10
TEXEL = 0.2
TAILLE = (128, 2048)
ECHANTILLONS = 256
PORTEE = 8.0
# La sonde de visite/sonde.js écarte déjà le ciel du Heikhal : une portée longue y éteindrait la Menora.
PORTEE_SOUS_SONDE = 3.0
SOUS_SONDE = {"heikhal", "parokhet"}
# Sa pénombre (matieres.js) suffit ; cuites, ses parois s'assombriraient et pas les plaques de sculptures_murs.
EXCLUS = {"kodesh_hakodashim"}
# Deux faces collées se disputent la profondeur : la cachée cuit noire et perce, mouchetée, sur les GPU mobiles.
COLLEE = 0.01
PARALLELE = 0.99
TOLERANCE = 0.0005
RETRAIT = 0.98
PAS_TEMOIN = 0.25
PAS_MAX = 128


def aire(obj):
    echelle = obj.matrix_world.to_scale()
    return sum(p.area for p in obj.data.polygons) * abs(echelle.x * echelle.y * echelle.z) ** (2 / 3)


def taille_de(surface):
    voulue = 2 ** math.ceil(math.log2(max(math.sqrt(surface) / TEXEL, 1)))
    return min(max(voulue, TAILLE[0]), TAILLE[1])


def retenus(fusionnes):
    for ident, obj in sorted(fusionnes.items()):
        surface = aire(obj)
        taille = taille_de(surface)
        if ident not in EXCLUS and surface >= AIRE_MIN and taille * taille / len(obj.data.polygons) >= TEXELS_PAR_FACE_MIN:
            yield ident, obj, taille


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
        self.faces, self.face_de, self.origines, sommets, triangles = [], [], [], [], []
        for obj in objets:
            maillage = obj.data
            maillage.calc_loop_triangles()
            base, premiere = len(sommets), len(self.faces)
            sommets += [obj.matrix_world @ v.co for v in maillage.vertices]
            self.faces += [([], geometry.normal([sommets[base + i] for i in poly.vertices])) for poly in maillage.polygons]
            self.origines += [(obj, poly.index) for poly in maillage.polygons]
            for tri in maillage.loop_triangles:
                triangles.append([base + i for i in tri.vertices])
                self.face_de.append(premiere + tri.polygon_index)
                self.faces[premiere + tri.polygon_index][0].append([sommets[i] for i in triangles[-1]])
        self.aires = [sum(geometry.area_tri(*t) for t in triangles_) for triangles_, _ in self.faces]
        self.arbre = BVHTree.FromPolygons(sommets, triangles)
        self.retirees = set()

    def temoins(self, k):
        return (point for triangle in self.faces[k][0] for point in points_temoins(triangle))

    def couverte(self, k):
        return self.faces[k][1].length > 0 and all(self.couvrante(point, k) is not None for point in self.temoins(k))

    # Recouverte en partie seulement, elle reste ; la plus petite des deux recule derrière l'autre.
    def a_reculer(self, k):
        return self.faces[k][1].length > 0 and not self.mince(k) and any(
            (g := self.couvrante(point, k)) is not None and g[1] <= TOLERANCE and (self.aires[g[0]], -g[0]) > (self.aires[k], -k)
            for point in self.temoins(k))

    def mince(self, k):
        triangle, normale = self.faces[k][0][0], self.faces[k][1]
        centre = sum(triangle, triangle[0] * 0) / 3
        return self.arbre.ray_cast(centre - normale * TOLERANCE, -normale, 2 * COLLEE)[0] is not None

    def couvrante(self, point, k):
        normale = self.faces[k][1]
        for position, _, t, _ in self.arbre.find_nearest_range(point, COLLEE):
            g = self.face_de[t]
            if g == k or g in self.retirees or normale.dot(self.faces[g][1]) < PARALLELE:
                continue
            ecart = position - point
            devant = ecart.dot(normale)
            if -TOLERANCE <= devant <= COLLEE and (ecart - normale * devant).length <= TOLERANCE:
                return g, abs(devant)
        return None


def reculer(objets, collees, reculees):
    for obj in objets:
        vers_local = obj.matrix_world.inverted_safe().to_3x3()
        deplacements = {}
        for k in reculees:
            o, i = collees.origines[k]
            if o is obj:
                for sommet in obj.data.polygons[i].vertices:
                    deplacements[sommet] = deplacements.get(sommet, Vector()) - collees.faces[k][1] * COLLEE
        for sommet, deplacement in deplacements.items():
            obj.data.vertices[sommet].co += vers_local @ deplacement


def retirer(objets, collees):
    for obj in objets:
        indices = {i for k, (o, i) in enumerate(collees.origines) if o is obj and k in collees.retirees}
        maillage = bmesh.new()
        maillage.from_mesh(obj.data)
        maillage.faces.ensure_lookup_table()
        bmesh.ops.delete(maillage, geom=[maillage.faces[i] for i in indices], context="FACES_ONLY")
        maillage.to_mesh(obj.data)
        maillage.free()


def separer_collees(objets):
    collees = Collees(objets)
    for k in range(len(collees.faces)):
        if collees.couverte(k):
            collees.retirees.add(k)
    reculees = [k for k in range(len(collees.faces)) if k not in collees.retirees and collees.a_reculer(k)]
    reculer(objets, collees, reculees)
    retirer(objets, collees)
    print(f"  faces collées sur {len(collees.faces)} : {len(collees.retirees)} retirées, {len(reculees)} reculées de {COLLEE * 100:.0f} cm")


def preparer_cycles():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for appareil in prefs.devices:
        appareil.use = True
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = ECHANTILLONS
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Occlusion")


def deplier(obj, taille):
    obj.data.uv_layers.active = obj.data.uv_layers.new(name=COUCHE)
    for o in bpy.context.view_layer.objects:
        o.select_set(o is obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=2.0 / taille, area_weight=0.0)
    bpy.ops.uv.pack_islands(margin=2.0 / taille, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    return len(obj.data.uv_layers) - 1


def cuire(obj, taille, portee):
    bpy.context.scene.world.light_settings.distance = portee
    image = bpy.data.images.new(obj.name, taille, taille, float_buffer=True, is_data=True)
    noeuds = []
    for fente in obj.material_slots:
        if fente.material is None or fente.material.node_tree is None:
            continue
        arbre = fente.material.node_tree
        noeud = arbre.nodes.new("ShaderNodeTexImage")
        noeud.image = image
        arbre.nodes.active = noeud
        noeuds.append((arbre, noeud))
    bpy.ops.object.bake(type="AO", margin=4, margin_type="EXTEND", use_clear=True, uv_layer=COUCHE)
    for arbre, noeud in noeuds:
        arbre.nodes.remove(noeud)
    return image


# Cuite au double puis réduite : la réduction efface le bruit de Cycles, qui doublait le poids du WebP.
def ecrire(image, chemin, taille, brut):
    pixels = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(-1, 4)
    pixels[:, 1:3] = pixels[:, :1]
    pixels[:, 3] = 1.0
    png = brut / f"{chemin.stem}.png"
    sortie = bpy.data.images.new(chemin.stem, image.size[0], image.size[1], is_data=True)
    sortie.pixels.foreach_set(np.clip(pixels, 0.0, 1.0).ravel())
    sortie.filepath_raw = str(png)
    sortie.file_format = "PNG"
    sortie.save()
    bpy.data.images.remove(sortie)
    bpy.data.images.remove(image)
    subprocess.run(["cwebp", "-quiet", "-noalpha", "-resize", str(taille), str(taille), "-q", "85",
                    str(png), "-o", str(chemin)], check=True)


def cuire_occlusion(fusionnes):
    """Cuit les concepts retenus ; renvoie {concept: {"carte", "canal"}} pour reperes.json."""
    SORTIE.mkdir(parents=True, exist_ok=True)
    for ancienne in SORTIE.glob("*.webp"):
        ancienne.unlink()
    choisis = list(retenus(fusionnes))
    separer_collees([obj for _, obj, _ in choisis])
    preparer_cycles()
    cartes = {}
    debut = time.time()
    with tempfile.TemporaryDirectory() as brut:
        for ident, obj, taille in choisis:
            portee = PORTEE_SOUS_SONDE if ident in SOUS_SONDE else PORTEE
            canal = deplier(obj, 2 * taille)
            chemin = SORTIE / f"{ident}.webp"
            ecrire(cuire(obj, 2 * taille, portee), chemin, taille, pathlib.Path(brut))
            cartes[ident] = {"carte": f"occlusion/{ident}.webp", "canal": canal}
            print(f"  occlusion {ident:26s} {taille:5d} px  {portee:.0f} m  {chemin.stat().st_size / 1e3:5.0f} ko")
    poids = sum(f.stat().st_size for f in SORTIE.glob("*.webp")) / 1e6
    print(f"  {len(cartes)} cartes d'occlusion, {poids:.1f} Mo, {time.time() - debut:.0f} s")
    return cartes
