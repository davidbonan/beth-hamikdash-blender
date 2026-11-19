import itertools
import json
import pathlib

import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

import beit_hamikdash_gestes as G

from .etoffes import _normaliser, poids_de

# Les figurants que fal.ai a modelés d'après un portrait (beit_hamikdash_generer_figurant.py) : <sorte>_<k>.glb, et son âge au .json.
DOSSIER = pathlib.Path(__file__).resolve().parent / "generes"
# Les variantes d'une sorte à moins de cet écart de l'âge le plus proche alternent entre voisins.
ECART_D_AGE = 0.12
# Du bout des doigts tendus au poignet.
MAIN = 0.17
# Bras écartés, la manche ample qui pend suit le bras dont elle est plus près que du tronc ; entre les deux, sur cette bande, elle se partage.
BANDE = 0.04
COTE_DES_TEXTURES = 1024


def _importer(glb):
    avant = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    nouveaux = [o for o in bpy.data.objects if o not in avant]
    maillage = next(o for o in nouveaux if o.type == "MESH")
    graphe = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(maillage.evaluated_get(graphe))
    me.transform(maillage.matrix_world)
    for o in nouveaux:
        bpy.data.objects.remove(o)
    return me


# Pieds au sol, la coiffe à la hauteur de celle que le corps porte, les hanches sur les siennes.
def _caler(h, co):
    haut = max(float(h.points_objet(o)[:, 2].max()) for o in h.rig.children if o.type == "MESH" and o is not h.corps)
    echelle = (max(haut, h.z_tete) - h.sol) / np.ptp(co[:, 2])
    co = (co - [0.0, 0.0, co[:, 2].min()]) * echelle + [0.0, 0.0, h.sol]
    hanche = h.co[h.visible & (np.abs(h.co[:, 2] - h.z_hanche) < 0.03)]
    co[:, :2] += hanche[:, :2].mean(0) - co[np.abs(co[:, 2] - h.z_hanche) < 0.03][:, :2].mean(0)
    return co


# Le modèle est bâti bras écartés : les bras du corps vont y chercher ses mains.
def _poser_en_a(h, co):
    sq = G.Squelette(h.rig)
    regles = {}
    for cote, s in (("l", 1.0), ("r", -1.0)):
        epaule = sq.tete(f"upperarm_{cote}")
        bout = co[np.argmax(co[:, 0] * s)]
        bout = Vector(co[np.linalg.norm(co - bout, axis=1) < 0.05].mean(0))
        poignet = bout - (bout - epaule).normalized() * MAIN
        regles.update(G.chaine(sq, f"upperarm_{cote}", f"lowerarm_{cote}", poignet, Vector((s * 0.2, 1.0, 0.0)), G.COUDE))
    _, bases = sq.resoudre(regles)
    for nom, base in bases.items():
        os_ = h.rig.pose.bones[nom]
        os_.rotation_mode = "QUATERNION"
        os_.matrix_basis = base
    bpy.context.view_layer.update()
    return {b.name: np.array(h.rig.pose.bones[b.name].matrix @ b.matrix_local.inverted()) for b in h.rig.data.bones}


def _melange(matrices, poids):
    total = sum(poids.values())
    return sum(w * matrices[g] for g, w in poids.items()) / total if total > 0 else np.eye(4)


def _arbre(points, indices):
    arbre = KDTree(len(indices))
    for k, i in enumerate(indices):
        arbre.insert(points[i], k)
    arbre.balance()
    return arbre


