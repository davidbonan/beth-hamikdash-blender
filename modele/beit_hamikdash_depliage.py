"""Le dépliage de chaque concept sur la couche UV COUCHE, où se cuit sa carte."""
import math
import pathlib

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from beit_hamikdash_collees import PARALLELE, RETRAIT, TOLERANCE
from beit_hamikdash_memoire import cle_de, garder, reprendre

COUCHE = "Occlusion"


def aire_uv(uv, face):
    """L'aire de la face dans le carré UV."""
    u = np.array([uv[b].uv[0] for b in face.loop_indices])
    v = np.array([uv[b].uv[1] for b in face.loop_indices])
    return 0.5 * abs(u @ np.roll(v, -1) - v @ np.roll(u, -1))


def iles(maillage, uv):
    """Chaque face avec l'île du dépliage dont elle est : ce qui se tient par une même coordonnée."""
    parent = list(range(len(maillage.polygons)))

    def racine(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    premiere = {}
    for face in maillage.polygons:
        for boucle in face.loop_indices:
            coin = (round(uv[boucle].uv[0], 6), round(uv[boucle].uv[1], 6))
            a, b = racine(face.index), racine(premiere.setdefault(coin, face.index))
            if a != b:
                parent[a] = b
    return [racine(i) for i in range(len(maillage.polygons))]


def voisines(maillage):
    """Les faces qui se touchent par une arête."""
    par_arete = {}
    for face in maillage.polygons:
        for arete in face.edge_keys:
            par_arete.setdefault(arete, []).append(face.index)
    contact = {}
    for faces in par_arete.values():
        for i in faces:
            contact.setdefault(i, set()).update(f for f in faces if f != i)
    return contact


def application_du_plan(maillage, uv, face):
    """Le dépliage du plan de `face`, en UV = q0 + M·(p − p0), prolongé hors du plan par M·n = 0."""
    sommets = [(maillage.vertices[maillage.loops[b].vertex_index].co, Vector(uv[b].uv))
               for b in face.loop_indices]
    p0, q0 = sommets[0]
    ecarts = [(p - p0, q - q0) for p, q in sommets[1:]]
    e1, d1 = max(ecarts, key=lambda e: e[0].length_squared)
    e2, d2 = max(ecarts, key=lambda e: e[0].cross(e1).length_squared)
    base = np.array([e1, e2, face.normal], dtype=np.float64).T
    if abs(np.linalg.det(base)) < 1e-12:
        return None
    return p0, q0, np.array([[d1.x, d2.x, 0.0], [d1.y, d2.y, 0.0]]) @ np.linalg.inv(base)


# Une île sous le texel n'est pas une île : la cuisson n'écrit aucun texel dedans, le noir du
# fond de l'image y reste, et c'est lui que la face lit. Il y en a des centaines par concept —
# les chanfreins, et surtout les flancs d'une figure gravée et ceux du trou que le booléen
# ouvre en face : 2,5 cm, sous le texel quelle que soit la carte, neuf cent soixante-trois pour
# la seule porte de Shushan. Elles se rabattent sur le plan de la face voisine la plus large, où
# elles s'écrasent le long de l'arête qu'elles partagent avec elle : la lumière d'un flanc
# devient celle du fond qu'il borde, ce qu'elle est de toute façon à 2,5 cm.
TEXEL_ILE_MIN = 1.0


def poser_sur_la_plus_proche(maillage, uv, orphelines, est_large):
    """Pose chaque île de `orphelines` (ses faces) au centre UV de la plus proche des faces que `est_large` retient."""
    larges = [face for face in maillage.polygons if est_large(face.index)]
    if not larges:
        return
    arbre = BVHTree.FromPolygons([sommet.co for sommet in maillage.vertices], [tuple(face.vertices) for face in larges])
    for faces in orphelines:
        centre = sum((maillage.polygons[i].center for i in faces), Vector()) / len(faces)
        hote = larges[arbre.find_nearest(centre)[2]]
        pose = sum((uv[boucle].uv for boucle in hote.loop_indices), Vector((0.0, 0.0))) / hote.loop_total
        for i in faces:
            for boucle in maillage.polygons[i].loop_indices:
                uv[boucle].uv = pose


# Plaquée dos à dos contre une autre, une face est enfermée dans le volume voisin : sa carte est noire.
def enfermees(maillage):
    arbre = BVHTree.FromPolygons([sommet.co for sommet in maillage.vertices], [tuple(face.vertices) for face in maillage.polygons])
    def couvert(face, point):
        return any(g != face.index and normale.dot(face.normal) < -PARALLELE
                   for _, normale, g, _ in arbre.find_nearest_range(point, TOLERANCE))
    # Coins compris : la contremarche d'une marche dépasse de la marche plus basse plaquée contre elle.
    return {face.index for face in maillage.polygons
            if couvert(face, face.center)
            and all(couvert(face, face.center.lerp(maillage.vertices[s].co, RETRAIT)) for s in face.vertices)}


def rabattre_les_minuscules(obj, taille, cachees):
    """Rabat sur leur voisine les îles que le dépliage laisse sous le texel.

    Une île en découvre une autre : le flanc d'une taille ne touche que son chanfrein, qui
    est minuscule lui aussi, et ne trouve le fond qu'une fois le chanfrein rabattu dessus.
    Celle qui ne touche rien de large — le montant d'un accoudoir, boîte à part — lit la face large la plus proche.
    """
    maillage = obj.data
    uv = maillage.uv_layers.active.data
    ile_de = iles(maillage, uv)
    aires, faces_de = {}, {}
    for face in maillage.polygons:
        ile = ile_de[face.index]
        aires[ile] = aires.get(ile, 0.0) + aire_uv(uv, face) * taille * taille
        faces_de.setdefault(ile, []).append(face.index)
    contact = voisines(maillage)
    minuscules = sorted(i for i, aire in aires.items() if aire < TEXEL_ILE_MIN)
    while minuscules:
        restent = []
        for ile in minuscules:
            hotes = [maillage.polygons[g] for i in faces_de[ile] for g in contact.get(i, ())
                     if aires[ile_de[g]] >= TEXEL_ILE_MIN]
            # Le chanfrein entre deux blocs jointifs touche le dos de son bloc, plus large que le flanc qu'on voit.
            hote = max([f for f in hotes if f.index not in cachees] or hotes, key=lambda f: f.area) if hotes else None
            plan = application_du_plan(maillage, uv, hote) if hote else None
            if plan is None:
                restent.append(ile)
                continue
            p0, q0, application = plan
            for i in faces_de[ile]:
                face = maillage.polygons[i]
                for boucle, sommet in zip(face.loop_indices, face.vertices):
                    uv[boucle].uv = q0 + Vector(application @ np.array(maillage.vertices[sommet].co - p0))
            accueil = ile_de[hote.index]
            aires[accueil] += aires.pop(ile)
            for i in faces_de.pop(ile):
                ile_de[i] = accueil
                faces_de[accueil].append(i)
        if len(restent) == len(minuscules):
            poser_sur_la_plus_proche(maillage, uv, [faces_de[ile] for ile in restent], lambda i: aires[ile_de[i]] >= TEXEL_ILE_MIN)
            return
        minuscules = restent


# Plus étroite, une île longue n'a parfois aucun centre de texel dedans : les facettes d'un fût cannelé cuisaient noires.
LARGEUR_ILE_MIN = 2.0


def elargir_les_etroites(obj, taille):
    """Étire en travers, jusqu'à LARGEUR_ILE_MIN texels, les îles plus étroites ; renvoie leur nombre."""
    maillage = obj.data
    uv = maillage.uv_layers.active.data
    coins = np.empty(len(uv) * 2)
    uv.foreach_get("uv", coins)
    coins = coins.reshape(-1, 2) * taille
    boucles_de, aires = {}, {}
    for face, ile in zip(maillage.polygons, iles(maillage, uv)):
        boucles_de.setdefault(ile, []).extend(face.loop_indices)
        aires[ile] = aires.get(ile, 0.0) + aire_uv(uv, face) * taille * taille
    elargies = 0
    for ile, boucles in boucles_de.items():
        if aires[ile] < TEXEL_ILE_MIN:
            continue
        ecarts = coins[boucles] - coins[boucles].mean(axis=0)
        travers = np.linalg.eigh(ecarts.T @ ecarts)[1][:, 0]
        cotes = ecarts @ travers
        largeur = np.ptp(cotes)
        if largeur >= LARGEUR_ILE_MIN:
            continue
        coins[boucles] += np.outer(cotes * (LARGEUR_ILE_MIN / largeur - 1), travers)
        elargies += 1
    uv.foreach_set("uv", (coins / taille).ravel())
    return elargies


def empaqueter(taille):
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.pack_islands(margin=2.0 / taille, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")


# La cuisson qui suit vise l'objet actif et sélectionné : il l'est, que le dépliage soit calculé ou repris.
def deplier(obj, taille):
    """Pose la couche COUCHE, active, sur `obj` et rend son rang ; le dépliage se reprend tant que le maillage et la taille n'ont pas bougé."""
    obj.data.uv_layers.active = obj.data.uv_layers.new(name=COUCHE)
    for o in bpy.context.view_layer.objects:
        o.select_set(o is obj)
    bpy.context.view_layer.objects.active = obj
    cle = cle_de([obj], [pathlib.Path(__file__)], (taille, TOLERANCE, PARALLELE, RETRAIT))
    depliage = reprendre(f"depliage/{obj.name}", cle)
    if depliage is None:
        calculer_le_depliage(obj, taille)
        uv = np.empty(len(obj.data.loops) * 2, dtype=np.float32)
        obj.data.uv_layers[COUCHE].data.foreach_get("uv", uv)
        garder(f"depliage/{obj.name}", cle, {"uv": uv})
    else:
        obj.data.uv_layers[COUCHE].data.foreach_set("uv", depliage["uv"])
    return len(obj.data.uv_layers) - 1


def calculer_le_depliage(obj, taille):
    cachees = enfermees(obj.data)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)
    # Dépliées à part : un chanfrein entre deux blocs jointifs rejoignait l'île du dos caché de son bloc.
    for part in (lambda f: f.index not in cachees, lambda f: f.index in cachees):
        maillage = bmesh.from_edit_mesh(obj.data)
        maillage.faces.ensure_lookup_table()
        for face in maillage.faces:
            face.select_set(False)
        for face in maillage.faces:
            face.select_set(part(face))
        bmesh.update_edit_mesh(obj.data)
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=2.0 / taille, area_weight=0.0)
    # L'empaquetage ne range que la sélection : les îles laissées hors d'elle se superposaient aux autres.
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    # Empaqueté d'abord : c'est l'empaquetage qui dit ce qu'une île mesure en texels.
    empaqueter(taille)
    elargies = elargir_les_etroites(obj, taille)
    if elargies:
        empaqueter(taille)
        print(f"  îles étroites élargies : {obj.name:26s} {elargies}", flush=True)
    # Le rabattage vient APRÈS l'empaquetage, et rien ne le suit : c'est l'empaquetage qui fixe
    # l'échelle, donc ce qu'une île mesure en texels, et une île rabattue est plate en UV —
    # réempaqueter derrière, l'atlas entier s'effondrait sur une île d'un texel.
    rabattre_les_minuscules(obj, taille, cachees)
