import bmesh
import bpy
import numpy as np

import beit_hamikdash_gestes as G

from .corps import BRAS
from .cuisson import COTE, Plateau, cuire, ecrire, image_a_cuire, pixels

# La kutonet ceinte est plus large que le corps : tenue aux épaules et à l'avnet, son ampleur retombe en plis.
AMPLEUR_A_LA_CEINTURE = 1.40
AMPLEUR_A_L_OURLET = 1.06
AMPLEUR_BLOUSE = 1.20
NIVEAUX = 1
IMAGES_DE_CHUTE = 48
PORTEE_DU_CREUX = 0.12
PENTE_MAX = 0.35
CREUX_MIN = 0.70

_plis = {}


def _poids_bras(objet):
    noms = {g.index: g.name for g in objet.vertex_groups}
    return np.array([sum(e.weight for e in v.groups if noms[e.group].startswith(BRAS)) for v in objet.data.vertices])


def _subdiviser(robe):
    copie = robe.copy()
    copie.data = robe.data.copy()
    copie.name = f"{robe.name}_plisse"
    for c in robe.users_collection:
        c.objects.link(copie)
    copie.modifiers.clear()
    division = copie.modifiers.new("division", "SUBSURF")
    division.levels = division.render_levels = NIVEAUX
    division.boundary_smooth = "PRESERVE_CORNERS"
    graphe = bpy.context.evaluated_depsgraph_get()
    fine = bpy.data.meshes.new_from_object(copie.evaluated_get(graphe), preserve_all_data_layers=True, depsgraph=graphe)
    copie.modifiers.clear()
    ancienne, copie.data = copie.data, fine
    bpy.data.meshes.remove(ancienne)
    # Les pans de la robe sont cousus bord à bord : soudés, la couture du dos ne s'ouvre pas en tombant.
    bm = bmesh.new()
    bm.from_mesh(fine)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=5e-4)
    bm.to_mesh(fine)
    bm.free()
    return copie


# Fronces serrées sous l'avnet, l'ourlet presque à sa largeur : plus ample en bas, la jupe s'évaserait au lieu de plisser.
def _ampleur_a(z, z_ceinture, z_bas, z_haut):
    if z >= z_ceinture:
        return 1.0 + (AMPLEUR_BLOUSE - 1.0) * (1.0 - (z - z_ceinture) / (z_haut - z_ceinture))
    t = (z_ceinture - z) / (z_ceinture - z_bas)
    return AMPLEUR_A_L_OURLET + (AMPLEUR_A_LA_CEINTURE - AMPLEUR_A_L_OURLET) * (1.0 - t) ** 2


# Clés de forme : la robe telle qu'ajustée (« Basis »), et la même élargie autour de l'axe du corps, longueurs de repos du tissu.
def _ampleur(humain, ceinture, drape):
    h = humain
    passage = h.rig.matrix_world.inverted() @ drape.matrix_world
    retour = passage.inverted()
    bras = _poids_bras(drape)
    drape.shape_key_add(name="Basis")
    ample = drape.shape_key_add(name="ample")
    epingles = drape.vertex_groups.new(name="epingles")
    hauteurs = [(passage @ v.co).z for v in drape.data.vertices]
    z_bas, z_haut = min(hauteurs), max(hauteurs)
    for v, part_bras in zip(drape.data.vertices, bras):
        p = passage @ v.co
        facteur = 1.0 + (1.0 - min(part_bras / 0.5, 1.0)) * (_ampleur_a(p.z, ceinture.z, z_bas, z_haut) - 1.0)
        q = p.copy()
        q.x *= facteur
        q.y = ceinture.cy + (p.y - ceinture.cy) * facteur
        ample.data[v.index].co = retour @ q
        tenu = max(G.lisse(1.0 - (z_haut - p.z) / 0.04), G.lisse(1.0 - (abs(p.z - ceinture.z) - ceinture.largeur / 2) / 0.015))
        if tenu > 0.0:
            epingles.add([v.index], tenu, "REPLACE")
    return epingles


