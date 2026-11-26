import bmesh
import bpy
import math
from mathutils import Vector, noise

from .primitives import tissage
from .primitives.parametres import MODELE, TEFAH, Z_AZ, Z_EZN, Z_MAARAKHA, Z_SOVEV, Z_YESSOD, m
from .primitives.matieres import (MAT_ARGENT, MAT_BOIS_CHARBON, MAT_BOIS_MAARAKHA, MAT_BOIS_ROUSSI,
                                  MAT_BRONZE, MAT_CEDRE, MAT_CENDRE, MAT_CHAUX, MAT_CHENE, MAT_CHAUX_FEU, MAT_EAU,
                                  MAT_FER, MAT_MARBRE, MAT_SEL, MAT_SIKRA, braise, nuee)
from .primitives.volumes import (_objet, _poser, alea, box, braises, crochet, cyl, cyl_between, gzir, lampe, link_to,
                                 mesh_from_pydata, revolution, sphere, tore)
from .primitives.ouvrages import table_de_service


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
# « עָלָה חֲמִשָּׁה טְפָחִים וְכָנַס חֲמִשָּׁה טְפָחִים זֶהוּ יְסוֹד… עָלָה שְׁלֹשִׁים טְפָחִים וְכָנַס חֲמִשָּׁה טְפָחִים זֶהוּ סוֹבֵב » (Rambam Beit HaBe'hira 2:7) :
# yessod, sovev et keranot se comptent « בְּאַמָּה בַּת חֲמִשָּׁה » (Mena'hot 97b), en hauteur comme en retrait.
RETRAIT_MIZBEACH = 5 * TEFAH
# « מֵבִיא אֲבָנִים שְׁלֵמוֹת גְּדוֹלוֹת וּקְטַנּוֹת וּמֵבִיא סִיד וְזֶפֶת וְקוּנְיָא וּמְמַחֶה וְשׁוֹפֵךְ לְתוֹךְ מַלְבֵּן גָּדוֹל כְּמִדָּתוֹ »
# (Rambam Beit HaBe'hira 2:16) : l'autel est coulé dans un moule à sa mesure — faces planes, arêtes droites,
# que la chaux repassée deux fois l'an (Middot 3:4) n'a fait qu'adoucir. Rayon de l'arête : CHOIX.
ARETE_CHAUX = 0.06
# Ce qu'un bloc s'enfonce dans ce qui le porte, et ce qu'un voisin mord dans sa face.
REPRISE_CHAUX = 0.3
# Un sommet de l'arrondi tous les 15° : la tangente de 45° à 90°, portée sur le rayon.
ARRONDI_CHAUX = (0.0, 0.42, 0.73, 1.0)
# L'arrondi tourne de 15° par facette : au-delà, c'est une arête vive — le bord d'un puits, le dessous d'une tête — que le lissé ne franchit pas.
PLI_VIF_CHAUX = math.radians(40)

def _lisser_la_chaux(o):
    """Lisse l'arrondi, garde vives les arêtes franches, et laisse les grandes faces décider de la normale de leurs sommets : elles restent planes à l'œil."""
    o.data.shade_smooth()
    o.data.set_sharp_from_angle(angle=PLI_VIF_CHAUX)
    normales = o.modifiers.get("Normales") or o.modifiers.new("Normales", 'WEIGHTED_NORMAL')
    normales.weight = 100
    normales.keep_sharp = True

def _cotes_chaux(a, b, r_bas, r_haut):
    """Les lignes du maillage entre a et b : l'arrondi des deux bouts."""
    return sorted({round(c, 6) for f in ARRONDI_CHAUX for c in (a + r_bas * f, b - r_haut * f)})

def _sur_la_chaux(p, dedans, r, ecart=0.0, forme=None):
    """Le point p de la face dressée, porté sur l'arrondi de rayon r autour de `dedans`, puis déformé."""
    c = Vector([min(max(p[k], dedans[0][k]), dedans[1][k]) for k in range(3)])
    nu = c + (Vector(p) - c).normalized() * (r + ecart)
    return forme(nu) if forme else nu

def _dedans_chaux(x0, x1, y0, y1, z0, z1, r, vifs=(), reprise=REPRISE_CHAUX):
    """La boîte que l'arrondi entoure. Un côté `vifs`, enfoui dans un voisin ou coupé net, ne s'arrondit pas."""
    rayon = {cote: 0.0 if cote in vifs else r for cote in ("x0", "x1", "y0", "y1")}
    return ((x0 + rayon["x0"], y0 + rayon["y0"], z0 - reprise),
            (x1 - rayon["x1"], y1 - rayon["y1"], z1 - r)), rayon

def en_pente(z0, z1, dessus, r=ARETE_CHAUX):
    """La forme qui couche le dessus plat d'un bloc, de cote z1, sur la pente `dessus(y)` : l'arête descend telle quelle, et une ligne du flanc que la pente dépasse se range sous elle."""
    def coucher(v):
        if v.z <= z0:
            return v
        haut = max(dessus(v.y), z0)
        dans_l_arete = v.z >= z1 - r - 1e-9
        return Vector((v.x, v.y, haut - (z1 - v.z) if dans_l_arete else min(v.z, haut - r)))
    return coucher

def bloc_de_chaux(name, x0, x1, y0, y1, z0, z1, col, mat, r=ARETE_CHAUX, ouvert=(), creux=0.0,
                  reprise=REPRISE_CHAUX, couvert=None, forme=None, franc=(), baie=None, paliers=(), socles=()):
    """Boîte de chaux aux faces planes, enfoncée de `reprise` dans ce qui la porte et ouverte en dessous ; sans reprise, pleine elle est en l'air et son dessous fermé, creuse elle est posée à fleur.

    `ouvert` : les côtés ("x0", "x1", "y0", "y1") qui continuent dans un bloc voisin, sans face ni arrondi.
    `franc` : les côtés coupés net, dont la face se bâtit sans arrondi — un bloc en porte-à-faux s'y soude.
    `creux` : l'épaisseur de paroi d'un bloc percé de haut en bas, comme une keren.
    `couvert` : le rectangle (x0, x1, y0, y1) du dessus qu'un bloc posé cache, et qui ne se bâtit pas.
    `baie` : le rectangle (y0, y1, z0, z1) du flanc x0 laissé ouvert — une niche.
    `paliers` : les cotes où les flancs gardent une ligne de sommets, celles d'un bloc qui s'y soude.
    `socles` : les blocs posés à fleur sur le dessus, qui en continuent les flancs, par leurs bornes et leur paroi (x0, x1, y0, y1, creux) — l'arête du haut n'y tourne pas.
    `forme` : ce qui déforme le bloc — une pente, un biais.
    """
    (dedans, rayon) = _dedans_chaux(x0, x1, y0, y1, z0, z1, r, (*ouvert, *franc), reprise)
    trou = (x0 + creux, x1 - creux, y0 + creux, y1 - creux)
    xs = sorted({*_cotes_chaux(x0, x1, rayon["x0"], rayon["x1"]), *(trou[:2] if creux else ()), *(couvert[:2] if couvert else ()),
                 *(c for sx0, sx1, _, _, paroi in socles for c in (*_cotes_chaux(sx0, sx1, r, r), sx0 + paroi, sx1 - paroi))})
    ys = sorted({*_cotes_chaux(y0, y1, rayon["y0"], rayon["y1"]), *(trou[2:] if creux else ()), *(couvert[2:] if couvert else ()),
                 *(baie[:2] if baie else ()), *(c for _, _, sy0, sy1, paroi in socles for c in (*_cotes_chaux(sy0, sy1, r, r), sy0 + paroi, sy1 - paroi))})
    # La bande enfouie a ses faces à elle : collée à une coupe du dallage, elle seule tombe à l'export, pas le flanc entier.
    zs = sorted({*_cotes_chaux(z0 - reprise, z1, 0.0, r), round(z0, 6), *paliers, *(baie[2:] if baie else ())})
    dedans_sous_un_socle = (dedans[0], (*dedans[1][:2], z1))
    index, verts, faces = {}, [], []

    def sous_un_socle(p):
        """Sous les flancs du bloc posé : jusqu'au bord quand il est à fleur, et pas sous l'arrondi de ses autres arêtes."""
        def couvre(c, a, b, bord_a, bord_b):
            return (a if a == bord_a else a + r) <= c <= (b if b == bord_b else b - r)
        return any(couvre(p[0], sx0, sx1, x0, x1) and couvre(p[1], sy0, sy1, y0, y1) for sx0, sx1, sy0, sy1, _ in socles)

    def sommet(p):
        # Les lignes du maillage sont arrondies, les bornes du bloc non : sans cet arrondi, une cote en tefa'him ne se soude pas.
        cle = tuple(round(c, 6) for c in p)
        if cle not in index:
            index[cle] = len(verts)
            verts.append(tuple(_sur_la_chaux(p, dedans_sous_un_socle if sous_un_socle(p) else dedans, r, forme=forme)))
        return index[cle]

    def grille(us, vs, point, sauf=None):
        for i in range(len(us) - 1):
            for j in range(len(vs) - 1):
                if sauf and sauf((us[i] + us[i + 1]) / 2, (vs[j] + vs[j + 1]) / 2):
                    continue
                faces.append([sommet(point(us[i], vs[j])), sommet(point(us[i + 1], vs[j])),
                              sommet(point(us[i + 1], vs[j + 1])), sommet(point(us[i], vs[j + 1]))])

    def perce(u, v):
        return creux and trou[0] < u < trou[1] and trou[2] < v < trou[3]

    def cache(u, v):
        return couvert and couvert[0] < u < couvert[1] and couvert[2] < v < couvert[3]

    def dans_la_baie(z, y):
        return baie and baie[0] < y < baie[1] and baie[2] < z < baie[3]

    grille(xs, ys, lambda u, v: (u, v, z1), sauf=lambda u, v: perce(u, v) or cache(u, v))
    if not reprise and not creux:
        grille(ys, xs, lambda u, v: (v, u, z0))
    if "x1" not in ouvert:
        grille(ys, zs, lambda u, v: (x1, u, v))
    if "x0" not in ouvert:
        grille(zs, ys, lambda u, v: (x0, v, u), sauf=dans_la_baie)
    if "y1" not in ouvert:
        grille(zs, xs, lambda u, v: (v, y1, u))
    if "y0" not in ouvert:
        grille(xs, zs, lambda u, v: (u, y0, v))
    if creux:
        # Le puits descend jusque sous le dessus qui porte le bloc : c'est lui qui en fait le fond.
        bord = ([(x, trou[2]) for x in xs if trou[0] <= x <= trou[1]]
                + [(trou[1], y) for y in ys if trou[2] < y <= trou[3]]
                + [(x, trou[3]) for x in reversed(xs) if trou[0] <= x < trou[1]]
                + [(trou[0], y) for y in reversed(ys) if trou[2] < y < trou[3]])
        fond = len(verts)
        verts += [(x, y, z0 - REPRISE_CHAUX) for x, y in bord]
        for k in range(len(bord)):
            suivant = (k + 1) % len(bord)
            faces.append([sommet((*bord[k], z1)), sommet((*bord[suivant], z1)), fond + suivant, fond + k])
    o = mesh_from_pydata(name, verts, faces, col, mat)
    _lisser_la_chaux(o)
    o["sans_biseau"] = True
    return o

