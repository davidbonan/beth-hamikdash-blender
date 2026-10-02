import pathlib
import zlib

import bpy
import numpy as np


LIN = (0.80, 0.78, 0.72)
TEKHELET = (0.030, 0.075, 0.30)
ARGAMAN = (0.22, 0.025, 0.12)
SHANI = (0.45, 0.022, 0.020)
DRAP_NOIR = (0.018, 0.018, 0.021)
TALITH = (0.78, 0.76, 0.70)
RAIE_TALITH = (0.02, 0.02, 0.035)
LAINE_BLEUE = (0.035, 0.050, 0.11)
CHENE = (0.28, 0.17, 0.08)
BOYAU = (0.62, 0.52, 0.36)
BRONZE = (0.62, 0.40, 0.18)
CHAIR = (0.55, 0.16, 0.12)
OR = (1.0, 0.74, 0.30)
ARGENT = (0.90, 0.91, 0.93)
ETOUPE = (0.09, 0.07, 0.05)
METAUX = (OR, BRONZE, ARGENT)


TUILE = 0.04


def _image(nom, rgb, donnees=False):
    cote = rgb.shape[0]
    image = bpy.data.images.new(nom, cote, cote, alpha=False)
    if donnees:
        image.colorspace_settings.name = "Non-Color"
    rgba = np.ones((cote, cote, 4), dtype=np.float32)
    rgba[..., :3] = rgb
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    return image


# Armure toile, ou sergé, raccordable : `fils` fils par tuile de TUILE mètres.
def trame(nom, fils, serge=False, duvet=0.0, cote=256):
    alea = np.random.default_rng(zlib.crc32(nom.encode()))
    t = (np.arange(cote) + 0.5) / cote * fils
    x, y = np.meshgrid(t, t)
    i, j = x.astype(int) % fils, y.astype(int) % fils
    grosseur_c, grosseur_t = 0.75 + 0.5 * alea.random(fils), 0.75 + 0.5 * alea.random(fils)
    dessus = ((i - j) % 4 < 2) if serge else ((i + j) % 2 == 0)
    bombe_c = np.sin(np.pi * (x % 1.0)) ** 0.7 * np.sin(np.pi * (y % 1.0)) ** 0.25 * grosseur_c[i]
    bombe_t = np.sin(np.pi * (y % 1.0)) ** 0.7 * np.sin(np.pi * (x % 1.0)) ** 0.25 * grosseur_t[j]
    hauteur = np.where(dessus, bombe_c, bombe_t)
    if duvet:
        bruit = alea.random((cote, cote))
        for _ in range(3):
            bruit = (bruit + np.roll(bruit, 1, 0) + np.roll(bruit, 1, 1) + np.roll(bruit, (1, 1), (0, 1))) / 4
        hauteur = hauteur * (1.0 - duvet) + (bruit - bruit.mean() + 0.5) * duvet
    fil = np.where(dessus, grosseur_c[i], grosseur_t[j])
    teinte = (0.78 + 0.22 * hauteur) * (0.96 + 0.08 * (fil - 0.75))
    force = 0.12 * cote / fils
    gx = (np.roll(hauteur, -1, 1) - np.roll(hauteur, 1, 1)) * force
    gy = (np.roll(hauteur, -1, 0) - np.roll(hauteur, 1, 0)) * force
    normale = np.dstack([-gx, -gy, np.ones_like(hauteur)])
    normale /= np.linalg.norm(normale, axis=2, keepdims=True)
    return (_image(f"{nom}_couleur", np.repeat(teinte[..., None], 3, axis=2)),
            _image(f"{nom}_relief", normale * 0.5 + 0.5, donnees=True))


def _douille(douilles, identifiant):
    return next(d for d in douilles if d.identifier == identifiant)


