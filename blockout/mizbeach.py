import bpy
import math
from mathutils import Vector, noise

from .primitives import tissage
from .primitives.parametres import RACINE, Z_AZ, m
from .primitives.matieres import (MAT_ARGENT, MAT_BOIS_CHARBON, MAT_BOIS_MAARAKHA, MAT_BOIS_ROUSSI,
                                  MAT_BRONZE, MAT_CEDRE, MAT_CENDRE, MAT_CHAUX, MAT_CHAUX_FEU, MAT_EAU,
                                  MAT_FER, MAT_MARBRE, MAT_SEL, MAT_SIKRA, braise, nuee)
from .primitives.volumes import (_objet, _poser, alea, box, cone, crochet, cyl, cyl_between, lampe, link_to,
                                 massif_en_pente, mesh_from_pydata, revolution, sphere, tore, wedge_ramp,
                                 wedge_ramp_oblique)


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
# « אֲבָנִים שְׁלֵמוֹת, שֶׁלֹּא הוּנַף עֲלֵיהֶן בַּרְזֶל… לֹא הָיוּ סָדִין אוֹתָן בְּכָפִיס שֶׁל בַּרְזֶל » (Middot 3:4) :
# des pierres brutes sous une chaux posée sans truelle — ni face dressée, ni arête vive.
BOSSE_CHAUX, ONDE_CHAUX, PAS_CHAUX = 0.06, 1.3, 0.5
# Ce qu'un bloc s'enfonce dans ce qui le porte, et ce qu'un voisin mord dans sa face : la bosse n'ouvre jamais de jour.
REPRISE_CHAUX = 0.3
# Un sommet de l'arrondi tous les 15° : la tangente de 45° à 90°, portée sur le rayon.
ARRONDI_CHAUX = (0.0, 0.42, 0.73, 1.0)
DECALAGE_CHAUX = Vector((5.2, 1.3, 7.7))

def _cotes_chaux(a, b, r_bas, r_haut):
    n = max(1, round((b - a - r_bas - r_haut) / PAS_CHAUX))
    pas = [a + r_bas + (b - a - r_bas - r_haut) * k / n for k in range(n + 1)]
    bouts = [a + r_bas * f for f in ARRONDI_CHAUX] + [b - r_haut * f for f in ARRONDI_CHAUX]
    return sorted({round(c, 6) for c in pas + bouts})

def _sur_la_chaux(p, dedans, r, ecart=0.0):
    """Le point p de la face dressée, porté sur l'arrondi de rayon r autour de `dedans` puis bossué.

    La bosse se lit en coordonnées de monde : deux blocs qui se continuent ondulent ensemble.
    Le dessus reste presque plan — on y pose les gzirin, et les pieds l'ont foulé.
    """
    c = Vector([min(max(p[k], dedans[0][k]), dedans[1][k]) for k in range(3)])
    n = (Vector(p) - c).normalized()
    q = Vector(p) / ONDE_CHAUX
    bosse = noise.noise(q) + 0.4 * noise.noise(q * 2.7 + DECALAGE_CHAUX)
    return c + n * (r + ecart + BOSSE_CHAUX * bosse * (1.0 - 0.7 * n.z * n.z))

def _dedans_chaux(x0, x1, y0, y1, z0, z1, r, ouvert=()):
    """La boîte que l'arrondi entoure. Un côté `ouvert` est enfoui dans un voisin : il ne s'arrondit pas."""
    rayon = {cote: 0.0 if cote in ouvert else r for cote in ("x0", "x1", "y0", "y1")}
    return ((x0 + rayon["x0"], y0 + rayon["y0"], z0 - REPRISE_CHAUX),
            (x1 - rayon["x1"], y1 - rayon["y1"], z1 - r)), rayon

