import math
from typing import NamedTuple

import bmesh
import numpy as np
from mathutils import Vector

import beit_hamikdash_gestes as G

from .matieres import ARGAMAN, LIN, OR, SHANI, TEKHELET, _matiere, laine, lin, metal, reteindre, trame
from .etoffes import _etoffes, surface_de
from .corps import BRAS, Gabarit, Humain
from .maillage import TOUR, Ceinture, Maillage, Teintes, _angles, _lisser_cercle, _vers, enveloppe, pave
from .habillage import (AVNET_BRODE, AVNET_DE_LIN, HAUT_Z, KUTONET, _crane_et_cheveux, _poils,
                        appliquer_visibilite, avnet, empiecement, lier, migbaat, mitznefet, mitznefet_relevee,
                        ourler)
from .ustensiles import tourner_profil, tube_simple
from .mise_en_scene import repere_vers


class Habits(NamedTuple):
    avnet: Teintes
    coiffe: object


BIGDEI_KEHOUNA = Habits(AVNET_BRODE, migbaat)
BIGDEI_LAVAN = Habits(AVNET_DE_LIN, mitznefet)


def cohen(nom, gabarit=Gabarit(), gris=False):
    return vetir_de_lin(Humain(nom, gabarit, **_poils(nom, gris)), BIGDEI_KEHOUNA)


# Un seul homme sous tous ses rôles : même stature, même teint, mêmes cheveux.
COHEN_GADOL = "cohen_gadol"
GABARIT_DU_COHEN_GADOL = Gabarit(1.78, age=0.62)


def le_cohen_gadol(nom):
    return Humain(nom, GABARIT_DU_COHEN_GADOL, qui=COHEN_GADOL, **_poils(COHEN_GADOL, True))


# Les quatre habits blancs du Cohen Gadol à Kippour (Vayikra 16:4 ; Rambam Klei HaMikdash 8:3).
def cohen_gadol(nom):
    return vetir_de_lin(le_cohen_gadol(nom), BIGDEI_LAVAN)


# Lin (Rambam Klei HaMikdash 8:1), pieds nus (Zeva'him 24a).
def vetir_de_lin(h, habits):
    robe = h.vetir_mpfb(KUTONET)
    h.detendre()
    empiecement(h, robe)
    ceindre(h, robe, habits.avnet)
    coiffer(h, habits.coiffe)
    appliquer_visibilite(h, h.visible & ~h.efface)
    return h


def ceindre(h, robe, teintes):
    ceinture = Ceinture(h, h.squelette.tete("lowerarm_l").z)
    ceinture.serrer(h, robe)
    ceint = Maillage()
    avnet(ceint, ceinture, surface_de(h, [robe]), teintes)
    lier(h, ceint, f"{h.nom}_avnet", lin())


def coiffer(h, coiffe):
    coiffure = Maillage()
    coiffe(coiffure, h)
    lier(h, coiffure, f"{h.nom}_{coiffe.__name__}", lin(), "head")


# Les huit habits (Rambam Klei HaMikdash 8:4) : sur la kutonet, le me'il, l'éphod et son 'heshev, le 'hoshen, la
# mitznefet et le tsits. L'avnet, noué sous le me'il (10:1), ne se voit pas : il n'est pas bâti, ses pans le traversaient.
def cohen_gadol_en_or(nom):
    h = le_cohen_gadol(nom)
    robe = h.vetir_mpfb(KUTONET)
    h.detendre()
    col = empiecement(h, robe)
    pans = meil(h, robe, col)
    coiffer(h, mitznefet_relevee)
    dessus = surface_de(h, pans)
    epaules = ephod(h, pans, dessus)
    hoshen(h, surface_de(h, pans + epaules))
    tzitz(h)
    appliquer_visibilite(h, h.visible & ~h.efface)
    return h


def ephod_tisse():
    return _matiere("Figure_Ephod", 0.45, 0.55, tissu=trame("ephod", 28, serge=True))


def pierre():
    return _matiere("Figure_Pierre", 0.12)