def _laisser_tomber(humain, drape, epingles):
    h = humain
    tissu = drape.modifiers.new("tissu", "CLOTH")
    reglage = tissu.settings
    reglage.quality = 10
    reglage.mass = 0.18
    reglage.tension_stiffness = 15.0
    reglage.compression_stiffness = 0.5
    reglage.shear_stiffness = 2.0
    reglage.bending_stiffness = 0.08
    reglage.air_damping = 3.0
    reglage.vertex_group_mass = epingles.name
    reglage.pin_stiffness = 4.0
    reglage.rest_shape_key = drape.data.shape_keys.key_blocks["ample"]
    contact = tissu.collision_settings
    contact.collection = h.obstacle("corps", h.visible)
    contact.distance_min = 0.006
    contact.collision_quality = 4
    contact.use_self_collision = True
    contact.self_distance_min = 0.004
    tissu.point_cache.frame_start, tissu.point_cache.frame_end = 1, IMAGES_DE_CHUTE
    scene = bpy.context.scene
    for image in range(1, IMAGES_DE_CHUTE + 1):
        scene.frame_set(image)
    graphe = bpy.context.evaluated_depsgraph_get()
    tombee = bpy.data.meshes.new_from_object(drape.evaluated_get(graphe), depsgraph=graphe)
    derive = max((a.co - b.co).length for a, b in zip(drape.data.vertices, tombee.vertices))
    if derive > 0.5:
        raise RuntimeError(f"{drape.name} : la chute du tissu a divergé ({derive:.2f} m)")
    drape.modifiers.remove(tissu)
    drape.shape_key_clear()
    ancienne, drape.data = drape.data, tombee
    bpy.data.meshes.remove(ancienne)
    scene.frame_set(1)


def _lire(image):
    if image.size[0] != COTE:
        image = image.copy()
        image.scale(COTE, COTE)
    return pixels(image)


# Les normales du tissage posées sur celles des plis (« whiteout »), en espace tangent.
def _superposer(plis, tissage):
    a, b = plis[..., :3] * 2.0 - 1.0, tissage[..., :3] * 2.0 - 1.0
    # Plus couchée que ça, la normale vient d'un pan voisin que le rayon a touché à la place du sien : droite.
    a = np.where(a[..., 2:3] < PENTE_MAX, np.array([0.0, 0.0, 1.0]), a)
    n = np.dstack([a[..., 0] + b[..., 0], a[..., 1] + b[..., 1], a[..., 2] * b[..., 2]])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def _cuire_les_plis(humain, robe, drape):
    h = humain
    abords = [o for o in h.rig.children if o.type == "MESH" and o not in (robe, drape)]
    normales, creux = image_a_cuire("plis_normales", (0.5, 0.5, 1.0, 1.0)), image_a_cuire("plis_creux", (1.0, 1.0, 1.0, 1.0))
    with Plateau([drape, robe, *abords], PORTEE_DU_CREUX):
        cuire("NORMAL", robe, normales, [drape], use_selected_to_active=True, cage_extrusion=0.04,
               max_ray_distance=0.08, normal_space="TANGENT")
        # Le creux d'un pli seulement : les jambes sous la jupe noircissaient l'envers des pans.
        for o in (robe, h.corps):
            o.hide_render = True
        cuire("AO", drape, creux, [])
        for o in (robe, h.corps):
            o.hide_render = False
    return pixels(normales), pixels(creux)[..., 0]


def _matiere_plissee(robe, normales, creux):
    base = robe.data.materials[0]
    mat = base.copy()
    mat.name = f"{base.name}_Ceinte"
    arbre = mat.node_tree
    bsdf = next(n for n in arbre.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    carte = next(lien.from_node for lien in bsdf.inputs["Normal"].links[0].from_node.inputs["Color"].links)
    teinte = next(lien.from_node for lien in bsdf.inputs["Base Color"].links)
    tissage = _lire(carte.image)
    carte.image = ecrire(f"{mat.name}_normales", _superposer(normales, tissage), True)
    couleur = _lire(teinte.image)[..., :3]
    teinte.image = ecrire(f"{mat.name}_couleur", couleur * (CREUX_MIN + (1.0 - CREUX_MIN) * creux[..., None]), False)
    return mat


# La kutonet tombe une fois, sur le premier cohen qui la porte ceinte ; les autres en reçoivent les plis par ses UV.
def plisser(humain, robe, ceinture):
    base = robe.data.materials[0]
    if base.name not in _plis:
        drape = _subdiviser(robe)
        epingles = _ampleur(humain, ceinture, drape)
        _laisser_tomber(humain, drape, epingles)
        normales, creux = _cuire_les_plis(humain, robe, drape)
        bpy.data.objects.remove(drape)
        _plis[base.name] = _matiere_plissee(robe, normales, creux)
    robe.data.materials[0] = _plis[base.name]
