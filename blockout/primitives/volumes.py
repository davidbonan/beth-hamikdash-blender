import bpy
import math
import zlib
from mathutils import Matrix, Vector

from .parametres import AMA, m
from .matieres import MAT_COLONNE, MAT_FER, MAT_OR, MAT_PIERRE, MAT_TERRE_CUITE, braise


# ----------------------------------------------------------------------------
# VOLUMES
#   Aucun opérateur : `bpy.ops.mesh.primitive_*` réévalue le graphe de dépendances à
#   chaque appel, et le coût est quadratique en nombre d'objets (mesuré : 0,44 s pour
#   200 cubes, 11,9 s pour 800, 52,6 s pour 1600). Les milliers de volumes de la
#   scène se posent donc directement en `bpy.data`.
#   Les faces sont écrites dans le sens direct vu de l'extérieur : c'est la passe
#   Normal qui conditionne l'i2i, et une normale retournée y fait un trou.
# ----------------------------------------------------------------------------
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

def _objet(name, data, col, mat=None):
    """Objet neuf posé dans sa collection, sans passer par un opérateur."""
    o = bpy.data.objects.new(name, data)
    if mat is not None:
        data.materials.append(mat)
    return link_to(o, col)

def mesh_from_pydata(name, verts, faces, col, mat=None, uv=None):
    """Maillage à partir de sommets en amot et de faces indexées. `uv`, une coordonnée
    de texture par sommet, n'est porté que par les plaques gravées : tout le reste de la
    scène se lit en coordonnées de monde, et n'a rien à déplier."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(m(c) for c in v) for v in verts], [], faces)
    if uv is not None:
        couche = me.uv_layers.new(name="UVMap")
        couche.data.foreach_set("uv", [c for boucle in me.loops for c in uv[boucle.vertex_index]])
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

def _lisser(o, cotes):
    """Lisse entre facettes voisines ; tout pli plus franc que leur pas reste vif."""
    pli = math.radians(360 / cotes + 1)
    o.data.shade_smooth()
    o.data.set_sharp_from_angle(angle=pli)
    o["pli_vif"] = pli
    return o

FACES_BOITE = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
               [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]

def box(name, x0, x1, y0, y1, z0, z1, col="20_Azara", mat=None):
    """Boîte définie par ses bornes en amot."""
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    z0, z1 = min(z0, z1), max(z0, z1)
    verts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    return mesh_from_pydata(name, verts, FACES_BOITE, col, mat)

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
    return _lisser(prism(name, _cercle(x, y, r, verts), min(z0, z1), max(z0, z1), col, mat), verts)

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
    return _lisser(mesh_from_pydata(name, sommets, faces, col, mat), verts)

def revolution_axe(name, base, axe, profil, col, mat=None, verts=32, depart=None, forme=None):
    """`revolution` le long d'un axe quelconque partant de `base` (amot), même profil.

    `depart` : direction du premier méridien, ramenée perpendiculaire à l'axe.
    `forme(θ, t)` multiplie le rayon — θ compté depuis `depart`, t la hauteur sur le
    profil ramenée entre 0 et 1 : côtes d'amande, bec de lampe.
    """
    a = Vector(axe).normalized()
    u = Vector(depart) if depart else a.orthogonal()
    u = (u - a * u.dot(a)).normalized()
    v = a.cross(u)
    haut = max(h for _, h in profil)
    sommets, debut = [], []
    for r, h in profil:
        debut.append(len(sommets))
        centre = Vector(base) + a * h
        if not r:
            sommets.append(centre[:])
            continue
        for k in range(verts):
            th = 2 * math.pi * k / verts
            rayon = r * (forme(th, h / haut) if forme else 1)
            sommets.append((centre + (u * math.cos(th) + v * math.sin(th)) * rayon)[:])
    tailles = [verts if r else 1 for r, _ in profil]
    faces = []
    if tailles[0] > 1:
        faces.append(list(range(verts))[::-1])
    if tailles[-1] > 1:
        faces.append(list(range(debut[-1], debut[-1] + verts)))
    for i in range(len(profil) - 1):
        n0, n1 = tailles[i], tailles[i + 1]
        for k in range(verts):
            faces.append(_face([debut[i] + k % n0, debut[i] + (k + 1) % n0,
                                debut[i + 1] + (k + 1) % n1, debut[i + 1] + k % n1]))
    return _lisser(mesh_from_pydata(name, sommets, faces, col, mat), verts)

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

# Base, fût cannelé et chapiteau d'une colonne de galerie : tout le profil est un CHOIX,
# couvert par « וּמְפָאֲרִין אוֹתוֹ וּמְיַפִּין כְּפִי כֹּחָן » (Rambam, Beit HaBe'hira 1:11).
# Rayons et hauteurs en part du rayon du fût.
BASE_ATTIQUE = ((1.30, 0.00), (1.32, 0.25), (1.25, 0.50), (1.08, 0.60), (1.05, 0.83),
                (1.18, 0.93), (1.20, 1.10), (1.05, 1.25), (1.00, 1.25))
ECHINE = ((1.00, 0.00), (1.10, 0.13), (1.10, 0.33), (0.98, 0.47), (0.98, 0.67),
          (1.10, 0.83), (1.45, 1.50), (1.50, 1.67), (0.00, 1.67))
CANNELURES = 20

def colonne_cannelee(name, x, y, z0, z1, r, col, mat=None):
    """Colonne de galerie : plinthe, base attique, fût à vingt cannelures, échine, abaque.
    Le fût se pose à facettes : c'est l'arête entre deux cannelures qui prend la lumière."""
    mat = mat or MAT_COLONNE()
    plinthe, base = 0.5 * r, BASE_ATTIQUE[-1][1] * r
    echine, abaque = ECHINE[-1][1] * r, 0.65 * r
    box(f"{name}_plinthe", x - 1.4 * r, x + 1.4 * r, y - 1.4 * r, y + 1.4 * r,
        z0, z0 + plinthe, col, mat)
    revolution(f"{name}_base", x, y, z0 + plinthe,
               [(k * r, h * r) for k, h in BASE_ATTIQUE], col, mat, verts=24)
    etoile = [(x + r * (1.0 if i % 2 == 0 else 0.88) * math.cos(math.pi * i / CANNELURES),
               y + r * (1.0 if i % 2 == 0 else 0.88) * math.sin(math.pi * i / CANNELURES))
              for i in range(2 * CANNELURES)]
    haut_fut = z1 - abaque - echine
    prism(f"{name}_fut", etoile, z0 + plinthe + base, haut_fut, col, mat)
    revolution(f"{name}_echine", x, y, haut_fut, [(k * r, h * r) for k, h in ECHINE],
               col, mat, verts=24)
    box(f"{name}_abaque", x - 1.6 * r, x + 1.6 * r, y - 1.6 * r, y + 1.6 * r,
        z1 - abaque, z1, col, mat)

# Balustre de garde-corps : (rayon, hauteur) en amot, de la plinthe à la main courante.
BALUSTRE = ((0.14, 0.00), (0.14, 0.12), (0.08, 0.20), (0.08, 0.35), (0.20, 0.70),
            (0.22, 0.85), (0.12, 1.15), (0.08, 1.25), (0.14, 1.38), (0.14, 1.50))

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

def ellipsoide(name, x, y, z, rayons, col, mat=None, segs=16):
    """Sphère unité étirée de `rayons` (rx, ry, rz) amot autour de son centre."""
    o = sphere(name, x, y, z, 1.0, col, mat, segs)
    centre = Vector((m(x), m(y), m(z)))
    for v in o.data.vertices:
        v.co = centre + Vector(tuple(d * r for d, r in zip(v.co - centre, rayons)))
    o.data.update()
    return o

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

def wedge_ramp_oblique(name, x_bas, x_haut, largeur, y_bas, y_haut, z0, z1, col, mat=None):
    """Rampe comme `wedge_ramp`, dont le bord gauche glisse de x_bas (en y_bas) à x_haut (en y_haut)."""
    verts = [(x_bas, y_bas, z0), (x_bas + largeur, y_bas, z0), (x_haut + largeur, y_haut, z0), (x_haut, y_haut, z0),
             (x_haut + largeur, y_haut, z1), (x_haut, y_haut, z1)]
    faces = [[0, 1, 2, 3][::-1], [0, 1, 4, 5], [1, 2, 4], [3, 0, 5], [2, 3, 5, 4]]
    return mesh_from_pydata(name, verts, faces, col, mat)

def massif_en_pente(name, x0, x1, y0, y1, z_bas, z_haut_y0, z_haut_y1, col, mat=None):
    """Massif à fond plat dont le dessus monte de z_haut_y0 (en y0) à z_haut_y1 (en y1)."""
    verts = [(x0, y0, z_bas), (x1, y0, z_bas), (x1, y1, z_bas), (x0, y1, z_bas),
             (x0, y0, z_haut_y0), (x1, y0, z_haut_y0), (x1, y1, z_haut_y1), (x0, y1, z_haut_y1)]
    faces = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
             [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
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
    o = cyl(name, 0, 0, -demi, demi, r, col, mat or MAT_OR(), verts)
    o.location = (a + b) / 2
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o

def tube_between(name, p0, p1, r, col, mat=None, verts=16):
    """Cylindre sans fonds et lissé entre deux points (amot) : ses normales partent de l'axe."""
    a, b = Vector([m(c) for c in p0]), Vector([m(c) for c in p1])
    d = b - a
    demi = d.length / AMA / 2
    cercle = _cercle(0, 0, r, verts)
    n = len(cercle)
    sommets = [(x, y, -demi) for x, y in cercle] + [(x, y, demi) for x, y in cercle]
    faces = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    o = mesh_from_pydata(name, sommets, faces, col, mat or MAT_OR())
    o.data.shade_smooth()
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

def ner_sur_tablette(name, x, y, normale, z, col):
    """Tablette de pierre sortant du mur en (x, y), lampe de terre et flamme dessus.
    `normale` : le sens où le mur regarde le passage."""
    nx, ny = normale
    x0, x1 = sorted((x, x + nx * 0.4)) if nx else (x - 0.4, x + 0.4)
    y0, y1 = sorted((y, y + ny * 0.4)) if ny else (y - 0.4, y + 0.4)
    box(f"{name}_tablette", x0, x1, y0, y1, z - 0.2, z, col)
    cx, cy = x + nx * 0.2, y + ny * 0.2
    cyl(f"{name}_lampe", cx, cy, z, z + 0.15, 0.16, col, MAT_TERRE_CUITE(), verts=10)
    cone(f"{name}_flamme", cx, cy, z + 0.15, z + 0.45, 0.06, 0.0, col, braise("Braise"), verts=8)

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
