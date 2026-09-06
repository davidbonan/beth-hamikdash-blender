"""
BEIT HAMIKDASH — BLOCKOUT GÉNÉRATIF (Second Temple, selon Mishna Middot)
=========================================================================
Usage : Blender 3.x / 4.x → onglet Scripting → New → coller → Run Script (Alt+P).
Le script crée une scène complète en volumes gris, à l'échelle, avec 15 caméras
liées à des marqueurs de timeline (la caméra active change automatiquement au rendu).

Conventions
- 1 ama = AMA mètres (0.48 par défaut, Rav 'Haïm Naeh). Changer la constante suffit.
- +X = EST, -X = OUEST, +Y = NORD, -Y = SUD, +Z = haut.
- Origine : angle du mur EST de l'Azara (x=0) sur l'axe central du Heikhal (y=0),
  au niveau du sol de l'Azara (z=0). Le bâtiment est à l'ouest (x négatif).
- Toutes les cotes ci-dessous sont en amot ; la conversion se fait dans les helpers.

Sources : Middot 1–5, Yoma 3–5, Rambam Hilkhot Beit HaBe'hira 1–4.
Les choix entre avis divergents sont signalés par "# CHOIX".
"""

import bpy
import math
import sys
import zlib
from mathutils import Vector

# ----------------------------------------------------------------------------
# PARAMÈTRES
# ----------------------------------------------------------------------------
AMA = 0.48            # mètres par ama  (alternatives : 0.525 Ritmeyer, 0.576 Hazon Ish)
FPS = 24
MENORA_DROITE = True  # CHOIX : True = branches droites en diagonale (Rambam/Rashi), False = courbes
PORTES_HEIKHAL_OUVERTES = True  # battants rabattus dans l'embrasure, comme pendant l'avoda
NETTOYER_SCENE = True

# Niveaux (en amot)
Z_HAR = -13.5   # Har HaBayit  (12 marches du 'Heil × 0.5 + 15 marches × 0.5 sous l'Azara)
Z_EZN = -7.5    # Ezrat Nashim
Z_AZ = 0.0      # Azara
Z_BAT = 6.0     # sol de l'Oulam / Heikhal (12 marches de 0.5)

# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
def m(v):
    return v * AMA

def get_collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col

def link_to(obj, colname):
    col = get_collection(colname)
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj

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

def _position(mat):
    """Position du point ombré, en mètres, dans le repère du monde. Une seule par matériau."""
    for n in mat.node_tree.nodes:
        if n.bl_idname == "ShaderNodeNewGeometry":
            return n.outputs["Position"]
    return _noeud(mat, "ShaderNodeNewGeometry", -1500, 400).outputs["Position"]

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
    pose par-dessus le relief large sans l'écraser."""
    liens = mat.node_tree.links
    bsdf = _bsdf(mat)
    bosse = _noeud(mat, "ShaderNodeBump", -260, -160 * len(bsdf.inputs["Normal"].links) - 160)
    bosse.inputs["Strength"].default_value = force
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

ASSISE = 1.0      # hauteur d'une assise de taille, en amot

def _assises(mat):
    """Découpe la surface en assises horizontales de `ASSISE` amot.

    Renvoie (numéro d'assise, parité, facteur de teinte). La parité est le
    « אבן יוצא ואבן נכנס » de *Baba Batra* 4a : une assise en léger débord, la suivante
    en léger retrait. C'est ce jeu-là — pas un placage — qui a fait renoncer Hérode à
    dorer le bâtiment, « cela ressemble aux vagues de la mer ».
    """
    liens = mat.node_tree.links
    axe = _noeud(mat, "ShaderNodeSeparateXYZ", -1500, 0)
    liens.new(_position(mat), axe.inputs["Vector"])
    rang = _noeud(mat, "ShaderNodeMath", -1340, 0)
    rang.operation = "DIVIDE"
    rang.inputs[1].default_value = m(ASSISE)
    liens.new(axe.outputs["Z"], rang.inputs[0])
    numero = _noeud(mat, "ShaderNodeMath", -1180, 120)
    numero.operation = "FLOOR"
    liens.new(rang.outputs[0], numero.inputs[0])
    parite = _noeud(mat, "ShaderNodeMath", -1020, 240)
    parite.operation = "MODULO"
    parite.inputs[1].default_value = 2.0
    liens.new(numero.outputs[0], parite.inputs[0])
    tirage = _noeud(mat, "ShaderNodeTexWhiteNoise", -1020, 120)
    tirage.noise_dimensions = '1D'
    liens.new(numero.outputs[0], tirage.inputs["W"])
    # Joint creusé au ras de chaque assise, puis le débord d'une assise sur deux.
    joint = _noeud(mat, "ShaderNodeMath", -1180, -140)
    joint.operation = "FRACT"
    liens.new(rang.outputs[0], joint.inputs[0])
    creux = _noeud(mat, "ShaderNodeValToRGB", -1020, -140)
    creux.color_ramp.elements[0].position = 0.0
    creux.color_ramp.elements[1].position = 0.07
    liens.new(joint.outputs[0], creux.inputs["Factor"])
    _creuser(mat, creux.outputs["Color"], 0.8, 0.06)
    _creuser(mat, parite.outputs[0], 0.9, 0.05)
    _creuser(mat, _grain(mat, 0.4), 0.6, 0.03)
    return numero.outputs[0], parite.outputs[0], tirage.outputs["Value"]


def pierre(name, rgb):
    """Calcaire en assises, chacune tirée un peu plus claire ou plus sombre que sa
    voisine — les « assises légèrement contrastées » de la fiche (§7), et la seule
    chose qui donne une échelle à un mur de 100 amot vu de mille."""
    mat, neuf = _neuf(name, rgb)
    if not neuf:
        return mat
    liens = mat.node_tree.links
    _bsdf(mat).inputs["Roughness"].default_value = 0.78
    _, parite, tirage = _assises(mat)
    # La teinte suit d'abord la parité des assises, le tirage ne fait que la salir.
    bruit = _noeud(mat, "ShaderNodeMath", -840, 60)
    bruit.operation = "MULTIPLY"
    bruit.inputs[1].default_value = 0.3
    liens.new(tirage, bruit.inputs[0])
    facteur = _noeud(mat, "ShaderNodeMath", -680, 160)
    facteur.operation = "MULTIPLY_ADD"
    facteur.inputs[1].default_value = 0.7
    liens.new(parite, facteur.inputs[0])
    liens.new(bruit.outputs[0], facteur.inputs[2])
    CONTRASTE = 0.07
    teinte = _noeud(mat, "ShaderNodeMixRGB", -500, 160)
    teinte.inputs["Color1"].default_value = (*(c * (1 - CONTRASTE) for c in rgb), 1.0)
    teinte.inputs["Color2"].default_value = (*(min(1.0, c * (1 + CONTRASTE)) for c in rgb), 1.0)
    liens.new(facteur.outputs[0], teinte.inputs["Factor"])
    liens.new(teinte.outputs["Color"], _bsdf(mat).inputs["Base Color"])
    return mat


# Les trois marbres d'Hérode (Baba Batra 4a, Soucca 51b) : shesh, marmara, kuchla —
# blanc, bleu-vert, jaune. Saturation très basse : Josèphe voyait de loin « une montagne
# couverte de neige », pas une mosaïque.
MARBRES_HERODE = ((0.93, 0.93, 0.91), (0.80, 0.86, 0.84), (0.92, 0.88, 0.76))


def marbre_herode(name):
    """Le corps du bâtiment, en assises alternées de trois marbres.

    C'est la seule surface que les sources refusent explicitement de dorer : Hérode
    voulut la plaquer d'or et les Sages l'en dissuadèrent (*Baba Batra* 4a). Elle porte
    donc la pierre, et l'or est réservé à ce que Josèphe et *Middot* 4:1 dorent — la
    façade et tout l'intérieur.
    """
    mat, neuf = _neuf(name, MARBRES_HERODE[0])
    if not neuf:
        return mat
    liens = mat.node_tree.links
    _bsdf(mat).inputs["Roughness"].default_value = 0.62   # marbre poli, pas calcaire
    _, _, tirage = _assises(mat)
    choix = _noeud(mat, "ShaderNodeValToRGB", -680, 160)
    rampe = choix.color_ramp
    rampe.interpolation = 'CONSTANT'
    rampe.elements[0].position = 0.0
    rampe.elements[0].color = (*MARBRES_HERODE[0], 1.0)
    rampe.elements[1].position = 1.0 / 3.0
    rampe.elements[1].color = (*MARBRES_HERODE[1], 1.0)
    rampe.elements.new(2.0 / 3.0).color = (*MARBRES_HERODE[2], 1.0)
    liens.new(tirage, choix.inputs["Factor"])
    liens.new(choix.outputs["Color"], _bsdf(mat).inputs["Base Color"])
    return mat


def _enduire(mat):
    _bsdf(mat).inputs["Roughness"].default_value = 0.92
    _creuser(mat, _grain(mat, 1.6), 1.0, 0.10)
    _creuser(mat, _grain(mat, 0.25), 0.8, 0.02)

def enduit(name, rgb):
    """Chaux : blanchie deux fois l'an sur des pierres non taillées (Middot 3:4). Ni
    joint ni assise — une masse presque monolithique, mais jamais lisse."""
    mat, neuf = _neuf(name, rgb)
    if neuf:
        _enduire(mat)
    return mat

def enduit_noirci(name, rgb, bande):
    """Chaux prise par le feu entre les deux cotes de `bande` (en amot) : le sommet du
    Mizbea'h est noirci par la ma'arakha (fiche §5). Sans lui l'autel était blanc de
    la base aux cornes, et le seul feu du film ne laissait aucune trace."""
    mat, neuf = _neuf(name, rgb)
    if not neuf:
        return mat
    _enduire(mat)
    liens = mat.node_tree.links
    axe = _noeud(mat, "ShaderNodeSeparateXYZ", -1300, -400)
    liens.new(_position(mat), axe.inputs["Vector"])
    montee = _noeud(mat, "ShaderNodeMapRange", -1100, -400)
    montee.inputs["From Min"].default_value = m(bande[0])
    montee.inputs["From Max"].default_value = m(bande[1])
    montee.clamp = True
    liens.new(axe.outputs["Z"], montee.inputs["Value"])
    suie = _noeud(mat, "ShaderNodeMixRGB", -900, -400)
    suie.inputs["Color1"].default_value = (*rgb, 1.0)
    suie.inputs["Color2"].default_value = (0.20, 0.18, 0.165, 1.0)
    liens.new(montee.outputs["Result"], suie.inputs["Factor"])
    liens.new(suie.outputs["Color"], _bsdf(mat).inputs["Base Color"])
    return mat

def dallage(name, rgb):
    """Sol en dalles : c'est le joint, à la lumière rasante de l'aube, qui donne au
    dallage sa fuyante — sans lui les cours sont un aplat et la perspective ne tient
    qu'aux murs.

    Le joint fait 0,05 ama et les dalles ont toutes la même valeur : à 1,2 cm il
    disparaissait passé vingt amot, et il ne restait qu'un tirage de ±5 % par dalle —
    des taches, que l'œil lisait en relief au lieu d'un pavage."""
    mat, neuf = _neuf(name, rgb)
    if not neuf:
        return mat
    liens = mat.node_tree.links
    _bsdf(mat).inputs["Roughness"].default_value = 0.85
    dalles = _noeud(mat, "ShaderNodeTexBrick", -900, 0)
    dalles.offset = 0.5
    dalles.inputs["Scale"].default_value = 1.0
    dalles.inputs["Brick Width"].default_value = m(3.0)
    dalles.inputs["Row Height"].default_value = m(3.0)
    dalles.inputs["Mortar Size"].default_value = m(0.05)
    dalles.inputs["Mortar Smooth"].default_value = 0.25
    dalles.inputs["Color1"].default_value = (*(c * 0.985 for c in rgb), 1.0)
    dalles.inputs["Color2"].default_value = (*(min(1.0, c * 1.015) for c in rgb), 1.0)
    dalles.inputs["Mortar"].default_value = (*(c * 0.7 for c in rgb), 1.0)
    liens.new(_position(mat), dalles.inputs["Vector"])
    liens.new(dalles.outputs["Color"], _bsdf(mat).inputs["Base Color"])
    _creuser(mat, dalles.outputs["Factor"], 1.0, 0.08)
    _creuser(mat, _grain(mat, 0.3), 0.3, 0.01)
    return mat

def metal(name, rgb, rugosite):
    """Or et bronze : un diffus jaune ne renvoie pas la façade ni la flamme de la
    Menora. La rugosité est brouillée au bruit — l'or du Temple est martelé, pas poli
    au miroir, et un métal parfaitement lisse ne rend qu'un point spéculaire."""
    mat, neuf = _neuf(name, rgb)
    if not neuf:
        return mat
    liens = mat.node_tree.links
    _bsdf(mat).inputs["Metallic"].default_value = 1.0
    trame = _noeud(mat, "ShaderNodeMapRange", -900, 260)
    trame.inputs["To Min"].default_value = max(0.05, rugosite - 0.08)
    trame.inputs["To Max"].default_value = min(1.0, rugosite + 0.08)
    liens.new(_grain(mat, 0.12), trame.inputs["Value"])
    liens.new(trame.outputs["Result"], _bsdf(mat).inputs["Roughness"])
    _creuser(mat, _grain(mat, 0.09), 0.5, 0.01)
    return mat

def marbre(name, rgb):
    """Marbre veiné : les huit tables du Beit HaMitba'haïm (Middot 3:5) sont le sujet
    du plan 7a, et en chaux elles ne se distinguaient ni du sol ni de l'autel."""
    mat, neuf = _neuf(name, rgb)
    if not neuf:
        return mat
    liens = mat.node_tree.links
    _bsdf(mat).inputs["Roughness"].default_value = 0.28
    veines = _noeud(mat, "ShaderNodeTexWave", -900, 0)
    veines.bands_direction = 'DIAGONAL'
    veines.inputs["Scale"].default_value = 1.0 / m(2.5)
    veines.inputs["Distortion"].default_value = 12.0
    veines.inputs["Detail"].default_value = 3.0
    liens.new(_position(mat), veines.inputs["Vector"])
    filet = _noeud(mat, "ShaderNodeMixRGB", -700, 0)
    filet.inputs["Color1"].default_value = (*rgb, 1.0)
    filet.inputs["Color2"].default_value = (*(c * 0.72 for c in rgb), 1.0)
    liens.new(veines.outputs["Factor"], filet.inputs["Factor"])
    liens.new(filet.outputs["Color"], _bsdf(mat).inputs["Base Color"])
    return mat

def bois(name, rgb):
    """Cèdre des plafonds et chêne des maltera'ot (Middot 3:7, Josèphe) : le fil court
    le long de l'axe est-ouest, celui des poutres."""
    mat, neuf = _neuf(name, rgb)
    if not neuf:
        return mat
    liens = mat.node_tree.links
    _bsdf(mat).inputs["Roughness"].default_value = 0.62
    fil = _noeud(mat, "ShaderNodeTexWave", -900, 0)
    fil.bands_direction = 'X'
    fil.inputs["Scale"].default_value = 1.0 / m(0.35)
    fil.inputs["Distortion"].default_value = 6.0
    fil.inputs["Detail"].default_value = 4.0
    liens.new(_position(mat), fil.inputs["Vector"])
    veine = _noeud(mat, "ShaderNodeMixRGB", -700, 0)
    veine.inputs["Color1"].default_value = (*(c * 0.75 for c in rgb), 1.0)
    veine.inputs["Color2"].default_value = (*rgb, 1.0)
    liens.new(fil.outputs["Factor"], veine.inputs["Factor"])
    liens.new(veine.outputs["Color"], _bsdf(mat).inputs["Base Color"])
    _creuser(mat, fil.outputs["Factor"], 0.6, 0.02)
    return mat

def etoffe(name, rgb):
    """Parokhet, bigdei lavan, laine de la foule : mat, avec le halo rasant d'un tissu."""
    mat, neuf = _neuf(name, rgb)
    if not neuf:
        return mat
    bsdf = _bsdf(mat)
    bsdf.inputs["Roughness"].default_value = 0.88
    bsdf.inputs["Sheen Weight"].default_value = 0.35
    bsdf.inputs["Sheen Roughness"].default_value = 0.4
    _creuser(mat, _grain(mat, 0.06), 0.5, 0.006)
    return mat

def braise(name):
    """Charbons de la ma'arakha : le noir se fend sur un fond incandescent. La boîte
    était noire et éteinte, et la colonne de fumée montait d'un autel mort."""
    mat, neuf = _neuf(name, (0.05, 0.02, 0.01))
    if not neuf:
        return mat
    liens = mat.node_tree.links
    bsdf = _bsdf(mat)
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.3, 0.05, 1.0)
    feu = _noeud(mat, "ShaderNodeMapRange", -900, 0)
    feu.inputs["From Min"].default_value = 0.45
    feu.inputs["From Max"].default_value = 0.72
    feu.inputs["To Max"].default_value = 8.0
    feu.clamp = True
    liens.new(_grain(mat, 0.3), feu.inputs["Value"])
    liens.new(feu.outputs["Result"], bsdf.inputs["Emission Strength"])
    _creuser(mat, _grain(mat, 0.15), 0.6, 0.02)
    return mat

def nuee(name, rgb):
    """Proxy de fumée. Il reste OPAQUE à dessein : l'export mesure la plage de la passe
    Z sur ce que la géométrie écrit, et un volume ne l'écrit pas — la colonne
    disparaîtrait de la carte de profondeur, qui est ce qui la fait tenir en place
    d'une image à l'autre. Seule la matière dit « fumée ».
    """
    mat, neuf = _neuf(name, rgb)
    if not neuf:
        return mat
    liens = mat.node_tree.links
    bsdf = _bsdf(mat)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.05
    volute = _noeud(mat, "ShaderNodeMixRGB", -700, 0)
    volute.inputs["Color1"].default_value = (*(c * 0.62 for c in rgb), 1.0)
    volute.inputs["Color2"].default_value = (*rgb, 1.0)
    liens.new(_grain(mat, 4.0), volute.inputs["Factor"])
    liens.new(volute.outputs["Color"], bsdf.inputs["Base Color"])
    _creuser(mat, _grain(mat, 1.5), 1.0, 0.9)
    return mat

MAT_PIERRE = lambda: pierre("Pierre_claire", (0.85, 0.82, 0.74))
MAT_OR = lambda: metal("Or", (1.0, 0.76, 0.33), 0.3)
MAT_BRONZE = lambda: metal("Bronze", (0.66, 0.44, 0.22), 0.45)
MAT_CHAUX = lambda: enduit("Chaux_blanche", (0.95, 0.95, 0.92))
MAT_CHAUX_FEU = lambda: enduit_noirci("Chaux_noircie", (0.95, 0.95, 0.92), (Z_AZ + 7.5, Z_AZ + 10.5))
MAT_TISSU = lambda: etoffe("Parokhet", (0.2, 0.2, 0.55))
MAT_SOL = lambda: dallage("Sol", (0.75, 0.72, 0.65))
MAT_LIN = lambda: etoffe("Lin_blanc", (0.88, 0.87, 0.83))     # bigdei lavan des kohanim
MAT_BETE = lambda: material("Robe_animale", (0.32, 0.26, 0.22))
MAT_KETORET = lambda: material("Ketoret", (0.42, 0.30, 0.16))
MAT_MARBRE = lambda: marbre("Marbre_blanc", (0.93, 0.92, 0.89))
MAT_MARBRE_HERODE = lambda: marbre_herode("Marbre_Herode")
# L'or des parois est un placage martelé sur de la pierre, pas un ustensile tourné :
# plus mat que la Menora, sinon un mur entier ne rend qu'un point spéculaire.
MAT_OR_PLAQUE = lambda: metal("Or_plaque", (1.0, 0.76, 0.33), 0.4)
MAT_CEDRE = lambda: bois("Cedre", (0.44, 0.25, 0.14))
MAT_CHENE = lambda: bois("Chene", (0.36, 0.25, 0.15))

# ----------------------------------------------------------------------------
# VOLUMES
#   Aucun opérateur : `bpy.ops.mesh.primitive_*` réévalue le graphe de dépendances à
#   chaque appel, et le coût est quadratique en nombre d'objets (mesuré : 0,44 s pour
#   200 cubes, 11,9 s pour 800, 52,6 s pour 1600). Les milliers de volumes de la
#   scène se posent donc directement en `bpy.data`.
#   Les faces sont écrites dans le sens direct vu de l'extérieur : c'est la passe
#   Normal qui conditionne l'i2i, et une normale retournée y fait un trou.
# ----------------------------------------------------------------------------
def _objet(name, data, col, mat=None):
    """Objet neuf posé dans sa collection, sans passer par un opérateur."""
    o = bpy.data.objects.new(name, data)
    if mat is not None:
        data.materials.append(mat)
    return link_to(o, col)

