"""Blender -b -P beit_hamikdash_keruvim.py — écrit keruvim.blend : les deux keruvim de la kaporet.

Deux corps d'enfants MakeHuman (« כְּרַבְיָא », Soucca 5b), agenouillés, penchés l'un vers
l'autre, mains jointes au milieu de la kaporet, tête inclinée vers elle ; des ailes
plumées montent des omoplates et se rejoignent en dais au-dessus du milieu (Shemot 25:20).
Le garçon est un peu plus grand que la fille (Yoma 54a, « זָכָר וּנְקֵבָה » : CHOIX).

Les coiffes MakeHuman sont des cartes trouées par leur alpha, et le keruv est d'or massif :
seule une coiffe qui épouse le crâne s'y taille. En plaques opaques, `bob02` devenait un
casque qui mangeait le visage jusqu'aux yeux.

Le blockout ne bâtit pas ces corps : MakeHuman coûte une minute par figure, et le blockout
se reconstruit en cinq secondes. Il lit `keruvim.blend`, un maillage par keruv, dans le
repère du keruv du blockout : origine sur la kaporet, -x vers l'autre keruv, z vers le haut,
mains à `portee` mètres devant l'origine (propriété du maillage, lue par le blockout).

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_keruvim.py
"""
import math
import pathlib
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

RACINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
import beit_hamikdash_gestes as G  # noqa: E402
from beit_hamikdash_figures import Gabarit, Humain, appliquer_visibilite  # noqa: E402

SORTIE = RACINE / "keruvim.blend"
AMA = 0.48
TEFAH = AMA / 6

# Les mains se rejoignent au milieu de la kaporet : c'est la portée du blockout (PORTEE_KERUV,
# 0,66 ama), reprise ici en mètres et écrite sur le maillage pour que le blockout la relise.
PORTEE = 0.66 * AMA
# Genoux derrière l'origine, l'autre keruv devant (-y du repère d'armature) : le bord de la
# kaporet est à 1,25 ama du milieu, le keruv à 0,05 + portée — rien ne doit dépasser.
DEMI_KAPORET = 1.25 * AMA
RECUL_MAX = DEMI_KAPORET - (0.05 * AMA + PORTEE)
Y_GENOU = -0.075
Y_MAINS = -PORTEE + 0.06           # le poignet ; les doigts couvrent le reste jusqu'au milieu
PENCHE_CUISSE = math.radians(8)    # hanche un peu devant le genou : le corps se porte vers l'autre


class Coque:
    """Sommets et faces accumulés, sens direct vu de dehors — le maillage des ailes."""

    def __init__(self):
        self.sommets, self.faces = [], []

    def nappe(self, anneaux, ferme=True, capots=False):
        n, base = len(anneaux[0]), len(self.sommets)
        for anneau in anneaux:
            self.sommets.extend(anneau)
        cotes = n if ferme else n - 1
        for i in range(len(anneaux) - 1):
            for j in range(cotes):
                a, b = base + i * n + j, base + i * n + (j + 1) % n
                self.faces.append((a, b, b + n, a + n))
        if capots:
            self.faces.append(tuple(base + j for j in range(n))[::-1])
            dernier = base + (len(anneaux) - 1) * n
            self.faces.append(tuple(dernier + j for j in range(n)))

    def maillage(self, nom):
        me = bpy.data.meshes.new(nom)
        me.from_pydata([v[:] for v in self.sommets], [], self.faces)
        me.update()
        return me


# Demi-largeur d'une penne le long de son rachis : étroite à l'emplanture, bords presque
# parallèles, bout arrondi — une feuille de laurier serait pointue.
PENNE = ((0.00, 0.14), (0.06, 0.30), (0.16, 0.42), (0.32, 0.49), (0.52, 0.50), (0.70, 0.48),
         (0.84, 0.40), (0.93, 0.26), (0.98, 0.12), (1.00, 0.02))


