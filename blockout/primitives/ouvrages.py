import bpy
import math
from typing import NamedTuple

from .matieres import MAT_CEDRE, MAT_MARBRE_HERODE
from .volumes import box, cyl, plage, prism
from .gravures import largeur_gravure, timora


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
    4:3, « שֶׁיִּכָּנֵס בּוֹ הַדֶּלֶף ») ; la תקרה les planches ; la מעזיבה le blocage qui les couvre
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


def lishka(name, x0, x1, y0, y1, z0, z1, col, portes, adossee=None, mat=None, tremies=()):
    """Chambre du pourtour, creuse : socle, murs percés de baies, bandeau, corniche qui la couvre.

    Posée en boîte nue, une lishka ne se lit pas : à 750 amot elle n'a ni pied, ni
    sommet, ni ombre sur elle-même, et le styliseur en fait un rocher. Les trois
    lignes en saillie donnent l'assise et le couronnement, les baies l'échelle.

    `portes` : des `Porte`. Chacune s'ouvre à son seuil, et le socle s'ouvre avec elle
    quand ce seuil est plus bas que lui. Le sol intérieur n'est pas bâti ici : il dépend
    de ce que la chambre enjambe. `adossee` : la face collée à un mur d'enceinte, qui lui
    sert de mur — ni parement, ni socle, ni saillie. `tremies` : ce que la corniche laisse
    ouvert, le puits d'une mesiba qui monte au-dessus d'elle.
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
    dalle_percee(f"{name}_corniche", *enveloppe, zc, z1, col, mat, tremies)

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


def escalier_a_vis(name, cx, cy, rayon, z_haut, z_bas, sortie, col, mat=None):
    """Vis de degrés d'une demi-ama autour d'un noyau, douze au tour, qui descend dans le
    sens trigonométrique. `sortie` : le cap, en degrés, par où l'on quitte le dernier degré ;
    le degré du tour d'au-dessus y laisse cinq amot de passage."""
    noyau, par_tour = 0.35, 12
    pas = 2 * math.pi / par_tour
    n = round((z_haut - z_bas) / DEGRE) - 1
    depart = math.radians(sortie) - pas * (n + 0.5)
    cyl(f"{name}_noyau", cx, cy, z_bas, z_haut, noyau, col, mat, verts=12)
    for k in range(n):
        a0, a1 = depart + pas * k, depart + pas * (k + 1)
        rayons = [(noyau, a0)] + [(rayon, a0 + (a1 - a0) * t / 2) for t in range(3)] + [(noyau, a1)]
        z = z_haut - DEGRE * (k + 1)
        prism(f"{name}_{k:02d}", [(cx + r * math.cos(a), cy + r * math.sin(a)) for r, a in rayons],
              z - 1, z, col, mat)


# Aucune source ne dit par où l'on montait à l'aliyah de Middot 1:5 : la Mishna y poste
# les cohanim — « שֶׁהַכֹּהֲנִים שׁוֹמְרִים מִלְמַעְלָן » — sans jamais les y faire monter. CHOIX :
# une vis, comme celle qui mène au toit du Beit HaParva (Middot 5:3), dans l'angle est de
# la cage. Vingt-six amot de montée ne tiennent pas en volée droite dans les seize de la
# cage, et « וּכְמִין אַכְסַדְרָה הָיָה » ne laisse rien dépasser au-dehors. Son puits traverse
# la corniche et la terrasse ; la cage garde treize amot pour ses vingt degrés, plus que
# les dix du שער qu'ils desservent.
MESIBA_PORTE = 3          # côté du puits de la vis ; le reste de l'angle fait palier


def puits_de_mesiba(x1, y0, y1):
    """Le carré que la vis d'un corps de porte réserve dans l'angle est de sa cage."""
    cy = (y0 + y1) / 2
    return (x1 - MESIBA_PORTE, x1, cy - MESIBA_PORTE / 2, cy + MESIBA_PORTE / 2)


def terrasse_de_porte(name, x0, x1, y0, y1, z, chambre, col, mat=None, tremies=()):
    """Toit d'un corps de porte : dalle, garde-corps sur le pourtour resté libre.

    C'est elle qui assoit la chambre haute — l'aliyah de Middot 1:5 et de Tamid 1:1.
    `chambre` : l'intervalle en x qu'occupe cette chambre ; le garde-corps s'arrête
    contre elle, deux parois coplanaires clignoteraient. `tremies` : le puits par où
    la mesiba de la cage débouche sur la terrasse.
    """
    dalle_percee(f"{name}_terrasse", x0, x1, y0, y1, z, z + 1, col, mat, tremies)
    bords = [("ouest", x0, x0 + 1, y0, y1), ("est", x1 - 1, x1, y0, y1)]
    for cote, b0, b1 in (("sud", y0, y0 + 1), ("nord", y1 - 1, y1)):
        bords += [(f"{cote}_O", x0 + 1, chambre[0], b0, b1),
                  (f"{cote}_E", chambre[1], x1 - 1, b0, b1)]
    for suffixe, a, b, c, e in bords:
        box(f"{name}_garde_{suffixe}", a, b, c, e, z + 1, z + 3, col, mat)


