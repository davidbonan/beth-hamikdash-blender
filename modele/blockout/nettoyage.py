import bpy

from .primitives.parametres import AMA, FPS, NETTOYER_SCENE


# ----------------------------------------------------------------------------
# NETTOYAGE
# ----------------------------------------------------------------------------
if NETTOYER_SCENE:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for mk in list(bpy.context.scene.timeline_markers):
        bpy.context.scene.timeline_markers.remove(mk)

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.render.fps = FPS
scene["AMA_metres"] = AMA