# « וְהַזָּהָב … לוֹקֵחַ חוּט אֶחָד זָהָב טָהוֹר וְנוֹתְנוֹ עִם שִׁשָּׁה חוּטִין » (Rambam Klei HaMikdash 9:5) : chaque fil de
# couleur tordu avec un fil d'or ; les quatre couleurs en rayures de trame, CHOIX.
FILS_D_OR = tuple(tuple(0.40 * c + 0.60 * o for c, o in zip(couleur, OR)) for couleur in (TEKHELET, ARGAMAN, SHANI, LIN))


def fil_d_or(j):
    return FILS_D_OR[j % len(FILS_D_OR)]


# « הַמְּעִיל כֻּלּוֹ תְּכֵלֶת … וְאֵין לוֹ בֵּית יָד אֶלָּא נֶחְלָק לִשְׁתֵּי כְּנָפַיִם מִסּוֹף הַגָּרוֹן עַד לְמַטָּה » (Rambam
# Klei HaMikdash 9:3) : la robe et son empiècement recopiés à `ecart`, sans les manches, fendus sur les flancs sous
# l'aisselle. L'ourlet à une main du sol : CHOIX.
MEIL_ECART = 0.014
MEIL_OURLET = 0.12


def meil(h, robe, col):
    materiau = teinte_de(robe.data.materials[0], "Figure_Meil", TEKHELET)
    pans = []
    for source in (robe, col):
        copie = source.copy()
        copie.data = source.data.copy()
        copie.name = f"{h.nom}_meil" if source is robe else f"{h.nom}_meil_col"
        for c in source.users_collection:
            c.objects.link(copie)
        copie.data.materials[0] = materiau
        gonfler(copie, MEIL_ECART)
        pans.append(copie)
    ourler(h, pans[0], h.sol + MEIL_OURLET)
    fendre(h, pans[0], h.z_epaule - 0.12)
    oter_les_manches(h, pans[1])
    pans_et_grelots(h, pans[0])
    return pans


def teinte_de(materiau, nom, couleur):
    if nom in _etoffes:
        return _etoffes[nom]
    copie = materiau.copy()
    copie.name = nom
    for noeud in copie.node_tree.nodes:
        relief = any(lien.to_node.bl_idname == "ShaderNodeNormalMap" for lien in noeud.outputs[0].links) if noeud.outputs else False
        if noeud.bl_idname == "ShaderNodeTexImage" and noeud.image and not relief:
            noeud.image = reteindre(noeud.image, couleur)
    _etoffes[nom] = copie
    return copie


def gonfler(objet, ecart):
    me = objet.data
    for v in me.vertices:
        v.co += v.normal * ecart


def _armature_de(humain, objet):
    return humain.rig.matrix_world.inverted() @ objet.matrix_world


# Les manches ôtées — toute face qu'un bras emporte — et les flancs ouverts sous `z_aisselle` : une bande de
# `MEIL_FENTE` de part et d'autre du plan des épaules, coupée à trois plans pour que ses bords tombent droit.
MEIL_FENTE = 0.022


def fendre(h, objet, z_aisselle):
    oter_les_manches(h, objet)
    passage = _armature_de(h, objet)
    retour = passage.inverted()
    normales = passage.to_3x3().transposed()
    cy = h.squelette.tete("spine_02").y
    bm = bmesh.new()
    bm.from_mesh(objet.data)
    for point, normale in ((Vector((0.0, 0.0, z_aisselle)), HAUT_Z), (Vector((0.0, cy - MEIL_FENTE, 0.0)), G.DEVANT),
                           (Vector((0.0, cy + MEIL_FENTE, 0.0)), G.DEVANT)):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=retour @ point,
                               plane_no=(normales @ normale).normalized())

    def flanc(f):
        p = passage @ f.calc_center_median()
        return p.z < z_aisselle and abs(p.y - cy) < MEIL_FENTE and abs(p.x) > 0.08

    bmesh.ops.delete(bm, geom=[f for f in bm.faces if flanc(f)], context="FACES")
    bm.to_mesh(objet.data)
    bm.free()


def oter_les_manches(h, objet):
    groupes = objet.vertex_groups
    bm = bmesh.new()
    bm.from_mesh(objet.data)
    deform = bm.verts.layers.deform.active
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if any(
        sum(w for g, w in v[deform].items() if groupes[g].name.startswith(BRAS)) > 0.5 for v in f.verts)], context="FACES")
    bm.to_mesh(objet.data)
    bm.free()


