"""$BLENDER -b beit_hamikdash.blend -P beit_hamikdash_plan.py [-- id id…] — rend le plan de la visite vu du dessus."""
import json
import math
import pathlib
import sys

import bpy

DOSSIER = pathlib.Path(bpy.data.filepath).resolve().parent / "visite"
LONG_COTE = 1600          # px sur le plus grand côté d'une image
HAUTEUR_CAMERA = 400.0    # m : au-dessus des collines du pays
QUALITE_WEBP = 82
LOOK = "AgX - Medium High Contrast"   # vue d'avion, le calcaire sous AgX neutre tourne à l'aplat gris

# En mètres, dans le repère du glb : x vers l'est, z vers le sud. `coupe` : hauteur où la caméra tranche.
# `lieux` : ce que la coupe montre, quand les emprises seules ne le disent pas.
CADRAGES = [
    dict(id="har_habayit", x=(-134.0, 111.0), z=(-95.0, 150.0)),
    dict(id="ezrat_nashim", x=(-4.0, 74.0), z=(-38.0, 38.0)),
    dict(id="azara", x=(-95.0, 5.0), z=(-51.0, 44.0)),
    # À hauteur d'œil au-dessus du sol du Beit : plus haut, la coupe tombe dans les planchers des ta'im.
    dict(id="heikhal", x=(-88.0, -33.0), z=(-27.0, 27.0), coupe=4.5,
         lieux=["oulam", "heikhal", "kodesh_hakodashim", "taim", "mesiba", "douze_marches_oulam"]),
    # Sous le dessus du Heil (-4,8 m). `caches` : préfixes des massifs pleins — sol, podium, terrasses du Heil
    # et relief du pays dessous — qui couvriraient les tunnels ; sans eux ils restent sur fond transparent.
    # `plancher` : rien n'est rendu plus bas, juste sous le sol des tunnels. `dessous` : le plan, pâli, qui les situe.
    dict(id="sous_terrain", x=(-95.0, 5.0), z=(-51.0, 44.0), coupe=-6.0, plancher=-8.0, dessous="azara",
         caches=["HarHabayit_sol", "Podium_", "Heil_", "Pays_"],
         lieux=["mesiba_bira", "beit_hatevila", "shit", "beit_hamoked"]),
]


def objets_prefixes(prefixes):
    return [o for o in bpy.data.objects if prefixes and o.name.startswith(tuple(prefixes))]


def camera_du_dessus(scene):
    # Les plans du film lient leur caméra à un repère de la timeline : au rendu, le repère l'emporterait sur `scene.camera`.
    for repere in scene.timeline_markers:
        repere.camera = None
    donnees = bpy.data.cameras.new("Plan")
    donnees.type = "ORTHO"
    camera = bpy.data.objects.new("Plan", donnees)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


# Lumière de carte : haute et venue du nord-ouest, pour que le relief se lise en creux et en saillie.
def soleil_de_carte():
    soleil = next(o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN")
    soleil.rotation_euler = (math.radians(40), 0.0, math.radians(225))
    return soleil


def rendre(scene, camera, soleil, cadrage):
    largeur, hauteur = cadrage["x"][1] - cadrage["x"][0], cadrage["z"][1] - cadrage["z"][0]
    pixels_par_metre = LONG_COTE / max(largeur, hauteur)
    rendu = scene.render
    rendu.resolution_x, rendu.resolution_y = round(largeur * pixels_par_metre), round(hauteur * pixels_par_metre)
    rendu.resolution_percentage = 100
    centre_x, centre_z = sum(cadrage["x"]) / 2, sum(cadrage["z"]) / 2
    camera.data.ortho_scale = max(largeur, hauteur)
    camera.location = (centre_x, -centre_z, HAUTEUR_CAMERA)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    coupe = cadrage.get("coupe")
    camera.data.clip_start = HAUTEUR_CAMERA - coupe if coupe is not None else 0.1
    plancher = cadrage.get("plancher")
    camera.data.clip_end = HAUTEUR_CAMERA - plancher if plancher is not None else HAUTEUR_CAMERA + 150.0
    # Tranchée, la toiture resterait dans la carte d'ombre et plongerait la coupe dans le noir.
    soleil.data.use_shadow = coupe is None
    caches = objets_prefixes(cadrage.get("caches", []))
    for objet in caches:
        objet.visible_camera = False
    rendu.film_transparent = bool(caches)
    rendu.image_settings.file_format = "WEBP"
    rendu.image_settings.color_mode = "RGBA" if caches else "RGB"
    rendu.image_settings.quality = QUALITE_WEBP
    rendu.filepath = str(DOSSIER / "plans" / f"{cadrage['id']}.webp")
    bpy.ops.render.render(write_still=True)
    for objet in caches:
        objet.visible_camera = True
    demi_x, demi_z = rendu.resolution_x / pixels_par_metre / 2, rendu.resolution_y / pixels_par_metre / 2
    sortie = dict(id=cadrage["id"], image=f"plans/{cadrage['id']}.webp",
                  min=[centre_x - demi_x, centre_z - demi_z], max=[centre_x + demi_x, centre_z + demi_z])
    for clef in ("coupe", "lieux", "dessous"):
        if clef in cadrage:
            sortie[clef] = cadrage[clef]
    return sortie


def main():
    voulus = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    scene = bpy.context.scene
    scene.view_settings.look = LOOK
    (DOSSIER / "plans").mkdir(exist_ok=True)
    camera, soleil = camera_du_dessus(scene), soleil_de_carte()
    chemin = DOSSIER / "plan.json"
    anciens = {c["id"]: c for c in json.loads(chemin.read_text())["cadrages"]} if chemin.exists() else {}
    for cadrage in CADRAGES:
        if voulus and cadrage["id"] not in voulus:
            continue
        anciens[cadrage["id"]] = rendre(scene, camera, soleil, cadrage)
        print(f"plan {cadrage['id']} · {scene.render.resolution_x} × {scene.render.resolution_y}")
    ordre = [c["id"] for c in CADRAGES]
    cadrages = sorted(anciens.values(), key=lambda c: ordre.index(c["id"]))
    chemin.write_text(json.dumps({"cadrages": cadrages}, ensure_ascii=False, indent=2))


main()
