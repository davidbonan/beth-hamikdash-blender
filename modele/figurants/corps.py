import pathlib
import zlib
from typing import NamedTuple

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

import beit_hamikdash_gestes as G

from bl_ext.blender_org.mpfb.entities.objectproperties import HumanObjectProperties
from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.locationservice import LocationService
from bl_ext.blender_org.mpfb.services.rigservice import RigService
from bl_ext.blender_org.mpfb.services.targetservice import TargetService

from .matieres import teinter_objet
from .etoffes import _normaliser, etoffe_mpfb, garder_pieces, poids_de, repeser, surface_de


DONNEES = pathlib.Path(LocationService.get_user_data())

BRAS = ("upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky")
MAIN = ("hand", "thumb", "index", "middle", "ring", "pinky")
JAMBE = ("thigh", "calf", "foot", "ball")


def _alea(nom, k):
    return (zlib.crc32(f"{nom}#{k}".encode()) % 10007) / 10007


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
    # `qui` : l'homme dont la figure tire son teint, quand plusieurs rôles jouent le même.
    def __init__(self, nom, gabarit, cheveux=None, barbe=None, teinte_poils=(0.35, 0.28, 0.24), sourcils=1, qui=None):
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
        teinter_objet(self.corps, tuple(c * (0.90 + 0.14 * _alea(qui or nom, 7)) for c in g.teint))
        self.poils = []
        yeux = _asset(self.corps, "Eyes", "eyes/low-poly/low-poly.mhclo")
        teinter_objet(yeux, (1.0, 1.0, 1.0), 256)
        self.accessoires = [yeux]
        poils = [("Eyebrows", sourcils and f"eyebrows/eyebrow{sourcils:03d}/eyebrow{sourcils:03d}.mhclo"),
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