def plume(coque, base, direction, normale, longueur, largeur, epaisseur=0.0025, creux=0.25):
    """Une penne : rachis en arête, vane en gouttière, coque fermée de `epaisseur`."""
    d = Vector(direction).normalized()
    t = d.cross(Vector(normale)).normalized()
    n = t.cross(d).normalized()
    o = Vector(base)
    dessus, dessous = [], []
    for u, v in PENNE:
        demi = v * largeur
        arete = 0.35 * epaisseur * (1.0 - u)
        ligne_haut, ligne_bas = [], []
        for j in (-1.0, -0.5, 0.0, 0.5, 1.0):
            # La gouttière creuse la vane vers l'arrière de la plume, l'arête du rachis la relève.
            relief = -creux * demi * j * j + (arete if j == 0.0 else 0.0)
            p = o + d * (u * longueur) + t * (j * demi) + n * relief
            ligne_haut.append(p + n * epaisseur)
            ligne_bas.append(p)
        dessus.append(ligne_haut)
        dessous.append(ligne_bas)
    haut = len(coque.sommets)
    coque.nappe(dessus, ferme=False)
    bas = len(coque.sommets)
    coque.nappe([ligne[::-1] for ligne in dessous], ferme=False)
    for cote, sens in ((0, 1), (-1, -1)):
        bord = [[ligne_bas[cote], ligne_haut[cote]][::sens] for ligne_bas, ligne_haut in zip(dessous, dessus)]
        coque.nappe(bord, ferme=False)
    coque.faces.append(tuple(bas + j for j in range(5)) + tuple(haut + j for j in range(4, -1, -1)))


def bezier(p0, p1, p2, p3, t):
    s = 1.0 - t
    return p0 * (s * s * s) + p1 * (3 * s * s * t) + p2 * (3 * s * t * t) + p3 * (t * t * t)


# Rangées de plumes, de la plus longue à la plus courte : (part de la longueur des rémiges,
# nombre, t de départ, t d'arrivée, décalage hors plan). Les rémiges d'abord ; par-dessus,
# côté extérieur, grandes puis petites couvertures ; côté intérieur, une rangée de
# couvertures marginales qui cache le bras — un os d'aile ne se voit jamais nu.
RANGEES = ((1.00, 22, 0.08, 1.00, 0.000), (0.58, 18, 0.05, 0.98, 0.005), (0.34, 15, 0.03, 0.93, 0.010),
           (0.26, 16, 0.00, 0.96, -0.006))


def aile(coque, racine, coude, bout, apex, dehors, echelle):
    """Une aile : un bras de `racine` (omoplate) à `bout`, courbé par `coude`, et des rangées de
    plumes qui pendent hors de la courbe ; les rémiges du bout prolongent le bras, en éventail
    serré, jusqu'à `apex`.

    `dehors` : normale du plan de l'aile, côté extérieur — c'est de ce côté que les
    couvertures se superposent aux rémiges, comme des tuiles.
    """
    r, c, b, apex = Vector(racine), Vector(coude), Vector(bout), Vector(apex)
    c1 = r + (c - r) * 0.9
    c2 = b - (apex - b).normalized() * ((b - c).length * 0.6)
    longueur_remige = (apex - b).length

    def point(t):
        return bezier(r, c1, c2, b, t)

    def tangente(t):
        h = 1e-3
        return (point(min(t + h, 1.0)) - point(max(t - h, 0.0))).normalized()

    centre = (r + b) / 2 - Vector((0.0, 0.0, 0.10 * echelle))
    plan = Vector(dehors).normalized()
    pas = 24
    chemin = [point(k / pas) for k in range(pas + 1)]
    rayons = [echelle * (0.016 * (1.0 - u) + 0.006 * u) for u in (k / pas for k in range(pas + 1))]
    anneaux = []
    for p, ra, k in zip(chemin, rayons, range(pas + 1)):
        tg = tangente(k / pas)
        f = (plan - tg * plan.dot(tg)).normalized()
        g = tg.cross(f)
        # Section en amande, plus large dans le plan de l'aile : un bord d'attaque, pas un tuyau.
        anneaux.append([p + (f * (0.7 * math.cos(a)) + g * (1.3 * math.sin(a))) * ra
                        for a in (2 * math.pi * i / 10 for i in range(10))])
    coque.nappe(anneaux, capots=True)

    fil = tangente(1.0)
    for part, nombre, t0, t1, decalage in RANGEES:
        for k in range(nombre):
            t = t0 + (t1 - t0) * k / (nombre - 1)
            p, tg = point(t), tangente(t)
            hors = (p - centre)
            hors = (hors - tg * hors.dot(tg) - plan * hors.dot(plan)).normalized()
            w = G.lisse((t - 0.45) / 0.55)
            direction = (hors * (1.0 - w) + fil * w).normalized()
            longueur = echelle * part * (0.07 + 0.11 * G.lisse(t / 0.7)) + part * longueur_remige * G.lisse((t - 0.6) / 0.4)
            largeur = echelle * (0.034 + 0.016 * G.lisse(t / 0.7)) * (0.65 + 0.35 * part)
            tuile = decalage + 0.0015 * (k % 2)
            base = p + plan * (echelle * tuile) - direction * (0.12 * longueur)
            plume(coque, base, direction, plan, longueur, largeur, creux=0.18 if part == 1.0 else 0.3)