def aliyah(name, x0, x1, y0, y1, z0, h, col, fenetre, porte, mat=None):
    """Chambre haute posée sur un corps de porte, murs d'une ama, une fenêtre et une porte.

    « בֵּית אַבְטִינָס וּבֵית הַנִּיצוֹץ הָיוּ עֲלִיּוֹת » (Middot 1:1 ; Tamid 1:1) : ce sont
    des étages, et un étage a un rez-de-chaussée. `fenetre` et `porte` : (face, u0, u1) —
    la face percée et l'intervalle de la baie le long d'elle. La fenêtre va de 3 à 7 amot
    du sol, la porte du sol à 8 ; elle ouvre sur la terrasse, où débouche la mesiba.
    """
    baies = {fenetre[0]: [(fenetre[1], fenetre[2], z0 + 3, z0 + 7)],
             porte[0]: [(porte[1], porte[2], z0, z0 + 8)]}
    box(f"{name}_toit", x0, x1, y0, y1, z0 + h - 1, z0 + h, col, mat)
    for cote, bornes in (("ouest", (x0, x0 + 1, y0, y1)), ("est", (x1 - 1, x1, y0, y1)),
                         ("sud", (x0, x1, y0, y0 + 1)), ("nord", (x0, x1, y1 - 1, y1))):
        paroi_percee(f"{name}_mur_{cote}", *bornes, z0, z0 + h, col, mat, baies.get(cote, []))


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
# langue que les sources donnent au Temple — le כַּרְכֹּב du Mizbea'h (Shemot 27:5 ; Zeva'him 62a), les
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
             saillie=SAILLIE_MOULURE, filet=None, baies=None):
    """La moulure de `moulure`, mais sur les quatre côtés d'une enceinte fermée.

    Un mur seul se coupe là où un corps de porte passe la crête ; ici les quatre côtés
    sont solidaires, et ce qui compte est qu'ils s'aboutent au lieu de se recouvrir —
    deux boîtes coplanaires clignotent. Les côtés sud et nord prennent les angles, les
    côtés est et ouest s'arrêtent contre eux.

    `baies` : `{face: [(u0, u1), …]}`, ce que la moulure laisse libre le long d'une face.
    Un socle qui court devant une porte la rehausse d'autant, et en fait une fenêtre.
    """
    baies = baies or {}
    larmier = max(range(len(profil)), key=lambda k: profil[k][2])
    for i, (zb, zh, part) in enumerate(profil):
        p, e = saillie * part, epaisseur
        for face, bornes in (("S", (x0 - p, x1 + p, y0 - p, y0 + e + p)),
                             ("N", (x0 - p, x1 + p, y1 - e - p, y1 + p)),
                             ("O", (x0 - p, x0 + e + p, y0 + e, y1 - e)),
                             ("E", (x1 - e - p, x1 + p, y0 + e, y1 - e))):
            if face not in baies:
                box(f"{name}_{face}{i}", *bornes, z + zb, z + zh, col, mat)
                continue
            paroi_percee(f"{name}_{face}{i}", *bornes, z + zb, z + zh, col, mat,
                         [(u0, u1, z + zb, z + zh) for u0, u1 in baies[face]])
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


def _retrancher(bloc, vide):
    """Ce qui reste de la boîte `bloc` une fois ôtée la boîte `vide` : six boîtes au plus."""
    x0, x1, y0, y1, z0, z1 = bloc
    a0, a1, b0, b1, c0, c1 = vide
    if a0 >= x1 or a1 <= x0 or b0 >= y1 or b1 <= y0 or c0 >= z1 or c1 <= z0:
        return [bloc]
    zb, zh = max(z0, c0), min(z1, c1)
    xa, xb = max(x0, a0), min(x1, a1)
    restes = [(x0, x1, y0, y1, z0, zb), (x0, x1, y0, y1, zh, z1),
              (x0, xa, y0, y1, zb, zh), (xb, x1, y0, y1, zb, zh),
              (xa, xb, y0, max(y0, b0), zb, zh), (xa, xb, min(y1, b1), y1, zb, zh)]
    return [r for r in restes if r[0] < r[1] and r[2] < r[3] and r[4] < r[5]]


