import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

from beit_hamikdash_visite import RACINE

from .matieres import SHANI, corne, laine, poil, teinter_maillage
from .maillage import TOUR, Maillage
from .habillage import _objet
from .ustensiles import tube_simple


SEIR_BLEND = RACINE / "seir.blend"
POIL_NOIR = (0.028, 0.025, 0.023)
CORNE = (0.32, 0.28, 0.23)
# Entre les deux cornes, dans le repère du bouc (`beit_hamikdash_seir.py`) : là où se posent les mains.
FRONT_DU_SEIR = Vector((0.955, 0.0, 0.965))


# « קָשַׁר לָשׁוֹן שֶׁל זְהוֹרִית בְּרֹאשׁ שָׂעִיר הַמִּשְׁתַּלֵּחַ » (Yoma 4:2) : nouée au pied des cornes, un bout qui pend ; la forme est un CHOIX.
def lashon_zehorit(mm, repere):
    centre = FRONT_DU_SEIR + Vector((0.0, 0.0, -0.012))
    boucle = [centre + Vector((0.032 * math.cos(a), 0.046 * math.sin(a), 0.006 * math.sin(2.0 * a)))
              for a in np.linspace(0.0, TOUR, 19)]
    pan = [centre + Vector((0.004 * k, 0.046 + 0.010 * k, -0.034 * k)) for k in range(6)]
    for chemin in (boucle, pan):
        mm.nappe([[repere @ p for p in a] for a in tube_simple(chemin, 0.005, 6)], SHANI, "objet")


# La tête vers l'homme, la croupe qui s'en écarte : parallèle à lui, son flanc passait dans la kutonet.
BIAIS_DU_SEIR = math.radians(20.0)


# Un bouc (`beit_hamikdash_seir.py`) posé à `repere` dans le repère de l'armature ; ses objets s'appellent `nom`.
def poser_seir(h, nom, repere):
    with bpy.data.libraries.load(str(SEIR_BLEND)) as (_, charge):
        charge.meshes = ["Seir", "Seir_cornes"]
    for me, matiere, couleur, suffixe in zip(charge.meshes, (poil(), corne()), (POIL_NOIR, CORNE), ("", "_cornes")):
        teinter_maillage(me, couleur)
        me.materials.append(matiere)
        objet = bpy.data.objects.new(f"{nom}{suffixe}", me)
        for c in h.rig.users_collection:
            c.objects.link(objet)
        objet.parent = h.rig
        objet.matrix_basis = repere


# Le bouc suit son homme : `front` au point voulu, tourné vers où l'homme regarde.
def amener_le_seir(h, front):
    repere = (Matrix.Translation(front) @ Matrix.Rotation(-math.pi / 2.0 + BIAIS_DU_SEIR, 4, "Z")
              @ Matrix.Translation(-FRONT_DU_SEIR))
    poser_seir(h, f"{h.nom}_seir", repere)
    ruban = Maillage()
    lashon_zehorit(ruban, repere)
    _objet(h, ruban, f"{h.nom}_lashon_zehorit", laine())


# Le taureau de la Mer (`beit_hamikdash_shor.py`), en chair ; sa robe : CHOIX. Le haut de la tête, dans son repère :
# là où se posent les mains.
SHOR_BLEND = RACINE / "shor.blend"
NUQUE_DU_PAR = Vector((1.763, 0.0, 1.204))
PAR = (0.16, 0.075, 0.045)


# Le taureau suit son homme : posé dans le repère de l'armature, sabots au sol, le haut de sa tête sous `front`, le
# mufle vers `cap` (degrés, 0 : la gauche de l'homme).
def amener_le_par(h, front, cap):
    with bpy.data.libraries.load(str(SHOR_BLEND)) as (_, charge):
        charge.meshes = ["Shor"]
    me = charge.meshes[0]
    teinter_maillage(me, PAR)
    me.materials.append(poil())
    objet = bpy.data.objects.new(f"{h.nom}_par", me)
    for c in h.rig.users_collection:
        c.objects.link(objet)
    objet.parent = h.rig
    objet.matrix_basis = (Matrix.Translation((front.x, front.y, h.sol)) @ Matrix.Rotation(math.radians(cap), 4, "Z")
                          @ Matrix.Translation((-NUQUE_DU_PAR.x, -NUQUE_DU_PAR.y, 0.0)))
    return objet


# « פָּרוֹ הָיָה עוֹמֵד בֵּין הָאוּלָם וְלַמִּזְבֵּחַ, רֹאשׁוֹ לַדָּרוֹם … וְכֹהֵן עוֹמֵד בַּמִּזְרָח וּפָנָיו לַמַּעֲרָב, וְסוֹמֵךְ שְׁתֵּי
# יָדָיו עָלָיו » (Yoma 3:8) : face à l'ouest, le sud est à sa gauche ; la tête tournée vers l'ouest n'est pas faite.
def front_du_par(h):
    return Vector((0.30, -0.62, h.sol + NUQUE_DU_PAR.z))


SEH_BLEND = RACINE / "seh.blend"
LAINE_DU_SEH = (0.66, 0.60, 0.50)


# Un agneau (`beit_hamikdash_seh.py`) posé à `repere` dans le repère de l'armature ; `etire` : les membres dans l'axe.
def poser_seh(h, nom, repere, etire=False):
    with bpy.data.libraries.load(str(SEH_BLEND)) as (_, charge):
        charge.meshes = ["Seh_etire" if etire else "Seh"]
    me = charge.meshes[0]
    teinter_maillage(me, LAINE_DU_SEH)
    me.materials.append(poil())
    objet = bpy.data.objects.new(nom, me)
    for c in h.rig.users_collection:
        c.objects.link(objet)
    objet.parent = h.rig
    objet.matrix_basis = repere


# Debout, les pieds sur le sol : `pied` sous le garrot, le museau tourné de `cap` degrés depuis la gauche de l'homme.
GARROT_DU_SEH = 0.64


def seh_debout(pied, cap):
    return Matrix.Translation(pied) @ Matrix.Rotation(math.radians(cap), 4, "Z") @ Matrix.Translation((-GARROT_DU_SEH, 0.0, 0.0))


# Couché sur le flanc, les pattes vers l'arrière de l'homme si `cap` = 0 : la gorge à `gorge`, à une demi-épaisseur du sol.
GORGE_DU_SEH = Vector((0.80, 0.0, 0.55))
DEMI_EPAISSEUR_DU_SEH = 0.16


def seh_couche(gorge, cap):
    return (Matrix.Translation(gorge) @ Matrix.Rotation(math.radians(cap), 4, "Z") @ Matrix.Rotation(math.pi / 2.0, 4, "X")
            @ Matrix.Translation(-GORGE_DU_SEH))


# Pendu par les jarrets, la tête en bas : les sabots arrière à `crochet`, le ventre vers le devant de l'homme si `cap` = 90.
JARRETS_DU_SEH = Vector((-0.26, 0.0, 0.38))
VENTRE_DU_PENDU = 0.13


def seh_pendu(crochet, cap):
    return (Matrix.Translation(crochet) @ Matrix.Rotation(math.radians(cap), 4, "Z") @ Matrix.Rotation(math.pi / 2.0, 4, "Y")
            @ Matrix.Translation(-JARRETS_DU_SEH))