def souder_la_chaux(nom, blocs):
    """Un seul maillage pour des blocs qui se continuent : leurs sommets communs se confondent, et ni le lissé ni la lumière cuite n'y marquent de couture."""
    tete, suite = blocs[0], blocs[1:]
    maille = bmesh.new()
    for bloc in blocs:
        maille.from_mesh(bloc.data)
    bmesh.ops.remove_doubles(maille, verts=maille.verts, dist=m(0.0005))
    maille.to_mesh(tete.data)
    maille.free()
    for bloc in suite:
        donnees = bloc.data
        bpy.data.objects.remove(bloc, do_unlink=True)
        bpy.data.meshes.remove(donnees)
    tete.name = tete.data.name = nom
    _lisser_la_chaux(tete)
    return tete

def ceinture_de_chaux(name, bloc, z0, z1, col, mat, r=ARETE_CHAUX):
    """Bande peinte entre z0 et z1 sur les flancs du bloc de bornes `bloc` : sans épaisseur, à un cheveu de la chaux."""
    x0, x1, y0, y1 = bloc[:4]
    dedans, _ = _dedans_chaux(*bloc, r)
    xs, ys = _cotes_chaux(x0, x1, r, r), _cotes_chaux(y0, y1, r, r)
    tour = ([(x, y0) for x in xs] + [(x1, y) for y in ys[1:]]
            + [(x, y1) for x in reversed(xs[:-1])] + [(x0, y) for y in reversed(ys[1:-1])])
    n = len(tour)
    verts = [tuple(_sur_la_chaux((x, y, z), dedans, r, ecart=0.02)) for z in (z0, z1) for x, y in tour]
    faces = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]
    o = mesh_from_pydata(name, verts, faces, col, mat)
    o.data.shade_smooth()
    o["sans_biseau"] = True
    return o

CORPS = (MX0 + RETRAIT_MIZBEACH, MX1 - RETRAIT_MIZBEACH, MY0 + RETRAIT_MIZBEACH, MY1 - RETRAIT_MIZBEACH, Z_AZ, Z_SOVEV)
HAUT = (CORPS[0] + RETRAIT_MIZBEACH, CORPS[1] - RETRAIT_MIZBEACH, CORPS[2] + RETRAIT_MIZBEACH, CORPS[3] - RETRAIT_MIZBEACH)
# Le yessod est une seule bande de chaux : ses tronçons se continuent par leurs côtés ouverts, et mordent dans le corps.
souder_la_chaux("Mizbeach_yessod", [
    bloc_de_chaux("Mizbeach_yessod_N", CORPS[0] + REPRISE_CHAUX, MX1, CORPS[3] - REPRISE_CHAUX, MY1, Z_AZ, Z_YESSOD, "30_Mizbeach", MAT_CHAUX(),
                  ouvert=("x0", "y0")),
    bloc_de_chaux("Mizbeach_yessod_O", MX0, CORPS[0] + REPRISE_CHAUX, MY0, MY1, Z_AZ, Z_YESSOD, "30_Mizbeach", MAT_CHAUX(),
                  ouvert=("x1",)),
    bloc_de_chaux("Mizbeach_yessod_S", CORPS[0] + REPRISE_CHAUX, CORPS[0] + 1, MY0, CORPS[2] + REPRISE_CHAUX, Z_AZ, Z_YESSOD, "30_Mizbeach", MAT_CHAUX(),
                  ouvert=("x0", "y1")),
    bloc_de_chaux("Mizbeach_yessod_E", CORPS[1] - REPRISE_CHAUX, MX1, CORPS[3] - 1, CORPS[3] - REPRISE_CHAUX, Z_AZ, Z_YESSOD, "30_Mizbeach", MAT_CHAUX(),
                  ouvert=("x0", "y1")),
])
bloc_de_chaux("Mizbeach_corps", *CORPS, "30_Mizbeach", MAT_CHAUX(),
              couvert=(HAUT[0] + REPRISE_CHAUX, HAUT[1] - REPRISE_CHAUX, HAUT[2] + REPRISE_CHAUX, HAUT[3] - REPRISE_CHAUX))
# « וְאַרְבַּע הַקְּרָנוֹת חֲלוּלוֹת הָיוּ מִתּוֹכָן » (Rambam Beit HaBe'hira 2:8), « בִּנְיָן חָלוּל מְרֻבָּע לְכָל אַרְבַּע קְרָנוֹת » (2:7),
# coulées avec l'autel autour d'un noyau qu'on retire (2:16) : quatre murets autour d'un vide, dont les flancs continuent
# ceux de l'autel. « גֹּבַהּ כָּל קֶרֶן וְקֶרֶן חֲמִשָּׁה טְפָחִים. וְרִבּוּעַ כָּל קֶרֶן אַמָּה עַל אַמָּה » (2:8). Épaisseur des murets : CHOIX.
# Écarté : le Raavad sur 2:7, qui rentre les keranot des parois de l'autel.
PAROI_KEREN, HAUT_KEREN = 0.25, 5 * TEFAH
KERANOT = {"SE": (HAUT[1] - 1, HAUT[2]), "NE": (HAUT[1] - 1, HAUT[3] - 1), "NO": (HAUT[0], HAUT[3] - 1), "SO": (HAUT[0], HAUT[2])}
bloc_de_chaux("Mizbeach_haut", *HAUT, Z_SOVEV, Z_MAARAKHA, "30_Mizbeach", MAT_CHAUX_FEU(),
              socles=[(x, x + 1, y, y + 1, PAROI_KEREN) for x, y in KERANOT.values()])
for nm, (x, y) in KERANOT.items():
    bloc_de_chaux(f"Keren_{nm}", x, x + 1, y, y + 1, Z_MAARAKHA, Z_MAARAKHA + HAUT_KEREN, "30_Mizbeach", MAT_CHAUX_FEU(),
                  creux=PAROI_KEREN, reprise=0.0)