def _poids(h, co, matrices):
    os_deformants = {b.name for b in h.rig.data.bones if b.use_deform}
    pose = np.array([(_melange(matrices, {g: w for g, w in pd.items() if g in matrices}) @ [*c, 1.0])[:3]
                     for c, pd in zip(h.co, h.poids)])
    peaux = {"corps": h.visible, "bras": h.visible & (h.bras | h.main), "tronc": h.visible & ~h.bras & ~h.main}
    indices = {nom: np.nonzero(masque)[0] for nom, masque in peaux.items()}
    arbres = {nom: _arbre(pose, i) for nom, i in indices.items()}

    def proches(nom, p):
        somme = {}
        for _, k, d in arbres[nom].find_n(p, 4):
            for g, w in h.poids[indices[nom][k]].items():
                if g in os_deformants:
                    somme[g] = somme.get(g, 0.0) + w / max(d, 1e-3)
        return _normaliser(somme)

    poids = []
    for p in co:
        j = indices["corps"][arbres["corps"].find(p)[1]]
        if h.tete_[j] or h.cou[j] or p[2] < h.sol + 0.12:
            poids.append(proches("corps", p))
            continue
        bras = G.lisse((arbres["tronc"].find(p)[2] - arbres["bras"].find(p)[2]) / BANDE + 0.5)
        buste = poids_de(h, "buste", Vector(p)) if bras < 1.0 else {}
        membre = proches("bras", p) if bras > 0.0 else {}
        poids.append(_normaliser({g: bras * membre.get(g, 0.0) + (1.0 - bras) * buste.get(g, 0.0)
                                  for g in set(membre) | set(buste)}))
    return poids


def _alleger(me):
    for mat in me.materials:
        for noeud in mat.node_tree.nodes:
            if noeud.bl_idname == "ShaderNodeTexImage" and noeud.image and noeud.image.size[0] > COTE_DES_TEXTURES:
                noeud.image.scale(COTE_DES_TEXTURES, COTE_DES_TEXTURES)


# Le corps MakeHuman et ses habits laissent la place ; le corps reste, hors scène, pour ce que les gestes en mesurent.
def _devetir(h):
    for objet in [o for o in h.rig.children if o.type == "MESH" and o is not h.corps]:
        bpy.data.objects.remove(objet)
    h.corps.parent = None
    for collection in h.corps.users_collection:
        collection.objects.unlink(h.corps)


_tours = {}


def _variante(sorte, age):
    ages = {chemin.with_suffix(".glb"): json.loads(chemin.read_text())["age"] for chemin in DOSSIER.glob(f"{sorte}_*.json")
            if chemin.with_suffix(".glb").exists()}
    if not ages:
        return None
    proche = min(abs(a - age) for a in ages.values())
    voisines = sorted(glb for glb, a in ages.items() if abs(a - age) <= proche + ECART_D_AGE)
    tour = _tours.setdefault(sorte, itertools.count())
    return voisines[next(tour) % len(voisines)]


# `sorte` : la tenue, qui choisit parmi les variantes ; sans variante, l'habillage MakeHuman reste.
def revetir_du_genere(h, sorte):
    glb = _variante(sorte, h.gabarit.age)
    if glb is None:
        return h
    me = _importer(glb)
    me.transform(h.rig.matrix_world.inverted())
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = _caler(h, co.reshape(-1, 3))
    matrices = _poser_en_a(h, co)
    poids = _poids(h, co, matrices)
    repos = np.array([(np.linalg.inv(_melange(matrices, pd)) @ [*p, 1.0])[:3] for p, pd in zip(co, poids)])
    me.vertices.foreach_set("co", repos.ravel())
    me.update()
    for os_ in h.rig.pose.bones:
        os_.matrix_basis.identity()
    _devetir(h)
    me.name = f"{h.nom}_genere"
    for mat in me.materials:
        mat.name = f"Figure_Genere_{h.nom}"
    _alleger(me)
    objet = bpy.data.objects.new(me.name, me)
    for collection in h.rig.users_collection:
        collection.objects.link(objet)
    objet.parent = h.rig
    groupes = {}
    for i, pd in enumerate(poids):
        for g, w in pd.items():
            if g not in groupes:
                groupes[g] = objet.vertex_groups.new(name=g)
            groupes[g].add([i], w, "REPLACE")
    objet.modifiers.new("Armature", "ARMATURE").object = h.rig
    return h
