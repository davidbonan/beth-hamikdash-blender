"""Ce que l'export refait à l'identique d'un lancement à l'autre, gardé sous la clé de tout ce dont il dépend, dans le .git commun : les worktrees le partagent."""
import functools
import hashlib
import os
import pathlib
import subprocess
import tempfile

import bpy
import numpy as np

RACINE = pathlib.Path(__file__).resolve().parents[1]


@functools.cache
def dossier_commun():
    """Le .git commun à tous les worktrees du dépôt."""
    commun = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=RACINE,
                            capture_output=True, text=True, check=True).stdout.strip()
    return (RACINE / commun).resolve()


def hacher_maillage(hache, maillage):
    for collection, attribut, type_ in ((maillage.vertices, "co", np.float32),
                                        (maillage.loops, "vertex_index", np.int32),
                                        (maillage.polygons, "loop_total", np.int32),
                                        (maillage.polygons, "material_index", np.int32)):
        valeurs = np.empty(len(collection) * (3 if attribut == "co" else 1), dtype=type_)
        collection.foreach_get(attribut, valeurs)
        hache.update(valeurs.tobytes())


# Le source entier des modules, et non une liste de fonctions : une aide retouchée et oubliée dans la liste rendrait un résultat périmé.
def cle_de(objets, sources, reglages=None):
    """La clé d'un résultat : les maillages et la place des `objets`, le texte des modules `sources`, les `reglages` et Blender."""
    hache = hashlib.sha1(repr((bpy.app.version_string, reglages)).encode())
    for source in sources:
        hache.update(source.read_bytes())
    for obj in objets:
        hache.update(repr((obj.name, tuple(map(tuple, obj.matrix_world)))).encode())
        hacher_maillage(hache, obj.data)
    return hache.hexdigest()


def chemin(nom):
    return dossier_commun() / "memoire-export" / f"{nom}.npz"


def reprendre(nom, cle):
    """Les tableaux gardés sous `nom`, s'ils l'ont été sous cette `cle` ; sinon None."""
    fichier = chemin(nom)
    if not fichier.exists():
        return None
    with np.load(fichier) as gardes:
        if str(gardes["cle"]) != cle:
            return None
        return {nom_: gardes[nom_] for nom_ in gardes.files if nom_ != "cle"}


# Un seul fichier par nom, remplacé d'un bloc : une seconde exportation, sans verrou, ne lit jamais un fichier à moitié écrit.
def garder(nom, cle, tableaux):
    fichier = chemin(nom)
    fichier.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=fichier.parent, suffix=".npz", delete=False) as provisoire:
        np.savez(provisoire, cle=np.array(cle), **tableaux)
    os.replace(provisoire.name, fichier)
