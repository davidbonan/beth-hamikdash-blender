"""Mesure, plan par plan, ce qu'un i2v peut faire du couple (frame de début, frame de fin).

    /Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \
        -P beit_hamikdash_blockout.py -P beit_hamikdash_analyse_plans.py

Un image-to-video à deux frames n'interpole que ce que les deux frames ont en
commun. Quand elles ne partagent rien — le tilt du plan 9 finissait sur un aplat de
parokhet — le modèle invente le trajet, et le plan est perdu avant d'être généré.
Le recouvrement n'est pas jugeable à l'œil sur une planche : il se mesure.

Méthode : on tire une grille de rayons à travers une frame, on garde les points de
géométrie touchés, et on regarde ce que l'autre caméra en fait — dans son cadre, et
non caché derrière autre chose. Trois chiffres, qui ne disent pas la même chose :

- « gardé » — la part de la frame de début encore visible à la fin. Elle mesure ce
  que le mouvement chasse hors champ. Un travelling avant la fait tomber très bas
  sans que ce soit un défaut : les pierres du premier plan passent derrière la
  caméra, c'est ce qu'on lui demande.
- « couvert » — la part de la frame de fin déjà visible au début. C'est celle qui
  décide : ce qu'elle laisse de côté, le modèle doit l'inventer. Un travelling avant
  la garde haute — l'image d'arrivée est un agrandissement du centre de l'image de
  départ. Un panoramique ou une grue l'effondrent, parce que le cadre de fin regarde
  ailleurs, ou découvre ce qu'un mur cachait.
- « zoom » — de combien le décor commun grossit d'une frame à l'autre. Une
  couverture de 100 % ne suffit pas si la frame de fin est l'agrandissement d'un
  timbre-poste du centre de la frame de début : la géométrie est bien annoncée, mais
  la matière, elle, est à inventer.

Le diagnostic porte sur « couvert » et « zoom ». « Gardé » reste affiché : deux
valeurs basses ensemble signalent un plan qui ne partage plus rien du tout.

L'occultation est testée. Sans elle la mesure ment sur exactement les plans qu'elle
devrait condamner : une grue qui se lève au-dessus d'un mur découvre un pays neuf
dont chaque point tombait déjà dans le cône de la caméra de départ — mais derrière
le mur. Le plan 14 passait ainsi à 100 % de couverture.
"""

import math

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

AXE_VISEE = Vector((0.0, 0.0, -1.0))

RESOLUTION = (48, 27)     # grille de rayons ; 1296 par frame suffit à 1 % près
PORTEE = 5000.0           # au-delà, c'est le fond de ciel
MARGE_OCCULTATION = 0.02  # 2 % : un rayon touche toujours la surface qu'il a servi à trouver
SEUIL_BON = 0.40          # couverture : en dessous, l'i2v invente plus qu'il n'interpole
SEUIL_FIGE = 0.97         # au-dessus, les deux frames sont la même image
ZOOM_MAX = 2.5            # au-delà, la frame de fin agrandit trop peu de pixels de celle de début
GLISSE_LENTE = 0.06       # largeurs de cadre par seconde ; au-delà, le mouvement n'est plus lent


def cameras_de_la_scene(scene):
    """Les caméras dans l'ordre de la timeline, pas dans celui de bpy.data."""
    marqueurs = sorted((mk for mk in scene.timeline_markers if mk.camera),
                       key=lambda mk: mk.frame)
    return [mk.camera for mk in marqueurs]


def poser(scene, cam, frame):
    """(caméra évaluée, position) au frame, contrainte Track To appliquée."""
    scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    camera = cam.evaluated_get(depsgraph)
    return camera, camera.matrix_world.translation.copy()


