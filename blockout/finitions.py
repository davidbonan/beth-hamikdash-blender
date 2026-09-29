import bpy
import math
import re
from mathutils import Vector

from .primitives.parametres import m
from .primitives.matieres import MAT_PIERRE, MAT_SOL
from .primitives.volumes import mesh_from_pydata
from .primitives.gravures import _TAILLES, _contour_oriente
from .nettoyage import scene


# ----------------------------------------------------------------------------
# DESSUS FOULÉS
#   Ce qu'on foule est le dallage de la cour, ce qui se tient debout un parement — marche ou dalle.
# ----------------------------------------------------------------------------
FOULES = re.compile(r"Heil_(terrasse|marche)_.+|Marche_.+|Doukhan_\d+|Menora_marche_\d+"
                    r"|Gezuztra_(nord|sud)|Escalier_.+|.+_escalier_\d+|.+_mesiba_\d+"
                    r"|Mesiba_bira_vis_\d+|Beit_HaTevila_(montee|mikve_marches)_\d+"
                    r"|Lishkat_Metzoraim_NO_marche_\d+|Lishkat_HaGazit_estrade_.+"
                    r"|Shaar(HaMayim|HaNitzotz)_terrasse(_.+)?")


def _emplacement(me, mat):
    k = me.materials.find(mat.name)
    if k < 0:
        me.materials.append(mat)
        k = len(me.materials) - 1
    return k


def _dessus(face):
    return face.normal.z > 0.7


def daller_le_dessus(me):
    parement = me.materials.find("Pierre_claire")
    if parement < 0:
        return
    dallage = _emplacement(me, MAT_SOL())
    for face in me.polygons:
        if face.material_index == parement and _dessus(face):
            face.material_index = dallage


def parer_les_flancs(me):
    dallage = me.materials.find("Sol")
    if dallage < 0:
        return
    parement = _emplacement(me, MAT_PIERRE())
    for face in me.polygons:
        if face.material_index == dallage and not _dessus(face):
            face.material_index = parement


for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    if FOULES.fullmatch(o.name):
        daller_le_dessus(o.data)
    parer_les_flancs(o.data)

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
          "70_Kelim": 0.015, "65_Aron": 0.015}   # badim : 0.06 ama de rayon


def biseauter(collection, largeur):
    for o in collection.objects:
        if o.type != 'MESH' or o.get("sans_biseau"):
            continue
        biseau = o.modifiers.new("Biseau", 'BEVEL')
        biseau.width = m(largeur)
        biseau.segments = 2
        biseau.limit_method = 'ANGLE'
        # Chanfreiner entre deux facettes lissées coucherait les normales du flanc sur toute sa hauteur.
        biseau.angle_limit = max(math.radians(30), o.get("pli_vif", 0.0))
        biseau.use_clamp_overlap = True   # sans quoi une paroi de 0.17 ama se retourne


for nom_collection, largeur_biseau in BISEAU.items():
    collection = bpy.data.collections.get(nom_collection)
    if collection:
        biseauter(collection, largeur_biseau)

# ----------------------------------------------------------------------------
# TAILLES
#   Chaque support perd le trou de ses tailles par un booléen posé APRÈS le biseau,
#   pour que le bord de la taille reste vif. La visite évalue les deux ensemble
#   (beit_hamikdash_visite.py, `chanfreiner`).
# ----------------------------------------------------------------------------
MARGE_TAILLE = 0.01       # amot : l'outil passe le nu et le fond, sans quoi le booléen laisse une pellicule
OUTILS = "99_Outils"


def _prisme_taille(paroi, contour, profondeur):
    """Sommets (en amot) et faces du volume qu'une taille retire à son support."""
    nu, _, normale = _contour_oriente(paroi, contour, None)
    n = len(nu)
    verts = ([tuple(p - normale * (profondeur + MARGE_TAILLE)) for p in nu]
             + [tuple(p + normale * MARGE_TAILLE) for p in nu])
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]
    return verts, faces


def _emprise(coins):
    return tuple(map(min, zip(*coins))), tuple(map(max, zip(*coins)))


def _porte_la_taille(support, taille, paroi, profondeur):
    """Le support a sa face sur le nu de la paroi, et assez d'épaisseur derrière pour la
    taille — ni ce qui se tient devant le mur, ni la maçonnerie derrière le placage."""
    axe, c, sens = paroi
    i = 1 if axe == "x" else 0
    face = support[1][i] if sens > 0 else -support[0][i]
    fond = support[0][i] if sens > 0 else -support[1][i]
    nu = m(c) * sens
    if abs(face - nu) > m(MARGE_TAILLE) or fond > nu - m(profondeur):
        return False
    return all(taille[0][j] < support[1][j] and support[0][j] < taille[1][j] for j in range(3) if j != i)


def creuser_les_parois():
    """Ouvre dans chaque support le trou des tailles qui l'entament : un outil par
    support, fait de toutes ses tailles, soustrait par un modificateur."""
    supports = [(o, _emprise([o.matrix_world @ Vector(c) for c in o.bound_box]))
                for o in scene.objects if o.type == 'MESH' and not o.get("taille")]
    par_support, sans_support = {}, 0
    for paroi, contour, profondeur in _TAILLES:
        verts, faces = _prisme_taille(paroi, contour, profondeur)
        emprise = _emprise([tuple(m(c) for c in v) for v in verts])
        porteurs = [support for support, sienne in supports
                    if _porte_la_taille(sienne, emprise, paroi, profondeur)]
        sans_support += not porteurs
        for support in porteurs:
            par_support.setdefault(support, []).append((verts, faces))
    for support, prismes in par_support.items():
        verts, faces = [], []
        for v, f in prismes:
            faces += [[len(verts) + i for i in face] for face in f]
            verts += v
        outil = mesh_from_pydata(f"Outil_{support.name}", verts, faces, OUTILS)
        outil.hide_render = True
        outil.display_type = 'WIRE'
        booleen = support.modifiers.new("Taille", 'BOOLEAN')
        booleen.operation = 'DIFFERENCE'
        booleen.solver = 'EXACT'
        booleen.use_self = True   # sans lui, les parois du Kodesh HaKodashim s'évaluaient vides
        booleen.object = outil
    print(f"  {len(_TAILLES)} tailles creusées dans {len(par_support)} supports, {sans_support} sans support")


creuser_les_parois()
