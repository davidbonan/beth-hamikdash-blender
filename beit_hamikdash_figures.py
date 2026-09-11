"""Blender -b beit_hamikdash.blend -P beit_hamikdash_figures.py [-- rôle …] — écrit visite/figures.glb et visite/figures.json."""
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
from beit_hamikdash_visite import AMA, DOSSIER, Z_AZ, Z_EZN, comprimer, en_metres  # noqa: E402

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
FOULARD = (0.50, 0.44, 0.36)
CHENE = (0.28, 0.17, 0.08)
BOYAU = (0.62, 0.52, 0.36)
BRONZE = (0.62, 0.40, 0.18)
OR = (1.0, 0.74, 0.30)


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


def bois():
    return _matiere("Figure_Bois", 0.6)


def metal():
    return _matiere("Figure_Metal", 0.32, 1.0)


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


# `pieces` : rangs, de la plus grande à la plus petite, des parties du maillage gardées.
class Habit(NamedTuple):
    asset: str
    matiere: str = None
    couleur: tuple = None
    pieces: tuple = None
    longue: bool = False


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
    teint: tuple = (0.80, 0.64, 0.50)


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
        teinter_objet(self.corps, g.teint)
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
                self.ajuster_epaules(objet)
            if habit.longue:
                self.ample(objet)
                ourlet = float(self.points_objet(objet)[:, 2].min()) + 0.10
                self.efface |= ~self.bras & ~self.main & (self.co[:, 2] > ourlet) & (self.co[:, 2] < self.z_hanche + 0.05)

    # Épaules relevées et haut des manches, trop amples pour suivre un bras levé : ramenés sur la peau, ils en prennent les poids.
    def ajuster_epaules(self, objet):
        passage = self.rig.matrix_world.inverted() @ objet.matrix_world
        retour = passage.inverted()
        corps, bras = surface_de(self, [], self.visible), surface_de(self, [], self.visible & self.bras)
        groupes = objet.vertex_groups
        for v in objet.data.vertices:
            p = passage @ v.co
            avant = {groupes[e.group].name: e.weight for e in v.groups}
            haut_du_bras = sum(w for k, w in avant.items() if k.startswith("upperarm"))
            t = max(G.lisse((p.z - self.z_epaule + 0.07) / 0.06), 0.85 * G.lisse(haut_du_bras / 0.5))
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
AVNET = ((0.000, LIN), (0.010, TEKHELET), (0.022, ARGAMAN), (0.034, SHANI), (0.046, TEKHELET), (0.056, LIN), (0.064, LIN))


def avnet(mm, ceinture, surface):
    z0 = ceinture.z - 0.032
    th = _angles()
    anneaux, couleurs = [], []
    for dz, couleur in AVNET:
        epaisseur = 0.003 if dz in (0.0, AVNET[-1][0]) else 0.010
        anneaux.append([ceinture.point(t, z0 + dz, epaisseur) for t in th])
        couleurs.append(couleur)
    mm.nappe(anneaux, lambda i, j: couleurs[i + 1], "buste")
    raies = (TEKHELET, ARGAMAN, SHANI)
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


HAUT_Z = Vector((0.0, 0.0, 1.0))