# « וְחוּט שֶׁל סִקְרָא חוֹגְרוֹ בָאֶמְצַע » (Middot 3:1) : la ligne rouge à mi-hauteur, qui sépare
# les sangs d'en haut des sangs d'en bas — le seul trait de couleur sur la chaux. La moitié des 58 tefa'him,
# « כְּשִׁשָּׁה טְפָחִים מִסּוֹף הַסּוֹבֵב וּלְמַטָּה » (Rambam 2:8-9). Largeur du trait : CHOIX.
Z_SIKRA = Z_SOVEV - 6 * TEFAH
ceinture_de_chaux("Mizbeach_sikra", CORPS, Z_SIKRA - 0.05, Z_SIKRA + 0.05, "30_Mizbeach", MAT_SIKRA())
# « מְקוֹם הַקְּרָנוֹת אַמָּה מִזֶּה וְאַמָּה מִזֶּה… מְקוֹם הִלּוּךְ רַגְלֵי הַכֹּהֲנִים, אַמָּה מִזֶּה וְאַמָּה מִזֶּה… מְקוֹם הַמַּעֲרָכָה » (Middot 3:1).
MAQOM_HAMAARAKHA = (HAUT[0] + 2, HAUT[1] - 2, HAUT[2] + 2, HAUT[3] - 2)
# « וְתַפּוּחַ הָיָה בְאֶמְצַע הַמִּזְבֵּחַ » (Tamid 2:2) ; ses « שְׁלֹשׁ מֵאוֹת כּוֹר » sont « בִּלְשׁוֹן הֲבַאי » (Tamid 29a). Taille : CHOIX.
TAPUACH, R_TAPUACH, H_TAPUACH = ((MX0 + MX1) / 2, (MY0 + MY1) / 2), 2.0, 1.5
# La grande à l'est du tapoua'h, qu'elle touche (Tamid 2:4) ; 8 × 8 amot : CHOIX.
GEDOLA = (TAPUACH[0] + R_TAPUACH, TAPUACH[0] + R_TAPUACH + 8, TAPUACH[1] - 4, TAPUACH[1] + 4)
_X0 = MAQOM_HAMAARAKHA[0]
# Trois chaque jour, une de plus à Kippour (R. Yossé, Yoma 4:6 ; Rambam Temidin 2:4-5). Leur taille, 3 × 3 amot : CHOIX.
# La ketoret « מִכְּנֶגֶד קֶרֶן מַעֲרָבִית דְּרוֹמִית, מָשׁוּךְ מִן הַקֶּרֶן כְּלַפֵּי צָפוֹן אַרְבַּע אַמּוֹת » (Tamid 2:5), le long du bord ouest (Tif'eret Israël 2:32).
# Le kiyoum haesh « בְּכָל מָקוֹם שֶׁיִּרְצֶה מִן הַמִּזְבֵּחַ » (Rambam Temidin 2:9) : sa place, CHOIX.
# Kippour, pour les braises de la ketoret du Kodesh HaKodashim (Bartenura Yoma 4:6), « מִלִּפְנֵי ה׳ מִצַּד מַעֲרָב » (Rashi Yoma 45b),
# face aux portes de l'Oulam et du Heikhal : sa place sur ce bord, CHOIX.
MAARAKHOT_DE_GZIRIN = (("ketoret", _X0, _X0 + 3, HAUT[2] + 1 + 4, HAUT[2] + 1 + 7),
                       ("kiyum", TAPUACH[0] - 6, TAPUACH[0] - 3, TAPUACH[1] + 8, TAPUACH[1] + 11),
                       ("kippour", _X0, _X0 + 3, TAPUACH[1] + 4, TAPUACH[1] + 7))
# « וְרֶוַח הָיָה בֵין הַגִּזְרִין » (Tamid 2:4) : les bûches ne sont pas jointives.
R_GZIR, REWACH, PAS_LIT, LITS = 0.19, 0.16, 0.34, 4
# Du bois fendu à la longueur d'un bras, pas des troncs : longueur d'une bûche et jour entre deux bouts, CHOIX.
LONG_GZIR, JOUR_GZIR = 2.6, 0.25
RETRAIT_LIT = 0.25
RETRAIT_GEHALIM = RETRAIT_LIT * (LITS - 1) + 0.15

def lit_de_gzirin(nm, lit, xa, xb, ya, yb):
    """Un lit de bûches posées bout à bout, en rangs espacés ; les lits se croisent, et le feu a mangé ceux du haut."""
    z = Z_MAARAKHA + R_GZIR + lit * PAS_LIT
    mat = (MAT_BOIS_MAARAKHA(), MAT_BOIS_ROUSSI(), MAT_BOIS_CHARBON(), MAT_BOIS_CHARBON())[lit]
    le_long_de_x = lit % 2 == 0
    (a0, a1), (b0, b1) = ((ya, yb), (xa, xb)) if le_long_de_x else ((xa, xb), (ya, yb))
    retrait = RETRAIT_LIT * lit
    a0, a1, b0, b1 = a0 + retrait, a1 - retrait, b0 + retrait, b1 - retrait
    pas = 2 * R_GZIR + REWACH
    rangs = max(2, int((a1 - a0 - 2 * R_GZIR) / pas) + 1)
    marge = (a1 - a0 - (rangs - 1) * pas) / 2
    buches = max(1, round((b1 - b0) / LONG_GZIR))
    longueur = (b1 - b0) / buches
    for rang in range(rangs):
        for k in range(buches):
            cle = f"Maarakha_{nm}_gzir_{lit}_{rang:02d}{k}"
            if alea(cle, 8) < 0.12 * lit:
                continue
            c0, c1 = (a0 + marge + rang * pas + (alea(cle, i) - 0.5) * REWACH * 1.4 for i in (1, 9))
            d0 = b0 + k * longueur + JOUR_GZIR * alea(cle, 2) - (0.4 * alea(cle, 3) if k == 0 else 0.0)
            d1 = b0 + (k + 1) * longueur - JOUR_GZIR * alea(cle, 4) + (0.4 * alea(cle, 5) if k == buches - 1 else 0.0)
            z0, z1 = (z + (alea(cle, i) - 0.5) * 0.10 for i in (50, 51))
            rayon = R_GZIR * (0.8 + 0.4 * alea(cle, 52))
            p0, p1 = (((d0, c0, z0), (d1, c1, z1)) if le_long_de_x else ((c0, d0, z0), (c1, d1, z1)))
            gzir(cle, p0, p1, rayon, "30_Mizbeach", mat)

def maarakha(nm, xa, xb, ya, yb):
    """Quatre lits de gzirin croisés, et le bassin de braises sous celui du haut, qui le déborde : on ne voit de lui que sa nappe, entre les bûches."""
    for lit in range(LITS):
        lit_de_gzirin(nm, lit, xa, xb, ya, yb)
    braises(f"Maarakha_{nm}_gehalim", xa + RETRAIT_GEHALIM, xb - RETRAIT_GEHALIM, ya + RETRAIT_GEHALIM, yb - RETRAIT_GEHALIM,
            Z_MAARAKHA + 1.5 * R_GZIR + (LITS - 2) * PAS_LIT, "30_Mizbeach", braise("Braise"), profondeur=0.05)

for nm, xa, xb, ya, yb in MAARAKHOT_DE_GZIRIN:
    maarakha(nm, xa, xb, ya, yb)

# La grande selon Bartenura (Tamid 2:3-4) : un tas de מֻרְבִּיּוֹת, « עֲנָפִים שֶׁל תְּאֵנָה », où l'on couche
# « שְׁנֵי עֵצִים אֲרֻכִּים וּמְשׁוּפִין… לְתוֹךְ אֹרֶךְ הַמַּעֲרָכָה », dont les bouts intérieurs touchent le tapoua'h.
# Entre les deux, l'aliyta, « חֲרִיּוֹת וְקִסְמִין דַּקִּין תּוֹחֲבִין בֵּין הַגְּדוֹלִים », et à l'est « הַפֶּתַח וְהַחַלּוֹן ».
# Grosseur des deux gzirin et jour entre eux, nombre et taille des branches, hauteur du tas, du petah et du 'halon : CHOIX.
R_GZIR_GADOL, JOUR_DES_GZIRIN = 0.28, 1.0
MURAVIOT, ALIYTA = 420, 40
H_TAS = 1.5
PETAH, HALON = (0.0, 0.8), (1.05, 1.35)

def hauteur_du_tas(x, y):
    xa, xb, ya, yb = GEDOLA
    bord = max(abs(2 * (x - xa) / (xb - xa) - 1), abs(2 * (y - ya) / (yb - ya) - 1))
    return H_TAS * (0.35 + 0.65 * (1 - bord * bord))

def dans_l_ouverture(x, y, z):
    """Ce que le petah, et le 'halon au-dessus de lui, laissent vide entre les deux gzirin, à l'est."""
    xb, haut = GEDOLA[1], z - Z_MAARAKHA
    entre = abs(y - TAPUACH[1]) < JOUR_DES_GZIRIN / 2 + 0.1
    return entre and ((x > xb - 1.8 and PETAH[0] <= haut < PETAH[1]) or (x > xb - 1.2 and HALON[0] <= haut < HALON[1]))

def bois_selon_le_feu(cle, z):
    """Le feu prend par le bas : charbon et bois roussi s'y mêlent au bois frais."""
    tirage, bas = alea(cle, 7), z < Z_MAARAKHA + 0.4
    if bas and tirage < 0.5:
        return MAT_BOIS_CHARBON()
    return MAT_BOIS_ROUSSI() if tirage < (0.75 if bas else 0.3) else MAT_BOIS_MAARAKHA()

def bouts_de_la_branche(centre, longueur, cap, pente):
    """Les deux bouts d'une branche couchée autour de `centre`, raccourcie pour rester sur la ma'arakha."""
    xa, xb, ya, yb = GEDOLA
    d = Vector((math.cos(cap) * math.cos(pente), math.sin(cap) * math.cos(pente), math.sin(pente)))
    c = Vector(centre)
    demi = longueur / 2
    for axe, (bas, haut) in ((0, (xa, xb)), (1, (ya, yb))):
        if abs(d[axe]) > 1e-6:
            demi = min(demi, min(c[axe] - bas, haut - c[axe]) / abs(d[axe]))
    return tuple(c - d * demi), tuple(c + d * demi)

