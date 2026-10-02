import bpy
from typing import NamedTuple

from .parametres import AMA, RACINE, m
from .noeuds import _bsdf, _calc, _creuser, _grain, _neuf, _noeud, _normale, _position, _trainee


# Appareil : le Temple est bâti d'אַבְנֵי גָזִית, et le Tanakh les mesure —
# « וּמְיֻסָּד אֲבָנִים יְקָרוֹת אֲבָנִים גְּדֹלוֹת אַבְנֵי עֶשֶׂר אַמּוֹת וְאַבְנֵי שְׁמֹנֶה אַמּוֹת »
# (Melakhim I 7:10). Deux longueurs, pas une : le verset les nomme toutes les deux, et
# l'assise en tire une. La pierre de 10 et celle de 8 valent aussi pour le Temple
# lui-même, « וְלַחֲצַר בֵּית ה' הַפְּנִימִית וּלְאֻלָם הַבָּיִת » (7:12). Le module d'une ama qui
# les précédait lisait en brique — quarante rangs sur la façade au lieu de dix blocs.
# La HAUTEUR d'assise n'est dans aucune source : c'est un CHOIX. Le pas valait 2,5 pour
# l'enceinte et 2 pour le bâtiment — cinquante lits sur les 100 amot de la façade,
# l'échelle d'un mur de brique. À 4, une assise vaut le pas d'un rovad de l'Oulam (1 de
# nu + 3 de saillie, Rambam Beit HaBe'hira 4:9) : le haut de chaque bandeau tombe sur un
# lit au lieu de battre contre lui. Le bâtiment prend le double : à 4, ses vingt-cinq
# lits le lisaient en carrelage ; à 8, un bandeau sur deux tombe encore sur un lit, et
# aucun lit ne traverse une saillie.
PIERRE_LONG = (8.0, 10.0)   # Melakhim I 7:10 — l'assise tire l'une ou l'autre
ASSISE = 4.0                # CHOIX : hauteur d'assise, hors source
ASSISE_HERODE = 8.0         # CHOIX : le bâtiment, deux pas de rovad
# La face est SCIÉE, pas rustiquée : « אֲבָנִים יְקָרֹת כְּמִדּוֹת גָּזִית מְגֹרָרוֹת בַּמְּגֵרָה
# מִבַּיִת וּמִחוּץ » (Melakhim I 7:9). Tout le relief tient donc au joint et au liseré qui
# le borde, jamais à un bossage éclaté. Largeur du liseré : CHOIX. À 0,35 ama il faisait
# un cadre de dix-sept centimètres autour de chaque bloc, assez large pour se lire en
# bordure rapportée ; 0,25 le ramène à un trait de ciseau.
JOINT = 0.06
LISERE = 0.25
# « אפיק שפה ועייל שפה, כי היכי דלקבל סידא » (Soucca 51b ; Baba Batra 4a) : une
# assise déborde, la suivante rentre, pour que l'enduit prenne — celui qu'Hérode voulait
# dorer. Ce relief n'est pas la vague : Rashi la met dans la teinte, « שהאבנים משונים
# במראיהן זו מזו » (Soucca 51b). Le débord n'est chiffré nulle part — CHOIX, le même
# partout.
DEBORD_ASSISE = 0.05
# Le marbre est poli jusqu'à l'arête : pas de liseré, et un joint serré — CHOIX. Au
# joint du calcaire, ses blocs quadrillaient la façade de traits.
JOINT_MARBRE = 0.02
LISERE_MARBRE = 0.0


class Appareil(NamedTuple):
    assise: float
    longueurs: tuple[float, float]
    debord: float
    joint: float
    lisere: float
    origine: float = 0.0      # la cote d'un lit, en amot


APPAREIL_GAZIT = Appareil(ASSISE, PIERRE_LONG, DEBORD_ASSISE, JOINT, LISERE)