# Calotte posée en arrière du sommet, par-dessus les cheveux.
def calotte(mm, humain, couleur, rayon=0.056, recul=0.65, ecart=0.005):
    h = humain
    tete = h.visible & h.tete_
    arbre = surface_de(h, [h.cheveux] if h.cheveux else [], tete)
    centre = Vector(h.co[tete].mean(axis=0))
    axe = Vector((0.0, math.sin(recul), math.cos(recul)))
    u = Vector((1.0, 0.0, 0.0))
    w = axe.cross(u)
    ouverture = rayon / 0.095

    def direction(a, phi):
        return (axe * math.cos(a) + (u * math.cos(phi) + w * math.sin(phi)) * math.sin(a)).normalized()

    def distance(d):
        touche = arbre.ray_cast(centre + d * 0.3, -d)[0]
        return (touche - centre).length if touche is not None else 0.095

    phis = np.linspace(0.0, TOUR, 36, endpoint=False)
    rangs = [(ouverture, ecart - 0.003)] + [(ouverture * (1.0 - k / 9), ecart + 0.002 + 0.004 * math.sin(math.pi * k / 18))
                                             for k in range(9)]
    directions = [[direction(a, phi) for phi in phis] for a, _ in rangs]
    distances = np.array([[distance(d) for d in rang] for rang in directions])
    # Un rayon passé entre deux mèches creuserait la calotte : chaque point suit sa voisine la plus haute.
    bombe = np.max([np.roll(distances, k, axis=1) for k in (-2, -1, 0, 1, 2)], axis=0)
    anneaux = [[centre + d * (r + e) for d, r in zip(rang, ligne)] for rang, ligne, (_, e) in zip(directions, bombe, rangs)]
    sommet = direction(0.0, 0.0)
    mm.nappe(anneaux, couleur, "head", pole_fin=centre + sommet * (float(bombe[-1].max()) + ecart + 0.006))


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
    profil = ((0.000, 0.004), (0.02, 0.040), (0.05, 0.080), (0.075, 0.100), (0.082, 0.104), (0.078, 0.094))
    anneaux = [[repere @ Vector((r * math.cos(a), r * math.sin(a), z)) for a in np.linspace(0, TOUR, 22, endpoint=False)]
               for z, r in profil]
    mm.nappe(anneaux, OR, "objet")


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


def lier(humain, mm, nom, materiau, os_fixe=None, tissu=None):
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


BARBES = ("grinsegold_beard_sigmund_wip", "rehmanpolanski_beard_viking")
MOUSTACHE = "rehmanpolanski_moustache_viking"
CHEVEUX_COURTS = ("short01", "short04")
BRUN = (0.30, 0.24, 0.20)
GRIS = (1.1, 1.05, 1.0)


def _poils(nom, gris):
    barbe = BARBES[int(_alea(nom, 4 if gris else 3) * len(BARBES))]
    return dict(cheveux=CHEVEUX_COURTS[int(_alea(nom, 5) * 2)], barbe=(barbe, MOUSTACHE), teinte_poils=GRIS if gris else BRUN,
                sourcils=1 + int(_alea(nom, 6) * 9))


# Robe de moine CC0 (Donitz) sans pèlerine ni cordon : la coupe longue à manches de la kutonet.
KUTONET = Habit("donitz_monk_robe", "Figure_Kutonet", LIN, pieces=(0, 2, 3), longue=True)
ROBE = Habit("punkduck_medieval_dress", "Figure_Robe", LAINE_BLEUE, longue=True)
VOILE = Habit("elvs_charity_veil1", "Figure_Voile", FOULARD)
COSTUME = Habit("male_elegantsuit01")
CHAUSSURES = Habit("shoes03")
COIFFES = {"chapeau": Habit("fedora01", "Figure_Chapeau", DRAP_NOIR), "foulard": VOILE}


# Lin (Rambam Klei HaMikdash 8:1), pieds nus (Zeva'him 24a).
def cohen(nom, gabarit=Gabarit(), gris=False):
    h = Humain(nom, gabarit, **_poils(nom, gris))
    robe = h.vetir_mpfb(KUTONET)
    h.detendre()
    ceinture = Ceinture(h, h.squelette.tete("lowerarm_l").z)
    ceinture.serrer(h, robe)
    ceint = Maillage()
    avnet(ceint, ceinture, surface_de(h, [robe]))
    lier(h, ceint, f"{nom}_avnet", lin())
    coiffure = Maillage()
    migbaat(coiffure, h)
    lier(h, coiffure, f"{nom}_migbaat", lin(), "head")
    appliquer_visibilite(h, h.visible & ~h.efface)
    return h


# « מְלֻבָּשִׁים בּוּץ » (Divrei HaYamim II 5:12).
def levi(nom, gabarit=Gabarit(), gris=False):
    h = Humain(nom, gabarit, **_poils(nom, gris))
    h.vetir_mpfb(KUTONET)
    h.detendre()
    coiffure = Maillage()
    calotte(coiffure, h, LIN, rayon=0.070)
    lier(h, coiffure, f"{nom}_kippa", lin(), "head")
    appliquer_visibilite(h, h.visible & ~h.efface)
    return h


