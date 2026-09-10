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
from typing import NamedTuple
from mathutils import Matrix, Vector

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

# Appareil : le Temple est bâti d'אַבְנֵי גָזִית, et le Tanakh les mesure —
# « וּמְיֻסָּד אֲבָנִים יְקָרוֹת אֲבָנִים גְּדֹלוֹת אַבְנֵי עֶשֶׂר אַמּוֹת וְאַבְנֵי שְׁמֹנֶה אַמּוֹת »
# (Melakhim I 7:10). Deux longueurs, pas une : le verset les nomme toutes les deux, et
# l'assise en tire une. La pierre de 10 et celle de 8 valent aussi pour le Temple
# lui-même, « וְלַחֲצַר בֵּית ה' הַפְּנִימִית וּלְאֻלָם הַבָּיִת » (7:12). Le module d'une ama qui
# les précédait lisait en brique — quarante rangs sur la façade au lieu de dix blocs.
# La HAUTEUR d'assise n'est dans aucune source : 4 amot est un CHOIX, et le même
# partout. Le pas valait 2,5 pour l'enceinte et 2 pour le bâtiment — cinquante lits sur
# les 100 amot de la façade, l'échelle d'un mur de brique. À 4, une assise vaut le pas
# d'un rovad de l'Oulam (1 de nu + 3 de saillie, Rambam Beit HaBe'hira 4:9) : le haut
# de chaque bandeau tombe sur un lit au lieu de battre contre lui, et le pas unique
# rend la distinction enceinte / bâtiment inutile.
PIERRE_LONG = (8.0, 10.0)   # Melakhim I 7:10 — l'assise tire l'une ou l'autre
ASSISE = 4.0                # CHOIX : hauteur d'assise, hors source
# La face est SCIÉE, pas rustiquée : « אֲבָנִים יְקָרֹת כְּמִדּוֹת גָּזִית מְגֹרָרוֹת בַּמְּגֵרָה
# מִבַּיִת וּמִחוּץ » (Melakhim I 7:9). Tout le relief tient donc au joint et au liseré qui
# le borde, jamais à un bossage éclaté. Largeur du liseré : CHOIX. À 0,35 ama il faisait
# un cadre de dix-sept centimètres autour de chaque bloc, assez large pour se lire en
# bordure rapportée ; 0,25 le ramène à un trait de ciseau.
JOINT = 0.06
LISERE = 0.25
# « אַפֵּיק שָׂפָה וְעַיֵּיל שָׂפָה » (Baba Batra 4a ; Soucca 51b) : une assise déborde, la
# suivante rentre. Le débord n'est chiffré nulle part — CHOIX. Il est plus fort sur le
# bâtiment que sur l'enceinte parce que c'est de SA façade que parle la guemara : là, ce
# relief est ce que les Sages ont préféré à l'or, et il doit porter la vague à lui seul.
DEBORD_ASSISE = 0.05
DEBORD_BATIMENT = 0.11

# Le sol va en RANGÉES, pas en carreaux. « כָּל שׁוּרָה וְשׁוּרָה שֶׁל אַבְנֵי הָרִצְפָּה קְרוּיָה
# רֹבֶד » (Bartenura sur Yoma 4:3), et on les COMPTE en sortant du Heikhal : Yoma 4:3
# pose le ממרס « עַל הָרֹבֶד הָרְבִיעִי שֶׁבָּעֲזָרָה ». Une rangée est donc une bande, et ses
# joints courent nord-sud, en travers de l'axe du bâtiment. Largeur : « וְרֹבֶד אַרְבַּע »
# (Middot 3:6, où Bartenura ad loc. glose le rovad en « שׁוּרַת הָרִצְפָּה »). La longueur
# des dalles dans la rangée n'est nulle part : elles prennent celle des blocs de gazit.
ROVAD_DALLE = 4.0
JOINT_DALLE = 0.05          # le lit entre deux dalles
CREUX_DALLE = 0.015         # 7 mm : un lit de dalle, pas une rainure


# Cinq FINITIONS de taille, tirées par bloc, et la même table que `finition` dans
# visite/matieres.js. Un mur de gazit n'est pas taillé d'une seule main : les pierres
# sortent de bancs différents et passent sous la scie dans le sens où elles se
# présentent. `BANCS_CALCAIRE` donne à un bloc sa COULEUR, ceci lui donne son MOTIF —
# et c'est le motif qui manquait : un parement dont toutes les pierres se moucheturent
# au même pas se lit en papier peint, aussi large que soit sa bande de teintes.
# Aucune n'est un bossage éclaté : « אֲבָנִים יְקָרֹת כְּמִדּוֹת גָּזִית מְגֹרָרוֹת בַּמְּגֵרָה מִבַּיִת
# וּמִחוּץ » (Melakhim I 7:9) — ces faces sont SCIÉES, dedans et dehors. Ce qui change
# d'un bloc au suivant est le banc dont il sort et le lit sur lequel il est passé sous
# la scie, jamais l'outil.
# La PREMIÈRE est le parement d'avant, et reste la référence : le marbre d'Hérode la
# garde sur tous ses blocs — `marbre_herode` ne tire pas, et le bâtiment ne bouge donc
# pas d'un texel.
FINITIONS = (
    #  pas   lit  force couche  fin   strie relief lustre
    (1.5,  1.0,  1.00,  0.0,  0.45, 0.090, 1.00,  0.00),   # sciée debout
    (1.7,  1.0,  1.05,  1.0,  0.50, 0.075, 0.85, -0.03),   # sciée couchée : stries en travers
    (0.9,  1.0,  1.55,  0.0,  0.22, 0.030, 1.60,  0.10),   # piquée : le meleke vacuolaire
    (2.2,  1.0,  0.70,  1.0,  0.32, 0.130, 0.95,  0.02),   # layée au ciseau, en peigne serré
    (2.6,  5.0,  1.45,  0.0,  0.60, 0.045, 1.10, -0.04),   # à banc : la pierre est LITÉE
)

def _finition(mat, tire, colonnes, y):
    """Trois colonnes de `FINITIONS`, aiguillées par le tirage du bloc.

    Une rampe CONSTANT à cinq marches est l'aiguillage d'un arbre de nœuds : les trois
    valeurs voyagent dans les trois canaux d'une couleur, et un Separate les reprend.

    Une couleur de rampe ÉCRÊTE le négatif — mesuré : (-0,04 2,6 5,0) y devient
    (0,0 2,6 5,0), le haut passe et le bas non. Une colonne qui descend sous zéro, comme
    le lustre d'un parement poli, y monte donc en bloc et en redescend à la sortie.
    """
    liens = mat.node_tree.links
    plancher = min(0.0, min(fini[c] for fini in FINITIONS for c in colonnes))
    aiguillage = _noeud(mat, "ShaderNodeValToRGB", -1020, y)
    rampe = aiguillage.color_ramp
    rampe.interpolation = 'CONSTANT'
    marche = 1.0 / len(FINITIONS)
    for k, fini in enumerate(FINITIONS):
        element = rampe.elements[k] if k < 2 else rampe.elements.new(marche * k)
        element.position = marche * k
        element.color = tuple(fini[c] - plancher for c in colonnes) + (1.0,)
    liens.new(tire, aiguillage.inputs["Factor"])
    separe = _noeud(mat, "ShaderNodeSeparateColor", -860, y)
    liens.new(aiguillage.outputs["Color"], separe.inputs["Color"])
    return [_calc(mat, "ADD", separe.outputs[c], plancher)
            for c in ("Red", "Green", "Blue")]


def _grain_tire(mat, pas, lit=None):
    """`_grain`, mais dont le pas — et son étirement sur la verticale — sont TIRÉS.

    `_grain` fige sa taille dans le nœud ; ici elle vient de la finition du bloc, et
    deux pierres voisines ne se moucheturent donc pas au même pas. `lit` comprime ce
    pas sur Z : une pierre LITÉE montre ses strates en bandes en travers de la face.
    """
    liens = mat.node_tree.links
    empiles = sum(1 for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeTexNoise")
    bruit = _noeud(mat, "ShaderNodeTexNoise", -1200, 260 + 220 * empiles)
    bruit.inputs["Detail"].default_value = 6.0
    liens.new(_calc(mat, "DIVIDE", 1.0 / AMA, pas), bruit.inputs["Scale"])
    if lit is None:
        liens.new(_position(mat), bruit.inputs["Vector"])
        return bruit.outputs["Factor"]
    strates = _noeud(mat, "ShaderNodeCombineXYZ", -1560, 260 + 220 * empiles)
    strates.inputs["X"].default_value = 1.0
    strates.inputs["Y"].default_value = 1.0
    liens.new(lit, strates.inputs["Z"])
    etire = _noeud(mat, "ShaderNodeVectorMath", -1400, 260 + 220 * empiles)
    etire.operation = "MULTIPLY"
    liens.new(_position(mat), etire.inputs[0])
    liens.new(strates.outputs["Vector"], etire.inputs[1])
    liens.new(etire.outputs["Vector"], bruit.inputs["Vector"])
    return bruit.outputs["Factor"]


def _module(mat, coordonnee, taille):
    """Découpe une coordonnée de monde en modules de `taille` amot (nombre ou nœud).

    Renvoie (rang, distance au joint le plus proche, en amot). Le rang numérote les
    modules — c'est lui qui tire la teinte d'une assise ou d'un bloc ; la distance
    dessine le joint et le liseré.
    """
    metres = m(taille) if isinstance(taille, (int, float)) else _calc(mat, "MULTIPLY", taille, AMA)
    rang = _calc(mat, "DIVIDE", coordonnee, metres)
    reste = _calc(mat, "FRACT", rang)
    bord = _calc(mat, "MINIMUM", reste, _calc(mat, "SUBTRACT", 1.0, reste))
    return rang, _calc(mat, "MULTIPLY", bord, taille)


def _parement(mat):
    """Les trois lectures d'un point sur une face : sa hauteur, son abscisse LE LONG de
    la face, et à quel point cette face est horizontale.

    L'abscisse suit la normale — Y sur un mur tourné vers l'est ou l'ouest, X sur les
    deux autres. Lue sur X partout, la trame des joints verticaux filerait dans
    l'épaisseur des murs nord-sud au lieu d'en suivre le parement.
    """
    p = _noeud(mat, "ShaderNodeSeparateXYZ", -2100, 0)
    mat.node_tree.links.new(_position(mat), p.inputs["Vector"])
    n = _noeud(mat, "ShaderNodeSeparateXYZ", -2100, -200)
    mat.node_tree.links.new(_normale(mat), n.inputs["Vector"])
    vers_x = _calc(mat, "GREATER_THAN", _calc(mat, "ABSOLUTE", n.outputs["X"]),
                   _calc(mat, "ABSOLUTE", n.outputs["Y"]))
    u = _calc(mat, "MULTIPLY_ADD", _calc(mat, "SUBTRACT", p.outputs["Y"], p.outputs["X"]),
              vers_x, p.outputs["X"])
    return p.outputs["Z"], u, _calc(mat, "ABSOLUTE", n.outputs["Z"])


def _appareil(mat, assise=ASSISE, longueurs=PIERRE_LONG, debord=DEBORD_ASSISE):
    """Taille la surface en blocs de gazit et creuse leur joint et son liseré.

    Deux reliefs, et c'est le profil du bloc : le joint, creusé ; le liseré ciselé qui
    le borde, plat et en léger retrait ; entre les deux le champ de la pierre, scié
    lisse (Melakhim I 7:9). Le liseré est ce qui donne le bloc, et le bloc l'échelle —
    sans lui un mur de 100 amot n'a que des lignes horizontales et se lit en bardage.

    La parité des assises reste le « אבן יוצא ואבן נכנס » de *Baba Batra* 4a : une assise
    en léger débord, la suivante en retrait. C'est ce jeu-là — pas un placage — qui a
    fait renoncer Hérode à dorer le bâtiment, « cela ressemble aux vagues de la mer ».
    D'où `debord`, plus fort sur le bâtiment que sur l'enceinte : c'est de SA façade que
    parle la guemara, et c'est le relief qui doit y porter la vague, pas la teinte.

    Renvoie (parité de l'assise, tirage de l'assise, tirage du bloc, masque du joint,
    tirage de la finition). Le profil du relief ne sort pas : il ne sert qu'aux Bump,
    posés ici.
    """
    z, u, aplat = _parement(mat)
    rang, ecart_z = _module(mat, z, assise)
    numero = _calc(mat, "FLOOR", rang)
    parite = _calc(mat, "MODULO", numero, 2.0)
    tire_assise = _noeud(mat, "ShaderNodeTexWhiteNoise", -1700, 120)
    tire_assise.noise_dimensions = '1D'
    mat.node_tree.links.new(numero, tire_assise.inputs["W"])
    # « אבני עשר אמות ואבני שמנה אמות » : l'assise tire sa longueur de bloc.
    longue = _calc(mat, "GREATER_THAN", tire_assise.outputs["Value"], 0.5)
    longueur = _calc(mat, "MULTIPLY_ADD", longue, longueurs[1] - longueurs[0], longueurs[0])
    # Les joints verticaux se décalent d'une assise à la suivante : alignés, ils font
    # un damier, que ne montre aucun appareil de pierre de taille.
    decal = _calc(mat, "MULTIPLY", _calc(mat, "MULTIPLY_ADD", tire_assise.outputs["Value"], 0.37,
                                         _calc(mat, "MULTIPLY", parite, 0.5)),
                  _calc(mat, "MULTIPLY", longueur, AMA))
    colonne, ecart_u = _module(mat, _calc(mat, "ADD", u, decal), longueur)
    tire_bloc = _noeud(mat, "ShaderNodeTexWhiteNoise", -1700, -80)
    tire_bloc.noise_dimensions = '2D'
    grille = _noeud(mat, "ShaderNodeCombineXYZ", -1860, -80)
    mat.node_tree.links.new(_calc(mat, "FLOOR", colonne), grille.inputs["X"])
    mat.node_tree.links.new(numero, grille.inputs["Y"])
    mat.node_tree.links.new(grille.outputs["Vector"], tire_bloc.inputs["Vector"])
    # La finition se tire À PART du banc. Sur le même tirage, la pierre la plus claire
    # serait toujours la plus piquée : les cinq finitions se liraient en cinq calcaires,
    # et le mur retomberait dans le nuancier qu'on cherche à quitter.
    tire_fini = _noeud(mat, "ShaderNodeTexWhiteNoise", -1700, -280)
    tire_fini.noise_dimensions = '2D'
    decale = _noeud(mat, "ShaderNodeCombineXYZ", -1860, -280)
    mat.node_tree.links.new(_calc(mat, "ADD", _calc(mat, "FLOOR", colonne), 19.0),
                            decale.inputs["X"])
    mat.node_tree.links.new(_calc(mat, "ADD", numero, 7.0), decale.inputs["Y"])
    mat.node_tree.links.new(decale.outputs["Vector"], tire_fini.inputs["Vector"])
    # Une face horizontale — crête de mur, couronnement, marche — n'a ni assise ni
    # joint : le pas y serait lu sur une coordonnée constante, et la face entière
    # tomberait dans un joint ou dans aucun. On l'éloigne donc de tout joint.
    loin = _calc(mat, "MULTIPLY", aplat, 10.0)
    ecart = _calc(mat, "MINIMUM", _calc(mat, "ADD", ecart_z, loin),
                  _calc(mat, "ADD", ecart_u, loin))
    profil = _noeud(mat, "ShaderNodeValToRGB", -1200, -300)
    portee = JOINT + LISERE + 0.15
    rampe = profil.color_ramp
    # Le liseré est en léger retrait, le champ à peine proéminent : 0,62 de la course
    # est descendue dans le joint, et il ne reste que 0,32 pour la marche du bloc, un
    # centimètre au Bump de 0,07 — le creux est aussi profond que le joint est large.
    # À 0,44 le bloc débordait assez pour que le Bump cerne chaque pierre d'un jonc
    # clair — un carrelage, pas un mur.
    rampe.elements[0].position, rampe.elements[0].color = 0.0, (0.0, 0.0, 0.0, 1.0)
    rampe.elements[1].position, rampe.elements[1].color = JOINT / portee, (0.62,) * 3 + (1.0,)
    rampe.elements.new((JOINT + LISERE) / portee).color = (0.68,) * 3 + (1.0,)
    rampe.elements.new((JOINT + LISERE + 0.06) / portee).color = (1.0, 1.0, 1.0, 1.0)
    rapport = _calc(mat, "DIVIDE", ecart, portee)
    mat.node_tree.links.new(rapport, profil.inputs["Factor"])
    # Le JOINT seul, sans le liseré. Le profil sert au relief et court sur toute la
    # bordure ; l'ombre, elle, doit s'arrêter au fond de la rainure — étalée sur le
    # liseré, elle cerne chaque bloc d'un cadre sombre que ne montre aucun mur.
    creux = _noeud(mat, "ShaderNodeValToRGB", -1200, -520)
    creux.color_ramp.elements[0].position = 0.0
    creux.color_ramp.elements[1].position = JOINT * 1.15 / portee
    mat.node_tree.links.new(rapport, creux.inputs["Factor"])
    _creuser(mat, profil.outputs["Color"], 1.0, 0.07)
    _creuser(mat, parite, 0.9, debord)
    # Le grain reste dans le champ de la pierre et s'arrête au liseré, qui est ciselé.
    _creuser(mat, _calc(mat, "MULTIPLY", _grain(mat, 0.45), profil.outputs["Color"]), 0.8, 0.035)
    # Piqûre du calcaire : le meleke est poreux, et sans elle la face sciée rend un
    # plastique lisse dès que le soleil la prend de biais.
    _creuser(mat, _calc(mat, "MULTIPLY", _grain(mat, 0.10), profil.outputs["Color"]), 0.6, 0.012)
    return (parite, tire_assise.outputs["Value"], tire_bloc.outputs["Value"],
            creux.outputs["Color"], tire_fini.outputs["Value"])


# Ce que devient la pierre au fond du joint : plus sombre, et PLUS CHAUDE. Le facteur
# est plus bas dans le bleu que dans le rouge, donc la rainure vire vers l'ocre.
OMBRE_JOINT = (0.72, 0.66, 0.58)


def _ombre_du_joint(mat, teinte, creux):
    """Creuse le joint d'une ombre chaude. Le bump oriente la surface, il ne la salit
    pas, et à mille amot l'ombre propre du joint est tout ce qui reste de l'appareil.

    Elle passait par un multiply vers le NOIR, sur toute la largeur du liseré : deux
    défauts d'un coup. Sous AgX un calcaire assombri sans teinte vire au gris, et le
    mur se retrouvait quadrillé de traits grisâtres — ce qu'aucun mur de pierre ne
    fait. Un joint est de la pierre à l'ombre : il garde la couleur du bloc, en plus
    sombre et plus chaud, et il tient dans la rainure. Le liseré, lui, est de la pierre
    en plein soleil et ne perd rien.
    """
    liens = mat.node_tree.links
    sombre = _noeud(mat, "ShaderNodeMixRGB", -500, -40)
    sombre.blend_type = "MULTIPLY"
    sombre.inputs["Factor"].default_value = 1.0
    sombre.inputs["Color2"].default_value = (*OMBRE_JOINT, 1.0)
    liens.new(teinte, sombre.inputs["Color1"])
    ombre = _noeud(mat, "ShaderNodeMixRGB", -340, 160)
    liens.new(teinte, ombre.inputs["Color1"])
    liens.new(sombre.outputs["Color"], ombre.inputs["Color2"])
    liens.new(_calc(mat, "MULTIPLY_ADD", creux, -1.0, 1.0), ombre.inputs["Factor"])
    return ombre.outputs["Color"]


# Les quatre bancs du calcaire de Jérusalem, en écart multiplicatif sur la teinte de
# base : le meleke n'est pas d'une couleur mais d'une bande. Ce n'est pas qu'une valeur
# qui change d'un bloc au suivant, c'est la teinte — un mur dont les blocs ne diffèrent
# qu'en clarté rend un aplat sali, jamais de la pierre.
#
# La bande va du gris de cendre à l'ivoire, et NON à l'ocre. Le meleke fraîchement
# scié est presque blanc ; le doré des assises d'Hérode est une patine de vingt
# siècles, l'état d'une ruine et non d'un Temple en service. La bande ocre qui les
# précédait (jusqu'à 1,18 0,99 0,89, écrêtée à 1,0 sur le rouge) mettait le pourtour
# dans la teinte du pays et de la ville : l'enceinte, les maisons et la montagne ne se
# séparaient plus, et l'or des six portes (Middot 2:3) n'avait plus rien contre quoi
# être de l'or.
# Un banc reste toutefois plus chaud que froid en absolu — rouge ≥ bleu partout : le
# banc le plus clair est parti une fois à (0,64 0,68 0,76), plus bleu que rouge, et à
# l'ombre, où la seule lumière est celle d'un ciel bleu, il rendait du béton. Ce qui
# change d'un bloc au suivant, c'est de combien il est chaud.
BANCS_CALCAIRE = ((0.86, 0.87, 0.88), (0.94, 0.94, 0.93),
                  (1.02, 1.00, 0.97), (1.10, 1.06, 0.98))

# Ce que la pluie laisse sur un parement, selon qu'on le lave ou non. Le Temple est en
# service et entretenu — le Mizbea'h est blanchi deux fois l'an (Middot 3:4) —, et une
# enceinte entièrement coulée s'y lit en ruine ; la muraille du Har HaBayit et la ville
# ne sont lavées par personne et gardent la pleine coulure. `_exposer` fait la seconde.
COULURE_ENTRETENUE, COULURE_EXPOSEE = 0.08, 0.16


def pierre(name, rgb, assise=ASSISE, longueurs=PIERRE_LONG):
    """Calcaire en assises de blocs sciés.

    Trois échelles de teinte, et il en faut trois. **Le bloc** d'abord : il tire son
    banc dans `BANCS_CALCAIRE`, et c'est lui qui porte l'essentiel — dans un mur de
    gazit, deux pierres voisines diffèrent plus que deux assises. **L'assise** ensuite,
    d'un cheveu, pour que le lit se lise (les « assises légèrement contrastées » de la
    fiche). **Une patine** de trente amot enfin, qui passe par-dessus l'appareil sans
    en suivre le découpage : sans elle un mur reste un aplat quel que soit son
    appareil, parce qu'à la distance où le film le voit l'œil ne lit que les grandes
    taches.
    """
    mat, neuf = _neuf(name, rgb)
    if not neuf:
        return mat
    liens = mat.node_tree.links
    _bsdf(mat).inputs["Roughness"].default_value = 0.78
    parite, _, bloc, creux, fini = _appareil(mat, assise, longueurs)
    teinte = _noeud(mat, "ShaderNodeValToRGB", -700, 160)
    rampe = teinte.color_ramp
    bancs = [tuple(min(1.0, c * e) for c, e in zip(rgb, banc)) + (1.0,)
             for banc in BANCS_CALCAIRE]
    pas = 1.0 / (len(bancs) - 1)
    rampe.elements[0].position, rampe.elements[0].color = 0.0, bancs[0]
    rampe.elements[1].position, rampe.elements[1].color = pas, bancs[1]
    for k, couleur in enumerate(bancs[2:], start=2):
        rampe.elements.new(pas * k).color = couleur
    liens.new(_calc(mat, "MULTIPLY_ADD", parite, 0.10,
                    _calc(mat, "MULTIPLY_ADD", _grain(mat, 30.0), 0.22,
                          _calc(mat, "MULTIPLY", bloc, 0.68))), teinte.inputs["Factor"])
    # Deux coulures, l'une de trois amot de large, l'autre d'une demie. Mesuré : sous
    # AgX, un écart de teinte de 40 % entre deux blocs ne rendait que six centièmes à
    # l'image tant que le soleil était à 4,0 — la courbe est presque plate là-haut, et
    # tout le calcaire au soleil s'y plaçait. C'est ce qui a fait descendre le soleil à
    # 2,2. La règle reste vraie même bien exposé : ce qui va vers le BAS se lit mieux
    # que ce qui va vers le haut, et la pierre se donne d'abord par ses ombres.
    salissure = _noeud(mat, "ShaderNodeMixRGB", -340, 320)
    salissure.blend_type = "MULTIPLY"
    salissure.inputs["Color2"].default_value = (0.0, 0.0, 0.0, 1.0)
    liens.new(teinte.outputs["Color"], salissure.inputs["Color1"])
    coulure = _noeud(mat, "ShaderNodeMapRange", -520, 320)
    coulure.name = "Coulure"
    coulure.inputs["From Min"].default_value = 0.52
    coulure.inputs["From Max"].default_value = 0.88
    coulure.inputs["To Max"].default_value = COULURE_ENTRETENUE
    coulure.clamp = True
    liens.new(_calc(mat, "MULTIPLY_ADD", _trainee(mat, 0.5, 9.0), 0.35,
                    _calc(mat, "MULTIPLY", _trainee(mat, 3.0, 40.0), 0.65)),
              coulure.inputs["Value"])
    liens.new(coulure.outputs["Result"], salissure.inputs["Factor"])
    # Moucheture. Le banc donne au bloc SA couleur, mais un bloc d'une seule couleur est
    # un échantillon de nuancier : le calcaire est nué à l'intérieur de chaque pierre, à
    # une échelle plus courte que la pierre. Ce pas-là est TIRÉ (`FINITIONS`) — c'est lui
    # qui sépare le motif d'une pierre du motif de sa voisine, et il DÉVIE autour d'une
    # moyenne fixe : la teinte reste l'affaire du banc, et cinq finitions qui
    # s'éclairciraient l'une l'autre rendraient cinq calcaires au lieu de cinq tailles.
    pas, lit, force = _finition(mat, fini, (0, 1, 2), 620)
    fin, strie, couche = _finition(mat, fini, (4, 5, 3), 840)
    relief, lustre, _ = _finition(mat, fini, (6, 7, 7), 1060)   # trois canaux, deux colonnes
    grain_fin = _grain_tire(mat, fin)
    mouchete = _noeud(mat, "ShaderNodeMixRGB", -180, 320)
    mouchete.blend_type = "MULTIPLY"
    mouchete.inputs["Color2"].default_value = (*OMBRE_JOINT, 1.0)
    liens.new(salissure.outputs["Color"], mouchete.inputs["Color1"])
    liens.new(_calc(mat, "ADD", 0.14, _calc(mat, "MULTIPLY", force,
                    _calc(mat, "MULTIPLY_ADD", _calc(mat, "SUBTRACT", grain_fin, 0.5), 0.10,
                          _calc(mat, "MULTIPLY", _calc(mat, "SUBTRACT",
                                                       _grain_tire(mat, pas, lit), 0.5), 0.22)))),
              mouchete.inputs["Factor"])
    # La porosité du bloc, au pas de sa moucheture fine : le meleke vacuolaire la porte
    # jusqu'à la face, la pierre sciée fin l'a presque effacée. C'est ce que la visite
    # fait prendre à sa nappe (`Finition.relief`) ; ici c'est un creux de plus.
    _creuser(mat, grain_fin, _calc(mat, "MULTIPLY", relief, 0.30), 0.010)
    # La rugosité se tire par bloc : deux pierres du même banc ne renvoient pas le même
    # soleil rasant, et c'est le spéculaire — pas la teinte — qui les sépare à l'image.
    # S'y ajoute la scie : « מְגֹרָרוֹת בַּמְּגֵרָה מִבַּיִת וּמִחוּץ » (Melakhim I 7:9), et une scie
    # laisse sur le champ des stries parallèles de quatre centimètres de pas. Elles ne
    # sont que du lustre, jamais un relief — un parement scié est plat. Leur SENS est
    # tiré avec la finition : les unes traversent la face, les autres la descendent, et
    # deux voisins qui ne les portent pas dans le même sens sont ce qui sépare un
    # parement bâti d'une trame imprimée sur tout le mur.
    # Les stries sont maintenant CENTRÉES avant d'être dosées — leur force varie d'un
    # bloc à l'autre, et non centrées elles auraient déplacé la moyenne avec elle. La
    # constante remonte donc de 0,575 à 0,62 : c'est la moyenne que `aplatir` emporte
    # dans le .glb, et la visite ajoute ses écarts par-dessus.
    en_travers = _trainee(mat, 30.0, 0.08)
    de_haut_en_bas = _trainee(mat, 0.08, 30.0)
    scie = _calc(mat, "MULTIPLY_ADD", _calc(mat, "SUBTRACT", de_haut_en_bas, en_travers),
                 couche, en_travers)
    liens.new(_calc(mat, "ADD", lustre,
                    _calc(mat, "MULTIPLY_ADD", bloc, 0.18,
                          _calc(mat, "MULTIPLY_ADD", _calc(mat, "SUBTRACT", scie, 0.5), strie,
                                _calc(mat, "MULTIPLY_ADD", _grain(mat, 0.35), 0.16, 0.62)))),
              _bsdf(mat).inputs["Roughness"])
    liens.new(_ombre_du_joint(mat, mouchete.outputs["Color"], creux),
              _bsdf(mat).inputs["Base Color"])
    return mat


# Les trois marbres d'Hérode : « בְּאַבְנֵי כּוּחְלָא, שִׁישָׁא וּמַרְמְרָא » (Baba Batra 4a ; Soucca
# 51b). Rashi les nomme sur place (*ad loc.*) et ce sont trois FROIDS : « שישא — שיש
# ירוק », « מרמרא — שיש לבן », « כוחלא — שיש צבוע כעין כחול » — vert, blanc, bleu.
# Aucune source ne met de jaune sur ce bâtiment ; le troisième marbre en portait un, et
# c'est lui qui faisait lire la façade en assises de brique.
# Saturation très basse : ce que les Sages lui ont fait garder contre l'or, c'est « כִּי
# אִידְווֹתָא דְיַמָּא », le moiré d'une mer — pas une mosaïque.
MARBRES_HERODE = ((0.94, 0.93, 0.89), (0.81, 0.86, 0.86), (0.82, 0.88, 0.78))


def marbre_herode(name):
    """Le corps du bâtiment, en assises alternées de trois marbres.

    C'est la seule surface que les sources refusent explicitement de dorer : Hérode
    voulut la plaquer d'or et les Sages l'en dissuadèrent (*Baba Batra* 4a). Elle porte
    donc la pierre, et l'or reste où *Middot* 4:1 le met — tout l'intérieur du Bayit.

    Le marbre se tire par ASSISE et non par bloc — CHOIX : « בְּאַבְנֵי שֵׁישָׁא כּוּחְלָא
    וּמַרְמְרָא » (*Soucca* 51b ; *Baba Batra* 4a) nomme les trois pierres sans dire
    comment elles se répartissent. Par rangs entiers, elles font les vagues que les
    Sages ont préférées à l'or ; tirées bloc à bloc, elles feraient une mosaïque. Le
    tirage du bloc ne sert plus qu'à nuancer la teinte à l'intérieur du rang.
    """
    mat, neuf = _neuf(name, MARBRES_HERODE[0])
    if not neuf:
        return mat
    liens = mat.node_tree.links
    _bsdf(mat).inputs["Roughness"].default_value = 0.62   # marbre poli, pas calcaire
    # Le marbre ne tire pas de finition : ses trois pierres se posent par assises
    # entières et sa face est reprise jusqu'au poli — il n'y a pas cinq mains dessus.
    _, tire_assise, bloc, creux, _ = _appareil(mat, debord=DEBORD_BATIMENT)
    choix = _noeud(mat, "ShaderNodeValToRGB", -680, 160)
    rampe = choix.color_ramp
    rampe.interpolation = 'CONSTANT'
    rampe.elements[0].position = 0.0
    rampe.elements[0].color = (*MARBRES_HERODE[0], 1.0)
    rampe.elements[1].position = 1.0 / 3.0
    rampe.elements[1].color = (*MARBRES_HERODE[1], 1.0)
    rampe.elements.new(2.0 / 3.0).color = (*MARBRES_HERODE[2], 1.0)
    liens.new(tire_assise, choix.inputs["Factor"])
    veine = _noeud(mat, "ShaderNodeMixRGB", -500, 160)
    veine.blend_type = "MULTIPLY"
    veine.inputs["Factor"].default_value = 1.0
    liens.new(choix.outputs["Color"], veine.inputs["Color1"])
    nuance = _noeud(mat, "ShaderNodeValToRGB", -680, -40)
    nuance.color_ramp.elements[0].color = (0.84, 0.85, 0.88, 1.0)
    nuance.color_ramp.elements[1].color = (1.10, 1.08, 1.02, 1.0)
    liens.new(_calc(mat, "MULTIPLY_ADD", _grain(mat, 24.0), 0.45,
                    _calc(mat, "MULTIPLY", bloc, 0.55)), nuance.inputs["Factor"])
    liens.new(nuance.outputs["Color"], veine.inputs["Color2"])
    liens.new(_ombre_du_joint(mat, veine.outputs["Color"], creux),
              _bsdf(mat).inputs["Base Color"])
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
    """Sol en rangées de dalles — ROVAD_DALLE plus haut pour la source.

    C'est le joint, à la lumière rasante de l'aube, qui donne au dallage sa fuyante :
    sans lui les cours sont un aplat et la perspective ne tient qu'aux murs.

    La valeur ne varie presque pas d'une dalle à l'autre — ±1,5 %, pas plus : à ±5 % il
    ne restait que des taches, que l'œil lisait en relief au lieu d'un pavage. Ce qui
    varie, c'est la COUR : une patine de vingt amot passe par-dessus le pavage sans en
    suivre le découpage, et c'est elle qui empêche l'Azara de rendre un aplat aux plans
    larges, où une dalle ne fait plus deux pixels.
    """
    mat, neuf = _neuf(name, rgb)
    if not neuf:
        return mat
    liens = mat.node_tree.links
    # Une seule usure de vingt amot, lue deux fois : là où la cour est passée, la dalle
    # est plus sombre ET plus lustrée. Le dallage était à 0,85 de rugosité, c'est-à-dire
    # une terrasse de grès ; une dalle foulée pieds nus et lavée à l'eau du Sha'ar
    # HaMayim rend son soleil, et c'est ce lustre — pas la teinte — qui la sépare d'une
    # esplanade.
    usure = _grain(mat, 20.0)
    # La valeur par défaut de l'entrée reste lue quand un lien la recouvre : c'est elle
    # que `aplatir` emporte dans le .glb (beit_hamikdash_visite.py). Elle vaut donc la
    # moyenne du lien, sinon la visite garde un dallage mat que le rendu n'a plus.
    _bsdf(mat).inputs["Roughness"].default_value = 0.51
    liens.new(_calc(mat, "MULTIPLY_ADD", usure, -0.18, 0.60),
              _bsdf(mat).inputs["Roughness"])
    p = _noeud(mat, "ShaderNodeSeparateXYZ", -2100, 0)
    liens.new(_position(mat), p.inputs["Vector"])
    # Les rovadim se comptent en sortant du Heikhal, qui est à l'ouest : les rangées
    # s'empilent donc sur X et chacune court sur Y, d'un bout à l'autre de la cour.
    rang, ecart_x = _module(mat, p.outputs["X"], ROVAD_DALLE)
    numero = _calc(mat, "FLOOR", rang)
    tire_rang = _noeud(mat, "ShaderNodeTexWhiteNoise", -1700, 120)
    tire_rang.noise_dimensions = '1D'
    liens.new(numero, tire_rang.inputs["W"])
    longue = _calc(mat, "GREATER_THAN", tire_rang.outputs["Value"], 0.5)
    longueur = _calc(mat, "MULTIPLY_ADD", longue, PIERRE_LONG[1] - PIERRE_LONG[0],
                     PIERRE_LONG[0])
    # Les joints en travers se décalent d'une rangée à la suivante : alignés, ils
    # feraient une grille, et la rangée cesserait de se lire comme une rangée.
    decal = _calc(mat, "MULTIPLY",
                  _calc(mat, "MULTIPLY_ADD", tire_rang.outputs["Value"], 0.37,
                        _calc(mat, "MULTIPLY", _calc(mat, "MODULO", numero, 2.0), 0.5)),
                  _calc(mat, "MULTIPLY", longueur, AMA))
    colonne, ecart_y = _module(mat, _calc(mat, "ADD", p.outputs["Y"], decal), longueur)
    joint = _noeud(mat, "ShaderNodeValToRGB", -1200, -300)
    joint.color_ramp.elements[0].position = 0.0
    joint.color_ramp.elements[1].position = 1.0
    liens.new(_calc(mat, "DIVIDE", _calc(mat, "MINIMUM", ecart_x, ecart_y), JOINT_DALLE),
              joint.inputs["Factor"])
    tire_dalle = _noeud(mat, "ShaderNodeTexWhiteNoise", -1700, -80)
    tire_dalle.noise_dimensions = '2D'
    grille = _noeud(mat, "ShaderNodeCombineXYZ", -1860, -80)
    liens.new(_calc(mat, "FLOOR", colonne), grille.inputs["X"])
    liens.new(numero, grille.inputs["Y"])
    liens.new(grille.outputs["Vector"], tire_dalle.inputs["Vector"])
    dalle = _noeud(mat, "ShaderNodeValToRGB", -900, 0)
    dalle.color_ramp.elements[0].color = (*(c * 0.985 for c in rgb), 1.0)
    dalle.color_ramp.elements[1].color = (*(min(1.0, c * 1.015) for c in rgb), 1.0)
    liens.new(tire_dalle.outputs["Value"], dalle.inputs["Factor"])
    lit = _noeud(mat, "ShaderNodeMixRGB", -700, -160)
    lit.inputs["Color1"].default_value = (*(c * 0.70 for c in rgb), 1.0)
    liens.new(dalle.outputs["Color"], lit.inputs["Color2"])
    liens.new(joint.outputs["Color"], lit.inputs["Factor"])
    patine = _noeud(mat, "ShaderNodeMixRGB", -700, 0)
    patine.blend_type = "MULTIPLY"
    patine.inputs["Color2"].default_value = (*OMBRE_JOINT, 1.0)
    liens.new(lit.outputs["Color"], patine.inputs["Color1"])
    liens.new(_calc(mat, "MULTIPLY", usure, 0.45), patine.inputs["Factor"])
    liens.new(patine.outputs["Color"], _bsdf(mat).inputs["Base Color"])
    _creuser(mat, joint.outputs["Color"], 1.0, CREUX_DALLE)
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
    """Cèdre des plafonds (« וַיִּסְפֹּן אֶת הַבַּיִת… בָּאֲרָזִים », Melakhim I 6:9) et chêne des
    maltera'ot (Middot 3:7) : le fil court le long de l'axe est-ouest, celui des poutres."""
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
NIMA = 20 / 72   # amot : les 72 נִימִין de Shekalim 8:5 réparties sur les 20 amot de large
# La moyenne des quatre laines, et de combien un cordon s'en écarte. Les quatre teintes
# pures, tirées cordon par cordon, rendaient une neige de télévision : à dix amot un
# cordon fait un pixel, et quatre couleurs saturées tirées au sort par pixel ne se
# fondent pas, elles crépitent. Un fil de 24 brins qui contient les quatre EST de la
# couleur moyenne — ce qui change d'un fil à l'autre n'est que le dosage.
MOYENNE_PAROKHET = tuple(sum(c[k] for c in MATIERES_PAROKHET) / 4 for k in range(3))
ECART_PAROKHET = 0.18
LONGUEUR_DOSAGE = 12   # en nimin : sur quelle longueur le dosage d'un cordon dérive

def parokhet(name, figure=False):
    """Étoffe chinée des quatre matières, et non quatre bandes de couleur.

    « וְעַל שִׁבְעִים וּשְׁתַּיִם נִימִין נֶאֱרֶגֶת, וְעַל כָּל נִימָא וְנִימָא עֶשְׂרִים וְאַרְבָּעָה חוּטִין »
    (Shekalim 8:5), et Rashi Ex. 26:31 : « כָּל מִין וָמִין הָיָה כָפוּל בְּכָל חוּט וָחוּט שִׁשָּׁה
    חוּטִין ». Les quatre laines sont retordues DANS chaque fil : le champ est un pourpre
    changeant où les quatre teintes se lisent de près, pas un drapeau à quatre bandes —
    huit champs de cinq amot rendaient un pavillon national en travers du Devir.

    Un tirage uniforme par cordon donne les quatre laines à parts égales ; une rampe
    posée sur un bruit les aurait pondérées par la loi du bruit. Le cordon des nimin,
    large de 20/72 d'ama, donne au tissu son corps.

    `figure=True` couche ce cordon et remonte le ton : c'est la seconde face d'un
    maassé 'hoshev, « אֲרִיגָה שֶׁל שְׁתֵּי קִירוֹת » (Rashi, ibid.), la même laine lue par son
    autre côté. C'est ce qui fait voir les créatures sans y mettre un fil d'or, qu'Ex.
    26:31 ne donne pas.
    """
    mat, neuf = _neuf(name, tuple(min(1.0, c * (1.35 if figure else 1.0))
                                 for c in MOYENNE_PAROKHET))
    if not neuf:
        return mat
    liens = mat.node_tree.links
    bsdf = _bsdf(mat)
    bsdf.inputs["Roughness"].default_value = 0.90
    bsdf.inputs["Sheen Weight"].default_value = 0.50
    bsdf.inputs["Sheen Roughness"].default_value = 0.45
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    axe = _noeud(mat, "ShaderNodeSeparateXYZ", -1700, 0)
    liens.new(_position(mat), axe.inputs["Vector"])
    chaine, trame = ((axe.outputs["Y"], axe.outputs["Z"]) if not figure
                     else (axe.outputs["Z"], axe.outputs["Y"]))
    cellule = _noeud(mat, "ShaderNodeCombineXYZ", -1400, 0)
    liens.new(_calc(mat, "FLOOR", _calc(mat, "DIVIDE", chaine, m(NIMA))), cellule.inputs["X"])
    liens.new(_calc(mat, "FLOOR", _calc(mat, "DIVIDE", trame, m(NIMA * LONGUEUR_DOSAGE))),
              cellule.inputs["Y"])
    tirage = _noeud(mat, "ShaderNodeTexWhiteNoise", -1200, 0)
    tirage.noise_dimensions = '2D'
    liens.new(cellule.outputs["Vector"], tirage.inputs["Vector"])
    laine = _noeud(mat, "ShaderNodeValToRGB", -1000, 0)
    laine.color_ramp.interpolation = 'CONSTANT'
    laine.color_ramp.elements[0].position = 0.0
    laine.color_ramp.elements[0].color = (*MATIERES_PAROKHET[0], 1.0)
    laine.color_ramp.elements[1].position = 0.25
    laine.color_ramp.elements[1].color = (*MATIERES_PAROKHET[1], 1.0)
    laine.color_ramp.elements.new(0.50).color = (*MATIERES_PAROKHET[2], 1.0)
    laine.color_ramp.elements.new(0.75).color = (*MATIERES_PAROKHET[3], 1.0)
    liens.new(tirage.outputs["Value"], laine.inputs["Factor"])
    dosage = _noeud(mat, "ShaderNodeMixRGB", -840, 0)
    dosage.inputs["Factor"].default_value = ECART_PAROKHET
    dosage.inputs["Color1"].default_value = (*MOYENNE_PAROKHET, 1.0)
    liens.new(laine.outputs["Color"], dosage.inputs["Color2"])
    # Le jour d'une étoffe lourde : un champ d'un ton parfaitement égal se lit peint.
    jour = _noeud(mat, "ShaderNodeMixRGB", -700, 0)
    jour.blend_type = 'MULTIPLY'
    jour.inputs["Color2"].default_value = ((1.20, 1.16, 1.10, 1.0) if figure
                                           else (0.72, 0.68, 0.72, 1.0))
    liens.new(dosage.outputs["Color"], jour.inputs["Color1"])
    liens.new(_grain(mat, 2.5), jour.inputs["Factor"])
    liens.new(jour.outputs["Color"], bsdf.inputs["Base Color"])
    for k, (sens, largeur, force, creux) in enumerate(((chaine, NIMA, 0.6, NIMA * 0.18),
                                                       (trame, NIMA / 3, 0.4, NIMA * 0.07))):
        cordon = _noeud(mat, "ShaderNodeMath", -900, -500 - 200 * k)
        cordon.operation = "SINE"
        liens.new(_calc(mat, "MULTIPLY", sens, 2 * math.pi / m(largeur)), cordon.inputs[0])
        _creuser(mat, cordon.outputs[0], force, creux)
    _creuser(mat, _grain(mat, 0.05), 0.4, 0.008)
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

def _exposer(mat):
    """Rend à un parement la coulure entière : celui-là n'est lavé par personne."""
    mat.node_tree.nodes["Coulure"].inputs["To Max"].default_value = COULURE_EXPOSEE
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

# Le calcaire du pourtour, crème presque neutre : c'est la couleur d'un meleke scié
# de frais, et l'ocre lui vient des bancs (BANCS_CALCAIRE), pas de sa base.
# Il reste SOUS les trois marbres du bâtiment (MARBRES_HERODE, 0,94 / 0,81 / 0,82) :
# à 0,81, ses blocs les plus clairs montaient à 0,89 et le pourtour brillait autant
# que le Bayit — l'échelle des blancs va de la chaux du Mizbea'h au dallage, et le
# bâtiment ne doit jamais y perdre son rang.
CALCAIRE = (0.75, 0.73, 0.70)
MAT_PIERRE = lambda: pierre("Pierre_claire", CALCAIRE)
# La muraille des 500 amot et son soubassement : même pierre que l'Azara, mais
# personne ne la lave — elle garde la coulure entière.
MAT_MURAILLE = lambda: _exposer(pierre("Pierre_muraille", CALCAIRE))
MAT_OR = lambda: metal("Or", (1.0, 0.76, 0.33), 0.3)
MAT_BRONZE = lambda: metal("Bronze", (0.66, 0.44, 0.22), 0.45)
# Le bronze de Nikanor n'est pas celui des ustensiles : tout l'argument de Middot 2:3
# est qu'on ne l'a PAS dorée — « וְיֵשׁ אוֹמְרִים, מִפְּנֵי שֶׁנְּחֻשְׁתָּן מַצְהִיב », parce que son
# cuivre tirait déjà sur l'or. Il se tient donc entre le bronze et l'or, et plus poli
# que le bronze : c'est de sa lumière que vient l'argument.
MAT_NEHOSHET = lambda: metal("Nehoshet_matzhiv", (0.86, 0.63, 0.29), 0.34)
MAT_TERRE_CUITE = lambda: enduit("Terre_cuite", (0.46, 0.25, 0.16))
MAT_SEL = lambda: enduit("Sel", (0.93, 0.93, 0.91))              # Lishkat HaMela'h (Middot 5:3)
MAT_PEAU = lambda: etoffe("Peau", (0.40, 0.26, 0.16))            # peaux salées de la Parva (Middot 5:3)
MAT_KETORET = lambda: enduit("Ketoret", (0.52, 0.38, 0.26))      # sammanim pilés (Keritot 6b)
MAT_CHAUX = lambda: enduit("Chaux_blanche", (0.95, 0.95, 0.92))
MAT_CHAUX_FEU = lambda: enduit_noirci("Chaux_noircie", (0.95, 0.95, 0.92), (Z_AZ + 7.5, Z_AZ + 10.5))
# Le dallage est SOUS les murs en valeur, mais dans LEUR pierre : à 0,57 neutre il
# rendait 62 % de la clarté du parement avec le quart de son chroma, et du côté froid
# du gris — la moitié basse de chaque cadre y passait en dalle de béton sous des murs
# finis. Le rovad est du même meleke que le mur, poli par les pieds et lavé : plus
# sombre, plus chaud, jamais d'une autre roche. Son rang tient sans qu'on l'éteigne —
# à plat sous un soleil de 20°, il ne reçoit déjà qu'un tiers de ce que prend le
# parement, et c'est cette assiette-là qui lui cède la clarté du lin et de la chaux.
MAT_SOL = lambda: dallage("Sol", (0.64, 0.60, 0.53))
MAT_LIN = lambda: etoffe("Lin_blanc", (0.88, 0.87, 0.83))     # bigdei lavan des kohanim
MAT_MARBRE = lambda: marbre("Marbre_blanc", (0.93, 0.92, 0.89))
MAT_MARBRE_HERODE = lambda: marbre_herode("Marbre_Herode")
# L'or des parois est un placage martelé sur de la pierre, pas un ustensile tourné :
# plus mat que la Menora, sinon un mur entier ne rend qu'un point spéculaire.
MAT_OR_PLAQUE = lambda: metal("Or_plaque", (1.0, 0.76, 0.33), 0.4)
MAT_CEDRE = lambda: bois("Cedre", (0.44, 0.25, 0.14))
MAT_CHENE = lambda: bois("Chene", (0.36, 0.25, 0.15))
MAT_CHENE_SCULPTE = lambda: bois_sculpte("Chene_sculpte", (0.36, 0.25, 0.15))
# Le bûcher n'est PAS en chêne : « בְּמֻרְבִּיּוֹת שֶׁל תְּאֵנָה וְשֶׁל אֱגוֹז וְשֶׁל עֵץ שָׁמֶן »
# (Tamid 2:3) — figuier, noyer, pin ; l'olivier et la vigne en sont exclus. Bois sec et
# sombre, là où le chêne des maltera'ot est clair : le même chêne d'un bout à l'autre du
# bûcher était ce qui le faisait lire en palette de bois neuf. Et il ne le reste pas :
# le feu descend, d'où les trois tons du lit du bas au lit du dessus.
MAT_BOIS_MAARAKHA = lambda: bois("Bois_maarakha", (0.17, 0.12, 0.074))
MAT_BOIS_ROUSSI = lambda: bois("Bois_roussi", (0.125, 0.092, 0.062))
MAT_BOIS_CHARBON = lambda: bois("Bois_charbon", (0.050, 0.040, 0.036))
MAT_PAROKHET = lambda: parokhet("Parokhet_tissee")
# Le fil couché des figures : même laine, tissage tourné (Rashi Ex. 26:31).
MAT_PAROKHET_FIGURE = lambda: parokhet("Parokhet_figure", figure=True)
MAT_TERRE = lambda: terre("Terre_Jerusalem")
# La ville, deux tons sous le Temple, et son appareil est domestique : le gazit de
# huit à dix amot (Melakhim I 7:10) est celui de la maison du Roi et du Bayit, pas
# celui d'une maison de Jérusalem. Assise et bloc au moellon.
MAT_MAISON = lambda: _voiler(_exposer(pierre("Maisons", (0.64, 0.55, 0.40), 0.8, (1.5, 2.5))))
# Les colonnes des portiques : un tambour est UNE pierre, et n'a donc pas de joint
# vertical. Une longueur de bloc énorme les supprime ; il ne reste que le lit d'un
# tambour à l'autre. Sur un cylindre, le joint vertical était pire qu'inutile : la face
# choisit son axe sur la normale (`_parement`), qui bascule quatre fois autour du fût,
# et la trame sautait quatre fois par colonne.
MAT_COLONNE = lambda: pierre("Pierre_colonne", CALCAIRE, 1.4, (1e4, 1e4))
MAT_FEUILLAGE = lambda: _voiler(material("Olivier_feuillage", (0.24, 0.30, 0.17)))
MAT_TRONC = lambda: _voiler(material("Olivier_tronc", (0.30, 0.24, 0.17)))
MAT_EAU = lambda: eau("Eau_Kiyor")
MAT_FER = lambda: metal("Fer", (0.30, 0.29, 0.28), 0.6)            # crochets des ninnasin (Middot 3:5)
# Le kaleh orev est du fer AFFÛTÉ — « חַד כְּמוֹ הַסַּיִף » (Rambam sur Middot 4:6), « חַד כְּמִין
# סַיִף » (Bartenura ad loc.) : un tranchant est poli, et le fer voué au Temple sert à
# cela (« בַּרְזֶל… לֹא יִפְחוֹת מֵאַמָּה עַל אַמָּה. לְמַאי חַזְיָא? … לְכָלְיָה עוֹרֵב », Mena'hot 107a).
# Au fer forgé des crochets, l'ama du faîte se lisait en barre noire sur les cent amot
# de la façade ; polie, elle prend le ciel et se lit en arête. La matière ne change pas.
MAT_FER_LAME = lambda: metal("Fer_lame", (0.62, 0.62, 0.63), 0.18)
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

POLICES_HEBREU = ("/System/Library/Fonts/SFHebrew.ttf",
                  "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                  "/System/Library/Fonts/ArialHB.ttc")

def _police_hebreu():
    for chemin in POLICES_HEBREU:
        try:
            return bpy.data.fonts.load(chemin)
        except RuntimeError:
            continue
    print("AVERTISSEMENT : aucune police hébraïque installée — gravures ignorées.")
    return None

def _enrouler(me, rayon):
    """Enroule un maillage plat autour d'un cylindre vertical tangent en son origine.

    x court le long de la ligne, z porte l'épaisseur et regarde le lecteur : la ligne
    s'incurve vers l'arrière et son milieu reste sur la surface.
    """
    for v in me.vertices:
        a = v.co.x / rayon
        v.co.x, v.co.z = (rayon + v.co.z) * math.sin(a), (rayon + v.co.z) * math.cos(a) - rayon


def graver(inscriptions, col, mat=None, taille=0.10, saillie=0.02, courbure=None):
    """Lettres hébraïques en relief, tournées vers l'ouest (amot).

    `inscriptions` : suite de (nom, texte, x, y, z), le point étant le milieu de la
    ligne, posé sur la surface à graver. Le corps est retourné parce que Blender pose
    les glyphes de gauche à droite quel que soit le script.

    `courbure` : rayon du support, quand il est rond. La ligne s'enroule alors autour
    de lui — une ligne plate de deux tiers d'ama sur un tronc qui en fait un de large
    décollerait de quatre centimètres à ses extrémités.
    """
    police = _police_hebreu()
    if police is None:
        return
    textes = []
    for nom, texte, x, y, z in inscriptions:
        cu = bpy.data.curves.new(f"{nom}_texte", 'FONT')
        cu.body, cu.font = texte[::-1], police
        cu.size, cu.extrude = m(taille), m(saillie)
        cu.align_x, cu.align_y = 'CENTER', 'CENTER'
        o = _objet(f"{nom}_texte", cu, col, mat)
        o.location = (m(x), m(y), m(z))
        o.rotation_euler = (math.pi / 2, 0.0, -math.pi / 2)
        textes.append((nom, o))
    deps = bpy.context.evaluated_depsgraph_get()
    for nom, o in textes:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(deps))
        me.name = nom
        if courbure is not None:
            _enrouler(me, m(courbure))
        matrice = o.matrix_world.copy()
        bpy.data.objects.remove(o)
        _objet(nom, me, col, None if me.materials else mat).matrix_world = matrice

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

def limbe(name, contour, base, axe, plan, taille, epaisseur, col, mat=None, courbure=0.0):
    """Lame mince à contour libre : feuille, pétale, fleuron.

    `contour` : un demi-profil (u le long de la nervure, v en travers, u croissant),
    déplié symétriquement — une plaque, mais qui a le droit d'avoir des lobes.
    `base` l'attache, `axe` la nervure, `plan` la face vers laquelle elle regarde,
    `courbure` le creux en gouttière, au carré de l'écart à la nervure.
    """
    d = Vector(axe).normalized()
    t = d.cross(Vector(plan)).normalized()
    n = t.cross(d).normalized()
    o = Vector(base)

    def point(u, v):
        return o + taille * (u * d + v * t + courbure * 4 * v * v * n)

    lignes = [[point(u, j * v) for j in (-1, 0, 1)] for u, v in contour]
    N = len(lignes)
    verts = [tuple(p) for ligne in lignes for p in ligne]
    verts += [tuple(p + n * epaisseur) for ligne in lignes for p in ligne]

    def i(couche, k, j):
        return couche * 3 * N + 3 * k + j

    faces = []
    for k in range(N - 1):
        for j in (0, 1):
            faces.append([i(0, k, j), i(0, k, j + 1), i(0, k + 1, j + 1), i(0, k + 1, j)][::-1])
            faces.append([i(1, k, j), i(1, k, j + 1), i(1, k + 1, j + 1), i(1, k + 1, j)])
        for j in (0, 2):
            faces.append([i(0, k, j), i(0, k + 1, j), i(1, k + 1, j), i(1, k, j)])
    return mesh_from_pydata(name, verts, faces, col, mat)

# --- Relief d'une paroi -------------------------------------------------------------
# « פִּתּוּחֵי מִקְלְעוֹת » (Melakhim I 6:29), et « וְצִפָּה זָהָב מְיֻשָּׁר עַל־הַמְּחֻקֶּה » (6:35) :
# la figure est creusée, et l'or épouse le creusé. Une paroi se donne en (axe le long
# duquel court `u`, cote de la face, sens de la saillie) ; tout ce qui suit se trace
# dans le plan (u, z) de cette paroi et sort d'elle.

def _repere(paroi):
    """(point(u, z, saillie), direction de u, normale sortante) d'une paroi."""
    axe, c, sens = paroi
    if axe == "x":
        return (lambda u, z, d: Vector((u, c + sens * d, z))), Vector((1, 0, 0)), Vector((0, sens, 0))
    return (lambda u, z, d: Vector((c + sens * d, u, z))), Vector((0, 1, 0)), Vector((sens, 0, 0))


def _relief_profil(nom, paroi, contour, d0, d1, col, mat=None):
    """Un contour libre tracé dans le plan de la paroi, sorti d'elle de `d0` à `d1`.

    Une silhouette d'un seul tenant, et non un assemblage de plaques rectangulaires :
    c'est le contour qui fait lire la figure, et c'est lui que la passe Normal donne au
    styliseur. Le contour a le droit d'être concave — l'orientation se prend sur l'aire
    entière, qu'un test au premier sommet donnerait à l'envers sur une corolle.
    """
    point, _, normale = _repere(paroi)
    fond = [point(u, z, d0) for u, z in contour]
    aire = Vector((0.0, 0.0, 0.0))
    for k in range(1, len(fond) - 1):
        aire += (fond[k] - fond[0]).cross(fond[k + 1] - fond[0])
    if aire.dot(normale) < 0:
        fond.reverse()
    n = len(fond)
    saillie = normale * (d1 - d0)
    verts = [tuple(p) for p in fond] + [tuple(p + saillie) for p in fond]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]
    return mesh_from_pydata(nom, verts, faces, col, mat or MAT_OR_PLAQUE())


