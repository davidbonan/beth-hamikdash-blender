from typing import NamedTuple

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

import beit_hamikdash_gestes as G

from .matieres import reteindre, teinter


# `pieces` : rangs, de la plus grande à la plus petite, des parties du maillage gardées ; `epaules` : « manches » ou tout
# le « haut » suit un bras levé.
class Habit(NamedTuple):
    asset: str
    matiere: str = None
    couleur: tuple = None
    pieces: tuple = None
    longue: bool = False
    epaules: str = None


_etoffes = {}


# Un matériau par habit teint, partagé entre les figures, sous le nom que la visite reconnaît.
def etoffe_mpfb(objet, habit):
    ancien = objet.data.materials[0]
    if habit.matiere in _etoffes:
        objet.data.materials[0] = _etoffes[habit.matiere]
        bpy.data.materials.remove(ancien)
        return
    arbre = ancien.node_tree
    for noeud in [n for n in arbre.nodes if n.bl_idname == "ShaderNodeTexImage" and n.image]:
        if noeud.outputs["Alpha"].is_linked and not noeud.outputs["Color"].is_linked:
            arbre.nodes.remove(noeud)
        elif any(lien.to_node.bl_idname == "ShaderNodeNormalMap" for lien in noeud.outputs["Color"].links):
            noeud.image = teinter(noeud.image, (1.0, 1.0, 1.0))
        else:
            noeud.image = reteindre(noeud.image, habit.couleur)
    ancien.name = habit.matiere
    _etoffes[habit.matiere] = ancien


def repeser(objet, v, poids):
    groupes = objet.vertex_groups
    for nom in [groupes[e.group].name for e in v.groups]:
        groupes[nom].remove([v.index])
    for nom, w in poids.items():
        (groupes.get(nom) or groupes.new(name=nom)).add([v.index], w, "REPLACE")


def garder_pieces(objet, rangs):
    bm = bmesh.new()
    bm.from_mesh(objet.data)
    pieces, vus = [], set()
    for depart in bm.verts:
        if depart in vus:
            continue
        piece, pile = [], [depart]
        vus.add(depart)
        while pile:
            v = pile.pop()
            piece.append(v)
            for arete in v.link_edges:
                autre = arete.other_vert(v)
                if autre not in vus:
                    vus.add(autre)
                    pile.append(autre)
        pieces.append(piece)
    pieces.sort(key=len, reverse=True)
    bmesh.ops.delete(bm, geom=[v for k, piece in enumerate(pieces) if k not in rangs for v in piece], context="VERTS")
    bm.to_mesh(objet.data)
    bm.free()


# Les `objets` et, si `masque` est donné, les faces du corps qu'il retient, en repère d'armature.
def surface_de(humain, objets, masque=None):
    h = humain
    sommets, faces = [], []
    if masque is not None:
        sommets = [tuple(c) for c in h.co]
        faces = [tuple(p.vertices) for p in h.corps.data.polygons if all(masque[v] for v in p.vertices)]
    for objet in objets:
        base = len(sommets)
        sommets += [tuple(c) for c in h.points_objet(objet)]
        faces += [tuple(base + v for v in p.vertices) for p in objet.data.polygons]
    return BVHTree.FromPolygons(sommets, faces)


def hors_de(surface, p, ecart):
    lieu, normale, _, _ = surface.find_nearest(p)
    if lieu is None or (p - lieu).dot(normale) >= ecart:
        return p
    return lieu + normale * ecart


def _poids_jupe(humain, p):
    h = humain
    z_ourlet = h.sol + 0.05
    u = min(max((h.z_hanche - p.z) / (h.z_hanche - z_ourlet), 0.0), 1.0)
    gauche = G.lisse((p.x / 0.09 + 1.0) / 2.0)
    suit = 0.85 * u ** 0.8
    mollet = 0.45 * G.lisse((u - 0.45) / 0.55)
    poids = {"pelvis": 1.0 - suit}
    for cote, part in (("l", gauche), ("r", 1.0 - gauche)):
        poids[f"thigh_{cote}"] = suit * part * (1.0 - mollet)
        poids[f"calf_{cote}"] = suit * part * mollet
    return poids


def _normaliser(poids, garder=4):
    meilleurs = sorted(poids.items(), key=lambda kv: -kv[1])[:garder]
    total = sum(w for _, w in meilleurs) or 1.0
    return {k: w / total for k, w in meilleurs if w > 1e-4}


def poids_de(humain, zone, p):
    h = humain
    if zone in h.squelette.longueur:
        return {zone: 1.0}
    if zone == "objet":
        raise ValueError("un objet porte le nom de l'os qui le tient")
    if zone.startswith("manche_"):
        cote = zone[-1]
        masque = h.visible & (h.bras | h.cou) & (np.sign(h.co[:, 0]) == (1 if cote == "l" else -1))
        return _normaliser(h.poids_proches(zone, masque, p))
    tronc = h.visible & ~h.bras & ~h.main
    proches = _normaliser(h.poids_proches("tronc", tronc, p))
    if zone == "voile":
        return _normaliser(h.poids_proches("peau_sans_mains", h.visible & ~h.main, p, 6))
    if zone == "jupe" or p.z < h.z_hanche:
        t = G.lisse((h.z_hanche - p.z) / 0.12)
        jupe = _poids_jupe(h, p)
        melange = {k: (1 - t) * proches.get(k, 0.0) + t * jupe.get(k, 0.0) for k in set(proches) | set(jupe)}
        return _normaliser(melange)
    return proches
