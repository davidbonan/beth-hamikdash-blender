"""Blender -b -P beit_hamikdash_perifa.py — écrit perifa.blend : le coin replié d'une parokhet.

« פְּרוּפָה — רֹאשָׁהּ כְּפוּלָה לְצַד הַחוּץ וְנֶאֱחֶזֶת בְּקֶרֶס שֶׁל זָהָב לִהְיוֹת פְּתוּחָה וְעוֹמֶדֶת »
(Rashi Yoma 52b) : le coin est relevé par-dessus l'étoffe, vers l'extérieur, et accroché. Le
repli est simulé en tissu : le coin est tiré jusqu'au keres, la pesanteur et la raideur d'une
étoffe d'un tefa'h font le pli, le creux du rabat et les plis de tension. Seul le coin est
simulé ; ses bords côté rideau restent épinglés dans le plan, où le blockout raccorde l'étoffe plate.

Repère du coin, en mètres : x depuis le mur le long du rideau, y vers le côté où le coin se
rabat (l'est), z depuis le sol. Le maillage est déjà épaissi d'un tefa'h, centré sur y = 0.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_perifa.py
"""
import math
import pathlib

import bpy
from mathutils import Vector

SORTIE = pathlib.Path(__file__).resolve().parent / "perifa.blend"
AMA = 0.48
EPAISSEUR = AMA / 6                     # עָבְיָהּ טֶפַח (Shekalim 8:5)
LARGEUR, HAUTEUR = 20 * AMA, 24 * AMA   # toute la largeur du rideau, sur 24 de ses 40 amot ;
                                        # au-dessus il pend à plat, et la couture s'y voit de moins loin
PAS = 0.10
PLI_SOL, PLI_MUR = 3.5, 14.0            # amot : le pli va du sol, à 3,5 amot du mur, au mur à 14 de haut — CHOIX
_PIED = Vector((1 / PLI_SOL, 1 / PLI_MUR)) / (1 / PLI_SOL ** 2 + 1 / PLI_MUR ** 2)
KERES = tuple(2 * AMA * c for c in _PIED)   # le coin retourné par-dessus le pli : un repli sans mou
TIRAGE, REPOS = 80, 100                 # images : le coin monte au keres, puis l'étoffe se pose


def nappe():
    """Grille à plat dans le plan du rideau ; le groupe `epingle` tient les bords côté
    rideau et le coin, que le crochet emporte."""
    nx, nz = round(LARGEUR / PAS), round(HAUTEUR / PAS)
    sommets = [(i * LARGEUR / nx, 0.0, k * HAUTEUR / nz) for k in range(nz + 1) for i in range(nx + 1)]
    faces = [(k * (nx + 1) + i, k * (nx + 1) + i + 1, (k + 1) * (nx + 1) + i + 1, (k + 1) * (nx + 1) + i)
             for k in range(nz) for i in range(nx)]
    me = bpy.data.meshes.new("Perifa_nappe")
    me.from_pydata(sommets, [], faces)
    o = bpy.data.objects.new("Perifa_nappe", me)
    bpy.context.scene.collection.objects.link(o)
    epingle = o.vertex_groups.new(name="epingle")
    # tiennent : le haut, le mur d'en face, et l'ourlet posé au sol — sauf sous le repli,
    # où le rideau doit pouvoir se relever. Le reste ne bouge pas : l'étoffe est lourde et plate.
    bord = [v.index for v in me.vertices
            if v.co.x > LARGEUR - 1.5 * PAS or v.co.z > HAUTEUR - 1.5 * PAS
            or (v.co.z < 1.5 * PAS and v.co.x > PLI_SOL * AMA)]
    epingle.add(bord, 1.0, 'REPLACE')
    coin = o.vertex_groups.new(name="coin")
    coin.add([0], 1.0, 'REPLACE')
    epingle.add([0], 1.0, 'REPLACE')
    return o


def crochet(o):
    """Le coin suit un vide qui l'emporte en arc par-dessus l'étoffe jusqu'au keres."""
    vide = bpy.data.objects.new("Keres", None)
    bpy.context.scene.collection.objects.link(vide)
    for f in range(1, TIRAGE + 1):
        t = (f - 1) / (TIRAGE - 1)
        s = 0.5 - 0.5 * math.cos(math.pi * t)
        vide.location = (KERES[0] * s, 0.15 * math.sin(math.pi * s) + EPAISSEUR * s,
                         KERES[1] * s + 1.5 * math.sin(math.pi * s))
        vide.keyframe_insert("location", frame=f)
    h = o.modifiers.new("Crochet", 'HOOK')
    h.object = vide
    h.vertex_group = "coin"
    h.center = (0, 0, 0)


