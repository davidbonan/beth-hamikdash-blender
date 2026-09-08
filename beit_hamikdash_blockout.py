"""
BEIT HAMIKDASH — BLOCKOUT GÉNÉRATIF (Second Temple, selon Mishna Middot)
=========================================================================
Usage : Blender 3.x / 4.x → onglet Scripting → New → coller → Run Script (Alt+P),
ou en headless, chaîné avec les scripts qui l'exploitent (voir README).

Le script crée une scène complète en volumes gris, à l'échelle : le bâtiment, ses
ustensiles, le pays autour et la foule du jour. Il ne pose aucune caméra — elles
sont déclarées dans cameras.json et bâties par beit_hamikdash_cameras.py.

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
# Foule de Yom Kippour : False = architecture seule. Retire toute la collection
# 76_Foule — peuple de l'Ezrat Israël, cohanim de l'Ezrat Kohanim, Léviim et leurs
# instruments sur le Doukhan, masses de l'Ezrat Nashim, du Har HaBayit et du portique.
FOULE = False
# Les mâts d'or de Simhat Beit HaShoeva (Soucca 5:2) : dressés dans l'Ezrat Nashim le
# jour de Kippour aussi (CHOIX — la Mishna les dit « là », sans dire qu'on les démonte).
CANDELABRES_SHOEVA = True
NETTOYER_SCENE = True

# Niveaux (en amot)
Z_HAR = -16.0   # Har HaBayit : 12 marches du 'Heil (6) + 15 marches (7,5) + Ezrat Israël (2,5) sous l'Azara
Z_ROCHE = -240  # pied des murs de soutènement de l'esplanade, sous le fond du Kidron
Z_EZN = -10.0   # Ezrat Nashim : 15 marches sous l'Ezrat Israël (Middot 2:5), elle-même 2,5 sous l'Ezrat Kohanim (2:6)
Z_EZI = -2.5    # Ezrat Israël : « מַעֲלָה גְבוֹהָה אַמָּה וְהַדּוּכָן נָתוּן עָלֶיהָ וּבוֹ שָׁלֹשׁ מַעֲלוֹת » (Middot 2:6)
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

def bois_sculpte(name, rgb):
    """Chêne des maltera'ot : « קוֹרוֹת מְצֻיָּרוֹת וּמְכֻיָּרוֹת » (Bartenura sur Middot 3:7),
    sculptées, pas nues. Le fil du bois, plus un relief de rinceaux en travers du fil
    — c'est ce relief qui entre dans la passe Normal et que le styliseur cisèle."""
    mat = bois(name, rgb)
    if name in _MATIERES_CABLEES and mat.node_tree.nodes.get("Rinceaux"):
        return mat
    liens = mat.node_tree.links
    rinceaux = _noeud(mat, "ShaderNodeTexWave", -900, -300)
    rinceaux.name = "Rinceaux"
    rinceaux.wave_type = 'RINGS'
    rinceaux.rings_direction = 'X'
    rinceaux.wave_profile = 'SAW'
    rinceaux.inputs["Scale"].default_value = 1.0 / m(0.6)
    rinceaux.inputs["Distortion"].default_value = 4.0
    rinceaux.inputs["Detail"].default_value = 2.0
    liens.new(_position(mat), rinceaux.inputs["Vector"])
    _creuser(mat, rinceaux.outputs["Factor"], 0.9, 0.05)
    return mat

# Les quatre matières de la parokhet (Shekalim 8:5 ; Rashi Ex. 26:31) : tekhelet,
# argaman, tola'at shani, lin — à parts égales, et aucun fil d'or (Ex. 26:31).
MATIERES_PAROKHET = ((0.10, 0.17, 0.48), (0.40, 0.08, 0.30), (0.55, 0.08, 0.08), (0.86, 0.84, 0.78))
CHAMP_PAROKHET = 5.0      # hauteur d'un champ de couleur, en amot : 40 amot font 8 champs, 2 par matière

def parokhet(name):
    """Étoffe lourde et plate en champs larges des quatre matières, à parts égales.

    Un bleu uni se stylisait en rideau de velours à plis : la fiche (§8d) veut les
    quatre couleurs « en champs larges, lin blanc compris », sans un fil d'or. Les
    champs sont lus en Z du monde, donc les deux parokhot portent le même tissage.
    Le relief du tissage — deux trames croisées — et une lisière sombre entre les
    champs donnent à la passe Normal une surface de laine et non un aplat.
    """
    mat, neuf = _neuf(name, MATIERES_PAROKHET[0])
    if not neuf:
        return mat
    liens = mat.node_tree.links
    bsdf = _bsdf(mat)
    bsdf.inputs["Roughness"].default_value = 0.92
    bsdf.inputs["Sheen Weight"].default_value = 0.4
    bsdf.inputs["Sheen Roughness"].default_value = 0.5
    axe = _noeud(mat, "ShaderNodeSeparateXYZ", -1500, 0)
    liens.new(_position(mat), axe.inputs["Vector"])
    rang = _noeud(mat, "ShaderNodeMath", -1340, 0)
    rang.operation = "DIVIDE"
    rang.inputs[1].default_value = m(CHAMP_PAROKHET)
    liens.new(axe.outputs["Z"], rang.inputs[0])
    numero = _noeud(mat, "ShaderNodeMath", -1180, 120)
    numero.operation = "FLOOR"
    liens.new(rang.outputs[0], numero.inputs[0])
    matiere = _noeud(mat, "ShaderNodeMath", -1020, 120)
    matiere.operation = "MODULO"
    matiere.inputs[1].default_value = 4.0
    liens.new(numero.outputs[0], matiere.inputs[0])
    part = _noeud(mat, "ShaderNodeMath", -860, 120)
    part.operation = "DIVIDE"
    part.inputs[1].default_value = 4.0
    liens.new(matiere.outputs[0], part.inputs[0])
    choix = _noeud(mat, "ShaderNodeValToRGB", -680, 160)
    rampe = choix.color_ramp
    rampe.interpolation = 'CONSTANT'
    rampe.elements[0].position = 0.0
    rampe.elements[0].color = (*MATIERES_PAROKHET[0], 1.0)
    rampe.elements[1].position = 0.25
    rampe.elements[1].color = (*MATIERES_PAROKHET[1], 1.0)
    rampe.elements.new(0.5).color = (*MATIERES_PAROKHET[2], 1.0)
    rampe.elements.new(0.75).color = (*MATIERES_PAROKHET[3], 1.0)
    liens.new(part.outputs[0], choix.inputs["Factor"])
    # Lisière : un liseré plus sombre au bord de chaque champ, là où la frise change.
    lisiere = _noeud(mat, "ShaderNodeMath", -1180, -140)
    lisiere.operation = "FRACT"
    liens.new(rang.outputs[0], lisiere.inputs[0])
    bord = _noeud(mat, "ShaderNodeValToRGB", -1020, -140)
    bord.color_ramp.elements[0].position = 0.0
    bord.color_ramp.elements[0].color = (0.55, 0.55, 0.55, 1.0)
    bord.color_ramp.elements[1].position = 0.06
    liens.new(lisiere.outputs[0], bord.inputs["Factor"])
    teinte = _noeud(mat, "ShaderNodeMixRGB", -500, 160)
    teinte.blend_type = 'MULTIPLY'
    teinte.inputs["Factor"].default_value = 1.0
    liens.new(choix.outputs["Color"], teinte.inputs["Color1"])
    liens.new(bord.outputs["Color"], teinte.inputs["Color2"])
    liens.new(teinte.outputs["Color"], bsdf.inputs["Base Color"])
    _creuser(mat, bord.outputs["Color"], 0.6, 0.02)
    for sens, k in (('Y', 0), ('Z', 1)):
        trame = _noeud(mat, "ShaderNodeTexWave", -900, -500 - 220 * k)
        trame.bands_direction = sens
        trame.inputs["Scale"].default_value = 1.0 / m(0.04)
        trame.inputs["Distortion"].default_value = 0.5
        trame.inputs["Detail"].default_value = 1.0
        liens.new(_position(mat), trame.inputs["Vector"])
        _creuser(mat, trame.outputs["Factor"], 0.35, 0.004)
    return mat

BRUME = (0.72, 0.73, 0.74)           # la couleur du fond de ciel à l'horizon (voir `ciel`)
VOILE_DEBUT, VOILE_FIN = 1500, 5500  # amot depuis l'origine : d'où le pays se fond dans la brume

def _voiler(mat):
    """Perspective atmosphérique dans la matière : passé VOILE_DEBUT amot de l'origine,
    la couleur se fond vers la brume du ciel. Eevee n'a pas de brouillard sans volume,
    et un volume sur un pays de six mille amot de côté se paye à chaque frame ; une
    colline à cinq mille amot rendue au même contraste qu'un mur à cent se lisait
    collée dessus (plan 1). Le voile ne touche que le pays."""
    if mat.node_tree.nodes.get("Voile"):
        return mat
    liens = mat.node_tree.links
    bsdf = _bsdf(mat)
    distance = _noeud(mat, "ShaderNodeVectorMath", -1300, 600)
    distance.operation = 'LENGTH'
    liens.new(_position(mat), distance.inputs[0])
    part = _noeud(mat, "ShaderNodeMapRange", -1100, 600)
    part.clamp = True
    part.inputs["From Min"].default_value = m(VOILE_DEBUT)
    part.inputs["From Max"].default_value = m(VOILE_FIN)
    part.inputs["To Max"].default_value = 0.85
    liens.new(distance.outputs["Value"], part.inputs["Value"])
    voile = _noeud(mat, "ShaderNodeMixRGB", -300, 600)
    voile.name = "Voile"
    voile.inputs["Color2"].default_value = (*BRUME, 1.0)
    entree = bsdf.inputs["Base Color"]
    if entree.links:
        liens.new(entree.links[0].from_socket, voile.inputs["Color1"])
    else:
        voile.inputs["Color1"].default_value = entree.default_value
    liens.new(part.outputs["Result"], voile.inputs["Factor"])
    liens.new(voile.outputs["Color"], entree)
    return mat

def terre(name):
    """Collines de Jérusalem : calcaire affleurant et garrigue, en terrasses.

    Les terrasses ne sont pas bâties : un relief en dents de scie lu en Z du monde
    (pas de 4 amot) marque les murets de soutènement sur toute pente — c'est ce que
    les prompts des plans 1 et 14b appellent « olive terraces ».
    """
    mat, neuf = _neuf(name, (0.52, 0.45, 0.33))
    if not neuf:
        return mat
    liens = mat.node_tree.links
    _bsdf(mat).inputs["Roughness"].default_value = 0.95
    melange = _noeud(mat, "ShaderNodeMixRGB", -700, 0)
    melange.inputs["Color1"].default_value = (0.46, 0.39, 0.27, 1.0)   # roche et terre nues
    melange.inputs["Color2"].default_value = (0.26, 0.29, 0.16, 1.0)   # garrigue
    liens.new(_grain(mat, 45.0), melange.inputs["Factor"])
    liens.new(melange.outputs["Color"], _bsdf(mat).inputs["Base Color"])
    _voiler(mat)
    axe = _noeud(mat, "ShaderNodeSeparateXYZ", -1500, -600)
    liens.new(_position(mat), axe.inputs["Vector"])
    terrasse = _noeud(mat, "ShaderNodeMath", -1340, -600)
    terrasse.operation = "DIVIDE"
    terrasse.inputs[1].default_value = m(4.0)
    liens.new(axe.outputs["Z"], terrasse.inputs[0])
    dents = _noeud(mat, "ShaderNodeMath", -1180, -600)
    dents.operation = "FRACT"
    liens.new(terrasse.outputs[0], dents.inputs[0])
    _creuser(mat, dents.outputs[0], 0.7, 0.5)
    _creuser(mat, _grain(mat, 10.0), 1.0, 0.8)
    _creuser(mat, _grain(mat, 1.5), 0.5, 0.12)
    return mat

def eau(name):
    """Eau du Kiyor : sombre, lisse, elle ne renvoie que le ciel et le bronze."""
    mat, neuf = _neuf(name, (0.05, 0.08, 0.09))
    if neuf:
        bsdf = _bsdf(mat)
        bsdf.inputs["Roughness"].default_value = 0.04
        bsdf.inputs["Specular IOR Level"].default_value = 0.6
        _creuser(mat, _grain(mat, 0.25), 0.15, 0.003)
    return mat

MAT_PIERRE = lambda: pierre("Pierre_claire", (0.85, 0.82, 0.74))
MAT_OR = lambda: metal("Or", (1.0, 0.76, 0.33), 0.3)
MAT_BRONZE = lambda: metal("Bronze", (0.66, 0.44, 0.22), 0.45)
MAT_CHAUX = lambda: enduit("Chaux_blanche", (0.95, 0.95, 0.92))
MAT_CHAUX_FEU = lambda: enduit_noirci("Chaux_noircie", (0.95, 0.95, 0.92), (Z_AZ + 7.5, Z_AZ + 10.5))
MAT_SOL = lambda: dallage("Sol", (0.75, 0.72, 0.65))
MAT_LIN = lambda: etoffe("Lin_blanc", (0.88, 0.87, 0.83))     # bigdei lavan des kohanim
MAT_MARBRE = lambda: marbre("Marbre_blanc", (0.93, 0.92, 0.89))
MAT_MARBRE_HERODE = lambda: marbre_herode("Marbre_Herode")
# L'or des parois est un placage martelé sur de la pierre, pas un ustensile tourné :
# plus mat que la Menora, sinon un mur entier ne rend qu'un point spéculaire.
MAT_OR_PLAQUE = lambda: metal("Or_plaque", (1.0, 0.76, 0.33), 0.4)
MAT_CEDRE = lambda: bois("Cedre", (0.44, 0.25, 0.14))
MAT_CHENE = lambda: bois("Chene", (0.36, 0.25, 0.15))
MAT_CHENE_SCULPTE = lambda: bois_sculpte("Chene_sculpte", (0.36, 0.25, 0.15))
MAT_PAROKHET = lambda: parokhet("Parokhet_tissee")
MAT_TERRE = lambda: terre("Terre_Jerusalem")
MAT_MAISON = lambda: _voiler(pierre("Maisons", (0.66, 0.59, 0.46)))   # la ville, deux tons sous le Temple
MAT_FEUILLAGE = lambda: _voiler(material("Olivier_feuillage", (0.24, 0.30, 0.17)))
MAT_TRONC = lambda: _voiler(material("Olivier_tronc", (0.30, 0.24, 0.17)))
MAT_EAU = lambda: eau("Eau_Kiyor")
MAT_FER = lambda: metal("Fer", (0.30, 0.29, 0.28), 0.6)            # crochets des ninnasin (Middot 3:5)
MAT_SIKRA = lambda: material("Sikra", (0.55, 0.10, 0.06))          # le 'hout hasikra (Middot 3:1)

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



