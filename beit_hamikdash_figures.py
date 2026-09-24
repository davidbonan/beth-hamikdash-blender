"""Blender -b beit_hamikdash.blend -P beit_hamikdash_figures.py [-- [--troupe figures_shoeva] rôle …] — écrit visite/<troupe>.glb et .json."""
import json
import math
import pathlib
import sys
import zlib
from typing import NamedTuple

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

RACINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
import beit_hamikdash_gestes as G  # noqa: E402
from beit_hamikdash_visite import AMA, DOSSIER, Z_AZ, Z_BAT, Z_EZI, Z_EZN, comprimer, en_metres  # noqa: E402

from bl_ext.blender_org.mpfb.entities.objectproperties import HumanObjectProperties  # noqa: E402
from bl_ext.blender_org.mpfb.services.humanservice import HumanService  # noqa: E402
from bl_ext.blender_org.mpfb.services.locationservice import LocationService  # noqa: E402
from bl_ext.blender_org.mpfb.services.rigservice import RigService  # noqa: E402
from bl_ext.blender_org.mpfb.services.targetservice import TargetService  # noqa: E402

DONNEES = pathlib.Path(LocationService.get_user_data())
TOUR = 2.0 * math.pi
N_ANNEAU = 64

BRAS = ("upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky")
MAIN = ("hand", "thumb", "index", "middle", "ring", "pinky")
JAMBE = ("thigh", "calf", "foot", "ball")


def _alea(nom, k):
    return (zlib.crc32(f"{nom}#{k}".encode()) % 10007) / 10007


LIN = (0.80, 0.78, 0.72)
TEKHELET = (0.030, 0.075, 0.30)
ARGAMAN = (0.22, 0.025, 0.12)
SHANI = (0.45, 0.022, 0.020)
DRAP_NOIR = (0.018, 0.018, 0.021)
TALITH = (0.78, 0.76, 0.70)
RAIE_TALITH = (0.02, 0.02, 0.035)
LAINE_BLEUE = (0.035, 0.050, 0.11)
CHENE = (0.28, 0.17, 0.08)
BOYAU = (0.62, 0.52, 0.36)
BRONZE = (0.62, 0.40, 0.18)
CHAIR = (0.55, 0.16, 0.12)
OR = (1.0, 0.74, 0.30)
ARGENT = (0.90, 0.91, 0.93)
ETOUPE = (0.09, 0.07, 0.05)
METAUX = (OR, BRONZE, ARGENT)


TUILE = 0.04


def _image(nom, rgb, donnees=False):
    cote = rgb.shape[0]
    image = bpy.data.images.new(nom, cote, cote, alpha=False)
    if donnees:
        image.colorspace_settings.name = "Non-Color"
    rgba = np.ones((cote, cote, 4), dtype=np.float32)
    rgba[..., :3] = rgb
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    return image


# Armure toile, ou sergé, raccordable : `fils` fils par tuile de TUILE mètres.
def trame(nom, fils, serge=False, duvet=0.0, cote=256):
    alea = np.random.default_rng(zlib.crc32(nom.encode()))
    t = (np.arange(cote) + 0.5) / cote * fils
    x, y = np.meshgrid(t, t)
    i, j = x.astype(int) % fils, y.astype(int) % fils
    grosseur_c, grosseur_t = 0.75 + 0.5 * alea.random(fils), 0.75 + 0.5 * alea.random(fils)
    dessus = ((i - j) % 4 < 2) if serge else ((i + j) % 2 == 0)
    bombe_c = np.sin(np.pi * (x % 1.0)) ** 0.7 * np.sin(np.pi * (y % 1.0)) ** 0.25 * grosseur_c[i]
    bombe_t = np.sin(np.pi * (y % 1.0)) ** 0.7 * np.sin(np.pi * (x % 1.0)) ** 0.25 * grosseur_t[j]
    hauteur = np.where(dessus, bombe_c, bombe_t)
    if duvet:
        bruit = alea.random((cote, cote))
        for _ in range(3):
            bruit = (bruit + np.roll(bruit, 1, 0) + np.roll(bruit, 1, 1) + np.roll(bruit, (1, 1), (0, 1))) / 4
        hauteur = hauteur * (1.0 - duvet) + (bruit - bruit.mean() + 0.5) * duvet
    fil = np.where(dessus, grosseur_c[i], grosseur_t[j])
    teinte = (0.78 + 0.22 * hauteur) * (0.96 + 0.08 * (fil - 0.75))
    force = 0.12 * cote / fils
    gx = (np.roll(hauteur, -1, 1) - np.roll(hauteur, 1, 1)) * force
    gy = (np.roll(hauteur, -1, 0) - np.roll(hauteur, 1, 0)) * force
    normale = np.dstack([-gx, -gy, np.ones_like(hauteur)])
    normale /= np.linalg.norm(normale, axis=2, keepdims=True)
    return (_image(f"{nom}_couleur", np.repeat(teinte[..., None], 3, axis=2)),
            _image(f"{nom}_relief", normale * 0.5 + 0.5, donnees=True))


def _douille(douilles, identifiant):
    return next(d for d in douilles if d.identifier == identifiant)