def _relief_limbe(nom, paroi, u, z, inclinaison, longueur, contour, epaisseur, col, mat=None,
                  courbure=0.0):
    """Une lame attachée en (u, z) et penchée de `inclinaison` degrés sur la verticale,
    positive vers les u croissants : palme d'une timora, aile d'un keruv."""
    point, du, normale = _repere(paroi)
    a = math.radians(inclinaison)
    axe = du * math.sin(a) + Vector((0.0, 0.0, 1.0)) * math.cos(a)
    return limbe(nom, contour, point(u, z, 0.01), axe, normale, longueur, epaisseur,
                 col, mat or MAT_OR_PLAQUE(), courbure)


def _relief_bosse(nom, paroi, u, z, d, r, col, mat=None):
    """Un bouton en relief : cœur d'un fleuron, pommeau, mufle."""
    point, _, _ = _repere(paroi)
    p = point(u, z, d)
    return sphere(nom, p.x, p.y, p.z, r, col, mat or MAT_OR_PLAQUE(), segs=10)


# Le profil d'une tête, museau vers +u, origine à l'attache du cou : crâne, nuque,
# gorge, mâchoire, museau, chanfrein, front. Un ovale paramétré rendait deux pièces de
# monnaie posées sur les épaules — une tête se lit à sa nuque et à son museau, pas à
# son ovale.
PROFIL_TETE = ((1.35, 0.10), (1.25, -0.15), (0.75, -0.30), (0.15, -0.42), (-0.55, -0.35),
               (-0.90, 0.05), (-0.80, 0.55), (-0.35, 0.85), (0.35, 0.88), (0.90, 0.62),
               (1.20, 0.35))


def _profil_tete(u, z, taille, sens):
    """Contour d'une tête de profil, museau vers `sens`, SANS AUCUN TRAIT.

    Ye'hezkel 41:19 donne « פְּנֵי אָדָם » d'un côté et « פְּנֵי כְפִיר » de l'autre ; §9 de la
    fiche interdit le visage humain. Une silhouette sans œil ni bouche tient les deux —
    le verset est lu, aucun visage n'est figuré.
    """
    return [(u + sens * taille * du, z + taille * dz) for du, dz in PROFIL_TETE]


def _profil_corolle(u, z, r, lobes=8):
    """Contour d'une fleur épanouie : `lobes` pétales autour d'un cœur. Sert aussi de
    crinière — une crinière de lion est une corolle."""
    return [(u + rk * math.cos(a), z + rk * math.sin(a))
            for a, rk in ((a, r * (0.60 + 0.40 * abs(math.cos(lobes * a / 2)) ** 0.65))
                          for a in (2 * math.pi * k / (lobes * 8) for k in range(lobes * 8)))]


# Demi-profils des lames, dépliés par `limbe` : le long de la nervure, puis en travers.
PALME = ((0.0, 0.045), (0.16, 0.150), (0.48, 0.195), (0.78, 0.135), (1.0, 0.0))
AILE = ((0.0, 0.100), (0.22, 0.215), (0.55, 0.240), (0.82, 0.155), (1.0, 0.0))

# --- Les trois figures gravées du Bayit, et le palmier de tous ses jambages :
#     « כְּרוּבִים וְתִמֹרֹת וּפְטוּרֵי צִצִּים » (Melakhim I 6:29 pour les parois, 6:32 et 6:35
#     pour les vantaux). Ye'hezkel 41:18-19 donne l'ORDRE dans lequel elles alternent —
#     « וְתִמֹרָה בֵּין כְּרוּב לִכְרוּב, וּשְׁנַיִם פָּנִים לַכְּרוּב », chaque profil tourné vers la
#     timora qui le jouxte.
#     La timora ne sert pas qu'au Bayit : « וְתִמֹרִים אֶל־אֵילָיו, אֶחָד מִפּוֹ וְאֶחָד מִפּוֹ »
#     (Ye'hezkel 40:26, 31, 34, 37) en met une sur CHAQUE jambage de porte, et c'est le
#     seul ornement que les sources donnent aux baies des cours. D'où sa place ici, dans
#     la bibliothèque, et non dans la section du Heikhal où elle est née.
BANDEAU_KIR = 0.55        # hauteur d'un bandeau, en amot
SAILLIE_KIR = 0.22        # saillie du relief : 11 cm. À 0,35 la figure se lisait en plaque
                          # posée dessus, à 0,14 elle ne prenait plus la lumière rasante
PAS_KIR = 4.44            # pas visé d'une figure, en amot

# Les palmes d'une timora : (inclinaison sur la verticale, longueur en part de la
# hauteur). Sept est un CHOIX — la source ne les compte pas ; les deux dernières
# retombent, ce qui est ce qui distingue un palmier d'un éventail.
PALMES = ((0, 0.42), (30, 0.37), (-30, 0.37), (66, 0.30), (-66, 0.30), (106, 0.26), (-106, 0.26))


def timora(nom, paroi, u, z0, h, col, mat=None):
    """« תִּמֹרָה » : le palmier — fût annelé, couronne de sept palmes.

    Sur l'or du Bayit elle est dorée et `mat` reste vide ; sur le jambage d'une porte
    du Har HaBayit, que nulle source ne dore, elle se taille dans la pierre du mur.
    """
    fut, e = 0.58 * h, 0.052 * h
    gauche, droite = [], []
    for k in range(9):
        z = z0 + fut * k / 8
        w = e * (1.0 - 0.22 * k / 8) * (1.0 if k % 2 == 0 else 0.74)
        gauche.append((u - w, z))
        droite.append((u + w, z))
    _relief_profil(f"{nom}_fut", paroi, gauche + droite[::-1], 0.0, SAILLIE_KIR, col, mat)
    for k, (inclinaison, longueur) in enumerate(PALMES):
        _relief_limbe(f"{nom}_palme_{k}", paroi, u, z0 + fut * 0.94, inclinaison, longueur * h,
                      PALME, SAILLIE_KIR * 0.45, col, mat, courbure=0.10)
    _relief_bosse(f"{nom}_coeur", paroi, u, z0 + fut * 0.97, SAILLIE_KIR * 0.35, 0.045 * h,
                  col, mat)


def keruv_grave(nom, paroi, u, z0, h, col):
    """« כְּרוּבִים » — « וּשְׁנַיִם פָּנִים לַכְּרוּב » (Ye'hezkel 41:18), et 41:19 tourne chaque
    profil vers la timora qui le jouxte. Deux têtes SANS TRAITS, deux ailes levées."""
    corps = [(u - 0.150 * h, z0), (u + 0.150 * h, z0),
             (u + 0.105 * h, z0 + 0.10 * h), (u + 0.060 * h, z0 + 0.34 * h),
             (u + 0.140 * h, z0 + 0.54 * h), (u + 0.120 * h, z0 + 0.62 * h),
             (u - 0.120 * h, z0 + 0.62 * h), (u - 0.140 * h, z0 + 0.54 * h),
             (u - 0.060 * h, z0 + 0.34 * h), (u - 0.105 * h, z0 + 0.10 * h)]
    _relief_profil(f"{nom}_corps", paroi, corps, 0.0, SAILLIE_KIR, col)
    for sens in (-1, 1):
        cote = "N" if sens > 0 else "S"
        _relief_profil(f"{nom}_tete_{cote}", paroi,
                       _profil_tete(u + sens * 0.100 * h, z0 + 0.62 * h, 0.095 * h, sens),
                       0.0, SAILLIE_KIR * 0.85, col)
        _relief_limbe(f"{nom}_aile_{cote}", paroi, u + sens * 0.075 * h, z0 + 0.52 * h,
                      sens * 32, 0.40 * h, AILE, SAILLIE_KIR * 0.45, col, courbure=0.16)