def fidele(nom, tenue, gabarit=Gabarit(), gris=False, barbe=True, tete="kippa"):
    poils = _poils(nom, gris)
    if not barbe:
        poils["barbe"] = None
    h = Humain(nom, gabarit, **poils)
    h.vetir_mpfb({"costume": COSTUME, "robe": ROBE}[tenue])
    h.vetir_mpfb(CHAUSSURES)
    if tete in COIFFES:
        h.vetir_mpfb(COIFFES[tete])
    h.detendre()
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
    materiau = metal() if all(c in (OR, BRONZE) for c in mm.couleurs) else bois()
    return lier(h, mm, f"{h.nom}_{nom}", materiau, os_)


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


# En amot : aller-retour de `a` à `b`, demi-tours de `rayon` aux deux bouts.
class Stade:
    def __init__(self, a, b, rayon, pas=0.04):
        a, b, r = Vector(a) * AMA, Vector(b) * AMA, rayon * AMA
        d = (b - a).normalized()
        n = Vector((-d.y, d.x))
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


def repere_kinor(h, echelle):
    base = Vector((0.07, -0.28 - 0.05 * (echelle - 1.0), h.z_epaule - 0.36 * echelle))
    return repere_vers(base, Vector((0.28, -0.30, 1.0)), Vector((1.0, 0.0, -0.25)))


def jouer_kinor(h, a, horloge, t, echelle, retard):
    lyre = a.repere("spine_03", repere_kinor(h, echelle))
    b = (t / BATTEMENT - retard) % 1.0
    geste = G.lisse(b / 0.30) if b < 0.30 else 1.0 - G.lisse((b - 0.30) / 0.70)
    e = echelle
    return G.composer(G.debout(a, horloge, t, retard, regard=0.03), G.balancement(t, BATTEMENT, retard=retard),
                      G.bras(a, "l", lambda poses: lyre(poses) @ Vector((0.16 * e, 0.0, 0.40 * e))),
                      G.bras(a, "r", lambda poses: lyre(poses) @ Vector(((-0.07 + 0.13 * geste) * e, -0.06, 0.30 * e))),
                      G.doigts(a, "l", 0.7, 0.4), G.doigts(a, "r", 0.3 + 0.3 * geste))


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


def parler(h, a, horloge, t):
    montre = 0.5 + 0.5 * horloge.onde(t, 3.2)
    main = a.au("spine_03", devant_poitrine(h, 0.20 + 0.14 * montre, 0.38 - 0.10 * montre, -0.14))
    return G.composer(G.debout(a, horloge, t, 0.7, regard=0.06), G.tete(flexion=0.05 * horloge.onde(t, 1.6)),
                      G.bras_ballant(a, "l"), G.bras(a, "r", main), G.paume(a, "r", G.HAUT + G.DEVANT),
                      G.doigts(a, "l"), G.doigts(a, "r", 0.2))


def ecouter(h, a, horloge, t):
    mains = a.au("spine_03", Vector((0.0, -0.16, h.z_hanche - 0.02)))
    return G.composer(G.debout(a, horloge, t, 0.4, regard=0.04), G.tete(flexion=0.06 + 0.04 * horloge.onde(t, 2.4)),
                      G.bras(a, "l", lambda poses: mains(poses) + G.GAUCHE * 0.03),
                      G.bras(a, "r", lambda poses: mains(poses) - G.GAUCHE * 0.03),
                      G.doigts(a, "l", 0.6), G.doigts(a, "r", 0.6))


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


LEVIIM_Y = (-23.5, -20.0, -16.5, -13.0, -9.5, -6.0, 6.0, 9.5, 13.0, 16.5, 20.0, 23.5)
# Neuf kinorot, deux nevalim, un tziltzal : les douze qu'on ne descend jamais au-dessous (Arakhin 2:3-6).
LEVIIM_INSTRUMENTS = ("kinor",) * 4 + ("nevel", "kinor", "tziltzal", "nevel") + ("kinor",) * 4


def _levi(k, genre):
    nom = f"leviim_{k + 1}"
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
    return Role(nom, "leviim", batir, geste, (-13.15, LEVIIM_Y[k], Z_AZ), 180.0 + 10.0 * (_alea(nom, 3) - 0.5),
                duree=MESURES * BATTEMENT)