def agenouiller(a, h, mains_z, penche_buste, penche_tete):
    """Règles de la pose : genoux au sol derrière l'origine, buste et tête vers l'autre keruv,
    poignets à Y_MAINS, paumes vers le bas."""
    sq = a.sq
    l1, l2 = sq.longueur["thigh_l"], sq.longueur["calf_l"]
    genou_z = 0.05
    regles = []
    for cote, s in (("l", 1.0), ("r", -1.0)):
        hanche_repos = sq.tete(f"thigh_{cote}")
        genou = Vector((hanche_repos.x, Y_GENOU, genou_z))
        hanche = genou + Vector((0.0, -l1 * math.sin(PENCHE_CUISSE), l1 * math.cos(PENCHE_CUISSE)))
        cheville = genou + Vector((0.0, l2 * 0.985, 0.012))
        if cote == "l":
            regles.append(G.bassin(Vector((0.0, hanche.y - hanche_repos.y, hanche.z - hanche_repos.z))))
        pied = sq.longueur[f"foot_{cote}"]
        regles.append(G.chaine(sq, f"thigh_{cote}", f"calf_{cote}", cheville, G.DEVANT + G.GAUCHE * (0.1 * s), G.GENOU))
        regles.append({f"foot_{cote}": (lambda m, poses, c=cheville, p=pied: G.viser(m, c + Vector((0.0, p, -0.35 * p)))),
                       f"ball_{cote}": (lambda m, poses, c=cheville, p=pied: G.viser(m, c + Vector((0.0, 1.6 * p, -0.5 * p))))})
        regles.append(G.bras(a, cote, Vector((s * 0.035, Y_MAINS, mains_z)),
                             pole=lambda poses, s=s: a.dans("spine_03", poses, Vector((0.45 * s, 0.6, -0.9)))))
        regles.append(G.paume(a, cote, Vector((0.0, 0.0, -1.0))))
        regles.append(G.doigts(a, cote, flexion=0.10, pouce=0.20))
    regles.append(G.buste(flexion=penche_buste))
    regles.append(G.tete(flexion=penche_tete))
    return G.composer(*regles)


def poser(h, regles):
    _, bases = h.squelette.resoudre(regles)
    for nom, base in bases.items():
        os_ = h.rig.pose.bones[nom]
        os_.rotation_mode = "QUATERNION"
        os_.matrix_basis = base
    bpy.context.view_layer.update()


def cuire(objet, rig):
    """Le maillage évalué (armature, masque), dans le repère de l'armature."""
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(objet.evaluated_get(deps))
    me.transform(rig.matrix_world.inverted() @ objet.matrix_world)
    return me


