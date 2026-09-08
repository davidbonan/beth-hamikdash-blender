"""Interroge la scène du .blend — sans la reconstruire.

    /Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
        -P beit_hamikdash_inspect.py -- <commande>

Les autres scripts du dépôt *fabriquent* ; celui-ci ne fait que lire, et il lit le
.blend tel qu'il a été sauvegardé — pas de `-P beit_hamikdash_blockout.py` devant.
C'est toute la raison d'être du script : répondre en une seconde à « où est le
Doukhan », « qu'est-ce que cette caméra a vraiment dans le cadre », « la fenêtre du
Beit Avtinas montre-t-elle la cour », questions qui se posaient jusqu'ici en écrivant
un script jetable et en attendant une reconstruction complète.

Le .blend est un artefact dérivé : il date du dernier `beit_hamikdash_export.py`,
seul script qui appelle `wm.save_mainfile`. Après une modification du blockout ou de
`cameras.json` non suivie d'un export, ce qu'on lit ici est l'ancienne scène.

Commandes
    --scene                    collections, durée, caméras, étendue    (défaut)
    --objets <motif>           bornes en amot des objets dont le nom contient <motif>
    --camera <plan>            pose, cadrage et champ aux deux frames clés du plan
    --voit <plan> [debut|fin]  ce que le cadre contient vraiment, par part d'écran
    --foule <plan> [debut|fin] combien de figures le plan voit, et de quelle taille

<plan> se donne au choix : le nom complet de la caméra (CAM_03_Heikhal), son numéro
(3, 03) ou n'importe quel fragment de son nom (heikhal).
"""

import math
import re
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

GRILLE = (40, 23)     # 920 rayons : la part d'écran est juste à ~1 % près
PORTEE = 5000.0       # au-delà, c'est le fond de ciel
AMA_DEFAUT = 0.48     # si le .blend est antérieur à la propriété de scène


# --- lecture de la scène ------------------------------------------------------

def arguments():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def ama(scene):
    return scene.get("AMA_metres", AMA_DEFAUT)


def cameras(scene):
    """Les caméras dans l'ordre de la timeline, pas dans celui de bpy.data."""
    marqueurs = sorted((mk for mk in scene.timeline_markers if mk.camera),
                       key=lambda mk: mk.frame)
    return [mk.camera for mk in marqueurs]


def resoudre(scene, cle):
    """« 3 », « 03 », « heikhal », « CAM_03_Heikhal » — tous mènent à la même caméra."""
    liste = cameras(scene)
    cherche = cle.upper().removeprefix("CAM_")
    for cam in liste:
        court = cam.name.removeprefix("CAM_").split("_")[0]
        if cam.name.upper() == cle.upper() or court == cherche or court == cherche.zfill(2):
            return cam
    for cam in liste:
        if cherche in cam.name.upper():
            return cam
    sys.exit(f"Aucune caméra pour « {cle} ». Connues : "
             + ", ".join(c.name.removeprefix("CAM_").split("_")[0] for c in liste))


def bornes(o, unite):
    """(min, max) de l'emprise mondiale de l'objet, en amot."""
    coins = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return ([min(p[k] for p in coins) / unite for k in range(3)],
            [max(p[k] for p in coins) / unite for k in range(3)])


def frames_cles(cam):
    return int(cam["frame_debut"]), int(cam["frame_fin"])


def poser(scene, cam, frame):
    """(caméra évaluée, position) au frame, contrainte Track To appliquée."""
    scene.frame_set(frame)
    camera = cam.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return camera, camera.matrix_world.translation.copy()


def champs(cam, scene):
    """(champ horizontal, champ vertical) en degrés."""
    ratio = scene.render.resolution_y / scene.render.resolution_x
    demi = cam.data.sensor_width / 2
    return (math.degrees(2 * math.atan(demi / cam.data.lens)),
            math.degrees(2 * math.atan(demi * ratio / cam.data.lens)))