# « וּמֵבִיא שְׁנַיִם וְשִׁבְעִים זוּגִים … וְתוֹלֶה בּוֹ שִׁשָּׁה וּשְׁלֹשִׁים בְּשׁוּלֵי כָּנָף זֶה וְשִׁשָּׁה וּשְׁלֹשִׁים בְּשׁוּלֵי כָּנָף זֶה »,
# « פַּעֲמוֹן וְרִמּוֹן » (Rambam Klei HaMikdash 9:4) : sur chaque pan, trente-six clochettes d'or entre trente-six grenades
# de laine, qu'on n'a pas ouvertes. Leur taille : CHOIX, un doigt.
GRELOTS_PAR_PAN = 36
CLOCHETTE = ((0.000, 0.0012), (0.002, 0.0040), (0.007, 0.0052), (0.011, 0.0062), (0.012, 0.0066))
GRENADE = ((0.000, 0.0012), (0.003, 0.0050), (0.008, 0.0064), (0.013, 0.0054), (0.016, 0.0028), (0.018, 0.0036))
LAINES_DES_GRENADES = (TEKHELET, ARGAMAN, SHANI)


def pans_et_grelots(h, pan):
    passage = _armature_de(h, pan)
    points = [passage @ v.co for v in pan.data.vertices]
    bas = min(p.z for p in points)
    cy = h.squelette.tete("spine_02").y
    ourlet = sorted((p for p in points if p.z < bas + 0.006), key=lambda p: math.atan2(p.x, -(p.y - cy)))
    devant = [p for p in ourlet if abs(math.atan2(p.x, -(p.y - cy))) < math.pi / 2.0]
    derriere = [p for p in ourlet if abs(math.atan2(p.x, -(p.y - cy))) >= math.pi / 2.0]
    derriere.sort(key=lambda p: math.atan2(p.x, -(p.y - cy)) % TOUR)
    or_, laine_ = Maillage(), Maillage()
    for bord in (devant, derriere):
        for k, p in enumerate(_le_long(bord, 2 * GRELOTS_PAR_PAN)):
            dehors = Vector((p.x, p.y - cy, 0.0)).normalized()
            repere = repere_vers(p + dehors * 0.004 - HAUT_Z * 0.002, -HAUT_Z, dehors)
            if k % 2 == 0:
                tourner_profil(or_, repere, CLOCHETTE, OR, 10, "jupe")
            else:
                tourner_profil(laine_, repere, GRENADE, LAINES_DES_GRENADES[(k // 2) % 3], 10, "jupe")
    lier(h, or_, f"{h.nom}_paamonim", metal())
    lier(h, laine_, f"{h.nom}_rimonim", laine())


# `n` points également espacés le long de la polyligne, demi-pas aux deux bouts.
def _le_long(points, n):
    cumul = [0.0]
    for a, b in zip(points, points[1:]):
        cumul.append(cumul[-1] + (b - a).length)
    sortie = []
    for k in range(n):
        s = cumul[-1] * (k + 0.5) / n
        i = min(max(int(np.searchsorted(cumul, s)) - 1, 0), len(points) - 2)
        u = (s - cumul[i]) / max(cumul[i + 1] - cumul[i], 1e-9)
        sortie.append(points[i].lerp(points[i + 1], u))
    return sortie


# Au plus près de la surface `dessus` en tirant de `depart` selon `direction` ; None si le rayon ne touche rien.
def toucher(dessus, depart, direction):
    return dessus.ray_cast(depart, direction)[0]


# « רָחְבּוֹ כְּרֹחַב גַּבּוֹ … וְאָרְכּוֹ מִכְּנֶגֶד אַצִּילֵי הַיָּדַיִם מֵאֲחוֹרָיו עַד הָרַגְלַיִם … וְתוֹפֵר עָלָיו שְׁתֵּי כְּתֵפוֹת »
# (Rambam Klei HaMikdash 9:9) : un tablier dans le dos, de l'avnet aux chevilles, tombé droit du plus saillant du me'il ;
# le 'heshev noué devant, « עַל לִבּוֹ תַּחַת הַחשֶׁן » (9:11) ; les deux épaulettes, leur shoham chacune.
# Rend les épaulettes, sur lesquelles le 'hoshen se pose.
EPHOD_ECART = 0.02


def ephod(h, pans, dessus):
    z_heshev = h.squelette.tete("lowerarm_l").z
    demi = abs(h.squelette.tete("upperarm_l").x)
    z_bas = h.sol + MEIL_OURLET + 0.05
    rangs, colonnes = 36, 29
    xs = np.linspace(-demi, demi, colonnes)
    tombe = np.full(colonnes, -np.inf)
    anneaux = []
    for i in range(rangs):
        z = z_heshev + 0.02 - (z_heshev + 0.02 - z_bas) * i / (rangs - 1)
        dos = np.array([_y_du_dos(dessus, x, z) for x in xs])
        tombe = np.maximum(tombe, _combler(dos))
        anneaux.append([Vector((x, y + EPHOD_ECART, z)) for x, y in zip(xs, _lisser_ligne(tombe))])
    tissu = Maillage()
    tissu.nappe(anneaux, lambda i, j: fil_d_or(j), "dos", ferme=False)
    heshev(tissu, h, pans, z_heshev)
    lier(h, tissu, f"{h.nom}_ephod", ephod_tisse())
    return katefot(h, dessus, anneaux[0][2], anneaux[0][-3], z_heshev)


# Tiré de derrière vers l'avant : le y du dos, NaN où le rayon passe à côté.
def _y_du_dos(dessus, x, z):
    touche = toucher(dessus, Vector((x, 0.8, z)), G.DEVANT)
    return touche.y if touche is not None else np.nan


def _combler(valeurs):
    bons = ~np.isnan(valeurs)
    indices = np.arange(len(valeurs))
    return np.interp(indices, indices[bons], valeurs[bons])


def _lisser_ligne(r, fois=2):
    for _ in range(fois):
        r = np.concatenate([r[:1], 0.25 * r[:-2] + 0.5 * r[1:-1] + 0.25 * r[2:], r[-1:]])
    return r


# Le tour du me'il à sa hauteur, fentes comprises : l'enveloppe de ses sommets.
def heshev(mm, h, pans, z, largeur=0.05):
    sommets = np.vstack([h.points_objet(pan) for pan in pans])
    rangs = []
    for dz in (-largeur / 2, 0.0, largeur / 2):
        points = tranche_de(sommets, z + dz, 0.02)
        cy = 0.5 * (points[:, 1].min() + points[:, 1].max())
        rayons = _lisser_cercle(enveloppe(points, (0.0, cy)), 4) + EPHOD_ECART + 0.004
        rangs.append([Vector((r * _vers(th)[0], cy + r * _vers(th)[1], z + dz)) for th, r in zip(_angles(), rayons)])
    mm.nappe(rangs, lambda i, j: fil_d_or(j // 3), "buste")


def tranche_de(points, z, epaisseur):
    return points[np.abs(points[:, 2] - z) < epaisseur][:, :2]


# Du haut de l'éphod, par-dessus l'épaule, jusqu'au-dessus du 'heshev devant (Rambam Klei HaMikdash 9:11) : chaque
# pas du ruban est tiré vers le me'il, de derrière, d'en haut, puis de devant.
KATEF_ECART = EPHOD_ECART + 0.006


def katefot(h, dessus, gauche, droite, z_heshev, largeur=0.05):
    objets = []
    for depart in (gauche, droite):
        s = math.copysign(1.0, depart.x)
        tirs = _tirs_du_katef(h, depart, s * 0.145, z_heshev)
        rangs = [[_touche_ou(dessus, origine + G.GAUCHE * (largeur / 2 * t), direction) for t in (-1.0, 1.0)]
                 for origine, direction in tirs]
        mm = Maillage()
        mm.nappe(rangs, lambda i, j: fil_d_or(i // 2), "buste", ferme=False)
        sommet = max((0.5 * (a + b) for a, b in rangs), key=lambda c: c.z)
        shoham(mm, dessus, sommet)
        objets.append(lier(h, mm, f"{h.nom}_katef_{'l' if s > 0 else 'r'}", ephod_tisse()))
    return objets


def _tirs_du_katef(h, depart, x_devant, z_heshev):
    z_epaule = h.z_epaule + 0.02
    tirs = [(Vector((depart.x, 0.8, depart.z + (z_epaule - depart.z) * k / 10)), G.DEVANT) for k in range(10)]
    for k in range(9):
        y = 0.10 - 0.20 * k / 8
        x = depart.x + (x_devant - depart.x) * k / 8
        tirs.append((Vector((x, y, h.z_tete + 0.3)), -HAUT_Z))
    tirs += [(Vector((x_devant, -0.8, z_epaule - (z_epaule - z_heshev - 0.05) * k / 10)), -G.DEVANT) for k in range(1, 11)]
    return tirs


def _touche_ou(dessus, origine, direction, ecart=KATEF_ECART):
    lieu, normale, _, _ = dessus.ray_cast(origine, direction)
    if lieu is None:
        return origine + direction * 0.7
    return lieu + normale * ecart


def _poser_sur(dessus, p, ecart):
    lieu, normale, _, _ = dessus.find_nearest(p)
    return p if lieu is None else lieu + normale * ecart


# « וְקוֹבֵעַ עַל כָּל כָּתֵף וְכָתֵף אֶבֶן שֹׁהַם מְרֻבָּע מֻשְׁקָע בְּבַיִת שֶׁל זָהָב » (Rambam Klei HaMikdash 9:9).
SHOHAM = (0.035, 0.045, 0.035)


def shoham(mm, dessus, sommet):
    lieu, normale, _, _ = dessus.find_nearest(sommet)
    n = normale if lieu is not None else HAUT_Z
    u = G.GAUCHE - n * G.GAUCHE.dot(n)
    u.normalize()
    v = n.cross(u)
    base = sommet + n * 0.004
    pave(mm, base, u, v, (0.05, 0.04), 0.006, OR, "buste")
    pave(mm, base + n * 0.006, u, v, (0.04, 0.03), 0.006, SHOHAM, "buste")


# Les douze pierres (Shemot 28:17–20) ; les couleurs suivent les identifications courantes, CHOIX : odem, pitda, bareket ;
# nofekh, sapir, yahalom ; leshem, shevo, a'hlama ; tarshish, shoham, yashfe.
PIERRES = ((0.55, 0.04, 0.03), (0.72, 0.62, 0.10), (0.05, 0.42, 0.18),
           (0.08, 0.40, 0.42), (0.06, 0.12, 0.55), (0.85, 0.87, 0.90),
           (0.78, 0.36, 0.06), (0.55, 0.52, 0.48), (0.36, 0.10, 0.45),
           (0.30, 0.58, 0.62), (0.035, 0.045, 0.035), (0.20, 0.40, 0.16))
ZERET = 0.24


# « אָרְכּוֹ אַמָּה וְרָחְבּוֹ זֶרֶת וְכוֹפְלוֹ לִשְׁנַיִם … אַרְבָּעָה טוּרִים … מְשֻׁקָּע בְּבַיִת שֶׁל זָהָב » (Rambam Klei HaMikdash
# 9:6) ; les chaînettes d'or de ses coins hauts aux épaulettes, les fils de tekhelet de ses coins bas (9:8, 9:11).
def hoshen(h, dessus):
    z_haut = h.z_epaule - 0.075
    demi = ZERET / 2
    rangs, colonnes = 7, 7
    xs = np.linspace(-demi, demi, colonnes)
    zs = np.linspace(z_haut, z_haut - ZERET, rangs)
    touches = [toucher(dessus, Vector((x, -0.8, z)), Vector((0.0, 1.0, 0.0))) for z in zs for x in xs]
    y = min(t.y for t in touches if t is not None) - 0.010
    plaque = Maillage()
    plaque.nappe([[Vector((x, y, z)) for x in xs] for z in zs], lambda i, j: fil_d_or(i + j), "buste", ferme=False)
    plaque.nappe([[Vector((x, y + 0.006, z)) for x in xs[::-1]] for z in zs], lambda i, j: fil_d_or(i + j), "buste",
                 ferme=False)
    lier(h, plaque, f"{h.nom}_hoshen", ephod_tisse())
    serti, gemmes = Maillage(), Maillage()
    u, v = G.GAUCHE.copy(), HAUT_Z.copy()
    for k, couleur in enumerate(PIERRES):
        rang, col = divmod(k, 3)
        centre = Vector(((1 - col) * ZERET / 3, y, z_haut - ZERET / 8 - rang * ZERET / 4))
        pave(serti, centre, u, v, (0.064, 0.050), 0.005, OR, "buste")
        pave(gemmes, centre + G.DEVANT * 0.005, u, v, (0.052, 0.040), 0.006, couleur, "buste")
    for s in (-1.0, 1.0):
        coin = Vector((s * (demi - 0.01), y, z_haut))
        epaule = Vector((s * (abs(h.squelette.tete("upperarm_l").x) - 0.02), 0.0, h.z_epaule + 0.05))
        chaine_ = [_poser_sur(dessus, coin.lerp(epaule, t), 0.02) if 0.0 < t < 1.0 else coin.lerp(epaule, t)
                   for t in np.linspace(0.0, 1.0, 8)]
        serti.nappe(tube_simple(chaine_, 0.004, 6), OR, "buste")
        bas = Vector((s * (demi - 0.01), y, z_haut - ZERET))
        cote_ = Vector((s * (demi + 0.05), y + 0.05, h.squelette.tete("lowerarm_l").z + 0.05))
        gemmes.nappe(tube_simple([bas, bas.lerp(cote_, 0.5) + G.DEVANT * 0.01, cote_], 0.003, 6), TEKHELET, "buste")
    lier(h, serti, f"{h.nom}_hoshen_zahav", metal())
    lier(h, gemmes, f"{h.nom}_hoshen_avanim", pierre())


# « טַס שֶׁל זָהָב רֹחַב שְׁתֵּי אֶצְבָּעוֹת וּמַקִּיף מֵאֹזֶן לְאֹזֶן … וּפְתִיל תְּכֵלֶת … נִקְשָׁר … כְּנֶגֶד הָעֹרֶף » (Rambam
# Klei HaMikdash 9:1-2) : sur le front, sous la mitznefet — les cheveux paraissent entre les deux (Zeva'him 19a).
TZITZ_LARGEUR = 0.038
TZITZ_OREILLE = math.radians(78.0)


def tzitz(h):
    yeux = h.points_objet(h.accessoires[0]).mean(axis=0)
    z = float(yeux[2]) + 0.036
    points = _crane_et_cheveux(h)
    tout = _angles(40)
    plaque, fil = Maillage(), Maillage()
    rangs = []
    for dz, dehors in ((-TZITZ_LARGEUR / 2, 0.0), (-TZITZ_LARGEUR / 2, 0.0025), (TZITZ_LARGEUR / 2, 0.0025),
                       (TZITZ_LARGEUR / 2, 0.0)):
        bande = points[np.abs(points[:, 2] - (z + dz)) < 0.008]
        cy = 0.5 * (bande[:, 1].min() + bande[:, 1].max())
        r = _lisser_cercle(enveloppe(bande, (0.0, cy), 40), 3)
        th = np.linspace(-TZITZ_OREILLE, TZITZ_OREILLE, 24)
        ri = np.interp(th % TOUR, np.append(tout, TOUR), np.append(r, r[0])) + 0.004 + dehors
        rangs.append([Vector((a * _vers(t)[0], cy + a * _vers(t)[1], z + dz)) for t, a in zip(th, ri)])
    plaque.nappe(rangs, OR, "head", ferme=False)
    bande = points[np.abs(points[:, 2] - z) < 0.008]
    cy = 0.5 * (bande[:, 1].min() + bande[:, 1].max())
    r = _lisser_cercle(enveloppe(bande, (0.0, cy), 40), 3)
    th = np.linspace(TZITZ_OREILLE, TOUR - TZITZ_OREILLE, 20)
    ri = np.interp(th, np.append(tout, TOUR), np.append(r, r[0])) + 0.012
    cordon = [Vector((a * _vers(t)[0], cy + a * _vers(t)[1], z - 0.005)) for t, a in zip(th, ri)]
    fil.nappe(tube_simple(cordon, 0.0025, 5), TEKHELET, "head")
    lier(h, plaque, f"{h.nom}_tzitz", metal(), "head")
    lier(h, fil, f"{h.nom}_petil_tekhelet", laine(), "head")