def petur_tzitz(nom, paroi, u, z, r, col):
    """« פְּטוּרֵי צִצִּים » : la fleur épanouie. Le verset la met au même rang que les
    keruvim et les timorot — elle court donc en bandeau, elle n'est pas un bouton isolé."""
    _relief_profil(f"{nom}_corolle", paroi, _profil_corolle(u, z, r), 0.0, SAILLIE_KIR * 0.55, col)
    _relief_bosse(f"{nom}_coeur", paroi, u, z, SAILLIE_KIR * 0.5, r * 0.28, col)


def bandeau_fleurons(nom, paroi, u0, u1, z, col):
    """Un bandeau de fleurons en travers d'une paroi : ce qui tient les registres.
    Sans lui, les figures flottaient sur un aplat d'or sans une ligne pour les poser."""
    _relief_profil(f"{nom}_listel", paroi,
                   [(u0, z), (u1, z), (u1, z + BANDEAU_KIR), (u0, z + BANDEAU_KIR)],
                   0.0, SAILLIE_KIR * 0.4, col)
    n = max(1, round((u1 - u0) / PAS_KIR))
    pas = (u1 - u0) / n
    for i in range(n):
        petur_tzitz(f"{nom}_fleuron_{i:02d}", paroi, u0 + pas * (i + 0.5), z + BANDEAU_KIR / 2,
                    BANDEAU_KIR * 0.42, col)


REGISTRES_VANTAIL = 3     # figures empilées sur un vantail : « תמרה בין כרוב לכרוב »


def vantail_sculpte(nom, paroi, u0, u1, z0, z1, col):
    """« כְּרוּבִים וְתִמֹרֹת וּפְטוּרֵי צִצִּים » sur un vantail, et de l'or par-dessus le creusé —
    « וְצִפָּה זָהָב מְיֻשָּׁר עַל הַמְּחֻקֶּה » (Melakhim I 6:32 et 6:35). Ye'hezkel 41:25 le redit
    des portes du Heikhal, « כַּאֲשֶׁר עֲשׂוּיִם לַקִּירוֹת » : les mêmes figures que les parois.

    Un vantail est haut et étroit là où une paroi est large : la file de figures y monte
    au lieu de courir. Ce qui tient, c'est l'ALTERNANCE — « וְתִמֹרָה בֵּין כְּרוּב לִכְרוּב »
    (Ye'hezkel 41:18), une timora entre deux keruvim, quel que soit le sens de la file.
    """
    registre = (z1 - z0 - BANDEAU_KIR) / REGISTRES_VANTAIL
    for r in range(REGISTRES_VANTAIL + 1):
        bandeau_fleurons(f"{nom}_{r}", paroi, u0, u1, z0 + r * registre, col)
    for r in range(REGISTRES_VANTAIL):
        motif = keruv_grave if r % 2 == 0 else timora
        motif(f"{nom}_{r}", paroi, (u0 + u1) / 2, z0 + r * registre + BANDEAU_KIR,
              registre - BANDEAU_KIR, col)


def revolution(name, x, y, z0, profil, col="20_Azara", mat=None, verts=32, capots=True):
    """Surface de révolution autour de la verticale passant par (x, y).

    `profil` : suite de (rayon, hauteur au-dessus de z0) en amot, parcourue dans
    l'ordre. Un rayon nul fait une pointe. Se lit paroi extérieure en montant puis,
    si elle redescend, paroi intérieure en descendant : c'est ce sens de parcours qui
    garde les normales tournées vers l'air, dehors comme dans le creux.

    `capots=False` : profil refermé sur lui-même — un bandeau creux, ouvert en haut
    comme en bas, que les deux disques d'extrémité boucheraient.
    """
    anneaux = [_cercle(x, y, r, verts) if r else [(x, y)] for r, _ in profil]
    sommets, debut = [], []
    for (_, dz), anneau in zip(profil, anneaux):
        debut.append(len(sommets))
        sommets += [(px, py, z0 + dz) for px, py in anneau]
    faces = []
    if capots and len(anneaux[0]) > 1:
        faces.append(list(range(verts))[::-1])
    if capots and len(anneaux[-1]) > 1:
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
    """Colonne de portique : base, fût, chapiteau évasé. « הַר הַבַּיִת סְטָיו כָּפוּל הָיָה…
    סְטָיו לִפְנִים מִסְּטָיו » (Pesa'him 13b) — la colonnade double de l'esplanade ; le profil
    est un CHOIX, la guemara n'en donne pas.
    Un fût nu ne donnait ni assise au sol ni rupture de silhouette en haut
    de cadre — les deux choses qu'un travelling de colonnade (plan 2) fait voir
    défiler, et les deux qui entrent dans la passe Depth."""
    mat = mat or MAT_COLONNE()
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

