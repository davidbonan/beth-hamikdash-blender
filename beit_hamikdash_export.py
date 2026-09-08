"""Exporte la première et la dernière image de chaque plan : planche, ou production.

    # planche de contrôle, 640 x 360 + index HTML
    /Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
        -P beit_hamikdash_blockout.py -P beit_hamikdash_cameras.py \
        -P beit_hamikdash_export.py -- --planche

    # fichiers de production : couleur + profondeur, 1920 x 1080
    /Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
        -P beit_hamikdash_blockout.py -P beit_hamikdash_cameras.py \
        -P beit_hamikdash_export.py

    # un ou plusieurs plans seulement
    ... -P beit_hamikdash_export.py -- CAM_03_Heikhal

Les plans exportés sont ceux que porte la scène — ceux de cameras.json, posés par
beit_hamikdash_cameras.py — dans l'ordre de la timeline. Le script n'en tient aucune
liste à lui, et les deux sorties viennent du même script : dupliquée, une liste
dérive, et la planche a déjà annoncé un plan en 50 mm quand la scène était passée
à 85.

Les fichiers portent le nom de la caméra : `renders/blockout/<caméra>_debut.png`,
`_fin.png` et leurs `_profondeur.png`. C'est ce que les scripts fal vont chercher.

La carte de profondeur est normalisée 0-1, proche = blanc (convention ControlNet
Depth). L'échelle est logarithmique : sur ces plans, un dégradé linéaire en mètres
aplatit tout le proche (paroi de l'Oulam à 8 m contre ouverture à 44 m) et une
disparité 1/z écrase tout le lointain (intérieur du Heikhal à 15-26 m, kelim
noyés). Le log garde du contraste aux deux bouts. La plage proche/lointain est
mesurée sur la passe Z elle-même, rendue en EXR dans le dossier temporaire de
Blender : aucun pixel n'est écrêté.

Rejouable : le script reconstruit ses groupes de compositing et remesure les plages
à chaque lancement, puis sauvegarde le .blend.
"""

import math
import os
import sys

import bpy
import numpy as np

DOSSIER = "renders"
SOUS_DOSSIER_BLOCKOUT = "blockout"   # rendus Blender 1920 x 1080 qui nourrissent l'i2i
SOUS_DOSSIER_PLANCHE = "planche"     # planche de contrôle 640 x 360
LARGEUR, HAUTEUR = 1920, 1080
LARGEUR_PLANCHE, HAUTEUR_PLANCHE = 640, 360
MARGE = 0.02             # 2 % de part et d'autre : évite de saturer les extrêmes

GROUPE_COULEUR = "Comp_Couleur"
GROUPE_PROFONDEUR = "Comp_Profondeur"
GROUPE_Z = "Comp_Z_mesure"
NOEUD_PLAGE = "Plage_profondeur"


# --- ligne de commande --------------------------------------------------------

def arguments():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def cameras_de_la_scene(scene):
    """Les caméras dans l'ordre de la timeline, pas dans celui de bpy.data."""
    marqueurs = sorted((mk for mk in scene.timeline_markers if mk.camera),
                       key=lambda mk: mk.frame)
    return [mk.camera.name for mk in marqueurs]


def cameras_demandees(scene, args):
    connues = cameras_de_la_scene(scene)
    if not connues:
        raise SystemExit("Aucune caméra dans la scène : lancer beit_hamikdash_cameras.py "
                         "avant l'export.")
    nommees = [a for a in args if not a.startswith("--")]
    for nom in nommees:
        if nom not in connues:
            raise SystemExit(f"Plan inconnu : {nom}. Connus : {', '.join(connues)}")
    return nommees or connues


def masquer(nom_collection, cacher):
    collection = bpy.data.collections.get(nom_collection)
    if collection:
        collection.hide_render = cacher


# --- compositing --------------------------------------------------------------

def nouveau_groupe(nom):
    ancien = bpy.data.node_groups.get(nom)
    if ancien:
        bpy.data.node_groups.remove(ancien)
    groupe = bpy.data.node_groups.new(nom, "CompositorNodeTree")
    # Sans utilisateur factice, un groupe inactif est purgé à la sauvegarde du .blend.
    groupe.use_fake_user = True
    groupe.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    return groupe


def groupe_passe(scene, nom, passe):
    """Une passe de Render Layers, telle quelle, vers la sortie de la scène."""
    groupe = nouveau_groupe(nom)
    couches = groupe.nodes.new("CompositorNodeRLayers")
    couches.scene = scene
    couches.location = (-400, 0)
    sortie = groupe.nodes.new("NodeGroupOutput")
    sortie.location = (0, 0)
    groupe.links.new(couches.outputs[passe], sortie.inputs[0])
    return groupe


