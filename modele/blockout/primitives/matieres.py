from .parametres import AMA, Z_AZ, m
from .noeuds import (_MATIERES_CABLEES, _bsdf, _calc, _creuser, _grain, _neuf, _noeud, _position, material,
                     vitre)
from .pierre import (COULURE_EXPOSEE, CREUX_DALLE, DEBORD_ASSISE, JOINT, JOINT_DALLE, LISERE, OMBRE_JOINT,
                     PIERRE_LONG, ROVAD_DALLE, Appareil, _module, marbre_herode, pierre)
from .tissage import parokhet


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

def dallage(name, rgb, rovad=ROVAD_DALLE, longueurs=PIERRE_LONG):
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
    rang, ecart_x = _module(mat, p.outputs["X"], rovad)
    numero = _calc(mat, "FLOOR", rang)
    tire_rang = _noeud(mat, "ShaderNodeTexWhiteNoise", -1700, 120)
    tire_rang.noise_dimensions = '1D'
    liens.new(numero, tire_rang.inputs["W"])
    longue = _calc(mat, "GREATER_THAN", tire_rang.outputs["Value"], 0.5)
    longueur = _calc(mat, "MULTIPLY_ADD", longue, longueurs[1] - longueurs[0],
                     longueurs[0])
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

def roche(name):
    """Rocher en place, ni taillé ni lavé en dalle : deux tons de calcaire, piqué et crevassé.
    La couleur de base est la moyenne des deux — c'est elle que la visite emporte."""
    mat, neuf = _neuf(name, (0.28, 0.24, 0.18))
    if not neuf:
        return mat
    liens = mat.node_tree.links
    _bsdf(mat).inputs["Roughness"].default_value = 0.88
    melange = _noeud(mat, "ShaderNodeMixRGB", -700, 0)
    melange.inputs["Color1"].default_value = (0.38, 0.33, 0.25, 1.0)
    melange.inputs["Color2"].default_value = (0.18, 0.15, 0.11, 1.0)
    liens.new(_grain(mat, 0.9), melange.inputs["Factor"])
    liens.new(melange.outputs["Color"], _bsdf(mat).inputs["Base Color"])
    _creuser(mat, _grain(mat, 1.2), 1.0, 0.35)
    _creuser(mat, _grain(mat, 0.3), 0.9, 0.08)
    _creuser(mat, _grain(mat, 0.06), 0.6, 0.015)
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


def huile(name, rgb):
    """L'huile d'une lampe : lisse et sombre, elle renvoie la flamme."""
    mat, neuf = _neuf(name, rgb)
    if neuf:
        _bsdf(mat).inputs["Roughness"].default_value = 0.06
    return mat

# Le calcaire du pourtour, crème presque neutre : c'est la couleur d'un meleke scié
# de frais, et l'ocre lui vient des bancs (BANCS_CALCAIRE), pas de sa base.
# Il reste SOUS les trois marbres du bâtiment (MARBRES_HERODE, 0,94 / 0,78 / 0,80) :
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
MAT_ROCHE = lambda: roche("Roche_shetiya")
MAT_SEL = lambda: enduit("Sel", (0.93, 0.93, 0.91))              # Lishkat HaMela'h (Middot 5:3)
MAT_PEAU = lambda: etoffe("Peau", (0.40, 0.26, 0.16))            # peaux salées de la Parva (Middot 5:3)
MAT_KETORET = lambda: enduit("Ketoret", (0.52, 0.38, 0.26))      # sammanim pilés (Keritot 6b)
MAT_CENDRE = lambda: enduit("Cendre", (0.40, 0.38, 0.36))        # tapoua'h et deshen (Tamid 1:4, 2:2)
MAT_ARGENT = lambda: metal("Argent", (0.90, 0.90, 0.91), 0.3)
MAT_CHAUX = lambda: enduit("Chaux_blanche", (0.95, 0.95, 0.92))
MAT_LECHEM = lambda: enduit("Lechem_afui", (0.52, 0.30, 0.12))    # matsa cuite dans l'Azara (Mena'hot 5:1, 11:2)
MAT_SOLET = lambda: enduit("Solet", (0.92, 0.89, 0.80))           # fleur de farine des mena'hot (Ma'asse HaKorbanot 13:2)
MAT_TEVEN = lambda: enduit("Teven", (0.62, 0.52, 0.30))           # paille de l'enclos des agneaux (Arakhin 2:5)
MAT_KLAF = lambda: enduit("Klaf", (0.78, 0.70, 0.54))             # rouleaux lus au Cohen Gadol (Yoma 1:6)
MAT_LAINE = lambda: etoffe("Laine", (0.50, 0.42, 0.32))           # « אִישׁ כִּסְתּוֹ בָאָרֶץ » (Tamid 1:1)
MAT_AVNET = lambda: etoffe("Avnet_kilayim", (0.40, 0.21, 0.30))   # « וְהָאַבְנֵט לְבַדּוֹ רָקוּם בְּצֶמֶר » (Klei HaMikdash 8:1)
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
MAT_OR_MIKSHE = lambda: metal("Or_mikshe", (1.0, 0.76, 0.33), 0.3)   # la visite y bat « שְׁקֵדִים שְׁקֵדִים »
MAT_SHEMEN = lambda: huile("Shemen_zayit", (0.11, 0.065, 0.01))      # « שֶׁמֶן זַיִת זָךְ » (Shemot 27:20)
MAT_PETILA = lambda: material("Petila", (0.10, 0.08, 0.06))
TEINTE_CEDRE = (0.44, 0.25, 0.14)
MAT_CEDRE = lambda: bois("Cedre", TEINTE_CEDRE)
# Le cèdre choisi des revêtements, plus rouge ; la visite en tire une photo plus calme.
MAT_CEDRE_LAMBRIS = lambda: bois("Cedre_lambris", (0.46, 0.23, 0.13))