def rampe(name, x0, x1, y0, y1, z0, z1, montee, col, mat=None, epaisseur=1.0):
    """Dalle inclinée d'épaisseur constante. `montee` : '+x', '-x', '+y' ou '-y'.

    `wedge_ramp` fait un coin plein qui monte selon y — bon pour le kevesh, qui est un
    remblai. La messiba est un plancher qui tourne : il lui faut une dalle, et les quatre
    sens.
    """
    axe, sens = montee[1], 1 if montee[0] == "+" else -1
    a0, a1 = (x0, x1) if axe == "x" else (y0, y1)

    def zc(x, y):
        t = ((x if axe == "x" else y) - a0) / (a1 - a0)
        return z0 + (t if sens > 0 else 1 - t) * (z1 - z0)

    coins = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    bas = [(x, y, zc(x, y)) for x, y in coins]
    verts = bas + [(x, y, z + epaisseur) for x, y, z in bas]
    faces = [[0, 1, 2, 3][::-1], [4, 5, 6, 7],
             [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return mesh_from_pydata(name, verts, faces, col, mat)


def mur_perce(name, x0, x1, y0, y1, z0, z1, col, portes, h_porte, mat=None):
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
            box(f"{name}_{suffixe}", u0, u1, y0, y1, zb, zh, col, mat)
        else:
            box(f"{name}_{suffixe}", x0, x1, u0, u1, zb, zh, col, mat)

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
# Écart entre deux corps voisins, pris de nu à nu : leurs socles se manquent alors
# d'une ama. À corps plus rapprochés les deux débords s'interpénètrent et leurs faces
# supérieures, coplanaires, clignotent — ce qui arrivait entre la Lishkat Parhedrin et
# le corps de porte de Sha'ar HaMayim.
ECART_LISHKA = 2 * LISHKA_DEBORD + 1
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


def dalle_percee(name, x0, x1, y0, y1, z0, z1, col, mat, tremies=(), alignees="x"):
    """Dalle horizontale percée de trémies `(tx0, tx1, ty0, ty1)`.

    `paroi_percee` ouvre des baies dans un mur debout ; il faut ici percer un plancher,
    et les trous ne descendent pas jusqu'à un bord comme le fait une porte.
    `alignees` dit sur quel axe les trémies se suivent — la dalle se coupe en bandes sur
    cet axe, et chaque bande s'ouvre sur l'autre. Deux trémies qui se chevauchent sur
    l'axe des bandes se recouvriraient : les distribuer sur l'axe où elles se suivent.
    """
    if not tremies:
        box(name, x0, x1, y0, y1, z0, z1, col, mat)
        return
    en_x = alignees == "x"
    a0, a1 = (x0, x1) if en_x else (y0, y1)
    b0, b1 = (y0, y1) if en_x else (x0, x1)

    def pose(suffixe, u0, u1, v0, v1):
        if u1 - u0 <= 0 or v1 - v0 <= 0:
            return
        coord = (u0, u1, v0, v1) if en_x else (v0, v1, u0, u1)
        box(f"{name}_{suffixe}", *coord, z0, z1, col, mat)

    trous = sorted((t[0], t[1], t[2], t[3]) if en_x else (t[2], t[3], t[0], t[1])
                   for t in tremies)
    bord = a0
    for k, (ta0, ta1, tb0, tb1) in enumerate(trous):
        assert ta0 >= bord, f"{name}: trémies qui se chevauchent sur l'axe {alignees}"
        pose(f"bande_{k}", bord, ta0, b0, b1)
        pose(f"avant_{k}", ta0, ta1, b0, tb0)
        pose(f"apres_{k}", ta0, ta1, tb1, b1)
        bord = ta1
    pose("bande_fin", bord, a1, b0, b1)


def couches_middot(name, x0, x1, y0, y1, zbas, col, tremies=()):
    """Les cinq amot qui séparent deux niveaux du bâtiment (Middot 4:6).

    אַמָּה כִּיּוּר, אַמָּתַיִם בֵּית דִּלְפָה, אַמָּה תִּקְרָה, אַמָּה מַעֲזִיבָה. Bartenura ad loc. : le כיור
    est la poutre basse d'une ama, ciselée et dorée, d'où son nom ; le בית דלפה les deux
    amot au-dessus, laissées vides pour recevoir le dégât d'eau (Rambam, Beit HaBe'hira
    4:2, « שֶׁיִּכָּנֵס בּוֹ הַדֶּלֶף ») ; la תקרה les planches ; la מעזיבה le blocage qui les couvre
    et fait le sol du niveau suivant.
    """
    dalle_percee(f"{name}_kiyour", x0, x1, y0, y1, zbas, zbas + 1, col, MAT_CEDRE(), tremies)
    dalle_percee(f"{name}_tikra", x0, x1, y0, y1, zbas + 3, zbas + 4, col, MAT_CEDRE(), tremies)
    dalle_percee(f"{name}_maaziva", x0, x1, y0, y1, zbas + 4, zbas + 5, col, MAT_MARBRE_HERODE(), tremies)


class Porte(NamedTuple):
    """Baie d'une lishka. `seuil` : le sol qu'elle dessert ; `centre` : sa cote le long de
    la face, le milieu du mur par défaut ; `metal` : ce dont un שער a été changé."""
    face: str
    largeur: float
    hauteur: float
    seuil: float
    centre: float | None = None
    metal: bpy.types.Material | None = None


def _bandes(x0, x1, y0, y1, dedans, dehors, adossee):
    """Pourtour d'une emprise en bandes par face, de `dehors` hors du nu à `dedans` en retrait.

    Les bandes est et ouest s'arrêtent entre celles du nord et du sud : prolongées, leurs
    faces seraient coplanaires avec elles. La face `adossee` n'en reçoit pas, et ses deux
    voisines s'arrêtent à son nu.
    """
    hors = {f: 0 if f == adossee else dehors for f in "OE"}
    retrait = {f: 0 if f == adossee else dedans for f in "SN"}
    bandes = {"S": (x0 - hors["O"], x1 + hors["E"], y0 - dehors, y0 + dedans),
              "N": (x0 - hors["O"], x1 + hors["E"], y1 - dedans, y1 + dehors),
              "O": (x0 - dehors, x0 + dedans, y0 + retrait["S"], y1 - retrait["N"]),
              "E": (x1 - dedans, x1 + dehors, y0 + retrait["S"], y1 - retrait["N"])}
    bandes.pop(adossee, None)
    return bandes


def lishka(name, x0, x1, y0, y1, z0, z1, col, portes, adossee=None, mat=None):
    """Chambre du pourtour, creuse : socle, murs percés de baies, bandeau, corniche qui la couvre.

    Posée en boîte nue, une lishka ne se lit pas : à 750 amot elle n'a ni pied, ni
    sommet, ni ombre sur elle-même, et le styliseur en fait un rocher. Les trois
    lignes en saillie donnent l'assise et le couronnement, les baies l'échelle.

    `portes` : des `Porte`. Chacune s'ouvre à son seuil, et le socle s'ouvre avec elle
    quand ce seuil est plus bas que lui. Le sol intérieur n'est pas bâti ici : il dépend
    de ce que la chambre enjambe. `adossee` : la face collée à un mur d'enceinte, qui lui
    sert de mur — ni parement, ni socle, ni saillie.
    """
    zs, zc = z0 + LISHKA_SOCLE, z1 - LISHKA_CORNICHE
    d = LISHKA_PAREMENT
    portes = [p._replace(hauteur=min(p.hauteur, zc - p.seuil - LISHKA_BANDEAU - 1)) for p in portes]
    z_bandeau = max((p.seuil + p.hauteur for p in portes), default=zs + PORTE_LISHKA[1]) + 1
    murs = _bandes(x0, x1, y0, y1, d, 0, adossee)

    def le_long(face, bornes):
        return (bornes[0], bornes[1]) if face in "SN" else (bornes[2], bornes[3])

    def centre(porte):
        if porte.centre is not None:
            return porte.centre
        return sum(le_long(porte.face, murs[porte.face])) / 2

    for face, bornes in _bandes(x0, x1, y0, y1, d, LISHKA_DEBORD, adossee).items():
        passages = [(centre(p) - p.largeur / 2, centre(p) + p.largeur / 2, p.seuil, zs)
                    for p in portes if p.face == face and p.seuil < zs]
        paroi_percee(f"{name}_socle_{face}", *bornes, z0, zs, col, mat, passages)
    pourtour = _bandes(x0, x1, y0, y1, 0, LISHKA_DEBORD, adossee)
    for face, bornes in pourtour.items():
        box(f"{name}_bandeau_{face}", *bornes, z_bandeau, z_bandeau + LISHKA_BANDEAU, col, mat)
    enveloppe = [plus(b[i] for b in pourtour.values())
                 for plus, i in ((min, 0), (max, 1), (min, 2), (max, 3))]
    box(f"{name}_corniche", *enveloppe, zc, z1, col, mat)

    haut_bandeau = z_bandeau + LISHKA_BANDEAU
    z_baie0 = haut_bandeau + (zc - haut_bandeau) * 0.25
    z_baie1 = haut_bandeau + (zc - haut_bandeau) * 0.75
    for face, bornes in murs.items():
        a0, a1 = le_long(face, bornes)
        baies = []
        for p in portes:
            if p.face != face:
                continue
            c = centre(p)
            baies.append((c - p.largeur / 2, c + p.largeur / 2, max(p.seuil, zs), p.seuil + p.hauteur))
            # Le cadre s'arrête sous le bandeau, qui lui sert de corniche et court sur toute
            # la façade. Plus étroit que celui d'un שער de l'Azara : sur une face de vingt
            # amot, un chambranle de trois mangerait le trumeau.
            shaar(f"{name}_{face}_cadre",
                  {"S": ("x", y0, -1), "N": ("x", y1, 1),
                   "O": ("y", x0, -1), "E": ("y", x1, 1)}[face],
                  c, p.seuil, min(z_bandeau, p.seuil + p.hauteur + 1), d, col, mat,
                  metal=p.metal, largeur=p.largeur, hauteur=p.hauteur, cadre=min(2.0, p.largeur / 4))
        n = max(2, round((a1 - a0) / 12))
        for k in range(n) if z_baie1 - z_baie0 >= 2 else ():
            c = a0 + (a1 - a0) * (k + 0.5) / n
            u0, u1 = c - LISHKA_BAIE / 2, c + LISHKA_BAIE / 2
            if any(u1 > b0 and u0 < b1 for b0, b1, _, _ in baies):
                continue
            baies.append((u0, u1, z_baie0, z_baie1))
        paroi_percee(f"{name}_{face}", *bornes, zs, zc, col, mat, baies)


DEGRE = 0.5   # « רוּם מַעֲלָה חֲצִי אַמָּה וְשִׁלְחָהּ חֲצִי אַמָּה » (Middot 2:3)


def escalier(name, x0, x1, y0, y1, z_bas, z_haut, descente, col, mat=None):
    """Volée de degrés d'une demi-ama sur l'emprise donnée, chacun plein jusqu'à `z_bas`.

    `descente` : '+x', '-x', '+y' ou '-y', le sens où l'on descend. Le premier degré
    affleure `z_haut`, le sol d'où l'on part ; le dernier est à un degré de `z_bas`.
    """
    axe, sens = descente[1], 1 if descente[0] == "+" else -1
    a0, a1 = (x0, x1) if axe == "x" else (y0, y1)
    n = round((z_haut - z_bas) / DEGRE)
    pas, depart = (a1 - a0) / n, a0 if sens > 0 else a1
    for k in range(n):
        u0, u1 = sorted((depart + sens * pas * k, depart + sens * pas * (k + 1)))
        emprise = (u0, u1, y0, y1) if axe == "x" else (x0, x1, u0, u1)
        box(f"{name}_{k:02d}", *emprise, z_bas, z_haut - DEGRE * k, col, mat)


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


# Profils des moulures, de bas en haut : (cote depuis la référence, cote suivante, part
# de la saillie). PLUSIEURS assises et non une seule : un mur qui s'arrête net se lit en
# boîte, et une assise unique en débord ne fait qu'élargir la boîte. Ce qu'on lit d'un
# socle ou d'une corniche, ce sont leurs LIGNES D'OMBRE, et il en faut deux — l'assise
# qui déborde le plus, puis celle qui se retire.
# CORNICHE se réfère à la crête et monte d'une demi-ama au-dessus ; SOCLE se réfère au
# sol où le mur se pose. Aucune source ne moulure l'enceinte : CHOIX, mais dans la
# langue que les sources donnent au Temple — le כַּרְכֹּב du Mizbea'h (Middot 3:1), les
# rovadim de l'Oulam (Rambam Beit HaBe'hira 4:9), l'assise en débord du Bayit
# (« אַפֵּיק שָׂפָה וְעַיֵּיל שָׂפָה », Baba Batra 4a).
CORNICHE = ((-2.20, -1.55, 0.34), (-1.55, -0.30, 1.00), (-0.30, 0.60, 0.60))
SOCLE = ((0.00, 1.90, 1.00), (1.90, 2.60, 0.42))
BANDEAU = ((0.00, 1.30, 1.00), (1.30, 1.70, 0.40))
# La saillie est calée sur celle des lishkot de l'Azara (LISHKA_DEBORD), et pour la même
# raison : c'est la mesure au-dessous de laquelle une moulure cesse de jeter une ombre.
# À 0,75 ama, la corniche se lisait encore en filet sale au sommet d'un mur de dix-sept
# mètres ; à 1,4, sous un soleil rasant, elle porte son ombre sur six amot de parement.
SAILLIE_MOULURE = 1.4
SAILLIE_BANDEAU = 0.8
# Un filet d'or sur la face du larmier. AUCUNE SOURCE ne dore une corniche : c'est le
# seul poste purement électif de l'enceinte, couvert par « וּמְפָאֲרִין אוֹתוֹ וּמְיַפִּין כְּפִי
# כֹּחָן… לָטוּחַ אוֹתוֹ בְּזָהָב » (Rambam, Beit HaBe'hira 1:11). Il se coupe d'ici, et il faut
# le garder mince : les six portes d'or de Middot 2:3 ne se lisent comme de l'or que
# tant que l'or est rare dans le champ.
FILET_OR = True
FILET_PART, FILET_EPAISSEUR = 0.34, 0.05


def _mitre(a, dehors, regle, p):
    """Où s'arrête un membre de moulure au bout d'un mur, selon ce qu'il y trouve.

    Chaque assise déborde de sa propre valeur : le bout ne peut donc pas être chiffré
    au point d'appel, sinon les membres les plus minces laissent une encoche à l'angle
    et les plus larges un moignon en l'air.
    """
    return {"deborde": a + dehors * p,     # ce mur prend l'angle
            "bute": a - dehors * p,        # il s'arrête contre la saillie de l'autre
            "libre": a}[regle]             # il n'y a rien à cet angle


def moulure(name, x0, x1, y0, y1, z, profil, col, mat=None, saillie=SAILLIE_MOULURE,
            mitres=("libre", "libre"), cotes=(True, True), reserve=(), filet=None):
    """Assises en débord au pied ou à la crête d'un mur, cotées par `profil` depuis `z`.

    Le blockout le disait déjà des lishkot de l'Azara — « posée en boîte nue, une lishka
    ne se lit pas : à 750 amot elle n'a ni pied, ni sommet, ni ombre sur elle-même » —
    et leur donnait socle, bandeau et corniche. L'enceinte et les cours n'en avaient
    jamais eu : leurs murs s'arrêtaient sur une arête vive et sortaient de terre sans
    pied, ce qui les faisait lire en gros œuvre non fini.

    `mitres` dit ce que rencontre chaque bout du grand côté (voir `_mitre`) ; `cotes`,
    de quelle face du mur la moulure sort — un mur de soutènement n'a pas le même sol
    des deux côtés ; `reserve`, les intervalles du grand côté qu'elle saute ; `filet`,
    la matière d'un mince bandeau posé sur la face de l'assise la plus saillante.
    """
    long_x = (x1 - x0) >= (y1 - y0)
    a0, a1 = (x0, x1) if long_x else (y0, y1)
    bas, haut = z + min(zb for zb, _, _ in profil), z + max(zh for _, zh, _ in profil)
    larmier = max(range(len(profil)), key=lambda k: profil[k][2])
    for i, (zb, zh, part) in enumerate(profil):
        p = saillie * part
        p0, p1 = (p if cotes[0] else 0.0), (p if cotes[1] else 0.0)
        u0, u1 = _mitre(a0, -1, mitres[0], p), _mitre(a1, 1, mitres[1], p)
        morceaux = _hors_reserve(u0, u1, z + zb, z + zh,
                                 [(r0, r1, bas, haut) for r0, r1 in reserve])
        for j, (v0, v1) in enumerate(morceaux):
            if long_x:
                box(f"{name}_{i}{j}", v0, v1, y0 - p0, y1 + p1, z + zb, z + zh, col, mat)
            else:
                box(f"{name}_{i}{j}", x0 - p0, x1 + p1, v0, v1, z + zb, z + zh, col, mat)
        if filet is None or i != larmier:
            continue
        e = FILET_EPAISSEUR
        milieu, moitie = z + (zb + zh) / 2, (zh - zb) * FILET_PART / 2
        for j, (v0, v1) in enumerate(morceaux):
            for k, (sort, face) in enumerate(((cotes[0], y0 - p0 if long_x else x0 - p0),
                                              (cotes[1], y1 + p1 if long_x else x1 + p1))):
                if not sort:
                    continue
                bornes = ((v0, v1, face - e, face + e) if long_x else
                          (face - e, face + e, v0, v1))
                box(f"{name}_filet_{k}{j}", *bornes, milieu - moitie, milieu + moitie,
                    col, filet)


def ceinture(name, x0, x1, y0, y1, epaisseur, z, profil, col, mat=None,
             saillie=SAILLIE_MOULURE, filet=None):
    """La moulure de `moulure`, mais sur les quatre côtés d'une enceinte fermée.

    Un mur seul se coupe là où un corps de porte passe la crête ; ici les quatre côtés
    sont solidaires, et ce qui compte est qu'ils s'aboutent au lieu de se recouvrir —
    deux boîtes coplanaires clignotent. Les côtés sud et nord prennent les angles, les
    côtés est et ouest s'arrêtent contre eux.
    """
    larmier = max(range(len(profil)), key=lambda k: profil[k][2])
    for i, (zb, zh, part) in enumerate(profil):
        p, e = saillie * part, epaisseur
        box(f"{name}_S{i}", x0 - p, x1 + p, y0 - p, y0 + e + p, z + zb, z + zh, col, mat)
        box(f"{name}_N{i}", x0 - p, x1 + p, y1 - e - p, y1 + p, z + zb, z + zh, col, mat)
        box(f"{name}_O{i}", x0 - p, x0 + e + p, y0 + e, y1 - e, z + zb, z + zh, col, mat)
        box(f"{name}_E{i}", x1 - e - p, x1 + p, y0 + e, y1 - e, z + zb, z + zh, col, mat)
        if filet is None or i != larmier:
            continue
        # Le filet ne court que sur les faces EXTÉRIEURES : à l'intérieur d'une lishka
        # à ciel ouvert, il n'y a personne pour le voir.
        d = FILET_EPAISSEUR
        milieu, moitie = z + (zb + zh) / 2, (zh - zb) * FILET_PART / 2
        for suffixe, bornes in (
                ("S", (x0 - p, x1 + p, y0 - p - d, y0 - p + d)),
                ("N", (x0 - p, x1 + p, y1 + p - d, y1 + p + d)),
                ("O", (x0 - p - d, x0 - p + d, y0 + e, y1 - e)),
                ("E", (x1 + p - d, x1 + p + d, y0 + e, y1 - e))):
            box(f"{name}_filet_{suffixe}", *bornes, milieu - moitie, milieu + moitie,
                col, filet)


def dalle_trouee(name, x0, x1, y0, y1, z0, z1, trou, col, mat=None):
    """Dalle percée d'une ouverture rectangulaire : quatre boîtes qui l'entourent.

    Le blockout ne fait aucune booléenne — chaque volume est posé en `bpy.data`. Une
    cuve enterrée demande pourtant que le dallage ET le podium s'écartent d'elle, sinon
    elle est pleine de pierre.
    """
    tx0, tx1, ty0, ty1 = trou
    box(f"{name}_S", x0, x1, y0, ty0, z0, z1, col, mat)
    box(f"{name}_N", x0, x1, ty1, y1, z0, z1, col, mat)
    box(f"{name}_O", x0, tx0, ty0, ty1, z0, z1, col, mat)
    box(f"{name}_E", tx1, x1, ty0, ty1, z0, z1, col, mat)


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


EPAISSEUR_PLACAGE = 0.1   # amot : l'or est une feuille, la boîte doit rester visible

# Encadrement d'un שער. Ce que les sources donnent à une porte du Temple, et rien de
# plus : un LINTEAU — « כָּל הַשְּׁעָרִים שֶׁהָיוּ שָׁם הָיוּ לָהֶן שְׁקוֹפוֹת » (Middot 2:3), et c'est
# la michna qui exclut l'arc, pas une règle de style ; l'OR sur toute la baie — « כָּל
# הַשְּׁעָרִים… נִשְׁתַּנּוּ לִהְיוֹת שֶׁל זָהָב, חוּץ מִשַּׁעַר נִקָּנוֹר » (2:3), lu comme la baie entière
# et non ses seuls vantaux (ARBITRAGE, fiche §3) ; et une TIMORA par jambage —
# « וְתִמֹרִים אֶל־אֵילָיו, אֶחָד מִפּוֹ וְאֶחָד מִפּוֹ » (Ye'hezkel 40:26, 31, 34, 37), le seul
# ornement que le corpus pose sur une baie de cour.
# Le chambranle et sa corniche sont un CHOIX, dans la langue des moulures de l'enceinte
# et couverts par « וּמְפָאֲרִין אוֹתוֹ וּמְיַפִּין כְּפִי כֹּחָן » (Rambam, Beit HaBe'hira 1:11).
# Ils sont ce qui manquait : une baie percée dans un nu de vingt-cinq amot n'est pas
# une porte, c'est un trou — rien n'y dit où l'on entre, et les six portes d'or de
# Middot 2:3 ne se voyaient pas mieux que les trumeaux entre elles.
CHAMBRANLE = 3.0          # largeur du jambage bâti, en amot
# Ce dont un chambranle de `CHAMBRANLE` de large sort du parement. Il part de
# `SAILLIE_MOULURE`, pour la raison qui y est chiffrée — au-dessous, un ressaut ne jette
# plus d'ombre sur un mur de dix-sept mètres et redevient un filet sale ; mesuré ici, à
# 0,7 ama le chambranle de Nikanor était bâti et INVISIBLE, un jambage étant vertical et
# n'ayant que sa saillie pour se donner. Et il en sort un rien de PLUS, parce qu'il
# traverse le socle et le bandeau du mur : à saillie égale, sa face et la leur se
# disputeraient le même plan sur toute la hauteur du jambage.
CHAMBRANLE_NU = SAILLIE_MOULURE + 0.3
CHAMBRANLE_LISERE = 0.5   # le filet qui le borde, et sa seconde ligne d'ombre
# La corniche qui couronne le chambranle sort plus que lui, comme le larmier d'un mur
# sort de son nu et pour la même raison : c'est le ressaut le plus fort qui porte
# l'ombre, et une porte qui n'en jette pas ne se voit pas du fond de la cour.
CHAMBRANLE_CORNICHE = 1.7        # sa hauteur, quand la place au-dessus de la baie le permet
# Hauteur du palmier, en part de la largeur du jambage : ses palmes s'ouvrent sur un peu
# plus d'une demi-hauteur, et c'est le jambage qui doit les contenir — sur le cadre
# étroit d'un corps de porte, une timora à cote fixe débordait sur le nu du mur.
TIMORA_SUR_CADRE = 2.0


def shaar(nom, paroi, centre, z0, sommet, ebrasement, col, mat=None, metal=None,
          largeur=10, hauteur=20, cadre=CHAMBRANLE):
    """L'encadrement bâti d'une porte : chambranle, corniche, timorim, or de la baie.

    `paroi` : (axe, cote de la face, sens de la saillie) — la face EXTÉRIEURE, celle
    qu'on regarde en arrivant, dans le repère de `_repere`. Tout le bâti SORT du nu :
    une pièce rapportée dont la face arrière est au nu du mur tourne le dos à celle du
    mur, et les deux ne se disputent pas le même plan ; posée à cheval, elle
    clignoterait sur toute sa longueur.
    `sommet` : la cote où le cadre s'arrête — sous le couronnement du mur, qu'il ne doit
    pas traverser. `ebrasement` : la profondeur que l'or de CETTE face tapisse dans la
    baie ; une porte cadrée des deux côtés en donne la moitié à chacune, et les deux
    plaques s'aboutent au milieu du mur au lieu de se recouvrir. `metal` : ce dont ce
    שער « a été changé » (Middot 2:3) — l'or partout, le bronze à Nikanor, rien pour un
    פתח de chambre, qui n'est pas un שער.
    """
    axe, cote, sens = paroi
    demi, haut = largeur / 2, z0 + hauteur
    corniche = min(CHAMBRANLE_CORNICHE, (sommet - haut) * 0.55)
    tete = sommet - corniche
    # La saillie suit la largeur du chambranle : un cadre étroit qui sortirait autant
    # qu'un large serait un boudin, et c'est celui d'un corps de porte qui le montrait.
    nu = CHAMBRANLE_NU * cadre / CHAMBRANLE

    def pose(suffixe, u0, u1, zb, zh, d0, d1, matiere=None):
        bornes = ((u0, u1, cote + sens * d0, cote + sens * d1) if axe == "x" else
                  (cote + sens * d0, cote + sens * d1, u0, u1))
        if abs(u1 - u0) > 1e-6 and zh - zb > 1e-6:
            box(f"{nom}_{suffixe}", *sorted(bornes[:2]), *sorted(bornes[2:]), zb, zh,
                col, mat if matiere is None else matiere)

    # Le chambranle : deux jambages et la traverse qui les joint, puis le liseré qui les
    # borde. Une seule assise en débord n'élargirait que la baie ; ce qui fait lire un
    # cadre, ce sont ses DEUX lignes d'ombre — la même règle qu'aux corniches de
    # l'enceinte, et la même raison : sous un demi-pied de ressaut, un soleil rasant
    # n'écrit plus rien.
    for nommage, large, saillie in (("cadre", cadre, nu),
                                    ("lisere", cadre + CHAMBRANLE_LISERE, nu * 0.45)):
        for face, sortie in (("O", -1), ("E", 1)):
            pose(f"{nommage}_jambage_{face}", centre + sortie * demi,
                 centre + sortie * (demi + large), z0, tete, 0.0, saillie)
        pose(f"{nommage}_traverse", centre - demi, centre + demi, haut, tete, 0.0, saillie)
    # Le larmier puis la couvertine qui se retire : les deux mêmes lignes d'ombre qu'aux
    # corniches de l'enceinte, et tout tient SOUS `sommet` — au-dessus commence le
    # couronnement du mur, qui sort davantage et avalerait ce qui monterait dedans.
    debord = cadre + CHAMBRANLE_LISERE + 0.4
    pose("corniche_larmier", centre - demi - debord, centre + demi + debord,
         tete, sommet - 0.35, 0.0, nu * 1.5)
    pose("corniche_couvertine", centre - demi - debord + 0.3, centre + demi + debord - 0.3,
         sommet - 0.35, sommet, 0.0, nu * 1.1)
    # « וְתִמֹרִים אֶל־אֵילָיו » : le palmier se pose sur la face du jambage, pas sur le nu du
    # mur — c'est de l'איל que parle le verset. Il se dore avec le שער, et reste de la
    # pierre du mur là où aucune source ne met d'or.
    jambage = (axe, cote + sens * nu, sens)
    palmier = min(cadre * TIMORA_SUR_CADRE, hauteur * 0.4)
    for face, sortie in (("O", -1), ("E", 1)):
        timora(f"{nom}_timora_{face}", jambage, centre + sortie * (demi + cadre / 2),
               z0 + (hauteur - palmier) / 2, palmier, col, metal or mat)
    if metal is None:
        return
    # L'or prend l'ÉBRASEMENT, sur toute l'épaisseur du mur, et la שקופה avec lui : la
    # michna dit le שער, et deux michnayot plus haut elle donne à chaque שער sa שקופה.
    # Posé sur la seule face extérieure il ne se voyait que de face ; c'est dans
    # l'embrasure qu'on le regarde, et de toute la cour.
    e = EPAISSEUR_PLACAGE
    for face, sortie in (("O", -1), ("E", 1)):
        pose(f"or_jambage_{face}", centre + sortie * demi, centre + sortie * (demi - e),
             z0, haut, 0.0, -ebrasement, metal)
    pose("or_shkufa", centre - demi, centre + demi, haut - e, haut, 0.0, -ebrasement, metal)


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

def chaine(name, p0, p1, R, col, mat=None, tube=None, majeur=10, mineur=6):
    """Chaîne tendue entre deux points : maillons enfilés, un plan sur deux tourné.

    Une chaîne longue se paie en sommets dans le .glb — un maillon plus gros et moins
    facetté est ce qui la rend soutenable sur toute la hauteur de l'Oulam.
    """
    a, d = Vector(p0), Vector(p1) - Vector(p0)
    axe1 = d.normalized().cross(Vector((1, 0, 0)))
    if axe1.length < 1e-3:
        axe1 = d.normalized().cross(Vector((0, 1, 0)))
    axe1.normalize()
    axe2 = d.normalized().cross(axe1)
    n = max(1, int(d.length / (1.5 * R)))
    for k in range(n):
        p = a + d * ((k + 0.5) / n)
        axe = axe1 if k % 2 else axe2
        tore(f"{name}_{k:02d}", p.x, p.y, p.z, R, tube or R * 0.32, col, mat,
             rotation=axe.to_track_quat('Z', 'Y').to_euler(), majeur=majeur, mineur=mineur)

def _poser(pieces, x, y, z0, lacet):
    """Pièces bâties à l'origine, posées en (x, y, z0) amot et tournées de `lacet`
    autour de la verticale — silhouettes et keruvim.

    La pose se COMPOSE avec ce que la pièce porte déjà. `cyl_between` oriente son
    cylindre par `rotation_euler` : l'écraser couchait à la verticale, sur l'origine du
    keruv, tous les membres bâtis avec lui — les bras du keruv ne se voyaient nulle part.
    """
    pose = Matrix.Translation((m(x), m(y), m(z0))) @ Matrix.Rotation(lacet, 4, 'Z')
    for piece in pieces:
        # La transformation propre se recompose à la main : `matrix_world` n'est
        # recalculée qu'au rafraîchissement du graphe de dépendances, et vaut encore
        # l'identité pour une pièce qu'on vient de poser.
        propre = Matrix.Translation(piece.location) @ piece.rotation_euler.to_matrix().to_4x4()
        piece.matrix_world = pose @ propre

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

def courbe(p0, p1, p2, n):
    """Bézier quadratique échantillonnée en n+1 points : le tracé d'une branche."""
    return [tuple((1 - t) ** 2 * a + 2 * (1 - t) * t * b + t * t * c
                  for a, b, c in zip(p0, p1, p2))
            for t in (k / n for k in range(n + 1))]


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
MUR_HAR = 3                             # épaisseur de l'enceinte
TADI_X, KIPONUS_Y, MIZRAHI_Y = -100, 0, 0
# Les cinq portes, et l'enceinte percée pour elles. `paroi` est la face de l'ESPLANADE :
# c'est de là qu'on les voit, le revers d'un mur de soutènement tombant sur le Kidron ou
# sur la ville. Aucune source ne dore ces שערים-là — Middot 2:3 parle des portes que le
# Temple a fait changer en or, et la fiche ne les compte pas ici : leur cadre et leurs
# timorim se taillent dans la pierre du mur.
PORTES_HAR = (
    ("sud", (HX0, HX1, HY0, HY0 + 3), ("x", HY0 + 3, 1), H_HAR,
     [("Houlda_ouest", -60, 20), ("Houlda_est", 20, 20)]),
    ("nord", (HX0, HX1, HY1 - 3, HY1), ("x", HY1 - 3, -1), H_HAR,
     [("Tadi", TADI_X, 10)]),
    ("ouest", (HX0, HX0 + 3, HY0, HY1), ("y", HX0 + 3, 1), H_HAR,
     [("Kiponus", KIPONUS_Y, 10)]),
    ("est", (HX1 - 3, HX1, HY0, HY1), ("y", HX1 - 3, -1), H_HAR_EST,
     [("Mizrahi", MIZRAHI_Y, 10)]),
)
for _nm, _bornes, _paroi, _h, _portes in PORTES_HAR:
    mur_perce(f"HarHabayit_mur_{_nm}", *_bornes, Z_HAR, Z_HAR + _h,
              "00_HarHabayit", [(c, l) for _, c, l in _portes], 20, MAT_MURAILLE())
    for _porte, _c, _l in _portes:
        shaar(f"HarHabayit_porte_{_porte}", _paroi, _c, Z_HAR, Z_HAR + _h - 3, MUR_HAR,
              "00_HarHabayit", MAT_MURAILLE(), largeur=_l)
# « חוּץ מִשַּׁעַר טָדִי, שֶׁהָיוּ שָׁם שְׁתֵּי אֲבָנִים מֻטּוֹת זוֹ עַל גַּב זוֹ » (Middot 2:3) : la seule
# tête de baie du Temple qui ne soit pas une שְׁקוֹפָה. Deux dalles penchées l'une contre
# l'autre, et non un arc — la michna les compte, et elles se rejoignent sur l'axe. Elles
# se posent DANS la baie, sous le plein du mur : ce qu'on voit en passant est le triangle
# qu'elles laissent. La pente et la portée du sommet sont un CHOIX ; le nombre et
# l'appui l'un sur l'autre ne le sont pas.
TADI_NAISSANCE, TADI_APPUI = 12, 0.3
for _sens in (-1, 1):
    _cote = "O" if _sens < 0 else "E"
    _relief_profil(f"HarHabayit_porte_Tadi_pierre_{_cote}", ("x", HY1, 1),
                   [(TADI_X + _sens * 5, Z_HAR + TADI_NAISSANCE),
                    (TADI_X + _sens * 5, Z_HAR + 20),
                    (TADI_X + _sens * TADI_APPUI, Z_HAR + 20),
                    (TADI_X + _sens * TADI_APPUI, Z_HAR + 20 - 0.6)],
                   -MUR_HAR, 0.0, "00_HarHabayit", MAT_MURAILLE())
# « שַׁעַר הַמִּזְרָחִי, עָלָיו שׁוּשַׁן הַבִּירָה צוּרָה » (Middot 1:3) : le dessin de Suse au-dessus
# de la porte est, tourné vers le mont des Oliviers. Un bas-relief : rempart et trois
# tours crénelées, dans la pierre du mur.
SHUSHAN_Z = Z_HAR + 20.4
box("Shushan_plaque", HX1, HX1 + 0.15, -4.5, 4.5, SHUSHAN_Z, SHUSHAN_Z + 3.2,
    "00_HarHabayit", MAT_MURAILLE())
box("Shushan_rempart", HX1 + 0.15, HX1 + 0.35, -3.8, 3.8, SHUSHAN_Z + 0.3, SHUSHAN_Z + 1.3,
    "00_HarHabayit", MAT_MURAILLE())
for k, y in enumerate((-3.0, 0.0, 3.0)):
    h = 2.6 if y == 0 else 2.0
    box(f"Shushan_tour_{k}", HX1 + 0.15, HX1 + 0.4, y - 0.6, y + 0.6, SHUSHAN_Z + 0.3,
        SHUSHAN_Z + h, "00_HarHabayit", MAT_MURAILLE())
    for j, yc in enumerate((y - 0.45, y, y + 0.45)):
        box(f"Shushan_tour_{k}_merlon_{j}", HX1 + 0.15, HX1 + 0.4, yc - 0.12, yc + 0.12,
            SHUSHAN_Z + h, SHUSHAN_Z + h + 0.25, "00_HarHabayit", MAT_MURAILLE())
# Crête des murs : merlons (CHOIX, appareil hérodien — les stylisations des plans 1 et
# 14b crénelaient d'elles-mêmes cette enceinte, autant que le blockout le fixe).
for nm, xa, xb, ya, yb, h in (("sud", HX0, HX1, HY0, HY0 + 3, H_HAR),
                              ("nord", HX0, HX1, HY1 - 3, HY1, H_HAR),
                              ("ouest", HX0, HX0 + 3, HY0 + 3, HY1 - 3, H_HAR),
                              ("est", HX1 - 3, HX1, HY0 + 3, HY1 - 3, H_HAR_EST)):
    creneaux(f"HarHabayit_creneaux_{nm}", xa, xb, ya, yb, Z_HAR + h, "00_HarHabayit",
             MAT_MURAILLE())
# Murs de soutènement : l'esplanade est une terrasse bâtie au-dessus du Kidron et du
# Tyropéon, ses murs descendent jusqu'au rocher. Sans lui, le pays passait sous le
# dallage et l'esplanade flottait au-dessus de ses propres vallées.
box("HarHabayit_soubassement", HX0, HX1, HY0, HY1, Z_ROCHE, Z_HAR - 1, "00_HarHabayit",
    MAT_MURAILLE())
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
# Les portiques sont couverts : la guemara parle du « גַּג הָאִיצְטְבָא » (Pesa'him 13b), le
# TOIT de la colonnade, sur lequel on posait les deux hallot — il y a donc un toit. Du
# mur à la rangée de colonnes, chapiteau compris. À ciel ouvert, les colonnes se
# lisaient d'en haut en rangées de bornes sur le dallage. Cèdre : CHOIX, c'est le bois
# dont le Tanakh couvre le Bayit (Melakhim I 6:9).
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
# Plafond de la nef centrale de la Stoa. Sans lui la colonnade est ouverte au ciel :
# CAM_02 ne filmait que du fond de monde entre des piliers, et le plafond de cèdre du
# prompt n'avait aucune géométrie à habiller.
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
# « כָּל הַשְּׁעָרִים שֶׁהָיוּ שָׁם, הָיוּ לָהֶן שְׁקוֹפוֹת » (Middot 2:3) : chaque שער a son linteau, et
# la même michna donne vingt amot à la baie. Un mur de vingt n'en laisse donc AUCUN —
# la porte est n'avait plus qu'un linteau d'un centième d'ama, ce qui est un artefact de
# modèle et non une porte. Aucune source ne donne la hauteur de ce mur : il prend celle
# de l'Azara, qui est le premier nombre disponible qui laisse la michna tenir.
H_MUR_EN = 25
box("EzratNashim_mur_nord", EX0, EX1 + 5, 67.5, 72.5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_mur_sud", EX0, EX1 + 5, -72.5, -67.5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_mur_est_S", EX1, EX1 + 5, -72.5, -5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_mur_est_N", EX1, EX1 + 5, 5, 72.5, Z_EZN, Z_EZN + H_MUR_EN, "10_EzratNashim")
box("EzratNashim_porte_est_linteau", EX1, EX1 + 5, -5, 5, Z_EZN + 20, Z_EZN + H_MUR_EN, "10_EzratNashim")
# Quatre chambres d'angle 40 × 40, sans toit (murs de 2 amot) — « ולא היו מקורות »
# (Middot 2:5, qui les rattache aux « חצרות קטורות » d'Ezekiel 46:21-22). Affectations
# par angle : Middot 2:5. CHOIX : la Mishna ne décrit aucune porte, seulement des
# usages qui la supposent (les nazirs y cuisent, les metzoraim s'y immergent) ;
# quatre murs aveugles ne sont pas une lishka mais une fosse. Chacune s'ouvre donc
# sur la cour, par la face tournée vers l'axe. Cote inventée (6 × 12) : Middot 2:3
# donne 10 × 20 à « tous les pesa'him et tous les shearim », mais une porte de 20 ne
# tient pas dans un mur de 15 — la hauteur de ces murs n'est elle-même dans aucune
# source.
#
# Elles restent DÉCOUVERTES, et c'est la seule chose ici qui ne soit pas un choix :
# « וְלֹא הָיוּ מְקוֹרוֹת. וְכָךְ הֵם עֲתִידִים לִהְיוֹת » (Middot 2:5) — pas de toit, et pas
# davantage dans le Temple à venir, qui est celui que le film bâtit. Ce qu'on peut leur
# donner, c'est le couronnement de leurs murs : les quatre crêtes s'arrêtaient net et
# se lisaient en boîtes découpées, ce que le reste de l'enceinte ne fait nulle part.
H_LISHKA_EN = 15
for nm, xa, ya, cour in (("Nezirim_SE", EX1 - 40, -67.5, "N"), ("Etzim_NE", EX1 - 40, 27.5, "S"),
                         ("Metzoraim_NO", EX0, 27.5, "S"), ("Shemanya_SO", EX0, -67.5, "N")):
    xb, yb = xa + 40, ya + 40
    for a, b, c, d, side in ((xa, xb, ya, ya + 2, "S"), (xa, xb, yb - 2, yb, "N"),
                             (xa, xa + 2, ya, yb, "O"), (xb - 2, xb, ya, yb, "E")):
        nom = f"Lishkat_{nm}_{side}"
        if side == cour:
            mur_perce(nom, a, b, c, d, Z_EZN, Z_EZN + H_LISHKA_EN, "10_EzratNashim",
                      [((a + b) / 2, 6)], 12)
            # Un פתח de chambre n'est pas un שער : Middot 2:3 ne le change pas en or, et
            # il ne reçoit qu'un cadre de pierre, à l'échelle de sa baie de six.
            shaar(f"{nom}_cadre",
                  {"S": ("x", c, -1), "N": ("x", d, 1),
                   "O": ("y", a, -1), "E": ("y", b, 1)}[side],
                  (a + b) / 2, Z_EZN,
                  Z_EZN + H_LISHKA_EN + min(zb for zb, _, _ in CORNICHE), 2,
                  "10_EzratNashim", largeur=6, hauteur=12, cadre=1.5)
        else:
            box(nom, a, b, c, d, Z_EZN, Z_EZN + H_LISHKA_EN, "10_EzratNashim")
    ceinture(f"Lishkat_{nm}_couronnement", xa, xb, ya, yb, 2,
             Z_EZN + H_LISHKA_EN, CORNICHE, "10_EzratNashim",
             filet=MAT_OR() if FILET_OR else None)
    ceinture(f"Lishkat_{nm}_socle", xa, xb, ya, yb, 2, Z_EZN, SOCLE, "10_EzratNashim")
# Ce que la Michna met DANS ces chambres. Elles étaient quatre boîtes vides : leurs
# usages sont pourtant donnés un par un (Middot 2:5), et ce sont eux qui apportent à
# l'Ezrat Nashim les quatre matières qu'elle n'a pas — l'eau, le bois, le feu, la terre
# cuite. Les cotes du mobilier sont partout des CHOIX : aucune source ne les donne.
#
# NORD-EST, Lishkat HaEtzim : « הַכֹּהֲנִים בַּעֲלֵי מוּמִין מַתְלִיעִין הָעֵצִים, וְכָל עֵץ שֶׁנִּמְצָא
# בּוֹ תּוֹלַעַת פָּסוּל מֵעַל גַּבֵּי הַמִּזְבֵּחַ ». Le bois trié est celui de la ma'arakha —
# figuier, noyer et עֵץ שָׁמֶן (Tamid 2:3) —, d'où MAT_BOIS_MAARAKHA et pas le chêne clair.
for _s, _x in enumerate((106.0, 118.0, 130.0)):
    for _l in range(5):
        _z = Z_EZN + 0.3 + _l * 0.62
        for _k in range(5):
            if _l % 2 == 0:
                _y = 58.0 + _k * 0.65
                cyl_between(f"Lishkat_Etzim_NE_bois_{_s}{_l}{_k}", (_x, _y, _z), (_x + 8, _y, _z),
                            0.3, "10_EzratNashim", MAT_BOIS_MAARAKHA(), verts=6)
            else:
                _xk = _x + 0.6 + _k * 1.8
                cyl_between(f"Lishkat_Etzim_NE_bois_{_s}{_l}{_k}", (_xk, 57.7, _z), (_xk, 60.9, _z),
                            0.3, "10_EzratNashim", MAT_BOIS_MAARAKHA(), verts=6)
# SUD-EST, Lishkat HaNezirim : « מְבַשְּׁלִין אֶת שַׁלְמֵיהֶן, וּמְגַלְּחִין אֶת שְׂעָרָן,
# וּמְשַׁלְּחִים תַּחַת הַדּוּד » — le chaudron et son foyer. C'est le seul feu de l'Ezrat
# Nashim en dehors de Simhat Beit HaShoeva.
DOUD_X, DOUD_Y = 120.0, -48.0
for _nm, _a, _b, _c, _d in (("S", -4, 4, -4, -3), ("N", -4, 4, 3, 4),
                            ("O", -4, -3, -3, 3), ("E", 3, 4, -3, 3)):
    box(f"Lishkat_Nezirim_SE_foyer_{_nm}", DOUD_X + _a, DOUD_X + _b, DOUD_Y + _c, DOUD_Y + _d,
        Z_EZN, Z_EZN + 2.4, "10_EzratNashim")
box("Lishkat_Nezirim_SE_braises", DOUD_X - 3, DOUD_X + 3, DOUD_Y - 3, DOUD_Y + 3,
    Z_EZN + 0.1, Z_EZN + 0.5, "10_EzratNashim", braise("Braise"))
revolution("Lishkat_Nezirim_SE_doud", DOUD_X, DOUD_Y, Z_EZN + 2.4,
           [(0.0, 0.0), (1.8, 0.4), (2.6, 1.6), (2.7, 2.4), (2.5, 2.45),
            (2.4, 1.7), (1.6, 0.5), (0.0, 0.15)], "10_EzratNashim", MAT_BRONZE(), verts=24)
# NORD-OUEST, Lishkat HaMetzoraïm : la Michna ne lui donne qu'un nom, mais une autre
# le meuble — « וְהַמְּצֹרָע טָבַל בְּלִשְׁכַּת הַמְּצֹרָעִים, בָּא וְעָמַד בְּשַׁעַר נִקָּנוֹר »
# (Negaïm 14:8). C'est un mikvé, et la seule eau de la cour. Sa cote minimale est
# « אַמָּה עַל אַמָּה בְּרוּם שָׁלֹשׁ אַמּוֹת » = quarante séa (Rambam, Mikvaot 4:1) ; les
# 10 × 8 × 3 d'ici sont un CHOIX, comme la volée qui y descend — dont la marche reprend
# le « רוּם מַעֲלָה חֲצִי אַמָּה וְשִׁלְחָהּ חֲצִי אַמָּה » de toutes les marches du Temple
# (Middot 2:3).
MIKVE = (19.0, 31.0, 48.0, 58.0)     # l'emprise que le dallage et le podium lui cèdent
MIKVE_FOND, MIKVE_EAU = Z_EZN - 4.5, Z_EZN - 1.5
for _nm, _a, _b, _c, _d in (("S", 0, 12, 0, 1), ("N", 0, 12, 9, 10),
                            ("O", 0, 1, 1, 9), ("E", 11, 12, 1, 9)):
    box(f"Lishkat_Metzoraim_NO_cuve_{_nm}", MIKVE[0] + _a, MIKVE[0] + _b,
        MIKVE[2] + _c, MIKVE[2] + _d, Z_EZN - 5, Z_EZN, "10_EzratNashim")
box("Lishkat_Metzoraim_NO_cuve_fond", *MIKVE, Z_EZN - 5, MIKVE_FOND, "10_EzratNashim")
for _k in range(9):
    box(f"Lishkat_Metzoraim_NO_marche_{_k}", MIKVE[0] + 1, MIKVE[1] - 1,
        MIKVE[2] + 1, MIKVE[2] + 1 + 0.5 * (_k + 1), MIKVE_FOND, Z_EZN - 0.5 * _k,
        "10_EzratNashim")
box("Lishkat_Metzoraim_NO_eau", MIKVE[0] + 1, MIKVE[1] - 1, MIKVE[2] + 1, MIKVE[3] - 1,
    MIKVE_FOND, MIKVE_EAU, "10_EzratNashim", MAT_EAU())
# SUD-OUEST, Beit Shemanya : « שָׁם הָיוּ נוֹתְנִין יַיִן וָשֶׁמֶן » — mais c'est Abba Shaoul ;
# R. Eliezer ben Yaakov dit « שָׁכַחְתִּי מֶה הָיְתָה מְשַׁמֶּשֶׁת ». Le film suit Abba Shaoul,
# seul avis qui donne un contenu (fiche §3).
JARRE = [(0.0, 0.0), (0.35, 0.06), (0.78, 0.7), (0.86, 1.3), (0.58, 2.0),
         (0.34, 2.2), (0.44, 2.35), (0.36, 2.42), (0.0, 2.36)]
for _r, (_y, _n) in enumerate(((-62.0, 10), (-59.4, 10), (-33.4, 9), (-30.8, 9))):
    for _k in range(_n):
        revolution(f"Lishkat_Shemanya_SO_jarre_{_r}{_k}", 10.5 + _k * 3.5, _y, Z_EZN,
                   JARRE, "10_EzratNashim", MAT_TERRE_CUITE(), verts=14)
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
# Socle, bandeau et couronnement se posent aux mêmes bouts, avec les mêmes mitres, et
# tombent ici tous les dix amot : le pied à Z_EZN, la crête vingt amot plus haut, et
# entre les deux le plancher de la gezuztra (Middot 2:5), qui est de plain-pied avec le
# dallage de l'Azara. Le bandeau n'est donc pas un ornement posé à mi-hauteur : c'est le
# niveau de la galerie, lu du dehors. Seule la porte est interrompt les deux moulures
# basses.
OR_CORNICHE = MAT_OR() if FILET_OR else None
for _ouvrage, _profil, _z, _s in (("socle", SOCLE, Z_EZN, SAILLIE_MOULURE),
                                  ("bandeau", BANDEAU, Z_AZ, SAILLIE_BANDEAU),
                                  ("couronnement", CORNICHE, Z_EZN + H_MUR_EN, SAILLIE_MOULURE)):
    _baie = () if _ouvrage == "couronnement" else [(-5, 5)]
    _filet = OR_CORNICHE if _ouvrage == "couronnement" else None
    moulure(f"EzratNashim_{_ouvrage}_nord", EX0, EX1, 67.5, 72.5, _z, _profil, "10_EzratNashim",
            saillie=_s, mitres=("deborde", "bute"), filet=_filet)
    moulure(f"EzratNashim_{_ouvrage}_sud", EX0, EX1, -72.5, -67.5, _z, _profil, "10_EzratNashim",
            saillie=_s, mitres=("deborde", "bute"), filet=_filet)
    moulure(f"EzratNashim_{_ouvrage}_est", EX1, EX1 + 5, -72.5, 72.5, _z, _profil, "10_EzratNashim",
            saillie=_s, mitres=("deborde", "deborde"), reserve=_baie, filet=_filet)
battants("EzratNashim_porte_est", EX1, EX1 + 5, -5, 5, Z_EZN, 20, "10_EzratNashim", MAT_OR())
# « כָּל הַשְּׁעָרִים שֶׁהָיוּ שָׁם נִשְׁתַּנּוּ לִהְיוֹת שֶׁל זָהָב » (Middot 2:3) : la michna dit le
# ŠAʿAR, pas ses vantaux — et elle dit deux michnayot plus haut que chaque שער avait sa
# שְׁקוֹפָה. L'or déborde donc des battants sur les jambages et sur elle. ARBITRAGE : lire
# « שער » comme la baie entière et non comme ses seules portes.
# C'est la porte par laquelle le peuple entre : elle se cadre des deux côtés, en venant
# du 'Heil comme en la regardant de la cour.
for _cote, _nu, _sens in (("est", EX1 + 5, 1), ("ouest", EX1, -1)):
    shaar(f"EzratNashim_porte_{_cote}", ("y", _nu, _sens), 0, Z_EZN,
          Z_EZN + H_MUR_EN + min(zb for zb, _, _ in CORNICHE), 2.5,
          "10_EzratNashim", metal=MAT_OR())
# Treize shofarot (Shekalim 6:5) : les troncs « en forme de shofar » — étroits en haut,
# larges en bas, pour qu'on n'y glisse pas la main (Bartenura) — le long du mur est, de
# part et d'autre de la porte. Bronze : CHOIX, la Mishna n'en dit pas la matière.
SHOFAR = [(0.62, 0.0), (0.60, 0.12), (0.40, 0.60), (0.24, 1.35), (0.20, 1.55), (0.14, 1.55), (0.12, 1.2), (0.0, 1.1)]
# « וְכָתוּב עֲלֵיהֶם » (Shekalim 6:5) : la destination de chaque tronc est écrite dessus,
# et la michna en donne les treize libellés. Sans voyelles — la ponctuation est
# postérieure au Temple. Lettres dorées sur le bronze : CHOIX.
SHOFAROT = ["תקלין חדתין", "תקלין עתיקין", "קנין", "גוזלי עולה", "עצים", "לבונה",
            "זהב לכפרת"] + ["לנדבה"] * 6
_gravures = []
for k, y in enumerate([-26.5 + 3.4 * i for i in range(7)] + [6.1 + 3.4 * i for i in range(6)]):
    revolution(f"Shofar_{k:02d}", EX1 - 1.4, y, Z_EZN, SHOFAR, "10_EzratNashim", MAT_BRONZE(), verts=20)
    _gravures.append((f"Shofar_{k:02d}_gravure", SHOFAROT[k], EX1 - 1.894, y, Z_EZN + 0.35))
graver(_gravures, "10_EzratNashim", MAT_OR(), taille=0.11, saillie=0.04, courbure=0.494)
# Simhat Beit HaShoeva (Soucca 5:2-3 ; 52b) : « מְנוֹרוֹת שֶׁל זָהָב הָיוּ שָׁם, וְאַרְבָּעָה סְפָלִים
# שֶׁל זָהָב בְּרָאשֵׁיהֶן, וְאַרְבָּעָה סֻלָּמוֹת לְכָל אֶחָד וְאֶחָד » — cinquante amot de haut
# (« תָּנָא גָּבְהָהּ שֶׁל מְנוֹרָה חֲמִשִּׁים אַמָּה », Soucca 52b), dans l'Ezrat Nashim. Quatre mâts
# (nombre : CHOIX, la Mishna dit « des menorot »), quatre coupes et quatre échelles chacun.
# Le barreau se prend tous les trois quarts d'ama et pas toutes les deux : à un mètre
# d'écart on n'y monte pas, et une échelle qu'on ne peut pas gravir se lit en étai
# d'échafaudage — or la guemara y fait justement monter des enfants avec trente log
# d'huile, en opposant l'échelle raide au kevesh qui ne l'est pas (Soucca 52b).
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
            for i, t in enumerate(plage(0.02, 0.98, 0.75 / (H_CANDELABRE - 1.5))):
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
H_MUR = 25
T = 5   # épaisseur des murs
# Un cadre de porte s'arrête sous le couronnement du mur : au-dessus, c'est le larmier
# qui sort le plus et lui qui porte l'ombre. `CORNICHE` se cote depuis la crête.
SOUS_CORNICHE = Z_AZ + H_MUR + min(zb for zb, _, _ in CORNICHE)
box("Azara_sol", AX0 - T, X_DOUKHAN, AY0 - T, AY1 + T, Z_AZ - 1, Z_AZ, "20_Azara", MAT_SOL())
box("EzratIsrael_sol", X_DOUKHAN, AX1, AY0, AY1, Z_EZI - 1, Z_EZI, "20_Azara", MAT_SOL())
# L'Azara et l'Ezrat Nashim sont des terrasses taillées dans le Har HaBayit, pas des
# dalles posées en l'air : hors de leurs murs le sol retombe à Z_HAR. Sans la masse
# qui les porte, les murs, les chambres d'angle et les quatre lishkot du pourtour
# flottaient — 13,5 amot au-dessus du dallage, visible plein cadre au plan 1.
# Deux blocs et non un : le mur est de l'Azara (x 0..5) descend déjà à Z_EZN, une
# masse qui monterait à Z_AZ sous lui lui donnerait une face coplanaire.
# Chaque podium s'arrête UNE AMA sous sa terrasse, et le dallage fait sa croûte sur
# toute son emprise, murs compris. Deux faces coplanaires ne se départagent pas : le
# rayon qui repart du dallage retombe aussitôt sur la face jumelle, et Cycles rendait
# l'Azara et l'Ezrat Nashim en noir plein. Le podium de l'Ezrat Israël le faisait
# déjà juste ; les deux autres montaient au ras de leur sol.
dalle_trouee("Podium_har", AX0 - T, EX1 + 5, AY0 - T, AY1 + T, Z_HAR, Z_EZN - 1,
             MIKVE, "00_HarHabayit")
dalle_trouee("EzratNashim_sol", AX0 - T, EX1 + 5, AY0 - T, AY1 + T, Z_EZN - 1, Z_EZN,
             MIKVE, "10_EzratNashim", MAT_SOL())
box("Podium_azara", AX0 - T, X_DOUKHAN, AY0 - T, AY1 + T, Z_EZN, Z_AZ - 1, "00_HarHabayit")
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
# Le שער de Nikanor se regarde des DEUX côtés, et c'est le seul du Temple dans ce cas :
# de l'Ezrat Nashim par les quinze marches, et de toute l'Azara par la mire est-ouest
# que Middot 2:4 dégage. Son encadrement est celui des six autres ; ce qui l'en sépare
# est son métal — « חוּץ מִשַּׁעֲרֵי נִיקָנוֹר… מִפְּנֵי שֶׁנְּחֻשְׁתָּן מַצְהִיב » (Middot 2:3).
for _cote, _nu, _sens in (("est", AX1 + T, 1), ("ouest", AX1, -1)):
    shaar(f"Nikanor_{_cote}", ("y", _nu, _sens), 0, Z_EZI, SOUS_CORNICHE, T / 2,
          "20_Azara", metal=MAT_NEHOSHET())
box("Nikanor_porte_S", AX1 + 1, AX1 + 4.5, -5, -4.7, Z_EZI, Z_EZI + 20, "20_Azara", MAT_NEHOSHET())
box("Nikanor_porte_N", AX1 + 1, AX1 + 4.5, 4.7, 5, Z_EZI, Z_EZI + 20, "20_Azara", MAT_NEHOSHET())
# « שְׁנֵי פִשְׁפְּשִׁין הָיוּ לוֹ לְשַׁעַר נִיקָנוֹר, אֶחָד בִּימִינוֹ וְאֶחָד בִּשְׂמֹאלוֹ » (Middot 2:6) : deux
# guichets de bronze de part et d'autre de la grande porte, côté Azara. Cote (3 × 8) :
# CHOIX. Les vantaux sont posés sur le nu du mur — la baie n'est pas percée, et la face
# est, dix amot au-dessus du sol de l'Ezrat Nashim, n'en reçoit pas.
PISHPESHIM = (("S", -14.5, -11.5), ("N", 11.5, 14.5))
H_PISHPESH = 8
for cote, y0, y1 in PISHPESHIM:
    box(f"Nikanor_pishpesh_{cote}", AX1 - 0.25, AX1, y0, y1, Z_EZI, Z_EZI + H_PISHPESH, "20_Azara", MAT_NEHOSHET())
    box(f"Nikanor_pishpesh_{cote}_linteau", AX1 - 0.25, AX1, y0 - 0.3, y1 + 0.3, Z_EZI + H_PISHPESH, Z_EZI + H_PISHPESH + 0.4, "20_Azara", MAT_NEHOSHET())
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
# פָּתוּחַ בַּחוֹל » (Yoma 25a ; Rambam, Beit HaBe'hira 5:17). Elle enjambe
# le mur, qui s'interrompt sur sa largeur. Ce ne sont pas des portes de plus : Middot 1:4
# compte sept **שערים**, et Yoma 25a appelle celles-ci des פתחים.
# La Lishkat HaGola, bâtie derrière le mur, le perce : « וּמִשָּׁם מַסְפִּיקִים מַיִם לְכָל
# הָעֲזָרָה » (Middot 5:4) — une chambre qui alimente toute la cour s'ouvre sur elle.
# Les x du groupe du nord (Gazit, Gola, HaEtz) sont un CHOIX : voir plus bas, c'est la
# seule portée de mur assez longue pour les trois. HaGazit est la plus orientale, les
# lishkot se comptant d'est en ouest (Tosfot Yom Tov sur Middot 5:3, « מִדְּלֹא תְּנַן הָכָא
# סְמוּכִין לַמַּעֲרָב… שְׁמַעִינַן דְּהָכָא מִמִּזְרָח לְמַעֲרָב קָא חָשֵׁיב דֶּרֶךְ כְּנִיסַת הָעֲזָרָה »).
GAZIT_X0, GAZIT_X1 = -158, -138
GOLA_X0, GOLA_X1 = -182, -162
MOKED_X0, MOKED_X1 = PORTE_MOKED - 10, PORTE_MOKED + 10
PETAH_GOLA = (GOLA_X0 + GOLA_X1) / 2
# Le Beit HaMoked et la Lishkat HaGazit enjambent le mur : il s'interrompt sur leur
# largeur, et leurs baies sont dans leurs propres faces. Un mur qui les traverserait en
# ferait deux culs-de-sac de dix amot.
TRAVERSEES = {"nord": [(MOKED_X0, MOKED_X1), (GAZIT_X0, GAZIT_X1)], "sud": []}
OUVERTURES = {"nord": [PORTE_KORBAN, PORTE_NITZOTZ, PETAH_GOLA],
              "sud": [PORTE_MAYIM, PORTE_BEKHOROT, PORTE_DELEK]}
for (y0, y1, nm) in [(AY1, AY1 + T, "nord"), (AY0 - T, AY0, "sud")]:
    ouvertures = OUVERTURES[nm]
    coupures = sorted([(p - 5, p + 5) for p in ouvertures] + TRAVERSEES[nm])
    bornes = [AX0] + [u for coupure in coupures for u in coupure] + [AX1]
    for k in range(0, len(bornes) - 1, 2):
        box(f"Azara_mur_{nm}_{k // 2}", bornes[k], bornes[k + 1], y0, y1,
            Z_AZ, Z_AZ + H_MUR, "20_Azara")
    # Le cadre se pose du côté de la COUR : dehors, ces murs soutiennent dix amot de
    # remblai et leur pied est sur la terrasse du 'Heil — c'est aussi de ce côté-là que
    # le mur porte son socle et son couronnement.
    face = (AY1, -1) if nm == "nord" else (AY0, 1)
    for p in ouvertures:
        box(f"Azara_porte_{nm}_{p:+.0f}_linteau", p - 5, p + 5, y0, y1,
            Z_AZ + 20, Z_AZ + H_MUR, "20_Azara")
        # Six שערים aux battants d'or, Nikanor seule en bronze (Middot 2:3 ; Yoma 3:10) ;
        # ouverts dès l'aube (Tamid 3:7). Le פתח de HaGola n'en est pas un.
        shaar(f"Azara_porte_{nm}_{p:+.0f}", ("x", *face), p, Z_AZ, SOUS_CORNICHE, T,
              "20_Azara", metal=None if p == PETAH_GOLA else MAT_OR())
        if p != PETAH_GOLA:
            battants(f"Azara_porte_{nm}_{p:+.0f}_battants", p - 5, p + 5, y0, y1,
                     Z_AZ, 20, "20_Azara", MAT_OR())
SAILLIE = 12          # ce que les corps débordent du mur ; = la profondeur du Beit Avtinas
AXE_MUR_N = AY1 + T / 2
NORD_Y1 = AY1 + T + SAILLIE
NORD_Y0 = 2 * AXE_MUR_N - NORD_Y1     # symétrique du précédent par rapport à l'axe du mur
# Second rang : la Lishkat HaEtz est « אֲחוֹרֵי שְׁתֵּיהֶן » (Middot 5:4), donc en retrait
# derrière HaGazit et HaGola. C'est la seule chose de tout le pourtour qui sorte des
# douze amot de saillie, et c'est elle qui fixe désormais où se pose le soreg.
ETZ_Y0 = NORD_Y1 + ECART_LISHKA
ETZ_Y1 = ETZ_Y0 + SAILLIE
POURTOUR_Y1 = ETZ_Y1 + LISHKA_DEBORD   # la face bâtie la plus saillante du complexe
# Ezrat Israël → Ezrat Kohanim (Middot 2:6, R. Eliezer ben Yaakov) : « מַעֲלָה גְבוֹהָה אַמָּה
# וְהַדּוּכָן נָתוּן עָלֶיהָ וּבוֹ שָׁלֹשׁ מַעֲלוֹת שֶׁל חֲצִי חֲצִי אַמָּה, נִמְצֵאת עֶזְרַת כֹּהֲנִים גְּבוֹהָה
# מֵעֶזְרַת יִשְׂרָאֵל שְׁתֵּי אַמּוֹת וּמֶחֱצָה ». Une volée qui monte vers l'ouest, sur toute la largeur :
# la marche d'une ama, puis les trois demi-marches du Doukhan, la dernière affleurant la cour.
# Les boîtes emboîtées d'avant faisaient un mur de 2,5 amot en travers de la porte.
# Au nord, la volée s'arrête au Beit HaMoked, qui avance de douze amot dans la cour.
box("Marche_EzratIsrael_Cohanim", AX1 - 12, AX1 - 11, AY0, NORD_Y0, Z_EZI - 1, Z_EZI + 1, "20_Azara")
for i in range(3):
    box(f"Doukhan_{i}", AX1 - 12.5 - i * 0.5, AX1 - 12 - i * 0.5, AY0, NORD_Y0, Z_EZI - 1, Z_EZI + 1.5 + 0.5 * i, "20_Azara")

# Chambres du pourtour — 80_Lishkot. Elles sont adossées aux murs de l'Azara mais
# posées sur la terrasse du 'Heil (plus bas) : leur pied est à Z_EZN, dix amot sous le sol
# de la cour qu'elles bordent. Les faire partir de Z_AZ les laissait en l'air. Middot 1:7 le dit
# du Beit HaMoked : « אֶחָד פָּתוּחַ לַחֵיל וְאֶחָד פָּתוּחַ לָעֲזָרָה » — une porte à chaque
# niveau, donc un bâtiment qui les enjambe.

# Beit HaMoked : sur la porte nord la plus orientale, la troisième que compte
# Middot 1:5. Il est à cheval sur la limite du sacré et non posé derrière le mur —
# « אַרְבַּע לְשָׁכוֹת הָיוּ בְּבֵית הַמּוֹקֵד… שְׁתַּיִם בַּקֹּדֶשׁ וּשְׁתַּיִם בַּחֹל, וְרָאשֵׁי
# פִסְפָּסִין מַבְדִּילִין בֵּין קֹדֶשׁ לַחֹל » (Middot 1:6). D'où deux שערים opposés
# (Middot 1:7), et le mur de l'Azara s'interrompt sur sa largeur. CHOIX : ni la largeur
# (20 amot, comme les deux autres corps de porte) ni la hauteur (30 au-dessus de l'Azara)
# n'ont de source ; la hauteur passe le mur de 25, sans quoi les deux toits seraient
# coplanaires.
# La salle est au niveau de l'Azara, où ouvre le שער que Middot 2:3 change en or ; celui du
# 'Heil est en haut de vingt degrés, comme Sha'ar HaKorban. CHOIX : pris dedans, ces degrés
# couperaient la salle, et les quatre chambres de Middot 1:6 n'y tiendraient plus.
lishka("Beit_HaMoked", MOKED_X0, MOKED_X1, NORD_Y0, NORD_Y1, Z_EZN, Z_AZ + 30, "80_Lishkot",
       [Porte("N", *PORTE_SHAAR, Z_AZ), Porte("S", *PORTE_SHAAR, Z_AZ, metal=MAT_OR())])
battants("Beit_HaMoked_S_battants", PORTE_MOKED - 5, PORTE_MOKED + 5, NORD_Y0,
         NORD_Y0 + LISHKA_PAREMENT, Z_AZ, PORTE_SHAAR[1], "80_Lishkot", MAT_OR())
maake("Beit_HaMoked", MOKED_X0, MOKED_X1, NORD_Y0, NORD_Y1, Z_AZ + 30, "80_Lishkot")
escalier("Beit_HaMoked_escalier", PORTE_MOKED - 5, PORTE_MOKED + 5, NORD_Y1, NORD_Y1 + 10,
         Z_EZN, Z_AZ, "+y", "80_Lishkot")
MK_X0, MK_X1 = MOKED_X0 + LISHKA_PAREMENT, MOKED_X1 - LISHKA_PAREMENT
MK_Y0, MK_Y1 = NORD_Y0 + LISHKA_PAREMENT, NORD_Y1 - LISHKA_PAREMENT
# Le sol de la salle : la cour le donne jusqu'à la face extérieure du mur, sauf au-dessus de
# l'Ezrat Israël, deux amot et demie plus bas ; au-delà, la terrasse du 'Heil est à dix amot.
DESCENTE_TEVILA = (MK_X0, MK_X0 + 2, AY1 + T, AY1 + T + 3.5)
dalle_percee("Beit_HaMoked_sol_hol", MK_X0, MK_X1, AY1 + T, MK_Y1, Z_EZN, Z_AZ, "80_Lishkot",
             MAT_SOL(), [DESCENTE_TEVILA])
box("Beit_HaMoked_sol_ezrat_israel", X_DOUKHAN, MK_X1, MK_Y0, AY1 + T, Z_EZI - 1, Z_AZ,
    "80_Lishkot", MAT_SOL())
# « אַרְבַּע לְשָׁכוֹת… כְּקִיטוֹנוֹת פְּתוּחוֹת לִטְרַקְלִין, שְׁתַּיִם בַּקֹּדֶשׁ וּשְׁתַּיִם בַּחֹל » (Middot 1:6) : quatre
# chambrettes qui ouvrent sur la salle, deux de chaque côté de la limite, rangées le long
# des murs est et ouest entre les deux vestibules des שערים. Cotes : CHOIX.
KITON_L, KITON_P, KITON_H, CLOISON = 4.5, 5.5, 6, 0.5
KITONOT_Y = ((AXE_MUR_N - CLOISON - KITON_P, AXE_MUR_N - CLOISON),
             (AXE_MUR_N + CLOISON, AXE_MUR_N + CLOISON + KITON_P))
KITONOT_Y0, KITONOT_Y1 = KITONOT_Y[0][0] - CLOISON, KITONOT_Y[1][1] + CLOISON
for cote, mur, sens in (("O", MK_X0, 1), ("E", MK_X1, -1)):
    salle = mur + sens * KITON_L
    paroi_percee(f"Beit_HaMoked_kitonot_{cote}", *sorted((salle, salle + sens * CLOISON)),
                 KITONOT_Y0, KITONOT_Y1, Z_AZ, Z_AZ + KITON_H, "80_Lishkot", None,
                 [(sum(ky) / 2 - 1, sum(ky) / 2 + 1, Z_AZ, Z_AZ + KITON_H - 1) for ky in KITONOT_Y])
    for k, (ya, yb) in enumerate(((KITONOT_Y0, KITONOT_Y[0][0]), (KITONOT_Y[0][1], KITONOT_Y[1][0]),
                                  (KITONOT_Y[1][1], KITONOT_Y1))):
        box(f"Beit_HaMoked_kitonot_{cote}_cloison_{k}", *sorted((mur, salle)), ya, yb,
            Z_AZ, Z_AZ + KITON_H, "80_Lishkot")
    box(f"Beit_HaMoked_kitonot_{cote}_plafond", *sorted((mur, salle + sens * CLOISON)),
        KITONOT_Y0, KITONOT_Y1, Z_AZ + KITON_H, Z_AZ + KITON_H + CLOISON, "80_Lishkot")
# Sud-ouest, « לִשְׁכַּת טְלָאֵי קָרְבָּן » : vide. Sud-est, « לִשְׁכַּת עוֹשֵׂי לֶחֶם הַפָּנִים » : une table.
box("Beit_HaMoked_kiton_SE_table", MK_X1 - 3.5, MK_X1 - 1, KITONOT_Y[0][0] + 1,
    KITONOT_Y[0][1] - 1, Z_AZ, Z_AZ + 1.5, "80_Lishkot", MAT_MARBRE())
# Nord-est, « בָּהּ גָּנְזוּ בְנֵי חַשְׁמוֹנַאי אֶת אַבְנֵי הַמִּזְבֵּחַ שֶׁשִּׁקְּצוּם מַלְכֵי יָוָן » : les pierres entassées.
for k, (dx, dy, dz) in enumerate(((0.0, 0.0, 0), (1.8, 0.1, 0), (0.3, 1.2, 0), (1.6, 1.3, 0),
                                  (0.1, 0.3, 1), (1.6, 1.1, 1), (0.8, 0.8, 2))):
    x, y = MK_X1 - 3.3 + dx, KITONOT_Y[1][1] - 3 + dy
    box(f"Beit_HaMoked_kiton_NE_even_{k}", x, x + 1.4, y, y + 1, Z_AZ + dz, Z_AZ + dz + 1,
        "80_Lishkot", MAT_CHAUX())
# Nord-ouest, « בָּהּ יוֹרְדִים לְבֵית הַטְּבִילָה » : les degrés s'enfoncent vers la « מְסִבָּה הַהוֹלֶכֶת
# תַּחַת הַבִּירָה » (Middot 1:9), qui n'est pas modélisée ; ils s'arrêtent à trois amot et demie.
escalier("Beit_HaMoked_kiton_NO_descente", *DESCENTE_TEVILA, Z_AZ - 3.5, Z_AZ, "+y", "80_Lishkot")
# « מֻקָּף רוֹבָדִין שֶׁל אֶבֶן » (Middot 1:8) — Bartenura : « אִצְטַבָּאוֹת… מְשֻׁקָּעוֹת בַּכֹּתֶל… כְּעֵין מַעֲלוֹת
# זוֹ עַל זוֹ ». Deux gradins le long des murs, où dorment les anciens ; ils bordent les deux
# vestibules, cotes CHOIX.
for cote, mur, sens in (("O", MK_X0, 1), ("E", MK_X1, -1)):
    for vestibule, va, vb in (("S", MK_Y0, KITONOT_Y0), ("N", KITONOT_Y1, MK_Y1)):
        for rang, (saillie, zb, zh) in enumerate(((1.5, 0, 1), (0.75, 1, 2))):
            box(f"Beit_HaMoked_rovad_{vestibule}{cote}_{rang}", *sorted((mur, mur + sens * saillie)),
                va, vb, Z_AZ + zb, Z_AZ + zh, "80_Lishkot")
# « מָקוֹם הָיָה שָׁם, אַמָּה עַל אַמָּה, וְטַבְלָא שֶׁל שַׁיִשׁ וְטַבַּעַת הָיְתָה קְבוּעָה בָהּ » (Middot 1:9) :
# la dalle sous laquelle pendent les clefs de l'Azara. Sa place, près du שער : CHOIX.
TAVLA_X, TAVLA_Y = PORTE_MOKED, MK_Y0 + 3
box("Beit_HaMoked_tavla", TAVLA_X - 0.5, TAVLA_X + 0.5, TAVLA_Y - 0.5, TAVLA_Y + 0.5,
    Z_AZ, Z_AZ + 0.05, "80_Lishkot", MAT_MARBRE())
tore("Beit_HaMoked_tavla_tabaat", TAVLA_X, TAVLA_Y, Z_AZ + 0.09, 0.2, 0.04, "80_Lishkot", MAT_FER())
# « וְרָאשֵׁי פִסְפָּסִין מַבְדִּילִין בֵּין קֹדֶשׁ לַחֹל » (Middot 1:6) : la limite tracée au sol de la salle,
# sur l'axe du mur. Filet de marbre : CHOIX.
box("Beit_HaMoked_rashei_pispasin", MK_X0 + KITON_L + CLOISON, MK_X1 - KITON_L - CLOISON,
    AXE_MUR_N - 0.1, AXE_MUR_N + 0.1, Z_AZ, Z_AZ + 0.03, "80_Lishkot", MAT_MARBRE())
# --- Les trois lishkot du nord (Middot 5:3-4 ; Rambam, Beit HaBe'hira 5:17) : HaGazit,
#     HaGola, HaEtz, « וְגַג שְׁלָשְׁתָּן שָׁוֶה » — un seul niveau de toit pour les trois, à 30
#     au-dessus de l'Azara. Le groupe demande 44 amot de mur continu, et la portée à
#     l'ouest de Sha'ar HaNitzotz est la seule qui les offre : à l'est, les escaliers de
#     Sha'ar HaKorban et le Beit HaMoked ne laissent que 37,5. Aucune source ne donne
#     ces x (CHOIX) ; l'ORDRE, lui, est tenu — d'est en ouest, HaGazit puis HaGola,
#     HaEtz en second rang.
#     OUVERT — le nord des trois suit la girsa de Yoma 19a, celle du Rambam et la
#     préférence de Tosfot Yom Tov sur Middot 5:3 (« ונראה בעיני שגירסת הספר נשתבשה »),
#     contre le texte imprimé de Middot 5:4 qui les met au SUD. Mais le même Rambam
#     identifie Lishkat HaEtz à la Lishkat Parhedrin, que la scène place au sud d'après
#     le Yerushalmi (voir plus bas) : la scène tient l'avis que le Cohen Gadol avait
#     DEUX lishkot — ce que Yoma 19a laisse ouvert (« וְלֹא יָדַעְנָא » laquelle est au nord,
#     laquelle au sud) — et non que Parhedrin = HaEtz.
# Lishkat HaGazit, même parti que le Beit HaMoked : à cheval, la salle au niveau de la cour,
# un פתח sur le sacré et un sur le 'hol (Yoma 25a). Celui du 'hol ne peut pas être au nord,
# où la Lishkat HaEtz, « אֲחוֹרֵי שְׁתֵּיהֶן », est à une ama de son socle : il est à l'est, et
# ses degrés descendent dans les cinq amot qui la séparent de Sha'ar HaNitzotz. CHOIX,
# comme sa cote.
PETAH_HOL_GAZIT = (4, 8)
lishka("Lishkat_HaGazit", GAZIT_X0, GAZIT_X1, NORD_Y0, NORD_Y1, Z_EZN, Z_AZ + 30, "80_Lishkot",
       [Porte("S", *PORTE_SHAAR, Z_AZ),
        Porte("E", *PETAH_HOL_GAZIT, Z_AZ, centre=AY1 + T + PETAH_HOL_GAZIT[0] / 2)])
maake("Lishkat_HaGazit", GAZIT_X0, GAZIT_X1, NORD_Y0, NORD_Y1, Z_AZ + 30, "80_Lishkot")
box("Lishkat_HaGazit_sol_hol", GAZIT_X0 + LISHKA_PAREMENT, GAZIT_X1 - LISHKA_PAREMENT, AY1 + T,
    NORD_Y1 - LISHKA_PAREMENT, Z_EZN, Z_AZ, "80_Lishkot", MAT_SOL())
# « וּבַחֵצִי שֶׁל חֹל הָיוּ הַסַּנְהֶדְרִין יוֹשְׁבִין » (Rambam, Beit HaBe'hira 5:17), « כַּחֲצִי גֹרֶן עֲגֻלָּה, כְּדֵי
# שֶׁיְּהוּ רוֹאִין זֶה אֶת זֶה » (Sanhedrin 4:3) : le demi-cercle dans la moitié nord, son diamètre
# sur la limite du sacré. Seize amot de salle ne tiennent pas soixante et onze sièges sur
# un seul rang : trois gradins, CHOIX.
SANHEDRIN_X = (GAZIT_X0 + GAZIT_X1) / 2
for rang in range(3):
    r0, r1 = 3.2 + rang, 4.2 + rang
    for k in range(12):
        a0, a1 = math.pi * k / 12, math.pi * (k + 1) / 12
        prism(f"Lishkat_HaGazit_sanhedrin_{rang}_{k:02d}",
              [(SANHEDRIN_X + r * math.cos(a), AXE_MUR_N + r * math.sin(a))
               for r, a in ((r0, a0), (r1, a0), (r1, a1), (r0, a1))],
              Z_AZ, Z_AZ + 0.9 + 0.6 * rang, "80_Lishkot")
# Lishkat HaGola : « שָׁם הָיָה בוֹר קָבוּעַ, וְהַגַּלְגַּל נָתוּן עָלָיו, וּמִשָּׁם מַסְפִּיקִים מַיִם
# לְכָל הָעֲזָרָה » (Middot 5:4). Elle alimente la cour, elle s'ouvre donc dessus, et son
# unique פתח perce le mur nord — pas une porte de plus au compte de Middot 1:4.
# Elle reste posée sur la terrasse du 'Heil, sans enjamber la limite du sacré : rien ne
# le dit d'elle, et ce n'est pas nécessaire. Bâtie dans le 'hol mais ouverte au קדש, son
# intérieur est sanctifié et son toit ne l'est pas (Tosfot Yom Tov sur Middot 5:3,
# d'après Maaser Sheni 3:8 : « גגותיהן לא נתקדשו כלל, אע"פ שתוכן קדש כשפתוחות לקדש »).
# Sans conséquence pour un puits ; décisif pour le Beit HaParva, plus bas.
lishka("Lishkat_HaGola", GOLA_X0, GOLA_X1, AY1 + T, NORD_Y1, Z_EZN, Z_AZ + 30, "80_Lishkot", [],
       adossee="S")
maake("Lishkat_HaGola", GOLA_X0, GOLA_X1, AY1 + T, NORD_Y1, Z_AZ + 30, "80_Lishkot")
# Le בּוֹר au milieu du sol que la cour prolonge par le פתח, et le גַּלְגַּל posé dessus :
# margelle, potence et roue sur le modèle du mukhni du Kiyor, formes CHOIX.
BOR_X, BOR_Y = PETAH_GOLA, (AY1 + T + NORD_Y1 - LISHKA_PAREMENT) / 2
dalle_percee("Lishkat_HaGola_sol", GOLA_X0 + LISHKA_PAREMENT, GOLA_X1 - LISHKA_PAREMENT, AY1 + T,
             NORD_Y1 - LISHKA_PAREMENT, Z_EZN, Z_AZ, "80_Lishkot", MAT_SOL(),
             [(BOR_X - 1.5, BOR_X + 1.5, BOR_Y - 1.5, BOR_Y + 1.5)])
cyl("Lishkat_HaGola_bor_eau", BOR_X, BOR_Y, Z_EZN, Z_EZN + 2, 1.5, "80_Lishkot", MAT_EAU(), verts=24)
revolution("Lishkat_HaGola_bor_margelle", BOR_X, BOR_Y, Z_AZ,
           [(2.4, 0.0), (2.4, 1.1), (2.2, 1.3), (1.4, 1.3), (1.2, 1.1), (1.2, -0.3)],
           "80_Lishkot", verts=24, capots=False)
GALGAL_Z = Z_AZ + 4.6
for s in (-1, 1):
    cyl(f"Lishkat_HaGola_galgal_poteau_{s:+d}", BOR_X, BOR_Y + s * 2.8, Z_AZ, GALGAL_Z + 0.4, 0.22,
        "80_Lishkot", MAT_CEDRE(), verts=12)
cyl_between("Lishkat_HaGola_galgal_essieu", (BOR_X, BOR_Y - 2.8, GALGAL_Z), (BOR_X, BOR_Y + 2.8, GALGAL_Z),
            0.07, "80_Lishkot", MAT_FER(), verts=8)
tore("Lishkat_HaGola_galgal", BOR_X, BOR_Y, GALGAL_Z, 0.9, 0.1, "80_Lishkot", MAT_CEDRE(),
     rotation=(math.pi / 2, 0, 0))
for k in range(6):
    a = math.pi * k / 6
    cyl_between(f"Lishkat_HaGola_galgal_rayon_{k}",
                (BOR_X + 0.85 * math.cos(a), BOR_Y, GALGAL_Z + 0.85 * math.sin(a)),
                (BOR_X - 0.85 * math.cos(a), BOR_Y, GALGAL_Z - 0.85 * math.sin(a)),
                0.04, "80_Lishkot", MAT_CEDRE(), verts=6)
cyl_between("Lishkat_HaGola_galgal_corde", (BOR_X + 0.9, BOR_Y, GALGAL_Z), (BOR_X + 0.9, BOR_Y, Z_EZN + 2.5),
            0.04, "80_Lishkot", MAT_CHENE(), verts=6)
# Lishkat HaEtz, en second rang : « וְהִיא הָיְתָה אֲחוֹרֵי שְׁתֵּיהֶן » (Middot 5:4), sur la
# largeur des deux autres. Elle ne peut pas être dans l'Azara : entre le mur nord et le
# socle du Sanctuaire il ne reste que 17,5 amot (135 − 100, moitié), et à l'est de
# celui-ci le Beit HaMitba'haïm tient le terrain — pas de quoi loger un corps derrière
# un autre. Elle est donc entière dans le 'hol, ce que la Mishna ne dit pas d'elle
# (« שֵׁשׁ לְשָׁכוֹת הָיוּ בָעֲזָרָה », Middot 5:3) : c'est le prix du second rang, et il est
# écrit ici. R. Eliezer ben Yaakov : « שָׁכַחְתִּי מֶה הָיְתָה מְשַׁמֶּשֶׁת » — sans usage connu,
# pas d'ouverture connue non plus ; CHOIX, une porte sur le 'Heil.
lishka("Lishkat_HaEtz", GOLA_X0, GAZIT_X1, ETZ_Y0, ETZ_Y1,
       Z_EZN, Z_AZ + 30, "80_Lishkot", [Porte("N", *PORTE_LISHKA, Z_EZN)])
maake("Lishkat_HaEtz", GOLA_X0, GAZIT_X1, ETZ_Y0, ETZ_Y1, Z_AZ + 30, "80_Lishkot")

# Sha'ar HaNitzotz, la porte nord la plus occidentale — le seul corps de porte que la
# Mishna décrive en entier : « וּכְמִין אַכְסַדְרָה הָיָה, וַעֲלִיָּה בְנוּיָה עַל גַּבָּיו,
# שֶׁהַכֹּהֲנִים שׁוֹמְרִים מִלְמַעְלָן וְהַלְוִיִּם מִלְּמַטָּן, וּפֶתַח הָיָה לוֹ לַחֵיל »
# (Middot 1:5). Le Beit HaNitzotz est l'un des trois postes de garde des Cohanim
# (Middot 1:1 ; Tamid 1:1), et son aliyah regarde l'Azara.
NZ_X0, NZ_X1 = PORTE_NITZOTZ - 10, PORTE_NITZOTZ + 10
NZ_Y0, NZ_Y1, NZ_Z0 = AY1 + T, NORD_Y1, Z_AZ + 25
# La porte de l'Azara est au niveau de la cour, celle du 'Heil dix amot plus bas : le corps
# de porte est une cage d'escalier, ses vingt degrés sur toute sa largeur.
lishka("Beit_ShaarHaNitzotz", NZ_X0, NZ_X1, NZ_Y0, NZ_Y1, Z_EZN, NZ_Z0, "80_Lishkot",
       [Porte("N", *PORTE_SHAAR, Z_EZN)], adossee="S")
escalier("Beit_ShaarHaNitzotz_escalier", NZ_X0 + LISHKA_PAREMENT, NZ_X1 - LISHKA_PAREMENT,
         NZ_Y0, NZ_Y1 - LISHKA_PAREMENT, Z_EZN, Z_AZ, "+y", "80_Lishkot")
# Les degrés du פתח de 'hol de la Lishkat HaGazit, entre elle et ce corps de porte, à deux
# dixièmes de son socle : jointifs, leurs faces se confondraient.
GAZIT_PALIER_Y = AY1 + T + PETAH_HOL_GAZIT[0]
GAZIT_DEGRES_X1 = NZ_X0 - LISHKA_DEBORD - 0.2
box("Lishkat_HaGazit_palier", GAZIT_X1, GAZIT_DEGRES_X1, AY1 + T, GAZIT_PALIER_Y, Z_EZN, Z_AZ,
    "80_Lishkot", MAT_SOL())
escalier("Lishkat_HaGazit_escalier", GAZIT_X1, GAZIT_DEGRES_X1, GAZIT_PALIER_Y, GAZIT_PALIER_Y + 10,
         Z_EZN, Z_AZ, "+y", "80_Lishkot")
terrasse_de_porte("ShaarHaNitzotz", NZ_X0, NZ_X1, NZ_Y0, NZ_Y1, NZ_Z0,
                  (PORTE_NITZOTZ - 5, PORTE_NITZOTZ + 5), "80_Lishkot")
aliyah("BeitHaNitzotz", PORTE_NITZOTZ - 5, PORTE_NITZOTZ + 5, NZ_Y0, NZ_Y1, NZ_Z0, 12,
       "80_Lishkot", ("sud", PORTE_NITZOTZ - 1.5, PORTE_NITZOTZ + 1.5))

# Beit Avtinas : l'aliyah du corps de porte de Sha'ar HaMayim — la plus ORIENTALE des
# trois portes du sud —, creuse, murs d'une ama, fenêtre 3 x 4 au nord sur l'Azara.
# Source : Yerushalmi Yoma 1:5 (halakha)
# « על גבי שער המים היתה וסמוך ללשכתו היתה » — elle était au-dessus de Sha'ar HaMayim
# et contre sa lishka (celle du Cohen Gadol). Le Bavli Yoma 19a laisse la question
# ouverte (« ולא ידענא ») et sa baraïta situe la première tevila « בחול, על גבי שער
# המים, ובצד לשכתו » ; on suit le Yerushalmi, explicite.
# « על גבי » se prend au mot : la chambre est le haut d'un bâtiment de porte, et il
# fallait le bâtir. Sans lui elle pendait à 38,5 amot au-dessus du dallage, collée à
# la face sud du mur, sans rien dessous — le bloc qui flottait au plan 1. Son rez-de-
# chaussée est la cage d'escalier de la porte, comme à Sha'ar HaNitzotz.
BA_X0, BA_X1 = PORTE_MAYIM - 5, PORTE_MAYIM + 5
BA_Y0, BA_Y1, BA_Z0 = AY0 - T - SAILLIE, AY0 - T, Z_AZ + 25
SM_X0, SM_X1 = PORTE_MAYIM - 10, PORTE_MAYIM + 10
lishka("Beit_ShaarHaMayim", SM_X0, SM_X1, BA_Y0, BA_Y1, Z_EZN, BA_Z0, "80_Lishkot",
       [Porte("S", *PORTE_SHAAR, Z_EZN)], adossee="N")
escalier("Beit_ShaarHaMayim_escalier", SM_X0 + LISHKA_PAREMENT, SM_X1 - LISHKA_PAREMENT,
         BA_Y0 + LISHKA_PAREMENT, BA_Y1, Z_EZN, Z_AZ, "-y", "80_Lishkot")
# La baie déborde sur l'Ezrat Israël : sous le mur, le podium laisserait un trou au pied des degrés.
box("Beit_ShaarHaMayim_seuil", X_DOUKHAN, PORTE_MAYIM + 5, AY0 - T, AY0, Z_EZI - 1, Z_AZ,
    "80_Lishkot", MAT_SOL())
terrasse_de_porte("ShaarHaMayim", SM_X0, SM_X1, BA_Y0, BA_Y1, BA_Z0,
                  (BA_X0, BA_X1), "80_Lishkot")
aliyah("BeitAvtinas", BA_X0, BA_X1, BA_Y0, BA_Y1, BA_Z0, 12,
       "80_Lishkot", ("nord", PORTE_MAYIM - 1.5, PORTE_MAYIM + 1.5))
# « היו מחזירין אותה למכתשת… וכשהוא שוחק אומר הדק היטב » (Keritot 6b), « מכתשת של בית אבטינס »
# (Avot deRabbi Natan 41:12) ; les sammanim pesés « במשקל מכוון », chacun pilé à part (Rambam
# Klei HaMikdash 2:2, 2:5). Table, balance, bols, formes et matières : CHOIX.
AV_X0, AV_X1, AV_Y0, AV_Z = BA_X0 + 1, BA_X1 - 1, BA_Y0 + 1, BA_Z0 + 1
box("BeitAvtinas_table", AV_X0 + 0.2, AV_X0 + 2.2, AV_Y0 + 2, AV_Y0 + 8, AV_Z, AV_Z + 1.5,
    "80_Lishkot", MAT_MARBRE())
for k in range(11):
    x, y = AV_X0 + 0.7, AV_Y0 + 2.5 + 0.5 * k
    revolution(f"BeitAvtinas_sam_{k:02d}", x, y, AV_Z + 1.5,
               [(0.0, 0.0), (0.16, 0.0), (0.21, 0.2), (0.17, 0.2), (0.0, 0.07)],
               "80_Lishkot", MAT_TERRE_CUITE(), verts=16)
    cone(f"BeitAvtinas_sam_{k:02d}_poudre", x, y, AV_Z + 1.64, AV_Z + 1.78, 0.12, 0.03,
         "80_Lishkot", MAT_KETORET(), verts=16)
BAL_X, BAL_Y, BAL_Z = AV_X0 + 1.6, AV_Y0 + 7, AV_Z + 2.8
cyl("BeitAvtinas_moznayim_pied", BAL_X, BAL_Y, AV_Z + 1.5, BAL_Z, 0.05, "80_Lishkot",
    MAT_BRONZE(), verts=12)
cyl_between("BeitAvtinas_moznayim_fleau", (BAL_X, BAL_Y - 0.6, BAL_Z), (BAL_X, BAL_Y + 0.6, BAL_Z),
            0.03, "80_Lishkot", MAT_BRONZE(), verts=8)
for s in (-1, 1):
    y = BAL_Y + 0.6 * s
    cyl_between(f"BeitAvtinas_moznayim_corde_{s:+d}", (BAL_X, y, BAL_Z), (BAL_X, y, BAL_Z - 0.85),
                0.01, "80_Lishkot", MAT_BRONZE(), verts=6)
    revolution(f"BeitAvtinas_moznayim_plateau_{s:+d}", BAL_X, y, BAL_Z - 0.95,
               [(0.0, 0.0), (0.3, 0.1), (0.26, 0.1), (0.0, 0.03)], "80_Lishkot", MAT_BRONZE(), verts=16)
MORT_X, MORT_Y = (AV_X0 + AV_X1) / 2, AV_Y0 + 4
revolution("BeitAvtinas_makhteshet", MORT_X, MORT_Y, AV_Z,
           [(0.0, 0.0), (0.75, 0.0), (0.85, 1.3), (0.7, 1.3), (0.5, 0.45), (0.0, 0.4)],
           "80_Lishkot", MAT_BRONZE())
cone("BeitAvtinas_ketoret", MORT_X, MORT_Y, AV_Z + 0.4, AV_Z + 0.95, 0.5, 0.12, "80_Lishkot",
     MAT_KETORET())
cyl_between("BeitAvtinas_eli", (MORT_X + 0.1, MORT_Y, AV_Z + 0.7),
            (MORT_X + 0.45, MORT_Y + 0.35, AV_Z + 2.9), 0.12, "80_Lishkot", MAT_BRONZE(), verts=12)

# « וסמוך ללשכתו היתה » (Yerushalmi Yoma 1:5) : la lishka du Cohen Gadol touche le
# Beit Avtinas — donc à l'ouest de Sha'ar HaMayim, et non à l'ouest du mur sud. Elle
# s'en approche à ECART_LISHKA, ce qui laisse une ama d'air entre les deux socles :
# à une seule, les débords s'interpénétraient et leurs faces supérieures, coplanaires,
# clignotaient.
PARHEDRIN_X1 = SM_X0 - ECART_LISHKA
lishka("Lishkat_Parhedrin", PARHEDRIN_X1 - 15, PARHEDRIN_X1, BA_Y0, BA_Y1,
       Z_EZN, Z_AZ + 15, "80_Lishkot", [Porte("S", *PORTE_LISHKA, Z_EZN)], adossee="N")
maake("Lishkat_Parhedrin", PARHEDRIN_X1 - 15, PARHEDRIN_X1, BA_Y0, BA_Y1, Z_AZ + 15, "80_Lishkot")

# Les deux lishkot de Sha'ar Nikanor, dans l'Ezrat Israël, de part et d'autre de la
# porte est : « וּשְׁתֵּי לְשָׁכוֹת הָיוּ לוֹ, אַחַת מִימִינוֹ וְאַחַת מִשְּׂמֹאלוֹ, אַחַת לִשְׁכַּת
# פִּנְחָס הַמַּלְבִּישׁ, וְאַחַת לִשְׁכַּת עוֹשֵׂי חֲבִתִּין » (Middot 1:4 ; Rambam, Beit
# HaBe'hira 5:17). CHOIX : Pin'has au nord (la droite de qui entre), leur cote et leur
# hauteur, qu'aucune source ne donne. Elles s'ouvrent à l'ouest, sur la cour.
LISHKA_NIKANOR_X0 = -8
LISHKOT_NIKANOR = {"Pinchas_HaMalbish": (5, 20), "Osei_Chavitin": (-20, -5)}
for nm, (ny0, ny1) in LISHKOT_NIKANOR.items():
    lishka(f"Lishkat_{nm}", LISHKA_NIKANOR_X0, AX1, ny0, ny1, Z_EZI, Z_AZ + 20, "80_Lishkot",
           [Porte("O", *PORTE_LISHKA, Z_EZI)], adossee="E")
    maake(f"Lishkat_{nm}", LISHKA_NIKANOR_X0, AX1, ny0, ny1, Z_AZ + 20, "80_Lishkot")
# « וּפִנְחָס עַל הַמַּלְבּוּשׁ » (Shekalim 5:1), et « שִׁשָּׁה וְתִשְׁעִים חַלּוֹן הָיוּ בַּמִּקְדָּשׁ לְהָנִיחַ בָּהֶן
# הַבְּגָדִים… וְכֻלָּן סְתוּמוֹת » (Rambam, Klei HaMikdash 8:8). Le Rambam ne dit pas où : la scène en
# garnit la chambre de Pin'has, sur ce que ses murs tiennent autour du guichet de Nikanor.
# Placards fermés d'une ama : CHOIX.
CHALON, PAS_CHALON = 1.0, 1.35
PC_X0 = LISHKA_NIKANOR_X0 + LISHKA_PAREMENT
PC_Y0, PC_Y1 = (LISHKOT_NIKANOR["Pinchas_HaMalbish"][0] + LISHKA_PAREMENT,
                LISHKOT_NIKANOR["Pinchas_HaMalbish"][1] - LISHKA_PAREMENT)
for r in range(6):
    z = Z_EZI + 0.6 + PAS_CHALON * r
    for k in range(4):
        x = PC_X0 + 0.6 + PAS_CHALON * k
        box(f"Lishkat_Pinchas_HaMalbish_chalon_S{r}{k}", x, x + CHALON, PC_Y0, PC_Y0 + 0.15,
            z, z + CHALON, "80_Lishkot", MAT_CEDRE())
        box(f"Lishkat_Pinchas_HaMalbish_chalon_N{r}{k}", x, x + CHALON, PC_Y1 - 0.15, PC_Y1,
            z, z + CHALON, "80_Lishkot", MAT_CEDRE())
    for k in range(8):
        y = PC_Y0 + 0.4 + PAS_CHALON * k
        devant_guichet = any(y < b + 0.3 and y + CHALON > a - 0.3 for _, a, b in PISHPESHIM)
        if devant_guichet and z < Z_EZI + H_PISHPESH + 0.4:
            continue
        box(f"Lishkat_Pinchas_HaMalbish_chalon_E{r}{k}", AX1 - 0.15, AX1, y, y + CHALON,
            z, z + CHALON, "80_Lishkot", MAT_CEDRE())
# « חביתי כהן גדול לישתן ועריכתן ואפייתן בפנים » (Mena'hot 11:3), « עַל־מַחֲבַת בַּשֶּׁמֶן תֵּעָשֶׂה »
# (Vayikra 6:14), « וְהַמַּחֲבַת אֵין לָהּ כִּסּוּי » (Mena'hot 5:8) : la table où l'on pétrit, le foyer
# et la ma'havat plate posée sur ses braises. Formes et cotes : CHOIX.
OC_Y0, OC_Y1 = (LISHKOT_NIKANOR["Osei_Chavitin"][0] + LISHKA_PAREMENT,
                LISHKOT_NIKANOR["Osei_Chavitin"][1] - LISHKA_PAREMENT)
box("Lishkat_Osei_Chavitin_foyer", AX1 - 2.4, AX1 - 0.2, OC_Y0 + 0.4, OC_Y0 + 2.6,
    Z_EZI, Z_EZI + 1.1, "80_Lishkot")
box("Lishkat_Osei_Chavitin_braises", AX1 - 2.2, AX1 - 0.4, OC_Y0 + 0.6, OC_Y0 + 2.4,
    Z_EZI + 1.1, Z_EZI + 1.25, "80_Lishkot", braise("Braise"))
revolution("Lishkat_Osei_Chavitin_machvat", AX1 - 1.3, OC_Y0 + 1.5, Z_EZI + 1.25,
           [(0.0, 0.0), (0.85, 0.0), (0.9, 0.1), (0.84, 0.1), (0.0, 0.04)],
           "80_Lishkot", MAT_BRONZE(), verts=24)
box("Lishkat_Osei_Chavitin_table", AX1 - 1.6, AX1 - 0.2, OC_Y1 - 4, OC_Y1 - 1,
    Z_EZI, Z_EZI + 1.5, "80_Lishkot", MAT_MARBRE())

# --- Les trois lishkot du sud (Middot 5:3) : HaMelah, HaParva, HaMedi'hin. Elles sont
#     DANS l'Azara, contre la face intérieure du mur, et non sur la terrasse du 'Heil
#     comme celles du nord. Ce n'est pas une inconséquence, c'est le Beit HaParva qui
#     l'impose : « חָמֵשׁ טְבִילוֹת… וְכֻלָּן בַּקֹּדֶשׁ עַל בֵּית הַפַּרְוָה » (Yoma 3:3),
#     « הֱבִיאוּהוּ לְבֵית הַפַּרְוָה, וּבַקֹּדֶשׁ הָיְתָה » (Yoma 3:6). Quatre des cinq immersions
#     du Cohen Gadol se font sur son TOIT, et un toit bâti dans le 'hol n'est pas
#     sanctifié quand bien même l'intérieur l'est (Tosfot Yom Tov sur Middot 5:3,
#     d'après Maaser Sheni 3:8). Une Parva posée dehors mettrait l'avoda dans le 'hol.
#     Les deux autres suivent : Medi'hin par la mesiba qui monte au toit de Parva, et
#     Melah parce que Middot 5:3 les donne comme un même groupe.
#     Ordre d'est en ouest — Melah, Parva, Medi'hin — Tosfot Yom Tov, ibid. : « וְכֵן
#     רָאִיתִי בְּצִיּוּרוֹ שֶׁל פֵּירוּשׁ הָרַמְבַּ"ם שֶׁמְּסַדֵּר לִשְׁכַּת הַמֶּלַח סָמוּךְ לַמִּזְרָח ». Les x sont
#     un CHOIX : aucune source n'en donne, et ce qui reste libre le long du mur sud est
#     fixé par ses trois portes, par le kevesh et par la Mer. Melah est séparée des deux
#     autres par Sha'ar HaBekhorot — rien ne demande que les trois se touchent, sauf
#     Medi'hin et Parva, que la mesiba relie.
SAILLIE_INT = 10          # profondeur des corps intérieurs. Au-delà, le débord du socle
                          # mordrait sur le pied du kevesh : Rambam, Beit HaBe'hira 5:15,
                          # « וּבֵין הַכֶּבֶשׁ וּלְכֹתֶל דְּרוֹמִי י"ב אַמָּה וּמֶחֱצָה ».
H_LISHKA_INT = 22         # CHOIX : sous les 25 amot du mur, qui continue de se lire.
SUD_INT = (AY0, AY0 + SAILLIE_INT)
MELACH_X, PARVA_X, MEDICHIN_X = (-44, -26), (-92, -74), (-113, -96)
# La Lishkat HaMela'h ouvre à l'est : le pied du kevesh passe à une ama de son socle
# (Rambam, Beit HaBe'hira 5:15), et une porte nord ne donnait que sur le talus. Six amot,
# la face n'en ayant que huit entre le mur de l'Azara et le parement nord : CHOIX.
PORTES_SUD = {"HaMelach": Porte("E", 6, PORTE_LISHKA[1], Z_AZ),
              "HaParva": Porte("N", *PORTE_LISHKA, Z_AZ),
              "HaMedichin": Porte("N", *PORTE_LISHKA, Z_AZ)}
for nm, (x0, x1) in (("HaMelach", MELACH_X), ("HaParva", PARVA_X), ("HaMedichin", MEDICHIN_X)):
    lishka(f"Lishkat_{nm}", x0, x1, *SUD_INT, Z_AZ, Z_AZ + H_LISHKA_INT, "80_Lishkot",
           [PORTES_SUD[nm]], adossee="S")
# Ce que Middot 5:3 met dans chacune ; formes et cotes du mobilier : CHOIX.
# HaMela'h, « שָׁם הָיוּ נוֹתְנִים מֶלַח לַקָּרְבָּן » : le sel en tas contre le mur.
for k in range(4):
    cle = f"Lishkat_HaMelach_sel_{k}"
    cone(cle, MELACH_X[0] + LISHKA_PAREMENT + 1.6 + 3 * k, SUD_INT[0] + 1.7, Z_AZ,
         Z_AZ + 1.2 + 0.5 * alea(cle, 1), 1.1 + 0.4 * alea(cle), 0.2, "80_Lishkot", MAT_SEL(), verts=16)
# HaParva, « שָׁם הָיוּ מוֹלְחִין עוֹרוֹת קָדָשִׁים » : les peaux empilées sur une banquette, et le sel.
PV_X0, PV_X1 = PARVA_X[0] + LISHKA_PAREMENT, PARVA_X[1] - LISHKA_PAREMENT
box("Lishkat_HaParva_banquette", PV_X0 + 1, PV_X1 - 3, SUD_INT[0], SUD_INT[0] + 2.5,
    Z_AZ, Z_AZ + 1, "80_Lishkot")
for pile in range(3):
    for couche in range(6):
        cle = f"Lishkat_HaParva_peau_{pile}{couche}"
        x = PV_X0 + 1.6 + 3.2 * pile + (alea(cle) - 0.5) * 0.4
        y = SUD_INT[0] + 0.3 + (alea(cle, 1) - 0.5) * 0.3
        box(cle, x, x + 2.4, y, y + 1.9, Z_AZ + 1 + 0.09 * couche, Z_AZ + 1.08 + 0.09 * couche,
            "80_Lishkot", MAT_PEAU())
cone("Lishkat_HaParva_sel", PV_X1 - 2, SUD_INT[0] + 5, Z_AZ, Z_AZ + 1.1, 1.3, 0.2,
     "80_Lishkot", MAT_SEL(), verts=16)
# HaMedi'hin, « שֶׁשָּׁם הָיוּ מְדִיחִין קִרְבֵי הַקֳּדָשִׁים » : une auge d'eau contre le mur, deux tables.
MD_X0, MD_X1 = MEDICHIN_X[0] + LISHKA_PAREMENT, MEDICHIN_X[1] - LISHKA_PAREMENT
AUGE = (MD_X0 + 2, MD_X1 - 2, SUD_INT[0] + 0.5, SUD_INT[0] + 1.7)
dalle_trouee("Lishkat_HaMedichin_auge", MD_X0 + 1.5, MD_X1 - 1.5, SUD_INT[0], SUD_INT[0] + 2.2,
             Z_AZ, Z_AZ + 1.2, AUGE, "80_Lishkot")
box("Lishkat_HaMedichin_auge_eau", *AUGE, Z_AZ, Z_AZ + 0.9, "80_Lishkot", MAT_EAU())
for cote, xa in (("O", MD_X0), ("E", MD_X1 - 1.5)):
    box(f"Lishkat_HaMedichin_table_{cote}", xa, xa + 1.5, SUD_INT[0] + 3.5, SUD_INT[0] + 7,
        Z_AZ, Z_AZ + 1.5, "80_Lishkot", MAT_MARBRE())
# Le bain rituel sur le toit du Beit HaParva — « וְעַל גַּגָּהּ הָיָה בֵית הַטְּבִילָה לְכֹהֵן
# גָּדוֹל בְּיוֹם הַכִּפּוּרִים » (Middot 5:3). Maake parce que ce toit est un lieu de service
# (Rambam, Rotzea'h 11:2). Le drap de bouts tendu entre lui et le peuple (Yoma 3:4)
# n'est pas modélisé, non plus que les marches de la cuve : cote inventée, CHOIX.
Z_TOIT_PARVA = Z_AZ + H_LISHKA_INT
maake("Lishkat_HaParva", *PARVA_X, *SUD_INT, Z_TOIT_PARVA, "80_Lishkot")
MIKVE_L, MIKVE_P, MIKVE_MARGELLE = 8, 6, 1        # cuve au centre du toit, margelle d'une ama
MX_C, MY_C = sum(PARVA_X) / 2, sum(SUD_INT) / 2
MKX0, MKX1 = MX_C - MIKVE_L / 2, MX_C + MIKVE_L / 2
MKY0, MKY1 = MY_C - MIKVE_P / 2, MY_C + MIKVE_P / 2
e = MIKVE_MARGELLE
for cote, a, b, c, d in (("S", MKX0, MKX1, MKY0, MKY0 + e), ("N", MKX0, MKX1, MKY1 - e, MKY1),
                         ("O", MKX0, MKX0 + e, MKY0 + e, MKY1 - e),
                         ("E", MKX1 - e, MKX1, MKY0 + e, MKY1 - e)):
    box(f"Mikve_Parva_margelle_{cote}", a, b, c, d, Z_TOIT_PARVA, Z_TOIT_PARVA + 2, "80_Lishkot")
box("Mikve_Parva_eau", MKX0 + e, MKX1 - e, MKY0 + e, MKY1 - e,
    Z_TOIT_PARVA, Z_TOIT_PARVA + 1.7, "80_Lishkot", MAT_EAU())
# « וּמִשָּׁם מְסִבָּה עוֹלָה לְגַג בֵּית הַפַּרְוָה » (Middot 5:3 ; Rambam, Beit HaBe'hira 5:17) :
# la montée part de la Lishkat HaMedi'hin et débouche sur le toit du Beit HaParva.
# Tosfot Yom Tov (ibid.) la veut du côté de la Parva et à l'écart de l'endroit où l'on
# rince les entrailles — « שֶׁלֹּא יִתָּכֵן… שֶׁהַכֹּהֵן גָּדוֹל יַעֲלֶה לְבֵית טְבִילָתוֹ דֶּרֶךְ מָקוֹם
# שֶׁמְּדִיחִין בּוֹ ». D'où la tour engagée entre les deux corps, et ronde : מסיבה est une
# vis, un escalier droit ne porterait pas ce nom.
MESIBA_X = (MEDICHIN_X[1] + PARVA_X[0]) / 2
MESIBA_Y = SUD_INT[1] + 1        # la tour engage les deux corps et ressort dans la cour
cyl("Mesiba_Parva", MESIBA_X, MESIBA_Y, Z_AZ, Z_TOIT_PARVA + 1, 3.5, "80_Lishkot", verts=24)
cyl("Mesiba_Parva_corniche", MESIBA_X, MESIBA_Y, Z_TOIT_PARVA - 1, Z_TOIT_PARVA + 0.5, 4,
    "80_Lishkot", verts=24)

# Soreg (10 tefa'him = 1.67 ama) et 'Heil. Middot 2:3 : « לִפְנִים מִמֶּנּוּ הַחֵיל, עֶשֶׂר
# אַמּוֹת » — dix amot de dégagement, et les douze marches y sont. Le soreg se pose donc
# à 10 amot de la face bâtie la plus saillante, corps de porte compris : mesuré depuis
# le mur, il traversait le Beit HaMoked et le Beit Avtinas. La face la plus saillante
# est désormais celle de la Lishkat HaEtz, en second rang derrière HaGazit et HaGola —
# d'où POURTOUR_Y1. Le soreg reste un rectangle : la dissymétrie du bâti ne passe pas
# dans son tracé, elle se lit dans la largeur du 'Heil. Ses treize פרצות ont été
# rebouchées (« חָזְרוּ וּגְדָרוּם »), il est donc continu.
HEIL = 10
SX0, SX1 = AX0 - T - HEIL, EX1 + 5 + HEIL
SY0, SY1 = -(POURTOUR_Y1 + HEIL), POURTOUR_Y1 + HEIL
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
for cote, ya, yb in (("nord", AY1 + T, POURTOUR_Y1), ("sud", -POURTOUR_Y1, AY0 - T)):
    box(f"Heil_terrasse_{cote}", AX0 - T, SX1 - 4, ya, yb, Z_HAR, Z_EZN, "00_HarHabayit")
for i in range(HEIL_MARCHES):
    z = Z_HAR + 0.5 * (i + 1)
    box(f"Heil_marche_nord_{i:02d}", SX0 + 4, SX1 - 4, SY1 - 4 - 0.5 * (i + 1), SY1 - 4 - 0.5 * i, Z_HAR, z, "00_HarHabayit")
    box(f"Heil_marche_sud_{i:02d}", SX0 + 4, SX1 - 4, SY0 + 4 + 0.5 * i, SY0 + 4 + 0.5 * (i + 1), Z_HAR, z, "00_HarHabayit")
    box(f"Heil_marche_ouest_{i:02d}", SX0 + 4 + 0.5 * i, SX0 + 4 + 0.5 * (i + 1), -POURTOUR_Y1, POURTOUR_Y1, Z_HAR, z, "00_HarHabayit")
# De la terrasse aux portes latérales : dix amot, vingt marches de « רוּם מַעֲלָה חֲצִי אַמָּה
# וְשִׁלְחָהּ חֲצִי אַמָּה » (Middot 2:3), sur la largeur de la baie. Devant les trois portes
# sans corps de porte ; Nitzotz et Mayim montent dans le leur, et le Beit HaMoked a les
# siens devant sa porte du 'Heil.
for nm, x, cote in (("Korban", PORTE_KORBAN, "nord"), ("Bekhorot", PORTE_BEKHOROT, "sud"), ("Delek", PORTE_DELEK, "sud")):
    if cote == "nord":
        escalier(f"Escalier_{nm}", x - 5, x + 5, AY1 + T, AY1 + T + 10, Z_EZN, Z_AZ, "+y", "20_Azara")
    else:
        escalier(f"Escalier_{nm}", x - 5, x + 5, AY0 - T - 10, AY0 - T, Z_EZN, Z_AZ, "-y", "20_Azara")
# Couronnement des murs de l'Azara : une assise en débord sur la crête, qui saute
# les corps passant les 25 amot (Beit HaMoked, HaGazit, HaGola, et les terrasses
# de Sha'ar HaNitzotz et de Sha'ar HaMayim).
moulure("Azara_couronnement_est", AX1, AX1 + T, AY0 - T, AY1 + T, Z_AZ + H_MUR, CORNICHE, "20_Azara",
        mitres=("deborde", "deborde"))
moulure("Azara_couronnement_ouest", AX0 - T, AX0, AY0, AY1, Z_AZ + H_MUR, CORNICHE, "20_Azara",
        mitres=("bute", "bute"))
CORPS_NORD = [(PORTE_MOKED - 10.5, PORTE_MOKED + 10.5),
              (GAZIT_X0 - LISHKA_DEBORD, GAZIT_X1 + LISHKA_DEBORD),
              (GOLA_X0 - LISHKA_DEBORD, GOLA_X1 + LISHKA_DEBORD),
              (NZ_X0 - LISHKA_DEBORD, NZ_X1 + LISHKA_DEBORD)]
CORPS_SUD = [(SM_X0 - LISHKA_DEBORD, SM_X1 + LISHKA_DEBORD)]
moulure("Azara_couronnement_nord", AX0 - T, AX1, AY1, AY1 + T, Z_AZ + H_MUR, CORNICHE, "20_Azara",
        mitres=("deborde", "bute"), reserve=CORPS_NORD)
moulure("Azara_couronnement_sud", AX0 - T, AX1, AY0 - T, AY0, Z_AZ + H_MUR, CORNICHE, "20_Azara",
        mitres=("deborde", "bute"), reserve=CORPS_SUD)
# Le socle ne se pose que du côté de la cour : dehors, ces murs soutiennent dix amot de
# remblai et leur pied est sur la terrasse du 'Heil, pas sur le dallage de l'Azara. Il
# saute les baies — une porte n'a pas de pied de mur en travers — et les corps bâtis.
moulure("Azara_socle_est", AX1, AX1 + T, AY0 - T, AY1 + T, Z_AZ, SOCLE, "20_Azara",
        mitres=("deborde", "deborde"), cotes=(True, False), reserve=[(-5, 5)])
moulure("Azara_socle_ouest", AX0 - T, AX0, AY0, AY1, Z_AZ, SOCLE, "20_Azara",
        mitres=("bute", "bute"), cotes=(False, True))
for _nm, _y0, _y1, _cotes, _corps in (("nord", AY1, AY1 + T, (True, False), CORPS_NORD),
                                      ("sud", AY0 - T, AY0, (False, True), CORPS_SUD)):
    moulure(f"Azara_socle_{_nm}", AX0 - T, AX1, _y0, _y1, Z_AZ, SOCLE, "20_Azara",
            mitres=("deborde", "bute"), cotes=_cotes,
            reserve=_corps + [(p - 5, p + 5) for p in OUVERTURES[_nm]])
# Face est, celle que l'Ezrat Nashim regarde : ce mur-là descend jusqu'à la terrasse du
# 'Heil, et c'est là que son pied se pose. Trente-cinq amot de parement d'un seul tenant
# se lisent en gros œuvre ; le bandeau y porte, comme dans l'Ezrat Nashim, le niveau du
# dallage de l'Azara qui est derrière.
moulure("Azara_socle_est_bas", AX1, AX1 + T, AY0 - T, AY1 + T, Z_EZN, SOCLE, "20_Azara",
        mitres=("deborde", "deborde"), cotes=(False, True), reserve=[(-5, 5)])
moulure("Azara_bandeau_est", AX1, AX1 + T, AY0 - T, AY1 + T, Z_AZ, BANDEAU, "20_Azara",
        saillie=SAILLIE_BANDEAU, mitres=("deborde", "deborde"), cotes=(False, True),
        reserve=[(-5, 5)])

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
# quatrième pour les membres du tamid de la veille.
MAARAKHOT = (("gedola", -36, -28, -13, -5), ("ketoret", -48, -45, -19, -16),
             ("kiyum", -48, -45, -4, -1), ("kippour", -42, -39, -19, -16))
# « וְרֶוַח הָיָה בֵין הַגִּזְרִין, שֶׁהָיוּ מַצִּיתִין אֶת הָאֲלִיתָא מִשָּׁם » (Tamid 2:4 ; Rambam
# Temidin ouMousafin 2:7) : les bûches ne sont PAS jointives. C'est ce vide-là qui fait
# lire un bûcher — deux lits jointifs sous une dalle donnaient une palette sous un
# matelas, ce que la visite montrait de près.
R_GZIR, REWACH, PAS_LIT, LITS = 0.18, 0.15, 0.30, 3

def braises(nom, x0, x1, y0, y1, z, col, mat, maille=0.42, relief=0.22):
    """Bassin de gehalim : une nappe de charbons empilés, en un seul maillage.

    Une boîte n'a pas de silhouette de braise, et aucune matière ne la lui rend : la
    hauteur est donc dans la géométrie, tirée du nom pour que le tas soit le même à
    chaque construction. Le bord garde la maille exacte — lui aussi déformé, le bassin
    débordait sur les gzirin.
    """
    nx, ny = max(2, round((x1 - x0) / maille)), max(2, round((y1 - y0) / maille))
    rang = nx + 1
    place = lambda i, j: j * rang + i
    haut, bas = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            cle = f"{nom}_{i}_{j}"
            bord = i in (0, nx) or j in (0, ny)
            derive = 0.0 if bord else maille * 0.45
            x = x0 + (x1 - x0) * i / nx + (alea(cle, 1) - 0.5) * derive
            y = y0 + (y1 - y0) * j / ny + (alea(cle, 2) - 0.5) * derive
            haut.append((x, y, z + (0.0 if bord else relief * (0.2 + alea(cle, 3)))))
            bas.append((x, y, z - 0.35))
    n = len(haut)
    faces = []
    for j in range(ny):
        for i in range(nx):
            a, b, c, d = place(i, j), place(i + 1, j), place(i + 1, j + 1), place(i, j + 1)
            faces += [[a, b, c, d], [n + d, n + c, n + b, n + a]]
    for i in range(nx):
        faces.append([place(i + 1, 0), place(i, 0), n + place(i, 0), n + place(i + 1, 0)])
        faces.append([place(i, ny), place(i + 1, ny), n + place(i + 1, ny), n + place(i, ny)])
    for j in range(ny):
        faces.append([place(0, j), place(0, j + 1), n + place(0, j + 1), n + place(0, j)])
        faces.append([place(nx, j + 1), place(nx, j), n + place(nx, j), n + place(nx, j + 1)])
    return mesh_from_pydata(nom, haut + bas, faces, col, mat)

def maarakha(nm, xa, xb, ya, yb):
    """Trois lits de gzirin croisés, espacés, et le bassin de braises posé dedans."""
    for lit in range(LITS):
        z = Z_AZ + 9.0 + R_GZIR + lit * PAS_LIT
        mat = (MAT_BOIS_MAARAKHA(), MAT_BOIS_ROUSSI(), MAT_BOIS_CHARBON())[min(lit, 2)]
        long_x = lit % 2 == 0
        (a0, a1), (b0, b1) = ((ya, yb), (xa, xb)) if long_x else ((xa, xb), (ya, yb))
        pas = 2 * R_GZIR + REWACH
        n = max(2, int((a1 - a0 - 2 * R_GZIR) / pas) + 1)
        marge = (a1 - a0 - (n - 1) * pas) / 2
        for k in range(n):
            cle = f"Maarakha_{nm}_gzir_{lit}{k}"
            c = a0 + marge + k * pas + (alea(cle, 1) - 0.5) * REWACH * 0.7
            # Une bûche fendue n'a ni le diamètre ni la longueur de sa voisine, et le
            # bout qui dépasse est ce qui distingue un bûcher d'un caillebotis.
            d0, d1 = b0 - 0.55 * alea(cle, 2), b1 + 0.55 * alea(cle, 3)
            zc = z + (alea(cle, 4) - 0.5) * 0.06
            r = R_GZIR * (0.78 + 0.44 * alea(cle, 5))
            p0, p1 = (((d0, c, zc), (d1, c, zc)) if long_x else ((c, d0, zc), (c, d1, zc)))
            cyl_between(cle, p0, p1, r, "30_Mizbeach", mat, verts=10)
    braises(f"Maarakha_{nm}_gehalim", xa + 0.3, xb - 0.3, ya + 0.3, yb - 0.3,
            Z_AZ + 9.0 + R_GZIR * 1.4 + (LITS - 1) * PAS_LIT, "30_Mizbeach", braise("Braise"))

for nm, xa, xb, ya, yb in MAARAKHOT:
    maarakha(nm, xa, xb, ya, yb)
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
# --- La façade est n'est PAS dorée, et la guemara le raconte comme un refus : « סָבַר
#     לְמִשְׁעֲיֵיהּ בְּדַהֲבָא, אֲמַרוּ לֵיהּ רַבָּנַן שַׁבְקֵיהּ דְּהָכִי שַׁפִּיר טְפֵי דְּמִיחֲזֵי כְּאִידַּוְּותָא דְיַמָּא » — Hérode
#     voulut la plaquer d'or, les Sages l'en dissuadèrent, la pierre est plus belle
#     ainsi, « comme les vagues de la mer » (Baba Batra 4a ; Soucca 51b). Ce qui fait
#     l'extérieur est donc l'assise elle-même : shesh, marmara et kuchla en assises
#     alternées, une en débord une en retrait, déjà dans MAT_MARBRE_HERODE.
#     L'or reste où les sources le mettent : dedans (Middot 4:1), sur les portes, sur
#     la vigne et sur la couronne d'Hélène.
# Cinq poutres de chêne au-dessus de l'ouverture (Middot 3:7)
for i in range(5):
    L = 22 + i * 2
    box(f"Maltera_{i}", BX_E - 5.4, BX_E + 0.4, -L / 2, L / 2, Z_BAT + 41 + i * 2, Z_BAT + 42 + i * 2, "40_Ulam", MAT_CHENE_SCULPTE())
# --- Rovadim : les bandeaux en saillie qui ceinturent les murs de l'Oulam de bas en
#     haut (Rambam, Beit HaBe'hira 4:9). C'est la seule articulation que les sources
#     donnent à cette façade, et elle est horizontale.
#     La face du bâtiment ne porte aucune colonne : ni Middot 3:7-8 et 4:6-7, ni le
#     Rambam n'en mettent une dehors.
#     Ya'hin et Boaz sont dedans, dans l'Oulam, là où le Tanakh et ses commentateurs les
#     posent (voir plus bas). Les fûts de l'Oulam sont les כְּלוֹנָסוֹת de cèdre tendus du mur
#     du Heikhal à celui de l'Oulam (Middot 3:8).
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
# Le plafond de l'Oulam porte les mêmes cinq amot (Middot 4:6, le bâtiment est un seul
# bloc de 100). Au-dessus, plein : aucune source ne met de pièce là — les עליות sont sur la
# Maison chez Rashi, et l'Oulam-tour de Radak est du Premier Temple (CHOIX de suivre Rashi).
couches_middot("Ulam_plancher", BX_E - 16, BX_E - 5, -35, 35, Z_BAT + 40, "40_Ulam")
box("Ulam_masse", BX_E - 16, BX_E - 5, -35, 35, Z_BAT + 45, Z_TOIT, "40_Ulam", MAT_MARBRE_HERODE())
# « כְּלוֹנָסוֹת שֶׁל אֶרֶז הָיוּ קְבוּעִין מִכָּתְלוֹ שֶׁל הֵיכָל לְכָתְלוֹ שֶׁל אוּלָם, כְּדֵי שֶׁלֹּא יִבְעַט »
# (Middot 3:8) : les poutres rondes de cèdre tendues d'un mur à l'autre, sous le
# plafond, et trois poutres en travers qui en font les caissons — le « coffered cedar
# ceiling of the porch » du prompt 8, qui n'était qu'une dalle.
for k, y in enumerate(plage(-31.5, 31.5, 7)):
    cyl_between(f"Ulam_klonas_{k:02d}", (BX_E - 16, y, Z_BAT + 38.4), (BX_E - 5, y, Z_BAT + 38.4),
                0.5, "40_Ulam", MAT_CEDRE(), verts=12)
for k, x in enumerate((BX_E - 13.25, BX_E - 10.5, BX_E - 7.75)):
    box(f"Ulam_plafond_poutre_{k}", x - 0.4, x + 0.4, -35, 35, Z_BAT + 39.1, Z_BAT + 40, "40_Ulam", MAT_CEDRE())
# « וְשַׁרְשְׁרוֹת שֶׁל זָהָב הָיוּ קְבוּעוֹת בְּתִקְרַת הָאוּלָם, שֶׁבָּהֶן פִּרְחֵי כְהֻנָּה עוֹלִין וְרוֹאִין אֶת
# הָעֲטָרֹת » (Middot 3:8) : fixées dans les poutres du plafond et pendantes dans le vide de
# l'Oulam — « וְתוֹלוֹת לְמַטָּה בָּאוּלָם שֶׁאוֹחֲזִין בָּהֶן פִּרְחֵי כְהֻנָּה מְפַסְּגִין וְעוֹלִין » (R. Shemaya,
# cité par le Tossefot Yom Tov ad loc.) : on s'y agrippe et on monte. Elles descendent donc
# à hauteur de main, pas à mi-hauteur. Nombre et place : CHOIX — au-delà de y ±10 pour
# laisser la mire de Middot 2:4, et à l'écart des kotarot de Ya'hin et Boaz.
# Les עֲטָרוֹת de Zekharia 6:14 qu'on monte voir ne sont pas modelées : leur place est
# disputée — aux fenêtres de l'aliyah de l'Oulam (Melekhet Shlomo ad loc.), étage que ce
# blockout ne bâtit pas, ou aux fenêtres du Heikhal (Bartenura ad loc. ; Abravanel sur
# Zekharia 6:14), qui ne sont pas visibles de l'Oulam.
for k, y in enumerate((-24, -13, 13, 24)):
    chaine(f"Ulam_sharsheret_{k}", (BX_E - 10.5, y, Z_BAT + 39.4), (BX_E - 10.5, y, Z_BAT + 3.5),
           0.24, "40_Ulam", MAT_OR(), tube=0.075, majeur=8, mineur=5)
# Deux tables de l'Oulam (marbre au nord... CHOIX : marbre à droite en entrant = nord ; or au sud)
box("Ulam_table_marbre", -90, -88, 5.5, 6.5, Z_BAT, Z_BAT + 1.5, "40_Ulam", MAT_MARBRE())
box("Ulam_table_or", -90, -88, -6.5, -5.5, Z_BAT, Z_BAT + 1.5, "40_Ulam", MAT_OR())
# Ya'hin et Boaz (Melakhim I 7:15-22 ; Yirmiyahou 52:21-23 ; Divrei HaYamim II 3:15-17).
# Fût : 18 amot, donné trois fois et sans divergence — Melakhim I 7:15, Yirmiyahou 52:21,
# Melakhim II 25:17. Les 35 amot de Divrei HaYamim II 3:15 ne sont pas la hauteur d'une
# colonne mais la mesure des deux couchées au moment de la coulée, d'où « אֹרֶךְ » et non
# « קוֹמָה » : 18 + 18 = 36, moins l'ama que les deux demi-fûts perdent dans les kotarot
# (Radak et Rashi ad loc. ; Metsoudat David, « של שניהם יחד »).
# Kotéret : 5 amot (Melakhim I 7:16 ; Divrei HaYamim II 3:15). Les 3 amot de Melakhim II
# 25:17 sont les seules décorées — « שְׁתֵּי אַמּוֹת הַתַּחְתּוֹנוֹת שֶׁל כּוֹתָרוֹת הָיוּ שָׁווֹת לָעַמּוּד שֶׁלֹּא
# הָיָה בָּהֶם צוּרָה, וְשָׁלֹשׁ עֶלְיוֹנוֹת הֵן נִפְרָדוֹת לַחוּץ מֻקָּפוֹת שְׂבָכִים » (Baraïta des 49 Middot, citée
# par Radak sur 7:16). D'où le profil : 2 amot au nu du fût, 3 en saillie, et au sommet la
# calotte de « מַעֲשֵׂה שׁוּשַׁן » qui coiffe le creux du fût (Metsoudat David sur 7:19-20).
# Largeur : « כִּי הָעַמּוּדִים הָיוּ בְּרֹחַב אַרְבַּע אַמּוֹת » (Metsoudat David sur 7:19) — 4 amot, ce
# que donne aussi le tour de 12 amot (Melakhim I 7:15 ; Yirmiyahou 52:21) au π de trois
# d'Erouvin 76a. Élancement 4,5:1 : du bronze coulé, pas une tige.
# Place : dans l'Oulam. « וַיָּקֶם אֶת הָעַמֻּדִים לְאֻלָם הַהֵיכָל » (7:21), que Radak lit « כְּמוֹ
# בְּאוּלָם הַהֵיכָל », Ralbag « שֶׁהֱקִימָם בּוֹ », Metsoudat David « בָּאוּלָם שֶׁלִּפְנֵי הַהֵיכָל » et, sur
# Divrei HaYamim II 3:15, « בַּחֲלַל הָאוּלָם ». Le « מַעֲשֵׂה שׁוּשַׁן בָּאוּלָם » de 7:19 dit la même
# chose. Elles tiennent donc l'ouverture de 20 (Middot 3:7) par l'intérieur, face externe
# au nu du jambage, 12 amot de passage au milieu : la ligne de mire du mont des Oliviers
# vers la porte du Heikhal, large de 10, reste dégagée (Middot 2:4).
# Ya'hin à droite, soit au sud, Boaz à gauche (Metsoudat David sur 7:21).
AMOUD_X, AMOUD_Y, AMOUD_R, AMOUD_H = BX_E - 8.5, 8, 2, 18
KOTERET = [(AMOUD_R, 0.0), (AMOUD_R, 2.0), (2.5, 2.35), (2.9, 3.0), (3.1, 3.8), (3.0, 4.4),
           (2.55, 4.75), (AMOUD_R, 4.95), (1.15, 4.8), (0.0, 4.5)]
# Sept chaînettes par kotéret (Melakhim I 7:17), posées sur les trois amot en saillie
SHARSHEROT = ((2.45, 2.62), (2.75, 2.82), (3.05, 2.98), (3.35, 3.06),
              (3.65, 3.14), (3.95, 3.14), (4.25, 3.08))
for nom, y in (("Yakhin", -AMOUD_Y), ("Boaz", AMOUD_Y)):
    cyl(f"{nom}_fut", AMOUD_X, y, Z_BAT, Z_BAT + AMOUD_H, AMOUD_R, "40_Ulam", MAT_BRONZE(), verts=48)
    revolution(f"{nom}_koteret", AMOUD_X, y, Z_BAT + AMOUD_H, KOTERET, "40_Ulam", MAT_BRONZE(), verts=48)
    for k, (z, R) in enumerate(SHARSHEROT):
        tore(f"{nom}_sharsheret_{k}", AMOUD_X, y, Z_BAT + AMOUD_H + z, R, 0.06, "40_Ulam", MAT_BRONZE())
    # « וְהָרִמּוֹנִים מָאתַיִם טֻרִים סָבִיב » (7:20) : cent par rang, deux rangs, enfilés sur les
    # chaînettes comme des perles — « חֲרוּזִים בִּשְׁנֵי טוּרִים » (Metsoudat David ad loc.)
    for rang, k in enumerate((3, 5)):
        z, R = SHARSHEROT[k]
        for i in range(100):
            a = 2 * math.pi * (i + 0.5 * rang) / 100
            sphere(f"{nom}_rimon_{rang}{i:02d}", AMOUD_X + (R + 0.04) * math.cos(a), y + (R + 0.04) * math.sin(a),
                   Z_BAT + AMOUD_H + z, 0.09, "40_Ulam", MAT_BRONZE(), segs=6)
# La tablette d'or d'Hélène (Yoma 3:10), « שֶׁפָּרָשַׁת סוֹטָה כְּתוּבָה עָלֶיהָ », d'où le kohen
# copie la parasha. Sur l'or du mur est de l'Oulam, côté nord : CHOIX.
TAVLA_X = BX_E - 16 + EPAISSEUR_PLACAGE   # le nu de l'or sur le mur est du Heikhal, HX_E plus bas
box("Tavla_Helene", TAVLA_X, TAVLA_X + 0.08, 18.5, 21.5, Z_BAT + 5.5, Z_BAT + 7.5, "40_Ulam", MAT_OR())
for k in range(8):
    z = Z_BAT + 7.25 - 0.22 * k
    box(f"Tavla_Helene_ligne_{k}", TAVLA_X + 0.08, TAVLA_X + 0.11, 18.75 + (0.35 if k == 7 else 0), 21.25,
        z, z + 0.06, "40_Ulam", MAT_OR())
# --- Gefen Zahav (Middot 3:8) : « גֶּפֶן שֶׁל זָהָב הָיְתָה עוֹמֶדֶת עַל פִּתְחוֹ שֶׁל הֵיכָל, וּמֻדְלָה עַל
#     גַּבֵּי כְלוֹנָסוֹת. כָּל מִי שֶׁהוּא מִתְנַדֵּב עָלֶה, אוֹ גַרְגִּיר, אוֹ אֶשְׁכּוֹל, מֵבִיא וְתוֹלֶה בָהּ ».
#     מֻדְלָה, c'est palissée : un cep, des perches, des sarments tendus dessus. L'anneau
#     de tore ceint de vingt-quatre plaques radiales se lisait en rouage, et aucune
#     source ne met de cercle ici.
#     Ce que la michna donne d'autre, c'est le désordre : chacun apporte son or « כִּדְמוּת
#     גַּרְגִּיר אוֹ עָלֶה אוֹ אֶשְׁכּוֹל » (Bartenura ad loc.) et l'accroche — donc des feuilles de
#     tailles et d'inclinaisons différentes, des grappes inégales, jamais un pas régulier.
#     Le poids d'or accumulé est ce que dit R. Eliezer b. Tsadok par ses trois cents
#     kohanim (lashon havai, Bartenura ad loc. ; Houllin 90b).
#     Le cep monte du sol de l'Oulam le long de la perche sud — CHOIX, la michna ne dit
#     pas d'où il part. Les perches se posent hors des jambages de la porte de 10 et la
#     vigne tient au-dessus du linteau : la ligne de mire du mont des Oliviers vers la
#     porte du Heikhal (Middot 2:4) reste dégagée.
CONTOUR_FEUILLE = [(0.00, 0.00), (0.03, 0.13), (0.11, 0.25), (0.20, 0.28), (0.26, 0.20),
                   (0.34, 0.31), (0.45, 0.40), (0.54, 0.36), (0.58, 0.25), (0.66, 0.29),
                   (0.78, 0.25), (0.90, 0.15), (1.00, 0.00)]


def sarment(nom, points, r0, r1):
    """Sarment : tronçons au rayon décroissant le long d'une polyligne, nœuds aux coudes."""
    n = len(points) - 1
    for k in range(n):
        r = r0 + (r1 - r0) * (k + 1) / n
        cyl_between(f"{nom}_{k:02d}", points[k], points[k + 1], r, "40_Ulam", MAT_OR(), verts=8)
        if k % 3 == 1:
            sphere(f"{nom}_noeud_{k:02d}", *points[k], r * 1.15, "40_Ulam", MAT_OR(), segs=6)
    return points


def _sur_sarment(points, t):
    """Point et tangente à la fraction t d'une polyligne."""
    k = min(int(t * (len(points) - 1)), len(points) - 2)
    u = t * (len(points) - 1) - k
    a, b = Vector(points[k]), Vector(points[k + 1])
    return a + (b - a) * u, (b - a).normalized()


def rameau(z, y0, y1, cle, n=16, ampli=0.55):
    """Course d'un sarment le long d'un lit : il ondule autour de la traverse, il ne la double pas."""
    return [(VIGNE_XL + 0.28 + 0.16 * math.sin(4.1 * t + 6 * alea(cle)),
             y0 + (y1 - y0) * t,
             z + ampli * math.sin(2.4 * math.pi * t + 6 * alea(cle, 1)))
            for t in (k / n for k in range(n + 1))]


def feuille_de_vigne(nom, attache, taille, cle):
    """Feuille à cinq lobes et son pétiole, pliée en gouttière le long de la nervure."""
    axe = Vector((0.45 + 0.5 * alea(cle, 1),
                  1.7 * (alea(cle, 2) - 0.5),
                  0.9 * (alea(cle, 3) - 0.62))).normalized()
    base = Vector(attache) + axe * 0.3 * taille
    plan = (axe.cross(Vector((0, 1, 0))) + Vector((0.6, 0, 0.4 * (alea(cle, 4) - 0.5)))).normalized()
    cyl_between(f"{nom}_petiole", attache, tuple(base), 0.03, "40_Ulam", MAT_OR(), verts=5)
    limbe(nom, CONTOUR_FEUILLE, tuple(base), tuple(axe), tuple(plan), taille, 0.022,
          "40_Ulam", MAT_OR(), courbure=0.2)


def grappe(nom, attache, longueur, cle, baies=28):
    """Grappe : rafle courte et baies en cône serré, les plus grosses en haut."""
    haut = Vector(attache) + Vector((0.1, 0, -0.22 * longueur))
    cyl_between(f"{nom}_rafle", attache, tuple(haut), 0.05, "40_Ulam", MAT_OR(), verts=6)
    for k in range(baies):
        t = k / (baies - 1)
        large = 0.22 * longueur * (1 - t) ** 0.65
        a = 2.4 * k + 6 * alea(cle, k)
        p = haut + Vector((0.6 * large * math.cos(a) * (0.4 + alea(cle, 40 + k)),
                           large * math.sin(a),
                           -0.78 * longueur * t))
        sphere(f"{nom}_{k:02d}", p.x, p.y, p.z, 0.17 - 0.06 * t, "40_Ulam", MAT_OR(), segs=8)


def vrille(nom, depart, rayon, longueur, cle, tours=2.5, n=14):
    """Vrille : la spirale par où la vigne s'accroche — c'est elle qui la dit de loin."""
    d = Vector((0.35 * (alea(cle) - 0.5), 0.5 * (alea(cle, 1) - 0.5), -1)).normalized()
    u = d.cross(Vector((1, 0, 0))).normalized()
    v = d.cross(u)
    pts = []
    for k in range(n + 1):
        t = k / n
        a = 2 * math.pi * tours * t
        r = rayon * min(1.0, 3 * t)
        pts.append(tuple(Vector(depart) + d * (longueur * t)
                         + (u * (math.cos(a) - 1) + v * math.sin(a)) * r))
    for k in range(n):
        cyl_between(f"{nom}_{k:02d}", pts[k], pts[k + 1], 0.035, "40_Ulam", MAT_OR(), verts=5)


VIGNE_X, VIGNE_Y = -91.5, 5.5        # devant le nu du mur est du Heikhal ; perches hors des jambages
VIGNE_XL = VIGNE_X + 0.3             # les lits passent devant les perches
VIGNE_LITS = (Z_BAT + 25, Z_BAT + 29.5, Z_BAT + 34)
VIGNE_Z_HAUT = Z_BAT + 37.9          # sous les klonasot du plafond de l'Oulam
for s in (-1, 1):
    cyl_between(f"Vigne_perche{s:+d}", (VIGNE_X, s * VIGNE_Y, Z_BAT),
                (VIGNE_X, s * VIGNE_Y, VIGNE_Z_HAUT), 0.16, "40_Ulam", MAT_OR(), verts=10)
for k, z in enumerate(VIGNE_LITS):
    cyl_between(f"Vigne_lit_{k}", (VIGNE_XL, -VIGNE_Y, z), (VIGNE_XL, VIGNE_Y, z),
                0.13, "40_Ulam", MAT_OR(), verts=10)
    for s in (-1, 1):
        tore(f"Vigne_lien_{k}{s:+d}", VIGNE_X + 0.15, s * VIGNE_Y, z, 0.24, 0.05,
             "40_Ulam", MAT_OR(), rotation=(0, math.pi / 2, 0), majeur=12, mineur=6)

SARMENTS = [
    sarment("Vigne_cep",
            courbe((VIGNE_X + 0.4, -VIGNE_Y + 0.7, Z_BAT), (VIGNE_X + 0.9, -VIGNE_Y - 0.6, Z_BAT + 13),
                   (VIGNE_XL + 0.1, -VIGNE_Y + 0.5, VIGNE_LITS[0]), 12), 0.55, 0.26),
    sarment("Vigne_rameau_0", rameau(VIGNE_LITS[0], -VIGNE_Y + 0.5, VIGNE_Y - 0.4, "rameau0"), 0.24, 0.1),
    sarment("Vigne_montant_S",
            courbe((VIGNE_XL + 0.15, -4.4, VIGNE_LITS[0]), (VIGNE_XL + 0.7, -5.2, (VIGNE_LITS[0] + VIGNE_LITS[1]) / 2),
                   (VIGNE_XL + 0.2, -4.5, VIGNE_LITS[1]), 8), 0.22, 0.14),
    sarment("Vigne_rameau_1", rameau(VIGNE_LITS[1], -4.5, VIGNE_Y - 0.5, "rameau1"), 0.2, 0.09),
    sarment("Vigne_montant_N",
            courbe((VIGNE_XL + 0.2, 4.3, VIGNE_LITS[1]), (VIGNE_XL + 0.75, 5.2, (VIGNE_LITS[1] + VIGNE_LITS[2]) / 2),
                   (VIGNE_XL + 0.2, 4.5, VIGNE_LITS[2]), 8), 0.18, 0.12),
    sarment("Vigne_rameau_2", rameau(VIGNE_LITS[2], 4.5, -VIGNE_Y + 0.8, "rameau2", ampli=0.4), 0.17, 0.08),
    sarment("Vigne_rameau_3",
            courbe((VIGNE_XL + 0.3, -2.6, VIGNE_LITS[0] + 0.3), (VIGNE_XL + 0.9, -1.2, VIGNE_LITS[0] + 2.6),
                   (VIGNE_XL + 0.35, 0.9, VIGNE_LITS[1] - 0.4), 9), 0.14, 0.07),
    sarment("Vigne_rameau_4",
            courbe((VIGNE_XL + 0.3, 2.2, VIGNE_LITS[1] + 0.2), (VIGNE_XL + 0.95, 3.4, VIGNE_LITS[1] + 2.5),
                   (VIGNE_XL + 0.35, 1.6, VIGNE_LITS[2] - 0.3), 9), 0.13, 0.06),
]
# Les guirlandes : ce que la vigne fait retomber entre deux points d'un même lit, et
# d'où pendent les grappes.
GUIRLANDES = []
for k, (lit, ya, yb) in enumerate(((0, -4.9, -2.3), (0, 2.2, 5.0),
                                   (1, -4.4, -1.1), (1, -0.6, 2.5), (1, 3.0, 4.9),
                                   (2, -4.1, -0.5), (2, 0.3, 4.3))):
    z = VIGNE_LITS[lit]
    creux = 1.2 + 1.3 * alea("guirlande", k)
    GUIRLANDES.append(sarment(f"Vigne_guirlande_{k:02d}",
                              courbe((VIGNE_XL + 0.15, ya, z), (VIGNE_XL + 0.75, (ya + yb) / 2, z - 2 * creux),
                                     (VIGNE_XL + 0.15, yb, z), 10), 0.13, 0.09))
for k, points in enumerate(GUIRLANDES):
    for j, t in ((0, 0.5), (1, 0.22 + 0.12 * alea("grappe", k))):
        p, _ = _sur_sarment(points, t)
        grappe(f"Vigne_grappe_{k:02d}{j}", tuple(p), 1.0 + 1.2 * alea("grappe", 10 * k + j),
               f"grappe{k}{j}")
# La feuille et le fruit poussent sur le sarment de l'année, pas sur le vieux cep —
# et une feuille sur le cep descendait sous le linteau, dans la mire de Middot 2:4.
TIGES = SARMENTS[1:] + GUIRLANDES
for k in range(54):
    points = TIGES[(5 * k + k // len(TIGES)) % len(TIGES)]
    p, _ = _sur_sarment(points, 0.06 + 0.88 * alea("feuille", k))
    feuille_de_vigne(f"Vigne_feuille_{k:02d}", tuple(p), 0.8 + 0.7 * alea("feuille", 50 + k),
                     f"feuille{k}")
for k in range(9):
    points = TIGES[(3 * k + 1) % len(TIGES)]
    p, _ = _sur_sarment(points, 0.15 + 0.7 * alea("vrille", k))
    vrille(f"Vigne_vrille_{k}", tuple(p), 0.14 + 0.08 * alea("vrille", 10 + k),
           0.7 + 0.5 * alea("vrille", 20 + k), f"vrille{k}")

# Couronne (נִבְרֶשֶׁת) d'or de la reine Hélène au-dessus de l'entrée du Heikhal (Yoma 3:10).
# « בְּשָׁעָה שֶׁהַחַמָּה זוֹרַחַת נִיצוֹצוֹת יוֹצְאִין מִמֶּנָּה, וְהַכֹּל יוֹדְעִין שֶׁהִגִּיעַ זְמַן קְרִיאַת שְׁמַע »
# (Yoma 37b) : ce qu'elle doit faire, c'est renvoyer le premier soleil pris par
# l'ouverture est de l'Oulam. Un tore et huit cônes à six faces n'en renvoyaient rien ;
# il faut un bandeau poli, des fleurons creux tournés vers l'est et des gouttes sous le
# jonc. Middot n'en donne pas les cotes. Elle pend au premier lit de la vigne par trois
# chaînes à maillons (CHOIX) : un cylindre tendu se lisait en tige.
COURONNE_X, COURONNE_Z, COURONNE_R = -90.6, Z_BAT + 22, 1.2
revolution("Couronne_Helene", COURONNE_X, 0, COURONNE_Z,
           [(COURONNE_R - 0.14, 0.00), (COURONNE_R, 0.03), (COURONNE_R + 0.02, 0.12),
            (COURONNE_R - 0.04, 0.34), (COURONNE_R + 0.06, 0.52), (COURONNE_R + 0.02, 0.58),
            (COURONNE_R - 0.10, 0.55), (COURONNE_R - 0.06, 0.30), (COURONNE_R - 0.16, 0.10),
            (COURONNE_R - 0.14, 0.00)],
           "40_Ulam", MAT_OR(), verts=36, capots=False)
CONTOUR_FLEURON = [(0.00, 0.00), (0.16, 0.15), (0.40, 0.21), (0.64, 0.18), (0.86, 0.10), (1.00, 0.00)]
for k in range(12):
    a = 2 * math.pi * k / 12
    c, sn = math.cos(a), math.sin(a)
    limbe(f"Couronne_Helene_fleuron_{k:02d}", CONTOUR_FLEURON,
          (COURONNE_X + (COURONNE_R - 0.04) * c, (COURONNE_R - 0.04) * sn, COURONNE_Z + 0.5),
          (0.3 * c, 0.3 * sn, 1), (c, sn, 0), 0.5 if k % 2 else 0.75, 0.03,
          "40_Ulam", MAT_OR(), courbure=0.45)
for k in range(12):
    a = 2 * math.pi * (k + 0.5) / 12
    x, y = COURONNE_X + (COURONNE_R - 0.06) * math.cos(a), (COURONNE_R - 0.06) * math.sin(a)
    cyl_between(f"Couronne_Helene_goutte_{k:02d}_tige", (x, y, COURONNE_Z),
                (x, y, COURONNE_Z - 0.16), 0.02, "40_Ulam", MAT_OR(), verts=5)
    cone(f"Couronne_Helene_goutte_{k:02d}", x, y, COURONNE_Z - 0.30, COURONNE_Z - 0.14,
         0.0, 0.075, "40_Ulam", MAT_OR(), verts=8)
for k in range(3):
    a = math.radians(90 + 120 * k)
    y = (COURONNE_R - 0.02) * math.sin(a)
    chaine(f"Couronne_Helene_chaine_{k}",
           (COURONNE_X + (COURONNE_R - 0.02) * math.cos(a), y, COURONNE_Z + 0.45),
           (VIGNE_XL, y, VIGNE_LITS[0]), 0.075, "40_Ulam", MAT_OR())

# --- Mur est du Heikhal (6 amot) avec porte 10 × 20, quatre portes plaquées d'or
HX_E = BX_E - 16      # -92
# « וּשְׁנֵי פִשְׁפָּשִׁין הָיוּ לוֹ לַשַּׁעַר הַגָּדוֹל, אֶחָד בַּצָּפוֹן וְאֶחָד בַּדָּרוֹם. שֶׁבַּדָּרוֹם, לֹא נִכְנַס
# בּוֹ אָדָם מֵעוֹלָם… נָטַל אֶת הַמַּפְתֵּחַ וּפָתַח אֶת הַפִּשְׁפָּשׁ, וְנִכְנַס לְהַתָּא, וּמֵהַתָּא לַהֵיכָל »
# (Middot 4:2) : deux guichets de part et d'autre du grand portail, ouvrant sur le tא du
# coin. Celui du sud ne s'ouvre jamais (Yehezkel 44:2) ; il est bâti, pas percé.
PISHPASH = (6, 8, Z_BAT, Z_BAT + 4)        # largeur et hauteur : CHOIX, Middot n'en donne pas
paroi_percee("Heikhal_mur_est_N", HX_E - 6, HX_E, 5, 35, Z_BAT, Z_TOIT,
             "50_Heikhal", MAT_PIERRE(), [PISHPASH])
box("Heikhal_mur_est_S", HX_E - 6, HX_E, -35, -5, Z_BAT, Z_TOIT, "50_Heikhal")
box("Heikhal_mur_est_linteau", HX_E - 6, HX_E, -5, 5, Z_BAT + 20, Z_TOIT, "50_Heikhal")
if PORTES_HEIKHAL_OUVERTES:
    # Battants rabattus dans l'embrasure de 6 amot, contre les jambages. Ils portent les
    # figures que les versets leur donnent — « וְקָלַע כְּרוּבִים וְתִמֹרוֹת וּפְטֻרֵי צִצִּים וְצִפָּה
    # זָהָב » (Melakhim I 6:35 ; Ye'hezkel 41:25) : c'est le seul vantail du Temple que le
    # corpus sculpte, et il était une plaque d'or nue.
    for _cote, _y, _sens in (("S", -4.7, 1), ("N", 4.7, -1)):
        box(f"Heikhal_porte_{_cote}", HX_E - 5, HX_E - 0.3, _y - 0.3 * _sens, _y,
            Z_BAT, Z_BAT + 20, "50_Heikhal", MAT_OR())
        vantail_sculpte(f"Heikhal_porte_{_cote}_figure", ("x", _y, _sens),
                        HX_E - 4.7, HX_E - 0.6, Z_BAT + 0.6, Z_BAT + 19.4, "50_Heikhal")
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


Y_INT, Y_TA, Y_MUR_TA, Y_MES, Y_EXT = 10, 22, 27, 30, 35
X_TA_O = KK1 - 12                          # -171 : le nu extérieur des cellules d'ouest
Z_ETAGE_SOL = Z_BAT + 45            # 51 : sur la מעזיבה, les cinq amot de Middot 4:6
Z_ETAGE_HAUT = Z_ETAGE_SOL + 40     # 91 : le haut de ses murs, puis les cinq amot du toit
# --- Messiba (Middot 4:5) : « וּמְסִבָּה הָיְתָה עוֹלָה מִקֶּרֶן מִזְרָחִית צְפוֹנִית לְקֶרֶן צְפוֹנִית
#     מַעֲרָבִית, שֶׁבָּהּ הָיוּ עוֹלִים לְגַגּוֹת הַתָּאִים. הָיָה עוֹלֶה בַּמְּסִבָּה וּפָנָיו לַמַּעֲרָב. הָלַךְ עַל
#     כָּל פְּנֵי הַצָּפוֹן, עַד שֶׁהוּא מַגִּיעַ לַמַּעֲרָב… וְהָפַךְ פָּנָיו לַדָּרוֹם… הָלַךְ כָּל פְּנֵי מַעֲרָב…
#     וְהָפַךְ פָּנָיו לַמִּזְרָח. הָיָה מְהַלֵּךְ בַּדָּרוֹם, עַד שֶׁהוּא מַגִּיעַ לְפִתְחָהּ שֶׁל עֲלִיָּה »
#     — un seul circuit, coin nord-est → nord → ouest → sud → la porte de l'étage.
#     Middot 4:7 donne la bande du nord (מְסִבָּה 3, כֹּתֶל הַמְּסִבָּה 5) et celle du sud
#     (בֵּית הוֹרָדַת הַמַּיִם 3), toutes deux laissées en creux ici. À l'OUEST la michna ne bande
#     rien : les cent amot est-ouest sont pleines. Les trois amot du couloir d'ouest sont
#     donc prises sur les cinq du כֹּתֶל הַתָּא, une ama de maçonnerie de chaque côté — CHOIX.
#     La pente n'est donnée nulle part : elle se répartit sur les trois branches, CHOIX.
MESIBA_L, MESIBA_EP = 3, 1
X_MES_O0, X_MES_O1 = BX_O + 1, BX_O + 4        # le couloir d'ouest, dans le mur des ta'im
X_PORTE_ALIYAH = -113                          # où la branche sud atteint le niveau de l'étage
LEGS = (abs(BX_O - HK0), 2 * Y_MES, abs(X_PORTE_ALIYAH - BX_O))
Z_MES = [Z_BAT]
for L in LEGS:
    Z_MES.append(Z_MES[-1] + (Z_ETAGE_SOL - Z_BAT) * L / sum(LEGS))
PORTE_ALIYAH = (X_PORTE_ALIYAH, X_PORTE_ALIYAH + 3, Z_ETAGE_SOL, Z_ETAGE_SOL + 10)
PORTE_TA = (HK0 - 4, HK0 - 2, Z_BAT, Z_BAT + 4)      # le ta du coin nord-est, CHOIX

# --- Découpage nord-sud du corps (Middot 4:7) : « כֹּתֶל הַמְּסִבָּה חָמֵשׁ, וְהַמְּסִבָּה שָׁלֹשׁ,
#     כֹּתֶל הַתָּא חָמֵשׁ, וְהַתָּא שֵׁשׁ, כֹּתֶל הַהֵיכָל שֵׁשׁ, וְתוֹכוֹ עֶשְׂרִים » puis le miroir au sud,
#     où les trois amot sont בֵּית הוֹרָדַת הַמַּיִם — 70 en tout. Est-ouest, derrière le KhK, la
#     même michna donne כֹּתֶל הַהֵיכָל שֵׁשׁ, הַתָּא שֵׁשׁ, כֹּתֶל הַתָּא חָמֵשׁ.
#     Le blockout portait deux bandes pleines de quinze amot : ni ta'im, ni messiba.
# --- Ta'im. « שְׁלֹשִׁים וּשְׁמֹנָה תָאִים הָיוּ שָׁם, חֲמִשָּׁה עָשָׂר בַּצָּפוֹן, חֲמִשָּׁה עָשָׂר בַּדָּרוֹם,
#     וּשְׁמֹנָה בַּמַּעֲרָב. שֶׁבַּצָּפוֹן וְשֶׁבַּדָּרוֹם, חֲמִשָּׁה עַל גַּבֵּי חֲמִשָּׁה, וַחֲמִשָּׁה עַל גַּבֵּיהֶם.
#     וְשֶׁבַּמַּעֲרָב, שְׁלֹשָׁה עַל גַּבֵּי שְׁלֹשָׁה, וּשְׁנַיִם עַל גַּבֵּיהֶם » (Middot 4:3) : 15 + 15 + 8.
#     « הַתַּחְתּוֹנָה חָמֵשׁ, וְרֹבֶד שֵׁשׁ. וְהָאֶמְצָעִית שֵׁשׁ, וְרֹבֶד שֶׁבַע. וְהָעֶלְיוֹנָה שֶׁבַע » (4:4,
#     qui le tire de Melakhim I 6:6) : la cellule s'élargit de 5 à 7 parce que le mur du
#     Heikhal se retire d'une ama par étage (מִגְרָעוֹת, Melakhim I 6:6, « לְבִלְתִּי אֲחֹז
#     בְּקִירוֹת הַבָּיִת »). Les six de mur et six de cellule de 4:7 sont l'étage du MILIEU.
#     Ce que les sources ne donnent pas, et qui est donc CHOIX : la hauteur d'un étage
#     (les trois remplissent les quarante amot du rez, 12 de vide et une de dalle, la
#     dernière de deux), la longueur des cellules et l'épaisseur des refends.
TA_VIDE = 12
TA_ETAGES = ((Z_BAT, 5, 1), (Z_BAT + 13, 6, 1), (Z_BAT + 26, 7, 2))   # (sol, largeur, dalle)
Z_TA_TOIT = Z_BAT + 40                     # 46 : le toit des ta'im, au niveau du plafond du rez
TA_REFEND, TA_PORTE_L, TA_PORTE_H = 1, 2, 4
TA_TREMIE = 2                              # « וְאֶחָד לַתָּא שֶׁעַל גַּבָּיו » (4:3)


def travees(a0, a1, n, refend):
    """Découpe le segment a0→a1 en n travées égales séparées de `refend`, dans son sens."""
    sens = 1 if a1 > a0 else -1
    L = (abs(a1 - a0) - (n - 1) * refend) / n
    return [(a0 + sens * k * (L + refend), a0 + sens * (k * (L + refend) + L)) for k in range(n)]


def refend(name, mince0, mince1, long0, long1, z0, mince_en, col, mat):
    """Cloison entre deux ta'im, percée d'une porte au milieu (Middot 4:3).

    `mince_en` dit sur quel axe la cloison est mince ; la porte s'ouvre sur l'autre.
    """
    c = (long0 + long1) / 2
    demi = TA_PORTE_L / 2

    def pose(suffixe, a, b, zb, zh):
        if b - a <= 0:
            return
        if mince_en == "x":
            box(f"{name}_{suffixe}", mince0, mince1, a, b, zb, zh, col, mat)
        else:
            box(f"{name}_{suffixe}", a, b, mince0, mince1, zb, zh, col, mat)

    pose("a", min(long0, long1), c - demi, z0, z0 + TA_VIDE)
    pose("b", c + demi, max(long0, long1), z0, z0 + TA_VIDE)
    pose("linteau", c - demi, c + demi, z0 + TA_PORTE_H, z0 + TA_VIDE)


for cote, sg in (("N", 1), ("S", -1)):
    for etage, (z0, large, dalle) in enumerate(TA_ETAGES):
        ep = 12 - large                                   # 7, 6, 5 : le mur se retire
        ya, yb = sorted((sg * (Y_INT + ep), sg * Y_TA))
        # « וּבְקֶרֶן מִזְרָחִית צְפוֹנִית הָיוּ חֲמִשָּׁה פְתָחִים… וְאֶחָד לַמְּסִבָּה, וְאֶחָד לַפִּשְׁפָּשׁ,
        # וְאֶחָד לַהֵיכָל » (Middot 4:3) : le ta du coin nord-est perce le mur du Heikhal.
        vers_heikhal = [PORTE_TA] if (cote, etage) == ("N", 0) else []
        # Les fenêtres du Heikhal (Melakhim I 6:4) traversent le mur au troisième étage des
        # ta'im, le seul dont la tranche couvre leur hauteur : étroites ici, larges dehors.
        if z0 <= FENETRE_INT[1] and FENETRE_INT[2] <= z0 + TA_VIDE + dalle:
            vers_heikhal = vers_heikhal + baies_heikhal(*FENETRE_INT)
        paroi_percee(f"Corps_mur_HK_{cote}_{etage}", KK1, HK0,
                     *sorted((sg * Y_INT, sg * (Y_INT + ep))),
                     z0, z0 + TA_VIDE + dalle, "50_Heikhal", MAT_MARBRE_HERODE(), vers_heikhal)
        cellules = travees(HK0, KK1, 5, TA_REFEND)
        for k in range(4):
            xb = cellules[k][1]
            refend(f"Ta_{cote}_{etage}_refend_{k}", xb, xb - TA_REFEND, ya, yb, z0, "x",
                   "50_Heikhal", MAT_MARBRE_HERODE())
        dalle_percee(f"Ta_{cote}_{etage}_dalle", KK1, HK0, ya, yb, z0 + TA_VIDE,
                     z0 + TA_VIDE + dalle, "50_Heikhal", MAT_CEDRE(),
                     [(min(xa, xb) + 2, min(xa, xb) + 2 + TA_TREMIE, yb - 2 - TA_TREMIE, yb - 2)
                      for xa, xb in cellules])
# Ouest : trois cellules sur trois, deux au-dessus (Middot 4:3)
for etage, (z0, large, dalle) in enumerate(TA_ETAGES):
    ep = 12 - large
    xa, xb = X_TA_O, KK1 - ep
    n = 2 if etage == 2 else 3
    box(f"Corps_mur_HK_O_{etage}", xb, KK1, -Y_TA, Y_TA, z0, z0 + TA_VIDE + dalle,
        "50_Heikhal", MAT_MARBRE_HERODE())
    cellules = travees(-Y_TA, Y_TA, n, TA_REFEND)
    for k in range(n - 1):
        yb_ = cellules[k][1]
        refend(f"Ta_O_{etage}_refend_{k}", yb_, yb_ + TA_REFEND, xa, xb, z0, "y",
               "50_Heikhal", MAT_MARBRE_HERODE())
    dalle_percee(f"Ta_O_{etage}_dalle", xa, xb, -Y_TA, Y_TA, z0 + TA_VIDE,
                 z0 + TA_VIDE + dalle, "50_Heikhal", MAT_CEDRE(),
                 [(xa + 2, xa + 2 + TA_TREMIE, ya_ + 2, ya_ + 2 + TA_TREMIE) for ya_, _ in cellules],
                 alignees="y")
# Les murs qui enferment les ta'im, pleins sur toute la hauteur, et le toit des cellules
for cote, sg in (("N", 1), ("S", -1)):
    # Au sud la porte de l'étage traverse ; au nord, le ta du coin ouvre sur la messiba (4:3)
    vers_mesiba = [PORTE_ALIYAH] if cote == "S" else [PORTE_TA]
    passage = [PORTE_ALIYAH] if cote == "S" else []
    paroi_percee(f"Corps_mur_TA_{cote}", X_MES_O1, HK0, *sorted((sg * Y_TA, sg * Y_MUR_TA)),
                 Z_BAT, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE(),
                 baies_heikhal(*FENETRE_EXT) + vers_mesiba)
    paroi_percee(f"Corps_mur_{cote}_ext", BX_O, HK0, *sorted((sg * Y_MES, sg * Y_EXT)),
                 Z_BAT, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE(), baies_heikhal(*FENETRE_EXT))
    # Au-dessus du toit des ta'im, la bande redevient pleine jusqu'au mur du Heikhal
    paroi_percee(f"Corps_masse_{cote}", KK1, HK0, *sorted((sg * Y_INT, sg * Y_TA)),
                 Z_TA_TOIT + 5, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE(), passage)
    couches_middot(f"Ta_toit_{cote}", KK1, HK0, *sorted((sg * Y_INT, sg * Y_TA)), Z_TA_TOIT,
                   "50_Heikhal")
# Le nu extérieur d'ouest court sans interruption ; le mur intérieur du couloir, lui,
# s'ouvre là où les branches nord et sud de la messiba le traversent pour tourner.
box("Corps_mur_TA_O_ext", BX_O, X_MES_O0, -Y_EXT, Y_EXT, Z_BAT, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
# Ses bouts nord et sud sont déjà dans les murs extérieurs des bandes : seul le centre reste.
box("Corps_mur_TA_O_int", X_MES_O1, X_TA_O, -Y_MUR_TA, Y_MUR_TA, Z_BAT, Z_TOIT,
    "50_Heikhal", MAT_MARBRE_HERODE())
box("Corps_masse_O", X_TA_O, KK1, -Y_TA, Y_TA, Z_TA_TOIT + 5, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
couches_middot("Ta_toit_O", X_TA_O, KK1, -Y_TA, Y_TA, Z_TA_TOIT, "50_Heikhal")
rampe("Mesiba_nord", X_MES_O0, HK0, Y_MES - MESIBA_L, Y_MES, Z_MES[1], Z_MES[0], "+x",
      "50_Heikhal", MAT_MARBRE_HERODE(), MESIBA_EP)
rampe("Mesiba_ouest", X_MES_O0, X_MES_O1, -Y_MES, Y_MES, Z_MES[2], Z_MES[1], "+y",
      "50_Heikhal", MAT_MARBRE_HERODE(), MESIBA_EP)
rampe("Mesiba_sud", X_MES_O0, X_PORTE_ALIYAH, -Y_MES, -Y_MES + MESIBA_L, Z_MES[2], Z_MES[3], "+x",
      "50_Heikhal", MAT_MARBRE_HERODE(), MESIBA_EP)
# Le couloir est couvert : sans cela il ouvre une fente de quatre-vingt-dix amot sur le
# ciel au flanc du bâtiment. La hauteur sous plafond n'est pas donnée : huit amot au-dessus
# du haut de chaque branche, le reste plein jusqu'au toit — CHOIX.
for nom, xa, xb, ya, yb, z in (
        ("nord", X_MES_O0, HK0, Y_MES - MESIBA_L, Y_MES, Z_MES[1] + 8),
        ("ouest", X_MES_O0, X_MES_O1, -Y_MES, Y_MES, Z_MES[2] + 8),
        ("sud", X_MES_O0, X_PORTE_ALIYAH, -Y_MES, -Y_MES + MESIBA_L, Z_MES[3] + 8)):
    box(f"Mesiba_{nom}_couverture", xa, xb, ya, yb, z, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
# Le bout est de la bande sud n'est pas la messiba mais בֵּית הוֹרָדַת הַמַּיִם (Middot 4:7) :
# un canal, plein au-dessus. Les trois amot du palier restent ouvertes jusqu'à la porte.
box("Beit_horadat_hamayim_masse", PORTE_ALIYAH[1], HK0, -Y_MES, -Y_MES + MESIBA_L,
    Z_BAT + 6, Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
box("Mesiba_palier", *PORTE_ALIYAH[:2], -Y_MES, -Y_MUR_TA,
    PORTE_ALIYAH[3], Z_TOIT, "50_Heikhal", MAT_MARBRE_HERODE())
# « וּבְפִתְחָהּ שֶׁל עֲלִיָּה הָיוּ שְׁנֵי כְלוֹנָסוֹת שֶׁל אֶרֶז, שֶׁבָּהֶן הָיוּ עוֹלִין לְגַגָּהּ שֶׁל עֲלִיָּה »
# (Middot 4:5) : deux perches de cèdre à la porte, et donc une trémie dans le toit au-dessus.
for k, x in enumerate((X_PORTE_ALIYAH + 1, X_PORTE_ALIYAH + 2)):
    cyl(f"Klonas_aliyah_{k}", x, -Y_INT + 1.5, Z_ETAGE_SOL, Z_ETAGE_HAUT + 1, 0.4,
        "50_Heikhal", MAT_CEDRE(), verts=12)


# --- L'étage. Le corps montait plein de 46 à 96 ; Middot 4:5-6 y met une pièce.
#     « וְגֹבַהּ שֶׁל עֲלִיָּה אַרְבָּעִים אַמָּה » (4:6), et le Rambam la dit bâtie : « וַעֲלִיָּה בְּנוּיָה
#     עַל גַּבָּיו, גֹּבַהּ כְּתָלֶיהָ אַרְבָּעִים אַמָּה » (Beit HaBe'hira 4:2). Elle est praticable : porte
#     au sud au bout de la מְסִבָּה, deux perches de cèdre pour monter sur son toit, une ligne
#     de bornes au sol qui y rejoue la séparation d'en bas, et des trappes vers le Kodesh
#     HaKodashim par où l'on descendait les ouvriers en caisses (4:5).
#     Au-dessus du Heikhal et du Kodesh HaKodashim, pas de l'Oulam : c'est là que Middot 4:5
#     la meuble, et Rashi (sur Divrei HaYamim II 3:4) met les עליות du Premier Temple
#     au-dessus de la Maison — « מִקַּרְקָעִית הַבַּיִת עַד קֵרוּי עֲלִיָּה רִאשׁוֹנָה שְׁלֹשִׁים, וּמֵעֲלִיָּה
#     לַעֲלִיָּה עַד גַּג הָעֶלְיוֹן תִּשְׁעִים ». Metsoudat David donne la même lecture en second.
#     Radak les met dans l'Oulam seul : minorité, et sur le Premier Temple.
# Les לוּלִין percent le plancher au-dessus du Kodesh HaKodashim. Middot 4:5 n'en donne ni
# le nombre ni la place : deux trémies de deux amot sur l'axe, CHOIX.
LOULIN = [(KK1 + 6, KK1 + 8, -1, 1), (KK1 + 12, KK1 + 14, -1, 1)]
couches_middot("Corps_plancher", KK1, HK0, -10, 10, Z_BAT + 40, "50_Heikhal", LOULIN)
couches_middot("Corps_toit", KK1, HK0, -10, 10, Z_ETAGE_HAUT, "50_Heikhal",
               [(X_PORTE_ALIYAH + 0.5, X_PORTE_ALIYAH + 2.5, -Y_INT + 0.5, -Y_INT + 2.5)])
# « רָאשֵׁי פִסְפָּסִין מַבְדִּילִים בָּעֲלִיָּה בֵּין הַקֹּדֶשׁ לְבֵין קֹדֶשׁ הַקֳּדָשִׁים » (Middot 4:5) : la ligne
# de bornes qui rejoue à l'étage l'ama de Traksin, restée en creux au-dessous.
for k, y in enumerate(plage(-9.5, 9.5, 1.0)):
    box(f"Pispassin_{k:02d}", TR1, TR0, y - 0.2, y + 0.2, Z_ETAGE_SOL, Z_ETAGE_SOL + 0.3,
        "50_Heikhal", MAT_MARBRE_HERODE())
# --- « כָּל הַבַּיִת טוּחַ בְּזָהָב, חוּץ מֵאַחַר הַדְּלָתוֹת » (Middot 4:1 ; Rambam Beit
#     HaBe'hira 4:7 : « וכל ההיכל היה טפוח זהב חוץ ממקום אחורי הדלתות »).
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

# --- Ligne de toit (Middot 4:6) : מַעֲקֶה de 3 amot, puis אַמָּה כָּלֵה עוֹרֵב. Les deux
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
# Le kaleh orev est une LAME, pas une rangée de pointes. Le Rambam le décrit sur place
# (commentaire sur Middot 4:6) : « שֶׁהָיָה מַקִּיף הַהֵיכָל לְמַעְלָה מִן הַמַּעֲקֶה מֵאַרְבַּע רוּחוֹתָיו
# בְּחֶשֶׁק שֶׁל בַּרְזֶל גֹּבַהּ אַמָּה חַד כְּמוֹ הַסַּיִף, כְּדֵי שֶׁלֹּא יֵשֵׁב עָלָיו שׁוּם עוֹף עַל הַהֵיכָל,
# מִפְּנֵי שֶׁנֶּחְתָּכִים רַגְלָיו בְּאוֹתוֹ הַסַּיִף » — un cerclage de FER d'une ama, continu sur les
# quatre côtés, affilé comme une épée. Le blockout en faisait une lisse de bronze
# hérissée d'une pointe par ama — une lecture qui ne vient d'aucune source juive.
# Le fil n'est pas modélisé : à 0,05 ama d'épaisseur la lame tient dans deux
# pixels sur la façade entière, et l'affûtage est sous le pixel.
LAME_EP = 0.10
for suffixe, xa, xb, ya, yb in POURTOUR_TOIT:
    box(f"Maake_{suffixe}", xa, xb, ya, yb, Z_TOIT, Z_TOIT + MAAKE_H, "50_Heikhal", MAT_MARBRE_HERODE())
    if (xb - xa) >= (yb - ya):
        c = (ya + yb) / 2
        box(f"Kaleh_orev_{suffixe}", xa, xb, c - LAME_EP / 2, c + LAME_EP / 2,
            Z_TOIT + MAAKE_H, Z_FAITE, "50_Heikhal", MAT_FER_LAME())
    else:
        c = (xa + xb) / 2
        box(f"Kaleh_orev_{suffixe}", c - LAME_EP / 2, c + LAME_EP / 2, ya, yb,
            Z_TOIT + MAAKE_H, Z_FAITE, "50_Heikhal", MAT_FER_LAME())

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

# --- Les deux Parokhot (Yoma 5:1) : extérieure agrafée au SUD, intérieure au NORD.
#     « אָרְכָּהּ אַרְבָּעִים אַמָּה וְרָחְבָּהּ עֶשְׂרִים אַמָּה », « עָבְיָהּ טֶפַח » (Shekalim 8:5).
PAROKHET_EP = 1 / 6            # טפח : l'épaisseur que la michna donne à l'étoffe
PAROKHET_CHAMP = (2.0, 38.0)   # bas et haut du champ figuré, en amot au-dessus de Z_BAT
PAROKHET_RANGS, PAROKHET_COLONNES = 6, 4
PAROKHET_SAILLIE = 0.12        # ce dont une figure TISSÉE bombe l'étoffe : 6 cm, pas un relief
LISERE_PAROKHET = 0.9          # largeur de la lisière qui borde le champ


def creature_ailee(nom, paroi, u, z0, h, col, mat):
    """Créature ailée de la frise : corps dressé, deux ailes levées, tête de profil sans
    traits, queue étalée. « כְּרֻבִים » de Ex. 26:31 vaut « צִיּוּרִין שֶׁל בְּרִיּוֹת » (Rashi)."""
    e = PAROKHET_SAILLIE
    corps = [(u - 0.11 * h, z0 + 0.06 * h), (u + 0.11 * h, z0 + 0.06 * h),
             (u + 0.075 * h, z0 + 0.20 * h), (u + 0.055 * h, z0 + 0.42 * h),
             (u + 0.105 * h, z0 + 0.58 * h), (u + 0.085 * h, z0 + 0.66 * h),
             (u - 0.085 * h, z0 + 0.66 * h), (u - 0.105 * h, z0 + 0.58 * h),
             (u - 0.055 * h, z0 + 0.42 * h), (u - 0.075 * h, z0 + 0.20 * h)]
    _relief_profil(f"{nom}_corps", paroi, corps, 0.0, e, col, mat)
    _relief_profil(f"{nom}_tete", paroi, _profil_tete(u + 0.08 * h, z0 + 0.66 * h, 0.10 * h, 1),
                   0.0, e * 0.9, col, mat)
    _relief_profil(f"{nom}_queue", paroi,
                   [(u - 0.06 * h, z0 + 0.10 * h), (u + 0.06 * h, z0 + 0.10 * h),
                    (u + 0.20 * h, z0), (u - 0.20 * h, z0)], 0.0, e * 0.8, col, mat)
    for sens in (-1, 1):
        _relief_limbe(f"{nom}_aile_{'N' if sens > 0 else 'S'}", paroi, u + sens * 0.06 * h,
                      z0 + 0.44 * h, sens * 74, 0.42 * h, AILE, e * 0.7, col, mat, courbure=0.12)


def lion(nom, paroi, u, z0, h, col, mat):
    """Le lion de la frise — « וּפְנֵי כְפִיר » (Ye'hezkel 41:19), et le lion du revers d'un
    maassé 'hoshev (Yoma 72b). De profil, marchant vers les u croissants."""
    e = PAROKHET_SAILLIE
    corps = [(u - 0.44 * h, z0 + 0.30 * h), (u - 0.30 * h, z0 + 0.58 * h),
             (u + 0.10 * h, z0 + 0.62 * h), (u + 0.34 * h, z0 + 0.56 * h),
             (u + 0.40 * h, z0 + 0.34 * h), (u + 0.16 * h, z0 + 0.30 * h),
             (u - 0.16 * h, z0 + 0.28 * h)]
    _relief_profil(f"{nom}_corps", paroi, corps, 0.0, e, col, mat)
    for k, du in enumerate((-0.36, -0.22, 0.14, 0.28)):
        _relief_profil(f"{nom}_patte_{k}", paroi,
                       [(u + (du - 0.05) * h, z0), (u + (du + 0.05) * h, z0),
                        (u + (du + 0.05) * h, z0 + 0.34 * h), (u + (du - 0.05) * h, z0 + 0.34 * h)],
                       0.0, e * 0.8, col, mat)
    _relief_profil(f"{nom}_criniere", paroi,
                   _profil_corolle(u + 0.32 * h, z0 + 0.60 * h, 0.16 * h, 9), 0.0, e * 0.75, col, mat)
    _relief_profil(f"{nom}_tete", paroi, _profil_tete(u + 0.34 * h, z0 + 0.58 * h, 0.11 * h, 1),
                   0.0, e, col, mat)
    _relief_profil(f"{nom}_queue", paroi,
                   [(u - 0.44 * h, z0 + 0.50 * h), (u - 0.38 * h, z0 + 0.56 * h),
                    (u - 0.44 * h, z0 + 0.80 * h), (u - 0.50 * h, z0 + 0.78 * h)],
                   0.0, e * 0.7, col, mat)


def frise_parokhet(nom, paroi, col):
    """« מַעֲשֵׂה חֹשֵׁב יַעֲשֶׂה אֹתָהּ כְּרֻבִים » (Ex. 26:31) : créatures ailées et lions en
    alternance, tissés dans les mêmes quatre laines — jamais d'or (le verset n'en liste
    que quatre), jamais brodés, et sans un visage (§9). Un rideau nu se lisait en drap.
    """
    mat = MAT_PAROKHET_FIGURE()
    z0, z1 = Z_BAT + PAROKHET_CHAMP[0], Z_BAT + PAROKHET_CHAMP[1]
    rang, pas = (z1 - z0) / PAROKHET_RANGS, 20 / PAROKHET_COLONNES
    for r in range(PAROKHET_RANGS):
        for i in range(PAROKHET_COLONNES):
            motif = creature_ailee if (i + r) % 2 == 0 else lion
            motif(f"{nom}_frise_{r}{i}", paroi, -10 + pas * (i + 0.5),
                  z0 + rang * (r + 0.10), rang * 0.80, col, mat)
    L = LISERE_PAROKHET
    for k, contour in enumerate((
            [(-10, z0 - L), (10, z0 - L), (10, z0), (-10, z0)],
            [(-10, z1), (10, z1), (10, z1 + L), (-10, z1 + L)],
            [(-10, z0 - L), (-10 + L, z0 - L), (-10 + L, z1 + L), (-10, z1 + L)],
            [(10 - L, z0 - L), (10, z0 - L), (10, z1 + L), (10 - L, z1 + L)])):
        _relief_profil(f"{nom}_lisiere_{k}", paroi, contour, 0.0, PAROKHET_SAILLIE * 0.7, col, mat)


box("Parokhet_ext", TR0 - PAROKHET_EP, TR0, -10, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_PAROKHET())
box("Parokhet_int", TR1, TR1 + PAROKHET_EP, -10, 10, Z_BAT, Z_BAT + 40, "60_KodeshHakodashim", MAT_PAROKHET())
empty("Parokhet_ext_agrafe_SUD", TR0, -9.5, Z_BAT + 20, "60_KodeshHakodashim")
empty("Parokhet_int_agrafe_NORD", TR1, 9.5, Z_BAT + 20, "60_KodeshHakodashim")
# La frise ne se pose que du côté que la caméra atteint : l'est pour l'extérieure (vue
# du Heikhal), l'ouest pour l'intérieure (vue du Kodesh HaKodashim). Un maassé 'hoshev
# en porte une AUTRE au revers — « נֶשֶׁר מִצַּד זֶה וְאַרְיֵה מִצַּד זֶה » (Yoma 72b) ; aucun plan
# ne cadre ces deux faces-là, et elles ne sont pas modélisées.
for cote, paroi in (("ext", ("y", TR0, 1)), ("int", ("y", TR1, -1))):
    frise_parokhet(f"Parokhet_{cote}", paroi, "60_KodeshHakodashim")
# Les badim de l'Arche pressent le rideau et se voient du Heikhal « כִּשְׁנֵי דַּדֵּי אִשָּׁה »
# (Yoma 54a ; Mena'hot 98b ; Melakhim I 8:8) : l'étoffe se tend sur quelques amot, et
# le bout de la barre la pointe au milieu de ce gonflement. Une demi-sphère seule ne
# rendait qu'une pastille sombre sur le rideau.
for ns, y in (("N", ARON_Y_BAD), ("S", -ARON_Y_BAD)):
    sphere(f"Parokhet_ext_tension_{ns}", TR0 - 1.55, y, ARON_Z_BAD, 1.8,
           "60_KodeshHakodashim", MAT_PAROKHET())
    sphere(f"Parokhet_ext_bosse_{ns}", TR0 + 0.16, y, ARON_Z_BAD, 0.36,
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


# --- Le champ sculpté d'une paroi du Bayit. Son ÉTENDUE est Ye'hezkel 41:20 —
#     « מֵהָאָרֶץ עַד־מֵעַל הַפֶּתַח », du sol jusqu'au-dessus de l'entrée, qui fait 20 amot
#     (Middot 4:1). Au-dessus, l'or reste nu jusqu'à la corniche : deux registres
#     flottant à mi-hauteur ne sont dans aucune source.
CHAMP_KIR = (1.0, 22.0)   # bas et haut du champ sculpté, en amot au-dessus de Z_BAT
REGISTRES_KIR = 3         # registres de figures, séparés par des bandeaux de fleurons


def champ_sculpte(nom, paroi, u0, u1, col):
    """Le champ « מֵהָאָרֶץ עַד־מֵעַל הַפֶּתַח » d'une paroi : des registres de keruvim et de
    timorot en alternance stricte, séparés par des bandeaux de fleurons."""
    z0, z1 = Z_BAT + CHAMP_KIR[0], Z_BAT + CHAMP_KIR[1]
    registre = (z1 - z0 - BANDEAU_KIR) / REGISTRES_KIR
    n = max(1, round((u1 - u0) / PAS_KIR))
    pas = (u1 - u0) / n
    for r in range(REGISTRES_KIR + 1):
        bandeau_fleurons(f"Kir_{nom}_{r}", paroi, u0, u1, z0 + r * registre, col)
    for r in range(REGISTRES_KIR):
        for i in range(n):
            motif = keruv_grave if i % 2 == 0 else timora
            motif(f"Kir_{nom}_{r}{i:02d}", paroi, u0 + pas * (i + 0.5),
                  z0 + r * registre + BANDEAU_KIR, registre - BANDEAU_KIR, col)


PAROIS_OR = [
    ("Heikhal_N", ("x", 10 - EPAISSEUR_PLACAGE, -1), HK1, HK0, "50_Heikhal"),
    ("Heikhal_S", ("x", -10 + EPAISSEUR_PLACAGE, 1), HK1, HK0, "50_Heikhal"),
    ("Heikhal_E_S", ("y", HK0 - EPAISSEUR_PLACAGE, -1), -10, -5, "50_Heikhal"),
    ("Heikhal_E_N", ("y", HK0 - EPAISSEUR_PLACAGE, -1), 5, 10, "50_Heikhal"),
    ("KhK_N", ("x", 10 - EPAISSEUR_PLACAGE, -1), KK1, KK0, "60_KodeshHakodashim"),
    ("KhK_S", ("x", -10 + EPAISSEUR_PLACAGE, 1), KK1, KK0, "60_KodeshHakodashim"),
    ("KhK_O", ("y", KK1 + EPAISSEUR_PLACAGE, 1), -10, 10, "60_KodeshHakodashim"),
]
for nom, paroi, u0, u1, col in PAROIS_OR:
    champ_sculpte(nom, paroi, u0, u1, col)
# Au-dessus de la baie du Heikhal, la paroi ne commence qu'à 20 amot : « עַד־מֵעַל
# הַפֶּתַח » n'y laisse que le bandeau qui ferme le champ de part et d'autre.
bandeau_fleurons("Kir_Heikhal_E_linteau", ("y", HK0 - EPAISSEUR_PLACAGE, -1), -5, 5,
                 Z_BAT + CHAMP_KIR[1] - BANDEAU_KIR, "50_Heikhal")

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
# Demi-profil d'une penne, déplié par `limbe` : étroite à l'emplanture, large au tiers,
# effilée au bout. Trois pennes par aile, décalées — une aile d'une seule plaque n'a pas
# de plumage, et trois plaques plates n'ont pas d'aile.
PENNE = ((0.0, 0.055), (0.16, 0.150), (0.44, 0.205), (0.70, 0.175), (0.89, 0.100), (1.0, 0.0))


def keruv(name, x, y, z0, col, vers, h=H_KERUV, epaules=0.26):
    """Keruv de la kaporet : enfant (« כְּרַבְיָא », Soucca 5b) agenouillé, martelé d'une
    pièce avec elle — « מִקְשָׁה », ni pieds ni socle (Rashi Shemot 25:18).

    Ligne du film (§8h) : le garçon et la fille enlacés, « כְּמַעֲשֵׂה אִישׁ וְאִשְׁתּוֹ »
    (Yoma 54a), bras tendus jusqu'à se toucher, tête inclinée vers la kaporet « comme
    l'élève devant son maître » (Bava Batra 99a), et « פֹּרְשֵׂי כְנָפַיִם לְמַעְלָה סֹכְכִים
    בְּכַנְפֵיהֶם עַל הַכַּפֹּרֶת » (Shemot 25:20) — les ailes montent du dos, se rejoignent en
    dais au-dessus du milieu, et ne touchent pas le corps.

    Bâti à l'origine, **-x vers l'autre keruv**, puis tourné : `vers` est le sens en y
    du centre de la kaporet. `h` et `epaules` distinguent le garçon de la fille (Yoma 54b).

    Une pile de boîtes surmontée d'une sphère et deux plaques plates en travers rendaient
    un épouvantail : le membre se lit à son galbe, et l'aile à son plumage.
    """
    or_ = MAT_OR()
    genou, hanche, epaule = 0.13 * h, 0.34 * h, 0.62 * h
    pieces = []
    for s_ in (-1, 1):
        yj = s_ * 0.135
        # Le tibié repose à plat sur la kaporet, le genou devant : c'est l'agenouillement.
        pieces.append(cyl_between(f"{name}_tibia{s_:+d}", (0.14, yj, 0.075 * h), (0.66, yj, 0.070 * h),
                                  0.075, col, or_, verts=10))
        pieces.append(sphere(f"{name}_genou{s_:+d}", 0.14, yj, genou * 0.85, 0.085, col, or_, segs=8))
        pieces.append(cyl_between(f"{name}_cuisse{s_:+d}", (0.16, yj, genou * 0.85), (-0.06, yj, hanche),
                                  0.095, col, or_, verts=10))
    pieces.append(sphere(f"{name}_bassin", -0.03, 0, hanche, 0.155, col, or_, segs=10))
    # Le torse penche vers l'autre keruv, et c'est ce penchant qui porte tout le groupe.
    pieces.append(cyl_between(f"{name}_torse", (-0.04, 0, hanche - 0.04), (-0.19, 0, epaule),
                              0.145, col, or_, verts=12))
    pieces.append(cyl_between(f"{name}_epaules", (-0.19, -epaules, epaule), (-0.19, epaules, epaule),
                              0.085, col, or_, verts=10))
    pieces.append(cyl_between(f"{name}_cou", (-0.21, 0, epaule + 0.01), (-0.27, 0, epaule + 0.10 * h),
                              0.058, col, or_, verts=8))
    # Tête d'enfant : large pour le corps, portée en avant — inclinée vers la kaporet.
    pieces.append(sphere(f"{name}_tete", -0.31, 0, epaule + 0.16 * h, 0.125 * h, col, or_, segs=14))
    for s_ in (-1, 1):
        # Les bras vont droit devant, jusqu'à la main de l'autre keruv, au milieu.
        main = (-0.80, s_ * 0.055, epaule - 0.10 * h)
        pieces.append(cyl_between(f"{name}_bras{s_:+d}", (-0.19, s_ * (epaules - 0.03), epaule - 0.02),
                                  (-0.50, s_ * 0.13, epaule - 0.09 * h), 0.062, col, or_, verts=8))
        pieces.append(cyl_between(f"{name}_avantbras{s_:+d}", (-0.50, s_ * 0.13, epaule - 0.09 * h),
                                  main, 0.052, col, or_, verts=8))
        pieces.append(sphere(f"{name}_main{s_:+d}", *main, 0.072, col, or_, segs=8))
        # L'aile part de l'omoplate, monte et vient au-dessus du milieu de la kaporet :
        # les deux keruvim s'y rejoignent en dais, sans qu'aucune aile touche un corps.
        emplanture = (-0.06, s_ * 0.115, epaule - 0.06 * h)
        for k, (ecart, longueur, largeur) in enumerate(((0.00, 1.00, 1.00), (0.13, 0.82, 0.80),
                                                        (0.24, 0.62, 0.62))):
            cible = (-0.76 + 0.10 * k, s_ * (0.14 + 0.13 * k), epaule + 0.42 * h - 0.08 * h * k)
            base = (emplanture[0] + 0.10 * ecart, emplanture[1] + s_ * 0.05 * ecart,
                    emplanture[2] - 0.20 * ecart)
            axe = tuple(c - b for c, b in zip(cible, base))
            portee = math.dist(cible, base)
            pieces.append(limbe(f"{name}_aile{s_:+d}_penne{k}", PENNE, base, axe, (0, s_, 0),
                                portee * longueur, 0.028 * largeur, col, or_, courbure=0.16))
    _poser(pieces, x, y, z0, -vers * math.pi / 2)   # -x vers l'autre keruv

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