def mesh_from_pydata(name, verts, faces, col, mat=None):
    """Maillage à partir de sommets en amot et de faces indexées."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(m(c) for c in v) for v in verts], [], faces)
    me.update()
    return _objet(name, me, col, mat or MAT_PIERRE())

def _face(indices):
    """Face débarrassée de ses sommets répétés — pointes de cône et pôles de sphère."""
    return [i for k, i in enumerate(indices) if i != indices[k - 1]]

def _cercle(x, y, r, verts):
    """Polygone régulier inscrit, sens direct, premier sommet à midi (amot).

    `sin` en x et `cos` en y, puis la liste retournée : c'est le calcul exact de
    `primitive_cylinder_add` — midi, et non trois heures —, relu dans l'autre sens
    pour que les faces restent dans le sens direct. Écrit autrement (`cos(π/2 + a)`),
    il donnerait les mêmes points au dernier bit près, et le blockout n'aurait plus
    exactement les sommets qu'il avait.
    """
    return [(x + r * math.sin(2 * math.pi * k / verts),
             y + r * math.cos(2 * math.pi * k / verts)) for k in range(verts)][::-1]

def box(name, x0, x1, y0, y1, z0, z1, col="20_Azara", mat=None):
    """Boîte définie par ses bornes en amot."""
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    z0, z1 = min(z0, z1), max(z0, z1)
    verts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
             [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return mesh_from_pydata(name, verts, faces, col, mat)

def prism(name, poly, z0, z1, col, mat=None):
    """Extrusion verticale d'un polygone 2D (liste de (x,y) en amot)."""
    n = len(poly)
    verts = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    return mesh_from_pydata(name, verts, faces, col, mat)

def cyl(name, x, y, z0, z1, r, col="20_Azara", mat=None, verts=32):
    return prism(name, _cercle(x, y, r, verts), min(z0, z1), max(z0, z1), col, mat)