def _matiere(nom, rugosite, metal=0.0, tissu=None):
    mat = bpy.data.materials.get(nom)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(nom)
    mat.use_nodes = True
    mat.use_backface_culling = False
    arbre = mat.node_tree
    bsdf = next(n for n in arbre.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    couleur = arbre.nodes.new("ShaderNodeVertexColor")
    couleur.layer_name = "Color"
    bsdf.inputs["Roughness"].default_value = rugosite
    bsdf.inputs["Metallic"].default_value = metal
    if tissu is None:
        arbre.links.new(couleur.outputs["Color"], bsdf.inputs["Base Color"])
        return mat
    teinte, relief = tissu
    image = arbre.nodes.new("ShaderNodeTexImage")
    image.image = teinte
    melange = arbre.nodes.new("ShaderNodeMix")
    melange.data_type, melange.blend_type = "RGBA", "MULTIPLY"
    melange.inputs["Factor"].default_value = 1.0
    arbre.links.new(couleur.outputs["Color"], _douille(melange.inputs, "A_Color"))
    arbre.links.new(image.outputs["Color"], _douille(melange.inputs, "B_Color"))
    arbre.links.new(_douille(melange.outputs, "Result_Color"), bsdf.inputs["Base Color"])
    carte = arbre.nodes.new("ShaderNodeTexImage")
    carte.image = relief
    normale = arbre.nodes.new("ShaderNodeNormalMap")
    arbre.links.new(carte.outputs["Color"], normale.inputs["Color"])
    arbre.links.new(normale.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def lin():
    return _matiere("Figure_Lin", 0.82, tissu=trame("lin", 24))


def laine():
    return _matiere("Figure_Laine", 0.92, tissu=trame("laine", 16, serge=True, duvet=0.35))


def velours():
    return _matiere("Figure_Velours", 0.75, tissu=trame("velours", 32, duvet=0.85))


def feutre():
    return _matiere("Figure_Feutre", 0.62)


def bois():
    return _matiere("Figure_Bois", 0.6)


def metal():
    return _matiere("Figure_Metal", 0.32, 1.0)


def poil():
    return _matiere("Figure_Poil", 0.9)


def corne():
    return _matiere("Figure_Corne", 0.45)


_teintes = {}


def _retoucher(image, cle, cote, retouche):
    cle = (image.filepath or image.name, cle, cote)
    if cle in _teintes:
        return _teintes[cle]
    copie = image.copy()
    copie.name = f"{pathlib.Path(image.name).stem}_{len(_teintes)}"
    if copie.size[0] > cote:
        copie.scale(cote, cote)
    px = np.empty(len(copie.pixels), dtype=np.float32)
    copie.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    retouche(px)
    copie.pixels.foreach_set(px.ravel())
    copie.pack()
    _teintes[cle] = copie
    return copie


def teinter(image, facteur, cote=1024):
    def multiplier(px):
        px[:, :3] *= np.array(facteur, dtype=np.float32)
    return _retoucher(image, ("teinte", tuple(round(f, 3) for f in facteur)), cote, multiplier)


# Garde le grain et l'ombre des plis ; la clarté médiane prend la teinte `couleur`.
def reteindre(image, couleur, cote=1024):
    def remplacer(px):
        clarte = px[:, :3] @ np.array((0.2126, 0.7152, 0.0722), dtype=np.float32)
        relative = 1.0 + 0.5 * (clarte / max(float(np.median(clarte)), 1e-3) - 1.0)
        px[:, :3] = np.minimum(relative[:, None] * np.array(couleur, dtype=np.float32), 1.0)
    return _retoucher(image, ("reteinte", tuple(round(c, 3) for c in couleur)), cote, remplacer)


def teinter_objet(objet, facteur, cote=1024):
    for mat in objet.data.materials:
        for relief in [n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeNormalMap"]:
            mat.node_tree.nodes.remove(relief)
        for noeud in mat.node_tree.nodes:
            if noeud.bl_idname == "ShaderNodeTexImage" and noeud.image and "normal" not in noeud.image.name \
                    and not noeud.image.name.endswith(("_hn.png", "_s.png")):
                noeud.image = teinter(noeud.image, facteur, cote)


# Un maillage sans couleur de sommets en reçoit une seule : la matière des figures la lit.
def teinter_maillage(me, couleur):
    couleurs = me.color_attributes.new("Color", "BYTE_COLOR", "CORNER")
    couleurs.data.foreach_set("color", [*couleur, 1.0] * len(me.loops))