def roles():
    return [
        # Deux cohanim au Kiyor (Middot 3:6) : l'un se sanctifie mains et pieds, l'autre va et vient.
        Role("cohanim_1", "cohanim", lambda: cohen("cohanim_1", Gabarit(1.74, age=0.55)), lavage,
             (-59.0, -17.4, Z_AZ), 90.0, duree=12.0),
        Role("cohanim_2", "cohanim", lambda: cohen("cohanim_2", Gabarit(1.71, age=0.48)),
             trajet=Stade((-62.0, -20.0), (-62.0, -31.0), 1.8)),
        # Le kevesh monte du sud vers l'autel (Middot 3:3) : on y monte d'un côté, on en descend de l'autre.
        Role("cohanim_3", "cohanim", lambda: cohen("cohanim_3", Gabarit(1.77, age=0.62)),
             trajet=Stade((-38.0, -52.0), (-38.0, -28.0), 2.0), vitesse=1.0, sol_haut=9.0),
        Role("cohanim_4", "cohanim", lambda: tenir_mizrak(cohen("cohanim_4", Gabarit(1.72, age=0.82,
                                                                                        peau="old_caucasian_male"),
                                                                   gris=True)),
             zerika, (-20.5, 4.6, Z_AZ), 142.0),
    ] + [_levi(k, genre) for k, genre in enumerate(LEVIIM_INSTRUMENTS)] + [
        Role("fideles_1", "fideles", lambda: fidele("fideles_1", "costume", Gabarit(1.78, age=0.55), tete="chapeau"),
             trajet=Stade((24.0, -5.5), (50.0, -5.5), 1.4), vitesse=1.05, sol_haut=Z_EZN),
        Role("fideles_2", "fideles", lambda: fidele("fideles_2", "costume", Gabarit(1.22, age=0.15,
                                                                                   peau="young_caucasian_male"),
                                                    barbe=False),
             trajet=Stade((24.0, -5.5), (50.0, -5.5), 3.3), foulee=0.95, sol_haut=Z_EZN),
        Role("fideles_3", "fideles", lambda: fidele("fideles_3", "costume", Gabarit(1.76, age=0.68), tete="talith"),
             priere, (58.0, -13.0, Z_EZN), 180.0),
        Role("fideles_4", "fideles", lambda: fidele("fideles_4", "costume", Gabarit(1.73, age=0.45)),
             parler, (70.0, 14.0, Z_EZN), 301.0),
        Role("fideles_5", "fideles", lambda: fidele("fideles_5", "costume", Gabarit(1.69, age=0.85,
                                                                                    peau="old_caucasian_male"),
                                                    gris=True),
             ecouter, (71.3, 11.8, Z_EZN), 121.0),
        Role("fideles_6", "fideles", lambda: fidele("fideles_6", "robe", Gabarit(1.62, genre=0.0, age=0.5,
                                                                                peau="middleage_caucasian_female"),
                                                    barbe=False, tete="foulard"),
             trajet=Stade((80.0, 6.0), (98.0, 6.0), 1.6), vitesse=1.0, foulee=1.2, sol_haut=Z_EZN),
    ]


def tenir_mizrak(h):
    tenir(h, "mizrak", mizrak, "spine_03", repere_mizrak(h))
    return h


# Le père et le fils bouclent leur tour dans le même temps.
DUREE_COMMUNE = {"fideles_1": "fideles_2"}


def animer_sur_place(h, role, sol):
    a = G.Acteur(h.squelette, h.sol)
    horloge = G.Horloge(role.duree)
    x, y = role.ou[0] * AMA, role.ou[1] * AMA
    place = placement(x, y, sol, cap_vers(role.cap), h.sol)
    h.rig.matrix_world = place
    rec = G.Enregistreur(h.rig, a.sq, h.rig.name)
    images = round(role.duree * IMAGES)
    for f in range(images + 1):
        t = f / IMAGES
        _, bases = a.sq.resoudre(role.geste(h, a, horloge, t))
        rec.image(f, bases)
    rec.ecrire()
    return [place]