def _matiere(nom, rugosite, metal=0.0, tissu=None):
    mat = bpy.data.materials.get(nom)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(nom)
    mat.use_nodes = True
    mat.use_backface_culling = False
    arbre = mat.node_tree
    bsdf = next(n for n in arbre.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    couleur = arbre.nodes.new("ShaderNodeVertexColor")
    couleur.layer_name = "Color"
    bsdf.inputs["Roughness"].default_value = rugosite
    bsdf.inputs["Metallic"].default_value = metal
    if tissu is None:
        arbre.links.new(couleur.outputs["Color"], bsdf.inputs["Base Color"])
        return mat
    teinte, relief = tissu
    image = arbre.nodes.new("ShaderNodeTexImage")
    image.image = teinte
    melange = arbre.nodes.new("ShaderNodeMix")
    melange.data_type, melange.blend_type = "RGBA", "MULTIPLY"
    melange.inputs["Factor"].default_value = 1.0
    arbre.links.new(couleur.outputs["Color"], _douille(melange.inputs, "A_Color"))
    arbre.links.new(image.outputs["Color"], _douille(melange.inputs, "B_Color"))
    arbre.links.new(_douille(melange.outputs, "Result_Color"), bsdf.inputs["Base Color"])
    carte = arbre.nodes.new("ShaderNodeTexImage")
    carte.image = relief
    normale = arbre.nodes.new("ShaderNodeNormalMap")
    arbre.links.new(carte.outputs["Color"], normale.inputs["Color"])
    arbre.links.new(normale.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def lin():
    return _matiere("Figure_Lin", 0.82, tissu=trame("lin", 24))


def laine():
    return _matiere("Figure_Laine", 0.92, tissu=trame("laine", 16, serge=True, duvet=0.35))


def velours():
    return _matiere("Figure_Velours", 0.75, tissu=trame("velours", 32, duvet=0.85))


def feutre():
    return _matiere("Figure_Feutre", 0.62)


def bois():
    return _matiere("Figure_Bois", 0.6)


def metal():
    return _matiere("Figure_Metal", 0.32, 1.0)


def poil():
    return _matiere("Figure_Poil", 0.9)


def corne():
    return _matiere("Figure_Corne", 0.45)


_teintes = {}


def _retoucher(image, cle, cote, retouche):
    cle = (image.filepath or image.name, cle, cote)
    if cle in _teintes:
        return _teintes[cle]
    copie = image.copy()
    copie.name = f"{pathlib.Path(image.name).stem}_{len(_teintes)}"
    if copie.size[0] > cote:
        copie.scale(cote, cote)
    px = np.empty(len(copie.pixels), dtype=np.float32)
    copie.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    retouche(px)
    copie.pixels.foreach_set(px.ravel())
    copie.pack()
    _teintes[cle] = copie
    return copie


def teinter(image, facteur, cote=1024):
    def multiplier(px):
        px[:, :3] *= np.array(facteur, dtype=np.float32)
    return _retoucher(image, ("teinte", tuple(round(f, 3) for f in facteur)), cote, multiplier)


# Garde le grain et l'ombre des plis ; la clarté médiane prend la teinte `couleur`.
def reteindre(image, couleur, cote=1024):
    def remplacer(px):
        clarte = px[:, :3] @ np.array((0.2126, 0.7152, 0.0722), dtype=np.float32)
        relative = 1.0 + 0.5 * (clarte / max(float(np.median(clarte)), 1e-3) - 1.0)
        px[:, :3] = np.minimum(relative[:, None] * np.array(couleur, dtype=np.float32), 1.0)
    return _retoucher(image, ("reteinte", tuple(round(c, 3) for c in couleur)), cote, remplacer)


def teinter_objet(objet, facteur, cote=1024):
    for mat in objet.data.materials:
        for relief in [n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeNormalMap"]:
            mat.node_tree.nodes.remove(relief)
        for noeud in mat.node_tree.nodes:
            if noeud.bl_idname == "ShaderNodeTexImage" and noeud.image and "normal" not in noeud.image.name \
                    and not noeud.image.name.endswith(("_hn.png", "_s.png")):
                noeud.image = teinter(noeud.image, facteur, cote)


# Un maillage sans couleur de sommets en reçoit une seule : la matière des figures la lit.
def teinter_maillage(me, couleur):
    couleurs = me.color_attributes.new("Color", "BYTE_COLOR", "CORNER")
    couleurs.data.foreach_set("color", [*couleur, 1.0] * len(me.loops))


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


class Gabarit(NamedTuple):
    taille: float = 1.75
    genre: float = 1.0
    age: float = 0.6
    muscle: float = 0.55
    poids: float = 0.5
    peau: str = "middleage_caucasian_male"
    teint: tuple = (0.82, 0.70, 0.60)


def _hauteur(humain):
    evalue = humain.evaluated_get(bpy.context.evaluated_depsgraph_get())
    maillage = evalue.to_mesh()
    zs = [v.co.z for v in maillage.vertices]
    evalue.to_mesh_clear()
    return min(zs), max(zs)


# La macro « height » de MakeHuman n'est pas en mètres.
def _regler_taille(humain, taille):
    def essai(v):
        HumanObjectProperties.set_value("height", v, entity_reference=humain)
        TargetService.reapply_macro_details(humain)
        bas, haut = _hauteur(humain)
        return haut - bas

    v0, h0 = 0.5, essai(0.5)
    v1 = min(max(v0 + (taille - h0) / 0.45, 0.0), 1.0)
    h1 = essai(v1)
    for _ in range(4):
        if abs(h1 - taille) < 0.004 or abs(h1 - h0) < 1e-5:
            break
        v2 = min(max(v1 + (taille - h1) * (v1 - v0) / (h1 - h0), 0.0), 1.0)
        v0, h0, v1, h1 = v1, h1, v2, essai(v2)
    bas, _ = _hauteur(humain)
    humain.location.z = -bas


def _asset(humain, type_, chemin):
    return HumanService.add_mhclo_asset(str(DONNEES / chemin), humain, asset_type=type_, subdiv_levels=0,
                                        material_type="GAMEENGINE")


class Humain:
    def __init__(self, nom, gabarit, cheveux=None, barbe=None, teinte_poils=(0.35, 0.28, 0.24), sourcils=1):
        g = gabarit
        macro = TargetService.get_default_macro_info_dict()
        macro.update(gender=g.genre, age=g.age, muscle=g.muscle, weight=g.poids, height=0.5, proportions=0.6)
        macro["race"] = {"caucasian": 0.72, "african": 0.14, "asian": 0.14}
        self.nom, self.gabarit = nom, g
        self.corps = HumanService.create_human(macro_detail_dict=macro)
        _regler_taille(self.corps, g.taille)
        self.rig = HumanService.add_builtin_rig(self.corps, "game_engine")
        HumanService.set_character_skin(str(DONNEES / f"skins/{g.peau}/{g.peau}.mhmat"), self.corps,
                                        skin_type="GAMEENGINE")
        teinter_objet(self.corps, tuple(c * (0.90 + 0.14 * _alea(nom, 7)) for c in g.teint))
        self.poils = []
        yeux = _asset(self.corps, "Eyes", "eyes/low-poly/low-poly.mhclo")
        teinter_objet(yeux, (1.0, 1.0, 1.0), 256)
        self.accessoires = [yeux]
        poils = [("Eyebrows", f"eyebrows/eyebrow{sourcils:03d}/eyebrow{sourcils:03d}.mhclo"),
                 ("Hair", cheveux and f"hair/{cheveux}/{cheveux}.mhclo")]
        poils += [("Clothes", f"clothes/{b}/{b}.mhclo") for b in barbe or ()]
        self.cheveux = None
        for type_, chemin in poils:
            if chemin:
                objet = _asset(self.corps, type_, chemin)
                teinter_objet(objet, teinte_poils, 512)
                self.poils.append(objet)
                if type_ == "Hair":
                    self.cheveux = objet
        self.vetements_mpfb, self.habits = [], []
        self.obstacles = {}
        self.rig.name = nom
        self.corps.name = f"{nom}_corps"

    def vetir_mpfb(self, habit):
        objet = _asset(self.corps, "Clothes", f"clothes/{habit.asset}/{habit.asset}.mhclo")
        if habit.matiere:
            etoffe_mpfb(objet, habit)
        else:
            teinter_objet(objet, (1.0, 1.0, 1.0), 1024)
        self.vetements_mpfb.append(objet)
        self.habits.append((objet, habit))
        return objet

    def detendre(self):
        sq = G.Squelette(self.rig)
        regles = {}
        for cote, s in (("l", 1.0), ("r", -1.0)):
            epaule = sq.tete(f"upperarm_{cote}")
            longueur = sq.longueur[f"upperarm_{cote}"] + sq.longueur[f"lowerarm_{cote}"]
            main = epaule + Vector((s * 0.045, -0.035, -0.975 * longueur))
            regles.update(G.chaine(sq, f"upperarm_{cote}", f"lowerarm_{cote}", main, Vector((s * 0.2, 1.0, 0.0)), G.COUDE))
        _, bases = sq.resoudre(regles)
        for nom, base in bases.items():
            os_ = self.rig.pose.bones[nom]
            os_.rotation_mode = "QUATERNION"
            os_.matrix_basis = base
        RigService.apply_pose_as_rest_pose(self.rig)
        for os_ in self.rig.pose.bones:
            os_.matrix_basis = Matrix.Identity(4)
        self.squelette = G.Squelette(self.rig)
        self._mesurer()
        for objet, habit in self.habits:
            if habit.pieces:
                garder_pieces(objet, habit.pieces)
            if habit.epaules:
                self.ajuster_epaules(objet, habit.epaules == "haut")
            if habit.longue:
                self.ample(objet)
                ourlet = float(self.points_objet(objet)[:, 2].min()) + 0.10
                self.efface |= ~self.bras & ~self.main & (self.co[:, 2] > ourlet) & (self.co[:, 2] < self.z_hanche + 0.05)

    # Épaules relevées et haut des manches, trop amples pour suivre un bras levé : ramenés sur la peau, ils en prennent les poids.
    # Le col d'une veste, rabattu sur la nuque, découvrait celui de la chemise : elle n'y ramène que ses manches.
    def ajuster_epaules(self, objet, epaules):
        passage = self.rig.matrix_world.inverted() @ objet.matrix_world
        retour = passage.inverted()
        corps, bras = surface_de(self, [], self.visible), surface_de(self, [], self.visible & self.bras)
        groupes = objet.vertex_groups
        for v in objet.data.vertices:
            p = passage @ v.co
            avant = {groupes[e.group].name: e.weight for e in v.groups}
            haut_du_bras = sum(w for k, w in avant.items() if k.startswith("upperarm"))
            t = max(G.lisse((p.z - self.z_epaule + 0.07) / 0.06) if epaules else 0.0, 0.85 * G.lisse(haut_du_bras / 0.5))
            if t <= 0.0:
                continue
            lieu, normale, _, _ = (bras if haut_du_bras > 0.3 else corps).find_nearest(p)
            v.co = retour @ p.lerp(lieu + normale * 0.015, t)
            peau = _normaliser(self.poids_proches("peau", self.visible, lieu))
            repeser(objet, v, _normaliser({k: (1 - t) * avant.get(k, 0.0) + t * peau.get(k, 0.0)
                                           for k in set(avant) | set(peau)}))

    # Avec les poids MakeHuman, chaque jambe emporterait son pan de robe comme une jambe de pantalon.
    def ample(self, objet):
        groupes = objet.vertex_groups
        passage = self.rig.matrix_world.inverted() @ objet.matrix_world
        for v in objet.data.vertices:
            noms = [groupes[e.group].name for e in v.groups]
            jambe = sum(e.weight for e, nom in zip(v.groups, noms) if nom.startswith(JAMBE) or nom == "pelvis")
            p = passage @ v.co
            if jambe < 0.5 or p.z >= self.z_hanche:
                continue
            repeser(objet, v, poids_de(self, "jupe", p))

    def _mesurer(self):
        me = self.corps.data
        noms = {g.index: g.name for g in self.corps.vertex_groups}
        n = len(me.vertices)
        self.co = np.empty(n * 3, dtype=np.float64)
        me.vertices.foreach_get("co", self.co)
        self.co = self.co.reshape(n, 3)
        self.poids = [{noms[e.group]: e.weight for e in v.groups} for v in me.vertices]

        def part(prefixes):
            return np.array([sum(w for k, w in p.items() if k.startswith(prefixes)) for p in self.poids])

        self.visible = np.array([p.get("body", 0.0) > 0.5 for p in self.poids])
        self.bras = part(BRAS) > 0.5
        self.main = part(MAIN) > 0.3
        self.tete_ = part(("head",)) > 0.5
        self.cou = part(("neck",)) > 0.5
        self.efface = np.array([any(k.startswith("Delete.") and w > 0.5 for k, w in p.items()) for p in self.poids])
        self.sol = float(self.co[self.visible, 2].min())
        sq = self.squelette
        self.z_hanche = sq.tete("pelvis").z
        self.z_epaule = sq.tete("upperarm_l").z
        self.z_cou = sq.tete("neck_01").z
        self.z_tete = float(self.co[self.visible, 2].max())
        self.arbre, self.indices_arbre = {}, {}

    def arbre_de(self, masque_nom, masque):
        if masque_nom not in self.arbre:
            indices = np.nonzero(masque)[0]
            arbre = KDTree(len(indices))
            for k, i in enumerate(indices):
                arbre.insert(self.co[i], k)
            arbre.balance()
            self.arbre[masque_nom], self.indices_arbre[masque_nom] = arbre, indices
        return self.arbre[masque_nom], self.indices_arbre[masque_nom]

    def poids_proches(self, masque_nom, masque, point, k=4):
        arbre, indices = self.arbre_de(masque_nom, masque)
        somme = {}
        for _, j, d in arbre.find_n(point, k):
            w = 1.0 / max(d, 1e-3)
            for groupe, valeur in self.poids[indices[j]].items():
                if groupe in self.squelette.longueur:
                    somme[groupe] = somme.get(groupe, 0.0) + w * valeur
        return somme

    def points_objet(self, objet):
        passage = self.rig.matrix_world.inverted() @ objet.matrix_world
        return np.array([(passage @ v.co)[:] for v in objet.data.vertices])

    # Copie du corps réduite à `masque` (et des vêtements MakeHuman `avec`), sur laquelle une étoffe retombe.
    def obstacle(self, nom, masque, avec=()):
        if nom in self.obstacles:
            return self.obstacles[nom]
        groupe = self.corps.vertex_groups.new(name=f"obstacle_{nom}")
        groupe.add([int(i) for i in np.nonzero(masque)[0]], 1.0, "REPLACE")
        collection = bpy.data.collections.new(f"{self.nom}_obstacle_{nom}")
        bpy.context.scene.collection.children.link(collection)
        for source in (self.corps, *avec):
            copie = source.copy()
            collection.objects.link(copie)
            if source is self.corps:
                copie.modifiers.new("obstacle", "MASK").vertex_group = groupe.name
            copie.modifiers.new("collision", "COLLISION")
            copie.collision.thickness_outer = 0.010
            copie.collision.cloth_friction = 8.0
        self.obstacles[nom] = collection
        return collection

    def ranger(self):
        for nom, collection in self.obstacles.items():
            for objet in list(collection.objects):
                bpy.data.objects.remove(objet)
            bpy.data.collections.remove(collection)
            self.corps.vertex_groups.remove(self.corps.vertex_groups[f"obstacle_{nom}"])
        self.obstacles = {}


class Maillage:
    def __init__(self):
        self.sommets, self.faces, self.couleurs, self.zones, self.uvs = [], [], [], [], []
        self.epingles = {}

    def nappe(self, anneaux, couleur, zone, ferme=True, pole_fin=None, epingle=None):
        choisir = couleur if callable(couleur) else (lambda i, j: couleur)
        n, base = len(anneaux[0]), len(self.sommets)
        for i, anneau in enumerate(anneaux):
            self.sommets.extend(anneau)
            self.zones.extend([zone(i) if callable(zone) else zone] * n)
            poids = epingle(i) if epingle else 0.0
            if poids:
                self.epingles.update({base + i * n + k: poids for k in range(n)})
        longueurs = []
        for anneau in anneaux:
            tour = anneau + anneau[:1] if ferme else anneau
            cumul = [0.0]
            for a, b in zip(tour, tour[1:]):
                cumul.append(cumul[-1] + (b - a).length)
            longueurs.append(cumul)
        hauteurs = [0.0]
        for a, b in zip(anneaux, anneaux[1:]):
            hauteurs.append(hauteurs[-1] + sum((q - p).length for p, q in zip(a, b)) / n)

        def uv(i, j):
            return longueurs[i][j] / TUILE, hauteurs[i] / TUILE

        cotes = n if ferme else n - 1
        for i in range(len(anneaux) - 1):
            for j in range(cotes):
                a, b = base + i * n + j, base + i * n + (j + 1) % n
                self.faces.append((a, b, b + n, a + n))
                self.uvs.append((uv(i, j), uv(i, j + 1), uv(i + 1, j + 1), uv(i + 1, j)))
                self.couleurs.append(choisir(i, j))
        if pole_fin is not None:
            p, i = len(self.sommets), len(anneaux) - 1
            dernier = base + i * n
            self.sommets.append(pole_fin)
            self.zones.append(self.zones[-1])
            centre = (longueurs[i][-1] / 2 / TUILE, hauteurs[i] / TUILE + 0.5)
            for j in range(cotes):
                self.faces.append((dernier + j, dernier + (j + 1) % n, p))
                self.uvs.append((uv(i, j), uv(i, j + 1), centre))
                self.couleurs.append(choisir(i - 1, j))


def _angles(n=N_ANNEAU):
    return np.linspace(0.0, TOUR, n, endpoint=False)


def _vers(th):
    return math.sin(th), -math.cos(th)


# θ = 0 devant, θ = π/2 à gauche ; les creux sont comblés.
def enveloppe(points_xy, centre, n=N_ANNEAU, minimum=0.02):
    if len(points_xy) < 3:
        return np.full(n, minimum)
    x = points_xy[:, 0] - centre[0]
    y = points_xy[:, 1] - centre[1]
    th = np.arctan2(x, -y)
    r = np.hypot(x, y)
    ecart = (th[None, :] - _angles(n)[:, None] + math.pi) % TOUR - math.pi
    appui = np.where(np.abs(ecart) < math.pi / 2, r[None, :] * np.cos(ecart), 0.0)
    return np.maximum(appui.max(axis=1), minimum)


def _lisser_cercle(r, fois=2):
    for _ in range(fois):
        r = 0.25 * np.roll(r, 1) + 0.5 * r + 0.25 * np.roll(r, -1)
    return r


def tranche(humain, masque, z, epaisseur=0.018, extra=None):
    sel = masque & (np.abs(humain.co[:, 2] - z) < epaisseur)
    points = humain.co[sel, :2]
    if extra is not None and len(extra):
        points = np.vstack([points, extra[np.abs(extra[:, 2] - z) < epaisseur][:, :2]])
    return points


# La ceinture : un cylindre sur le tronc, à la hauteur `z`, qui ramène la robe sur le corps.
class Ceinture:
    def __init__(self, humain, z, largeur=0.07, jeu=0.012):
        h = humain
        points = tranche(h, h.visible & ~h.bras & ~h.main, z, largeur / 2)
        self.z, self.largeur = z, largeur
        self.cy = 0.5 * (points[:, 1].min() + points[:, 1].max())
        self.rayons = _lisser_cercle(enveloppe(points, (0.0, self.cy)), 4) + jeu

    def rayon(self, th):
        j = th % TOUR / TOUR * N_ANNEAU
        j0, u = int(j) % N_ANNEAU, j - int(j)
        return self.rayons[j0] * (1 - u) + self.rayons[(j0 + 1) % N_ANNEAU] * u

    def point(self, th, z, ecart=0.0):
        r = self.rayon(th) + ecart
        return Vector((r * _vers(th)[0], self.cy + r * _vers(th)[1], z))

    def serrer(self, humain, objet, portee=0.10):
        passage = humain.rig.matrix_world.inverted() @ objet.matrix_world
        retour = passage.inverted()
        for v in objet.data.vertices:
            if sum(e.weight for e in v.groups if objet.vertex_groups[e.group].name.startswith(BRAS)) > 0.5:
                continue
            p = passage @ v.co
            dx, dy = p.x, p.y - self.cy
            r = math.hypot(dx, dy)
            cible = self.rayon(math.atan2(dx, -dy)) - 0.004
            hors = abs(p.z - self.z) - self.largeur / 2
            if r <= cible or hors > portee:
                continue
            k = 1.0 - (1.0 - G.lisse(hors / portee)) * (1.0 - cible / r)
            v.co = retour @ Vector((dx * k, self.cy + dy * k, p.z))


def tube(chemin, rayons, n):
    anneaux = []
    reference = Vector((0.0, -1.0, 0.0))
    for k, (p, r) in enumerate(zip(chemin, rayons)):
        t = (chemin[min(k + 1, len(chemin) - 1)] - chemin[max(k - 1, 0)]).normalized()
        f = reference - t * reference.dot(t)
        if f.length < 1e-5:
            f = t.orthogonal()
        f.normalize()
        g = t.cross(f)
        anneaux.append([p + (f * math.cos(a) + g * math.sin(a)) * r for a in np.linspace(0, TOUR, n, endpoint=False)])
    return anneaux


# Avnet de trois doigts, tour sur tour (Klei HaMikdash 8:19), brodé (8:1), aux coudes (Rashi Shemot 28:7) ; rayures : CHOIX.
class Teintes(NamedTuple):
    bandes: tuple
    raies: tuple


AVNET_BRODE = Teintes(((0.000, LIN), (0.010, TEKHELET), (0.022, ARGAMAN), (0.034, SHANI), (0.046, TEKHELET), (0.056, LIN),
                       (0.064, LIN)), (TEKHELET, ARGAMAN, SHANI))
# « וְאַרְבַּעְתָּן לְבָנִים … וּמִן הַפִּשְׁתָּן לְבַדּוֹ הֵם » (Rambam Klei HaMikdash 8:3) : à Kippour, l'avnet est de lin seul.
AVNET_DE_LIN = Teintes(tuple((dz, LIN) for dz, _ in AVNET_BRODE.bandes), (LIN,) * 3)


def avnet(mm, ceinture, surface, teintes=AVNET_BRODE):
    z0 = ceinture.z - 0.032
    th = _angles()
    anneaux, couleurs = [], []
    for dz, couleur in teintes.bandes:
        epaisseur = 0.003 if dz in (0.0, teintes.bandes[-1][0]) else 0.010
        anneaux.append([ceinture.point(t, z0 + dz, epaisseur) for t in th])
        couleurs.append(couleur)
    mm.nappe(anneaux, lambda i, j: couleurs[i + 1], "buste")
    raies = teintes.raies
    for depart, longueur in ((0.42, 0.52), (0.52, 0.44)):
        travers = Vector((math.cos(depart), math.sin(depart), 0.0))
        rangs = []
        for k in range(14):
            centre = hors_de(surface, ceinture.point(depart, z0 + 0.03 - longueur * k / 13, 0.016), 0.008)
            rangs.append([centre + travers * (0.027 * c) for c in (-1.0, -0.33, 0.33, 1.0)])
        mm.nappe(rangs, lambda i, j: raies[j], "jupe", ferme=False)


def _crane(humain, dessus=()):
    points = humain.co[humain.visible & humain.tete_]
    if len(dessus):
        points = np.vstack([points] + [humain.points_objet(o) for o in dessus])
    return points


# rangs = (z relatif au sommet, écart, échelle) ; `ouverture(dz)` dégage le visage.
def coiffe(mm, humain, rangs, couleur, zone="head", ouverture=None, n=40):
    points = _crane(humain, humain.poils)
    sommet = float(points[:, 2].max())
    tout = _angles(n)
    anneaux = []
    for dz, ecart, echelle in rangs:
        z = sommet + dz
        bande = points[np.abs(points[:, 2] - min(z, sommet - 0.01)) < 0.012]
        if len(bande) < 3:
            bande = points[points[:, 2] > sommet - 0.03]
        cy = 0.5 * (bande[:, 1].min() + bande[:, 1].max())
        r = _lisser_cercle(enveloppe(bande, (0.0, cy), n)) * echelle + ecart
        demi = ouverture(dz) if ouverture else 0.0
        th = np.linspace(demi, TOUR - demi, n) if ouverture else tout
        ri = np.interp(th, np.append(tout, TOUR), np.append(r, r[0]))
        anneaux.append([Vector((a * _vers(t)[0], cy + a * _vers(t)[1], z)) for t, a in zip(th, ri)])
    fin = anneaux[-1]
    mm.nappe(anneaux, couleur, zone, ferme=ouverture is None, pole_fin=sum(fin, Vector()) / len(fin))


# Une bande de lin enroulée « comme un chapeau » (Rambam Klei HaMikdash 8:2), chaque tour chevauchant le précédent.
def migbaat(mm, humain, tours=5.0, par_tour=40, largeur=0.048, epaisseur=0.009, montee=0.022):
    h = humain
    points = _crane(h, h.poils)
    sommet = float(points[:, 2].max())
    contours = {}

    def contour(z):
        cle = round(z * 400) / 400
        if cle not in contours:
            bande = points[np.abs(points[:, 2] - min(cle, sommet - 0.015)) < 0.01]
            cy = 0.5 * (bande[:, 1].min() + bande[:, 1].max())
            contours[cle] = (_lisser_cercle(enveloppe(bande, (0.0, cy)), 6), cy)
        return contours[cle]

    angles = np.append(_angles(), TOUR)
    z0, total = h.z_tete - 0.085, int(tours * par_tour)
    sections = []
    for s in range(total + 1):
        t = s / par_tour
        th = TOUR * t + 0.6
        z = z0 + montee * t + 0.007 * math.sin(th - 0.9)
        r_env, cy = contour(z)
        dome = G.lisse((z - (sommet - 0.05)) / 0.07)
        r = float(np.interp(th % TOUR, angles, np.append(r_env, r_env[0]))) * (1.0 - 0.5 * dome) + epaisseur * (0.8 + 0.3 * t)
        dx, dy = _vers(th)
        centre, dehors = Vector((r * dx, cy + r * dy, z)), Vector((dx, dy, 0.0))
        haut = (HAUT_Z - dehors * (0.2 + 0.9 * dome)).normalized()
        w = largeur * (0.35 + 0.65 * G.lisse(s / 10) * G.lisse((total - s) / 10)) / 2
        e = epaisseur / 2
        profil = ((-e, -w), (e, -0.9 * w), (1.3 * e, 0.0), (e, 0.9 * w), (-e, w), (-0.6 * e, 0.0))
        sections.append([centre + dehors * a + haut * b for a, b in profil])
    mm.nappe(sections, LIN, "head")
    coiffe(mm, h, [(-0.035, 0.010, 0.80), (-0.015, 0.010, 0.62), (0.0, 0.008, 0.42), (0.008, 0.004, 0.2)], LIN, "head")


# « כֹּהֵן גָּדוֹל צוֹנֵף בָּהּ כְּמִי שֶׁלּוֹפֵף עַל הַשֶּׁבֶר » (Rambam Klei HaMikdash 8:2) : la même bande, enroulée à plat.
def mitznefet(mm, humain):
    migbaat(mm, humain, tours=6.0, montee=0.010)


HAUT_Z = Vector((0.0, 0.0, 1.0))


def _crane_et_cheveux(humain):
    h = humain
    return _crane(h, [h.cheveux] if h.cheveux else [])


def _centre_de_voute(points):
    voute = points[points[:, 2] > points[:, 2].max() - 0.07]
    (cx, cy, cz, _), *_ = np.linalg.lstsq(np.hstack([2.0 * voute, np.ones((len(voute), 1))]), (voute ** 2).sum(axis=1), rcond=None)
    return Vector((cx, cy, cz))


# Calotte sur le sommet un peu en arrière, `rayon` celui de son bord : sa distance au centre du crâne est un polynôme cubique
# des rayons lancés sur crâne et cheveux, tirée vers les plus saillants puis relevée du dernier dépassement : lisse et ronde quelles que soient les mèches.
def calotte(mm, humain, couleur, rayon=0.060, recul=0.50, ecart=0.007, rangs=14, n=56):
    h = humain
    tete = h.visible & h.tete_
    arbre = surface_de(h, [], tete)
    centre = _centre_de_voute(h.co[tete])
    axe = Vector((0.0, math.sin(recul), math.cos(recul)))
    u = Vector((1.0, 0.0, 0.0))
    w = axe.cross(u)
    ouverture = math.asin(min(rayon / 0.09, 0.95))
    phis = np.linspace(0.0, TOUR, n, endpoint=False)
    rangs_ = [(ouverture + 0.008, -0.006), (ouverture + 0.003, -0.001)] + [(ouverture * (1.0 - k / rangs), 0.0) for k in range(rangs)]

    def direction(a, phi):
        return axe * math.cos(a) + (u * math.cos(phi) + w * math.sin(phi)) * math.sin(a)

    def termes(a, phi):
        x, y = math.sin(a) * math.cos(phi), math.sin(a) * math.sin(phi)
        return (1.0, x, y, x * x, x * y, y * y, x ** 3, x * x * y, x * y * y, y ** 3)

    echantillons = [(a, phi) for a in np.linspace(0.0, ouverture + 0.12, 10) for phi in phis[::2]]
    mesures = []
    for a, phi in echantillons:
        d = direction(a, phi)
        touche = arbre.ray_cast(centre + d * 0.3, -d)[0]
        mesures.append((touche - centre).length if touche is not None else np.nan)
    mesures = np.array(mesures)
    garde = ~np.isnan(mesures)
    a_, m = np.array([termes(a, phi) for a, phi in echantillons])[garde], mesures[garde]
    poids = np.ones(len(m))
    for _ in range(12):
        coef, *_ = np.linalg.lstsq(a_ * poids[:, None], m * poids, rcond=None)
        poids = np.where(m > a_ @ coef, 1.0, 0.25)
    releve = float((m - a_ @ coef).max()) + ecart

    def distance(a, phi):
        return float(np.dot(termes(a, phi), coef)) + releve

    anneaux = [[centre + direction(a, phi) * (distance(a, phi) + dehors) for phi in phis] for a, dehors in rangs_]
    mm.nappe(anneaux, couleur, "head", pole_fin=centre + axe * distance(0.0, 0.0))


FEUTRE = DRAP_NOIR
RUBAN = (0.006, 0.006, 0.008)


class Borsalino(NamedTuple):
    hauteur: float = 0.120
    bord: float = 0.070
    pli: float = 0.032
    ruban: float = 0.036
    inclinaison: float = 0.10
    ecart: float = 0.006


# Borsalino noir : calotte haute pincée devant et creusée d'un pli, bord large relevé sur les côtés, ruban gros-grain noué à gauche.
# Le bandeau passe à 5 cm au-dessus des yeux, un peu plus bas derrière ; θ = 0 devant.
class Chapeau:
    N = 72
    ARRONDI = 0.018

    def __init__(self, humain, forme):
        h, f = humain, forme
        self.forme = f
        points = _crane_et_cheveux(h)
        yeux = h.points_objet(h.accessoires[0]).mean(axis=0)
        self.pente = math.tan(f.inclinaison)
        niveau = points[:, 2] + self.pente * points[:, 1]
        self.z_bande = float(yeux[2] + 0.052 + self.pente * yeux[1])
        tour = points[(niveau > self.z_bande - 0.01) & (niveau < self.z_bande + 0.06)]
        self.cy = 0.5 * float(tour[:, 1].min() + tour[:, 1].max())
        self.th = _angles(self.N)
        self.r_bande = _lisser_cercle(enveloppe(tour[:, :2], (0.0, self.cy), self.N), 12) + f.ecart
        self.hauteur = max(f.hauteur, float(niveau.max()) - self.z_bande + f.pli + 0.014)

    def point(self, t, r, dz):
        x, y = r * math.sin(t), self.cy - r * math.cos(t)
        return Vector((x, y, self.z_bande - self.pente * y + dz))

    def haut(self, t):
        return self.hauteur - 0.007 * math.cos(t)

    def paroi(self, k, s):
        t = self.th[k]
        pince = sum(math.exp(-((((t - c) + math.pi) % TOUR - math.pi) / 0.45) ** 2) for c in (0.8, TOUR - 0.8))
        return self.r_bande[k] * (1.0 - 0.11 * s) - 0.011 * s * s * pince, self.haut(t) * s

    def couronne(self, mm):
        n, a = self.N, self.ARRONDI
        anneaux = [[self.point(self.th[k], *self.paroi(k, s)) for k in range(n)] for s in np.linspace(0.0, 1.0, 10)[:-1]]
        for phi in np.linspace(0.0, math.pi / 2, 5):
            anneaux.append([self.point(self.th[k], self.paroi(k, 1.0)[0] - a * (1.0 - math.cos(phi)),
                                       self.haut(self.th[k]) - a + a * math.sin(phi)) for k in range(n)])
        r_haut = [self.paroi(k, 1.0)[0] - a for k in range(n)]
        long_ = 0.5 * (r_haut[0] + r_haut[n // 2])

        def creux(p):
            y = p.y - self.cy
            largeur = 0.030 + 0.006 * y / long_
            return Vector((0.0, 0.0, self.forme.pli * G.lisse(1.0 - abs(p.x) / largeur) * G.lisse((long_ - abs(y)) / 0.028)))

        for lam in np.linspace(1.0, 0.0, 15)[1:-1]:
            dome = 0.004 * (1.0 - lam * lam)
            anneaux.append([self.point(self.th[k], lam * r_haut[k], self.haut(self.th[k]) + dome) for k in range(n)])
            anneaux[-1] = [p - creux(p) for p in anneaux[-1]]
        pole = self.point(0.0, 0.0, self.hauteur + 0.004)
        mm.nappe(anneaux, FEUTRE, "head", pole_fin=pole - creux(pole))

    def bord(self, mm):
        epaisseur = 0.0022
        profil = ([(s, -epaisseur) for s in np.linspace(0.0, 1.0, 6)] + [(1.03, 0.0)]
                  + [(s, epaisseur) for s in np.linspace(1.0, 0.0, 6)])

        def releve(t, s):
            return s * s * (0.006 + 0.016 * math.sin(t) ** 2)

        mm.nappe([[self.point(t, r - 0.002 + s * self.forme.bord, releve(t, min(s, 1.0)) + dz) for t, r in zip(self.th, self.r_bande)]
                  for s, dz in profil], FEUTRE, "head")

    def _ceinture(self, s, dehors):
        return [self.point(self.th[k], self.paroi(k, s)[0] + dehors, self.paroi(k, s)[1]) for k in range(self.N)]

    def ruban(self, mm):
        haut = self.forme.ruban / self.hauteur
        mm.nappe([self._ceinture(s, dehors) for s, dehors in ((0.0, 0.0), (0.0, 0.0018), (haut, 0.0018), (haut, 0.0))], RUBAN, "head")
        k0 = int(round(self.N * 0.39))
        rangs = []
        for dk in range(-4, 5):
            demi = 0.55 * haut * (0.45 + 0.55 * min(abs(dk) / 2.0, 1.0))
            k = (k0 + dk) % self.N
            rangs.append([self.point(self.th[k], self.paroi(k, s)[0] + 0.0035, self.paroi(k, s)[1])
                          for s in np.linspace(0.5 * haut - demi, 0.5 * haut + demi, 4)])
        mm.nappe(rangs, RUBAN, "head", ferme=False)


def chapeau(mm, humain, forme=Borsalino()):
    c = Chapeau(humain, forme)
    c.couronne(mm)
    c.bord(mm)
    c.ruban(mm)


RAIES_TALITH = ((0.10, 0.175), (0.20, 0.225), (0.25, 0.275))
ATARA = (0.70, 0.70, 0.68)


# Plié en étole : l'atara cerne la nuque, les deux pans descendent sur la poitrine et tombent par-dessus les bras.
def talith(mm, humain, longueur=1.90, largeur=0.20, pas=0.02):
    h = humain
    surface = surface_de(h, h.vetements_mpfb, h.visible)
    z_col = h.z_cou - 0.01
    cou = tranche(h, h.cou & h.visible, z_col, 0.02)
    cy = 0.5 * (cou[:, 1].min() + cou[:, 1].max())
    r_col = float(np.median(enveloppe(cou, (0.0, cy)))) + 0.02
    th_devant = 0.55
    arc = r_col * (math.pi - th_devant)
    dx, dy = _vers(th_devant)
    depart = Vector((r_col * dx, cy + r_col * dy, z_col))
    sortie_col, sortie_pan = Vector((dx, dy, -0.9)).normalized(), Vector((1.0, 0.0, -0.1)).normalized()

    def bord(s):
        if s <= arc:
            vx, vy = _vers(math.pi - s / r_col)
            return Vector((r_col * vx, cy + r_col * vy, z_col)), Vector((vx, vy, -0.9)).normalized()
        d = s - arc
        return depart + Vector((0.02, -0.15, -1.0)) * d, sortie_col.lerp(sortie_pan, G.lisse(d / 0.12)).normalized()

    nu, nv = round(longueur / pas) + 1, round(largeur / pas) + 1
    rangs = []
    for i in range(nu):
        u = -longueur / 2 + i * pas
        p, dehors = bord(abs(u))
        rang = []
        for j in range(nv):
            q = p + dehors * (j * pas)
            if u < 0:
                q.x = -q.x
            rang.append(hors_de(surface, q, 0.02))
        rangs.append(rang)

    def couleur(i, j):
        s = abs(-longueur / 2 + (i + 0.5) * pas)
        if any(a <= longueur / 2 - s < b for a, b in RAIES_TALITH):
            return RAIE_TALITH
        return ATARA if j < 3 and s < 0.30 else TALITH

    base = len(mm.sommets)
    mm.nappe(rangs, couleur, "voile", ferme=False)
    mm.epingles.update({base + i * nv + j: 1.0 for i in range(nu) for j in range(nv)
                        if abs(-longueur / 2 + i * pas) < arc and j * pas < 0.07})
    return [base, base + nv - 1, base + (nu - 1) * nv, base + nu * nv - 1]


def tzitzit(mm, coins, longueur=0.34):
    for coin in coins:
        for k in range(4):
            ecart = Vector((math.cos(k * 1.57), math.sin(k * 1.57), 0.0)) * 0.005
            chemin = [coin + ecart * (1.0 + 2.0 * s) - HAUT_Z * (longueur * s) for s in np.linspace(0.0, 1.0, 7)]
            rayons = [0.0045 if s < 0.3 and k == 0 else 0.0015 for s in np.linspace(0.0, 1.0, 7)]
            mm.nappe(tube(chemin, rayons, 5), TALITH, "voile")


def tube_simple(chemin, rayon, n=8):
    return tube(chemin, [rayon] * len(chemin), n)


def kinor(mm, repere, echelle=1.0):
    e = echelle
    place = lambda pts: [repere @ p for p in pts]
    caisse = [Vector((0.0, 0.0, z * e)) for z in (-0.01, 0.0, 0.06, 0.12, 0.14)]
    largeurs = (0.11, 0.13, 0.14, 0.13, 0.11)
    anneaux = [[repere @ (c + Vector((w * e * math.cos(a), 0.022 * e * math.sin(a), 0.0)))
                for a in np.linspace(0, TOUR, 16, endpoint=False)] for c, w in zip(caisse, largeurs)]
    mm.nappe(anneaux, CHENE, "objet", pole_fin=repere @ caisse[-1])
    for s in (-1, 1):
        chemin = [Vector((s * (0.10 + 0.08 * math.sin(math.pi * 0.9 * t)) * e, 0.0, (0.11 + 0.42 * t) * e))
                  for t in np.linspace(0, 1, 7)]
        mm.nappe([place(a) for a in tube_simple(chemin, 0.015 * e)], CHENE, "objet")
    joug = [Vector((x * e, 0.0, 0.52 * e)) for x in (-0.15, 0.0, 0.15)]
    mm.nappe([place(a) for a in tube_simple(joug, 0.013 * e)], CHENE, "objet")
    for k in range(7):
        x = (-0.075 + 0.025 * k) * e
        corde = [Vector((x, 0.004, 0.13 * e)), Vector((x * 1.2, 0.004, 0.51 * e))]
        mm.nappe([place(a) for a in tube_simple(corde, 0.0028, 4)], BOYAU, "objet")


def tziltzal(mm, repere):
    profil = ((0.000, 0.014), (0.010, 0.035), (0.016, 0.100), (0.022, 0.115), (0.016, 0.112))
    anneaux = [[repere @ Vector((r * math.cos(a), -z, r * math.sin(a))) for a in np.linspace(0, TOUR, 20, endpoint=False)]
               for z, r in profil]
    mm.nappe(anneaux, BRONZE, "objet")


# Au fond pointu (Zeva'him 88a).
def mizrak(mm, repere):
    tourner_profil(mm, repere, ((0.000, 0.004), (0.02, 0.040), (0.05, 0.080), (0.075, 0.100), (0.082, 0.104), (0.078, 0.094)), OR)


def tourner_profil(mm, repere, profil, couleur, n=22):
    anneaux = [[repere @ Vector((r * math.cos(a), r * math.sin(a), z)) for a in np.linspace(0, TOUR, n, endpoint=False)]
               for z, r in profil]
    mm.nappe(anneaux, couleur, "objet")


# D'argent (Tamid 7:3 ; Bamidbar 10:2), embouchure à l'origine, pavillon au bout du z ; la longueur est un CHOIX.
def hatzotzra(mm, repere):
    profil = ((0.000, 0.004), (0.006, 0.013), (0.016, 0.006), (0.30, 0.006), (0.50, 0.008), (0.56, 0.018),
              (0.60, 0.040), (0.62, 0.062), (0.617, 0.064))
    tourner_profil(mm, repere, profil, ARGENT, 16)


# Une torche : manche de bois tenu à l'origine, tête d'étoupe au bout du z, que la visite allume.
def avouka(mm, repere):
    manche = [Vector((0.0, 0.0, z)) for z in np.linspace(-0.14, 0.32, 5)]
    mm.nappe([[repere @ p for p in a] for a in tube_simple(manche, 0.017)], CHENE, "objet",
             pole_fin=repere @ manche[-1])
    tete = ((0.30, 0.020), (0.32, 0.034), (0.40, 0.038), (0.45, 0.030))
    anneaux = [[repere @ Vector((r * math.cos(a), r * math.sin(a), z)) for a in np.linspace(0, TOUR, 12, endpoint=False)]
               for z, r in tete]
    mm.nappe(anneaux, ETOUPE, "objet", pole_fin=repere @ Vector((0.0, 0.0, 0.47)))


def bout_a_bout(mm, repere, chemin, rayons, couleur, n=10):
    chemin = [Vector((0.0, 0.0, -0.01)) + chemin[0]] + chemin
    rayons = [0.004] + list(rayons)
    mm.nappe([[repere @ p for p in a] for a in tube(chemin, rayons, n)], couleur, "objet", pole_fin=repere @ chemin[-1])


# Une bûche de la ma'arakha (Tamid 2:3), le long du z du repère.
RAYON_GIZRA = 0.045


def gizra(mm, repere, longueur=0.72, rayon=RAYON_GIZRA):
    chemin = [Vector((0.0, 0.0, z)) for z in np.linspace(-longueur / 2, longueur / 2, 6)]
    bout_a_bout(mm, repere, chemin, [rayon * (1.0 + 0.08 * math.sin(3.1 * k)) for k in range(6)], CHENE)


# Une patte avant du tamid (Tamid 4:3), l'épaule en haut du repère, le sabot en bas.
def ever(mm, repere):
    chemin = [Vector((0.0, y, z)) for z, y in ((0.0, 0.0), (0.12, 0.0), (0.24, -0.03), (0.34, -0.03), (0.46, -0.02))]
    bout_a_bout(mm, repere, chemin, (0.055, 0.050, 0.030, 0.024, 0.022), CHAIR, 12)


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


class Tissu(NamedTuple):
    obstacles: object
    masse: float = 0.2
    tension: float = 12.0
    compression: float = 4.0
    flexion: float = 0.5
    images: int = 36


TALITH_TISSU = dict(masse=0.25, tension=15.0, compression=8.0, flexion=1.2)


# Le tissu tombe sous la pesanteur, retenu par ses épingles et arrêté par `obstacles` ; sa forme finale est gardée.
def draper(objet, epingles, tissu):
    groupe = objet.vertex_groups.new(name="epingles")
    for i, poids in epingles.items():
        groupe.add([i], poids, "REPLACE")
    modificateur = objet.modifiers.new("tissu", "CLOTH")
    reglage = modificateur.settings
    reglage.quality = 8
    reglage.mass = tissu.masse
    reglage.tension_stiffness = tissu.tension
    reglage.compression_stiffness = reglage.shear_stiffness = tissu.compression
    reglage.bending_stiffness = tissu.flexion
    reglage.air_damping = 2.0
    reglage.vertex_group_mass = groupe.name
    contact = modificateur.collision_settings
    contact.collection = tissu.obstacles
    contact.distance_min = 0.008
    contact.collision_quality = 4
    contact.use_self_collision = False
    modificateur.point_cache.frame_start, modificateur.point_cache.frame_end = 1, tissu.images
    scene = bpy.context.scene
    for image in range(1, tissu.images + 1):
        scene.frame_set(image)
    graphe = bpy.context.evaluated_depsgraph_get()
    drape = bpy.data.meshes.new_from_object(objet.evaluated_get(graphe), preserve_all_data_layers=True, depsgraph=graphe)
    derive = max((a.co - b.co).length for a, b in zip(objet.data.vertices, drape.vertices))
    if derive > 0.5:
        raise RuntimeError(f"{objet.name} : la simulation du tissu a divergé ({derive:.2f} m)")
    objet.modifiers.remove(modificateur)
    objet.vertex_groups.remove(groupe)
    ancien, objet.data = objet.data, drape
    nom = ancien.name
    bpy.data.meshes.remove(ancien)
    drape.name = nom
    scene.frame_set(1)


def _objet(humain, mm, nom, materiau):
    h = humain
    me = bpy.data.meshes.new(nom)
    me.from_pydata([p[:] for p in mm.sommets], [], mm.faces)
    me.update()
    me.materials.append(materiau)
    couleurs = me.color_attributes.new("Color", "BYTE_COLOR", "CORNER")
    valeurs = []
    for poly, c in zip(me.polygons, mm.couleurs):
        valeurs.extend([*c, 1.0] * poly.loop_total)
    couleurs.data.foreach_set("color", valeurs)
    me.uv_layers.new(name="UVMap").data.foreach_set("uv", [x for face in mm.uvs for coin in face for x in coin])
    me.shade_smooth()
    objet = bpy.data.objects.new(nom, me)
    for c in h.rig.users_collection:
        c.objects.link(objet)
    objet.parent = h.rig
    return objet


def materiau_de(mm):
    return metal() if all(c in METAUX for c in mm.couleurs) else bois()


# Tenu sans peau : `Enregistreur.objet` l'anime dans le repère de l'armature.
def porter(humain, mm, nom):
    return _objet(humain, mm, nom, materiau_de(mm))


def lier(humain, mm, nom, materiau, os_fixe=None, tissu=None):
    h = humain
    objet = _objet(h, mm, nom, materiau)
    if tissu is not None:
        draper(objet, mm.epingles, tissu)
    groupes = {}
    for i, (sommet, zone) in enumerate(zip(objet.data.vertices, mm.zones)):
        poids = {os_fixe: 1.0} if os_fixe else poids_de(h, zone, sommet.co)
        for groupe, w in poids.items():
            if groupe not in groupes:
                groupes[groupe] = objet.vertex_groups.new(name=groupe)
            groupes[groupe].add([i], w, "REPLACE")
    modificateur = objet.modifiers.new("Armature", "ARMATURE")
    modificateur.object = h.rig
    return objet


def appliquer_visibilite(humain, visible):
    h = humain
    groupe = h.corps.vertex_groups.get("visible") or h.corps.vertex_groups.new(name="visible")
    groupe.add([int(i) for i in np.nonzero(visible)[0]], 1.0, "REPLACE")
    for m in list(h.corps.modifiers):
        if m.type == "MASK":
            h.corps.modifiers.remove(m)
    masque = h.corps.modifiers.new("visible", "MASK")
    masque.vertex_group = "visible"
    h.corps.modifiers.move(len(h.corps.modifiers) - 1, 0)


# La barbe « sigmund » faisait un masque plein, la bouche ouverte dessus en crocs : la viking est seule en mèches.
BARBE = "rehmanpolanski_beard_viking"
MOUSTACHE = "rehmanpolanski_moustache_viking"
CHEVEUX_COURTS = ("short01", "short04")
BRUN = (0.30, 0.24, 0.20)
GRIS = (1.1, 1.05, 1.0)


def _poils(nom, gris):
    return dict(cheveux=CHEVEUX_COURTS[int(_alea(nom, 5) * 2)], barbe=(BARBE, MOUSTACHE), teinte_poils=GRIS if gris else BRUN,
                sourcils=1 + int(_alea(nom, 6) * 9))


# Robe de moine CC0 (Donitz) sans pèlerine ni cordon : la coupe longue à manches de la kutonet.
KUTONET = Habit("donitz_monk_robe", "Figure_Kutonet", LIN, pieces=(0, 2, 3), longue=True, epaules="haut")
ROBE = Habit("punkduck_medieval_dress", "Figure_Robe", LAINE_BLEUE, longue=True)
COSTUME = Habit("male_elegantsuit01", epaules="manches")


# Les faces de la robe sont larges : coupées au plan d'abord, sinon celles qui l'enjambent dressent des ailerons.
def rogner(humain, objet, z):
    passage = humain.rig.matrix_world.inverted() @ objet.matrix_world
    retour = passage.inverted()
    bm = bmesh.new()
    bm.from_mesh(objet.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=retour @ Vector((0.0, 0.0, z)),
                           plane_no=(passage.to_3x3().transposed() @ HAUT_Z).normalized())
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if all((passage @ v.co).z > z - 1e-5 for v in f.verts)], context="FACES")
    bm.to_mesh(objet.data)
    bm.free()


# Le tissage de la robe, pris autour du point de `source` le plus proche de `ancre` et à sa densité, replié en miroir
# tous les `demi` mètres : `plan(p)` rend la place de chaque sommet dans le tissu, en mètres, et `tour` la longueur
# d'un tour, pour qu'une face à cheval sur la couture reste d'un seul tenant.
def uv_en_piece(humain, objet, source, ancre, plan, tour, demi=0.10):
    me = source.data
    passage = humain.rig.matrix_world.inverted() @ source.matrix_world
    uvs = me.uv_layers.active.data
    aire_3d = sum(p.area for p in me.polygons)
    aire_uv = sum(abs(_aire_plane([uvs[b].uv for b in p.loop_indices])) for p in me.polygons)
    par_metre = math.sqrt(aire_uv / aire_3d)
    proche = min(me.loops, key=lambda b: (passage @ me.vertices[b.vertex_index].co - ancre).length)
    centre = uvs[proche.index].uv.copy()

    def replier(x):
        return abs((x + demi) % (4.0 * demi) - 2.0 * demi) - demi

    retour = humain.rig.matrix_world.inverted() @ objet.matrix_world
    couche = objet.data.uv_layers.active.data
    for face in objet.data.polygons:
        places = [plan(retour @ objet.data.vertices[v].co) for v in face.vertices]
        u0 = places[0][0]
        for boucle, (u, v) in zip(face.loop_indices, places):
            u -= tour * round((u - u0) / tour)
            couche[boucle].uv = centre + Vector((replier(u), replier(v))) * par_metre


def _aire_plane(coins):
    return 0.5 * sum(a.x * b.y - b.x * a.y for a, b in zip(coins, coins[1:] + coins[:1]))


OURLET = (0.0015, 0.003, 0.005)


# La robe sans pèlerine s'arrêtait net à hauteur d'épaule, les manches dressées en ailerons : rognée dessous,
# elle reçoit un empiècement de son propre lin, tiré en rayons vers la base du cou, par-dessus robe, manches et épaules.
def empiecement(humain, robe, ecart=0.008, rangs=12, n=56):
    h = humain
    z_bas, z_haut = h.z_epaule - 0.055, h.z_cou - 0.05
    entiere = robe.copy()
    entiere.data = robe.data.copy()
    rogner(h, robe, z_bas + 0.01)
    surface = surface_de(h, [robe], h.visible & ~h.tete_ & ~h.main)
    cou = tranche(h, h.cou & h.visible, h.z_cou, 0.02)
    cy = 0.5 * (cou[:, 1].min() + cou[:, 1].max())
    portee = 0.6
    pivots, directions, rayons = [], [], np.zeros((rangs, n))
    for k in range(rangs):
        u = k / (rangs - 1)
        phi = math.radians(62.0) * u
        pivots.append(Vector((0.0, cy, z_bas + (z_haut - z_bas) * u)))
        rang = []
        for j, th in enumerate(_angles(n)):
            dx, dy = _vers(th)
            d = Vector((dx * math.cos(phi), dy * math.cos(phi), math.sin(phi)))
            touche = surface.ray_cast(pivots[k] + d * portee, -d)[0]
            rayons[k, j] = portee - (touche - (pivots[k] + d * portee)).length if touche is not None else 0.08
            rang.append(d)
        directions.append(rang)
    # Le lin passe d'un relief à l'autre sans entrer dans les creux, entre bras et poitrine ; l'encolure, elle, colle au cou.
    ponts = np.max([np.roll(rayons, k, axis=1) for k in (-2, -1, 0, 1, 2)], axis=0)
    colle = np.array([G.lisse((rangs - 1 - k) / 3) for k in range(rangs)])[:, None]
    rayons = np.array([_lisser_cercle(r, 4 + 10 * (k >= rangs - 3)) for k, r in enumerate(ponts * colle + rayons * (1.0 - colle))])
    rayons[1:-1] = 0.25 * rayons[:-2] + 0.5 * rayons[1:-1] + 0.25 * rayons[2:]
    anneaux = [[pivots[k] + d * (rayons[k, j] + ecart) for j, d in enumerate(directions[k])] for k in range(rangs)]
    # L'ourlet est plaqué sur la robe entière : pas de marche, et le bord rogné reste dessous.
    lin_de_la_robe = surface_de(h, [entiere])
    for k, dehors in enumerate(OURLET):
        anneaux[k] = [lieu + normale * dehors for lieu, normale, _, _ in map(lin_de_la_robe.find_nearest, anneaux[k])]
    mm = Maillage()
    mm.nappe(anneaux, LIN, "voile")
    objet = lier(h, mm, f"{h.nom}_empiecement", robe.data.materials[0])
    # Un tour du cou vaut trois périodes du tissu replié : la couture du dos tombe sans raccord.
    tour = 1.2

    def autour_du_cou(p):
        dx, dy = p.x, p.y - cy
        return math.atan2(dx, -dy) / TOUR * tour, math.hypot(dx, dy) + z_haut - p.z

    uv_en_piece(h, objet, entiere, Vector((0.0, cy - 0.25, h.z_epaule - 0.12)), autour_du_cou, tour)
    bpy.data.meshes.remove(entiere.data)


class Habits(NamedTuple):
    avnet: Teintes
    coiffe: object


BIGDEI_KEHOUNA = Habits(AVNET_BRODE, migbaat)
BIGDEI_LAVAN = Habits(AVNET_DE_LIN, mitznefet)


def cohen(nom, gabarit=Gabarit(), gris=False):
    return vetir_de_lin(Humain(nom, gabarit, **_poils(nom, gris)), BIGDEI_KEHOUNA)


# Les quatre habits blancs du Cohen Gadol à Kippour (Vayikra 16:4 ; Rambam Klei HaMikdash 8:3).
def cohen_gadol(nom, gabarit=Gabarit()):
    return vetir_de_lin(Humain(nom, gabarit, **_poils(nom, True)), BIGDEI_LAVAN)


# Lin (Rambam Klei HaMikdash 8:1), pieds nus (Zeva'him 24a).
def vetir_de_lin(h, habits):
    nom = h.nom
    robe = h.vetir_mpfb(KUTONET)
    h.detendre()
    empiecement(h, robe)
    ceinture = Ceinture(h, h.squelette.tete("lowerarm_l").z)
    ceinture.serrer(h, robe)
    ceint = Maillage()
    avnet(ceint, ceinture, surface_de(h, [robe]), habits.avnet)
    lier(h, ceint, f"{nom}_avnet", lin())
    coiffure = Maillage()
    habits.coiffe(coiffure, h)
    lier(h, coiffure, f"{nom}_{habits.coiffe.__name__}", lin(), "head")
    appliquer_visibilite(h, h.visible & ~h.efface)
    return h


# « מְלֻבָּשִׁים בּוּץ » (Divrei HaYamim II 5:12).
def levi(nom, gabarit=Gabarit(), gris=False, barbe=True):
    poils = _poils(nom, gris)
    if not barbe:
        poils["barbe"] = None
    h = Humain(nom, gabarit, **poils)
    robe = h.vetir_mpfb(KUTONET)
    h.detendre()
    empiecement(h, robe)
    coiffure = Maillage()
    calotte(coiffure, h, LIN, rayon=0.066)
    lier(h, coiffure, f"{nom}_kippa", lin(), "head")
    appliquer_visibilite(h, h.visible & ~h.efface)
    return h


# Pieds nus : « לֹא יִכָּנֵס לְהַר הַבַּיִת בְּמַקְלוֹ וּבְמִנְעָלוֹ » (Berakhot 9:5).
def fidele(nom, tenue, gabarit=Gabarit(), gris=False, barbe=True, tete="kippa"):
    poils = _poils(nom, gris)
    if not barbe:
        poils["barbe"] = None
    h = Humain(nom, gabarit, **poils)
    h.vetir_mpfb({"costume": COSTUME, "robe": ROBE}[tenue])
    h.detendre()
    if tete == "chapeau":
        coiffure = Maillage()
        chapeau(coiffure, h)
        lier(h, coiffure, f"{nom}_chapeau", feutre(), "head")
    if tete == "talith":
        draper_talith(h)
    if tete in ("kippa", "talith"):
        coiffure = Maillage()
        calotte(coiffure, h, DRAP_NOIR)
        lier(h, coiffure, f"{nom}_kippa", velours(), "head")
    appliquer_visibilite(h, h.visible & ~h.efface)
    h.ranger()
    return h


def draper_talith(humain):
    h = humain
    drap = Maillage()
    coins = talith(drap, h)
    haut = h.obstacle("haut", h.visible, h.vetements_mpfb)
    objet = lier(h, drap, f"{h.nom}_talith", laine(), tissu=Tissu(haut, **TALITH_TISSU))
    franges = Maillage()
    tzitzit(franges, [objet.data.vertices[i].co.copy() for i in coins])
    lier(h, franges, f"{h.nom}_tzitzit", laine())


# `repere` : place au repos de l'objet, en repère d'armature.
def tenir(h, nom, construire, os_, repere):
    mm = Maillage()
    construire(mm, repere)
    return lier(h, mm, f"{h.nom}_{nom}", materiau_de(mm), os_)


def repere_vers(origine, z, x):
    z = z.normalized()
    x = (x - z * x.dot(z)).normalized()
    m = Matrix((x, z.cross(x), z)).transposed().to_4x4()
    m.translation = origine
    return m


IMAGES = 15
BAS = Vector((0.0, 0.0, -1.0))


# `z_haut` : au-dessus du plus haut sol du trajet, sous tout toit.
def _rayon_sol(x, y, z_haut):
    scene = bpy.context.scene
    touche, lieu, *_ = scene.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((x, y, z_haut + 1.5)), BAS,
                                      distance=8.0)
    return lieu.z if touche else z_haut


# Relevé avant de poser les figures : un rayon tiré ensuite toucherait les corps.
class Terrain:
    def __init__(self, x0, x1, y0, y1, z_haut, pas=0.1):
        self.x0, self.y0, self.pas = x0, y0, pas
        nx, ny = int((x1 - x0) / pas) + 2, int((y1 - y0) / pas) + 2
        self.z = np.array([[_rayon_sol(x0 + i * pas, y0 + j * pas, z_haut) for j in range(ny)] for i in range(nx)])

    def __call__(self, x, y):
        u = min(max((x - self.x0) / self.pas, 0.0), self.z.shape[0] - 1.001)
        v = min(max((y - self.y0) / self.pas, 0.0), self.z.shape[1] - 1.001)
        i, j = int(u), int(v)
        fu, fv = u - i, v - j
        z = self.z
        return ((z[i, j] * (1 - fu) + z[i + 1, j] * fu) * (1 - fv) + (z[i, j + 1] * (1 - fu) + z[i + 1, j + 1] * fu) * fv)


# En amot : aller-retour de `a` à `b`, demi-tours de `rayon` aux deux bouts ; l'aller se fait à gauche de `a` → `b`, ou à droite avec `sens=-1`.
class Stade:
    def __init__(self, a, b, rayon, pas=0.04, sens=1):
        a, b, r = Vector(a) * AMA, Vector(b) * AMA, rayon * AMA
        d = (b - a).normalized()
        n = Vector((-d.y, d.x)) * sens
        droit = (b - a).length
        k, m = max(2, int(droit / pas)), max(8, int(math.pi * r / pas))
        points = [a + n * r + d * (droit * i / k) for i in range(k)]
        points += [b + n * (r * math.cos(math.pi * i / m)) + d * (r * math.sin(math.pi * i / m)) for i in range(m)]
        points += [b - n * r - d * (droit * i / k) for i in range(k)]
        points += [a - n * (r * math.cos(math.pi * i / m)) - d * (r * math.sin(math.pi * i / m)) for i in range(m)]
        self.points = points
        self.cumul = [0.0]
        for p, q in zip(points, points[1:] + points[:1]):
            self.cumul.append(self.cumul[-1] + (q - p).length)
        self.longueur = self.cumul[-1]

    def en(self, s):
        s %= self.longueur
        i = max(0, np.searchsorted(self.cumul, s, side="right") - 1)
        p, q = self.points[i], self.points[(i + 1) % len(self.points)]
        t = (s - self.cumul[i]) / max(self.cumul[i + 1] - self.cumul[i], 1e-9)
        return p.lerp(q, t)

    def direction(self, s):
        return (self.en(s + 0.25) - self.en(s - 0.25)).normalized()

    def bornes(self, marge):
        xs, ys = [p.x for p in self.points], [p.y for p in self.points]
        return min(xs) - marge, max(xs) + marge, min(ys) - marge, max(ys) + marge


def placement(x, y, z, direction, sol_local):
    return Matrix.Translation((x, y, z - sol_local)) @ Matrix.Rotation(math.atan2(direction.x, -direction.y), 4, "Z")


def cap_vers(cap):
    return Vector((math.cos(math.radians(cap)), math.sin(math.radians(cap))))


BATTEMENT = 60.0 / 72.0
MESURES = 16


def devant_poitrine(h, avance, sous_epaule, ecart=0.0):
    return Vector((ecart, -avance, h.z_epaule - sous_epaule))


# « מַנִּיחַ יָדוֹ הַיְמָנִית עַל גַּבֵּי רַגְלוֹ הַיְמָנִית … וְשׁוֹחֶה וּמְקַדֵּשׁ » (Rambam Bi'at HaMikdash 5:16).
def lavage(h, a, horloge, t):
    u = t / horloge.duree
    w = G.lisse((u - 0.22) / 0.14) * (1.0 - G.lisse((u - 0.68) / 0.14))
    frotte = 0.015 * horloge.onde(t, 0.9) * w

    def main(cote):
        pendante = a.au("spine_03", a.poignet[cote])
        pied = a.cheville[cote] + G.DEVANT * (0.07 + frotte) + G.HAUT * 0.055
        return lambda poses: pendante(poses).lerp(pied, w)

    return G.composer(G.debout(a, horloge, t, regard=0.04 * (1 - w)),
                      G.bassin(Vector((0.0, 0.17 * w, -0.25 * w)), tangage=0.45 * w),
                      G.buste(flexion=0.78 * w), G.tete(flexion=-0.22 * w),
                      G.bras(a, "l", main("l")), G.bras(a, "r", main("r")),
                      G.doigts(a, "l", 0.35 - 0.25 * w), G.doigts(a, "r", 0.35 - 0.25 * w))


def repere_mizrak(h):
    return repere_vers(devant_poitrine(h, 0.30, 0.34), G.HAUT, G.GAUCHE)


def zerika(h, a, horloge, t):
    coupe = a.repere("spine_03", repere_mizrak(h))
    incline = 0.5 - 0.5 * horloge.onde(t, 8.0, 0.25)
    return G.composer(G.debout(a, horloge, t, 0.2, regard=0.05), G.buste(flexion=0.18 * incline),
                      G.tete(flexion=0.20 * incline),
                      G.bras(a, "l", lambda poses: coupe(poses) @ Vector((0.11, 0.0, 0.03))),
                      G.bras(a, "r", lambda poses: coupe(poses) @ Vector((-0.11, 0.0, 0.03))),
                      G.paume(a, "l", lambda poses: G.HAUT - G.GAUCHE), G.paume(a, "r", lambda poses: G.HAUT + G.GAUCHE),
                      G.doigts(a, "l", 0.25), G.doigts(a, "r", 0.25))


# Calé contre le ventre, la tête penchée en avant : tenu à bout de bras, il tendait les bras comme deux perches.
def repere_kinor(h, echelle):
    base = Vector((0.05, -0.17 - 0.04 * (echelle - 1.0), h.z_epaule - 0.46 * echelle))
    return repere_vers(base, Vector((0.12, -0.42, 1.0)), Vector((1.0, 0.0, -0.1)))


# La gauche tient le montant par-derrière, la droite pince les cordes devant, à mi-hauteur.
def jouer_kinor(h, a, horloge, t, echelle, retard):
    lyre = a.repere("spine_03", repere_kinor(h, echelle))
    b = (t / BATTEMENT - retard) % 1.0
    geste = G.lisse(b / 0.30) if b < 0.30 else 1.0 - G.lisse((b - 0.30) / 0.70)
    e = echelle
    return G.composer(G.debout(a, horloge, t, retard, regard=0.03), G.balancement(t, BATTEMENT, retard=retard),
                      G.tete(flexion=0.12),
                      G.bras(a, "l", lambda poses: lyre(poses) @ Vector((0.15 * e, 0.035, 0.30 * e))),
                      G.bras(a, "r", lambda poses: lyre(poses) @ Vector(((-0.04 + 0.10 * geste) * e, -0.07, 0.22 * e))),
                      G.paume(a, "l", lambda poses: a.dans("spine_03", poses, G.DEVANT - G.GAUCHE * 0.3)),
                      G.paume(a, "r", lambda poses: a.dans("spine_03", poses, G.HAUT * 0.3 + G.GAUCHE)),
                      G.doigts(a, "l", 0.45, 0.3), G.doigts(a, "r", 0.35 + 0.35 * geste, 0.4))


def repere_cymbale(h, cote):
    a = G.Acteur(h.squelette, h.sol)
    centre = a.poignet[cote] + a.jointure[cote] * 0.085 + a.paume[cote] * 0.03
    return repere_vers(centre, a.jointure[cote].cross(-a.paume[cote]), a.jointure[cote])


# « וְהִקִּישׁ בֶּן אַרְזָא בַּצֶּלְצָל, וְדִבְּרוּ הַלְוִיִּם בַּשִּׁיר » (Tamid 7:3).
def frapper(h, a, horloge, t, retard):
    q = ((t / BATTEMENT - retard) % 4.0) / 4.0
    ecart = 0.09 + 0.22 * (G.lisse(q / 0.25) if q < 0.8 else 1.0 - G.lisse((q - 0.8) / 0.2))
    centre = a.au("spine_03", devant_poitrine(h, 0.30, 0.10))
    return G.composer(G.debout(a, horloge, t, retard), G.balancement(t, BATTEMENT, 0.6, retard),
                      G.bras(a, "l", lambda poses: centre(poses) + G.GAUCHE * (ecart / 2)),
                      G.bras(a, "r", lambda poses: centre(poses) - G.GAUCHE * (ecart / 2)),
                      G.paume(a, "l", -G.GAUCHE), G.paume(a, "r", G.GAUCHE),
                      G.doigts(a, "l", 0.8, 0.5), G.doigts(a, "r", 0.8, 0.5))


def priere(h, a, horloge, t):
    va = 0.5 + 0.5 * horloge.onde(t, 1.3)
    mains = a.au("spine_03", devant_poitrine(h, 0.24, 0.30))
    return G.composer(G.pied(a, "l"), G.pied(a, "r"), G.respiration(horloge, t),
                      G.buste(flexion=0.10 + 0.16 * va), G.tete(flexion=0.12 + 0.10 * va),
                      G.bras(a, "l", lambda poses: mains(poses) + G.GAUCHE * 0.035),
                      G.bras(a, "r", lambda poses: mains(poses) - G.GAUCHE * 0.035),
                      G.doigts(a, "l", 0.55), G.doigts(a, "r", 0.55))


# La main droite posée sur le dos de la gauche, les deux paumes vers le ventre.
def mains_jointes(h, a, sous_hanche=0.02):
    mains = a.au("spine_03", Vector((0.0, -0.15, h.z_hanche - sous_hanche)))
    vers_le_ventre = lambda poses: a.dans("spine_03", poses, -G.DEVANT)
    return G.composer(G.bras(a, "l", lambda poses: mains(poses) + G.GAUCHE * 0.035),
                      G.bras(a, "r", lambda poses: mains(poses) - G.GAUCHE * 0.02 + G.DEVANT * 0.03 + G.HAUT * 0.02),
                      G.paume(a, "l", vers_le_ventre), G.paume(a, "r", vers_le_ventre),
                      G.doigts(a, "l", 0.30, 0.15), G.doigts(a, "r", 0.40, 0.2))


def ecouter(h, a, horloge, t):
    return G.composer(G.debout(a, horloge, t, 0.4, regard=0.04), G.tete(flexion=0.06 + 0.04 * horloge.onde(t, 2.4)),
                      mains_jointes(h, a))


# Un des vingt et un postes des Léviim, aux portes de l'Azara (Middot 1:1) : debout, les bras le long du corps, le regard qui va.
def garder(h, a, horloge, t):
    return G.composer(G.debout(a, horloge, t, 0.8, regard=0.45), G.doigts(a, "l", 0.35, 0.15), G.doigts(a, "r", 0.35, 0.15))


# « וְרָאשֵׁיהֶן מִבֵּין רַגְלֵי הַלְוִיִּם » (Arakhin 2:6) : les enfants chantent à terre, sans instrument.
def chanter(h, a, horloge, t, retard):
    return G.composer(G.debout(a, horloge, t, retard, regard=0.03), G.balancement(t, BATTEMENT, 0.8, retard),
                      G.tete(flexion=-0.14), mains_jointes(h, a, -0.04))


def repere_gizra(h):
    return repere_vers(devant_poitrine(h, 0.30, 0.32), G.GAUCHE, G.HAUT)


# « הֵחֵלּוּ מַעֲלִין בְּגִזְרִין לְסַדֵּר אֵשׁ הַמַּעֲרָכָה » (Tamid 2:3) : la bûche descend vers la ma'arakha, puis remonte.
def charger(h, a, horloge, t):
    u = t / horloge.duree
    w = G.lisse((u - 0.20) / 0.18) * (1.0 - G.lisse((u - 0.62) / 0.18))
    corps = G.composer(G.debout(a, horloge, t, 0.3, regard=0.03),
                       G.bassin(Vector((0.0, 0.10 * w, -0.16 * w)), tangage=0.30 * w),
                       G.buste(flexion=0.62 * w), G.tete(flexion=-0.10 * w))
    buche = a.repere("spine_03", repere_gizra(h))(a.sq.resoudre(corps)[0])
    axe = buche.col[2].to_3d()
    return saisir(a, corps, RAYON_GIZRA, {"l": buche @ Vector((0.0, 0.0, 0.22)), "r": buche @ Vector((0.0, 0.0, -0.22))},
                  {"l": -axe, "r": axe}, poles={"l": None, "r": None})


PENTE_KEVESH = 9.0 / 30.0


def repere_ever(h):
    return repere_vers(Vector((0.21, -0.20, h.z_hanche + 0.06)), 0.25 * G.DEVANT - G.HAUT, G.GAUCHE)


# « הָלְכוּ וּנְתָנוּם מֵחֲצִי הַכֶּבֶשׁ וּלְמַטָּה בְּמַעֲרָבוֹ, וּמְלָחוּם » (Tamid 4:3) : la droite va au sel, puis sale le membre que tient la gauche.
def saler(h, a, horloge, t):
    u = t / horloge.duree
    au_sel = G.lisse((u - 0.04) / 0.16) * (1.0 - G.lisse((u - 0.36) / 0.12))
    sur_ever = G.lisse((u - 0.44) / 0.10) * (1.0 - G.lisse((u - 0.86) / 0.10))
    secousse = 0.02 * math.sin(TOUR * 5.0 * u) * sur_ever
    membre = a.repere("spine_03", repere_ever(h))
    sel = a.au("spine_03", Vector((-0.12, -0.50, h.z_hanche - 0.55)))
    dessus = a.au("spine_03", Vector((0.16, -0.30, h.z_hanche + 0.06)))
    pendante = a.au("spine_03", a.poignet["r"])

    def droite(poses):
        return pendante(poses).lerp(sel(poses), au_sel).lerp(dessus(poses) + G.HAUT * secousse, sur_ever)

    penche = 0.55 * au_sel + 0.20 * sur_ever
    return G.composer(G.pied(a, "l", sol=-PENTE_KEVESH * 0.09), G.pied(a, "r", sol=PENTE_KEVESH * 0.09),
                      G.respiration(horloge, t),
                      G.bassin(Vector((0.0, 0.12 * penche, -0.18 * penche)), tangage=0.35 * penche),
                      G.buste(flexion=0.55 * penche), G.tete(flexion=0.25 * penche - 0.05),
                      G.bras(a, "l", lambda poses: membre(poses) @ Vector((0.0, 0.0, -0.03))), G.bras(a, "r", droite),
                      G.paume(a, "l", G.DEVANT - G.GAUCHE), G.paume(a, "r", G.DEVANT * (1.0 - sur_ever) - G.HAUT * sur_ever),
                      G.doigts(a, "l", 0.8, 0.5), G.doigts(a, "r", 0.35 + 0.3 * au_sel))


# « אֶבֶן הָיְתָה לִפְנֵי הַמְּנוֹרָה וּבָהּ שָׁלֹשׁ מַעֲלוֹת שֶׁעָלֶיהָ הַכֹּהֵן עוֹמֵד וּמֵטִיב אֶת הַנֵּרוֹת » (Tamid 3:9) :
# debout sur la pierre, il se penche sur les lampes ; le kouz attend sur la deuxième marche.
def hatava(h, a, horloge, t):
    va = 0.5 + 0.5 * horloge.onde(t, 2.5)
    lampe = a.au("spine_03", devant_poitrine(h, 0.56 - 0.05 * va, 0.38 - 0.05 * va, -0.10))
    pendante = a.au("spine_03", a.poignet["l"])
    return G.composer(G.debout(a, horloge, t, 0.6, regard=0.02), G.buste(flexion=0.16, torsion=0.08), G.tete(flexion=0.12),
                      G.bras(a, "l", pendante), G.bras(a, "r", lampe),
                      G.paume(a, "r", G.DEVANT - G.HAUT), G.doigts(a, "l", 0.3), G.doigts(a, "r", 0.3))


# Tenu sans peau : `matrice(h, a, horloge, t, poses)` le place dans le repère de l'armature, image par image.
class Accessoire(NamedTuple):
    nom: str
    construire: object
    matrice: object


# Les lèvres, sous le bout du nez : le point le plus avancé du profil, entre les yeux et le menton.
def bouche(h):
    profil = h.co[h.visible & h.tete_ & (np.abs(h.co[:, 0]) < 0.01)]
    profil = profil[(profil[:, 2] > h.z_tete - 0.24) & (profil[:, 2] < h.z_tete - 0.10)]
    z = float(profil[np.argmin(profil[:, 1]), 2]) - 0.045
    levres = profil[np.abs(profil[:, 2] - z) < 0.006]
    return Vector((0.0, float(levres[:, 1].min()) - 0.008, z))


def entre(m0, m1, w):
    m = m0.to_quaternion().slerp(m1.to_quaternion(), w).to_matrix().to_4x4()
    m.translation = m0.translation.lerp(m1.translation, w)
    return m


TEKIA = 12.0
# Tekia, terua, tekia (Soucca 5:4), en secondes dans la boucle.
SONNERIES = ((1.8, 3.6), (3.9, 5.4), (5.7, 7.5))


def repere_trompette(h, t):
    levee = G.lisse((t - 0.5) / 1.0) * (1.0 - G.lisse((t - 8.0) / 1.0))
    baissee = repere_vers(devant_poitrine(h, 0.10, 0.30), Vector((0.0, -1.0, -0.8)), G.GAUCHE)
    return entre(baissee, repere_vers(h.bouche, Vector((0.0, -1.0, 0.45)), G.GAUCHE), levee)


# m de l'embouchure à chaque poing : plus près, l'avant-bras gauche se dressait devant le visage.
PRISES = {"l": 0.22, "r": 0.36}
RAYON_TUBE = 0.0065


def trompette_tenue(h, a, horloge, t, poses):
    return a.repere("spine_03", repere_trompette(h, t))(poses)


# Le coude part en dehors et vers le bas : le pôle par défaut, en arrière, pliait les bras levés à rebours.
def coude_ouvert(a, cote):
    s = 1.0 if cote == "l" else -1.0
    return lambda poses: a.dans("spine_03", poses, Vector((s, 0.2, -0.6)))


# `corps` posé, chaque main `cote` ferme sa poigne sur un manche de `rayon` au point `voulus[cote]`, dans l'axe
# `directions[cote]`, le coude porté vers `poles[cote]` autant que le poignet le permet. Le bras vise le poignet,
# la main tient plus loin : trois passes y ramènent le manche.
def saisir(a, corps, rayon, voulus, directions, poles=None):
    poles = poles or {c: coude_ouvert(a, c) for c in voulus}

    def tenir_a(cibles):
        regles = [corps]
        for c in voulus:
            coude = G.coude_pour_manche(a, c, rayon, cibles[c], directions[c], poles[c])
            regles += [G.bras(a, c, cibles[c], coude), G.aligner_prise(a, c, rayon, directions[c]),
                       G.poigne(a, c, rayon)]
        return G.composer(*regles)

    cibles = dict(voulus)
    for _ in range(3):
        poses = a.sq.resoudre(tenir_a(cibles))[0]
        cibles = {c: cibles[c] + voulus[c] - G.manche(a, c, rayon, poses)[0] for c in voulus}
    return tenir_a(cibles)


# « וְעָמְדוּ שְׁנֵי כֹהֲנִים בַּשַּׁעַר הָעֶלְיוֹן … וּשְׁתֵּי חֲצוֹצְרוֹת בִּידֵיהֶן » (Soucca 5:4) : la trompette monte aux lèvres, sonne, redescend.
# Les deux mains par-dessus le tube, le pouce vers l'embouchure.
def tekia(h, a, horloge, t):
    souffle = max(G.lisse((t - debut) / 0.3) * (1.0 - G.lisse((t - fin) / 0.3)) for debut, fin in SONNERIES)
    corps = G.composer(G.debout(a, horloge, t, 0.5, regard=0.0), G.buste(flexion=-0.05 * souffle))
    visee = a.repere("spine_03", repere_trompette(h, t))(a.sq.resoudre(corps)[0])
    vers_l_embouchure = -visee.col[2].to_3d()
    return saisir(a, corps, RAYON_TUBE, {c: visee @ Vector((0.0, 0.0, PRISES[c])) for c in "lr"},
                  {c: vers_l_embouchure for c in "lr"})


# Le manche passe dans le poing fermé, la tête du côté du pouce.
def dans_la_poigne(cote, rayon):
    def matrice(h, a, horloge, t, poses):
        centre, axe = G.manche(a, cote, rayon, poses)
        return repere_vers(centre, axe, a.dans(f"hand_{cote}", poses, a.jointure[cote]))
    return matrice


def pas_de_marche(h, a, horloge, t, phase, foulee, sol):
    return G.composer(G.marche(a, phase, foulee, sol), G.respiration(horloge, t),
                      G.tete(lacet=0.08 * horloge.onde(t, 6.0)))


# « חֲסִידִים וְאַנְשֵׁי מַעֲשֶׂה הָיוּ מְרַקְּדִים לִפְנֵיהֶם בַּאֲבוּקוֹת שֶׁל אוֹר שֶׁבִּידֵיהֶן » (Soucca 5:4) : la ronde est une
# hora, CHOIX : face au centre, pas de côté, pas croisé derrière, pas de côté, sautillé jambe lancée, deux fois,
# puis quatre pas vers celui qui jongle, torches levées, et quatre pas en arrière ; la même chose vers la droite.
BATTEMENT_HORA = 60.0 / 126.0
PAS_HORA = 0.22
ECART_HORA = 0.10


class Appui(NamedTuple):
    envol: float
    pose: float
    x: float
    y: float
    coup: tuple = None


# En temps (battements) et en mètres dans la ronde : x vers la gauche du danseur, y vers l'extérieur.
class Choregraphie:
    def __init__(self):
        self.appuis, self.suspens = {"l": [], "r": []}, {}
        self.sauts, self.elans, self.sens = [], [], []
        x = 0.0
        for k in range(3):
            x = self.hora(6.0 * k, x, 1.0)
        self.vers_le_centre(18.0, x, "l")
        for k in range(3):
            x = self.hora(26.0 + 6.0 * k, x, -1.0)
        self.vers_le_centre(44.0, x, "r")
        self.temps = 52.0

    def poser(self, cote, pose, x, y, envol=None, coup=None):
        if cote in self.suspens:
            envol, coup = self.suspens.pop(cote)
        self.appuis[cote].append(Appui(pose - 0.8 if envol is None else envol, pose, x, y, coup))

    def hora(self, b0, x0, sens):
        w, a = ECART_HORA, PAS_HORA
        mene, suit = ("l", "r") if sens > 0 else ("r", "l")

        def X(v):
            return x0 + sens * v
        self.poser(mene, b0 + 0.8, X(w + a), 0.0, envol=b0)
        self.poser(suit, b0 + 1.8, X(w + a - 0.08), 0.09, envol=b0 + 1.0)
        self.poser(mene, b0 + 2.8, X(w + 2 * a), 0.0, envol=b0 + 2.0)
        self.poser(suit, b0 + 4.6, X(2 * a - w), 0.0, envol=b0 + 3.0, coup=(X(w + 2 * a - 0.03), -0.17, 0.16))
        self.suspens[mene] = (b0 + 5.0, (X(2 * a - w + 0.03), -0.17, 0.16))
        self.sauts += [(b0 + 3.5, mene), (b0 + 5.5, suit)]
        self.sens.append((b0, b0 + 6.0, sens))
        return X(2 * a)

    def vers_le_centre(self, b0, x0, mene):
        suit = "r" if mene == "l" else "l"
        pieds = {"l": x0 + ECART_HORA, "r": x0 - ECART_HORA}
        for k, (cote, y) in enumerate(zip((mene, suit) * 4, (-0.22, -0.44, -0.66, -0.66, -0.44, -0.22, 0.0, 0.0))):
            self.poser(cote, b0 + k + 0.8, pieds[cote], y, envol=b0 + k)
        self.elans.append((b0, b0 + 8.0))

    # (x, y, hauteur, envol) du pied au temps `b` ; envol = (part du pas, jambe lancée) en l'air, None posé.
    def pied(self, cote, b):
        x, y = (ECART_HORA if cote == "l" else -ECART_HORA), 0.0
        for ap in self.appuis[cote]:
            if b < ap.envol:
                break
            if b < ap.pose:
                u = (b - ap.envol) / (ap.pose - ap.envol)
                if ap.coup is None:
                    v = G.lisse(u)
                    return x + (ap.x - x) * v, y + (ap.y - y) * v, 0.07 * math.sin(math.pi * u), (u, False)
                cx, cy, hauteur = ap.coup
                if u < 0.5:
                    v = G.lisse(u / 0.5)
                    px, py = x + (cx - x) * v, y + (cy - y) * v
                else:
                    v = G.lisse((u - 0.5) / 0.5)
                    px, py = cx + (ap.x - cx) * v, cy + (ap.y - cy) * v
                return px, py, hauteur * math.sin(math.pi * u), (u, True)
            x, y = ap.x, ap.y
        return x, y, 0.0, None

    def saut(self, b, cote=None):
        return max([math.sin(math.pi * (b - t + 0.5)) for t, c in self.sauts
                    if abs(b - t) < 0.5 and cote in (None, c)] or [0.0])

    def lever(self, b):
        return max([G.lisse((b - d) / 3.5) * (1.0 - G.lisse((b - f + 4.0) / 3.5)) for d, f in self.elans] or [0.0])

    def cote_de_marche(self, b):
        return next((s for d, f, s in self.sens if d <= b < f), 0.0)


CHOREGRAPHIE = Choregraphie()


# En amot : le danseur tient sa place `depart` (angle) sur le cercle de `rayon` autour de `centre`, face au centre.
class Hora:
    def __init__(self, centre, rayon, depart, torche="r", main_libre="ouverte"):
        self.centre, self.rayon, self.depart = Vector(centre) * AMA, rayon * AMA, depart
        self.torche, self.main_libre = torche, main_libre
        self.pas = CHOREGRAPHIE
        self.duree = self.pas.temps * BATTEMENT_HORA

    def monde(self, x, y):
        angle = self.depart - x / self.rayon
        return self.centre + Vector((math.cos(angle), math.sin(angle))) * (self.rayon + y)

    def bornes(self, marge):
        c, r = self.centre, self.rayon + 1.0 + marge
        return c.x - r, c.x + r, c.y - r, c.y + r


RAYON_MANCHE = 0.017


def danse(h, a, hora, b, pieds):
    pas = hora.pas
    lever = pas.lever(b)
    appui = 0.5 + 0.5 * math.cos(TOUR * (b % 1.0 - 0.85))
    saut = pas.saut(b)
    regles = []
    for cote, (decalage, envol) in pieds.items():
        if envol is None:
            tangage, pivot = 0.35 * pas.saut(b, cote), "balle"
        elif envol[1]:
            tangage, pivot = 0.25 * math.sin(math.pi * envol[0]), "talon"
        else:
            tangage, pivot = 0.35 * math.sin(math.pi * envol[0]), "balle"
        regles.append(G.pied(a, cote, decalage, tangage, pivot))
    marche = pas.cote_de_marche(b)
    corps = G.composer(*regles, G.bassin(Vector((0.0, 0.0, -0.035 - 0.035 * appui + 0.045 * saut)),
                                         roulis=0.03 * marche * appui),
                       G.buste(flexion=0.08 + 0.08 * lever, inclinaison=-0.05 * marche),
                       G.tete(flexion=-0.12 - 0.10 * lever + 0.04 * appui, inclinaison=0.04 * marche))
    poses = a.sq.resoudre(corps)[0]
    t = hora.torche
    s = 1.0 if t == "l" else -1.0
    # La torche, coude plié à hauteur de tête, se soulève à chaque temps un peu après le rebond du corps, traîne
    # à l'opposé du pas de côté, et monte bras tendu vers le jongleur quand la ronde avance.
    elan = 0.5 - 0.5 * math.cos(TOUR * (b - 0.2))
    traine = -marche * (1.0 - lever)
    torche = a.au("spine_03", a.epaule[t] + G.HAUT * (0.13 + 0.05 * elan + 0.22 * lever)
                  + G.GAUCHE * (s * 0.10 + 0.03 * traine) + G.DEVANT * (0.20 + 0.20 * lever))
    droite = a.dans("spine_03", poses, G.HAUT + G.GAUCHE * (s * 0.12 * (1.0 - lever) + 0.08 * traine)
                    + G.DEVANT * (0.05 + 0.12 * lever))
    tenue = saisir(a, corps, RAYON_MANCHE, {t: torche(poses)}, {t: droite})
    libre = "r" if t == "l" else "l"
    s = -s
    main = a.au("spine_03", a.epaule[libre] + G.HAUT * (0.05 + 0.18 * lever + 0.07 * (1.0 - appui))
                + G.GAUCHE * (s * (0.22 - 0.10 * lever)) + G.DEVANT * (0.22 + 0.18 * lever))
    ouverte = hora.main_libre == "ouverte"
    return G.composer(tenue, G.bras(a, libre, main, coude_ouvert(a, libre)),
                      G.paume(a, libre, lambda p: a.dans("spine_03", p, G.DEVANT - G.GAUCHE * (0.5 * s))),
                      G.doigts(a, libre, 0.15, 0.2) if ouverte else G.doigts(a, libre, 1.3, 0.9))


# « הָיָה נוֹטֵל שְׁמֹנֶה אֲבוּקוֹת שֶׁל אוֹר, וְזוֹרֵק אַחַת וְנוֹטֵל אַחַת וְאֵין נוֹגְעוֹת זוֹ בָּזוֹ » (Soucca 53a) :
# huit torches en fontaine, quatre par main, chacune relancée par la main qui l'a reçue. Les cadences sont un CHOIX.
JET = 0.225             # s entre deux lancers, d'une main à l'autre
TENUE = 0.30            # s dans la main, de la réception au lancer
VOL = 8 * JET - TENUE
PESANTEUR = 9.81
INCLINAISON_TENUE = 0.75   # rad : la tête de la torche en avant, loin du visage
AXE_TENUE = Vector((0.0, -math.sin(INCLINAISON_TENUE), math.cos(INCLINAISON_TENUE)))


# La poigne dans son cycle de deux jets : lancé à l'intérieur à `phase` 0, vide par-dessus, reçu dehors, porté par-dessous.
def poing_du_jongleur(h, cote, phase):
    s = 1.0 if cote == "l" else -1.0
    z0 = h.z_hanche + 0.20
    dedans, dehors = s * 0.10, s * 0.30
    tenue = TENUE / (2 * JET)
    if phase < 1.0 - tenue:
        u = phase / (1.0 - tenue)
        return Vector((dedans + (dehors - dedans) * u, -0.38, z0 + 0.05 * math.sin(math.pi * u)))
    v = (phase - 1.0 + tenue) / tenue
    return Vector((dehors + (dedans - dehors) * v, -0.38, z0 - 0.10 * math.sin(math.pi * v)))


def depart_du_poing(cote):
    return 0.0 if cote == "l" else JET


def poing_a(h, cote, t):
    return poing_du_jongleur(h, cote, ((t - depart_du_poing(cote)) / (2 * JET)) % 1.0)


def torche_jonglee(j):
    cote = "lr"[j % 2]
    decalage = depart_du_poing(cote) + 2 * JET * (j // 2)

    def matrice(h, a, horloge, t, poses):
        u = (t - decalage) % (8 * JET)
        if u >= VOL:
            p, tour = poing_a(h, cote, t), 0.0
        else:
            lancer, reception = poing_du_jongleur(h, cote, 0.0), poing_du_jongleur(h, cote, 1.0 - TENUE / (2 * JET))
            p = lancer.lerp(reception, u / VOL)
            p.z += PESANTEUR * u * (VOL - u) / 2
            tour = TOUR * u / VOL
        m = Matrix.Rotation(INCLINAISON_TENUE + tour, 4, "X")
        m.translation = p
        return m
    return Accessoire(f"avouka_{j + 1}", avouka, matrice)


# Les coudes au corps, la poigne toujours fermée sur la torche qu'elle tient ou attend.
def jongler(h, a, horloge, t):
    corps = G.composer(G.debout(a, horloge, t, 0.2, regard=0.0), G.buste(flexion=-0.03), G.tete(flexion=-0.32))
    return saisir(a, corps, RAYON_MANCHE, {c: poing_a(h, c, t) for c in "lr"}, {c: AXE_TENUE for c in "lr"},
                  poles={c: None for c in "lr"})


class Role(NamedTuple):
    nom: str
    concept: str
    batir: object
    geste: object = None
    ou: tuple = None
    cap: float = 0.0
    duree: float = 16.0
    trajet: Stade = None
    foulee: float = 1.35
    vitesse: float = 1.15
    sol_haut: float = Z_AZ
    famille: str = None
    accessoires: tuple = ()


LEVIIM_Y = (-23.5, -20.0, -16.5, -13.0, -9.5, -6.0, 6.0, 9.5, 13.0, 16.5, 20.0, 23.5)
# Neuf kinorot, deux nevalim, un tziltzal : les douze qu'on ne descend jamais au-dessous (Arakhin 2:3-6).
LEVIIM_INSTRUMENTS = ("kinor",) * 4 + ("nevel", "kinor", "tziltzal", "nevel") + ("kinor",) * 4


def _levi(k, genre):
    nom = f"leviim_{k + 1}"
    cap = 180.0 + 10.0 * (_alea(nom, 3) - 0.5)
    return _musicien(nom, "leviim", genre, (-13.15, LEVIIM_Y[k], Z_AZ), cap, famille="leviim")


def _musicien(nom, concept, genre, ou, cap, famille=None):
    age = 0.42 + 0.45 * _alea(nom, 0)
    gabarit = Gabarit(1.66 + 0.14 * _alea(nom, 1), age=age, peau="old_caucasian_male" if age > 0.78 else
                      "middleage_caucasian_male")
    retard = 0.06 * (_alea(nom, 2) - 0.5)

    echelle = 1.35 if genre == "nevel" else 1.0

    def batir():
        h = levi(nom, gabarit, gris=age > 0.72)
        if genre == "tziltzal":
            for cote in ("l", "r"):
                tenir(h, f"tziltzal_{cote}", tziltzal, f"hand_{cote}", repere_cymbale(h, cote))
        else:
            tenir(h, genre, lambda mm, r: kinor(mm, r, echelle), "spine_03", repere_kinor(h, echelle))
        return h

    if genre == "tziltzal":
        geste = lambda h, a, horloge, t: frapper(h, a, horloge, t, retard)
    else:
        geste = lambda h, a, horloge, t: jouer_kinor(h, a, horloge, t, echelle, retard)
    return Role(nom, concept, batir, geste, ou, cap, duree=MESURES * BATTEMENT, famille=famille)


# À terre, dans l'Ezrat Israël au pied du Doukhan : la tête à hauteur des pieds des Léviim (Arakhin 2:6, R. Eliézer ben Yaakov).
def _tzoar(k, y):
    nom = f"tzoarei_haleviim_{k + 1}"
    gabarit = Gabarit(1.18 + 0.10 * _alea(nom, 1), age=0.12 + 0.05 * _alea(nom, 0), peau="young_caucasian_male")
    retard = 0.06 * (_alea(nom, 2) - 0.5)
    return Role(nom, "tzoarei_haleviim", lambda: levi(nom, gabarit, barbe=False),
                lambda h, a, horloge, t: chanter(h, a, horloge, t, retard),
                (-10.4, y, Z_AZ), 180.0 + 8.0 * (_alea(nom, 3) - 0.5), duree=MESURES * BATTEMENT)


def _cohen(nom, geste, ou, cap, gabarit, tenu=None, gris=False, duree=16.0):
    def batir():
        h = cohen(nom, gabarit, gris=gris)
        if tenu:
            objet, construire, repere = tenu
            tenir(h, objet, construire, "spine_03", repere(h))
        return h
    return Role(nom, nom, batir, geste, ou, cap, duree=duree, famille="cohanim")


# Un des cinq postes des Léviim aux portes de l'Azara (Middot 1:1), hors de la porte, sur le palier des quinze marches.
def _shomer_levi():
    return Role("shomer_levi", "shomer_levi", lambda: levi("shomer_levi", Gabarit(1.79, age=0.45)), garder,
                (9.0, 5.5, Z_AZ), 0.0, duree=24.0)


# Chaque figure fait un geste du tamid du matin, à l'endroit que la Mishna lui donne ; son nom est son concept.
def roles_du_tamid():
    return [
        # Au Kiyor (Middot 3:6) : main droite sur le pied droit, main gauche sur le pied gauche, penché.
        _cohen("kiddoush_yadayim", lavage, (-59.0, -17.4, Z_AZ), 90.0, Gabarit(1.74, age=0.55), duree=12.0),
        # Le kevesh au sud de l'autel (Middot 3:3) : on monte par la droite, on descend par la gauche (Zeva'him 6:3).
        Role("aliyat_hakevesh", "aliyat_hakevesh", lambda: cohen("aliyat_hakevesh", Gabarit(1.77, age=0.62)),
             trajet=Stade((-38.0, -52.0), (-38.0, -28.0), 2.0, sens=-1), vitesse=1.0, sol_haut=9.0, famille="cohanim"),
        # Le sang du tamid au coin nord-est (Tamid 4:1).
        _cohen("zerika", zerika, (-20.5, 4.6, Z_AZ), 142.0, Gabarit(1.72, age=0.82, peau="old_caucasian_male"),
               tenu=("mizrak", mizrak, repere_mizrak), gris=True),
        # Les membres salés sur la moitié basse du kevesh, à l'ouest, où le sel est posé (Tamid 4:3).
        _cohen("melihat_haevarim", saler, (-41.5, -46.5, 3.0), 180.0, Gabarit(1.73, age=0.50),
               tenu=("ever", ever, repere_ever), duree=6.0),
        # Le bois monté sur l'autel pour la ma'arakha, dressée à l'est (Tamid 2:3-4).
        _cohen("siddour_hamaarakha", charger, (-26.0, -9.0, 9.0), 180.0, Gabarit(1.76, age=0.42),
               tenu=("gizra", gizra, repere_gizra), duree=8.0),
        # Sur la marche haute de la pierre de la Menora (Tamid 3:9).
        _cohen("hatavat_hanerot", hatava, (-123.6, -7.5, Z_BAT + 0.9), 180.0, Gabarit(1.70, age=0.58), duree=10.0),
    ] + [_levi(k, genre) for k, genre in enumerate(LEVIIM_INSTRUMENTS)] + [
        _tzoar(0, 3.2), _tzoar(1, -3.2),
        # Les anshei ma'amad, debout sur leur korban dans l'Ezrat Israël (Ta'anit 4:2 ; Middot 5:1).
        Role("anshei_maamad_1", "anshei_maamad",
             lambda: fidele("anshei_maamad_1", "costume", Gabarit(1.76, age=0.68), tete="talith"), priere,
             (-5.0, -26.0, Z_AZ), 180.0),
        Role("anshei_maamad_2", "anshei_maamad",
             lambda: fidele("anshei_maamad_2", "costume", Gabarit(1.69, age=0.85, peau="old_caucasian_male"), gris=True),
             ecouter, (-5.5, 24.0, Z_AZ), 186.0),
    ]


CENTRE_DES_MAALOT = 5.0     # amot : EX0 du blockout, d'où les quinze demi-cercles sont tracés
# Soucca 5:4 : « בְּכִנּוֹרוֹת וּבִנְבָלִים וּבִמְצִלְתַּיִם … בְּלֹא מִסְפָּר ». Un par marche, et ce partage : CHOIX.
MAALOT_INSTRUMENTS = ("kinor", "nevel", "kinor", "tziltzal", "kinor", "kinor", "nevel", "kinor", "kinor", "tziltzal",
                      "nevel", "kinor", "kinor", "nevel", "kinor")


# Tournés vers l'Ezrat Nashim, sur le giron de la marche `i` (Middot 2:5 : une demi-ama), les pieds tenant dessus.
# Un côté puis l'autre, à 20° au moins de l'axe : les deux cohanim descendent au milieu en sonnant (Soucca 5:4).
def _levi_des_maalot(i):
    rayon = 13.1 - 0.5 * i
    cote, n = (1.0, 8) if i % 2 == 0 else (-1.0, 7)
    angle = math.radians(cote * (20.0 + 50.0 * ((i // 2 * 3) % n) / (n - 1)))
    ou = (CENTRE_DES_MAALOT + rayon * math.cos(angle), rayon * math.sin(angle), Z_EZN + 0.5 * (i + 1))
    return _musicien(f"leviim_hamaalot_{i + 1}", "leviim_hamaalot", MAALOT_INSTRUMENTS[i], ou, math.degrees(angle))


# Chacun ouvert de 35° vers son côté de la porte : de face, la trompette se cachait derrière les poings.
def _toke(k, y):
    nom = f"tokei_hatzotzrot_{k + 1}"

    def batir():
        h = cohen(nom, Gabarit(1.72 + 0.06 * _alea(nom, 1), age=0.45 + 0.3 * _alea(nom, 0)))
        h.bouche = bouche(h)
        return h
    return Role(nom, "tokei_hatzotzrot", batir, tekia, (3.0, y, Z_EZI), math.copysign(35.0, y), duree=TEKIA,
                accessoires=(Accessoire("hatzotzra", hatzotzra, trompette_tenue),))


RONDE = (78.0, 14.0)        # amot : CHOIX, hors des allées du parcours, entre les mâts de l'est et l'axe
DANSEURS = 8


def _hassid(k):
    nom = f"hassidim_veanshei_maase_{k + 1}"
    age = 0.35 + 0.55 * _alea(nom, 0)
    gabarit = Gabarit(1.66 + 0.16 * _alea(nom, 1), age=age, poids=0.4 + 0.3 * _alea(nom, 2),
                      peau="old_caucasian_male" if age > 0.8 else "middleage_caucasian_male")
    tete = "chapeau" if k % 3 == 0 else "kippa"
    torche = "l" if k in (2, 5) else "r"
    return Role(nom, "hassidim_veanshei_maase", lambda: fidele(nom, "costume", gabarit, gris=age > 0.7, tete=tete),
                trajet=Hora(RONDE, 5.0, TOUR * k / DANSEURS, torche, "ouverte" if k % 2 == 0 else "poing"),
                sol_haut=Z_EZN, accessoires=(Accessoire("avouka", avouka, dans_la_poigne(torche, RAYON_MANCHE)),))


# La nuit de Sim'hat Beit HaSho'éva (Soucca 5:4, 53a) : ce que la visite montre quand le parcours tombe la nuit.
def roles_shoeva():
    return [_levi_des_maalot(i) for i in range(15)] + [_toke(0, 2.4), _toke(1, -2.4)] + [
        _hassid(k) for k in range(DANSEURS)] + [
        Role("shemone_avoukot", "shemone_avoukot",
             lambda: fidele("shemone_avoukot", "costume", Gabarit(1.73, age=0.55), tete="kippa"),
             jongler, (*RONDE, Z_EZN), 0.0, duree=64 * JET, accessoires=tuple(torche_jonglee(j) for j in range(8))),
    ]


SEIR_BLEND = RACINE / "seir.blend"
POIL_NOIR = (0.028, 0.025, 0.023)
CORNE = (0.32, 0.28, 0.23)
# Entre les deux cornes, dans le repère du bouc (`beit_hamikdash_seir.py`) : là où se posent les mains.
FRONT_DU_SEIR = Vector((0.955, 0.0, 0.965))


# « קָשַׁר לָשׁוֹן שֶׁל זְהוֹרִית בְּרֹאשׁ שָׂעִיר הַמִּשְׁתַּלֵּחַ » (Yoma 4:2) : nouée au pied des cornes, un bout qui pend ; la forme est un CHOIX.
def lashon_zehorit(mm, repere):
    centre = FRONT_DU_SEIR + Vector((0.0, 0.0, -0.012))
    boucle = [centre + Vector((0.032 * math.cos(a), 0.046 * math.sin(a), 0.006 * math.sin(2.0 * a)))
              for a in np.linspace(0.0, TOUR, 19)]
    pan = [centre + Vector((0.004 * k, 0.046 + 0.010 * k, -0.034 * k)) for k in range(6)]
    for chemin in (boucle, pan):
        mm.nappe([[repere @ p for p in a] for a in tube_simple(chemin, 0.005, 6)], SHANI, "objet")


# La tête vers l'homme, la croupe qui s'en écarte : parallèle à lui, son flanc passait dans la kutonet.
BIAIS_DU_SEIR = math.radians(20.0)


# Le bouc suit son homme : posé dans le repère de l'armature, `front` au point voulu, tourné vers où l'homme regarde.
def amener_le_seir(h, front):
    repere = (Matrix.Translation(front) @ Matrix.Rotation(-math.pi / 2.0 + BIAIS_DU_SEIR, 4, "Z")
              @ Matrix.Translation(-FRONT_DU_SEIR))
    with bpy.data.libraries.load(str(SEIR_BLEND)) as (_, charge):
        charge.meshes = ["Seir", "Seir_cornes"]
    for me, matiere, couleur in zip(charge.meshes, (poil(), corne()), (POIL_NOIR, CORNE)):
        teinter_maillage(me, couleur)
        me.materials.append(matiere)
        objet = bpy.data.objects.new(f"{h.nom}_{me.name.lower()}", me)
        for c in h.rig.users_collection:
            c.objects.link(objet)
        objet.parent = h.rig
        objet.matrix_basis = repere
    ruban = Maillage()
    lashon_zehorit(ruban, repere)
    _objet(h, ruban, f"{h.nom}_lashon_zehorit", laine())


# « וְסוֹמֵךְ שְׁתֵּי יָדָיו עָלָיו וּמִתְוַדֶּה » (Yoma 6:2), « בֵּין שְׁתֵּי קַרְנָיו » (Rambam Ma'asse HaKorbanot 3:14) :
# les deux paumes sur le front du bouc, le buste penché qui suit la confession.
def semikha(front):
    def geste(h, a, horloge, t):
        souffle = 0.5 + 0.5 * horloge.onde(t, 5.5)
        poignets = front + Vector((0.02, 0.06, 0.06))
        return G.composer(G.pied(a, "l"), G.pied(a, "r"), G.respiration(horloge, t),
                          G.bassin(Vector((0.0, 0.06, -0.03)), tangage=0.12),
                          G.buste(flexion=0.34 + 0.06 * souffle, torsion=-0.18), G.tete(flexion=0.24 + 0.08 * souffle),
                          G.bras(a, "l", poignets + G.GAUCHE * 0.04), G.bras(a, "r", poignets - G.GAUCHE * 0.04),
                          G.paume(a, "l", -G.HAUT), G.paume(a, "r", -G.HAUT),
                          G.doigts(a, "l", 0.12, 0.1), G.doigts(a, "r", 0.12, 0.1))
    return geste


# « הִשְׁתַּחֲוָיָה זֶה פִּשּׁוּט יָדַיִם וְרַגְלַיִם עַד שֶׁנִּמְצָא מֻטָּל עַל פָּנָיו אַרְצָה » (Rambam Tefila 5:13) :
# le bassin bascule d'un quart de tour et le corps entier le suit, étendu, les bras allongés devant la tête.
HAUTEUR_DU_BASSIN_COUCHE = 0.13


def prosternation(h, a, horloge, t):
    pivot = a.bassin
    couche = Matrix.Rotation(math.pi / 2.0, 3, G.GAUCHE)
    descente = Vector((0.0, 0.0, a.sol + HAUTEUR_DU_BASSIN_COUCHE - pivot.z))
    loin = Vector((0.0, 0.0, -1.0))

    def pointe(cote):
        return {f"foot_{cote}": lambda m, poses: G.viser(m, m.translation + couche @ (loin + G.LATERAL * 0.3)),
                f"ball_{cote}": lambda m, poses: G.viser(m, m.translation + couche @ loin)}

    def main_devant(s):
        return a.au("spine_03", Vector((s * 0.17, -0.10, h.z_tete + 0.32)))

    return G.composer(G.bassin(descente, tangage=math.pi / 2.0), G.respiration(horloge, t, ampleur=0.008),
                      G.buste(flexion=-0.06), G.tete(flexion=-0.10),
                      pointe("l"), pointe("r"),
                      G.bras(a, "l", main_devant(1.0)), G.bras(a, "r", main_devant(-1.0)),
                      G.paume(a, "l", lambda poses: a.dans("spine_03", poses, G.DEVANT)),
                      G.paume(a, "r", lambda poses: a.dans("spine_03", poses, G.DEVANT)),
                      G.doigts(a, "l", 0.08, 0.1), G.doigts(a, "r", 0.08, 0.1))


# Au nord-est de l'autel, où les boucs ont été tirés au sort (Yoma 3:9), tourné vers la porte de son départ (Yoma 4:2).
SEIR_OU = (-17.5, 10.6, Z_AZ)


# À sa droite, la tête devant lui : il se tient le long du bouc, tourné comme lui (CHOIX).
def front_du_seir(h):
    return Vector((-0.38, -0.50, h.sol + FRONT_DU_SEIR.z))


def _cohen_gadol():
    nom = "sair_hamishtaleach"

    def batir():
        h = cohen_gadol(nom, Gabarit(1.78, age=0.62))
        amener_le_seir(h, front_du_seir(h))
        return h
    return Role(nom, nom, batir, lambda h, a, horloge, t: semikha(front_du_seir(h))(h, a, horloge, t), SEIR_OU, 0.0,
                famille="cohanim")


# Les cohanim dans l'Ezrat Cohanim, les Israélites dans l'Ezrat Israël (Middot 5:1), tous la tête vers le Heikhal.
# Couché, un homme tient 3,5 amot devant ses pieds et 2 derrière : ni sur le yessod, ni sous les lishkot qui flanquent Nikanor.
PROSTERNES_COHANIM = ((-17.5, 26.0), (-17.0, 18.5), (-17.8, -3.0), (-17.2, -14.0), (-17.6, -27.0))
PROSTERNES_ISRAEL = ((-4.5, -41.0), (-5.2, -33.5), (-4.2, -26.5), (-4.8, 24.5), (-4.0, 31.0), (-5.0, 37.5), (-4.4, 44.0))


def _gabarit_de_prosterne(nom):
    age = 0.35 + 0.55 * _alea(nom, 0)
    return Gabarit(1.66 + 0.16 * _alea(nom, 1), age=age, poids=0.4 + 0.3 * _alea(nom, 2),
                   peau="old_caucasian_male" if age > 0.8 else "middleage_caucasian_male")


def _prosterne(nom, batir, ou, famille=None):
    cap = 180.0 + 6.0 * (_alea(nom, 3) - 0.5)
    return Role(nom, "korim_oumishtahavim", batir, prosternation, (*ou, Z_AZ), cap, famille=famille)


def _cohen_prosterne(k):
    nom = f"korim_oumishtahavim_{k + 1}"
    gabarit = _gabarit_de_prosterne(nom)
    return _prosterne(nom, lambda: cohen(nom, gabarit, gris=gabarit.age > 0.7), PROSTERNES_COHANIM[k], "cohanim")


def _israel_prosterne(k):
    nom = f"korim_oumishtahavim_{len(PROSTERNES_COHANIM) + k + 1}"
    gabarit = _gabarit_de_prosterne(nom)
    tete = "talith" if k % 2 == 0 else "kippa"
    return _prosterne(nom, lambda: fidele(nom, "costume", gabarit, gris=gabarit.age > 0.7, tete=tete),
                      PROSTERNES_ISRAEL[k])


# Yom Kippour, au troisième viduy : le Nom sort de la bouche du Cohen Gadol, et l'Azara tombe sur sa face (Yoma 6:2).
def roles_kippour():
    return [_cohen_gadol()] + [_cohen_prosterne(k) for k in range(len(PROSTERNES_COHANIM))] + [
        _israel_prosterne(k) for k in range(len(PROSTERNES_ISRAEL))]


# La visite libre : un lieu, un geste — la zerika à l'autel, deux Léviim qui jouent, un Israélite, la garde de Nikanor.
FIGURES_DE_LA_VISITE = ("zerika", "leviim_6", "leviim_7", "anshei_maamad_1")


def roles_de_la_visite():
    return [r for r in roles_du_tamid() if r.nom in FIGURES_DE_LA_VISITE] + [_shomer_levi()]


def animer_sur_place(h, role, sol):
    a = G.Acteur(h.squelette, h.sol)
    horloge = G.Horloge(role.duree)
    x, y = role.ou[0] * AMA, role.ou[1] * AMA
    place = placement(x, y, sol, cap_vers(role.cap), h.sol)
    h.rig.matrix_world = place
    rec = G.Enregistreur(h.rig, a.sq, h.rig.name)
    tenus = [[] for _ in role.accessoires]
    images = round(role.duree * IMAGES)
    for f in range(images + 1):
        t = f / IMAGES
        poses, bases = a.sq.resoudre(role.geste(h, a, horloge, t))
        rec.image(f, bases)
        tenir_image(h, a, role, horloge, t, poses, tenus)
    rec.ecrire()
    ecrire_accessoires(h, role, tenus)
    return [place]


def tenir_image(h, a, role, horloge, t, poses, tenus):
    for accessoire, suite in zip(role.accessoires, tenus):
        suite.append(accessoire.matrice(h, a, horloge, t, poses))


def ecrire_accessoires(h, role, tenus):
    for accessoire, suite in zip(role.accessoires, tenus):
        mm = Maillage()
        accessoire.construire(mm, Matrix.Identity(4))
        G.Enregistreur.objet(porter(h, mm, f"{h.nom}_{accessoire.nom}"), suite)


def animer_en_marche(h, role, terrain):
    a = G.Acteur(h.squelette, h.sol)
    trajet = role.trajet
    longueur = trajet.longueur
    foulee = longueur / max(1, round(longueur / role.foulee))
    images = round(longueur / role.vitesse * IMAGES)
    vitesse = longueur * IMAGES / images
    horloge = G.Horloge(images / IMAGES)
    rec = G.Enregistreur(h.rig, a.sq, h.rig.name)
    tenus = [[] for _ in role.accessoires]
    places = []
    for f in range(images + 1):
        t = f / IMAGES
        s = (vitesse * t) % longueur
        p = trajet.en(s)
        g = terrain(p.x, p.y)
        place = placement(p.x, p.y, g, trajet.direction(s), h.sol)

        def sol(cote, decalage, place=place, g=g):
            pied = place @ (a.cheville[cote] + decalage)
            return terrain(pied.x, pied.y) - g

        poses, bases = a.sq.resoudre(pas_de_marche(h, a, horloge, t, (s / foulee) % 1.0, foulee, sol))
        rec.image(f, bases, place)
        tenir_image(h, a, role, horloge, t, poses, tenus)
        if f % IMAGES == 0:
            places.append(place)
    h.rig.matrix_world = places[0]
    rec.ecrire()
    ecrire_accessoires(h, role, tenus)
    return places


# Les pieds posés restent où ils sont sur la dalle : la racine suit leur milieu, face au centre.
def animer_en_danse(h, role, terrain):
    a = G.Acteur(h.squelette, h.sol)
    hora = role.trajet
    images = round(hora.duree * IMAGES)
    rec = G.Enregistreur(h.rig, a.sq, h.rig.name)
    horloge = G.Horloge(images / IMAGES)
    tenus = [[] for _ in role.accessoires]
    places = []
    for f in range(images + 1):
        b = hora.pas.temps * f / images
        traces = {c: hora.pas.pied(c, b) for c in "lr"}
        racine = hora.monde(sum(p[0] for p in traces.values()) / 2, sum(p[1] for p in traces.values()) / 2)
        g = terrain(racine.x, racine.y)
        place = placement(racine.x, racine.y, g, hora.centre - racine, h.sol)
        inverse = place.inverted()
        pieds = {}
        for c, (x, y, hauteur, envol) in traces.items():
            dalle = hora.monde(x, y)
            local = inverse @ Vector((dalle.x, dalle.y, 0.0))
            pieds[c] = (Vector((local.x - a.cheville[c].x, local.y - a.cheville[c].y,
                                hauteur + terrain(dalle.x, dalle.y) - g)), envol)
        poses, bases = a.sq.resoudre(danse(h, a, hora, b, pieds))
        rec.image(f, bases, place)
        tenir_image(h, a, role, horloge, f / IMAGES, poses, tenus)
        if f % IMAGES == 0:
            places.append(place)
    h.rig.matrix_world = places[0]
    rec.ecrire()
    ecrire_accessoires(h, role, tenus)
    return places


# Mesurée sur la pose de la première image, avec ce que la figure porte : couché, un corps sort de sa boîte debout.
def points_poses(h):
    bpy.context.scene.frame_set(0)
    graphe = bpy.context.evaluated_depsgraph_get()
    points = []
    for objet in (o for o in h.rig.children if o.type == "MESH"):
        evalue = objet.evaluated_get(graphe)
        me = evalue.to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        evalue.to_mesh_clear()
        passage = np.array(objet.matrix_local)
        co = co.reshape(-1, 3) @ passage[:3, :3].T + passage[:3, 3]
        points.append(co)
    return np.vstack(points)


def emprise(h, places):
    poses = points_poses(h)
    bas, haut = poses.min(axis=0) - 0.15, poses.max(axis=0) + 0.15
    coins = [Vector((x, y, z)) for x in (bas[0], haut[0]) for y in (bas[1], haut[1]) for z in (bas[2], haut[2])]
    points = [place @ c for place in places for c in coins]
    return ([min(p.x for p in points), min(p.z for p in points), -max(p.y for p in points)],
            [max(p.x for p in points), max(p.z for p in points), -min(p.y for p in points)])


def unir(boites):
    return {"min": [min(b[0][k] for b in boites) for k in range(3)], "max": [max(b[1][k] for b in boites) for k in range(3)]}


VUES = [
    # Face au Kiyor, entre la Mer de bronze et l'autel : de plus loin, l'un ou l'autre le cache.
    dict(id="vue_kiddoush_yadayim", position=(-54.8, -29.2, Z_AZ), cap=105, tangage=-4),
    # Les Léviim font face au Sanctuaire ; neuf amot entre l'autel et le Doukhan ne cadrent pas les douze de face.
    dict(id="vue_leviim", position=(-20.5, -30.0, Z_AZ), cadre=["leviim"]),
    # De dos, l'autel devant lui : depuis le seuil de Nikanor, dans l'Ezrat Israël.
    dict(id="vue_anshei_maamad", position=(-1.5, -26.5, Z_AZ - 2.5), cap=180),
]


class Troupe(NamedTuple):
    roles: object
    vues: list


TROUPES = {"figures": Troupe(roles_de_la_visite, VUES), "figures_tamid": Troupe(roles_du_tamid, VUES),
           "figures_kippour": Troupe(roles_kippour, []), "figures_shoeva": Troupe(roles_shoeva, [])}


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    nom_troupe = "figures"
    if "--troupe" in arguments:
        k = arguments.index("--troupe")
        nom_troupe = arguments[k + 1]
        del arguments[k:k + 2]
    troupe = TROUPES[nom_troupe]
    bpy.context.scene.render.fps, bpy.context.scene.render.fps_base = IMAGES, 1.0
    lot = [r for r in troupe.roles() if not arguments or r.nom in arguments]
    terrains, sols, releves = {}, {}, {}
    for role in lot:
        if role.trajet:
            # Les danseurs d'une même ronde foulent le même sol : un relevé pour tous.
            cle = (*role.trajet.bornes(0.8), role.sol_haut * AMA)
            releves[cle] = releves.get(cle) or Terrain(*cle)
            terrains[role.nom] = releves[cle]
        else:
            sols[role.nom] = _rayon_sol(role.ou[0] * AMA, role.ou[1] * AMA, role.ou[2] * AMA)

    boites, figures = {}, []
    for role in lot:
        h = role.batir()
        if isinstance(role.trajet, Hora):
            places = animer_en_danse(h, role, terrains[role.nom])
        elif role.trajet:
            places = animer_en_marche(h, role, terrains[role.nom])
        else:
            places = animer_sur_place(h, role, sols[role.nom])
        # Les cohanim ont aussi leur emprise commune : « Un élément… » y mène. Les Léviim sont déjà un concept.
        for concept in {role.concept, role.famille} - {None}:
            boites.setdefault(concept, []).append(emprise(h, places))
        figures.append(h)
        print(f"  {role.nom:12s} {len(places):4d} places")

    bpy.ops.object.select_all(action="DESELECT")
    for h in figures:
        h.rig.select_set(True)
        for enfant in h.rig.children:
            enfant.select_set(True)
    glb = DOSSIER / f"{nom_troupe}.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb), export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
        export_cameras=False, export_lights=False, export_extras=False, export_materials="EXPORT",
        export_normals=True, export_texcoords=True, export_vertex_color="MATERIAL", export_image_format="WEBP",
        export_image_quality=82, export_skins=True, export_influence_nb=4, export_animations=True,
        export_animation_mode="ACTIONS", export_force_sampling=True, export_optimize_animation_size=True,
        export_def_bones=False)
    comprimer(glb, ("-af", str(IMAGES), "-si", "0.5"))

    emprises = {concept: unir(liste) for concept, liste in boites.items()}
    (DOSSIER / f"{nom_troupe}.json").write_text(json.dumps({
        "emprises": emprises,
        "vues": [en_metres(v, emprises) for v in troupe.vues if v["id"].removeprefix("vue_") in emprises],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(figures)} figures · {glb.name} {glb.stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()