def massif_evide(name, x0, x1, y0, y1, z0, z1, vides, col, mat=None):
    """Masse pleine dont on ôte des vides `(x0, x1, y0, y1, z0, z1)` : les boîtes qui restent.

    `dalle_trouee` perce un plancher de part en part ; un tunnel passe à mi-hauteur d'une
    masse. Les coupes ne sont pas des arêtes de pierre : les morceaux ne prennent pas de
    biseau, qui creuserait une rainure le long de chacune, en travers du dallage.
    """
    blocs = [(x0, x1, y0, y1, z0, z1)]
    for vide in vides:
        blocs = [reste for bloc in blocs for reste in _retrancher(bloc, vide)]
    if len(blocs) == 1:
        box(name, *blocs[0], col, mat)
        return
    for k, bloc in enumerate(blocs):
        box(f"{name}_{k:02d}", *bloc, col, mat)["sans_biseau"] = True


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
# Largeur du palmier, en part de la largeur du jambage : c'est le jambage qui doit le
# contenir. Réglé par la HAUTEUR (deux fois le cadre), le dattier aux palmes ouvertes
# — large des trois quarts de sa hauteur — débordait le jambage d'un quart de chaque côté,
# et se lisait posé sur le mur ; sur le cadre étroit d'un corps de porte, une timora à
# cote fixe faisait de même.
TIMORA_SUR_CADRE = 0.7
# L'emprise d'un cadre de porte de part et d'autre de sa baie, corniche comprise.
ENCADREMENT_SHAAR = CHAMBRANLE + CHAMBRANLE_LISERE + 0.4


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
    palmier = min(cadre * TIMORA_SUR_CADRE / largeur_gravure("timora"), hauteur * 0.4)
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


# Pilastre engagé : fût, astragale, chapiteau. CHOIX (Rambam, Beit HaBe'hira 1:11). Sous
# le soleil rasant du plan 1 un ressaut vertical ne jette pas d'ombre (voir l'appareil des
# lishkot) : c'est le chapiteau, en débord, qui le fait lire de loin.
PILASTRE_CHAPITEAU = 1.2

def pilastre(nom, paroi, u, z0, z1, col, mat=None, largeur=2.5, saillie=0.9):
    """`paroi` : (axe, cote de la face, sens de la saillie), comme pour `shaar`."""
    axe, cote, sens = paroi

    def pose(suffixe, demi, zb, zh, d):
        if axe == "x":
            box(f"{nom}_{suffixe}", u - demi, u + demi, cote, cote + sens * d, zb, zh, col, mat)
        else:
            box(f"{nom}_{suffixe}", cote, cote + sens * d, u - demi, u + demi, zb, zh, col, mat)

    pied_chapiteau = z1 - PILASTRE_CHAPITEAU
    pose("fut", largeur / 2, z0, pied_chapiteau, saillie)
    pose("astragale", largeur / 2 + 0.15, pied_chapiteau, pied_chapiteau + 0.3, saillie + 0.15)
    pose("chapiteau", largeur / 2 + 0.35, pied_chapiteau + 0.3, z1, saillie + 0.4)


# Ce qu'un pilastre laisse libre de part et d'autre de son chapiteau : sans lui, il se colle
# au chambranle d'une porte ou à l'angle d'un corps bâti.
DEGAGEMENT_PILASTRE = 1.0

def ordre_de_pilastres(nom, paroi, travee, hauteur, col, reserve=(), mat=None,
                       pas=10.0, largeur=2.5, saillie=0.9):
    """Pilastres au pas le plus proche de `pas` sur `travee` = (u0, u1), les deux bouts
    compris, sauf ceux qui empiètent sur un intervalle de `reserve` — une porte avec son
    cadre, un corps bâti, ce qui se dresse contre le mur. `hauteur` = (z0, z1)."""
    demi = largeur / 2 + 0.35 + DEGAGEMENT_PILASTRE
    u0, u1 = travee[0] + largeur / 2, travee[1] - largeur / 2
    n = max(1, round((u1 - u0) / pas))
    for i in range(n + 1):
        u = u0 + (u1 - u0) * i / n
        if any(u + demi > r0 and u - demi < r1 for r0, r1 in reserve):
            continue
        pilastre(f"{nom}_{i:03d}", paroi, u, *hauteur, col, mat, largeur=largeur, saillie=saillie)