def groupe_profondeur(scene):
    """Z (mètres) -> log10(z) -> 0-1 sur la plage du frame, proche = blanc."""
    groupe = nouveau_groupe(GROUPE_PROFONDEUR)
    couches = groupe.nodes.new("CompositorNodeRLayers")
    couches.scene = scene
    couches.location = (-600, 0)
    logarithme = groupe.nodes.new("ShaderNodeMath")
    logarithme.operation = "LOGARITHM"
    logarithme.inputs[1].default_value = 10.0
    logarithme.location = (-380, 0)
    plage = groupe.nodes.new("ShaderNodeMapRange")
    plage.name = plage.label = NOEUD_PLAGE
    plage.clamp = True
    plage.location = (-160, 0)
    plage.inputs["To Min"].default_value = 1.0   # proche = blanc
    plage.inputs["To Max"].default_value = 0.0   # lointain (et fond) = noir
    sortie = groupe.nodes.new("NodeGroupOutput")
    sortie.location = (100, 0)
    groupe.links.new(couches.outputs["Depth"], logarithme.inputs[0])
    groupe.links.new(logarithme.outputs[0], plage.inputs["Value"])
    groupe.links.new(plage.outputs["Result"], sortie.inputs[0])
    return groupe


def regler_plage(groupe, proche, lointain):
    plage = groupe.nodes[NOEUD_PLAGE]
    plage.inputs["From Min"].default_value = math.log10(proche)
    plage.inputs["From Max"].default_value = math.log10(lointain)


# --- rendu --------------------------------------------------------------------

def preparer_sortie(scene, largeur, hauteur):
    rendu = scene.render
    rendu.resolution_x, rendu.resolution_y, rendu.resolution_percentage = largeur, hauteur, 100
    rendu.use_file_extension = True
    scene.view_layers[0].use_pass_z = True


def format_png(scene):
    reglages = scene.render.image_settings
    reglages.file_format = "PNG"
    reglages.color_mode = "RGB"
    reglages.color_depth = "8"


def format_exr(scene):
    reglages = scene.render.image_settings
    reglages.file_format = "OPEN_EXR"
    reglages.color_mode = "RGB"
    reglages.color_depth = "32"


def rendre(scene, groupe, transformation, chemin):
    scene.compositing_node_group = groupe
    scene.view_settings.view_transform = transformation
    scene.render.filepath = chemin
    bpy.ops.render.render(write_still=True)


def rendre_donnees(scene, groupe, chemin):
    """Rendu de données : aucune transformation d'affichage, et un seul échantillon.

    La passe Z ne dépend pas de l'échantillonnage — mais sous Cycles (`--cycles` au
    blockout) elle serait payée au prix des 128 échantillons de l'image couleur, deux
    fois par frame.
    """
    echantillons = scene.cycles.samples if scene.render.engine == "CYCLES" else None
    if echantillons is not None:
        scene.cycles.samples = 1
    try:
        rendre(scene, groupe, "Raw", chemin)
    finally:
        if echantillons is not None:
            scene.cycles.samples = echantillons


def valeurs_rouge(chemin):
    image = bpy.data.images.load(chemin)
    image.colorspace_settings.name = "Non-Color"
    largeur, hauteur = image.size
    canaux = image.channels
    tampon = np.empty(largeur * hauteur * canaux, dtype=np.float32)
    image.pixels.foreach_get(tampon)
    bpy.data.images.remove(image)
    return tampon[0::canaux]


PAYS = "01_Pays"   # collines, ville et oliviers : jusqu'à six mille amot de l'origine


def plage_z(scene, groupe_z):
    """(proche, lointain) en mètres, mesurés sur la passe Z du frame courant.

    Le pays est masqué le temps de la mesure : à trois kilomètres, il tirait la borne
    lointaine des plans 1, 1b, 14b et 15 hors du Temple, et l'échelle log n'y laissait
    plus qu'un cinquième de sa plage. Il reste dans la carte, écrêté au noir du fond.
    """
    chemin = os.path.join(bpy.app.tempdir, "mesure_z.exr")
    format_exr(scene)
    masquer(PAYS, True)
    try:
        rendre_donnees(scene, groupe_z, chemin)
    finally:
        masquer(PAYS, False)
    format_png(scene)
    z = valeurs_rouge(chemin)
    visibles = z[z < scene.camera.data.clip_end]
    if not visibles.size:
        raise RuntimeError(f"{scene.camera.name} ne voit aucune géométrie au frame "
                           f"{scene.frame_current}")
    return (round(float(visibles.min()) * (1 - MARGE), 2),
            round(float(visibles.max()) * (1 + MARGE), 2))


def frames_cles(cam):
    return (("debut", int(cam["frame_debut"])), ("fin", int(cam["frame_fin"])))


# --- planche ------------------------------------------------------------------