class Bloc(NamedTuple):
    """Ce que `_tailler` lit en un point. `champ` vaut 0 au fond du joint, 1 sur la face."""
    parite: bpy.types.NodeSocket
    tire_assise: bpy.types.NodeSocket
    tire_bloc: bpy.types.NodeSocket
    tire_fini: bpy.types.NodeSocket
    creux: bpy.types.NodeSocket
    champ: bpy.types.NodeSocket

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
# La PREMIÈRE est le parement d'avant, et reste la référence.
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


def _tailler(mat, appareil):
    """Taille la surface en blocs et creuse leur joint et son liseré.

    Deux reliefs, et c'est le profil du bloc : le joint, creusé ; le liseré qui le
    borde, plat et en léger retrait ; entre les deux le champ de la pierre. Le liseré
    est ce qui donne le bloc, et le bloc l'échelle — sans lui un mur de 100 amot n'a que
    des lignes horizontales et se lit en bardage.

    La parité des assises reste le « אַפֵּיק שָׂפָה וְעַיֵּיל שָׂפָה » de *Soucca* 51b : une assise
    en léger débord, la suivante en retrait, « כי היכי דלקבל סידא ». D'où `debord`.
    """
    assise, longueurs, _, joint, lisere, origine = appareil
    z, u, aplat = _parement(mat)
    rang, ecart_z = _module(mat, _calc(mat, "SUBTRACT", z, m(origine)), assise)
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
    portee = joint + lisere + 0.15
    rampe = profil.color_ramp
    # Le liseré est en léger retrait, le champ à peine proéminent : 0,62 de la course
    # est descendue dans le joint, et il ne reste que 0,32 pour la marche du bloc, un
    # centimètre au Bump de 0,07 — le creux est aussi profond que le joint est large.
    # À 0,44 le bloc débordait assez pour que le Bump cerne chaque pierre d'un jonc
    # clair — un carrelage, pas un mur.
    rampe.elements[0].position, rampe.elements[0].color = 0.0, (0.0, 0.0, 0.0, 1.0)
    rampe.elements[1].position, rampe.elements[1].color = joint / portee, (0.62,) * 3 + (1.0,)
    rampe.elements.new((joint + lisere) / portee).color = (0.68,) * 3 + (1.0,)
    rampe.elements.new((joint + lisere + 0.06) / portee).color = (1.0, 1.0, 1.0, 1.0)
    rapport = _calc(mat, "DIVIDE", ecart, portee)
    mat.node_tree.links.new(rapport, profil.inputs["Factor"])
    # Le JOINT seul, sans le liseré. Le profil sert au relief et court sur toute la
    # bordure ; l'ombre, elle, doit s'arrêter au fond de la rainure — étalée sur le
    # liseré, elle cerne chaque bloc d'un cadre sombre que ne montre aucun mur.
    creux = _noeud(mat, "ShaderNodeValToRGB", -1200, -520)
    creux.color_ramp.elements[0].position = 0.0
    creux.color_ramp.elements[1].position = joint * 1.15 / portee
    mat.node_tree.links.new(rapport, creux.inputs["Factor"])
    _creuser(mat, profil.outputs["Color"], 1.0, 0.07)
    _creuser(mat, parite, 0.9, appareil.debord)
    return Bloc(parite, tire_assise.outputs["Value"], tire_bloc.outputs["Value"],
                tire_fini.outputs["Value"], creux.outputs["Color"], profil.outputs["Color"])


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