def creneaux(name, x0, x1, y0, y1, z, col, mat=None, pas=4.0, large=2.0, haut=2.0):
    """Merlons sur la crête d'un mur, le long de son grand côté.

    Aucune source halakhique : c'est l'appareil hérodien que les stylisations des
    plans 1 et 14b dessinent d'elles-mêmes (« crenellated outer wall »), et que le
    blockout doit donc porter pour qu'il ne change pas d'une image à l'autre. CHOIX.
    """
    long_x = (x1 - x0) >= (y1 - y0)
    a0, a1 = (x0, x1) if long_x else (y0, y1)
    for k, c in enumerate(plage(a0 + pas / 2, a1 - pas / 2, pas)):
        if long_x:
            box(f"{name}_{k:03d}", c - large / 2, c + large / 2, y0, y1, z, z + haut, col, mat)
        else:
            box(f"{name}_{k:03d}", x0, x1, c - large / 2, c + large / 2, z, z + haut, col, mat)


def couronnement(name, x0, x1, y0, y1, z, col, mat=None, saillie=0.5, reserve=()):
    """Assise de couronnement d'un mur : une ama qui déborde de `saillie` sur les deux
    faces, à cheval sur la crête. Un mur qui s'arrête net se lit en boîte ; l'assise
    qui déborde donne la ligne d'ombre qui fait le mur. `reserve` : intervalles du
    grand côté que le couronnement saute — les corps de porte qui passent la crête."""
    long_x = (x1 - x0) >= (y1 - y0)
    a0, a1 = (x0, x1) if long_x else (y0, y1)
    for j, (u0, u1) in enumerate(_hors_reserve(a0, a1, z - 0.5, z + 0.5,
                                               [(r0, r1, z - 1, z + 1) for r0, r1 in reserve])):
        if long_x:
            box(f"{name}_{j}", u0, u1, y0 - saillie, y1 + saillie, z - 0.5, z + 0.5, col, mat)
        else:
            box(f"{name}_{j}", x0 - saillie, x1 + saillie, u0, u1, z - 0.5, z + 0.5, col, mat)


def battants(name, x0, x1, y0, y1, z0, h, col, mat, largeur=10):
    """Deux vantaux rabattus dans l'embrasure d'une porte percée dans un mur — ouverts,
    comme ceux de Nikanor et du Heikhal. `x0..x1, y0..y1` : l'emprise de la baie dans
    l'épaisseur du mur ; le vantail court le long du jambage, sur les trois quarts
    de l'épaisseur, épais de 0,3 ama."""
    large_en_x = (x1 - x0) >= (y1 - y0)   # baie d'un mur nord-sud : les jambages sont en x
    if large_en_x:
        u0, u1 = y0 + (y1 - y0) * 0.15, y1 - (y1 - y0) * 0.15
        box(f"{name}_O", x0, x0 + 0.3, u0, u1, z0, z0 + h, col, mat)
        box(f"{name}_E", x1 - 0.3, x1, u0, u1, z0, z0 + h, col, mat)
    else:
        u0, u1 = x0 + (x1 - x0) * 0.15, x1 - (x1 - x0) * 0.15
        box(f"{name}_S", u0, u1, y0, y0 + 0.3, z0, z0 + h, col, mat)
        box(f"{name}_N", u0, u1, y1 - 0.3, y1, z0, z0 + h, col, mat)


def crochet(name, x, y, z, sens, col):
    """Crochet de fer des ninnasin : une tige horizontale qui sort du bloc de cèdre,
    relevée au bout. `sens` : ±1, le côté en x où il sort."""
    fer = MAT_FER()
    cyl_between(f"{name}_tige", (x, y, z), (x + sens * 0.30, y, z), 0.035, col, fer, verts=6)
    cyl_between(f"{name}_pointe", (x + sens * 0.30, y, z - 0.02), (x + sens * 0.30, y, z + 0.14),
                0.035, col, fer, verts=6)


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
# « שַׁעַר הַמִּזְרָחִי, עָלָיו שׁוּשַׁן הַבִּירָה צוּרָה » (Middot 1:3) : le dessin de Suse au-dessus
# de la porte est, tourné vers le mont des Oliviers. Un bas-relief : rempart et trois
# tours crénelées, dans la pierre du mur.
SHUSHAN_Z = Z_HAR + 20.4
box("Shushan_plaque", HX1, HX1 + 0.15, -4.5, 4.5, SHUSHAN_Z, SHUSHAN_Z + 3.2, "00_HarHabayit")
box("Shushan_rempart", HX1 + 0.15, HX1 + 0.35, -3.8, 3.8, SHUSHAN_Z + 0.3, SHUSHAN_Z + 1.3, "00_HarHabayit")
for k, y in enumerate((-3.0, 0.0, 3.0)):
    h = 2.6 if y == 0 else 2.0
    box(f"Shushan_tour_{k}", HX1 + 0.15, HX1 + 0.4, y - 0.6, y + 0.6, SHUSHAN_Z + 0.3, SHUSHAN_Z + h, "00_HarHabayit")
    for j, yc in enumerate((y - 0.45, y, y + 0.45)):
        box(f"Shushan_tour_{k}_merlon_{j}", HX1 + 0.15, HX1 + 0.4, yc - 0.12, yc + 0.12,
            SHUSHAN_Z + h, SHUSHAN_Z + h + 0.25, "00_HarHabayit")
# Crête des murs : merlons (CHOIX, appareil hérodien — les stylisations des plans 1 et
# 14b crénelaient d'elles-mêmes cette enceinte, autant que le blockout le fixe).
for nm, xa, xb, ya, yb, h in (("sud", HX0, HX1, HY0, HY0 + 3, H_HAR),
                              ("nord", HX0, HX1, HY1 - 3, HY1, H_HAR),
                              ("ouest", HX0, HX0 + 3, HY0 + 3, HY1 - 3, H_HAR),
                              ("est", HX1 - 3, HX1, HY0 + 3, HY1 - 3, H_HAR_EST)):
    creneaux(f"HarHabayit_creneaux_{nm}", xa, xb, ya, yb, Z_HAR + h, "00_HarHabayit")
# Murs de soutènement : l'esplanade est une terrasse bâtie au-dessus du Kidron et du
# Tyropéon, ses murs descendent jusqu'au rocher. Sans lui, le pays passait sous le
# dallage et l'esplanade flottait au-dessus de ses propres vallées.
box("HarHabayit_soubassement", HX0, HX1, HY0, HY1, Z_ROCHE, Z_HAR - 1, "00_HarHabayit")
pas = 10
# Le portique est est le seul bas, comme son mur (Middot 2:4) : colonnes et toit
# tiennent sous la crête de 24 amot.
H_PORTIQUE, H_PORTIQUE_EST = 25, 21
for i, x in enumerate(range(HX0 + 15, HX1 - 10, pas)):
    colonne(f"Portique_sud_{i:03d}", x, HY0 + 15, Z_HAR, Z_HAR + H_PORTIQUE, 1.5)
    colonne(f"Portique_nord_{i:03d}", x, HY1 - 15, Z_HAR, Z_HAR + H_PORTIQUE, 1.5)
for i, y in enumerate(range(HY0 + 25, HY1 - 20, pas)):
    colonne(f"Portique_ouest_{i:03d}", HX0 + 15, y, Z_HAR, Z_HAR + H_PORTIQUE, 1.5)
    if abs(y) > 6:      # dégager la ligne de mire de la para (Middot 2:4)
        colonne(f"Portique_est_{i:03d}", HX1 - 15, y, Z_HAR, Z_HAR + H_PORTIQUE_EST, 1.5)
# Stoa royale au sud : seconde rangée de colonnes
for i, x in enumerate(range(HX0 + 15, HX1 - 10, pas)):
    colonne(f"Stoa_sud_{i:03d}", x, HY0 + 30, Z_HAR, Z_HAR + H_PORTIQUE, 1.5)
# Les portiques sont couverts (Josèphe, Guerre V, 5, 2 : plafonds de cèdre sur les
# colonnades) : du mur à la rangée de colonnes, chapiteau compris. À ciel ouvert,
# les colonnes se lisaient d'en haut en rangées de bornes sur le dallage.
DEBORD_CHAPITEAU = 1.5 * 1.45 + 0.7
for nm, xa, xb, ya, yb, zt in (
        ("nord", HX0 + 3, HX1 - 3, HY1 - 15 - DEBORD_CHAPITEAU, HY1 - 3, Z_HAR + H_PORTIQUE),
        ("ouest", HX0 + 3, HX0 + 15 + DEBORD_CHAPITEAU, HY0 + 32, HY1 - 15 - DEBORD_CHAPITEAU, Z_HAR + H_PORTIQUE),
        ("est", HX1 - 15 - DEBORD_CHAPITEAU, HX1 - 3, HY0 + 32, HY1 - 15 - DEBORD_CHAPITEAU, Z_HAR + H_PORTIQUE_EST),
        ("stoa_bas_cote", HX0 + 3, HX1 - 3, HY0 + 3, HY0 + 13, Z_HAR + H_PORTIQUE)):
    box(f"Portique_{nm}_plafond", xa, xb, ya, yb, zt, zt + 1.4, "00_HarHabayit", MAT_CEDRE())
    box(f"Portique_{nm}_toit", xa, xb, ya, yb, zt + 1.4, zt + 2, "00_HarHabayit")
# Le dessus du plafond de la Stoa est de la pierre aussi : vu d'en haut (plans 1, 1b,
# 15), un toit de cèdre faisait une bande brune de cinq cents amot.
box("Stoa_sud_toit", HX0, HX1, HY0 + 13, HY0 + 32, Z_HAR + 27, Z_HAR + 27.6, "00_HarHabayit")
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

# 'Heil : 12 marches de 0.5 × 0.5 (Middot 2:3) côté est, l'accès principal (les trois
# autres côtés se bâtissent avec le soreg, plus bas, où leur cote est connue). Elles
# montent du dallage au niveau de l'Ezrat Nashim et s'arrêtent contre la face est de
# son mur (x 145) : posées 5 amot plus à l'ouest, elles étaient enfouies dans le
# podium. Le soreg qui borde le 'Heil se construit avec les lishkot, plus bas : sa
# ligne se mesure depuis les corps de porte, qui débordent des murs.
for i in range(12):
    box(f"Heil_marche_{i:02d}", 150.5 - i * 0.5, 151 - i * 0.5, -67.5, 67.5,
        Z_HAR, Z_HAR + 0.5 * (i + 1), "00_HarHabayit")

# ----------------------------------------------------------------------------
# 01 — LE PAYS : collines de Jérusalem, la ville, les oliviers
#   Rien n'était modélisé au-delà du Har HaBayit : le Temple se lisait posé sur une
#   mer (README, ciel physique écarté pour cela), et au plan 14b la grue découvrait
#   par-dessus le mur un vide que le styliseur remplissait à sa guise — collines,
#   maisons et terrasses différentes d'une image à l'autre. Les prompts des plans 1
#   et 14b les nomment (« mist in the Kidron valley, olive terraces and low
#   flat-roofed houses on the hills ») : ils ont maintenant une géométrie.
#   Le relief est un CHOIX lissé sur les cotes réelles, en amot depuis l'esplanade
#   (740 m) : Kidron 650, mont des Oliviers 810, Tyropéon 700, ville haute 770,
#   collines de l'ouest 800 et plus. Aucune source halakhique ici.
# ----------------------------------------------------------------------------
PAYS = "01_Pays"


def _profil(u, points):
    """Interpolation en cosinus entre (abscisse, cote) triées : des collines, pas des toits."""
    if u <= points[0][0]:
        return points[0][1]
    for (u0, z0), (u1, z1) in zip(points, points[1:]):
        if u <= u1:
            t = (u - u0) / (u1 - u0)
            return z0 + (z1 - z0) * (1 - math.cos(math.pi * t)) / 2
    return points[-1][1]


# Vers l'ouest la crête est tenue sous la ligne de toit du plan 1 (à 850 amot, le
# faîte à 100 est vu 0,35° sous l'horizontale ; une colline à 3000 amot doit rester
# sous 60 pour passer dessous) : le Sanctuaire garde sa silhouette sur le ciel.
RELIEF_EO = [(-6000, 60), (-3000, 60), (-1300, 49), (-517, -97), (HX0, -45),
             (HX1, -60), (733, -200), (2383, 132), (4000, 60), (6000, 30)]
RELIEF_NS = [(-6000, -60), (-2000, -130), (HY0 - 800, -80), (HY0, 0), (HY1, 0),
             (HY1 + 600, 35), (2000, 55), (6000, 80)]


def hors_esplanade(x, y):
    """Distance au rectangle du Har HaBayit (négative dedans)."""
    return max(HX0 - x, x - HX1, HY0 - y, y - HY1)


def altitude(x, y):
    """Cote du sol naturel en (x, y), en amot. Sous l'esplanade, enfoui dans la roche ;
    à moins de 80 amot de ses murs, tenu sous le dallage pour que le pays ne remonte
    jamais par-dessus la crête de soutènement."""
    marge = hors_esplanade(x, y)
    if marge < 2:
        return Z_HAR - 8
    z = (_profil(x, RELIEF_EO) + _profil(y, RELIEF_NS)
         + 5 * math.sin(x / 90) * math.sin(y / 110)
         + 3 * math.sin(x / 37 + 1.3) * math.cos(y / 29 + 0.4)
         + 1.5 * math.sin((x + y) / 13))
    if marge < 80:
        z = min(z, Z_HAR - 4 - (80 - marge) * 0.1)
    return z