def coucher_les_muraviot():
    xa, xb, ya, yb = GEDOLA
    for i in range(MURAVIOT):
        cle = f"Maarakha_gedola_zmora_{i:03d}"
        x, y = xa + 0.3 + (xb - xa - 0.6) * alea(cle, 1), ya + 0.3 + (yb - ya - 0.6) * alea(cle, 2)
        rayon = 0.03 + 0.04 * alea(cle, 3)
        z = Z_MAARAKHA + rayon + (hauteur_du_tas(x, y) - 2 * rayon) * alea(cle, 4)
        p0, p1 = bouts_de_la_branche((x, y, z), 1.2 + 1.2 * alea(cle, 5), 2 * math.pi * alea(cle, 6), 0.5 * (alea(cle, 8) - 0.5))
        milieu = tuple((a + b) / 2 for a, b in zip(p0, p1))
        if any(dans_l_ouverture(*p) for p in (p0, milieu, p1)):
            continue
        gzir(cle, p0, p1, rayon, "30_Mizbeach", bois_selon_le_feu(cle, z), fentes=(2 * math.pi,))

def coucher_les_deux_gzirin():
    """Les deux grosses bûches est-ouest, de part et d'autre du jour où l'on glisse l'aliyta."""
    xa, xb, _, _ = GEDOLA
    for k, sens in enumerate((-1, 1)):
        y = TAPUACH[1] + sens * (JOUR_DES_GZIRIN / 2 + R_GZIR_GADOL)
        p0, p1 = (xa - 0.35, y, Z_MAARAKHA + R_GZIR_GADOL), (xb - 0.1, y, Z_MAARAKHA + R_GZIR_GADOL)
        o = cyl_between(f"Maarakha_gedola_gzir_{k}", p0, p1, R_GZIR_GADOL, "30_Mizbeach", MAT_BOIS_MAARAKHA(), verts=14)
        o["moelle"] = [m(c) for c in (*p0, *p1)]

def glisser_l_aliyta():
    xa, xb, _, _ = GEDOLA
    for i in range(ALIYTA):
        cle = f"Maarakha_gedola_aliyta_{i:02d}"
        x = xa + 0.3 + (xb - xa - 1.0) * alea(cle, 1)
        y = TAPUACH[1] + (alea(cle, 2) - 0.5) * JOUR_DES_GZIRIN * 0.8
        z = Z_MAARAKHA + 0.05 + 0.4 * alea(cle, 3)
        demi, ecart = 0.2 + 0.3 * alea(cle, 4), 0.3 * (alea(cle, 5) - 0.5)
        gzir(cle, (x - demi, y - ecart, z), (x + demi, y + ecart, z + 0.05), 0.015 + 0.015 * alea(cle, 6), "30_Mizbeach",
             bois_selon_le_feu(cle, z), fentes=(2 * math.pi,))

coucher_les_muraviot()
coucher_les_deux_gzirin()
glisser_l_aliyta()
braises("Maarakha_gedola_gehalim", GEDOLA[0] + 0.5, GEDOLA[1] - 0.5, GEDOLA[2] + 0.5, GEDOLA[3] - 0.5,
        Z_MAARAKHA + 0.12, "30_Mizbeach", braise("Braise"), profondeur=0.05)
# Le feu lui-même. La ma'arakha était une boîte noire sans source : la colonne de fumée
# montait d'un autel éteint, et la rampe du plan 7b n'avait que la lumière du ciel — la
# raison pour laquelle elle ne se détachait ni de l'autel ni du dallage.
GX0, GX1, GY0, GY1 = GEDOLA
feu = lampe("Maarakha_feu", 'AREA', (m((GX0 + GX1) / 2), m((GY0 + GY1) / 2), m(Z_MAARAKHA + 1.2)))
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
                    Z_MAARAKHA + 0.5 + 42 * t, (1.6 + 2.6 * t) * (0.7 + 0.6 * alea("fumee", 3 * i + 2)),
                    "77_Fumee", MAT_FUMEE, segs=12)
    volute.visible_shadow = False

# Kevesh : 32 × 16 au sud (Middot 3:3), « אוֹכֵל בָּאָרֶץ שְׁלֹשִׁים אַמָּה… וּפוֹרֵחַ מִמֶּנָּה אַמָּה עַל הַיְסוֹד
# וְאַמָּה עַל הַסּוֹבֵב. וַאֲוִיר מְעַט הָיָה מַפְסִיק בֵּין הַכֶּבֶשׁ לַמִּזְבֵּחַ » (Rambam Beit HaBe'hira 2:13 ;
# Zeva'him 62b), « וְגֹבַהּ הַכֶּבֶשׁ תֵּשַׁע אַמּוֹת פָּחוֹת שְׁתוּת עַד כְּנֶגֶד הַמַּעֲרָכָה » (2:13). La tête en porte-à-faux couvre les deux
# retraits, de cinq tefa'him chacun, et s'arrête avant la face de l'autel : la rampe fait 31 amot et 4 tefa'him moins
# l'air, pas 32 (CHOIX, comme les 28 × 28 de Middot 3:1 arrondissent 28 et 4 tefa'him). Épaisseur de la tête et largeur de l'air : CHOIX.
xc = (MX0 + MX1) / 2
KX0, KX1, KY0 = xc - 8, xc + 8, MY0 - 30
AVIR_KEVESH, NIMA = 0.25, 0.02
# Piège : ce NIMA écrase celui de la parokhet tissée, qui est câblée plus tard (Bayit).
tissage.NIMA = NIMA
z_kevesh = lambda y: Z_AZ + (Z_MAARAKHA - Z_AZ) * (y - KY0) / (MY0 - KY0)
# « וְחַלּוֹן הָיְתָה בְּמַעֲרָבוֹ שֶׁל כֶּבֶשׁ אַמָּה עַל אַמָּה, וּרְבוּבָה הָיְתָה נִקְרֵאת » (Rambam 2:14 ; Middot 3:3) :
# la niche où l'on posait les pesoulei 'hatat haof. Place, hauteur et profondeur : CHOIX.
REVOUVA_Y, REVOUVA_Z = MY0 - 12, Z_AZ + 2
PENTE_KEVESH = en_pente(Z_AZ, Z_MAARAKHA, z_kevesh)
REVOUVA_YS, REVOUVA_ZS = (REVOUVA_Y, REVOUVA_Y + 1), (REVOUVA_Z, REVOUVA_Z + 1)
# Le coin est coupé net au nord, sous la tête en porte-à-faux qui s'y soude ; la niche s'ouvre dans son flanc ouest.
souder_la_chaux("Kevesh", [
    bloc_de_chaux("Kevesh", KX0, KX1, KY0, MY0, Z_AZ, Z_MAARAKHA, "30_Mizbeach", MAT_CHAUX(), ouvert=("y0",), franc=("y1",),
                  forme=PENTE_KEVESH, baie=(*REVOUVA_YS, *REVOUVA_ZS), paliers=(Z_MAARAKHA - 1,)),
    bloc_de_chaux("Kevesh_rosh", KX0, KX1, MY0, HAUT[2] - AVIR_KEVESH, Z_MAARAKHA - 1, Z_MAARAKHA, "30_Mizbeach", MAT_CHAUX(),
                  ouvert=("y0",), reprise=0.0),
])
FOND_REVOUVA = KX0 + 0.9
mesh_from_pydata("Kevesh_revouva",
                 [(x, y, z) for x in (KX0, FOND_REVOUVA) for y in REVOUVA_YS for z in REVOUVA_ZS],
                 [[4, 6, 2, 0], [3, 7, 5, 1], [1, 5, 4, 0], [6, 7, 3, 2], [5, 7, 6, 4]],
                 "30_Mizbeach", MAT_CHAUX())["sans_biseau"] = True
# « שְׁנֵי כְּבָשִׁים קְטַנִּים יוֹצְאִין מִן הַכֶּבֶשׁ, שֶׁבָּהֶן פּוֹנִים לַיְסוֹד וְלַסּוֹבֵב; וּמוּבְדָּלִין מִן הַמִּזְבֵּחַ
# מְלֹא נִימָא » (Zeva'him 62b ; Rambam 2:14). Les côtés sont ceux de Rashi ad loc. : celui du sovev
# « יצא במזרחו של כבש… ועולה באלכסון עד שמגיע לסובב », celui du yessod « יוצא למערבו…
# פונה לשמאלו ליסוד דרומי ומתחיל לצאת בשיפולו של כבש », et le yessod du sud n'est qu'à l'angle
# sud-ouest (Rambam 2:10) : la rampe du yessod part du pied du kevesh contre son flanc et
# descend en biais jusqu'à l'angle, sur le yessod de l'ouest et celui du sud. Le sovev part à 18 amot
# de l'autel et non du pied, pour laisser au sol la place du deshen à dix amot du pied
# (Tamid 1:4). Largeurs et départ : CHOIX.
SOVEV_Y0, SOVEV_Y1 = MY0 - 18, CORPS[2] - NIMA
bloc_de_chaux("Kevesh_katan_sovev", KX1 - REPRISE_CHAUX, KX1 + 2.5, SOVEV_Y0, SOVEV_Y1, Z_AZ, Z_SOVEV, "30_Mizbeach", MAT_CHAUX(),
              ouvert=("x0", "y0"),
              forme=en_pente(Z_AZ, Z_SOVEV, lambda y: Z_AZ + (Z_SOVEV - Z_AZ) * (y - SOVEV_Y0) / (SOVEV_Y1 - SOVEV_Y0)))
YESSOD_Y1 = MY0 - NIMA
YESSOD_X_BAS, YESSOD_X_HAUT = KX0 - 2, MX0