def surface(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    arbre = BVHTree.FromBMesh(bm)
    bm.free()
    return arbre


def omoplate(arbre, x, z):
    """Le point du dos à la hauteur `z`, sur la verticale `x` : premier impact d'un rayon venu de l'arrière."""
    touche, normale, _, _ = arbre.ray_cast(Vector((x, 1.0, z)), Vector((0.0, -1.0, 0.0)), 2.0)
    if touche is None:
        raise RuntimeError(f"pas de dos en x={x:.3f} z={z:.3f}")
    return touche, normale


def keruv(nom, gabarit, cheveux, penche_buste, penche_tete, mains_z, apex_z):
    h = Humain(nom, gabarit, cheveux=cheveux, barbe=None, sourcils=1)
    h.detendre()
    appliquer_visibilite(h, h.visible & ~h.efface)
    a = G.Acteur(h.squelette, h.sol)
    poser(h, agenouiller(a, h, mains_z, penche_buste, penche_tete))

    pieces = [cuire(o, h.rig) for o in [h.corps] + h.accessoires + h.poils]
    corps = pieces[0]
    arbre = surface(corps)
    poses, _ = h.squelette.resoudre(agenouiller(a, h, mains_z, penche_buste, penche_tete))
    epaule = poses["spine_03"] @ Vector((0.0, h.squelette.longueur["spine_03"], 0.0))
    echelle = gabarit.taille / 0.92
    ailes = Coque()
    for s in (1.0, -1.0):
        racine, normale = omoplate(arbre, s * 0.05 * echelle, epaule.z - 0.03 * echelle)
        racine = racine + normale * 0.01
        coude = Vector((s * 0.08 * echelle, racine.y + 0.15 * echelle, racine.z + 0.24 * echelle))
        # Le bras s'arrête là où les rémiges prennent le relais : elles filent dans son axe
        # jusqu'à l'apex, au-dessus du milieu de la kaporet — les quatre ailes s'y rejoignent.
        apex = Vector((s * 0.012, -PORTEE + 0.005, apex_z))
        bout = Vector((s * 0.045 * echelle, -PORTEE + 0.20 * echelle, racine.z + 0.30 * echelle))
        dehors = ((bout - racine).cross(coude - racine)).normalized()
        if dehors.x * s < 0:
            dehors = -dehors
        aile(ailes, racine, coude, bout, apex, dehors, echelle)
    pieces.append(ailes.maillage(f"{nom}_ailes"))

    bm = bmesh.new()
    for me in pieces:
        bm.from_mesh(me)
    for me in pieces:
        bpy.data.meshes.remove(me)
    final = bpy.data.meshes.new(nom)
    bm.to_mesh(final)
    bm.free()
    # Repère du keruv du blockout : -x vers l'autre keruv, et le corps posé sur la kaporet.
    bas = min(v.co.z for v in final.vertices)
    final.transform(Matrix.Rotation(-math.pi / 2, 4, "Z") @ Matrix.Translation((0.0, 0.0, -bas)))
    final.update()
    final.shade_smooth()
    final.set_sharp_from_angle(angle=math.radians(50))
    final["portee"] = PORTEE
    xs = [v.co.x for v in final.vertices]
    zs = [v.co.z for v in final.vertices]
    print(f"  {nom:14s} {len(final.vertices):6d} sommets · devant {-min(xs):.3f} m · arrière {max(xs):.3f} m "
          f"(max {RECUL_MAX:.3f}) · haut {max(zs):.3f} m ({max(zs) / TEFAH:.1f} tefa'him)")
    if max(xs) > RECUL_MAX + 1e-3:
        print(f"  AVERTISSEMENT : {nom} dépasse le bord de la kaporet de {max(xs) - RECUL_MAX:.3f} m")
    return final


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    garcon = keruv("Keruv_garcon", Gabarit(0.92, genre=1.0, age=0.10, muscle=0.5, poids=0.5, peau="young_caucasian_male"),
                   "short02", penche_buste=0.20, penche_tete=0.60, mains_z=0.40, apex_z=0.90)
    fille = keruv("Keruv_fille", Gabarit(0.87, genre=0.0, age=0.10, muscle=0.45, poids=0.5, peau="young_caucasian_female"),
                  "braid01", penche_buste=0.18, penche_tete=0.60, mains_z=0.38, apex_z=0.87)
    for me in (garcon, fille):
        me.use_fake_user = True
    bpy.data.libraries.write(str(SORTIE), {garcon, fille}, fake_user=True, compress=True)
    print(f"écrit {SORTIE.name} · {SORTIE.stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()