def relief(name, x0, x1, y0, y1, pas, col, mat):
    """Nappe du sol naturel, une face par case de `pas` amot."""
    xs, ys = plage(x0, x1, pas), plage(y0, y1, pas)
    n = len(xs)
    verts = [(x, y, altitude(x, y)) for y in ys for x in xs]
    faces = [[j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i]
             for j in range(len(ys) - 1) for i in range(n - 1)]
    return mesh_from_pydata(name, verts, faces, col, mat)


def maison(nom, x, y, col):
    """Maison à toit plat, enfoncée dans la pente ; un étage en retrait une fois sur trois."""
    z = altitude(x, y)
    l, p = 5 + 8 * alea(nom, 1), 5 + 8 * alea(nom, 2)
    h = 4 + 4 * alea(nom, 3)
    box(nom, x - l / 2, x + l / 2, y - p / 2, y + p / 2, z - 2.5, z + h, col, MAT_MAISON())
    if alea(nom, 4) < 0.35:
        box(f"{nom}_etage", x - l / 2 + 1, x + l / 2 - 2, y - p / 2 + 1, y + p / 2 - 1,
            z + h, z + h + 3, col, MAT_MAISON())


def olivier(nom, x, y, col):
    z = altitude(x, y)
    r = 1.6 + 1.4 * alea(nom, 1)
    cyl(f"{nom}_tronc", x, y, z - 0.5, z + 1.6, 0.25, col, MAT_TRONC(), verts=6)
    sphere(f"{nom}_houppier", x, y, z + 1.6 + r * 0.8, r, col, MAT_FEUILLAGE(), segs=8)


def _densite_ville(x, y):
    """Où la ville est : dense à l'ouest (ville haute) et au sud (cité de David),
    clairsemée sur le mont des Oliviers — villages et tombeaux."""
    if x > HX1 + 200:
        return 0.22
    if x < HX0 - 30 or y < HY0 - 30:
        return 0.85
    return 0.5


relief("Pays_relief", -6000, 6000, -6000, 6000, 50, PAYS, MAT_TERRE())
for i in range(2600):
    nom = f"Maison_{i:04d}"
    x, y = -3800 + 7300 * alea(nom, 5), -3800 + 7300 * alea(nom, 6)
    if hors_esplanade(x, y) < 70 or altitude(x, y) < -175:   # le fond des vallées : jardins
        continue
    if alea(nom, 0) < _densite_ville(x, y):
        maison(nom, x, y, PAYS)
# Le mont des Oliviers d'abord, puis quelques bosquets sur les autres pentes.
for i in range(1300):
    nom = f"Olivier_{i:04d}"
    x, y = HX1 + 120 + 3000 * alea(nom, 5), -2400 + 4800 * alea(nom, 6)
    if hors_esplanade(x, y) < 60 or altitude(x, y) < -185 or alea(nom, 0) > 0.7:
        continue
    olivier(nom, x, y, PAYS)
for i in range(400):
    nom = f"Olivier_ouest_{i:04d}"
    x, y = -3500 + 3200 * alea(nom, 5), -3000 + 6000 * alea(nom, 6)
    if hors_esplanade(x, y) < 60 or altitude(x, y) < -175 or alea(nom, 0) > 0.3:
        continue
    olivier(nom, x, y, PAYS)

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
# Gezuztra : galerie des femmes le long des murs nord et sud (Middot 2:5 ; Soukka 51b),
# entre les chambres d'angle — elle traversait leurs murs. Une dalle nue en l'air ne
# se lisait pas : elle porte maintenant sur des colonnes et un garde-corps.
for nm, ya, yb, devant in (("nord", 64, 67.5, 64), ("sud", -67.5, -64, -64)):
    box(f"Gezuztra_{nm}", EX0 + 40, EX1 - 40, ya, yb, Z_EZN + 10, Z_EZN + 11, "10_EzratNashim")
    sens = 1 if devant > 0 else -1
    box(f"Gezuztra_{nm}_garde", EX0 + 40, EX1 - 40, devant, devant + sens * 0.5,
        Z_EZN + 11, Z_EZN + 13, "10_EzratNashim")
    for i, x in enumerate(plage(EX0 + 44, EX1 - 44, 7)):
        colonne(f"Gezuztra_{nm}_colonne_{i:02d}", x, devant + sens * 0.9, Z_EZN, Z_EZN + 10, 0.6,
                "10_EzratNashim")
# Couronnement des murs de l'Ezrat Nashim, et les battants d'or de sa porte est :
# « כָּל הַשְּׁעָרִים שֶׁהָיוּ שָׁם נִשְׁתַּנּוּ לִהְיוֹת שֶׁל זָהָב, חוּץ מִשַּׁעֲרֵי נִיקָנוֹר » (Middot 2:3).
couronnement("EzratNashim_couronnement_nord", EX0 - 0.5, EX1 - 0.5, 67.5, 72.5, Z_EZN + H_MUR_EN, "10_EzratNashim")
couronnement("EzratNashim_couronnement_sud", EX0 - 0.5, EX1 - 0.5, -72.5, -67.5, Z_EZN + H_MUR_EN, "10_EzratNashim")
couronnement("EzratNashim_couronnement_est", EX1, EX1 + 5, -72.5 - 0.5, 72.5 + 0.5, Z_EZN + H_MUR_EN, "10_EzratNashim")
battants("EzratNashim_porte_est", EX1, EX1 + 5, -5, 5, Z_EZN, 20, "10_EzratNashim", MAT_OR())
# Treize shofarot (Shekalim 6:5) : les troncs « en forme de shofar » — étroits en haut,
# larges en bas, pour qu'on n'y glisse pas la main (Bartenura) — le long du mur est, de
# part et d'autre de la porte. Bronze : CHOIX, la Mishna n'en dit pas la matière.
SHOFAR = [(0.62, 0.0), (0.60, 0.12), (0.40, 0.60), (0.24, 1.35), (0.20, 1.55), (0.14, 1.55), (0.12, 1.2), (0.0, 1.1)]
for k, y in enumerate([-26.5 + 3.4 * i for i in range(7)] + [6.1 + 3.4 * i for i in range(6)]):
    revolution(f"Shofar_{k:02d}", EX1 - 1.4, y, Z_EZN, SHOFAR, "10_EzratNashim", MAT_BRONZE(), verts=20)
# Simhat Beit HaShoeva (Soucca 5:2-3 ; 52b) : « מְנוֹרוֹת שֶׁל זָהָב הָיוּ שָׁם, וְאַרְבָּעָה סְפָלִים
# שֶׁל זָהָב בְּרָאשֵׁיהֶן, וְאַרְבָּעָה סֻלָּמוֹת לְכָל אֶחָד וְאֶחָד » — hauts de cinquante amot, dans
# l'Ezrat Nashim. Quatre mâts (nombre : CHOIX, la Mishna dit « des menorot »), quatre
# coupes et quatre échelles chacun, un barreau toutes les deux amot.
if CANDELABRES_SHOEVA:
    H_CANDELABRE = 50
    for k, (x, y) in enumerate(((EX0 + 30, -20), (EX0 + 30, 20), (EX1 - 30, -20), (EX1 - 30, 20))):
        nom = f"Candelabre_Shoeva_{k}"
        cyl(f"{nom}_socle", x, y, Z_EZN, Z_EZN + 1.0, 1.6, "10_EzratNashim", MAT_OR(), verts=24)
        cone(f"{nom}_mat", x, y, Z_EZN + 1.0, Z_EZN + H_CANDELABRE, 0.55, 0.35, "10_EzratNashim", MAT_OR(), verts=16)
        for j in range(4):
            a = math.pi / 2 * j
            dx, dy = math.cos(a), math.sin(a)
            cyl_between(f"{nom}_bras_{j}", (x, y, Z_EZN + H_CANDELABRE - 0.6),
                        (x + 1.8 * dx, y + 1.8 * dy, Z_EZN + H_CANDELABRE - 0.2), 0.12, "10_EzratNashim", MAT_OR(), verts=8)
            revolution(f"{nom}_sefel_{j}", x + 1.8 * dx, y + 1.8 * dy, Z_EZN + H_CANDELABRE - 0.2,
                       [(0.25, 0.0), (0.7, 0.55), (0.75, 0.7), (0.62, 0.7), (0.0, 0.25)], "10_EzratNashim", MAT_OR(), verts=16)
            pied = (x + 4.0 * dx, y + 4.0 * dy, Z_EZN)
            haut = (x + 0.5 * dx, y + 0.5 * dy, Z_EZN + H_CANDELABRE - 1.5)
            lat = (-dy * 0.5, dx * 0.5)
            for s, cote in ((-1, "a"), (1, "b")):
                cyl_between(f"{nom}_echelle_{j}_montant_{cote}", (pied[0] + s * lat[0], pied[1] + s * lat[1], pied[2]),
                            (haut[0] + s * lat[0], haut[1] + s * lat[1], haut[2]), 0.07, "10_EzratNashim", MAT_CEDRE(), verts=6)
            for i, t in enumerate(plage(0.02, 0.98, 2.0 / (H_CANDELABRE - 1.5))):
                px, py, pz = (pied[c] + (haut[c] - pied[c]) * t for c in range(3))
                cyl_between(f"{nom}_echelle_{j}_barreau_{i:02d}", (px - lat[0], py - lat[1], pz), (px + lat[0], py + lat[1], pz),
                            0.04, "10_EzratNashim", MAT_CEDRE(), verts=6)
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
X_DOUKHAN = AX1 - 13.5       # pied de la volée : marche d'une ama puis trois demies, sur 2,5 amot de large
box("Azara_sol", AX0, X_DOUKHAN, AY0, AY1, Z_AZ - 1, Z_AZ, "20_Azara", MAT_SOL())
box("EzratIsrael_sol", X_DOUKHAN, AX1, AY0, AY1, Z_EZI - 1, Z_EZI, "20_Azara", MAT_SOL())
H_MUR = 25
T = 5   # épaisseur des murs
# L'Azara et l'Ezrat Nashim sont des terrasses taillées dans le Har HaBayit, pas des
# dalles posées en l'air : hors de leurs murs le sol retombe à Z_HAR. Sans la masse
# qui les porte, les murs, les chambres d'angle et les quatre lishkot du pourtour
# flottaient — 13,5 amot au-dessus du dallage, visible plein cadre au plan 1.
# Deux blocs et non un : le mur est de l'Azara (x 0..5) descend déjà à Z_EZN, une
# masse qui monterait à Z_AZ sous lui lui donnerait une face coplanaire.
box("Podium_har", AX0 - T, EX1 + 5, AY0 - T, AY1 + T, Z_HAR, Z_EZN, "00_HarHabayit")
box("Podium_azara", AX0 - T, X_DOUKHAN, AY0 - T, AY1 + T, Z_EZN, Z_AZ, "00_HarHabayit")
box("Podium_ezrat_israel", X_DOUKHAN, AX1, AY0 - T, AY1 + T, Z_EZN, Z_EZI - 1, "00_HarHabayit")
# Le seuil de Nikanor : le sol de l'Ezrat Israël continue dans l'épaisseur du mur, sinon la
# baie ouvre sur le vide entre ses deux vantaux.
box("Nikanor_seuil", AX1, AX1 + T, -5, 5, Z_EZN, Z_EZI, "20_Azara", MAT_SOL())
# Mur est avec la porte de Nikanor (10 × 20) au centre
box("Azara_mur_est_S", AX1, AX1 + T, AY0 - T, -5, Z_EZN, Z_AZ + H_MUR, "20_Azara")
box("Azara_mur_est_N", AX1, AX1 + T, 5, AY1 + T, Z_EZN, Z_AZ + H_MUR, "20_Azara")
box("Nikanor_linteau", AX1, AX1 + T, -5, 5, Z_EZI + 20, Z_AZ + H_MUR, "20_Azara")
# Battants rabattus dans l'embrasure, comme ceux du Heikhal : les portes de l'Azara
# sont ouvertes dès l'aube (Tamid 3:7 ; Yoma 3:1-2), et à Kippour pendant l'avoda.
# Fermés, ils bouchaient l'axe est-ouest — la colonne vertébrale du film : les plans
# 6, 13 et 14 finissaient sur deux vantaux de bronze là où le découpage demande
# l'ouverture de l'Oulam au fond. Ils contredisaient aussi la ligne de mire de la
# para adouma (Middot 2:4), que le mur est bas est fait pour dégager.
box("Nikanor_porte_S", AX1 + 1, AX1 + 4.5, -5, -4.7, Z_EZI, Z_EZI + 20, "20_Azara", MAT_BRONZE())
box("Nikanor_porte_N", AX1 + 1, AX1 + 4.5, 4.7, 5, Z_EZI, Z_EZI + 20, "20_Azara", MAT_BRONZE())
# « שְׁנֵי פִשְׁפְּשִׁין הָיוּ לוֹ לְשַׁעַר נִיקָנוֹר, אֶחָד בִּימִינוֹ וְאֶחָד בִּשְׂמֹאלוֹ » (Middot 2:6) : deux
# guichets de bronze de part et d'autre de la grande porte, côté Azara. Cote (3 × 8) :
# CHOIX. Les vantaux sont posés sur le nu du mur — la baie n'est pas percée, et la face
# est, dix amot au-dessus du sol de l'Ezrat Nashim, n'en reçoit pas.
for cote, y0, y1 in (("S", -14.5, -11.5), ("N", 11.5, 14.5)):
    box(f"Nikanor_pishpesh_{cote}", AX1 - 0.25, AX1, y0, y1, Z_EZI, Z_EZI + 8, "20_Azara", MAT_BRONZE())
    box(f"Nikanor_pishpesh_{cote}_linteau", AX1 - 0.25, AX1, y0 - 0.3, y1 + 0.3, Z_EZI + 8, Z_EZI + 8.4, "20_Azara", MAT_BRONZE())
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
        # Six שערים aux battants d'or, Nikanor seule en bronze (Middot 2:3 ; Yoma 3:10) ;
        # ouverts dès l'aube (Tamid 3:7). Le פתח de HaGazit n'est pas un שער.
        if p != (GAZIT_X0 + GAZIT_X1) / 2:
            battants(f"Azara_porte_{nm}_{p:+.0f}_battants", p - 5, p + 5, y0, y1,
                     Z_AZ, 20, "20_Azara", MAT_OR())