def biais_du_yessod(v):
    """La petite rampe du yessod monte en glissant vers l'angle sud-ouest."""
    part = (v.y - KY0) / (YESSOD_Y1 - KY0)
    return Vector((v.x + part * (YESSOD_X_HAUT - YESSOD_X_BAS), v.y, Z_AZ + max(v.z - Z_AZ, 0.0) * min(max(part, 0.0), 1.0) + min(v.z - Z_AZ, 0.0)))

bloc_de_chaux("Kevesh_katan_yessod", YESSOD_X_BAS, YESSOD_X_BAS + 2, KY0, YESSOD_Y1, Z_AZ, Z_YESSOD, "30_Mizbeach", MAT_CHAUX(),
              ouvert=("y0",), forme=biais_du_yessod)
TOURS_TAS, RAYONS_TAS = 28, 7

def tas(name, centre, z0, hauteur, rayon, mat):
    """Un tas versé — cendre, sel : un talus qui s'affaisse, au pourtour inégal, jamais un cône."""
    verts, faces = [(centre[0], centre[1], z0 + hauteur)], []
    for j in range(1, RAYONS_TAS + 1):
        part = j / RAYONS_TAS
        for i in range(TOURS_TAS):
            angle = 2 * math.pi * i / TOURS_TAS
            bord = 1.0 + 0.22 * noise.noise(Vector((centre[0] + 2.0 * math.cos(angle), centre[1] + 2.0 * math.sin(angle), z0)))
            grain = 0.05 * hauteur * noise.noise(Vector((part * 6.0 * math.cos(angle), part * 6.0 * math.sin(angle), centre[0])) )
            talus = (1.0 - part) ** 1.3 * (1.0 + 0.6 * part)
            verts.append((centre[0] + rayon * bord * part * math.cos(angle), centre[1] + rayon * bord * part * math.sin(angle),
                          z0 + hauteur * talus + (grain if j < RAYONS_TAS else 0.0)))
    faces += [[0, 1 + i, 1 + (i + 1) % TOURS_TAS] for i in range(TOURS_TAS)]
    for j in range(RAYONS_TAS - 1):
        a, b = 1 + j * TOURS_TAS, 1 + (j + 1) * TOURS_TAS
        faces += [[a + i, b + i, b + (i + 1) % TOURS_TAS, a + (i + 1) % TOURS_TAS] for i in range(TOURS_TAS)]
    o = mesh_from_pydata(name, verts, faces, "30_Mizbeach", mat)
    o.data.shade_smooth()
    o["sans_biseau"] = True
    return o

# « וּשְׁנַיִם בְּמַעֲרַב הַכֶּבֶשׁ, אֶחָד שֶׁל שַׁיִשׁ וְאֶחָד שֶׁל כֶּסֶף; עַל שֶׁל שַׁיִשׁ הָיוּ נוֹתְנִים אֶת הָאֵבָרִים, עַל
# שֶׁל כֶּסֶף כְּלֵי שָׁרֵת » (Shekalim 6:4 ; Rambam 2:15). Cotes, celles des tables du Beit
# HaMitba'haïm ; place, à l'ouest de la rampe du yessod : CHOIX.
HAUTEUR_SHULCHAN = 1.5
SHULCHAN_KESSEF = (KX0 - 8.5, KX0 - 7.5, MY0 - 15, MY0 - 13)
table_de_service("Kevesh_shulchan_shaish", (KX0 - 8.5, KX0 - 7.5, MY0 - 20, MY0 - 18), Z_AZ, HAUTEUR_SHULCHAN, "30_Mizbeach", MAT_MARBRE())
table_de_service("Kevesh_shulchan_kessef", SHULCHAN_KESSEF, Z_AZ, HAUTEUR_SHULCHAN, "30_Mizbeach", MAT_ARGENT())
# « וַהֲרֵי הַמַּחְתָּה נְתוּנָה בַמִּקְצוֹעַ בֵּין הַכֶּבֶשׁ לַמִּזְבֵּחַ, בְּמַעֲרָבוֹ שֶׁל כָּבֶשׁ » (Tamid 1:4 ; Rambam Temidin
# ouMoussafin 2:12) : à terre, dans l'angle du flanc ouest du kevesh et de la face sud de l'autel. D'argent, quatre kabin
# et le manche court (Yoma 4:4) : le bassin de la ma'hta de Kippour un dixième plus large. Manche vers le sud : CHOIX.
MACHTA_X, MACHTA_Y, MACHTA_R = KX0 - 0.45, CORPS[2] - 0.45, 0.358
revolution("Machta_kessef", MACHTA_X, MACHTA_Y, Z_AZ,
           [(0.264, 0.0), (0.286, 0.0), (0.33, 0.176), (MACHTA_R, 0.182), (MACHTA_R, 0.204), (0.325, 0.204),
            (0.303, 0.176), (0.259, 0.033), (0.0, 0.033)], "30_Mizbeach", MAT_ARGENT(), verts=32)
cyl_between("Machta_kessef_manche", (MACHTA_X, MACHTA_Y - MACHTA_R + 0.03, Z_AZ + 0.15),
            (MACHTA_X, MACHTA_Y - MACHTA_R - 0.6, Z_AZ + 0.04), 0.035, "30_Mizbeach", MAT_ARGENT(), verts=12)
# « נָטְלוּ אֶת הַמַּגְרֵפוֹת וְאֶת הַצִּנּוֹרוֹת » (Tamid 2:1), les pelles du deshen et les fourches des membres
# (Tosfot Yom Tov ad loc.). Le texte ne dit pas où on les prend : sur la table d'argent des kelei sharet (Shekalim 6:4),
# deux de chaque, CHOIX. Le cuivre est celui des « יָעָיו… וּמִזְלְגֹתָיו » de l'autel du Mishkan (Shemot 27:3).
PLATEAU_KESSEF = Z_AZ + HAUTEUR_SHULCHAN
X_SHULCHAN = (SHULCHAN_KESSEF[0] + SHULCHAN_KESSEF[1]) / 2
Y_MAGREFOT, R_MAGREFOT = SHULCHAN_KESSEF[2] + 0.45, 0.3
for k in range(2):
    z = PLATEAU_KESSEF + 0.035 * k
    revolution(f"Magrefot_{k}", X_SHULCHAN, Y_MAGREFOT, z,
               [(R_MAGREFOT, 0.0), (R_MAGREFOT, 0.015), (0.22, 0.045), (0.08, 0.06), (0.0, 0.06)],
               "30_Mizbeach", MAT_BRONZE(), verts=24)
    cyl_between(f"Magrefot_{k}_manche", (X_SHULCHAN, Y_MAGREFOT + R_MAGREFOT - 0.05, z + 0.025),
                (X_SHULCHAN, SHULCHAN_KESSEF[3] - 0.1, z + 0.025), 0.03, "30_Mizbeach", MAT_BRONZE(), verts=8)
for k, x in enumerate((SHULCHAN_KESSEF[0] + 0.12, SHULCHAN_KESSEF[1] - 0.12)):
    z = PLATEAU_KESSEF + 0.025
    cyl_between(f"Tsinorot_{k}", (x, SHULCHAN_KESSEF[2] + 0.75, z), (x, SHULCHAN_KESSEF[3] - 0.05, z), 0.025,
                "30_Mizbeach", MAT_BRONZE(), verts=8)
    for j, d in enumerate((-0.06, 0.0, 0.06)):
        cyl_between(f"Tsinorot_{k}_shen_{j}", (x, SHULCHAN_KESSEF[2] + 0.78, z), (x + d, SHULCHAN_KESSEF[2] + 0.4, z),
                    0.012, "30_Mizbeach", MAT_BRONZE(), verts=6)
# « וּפְסַכְתֵּר הָיְתָה כְלִי גָדוֹל מַחֲזֶקֶת לֶתֶךְ, וּשְׁתֵּי שַׁרְשְׁרוֹת הָיוּ בָהּ, אַחַת שֶׁהוּא מוֹשֵׁךְ בָּהּ וְיוֹרֵד, וְאַחַת שֶׁהוּא
# אוֹחֵז בָּהּ מִלְמַעְלָן » ; « וּמוֹרִידִין בָּהּ אֶת הַדֶּשֶׁן מֵעַל גַּבֵּי הַמִּזְבֵּחַ » (Tamid 5:5 ; Rambam Temidin 2:13). Un lethekh,
# 90 kabin à 1,38 l (fiche §8g), 1,1 ama³ ; « סיר של נחושת » (Rashi, cité par Siftei 'Hakhamim, Bamidbar 4:13). Forme,
# place entre les deux tables et longueur des chaînes : CHOIX.
PESAKHTER_X, PESAKHTER_Y, PESAKHTER_R = X_SHULCHAN, MY0 - 16.5, 0.70
revolution("Pesakhter", PESAKHTER_X, PESAKHTER_Y, Z_AZ,
           [(0.0, 0.0), (0.55, 0.0), (0.68, 0.30), (PESAKHTER_R, 0.55), (0.66, 0.90), (0.62, 0.90), (0.65, 0.55),
            (0.63, 0.30), (0.50, 0.05), (0.0, 0.05)], "30_Mizbeach", MAT_BRONZE(), verts=32)