GABARIT_HTML = """<meta charset='utf-8'><title>Planche {nombre} plans</title>
<style>body{{background:#1b1b1b;color:#ddd;font:13px/1.5 -apple-system,sans-serif;margin:24px}}
h1{{font-size:18px}}p{{color:#999;max-width:60em}}table{{border-collapse:collapse}}
td{{padding:6px;vertical-align:top}}img{{width:420px;display:block;border:1px solid #444}}
.n{{color:#fff;font-weight:600}}.m{{color:#999;font-size:12px}}</style>
<h1>Beit HaMikdash — planche de contrôle, {nombre} plans (début / fin)</h1>
<p>Rendue par <code>beit_hamikdash_export.py --planche</code> depuis la scène courante.
Le recouvrement début/fin de chaque plan se mesure avec
<code>beit_hamikdash_analyse_plans.py</code>.</p>
<table>
{lignes}</table>
"""

GABARIT_LIGNE = """<tr><td><div class='n'>{nom}</div><div class='m'>{focale:.0f} mm · {duree:.0f} s<br>frames {debut}–{fin}</div></td>
<td><img src='{nom}_debut.png'><div class='m'>début</div></td>
<td><img src='{nom}_fin.png'><div class='m'>fin</div></td>
</tr>
"""


def ecrire_index(dossier, plans):
    lignes = "".join(GABARIT_LIGNE.format(**plan) for plan in plans)
    chemin = os.path.join(dossier, "planche.html")
    with open(chemin, "w", encoding="utf-8") as fichier:
        fichier.write(GABARIT_HTML.format(nombre=len(plans), lignes=lignes))
    return chemin


def ligne_de_plan(nom):
    cam = bpy.data.objects[nom]
    return {"nom": nom, "focale": cam.data.lens,
            "duree": cam["duree_s"], "debut": int(cam["frame_debut"]),
            "fin": int(cam["frame_fin"])}


def exporter_planche(scene, dossier, noms):
    """Couleur seule, en 640 x 360, plus l'index HTML qui les met côte à côte.

    L'index liste toujours tous les plans de la scène, même quand on n'en re-rend
    qu'un : une planche amputée de ses autres lignes n'est plus une planche de
    contrôle.
    """
    os.makedirs(dossier, exist_ok=True)
    preparer_sortie(scene, LARGEUR_PLANCHE, HAUTEUR_PLANCHE)
    couleur = groupe_passe(scene, GROUPE_COULEUR, "Image")
    transformation = scene.view_settings.view_transform
    for nom in noms:
        cam = bpy.data.objects[nom]
        scene.camera = cam
        for etiquette, frame in frames_cles(cam):
            scene.frame_set(frame)
            rendre(scene, couleur, transformation,
                   os.path.join(dossier, f"{nom}_{etiquette}.png"))
        print(f"{nom} : planche rendue", flush=True)
    index = ecrire_index(dossier, [ligne_de_plan(n) for n in cameras_de_la_scene(scene)])
    print(f"index : {index}", flush=True)


def exporter_production(scene, dossier, noms):
    """Couleur + profondeur en 1920 x 1080, les quatre fichiers qu'attend l'i2i."""
    os.makedirs(dossier, exist_ok=True)
    preparer_sortie(scene, LARGEUR, HAUTEUR)
    couleur = groupe_passe(scene, GROUPE_COULEUR, "Image")
    mesure = groupe_passe(scene, GROUPE_Z, "Depth")
    profondeur = groupe_profondeur(scene)
    transformation = scene.view_settings.view_transform
    for nom in noms:
        cam = bpy.data.objects[nom]
        scene.camera = cam
        for etiquette, frame in frames_cles(cam):
            scene.frame_set(frame)
            proche, lointain = plage_z(scene, mesure)
            cam[f"profondeur_{etiquette}"] = (proche, lointain)
            regler_plage(profondeur, proche, lointain)
            base = os.path.join(dossier, f"{nom}_{etiquette}")
            rendre(scene, couleur, transformation, base + ".png")
            # Données, pas une image : aucune transformation d'affichage sur la profondeur.
            rendre_donnees(scene, profondeur, base + "_profondeur.png")
            print(f"{nom}_{etiquette} : frame {frame}, profondeur "
                  f"{proche} m → {lointain} m", flush=True)
    scene.compositing_node_group = couleur
    scene.view_settings.view_transform = transformation


def main():
    args = arguments()
    scene = bpy.context.scene
    racine = os.path.join(os.path.dirname(bpy.data.filepath), DOSSIER)
    noms = cameras_demandees(scene, args)
    format_png(scene)

    if "--planche" in args:
        exporter_planche(scene, os.path.join(racine, SOUS_DOSSIER_PLANCHE), noms)
    else:
        exporter_production(scene, os.path.join(racine, SOUS_DOSSIER_BLOCKOUT), noms)

    format_png(scene)
    # Le .blend ne doit pas repartir avec le chemin du dernier fichier rendu : tout
    # rendu d'animation lancé ensuite écrirait ses frames à côté, sous le nom de ce
    # fichier suffixé du numéro d'image (`CAM_15_fin.png0001.png` dans renders/planche).
    scene.render.filepath = ""
    bpy.ops.wm.save_mainfile()
    print("Export terminé.", flush=True)


main()
