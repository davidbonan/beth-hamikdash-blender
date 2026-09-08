"""Pose dans la scène les caméras déclarées dans `cameras.json`.

    /Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
        -P beit_hamikdash_blockout.py -P beit_hamikdash_cameras.py

Le blockout bâtit le Temple et rien d'autre : aucune caméra n'y est écrite. Les
plans vivent dans `cameras.json`, à côté du .blend, parce qu'un plan est ce que
l'utilisateur veut filmer et non une propriété du bâtiment — et parce qu'un fichier
de données se relit, se versionne et se corrige sans toucher aux 3 000 lignes du
blockout.

Une caméra y est un couple de courses, en amot : celle de l'objectif, celle de son
point de visée. Chacune est une liste de points — un seul point ne bouge pas, deux
donnent une droite, plus donnent une polyligne (orbite, courbe de grue). Les
keyframes sont posées à pas de temps constant, en interpolation linéaire : la vitesse
est celle qu'annonce la course, sans accélération parasite.

Ce sont les deux frames extrêmes de chaque plan qui partent ensuite à l'i2v ; leur
recouvrement se mesure avec `beit_hamikdash_analyse_plans.py`.

Rejouable : les caméras, leurs cibles et leurs marqueurs sont effacés avant d'être
rebâtis. Le script ne sauvegarde pas le .blend — c'est l'export qui le fait.
"""

import json
import os

import bpy

FICHIER = "cameras.json"
COLLECTION = "90_Cameras"
CAPTEUR = 36.0      # mm, plein format : c'est ce capteur qui donne son sens à la focale
CLIP_FIN = 5000.0   # m ; le pays va jusqu'à six mille amot de l'origine


def chemin_du_fichier():
    return os.path.join(os.path.dirname(bpy.data.filepath), FICHIER)


def declarations():
    chemin = chemin_du_fichier()
    if not os.path.exists(chemin):
        raise SystemExit(f"{chemin} absent : aucune caméra à poser.")
    with open(chemin, encoding="utf-8") as fichier:
        return json.load(fichier)["cameras"]


# --- scène --------------------------------------------------------------------

def collection():
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
        bpy.context.scene.collection.children.link(col)
    return col


def effacer(scene):
    """Toute caméra, toute cible de caméra, tout marqueur : le script est la source."""
    for marqueur in list(scene.timeline_markers):
        scene.timeline_markers.remove(marqueur)
    col = bpy.data.collections.get(COLLECTION)
    for objet in list(col.objects) if col else []:
        bpy.data.objects.remove(objet, do_unlink=True)
    for objet in list(bpy.data.objects):
        if objet.type == "CAMERA":
            bpy.data.objects.remove(objet, do_unlink=True)


def poser(objet, col):
    for ancienne in objet.users_collection:
        ancienne.objects.unlink(objet)
    col.objects.link(objet)
    return objet


def courbes(objet):
    """F-curves de l'action. Blender < 4.4 : action.fcurves ; >= 4.4 : actions à slots."""
    animation = objet.animation_data
    action = animation.action if animation else None
    if action is None:
        return []
    if hasattr(action, "fcurves"):
        return action.fcurves
    slot = animation.action_slot
    for couche in action.layers:
        for bande in couche.strips:
            sac = bande.channelbag(slot) if slot else None
            if sac:
                return sac.fcurves
    return []


def parcourir(objet, points, f0, f1, ama):
    """Un keyframe par point, à pas de temps constant, en interpolation linéaire."""
    dernier = len(points) - 1
    for rang, point in enumerate(points):
        objet.location = tuple(c * ama for c in point)
        objet.keyframe_insert("location",
                              frame=f0 if dernier == 0 else round(f0 + (f1 - f0) * rang / dernier))
    for courbe in courbes(objet):
        for keyframe in courbe.keyframe_points:
            keyframe.interpolation = "LINEAR"


def batir(scene, declaration, f0, ama, col):
    nom = declaration["nom"]
    duree = declaration["duree_s"]
    f1 = f0 + int(round(duree * scene.render.fps)) - 1

    cible = bpy.data.objects.new(f"{nom}_cible", None)
    cible.empty_display_size = 0.5 / ama
    poser(cible, col)

    donnees = bpy.data.cameras.new(nom)
    donnees.lens = declaration["focale"]
    donnees.sensor_width = declaration.get("capteur", CAPTEUR)
    donnees.clip_end = declaration.get("clip_fin", CLIP_FIN)
    cam = bpy.data.objects.new(nom, donnees)
    poser(cam, col)

    contrainte = cam.constraints.new("TRACK_TO")
    contrainte.target = cible
    contrainte.track_axis = "TRACK_NEGATIVE_Z"
    contrainte.up_axis = "UP_Y"

    parcourir(cam, declaration["camera"], f0, f1, ama)
    parcourir(cible, declaration["cible"], f0, f1, ama)

    marqueur = scene.timeline_markers.new(nom, frame=f0)
    marqueur.camera = cam
    cam["duree_s"] = duree
    cam["frame_debut"] = f0
    cam["frame_fin"] = f1
    return cam, f1


def main():
    scene = bpy.context.scene
    ama = scene["AMA_metres"]
    col = collection()
    effacer(scene)

    frame = 1
    scene.frame_start = 1
    for declaration in declarations():
        cam, frame = batir(scene, declaration, frame, ama, col)
        print(f"  {cam.name:34s} {cam.data.lens:>4.0f} mm  "
              f"frames {cam['frame_debut']}..{cam['frame_fin']}", flush=True)
        frame += 1

    scene.frame_end = max(1, frame - 1)
    scene.frame_set(1)
    premiere = next((mk.camera for mk in sorted(scene.timeline_markers, key=lambda m: m.frame)), None)
    if premiere:
        scene.camera = premiere
    print(f"{len(col.objects) // 2} caméras posées, {scene.frame_end} images "
          f"à {scene.render.fps} fps ({scene.frame_end / scene.render.fps:.0f} s).", flush=True)


main()