for k, sens in enumerate((-1, 1)):
    anneau_y = PESAKHTER_Y + sens * 0.66
    tore(f"Pesakhter_anneau_{k}", PESAKHTER_X, anneau_y, Z_AZ + 0.96, 0.08, 0.02, "30_Mizbeach", MAT_BRONZE(),
         rotation=(0, math.pi / 2, 0))
    chaine = [(PESAKHTER_X, anneau_y, Z_AZ + 0.9), (PESAKHTER_X + 0.5, anneau_y + sens * 0.15, Z_AZ + 0.04),
              (PESAKHTER_X + 1.4, anneau_y + sens * 0.25, Z_AZ + 0.04), (PESAKHTER_X + 2.2, anneau_y + sens * 0.1, Z_AZ + 0.04)]
    for j, (p, q) in enumerate(zip(chaine, chaine[1:])):
        cyl_between(f"Pesakhter_shalshelet_{k}_{j}", p, q, 0.03, "30_Mizbeach", MAT_BRONZE(), verts=6)
# « הָפַךְ פָּנָיו לַצָּפוֹן, הָלַךְ לְמִזְרָחוֹ שֶׁל כֶּבֶשׁ כְּעֶשֶׂר אַמּוֹת. צָבַר אֶת הַגֶּחָלִים עַל גַּבֵּי הָרִצְפָה רָחוֹק
# מִן הַכֶּבֶשׁ שְׁלשָׁה טְפָחִים » (Tamid 1:4) : trois tefa'him, une demi-ama. Taille du tas : CHOIX.
tas("Kevesh_makom_deshen", (KX1 + 1.5, KY0 + 10), Z_AZ, 0.5, 1.0, MAT_CENDRE())
tas("Maarakha_tapuach", TAPUACH, Z_MAARAKHA, H_TAPUACH, R_TAPUACH, MAT_CENDRE())
# « בִּשְׁלֹשָׁה מְקוֹמוֹת הַמֶּלַח נְתוּנָה… וְעַל גַּבֵּי הַכֶּבֶשׁ » (Mena'hot 21b), là où l'on sale les membres,
# posés « מֵחֲצִי הַכֶּבֶשׁ וּלְמַטָּה בְּמַעֲרָבוֹ, וּמְלָחוּם » (Tamid 4:3). Un tas, sa taille et sa place dans
# cette moitié : CHOIX. Son fond plat s'enfonce dans la pente côté haut.
MELACH_X, MELACH_Y, MELACH_R = KX0 + 2.5, KY0 + 9, 0.8
tas("Kevesh_melach", (MELACH_X, MELACH_Y), z_kevesh(MELACH_Y - MELACH_R) - 0.05, 0.4 + z_kevesh(MELACH_Y + MELACH_R) - z_kevesh(MELACH_Y - MELACH_R),
    MELACH_R, MAT_SEL())
# « בְּרֹאשׁוֹ שֶׁל מִזְבֵּחַ – שֶׁשָּׁם מוֹלְחִין הַקּוֹמֶץ וְהַלְּבוֹנָה וְהַקְּטוֹרֶת » (Mena'hot 21b). Sa place sur le sommet : CHOIX,
# dans l'ama de passage du sud, à l'est de l'arrivée du kevesh, hors du feu.
tas("Mizbeach_melach", (xc + 4, HAUT[2] + 1.5), Z_MAARAKHA, 0.4, 0.4, MAT_SEL())
# « עָלָה בַכֶּבֶשׁ וּפָנָה לִשְׂמֹאלוֹ, שְׁנֵי סְפָלִים שֶׁל כֶּסֶף הָיוּ שָׁם… מַעֲרָבִי שֶׁל מַיִם, מִזְרָחִי שֶׁל יָיִן »
# (Soucca 4:9 ; Rambam Temidin ouMousafin 10:7), « נתונים אצל הקרן… סמוכין זה לזה » (Rashi Soucca 48b),
# la corne sud-ouest. Le bec de l'eau plus fin que celui du vin, « כְּדֵי שֶׁיִּכְלֶה הַמַּיִם עִם הַיַּיִן
# כְּאֶחָד » (Rambam ibid.). Taille, profil et sens des becs : CHOIX. Avis écarté : de chaux noircie
# par le vin, selon R. Yehouda (même michna).
SEFEL = [(0.14, 0.0), (0.18, 0.03), (0.30, 0.22), (0.32, 0.32), (0.29, 0.32), (0.27, 0.24), (0.0, 0.07)]
for nm, x, r_bec in (("mayim", HAUT[0] + 1.5, 0.03), ("yayin", HAUT[0] + 2.3, 0.05)):
    y = HAUT[2] + 0.5
    revolution(f"Sefel_{nm}", x, y, Z_MAARAKHA, SEFEL, "30_Mizbeach", MAT_ARGENT(), verts=24)
    cyl_between(f"Sefel_{nm}_hotem", (x, y + 0.2, Z_MAARAKHA + 0.08), (x, y + 0.42, Z_MAARAKHA + 0.02), r_bec,
                "30_Mizbeach", MAT_ARGENT(), verts=8)
# Kiyor : entre l'Oulam et le Mizbea'h, « וּמָשׁוּךְ כְּלַפֵּי הַדָּרוֹם » (Middot 3:6). La même
# michna donne les 22 amot et les douze marches ; avec leurs rovadim elles en prennent 19
# (Bartenura ad loc.) et ne laissent que 3 amot de plat au pied de l'autel. Le bassin se
# pose donc au sud de la volée, large de 22 (CHOIX), sur le dallage.
# Bronze, sur son pied (le כַּן, Shemot 30:18) ; douze robinets, « שְׁנֵים עָשָׂר דַּד »,
# le perfectionnement de Ben Katin (Yoma 3:10 ; fiche §7). « שַׁחֲרִית בְּמִילּוּאוֹ מְקַדֵּשׁ… מִן הָעֶלְיוֹן,
# עַרְבִית בִּירִידָתוֹ… מִן הַתַּחְתּוֹן » (Yoma 37a), lu par Melekhet Shelomoh (ad loc.) : des deux d'avant,
# Ben Katin garde l'unique עֶלְיוֹן, posé entre les onze qu'il ajoute en bas, aucun sous lui, à peine plus
# haut. Le matin, douze cohanim ensemble ; le soir, le tamid se fait à onze (Yoma 2:5), tous en bas.
# Écarté : douze en haut et douze en bas, « לֹא מַשְׁמָע כֵּן כְּלָל » (Melekhet Shelomoh) ; les douze sur
# un rang, la baraita ne parlant que des deux d'avant (Rashash Yoma 37a). Hauteurs et profil : CHOIX.
KIYOR_X, KIYOR_Y = -59, -14
KIYOR_Z = Z_AZ + 0.15
KIYOR = [(1.05, 0.0), (1.0, 0.12), (0.55, 0.30), (0.42, 0.50), (0.42, 0.70), (0.65, 0.80), (1.30, 0.95),
         (1.60, 1.25), (1.72, 1.70), (1.74, 2.05), (1.82, 2.20), (1.84, 2.30), (1.70, 2.30), (1.64, 2.05),
         (1.60, 1.70), (1.48, 1.30), (1.15, 1.08), (0.0, 1.00)]
DAD_ELYON = (1.62, 2.08, 1.60, 1.38)
DAD_TAHTON = (1.55, 2.02, 1.40, 1.15)
DADIM = [("Kiyor_dad_elyon", 0, DAD_ELYON)] + [(f"Kiyor_dad_tahton_{i:02d}", i, DAD_TAHTON) for i in range(1, 12)]
revolution("Kiyor", KIYOR_X, KIYOR_Y, KIYOR_Z, KIYOR, "30_Mizbeach", MAT_BRONZE(), verts=36)
cyl("Kiyor_eau", KIYOR_X, KIYOR_Y, KIYOR_Z + 1.95, KIYOR_Z + 2.0, 1.63, "30_Mizbeach", MAT_EAU(), verts=36)
for nom, place, (r_paroi, r_bec, z, z_bec) in DADIM:
    a = 2 * math.pi * place / 12
    dx, dy = math.cos(a), math.sin(a)
    bec = (KIYOR_X + r_bec * dx, KIYOR_Y + r_bec * dy, KIYOR_Z + z - 0.05)
    cyl_between(nom, (KIYOR_X + r_paroi * dx, KIYOR_Y + r_paroi * dy, KIYOR_Z + z), bec,
                0.06, "30_Mizbeach", MAT_BRONZE(), verts=8)
    cyl_between(f"{nom}_bec", bec, (bec[0], bec[1], KIYOR_Z + z_bec), 0.06, "30_Mizbeach", MAT_BRONZE(), verts=8)
# Mukhni de Ben Katin : « גִּילְגְּלָא דַּהֲוָה מְשַׁקְּעָא לֵיהּ » (Abayé, Yoma 37a), « גַּלְגַּל לְשַׁקְּעוֹ בַּבּוֹר,
# שֶׁיִּהְיוּ מֵימָיו מְחֻבָּרִים בַּבּוֹר » (Bartenura Yoma 3:10), pour la nuit — « מִצְוָה לְשַׁקּוֹעֵי » (R. Yo'hanan,
# Zeva'him 21b). De jour, le Kiyor pend au-dessus de son puits. Une chaîne suffirait à l'y descendre :
# la roue sert à le remonter, et c'est elle qu'on entend, « קוֹל הָעֵץ » (Tamid 1:4 ; 3:8 ; Tosfot Yom
# Tov Yoma 3:10). Treuil, poulie, quatre chaînes aux anses, margelle et cotes du puits : CHOIX.
MUKHNI_X = KIYOR_X - 3.5
Z_ROUE, Z_POTENCE, Z_ANNEAU = Z_AZ + 3.8, Z_AZ + 5.3, KIYOR_Z + 4.0
R_POULIE, Y_TAMBOUR = 0.22, KIYOR_Y + 0.45
BOR_R, BOR_DEMI = 2.22, (2.25, 1.6)
KIYOR_BOR = [(KIYOR_X - u, KIYOR_X + u, KIYOR_Y - v, KIYOR_Y + v, Z_EZN, Z_AZ) for u, v in (BOR_DEMI, BOR_DEMI[::-1])]
revolution("Mukhni_bor_margelle", KIYOR_X, KIYOR_Y, Z_AZ,
           [(2.85, 0.0), (2.85, 0.25), (2.75, 0.35), (BOR_R + 0.1, 0.35), (BOR_R, 0.25), (BOR_R, -1.0)],
           "30_Mizbeach", verts=36, capots=False)