def bloc_de_chaux(name, x0, x1, y0, y1, z0, z1, col, mat, r=0.12, ouvert=(), creux=0.0):
    """Boîte de chaux ouverte en dessous et enfoncée de REPRISE_CHAUX dans ce qui la porte.

    `ouvert` : les côtés ("x0", "x1", "y0", "y1") qui continuent dans un bloc voisin, sans face ni arrondi —
    deux faces jointives bossuées en sens contraires ouvriraient un jour entre elles.
    `creux` : l'épaisseur de paroi d'un bloc percé de haut en bas, comme une keren.
    """
    (dedans, rayon) = _dedans_chaux(x0, x1, y0, y1, z0, z1, r, ouvert)
    trou = (x0 + creux, x1 - creux, y0 + creux, y1 - creux)
    xs = sorted(set(_cotes_chaux(x0, x1, rayon["x0"], rayon["x1"]) + ([trou[0], trou[1]] if creux else [])))
    ys = sorted(set(_cotes_chaux(y0, y1, rayon["y0"], rayon["y1"]) + ([trou[2], trou[3]] if creux else [])))
    zs = _cotes_chaux(z0 - REPRISE_CHAUX, z1, 0.0, r)
    index, verts, faces = {}, [], []

    def sommet(p):
        if p not in index:
            index[p] = len(verts)
            verts.append(tuple(_sur_la_chaux(p, dedans, r)))
        return index[p]

    def grille(us, vs, point):
        for i in range(len(us) - 1):
            for j in range(len(vs) - 1):
                faces.append([sommet(point(us[i], vs[j])), sommet(point(us[i + 1], vs[j])),
                              sommet(point(us[i + 1], vs[j + 1])), sommet(point(us[i], vs[j + 1]))])

    def perce(u, v):
        return creux and trou[0] < u < trou[1] and trou[2] < v < trou[3]

    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if not perce((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2):
                faces.append([sommet((xs[i], ys[j], z1)), sommet((xs[i + 1], ys[j], z1)),
                              sommet((xs[i + 1], ys[j + 1], z1)), sommet((xs[i], ys[j + 1], z1))])
    if "x1" not in ouvert:
        grille(ys, zs, lambda u, v: (x1, u, v))
    if "x0" not in ouvert:
        grille(zs, ys, lambda u, v: (x0, v, u))
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
    o.data.shade_smooth()
    o["sans_biseau"] = True
    return o

def ceinture_de_chaux(name, bloc, z0, z1, col, mat, r=0.12):
    """Bande peinte entre z0 et z1 sur les flancs du bloc de bornes `bloc` : sans épaisseur, elle en suit chaque bosse."""
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

# Le yessod est une seule bande de chaux : ses tronçons se continuent par leurs côtés ouverts, et mordent dans le corps.
bloc_de_chaux("Mizbeach_yessod_N", MX0 + 1 + REPRISE_CHAUX, MX1, MY1 - 1 - REPRISE_CHAUX, MY1, Z_AZ, Z_AZ + 1, "30_Mizbeach", MAT_CHAUX(),
              ouvert=("x0", "y0"))
bloc_de_chaux("Mizbeach_yessod_O", MX0, MX0 + 1 + REPRISE_CHAUX, MY0, MY1, Z_AZ, Z_AZ + 1, "30_Mizbeach", MAT_CHAUX(),
              ouvert=("x1",))
bloc_de_chaux("Mizbeach_yessod_S", MX0 + 1 + REPRISE_CHAUX, MX0 + 2, MY0, MY0 + 1 + REPRISE_CHAUX, Z_AZ, Z_AZ + 1, "30_Mizbeach", MAT_CHAUX(),
              ouvert=("x0", "y1"))
bloc_de_chaux("Mizbeach_yessod_E", MX1 - 1 - REPRISE_CHAUX, MX1, MY1 - 2, MY1 - 1 - REPRISE_CHAUX, Z_AZ, Z_AZ + 1, "30_Mizbeach", MAT_CHAUX(),
              ouvert=("x0", "y1"))
CORPS = (MX0 + 1, MX1 - 1, MY0 + 1, MY1 - 1, Z_AZ, Z_AZ + 6)
bloc_de_chaux("Mizbeach_corps", *CORPS, "30_Mizbeach", MAT_CHAUX())
bloc_de_chaux("Mizbeach_haut", MX0 + 2, MX1 - 2, MY0 + 2, MY1 - 2, Z_AZ + 6, Z_AZ + 9, "30_Mizbeach", MAT_CHAUX_FEU())
# « וְאַרְבַּע הַקְּרָנוֹת חֲלוּלוֹת הָיוּ מִתּוֹכָן » (Rambam Beit HaBe'hira 2:8, 2:16) : quatre murets
# d'une ama cube autour d'un vide. Épaisseur des murets : CHOIX.
PAROI_KEREN = 0.25
for (nm, x, y) in [("SE", MX1 - 3, MY0 + 2), ("NE", MX1 - 3, MY1 - 3), ("NO", MX0 + 2, MY1 - 3), ("SO", MX0 + 2, MY0 + 2)]:
    bloc_de_chaux(f"Keren_{nm}", x, x + 1, y, y + 1, Z_AZ + 9, Z_AZ + 10, "30_Mizbeach", MAT_CHAUX_FEU(),
                  r=0.06, creux=PAROI_KEREN)
# « וְחוּט שֶׁל סִקְרָא חוֹגְרוֹ בָאֶמְצַע » (Middot 3:1) : la ligne rouge à mi-hauteur, qui sépare
# les sangs d'en haut des sangs d'en bas — le seul trait de couleur sur la chaux.
ceinture_de_chaux("Mizbeach_sikra", CORPS, Z_AZ + 4.95, Z_AZ + 5.05, "30_Mizbeach", MAT_SIKRA())
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
R_GZIR, REWACH, PAS_LIT, LITS = 0.18, 0.15, 0.30, 3

def braises(nom, x0, x1, y0, y1, z, col, mat, maille=0.42, relief=0.22, profondeur=0.35):
    """Bassin de gehalim : une nappe de charbons empilés, en un seul maillage.

    Une boîte n'a pas de silhouette de braise, et aucune matière ne la lui rend : la
    hauteur est donc dans la géométrie, tirée du nom pour que le tas soit le même à
    chaque construction. Le bord garde la maille exacte — lui aussi déformé, le bassin
    débordait sur les gzirin. `profondeur` : ce que le tas descend sous `z`.
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
            bas.append((x, y, z - profondeur))
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

# Kevesh : 32 × 16 au sud (Middot 3:3), « אוֹכֵל בָּאָרֶץ שְׁלֹשִׁים אַמָּה… וּפוֹרֵחַ מִמֶּנָּה אַמָּה עַל הַיְסוֹד
# וְאַמָּה עַל הַסּוֹבֵב. וַאֲוִיר מְעַט הָיָה מַפְסִיק בֵּין הַכֶּבֶשׁ לַמִּזְבֵּחַ » (Rambam Beit HaBe'hira 2:13 ;
# Zeva'him 62b). Les deux dernières amot sont une tête en porte-à-faux, qui s'arrête avant
# la face de l'autel. Épaisseur de la tête et largeur de l'air : CHOIX.
xc = (MX0 + MX1) / 2
KX0, KX1, KY0 = xc - 8, xc + 8, MY0 - 30
AVIR_KEVESH, NIMA = 0.25, 0.02
# Piège : ce NIMA écrase celui de la parokhet tissée, qui est câblée plus tard (Bayit).
tissage.NIMA = NIMA
z_kevesh = lambda y: Z_AZ + 9 * (y - KY0) / 30
# « וְחַלּוֹן הָיְתָה בְּמַעֲרָבוֹ שֶׁל כֶּבֶשׁ אַמָּה עַל אַמָּה, וּרְבוּבָה הָיְתָה נִקְרֵאת » (Rambam 2:14 ; Middot 3:3) :
# la niche où l'on posait les pesoulei 'hatat haof. Place, hauteur et profondeur : CHOIX.
REVOUVA_Y, REVOUVA_Z = MY0 - 12, Z_AZ + 2
wedge_ramp("Kevesh", KX0 + 1, KX1, KY0, MY0, Z_AZ, Z_AZ + 9, "30_Mizbeach", MAT_CHAUX())
wedge_ramp("Kevesh_ouest_bas", KX0, KX0 + 1, KY0, REVOUVA_Y, Z_AZ, z_kevesh(REVOUVA_Y), "30_Mizbeach", MAT_CHAUX())
box("Kevesh_revouva_seuil", KX0, KX0 + 1, REVOUVA_Y, REVOUVA_Y + 1, Z_AZ, REVOUVA_Z, "30_Mizbeach", MAT_CHAUX())
massif_en_pente("Kevesh_revouva_linteau", KX0, KX0 + 1, REVOUVA_Y, REVOUVA_Y + 1, REVOUVA_Z + 1,
                z_kevesh(REVOUVA_Y), z_kevesh(REVOUVA_Y + 1), "30_Mizbeach", MAT_CHAUX())
massif_en_pente("Kevesh_ouest_haut", KX0, KX0 + 1, REVOUVA_Y + 1, MY0, Z_AZ,
                z_kevesh(REVOUVA_Y + 1), Z_AZ + 9, "30_Mizbeach", MAT_CHAUX())
box("Kevesh_rosh", KX0, KX1, MY0, MY0 + 2 - AVIR_KEVESH, Z_AZ + 8, Z_AZ + 9, "30_Mizbeach", MAT_CHAUX())
# « שְׁנֵי כְּבָשִׁים קְטַנִּים יוֹצְאִין מִן הַכֶּבֶשׁ, שֶׁבָּהֶן פּוֹנִים לַיְסוֹד וְלַסּוֹבֵב; וּמוּבְדָּלִין מִן הַמִּזְבֵּחַ
# מְלֹא נִימָא » (Zeva'him 62b ; Rambam 2:14). Les côtés sont ceux de Rashi ad loc. : celui du sovev
# « יצא במזרחו של כבש… ועולה באלכסון עד שמגיע לסובב », celui du yessod « יוצא למערבו…
# פונה לשמאלו ליסוד דרומי ומתחיל לצאת בשיפולו של כבש », et le yessod du sud n'est qu'à l'angle
# sud-ouest (Rambam 2:10) : la rampe du yessod part du pied du kevesh contre son flanc et
# descend en biais jusqu'à l'angle, sur le yessod de l'ouest et celui du sud. Le sovev part à 18 amot
# de l'autel et non du pied, pour laisser au sol la place du deshen à dix amot du pied
# (Tamid 1:4). Largeurs et départ : CHOIX.
# La nima se compte depuis la bosse de la chaux, pas depuis la face dressée.
wedge_ramp("Kevesh_katan_sovev", KX1, KX1 + 2.5, MY0 - 18, MY0 + 1 - NIMA - BOSSE_CHAUX, Z_AZ, Z_AZ + 6, "30_Mizbeach", MAT_CHAUX())
wedge_ramp_oblique("Kevesh_katan_yessod", KX0 - 2, MX0, 2, KY0, MY0 - NIMA - BOSSE_CHAUX, Z_AZ, Z_AZ + 1, "30_Mizbeach", MAT_CHAUX())
# « וּשְׁנַיִם בְּמַעֲרַב הַכֶּבֶשׁ, אֶחָד שֶׁל שַׁיִשׁ וְאֶחָד שֶׁל כֶּסֶף; עַל שֶׁל שַׁיִשׁ הָיוּ נוֹתְנִים אֶת הָאֵבָרִים, עַל
# שֶׁל כֶּסֶף כְּלֵי שָׁרֵת » (Shekalim 6:4 ; Rambam 2:15). Cotes, celles des tables du Beit
# HaMitba'haïm ; place, à l'ouest de la rampe du yessod : CHOIX.
box("Kevesh_shulchan_shaish", KX0 - 8.5, KX0 - 7.5, MY0 - 20, MY0 - 18, Z_AZ, Z_AZ + 1.5, "30_Mizbeach", MAT_MARBRE())
box("Kevesh_shulchan_kessef", KX0 - 8.5, KX0 - 7.5, MY0 - 15, MY0 - 13, Z_AZ, Z_AZ + 1.5, "30_Mizbeach", MAT_ARGENT())
# « הָפַךְ פָּנָיו לַצָּפוֹן, הָלַךְ לְמִזְרָחוֹ שֶׁל כֶּבֶשׁ כְּעֶשֶׂר אַמּוֹת. צָבַר אֶת הַגֶּחָלִים עַל גַּבֵּי הָרִצְפָה רָחוֹק
# מִן הַכֶּבֶשׁ שְׁלשָׁה טְפָחִים » (Tamid 1:4) : trois tefa'him, une demi-ama. Taille du tas : CHOIX.
cone("Kevesh_makom_deshen", KX1 + 1.5, KY0 + 10, Z_AZ, Z_AZ + 0.5, 1.0, 0.2, "30_Mizbeach", MAT_CENDRE(), verts=16)
# « וְתַפּוּחַ הָיָה בְאֶמְצַע הַמִּזְבֵּחַ » (Tamid 2:2), que touchent les bouts intérieurs des
# gzirin de la grande ma'arakha (Tamid 2:4 ; Rambam Temidin ouMousafin 2:7). Taille : CHOIX.
cone("Maarakha_tapuach", xc, (MY0 + MY1) / 2, Z_AZ + 9, Z_AZ + 10.5, 2.0, 0.3, "30_Mizbeach", MAT_CENDRE(), verts=24)
# « בִּשְׁלֹשָׁה מְקוֹמוֹת הַמֶּלַח נְתוּנָה… וְעַל גַּבֵּי הַכֶּבֶשׁ » (Mena'hot 21b), là où l'on sale les membres,
# posés « מֵחֲצִי הַכֶּבֶשׁ וּלְמַטָּה בְּמַעֲרָבוֹ, וּמְלָחוּם » (Tamid 4:3). Un tas, sa taille et sa place dans
# cette moitié : CHOIX. Son fond plat s'enfonce dans la pente côté haut.
MELACH_X, MELACH_Y, MELACH_R = KX0 + 2.5, KY0 + 9, 0.8
cone("Kevesh_melach", MELACH_X, MELACH_Y, z_kevesh(MELACH_Y - MELACH_R) - 0.05,
     z_kevesh(MELACH_Y + MELACH_R) + 0.35, MELACH_R, 0.15, "30_Mizbeach", MAT_SEL(), verts=16)
# « בְּרֹאשׁוֹ שֶׁל מִזְבֵּחַ – שֶׁשָּׁם מוֹלְחִין הַקּוֹמֶץ וְהַלְּבוֹנָה וְהַקְּטוֹרֶת » (Mena'hot 21b). Sa place sur le sommet : CHOIX,
# dans l'ama de passage du sud, à l'est de l'arrivée du kevesh, hors du feu.
cone("Mizbeach_melach", xc + 4, MY0 + 3.5, Z_AZ + 9, Z_AZ + 9.4, 0.4, 0.08, "30_Mizbeach", MAT_SEL(), verts=16)
# « עָלָה בַכֶּבֶשׁ וּפָנָה לִשְׂמֹאלוֹ, שְׁנֵי סְפָלִים שֶׁל כֶּסֶף הָיוּ שָׁם… מַעֲרָבִי שֶׁל מַיִם, מִזְרָחִי שֶׁל יָיִן »
# (Soucca 4:9 ; Rambam Temidin ouMousafin 10:7), « נתונים אצל הקרן… סמוכין זה לזה » (Rashi Soucca 48b),
# la corne sud-ouest. Le bec de l'eau plus fin que celui du vin, « כְּדֵי שֶׁיִּכְלֶה הַמַּיִם עִם הַיַּיִן
# כְּאֶחָד » (Rambam ibid.). Taille, profil et sens des becs : CHOIX. Avis écarté : de chaux noircie
# par le vin, selon R. Yehouda (même michna).
SEFEL = [(0.14, 0.0), (0.18, 0.03), (0.30, 0.22), (0.32, 0.32), (0.29, 0.32), (0.27, 0.24), (0.0, 0.07)]
for nm, x, r_bec in (("mayim", MX0 + 3.5, 0.03), ("yayin", MX0 + 4.3, 0.05)):
    y = MY0 + 2.5
    revolution(f"Sefel_{nm}", x, y, Z_AZ + 9, SEFEL, "30_Mizbeach", MAT_ARGENT(), verts=24)
    cyl_between(f"Sefel_{nm}_hotem", (x, y + 0.2, Z_AZ + 9.08), (x, y + 0.42, Z_AZ + 9.02), r_bec,
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


SHOR_BLEND = RACINE / "shor.blend"


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
    box(f"Table_marbre_{i}", x - 0.5, x + 0.5, 42, 44, Z_AZ, Z_AZ + 1.5, "30_Mizbeach", MAT_MARBRE())
for r in range(4):
    for c in range(6):
        x = MX1 - 4 - c * 4.8
        y = 18 + r * 6
        tore(f"Anneau_{r}{c}", x, y, Z_AZ + 0.1, 0.5, 0.08, "30_Mizbeach", MAT_BRONZE())