def animer_en_marche(h, role, terrain, duree=None):
    a = G.Acteur(h.squelette, h.sol)
    trajet = role.trajet
    longueur = trajet.longueur
    foulee = longueur / max(1, round(longueur / role.foulee))
    images = round((duree or longueur / role.vitesse) * IMAGES)
    vitesse = longueur * IMAGES / images
    horloge = G.Horloge(images / IMAGES)
    rec = G.Enregistreur(h.rig, a.sq, h.rig.name)
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

        regles = G.composer(G.marche(a, (s / foulee) % 1.0, foulee, sol), G.respiration(horloge, t),
                            G.tete(lacet=0.08 * horloge.onde(t, 6.0)))
        _, bases = a.sq.resoudre(regles)
        rec.image(f, bases, place)
        if f % IMAGES == 0:
            places.append(place)
    h.rig.matrix_world = places[0]
    rec.ecrire()
    return places, images


def emprise(h, places):
    visibles = h.co[h.visible]
    bas, haut = visibles.min(axis=0) - 0.15, visibles.max(axis=0) + 0.15
    coins = [Vector((x, y, z)) for x in (bas[0], haut[0]) for y in (bas[1], haut[1]) for z in (bas[2], haut[2])]
    points = [place @ c for place in places for c in coins]
    return ([min(p.x for p in points), min(p.z for p in points), -max(p.y for p in points)],
            [max(p.x for p in points), max(p.z for p in points), -min(p.y for p in points)])


def unir(boites):
    return {"min": [min(b[0][k] for b in boites) for k in range(3)], "max": [max(b[1][k] for b in boites) for k in range(3)]}


VUES = [
    # Face au Kiyor, entre la Mer de bronze et l'autel : de plus loin, l'un ou l'autre le cache.
    dict(id="vue_cohanim", position=(-54.8, -29.2, Z_AZ), cap=105, tangage=-4),
    # Les Léviim font face au Sanctuaire ; neuf amot entre l'autel et le Doukhan ne cadrent pas les douze de face.
    dict(id="vue_leviim", position=(-20.5, -30.0, Z_AZ), cadre=["leviim"]),
    dict(id="vue_fideles", cadre=["fideles"], cap=180, sol=Z_EZN, recul_max=60.0),
]


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.context.scene.render.fps, bpy.context.scene.render.fps_base = IMAGES, 1.0
    lot = [r for r in roles() if not arguments or r.nom in arguments]
    terrains, sols = {}, {}
    for role in lot:
        if role.trajet:
            terrains[role.nom] = Terrain(*role.trajet.bornes(0.8), role.sol_haut * AMA)
        else:
            sols[role.nom] = _rayon_sol(role.ou[0] * AMA, role.ou[1] * AMA, role.ou[2] * AMA)

    boites, figures, durees = {}, [], {}
    for role in lot:
        h = role.batir()
        if role.trajet:
            commune = next((k for k, v in DUREE_COMMUNE.items() if v == role.nom), None)
            places, images = animer_en_marche(h, role, terrains[role.nom], durees.get(commune))
            durees[role.nom] = images / IMAGES
        else:
            places = animer_sur_place(h, role, sols[role.nom])
        boites.setdefault(role.concept, []).append(emprise(h, places))
        figures.append(h)
        print(f"  {role.nom:12s} {len(places):4d} places")

    bpy.ops.object.select_all(action="DESELECT")
    for h in figures:
        h.rig.select_set(True)
        for enfant in h.rig.children:
            enfant.select_set(True)
    glb = DOSSIER / "figures.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb), export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
        export_cameras=False, export_lights=False, export_extras=False, export_materials="EXPORT",
        export_normals=True, export_texcoords=True, export_vertex_color="MATERIAL", export_image_format="WEBP",
        export_image_quality=82, export_skins=True, export_influence_nb=4, export_animations=True,
        export_animation_mode="ACTIONS", export_force_sampling=True, export_optimize_animation_size=True,
        export_def_bones=False)
    comprimer(glb, ("-af", str(IMAGES), "-si", "0.5"))

    emprises = {concept: unir(liste) for concept, liste in boites.items()}
    (DOSSIER / "figures.json").write_text(json.dumps({
        "emprises": emprises,
        "vues": [en_metres(v, emprises) for v in VUES if set(v.get("cadre", ())) <= emprises.keys()],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(figures)} figures · figures.glb {glb.stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()