cyl("Mukhni_bor_eau", KIYOR_X, KIYOR_Y, Z_EZN, Z_AZ - 1.5, BOR_R - 0.02, "30_Mizbeach", MAT_EAU(), verts=36)
cyl("Mukhni_poteau", MUKHNI_X, KIYOR_Y, Z_AZ, Z_AZ + 5.6, 0.22, "30_Mizbeach", MAT_CEDRE(), verts=12)
cyl_between("Mukhni_potence", (MUKHNI_X, KIYOR_Y, Z_POTENCE), (KIYOR_X, KIYOR_Y, Z_POTENCE), 0.16, "30_Mizbeach", MAT_CEDRE(), verts=10)
cyl_between("Mukhni_jambe_de_force", (MUKHNI_X, KIYOR_Y, Z_AZ + 3.6), (MUKHNI_X + 1.8, KIYOR_Y, Z_AZ + 5.2), 0.1, "30_Mizbeach", MAT_CEDRE(), verts=8)
tore("Mukhni_roue", MUKHNI_X, KIYOR_Y - 0.45, Z_ROUE, 0.8, 0.08, "30_Mizbeach", MAT_CEDRE(), rotation=(math.pi / 2, 0, 0))
for k in range(6):
    a = math.pi * k / 6
    cyl_between(f"Mukhni_rayon_{k}", (MUKHNI_X + 0.75 * math.cos(a), KIYOR_Y - 0.45, Z_ROUE + 0.75 * math.sin(a)),
                (MUKHNI_X - 0.75 * math.cos(a), KIYOR_Y - 0.45, Z_ROUE - 0.75 * math.sin(a)), 0.04, "30_Mizbeach", MAT_CEDRE(), verts=6)
for k in range(8):
    a = 2 * math.pi * (k + 0.5) / 8
    x, z = MUKHNI_X + 0.8 * math.cos(a), Z_ROUE + 0.8 * math.sin(a)
    cyl_between(f"Mukhni_yad_{k}", (x, KIYOR_Y - 0.45, z), (x, KIYOR_Y - 0.8, z), 0.04, "30_Mizbeach", MAT_CEDRE(), verts=6)
cyl_between("Mukhni_essieu", (MUKHNI_X, KIYOR_Y - 0.6, Z_ROUE), (MUKHNI_X, Y_TAMBOUR + 0.25, Z_ROUE), 0.06, "30_Mizbeach", MAT_FER(), verts=8)
for k, dy in enumerate((-0.15, 0.15)):
    cyl_between(f"Mukhni_tambour_joue_{k}", (MUKHNI_X, Y_TAMBOUR + dy - 0.02, Z_ROUE), (MUKHNI_X, Y_TAMBOUR + dy + 0.02, Z_ROUE),
                0.3, "30_Mizbeach", MAT_CEDRE(), verts=16)
cyl_between("Mukhni_tambour", (MUKHNI_X, Y_TAMBOUR - 0.13, Z_ROUE), (MUKHNI_X, Y_TAMBOUR + 0.13, Z_ROUE), 0.22,
            "30_Mizbeach", MAT_CHENE(), verts=16)
X_POULIE, Z_POULIE = KIYOR_X - R_POULIE, Z_POTENCE - 0.35
tore("Mukhni_poulie", X_POULIE, KIYOR_Y, Z_POULIE, R_POULIE, 0.05, "30_Mizbeach", MAT_CEDRE(), rotation=(math.pi / 2, 0, 0))
for k, dy in enumerate((-0.08, 0.08)):
    cyl_between(f"Mukhni_chape_{k}", (X_POULIE, KIYOR_Y + dy, Z_POTENCE), (X_POULIE, KIYOR_Y + dy, Z_POULIE), 0.025,
                "30_Mizbeach", MAT_FER(), verts=6)
cyl_between("Mukhni_hevel_kiyor", (KIYOR_X, KIYOR_Y, Z_POULIE), (KIYOR_X, KIYOR_Y, Z_ANNEAU + 0.1), 0.035,
            "30_Mizbeach", MAT_CHENE(), verts=6)
cyl_between("Mukhni_hevel_tambour", (X_POULIE - R_POULIE, KIYOR_Y, Z_POULIE), (MUKHNI_X + 0.15, Y_TAMBOUR, Z_ROUE + 0.16),
            0.035, "30_Mizbeach", MAT_CHENE(), verts=6)
tore("Mukhni_tabaat", KIYOR_X, KIYOR_Y, Z_ANNEAU, 0.1, 0.03, "30_Mizbeach", MAT_FER(), rotation=(math.pi / 2, 0, 0))
for k in range(4):
    a = 2 * math.pi * (k + 0.5) / 4
    dx, dy = math.cos(a), math.sin(a)
    tore(f"Kiyor_ozen_{k}", KIYOR_X + 1.9 * dx, KIYOR_Y + 1.9 * dy, KIYOR_Z + 2.2, 0.1, 0.025, "30_Mizbeach", MAT_BRONZE(),
         rotation=(math.pi / 2, 0, a))
    cyl_between(f"Mukhni_shalshelet_{k}", (KIYOR_X + 1.9 * dx, KIYOR_Y + 1.9 * dy, KIYOR_Z + 2.3), (KIYOR_X, KIYOR_Y, Z_ANNEAU - 0.08),
                0.03, "30_Mizbeach", MAT_FER(), verts=6)
# Magrefa : « נָטַל אֶחָד אֶת הַמַּגְרֵפָה וְזוֹרְקָהּ בֵּין הָאוּלָם וְלַמִּזְבֵּחַ » (Tamid 5:6), à terre là où
# elle tombe. « כלי גדול שהיו זורקים אותו כדי להשמיע קול » (Bartenura), « צורתו כצורת מגריפה »
# (Tosfot Yom Tov) : une pelle à cendres, pas l'instrument à dix trous d'Arakhin 11a, qui se
# serait brisé — le Raavad, rapporté par le Rashash, les identifie. La pelle est « כמין כסוי
# הקדרה של מתכת דק ולו בית יד » (Rashi sur Shemot 27:3). Diamètre, manche, bronze : CHOIX.
MAGREFA_X, MAGREFA_Y, MAGREFA_R = -60.5, 13.5, 0.75
revolution("Magrefa", MAGREFA_X, MAGREFA_Y, Z_AZ,
           [(MAGREFA_R, 0), (MAGREFA_R, 0.03), (0.55, 0.09), (0.2, 0.12), (0, 0.12)],
           "30_Mizbeach", MAT_BRONZE())
cyl_between("Magrefa_manche", (MAGREFA_X + MAGREFA_R - 0.1, MAGREFA_Y, Z_AZ + 0.05),
            (MAGREFA_X + MAGREFA_R + 1.5, MAGREFA_Y, Z_AZ + 0.05), 0.05, "30_Mizbeach", MAT_BRONZE(), verts=8)

# --- Les cuivres de Shlomo (Melakhim I 7:23-39 ; Divrei HaYamim II 4:2-6), à côté du
#     Kiyor de la Mishna — comme Menachot 98b range les dix menorot de Shlomo autour de
#     celle de Moshé. Ils sont du Premier Temple : Middot ne les connaît pas (CHOIX).
# La Mer : dix amot de bord à bord, cinq de haut, trente de tour, « כְּמַעֲשֵׂה שְׂפַת כּוֹס
# פֶּרַח שׁוֹשָׁן », deux rangs de coloquintes sous la lèvre, douze bœufs, trois vers chaque
# vent, « וְכָל אֲחֹרֵיהֶם בָּיְתָה ». « מִכֶּתֶף הַבַּיִת הַיְמָנִית קֵדְמָה מִמּוּל נֶגֶב » (7:39) :
# au sud-est du bâtiment, entre les marches de l'Oulam et la rampe.
# Les bœufs, taureaux d'un mètre trente au garrot (CHOIX), croupes à YAM_CROUPE du centre
# et côte à côte à YAM_ECART : les rangs de deux vents voisins ne se touchent pas au coin.
# La cuve pose sur leurs reins, là où son fond remonte à la hauteur du dos.
YAM_X, YAM_Y, YAM_Z = -63, -40, Z_AZ + 2.15
YAM_CROUPE, YAM_ECART = 2.3, 1.5
YAM = [(0.6, 0.0), (3.6, 0.5), (4.5, 1.6), (4.75, 3.2), (4.7, 3.9), (5.0, 4.6), (5.2, 5.0),
       (4.95, 5.0), (4.6, 4.4), (4.45, 3.0), (3.6, 1.0), (0.0, 0.6)]