def objets_vus(scene, cam, frame):
    """Part d'écran occupée par chaque objet, mesurée à la grille de rayons.

    Le ciel n'est pas un objet : la part manquante pour arriver à 100 % est ce que
    la caméra voit hors géométrie.
    """
    camera, origine = poser(scene, cam, frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    coins = camera.data.view_frame(scene=scene)       # HD, BD, BG, HG en espace caméra
    haut_droit, bas_gauche = coins[0], coins[2]
    matrice = camera.matrix_world
    largeur, hauteur = GRILLE
    parts, distances = {}, {}
    for i in range(largeur):
        u = (i + 0.5) / largeur
        for j in range(hauteur):
            v = (j + 0.5) / hauteur
            local = Vector((bas_gauche.x + (haut_droit.x - bas_gauche.x) * u,
                            bas_gauche.y + (haut_droit.y - bas_gauche.y) * v,
                            haut_droit.z))
            direction = (matrice @ local) - origine
            direction.normalize()
            touche, position, _, _, objet, _ = scene.ray_cast(
                depsgraph, origine, direction, distance=PORTEE)
            if not touche:
                continue
            nom = objet.name
            parts[nom] = parts.get(nom, 0) + 1
            distances[nom] = min(distances.get(nom, 1e9), (position - origine).length)
    total = largeur * hauteur
    return [(nom, n / total, distances[nom])
            for nom, n in sorted(parts.items(), key=lambda kv: -kv[1])], total


def collection_de(o):
    return o.users_collection[0].name if o.users_collection else "—"


# --- commandes ----------------------------------------------------------------

def montrer_scene(scene):
    unite = ama(scene)
    maillages = [o for o in bpy.data.objects if o.type == 'MESH']
    print(f"\n{bpy.data.filepath}", flush=True)
    print(f"1 ama = {unite} m · {scene.render.fps} fps · frames "
          f"{scene.frame_start}..{scene.frame_end} = "
          f"{(scene.frame_end - scene.frame_start + 1) / scene.render.fps:.0f} s", flush=True)
    print(f"{len(bpy.data.objects)} objets, dont {len(maillages)} volumes, "
          f"{len([o for o in bpy.data.objects if o.type == 'LIGHT'])} lampes\n", flush=True)

    print("collections", flush=True)
    for col in sorted(bpy.data.collections, key=lambda c: c.name):
        etat = "   (masquée au rendu)" if col.hide_render else ""
        print(f"  {col.name:<22} {len(col.objects):>5} "
              f"{'objets' if len(col.objects) > 1 else 'objet '}{etat}", flush=True)

    print("\nplans", flush=True)
    print(f"  {'plan':<32} {'focale':>7} {'frames':>14} {'durée':>7}  champ H × V",
          flush=True)
    for cam in cameras(scene):
        f0, f1 = frames_cles(cam)
        h, v = champs(cam, scene)
        print(f"  {cam.name:<32} {cam.data.lens:>4.0f} mm {f0:>6}..{f1:<6} "
              f"{cam['duree_s']:>6.0f}s  {h:>5.1f}° × {v:.1f}°", flush=True)

    if maillages:
        lo = [min(bornes(o, unite)[0][k] for o in maillages) for k in range(3)]
        hi = [max(bornes(o, unite)[1][k] for o in maillages) for k in range(3)]
        print("\nétendue, en amot : " + "  ".join(
            f"{axe} {a:>6.0f}..{b:<6.0f}" for axe, a, b in zip("xyz", lo, hi)), flush=True)
    print(flush=True)


def montrer_objets(scene, motif):
    unite = ama(scene)
    trouves = [o for o in bpy.data.objects if motif.lower() in o.name.lower()]
    if not trouves:
        sys.exit(f"Aucun objet dont le nom contient « {motif} ».")
    largeur = min(40, max(len(o.name) for o in trouves))
    print(f"\n{len(trouves)} objets contenant « {motif} » — bornes en amot\n", flush=True)
    print(f"  {'objet':<{largeur}} {'x':^16}  {'y':^16}  {'z':^16}  collection",
          flush=True)
    for o in sorted(trouves, key=lambda o: o.name):
        if o.type != 'MESH':
            p = o.matrix_world.translation / unite
            cases = "  ".join(f"{c:^16.1f}" for c in p)
            print(f"  {o.name:<{largeur}} {cases}  {o.type.lower()}", flush=True)
            continue
        lo, hi = bornes(o, unite)
        cases = "  ".join(f"{a:>7.1f}..{b:<7.1f}" for a, b in zip(lo, hi))
        print(f"  {o.name:<{largeur}} {cases}  {collection_de(o)}", flush=True)
    print(flush=True)


def montrer_camera(scene, cam):
    unite = ama(scene)
    f0, f1 = frames_cles(cam)
    h, v = champs(cam, scene)
    cible = next((c.target for c in cam.constraints if c.type == 'TRACK_TO'), None)
    print(f"\n{cam.name}", flush=True)
    print(f"  {cam.data.lens:.0f} mm sur capteur {cam.data.sensor_width:.0f} mm — "
          f"champ {h:.1f}° × {v:.1f}°", flush=True)
    print(f"  frames {f0}..{f1} = {cam['duree_s']:.0f} s à {scene.render.fps} fps",
          flush=True)
    print(flush=True)
    print(f"  {'':<7} {'caméra (amot)':>26}   {'cible (amot)':>26}", flush=True)
    poses = []
    for etiquette, frame in (("début", f0), ("fin", f1)):
        _, position = poser(scene, cam, frame)
        poses.append(position)
        p = position / unite
        t = (cible.matrix_world.translation / unite) if cible else Vector()
        print(f"  {etiquette:<7} {p.x:>8.1f} {p.y:>8.1f} {p.z:>8.1f}   "
              f"{t.x:>8.1f} {t.y:>8.1f} {t.z:>8.1f}", flush=True)
    course = (poses[1] - poses[0]).length / unite
    duree = cam["duree_s"]
    print(f"\n  course {course:.1f} amot en {duree:.0f} s "
          f"= {course / duree:.2f} ama/s", flush=True)
    if cible:
        print(f"  cible : {cible.name}", flush=True)
    print(flush=True)


def montrer_ce_qui_est_vu(scene, cam, etiquette):
    f0, f1 = frames_cles(cam)
    frame = f1 if etiquette == "fin" else f0
    lignes, total = objets_vus(scene, cam, frame)
    unite = ama(scene)
    couvert = sum(part for _, part, _ in lignes)
    print(f"\n{cam.name} — frame {frame} ({etiquette}), {total} rayons\n", flush=True)
    if not lignes:
        print("  Aucune géométrie dans le cadre : la caméra ne voit que le ciel, "
              "ou elle est posée dans un volume.\n", flush=True)
        return
    largeur = min(40, max(len(nom) for nom, _, _ in lignes))
    print(f"  {'objet':<{largeur}} {'écran':>7} {'plus proche':>13}", flush=True)
    for nom, part, distance in lignes:
        if part < 0.002:
            continue
        print(f"  {nom:<{largeur}} {part:>6.1%} {distance / unite:>10.1f} amot", flush=True)
    print(f"\n  géométrie {couvert:.0%} de l'écran, ciel {1 - couvert:.0%}\n", flush=True)


FOULE = "76_Foule"


def figure_de_foule(nom):
    """« Am_EzratIsrael_0012_robe » → « Am_EzratIsrael_0012 » : la figure, pas sa pièce.

    Une figure est faite de pièces — robe, torse, bras, talith, kinor… — nommées
    après son numéro ; les blocs lointains n'ont pas de pièce et gardent leur nom.
    """
    trouve = re.match(r"^(.*?_\d{2,4})(?:_|$)", nom)
    return trouve.group(1) if trouve else nom


def groupe_de_foule(figure):
    """« Am_EzratNashim_1204 » → « Am_EzratNashim » : le groupe, pas l'individu."""
    return re.sub(r"_\d{2,4}$", "", figure)


def proche(camera):
    return camera.data.clip_start


def dans_le_cadre(camera, ndc):
    """Le point est-il devant l'objectif ET dans les bords de l'image ?

    `world_to_camera_view` projette aussi ce qui est hors cadre et ce qui est derrière :
    sans ce filtre, la foule d'une cour que la caméra ne regarde pas compte comme vue,
    et une figure à cheval sur le plan proche sort à cent mille pixels.
    """
    return ndc.z > proche(camera) and 0.0 <= ndc.x <= 1.0 and 0.0 <= ndc.y <= 1.0


def montrer_foule(scene, cam, etiquette):
    """Combien de figures ce plan voit vraiment, et sur combien de pixels.

    La question décide d'un prompt : un plan qui ne montre aucune figure lisible ne
    donne au styliseur aucune échelle humaine, et la foule qu'il peindra sera inventée
    — mesuré sur le plan 1, où elle sortait quatre fois trop grande. Le corps sert de
    cible et la tête est ignorée : c'est la même figure.

    Un rayon qui ne rencontre que de la foule compte comme vu — une silhouette cachée
    par sa voisine est quand même de la foule à l'écran. Une figure est la boîte qui
    enveloppe toutes ses pièces : compter les pièces aurait compté six fois chacun.

    C'est la **médiane** qui dit si le plan porte une échelle, pas le maximum : à la fin
    du plan 4 la caméra traverse la foule de l'Ezrat Nashim et un bloc qui frôle
    l'objectif y fait trois mille pixels, ce qui ne dit rien des autres.
    """
    collection = bpy.data.collections.get(FOULE)
    if not collection:
        print(f"\n  Aucune collection « {FOULE} » dans la scène.\n", flush=True)
        return
    f0, f1 = frames_cles(cam)
    frame = f1 if etiquette == "fin" else f0
    camera, oeil = poser(scene, cam, frame)
    scene.camera = cam
    graphe = bpy.context.evaluated_depsgraph_get()
    hauteur_image = scene.render.resolution_y
    noms = {o.name for o in collection.objects}

    figures = {}
    for objet in collection.objects:
        coins = [objet.matrix_world @ Vector(coin) for coin in objet.bound_box]
        bornes = figures.setdefault(figure_de_foule(objet.name), [])
        bornes += [Vector(min(c[i] for c in coins) for i in range(3)),
                   Vector(max(c[i] for c in coins) for i in range(3))]

    groupes = {}
    for figure, bornes in figures.items():
        bas_xyz = Vector(min(b[i] for b in bornes) for i in range(3))
        haut_xyz = Vector(max(b[i] for b in bornes) for i in range(3))
        centre, haut, bas = (bas_xyz + haut_xyz) / 2, haut_xyz.z, bas_xyz.z
        sommet = Vector((centre.x, centre.y, haut))
        total, hauteurs = groupes.setdefault(groupe_de_foule(figure), [0, []])
        groupes[groupe_de_foule(figure)][0] = total + 1
        vue = sommet - oeil
        touche, _, _, _, obstacle, _ = scene.ray_cast(
            graphe, oeil, vue.normalized(), distance=vue.length * 1.02)
        if touche and obstacle is not None and obstacle.name not in noms:
            continue
        haut_ndc = world_to_camera_view(scene, camera, sommet)
        bas_ndc = world_to_camera_view(scene, camera, Vector((centre.x, centre.y, bas)))
        if not dans_le_cadre(camera, haut_ndc) or bas_ndc.z <= proche(camera):
            continue
        hauteurs.append(abs(haut_ndc.y - bas_ndc.y) * hauteur_image)

    print(f"\n{cam.name} — frame {frame} ({etiquette}), "
          f"sortie {scene.render.resolution_x} × {hauteur_image}\n", flush=True)
    largeur = min(30, max(len(nom) for nom in groupes))
    print(f"  {'groupe':<{largeur}} {'visibles':>14} {'médiane':>10} {'max':>10}", flush=True)
    total_vues, medianes = 0, []
    for nom, (total, hauteurs) in sorted(groupes.items()):
        if total < 5:                     # les figures uniques sont des proxys, pas la foule
            continue
        total_vues += len(hauteurs)
        if not hauteurs:
            print(f"  {nom:<{largeur}} {0:>6} / {total:<5} {'—':>10} {'—':>10}", flush=True)
            continue
        hauteurs.sort()
        mediane = hauteurs[len(hauteurs) // 2]
        medianes.append(mediane)
        print(f"  {nom:<{largeur}} {len(hauteurs):>6} / {total:<5} "
              f"{mediane:>7.1f} px {hauteurs[-1]:>7.1f} px", flush=True)
    plus_grande = max(medianes, default=0.0)
    print(f"\n  {total_vues} figures visibles, la plus grande médiane à "
          f"{plus_grande:.1f} px sur {hauteur_image}.", flush=True)
    if total_vues < 20 or plus_grande < 15:
        print("  Le plan ne porte aucune échelle humaine lisible : la dire en chiffres\n"
              "  dans la ligne **Édition finale** du plan.\n", flush=True)
    else:
        print(flush=True)


def main():
    args = arguments()
    scene = bpy.context.scene
    if not args or args[0] == "--scene":
        return montrer_scene(scene)
    commande, reste = args[0], args[1:]
    if commande == "--objets":
        if not reste:
            sys.exit("--objets attend un motif de nom.")
        return montrer_objets(scene, reste[0])
    if commande == "--camera":
        if not reste:
            sys.exit("--camera attend un plan (3, 03, heikhal, CAM_03_Heikhal…).")
        return montrer_camera(scene, resoudre(scene, reste[0]))
    if commande == "--voit":
        if not reste:
            sys.exit("--voit attend un plan (3, 03, heikhal, CAM_03_Heikhal…).")
        etiquette = reste[1].lower() if len(reste) > 1 else "debut"
        if etiquette not in ("debut", "début", "fin"):
            sys.exit(f"--voit attend « debut » ou « fin », pas « {etiquette} ».")
        return montrer_ce_qui_est_vu(scene, resoudre(scene, reste[0]),
                                     "fin" if etiquette == "fin" else "debut")
    if commande == "--foule":
        if not reste:
            sys.exit("--foule attend un plan (3, 03, heikhal, CAM_03_Heikhal…).")
        etiquette = reste[1].lower() if len(reste) > 1 else "debut"
        if etiquette not in ("debut", "début", "fin"):
            sys.exit(f"--foule attend « debut » ou « fin », pas « {etiquette} ».")
        return montrer_foule(scene, resoudre(scene, reste[0]),
                             "fin" if etiquette == "fin" else "debut")
    sys.exit(f"Commande inconnue : {commande}. Voir l'en-tête du script.")


main()
