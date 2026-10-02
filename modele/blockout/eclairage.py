import bpy
import math
import sys

from .primitives.parametres import m
from .primitives.volumes import lampe, link_to
from .nettoyage import scene


# ----------------------------------------------------------------------------
# ÉCLAIRAGE, CIEL ET MOTEUR
# ----------------------------------------------------------------------------
def ciel():
    """Fond dégradé : brume basse près de l'horizon, bleu au zénith.

    Le fond plat donnait le même bleu du zénith à l'horizon, et les plans 1, 2, 4 et
    14b y perdaient la brume du matin — la seule chose qui détache les plans les uns
    des autres sur un décor de la taille d'un pays.
    Pas de ciel physique (Sky Texture) : mesuré, il éclaire quatre fois plus qu'ici, et
    surtout il assombrit tout ce qui est sous l'horizon. Comme rien n'est modélisé
    au-delà du Har HaBayit, le Temple s'y lisait posé sur une mer. Le dégradé descend
    au contraire vers la brume : il n'a pas de ligne d'horizon.
    """
    monde = scene.world or bpy.data.worlds.new("World")
    scene.world = monde
    monde.use_nodes = True
    arbre = monde.node_tree
    # Rejouable : le script se relance sur le .blend qu'il a lui-même produit.
    for noeud in list(arbre.nodes):
        if noeud.bl_idname not in ("ShaderNodeBackground", "ShaderNodeOutputWorld"):
            arbre.nodes.remove(noeud)
    fond = arbre.nodes["Background"]
    vue = arbre.nodes.new("ShaderNodeNewGeometry")
    vue.location = (-820, 0)
    hauteur = arbre.nodes.new("ShaderNodeSeparateXYZ")
    hauteur.location = (-640, 0)
    arbre.links.new(vue.outputs["Incoming"], hauteur.inputs["Vector"])
    montee = arbre.nodes.new("ShaderNodeMapRange")
    montee.location = (-460, 0)
    montee.clamp = True
    montee.inputs["From Min"].default_value = -0.25   # Incoming.Z vaut +1 au zénith (mesuré)
    montee.inputs["From Max"].default_value = 0.75
    arbre.links.new(hauteur.outputs["Z"], montee.inputs["Value"])
    degrade = arbre.nodes.new("ShaderNodeValToRGB")
    degrade.location = (-260, 0)
    rampe = degrade.color_ramp
    rampe.elements[0].position = 0.0
    rampe.elements[0].color = (0.60, 0.66, 0.76, 1.0)     # brume
    rampe.elements[1].position = 1.0
    rampe.elements[1].color = (0.26, 0.40, 0.66, 1.0)     # zénith
    rampe.elements.new(0.35).color = (0.46, 0.57, 0.73, 1.0)
    arbre.links.new(montee.outputs["Result"], degrade.inputs["Factor"])
    arbre.links.new(degrade.outputs["Color"], fond.inputs["Color"])
    # Le ciel N'EST PAS un remplissage neutre. À 0,6 sur une brume presque blanche, il
    # éclairait chaque face d'autant que le soleil, sans direction et sans couleur : le
    # calcaire y perdait sa teinte, et le modelé avec. Baissé à 0,30 et bleui, il rend
    # ce qu'un ciel fait — la lumière du soleil est chaude, son ombre est FROIDE, et
    # c'est cet écart-là, pas l'appareil, qui fait lire une pierre comme de la pierre.
    fond.inputs["Strength"].default_value = 0.30


def moteur_eevee():
    """Rendu par défaut. Sans rebond, les intérieurs (plans 9 à 12) tombaient en aplat :
    le Heikhal n'est éclairé que par la Menora et quatre fenêtres hautes, et la lumière
    ne descendait pas jusqu'au sol."""
    for identifiant in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try:
            scene.render.engine = identifiant
            break
        except TypeError:
            continue
    eevee = scene.eevee
    eevee.taa_render_samples = 64
    eevee.use_shadows = True
    eevee.shadow_ray_count = 2
    eevee.shadow_step_count = 6
    eevee.use_raytracing = True
    eevee.ray_tracing_method = 'SCREEN'
    eevee.use_fast_gi = True
    eevee.fast_gi_method = 'GLOBAL_ILLUMINATION'
    eevee.use_volumetric_shadows = True


def moteur_cycles():
    """`--rendu-cycles` : pour les images clés seulement. Trente-huit frames, pas 8472 — le
    film ne sort pas de Blender, et l'occlusion réelle de l'Oulam ou du Kodesh
    HaKodashim vaut la minute qu'elle coûte.

    Le nom ne peut pas être `--cycles` : l'addon Cycles analyse tout `sys.argv`, `--` compris,
    et Blender 5.2 refuse la ligne avant de charger le fichier — « ambiguous option: --cycles
    could match --cycles-print-stats, --cycles-device »."""
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    reglages = bpy.context.preferences.addons.get("cycles")
    if reglages is None:
        return
    for calcul in ('METAL', 'OPTIX', 'CUDA'):
        try:
            reglages.preferences.compute_device_type = calcul
        except TypeError:
            continue
        reglages.preferences.get_devices()
        scene.cycles.device = 'GPU'
        return


sun = lampe("Soleil_AUBE_est", 'SUN', (m(200), m(-60), m(150)))
# 3,2 et non 4,0 : à 4,0, ciel compris, le calcaire sortait à 0,77 sur l'épaule d'AgX,
# où la courbe est presque plate — la pierre y perdait sa couleur (écart R-B de 5
# centièmes, un gris) et l'écart entre deux blocs y était écrasé d'un facteur six. Le
# mur n'est pas plus sombre pour autant : le ciel a baissé davantage, et la part du
# soleil dans ce qui l'éclaire a donc monté. C'est ce rapport-là qui compte.
sun.data.energy = 3.2
sun.data.color = (1.0, 0.85, 0.65)
sun.data.angle = math.radians(1.5)
# Vise depuis l'est, 12° au-dessus de l'horizon (aube). Pour "jour" : passer à 30–35°.
sun.rotation_euler = (math.radians(90 - 12), 0, math.radians(90 + 15))
link_to(sun, "91_Lumiere")
ciel()
(moteur_cycles if "--rendu-cycles" in sys.argv else moteur_eevee)()
for vt in ('AgX', 'Filmic'):
    try:
        scene.view_settings.view_transform = vt
        break
    except TypeError:
        continue


# Passes utiles pour le conditionnement IA (profondeur, normales)
vl = scene.view_layers[0]
vl.use_pass_z = True
vl.use_pass_normal = True
vl.use_pass_mist = True