ECART = 0.32     # m : de la nappe au rideau voisin, l'ama de Traksin moins les deux demi-tefa'him


def obstacles(voisin):
    """Le sol, le mur où le rideau finit, et le rideau voisin — à l'ouest pour l'extérieure,
    à l'est pour l'intérieure : l'étoffe qui ballonne vers l'ama de Traksin s'y appuie."""
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.01))
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.51, 0, HAUTEUR / 2), scale=(1, 20, HAUTEUR + 2))
    bpy.ops.mesh.primitive_cube_add(size=1, location=(LARGEUR / 2, voisin * (ECART + 0.5), HAUTEUR / 2),
                                    scale=(4 * LARGEUR, 1.0, 2 * HAUTEUR))
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and o.name != "Perifa_nappe":
            o.modifiers.new("Collision", 'COLLISION')
            o.collision.thickness_outer = 0.01


def etoffe(o):
    c = o.modifiers.new("Tissu", 'CLOTH').settings
    c.quality = 12
    c.mass = 2.5
    c.air_damping = 1.0
    c.tension_stiffness = c.compression_stiffness = 60
    c.shear_stiffness = 40
    c.bending_stiffness = 60.0
    c.tension_damping = c.compression_damping = 10
    c.bending_damping = 2.0
    c.vertex_group_mass = "epingle"
    co = o.modifiers["Tissu"].collision_settings
    co.use_collision = True
    co.distance_min = EPAISSEUR / 2
    co.use_self_collision = True
    co.self_distance_min = EPAISSEUR / 2
    co.self_friction = 5
    o.modifiers["Tissu"].point_cache.frame_start = 1
    o.modifiers["Tissu"].point_cache.frame_end = TIRAGE + REPOS


def _cuire(o):
    """Joue la simulation image par image : en arrière-plan, rien ne l'avance tout seul."""
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, TIRAGE + REPOS
    for f in range(1, TIRAGE + REPOS + 1):
        scene.frame_set(f)
    return bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))


def keres(coin, normale):
    """L'anneau d'or qui prend les deux épaisseurs à la pointe du repli : son plan est celui
    de la normale et de la verticale, donc il traverse l'étoffe."""
    axe = normale.cross(Vector((0, 0, 1)))
    axe = axe.normalized() if axe.length > 1e-6 else Vector((1, 0, 0))
    bpy.ops.mesh.primitive_torus_add(major_radius=1.6 * EPAISSEUR, minor_radius=0.25 * EPAISSEUR,
                                     major_segments=24, minor_segments=8, location=coin,
                                     rotation=Vector((0, 0, 1)).rotation_difference(axe).to_euler())
    anneau = bpy.context.object
    me = bpy.data.meshes.new_from_object(anneau.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    me.transform(anneau.matrix_world)
    me.name = "Perifa_keres"
    me.shade_smooth()
    bpy.data.objects.remove(anneau)
    return me


def epaissir(o):
    """L'étoffe posée reçoit son tefa'h d'épaisseur, de part et d'autre de la nappe simulée."""
    epais = o.modifiers.new("Tefah", 'SOLIDIFY')
    epais.thickness = EPAISSEUR
    epais.offset = 0.0
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    me.name = "Perifa"
    me.shade_smooth()
    return me


def parokhet(nom, voisin):
    """Cuit un coin : `voisin` dit de quel côté l'autre parokhet barre l'ama de Traksin."""
    o = nappe()
    crochet(o)
    etoffe(o)
    obstacles(voisin)
    pose = _cuire(o)
    coin, normale = pose.vertices[0].co.copy(), pose.vertices[0].normal.copy()
    anneau = keres(coin, normale)
    anneau.name = f"Perifa_{nom}_keres"
    bpy.data.meshes.remove(pose)
    me = epaissir(o)
    me.name = f"Perifa_{nom}"
    for reste in list(bpy.context.scene.objects):
        bpy.data.objects.remove(reste)
    bpy.context.scene.frame_set(1)
    ys = [v.co.y for v in me.vertices]
    print(f"Perifa {nom} : {len(me.polygons)} faces, débord de {min(ys):.2f} à {max(ys):.2f} m ; "
          f"keres à x = {coin.x / AMA:.2f}, z = {coin.z / AMA:.2f} amot")
    return me, anneau


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sorties = set()
    for nom, voisin in (("ext", -1), ("int", +1)):
        sorties.update(parokhet(nom, voisin))
    bpy.data.libraries.write(str(SORTIE), sorties, fake_user=True, compress=True)
    print(f"écrit {SORTIE}")


if __name__ == "__main__":
    main()