def points_vus(scene, cam, frame):
    """Points de géométrie touchés par une grille de rayons tirée du frame."""
    camera, origine = poser(scene, cam, frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    coins = camera.data.view_frame(scene=scene)       # HD, BD, BG, HG en espace caméra
    haut_droit, bas_gauche = coins[0], coins[2]
    matrice = camera.matrix_world
    largeur, hauteur = RESOLUTION
    touches = []
    for i in range(largeur):
        u = (i + 0.5) / largeur
        for j in range(hauteur):
            v = (j + 0.5) / hauteur
            local = Vector((bas_gauche.x + (haut_droit.x - bas_gauche.x) * u,
                            bas_gauche.y + (haut_droit.y - bas_gauche.y) * v,
                            haut_droit.z))
            direction = (matrice @ local) - origine
            direction.normalize()
            touche, position, *_ = scene.ray_cast(depsgraph, origine, direction,
                                                  distance=PORTEE)
            if touche:
                touches.append(position)
    return touches


def vues_depuis(scene, cam, frame, points):
    """Pour chaque point : (u, v) s'il est visible depuis cette caméra, sinon None.

    Visible veut dire dans le cadre *et* rien devant lui. Le second test est un
    rayon tiré vers le point et arrêté juste avant : s'il touche quelque chose, un
    mur s'est interposé et le point n'était pas à l'image.
    """
    camera, origine = poser(scene, cam, frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    vues = []
    for point in points:
        u, v, profondeur = world_to_camera_view(scene, camera, point)
        if not (profondeur > 0 and 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0):
            vues.append(None)
            continue
        direction = point - origine
        distance = direction.length
        direction.normalize()
        occulte, *_ = scene.ray_cast(depsgraph, origine, direction,
                                     distance=distance * (1 - MARGE_OCCULTATION))
        vues.append(None if occulte else (u, v))
    return vues


def part_visible(vues):
    return sum(1 for c in vues if c) / len(vues) if vues else 0.0


def zoom(points, position_debut, position_fin, vues_debut, vues_fin):
    """Grossissement médian du décor commun aux deux frames."""
    rapports = sorted((point - position_debut).length / (point - position_fin).length
                      for point, a, b in zip(points, vues_debut, vues_fin) if a and b)
    return rapports[len(rapports) // 2] if rapports else 1.0


def glisse_par_seconde(scene, cam, frame, points):
    """Déplacement médian d'un point de décor à l'image, en largeurs de cadre par seconde.

    C'est la mesure du « mouvement lent » que demande le shot list : elle regarde ce
    que fait l'image, pas ce que fait la caméra. Un travelling de 6 m/s vers une
    ville à 500 m glisse moins qu'un pas de côté dans un couloir.

    Mesurée sur une seconde et non d'un bout à l'autre du plan : entre les deux
    frames extrêmes d'un plan à recouvrement nul il ne reste aucun point commun, et
    la médiane porterait sur une poignée de points de bord. Les keyframes sont en
    interpolation linéaire, donc n'importe quelle seconde vaut pour tout le plan.
    """
    ici = vues_depuis(scene, cam, frame, points)
    apres = vues_depuis(scene, cam, frame + scene.render.fps, points)
    deplacements = sorted(math.dist(a, b) for a, b in zip(ici, apres) if a and b)
    return deplacements[len(deplacements) // 2] if deplacements else 0.0


def champ_vertical(cam, scene):
    ratio = scene.render.resolution_y / scene.render.resolution_x
    return math.degrees(2 * math.atan((cam.data.sensor_width * ratio / 2) / cam.data.lens))


def diagnostic(garde, couvert, grossissement, glisse):
    if garde >= SEUIL_FIGE and couvert >= SEUIL_FIGE:
        return "FIGÉ — une seule image + prompt de mouvement"
    if couvert < SEUIL_BON:
        return "À RE-DÉCOUPER — le cadre de fin regarde ailleurs"
    if grossissement > ZOOM_MAX:
        return f"APPROCHE TROP FORTE — ×{grossissement:.1f}, la matière de fin est à inventer"
    if glisse > GLISSE_LENTE:
        return f"TROP RAPIDE — {glisse:.2f} cadre/s"
    return "ok"


def mesure(scene, cam):
    debut, fin = int(cam["frame_debut"]), int(cam["frame_fin"])
    points_debut = points_vus(scene, cam, debut)
    points_fin = points_vus(scene, cam, fin)
    if not points_debut or not points_fin:
        # Une caméra posée dans un volume ne renvoie aucun point : ses rayons partent
        # de l'intérieur d'un mur ou d'une silhouette de foule. Ce n'est pas un défaut
        # de cadrage, et l'afficher comme 0 % de recouvrement le ferait croire.
        return (cam.name, cam["duree_s"], cam.data.lens, 0.0, 0.0, 1.0, 0.0,
                champ_vertical(cam, scene), 0.0,
                "CAMÉRA DANS UN VOLUME — la déplacer hors des murs et de la foule")

    # L'objet évalué suit le depsgraph : tout ce qui vient de la pose de début doit
    # être copié avant de déplacer la scène au frame de fin.
    camera_debut, position_debut = poser(scene, cam, debut)
    axe_debut = (camera_debut.matrix_world.to_3x3() @ AXE_VISEE).copy()
    vues_debut = vues_depuis(scene, cam, debut, points_debut)

    camera_fin, position_fin = poser(scene, cam, fin)
    axe_fin = (camera_fin.matrix_world.to_3x3() @ AXE_VISEE).copy()
    vues_fin = vues_depuis(scene, cam, fin, points_debut)

    garde = part_visible(vues_fin)
    couvert = part_visible(vues_depuis(scene, cam, debut, points_fin))
    grossissement = zoom(points_debut, position_debut, position_fin, vues_debut, vues_fin)
    glisse = glisse_par_seconde(scene, cam, debut, points_debut)

    return (cam.name, cam["duree_s"], cam.data.lens, garde, couvert, grossissement,
            math.degrees(axe_debut.angle(axe_fin)), champ_vertical(cam, scene), glisse,
            diagnostic(garde, couvert, grossissement, glisse))


def main():
    scene = bpy.context.scene
    lignes = [mesure(scene, cam) for cam in cameras_de_la_scene(scene)]
    largeur_nom = max(len(l[0]) for l in lignes)
    barre = "=" * (largeur_nom + 86)
    print("\n" + barre, flush=True)
    print(f"{'plan':<{largeur_nom}}  {'durée':>6} {'foc':>4} {'gardé':>6} {'couvert':>8} "
          f"{'zoom':>6} {'rot°':>6} {'champV°':>8} {'cadre/s':>8}  diagnostic", flush=True)
    print("-" * (largeur_nom + 86), flush=True)
    for (nom, duree, focale, garde, couvert, grossissement, rotation, champ,
         glisse, mot) in lignes:
        print(f"{nom:<{largeur_nom}}  {duree:>5.0f}s {focale:>4.0f} {garde:>5.0%} "
              f"{couvert:>7.0%} {grossissement:>5.2f}× {rotation:>6.1f} {champ:>8.1f} "
              f"{glisse:>8.3f}  {mot}", flush=True)
    print(barre + "\n", flush=True)


main()
