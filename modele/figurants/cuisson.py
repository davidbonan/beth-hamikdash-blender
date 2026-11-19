import bpy
import numpy as np

COTE = 1024


# Un texel que le rayon de cuisson ne trouve pas garde le fond.
def image_a_cuire(nom, fond):
    image = bpy.data.images.new(nom, COTE, COTE, alpha=False, float_buffer=True)
    image.colorspace_settings.name = "Non-Color"
    image.generated_color = fond
    return image


def cuire(type_, cible, image, sources, **reglages):
    arbre = cible.data.materials[0].node_tree
    noeud = arbre.nodes.new("ShaderNodeTexImage")
    noeud.image = image
    arbre.nodes.active = noeud
    bpy.ops.object.select_all(action="DESELECT")
    for objet in sources:
        objet.select_set(True)
    cible.select_set(True)
    bpy.context.view_layer.objects.active = cible
    bpy.ops.object.bake(type=type_, margin=8, **reglages)
    arbre.nodes.remove(noeud)


def pixels(image):
    px = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(px)
    return px.reshape(image.size[1], image.size[0], 4)


def ecrire(nom, rgb, donnees):
    image = bpy.data.images.new(nom, COTE, COTE, alpha=False)
    if donnees:
        image.colorspace_settings.name = "Non-Color"
    rgba = np.ones((COTE, COTE, 4), dtype=np.float32)
    rgba[..., :3] = rgb
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    return image


# Ce que la scène rend, réduit le temps d'une cuisson aux `gardes` ; le creux ne regarde pas plus loin que `portee`.
class Plateau:
    def __init__(self, gardes, portee):
        self.caches = [o for o in bpy.context.scene.objects if o not in gardes and not o.hide_render]
        self.portee = portee
        scene = bpy.context.scene
        self.moteur, self.echantillons = scene.render.engine, scene.cycles.samples
        self.distance = scene.world.light_settings.distance if scene.world else None

    def __enter__(self):
        scene = bpy.context.scene
        for o in self.caches:
            o.hide_render = True
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 64
        if scene.world:
            scene.world.light_settings.distance = self.portee
        return self

    def __exit__(self, *_):
        scene = bpy.context.scene
        for o in self.caches:
            o.hide_render = False
        scene.render.engine, scene.cycles.samples = self.moteur, self.echantillons
        if self.distance is not None:
            scene.world.light_settings.distance = self.distance