def plaque(name, quad, epaisseur, col, mat=None):
    """Plaque mince : un quadrilatère plan (4 points en amot, sens direct vu du côté
    où elle s'épaissit) extrudé de `epaisseur` le long de sa normale."""
    a, b, d = (Vector(q) for q in (quad[0], quad[1], quad[3]))
    n = (b - a).cross(d - a).normalized() * epaisseur
    verts = list(quad) + [tuple(Vector(q) + n) for q in quad]
    faces = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
             [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return mesh_from_pydata(name, verts, faces, col, mat)

def revolution(name, x, y, z0, profil, col="20_Azara", mat=None, verts=32):
    """Surface de révolution autour de la verticale passant par (x, y).

    `profil` : suite de (rayon, hauteur au-dessus de z0) en amot, parcourue dans
    l'ordre. Un rayon nul fait une pointe. Se lit paroi extérieure en montant puis,
    si elle redescend, paroi intérieure en descendant : c'est ce sens de parcours qui
    garde les normales tournées vers l'air, dehors comme dans le creux.
    """
    anneaux = [_cercle(x, y, r, verts) if r else [(x, y)] for r, _ in profil]
    sommets, debut = [], []
    for (_, dz), anneau in zip(profil, anneaux):
        debut.append(len(sommets))
        sommets += [(px, py, z0 + dz) for px, py in anneau]
    faces = []
    if len(anneaux[0]) > 1:
        faces.append(list(range(verts))[::-1])
    if len(anneaux[-1]) > 1:
        faces.append(list(range(debut[-1], debut[-1] + verts)))
    for a in range(len(profil) - 1):
        n0, n1 = len(anneaux[a]), len(anneaux[a + 1])
        for k in range(verts):
            faces.append(_face([debut[a] + k % n0, debut[a] + (k + 1) % n0,
                                debut[a + 1] + (k + 1) % n1, debut[a + 1] + k % n1]))
    return mesh_from_pydata(name, sommets, faces, col, mat)

def cone(name, x, y, z0, z1, r0, r1, col="20_Azara", mat=None, verts=32):
    """Tronc de cône : rayon r0 en bas, r1 en haut. Un rayon nul donne une pointe."""
    z0, z1 = min(z0, z1), max(z0, z1)
    return revolution(name, x, y, z0, [(r0, 0), (r1, z1 - z0)], col, mat, verts)

def colonne(name, x, y, z0, z1, r, col="00_HarHabayit", mat=None):
    """Colonne de portique : base, fût, chapiteau évasé (Josèphe, colonnades du Har
    HaBayit). Un fût nu ne donnait ni assise au sol ni rupture de silhouette en haut
    de cadre — les deux choses qu'un travelling de colonnade (plan 2) fait voir
    défiler, et les deux qui entrent dans la passe Depth."""
    cyl(f"{name}_base", x, y, z0, z0 + 1.0, r * 1.3, col, mat, verts=24)
    cyl(f"{name}_fut", x, y, z0 + 1.0, z1 - 2.0, r, col, mat)
    cone(f"{name}_chapiteau", x, y, z1 - 2.0, z1, r, r * 1.45, col, mat, verts=24)

def sphere(name, x, y, z, r, col="20_Azara", mat=None, segs=16):
    """Sphère UV : segs méridiens, segs // 2 tranches, pôles en éventail."""
    anneaux = max(2, segs // 2)
    verts = [(x, y, z + r)]
    for i in range(1, anneaux):
        phi = math.pi * i / anneaux
        verts += [(px, py, z + r * math.cos(phi))
                  for px, py in _cercle(x, y, r * math.sin(phi), segs)]
    verts.append((x, y, z - r))
    sud = len(verts) - 1

    def indice(i, k):
        if i == 0:
            return 0
        if i == anneaux:
            return sud
        return 1 + (i - 1) * segs + k % segs

    faces = [_face([indice(i, k), indice(i + 1, k),
                    indice(i + 1, k + 1), indice(i, k + 1)])
             for i in range(anneaux) for k in range(segs)]
    return mesh_from_pydata(name, verts, faces, col, mat)

def tore(name, x, y, z, R, r, col, mat=None, rotation=(0, 0, 0), majeur=48, mineur=12):
    """Tore : R rayon du cercle porteur, r rayon du tube (amot).

    Seul volume dont la pose reste sur l'objet et non dans le maillage : le cercle
    porteur se décrit à plat, la rotation le redresse.
    """
    verts = []
    for i in range(majeur):
        th = 2 * math.pi * i / majeur
        for j in range(mineur):
            ph = 2 * math.pi * j / mineur
            d = R + r * math.cos(ph)
            verts.append((d * math.cos(th), d * math.sin(th), r * math.sin(ph)))
    faces = [[i * mineur + j, (i + 1) % majeur * mineur + j,
              (i + 1) % majeur * mineur + (j + 1) % mineur, i * mineur + (j + 1) % mineur]
             for i in range(majeur) for j in range(mineur)]
    o = mesh_from_pydata(name, verts, faces, col, mat)
    o.location = (m(x), m(y), m(z))
    o.rotation_euler = rotation
    return o

def wedge_ramp(name, x0, x1, y_bas, y_haut, z0, z1, col, mat=None):
    """Rampe montant de y_bas (z0) vers y_haut (z1), largeur x0..x1."""
    verts = [(x0, y_bas, z0), (x1, y_bas, z0), (x1, y_haut, z0), (x0, y_haut, z0),
             (x1, y_haut, z1), (x0, y_haut, z1)]
    faces = [[0, 1, 2, 3][::-1], [0, 1, 4, 5], [1, 2, 4], [3, 0, 5], [2, 3, 5, 4]]
    return mesh_from_pydata(name, verts, faces, col, mat)

def mur_perce(name, x0, x1, y0, y1, z0, z1, col, portes, h_porte):
    """Mur droit percé d'ouvertures : segments pleins, plus un linteau sur chaque porte.

    `portes` : liste de (centre, largeur) le long du grand côté du mur.
    """
    long_x = (x1 - x0) >= (y1 - y0)
    a0, a1 = (x0, x1) if long_x else (y0, y1)
    bornes = [a0]
    for centre, largeur in sorted(portes):
        bornes += [centre - largeur / 2, centre + largeur / 2]
    bornes.append(a1)

    def morceau(suffixe, u0, u1, zb, zh):
        if long_x:
            box(f"{name}_{suffixe}", u0, u1, y0, y1, zb, zh, col)
        else:
            box(f"{name}_{suffixe}", x0, x1, u0, u1, zb, zh, col)

    for k in range(0, len(bornes) - 1, 2):
        morceau(f"plein_{k // 2}", bornes[k], bornes[k + 1], z0, z1)
    for centre, largeur in portes:
        morceau(f"linteau_{centre:+.0f}", centre - largeur / 2, centre + largeur / 2,
                z0 + h_porte, z1)


# Appareil des lishkot, en amot. Aucune source ne décrit l'élévation des chambres du
# pourtour : ces cotes sont un CHOIX, dicté par ce que le plan 1 peut montrer. Le
# soleil de l'aube y est à 12° au-dessus de l'horizon et à 15° de l'axe de la caméra,
# donc dans son dos : les faces est que le plan regarde sont éclairées de face, un
# ressaut vertical n'y creuse aucune ombre — seul un débord horizontal en jette, et
# 1,5 ama de saillie sous un soleil de 12° font 7 amot d'ombre sur le mur. D'où trois
# lignes horizontales plutôt que des pilastres, et des baies assez profondes pour
# rester noires de face.
LISHKA_DEBORD = 1.5       # saillie du socle, du bandeau et de la corniche
LISHKA_SOCLE = 4
LISHKA_CORNICHE = 4
LISHKA_BANDEAU = 2
LISHKA_PAREMENT = 2       # profondeur d'embrasure : en deçà, la baie n'est pas noire
# Middot 2:3 : « כָּל הַפְּתָחִים וְהַשְּׁעָרִים… גָּבְהָן עֶשְׂרִים אַמָּה וְרָחְבָּן עֶשֶׂר ». Le Rambam
# (Beit HaBe'hira 5:5) ne rapporte la cote qu'aux **portes de l'Azara** — et c'est la
# seule lecture tenable ici : une porte de 20 amot n'entre pas dans une chambre de 15.
# D'où deux cotes : PORTE_SHAAR pour ce que la Mishna appelle un שער (les deux du Beit
# HaMoked, Middot 1:7 ; celle du corps de porte sur le 'Heil, Middot 1:5), et
# PORTE_LISHKA — cote inventée, CHOIX — pour les chambres.
PORTE_SHAAR = (10, 20)
PORTE_LISHKA = (8, 16)
LISHKA_BAIE = 3           # largeur des fenêtres hautes
MAAKE_H, MAAKE_EP = 3, 1.5
ROVAD_H, ROVAD_HAUT = 3, 4    # hauteur d'un rovad, et celle du rovad du sommet
ROVAD_NU, ROVAD_SAILLIE = 1, 1


def paroi_percee(name, x0, x1, y0, y1, z0, z1, col, mat, baies):
    """Paroi percée de baies quelconques `(u0, u1, zb, zh)` le long de son grand côté.

    `mur_perce` ne sait ouvrir que des portes posées au sol et de même hauteur ; il
    faut ici mêler une porte et des fenêtres hautes dans la même paroi.
    """
    horizontal = (x1 - x0) >= (y1 - y0)
    a0, a1 = (x0, x1) if horizontal else (y0, y1)

    def pose(suffixe, u0, u1, zb, zh):
        if u1 - u0 <= 0 or zh - zb <= 0:
            return
        if horizontal:
            box(f"{name}_{suffixe}", u0, u1, y0, y1, zb, zh, col, mat)
        else:
            box(f"{name}_{suffixe}", x0, x1, u0, u1, zb, zh, col, mat)

    bord = a0
    for k, (u0, u1, zb, zh) in enumerate(sorted(baies)):
        pose(f"trumeau_{k}", bord, u0, z0, z1)
        pose(f"allege_{k}", u0, u1, z0, zb)
        pose(f"linteau_{k}", u0, u1, zh, z1)
        bord = u1
    pose("trumeau_fin", bord, a1, z0, z1)


def lishka(name, x0, x1, y0, y1, z0, z1, col, portes, mat=None):
    """Chambre du pourtour : socle, corps percé de baies, bandeau, corniche.

    Posée en boîte nue, une lishka ne se lit pas : à 750 amot elle n'a ni pied, ni
    sommet, ni ombre sur elle-même, et le styliseur en fait un rocher. Les trois
    lignes en saillie donnent l'assise et le couronnement, les baies l'échelle.

    `portes` : liste de `(face, largeur, hauteur)`, face parmi "S", "N", "O", "E".
    Deux portes sur des faces opposées font une **traversée** et non deux culs-de-sac :
    le noyau s'ouvre entre elles. C'est le Beit HaMoked, où l'on entre du 'Heil et
    ressort dans l'Azara (Middot 1:7), et la Lishkat HaGazit, « חֶצְיָהּ בַּקֹּדֶשׁ
    וְחֶצְיָהּ בַּחוֹל, שְׁנֵי פְתָחִים הָיוּ לָהּ » (Yoma 25a ; Rambam, Beit HaBe'hira 5:17).
    """
    zs, zc = z0 + LISHKA_SOCLE, z1 - LISHKA_CORNICHE
    debords = (x0 - LISHKA_DEBORD, x1 + LISHKA_DEBORD,
               y0 - LISHKA_DEBORD, y1 + LISHKA_DEBORD)
    portes = [(f, l, min(h, zc - zs - 4)) for f, l, h in portes]
    z_bandeau = zs + max(h for _, _, h in portes) + 1
    for suffixe, zb, zh in (("socle", z0, zs), ("corniche", zc, z1),
                            ("bandeau", z_bandeau, z_bandeau + LISHKA_BANDEAU)):
        box(f"{name}_{suffixe}", *debords, zb, zh, col, mat)

    d = LISHKA_PAREMENT
    _noyau(name, x0 + d, x1 - d, y0 + d, y1 - d, zs, zc, col, mat, portes)
    # Les parements est et ouest s'arrêtent avant les angles : sinon leurs faces
    # extérieures seraient coplanaires avec celles des parements nord et sud.
    haut_bandeau = z_bandeau + LISHKA_BANDEAU
    z_baie0 = haut_bandeau + (zc - haut_bandeau) * 0.25
    z_baie1 = haut_bandeau + (zc - haut_bandeau) * 0.75
    for face, bornes, a0, a1 in (("S", (x0, x1, y0, y0 + d), x0, x1),
                                 ("N", (x0, x1, y1 - d, y1), x0, x1),
                                 ("O", (x0, x0 + d, y0 + d, y1 - d), y0 + d, y1 - d),
                                 ("E", (x1 - d, x1, y0 + d, y1 - d), y0 + d, y1 - d)):
        baies = []
        for f, larg, haut in portes:
            if f == face:
                c = (a0 + a1) / 2
                baies.append((c - larg / 2, c + larg / 2, zs, zs + haut))
        n = max(2, round((a1 - a0) / 12))
        for k in range(n) if z_baie1 - z_baie0 >= 2 else ():
            c = a0 + (a1 - a0) * (k + 0.5) / n
            u0, u1 = c - LISHKA_BAIE / 2, c + LISHKA_BAIE / 2
            if any(u1 > b0 and u0 < b1 for b0, b1, _, _ in baies):
                continue
            baies.append((u0, u1, z_baie0, z_baie1))
        paroi_percee(f"{name}_{face}", *bornes, zs, zc, col, mat, baies)


def _noyau(name, x0, x1, y0, y1, z0, z1, col, mat, portes):
    """Masse intérieure de la lishka, ouverte d'un couloir si deux portes s'opposent."""
    faces = {f: (l, h) for f, l, h in portes}
    for couple, axe in ((("N", "S"), "x"), (("E", "O"), "y")):
        if not faces.keys() >= set(couple):
            continue
        larg = min(faces[f][0] for f in couple)
        haut = min(faces[f][1] for f in couple)
        a0, a1 = (x0, x1) if axe == "x" else (y0, y1)
        c = (a0 + a1) / 2
        tranches = [("cote_0", a0, c - larg / 2, z0, z1),
                    ("cote_1", c + larg / 2, a1, z0, z1),
                    ("linteau", c - larg / 2, c + larg / 2, z0 + haut, z1)]
        for suffixe, u0, u1, zb, zh in tranches:
            if axe == "x":
                box(f"{name}_noyau_{suffixe}", u0, u1, y0, y1, zb, zh, col, mat)
            else:
                box(f"{name}_noyau_{suffixe}", x0, x1, u0, u1, zb, zh, col, mat)
        return
    box(f"{name}_noyau", x0, x1, y0, y1, z0, z1, col, mat)


def terrasse_de_porte(name, x0, x1, y0, y1, z, chambre, col, mat=None):
    """Toit d'un corps de porte : dalle, garde-corps sur le pourtour resté libre.

    C'est elle qui assoit la chambre haute — l'aliyah de Middot 1:5 et de Tamid 1:1.
    `chambre` : l'intervalle en x qu'occupe cette chambre ; le garde-corps s'arrête
    contre elle, deux parois coplanaires clignoteraient.
    """
    box(f"{name}_terrasse", x0, x1, y0, y1, z, z + 1, col, mat)
    bords = [("ouest", x0, x0 + 1, y0, y1), ("est", x1 - 1, x1, y0, y1)]
    for cote, b0, b1 in (("sud", y0, y0 + 1), ("nord", y1 - 1, y1)):
        bords += [(f"{cote}_O", x0 + 1, chambre[0], b0, b1),
                  (f"{cote}_E", chambre[1], x1 - 1, b0, b1)]
    for suffixe, a, b, c, e in bords:
        box(f"{name}_garde_{suffixe}", a, b, c, e, z + 1, z + 3, col, mat)


def aliyah(name, x0, x1, y0, y1, z0, h, col, fenetre, mat=None):
    """Chambre haute posée sur un corps de porte, murs d'une ama, une fenêtre.

    « בֵּית אַבְטִינָס וּבֵית הַנִּיצוֹץ הָיוּ עֲלִיּוֹת » (Middot 1:1 ; Tamid 1:1) : ce sont
    des étages, et un étage a un rez-de-chaussée. `fenetre` : (face, u0, u1) — la
    face percée et l'intervalle en x de la baie, qui va de 3 à 7 amot du sol.
    """
    face, f0, f1 = fenetre
    box(f"{name}_toit", x0, x1, y0, y1, z0 + h - 1, z0 + h, col, mat)
    box(f"{name}_mur_ouest", x0, x0 + 1, y0, y1, z0, z0 + h, col, mat)
    box(f"{name}_mur_est", x1 - 1, x1, y0, y1, z0, z0 + h, col, mat)
    for cote, b0, b1 in (("sud", y0, y0 + 1), ("nord", y1 - 1, y1)):
        if cote != face:
            box(f"{name}_mur_{cote}", x0, x1, b0, b1, z0, z0 + h, col, mat)
            continue
        box(f"{name}_mur_{cote}_O", x0, f0, b0, b1, z0, z0 + h, col, mat)
        box(f"{name}_mur_{cote}_E", f1, x1, b0, b1, z0, z0 + h, col, mat)
        box(f"{name}_fenetre_appui", f0, f1, b0, b1, z0, z0 + 3, col, mat)
        box(f"{name}_fenetre_linteau", f0, f1, b0, b1, z0 + 7, z0 + h, col, mat)


def maake(name, x0, x1, y0, y1, z, col, mat=None):
    """Garde-corps de toit — « ועשית מעקה לגגך » (Deut. 22:8). Rambam, Rotzea'h 11:2 :
    « גגך » exclut ce qui n'est pas fait pour l'habitation. Ces deux-là le sont — les
    anciens de la maison paternelle dorment au Beit HaMoked (Middot 1:8) et le Cohen
    Gadol habite sept jours la Lishkat Parhedrin (Yoma 1:1), au point qu'elle est
    tenue à la mezouza (Yoma 11a). Hauteur minimale 10 tefa'him (Rotzea'h 11:3) ;
    3 amot est un CHOIX de lisibilité : c'est le décrochement qui, au-dessus de la
    corniche en saillie, donne au toit sa silhouette en gradin.
    """
    for suffixe, a, b, c, e in (("S", x0, x1, y0, y0 + MAAKE_EP),
                                ("N", x0, x1, y1 - MAAKE_EP, y1),
                                ("O", x0, x0 + MAAKE_EP, y0 + MAAKE_EP, y1 - MAAKE_EP),
                                ("E", x1 - MAAKE_EP, x1, y0 + MAAKE_EP, y1 - MAAKE_EP)):
        box(f"{name}_maake_{suffixe}", a, b, c, e, z, z + MAAKE_H, col, mat)


def bandes_rovad(z0, z1):
    """Découpe une hauteur de mur en bandeaux (zb, zh) : 1 ama de nu, 3 de saillie.

    Rambam, Beit HaBe'hira 4:9 : « וְכֵן סָבִיב לְכָתְלֵי הָאוּלָם מִלְּמַטָּה עַד לְמַעְלָה כָּךְ הָיוּ
    אַמָּה אַחַת חָלָק וְרֹבֶד שָׁלֹשׁ אַמּוֹת… וְרֹבֶד הָעֶלְיוֹן הָיָה רָחְבּוֹ אַרְבַּע אַמּוֹת ». Le compte
    ne tombe pas juste sur 94 amot de mur ; le reste va au nu du bas, qui fait socle.
    """
    pas = ROVAD_NU + ROVAD_H
    n = int((z1 - z0 - ROVAD_HAUT) // pas)
    z = z1 - ROVAD_HAUT - n * pas
    bandes = []
    for _ in range(n):
        bandes.append((z + ROVAD_NU, z + pas))
        z += pas
    bandes.append((z1 - ROVAD_HAUT, z1))
    return bandes


def _hors_reserve(a0, a1, zb, zh, reserve):
    """Ce qui reste de [a0, a1] une fois retirés les intervalles que ce bandeau croise."""
    bord, morceaux = a0, []
    for r0, r1 in sorted((r0, r1) for r0, r1, rb, rh in reserve if zh > rb and zb < rh):
        if r0 > bord:
            morceaux.append((bord, min(r0, a1)))
        bord = max(bord, r1)
    if bord < a1:
        morceaux.append((bord, a1))
    return [(u0, u1) for u0, u1 in morceaux if u1 > u0]


def rovadim(name, base, normale, a0, a1, z0, z1, col, mat, reserve=()):
    """Ceinture de bandeaux en saillie sur une face de mur, de bas en haut.

    Le Kessef Mishneh (sur Beit HaBe'hira 4:9) rapporte la lecture du Rambam sur
    Middot 3:6 : le rovad sort du nu du mur « כְּגוֹן כְּצוֹצְרָא », comme un balcon ; le
    Steinsaltz, « בְּלִיטַת בְּנִיָּה בְּגֹבַהּ שָׁלֹשׁ אַמּוֹת ». Aucune source ne chiffre la saillie :
    ROVAD_SAILLIE est un CHOIX, calé sur le pas de 1 ama des amaltraot.

    `base` : la cote du nu du mur ; `normale` : (±1, 0) ou (0, ±1), le dehors.
    `reserve` : les (a0, a1, zb, zh) que les bandeaux contournent — la baie et les
    amaltraot, que ce mur porte déjà.
    """
    nx, ny = normale
    for k, (zb, zh) in enumerate(bandes_rovad(z0, z1)):
        for j, (u0, u1) in enumerate(_hors_reserve(a0, a1, zb, zh, reserve)):
            b0, b1 = sorted((base, base + (nx or ny) * ROVAD_SAILLIE))
            nom = f"{name}_rovad_{k:02d}_{j}"
            if nx:
                box(nom, b0, b1, u0, u1, zb, zh, col, mat)
            else:
                box(nom, u0, u1, b0, b1, zb, zh, col, mat)



def cyl_between(name, p0, p1, r, col, mat=None, verts=16):
    """Cylindre entre deux points (amot)."""
    a, b = Vector([m(c) for c in p0]), Vector([m(c) for c in p1])
    d = b - a
    demi = d.length / AMA / 2
    o = prism(name, _cercle(0, 0, r, verts), -demi, demi, col, mat or MAT_OR())
    o.location = (a + b) / 2
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o

def _poser(pieces, x, y, z0, lacet):
    """Pièces bâties à l'origine, posées en (x, y, z0) amot et tournées de `lacet`
    autour de la verticale — silhouettes et keruvim."""
    for piece in pieces:
        piece.location = (m(x), m(y), m(z0))
        piece.rotation_euler = (0, 0, lacet)

def fcurves_of(obj):
    """F-curves de l'action de obj. Blender <4.4 : action.fcurves ; >=4.4 : actions à slots."""
    ad = obj.animation_data
    act = ad.action if ad else None
    if act is None:
        return []
    if hasattr(act, "fcurves"):
        return act.fcurves
    slot = ad.action_slot
    for layer in act.layers:
        for strip in layer.strips:
            cb = strip.channelbag(slot) if slot else None
            if cb:
                return cb.fcurves
    return []


def plage(debut, fin, pas):
    """Bornes incluses, pas fractionnaire — range() ne prend que des entiers."""
    return [debut + k * pas for k in range(int((fin - debut) / pas) + 1)]

def alea(cle, k=0):
    """Suite déterministe dans [0, 1), tirée du nom : même scène à chaque construction.

    `hash()` est salé par processus et `random` dépend de l'ordre d'appel ; un CRC du
    nom donne le même désordre d'une reconstruction à l'autre, et le même quel que
    soit le plan rendu.
    """
    return (zlib.crc32(f"{cle}#{k}".encode()) % 10007) / 10007


def empty(name, x, y, z, col="90_Cameras"):
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = 'PLAIN_AXES'
    o.empty_display_size = m(1)
    o.location = (m(x), m(y), m(z))
    return link_to(o, col)

def lampe(name, type_lampe, location):
    """Lampe posée dans la collection maître — à charge de l'appelant de la ranger.

    `location` est en mètres : ces lampes se posent sur des repères déjà convertis.
    """
    o = bpy.data.objects.new(name, bpy.data.lights.new(name, type_lampe))
    o.location = location
    bpy.context.scene.collection.objects.link(o)
    return o

def camera(name, location):
    """Caméra dans la collection maître, en mètres."""
    o = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    o.location = location
    bpy.context.scene.collection.objects.link(o)
    return o

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

# ----------------------------------------------------------------------------
# 00 — HAR HABAYIT (500 × 500), Middot 2:1 : sud > est > nord > ouest
# ----------------------------------------------------------------------------
HX0, HX1 = -217, 283      # ouest 30 amot derrière l'Azara ; est 143 devant l'Ezrat Nashim
HY0, HY1 = -265, 235      # sud 197 ; nord 167 (le complexe fait 135 de large)
box("HarHabayit_sol", HX0, HX1, HY0, HY1, Z_HAR - 1, Z_HAR, "00_HarHabayit", MAT_SOL())
# Cinq portes (Middot 1:3) : deux Houlda au sud, Kiponus à l'ouest, Tadi au nord,
# la porte est sur l'axe. Middot n'en donne ni les cotes ni les abscisses : CHOIX.
# Le mur EST est le seul à être bas (Middot 2:4) : le kohen qui brûle la para se tient
# au sommet du mont des Oliviers et doit voir l'ouverture du Heikhal au moment de
# l'aspersion. La ligne de mire passe donc par la porte est, Nikanor et l'Oulam — tous
# centrés sur y = 0 — et rien ne doit s'y trouver.
H_HAR, H_HAR_EST = 30, 24
P_HOULDA = [(-60, 20), (20, 20)]        # CHOIX : les deux portes du sud
mur_perce("HarHabayit_mur_sud", HX0, HX1, HY0, HY0 + 3, Z_HAR, Z_HAR + H_HAR,
          "00_HarHabayit", P_HOULDA, 20)
mur_perce("HarHabayit_mur_nord", HX0, HX1, HY1 - 3, HY1, Z_HAR, Z_HAR + H_HAR,
          "00_HarHabayit", [(-100, 10)], 20)          # Tadi (CHOIX)
mur_perce("HarHabayit_mur_ouest", HX0, HX0 + 3, HY0, HY1, Z_HAR, Z_HAR + H_HAR,
          "00_HarHabayit", [(0, 10)], 20)             # Kiponus (CHOIX)
mur_perce("HarHabayit_mur_est", HX1 - 3, HX1, HY0, HY1, Z_HAR, Z_HAR + H_HAR_EST,
          "00_HarHabayit", [(0, 10)], 20)             # Sha'ar HaMizrahi, sur l'axe
pas = 10
for i, x in enumerate(range(HX0 + 15, HX1 - 10, pas)):
    colonne(f"Portique_sud_{i:03d}", x, HY0 + 15, Z_HAR, Z_HAR + 25, 1.5)
    colonne(f"Portique_nord_{i:03d}", x, HY1 - 15, Z_HAR, Z_HAR + 25, 1.5)
for i, y in enumerate(range(HY0 + 25, HY1 - 20, pas)):
    colonne(f"Portique_ouest_{i:03d}", HX0 + 15, y, Z_HAR, Z_HAR + 25, 1.5)
    if abs(y) > 6:      # dégager la ligne de mire de la para (Middot 2:4)
        colonne(f"Portique_est_{i:03d}", HX1 - 15, y, Z_HAR, Z_HAR + 25, 1.5)
# Stoa royale au sud : seconde rangée de colonnes
for i, x in enumerate(range(HX0 + 15, HX1 - 10, pas)):
    colonne(f"Stoa_sud_{i:03d}", x, HY0 + 30, Z_HAR, Z_HAR + 25, 1.5)
# Plafond de la nef centrale de la Stoa (cèdre selon Josèphe). Sans lui la colonnade
# est ouverte au ciel : CAM_02 ne filmait que du fond de monde entre des piliers, et
# le « cedar ceiling » du prompt n'avait aucune géométrie à habiller.
box("Stoa_sud_plafond", HX0, HX1, HY0 + 13, HY0 + 32, Z_HAR + 25, Z_HAR + 27,
    "00_HarHabayit", MAT_CEDRE())
# Caissons : poutres au pas de la moitié d'une travée, deux sablières sur les axes de
# colonnade. Un plafond lisse ne donnait aucune cadence au travelling du plan 2 —
# c'est la fuite des poutres qui dit la vitesse, et elle est dans la passe Depth.
for i, x in enumerate(plage(HX0 + 2.5, HX1 - 2.5, 5)):
    box(f"Stoa_sud_poutre_{i:03d}", x - 0.5, x + 0.5, HY0 + 13, HY0 + 32,
        Z_HAR + 24, Z_HAR + 25, "00_HarHabayit", MAT_CEDRE())
for y in (HY0 + 15, HY0 + 30):
    box(f"Stoa_sud_sabliere_{y:+.0f}", HX0, HX1, y - 0.6, y + 0.6,
        Z_HAR + 23.8, Z_HAR + 25, "00_HarHabayit", MAT_CEDRE())

# 'Heil : 12 marches de 0.5 × 0.5 (Middot 2:3) côté est, l'accès principal. Elles
# montent du dallage au niveau de l'Ezrat Nashim et s'arrêtent contre la face est de
# son mur (x 145) : posées 5 amot plus à l'ouest, elles étaient enfouies dans le
# podium. Le soreg qui borde le 'Heil se construit avec les lishkot, plus bas : sa
# ligne se mesure depuis les corps de porte, qui débordent des murs.
for i in range(12):
    box(f"Heil_marche_{i:02d}", 150.5 - i * 0.5, 151 - i * 0.5, -67.5, 67.5,
        Z_HAR, Z_HAR + 0.5 * (i + 1), "00_HarHabayit")

# ----------------------------------------------------------------------------
# 10 — EZRAT NASHIM (135 × 135), Middot 2:5
# ----------------------------------------------------------------------------
EX0, EX1 = 5, 140          # commence après le mur est de l'Azara (0..5)
box("EzratNashim_sol", EX0, EX1, -67.5, 67.5, Z_EZN - 1, Z_EZN, "10_EzratNashim", MAT_SOL())
H_MUR_EN = 20
box("EzratNashim_mur_nord", EX0, EX1 + 5, 67.5, 72.5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_mur_sud", EX0, EX1 + 5, -72.5, -67.5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_mur_est_S", EX1, EX1 + 5, -72.5, -5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_mur_est_N", EX1, EX1 + 5, 5, 72.5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_porte_est_linteau", EX1, EX1 + 5, -5, 5, Z_EZN + 20 - 0.01, Z_EZN + H_MUR_EN, "10_EzratNashim")
# Quatre chambres d'angle 40 × 40, sans toit (murs de 2 amot) — « ולא היו מקורות »
# (Middot 2:5, qui les rattache aux « חצרות קטורות » d'Ezekiel 46:21-22). Affectations
# par angle : Middot 2:5. CHOIX : la Mishna ne décrit aucune porte, seulement des
# usages qui la supposent (les nazirs y cuisent, les metzoraim s'y immergent) ;
# quatre murs aveugles ne sont pas une lishka mais une fosse. Chacune s'ouvre donc
# sur la cour, par la face tournée vers l'axe. Cote inventée (6 × 12) : Middot 2:3
# donne 10 × 20 à « tous les pesa'him et tous les shearim », mais une porte de 20 ne
# tient pas dans un mur de 15 — la hauteur de ces murs n'est elle-même dans aucune
# source.
for nm, xa, ya, cour in (("Nezirim_SE", EX1 - 40, -67.5, "N"), ("Etzim_NE", EX1 - 40, 27.5, "S"),
                         ("Metzoraim_NO", EX0, 27.5, "S"), ("Shemanya_SO", EX0, -67.5, "N")):
    xb, yb = xa + 40, ya + 40
    for a, b, c, d, side in ((xa, xb, ya, ya + 2, "S"), (xa, xb, yb - 2, yb, "N"),
                             (xa, xa + 2, ya, yb, "O"), (xb - 2, xb, ya, yb, "E")):
        nom = f"Lishkat_{nm}_{side}"
        if side == cour:
            mur_perce(nom, a, b, c, d, Z_EZN, Z_EZN + 15, "10_EzratNashim",
                      [((a + b) / 2, 6)], 12)
        else:
            box(nom, a, b, c, d, Z_EZN, Z_EZN + 15, "10_EzratNashim")
# Gezuztra : galerie des femmes le long des murs nord et sud (Middot 2:5 ; Soukka 51b)
box("Gezuztra_nord", EX0, EX1, 64, 67.5, Z_EZN + 10, Z_EZN + 11, "10_EzratNashim")
box("Gezuztra_sud", EX0, EX1, -67.5, -64, Z_EZN + 10, Z_EZN + 11, "10_EzratNashim")
# Quinze marches semi-circulaires vers la porte de Nikanor (Middot 2:5), 0.5 × 0.5,
# centrées sur l'axe, rayon décroissant en montant
for i in range(15):
    r = 7.5 - i * 0.5 + 6
    poly = [(EX0 + r * math.cos(t), r * math.sin(t))
            for t in [-math.pi / 2 + math.pi * k / 24 for k in range(0, 25)]]
    prism(f"Marche_Nikanor_{i:02d}", poly, Z_EZN, Z_EZN + 0.5 * (i + 1), "10_EzratNashim")

# ----------------------------------------------------------------------------
# 20 — AZARA (187 × 135), Middot 5:1–2
# ----------------------------------------------------------------------------
AX0, AX1, AY0, AY1 = -187, 0, -67.5, 67.5
box("Azara_sol", AX0, AX1, AY0, AY1, Z_AZ - 1, Z_AZ, "20_Azara", MAT_SOL())
H_MUR = 25
T = 5   # épaisseur des murs
# L'Azara et l'Ezrat Nashim sont des terrasses taillées dans le Har HaBayit, pas des
# dalles posées en l'air : hors de leurs murs le sol retombe à Z_HAR. Sans la masse
# qui les porte, les murs, les chambres d'angle et les quatre lishkot du pourtour
# flottaient — 13,5 amot au-dessus du dallage, visible plein cadre au plan 1.
# Deux blocs et non un : le mur est de l'Azara (x 0..5) descend déjà à Z_EZN, une
# masse qui monterait à Z_AZ sous lui lui donnerait une face coplanaire.
box("Podium_har", AX0 - T, EX1 + 5, AY0 - T, AY1 + T, Z_HAR, Z_EZN, "00_HarHabayit")
box("Podium_azara", AX0 - T, AX1, AY0 - T, AY1 + T, Z_EZN, Z_AZ, "00_HarHabayit")
# Mur est avec la porte de Nikanor (10 × 20) au centre
box("Azara_mur_est_S", AX1, AX1 + T, AY0 - T, -5, Z_EZN, Z_AZ + H_MUR, "20_Azara")
box("Azara_mur_est_N", AX1, AX1 + T, 5, AY1 + T, Z_EZN, Z_AZ + H_MUR, "20_Azara")
box("Nikanor_linteau", AX1, AX1 + T, -5, 5, Z_AZ + 20, Z_AZ + H_MUR, "20_Azara")
# Battants rabattus dans l'embrasure, comme ceux du Heikhal : les portes de l'Azara
# sont ouvertes dès l'aube (Tamid 3:7 ; Yoma 3:1-2), et à Kippour pendant l'avoda.
# Fermés, ils bouchaient l'axe est-ouest — la colonne vertébrale du film : les plans
# 6, 13 et 14 finissaient sur deux vantaux de bronze là où le découpage demande
# l'ouverture de l'Oulam au fond. Ils contredisaient aussi la ligne de mire de la
# para adouma (Middot 2:4), que le mur est bas est fait pour dégager.
box("Nikanor_porte_S", AX1 + 1, AX1 + 4.5, -5, -4.7, Z_AZ, Z_AZ + 20, "20_Azara", MAT_BRONZE())
box("Nikanor_porte_N", AX1 + 1, AX1 + 4.5, 4.7, 5, Z_AZ, Z_AZ + 20, "20_Azara", MAT_BRONZE())
# Mur ouest
box("Azara_mur_ouest", AX0 - T, AX0, AY0 - T, AY1 + T, Z_AZ, Z_AZ + H_MUR, "20_Azara")
# Murs nord et sud avec trois portes chacun (10 × 20). Positions : CHOIX (Middot 1:4)
# Les trois portes de chaque mur, nommées. La Mishna les compte « סמוכים למערב »,
# c'est-à-dire en partant de la plus occidentale (Middot 2:6 = Shekalim 6:3 : « les
# portes du sud, à partir de celle qui est près de l'ouest : Sha'ar HaElyon, Sha'ar
# HaDelek, Sha'ar HaBekhorot, Sha'ar HaMayim » ; Bartenura sur Shekalim 6:3 : « la
# porte proche de l'ouest est Sha'ar HaElyon, et APRÈS elle Sha'ar HaDelek » ;
# Tosfot Yom Tov sur Middot 5:3 : c'est l'absence de « סמוכים למערב » qui fait
# compter les lishkot d'est en ouest, sa présence fait compter les portes de l'ouest
# vers l'est). La liste des sept portes (Middot 1:4-5) donne les mêmes trois portes
# du sud dans le même ordre : Sha'ar HaMayim est donc la plus ORIENTALE.
PORTE_DELEK, PORTE_BEKHOROT, PORTE_MAYIM = -120, -66, -12       # sud, ouest -> est
PORTE_NITZOTZ, PORTE_KORBAN, PORTE_MOKED = -120, -66, -12       # nord, ouest -> est
# La Lishkat HaGazit est à cheval sur la limite du sacré, avec deux ouvertures —
# « חֶצְיָהּ בַּקֹּדֶשׁ וְחֶצְיָהּ בַּחוֹל… שְׁנֵי פְתָחִים הָיוּ לָהּ, אֶחָד פָּתוּחַ בַּקֹּדֶשׁ וְאֶחָד
# פָּתוּחַ בַּחוֹל » (Yoma 25a ; Rambam, Beit HaBe'hira 5:17). Celle qui donne sur l'Azara
# perce donc le mur nord. Ce n'est pas une huitième porte : Middot 1:4 compte sept
# **שערים**, et Yoma 25a appelle celles-ci des פתחים.
GAZIT_X0, GAZIT_X1 = -52, -32
OUVERTURES = {"nord": [PORTE_MOKED, PORTE_KORBAN, PORTE_NITZOTZ, (GAZIT_X0 + GAZIT_X1) / 2],
              "sud": [PORTE_MAYIM, PORTE_BEKHOROT, PORTE_DELEK]}
for (y0, y1, nm) in [(AY1, AY1 + T, "nord"), (AY0 - T, AY0, "sud")]:
    ouvertures = OUVERTURES[nm]
    bornes = [AX0] + sum([[p - 5, p + 5] for p in sorted(ouvertures)], []) + [AX1]
    for k in range(0, len(bornes) - 1, 2):
        box(f"Azara_mur_{nm}_{k // 2}", bornes[k], bornes[k + 1], y0, y1,
            Z_AZ, Z_AZ + H_MUR, "20_Azara")
    for p in ouvertures:
        box(f"Azara_porte_{nm}_{p:+.0f}_linteau", p - 5, p + 5, y0, y1,
            Z_AZ + 20, Z_AZ + H_MUR, "20_Azara")
# Marche Ezrat Israël / Ezrat Cohanim (1 ama) + Doukhan (3 marches de 0.5) — Middot 2:6
box("Marche_EzratIsrael_Cohanim", -11, -10, AY0, AY1, Z_AZ, Z_AZ + 1, "20_Azara")
for i in range(3):
    box(f"Doukhan_{i}", -12 - i * 0.5, -11, -40, 40, Z_AZ, Z_AZ + 1 + 0.5 * (i + 1), "20_Azara")

# Chambres du pourtour — 80_Lishkot. Elles sont adossées aux murs de l'Azara mais
# posées sur le Har HaBayit : leur pied est à Z_HAR, 13,5 amot sous le sol de la cour
# qu'elles bordent. Les faire partir de Z_AZ les laissait en l'air. Middot 1:7 le dit
# du Beit HaMoked : « אֶחָד פָּתוּחַ לַחֵיל וְאֶחָד פָּתוּחַ לָעֲזָרָה » — une porte à chaque
# niveau, donc un bâtiment qui les enjambe.
SAILLIE = 12          # ce que les corps débordent du mur ; = la profondeur du Beit
                      # Avtinas, imposée par le recul de CAM_03 à l'intérieur
AXE_MUR_N = AY1 + T / 2
NORD_Y1 = AY1 + T + SAILLIE
NORD_Y0 = 2 * AXE_MUR_N - NORD_Y1     # symétrique du précédent par rapport à l'axe du mur

# Beit HaMoked : sur la porte nord la plus orientale, la troisième que compte
# Middot 1:5. Il est à cheval sur la limite du sacré et non posé derrière le mur —
# « אַרְבַּע לְשָׁכוֹת הָיוּ בְּבֵית הַמּוֹקֵד… שְׁתַּיִם בַּקֹּדֶשׁ וּשְׁתַּיִם בַּחֹל, וְרָאשֵׁי
# פִסְפָּסִין מַבְדִּילִין בֵּין קֹדֶשׁ לַחֹל » (Middot 1:6). D'où deux שערים opposés
# (Middot 1:7) et un couloir entre eux, le mur de l'Azara le traversant par sa propre
# baie. CHOIX : ni la largeur (20 amot, comme les deux autres corps de porte) ni la
# hauteur (30 au-dessus de l'Azara) n'ont de source ; la hauteur passe le mur de 25,
# sans quoi les deux toits seraient coplanaires, et la largeur laisse la caméra du
# plan 7a passer entre lui et la Lishkat HaGazit.
lishka("Beit_HaMoked", PORTE_MOKED - 10, PORTE_MOKED + 10, NORD_Y0, NORD_Y1,
       Z_HAR, Z_AZ + 30, "80_Lishkot", [("N", *PORTE_SHAAR), ("S", *PORTE_SHAAR)])
maake("Beit_HaMoked", PORTE_MOKED - 10, PORTE_MOKED + 10, NORD_Y0, NORD_Y1,
      Z_AZ + 30, "80_Lishkot")
# Lishkat HaGazit, même parti : à cheval, deux פתחים opposés (Yoma 25a).
# OUVERT — le nord suit la girsa de Yoma 19a, celle du Rambam (Beit HaBe'hira 5:17)
# et la préférence de Tosfot Yom Tov sur Middot 5:3, contre le texte imprimé de
# Middot 5:4 qui met Gazit, Gola et Etz au SUD. Mais le même Rambam identifie
# Lishkat HaEtz à la Lishkat Parhedrin, que la scène place au sud d'après le
# Yerushalmi (voir plus bas) : les deux chambres, que Middot 5:4 veut du même côté
# (« וְגַג שְׁלָשְׁתָּן שָׁוֶה »), sont ici de part et d'autre. La scène tient l'avis que le
# Cohen Gadol avait DEUX lishkot — ce que Yoma 19a laisse ouvert (« וְלֹא יָדַעְנָא »
# laquelle est au nord, laquelle au sud) — et non que Parhedrin = HaEtz.
lishka("Lishkat_HaGazit", GAZIT_X0, GAZIT_X1, NORD_Y0, NORD_Y1,
       Z_HAR, Z_AZ + 30, "80_Lishkot", [("N", *PORTE_SHAAR), ("S", *PORTE_SHAAR)])
maake("Lishkat_HaGazit", GAZIT_X0, GAZIT_X1, NORD_Y0, NORD_Y1, Z_AZ + 30, "80_Lishkot")

# Sha'ar HaNitzotz, la porte nord la plus occidentale — le seul corps de porte que la
# Mishna décrive en entier : « וּכְמִין אַכְסַדְרָה הָיָה, וַעֲלִיָּה בְנוּיָה עַל גַּבָּיו,
# שֶׁהַכֹּהֲנִים שׁוֹמְרִים מִלְמַעְלָן וְהַלְוִיִּם מִלְּמַטָּן, וּפֶתַח הָיָה לוֹ לַחֵיל »
# (Middot 1:5). Le Beit HaNitzotz est l'un des trois postes de garde des Cohanim
# (Middot 1:1 ; Tamid 1:1), et son aliyah regarde l'Azara.
NZ_X0, NZ_X1 = PORTE_NITZOTZ - 10, PORTE_NITZOTZ + 10
NZ_Y0, NZ_Y1, NZ_Z0 = AY1 + T, NORD_Y1, Z_AZ + 25
lishka("Beit_ShaarHaNitzotz", NZ_X0, NZ_X1, NZ_Y0, NZ_Y1, Z_HAR, NZ_Z0,
       "80_Lishkot", [("N", *PORTE_SHAAR)])
terrasse_de_porte("ShaarHaNitzotz", NZ_X0, NZ_X1, NZ_Y0, NZ_Y1, NZ_Z0,
                  (PORTE_NITZOTZ - 5, PORTE_NITZOTZ + 5), "80_Lishkot")
aliyah("BeitHaNitzotz", PORTE_NITZOTZ - 5, PORTE_NITZOTZ + 5, NZ_Y0, NZ_Y1, NZ_Z0, 12,
       "80_Lishkot", ("sud", PORTE_NITZOTZ - 1.5, PORTE_NITZOTZ + 1.5))

# Beit Avtinas : l'aliyah du corps de porte de Sha'ar HaMayim — la plus ORIENTALE des
# trois portes du sud —, creuse, murs d'une ama, fenêtre 3 x 4 au nord sur l'Azara.
# C'est l'intérieur filmé par CAM_03. Source : Yerushalmi Yoma 1:5 (halakha)
# « על גבי שער המים היתה וסמוך ללשכתו היתה » — elle était au-dessus de Sha'ar HaMayim
# et contre sa lishka (celle du Cohen Gadol). Le Bavli Yoma 19a laisse la question
# ouverte (« ולא ידענא ») et sa baraïta situe la première tevila « בחול, על גבי שער
# המים, ובצד לשכתו » ; on suit le Yerushalmi, explicite.
# « על גבי » se prend au mot : la chambre est le haut d'un bâtiment de porte, et il
# fallait le bâtir. Sans lui elle pendait à 38,5 amot au-dessus du dallage, collée à
# la face sud du mur, sans rien dessous — le bloc qui flottait au plan 1. Le corps est
# modelé plein : la baie franchie reste celle du mur de l'Azara.
BA_X0, BA_X1 = PORTE_MAYIM - 5, PORTE_MAYIM + 5
BA_Y0, BA_Y1, BA_Z0 = AY0 - T - SAILLIE, AY0 - T, Z_AZ + 25
SM_X0, SM_X1 = PORTE_MAYIM - 10, PORTE_MAYIM + 10
lishka("Beit_ShaarHaMayim", SM_X0, SM_X1, BA_Y0, BA_Y1, Z_HAR, BA_Z0,
       "80_Lishkot", [("S", *PORTE_SHAAR)])
terrasse_de_porte("ShaarHaMayim", SM_X0, SM_X1, BA_Y0, BA_Y1, BA_Z0,
                  (BA_X0, BA_X1), "80_Lishkot")
aliyah("BeitAvtinas", BA_X0, BA_X1, BA_Y0, BA_Y1, BA_Z0, 12,
       "80_Lishkot", ("nord", PORTE_MAYIM - 1.5, PORTE_MAYIM + 1.5))

# « וסמוך ללשכתו היתה » (Yerushalmi Yoma 1:5) : la lishka du Cohen Gadol touche le
# Beit Avtinas — donc à l'ouest de Sha'ar HaMayim, et non à l'ouest du mur sud.
# Elle touche le corps de porte par les socles : à corps jointifs les deux socles se
# recouvriraient sur leur débord, et deux faces supérieures coplanaires clignotent.
lishka("Lishkat_Parhedrin", SM_X0 - 16, SM_X0 - 1, BA_Y0, BA_Y1,
       Z_HAR, Z_AZ + 15, "80_Lishkot", [("S", *PORTE_LISHKA)])
maake("Lishkat_Parhedrin", SM_X0 - 16, SM_X0 - 1, BA_Y0, BA_Y1, Z_AZ + 15, "80_Lishkot")

# Les deux lishkot de Sha'ar Nikanor, dans l'Ezrat Israël, de part et d'autre de la
# porte est : « וּשְׁתֵּי לְשָׁכוֹת הָיוּ לוֹ, אַחַת מִימִינוֹ וְאַחַת מִשְּׂמֹאלוֹ, אַחַת לִשְׁכַּת
# פִּנְחָס הַמַּלְבִּישׁ, וְאַחַת לִשְׁכַּת עוֹשֵׂי חֲבִתִּין » (Middot 1:4 ; Rambam, Beit
# HaBe'hira 5:17). CHOIX : Pin'has au nord (la droite de qui entre), leur cote et leur
# hauteur, qu'aucune source ne donne. Elles s'ouvrent à l'ouest, sur la cour.
for nm, ny0, ny1 in (("Pinchas_HaMalbish", 5, 20), ("Osei_Chavitin", -20, -5)):
    lishka(f"Lishkat_{nm}", -8, AX1, ny0, ny1, Z_AZ, Z_AZ + 20,
           "80_Lishkot", [("O", *PORTE_LISHKA)])
    maake(f"Lishkat_{nm}", -8, AX1, ny0, ny1, Z_AZ + 20, "80_Lishkot")

# Soreg (10 tefa'him = 1.67 ama) et 'Heil. Middot 2:3 : « לִפְנִים מִמֶּנּוּ הַחֵיל, עֶשֶׂר
# אַמּוֹת » — dix amot de dégagement, et les douze marches y sont. Le soreg se pose donc
# à 10 amot de la face bâtie la plus saillante, corps de porte compris : mesuré depuis
# le mur, il traversait le Beit HaMoked et le Beit Avtinas. Ses treize פרצות ont été
# rebouchées (« חָזְרוּ וּגְדָרוּם »), il est donc continu.
HEIL = 10
SX0, SX1 = AX0 - T - HEIL, EX1 + 5 + HEIL
SY0, SY1 = -(NORD_Y1 + HEIL), NORD_Y1 + HEIL
for nm, xa, xb, ya, yb in (("sud", SX0, SX1, SY0, SY0 + 0.2),
                           ("nord", SX0, SX1, SY1 - 0.2, SY1),
                           ("ouest", SX0, SX0 + 0.2, SY0, SY1),
                           ("est", SX1 - 0.2, SX1, SY0, SY1)):
    box(f"Soreg_{nm}", xa, xb, ya, yb, Z_HAR, Z_HAR + 1.67, "00_HarHabayit")

# ----------------------------------------------------------------------------
# 30 — MIZBEA'H (Middot 3:1) + rampe + Kiyor + Beit HaMitba'haïm
# ----------------------------------------------------------------------------
MX0, MX1 = -54, -22          # 32 amot, à 22 amot de l'Oulam
MY0, MY1 = -25, 7            # CHOIX : centre 9 amot au sud de l'axe, bord nord à 60.5 du mur nord
                             # (Middot 5:2 ; Rambam Beit HaBe'hira 5:13-15). R. Yehouda (autel centré,
                             # Zeva'him 58b) non retenu. Voir README « Tranché ».
box("Mizbeach_yessod", MX0, MX1, MY0, MY1, Z_AZ, Z_AZ + 1, "30_Mizbeach", MAT_CHAUX())
box("Mizbeach_corps", MX0 + 1, MX1 - 1, MY0 + 1, MY1 - 1, Z_AZ + 1, Z_AZ + 6, "30_Mizbeach", MAT_CHAUX())
box("Mizbeach_haut", MX0 + 2, MX1 - 2, MY0 + 2, MY1 - 2, Z_AZ + 6, Z_AZ + 9, "30_Mizbeach", MAT_CHAUX_FEU())
for (nm, x, y) in [("SE", MX1 - 3, MY0 + 2), ("NE", MX1 - 3, MY1 - 3), ("NO", MX0 + 2, MY1 - 3), ("SO", MX0 + 2, MY0 + 2)]:
    box(f"Keren_{nm}", x, x + 1, y, y + 1, Z_AZ + 9, Z_AZ + 10, "30_Mizbeach", MAT_CHAUX_FEU())
# Ma'arakha (feu) : petit volume noir au centre
box("Maarakha", MX0 + 8, MX1 - 8, MY0 + 8, MY1 - 8, Z_AZ + 9, Z_AZ + 9.6, "30_Mizbeach", braise("Braise"))
# Le feu lui-même. La ma'arakha était une boîte noire sans source : la colonne de fumée
# montait d'un autel éteint, et la rampe du plan 7b n'avait que la lumière du ciel — la
# raison pour laquelle elle ne se détachait ni de l'autel ni du dallage.
feu = lampe("Maarakha_feu", 'AREA',
            (m((MX0 + MX1) / 2), m((MY0 + MY1) / 2), m(Z_AZ + 10)))
feu.data.shape = 'RECTANGLE'
feu.data.size = m(MX1 - MX0 - 16)
feu.data.size_y = m(MY1 - MY0 - 16)
feu.data.energy = 1500
feu.data.color = (1.0, 0.42, 0.13)
link_to(feu, "30_Mizbeach")
# Colonne de fumée : proxy géométrique, pas un décor. Sans volume ici, le styliseur
# invente la source (il a sorti un petit autel d'or posé sur le mur est) ; avec lui,
# la fumée part du bon point. L'ombre portée est coupée : sur la façade elle
# ressortait en seconde colonne sombre.
# 12 amot de large sur 80 de haut, la colonne dominait tout : elle barrait le plan 6
# de haut en bas et couvrait la façade au plan 1 — un proxy ne doit dire que « de la
# fumée, ici », pas devenir le sujet. Ramenée à 45 de haut, elle monte encore bien
# au-dessus du mur de l'Azara sans écraser le Sanctuaire.
# Volutes, pas un fût : le tronc de cône lisse, même évasé, se relisait en colonne de
# pierre — ni bord droit ni section constante n'existent dans de la fumée. Quarante
# sphères serrées (pas d'une ama, rayons de 1,6 à 4,2 tirés à ±30 %), de plus en plus
# écartées de l'axe en montant, avec une dérive vers le sud en haut : à quinze sphères
# espacées de trois amot on lisait un chapelet de boules. La silhouette est bosselée,
# la passe Z reste écrite (matière `nuee`), et le sommet quitte l'axe du Sanctuaire.
FUMEE_X, FUMEE_Y = (MX0 + MX1) / 2, (MY0 + MY1) / 2
MAT_FUMEE = nuee("Fumee", (0.80, 0.80, 0.82))
for i in range(40):
    t = i / 39
    ecart = 0.3 + 1.5 * t
    volute = sphere(f"Colonne_fumee_{i:02d}",
                    FUMEE_X + (alea("fumee", 3 * i) - 0.5) * 2 * ecart,
                    FUMEE_Y - 2.5 * t * t + (alea("fumee", 3 * i + 1) - 0.5) * 2 * ecart,
                    Z_AZ + 9.5 + 42 * t, (1.6 + 2.6 * t) * (0.7 + 0.6 * alea("fumee", 3 * i + 2)),
                    "77_Fumee", MAT_FUMEE, segs=12)
    volute.visible_shadow = False

# Kevesh : 32 long (dont 2 sur le yessod) × 16 large, au sud
xc = (MX0 + MX1) / 2
wedge_ramp("Kevesh", xc - 8, xc + 8, MY0 - 30, MY0, Z_AZ, Z_AZ + 9, "30_Mizbeach", MAT_CHAUX())
box("Kevesh_raccord", xc - 8, xc + 8, MY0, MY0 + 2, Z_AZ, Z_AZ + 9, "30_Mizbeach", MAT_CHAUX())
# Kiyor : entre l'Oulam et le Mizbea'h, décalé vers le sud (Middot 3:6). La même michna
# donne les 22 amot et les douze marches ; les marches en prennent 12, il reste 10 amot
# de plat entre x -64 et -54, et c'est là que le bassin tient.
cyl("Kiyor_pied", -59, -8, Z_AZ, Z_AZ + 1, 0.8, "30_Mizbeach", MAT_BRONZE())
cyl("Kiyor_bassin", -59, -8, Z_AZ + 1, Z_AZ + 2.2, 1.6, "30_Mizbeach", MAT_BRONZE())
# Beit HaMitba'haïm au nord : 8 piliers, 8 tables de marbre, 24 anneaux
for i in range(8):
    x = MX1 - 3 - i * 3.7
    cyl(f"Pilier_{i}", x, 53.2, Z_AZ, Z_AZ + 3, 0.5, "30_Mizbeach")
    box(f"Pilier_{i}_cedre", x - 0.7, x + 0.7, 52.5, 53.9, Z_AZ + 3, Z_AZ + 3.6, "30_Mizbeach", MAT_CEDRE())
    box(f"Table_marbre_{i}", x - 0.5, x + 0.5, 42, 44, Z_AZ, Z_AZ + 1.5, "30_Mizbeach", MAT_MARBRE())
for r in range(4):
    for c in range(6):
        x = MX1 - 4 - c * 4.8
        y = 18 + r * 6
        tore(f"Anneau_{r}{c}", x, y, Z_AZ + 0.1, 0.5, 0.08, "30_Mizbeach", MAT_BRONZE())

# ----------------------------------------------------------------------------
# 40/50/60 — LE BÂTIMENT (100 × 100 × 100), Middot 4
#   x : -76 (façade est) → -176 (arrière ouest)
#   Oulam mur 5 | Oulam 11 | mur 6 | Heikhal 40 | Traksin 1 | KhK 20 | mur 6 | cellule 6 | mur 5
# ----------------------------------------------------------------------------
BX_E, BX_O = -76, -176
H_BAT = 100
# Décomposition verticale de Middot 4:6 : אֹטֶם 6, גֹּבַהּ 40, כִּיּוּר 1, בֵּית דִּלְפָה 2, תִּקְרָה 1,
# מַעֲזִיבָה 1, עֲלִיָּה 40, puis de nouveau 1 + 2 + 1 + 1 — soit 96 depuis le sol de l'Azara.
# Les 4 amot qui manquent aux 100 ne sont pas du mur : מַעֲקֶה 3 et כָּלֵה עוֹרֵב 1.
Z_FAITE = Z_AZ + H_BAT              # 100 : le faîte, pointes comprises
Z_TOIT = Z_FAITE - MAAKE_H - 1      # 96 : là où s'arrête le mur
# Plateforme (sol surélevé de 6 amot) et 12 marches devant l'Oulam
box("Batiment_socle", BX_O, BX_E, -50, 50, Z_AZ, Z_BAT, "40_Ulam")
for i in range(12):
    # « רוּם מַעֲלָה חֲצִי אַמָּה וְשִׁלְחָהּ אַמָּה » (Middot 3:6) : le giron fait une ama, pas
    # une demie — les douze marches occupent 12 des 22 amot qui séparent l'Oulam du
    # Mizbea'h, le reste est du plat.
    box(f"Marche_Ulam_{i:02d}", BX_E + (12 - i) - 1, BX_E + (12 - i), -20, 20,
        Z_AZ, Z_AZ + 0.5 * (i + 1), "40_Ulam")

# --- Oulam : façade 100 large, ouverture 20 × 40 SANS portes (Middot 3:7)
box("Ulam_facade_S", BX_E - 5, BX_E, -50, -10, Z_BAT, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
box("Ulam_facade_N", BX_E - 5, BX_E, 10, 50, Z_BAT, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
box("Ulam_facade_linteau", BX_E - 5, BX_E, -10, 10, Z_BAT + 40, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
# --- La façade est n'est PAS dorée. Josèphe la voit couverte de plaques d'or (Guerre
#     V, 5, 6) ; la guemara raconte l'inverse et c'est elle que le film suit : « סָבַר
#     לְמִשְׁעֲיֵיהּ בְּדַהֲבָא, אֲמַרוּ לֵיהּ רַבָּנַן שַׁבְקֵיהּ דְּהָכִי שַׁפִּיר טְפֵי דְּמִיחֲזֵי כְּאִידַּוְּותָא דְיַמָּא » — Hérode
#     voulut la plaquer d'or, les Sages l'en dissuadèrent, la pierre est plus belle
#     ainsi, « comme les vagues de la mer » (Baba Batra 4a ; Soucca 51b). Ce qui fait
#     l'extérieur est donc l'assise elle-même : shesh, marmara et kuchla en assises
#     alternées, une en débord une en retrait, déjà dans MAT_MARBRE_HERODE.
#     L'or reste où les sources le mettent : dedans (Middot 4:1), sur les portes, sur
#     la vigne et sur la couronne d'Hélène.
EPAISSEUR_PLACAGE = 0.1   # amot : l'or est une feuille, la boîte doit rester visible
# Cinq poutres de chêne au-dessus de l'ouverture (Middot 3:7)
for i in range(5):
    L = 22 + i * 2
    box(f"Maltera_{i}", BX_E - 5.4, BX_E + 0.4, -L / 2, L / 2, Z_BAT + 41 + i * 2, Z_BAT + 42 + i * 2, "40_Ulam", MAT_CHENE())
# --- Rovadim : les bandeaux en saillie qui ceinturent les murs de l'Oulam de bas en
#     haut (Rambam, Beit HaBe'hira 4:9). C'est la seule articulation que les sources
#     donnent à cette façade, et elle est horizontale.
#     PAS DE COLONNES. Aucune source n'en met sur la face du bâtiment : ni Middot 3:7-8
#     et 4:6-7, ni le Rambam, ni Josèphe qui l'a vue et la décrit pierre à pierre
#     (Guerre V, 5, 4 et 6 : les épaules, la porte sans battants, les plaques d'or, la
#     pierre « exceeding white », les pointes du faîte — pas une colonne). Ya'hin et
#     Boaz (I Rois 7:21) sont du premier Temple et Middot les ignore : les importer ici
#     serait inventer. Les seuls fûts de la zone sont les כְּלוֹנָסוֹת de cèdre tendus
#     du mur du Heikhal à celui de l'Oulam (Middot 3:8), qui sont dedans, pas devant.
#     Le rovad du sommet emporte les 4 dernières amot du mur, où Middot 4:6 met le
#     כִּיּוּר et la בֵּית דִּלְפָה de l'étage.
#     Deux échelles d'horizontales, et elles se confirment : celle-ci, de 4 amot, et
#     celle des assises — « אַפֵּיק שָׂפָה וְעַיֵּיל שָׂפָה » (Baba Batra 4a ; Soucca 51b), une
#     assise en débord, une en retrait. La seconde est déjà dans MAT_MARBRE_HERODE et
#     n'a pas à être bâtie deux fois.
ROVAD_X_E = BX_E                          # les bandeaux se posent sur le nu du mur
rovadim("Ulam_facade", ROVAD_X_E, (1, 0), -50, 50, Z_BAT, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE(),
        reserve=[(-10, 10, Z_BAT, Z_BAT + 40),        # la baie de 20 × 40
                 (-16, 16, Z_BAT + 40, Z_BAT + 52)])  # et la pile d'amaltraot
# Les faces nord et sud portent les mêmes bandeaux, et s'arrêtent au mur du Heikhal :
# le Kessef Mishneh (sur 4:9) écarte les rovadim du corps du bâtiment,
# « וְלֹא שֶׁיְּהֵא מֻקָּף רְבָדִים כְּמוֹ שֶׁל אוּלָם ».
for cote, y, sens in (("N", 50, 1), ("S", -50, -1)):
    rovadim(f"Ulam_flanc_{cote}", y, (0, sens), BX_E - 16, ROVAD_X_E + ROVAD_SAILLIE,
            Z_BAT, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())

# Épaules (Beit Ha'halifot) et intérieur de l'Oulam (11 profond)
box("Ulam_epaule_S", BX_E - 16, BX_E - 5, -50, -35, Z_BAT, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
box("Ulam_epaule_N", BX_E - 16, BX_E - 5, 35, 50, Z_BAT, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
box("Ulam_plafond", BX_E - 16, BX_E - 5, -35, 35, Z_BAT + 40, Z_TOIT, "40_Ulam", MAT_CEDRE())
# Deux tables de l'Oulam (marbre au nord... CHOIX : marbre à droite en entrant = nord ; or au sud)
box("Ulam_table_marbre", -90, -88, 5.5, 6.5, Z_BAT, Z_BAT + 1.5, "40_Ulam", MAT_MARBRE())
box("Ulam_table_or", -90, -88, -6.5, -5.5, Z_BAT, Z_BAT + 1.5, "40_Ulam", MAT_OR())
# Vigne d'or suspendue devant l'entrée du Heikhal (Middot 3:8) : représentée par un tore
# Remontée à 27 amot : à 23 elle enfermait la couronne d'Hélène dans son anneau, et
# les deux ne faisaient plus qu'un objet au rendu du plan 8.
tore("Vigne_or", -91.5, 0, Z_BAT + 27, 3, 0.3, "40_Ulam", MAT_OR(),
     rotation=(0, math.pi / 2, 0))
# Couronne d'or de la reine Hélène, suspendue au-dessus de l'entrée du Heikhal
# (Yoma 37a : « c'est par elle qu'on savait que le soleil s'était levé »). Le prompt
# du plan 8 la décrivait sans qu'elle existe dans le blockout : ou le modèle
# l'inventait ailleurs, ou il ne la mettait pas. Middot n'en donne pas les cotes.
# La poser à -92,5 ne réglait rien : l'anneau de 2,4 amot s'enfonçait de 1,9 dans le
# linteau (x -98..-92) et aucun rayon du plan 8 ne le touchait. Son centre doit donc
# être à l'est de la face du mur d'au moins son rayon.
tore("Couronne_Helene", -90.6, 0, Z_BAT + 22, 1.2, 0.15, "40_Ulam", MAT_OR())

# --- Mur est du Heikhal (6 amot) avec porte 10 × 20, quatre portes plaquées d'or
HX_E = BX_E - 16      # -92
box("Heikhal_mur_est_S", HX_E - 6, HX_E, -35, -5, Z_BAT, Z_TOIT, "50_Heikhal")
box("Heikhal_mur_est_N", HX_E - 6, HX_E, 5, 35, Z_BAT, Z_TOIT, "50_Heikhal")
box("Heikhal_mur_est_linteau", HX_E - 6, HX_E, -5, 5, Z_BAT + 20, Z_TOIT, "50_Heikhal")
if PORTES_HEIKHAL_OUVERTES:
    # Battants rabattus dans l'embrasure de 6 amot, contre les jambages.
    box("Heikhal_porte_S", HX_E - 5, HX_E - 0.3, -5, -4.7, Z_BAT, Z_BAT + 20, "50_Heikhal", MAT_OR())
    box("Heikhal_porte_N", HX_E - 5, HX_E - 0.3, 4.7, 5, Z_BAT, Z_BAT + 20, "50_Heikhal", MAT_OR())
else:
    box("Heikhal_porte_S", HX_E - 0.6, HX_E - 0.3, -5, -0.3, Z_BAT, Z_BAT + 20, "50_Heikhal", MAT_OR())
    box("Heikhal_porte_N", HX_E - 0.6, HX_E - 0.3, 0.3, 5, Z_BAT, Z_BAT + 20, "50_Heikhal", MAT_OR())

# --- Corps : 70 large ; intérieur 20 large ; murs + 38 cellules = 25 de chaque côté
HK0, HK1 = HX_E - 6, HX_E - 46          # Heikhal intérieur : -98 → -138
TR0, TR1 = HK1, HK1 - 1                 # Amah Traksin : -138 → -139
KK0, KK1 = TR1, TR1 - 20                # Kodesh HaKodashim : -139 → -159
ARON_Y_BAD = 1.38                       # les badim, hors des flancs de l'Arche (1,25 + anneau)
ARON_Z_BAD = Z_BAT + 0.125 + 1.35       # à hauteur des anneaux, coins supérieurs de la caisse
ARON_X_MACHTA = (KK0 + KK1) / 2 + 1.15  # la ma'hta entre les badim, au pied de la face est
box("Corps_mur_N", BX_O, HK0, 10, 35, Z_BAT, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
box("Corps_mur_S", BX_O, HK0, -35, -10, Z_BAT, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
box("Corps_mur_O", BX_O, KK1, -35, 35, Z_BAT, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
box("Corps_plafond", KK1, HK0, -10, 10, Z_BAT + 40, Z_TOIT, "50_Heikhal", MAT_CEDRE())
# --- « כָּל הַבַּיִת טוּחַ בְּזָהָב, חוּץ מֵאַחַר הַדְּלָתוֹת » (Middot 4:1 ; Rambam Beit
#     HaBe'hira 4:7 : « וכל ההיכל היה טפוח זהב חוץ ממקום אחורי הדלתות »). Josèphe le
#     confirme du dehors : la porte « toute couverte d'or, ainsi que tout le mur autour
#     d'elle » (Guerre V, 5).
#     L'or est un PLACAGE sur la face intérieure, jamais la matière du mur : le corps du
#     bâtiment reste en marbre apparent au-dehors (Baba Batra 4a), et une boîte ne porte
#     pas deux matières.
#     Rien derrière les battants : c'est justement pour couvrir cette pierre nue que les
#     portes intérieures se rabattent vers l'intérieur (Middot 4:1) — les faces de
#     l'embrasure ne reçoivent donc aucune plaque.
box("Heikhal_or_mur_N", HK1, HK0, 10 - EPAISSEUR_PLACAGE, 10, Z_BAT, Z_BAT + 40, "50_Heikhal", MAT_OR_PLAQUE())
box("Heikhal_or_mur_S", HK1, HK0, -10, -10 + EPAISSEUR_PLACAGE, Z_BAT, Z_BAT + 40, "50_Heikhal", MAT_OR_PLAQUE())
box("Heikhal_or_plafond", HK1, HK0, -10, 10, Z_BAT + 40 - EPAISSEUR_PLACAGE, Z_BAT + 40, "50_Heikhal", MAT_OR_PLAQUE())
for cote, signe in (("S", -1), ("N", 1)):
    # côté Heikhal : la face ouest du mur est, sur la largeur de la nef (20 amot)
    box(f"Heikhal_or_est_{cote}", HK0 - EPAISSEUR_PLACAGE, HK0, signe * 5, signe * 10,
        Z_BAT, Z_BAT + 40, "50_Heikhal", MAT_OR_PLAQUE())
    # côté Oulam : « tout le mur autour d'elle », sur les 40 amot de hauteur de l'Oulam
    box(f"Ulam_or_est_{cote}", HX_E, HX_E + EPAISSEUR_PLACAGE, signe * 5, signe * 35,
        Z_BAT, Z_BAT + 40, "40_Ulam", MAT_OR_PLAQUE())
box("Heikhal_or_est_linteau", HK0 - EPAISSEUR_PLACAGE, HK0, -5, 5, Z_BAT + 20, Z_BAT + 40, "50_Heikhal", MAT_OR_PLAQUE())
box("Ulam_or_est_linteau", HX_E, HX_E + EPAISSEUR_PLACAGE, -5, 5, Z_BAT + 20, Z_BAT + 40, "40_Ulam", MAT_OR_PLAQUE())

# --- Ligne de toit (Middot 4:6) : מַעֲקֶה de 3 amot, puis אַמָּה כָּלֵה עוֹרֵב — les pointes
#     que Josèphe voit d'en bas, « on its top it had spikes with sharp points, to
#     prevent any pollution of it by birds sitting upon it » (Guerre V, 5, 6). Les deux
#     tiennent DANS les 100 amot : le garde-corps n'est pas posé sur un mur de 100, il
#     est ce qui monte de 96 à 99. R. Yehouda (là-bas) ne compte pas le kaleh orev dans
#     la mesure et donne 4 amot au maake ; le film suit le tana kama.
#     Le pourtour n'est pas un rectangle : l'Oulam déborde de 15 amot au nord et au sud
#     (Middot 4:7), et le toit décroche donc à l'aplomb du mur du Heikhal.
POURTOUR_TOIT = [
    ("est",         BX_E - MAAKE_EP, BX_E,         -50, 50),
    ("sud_oulam",   HX_E, BX_E - MAAKE_EP,            -50, -50 + MAAKE_EP),
    ("nord_oulam",  HX_E, BX_E - MAAKE_EP,            50 - MAAKE_EP, 50),
    ("retour_sud",  HX_E, HX_E + MAAKE_EP,            -50 + MAAKE_EP, -35 + MAAKE_EP),
    ("retour_nord", HX_E, HX_E + MAAKE_EP,            35 - MAAKE_EP, 50 - MAAKE_EP),
    ("sud_corps",   BX_O, HX_E,                       -35, -35 + MAAKE_EP),
    ("nord_corps",  BX_O, HX_E,                       35 - MAAKE_EP, 35),
    ("ouest",       BX_O, BX_O + MAAKE_EP,            -35 + MAAKE_EP, 35 - MAAKE_EP),
]
for suffixe, xa, xb, ya, yb in POURTOUR_TOIT:
    box(f"Maake_{suffixe}", xa, xb, ya, yb, Z_TOIT, Z_TOIT + MAAKE_H, "50_Heikhal", MAT_MARBRE_HERODE())
    box(f"Kaleh_orev_{suffixe}", xa, xb, ya, yb, Z_TOIT + MAAKE_H, Z_FAITE, "50_Heikhal", MAT_BRONZE())
# Fenêtres hautes (repères pour l'éclairage) : 4 par côté, étroites dedans / larges dehors
for i in range(4):
    x = HK0 - 6 - i * 9
    box(f"Fenetre_N_{i}", x - 1.5, x + 1.5, 10, 35, Z_BAT + 30, Z_BAT + 36, "50_Heikhal", MAT_CHAUX())
    box(f"Fenetre_S_{i}", x - 1.5, x + 1.5, -35, -10, Z_BAT + 30, Z_BAT + 36, "50_Heikhal", MAT_CHAUX())

# --- Ustensiles du Heikhal (Yoma 33b ; Menachot 98b) : dans les deux tiers ouest,
#     à 2.5 amot des murs. Table au NORD, Menora au SUD, autel d'or entre les deux, vers l'est.
XU = -125
# Shoul'han 2 × 1 × 1.5, longueur E-O (Rambam Beit HaBe'hira 3:12), à 2,5 amot du mur nord (Yoma 33b)
TEFAH = 1 / 6
YS0, YS1 = 6.5, 7.5
Z_TABLE = Z_BAT + 1.5
box("Shulchan", XU - 1, XU + 1, YS0, YS1, Z_BAT, Z_TABLE, "70_Kelim", MAT_OR())
# Le'hem hapanim (Rambam Temidin 5:9 ; Mena'hot 94b, 96a) : pain 5 × 6 tefa'him, fond d'un tefa'h,
# deux parois relevées de 7 etzbaot ; deux piles de 6 séparées de 2 tefa'him, 3 kanim entre les pains
H_PAIN, PAS_PAIN = 7 / 4 * TEFAH, 2 * TEFAH
for k in range(2):
    x0 = XU - 1 + k * 7 * TEFAH
    x1 = x0 + 5 * TEFAH
    for p in range(6):
        z = Z_TABLE + p * PAS_PAIN
        box(f"Lechem_{k}{p}", x0, x1, YS0, YS1, z, z + TEFAH, "70_Kelim", MAT_CHAUX())
        for cote, ya, yb in (("S", YS0, YS0 + 0.08), ("N", YS1 - 0.08, YS1)):
            box(f"Lechem_{k}{p}_paroi_{cote}", x0, x1, ya, yb, z, z + H_PAIN, "70_Kelim", MAT_CHAUX())
        if p < 5:   # kanim : 3 sous chaque pain sauf le premier, 2 sous le dernier (Rambam 3:15)
            for q, xq in enumerate((x0 + 1 * TEFAH, x0 + 2.5 * TEFAH, x0 + 4 * TEFAH)[: 2 if p == 4 else 3]):
                cyl_between(f"Kaneh_{k}{p}{q}", (xq, YS0 - 0.15, z + H_PAIN), (xq, YS1 + 0.15, z + H_PAIN), 0.03, "70_Kelim")
    # snifim : montants d'or au sol de part et d'autre de la Table, dépassant les piles (Mena'hot 11:6 ; 94b)
    Z_SNIF = Z_TABLE + 6 * PAS_PAIN + 0.3
    for cote, y in (("S", YS0 - 0.1), ("N", YS1 + 0.1)):
        box(f"Snif_{k}{cote}", (x0 + x1) / 2 - 0.08, (x0 + x1) / 2 + 0.08, y - 0.04, y + 0.04, Z_BAT, Z_SNIF, "70_Kelim", MAT_OR())
    # bazikh d'encens posé sur la pile (Rambam 3:14)
    cyl(f"Bazikh_{k}", (x0 + x1) / 2, (YS0 + YS1) / 2, Z_TABLE + 5 * PAS_PAIN + TEFAH, Z_TABLE + 5 * PAS_PAIN + TEFAH + 0.12, 0.15, "70_Kelim", MAT_OR())
# Mizbea'h HaZahav 1 × 1 × 2, au centre, légèrement vers l'est, quatre cornes (Ex 30:2)
box("Mizbeach_Zahav", -119.5, -118.5, -0.5, 0.5, Z_BAT, Z_BAT + 2, "70_Kelim", MAT_OR())
for ns, cy in (("S", -0.5), ("N", 0.5 - 0.15)):
    for eo, cx in (("O", -119.5), ("E", -118.5 - 0.15)):
        box(f"Mizbeach_Zahav_keren_{ns}{eo}", cx, cx + 0.15, cy, cy + 0.15, Z_BAT + 2, Z_BAT + 2.15, "70_Kelim", MAT_OR())
# Menora : 18 tefa'him = 3 amot, 7 branches dans le plan N-S, trois marches devant
YM = -7.5
for i in range(3):
    box(f"Menora_marche_{i}", XU + 1.2 + i * 0.4, XU + 1.6 + i * 0.4, YM - 1.5, YM + 1.5,
        Z_BAT, Z_BAT + 0.3 * (3 - i), "70_Kelim")
cyl("Menora_pied", XU, YM, Z_BAT, Z_BAT + 0.25, 0.5, "70_Kelim", MAT_OR())
cyl_between("Menora_tige", (XU, YM, Z_BAT + 0.25), (XU, YM, Z_BAT + 3), 0.08, "70_Kelim")
COUPE_Z = Z_BAT + 3            # lèvre de la coupe
COUPE_HAUT = COUPE_Z + 0.15    # et son bord supérieur
coupes = []                    # (suffixe, y) de chaque coupe, pour y poser sa flamme
for k, h in enumerate([1.2, 1.6, 2.0]):
    d = (3 - k) * 0.35 + 0.35   # écartement des branches
    for s in (-1, 1):
        cote = 'S' if s < 0 else 'N'
        if MENORA_DROITE:
            cyl_between(f"Menora_branche_{k}{cote}",
                        (XU, YM, Z_BAT + h), (XU, YM + s * d, COUPE_Z), 0.06, "70_Kelim")
        else:   # version "courbe" approximée en deux segments
            cyl_between(f"Menora_branche_{k}{cote}a",
                        (XU, YM, Z_BAT + h), (XU, YM + s * d, Z_BAT + h + 0.15), 0.06, "70_Kelim")
            cyl_between(f"Menora_branche_{k}{cote}b",
                        (XU, YM + s * d, Z_BAT + h + 0.15), (XU, YM + s * d, COUPE_Z), 0.06, "70_Kelim")
        cyl(f"Menora_coupe_{k}{cote}", XU, YM + s * d, COUPE_Z, COUPE_HAUT, 0.12,
            "70_Kelim", MAT_OR())
        coupes.append((f"{k}{cote}", YM + s * d))
cyl("Menora_coupe_centre", XU, YM, COUPE_Z, COUPE_HAUT, 0.12, "70_Kelim", MAT_OR())
coupes.append(("centre", YM))
# Flammes (lumières) : une petite lampe ponctuelle par coupe, 0,2 ama au-dessus de
# son milieu. Les coupes se donnent ici en coordonnées et non en relisant leur objet :
# un volume construit en bpy.data porte sa position dans son maillage, et son
# `location` vaut zéro.
for suffixe, y in coupes:
    l = lampe(f"Menora_flamme_{suffixe}", 'POINT',
              (m(XU), m(y), m((COUPE_Z + COUPE_HAUT) / 2 + 0.2)))
    l.data.energy = 15
    l.data.color = (1.0, 0.75, 0.4)
    l.data.shadow_soft_size = m(0.05)
    link_to(l, "70_Kelim")

# --- Les deux Parokhot (Yoma 5:1) : extérieure agrafée au SUD, intérieure au NORD
box("Parokhet_ext", TR0 - 0.17, TR0, -10, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_TISSU())
box("Parokhet_int", TR1, TR1 + 0.17, -10, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_TISSU())
empty("Parokhet_ext_agrafe_SUD", TR0, -9.5, Z_BAT + 20, "60_KodeshHakodashim")
empty("Parokhet_int_agrafe_NORD", TR1, 9.5, Z_BAT + 20, "60_KodeshHakodashim")
# Les badim de l'Arche pressent le rideau et se voient du Heikhal « comme deux seins »
# (Yoma 54a, Menachot 98b, Melakhim I 8:8) : deux demi-sphères de tissu, à la hauteur
# des barres, de part et d'autre de l'axe.
for ns, y in (("N", ARON_Y_BAD), ("S", -ARON_Y_BAD)):
    sphere(f"Parokhet_ext_bosse_{ns}", TR0 - 0.15, y, ARON_Z_BAD, 0.45,
           "60_KodeshHakodashim", MAT_TISSU())

# --- Kodesh HaKodashim : même placage. « כל הבית » ne s'arrête pas au Heikhal, et
#     Melakhim I 6:20-22 dore explicitement le devir au Premier Temple. La pièce n'a
#     aucune ouverture et reste noire : l'or n'y rend que sous la braise de la ma'hta —
#     ce qui est exactement la seule lumière du plan 11.
box("KhK_or_mur_N", KK1, KK0, 10 - EPAISSEUR_PLACAGE, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())
box("KhK_or_mur_S", KK1, KK0, -10, -10 + EPAISSEUR_PLACAGE, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())
box("KhK_or_mur_O", KK1, KK1 + EPAISSEUR_PLACAGE, -10, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())
box("KhK_or_plafond", KK1, KK0, -10, 10, Z_BAT + 40 - EPAISSEUR_PLACAGE, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())

# --- Kodesh HaKodashim : Even HaShetiya (3 doigts ≈ 0.125 ama, Yoma 5:2)
KKC = (KK0 + KK1) / 2
ZE = Z_BAT + 0.125          # dessus de la pierre
box("Even_HaShetiya", KKC - 1.5, KKC + 1.5, -1.5, 1.5,
    Z_BAT, ZE, "60_KodeshHakodashim", MAT_SOL())
empty("Point_Machta_braises", ARON_X_MACHTA, 0, Z_BAT + 0.3, "60_KodeshHakodashim")

# --- Aron HaBrit, posé sur la pierre (Rambam, Beit HaBe'hira 4:1) — le Temple à venir
#     rend l'Arche cachée (Yoma 54a). Cotes : Shemot 25:10-22 ; Soucca 5a-b ; Menachot 98b.
#     2,5 × 1,5 × 1,5 amot, grand côté nord-sud, badim est-ouest le long de la largeur
#     (Menachot 98b), anneaux aux coins supérieurs (Rashi Shemot 25:12), kaporet d'un
#     tefa'h, keruvim de 10 tefa'him, ailes au-dessus des têtes, l'une vers l'autre
#     (Soucca 5b). Les badim courent jusqu'à la parokhet intérieure : c'est ce qui rend
#     physiques « entre les deux badim » (Yoma 5:1, 5:3) et les bosses du rideau.
H_KERUV = 10 / 6      # 10 tefa'him (Soucca 5b)

def keruv(name, x, y, z0, col, vers, h=H_KERUV, epaules=0.29):
    """Keruv de la kaporet, ligne Rashi + Yoma 54a-b : enfant (Soucca 5b) **agenouillé**
    sur la kaporet, d'une pièce avec elle (miksha, Rashi Shemot 25:18), penché vers
    l'autre keruv, bras tendus jusqu'à le toucher (« מעורים זה בזה », Yoma 54a), tête
    inclinée vers la kaporet (Bava Batra 99a), deux ailes larges qui partent des
    omoplates et montent en diagonale jusqu'à la hauteur des têtes, en dais sur la
    kaporet (Rashi Shemot 25:20), chacune un éventail de trois plumes. Bâti à l'origine
    face à l'ouest comme une silhouette, puis tourné vers le centre. `vers` : ±1, le
    sens en y du centre de la kaporet ; `h`, `epaules` distinguent le garçon de la
    fille (Yoma 54b). Une base conique se lisait en queue d'écailles, des ailes à plat
    au-dessus de la tête en chapeau : d'où les jambes et les ailes qui partent du dos."""
    or_ = MAT_OR()
    hz = 0.30 * h          # hauteur des hanches, à genoux
    pieces = [
        box(f"{name}_torse", -0.20, 0.06, -0.17, 0.17, hz, hz + 0.36 * h, col, or_),
        box(f"{name}_epaules", -0.28, -0.02, -epaules, epaules, hz + 0.30 * h, hz + 0.37 * h, col, or_),
        cyl(f"{name}_cou", -0.22, 0, hz + 0.35 * h, hz + 0.42 * h, 0.07, col, or_, verts=8),
        sphere(f"{name}_tete", -0.32, 0, hz + 0.47 * h, 0.105 * h, col, or_, segs=12),
    ]
    for s_ in (-1, 1):
        yj = s_ * 0.13
        pieces.append(box(f"{name}_cuisse{s_:+d}", -0.12, 0.18, yj - 0.08, yj + 0.08, 0.13 * h, hz + 0.02, col, or_))
        pieces.append(box(f"{name}_jambe{s_:+d}", 0.06, 0.62, yj - 0.07, yj + 0.07, 0, 0.13 * h, col, or_))
        pieces.append(cyl_between(f"{name}_bras{s_:+d}", (-0.18, s_ * (epaules - 0.06), hz + 0.32 * h),
                                  (-0.78, s_ * 0.12, hz + 0.24 * h), 0.06, col, or_, verts=8))
        yw = s_ * 0.14
        for k in range(3):
            xt, zt = -0.86 + 0.08 * k, h + 0.02 - 0.10 * k
            yt = yw + s_ * (0.22 + 0.20 * k)
            wr, wt = 0.16, 0.12
            quad = [(0.08, yw - wr / 2, hz + 0.28 * h), (0.08, yw + wr / 2, hz + 0.28 * h),
                    (xt, yt + wt / 2, zt), (xt, yt - wt / 2, zt)]
            pieces.append(plaque(f"{name}_aile{s_:+d}_plume{k}", quad, 0.03, col, or_))
    _poser(pieces, x, y, z0, -vers * math.pi / 2)   # face à l'ouest, tournée vers le centre

ARON = "65_Aron"
ARON_X0, ARON_X1, ARON_Y = KKC - 0.75, KKC + 0.75, 1.25
Z_KAPORET = ZE + 1.5
box("Aron_caisse", ARON_X0, ARON_X1, -ARON_Y, ARON_Y, ZE, Z_KAPORET, ARON, MAT_OR())
box("Aron_kaporet", ARON_X0, ARON_X1, -ARON_Y, ARON_Y, Z_KAPORET, Z_KAPORET + 1 / 6, ARON, MAT_OR())
# Zer (Shemot 25:11 ; Rashi ; Yoma 72b) : trois caisses emboîtées, la caisse d'or
# extérieure plus haute que les autres — son rebord monte autour de la kaporet et la
# dépasse un peu, « comme une couronne » : le keter Torah. Un bandeau qui entoure la
# kaporet, puis une lèvre plus saillante au sommet.
Z_ZER = Z_KAPORET + 1 / 6 + 0.06
for etage, (saillie, zb, zh) in enumerate(((0.06, Z_KAPORET - 0.14, Z_ZER - 0.05),
                                           (0.10, Z_ZER - 0.05, Z_ZER))):
    for cote, (x0, x1, y0, y1) in (("N", (ARON_X0 - saillie, ARON_X1 + saillie, ARON_Y - 0.02, ARON_Y + saillie)),
                                  ("S", (ARON_X0 - saillie, ARON_X1 + saillie, -ARON_Y - saillie, -ARON_Y + 0.02)),
                                  ("E", (ARON_X1 - 0.02, ARON_X1 + saillie, -ARON_Y - saillie, ARON_Y + saillie)),
                                  ("O", (ARON_X0 - saillie, ARON_X0 + 0.02, -ARON_Y - saillie, ARON_Y + saillie))):
        box(f"Aron_zer{etage}_{cote}", x0, x1, y0, y1, zb, zh, ARON, MAT_OR())

# Devant l'Arche, entre les badim (Rambam, Beit HaBe'hira 4:1 ; Horayot 12a) : la
# fiole de manne en terre (Shemot 16:33, Rashi), le bâton d'Aharon avec ses amandes et
# ses fleurs (Bamidbar 17:23), la fiole d'huile d'onction, le coffret des Philistins
# (Shmouel I 6:8). Sur la pierre, de part et d'autre de la place de la ma'hta.
X_DEVANT = ARON_X1 + 0.32
revolution("Aron_tsintsenet_man", X_DEVANT, 0.62, ZE,
           [(0.07, 0), (0.12, 0.05), (0.13, 0.20), (0.09, 0.28), (0.06, 0.31), (0.07, 0.35),
            (0.05, 0.35), (0.0, 0.33)], ARON, MAT_PIERRE(), verts=16)
revolution("Aron_pakh_shemen", X_DEVANT, -0.62, ZE,
           [(0.06, 0), (0.10, 0.04), (0.10, 0.16), (0.04, 0.22), (0.035, 0.30), (0.05, 0.32),
            (0.0, 0.31)], ARON, MAT_PIERRE(), verts=16)
box("Aron_argaz", ARON_X1 + 0.06, ARON_X1 + 0.50, 0.88, 1.28, ZE, ZE + 0.28, ARON, MAT_CEDRE())
box("Aron_argaz_couvercle", ARON_X1 + 0.03, ARON_X1 + 0.53, 0.85, 1.31, ZE + 0.28, ZE + 0.34, ARON, MAT_CEDRE())
PIED_MATE, TETE_MATE = (ARON_X1 + 0.62, -1.02, ZE), (ARON_X1 + 0.02, -1.14, Z_ZER + 0.30)
cyl_between("Aron_mate_Aharon", PIED_MATE, TETE_MATE, 0.03, ARON, MAT_CHENE(), verts=8)
for k, t in enumerate((0.80, 0.88, 0.96)):
    x_ = PIED_MATE[0] + t * (TETE_MATE[0] - PIED_MATE[0])
    y_ = PIED_MATE[1] + t * (TETE_MATE[1] - PIED_MATE[1]) + (0.05 if k % 2 else -0.05)
    z_ = PIED_MATE[2] + t * (TETE_MATE[2] - PIED_MATE[2])
    sphere(f"Aron_mate_amande_{k}", x_, y_, z_, 0.035, ARON, MAT_PIERRE(), segs=8)

# Le garçon au nord, la fille au sud (Yoma 54b), un peu plus menue.
keruv("Aron_keruv_N", KKC, 0.85, Z_KAPORET + 1 / 6, ARON, vers=-1)
keruv("Aron_keruv_S", KKC, -0.85, Z_KAPORET + 1 / 6, ARON, vers=1, h=0.94 * H_KERUV, epaules=0.25)
for ns, sy in (("N", 1), ("S", -1)):
    for eo, x in (("E", ARON_X1 - 0.10), ("O", ARON_X0 + 0.10)):
        tore(f"Aron_anneau_{ns}{eo}", x, sy * ARON_Y_BAD, ARON_Z_BAD, 0.12, 0.03, ARON,
             MAT_OR(), rotation=(0, math.pi / 2, 0), majeur=24, mineur=8)
    cyl_between(f"Aron_bad_{ns}", (ARON_X0 - 0.5, sy * ARON_Y_BAD, ARON_Z_BAD),
                (TR1 + 0.05, sy * ARON_Y_BAD, ARON_Z_BAD), 0.06, ARON, MAT_OR(), verts=12)

# ----------------------------------------------------------------------------
# 75 — PROXYS DE SUJET, UNE COLLECTION PAR PLAN
#   Volumes grossiers là où le sujet du plan n'est pas de l'architecture (kohanim,
#   taureau, ma'hta). Ils ne visent pas la ressemblance : ils donnent aux passes
#   Depth/Normal une structure stable, sans laquelle l'i2i réinvente le sujet à
#   chaque image et le plan perd sa cohérence temporelle.
#
#   Une collection par plan, et non une seule pour tous : un sujet qui traîne dans
#   le cadre d'un autre plan devient un objet inventé (la silhouette du plan 12 est
#   ressortie en second candélabre au fond du Heikhal). Une collection unique
#   obligeait à tout masquer d'un coup — et masquer les prosternés du plan 6 pour
#   rendre le plan 1 vidait du même geste le Doukhan de ses Léviim. L'export ne
#   montre que la collection du plan qu'il rend.
# ----------------------------------------------------------------------------
H_HOMME = 3.65        # 1.75 m en amot


def proxies_du_plan(numero):
    return f"75_Plan{numero:02d}"


# Tenues (fiche §12, bloc FIGURES de prompts_par_plan.md) : le peuple en habits
# d'aujourd'hui, talith sur la tête ou non ; les Léviim en robe de lin unie ; les
# cohanim dans les quatre vêtements blancs, coiffe plate (Yoma 7:5). Trois corps
# différents, et pas trois teintes : à vingt amot le styliseur ne lit qu'une silhouette.
AM, TALITH, LEVI, KOHEN = "am", "talith", "levi", "kohen"
TENUES_AM = (TALITH, TALITH, TALITH, AM, AM)

def _etoffe(tenue, nom):
    if tenue in (LEVI, KOHEN):
        return MAT_LIN()
    return MAT_FOULE() if alea(nom, 6) < 0.6 else MAT_TALITH()

def _pieces_de_tenue(name, tenue, h, col):
    """Ce qui distingue la tenue au-dessus des épaules et à la taille."""
    if tenue == TALITH:
        # Capuche du talith gadol : des épaules jusqu'au-dessus de la tête, qu'elle
        # enveloppe — la tête ronde nue est le signe de la kippa, pas du talith.
        return [cone(f"{name}_talith", 0, 0, 0.74 * h, 1.03 * h, 0.54 * h / H_HOMME,
                     0.06 * h, col, MAT_TALITH(), verts=10)]
    if tenue == KOHEN:
        k = h / H_HOMME
        return [cyl(f"{name}_coiffe", 0, 0, 0.985 * h, 1.02 * h, 0.09 * h, col, MAT_LIN(), verts=10),
                box(f"{name}_avnet", -0.30 * k, 0.30 * k, -0.38 * k, 0.38 * k,
                    0.61 * h, 0.655 * h, col, MAT_LIN())]
    return []

def silhouette(name, x, y, z0, col, tenue=KOHEN, h=H_HOMME, lacet=0.0):
    """Figure debout : robe, torse, épaules, bras, cou, tête, plus sa tenue.

    Le fût à tête ronde d'avant était un volume de tour : le profil d'une colonne
    miniature, le plus large en bas, la boule posée à même le sommet. Le styliseur le
    repeignait donc en borne de pierre et ajoutait les fidèles du prompt derrière
    (CAM_02). Ce qu'un volume tourné ne peut pas donner, c'est l'anisotropie d'un
    corps : épaules larges de face, minces de profil, et deux bras détachés du tronc.
    Les pièces sont bâties à l'origine, face à l'ouest, puis posées : `lacet` tourne la
    figure autour de sa verticale (radians), et c'est ce qui défait le garde-à-vous
    d'une foule. Cotes proportionnelles à `h` pour que les ketanim restent des enfants.
    """
    corps = _etoffe(tenue, name)
    k = h / H_HOMME
    ep, prof = 0.50 * k, 0.26 * k
    pieces = [
        cone(f"{name}_robe", 0, 0, 0, 0.52 * h, 0.44 * k, 0.32 * k, col, corps, verts=12),
        box(f"{name}_torse", -prof, prof, -0.34 * k, 0.34 * k, 0.50 * h, 0.83 * h, col, corps),
        box(f"{name}_epaules", -prof, prof, -ep, ep, 0.76 * h, 0.83 * h, col, corps),
        cyl(f"{name}_cou", 0, 0, 0.80 * h, 0.88 * h, 0.13 * k, col, corps, verts=8),
        sphere(f"{name}_tete", 0, 0, 0.925 * h, 0.080 * h, col, corps, segs=8),
    ]
    for s in (-1, 1):
        pieces.append(cyl(f"{name}_bras{s:+d}", 0, s * (ep - 0.11 * k), 0.50 * h,
                          0.79 * h, 0.11 * k, col, corps, verts=8))
    pieces += _pieces_de_tenue(name, tenue, h, col)
    _poser(pieces, x, y, z0, lacet)

def instrument_de_levi(nom, genre, x, y, z0, col):
    """Kinor, nevel ou tziltzal tenu devant le torse, vers le Sanctuaire (ouest).

    C'est l'instrument qui dit « Lévi » : la robe de lin est celle des cohanim, et
    l'estrade ne se voit pas de partout. Kinor et nevel sont des cadres — caisse,
    deux bras, joug — et non des planches, qui se lisaient en livres ; le tziltzal
    une paire de disques de bronze.
    """
    bois, devant = MAT_CHENE(), x - 0.30
    if genre == "tziltzal":
        for s in (-1, 1):
            cyl_between(f"{nom}_tziltzal{s:+d}", (devant - 0.12, y + s * 0.32, z0 + 2.2),
                        (devant, y + s * 0.32, z0 + 2.2), 0.28, col, MAT_BRONZE(), verts=12)
        return
    large, haut = (0.30, 2.65) if genre == "kinor" else (0.42, 2.95)
    if genre == "kinor":
        box(f"{nom}_{genre}_caisse", devant - 0.12, devant, y - large, y + large,
            z0 + 1.55, z0 + 1.85, col, bois)
    else:
        cone(f"{nom}_{genre}_caisse", devant - 0.10, y, z0 + 1.25, z0 + 1.95, large, 0.30,
             col, bois, verts=10)
    for s in (-1, 1):
        cyl(f"{nom}_{genre}_bras{s:+d}", devant - 0.06, y + s * (large - 0.04),
            z0 + 1.85, z0 + haut, 0.04, col, bois, verts=6)
    box(f"{nom}_{genre}_joug", devant - 0.10, devant - 0.02, y - large - 0.01,
        y + large + 0.01, z0 + haut - 0.05, z0 + haut + 0.03, col, bois)

def kohen_prosterne(name, x, y, z0, col, mat=None):
    """Couché face contre terre, tête vers l'ouest."""
    box(name, x - H_HOMME / 2, x + H_HOMME / 2, y - 0.55, y + 0.55,
        z0, z0 + 0.45, col, mat or MAT_LIN())

def kohen(name, x, y, z0, col):
    """Un cohen seul, sujet d'un plan : la silhouette en tenue de service."""
    silhouette(name, x, y, z0, col, KOHEN)

def machta(name, x, y, z0, col, avec_braises=True, manche_vers=None):
    """Ma'hta de Kippour : bassin d'or de trois kabin, manche long.

    *Yoma* 4:4 tranche les trois choses qu'une image montre : elle est **d'or** ce
    jour-là (« הַיּוֹם חוֹתֶה בְשֶׁל זָהָב »), elle tient **trois kabin** (« בְשֶׁל שְׁלשֶׁת קַבִּין »)
    et son manche est **long** quand celui des autres jours est court (« בְּכָל יוֹם
    הָיְתָה יָדָהּ קְצָרָה, וְהַיּוֹם אֲרֻכָּה ») — long pour que l'avant-bras en porte le poids.
    Aucune source n'en donne le diamètre : le bassin est dimensionné sur sa
    contenance, 3 kabin = 4,14 l = 0,037 ama³ (kav 1,38 l, Rav 'Haïm Naeh, comme
    l'ama de la fiche §0). Le bassin d'avant en faisait 42 : une bassine de 53 cm de
    large portée à bout de bras.

    `manche_vers` : le point (amot) vers lequel le manche court — la main, puis
    l'avant-bras. Par défaut plein est, pour la ma'hta posée seule.
    """
    revolution(f"{name}_bassin", x, y, z0,
               [(0.20, 0.0), (0.25, 0.01), (0.27, 0.06), (0.29, 0.13), (0.32, 0.16),
                (0.33, 0.175), (0.30, 0.175), (0.28, 0.15), (0.26, 0.06), (0.0, 0.03)],
               col, MAT_OR(), verts=24)
    bout = manche_vers or (x + 1.30, y, z0 + 0.09)
    cyl_between(f"{name}_manche", (x, y, z0 + 0.09), bout, 0.045, col, MAT_OR(), verts=10)
    px, py, pz = bout
    dx, dy = px - x, py - y
    d = math.hypot(dx, dy) or 1.0
    cyl_between(f"{name}_collet", (x + 0.31 * dx / d, y + 0.31 * dy / d, z0 + 0.09),
                (x + 0.40 * dx / d, y + 0.40 * dy / d, z0 + 0.09), 0.065, col, MAT_OR(), verts=10)
    sphere(f"{name}_pommeau", px, py, pz, 0.07, col, MAT_OR(), segs=10)
    if avec_braises:
        cyl(f"{name}_braises", x, y, z0 + 0.11, z0 + 0.16, 0.255, col,
            bpy.data.materials.get("Braise") or MAT_BRONZE(), verts=20)
        l = lampe(f"{name}_lueur", 'POINT', (m(x), m(y), m(z0 + 0.5)))
        l.data.energy = 8
        l.data.color = (1.0, 0.45, 0.15)
        l.data.shadow_soft_size = m(0.4)
        link_to(l, col)

def kaf(name, x, y, z0, col, avec_ketoret=True):
    """Kaf : le bol d'or qui porte la ketoret, tenu dans la main gauche (*Yoma* 5:1).

    *Tamid* 5:4 en donne la forme et la contenance : « וְהַכַּף דּוֹמֶה לְתַרְקַב גָּדוֹל שֶׁל
    זָהָב, מַחֲזִיק שְׁלשֶׁת קַבִּים » — un grand récipient de mesure en or, trois kabin,
    donc un bol **ouvert et rond**, pas une boîte. Le bazakh posé dedans et son
    couvercle appartiennent au tamid de chaque jour ; à Kippour le Cohen Gadol y
    verse ses deux poignées et la mesure du kaf est celle de ses mains (*Yoma* 5:1,
    « הַגָּדוֹל לְפִי גָדְלוֹ… וְכָךְ הָיְתָה מִדָּתָהּ »), puis il en tient la **lèvre** du bout
    des doigts pour en reverser la ketoret (Rambam, *Avodat Yom HaKippurim* 4:1) —
    d'où la lèvre évasée, seule prise que la forme donne.

    Un tronc de cône coiffé d'un anneau se rendait en tambour ; le bol est un profil
    de révolution — pied, panse, lèvre — à paroi mince, et la ketoret un dôme, pas
    une galette. Aucune source ne donne de manche : *Yoma* 5:1 y fait verser deux
    poignées, c'est un récipient ouvert.
    """
    revolution(f"{name}_bol", x, y, z0,
               [(0.10, 0.0), (0.19, 0.05), (0.235, 0.14), (0.24, 0.23), (0.27, 0.29),
                (0.275, 0.31), (0.25, 0.31), (0.225, 0.27), (0.215, 0.14), (0.17, 0.05),
                (0.0, 0.04)], col, MAT_OR(), verts=24)
    if avec_ketoret:
        revolution(f"{name}_ketoret", x, y, z0,
                   [(0.20, 0.22), (0.21, 0.26), (0.19, 0.31), (0.14, 0.36),
                    (0.07, 0.395), (0.0, 0.41)], col, MAT_KETORET(), verts=20)

def taureau(name, x, y, z0, col, tete=(0, -1)):
    """Par (~2.6 m au garrot compris). `tete` : direction unitaire de la tête (défaut : sud)."""
    tx, ty = tete
    px, py = -ty, tx          # axe transversal
    def pt(a, t):             # a le long de l'axe tête, t en travers
        return (x + a * tx + t * px, y + a * ty + t * py)
    def boite(nm, a0, a1, t0, t1, z0_, z1_):
        xs = [pt(a, t)[0] for a in (a0, a1) for t in (t0, t1)]
        ys = [pt(a, t)[1] for a in (a0, a1) for t in (t0, t1)]
        box(nm, min(xs), max(xs), min(ys), max(ys), z0_, z1_, col, MAT_BETE())
    boite(f"{name}_tronc", -2.7, 2.7, -0.9, 0.9, z0 + 1.7, z0 + 3.6)
    boite(f"{name}_tete", 2.7, 4.2, -0.6, 0.6, z0 + 2.4, z0 + 3.5)
    for a in (-2.1, 2.1):
        for t in (-0.65, 0.65):
            cx, cy = pt(a, t)
            cyl(f"{name}_patte_{a:+.0f}{t:+.0f}", cx, cy, z0, z0 + 1.7, 0.22, col, MAT_BETE(), verts=12)

# --- CAM_05 : le par entre l'Oulam et le Mizbea'h (Yoma 3:8) — « רֹאשׁוֹ לַדָּרוֹם וּפָנָיו
#     לַמַּעֲרָב, וְהַכֹּהֵן עוֹמֵד בַּמִּזְרָח וּפָנָיו לַמַּעֲרָב ». Le Kohen Gadol se tenait à l'OUEST de
#     la tête, c'est-à-dire du mauvais côté ; il est à l'est, face à l'ouest, et reste
#     donc de dos pour une caméra qui vient du nord-est.
#     Tout le monde est sur les 10 amot de plat : les douze marches en prennent 12 sur
#     les 22 (Middot 3:6), et les proxys avaient les pieds enfouis dedans.
PLAN_05 = proxies_du_plan(5)
taureau("Par_HaHatat", -61.5, 4, Z_AZ, PLAN_05, tete=(0, -1))
kohen("KohenGadol_par", -59, 0.5, Z_AZ, PLAN_05)
for nm, (x, y) in {"nord_O": (-63, 9), "nord_E": (-57, 9), "sud_O": (-63, -3), "sud_E": (-57, -3)}.items():
    kohen(f"Kohen_par_{nm}", x, y, Z_AZ, PLAN_05)

# --- CAM_03 : le Kohen Gadol de dos devant la fenêtre du Beit Avtinas, table des épices
# Tout est calé sur PORTE_MAYIM : la chambre a suivi la porte quand elle est passée
# du milieu du mur sud à son extrémité est.
PLAN_03 = proxies_du_plan(3)
kohen("KohenGadol_Avtinas", PORTE_MAYIM, -76, Z_AZ + 26, PLAN_03)
# La table court le long du mur ouest, pas en travers : posée face à la caméra elle
# ne restait qu'un liseré au bas du cadre, et le pilon de la ketoret est le second
# sujet du plan. Onze coupes — les onze épices de Keritot 6a — plus le mortier.
# Collée au mur ouest (x -3,5..-1,5 depuis la porte) elle tombait au bord du cadre à
# 28 mm : les coupes flottaient à demi hors champ. Décalée d'une ama vers l'axe.
box("Avtinas_table", PORTE_MAYIM - 2.5, PORTE_MAYIM - 0.5, -78, -74, Z_AZ + 26, Z_AZ + 28, PLAN_03)
for i in range(11):
    cyl(f"Avtinas_coupe_{i:02d}", PORTE_MAYIM - 1.9 + 0.8 * (i % 2), -77.6 + 0.26 * i,
        Z_AZ + 28, Z_AZ + 28.35, 0.28, PLAN_03, MAT_BRONZE(), verts=12)
cyl("Avtinas_mortier", PORTE_MAYIM - 1.5, -74.6, Z_AZ + 28, Z_AZ + 28.8, 0.5, PLAN_03, verts=16)
box("Avtinas_pilon", PORTE_MAYIM - 1.65, PORTE_MAYIM - 0.6, -74.85, -74.55,
    Z_AZ + 28.8, Z_AZ + 29.1, PLAN_03)

# --- CAM_06 : prosternation. Elle remplace la foule debout, donc elle en occupe
# exactement l'emprise : les 11 amot de l'Ezrat Israël ET l'Ezrat Cohanim, sur toute
# la largeur, puis l'Ezrat Nashim — « la prosternation concerne les deux cours »
# (Yoma 6:2). Trente-trois silhouettes couchées sur trois colonnes tenaient lieu de
# « toute l'Azara » : à 35 amot de haut et 80 de distance elles ne faisaient plus une
# vague, mais trois traits sur un dallage vide.
PLAN_06 = proxies_du_plan(6)
for i, x in enumerate(plage(-20, -2, 2.2)):
    for j, y in enumerate(plage(-66, 66, 2)):
        if abs(y) < 4:      # l'allée de Nikanor reste dégagée (Middot 2:4)
            continue
        kohen_prosterne(f"Prosterne_Azara_{i:02d}{j:02d}", x, y, Z_AZ, PLAN_06)
for i, x in enumerate(plage(12, 126, 5)):
    for j, y in enumerate(plage(-66, 61, 5)):
        if abs(y) < 6:
            continue
        kohen_prosterne(f"Prosterne_EzN_{i:02d}{j:02d}", x, y, Z_EZN, PLAN_06)

# --- CAM_10 : le Kohen Gadol devant la parokhet extérieure, ma'hta et kaf aux mains
# « נָטַל אֶת הַמַּחְתָּה בִּימִינוֹ וְאֶת הַכַּף בִּשְׂמֹאלוֹ » (Yoma 5:1) : la ma'hta à droite, le kaf
# à gauche. Tourné vers l'ouest, sa droite est au nord — la ma'hta prend donc le y
# haut. Le plan est un gros plan sur les mains, et le blockout n'en donnait aucune :
# le torse s'arrêtait aux bras collés au tronc, le styliseur laissait le mannequin en
# pierre et n'avait rien où peindre une main. Les deux avant-bras vont maintenant
# jusqu'aux ustensiles, et le manche de la ma'hta court le long du droit, ce pour quoi
# Yoma 4:4 le veut long. Il regarde l'ouest : poignets et ustensiles sont à x < -136,
# devant lui — posés à l'est ils flottaient entre son dos et la caméra, et le
# styliseur peignait des mains de face sur un homme de dos (seed 101002).
PLAN_10 = proxies_du_plan(10)
kohen("KohenGadol_seuil", -136, -8.5, Z_BAT, PLAN_10)
COUDE_D, COUDE_G = (-136.0, -8.11, Z_BAT + 2.30), (-136.0, -8.89, Z_BAT + 2.30)
machta("Machta_mains", -137.00, -7.70, Z_BAT + 1.90, PLAN_10, manche_vers=COUDE_D)
kaf("Kaf_mains", -136.65, -9.45, Z_BAT + 1.95, PLAN_10)
cyl_between("KohenGadol_seuil_avantbras_d", COUDE_D, (-136.55, -7.85, Z_BAT + 2.10),
            0.12, PLAN_10, MAT_LIN(), verts=10)
cyl_between("KohenGadol_seuil_avantbras_g", COUDE_G, (-136.50, -9.25, Z_BAT + 2.15),
            0.12, PLAN_10, MAT_LIN(), verts=10)

# --- CAM_11 : ma'hta posée sur la pierre, entre les deux badim, au pied de l'Arche
#     (Yoma 5:1). Aucune figure ici (fiche 8e).
machta("Machta_posee", ARON_X_MACHTA, 0, ZE, proxies_du_plan(11))

# --- CAM_12 : franchissement de la parokhet intérieure, agrafée au NORD
# Il porte les deux ustensiles jusqu'à l'Even HaShetiya (Yoma 5:1) : la fiche les
# attend ici (§10, « Cohen Gadol et ma'hta, plans 10 et 12 »), le blockout n'avait
# que la silhouette. Ustensiles devant lui, donc à l'ouest, côté caméra.
PLAN_12 = proxies_du_plan(12)
kohen("KohenGadol_passage", -139.6, 8, Z_BAT, PLAN_12)
COUDE_P_D, COUDE_P_G = (-139.6, 8.39, Z_BAT + 2.30), (-139.6, 7.61, Z_BAT + 2.30)
machta("Machta_passage", -140.15, 8.60, Z_BAT + 2.00, PLAN_12, manche_vers=COUDE_P_D)
kaf("Kaf_passage", -140.15, 7.40, Z_BAT + 1.95, PLAN_12)
cyl_between("KohenGadol_passage_avantbras_d", COUDE_P_D, (-139.95, 8.48, Z_BAT + 2.12),
            0.12, PLAN_12, MAT_LIN(), verts=10)
cyl_between("KohenGadol_passage_avantbras_g", COUDE_P_G, (-139.95, 7.52, Z_BAT + 2.12),
            0.12, PLAN_12, MAT_LIN(), verts=10)

# ----------------------------------------------------------------------------
# 76 — FOULE DE YOM KIPPOUR
#   Les places viennent des sources, pas de la mise en scène :
#   - le peuple dans l'Ezrat Israël, bande de 11 amot au bout est de l'Azara sur
#     toute la largeur (Middot 5:1, « מקום דריסת ישראל אחת עשרה אמה ») ; il ne
#     franchit pas l'Ezrat Cohanim sinon pour semikha, she'hita, tenoufa (Kelim 1:8) ;
#   - les cohanim dans les 11 amot suivantes, l'Ezrat Cohanim (Middot 5:1) ;
#   - le débordement dans l'Ezrat Nashim (135 × 135, Middot 2:5) puis sur le Har
#     HaBayit — l'Ezrat Israël ne fait que 11 × 135 ;
#   - les Léviim sont sur le Doukhan, entre les deux cours ;
#   - personne dans l'Oulam ni le Heikhal : « et nul homme ne sera dans la tente
#     d'assignation » (Lév. 16:17 ; Yoma 5:1 ne montre que le Cohen Gadol).
#   Collection séparée des proxys : un proxy est le sujet d'un plan, la foule est
#   l'état permanent du jour — elle est là dans tous les plans qui voient l'Azara.
#   Les Léviim en font partie : postés sur le Doukhan du matin au soir, ils ne sont
#   le sujet d'aucun plan. Rangés avec les proxys, ils disparaissaient du Doukhan
#   dès qu'un plan masquait les sujets d'un autre. Le plan 6 (prosternation) est le
#   seul à masquer cette collection : il a ses propres figures couchées.
# ----------------------------------------------------------------------------
FL = "76_Foule"
# Deux étoffes, pas une : sous une seule, la foule sort du rendu en une seule valeur
# et le styliseur habille tout le monde pareil — au plan 2, trois rangs de talith
# identiques. La laine sombre est le manteau, la claire le talith sur la tête.
MAT_FOULE = lambda: etoffe("Foule_laine", (0.46, 0.42, 0.37))
MAT_TALITH = lambda: etoffe("Talith_laine", (0.80, 0.78, 0.72))


def figurant(nom, x, y, z0, col, tenues, desordre, lacet=0.35):
    """Une figure de foule : écart, taille, tenue et lacet tirés de son nom."""
    silhouette(nom, x + (alea(nom, 0) - 0.5) * desordre, y + (alea(nom, 1) - 0.5) * desordre,
               z0, col, tenues[int(alea(nom, 3) * len(tenues))],
               h=H_HOMME * (0.93 + 0.14 * alea(nom, 2)),
               lacet=(alea(nom, 5) - 0.5) * 2 * lacet)

def foule(prefixe, xs, ys, z0, tenues, col=FL, ecart_axe=0.0, desordre=1.4, lacet=0.35):
    """Foule debout sur une grille, que le tirage défait. `ecart_axe` dégage une allée
    centrée sur y = 0.

    Une grille nue se lit en rangs d'objets identiques, pas en foule, et un jitter
    d'un quart de pas n'y change rien : on voyait encore les rangs. Trois tirages la
    défont — l'écart de chaque figure (`desordre`, amplitude en amot, plus de la
    moitié du pas), son lacet (`lacet`, demi-angle en radians), et des vides : une
    case de 3 × 3 sur trois est clairsemée, et chaque figure y manque une fois sur
    deux, pour que la densité ondule au lieu de remplir. `desordre=0` et `lacet=0`
    alignent au cordeau (chœur, file).
    """
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            if abs(y) < ecart_axe:
                continue
            nom = f"{prefixe}_{i:02d}{j:02d}"
            clairseme = alea(f"{prefixe}_case_{i // 3}_{j // 3}") < 0.3
            if alea(nom, 4) < (0.5 if clairseme else 0.08):
                continue
            figurant(nom, x, y, z0, col, tenues, desordre, lacet)

def masse_foule(prefixe, xs, ys, z0, col=FL, ecart_axe=0.0):
    """Foule lointaine en blocs de 5 amot, pas en silhouettes.

    L'Ezrat Nashim fait 135 × 135 : une foule de Kippour s'y compte en milliers, que
    le blockout ne modélisera pas un par un. Un bloc à hauteur d'homme donne au
    Depth/Normal la bonne masse, et les hauteurs alternées empêchent l'ensemble de
    lire comme un mur crénelé.
    """
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            if abs(y) < ecart_axe:
                continue
            h = (3.2, 3.65, 3.9)[(i + j) % 3]
            box(f"{prefixe}_{i:02d}{j:02d}", x, x + 5, y, y + 5, z0, z0 + h,
                col, MAT_FOULE())

# Le peuple : les 11 amot de l'Ezrat Israël (x -11..0), allée dégagée devant Nikanor.
foule("Am_EzratIsrael", plage(-10, -2, 2), plage(-66, 66, 2), Z_AZ, TENUES_AM,
      ecart_axe=4)
# Les cohanim : les 11 amot suivantes (x -22..-11), en tenue de service. On s'arrête à
# l'est du Doukhan (x -13.5) et on laisse l'ouest libre pour le service. Désordre et
# lacet réduits, pas nuls : le service les range, il ne les aligne pas.
foule("Kohen_EzratKohanim", plage(-20, -15, 2.5), plage(-63, 63, 3), Z_AZ,
      (KOHEN,), desordre=1.2, lacet=0.2)
# Débordement : Ezrat Nashim, puis la cour est du Har HaBayit. L'axe y = 0 reste
# dégagé — c'est la ligne de mire de la para (Middot 2:4).
# Pas de 5 pour des blocs de 5 : jointifs. Espacés d'une ama ils se lisaient en
# caisses posées sur le dallage, et le plan 4 les prenait pour de la maçonnerie.
masse_foule("Am_EzratNashim", plage(12, 127, 5), plage(-67, 62, 5), Z_EZN, ecart_axe=6)
masse_foule("Am_HarHabayit", plage(157, 257, 5), plage(-67, 62, 5), Z_HAR, ecart_axe=10)
# Les Léviim sur le Doukhan (3 marches, x -12..-13.5). « On ne descend pas au-dessous
# de douze Léviim debout sur le Doukhan, et l'on ajoute sans limite » (Arakhin 2:6).
# Chacun tient son instrument : jamais moins de neuf kinorot, de deux nevalim, et le
# tziltzal seul (Arakhin 2:5, 2:3 ; Tamid 7:3) — neuf, deux et un font les douze.
# En rang, sans lacet : c'est un chœur.
INSTRUMENTS_DOUKHAN = ("kinor",) * 4 + ("nevel", "tziltzal", "nevel") + ("kinor",) * 5
for i, genre in enumerate(INSTRUMENTS_DOUKHAN):
    silhouette(f"Levi_{i:02d}", -12.6, -22 + i * 4, Z_AZ + 2.5, FL, LEVI)
    instrument_de_levi(f"Levi_{i:02d}", genre, -12.6, -22 + i * 4, Z_AZ + 2.5, FL)
# Les ketanim ne montent pas sur le Doukhan : ils se tiennent en bas, « la tête entre
# les jambes des Léviim » (Arakhin 2:6, R. Eliézer ben Yaakov), et chantent sans
# instrument (ibid.).
for i in range(6):
    silhouette(f"Levi_katan_{i:02d}", -10.4, -10 + i * 4, Z_AZ + 1, FL, LEVI, h=2.3)
# Le portique sud est l'entrée des fidèles : « on entre par la droite » depuis les
# portes de 'Houlda (Middot 1:3, 2:2). Deux masses de part et d'autre de l'axe de la
# nef (y = -242.5), l'axe lui-même laissé libre — c'est là que passe CAM_02.
# Trois rangs décalés par côté, et non une file unique : des figures isolées au pas
# régulier le long d'une nef se lisent en rangée de bornes, quand des silhouettes qui
# se recouvrent se lisent en foule (CAM_04). Le rang extérieur reste à 2,25 amot du
# fût des colonnes (y = -250 et -235, rayon 1,5).
for cote in (-1, 1):
    for r, dy in enumerate((2.75, 4.0, 5.25)):
        for i, x in enumerate(plage(-180 + r * 1.0, 256, 3)):
            nom = f"Am_Portique_{cote:+d}_{r}_{i:03d}"
            if alea(nom, 4) < 0.12:
                continue
            figurant(nom, x, -242.5 + cote * dy, Z_HAR, FL, TENUES_AM, desordre=1.2)

# ----------------------------------------------------------------------------
# BISEAU
#   Une arête vive n'existe pas dans la pierre et n'accroche aucune lumière : la
#   passe Normal la rendait plate, et l'i2i redessinait chaque angle à chaque image.
#   Deux segments suffisent — c'est le liseré, pas le congé, qui porte la lumière.
#   Foule, fumée et proxys de sujet en sont exclus : ce ne sont que des repères, et
#   quatre mille modificateurs pour des silhouettes de 40 pixels ne se payent pas.
# ----------------------------------------------------------------------------
BISEAU = {"00_HarHabayit": 0.06, "10_EzratNashim": 0.06, "20_Azara": 0.06,
          "30_Mizbeach": 0.06, "40_Ulam": 0.06, "50_Heikhal": 0.06,
          "60_KodeshHakodashim": 0.06, "80_Lishkot": 0.06,
          "70_Kelim": 0.015, "65_Aron": 0.015}   # tige de la Menora et badim : 0.08 et 0.06 ama de rayon


def biseauter(collection, largeur):
    for o in collection.objects:
        if o.type != 'MESH':
            continue
        biseau = o.modifiers.new("Biseau", 'BEVEL')
        biseau.width = m(largeur)
        biseau.segments = 2
        biseau.limit_method = 'ANGLE'
        biseau.angle_limit = math.radians(30)
        biseau.use_clamp_overlap = True   # sans quoi une paroi de 0.17 ama se retourne


for nom_collection, largeur_biseau in BISEAU.items():
    collection = bpy.data.collections.get(nom_collection)
    if collection:
        biseauter(collection, largeur_biseau)

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
    rampe.elements[0].color = (0.72, 0.73, 0.74, 1.0)     # brume
    rampe.elements[1].position = 1.0
    rampe.elements[1].color = (0.33, 0.45, 0.68, 1.0)     # zénith
    rampe.elements.new(0.35).color = (0.62, 0.68, 0.77, 1.0)
    arbre.links.new(montee.outputs["Result"], degrade.inputs["Factor"])
    arbre.links.new(degrade.outputs["Color"], fond.inputs["Color"])
    # Même niveau d'ambiance que le fond plat d'origine : l'exposition des plans déjà
    # stylisés ne bouge pas.
    fond.inputs["Strength"].default_value = 0.6


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
    """`--cycles` : pour les images clés seulement. Trente-huit frames, pas 8472 — le
    film ne sort pas de Blender, et l'occlusion réelle de l'Oulam ou du Kodesh
    HaKodashim vaut la minute qu'elle coûte."""
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
sun.data.energy = 4.0
sun.data.color = (1.0, 0.85, 0.65)
sun.data.angle = math.radians(1.5)
# Vise depuis l'est, 12° au-dessus de l'horizon (aube). Pour "jour" : passer à 30–35°.
sun.rotation_euler = (math.radians(90 - 12), 0, math.radians(90 + 15))
link_to(sun, "90_Cameras")
ciel()
(moteur_cycles if "--cycles" in sys.argv else moteur_eevee)()
for vt in ('AgX', 'Filmic'):
    try:
        scene.view_settings.view_transform = vt
        break
    except TypeError:
        continue

# ----------------------------------------------------------------------------
# CAMÉRAS — 19 plans, timecodes indicatifs (à recaler sur l'audio réel)
#   (nom, durée s, focale mm, cam_debut, cam_fin, cible_debut, cible_fin)  — positions en amot
# ----------------------------------------------------------------------------
SHOTS = [
    # Le recouvrement entre la frame de début et la frame de fin est mesuré par
    # beit_hamikdash_analyse_plans.py : c'est lui, et non la longueur de la course,
    # qui décide si un i2v à deux frames peut tenir le plan. Sous 40 %, le modèle
    # invente le trajet. Les valeurs ci-dessous sont réglées sur cette mesure.
    #
    # 50 amot de course ne changeaient l'échelle que de 5 % à 1000 amot de distance :
    # invisible sur 12 s. 150 amot donnent 18 %, soit un vrai travelling lent.
    # Le départ est ensuite reculé de 1000 à 1500 amot de la cible, le long de la même
    # ligne de visée (z porté de 120 a 160 : le même angle de plongée, donc les mêmes
    # cours et la même foule par-dessus les murs). La façade passe de 24 % à 16 % de la
    # largeur du cadre au départ — le Temple s'ouvre dans son pays, pas dans son cadre —,
    # l'arrivée ne bouge pas, et la course de 650 amot fait grossir le décor de x1,76
    # sur les 12 s. Le 85 mm reste : c'est la fin du plan, à 850 amot, qu'il cadre.
    # Caméra sur l'axe Heikhal-Nikanor (y = 0), la ligne de mire de la para adouma (Middot 2:4) :
    # 100 amot au sud, l'autel (9 amot au sud de l'axe) se reprojetait sur l'ouverture de l'Oulam et
    # la colonne de fumée semblait sortir de la porte. Sur l'axe, elle tombe au ras du montant sud.
    # 50 mm depuis le mont des Oliviers ne donnait au Heikhal que 14 % de la largeur du
    # cadre : géométriquement exact, mais le Temple s'y perd. 85 mm le porte à 24 % et
    # garde les cours, la foule et la crête. Le plan 15 doit rester identique.
    ("CAM_01_Ouverture_MontOliviers", 12, 85, (1400, 0, 160), (750, 0, 105), (-100, 0, 40), (-100, 0, 40)),
    # Travelling dans la nef de la Stoa royale (colonnades y=-250 et y=-235) :
    # l'axe de l'allée est y=-242.5, tout autre y met une colonne en travers du cadre.
    # Les colonnes sont au pas de 10 depuis x = -202 : ouvrir à -190 collait la caméra
    # à 2 amot d'un fût, qui remplissait le bord du cadre. On ouvre et on ferme à
    # mi-travée.
    # La course était de 280 amot : 134 m en 18 s, soit 7,5 m/s — une colonne toutes
    # les 0,64 s et 1,8 largeur de cadre parcourue, d'où un recouvrement nul. Ramenée
    # à 82 amot, l'allée défile encore franchement et les deux frames se recoupent.
    ("CAM_02_Portique_Sud", 18, 28, (-187, -242.5, Z_HAR + 7), (-105, -242.5, Z_HAR + 7), (-110, -242.5, Z_HAR + 6), (-28, -242.5, Z_HAR + 6)),
    # Intérieur du Beit Avtinas (sol à Z_AZ+26). Le personnage est à 7 puis 5.5 amot :
    # à 28 mm il tient en pied sans dépasser un tiers du cadre.
    # Depuis Sha'ar HaMayim la fenêtre ne donne plus que sur le ciel : le Sanctuaire est
    # 38° hors de l'axe et l'appui masque la cour (README). Elle reste dans le cadre pour
    # ce qu'elle est — une source de lumière derrière le Cohen Gadol —, et le sujet
    # redevient la chambre. La caméra tient l'axe de la pièce : depuis l'angle sud-est
    # elle collait la silhouette à 7 amot d'un 28 mm et la coupait au bord du cadre.
    # Descendue à 2,8 amot du sol, elle a la table (dessus à 2 amot) en pleine hauteur
    # d'image au lieu d'un liseré vu de dessus.
    # 20 mm et non 28 : la chambre fait 8 x 10 amot, le plus grand recul possible est de
    # 9,7 amot, et à 28 mm une silhouette de 3,65 amot y occupe les trois quarts de la
    # hauteur du cadre. Le « petit dans le cadre » du découpage n'est pas atteignable
    # dans une pièce de cette taille : à 20 mm, depuis l'angle sud-est, il en tient la
    # moitié — un plan moyen, avec la table en fuyante et deux murs.
    ("CAM_03_Beit_Avtinas", 25, 20, (-9.5, -82.5, Z_AZ + 28.8), (-10.5, -81, Z_AZ + 28.8), (-12.5, -74.5, Z_AZ + 28.2), (-12.5, -74.5, Z_AZ + 28.2)),
    # La grue partait du sol de l'Ezrat Nashim pour finir 22 amot plus haut en se
    # rapprochant de 30 : le dallage et la foule du premier plan quittaient le cadre
    # entièrement. Montée et approche réduites de moitié.
    # Puis la course a été remontée au-dessus du sol de l'Azara. À Z_EZN + 3 l'objectif
    # était 4,5 amot SOUS le seuil de Nikanor : le seuil masquait la cour entière —
    # `Azara_sol` absent de `--voit 4` aux deux frames, et la baie ne cadrait que la
    # façade de l'Oulam de 8 à 63 amot d'élévation, ce qui se lit en salle et pas en
    # cour. Une occultation ne se corrige pas en visant plus bas : il faut passer le
    # seuil, donc Z_AZ + 2.
    # Le prix est mesuré, pas supposé : la foule de l'Ezrat Nashim a sa tête à Z_EZN +
    # 3,9 = -3,6, donc toute caméra au-dessus du seuil la regarde de haut. `--foule 4`
    # passe de 96 figures à 26, médiane 190 → 172 px. Les deux ne sont pas conciliables
    # à cette focale : garder la foule à hauteur d'homme, c'est rester sous le seuil et
    # perdre la cour. La cible descend de 25 à 8 pour récupérer le premier plan que la
    # montée avait chassé du cadre.
    ("CAM_04_Grue_EzratNashim", 25, 35, (60, 0, Z_AZ + 2), (40, 0, Z_AZ + 10), (-76, 0, 8), (-76, 0, 8)),
    # Le par est entre l'Oulam et le Mizbea'h (Yoma 3:8) : depuis le Doukhan, l'autel de
    # 10 amot le masque entièrement. Seule ligne de vue au sol : depuis le nord, au-dessus
    # des anneaux, en rasant l'angle nord-ouest de l'autel (-54, 7).
    ("CAM_05_Doukhan_Taureau", 25, 40, (-38, 36, Z_AZ + 4), (-44, 33, Z_AZ + 4), (-61.5, 4, Z_AZ + 2.5), (-62.5, 4, Z_AZ + 2.5)),
    # Le plan signature ne montrait pas son sujet. Posée à 6 amot au-dessus du sol de
    # l'Oulam, la caméra avait le Mizbea'h — 32 x 32 x 10, à 24 amot devant elle et à
    # cheval sur l'axe (y -25..7) — exactement en travers : la ligne de visée passait
    # sous son couronnement et toute la cour prosternée était derrière. Il faut 35 amot
    # de hauteur pour raser l'angle nord-est de l'autel et rattraper le sol à Nikanor ;
    # l'ouverture de l'Oulam en fait 40, la caméra y tient.
    # Posée sur l'axe, elle avait ensuite la colonne de fumée — qui monte de l'autel à
    # y -9 — droit au milieu du cadre, coupant en deux la cour prosternée. On se décale
    # au bord nord de l'ouverture : l'autel et sa fumée passent dans le tiers droit du
    # cadre, à leur vraie place au sud, et la cour occupe le reste.
    ("CAM_06_Prosternation", 15, 20, (-78, 9, Z_BAT + 29), (-78, 9, Z_BAT + 29), (30, 6, Z_AZ), (30, 6, Z_AZ)),
    # Plan 7 coupé en deux. D'un seul tenant, la cible passait de (-30, 50) à (-40, -35)
    # alors que la caméra est à y = 39 : la visée traversait l'axe de la caméra et
    # tournait de 142°, un travelling suivi d'un panoramique fouetté. Et la cible était
    # à 11 amot pour 34 amot de course — le décor glissait de trois largeurs de cadre.
    # 7a regarde le champ d'anneaux en fuyante au lieu de le traverser. Posée à
    # 1,5 ama entre les anneaux (y 18..36) et les tables (y 42..44), la caméra les
    # avait tous les deux à trois amot de part et d'autre : le sol du premier plan
    # balayait 0,31 largeur de cadre par seconde, quatre cadres sur la durée du plan.
    # Reculée au nord-est du champ et remontée à 4 amot, elle le prend en entier et en
    # profondeur — piliers, puis tables, puis anneaux — au lieu de l'enjamber.
    # Le poste est aussi contraint par la foule : à x -20..-15 se tiennent les cohanim
    # et à x -10..-2 le peuple. Posée à x -8 elle était à l'intérieur d'une silhouette,
    # objectif dans une tête, et ne voyait plus rien du tout.
    ("CAM_07A_Beit_Mitbachaim", 13, 35, (-24, 62, Z_AZ + 4), (-30, 59, Z_AZ + 4), (-42, 34, Z_AZ + 2), (-42, 34, Z_AZ + 2)),
    # 7b : la rampe ne se filme pas depuis le Beit HaMitba'haïm. Elle est au SUD de
    # l'autel (Middot 3:3), l'autel fait 10 amot de haut et le poste du plan 7a est au
    # nord : la même géométrie qui cache le taureau au plan 5 cache la rampe ici. On
    # coupe, et on la prend depuis le sud, dans son axe, l'autel et la fumée au fond.
    # Prise dans son axe, la rampe n'était qu'un plan incliné gris sans arête : on la
    # regarde du sud-ouest, où elle monte en diagonale vers l'autel et la fumée. Le
    # poste reste à l'ouest de x -22, hors des rangs du peuple et des cohanim.
    # Dans l'axe de la rampe, basse, montant vers le couronnement de l'autel et la
    # fumée. Trois cadrages ont été essayés (sud-ouest, est, trois quarts) : aucun ne
    # détache la rampe, parce que le problème n'est pas le poste mais la matière —
    # rampe chaulée contre autel chaulé sur dallage clair, en lumière ambiante plate,
    # ne donne aucune arête. C'est le cas de la Stoa du plan 2 : le rendu couleur ne
    # porte rien, la carte de profondeur si. Plan à styliser avec `--structure`.
    ("CAM_07B_Rampe", 12, 35, (-38, -62, Z_AZ + 3), (-38, -57, Z_AZ + 3), (-38, -28, Z_AZ + 9), (-38, -28, Z_AZ + 9)),
    # 55 mm sur une cible à 7 amot finissait en aplat de parokhet. On monte les 12 marches
    # et on révèle l'ouverture de 20 x 40, les malterot et la vigne d'or.
    # La caméra divisait sa distance à la cible par 2,2 : à ce taux d'approche les deux
    # frames ne partagent plus qu'un quart d'image. Course ramenée à 9 amot, cible fixe.
    ("CAM_08_Ulam", 20, 28, (-58, 0, Z_AZ + 3), (-74, 0, Z_AZ + 11), (-91, 0, Z_BAT + 20), (-91, 0, Z_BAT + 20)),
    # Le Heikhal fait 40 amot de haut pour 20 de large : à 24 mm aucune position ne cadre
    # la hauteur et les kelim en même temps. Le plan tenait les deux par un relevé de
    # cible de 33 amot, soit 56° de tilt pour 46° de champ vertical : la frame de fin ne
    # montrait plus rien de la frame de début — un aplat de parokhet et de plafond, 7 %
    # de recouvrement. Deux plans, une intention chacune.
    # 9a : l'avancée sur l'axe, cible basse et fixe — porte, Shoul'han, Menora, autel d'or.
    ("CAM_09A_Heikhal_Kelim", 13, 24, (-85, 0, Z_BAT + 5), (-105, 0, Z_BAT + 5), (-138, 0, Z_BAT + 5), (-138, 0, Z_BAT + 5)),
    # 9b : le relevé seul, borné à 12 amot de cible. Le plafond entre quand même dans le
    # cadre — à 33 amot de la parokhet, le haut du champ atteint Z_BAT + 38 — mais les
    # deux frames gardent la moitié basse en commun.
    ("CAM_09B_Heikhal_Parokhet", 12, 24, (-102, 0, Z_BAT + 6), (-107, 0, Z_BAT + 6), (-138, 0, Z_BAT + 6), (-138, 0, Z_BAT + 14)),
    # 10 : dans l'axe du dos, pour que la ma'hta (droite, nord) et le kaf (gauche, sud)
    # passent chacun d'un côté du torse une fois tenus devant lui ; à 3,4 amot les deux
    # ustensiles remplissent les trois quarts de la largeur. Le kohen est à 1,5 ama du
    # mur sud, qui entre ainsi à gauche du cadre. Poussée de 0,7 ama sur 20 s.
    ("CAM_10_Mains_Machta", 20, 40, (-133.4, -8.5, Z_BAT + 2.9), (-134.08, -8.5, Z_BAT + 2.72), (-136.8, -8.55, Z_BAT + 2.0), (-136.8, -8.55, Z_BAT + 2.0)),
    # Aucune figure dans le Kodesh HaKodashim (fiche 8e) : le sujet est l'Arche sur la
    # pierre, la ma'hta à son pied. Caméra entre les deux badim, à la place du Cohen Gadol
    # (Yoma 5:3), basse, quasi fixe ; 28 mm pour tenir les ailes des keruvim (4 amot au-dessus
    # du sol) et la ma'hta au sol à 7,5 amot ; la fumée fera le reste en i2i.
    ("CAM_11_Kodesh_HaKodashim", 25, 28, (-141.5, 0, Z_BAT + 1.8), (-142.5, 0, Z_BAT + 1.6), (-149, 0, Z_BAT + 2.0), (-149, 0, Z_BAT + 2.0)),
    # Le traksin fait 1 ama (48 cm) : aucune caméra n'y tient. On se place dans le Kodesh
    # HaKodashim et on filme le Kohen Gadol franchissant la parokhet intérieure, agrafée
    # au nord. La caméra se déplaçait de 4 amot en travers pour une cible à 6 : la
    # parallaxe emportait tout le cadre. Course latérale ramenée à 1,6 ama, cible fixe.
    ("CAM_12_Entre_Parokhot", 25, 28, (-143, 1, Z_BAT + 4), (-142.5, -0.5, Z_BAT + 4), (-139.8, 7.5, Z_BAT + 2.5), (-139.8, 7.5, Z_BAT + 2.5)),
    # Plan 13 coupé au seuil. Le recul allait de x -120 à -80 : la caméra traversait le
    # mur est du Heikhal (-98..-92) et changeait de pièce en cours de plan. Une seule
    # paire de frames ne décrit pas une traversée de porte ; la coupe se fait dans
    # l'embrasure, là où le montage la voudrait de toute façon.
    ("CAM_13A_Retour_Heikhal", 15, 40, (-120, 0, Z_BAT + 5), (-101, 0, Z_BAT + 5), (0, 0, Z_AZ + 20), (0, 0, Z_AZ + 20)),
    ("CAM_13B_Retour_Oulam", 15, 40, (-98, 0, Z_BAT + 5), (-80, 0, Z_BAT + 5), (0, 0, Z_AZ + 20), (0, 0, Z_AZ + 20)),
    # Plan 14 coupé en deux : la grue montait de 54 amot en reculant de 44 pendant que la
    # cible balayait 70 amot vers l'est — trois révélations (l'Azara, l'Ezrat Nashim, la
    # ville) dans un seul plan, et rien de commun entre ses deux bouts.
    # 14a découvre l'Azara depuis le seuil de l'Oulam, cible fixe sur la cour.
    # Départ relevé pour la même raison qu'au plan 6 : à 2 amot au-dessus du sol de
    # l'Oulam la grue commençait derrière l'autel et ne découvrait rien.
    ("CAM_14A_Grue_Azara", 15, 28, (-74, 0, Z_BAT + 14), (-60, 0, Z_AZ + 30), (40, 0, Z_AZ + 5), (40, 0, Z_AZ + 5)),
    # 14b poursuit la montée. L'amplitude est bornée par ce qu'un mur cache : montant
    # de 32 amot en balayant la cible de 50 vers l'est, la caméra passait au-dessus du
    # mur du Har HaBayit et découvrait un sol que rien n'annonçait dans la frame de
    # début — 3 % de couverture, tout à inventer. Une grue ne se décrit à deux frames
    # que tant qu'elle ne franchit pas une ligne d'horizon.
    ("CAM_14B_Grue_Ville", 15, 28, (-60, 0, Z_AZ + 30), (-46, 0, Z_AZ + 46), (40, 0, Z_AZ + 5), (55, 0, Z_AZ + 3)),
    # Même axe que CAM_01 (boucle visuelle ouverture/fermeture).
    ("CAM_15_Fermeture", 33, 85, (850, 0, 110), (850, 0, 110), (-100, 0, 40), (-100, 0, 40)),
]

frame = 1
scene.frame_start = 1
for (name, dur, focal, c0, c1, t0, t1) in SHOTS:
    n = int(round(dur * FPS))
    f0, f1 = frame, frame + n - 1
    tgt = empty(name + "_cible", *t0)
    cam = camera(name, tuple(m(c) for c in c0))
    cam.data.lens = focal
    cam.data.clip_end = 5000
    cam.data.sensor_width = 36
    link_to(cam, "90_Cameras")
    con = cam.constraints.new('TRACK_TO')
    con.target = tgt
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'
    # Keyframes de position (interpolation linéaire = mouvement constant)
    for obj, p0, p1 in ((cam, c0, c1), (tgt, t0, t1)):
        obj.location = tuple(m(c) for c in p0); obj.keyframe_insert("location", frame=f0)
        obj.location = tuple(m(c) for c in p1); obj.keyframe_insert("location", frame=f1)
        for fc in fcurves_of(obj):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    mk = scene.timeline_markers.new(name, frame=f0)
    mk.camera = cam
    cam["duree_s"] = dur
    cam["frame_debut"] = f0
    cam["frame_fin"] = f1
    frame = f1 + 1

scene.frame_end = frame - 1
scene.camera = bpy.data.objects["CAM_01_Ouverture_MontOliviers"]
scene.frame_set(1)

# Passes utiles pour le conditionnement IA (profondeur, normales)
vl = scene.view_layers[0]
vl.use_pass_z = True
vl.use_pass_normal = True
vl.use_pass_mist = True

print(f"Blockout terminé : {len(bpy.data.objects)} objets, {len(SHOTS)} caméras, "
      f"{scene.frame_end} images à {FPS} fps ({scene.frame_end / FPS:.0f} s).")
print("Sélectionner une caméra dans la timeline via les marqueurs ; Ctrl+Numpad0 pour la rendre active.")
