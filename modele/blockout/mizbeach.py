import bmesh
import bpy
import math
from mathutils import Vector, noise

from .primitives import tissage
from .primitives.parametres import MODELE, TEFAH, Z_AZ, Z_MAARAKHA, Z_SOVEV, Z_YESSOD, m
from .primitives.matieres import (MAT_ARGENT, MAT_BOIS_CHARBON, MAT_BOIS_MAARAKHA, MAT_BOIS_ROUSSI,
                                  MAT_BRONZE, MAT_CEDRE, MAT_CENDRE, MAT_CHAUX, MAT_CHAUX_FEU, MAT_EAU,
                                  MAT_FER, MAT_MARBRE, MAT_SEL, MAT_SIKRA, braise, nuee)
from .primitives.volumes import (_objet, _poser, alea, box, braises, crochet, cyl, cyl_between, lampe, link_to,
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
# Trois ma'arakhot chaque jour et quatre à Kippour, l'avis de R. Yossi (Yoma 4:6 ; Rambam
# Temidin ouMousafin 2:4-5) : la grande à l'est, celle de la ketoret à l'angle sud-ouest
# (Tamid 2:4-5), celle du kiyoum haesh, et à Kippour celle des braises de la ketoret du
# Kodesh HaKodashim (Bartenura ad loc.). R. Meir en ajoute une pour les membres de la
# veille, que R. Yossi brûle au bord de la grande.
MAARAKHOT = (("gedola", -36, -28, -13, -5), ("ketoret", -48, -45, -19, -16),
             ("kiyum", -48, -45, -4, -1), ("kippour", -42, -39, -19, -16))
# « וְרֶוַח הָיָה בֵין הַגִּזְרִין, שֶׁהָיוּ מַצִּיתִין אֶת הָאֲלִיתָא מִשָּׁם » (Tamid 2:4 ; Rambam
# Temidin ouMousafin 2:7) : les bûches ne sont PAS jointives. C'est ce vide-là qui fait
# lire un bûcher — deux lits jointifs sous une dalle donnaient une palette sous un
# matelas, ce que la visite montrait de près.
R_GZIR, REWACH, PAS_LIT, LITS = 0.19, 0.16, 0.34, 4
# Du bois fendu à la longueur d'un bras, pas des troncs : longueur d'une bûche et jour entre deux bouts, CHOIX.
LONG_GZIR, JOUR_GZIR = 2.6, 0.25
# La section d'une bûche, en angle d'écorce : un rondin, une moitié, un quartier.
FENTES_GZIR = (2 * math.pi, math.pi, 0.55 * math.pi)
COTES_GZIR, TRANCHES_GZIR = 9, 3

def _section_de_gzir(cle, rayon):
    """Le contour d'une bûche fendue, écorce en arc et bois à plat, et le rang du premier sommet de bois."""
    arc = FENTES_GZIR[int(alea(cle, 6) * len(FENTES_GZIR))]
    rond = arc == 2 * math.pi
    pas = COTES_GZIR if rond else COTES_GZIR - 1
    ecorce = [(rayon * (0.86 + 0.28 * alea(cle, 10 + k)) * math.cos(arc * k / pas),
               rayon * (0.86 + 0.28 * alea(cle, 10 + k)) * math.sin(arc * k / pas)) for k in range(COTES_GZIR)]
    if rond or arc == math.pi:
        return ecorce, len(ecorce)
    return ecorce + [(0.0, 0.0)], len(ecorce) - 1

def gzir(cle, p0, p1, rayon, col, mat):
    """Une bûche fendue entre deux points : sa section tourne sur elle-même et se déporte d'une tranche à l'autre."""
    contour, bois = _section_de_gzir(cle, rayon)
    n = len(contour)
    tour = 2 * math.pi * alea(cle, 7)
    verts = []
    for t in range(TRANCHES_GZIR + 1):
        angle = tour + 0.25 * (alea(cle, 20 + t) - 0.5)
        ecart = [0.25 * rayon * (alea(cle, 30 + 2 * t + k) - 0.5) for k in (0, 1)]
        taille = 0.9 + 0.2 * alea(cle, 40 + t)
        z = t / TRANCHES_GZIR
        verts += [(taille * (u * math.cos(angle) - v * math.sin(angle)) + ecart[0],
                   taille * (u * math.sin(angle) + v * math.cos(angle)) + ecart[1], z) for u, v in contour]
    flancs = [[t * n + k, t * n + (k + 1) % n, (t + 1) * n + (k + 1) % n, (t + 1) * n + k]
              for t in range(TRANCHES_GZIR) for k in range(n)]
    bouts = [list(range(n))[::-1], [TRANCHES_GZIR * n + k for k in range(n)]]
    a, b = Vector(p0), Vector(p1)
    repere = (b - a).to_track_quat('Z', 'Y').to_matrix()
    longueur = (b - a).length
    o = mesh_from_pydata(cle, [tuple(a + repere @ Vector((x, y, z * longueur))) for x, y, z in verts], flancs + bouts, col, mat)
    # Lisse sur l'écorce, à plat sur le bois fendu et sur les bouts sciés.
    for k, face in enumerate(o.data.polygons):
        face.use_smooth = k < len(flancs) and k % n < bois - 1
    o["sans_biseau"] = True
    return o

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

for nm, xa, xb, ya, yb in MAARAKHOT:
    maarakha(nm, xa, xb, ya, yb)
# Le feu lui-même. La ma'arakha était une boîte noire sans source : la colonne de fumée
# montait d'un autel éteint, et la rampe du plan 7b n'avait que la lumière du ciel — la
# raison pour laquelle elle ne se détachait ni de l'autel ni du dallage.
_, GX0, GX1, GY0, GY1 = MAARAKHOT[0]
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
table_de_service("Kevesh_shulchan_shaish", (KX0 - 8.5, KX0 - 7.5, MY0 - 20, MY0 - 18), Z_AZ, 1.5, "30_Mizbeach", MAT_MARBRE())
table_de_service("Kevesh_shulchan_kessef", (KX0 - 8.5, KX0 - 7.5, MY0 - 15, MY0 - 13), Z_AZ, 1.5, "30_Mizbeach", MAT_ARGENT())
# « הָפַךְ פָּנָיו לַצָּפוֹן, הָלַךְ לְמִזְרָחוֹ שֶׁל כֶּבֶשׁ כְּעֶשֶׂר אַמּוֹת. צָבַר אֶת הַגֶּחָלִים עַל גַּבֵּי הָרִצְפָה רָחוֹק
# מִן הַכֶּבֶשׁ שְׁלשָׁה טְפָחִים » (Tamid 1:4) : trois tefa'him, une demi-ama. Taille du tas : CHOIX.
tas("Kevesh_makom_deshen", (KX1 + 1.5, KY0 + 10), Z_AZ, 0.5, 1.0, MAT_CENDRE())
# « וְתַפּוּחַ הָיָה בְאֶמְצַע הַמִּזְבֵּחַ » (Tamid 2:2), que touchent les bouts intérieurs des
# gzirin de la grande ma'arakha (Tamid 2:4 ; Rambam Temidin ouMousafin 2:7). Taille : CHOIX.
tas("Maarakha_tapuach", (xc, (MY0 + MY1) / 2), Z_MAARAKHA, 1.5, 2.0, MAT_CENDRE())
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
# le perfectionnement de Ben Katin (Yoma 3:10 ; fiche §7). Deux cylindres empilés se
# lisaient en tambour : profil tourné, panse, lèvre, et l'eau dans la vasque.
KIYOR_X, KIYOR_Y = -59, -14
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
for r in range(4):
    for c in range(6):
        x = MX1 - 4 - c * 4.8
        y = 18 + r * 6
        tore(f"Anneau_{r}{c}", x, y, Z_AZ + 0.1, 0.5, 0.08, "30_Mizbeach", MAT_BRONZE())