def pierre(name, rgb, appareil=APPAREIL_GAZIT):
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
    parite, _, bloc, fini, creux, champ = _tailler(mat, appareil)
    # Le grain reste dans le champ de la pierre et s'arrête au liseré, qui est ciselé.
    _creuser(mat, _calc(mat, "MULTIPLY", _grain(mat, 0.45), champ), 0.8, 0.035)
    # Piqûre du calcaire : le meleke est poreux, et sans elle la face sciée rend un
    # plastique lisse dès que le soleil la prend de biais.
    _creuser(mat, _calc(mat, "MULTIPLY", _grain(mat, 0.10), champ), 0.6, 0.012)
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
# C'est leur écart qui fait « כאדותא דימא » : « שהאבנים משונים במראיהן זו מזו »
# (Rashi sur Soucca 51b). Chroma : CHOIX, franc sans tourner à la mosaïque.
MARBRES_HERODE = ((0.94, 0.93, 0.89), (0.78, 0.86, 0.91), (0.80, 0.90, 0.74))
APPAREIL_HERODE = Appareil(ASSISE_HERODE, PIERRE_LONG, DEBORD_ASSISE, JOINT_MARBRE, LISERE_MARBRE)
RUGOSITE_MARBRE = 0.30
# Le scan Marble001 que fabrique beit_hamikdash_nappes.py. Mêmes réglages que CARREAU[9] de
# visite/matieres.js, et mêmes moyennes que le jeu `marbre` de visite/nappes.js.
NAPPE_MARBRE = RACINE / "visite" / "matieres" / "marbre_c_1024.webp"
COTE_NAPPE_MARBRE = 4.8                  # mètres : un carreau par bloc de 10 amot, sans répétition
COULEUR_NAPPE_MARBRE, CHROMA_NAPPE_MARBRE, RUGOSITE_NAPPE_MARBRE = 1.0, 0.35, 1.0
MOYENNE_NAPPE_MARBRE, RUGOSITE_MOYENNE_NAPPE_MARBRE = (0.7442, 0.7243, 0.6827), 0.1722