# Le rayon (m) part en extra glTF : la visite en a besoin pour garder la pièce lisible sous le pixel.
def MAT_ECHELLE(piece, rayon):
    mat = bois(f"Cedre_echelle_{piece}", TEINTE_CEDRE)
    mat["rayon"] = m(rayon)
    return mat

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
MAT_TERRE = lambda: terre("Terre_Jerusalem")
# La ville, deux tons sous le Temple, et son appareil est domestique : le gazit de
# huit à dix amot (Melakhim I 7:10) est celui de la maison du Roi et du Bayit, pas
# celui d'une maison de Jérusalem. Assise et bloc au moellon.
MAT_MAISON = lambda: _voiler(_exposer(pierre("Maisons", (0.64, 0.55, 0.40),
                                              Appareil(0.8, (1.5, 2.5), DEBORD_ASSISE, JOINT, LISERE))))
# Les colonnes des portiques : un tambour est UNE pierre, et n'a donc pas de joint
# vertical. Une longueur de bloc énorme les supprime ; il ne reste que le lit d'un
# tambour à l'autre. Sur un cylindre, le joint vertical était pire qu'inutile : la face
# choisit son axe sur la normale (`_parement`), qui bascule quatre fois autour du fût,
# et la trame sautait quatre fois par colonne.
MAT_COLONNE = lambda: pierre("Pierre_colonne", CALCAIRE, Appareil(1.4, (1e4, 1e4), 0.0, JOINT, LISERE))
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
# Les abords du Kotel d'aujourd'hui.
MAT_INOX = lambda: metal("Inox", (0.72, 0.72, 0.73), 0.25)
MAT_PLASTIQUE = lambda: material("Plastique_blanc", (0.88, 0.88, 0.86))
MAT_VERRE_DE_LAMPE = lambda: material("Verre_de_lampe", (0.90, 0.89, 0.84))    # projecteurs et lanternes : la visite les fait luire de nuit
MAT_VITRE = lambda: vitre("Vitre", (0.05, 0.06, 0.07))
MAT_BETON = lambda: material("Beton", (0.70, 0.68, 0.64))
MAT_PORTIQUE = lambda: material("Portique", (0.55, 0.56, 0.58))
MAT_BORNE_INCENDIE = lambda: material("Borne_incendie", (0.60, 0.10, 0.08))
MAT_TOILE = lambda: material("Toile_blanche", (0.90, 0.88, 0.82))        # parasols, auvents, palissades de chantier
MAT_FER_BRUN = lambda: metal("Fer_brun", (0.16, 0.12, 0.09), 0.6)          # grilles et garde-corps de la place
MAT_MEHITSA = lambda: metal("Mehitsa", (0.62, 0.48, 0.26), 0.5)
MAT_CAPRIER = lambda: material("Caprier", (0.27, 0.33, 0.15))             # les câpriers qui pendent du Kotel
MAT_DRAPEAU_BLANC = lambda: material("Drapeau_blanc", (0.92, 0.92, 0.92))
MAT_DRAPEAU_BLEU = lambda: material("Drapeau_bleu", (0.02, 0.14, 0.55))
MAT_TABLE_DE_PRIERE = lambda: material("Table_de_priere", (0.34, 0.12, 0.09))
MAT_TOLE = lambda: metal("Tole", (0.58, 0.60, 0.62), 0.5)
MAT_BOIS_DU_PONT = lambda: bois("Bois_du_pont", (0.36, 0.22, 0.13))
# La pierre de Jérusalem des bâtiments d'aujourd'hui autour de la place : un parement de moellons sciés, beige doré.
MAT_PIERRE_DE_JERUSALEM = lambda: pierre("Pierre_de_Jerusalem", (0.70, 0.63, 0.50),
                                         Appareil(0.8, (1.5, 2.5), DEBORD_ASSISE, JOINT, LISERE))
# Le pavé de la place haute, en rangs étroits le long du Kotel, et les grandes dalles claires de l'aire de prière.
MAT_DALLAGE_KOTEL = lambda: dallage("Dallage_kotel", (0.66, 0.60, 0.50), 0.9, (1.3, 2.2))
MAT_DALLAGE_DE_PRIERE = lambda: dallage("Dallage_de_priere", (0.74, 0.69, 0.58), 1.6, (2.0, 3.2))
MAT_ACIER_BLANC = lambda: metal("Acier_blanc", (0.82, 0.82, 0.80), 0.5)    # les palées du pont des Maghrébins
MAT_PALME = lambda: material("Palme", (0.20, 0.30, 0.12))
MAT_BLEU_POLICE = lambda: material("Bleu_police", (0.05, 0.16, 0.50))   # la bande et la rampe lumineuse des voitures de police
MAT_PNEU = lambda: material("Pneu", (0.03, 0.03, 0.03))
MAT_BOUGAINVILLEE = lambda: material("Bougainvillee", (0.55, 0.10, 0.32))   # au pied de la porte des Maghrébins
MAT_CARROSSERIE_SOMBRE = lambda: material("Carrosserie_sombre", (0.10, 0.11, 0.13))
MAT_CAPRIER_SEC = lambda: material("Caprier_sec", (0.40, 0.36, 0.20))      # les touffes de l'an passé
MAT_VELOURS = lambda: material("Velours_de_l_aron", (0.10, 0.09, 0.28))    # la parokhet des arons de la place
MAT_RELIURES = (lambda: material("Reliure_rouge", (0.35, 0.08, 0.07)),
                lambda: material("Reliure_bleue", (0.08, 0.12, 0.30)),
                lambda: material("Reliure_noire", (0.06, 0.05, 0.05)))
