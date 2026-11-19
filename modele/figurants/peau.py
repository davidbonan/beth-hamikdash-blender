import bpy

from .cuisson import Plateau, cuire, ecrire, image_a_cuire, pixels

# Orbites, narines, oreilles, entre les doigts : ce que le corps cache de lui-même, pas l'ombre d'un bras posé.
PORTEE_DU_CREUX = 0.15
# Cuit tel quel, le creux ne fonçait que l'oreille : creusé d'une puissance, l'orbite et la narine se lisent à l'ombre.
CONTRASTE = 3.0
# Le nom que l'export glTF cherche pour y lire l'occlusion.
SORTIE_GLTF = "glTF Material Output"

_creux = None


def _cuire_le_creux(humain):
    h = humain
    cuite = image_a_cuire("peau_creux_cuite", (1.0, 1.0, 1.0, 1.0))
    with Plateau([h.corps, *h.accessoires], PORTEE_DU_CREUX):
        cuire("AO", h.corps, cuite, [])
    creux = pixels(cuite)[..., :3] ** CONTRASTE
    bpy.data.images.remove(cuite)
    return ecrire("Peau_creux", creux, True)


def _sortie_gltf():
    groupe = bpy.data.node_groups.get(SORTIE_GLTF)
    if groupe is None:
        groupe = bpy.data.node_groups.new(SORTIE_GLTF, "ShaderNodeTree")
        groupe.interface.new_socket("Occlusion", socket_type="NodeSocketFloat")
    return groupe


# Les corps MakeHuman partagent leurs UV : le creux du premier, cuit une fois, sert à tous.
def creuser_la_peau(humain):
    global _creux
    if _creux is None:
        _creux = _cuire_le_creux(humain)
    for mat in humain.corps.data.materials:
        arbre = mat.node_tree
        image = arbre.nodes.new("ShaderNodeTexImage")
        image.image = _creux
        sortie = arbre.nodes.new("ShaderNodeGroup")
        sortie.node_tree = _sortie_gltf()
        arbre.links.new(image.outputs["Color"], sortie.inputs["Occlusion"])
