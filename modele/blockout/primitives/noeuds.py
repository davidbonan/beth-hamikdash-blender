import bpy

from .parametres import m


# ----------------------------------------------------------------------------
# MATIÈRES
#   Toutes procédurales et lues en coordonnées de MONDE (Geometry > Position) :
#   un mur percé est fait de cinq boîtes, et des coordonnées d'objet y auraient
#   recadré la pierre cinq fois — les assises se poursuivent maintenant d'une boîte
#   à la suivante et le grain ne saute pas d'un objet à son voisin.
#   C'est ce relief, et non la couleur, qui remplit la passe Normal : plate, elle
#   laissait l'i2i réinventer chaque arête à chaque image.
#   Palette et matériaux : §7 et §9 de la fiche technique.
# ----------------------------------------------------------------------------
def _bsdf(mat):
    return mat.node_tree.nodes["Principled BSDF"]

_MATIERES_CABLEES = set()

def _neuf(name, rgb):
    """(matériau, vrai s'il reste à câbler) — une fois par exécution, pas par appel.

    Le nœud est reconstruit même si le matériau existe déjà : `NETTOYER_SCENE` n'efface
    que les objets, et le script se relance sur le .blend qu'il a lui-même produit. Se
    contenter de `materials.get()` figeait dans le fichier la toute première version de
    chaque matière — l'or y est resté un jaune diffus une régénération sur deux.
    """
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if name in _MATIERES_CABLEES:
        return mat, False
    _MATIERES_CABLEES.add(name)
    mat.use_nodes = True
    arbre = mat.node_tree
    arbre.nodes.clear()
    sortie = arbre.nodes.new("ShaderNodeOutputMaterial")
    sortie.location = (300, 0)
    bsdf = arbre.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    arbre.links.new(bsdf.outputs["BSDF"], sortie.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    return mat, True

def _noeud(mat, type_noeud, x, y=0):
    n = mat.node_tree.nodes.new(type_noeud)
    n.location = (x, y)
    return n

def _geometrie(mat):
    """Le nœud Geometry du matériau — un seul, quel que soit le nombre de lecteurs."""
    for n in mat.node_tree.nodes:
        if n.bl_idname == "ShaderNodeNewGeometry":
            return n
    return _noeud(mat, "ShaderNodeNewGeometry", -2100, 400)

def _position(mat):
    """Position du point ombré, en mètres, dans le repère du monde."""
    return _geometrie(mat).outputs["Position"]

def _normale(mat):
    """Normale du point ombré, dans le repère du monde."""
    return _geometrie(mat).outputs["Normal"]

def _calc(mat, operation, a, b=None, c=None):
    """Nœud Math d'une ligne : chaque entrée est un nombre ou une sortie de nœud.

    L'appareil ci-dessous fait une trentaine d'opérations, et les écrire nœud par nœud
    noyait la formule sous la plomberie. Le placement est automatique : ces nœuds ne
    sont jamais lus dans l'éditeur, c'est le code qui est la source.
    """
    rang = sum(1 for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeMath")
    n = _noeud(mat, "ShaderNodeMath", -1900 + 150 * (rang % 9), -420 - 170 * (rang // 9))
    n.operation = operation
    for i, v in enumerate((a, b, c)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            mat.node_tree.links.new(v, n.inputs[i])
    return n.outputs[0]

def _trainee(mat, largeur, longueur):
    """Bruit étiré en Z : les coulures que la pluie laisse sur un parement, larges de
    `largeur` amot et longues de `longueur`. Un bruit isotrope fait des taches, et une
    tache sur un mur se lit en défaut de matière ; une coulure se lit en pierre."""
    echelle = _noeud(mat, "ShaderNodeVectorMath", -1400, 480)
    echelle.operation = "MULTIPLY"
    echelle.inputs[1].default_value = (1 / m(largeur), 1 / m(largeur), 1 / m(longueur))
    mat.node_tree.links.new(_position(mat), echelle.inputs[0])
    bruit = _noeud(mat, "ShaderNodeTexNoise", -1200, 480)
    bruit.inputs["Scale"].default_value = 1.0
    bruit.inputs["Detail"].default_value = 4.0
    mat.node_tree.links.new(echelle.outputs["Vector"], bruit.inputs["Vector"])
    return bruit.outputs["Factor"]

def _grain(mat, taille):
    """Bruit de surface dont le motif fait `taille` amot. Renvoie la sortie Factor."""
    empiles = sum(1 for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeTexNoise")
    bruit = _noeud(mat, "ShaderNodeTexNoise", -1200, 260 + 220 * empiles)
    bruit.inputs["Scale"].default_value = 1.0 / m(taille)
    bruit.inputs["Detail"].default_value = 6.0
    mat.node_tree.links.new(_position(mat), bruit.inputs["Vector"])
    return bruit.outputs["Factor"]

def _creuser(mat, hauteur, force, profondeur):
    """Empile un Bump sur l'entrée Normal du Principled. Chaînable : le relief fin se
    pose par-dessus le relief large sans l'écraser.

    `force` est un nombre ou une sortie de nœud, comme les entrées de `_calc` : la
    porosité d'un bloc se tire avec sa finition, elle ne s'écrit pas.
    """
    liens = mat.node_tree.links
    bsdf = _bsdf(mat)
    bosse = _noeud(mat, "ShaderNodeBump", -260, -160 * len(bsdf.inputs["Normal"].links) - 160)
    if isinstance(force, (int, float)):
        bosse.inputs["Strength"].default_value = force
    else:
        liens.new(force, bosse.inputs["Strength"])
    bosse.inputs["Distance"].default_value = m(profondeur)
    liens.new(hauteur, bosse.inputs["Height"])
    for lien in list(bsdf.inputs["Normal"].links):
        liens.new(lien.from_socket, bosse.inputs["Normal"])
    liens.new(bosse.outputs["Normal"], bsdf.inputs["Normal"])

def material(name, rgb):
    """Couleur plate : pour un volume qui n'est qu'un repère, pas une matière."""
    mat, neuf = _neuf(name, rgb)
    if neuf:
        _bsdf(mat).inputs["Roughness"].default_value = 0.7
    return mat

def vitre(name, rgb):
    """Verre sombre : une baie vue du dehors ne rend que son reflet."""
    mat, neuf = _neuf(name, rgb)
    if neuf:
        _bsdf(mat).inputs["Roughness"].default_value = 0.08
    return mat
