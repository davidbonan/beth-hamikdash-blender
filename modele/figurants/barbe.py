import math

import bmesh
import bpy
import numpy as np

from .matieres import TUILE, barbe
from .cuisson import pixels

# Les mèches de MakeHuman, des cartes à trous, se lisaient en paille : fondues en un volume, la barbe se lit d'un bloc.
# La barbe se gonfle jusqu'à la joue ; la moustache, plus mince, ne fait pas morse.
EPAISSEUR = {"moustache": 0.005, "barbe": 0.020}
VOXEL = 0.004
LISSAGE = 12
FACES = 2500
RAYON_DU_VISAGE = 0.09


def _volume(humain, meches_):
    h = humain
    graphe = bpy.context.evaluated_depsgraph_get()
    vers_le_rig = h.rig.matrix_world.inverted()
    bm = bmesh.new()
    for objet in meches_:
        epais = objet.copy()
        bpy.context.scene.collection.objects.link(epais)
        epaisseur = EPAISSEUR["moustache" if "moustache" in objet.name else "barbe"]
        gonfle = epais.modifiers.new("gonfle", "SOLIDIFY")
        gonfle.thickness, gonfle.offset = epaisseur, 0.0
        graphe = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(epais.evaluated_get(graphe), depsgraph=graphe)
        me.transform(vers_le_rig @ objet.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        bpy.data.objects.remove(epais)
    brut = bpy.data.meshes.new(f"{h.nom}_barbe_brute")
    bm.to_mesh(brut)
    bm.free()
    forme = bpy.data.objects.new(brut.name, brut)
    bpy.context.scene.collection.objects.link(forme)
    for type_, reglages in (("REMESH", dict(mode="VOXEL", voxel_size=VOXEL)),
                            ("SMOOTH", dict(factor=0.8, iterations=LISSAGE)),
                            ("DECIMATE", dict(ratio=1.0))):
        modificateur = forme.modifiers.new(type_.lower(), type_)
        for cle, valeur in reglages.items():
            setattr(modificateur, cle, valeur)
    graphe = bpy.context.evaluated_depsgraph_get()
    faces = len(forme.evaluated_get(graphe).data.polygons)
    forme.modifiers["decimate"].ratio = min(1.0, FACES / max(faces, 1))
    bloc = bpy.data.meshes.new_from_object(forme.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(forme)
    bpy.data.meshes.remove(brut)
    return bloc


# La teinte moyenne des mèches, là où la carte n'est pas trouée.
def _teinte(meches_):
    teintes = []
    for objet in meches_:
        for mat in objet.data.materials:
            for noeud in mat.node_tree.nodes:
                if noeud.bl_idname == "ShaderNodeTexImage" and noeud.image and noeud.outputs["Color"].is_linked:
                    px = pixels(noeud.image).reshape(-1, 4)
                    plein = px[px[:, 3] > 0.5]
                    if len(plein):
                        teintes.append(plein[:, :3].mean(axis=0))
    return tuple(np.mean(teintes, axis=0)) if teintes else (0.2, 0.16, 0.13)


# Les mèches descendent : le v suit la hauteur, le u fait le tour du visage.
def _deplier(me):
    co = np.array([v.co[:] for v in me.vertices])
    # L'axe passe derrière toute la barbe : la couture ne la traverse pas.
    cx, cy = co[:, 0].mean(), co[:, 1].max() + RAYON_DU_VISAGE
    couche = me.uv_layers.new(name="UVMap")
    for boucle, uv in zip(me.loops, couche.data):
        x, y, z = co[boucle.vertex_index]
        uv.uv = (math.atan2(x - cx, -(y - cy)) * RAYON_DU_VISAGE / TUILE, z / TUILE)


def barbe_d_un_bloc(humain, meches_):
    h = humain
    teinte = _teinte(meches_)
    me = _volume(h, meches_)
    me.name = f"{h.nom}_barbe"
    _deplier(me)
    couleurs = me.color_attributes.new("Color", "BYTE_COLOR", "CORNER")
    couleurs.data.foreach_set("color", [*teinte, 1.0] * len(me.loops))
    me.shade_smooth()
    me.materials.append(barbe())
    objet = bpy.data.objects.new(me.name, me)
    for c in h.rig.users_collection:
        c.objects.link(objet)
    objet.parent = h.rig
    objet.vertex_groups.new(name="head").add(list(range(len(me.vertices))), 1.0, "REPLACE")
    objet.modifiers.new("Armature", "ARMATURE").object = h.rig
    for o in meches_:
        bpy.data.objects.remove(o)
    return objet