revolution("Yam", YAM_X, YAM_Y, YAM_Z, YAM, "30_Mizbeach", MAT_BRONZE(), verts=48)
cyl("Yam_eau", YAM_X, YAM_Y, YAM_Z + 4.2, YAM_Z + 4.27, 4.5, "30_Mizbeach", MAT_EAU(), verts=48)
for rang, z in enumerate((3.55, 3.85)):
    for k in range(75):
        a = 2 * math.pi * (k + 0.5 * rang) / 75
        sphere(f"Yam_peka_{rang}{k:02d}", YAM_X + 4.8 * math.cos(a), YAM_Y + 4.8 * math.sin(a), YAM_Z + z, 0.14,
               "30_Mizbeach", MAT_BRONZE(), segs=6)


SHOR_BLEND = MODELE / "shor.blend"


def shor():
    """Le bœuf de la Mer, lu dans `shor.blend`.

    C'est `beit_hamikdash_shor.py` qui le modèle, en champ de distance polygonisé. Le
    maillage est en mètres, dans le repère du bœuf : origine au sol sous la pointe des
    fesses, +x vers le mufle.
    """
    with bpy.data.libraries.load(str(SHOR_BLEND)) as (_, charge):
        charge.meshes = ["Shor"]
    return charge.meshes[0]


def yam_bakar(col, mat):
    """Les douze bœufs, trois par vent, croupes vers le centre, tête vers le dehors."""
    modele = shor()
    for nom, (dx, dy) in (("E", (1, 0)), ("N", (0, 1)), ("O", (-1, 0)), ("S", (0, -1))):
        for k, t in enumerate((-YAM_ECART, 0.0, YAM_ECART)):
            me = modele.copy()
            me.materials.clear()
            me.materials.append(mat)
            o = _objet(f"Yam_shor_{nom}{k}", me, col)
            o["sans_biseau"] = True
            _poser([o], YAM_X + dx * YAM_CROUPE - dy * t, YAM_Y + dy * YAM_CROUPE + dx * t, Z_AZ,
                   math.atan2(dy, dx))
    bpy.data.meshes.remove(modele)


yam_bakar("30_Mizbeach", MAT_BRONZE())

# Les dix mekhonot (Melakhim I 7:27-39) : socles de bronze de 4 × 4 × 3 sur quatre roues
# d'une ama et demie, panneaux à lions, bœufs et keruvim (ici : leurs cadres seulement),
# et une cuve de quatre amot sur chacun. « חָמֵשׁ עַל כֶּתֶף הַבַּיִת מִיָּמִין וְחָמֵשׁ עַל כֶּתֶף
# הַבַּיִת מִשְּׂמֹאלוֹ » : sur l'épaule du bâtiment, à côté du corps, sur le sol de l'Azara —
# l'אֹטֶם de 6 amot ne déborde pas le corps (Middot 4:7).
MEKHONA = [(1.4, 0.0), (1.9, 0.25), (2.0, 0.9), (1.85, 1.35), (1.7, 1.35), (1.75, 0.9), (1.55, 0.35), (0.0, 0.2)]
for cote, y in (("S", -42.5), ("N", 42.5)):
    for k, x in enumerate((-105, -120, -135, -150, -165)):
        nom = f"Mekhona_{cote}{k}"
        box(f"{nom}_corps", x - 2, x + 2, y - 2, y + 2, Z_AZ + 0.9, Z_AZ + 3.6, "30_Mizbeach", MAT_BRONZE())
        for face, (xa, xb, ya, yb) in (("E", (x + 2, x + 2.12, y - 1.8, y + 1.8)), ("O", (x - 2.12, x - 2, y - 1.8, y + 1.8)),
                                        ("N", (x - 1.8, x + 1.8, y + 2, y + 2.12)), ("S", (x - 1.8, x + 1.8, y - 2.12, y - 2))):
            box(f"{nom}_cadre_{face}_bas", xa, xb, ya, yb, Z_AZ + 1.2, Z_AZ + 1.4, "30_Mizbeach", MAT_BRONZE())
            box(f"{nom}_cadre_{face}_haut", xa, xb, ya, yb, Z_AZ + 3.1, Z_AZ + 3.3, "30_Mizbeach", MAT_BRONZE())
        for j, (rx, ry) in enumerate(((-1.3, -2.2), (1.3, -2.2), (-1.3, 2.2), (1.3, 2.2))):
            tore(f"{nom}_roue_{j}", x + rx, y + ry, Z_AZ + 0.75, 0.62, 0.13, "30_Mizbeach", MAT_BRONZE(), rotation=(math.pi / 2, 0, 0))
        cyl(f"{nom}_col", x, y, Z_AZ + 3.6, Z_AZ + 4.1, 1.2, "30_Mizbeach", MAT_BRONZE(), verts=24)
        revolution(f"{nom}_kiyor", x, y, Z_AZ + 4.1, MEKHONA, "30_Mizbeach", MAT_BRONZE(), verts=32)
        cyl(f"{nom}_eau", x, y, Z_AZ + 5.25, Z_AZ + 5.3, 1.7, "30_Mizbeach", MAT_EAU(), verts=32)
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
    table_de_service(f"Table_marbre_{i}", (x - 0.5, x + 0.5, 42, 44), Z_AZ, 1.5, "30_Mizbeach", MAT_MARBRE())
# Les tabaot : « פְּתוּחוֹת צַד אֶחָד וְהוֹפְכָהּ לְמַעְלָה… וְחוֹזֵר וְהוֹפֵךְ פִּתְחָה לְמַטָּה לְתוֹךְ הָרִצְפָּה » (Bartenura,
# Soucca 5:8), « רְחָבוֹת מִלְּמַטָּן וְצָרוֹת מִלְּמַעְלָן » (Yerushalmi Ma'asser Sheni 5:5). Cotes, fer, gond à l'ouest : CHOIX.
TABAOT_Y = [MY1 + 8 + 4 * k for k in range(6)]     # six sedarim de quatre, le premier à 8 amot de l'autel (Middot 5:2)
TABAOT_X = [MX0 + 4 + 8 * k for k in range(4)]
TABAAT_BILGA = 14                                   # Bilga, 15e mishmar (Divrei HaYamim I 24:14) ; l'ordre des anneaux : CHOIX
PIED_TABAAT, COL_TABAAT, HAUT_TABAAT = 0.55, 0.35, 0.8
FER_TABAAT, COTES_TABAAT = 0.06, 12


def profil_de_tabaat():
    """La fibre de l'arc dans son plan (u est-ouest, z), d'un pied à l'autre, pieds pris sous le dallage."""
    arc = [(math.cos(t) * (COL_TABAAT + (PIED_TABAAT - COL_TABAAT) * (1 - math.sin(t))), HAUT_TABAAT * math.sin(t))
           for t in (math.pi * k / 16 for k in range(17))]
    return [(PIED_TABAAT, -0.1)] + arc + [(-PIED_TABAAT, -0.1)]


def arc_de_tabaat(nom, x, y):
    """L'arc de fer dressé dans le plan est-ouest, que le cou de la bête traverse du nord au sud."""
    profil, sommets = profil_de_tabaat(), []
    for k, (u, z) in enumerate(profil):
        (u0, z0), (u1, z1) = profil[max(k - 1, 0)], profil[min(k + 1, len(profil) - 1)]
        longueur = math.hypot(u1 - u0, z1 - z0)
        nu, nz = -(z1 - z0) / longueur, (u1 - u0) / longueur
        for a in (2 * math.pi * c / COTES_TABAAT for c in range(COTES_TABAAT)):
            r_n, r_y = FER_TABAAT * math.cos(a), FER_TABAAT * math.sin(a)
            sommets.append((x + u + r_n * nu, y + r_y, Z_AZ + z + r_n * nz))
    n = COTES_TABAAT
    faces = [[k * n + c, (k + 1) * n + c, (k + 1) * n + (c + 1) % n, k * n + (c + 1) % n]
             for k in range(len(profil) - 1) for c in range(n)]
    o = mesh_from_pydata(nom, sommets, faces, "30_Mizbeach", MAT_FER())
    o.data.shade_smooth()
    return o


for rang, y in enumerate(TABAOT_Y):
    for place, x in enumerate(TABAOT_X):
        nom, gond = f"Anneau_{rang}{place}", x - PIED_TABAAT
        pieces = [arc_de_tabaat(nom, x, y),
                  box(f"{nom}_platine", gond - 0.15, gond + 0.15, y - 0.15, y + 0.15, Z_AZ, Z_AZ + 0.03, "30_Mizbeach", MAT_FER()),
                  cyl_between(f"{nom}_gond", (gond, y - 0.14, Z_AZ + 0.09), (gond, y + 0.14, Z_AZ + 0.09), 0.08,
                              "30_Mizbeach", MAT_FER(), verts=12),
                  tore(f"{nom}_gaine", x + PIED_TABAAT, y, Z_AZ + 0.01, 0.1, 0.025, "30_Mizbeach", MAT_FER())]
        if rang * len(TABAOT_X) + place == TABAAT_BILGA:
            pieces.append(box(f"{nom}_Bilga_scelle", gond - 0.17, gond + 0.17, y - 0.17, y + 0.17, Z_AZ, Z_AZ + 0.2,
                              "30_Mizbeach", MAT_FER()))
        for piece in pieces:
            piece["sans_biseau"] = True