def marbre_herode(name):
    """Le corps du bâtiment, en assises alternées de trois marbres.

    C'est la seule surface que les sources refusent explicitement de dorer : Hérode
    voulut la plaquer d'or et les Sages l'en dissuadèrent (*Baba Batra* 4a). Elle porte
    donc le marbre, poli et veiné, et l'or reste où *Middot* 4:1 le met — tout
    l'intérieur du Bayit.

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
    _, tire_assise, bloc, fini, creux, _ = _tailler(mat, APPAREIL_HERODE)
    choix = _noeud(mat, "ShaderNodeValToRGB", -680, 160)
    rampe = choix.color_ramp
    rampe.interpolation = 'CONSTANT'
    rampe.elements[0].position = 0.0
    rampe.elements[0].color = (*MARBRES_HERODE[0], 1.0)
    rampe.elements[1].position = 1.0 / 3.0
    rampe.elements[1].color = (*MARBRES_HERODE[1], 1.0)
    rampe.elements.new(2.0 / 3.0).color = (*MARBRES_HERODE[2], 1.0)
    liens.new(tire_assise, choix.inputs["Factor"])
    teinte = _noeud(mat, "ShaderNodeMixRGB", -500, 160)
    teinte.blend_type = "MULTIPLY"
    teinte.inputs["Factor"].default_value = 1.0
    liens.new(choix.outputs["Color"], teinte.inputs["Color1"])
    nuance = _noeud(mat, "ShaderNodeValToRGB", -680, -40)
    # L'assise porte la vague ; d'un bloc au suivant, à peine une nuance, sinon la façade tourne au patchwork.
    nuance.color_ramp.elements[0].color = (0.97, 0.97, 0.98, 1.0)
    nuance.color_ramp.elements[1].color = (1.03, 1.02, 1.00, 1.0)
    liens.new(_calc(mat, "MULTIPLY_ADD", _grain(mat, 24.0), 0.45,
                    _calc(mat, "MULTIPLY", bloc, 0.55)), nuance.inputs["Factor"])
    liens.new(nuance.outputs["Color"], teinte.inputs["Color2"])
    photo, ecart_rugosite = _nappe_par_bloc(mat, bloc, fini)
    marbre = _noeud(mat, "ShaderNodeMixRGB", -340, 320)
    marbre.blend_type = "MULTIPLY"
    marbre.inputs["Factor"].default_value = 1.0
    liens.new(teinte.outputs["Color"], marbre.inputs["Color1"])
    liens.new(photo, marbre.inputs["Color2"])
    liens.new(_ombre_du_joint(mat, marbre.outputs["Color"], creux),
              _bsdf(mat).inputs["Base Color"])
    _bsdf(mat).inputs["Roughness"].default_value = RUGOSITE_MARBRE
    liens.new(_calc(mat, "ADD", ecart_rugosite,
                    _calc(mat, "MULTIPLY_ADD", _calc(mat, "SUBTRACT", bloc, 0.5), 0.06, RUGOSITE_MARBRE)),
              _bsdf(mat).inputs["Roughness"])
    return mat


def _nappe_par_bloc(mat, tire_bloc, tire_fini):
    """Le scan du marbre en projection boîte, recalé sur chaque bloc comme `photo` dans matieres.js.

    Renvoie (rapport de couleur à la moyenne du scan, écart de rugosité à sa moyenne).
    """
    liens = mat.node_tree.links
    carreau = _noeud(mat, "ShaderNodeVectorMath", -1400, 900)
    carreau.operation = "SCALE"
    carreau.inputs["Scale"].default_value = 1.0 / COTE_NAPPE_MARBRE
    liens.new(_position(mat), carreau.inputs[0])
    # Deux tirages du bloc sur chaque plan : celui de l'assise alignait la même veine sur tout le rang.
    tranche = _noeud(mat, "ShaderNodeCombineXYZ", -1400, 1100)
    liens.new(_calc(mat, "MULTIPLY", tire_bloc, 13.0), tranche.inputs["X"])
    liens.new(_calc(mat, "MULTIPLY", _calc(mat, "ADD", tire_bloc, tire_fini), 13.0), tranche.inputs["Y"])
    liens.new(_calc(mat, "MULTIPLY", tire_fini, 13.0), tranche.inputs["Z"])
    recale = _noeud(mat, "ShaderNodeVectorMath", -1200, 900)
    recale.operation = "ADD"
    liens.new(carreau.outputs["Vector"], recale.inputs[0])
    liens.new(tranche.outputs["Vector"], recale.inputs[1])
    scan = _noeud(mat, "ShaderNodeTexImage", -1000, 900)
    scan.image = bpy.data.images.load(str(NAPPE_MARBRE), check_existing=True)
    scan.image.alpha_mode = "CHANNEL_PACKED"
    scan.projection = "BOX"
    scan.projection_blend = 0.1
    liens.new(recale.outputs["Vector"], scan.inputs["Vector"])
    rapport = _noeud(mat, "ShaderNodeMixRGB", -800, 900)
    rapport.blend_type = "DIVIDE"
    rapport.inputs["Factor"].default_value = 1.0
    rapport.inputs["Color2"].default_value = (*MOYENNE_NAPPE_MARBRE, 1.0)
    liens.new(scan.outputs["Color"], rapport.inputs["Color1"])
    gris = _noeud(mat, "ShaderNodeRGBToBW", -650, 1000)
    liens.new(rapport.outputs["Color"], gris.inputs["Color"])
    bride = _noeud(mat, "ShaderNodeMixRGB", -500, 900)
    bride.inputs["Factor"].default_value = CHROMA_NAPPE_MARBRE
    liens.new(gris.outputs["Val"], bride.inputs["Color1"])
    liens.new(rapport.outputs["Color"], bride.inputs["Color2"])
    dose = _noeud(mat, "ShaderNodeMixRGB", -350, 900)
    dose.inputs["Factor"].default_value = COULEUR_NAPPE_MARBRE
    dose.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1.0)
    liens.new(bride.outputs["Color"], dose.inputs["Color2"])
    ecart = _calc(mat, "MULTIPLY", _calc(mat, "SUBTRACT", scan.outputs["Alpha"], RUGOSITE_MOYENNE_NAPPE_MARBRE),
                  RUGOSITE_NAPPE_MARBRE)
    return dose.outputs["Color"], ecart