# Ezrat Israël → Ezrat Kohanim (Middot 2:6, R. Eliezer ben Yaakov) : « מַעֲלָה גְבוֹהָה אַמָּה
# וְהַדּוּכָן נָתוּן עָלֶיהָ וּבוֹ שָׁלֹשׁ מַעֲלוֹת שֶׁל חֲצִי חֲצִי אַמָּה, נִמְצֵאת עֶזְרַת כֹּהֲנִים גְּבוֹהָה
# מֵעֶזְרַת יִשְׂרָאֵל שְׁתֵּי אַמּוֹת וּמֶחֱצָה ». Une volée qui monte vers l'ouest, sur toute la largeur :
# la marche d'une ama, puis les trois demi-marches du Doukhan, la dernière affleurant la cour.
# Les boîtes emboîtées d'avant faisaient un mur de 2,5 amot en travers de la porte.
box("Marche_EzratIsrael_Cohanim", AX1 - 12, AX1 - 11, AY0, AY1, Z_EZI - 1, Z_EZI + 1, "20_Azara")
for i in range(3):
    box(f"Doukhan_{i}", AX1 - 12.5 - i * 0.5, AX1 - 12 - i * 0.5, AY0, AY1, Z_EZI - 1, Z_EZI + 1.5 + 0.5 * i, "20_Azara")

# Chambres du pourtour — 80_Lishkot. Elles sont adossées aux murs de l'Azara mais
# posées sur la terrasse du 'Heil (plus bas) : leur pied est à Z_EZN, dix amot sous le sol
# de la cour qu'elles bordent. Les faire partir de Z_AZ les laissait en l'air. Middot 1:7 le dit
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
       Z_EZN, Z_AZ + 30, "80_Lishkot", [("N", *PORTE_SHAAR), ("S", *PORTE_SHAAR)])
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
       Z_EZN, Z_AZ + 30, "80_Lishkot", [("N", *PORTE_SHAAR), ("S", *PORTE_SHAAR)])
maake("Lishkat_HaGazit", GAZIT_X0, GAZIT_X1, NORD_Y0, NORD_Y1, Z_AZ + 30, "80_Lishkot")

# Sha'ar HaNitzotz, la porte nord la plus occidentale — le seul corps de porte que la
# Mishna décrive en entier : « וּכְמִין אַכְסַדְרָה הָיָה, וַעֲלִיָּה בְנוּיָה עַל גַּבָּיו,
# שֶׁהַכֹּהֲנִים שׁוֹמְרִים מִלְמַעְלָן וְהַלְוִיִּם מִלְּמַטָּן, וּפֶתַח הָיָה לוֹ לַחֵיל »
# (Middot 1:5). Le Beit HaNitzotz est l'un des trois postes de garde des Cohanim
# (Middot 1:1 ; Tamid 1:1), et son aliyah regarde l'Azara.
NZ_X0, NZ_X1 = PORTE_NITZOTZ - 10, PORTE_NITZOTZ + 10
NZ_Y0, NZ_Y1, NZ_Z0 = AY1 + T, NORD_Y1, Z_AZ + 25
lishka("Beit_ShaarHaNitzotz", NZ_X0, NZ_X1, NZ_Y0, NZ_Y1, Z_EZN, NZ_Z0,
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
lishka("Beit_ShaarHaMayim", SM_X0, SM_X1, BA_Y0, BA_Y1, Z_EZN, BA_Z0,
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
       Z_EZN, Z_AZ + 15, "80_Lishkot", [("S", *PORTE_LISHKA)])
maake("Lishkat_Parhedrin", SM_X0 - 16, SM_X0 - 1, BA_Y0, BA_Y1, Z_AZ + 15, "80_Lishkot")

# Les deux lishkot de Sha'ar Nikanor, dans l'Ezrat Israël, de part et d'autre de la
# porte est : « וּשְׁתֵּי לְשָׁכוֹת הָיוּ לוֹ, אַחַת מִימִינוֹ וְאַחַת מִשְּׂמֹאלוֹ, אַחַת לִשְׁכַּת
# פִּנְחָס הַמַּלְבִּישׁ, וְאַחַת לִשְׁכַּת עוֹשֵׂי חֲבִתִּין » (Middot 1:4 ; Rambam, Beit
# HaBe'hira 5:17). CHOIX : Pin'has au nord (la droite de qui entre), leur cote et leur
# hauteur, qu'aucune source ne donne. Elles s'ouvrent à l'ouest, sur la cour.
for nm, ny0, ny1 in (("Pinchas_HaMalbish", 5, 20), ("Osei_Chavitin", -20, -5)):
    lishka(f"Lishkat_{nm}", -8, AX1, ny0, ny1, Z_EZI, Z_AZ + 20,
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
# Un treillis de bois (Middot 2:3 ; fiche §2 : « séparation légère, pas un mur ») :
# poteaux au pas de 3 amot et deux lisses. La lame pleine d'avant se lisait en muret.
SOREG_H = 1.67
for nm, xa, xb, ya, yb in (("sud", SX0, SX1, SY0, SY0 + 0.2),
                           ("nord", SX0, SX1, SY1 - 0.2, SY1),
                           ("ouest", SX0, SX0 + 0.2, SY0 + 0.2, SY1 - 0.2),
                           ("est", SX1 - 0.2, SX1, SY0 + 0.2, SY1 - 0.2)):
    for k, (zb, zh) in enumerate(((Z_HAR + 0.55, Z_HAR + 0.68), (Z_HAR + SOREG_H - 0.13, Z_HAR + SOREG_H))):
        box(f"Soreg_{nm}_lisse_{k}", xa, xb, ya, yb, zb, zh, "00_HarHabayit", MAT_CHENE())
    long_x = (xb - xa) >= (yb - ya)
    a0, a1 = (xa, xb) if long_x else (ya + 1.5, yb - 1.5)   # les poteaux d'angle sont ceux des grands côtés
    for k, c in enumerate(plage(a0, a1, 3)):
        if long_x:
            box(f"Soreg_{nm}_poteau_{k:03d}", c - 0.15, c + 0.15, ya - 0.05, yb + 0.05,
                Z_HAR, Z_HAR + SOREG_H + 0.15, "00_HarHabayit", MAT_CHENE())
        else:
            box(f"Soreg_{nm}_poteau_{k:03d}", xa - 0.05, xb + 0.05, c - 0.15, c + 0.15,
                Z_HAR, Z_HAR + SOREG_H + 0.15, "00_HarHabayit", MAT_CHENE())
# La terrasse du 'Heil sur les trois autres côtés : le sol y est celui de l'Ezrat Nashim
# (Z_EZN), et ses douze marches descendent vers le soreg comme à l'est, en laissant les
# mêmes quatre amot de plat devant lui. À l'ouest, dix amot de 'Heil ne laissent pas de
# terrasse : les marches montent jusqu'au pied du podium. Les corps de porte et lishkot
# du pourtour sont posés sur cette terrasse, leur porte sur le 'Heil s'ouvre dessus.
HEIL_MARCHES = 12
for cote, ya, yb in (("nord", AY1 + T, NORD_Y1), ("sud", -NORD_Y1, AY0 - T)):
    box(f"Heil_terrasse_{cote}", AX0 - T, SX1 - 4, ya, yb, Z_HAR, Z_EZN, "00_HarHabayit")
for i in range(HEIL_MARCHES):
    z = Z_HAR + 0.5 * (i + 1)
    box(f"Heil_marche_nord_{i:02d}", SX0 + 4, SX1 - 4, SY1 - 4 - 0.5 * (i + 1), SY1 - 4 - 0.5 * i, Z_HAR, z, "00_HarHabayit")
    box(f"Heil_marche_sud_{i:02d}", SX0 + 4, SX1 - 4, SY0 + 4 + 0.5 * i, SY0 + 4 + 0.5 * (i + 1), Z_HAR, z, "00_HarHabayit")
    box(f"Heil_marche_ouest_{i:02d}", SX0 + 4 + 0.5 * i, SX0 + 4 + 0.5 * (i + 1), -NORD_Y1, NORD_Y1, Z_HAR, z, "00_HarHabayit")
# De la terrasse aux portes latérales : dix amot, vingt marches de « רוּם מַעֲלָה חֲצִי אַמָּה
# וְשִׁלְחָהּ חֲצִי אַמָּה » (Middot 2:3), sur la largeur de la baie. Devant les trois portes
# sans corps de porte ; Moked, Nitzotz et Mayim montent dans leur bâtiment.
for nm, x, cote in (("Korban", PORTE_KORBAN, "nord"), ("Bekhorot", PORTE_BEKHOROT, "sud"), ("Delek", PORTE_DELEK, "sud")):
    for k in range(20):
        if cote == "nord":
            ya, yb = AY1 + T + 0.5 * k, AY1 + T + 0.5 * (k + 1)
        else:
            ya, yb = AY0 - T - 0.5 * (k + 1), AY0 - T - 0.5 * k
        box(f"Escalier_{nm}_{k:02d}", x - 5, x + 5, ya, yb, Z_EZN, Z_AZ - 0.5 * k, "20_Azara")
# Couronnement des murs de l'Azara : une assise en débord sur la crête, qui saute
# les corps de porte passant les 25 amot (Beit HaMoked, HaGazit, et les terrasses
# de Sha'ar HaNitzotz et de Sha'ar HaMayim).
couronnement("Azara_couronnement_est", AX1, AX1 + T, AY0 - T - 0.5, AY1 + T + 0.5, Z_AZ + H_MUR, "20_Azara")
couronnement("Azara_couronnement_ouest", AX0 - T, AX0, AY0 + 0.5, AY1 - 0.5, Z_AZ + H_MUR, "20_Azara")
couronnement("Azara_couronnement_nord", AX0 - T - 0.5, AX1 - 0.5, AY1, AY1 + T, Z_AZ + H_MUR, "20_Azara",
             reserve=[(PORTE_MOKED - 10.5, PORTE_MOKED + 10.5), (GAZIT_X0 - 0.5, GAZIT_X1 + 0.5),
                      (NZ_X0 - LISHKA_DEBORD, NZ_X1 + LISHKA_DEBORD)])
couronnement("Azara_couronnement_sud", AX0 - T - 0.5, AX1 - 0.5, AY0 - T, AY0, Z_AZ + H_MUR, "20_Azara",
             reserve=[(SM_X0 - LISHKA_DEBORD, SM_X1 + LISHKA_DEBORD)])

# ----------------------------------------------------------------------------
# 30 — MIZBEA'H (Middot 3:1) + rampe + Kiyor + Beit HaMitba'haïm
# ----------------------------------------------------------------------------
MX0, MX1 = -54, -22          # 32 amot, à 22 amot de l'Oulam
MY0, MY1 = -25, 7            # CHOIX : centre 9 amot au sud de l'axe, bord nord à 60.5 du mur nord
                             # (Middot 5:2 ; Rambam Beit HaBe'hira 5:13-15). R. Yehouda (autel centré,
                             # Zeva'him 58b) non retenu. Voir README « Tranché ».
# Le yessod ne fait pas le tour : « הַיְסוֹד הָיָה מְהַלֵּךְ עַל פְּנֵי כָל הַצָּפוֹן וְעַל פְּנֵי כָל
# הַמַּעֲרָב, וְאוֹכֵל בַּדָּרוֹם אַמָּה אַחַת וּבַמִּזְרָח אַמָּה אַחַת » (Middot 3:1 ; fiche §6). Tout le
# nord et tout l'ouest, une ama à l'angle sud-ouest sur le sud, une ama à l'angle
# nord-est sur l'est ; le corps descend donc jusqu'au sol sur les faces est et sud.
box("Mizbeach_yessod_N", MX0 + 1, MX1, MY1 - 1, MY1, Z_AZ, Z_AZ + 1, "30_Mizbeach", MAT_CHAUX())
box("Mizbeach_yessod_O", MX0, MX0 + 1, MY0, MY1, Z_AZ, Z_AZ + 1, "30_Mizbeach", MAT_CHAUX())
box("Mizbeach_yessod_S", MX0 + 1, MX0 + 2, MY0, MY0 + 1, Z_AZ, Z_AZ + 1, "30_Mizbeach", MAT_CHAUX())
box("Mizbeach_yessod_E", MX1 - 1, MX1, MY1 - 2, MY1 - 1, Z_AZ, Z_AZ + 1, "30_Mizbeach", MAT_CHAUX())
box("Mizbeach_corps", MX0 + 1, MX1 - 1, MY0 + 1, MY1 - 1, Z_AZ, Z_AZ + 6, "30_Mizbeach", MAT_CHAUX())
box("Mizbeach_haut", MX0 + 2, MX1 - 2, MY0 + 2, MY1 - 2, Z_AZ + 6, Z_AZ + 9, "30_Mizbeach", MAT_CHAUX_FEU())
for (nm, x, y) in [("SE", MX1 - 3, MY0 + 2), ("NE", MX1 - 3, MY1 - 3), ("NO", MX0 + 2, MY1 - 3), ("SO", MX0 + 2, MY0 + 2)]:
    box(f"Keren_{nm}", x, x + 1, y, y + 1, Z_AZ + 9, Z_AZ + 10, "30_Mizbeach", MAT_CHAUX_FEU())
# « וְחוּט שֶׁל סִקְרָא חוֹגְרוֹ בָאֶמְצַע » (Middot 3:1) : la ligne rouge à mi-hauteur, qui sépare
# les sangs d'en haut des sangs d'en bas — le seul trait de couleur sur la chaux.
for nm, xa, xb, ya, yb in (("E", MX1 - 1, MX1 - 0.97, MY0 + 1, MY1 - 1), ("O", MX0 + 0.97, MX0 + 1, MY0 + 1, MY1 - 1),
                           ("N", MX0 + 1, MX1 - 1, MY1 - 1, MY1 - 0.97), ("S", MX0 + 1, MX1 - 1, MY0 + 0.97, MY0 + 1)):
    box(f"Mizbeach_sikra_{nm}", xa, xb, ya, yb, Z_AZ + 4.95, Z_AZ + 5.05, "30_Mizbeach", MAT_SIKRA())
# Quatre ma'arakhot le jour de Kippour (Rambam, Temidin ouMousafin 2:4 — l'avis de
# R. Yossi, Yoma 4:6 ; le tana kama en compte trois) : la grande à l'est, celle de la
# ketoret à l'angle sud-ouest (Tamid 2:4-5), la troisième pour entretenir le feu, la
# quatrième pour les membres du tamid de la veille. Chacune : deux lits de bûches
# croisées sous les braises. Une seule dalle noire de 16 amot se lisait en bassin.
MAARAKHOT = (("gedola", -36, -28, -13, -5), ("ketoret", -48, -45, -19, -16),
             ("kiyum", -48, -45, -4, -1), ("kippour", -42, -39, -19, -16))
for nm, xa, xb, ya, yb in MAARAKHOT:
    for lit, (le_long, zb) in enumerate((("x", Z_AZ + 9.0), ("y", Z_AZ + 9.35))):
        for k, c in enumerate(plage(0.15, 0.85, 0.35)):
            if le_long == "x":
                cyl_between(f"Maarakha_{nm}_buche_{lit}{k}", (xa, ya + (yb - ya) * c, zb + 0.18),
                            (xb, ya + (yb - ya) * c, zb + 0.18), 0.17, "30_Mizbeach", MAT_CHENE(), verts=8)
            else:
                cyl_between(f"Maarakha_{nm}_buche_{lit}{k}", (xa + (xb - xa) * c, ya, zb + 0.18),
                            (xa + (xb - xa) * c, yb, zb + 0.18), 0.17, "30_Mizbeach", MAT_CHENE(), verts=8)
    box(f"Maarakha_{nm}", xa + 0.2, xb - 0.2, ya + 0.2, yb - 0.2, Z_AZ + 9.6, Z_AZ + 9.95, "30_Mizbeach", braise("Braise"))
# Le feu lui-même. La ma'arakha était une boîte noire sans source : la colonne de fumée
# montait d'un autel éteint, et la rampe du plan 7b n'avait que la lumière du ciel — la
# raison pour laquelle elle ne se détachait ni de l'autel ni du dallage.
_, GX0, GX1, GY0, GY1 = MAARAKHOT[0]
feu = lampe("Maarakha_feu", 'AREA', (m((GX0 + GX1) / 2), m((GY0 + GY1) / 2), m(Z_AZ + 10.2)))
feu.data.shape = 'RECTANGLE'
feu.data.size = m(GX1 - GX0)
feu.data.size_y = m(GY1 - GY0)
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
FUMEE_X, FUMEE_Y = (GX0 + GX1) / 2, (GY0 + GY1) / 2    # au-dessus de la grande ma'arakha
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
# « וּשְׁנֵי כְבָשִׁים קְטַנִּים יוֹצְאִין מִן הַכֶּבֶשׁ, שֶׁבָּהֶן פּוֹנִים לַיְסוֹד וְלַסּוֹבֵב, מֻבְדָּלִין מִן
# הַמִּזְבֵּחַ אַמָּה אַחַת » (Middot 3:3 ; Rambam Beit HaBe'hira 2:14 : celui du sovev à
# l'ouest, celui du yessod à l'est) : deux passerelles qui quittent la rampe à la
# hauteur du sovev (6) et du yessod (1), et rejoignent l'autel à une ama d'écart.
Y_SOVEV_RAMPE = MY0 - 30 + 30 * 6 / 9       # là où la rampe passe 6 amot
Y_YESSOD_RAMPE = MY0 - 30 + 30 * 1 / 9      # et une ama
box("Kevesh_katan_sovev", xc - 10.5, xc - 8, Y_SOVEV_RAMPE, MY0 + 1, Z_AZ + 5.6, Z_AZ + 6, "30_Mizbeach", MAT_CHAUX())
box("Kevesh_katan_yessod", xc + 8, xc + 10.5, Y_YESSOD_RAMPE, MY0, Z_AZ + 0.6, Z_AZ + 1, "30_Mizbeach", MAT_CHAUX())
# Kiyor : entre l'Oulam et le Mizbea'h, décalé vers le sud (Middot 3:6). La même michna
# donne les 22 amot et les douze marches ; les marches en prennent 12, il reste 10 amot
# de plat entre x -64 et -54, et c'est là que le bassin tient.
# Bronze, sur son pied (le כַּן, Shemot 30:18) ; douze robinets, « שְׁנֵים עָשָׂר דַּד »,
# le perfectionnement de Ben Katin (Yoma 3:10 ; fiche §7). Deux cylindres empilés se
# lisaient en tambour : profil tourné, panse, lèvre, et l'eau dans la vasque.
KIYOR_X, KIYOR_Y = -59, -8
revolution("Kiyor", KIYOR_X, KIYOR_Y, Z_AZ,
           [(1.05, 0.0), (1.0, 0.12), (0.55, 0.30), (0.45, 0.55), (0.45, 0.95), (0.60, 1.05),
            (1.35, 1.25), (1.65, 1.60), (1.72, 2.05), (1.80, 2.20), (1.82, 2.30), (1.68, 2.30),
            (1.62, 2.05), (1.45, 1.55), (0.0, 1.30)], "30_Mizbeach", MAT_BRONZE(), verts=36)
cyl("Kiyor_eau", KIYOR_X, KIYOR_Y, Z_AZ + 1.95, Z_AZ + 2.02, 1.66, "30_Mizbeach", MAT_EAU(), verts=36)
for i in range(12):
    a = 2 * math.pi * i / 12
    dx, dy = math.cos(a), math.sin(a)
    cyl_between(f"Kiyor_dad_{i:02d}", (KIYOR_X + 1.45 * dx, KIYOR_Y + 1.45 * dy, Z_AZ + 1.45),
                (KIYOR_X + 2.0 * dx, KIYOR_Y + 2.0 * dy, Z_AZ + 1.40), 0.06, "30_Mizbeach", MAT_BRONZE(), verts=8)
    cyl_between(f"Kiyor_dad_{i:02d}_bec", (KIYOR_X + 2.0 * dx, KIYOR_Y + 2.0 * dy, Z_AZ + 1.40),
                (KIYOR_X + 2.0 * dx, KIYOR_Y + 2.0 * dy, Z_AZ + 1.22), 0.06, "30_Mizbeach", MAT_BRONZE(), verts=8)
# Mukhni de Ben Katin (Yoma 3:10 ; 37a) : la roue qui descend le Kiyor dans son puits
# chaque soir, « כְּדֵי שֶׁלֹּא יִהְיוּ מֵימָיו נִפְסָלִין בְּלִינָה ». Un poteau, une potence, une
# roue et une chaîne jusqu'au bord de la cuve ; la forme est un CHOIX.
MUKHNI_X = KIYOR_X - 3.5
cyl("Mukhni_poteau", MUKHNI_X, KIYOR_Y, Z_AZ, Z_AZ + 5.6, 0.22, "30_Mizbeach", MAT_CEDRE(), verts=12)
cyl_between("Mukhni_potence", (MUKHNI_X, KIYOR_Y, Z_AZ + 5.3), (KIYOR_X, KIYOR_Y, Z_AZ + 5.3), 0.16, "30_Mizbeach", MAT_CEDRE(), verts=10)
cyl_between("Mukhni_jambe_de_force", (MUKHNI_X, KIYOR_Y, Z_AZ + 3.6), (MUKHNI_X + 1.8, KIYOR_Y, Z_AZ + 5.2), 0.1, "30_Mizbeach", MAT_CEDRE(), verts=8)
tore("Mukhni_roue", MUKHNI_X, KIYOR_Y - 0.45, Z_AZ + 3.8, 0.8, 0.08, "30_Mizbeach", MAT_CEDRE(), rotation=(math.pi / 2, 0, 0))
for k in range(6):
    a = math.pi * k / 6
    cyl_between(f"Mukhni_rayon_{k}", (MUKHNI_X + 0.75 * math.cos(a), KIYOR_Y - 0.45, Z_AZ + 3.8 + 0.75 * math.sin(a)),
                (MUKHNI_X - 0.75 * math.cos(a), KIYOR_Y - 0.45, Z_AZ + 3.8 - 0.75 * math.sin(a)), 0.04, "30_Mizbeach", MAT_CEDRE(), verts=6)
cyl_between("Mukhni_essieu", (MUKHNI_X, KIYOR_Y - 0.6, Z_AZ + 3.8), (MUKHNI_X, KIYOR_Y + 0.3, Z_AZ + 3.8), 0.06, "30_Mizbeach", MAT_FER(), verts=8)
for k, (z0, z1) in enumerate(((5.3, 4.6), (4.6, 3.9), (3.9, 3.2), (3.2, 2.5))):
    cyl_between(f"Mukhni_chaine_{k}", (KIYOR_X, KIYOR_Y, Z_AZ + z0), (KIYOR_X, KIYOR_Y, Z_AZ + z1), 0.05, "30_Mizbeach", MAT_FER(), verts=6)
# Magrefa (Tamid 5:6 ; Arakhin 10b-11a) : « אַמָּה עַל אַמָּה, וְיָד יוֹצֵא מִמֶּנָּה, וַעֲשָׂרָה
# נְקָבִים הָיוּ בָהּ ». Posée entre l'Oulam et le Mizbea'h, là où on la jette (Tamid 5:6).
box("Magrefa", -61, -60, 13, 14, Z_AZ, Z_AZ + 0.15, "30_Mizbeach", MAT_BRONZE())
cyl_between("Magrefa_yad", (-60, 13.5, Z_AZ + 0.08), (-58.4, 13.5, Z_AZ + 0.08), 0.06, "30_Mizbeach", MAT_BRONZE(), verts=8)
for k in range(10):
    cyl(f"Magrefa_nekev_{k}", -60.85 + 0.19 * k, 13.5, Z_AZ + 0.15, Z_AZ + 0.55, 0.045, "30_Mizbeach", MAT_BRONZE(), verts=8)

# --- Les cuivres de Shlomo (Melakhim I 7:23-39 ; Divrei HaYamim II 4:2-6), à côté du
#     Kiyor de la Mishna — comme Menachot 98b range les dix menorot de Shlomo autour de
#     celle de Moshé. Ils sont du Premier Temple : Middot ne les connaît pas (CHOIX).
# La Mer : dix amot de bord à bord, cinq de haut, trente de tour, « כְּמַעֲשֵׂה שְׂפַת כּוֹס
# פֶּרַח שׁוֹשָׁן », deux rangs de coloquintes sous la lèvre, douze bœufs, trois vers chaque
# vent, « וְכָל אֲחֹרֵיהֶם בָּיְתָה ». « עַל כֶּתֶף הַבַּיִת הַיְמָנִית קֵדְמָה מִמּוּל נֶגֶב » (7:39) :
# au sud-est du bâtiment, entre les marches de l'Oulam et la rampe.
YAM_X, YAM_Y, YAM_Z = -63, -40, Z_AZ + 2.2
YAM = [(0.6, 0.0), (3.6, 0.5), (4.5, 1.6), (4.75, 3.2), (4.7, 3.9), (5.0, 4.6), (5.2, 5.0),
       (4.95, 5.0), (4.6, 4.4), (4.45, 3.0), (3.6, 1.0), (0.0, 0.6)]
revolution("Yam", YAM_X, YAM_Y, YAM_Z, YAM, "30_Mizbeach", MAT_BRONZE(), verts=48)
cyl("Yam_eau", YAM_X, YAM_Y, YAM_Z + 4.2, YAM_Z + 4.27, 4.5, "30_Mizbeach", MAT_EAU(), verts=48)
for rang, z in enumerate((3.55, 3.85)):
    for k in range(75):
        a = 2 * math.pi * (k + 0.5 * rang) / 75
        sphere(f"Yam_peka_{rang}{k:02d}", YAM_X + 4.8 * math.cos(a), YAM_Y + 4.8 * math.sin(a), YAM_Z + z, 0.14,
               "30_Mizbeach", MAT_BRONZE(), segs=6)


def boeuf(name, x, y, z0, d, col, mat):
    """Bœuf de la Mer : tête vers `d` (vecteur cardinal), croupe vers le centre."""
    dx, dy = d
    px, py = -dy, dx

    def pt(le_long, en_travers):
        return x + dx * le_long + px * en_travers, y + dy * le_long + py * en_travers

    (ax, ay), (bx, by) = pt(0, -0.5), pt(2.4, 0.5)
    box(f"{name}_corps", ax, bx, ay, by, z0 + 1.0, z0 + 2.1, col, mat)
    (ax, ay), (bx, by) = pt(2.3, -0.28), pt(3.0, 0.28)
    box(f"{name}_tete", ax, bx, ay, by, z0 + 1.55, z0 + 2.1, col, mat)
    for k, (l, t) in enumerate(((0.35, -0.32), (0.35, 0.32), (2.0, -0.32), (2.0, 0.32))):
        cx, cy = pt(l, t)
        cyl(f"{name}_patte_{k}", cx, cy, z0, z0 + 1.0, 0.13, col, mat, verts=8)
    for k, s in enumerate((-1, 1)):
        (ax, ay), (bx, by) = pt(2.85, s * 0.2), pt(2.95, s * 0.55)
        cyl_between(f"{name}_corne_{k}", (ax, ay, z0 + 2.1), (bx, by, z0 + 2.5), 0.04, col, mat, verts=6)


for nm, d in (("E", (1, 0)), ("N", (0, 1)), ("O", (-1, 0)), ("S", (0, -1))):
    for k, t in enumerate((-1.5, 0.0, 1.5)):
        boeuf(f"Yam_shor_{nm}{k}", YAM_X + d[0] * 3.0 - d[1] * t, YAM_Y + d[1] * 3.0 + d[0] * t, Z_AZ, d,
              "30_Mizbeach", MAT_BRONZE())
# Les dix mekhonot (Melakhim I 7:27-39) : socles de bronze de 4 × 4 × 3 sur quatre roues
# d'une ama et demie, panneaux à lions, bœufs et keruvim (ici : leurs cadres seulement),
# et une cuve de quatre amot sur chacun. « חָמֵשׁ עַל כֶּתֶף הַבַּיִת מִיָּמִין וְחָמֵשׁ עַל כֶּתֶף
# הַבַּיִת מִשְּׂמֹאל » : sur l'épaule du bâtiment — la plateforme de 6 amot, à côté du corps.
MEKHONA = [(1.4, 0.0), (1.9, 0.25), (2.0, 0.9), (1.85, 1.35), (1.7, 1.35), (1.75, 0.9), (1.55, 0.35), (0.0, 0.2)]
for cote, y in (("S", -42.5), ("N", 42.5)):
    for k, x in enumerate((-105, -120, -135, -150, -165)):
        nom = f"Mekhona_{cote}{k}"
        box(f"{nom}_corps", x - 2, x + 2, y - 2, y + 2, Z_BAT + 0.9, Z_BAT + 3.6, "30_Mizbeach", MAT_BRONZE())
        for face, (xa, xb, ya, yb) in (("E", (x + 2, x + 2.12, y - 1.8, y + 1.8)), ("O", (x - 2.12, x - 2, y - 1.8, y + 1.8)),
                                        ("N", (x - 1.8, x + 1.8, y + 2, y + 2.12)), ("S", (x - 1.8, x + 1.8, y - 2.12, y - 2))):
            box(f"{nom}_cadre_{face}_bas", xa, xb, ya, yb, Z_BAT + 1.2, Z_BAT + 1.4, "30_Mizbeach", MAT_BRONZE())
            box(f"{nom}_cadre_{face}_haut", xa, xb, ya, yb, Z_BAT + 3.1, Z_BAT + 3.3, "30_Mizbeach", MAT_BRONZE())
        for j, (rx, ry) in enumerate(((-1.3, -2.2), (1.3, -2.2), (-1.3, 2.2), (1.3, 2.2))):
            tore(f"{nom}_roue_{j}", x + rx, y + ry, Z_BAT + 0.75, 0.62, 0.13, "30_Mizbeach", MAT_BRONZE(), rotation=(math.pi / 2, 0, 0))
        cyl(f"{nom}_col", x, y, Z_BAT + 3.6, Z_BAT + 4.1, 1.2, "30_Mizbeach", MAT_BRONZE(), verts=24)
        revolution(f"{nom}_kiyor", x, y, Z_BAT + 4.1, MEKHONA, "30_Mizbeach", MAT_BRONZE(), verts=32)
        cyl(f"{nom}_eau", x, y, Z_BAT + 5.25, Z_BAT + 5.3, 1.7, "30_Mizbeach", MAT_EAU(), verts=32)
# Beit HaMitba'haïm au nord : 8 piliers, 8 tables de marbre, 24 anneaux. Les
# ninnasin portent « רְבִיעִית שֶׁל אֶרֶז עַל גַּבֵּיהֶן וְאֻנְקְלָיוֹת שֶׁל בַּרְזֶל הָיוּ קְבוּעִין בָּהֶן,
# שְׁלֹשָׁה סְדָרִים » (Middot 3:5) : trois rangs de crochets de fer, sur les deux faces qui
# regardent le rang — c'est là que pendent les bêtes.
for i in range(8):
    x = MX1 - 3 - i * 3.7
    cyl(f"Pilier_{i}", x, 53.2, Z_AZ, Z_AZ + 3, 0.5, "30_Mizbeach")
    box(f"Pilier_{i}_cedre", x - 0.7, x + 0.7, 52.5, 53.9, Z_AZ + 3, Z_AZ + 4.2, "30_Mizbeach", MAT_CEDRE())
    for sens, face in ((-1, "O"), (1, "E")):
        for rang, z in enumerate((Z_AZ + 3.25, Z_AZ + 3.6, Z_AZ + 3.95)):
            crochet(f"Pilier_{i}_crochet_{face}{rang}", x + sens * 0.7, 53.2 + (rang - 1) * 0.35, z, sens, "30_Mizbeach")
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
    box(f"Marche_Ulam_{i:02d}", BX_E + (12 - i) - 1, BX_E + (12 - i), -11, 11,
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
    box(f"Maltera_{i}", BX_E - 5.4, BX_E + 0.4, -L / 2, L / 2, Z_BAT + 41 + i * 2, Z_BAT + 42 + i * 2, "40_Ulam", MAT_CHENE_SCULPTE())
# --- Rovadim : les bandeaux en saillie qui ceinturent les murs de l'Oulam de bas en
#     haut (Rambam, Beit HaBe'hira 4:9). C'est la seule articulation que les sources
#     donnent à cette façade, et elle est horizontale.
#     Aucune source du Second Temple ne met de colonne sur la face du bâtiment : ni Middot
#     3:7-8 et 4:6-7, ni le Rambam, ni Josèphe qui l'a vue pierre à pierre (Guerre V, 5, 4
#     et 6). Ya'hin et Boaz sont du Premier Temple, « עַל פְּנֵי הַהֵיכָל » (Divrei HaYamim II
#     3:17) : le film les dresse devant la façade, de part et d'autre des marches (CHOIX,
#     voir plus bas). Les fûts de l'Oulam sont les כְּלוֹנָסוֹת de cèdre tendus du mur du
#     Heikhal à celui de l'Oulam (Middot 3:8).
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
# « כְּלוֹנָסוֹת שֶׁל אֶרֶז הָיוּ קְבוּעִין מִכָּתְלוֹ שֶׁל הֵיכָל לְכָתְלוֹ שֶׁל אוּלָם, כְּדֵי שֶׁלֹּא יִבְעַט »
# (Middot 3:8) : les poutres rondes de cèdre tendues d'un mur à l'autre, sous le
# plafond, et trois poutres en travers qui en font les caissons — le « coffered cedar
# ceiling of the porch » du prompt 8, qui n'était qu'une dalle.
for k, y in enumerate(plage(-31.5, 31.5, 7)):
    cyl_between(f"Ulam_klonas_{k:02d}", (BX_E - 16, y, Z_BAT + 38.4), (BX_E - 5, y, Z_BAT + 38.4),
                0.5, "40_Ulam", MAT_CEDRE(), verts=12)
for k, x in enumerate((BX_E - 13.25, BX_E - 10.5, BX_E - 7.75)):
    box(f"Ulam_plafond_poutre_{k}", x - 0.4, x + 0.4, -35, 35, Z_BAT + 39.1, Z_BAT + 40, "40_Ulam", MAT_CEDRE())
# Deux tables de l'Oulam (marbre au nord... CHOIX : marbre à droite en entrant = nord ; or au sud)
box("Ulam_table_marbre", -90, -88, 5.5, 6.5, Z_BAT, Z_BAT + 1.5, "40_Ulam", MAT_MARBRE())
box("Ulam_table_or", -90, -88, -6.5, -5.5, Z_BAT, Z_BAT + 1.5, "40_Ulam", MAT_OR())
# Ya'hin et Boaz (Melakhim I 7:15-22, 41-42 ; Divrei HaYamim II 3:15-17) : « וַיָּקֶם אֶת
# הָעַמּוּדִים עַל פְּנֵי הַהֵיכָל, אֶחָד מִיָּמִין וְאֶחָד מִשְּׂמֹאול » — devant la façade, de part et
# d'autre des marches, sur le sol de l'Azara. Hauteur : CHOIX. Melakhim donne 18 amot de fût,
# Divrei HaYamim II 3:15 en donne 35, dans une maison de 30 (Melakhim I 6:2) — les colonnes
# montaient aux trois quarts. La façade fait 100 : même proportion, 70 de fût plus le
# chapiteau de cinq (Melakhim 7:16), 75, au niveau des maltera'ot. Douze amot de tour, creux
# de quatre doigts, chapiteaux en lys sur quatre amot, réseaux et sept chaînettes sur le
# ventre, deux rangs de cent grenades. Ya'hin à droite (sud), Boaz à gauche.
AMOUD_X, AMOUD_Y, AMOUD_R, AMOUD_H = BX_E + 3, 13.5, 12 / (2 * math.pi), 70
KOTERET = [(AMOUD_R, 0.0), (2.25, 0.5), (2.4, 1.3), (2.3, 2.0), (1.95, 2.7), (2.15, 3.3), (2.8, 4.4), (3.05, 5.0),
           (2.85, 5.0), (2.2, 4.3), (0.0, 3.6)]
for nom, y in (("Yakhin", -AMOUD_Y), ("Boaz", AMOUD_Y)):
    cyl(f"{nom}_base", AMOUD_X, y, Z_AZ, Z_AZ + 0.6, AMOUD_R + 0.4, "40_Ulam", MAT_BRONZE(), verts=48)
    cyl(f"{nom}_fut", AMOUD_X, y, Z_AZ + 0.6, Z_AZ + AMOUD_H, AMOUD_R, "40_Ulam", MAT_BRONZE(), verts=48)
    revolution(f"{nom}_koteret", AMOUD_X, y, Z_AZ + AMOUD_H, KOTERET, "40_Ulam", MAT_BRONZE(), verts=48)
    for k in range(7):
        tore(f"{nom}_sharsheret_{k}", AMOUD_X, y, Z_AZ + AMOUD_H + 0.55 + 0.2 * k, 2.42 - 0.03 * abs(k - 3), 0.05,
             "40_Ulam", MAT_BRONZE())
    for rang, z in enumerate((1.0, 1.6)):
        for k in range(100):
            a = 2 * math.pi * (k + 0.5 * rang) / 100
            sphere(f"{nom}_rimon_{rang}{k:02d}", AMOUD_X + 2.45 * math.cos(a), y + 2.45 * math.sin(a),
                   Z_AZ + AMOUD_H + z, 0.07, "40_Ulam", MAT_BRONZE(), segs=6)
# La tablette d'or d'Hélène (Yoma 3:10), « שֶׁפָּרָשַׁת סוֹטָה כְּתוּבָה עָלֶיהָ », d'où le kohen
# copie la parasha. Sur l'or du mur est de l'Oulam, côté nord : CHOIX.
TAVLA_X = BX_E - 16 + EPAISSEUR_PLACAGE   # le nu de l'or sur le mur est du Heikhal, HX_E plus bas
box("Tavla_Helene", TAVLA_X, TAVLA_X + 0.08, 18.5, 21.5, Z_BAT + 5.5, Z_BAT + 7.5, "40_Ulam", MAT_OR())
for k in range(8):
    z = Z_BAT + 7.25 - 0.22 * k
    box(f"Tavla_Helene_ligne_{k}", TAVLA_X + 0.08, TAVLA_X + 0.11, 18.75 + (0.35 if k == 7 else 0), 21.25,
        z, z + 0.06, "40_Ulam", MAT_OR())
# Vigne d'or suspendue devant l'entrée du Heikhal (Middot 3:8) : représentée par un tore
# Remontée à 27 amot : à 23 elle enfermait la couronne d'Hélène dans son anneau, et
# les deux ne faisaient plus qu'un objet au rendu du plan 8.
# « גֶּפֶן שֶׁל זָהָב הָיְתָה עוֹמֶדֶת עַל פִּתְחוֹ שֶׁל הֵיכָל, וּמֻדְלָה עַל גַּבֵּי כְלוֹנָסוֹת, וְכָל מִי
# שֶׁהוּא מִתְנַדֵּב עָלֶה אוֹ גַרְגִּיר אוֹ אֶשְׁכּוֹל, מֵבִיא וְתוֹלֶה בָהּ » (Middot 3:8) : une vigne
# palissée sur des perches, où l'on suspend feuilles, grains et grappes. L'anneau nu
# se stylisait en cerceau ; il porte maintenant ses deux perches jusqu'aux poutres du
# plafond, vingt-quatre feuilles et douze grappes.
VIGNE_X, VIGNE_Z, VIGNE_R = -91.5, Z_BAT + 27, 3
tore("Vigne_or", VIGNE_X, 0, VIGNE_Z, VIGNE_R, 0.3, "40_Ulam", MAT_OR(),
     rotation=(0, math.pi / 2, 0))
for s in (-1, 1):
    cyl_between(f"Vigne_perche{s:+d}", (VIGNE_X, s * 3.6, VIGNE_Z - VIGNE_R - 0.3),
                (VIGNE_X, s * 3.6, Z_BAT + 37.9), 0.14, "40_Ulam", MAT_OR(), verts=10)
cyl_between("Vigne_traverse", (VIGNE_X, -3.6, VIGNE_Z + VIGNE_R + 0.5), (VIGNE_X, 3.6, VIGNE_Z + VIGNE_R + 0.5),
            0.12, "40_Ulam", MAT_OR(), verts=10)
GRAINS = ((0.08, 0.12, 0.0), (-0.08, -0.12, 0.0), (0.06, 0.0, -0.2), (-0.06, 0.1, -0.33),
          (0.05, -0.1, -0.33), (0.0, 0.0, -0.5))
for k in range(24):
    phi = math.radians(7.5 + 15 * k)
    radial, tangent = (math.sin(phi), -math.cos(phi)), (math.cos(phi), math.sin(phi))
    cy, cz = VIGNE_R * radial[0], VIGNE_Z + VIGNE_R * radial[1]
    x_feuille = VIGNE_X + 0.35
    quad = [(x_feuille, cy + 0.28 * tangent[0] - 0.1 * radial[0], cz + 0.28 * tangent[1] - 0.1 * radial[1]),
            (x_feuille, cy + 0.28 * tangent[0] + 0.5 * radial[0], cz + 0.28 * tangent[1] + 0.5 * radial[1]),
            (x_feuille, cy - 0.28 * tangent[0] + 0.5 * radial[0], cz - 0.28 * tangent[1] + 0.5 * radial[1]),
            (x_feuille, cy - 0.28 * tangent[0] - 0.1 * radial[0], cz - 0.28 * tangent[1] - 0.1 * radial[1])]
    plaque(f"Vigne_feuille_{k:02d}", quad, 0.03, "40_Ulam", MAT_OR())
    if k % 2 == 0:
        for g, (gx, gy, gz) in enumerate(GRAINS):
            sphere(f"Vigne_grappe_{k // 2:02d}_{g}", VIGNE_X + gx, cy + gy, cz - 0.45 + gz,
                   0.13 - 0.012 * g, "40_Ulam", MAT_OR(), segs=6)
# Couronne d'or de la reine Hélène, suspendue au-dessus de l'entrée du Heikhal
# (Yoma 37a : « c'est par elle qu'on savait que le soleil s'était levé »). Le prompt
# du plan 8 la décrivait sans qu'elle existe dans le blockout : ou le modèle
# l'inventait ailleurs, ou il ne la mettait pas. Middot n'en donne pas les cotes.
# La poser à -92,5 ne réglait rien : l'anneau de 2,4 amot s'enfonçait de 1,9 dans le
# linteau (x -98..-92) et aucun rayon du plan 8 ne le touchait. Son centre doit donc
# être à l'est de la face du mur d'au moins son rayon.
# Une נִבְרֶשֶׁת est suspendue : trois chaînes la pendent au bas de la vigne (CHOIX), et
# elle est une couronne, pointes dressées, ce que l'anneau nu ne disait pas.
COURONNE_X, COURONNE_Z, COURONNE_R = -90.6, Z_BAT + 22, 1.2
tore("Couronne_Helene", COURONNE_X, 0, COURONNE_Z, COURONNE_R, 0.15, "40_Ulam", MAT_OR())
for k in range(8):
    a = 2 * math.pi * k / 8
    cone(f"Couronne_Helene_pointe_{k}", COURONNE_X + COURONNE_R * math.cos(a), COURONNE_R * math.sin(a),
         COURONNE_Z + 0.12, COURONNE_Z + 0.42, 0.07, 0.0, "40_Ulam", MAT_OR(), verts=6)
for k in range(3):
    a = math.radians(90 + 120 * k)
    cyl_between(f"Couronne_Helene_chaine_{k}",
                (COURONNE_X + COURONNE_R * math.cos(a), COURONNE_R * math.sin(a), COURONNE_Z + 0.1),
                (VIGNE_X, 0, VIGNE_Z - VIGNE_R - 0.2), 0.025, "40_Ulam", MAT_OR(), verts=6)

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
# Les fenêtres hautes du Heikhal, « שְׁקוּפִים אֲטוּמִים » (Melakhim I 6:4 ; Mena'hot 86b :
# étroites dedans, larges dehors, « qu'il émet la lumière et ne la reçoit pas »).
# Elles étaient des boîtes de chaux noyées dans le mur, coplanaires avec ses deux
# faces : un rectangle blanc qui clignotait sur l'or du plan 9a. Ce sont maintenant
# de vraies baies, en deux épaisseurs — l'embrasure extérieure de 3 × 6, l'intérieure
# de 1,2 × 4 — percées dans le mur ET dans le placage d'or.
FENETRES_X = [HK0 - 6 - i * 9 for i in range(4)]
FENETRE_EXT, FENETRE_INT = (3.0, Z_BAT + 30, Z_BAT + 36), (1.2, Z_BAT + 31, Z_BAT + 35)


def baies_heikhal(largeur, zb, zh):
    return [(x - largeur / 2, x + largeur / 2, zb, zh) for x in FENETRES_X]


for cote, y_int, y_mi, y_ext in (("N", 10, 25, 35), ("S", -10, -25, -35)):
    paroi_percee(f"Corps_mur_{cote}_ext", BX_O, HK0, *sorted((y_mi, y_ext)), Z_BAT, Z_TOIT,
                 "50_Heikhal", MAT_MARBRE_HERODE(), baies_heikhal(*FENETRE_EXT))
    paroi_percee(f"Corps_mur_{cote}_int", BX_O, HK0, *sorted((y_int, y_mi)), Z_BAT, Z_TOIT,
                 "50_Heikhal", MAT_MARBRE_HERODE(), baies_heikhal(*FENETRE_INT))
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
paroi_percee("Heikhal_or_mur_N", HK1, HK0, 10 - EPAISSEUR_PLACAGE, 10, Z_BAT, Z_BAT + 40,
             "50_Heikhal", MAT_OR_PLAQUE(), baies_heikhal(*FENETRE_INT))
paroi_percee("Heikhal_or_mur_S", HK1, HK0, -10, -10 + EPAISSEUR_PLACAGE, Z_BAT, Z_BAT + 40,
             "50_Heikhal", MAT_OR_PLAQUE(), baies_heikhal(*FENETRE_INT))
box("Heikhal_or_plafond", HK1, HK0, -10, 10, Z_BAT + 40 - EPAISSEUR_PLACAGE, Z_BAT + 40, "50_Heikhal", MAT_OR_PLAQUE())


def lambris_or(piece, x0, x1, col, faces_bout):
    """Ce qui articule une salle plaquée d'or : poutres de caissons sous le plafond,
    corniche et plinthe le long des murs. Le lambris de cèdre (fiche §8b) est derrière
    l'or, « כָּל הַבַּיִת טוּחַ בְּזָהָב » (Middot 4:1) : le relief est d'or lui aussi. Le
    relevé du plan 9b finissait sur un plafond qui n'était qu'un aplat.
    `faces_bout` : les faces est/ouest à ceinturer, (suffixe, xa, xb)."""
    haut = Z_BAT + 40 - EPAISSEUR_PLACAGE
    for k, x in enumerate(plage(x0 + 4, x1 - 2, 4)):
        box(f"{piece}_caisson_poutre_{k:02d}", x - 0.5, x + 0.5, -10 + EPAISSEUR_PLACAGE, 10 - EPAISSEUR_PLACAGE,
            Z_BAT + 39, haut, col, MAT_OR_PLAQUE())
    for k, y in enumerate((-10 / 3, 10 / 3)):
        box(f"{piece}_caisson_longrine_{k}", x0, x1, y - 0.4, y + 0.4, Z_BAT + 39.2, haut, col, MAT_OR_PLAQUE())
    for cote, ya, yb in (("N", 10 - 0.5, 10 - EPAISSEUR_PLACAGE), ("S", -10 + EPAISSEUR_PLACAGE, -10 + 0.5)):
        box(f"{piece}_corniche_{cote}", x0, x1, ya, yb, Z_BAT + 38, Z_BAT + 39, col, MAT_OR_PLAQUE())
        box(f"{piece}_plinthe_{cote}", x0, x1, (ya + yb) / 2 - 0.15, (ya + yb) / 2 + 0.15, Z_BAT, Z_BAT + 0.8, col, MAT_OR_PLAQUE())
    for suffixe, xa, xb in faces_bout:
        box(f"{piece}_corniche_{suffixe}", xa, xb, -10 + 0.5, 10 - 0.5, Z_BAT + 38, Z_BAT + 39, col, MAT_OR_PLAQUE())


lambris_or("Heikhal", HK1, HK0, "50_Heikhal", [("E", HK0 - 0.5, HK0 - EPAISSEUR_PLACAGE)])
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
# Le kaleh orev est fait de pointes, pas d'un bandeau : « spikes with sharp points »
# (Josèphe) — une lisse de bronze sur le maake, et une pointe par ama.
for suffixe, xa, xb, ya, yb in POURTOUR_TOIT:
    box(f"Maake_{suffixe}", xa, xb, ya, yb, Z_TOIT, Z_TOIT + MAAKE_H, "50_Heikhal", MAT_MARBRE_HERODE())
    box(f"Kaleh_orev_{suffixe}", xa, xb, ya, yb, Z_TOIT + MAAKE_H, Z_TOIT + MAAKE_H + 0.15, "50_Heikhal", MAT_BRONZE())
    long_x = (xb - xa) >= (yb - ya)
    a0, a1 = (xa, xb) if long_x else (ya, yb)
    for k, c in enumerate(plage(a0 + 0.5, a1 - 0.5, 1.0)):
        px, py = (c, (ya + yb) / 2) if long_x else ((xa + xb) / 2, c)
        cone(f"Kaleh_orev_{suffixe}_pointe_{k:03d}", px, py, Z_TOIT + MAAKE_H + 0.15, Z_FAITE,
             0.12, 0.0, "50_Heikhal", MAT_BRONZE(), verts=6)

# --- Ustensiles du Heikhal (Yoma 33b ; Menachot 98b) : dans les deux tiers ouest,
#     à 2.5 amot des murs. Table au NORD, Menora au SUD, autel d'or entre les deux, vers l'est.
XU = -125
# Shoul'han 2 × 1 × 1.5, longueur E-O (Rambam Beit HaBe'hira 3:12), à 2,5 amot du mur nord (Yoma 33b)
TEFAH = 1 / 6
YS0, YS1 = 6.5, 7.5
Z_TABLE = Z_BAT + 1.5
# Le'hem hapanim (Rambam Temidin 5:9 ; Mena'hot 94b, 96a) : pain 5 × 6 tefa'him, fond d'un tefa'h,
# deux parois relevées de 7 etzbaot ; deux piles de 6 séparées de 2 tefa'him, 3 kanim entre les pains
H_PAIN, PAS_PAIN = 7 / 4 * TEFAH, 2 * TEFAH


def shulchan(nom, x, avec_pain):
    """Shoul'han 2 × 1 × 1.5, longueur E-O (Rambam Beit HaBe'hira 3:12), à 2,5 amot du mur nord (Yoma 33b)."""
    box(nom, x - 1, x + 1, YS0, YS1, Z_BAT, Z_TABLE, "70_Kelim", MAT_OR())
    if not avec_pain:
        return
    for k in range(2):
        x0 = x - 1 + k * 7 * TEFAH
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


shulchan("Shulchan", XU, avec_pain=True)
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


def gavia(nom, x, y, z, k=1.0):
    """Coupe « comme des calices d'amande » (Shemot 25:33), évasée vers le haut."""
    cone(f"{nom}_gavia", x, y, z, z + 0.14 * k, 0.03 * k, 0.09 * k, "70_Kelim", MAT_OR(), verts=10)


def kaftor(nom, x, y, z, r=0.075):
    sphere(f"{nom}_kaftor", x, y, z, r, "70_Kelim", MAT_OR(), segs=8)


def perach(nom, x, y, z, k=1.0):
    cone(f"{nom}_perach", x, y, z, z + 0.07 * k, 0.05 * k, 0.10 * k, "70_Kelim", MAT_OR(), verts=10)


COUPE_Z = Z_BAT + 3            # lèvre de la coupe
COUPE_HAUT = COUPE_Z + 0.15    # et son bord supérieur


def menora(nom, x, y, allumee):
    """Menora de 3 amot, sept branches dans le plan N-S ; `allumee` : ses sept lampes."""
    # Pied à trois jambes (Rambam, Beit HaBe'hira 3:2 : « וְשָׁלֹשׁ רַגְלַיִם הָיוּ לָהּ ») ; le
    # disque plein d'avant se lisait en socle de statue.
    cyl(f"{nom}_pied", x, y, Z_BAT + 0.05, Z_BAT + 0.30, 0.16, "70_Kelim", MAT_OR(), verts=12)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        cyl_between(f"{nom}_jambe_{k}", (x, y, Z_BAT + 0.18), (x + 0.45 * math.cos(a), y + 0.45 * math.sin(a), Z_BAT + 0.04),
                    0.05, "70_Kelim", MAT_OR(), verts=8)
    cyl_between(f"{nom}_tige", (x, y, Z_BAT + 0.25), (x, y, Z_BAT + 3), 0.08, "70_Kelim")
    # Coupes, boutons et fleurs (Shemot 25:31-36 ; Mena'hot 28b : 22 coupes, 11 boutons,
    # 9 fleurs) : sur la tige, une coupe avec bouton et fleur sous les branches, un bouton
    # sous chaque paire de branches, trois coupes en haut ; sur chaque branche trois
    # coupes, un bouton, une fleur. La tige nue et ses six tubes se lisaient en râteau.
    gavia(f"{nom}_tige_0", x, y, Z_BAT + 0.5)
    kaftor(f"{nom}_tige_0", x, y, Z_BAT + 0.72)
    perach(f"{nom}_tige_0", x, y, Z_BAT + 0.80)
    for k, z in enumerate((2.3, 2.55, 2.8)):
        gavia(f"{nom}_tige_{k + 1}", x, y, Z_BAT + z, 0.85)
    kaftor(f"{nom}_tige_haut", x, y, Z_BAT + 2.22, 0.06)
    perach(f"{nom}_tige_haut", x, y, Z_BAT + 2.93, 0.8)
    coupes = []                    # (suffixe, y) de chaque coupe, pour y poser sa flamme
    for k, h in enumerate([1.2, 1.6, 2.0]):
        d = (3 - k) * 0.35 + 0.35   # écartement des branches
        kaftor(f"{nom}_tige_branches_{k}", x, y, Z_BAT + h, 0.09)
        for s in (-1, 1):
            cote = 'S' if s < 0 else 'N'
            for t, ornement in ((0.40, gavia), (0.58, gavia), (0.76, gavia), (0.88, kaftor), (0.95, perach)):
                ornement(f"{nom}_branche_{k}{cote}_{t:.2f}", x, y + s * d * t, Z_BAT + h + (COUPE_Z - Z_BAT - h) * t,
                         *(() if ornement is kaftor else (0.8,)))
            if MENORA_DROITE:
                cyl_between(f"{nom}_branche_{k}{cote}",
                            (x, y, Z_BAT + h), (x, y + s * d, COUPE_Z), 0.06, "70_Kelim")
            else:   # version "courbe" approximée en deux segments
                cyl_between(f"{nom}_branche_{k}{cote}a",
                            (x, y, Z_BAT + h), (x, y + s * d, Z_BAT + h + 0.15), 0.06, "70_Kelim")
                cyl_between(f"{nom}_branche_{k}{cote}b",
                            (x, y + s * d, Z_BAT + h + 0.15), (x, y + s * d, COUPE_Z), 0.06, "70_Kelim")
            cyl(f"{nom}_coupe_{k}{cote}", x, y + s * d, COUPE_Z, COUPE_HAUT, 0.12, "70_Kelim", MAT_OR())
            coupes.append((f"{k}{cote}", y + s * d))
    cyl(f"{nom}_coupe_centre", x, y, COUPE_Z, COUPE_HAUT, 0.12, "70_Kelim", MAT_OR())
    coupes.append(("centre", y))
    if not allumee:
        return
    # Flammes (lumières) : une petite lampe ponctuelle par coupe, 0,2 ama au-dessus de
    # son milieu. Les coupes se donnent ici en coordonnées et non en relisant leur objet :
    # un volume construit en bpy.data porte sa position dans son maillage, et son
    # `location` vaut zéro.
    for suffixe, yc in coupes:
        l = lampe(f"{nom}_flamme_{suffixe}", 'POINT', (m(x), m(yc), m((COUPE_Z + COUPE_HAUT) / 2 + 0.2)))
        l.data.energy = 15
        l.data.color = (1.0, 0.75, 0.4)
        l.data.shadow_soft_size = m(0.05)
        link_to(l, "70_Kelim")


menora("Menora", XU, YM, allumee=True)

# --- Les deux Parokhot (Yoma 5:1) : extérieure agrafée au SUD, intérieure au NORD
box("Parokhet_ext", TR0 - 0.17, TR0, -10, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_PAROKHET())
box("Parokhet_int", TR1, TR1 + 0.17, -10, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_PAROKHET())
empty("Parokhet_ext_agrafe_SUD", TR0, -9.5, Z_BAT + 20, "60_KodeshHakodashim")
empty("Parokhet_int_agrafe_NORD", TR1, 9.5, Z_BAT + 20, "60_KodeshHakodashim")
# Les badim de l'Arche pressent le rideau et se voient du Heikhal « comme deux seins »
# (Yoma 54a, Menachot 98b, Melakhim I 8:8) : deux demi-sphères de tissu, à la hauteur
# des barres, de part et d'autre de l'axe.
for ns, y in (("N", ARON_Y_BAD), ("S", -ARON_Y_BAD)):
    sphere(f"Parokhet_ext_bosse_{ns}", TR0 - 0.15, y, ARON_Z_BAD, 0.45,
           "60_KodeshHakodashim", MAT_PAROKHET())

# --- Kodesh HaKodashim : même placage. « כל הבית » ne s'arrête pas au Heikhal, et
#     Melakhim I 6:20-22 dore explicitement le devir au Premier Temple. La pièce n'a
#     aucune ouverture et reste noire : l'or n'y rend que sous la braise de la ma'hta —
#     ce qui est exactement la seule lumière du plan 11.
box("KhK_or_mur_N", KK1, KK0, 10 - EPAISSEUR_PLACAGE, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())
box("KhK_or_mur_S", KK1, KK0, -10, -10 + EPAISSEUR_PLACAGE, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())
box("KhK_or_mur_O", KK1, KK1 + EPAISSEUR_PLACAGE, -10, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())
box("KhK_or_plafond", KK1, KK0, -10, 10, Z_BAT + 40 - EPAISSEUR_PLACAGE, Z_BAT + 40, "60_KodeshHakodashim", MAT_OR_PLAQUE())
lambris_or("KhK", KK1, KK0, "60_KodeshHakodashim", [("O", KK1 + EPAISSEUR_PLACAGE, KK1 + 0.5)])
# « וְאֶת קַרְקַע הַבַּיִת צִפָּה זָהָב לִפְנִימָה וְלַחִיצוֹן » (Melakhim I 6:30) : le sol aussi, dans le
# Heikhal et dans le Devir. Deux centièmes d'ama : les kelim s'y posent sans flotter.
box("Heikhal_or_sol", HK1, HK0, -10, 10, Z_BAT, Z_BAT + 0.02, "50_Heikhal", MAT_OR_PLAQUE())
box("KhK_or_sol", KK1, KK0, -10, 10, Z_BAT, Z_BAT + 0.02, "60_KodeshHakodashim", MAT_OR_PLAQUE())


# --- « וְאֵת כָּל קִירוֹת הַבַּיִת מֵסַב קָלַע פִּתּוּחֵי מִקְלְעוֹת כְּרוּבִים וְתִמֹרֹת וּפְטוּרֵי צִצִּים,
#     מִלִּפְנִים וְלַחִיצוֹן » (Melakhim I 6:29) ; Ye'hezkel 41:18-19 donne l'ordre : « וְתִמֹרָה
#     בֵּין כְּרוּב לִכְרוּב, וּשְׁנַיִם פָּנִים לַכְּרוּב ». Middot 4:1 dit l'or sans dire le motif :
#     le relief est d'or, sur l'or, en deux registres, une fleur entre les deux ; un
#     tiers d'ama de saillie — à six centièmes, il ne restait que les arêtes du biseau.
#     Une paroi : (axe le long duquel court `u`, cote de la face, sens de la saillie).
def _relief_boite(nom, paroi, u0, u1, z0, z1, d0, d1, col):
    axe, c, sens = paroi
    if axe == "x":
        box(nom, u0, u1, c + sens * d0, c + sens * d1, z0, z1, col, MAT_OR_PLAQUE())
    else:
        box(nom, c + sens * d0, c + sens * d1, u0, u1, z0, z1, col, MAT_OR_PLAQUE())


def _relief_plaque(nom, paroi, pts_uz, d0, epaisseur, col):
    axe, c, sens = paroi

    def p3(u, z):
        return (u, c + sens * d0, z) if axe == "x" else (c + sens * d0, u, z)

    quad = [p3(u, z) for u, z in pts_uz]
    a, b, d = (Vector(q) for q in (quad[0], quad[1], quad[3]))
    vers = Vector((0, sens, 0)) if axe == "x" else Vector((sens, 0, 0))
    if (b - a).cross(d - a).dot(vers) < 0:
        quad.reverse()
    plaque(nom, quad, epaisseur, col, MAT_OR_PLAQUE())


def _relief_sphere(nom, paroi, u, z, d, r, col):
    axe, c, sens = paroi
    x, y = (u, c + sens * d) if axe == "x" else (c + sens * d, u)
    sphere(nom, x, y, z, r, col, MAT_OR_PLAQUE(), segs=10)


def timora(nom, paroi, u, z0, h, col):
    """« תִּמֹרָה » : tronc et sept palmes en éventail."""
    _relief_boite(f"{nom}_tronc", paroi, u - 0.03 * h, u + 0.03 * h, z0, z0 + 0.58 * h, 0.01, 0.35, col)
    for k, (angle, longueur) in enumerate(((90, 0.42), (65, 0.36), (115, 0.36), (40, 0.28), (140, 0.28), (18, 0.2), (162, 0.2))):
        a = math.radians(angle)
        du, dz = math.cos(a), math.sin(a)
        L, w = longueur * h, 0.08 * h
        base = (u, z0 + 0.55 * h)
        milieu = (base[0] + du * L * 0.45, base[1] + dz * L * 0.45)
        pts = [base, (milieu[0] - dz * w, milieu[1] + du * w), (base[0] + du * L, base[1] + dz * L),
               (milieu[0] + dz * w, milieu[1] - du * w)]
        _relief_plaque(f"{nom}_palme_{k}", paroi, pts, 0.02, 0.28, col)


def keruv_relief(nom, paroi, u, z0, h, col):
    """Keruv à deux visages (Ye'hezkel 41:19) : corps, deux têtes, deux ailes levées."""
    _relief_boite(f"{nom}_corps", paroi, u - 0.06 * h, u + 0.06 * h, z0 + 0.06 * h, z0 + 0.62 * h, 0.01, 0.35, col)
    for k, s in enumerate((-1, 1)):
        _relief_sphere(f"{nom}_visage_{k}", paroi, u + s * 0.045 * h, z0 + 0.70 * h, 0.25, 0.07 * h, col)
        pts = [(u + s * 0.06 * h, z0 + 0.58 * h), (u + s * 0.22 * h, z0 + 0.42 * h),
               (u + s * 0.20 * h, z0 + 0.95 * h), (u + s * 0.09 * h, z0 + 0.80 * h)]
        _relief_plaque(f"{nom}_aile_{k}", paroi, pts, 0.02, 0.28, col)


def petur_tzitz(nom, paroi, u, z, r, col):
    """« פְּטוּרֵי צִצִּים », fleur épanouie : six pétales autour d'un cœur."""
    _relief_sphere(f"{nom}_coeur", paroi, u, z, 0.2, r * 0.3, col)
    for k in range(6):
        a = math.radians(60 * k)
        du, dz = math.cos(a), math.sin(a)
        pts = [(u, z), (u + du * r * 0.5 - dz * r * 0.28, z + dz * r * 0.5 + du * r * 0.28), (u + du * r, z + dz * r),
               (u + du * r * 0.5 + dz * r * 0.28, z + dz * r * 0.5 - du * r * 0.28)]
        _relief_plaque(f"{nom}_petale_{k}", paroi, pts, 0.01, 0.22, col)


REGISTRES = ((Z_BAT + 2, 11), (Z_BAT + 19, 10))     # (bas, hauteur) — sous les fenêtres (31..35)
PAROIS_OR = [
    ("Heikhal_N", ("x", 10 - EPAISSEUR_PLACAGE, -1), HK1, HK0, "50_Heikhal", (0, 1)),
    ("Heikhal_S", ("x", -10 + EPAISSEUR_PLACAGE, 1), HK1, HK0, "50_Heikhal", (0, 1)),
    ("Heikhal_E_S", ("y", HK0 - EPAISSEUR_PLACAGE, -1), -10, -5, "50_Heikhal", (0, 1)),
    ("Heikhal_E_N", ("y", HK0 - EPAISSEUR_PLACAGE, -1), 5, 10, "50_Heikhal", (0, 1)),
    ("Heikhal_E_linteau", ("y", HK0 - EPAISSEUR_PLACAGE, -1), -5, 5, "50_Heikhal", (1,)),
    ("KhK_N", ("x", 10 - EPAISSEUR_PLACAGE, -1), KK1, KK0, "60_KodeshHakodashim", (0, 1)),
    ("KhK_S", ("x", -10 + EPAISSEUR_PLACAGE, 1), KK1, KK0, "60_KodeshHakodashim", (0, 1)),
    ("KhK_O", ("y", KK1 + EPAISSEUR_PLACAGE, 1), -10, 10, "60_KodeshHakodashim", (0, 1)),
]
for nom, paroi, u0, u1, col, registres in PAROIS_OR:
    n = max(1, round((u1 - u0) / 4.44))
    pas = (u1 - u0) / n
    for i in range(n):
        u = u0 + pas * (i + 0.5)
        for r in registres:
            z0, h = REGISTRES[r]
            motif = timora if (i + r) % 2 == 0 else keruv_relief
            motif(f"Kir_{nom}_{i:02d}_{r}", paroi, u, z0, h, col)
        if len(registres) == 2:
            petur_tzitz(f"Kir_{nom}_{i:02d}_tzitz", paroi, u, Z_BAT + 16, 1.0, col)

# « וַיְעַבֵּר בְּרַתּוּקוֹת זָהָב לִפְנֵי הַדְּבִיר » (Melakhim I 6:21) : des chaînes d'or tendues
# devant le Devir. Trois chaînettes sous le plafond, de mur à mur, devant la parokhet.
for k, (creux, z_haut) in enumerate(((3.0, 38.6), (4.5, 37.6), (6.0, 36.6))):
    points = [(TR0 + 0.6, -9.8 + 19.6 * t, Z_BAT + z_haut - creux * (1 - (2 * t - 1) ** 2))
              for t in (i / 24 for i in range(25))]
    for i in range(24):
        cyl_between(f"Devir_chaine_{k}_{i:02d}", points[i], points[i + 1], 0.06, "50_Heikhal", MAT_OR(), verts=6)

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
# 75 — FIGURES
#   De quoi bâtir un corps debout : la silhouette et ce qui distingue sa tenue.
#   Volumes grossiers, qui ne visent pas la ressemblance — ils donnent aux passes
#   Depth/Normal une structure stable, sans laquelle l'i2i réinvente les gens à
#   chaque image et le plan perd sa cohérence temporelle.
#
#   La seule mise en scène que le blockout porte est la foule de la section 76 :
#   l'état permanent du jour. Une figure de premier plan — un cohen au travail, une
#   bête, un ustensile tenu — se pose dans une collection à soi, en appelant ces
#   helpers depuis un script à part, pour que l'export puisse la masquer sans vider
#   la cour.
# ----------------------------------------------------------------------------
H_HOMME = 3.65        # 1.75 m en amot


# Tenues (fiche §12) : le peuple en habits
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
    # Le me'il tombe droit « comme tous les manteaux » et n'a pas de manches (Rambam
    # Klei HaMikdash 9:3) : bras en lin de la kutonet, bas serré pour que l'éphod le frôle.
    evasement = 0.44 * k
    pieces = [
        cone(f"{name}_robe", 0, 0, 0, 0.52 * h, evasement, 0.32 * k, col, corps, verts=12),
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

if FOULE:
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
link_to(sun, "91_Lumiere")
ciel()
(moteur_cycles if "--cycles" in sys.argv else moteur_eevee)()
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

print(f"Blockout terminé : {len(bpy.data.objects)} objets, "
      f"{len(bpy.data.collections)} collections.")
print("Aucune caméra : elles se posent avec beit_hamikdash_cameras.py, depuis cameras.json.")
