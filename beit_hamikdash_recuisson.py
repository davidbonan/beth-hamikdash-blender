"""Ce que `--recuire` refait : les concepts demandés, ceux dont la carte ne correspond plus à la scène, et leurs voisins, que leurs rebonds touchent."""
import contextlib
import datetime
import fcntl
import hashlib
import os
import pathlib
import subprocess
import sys

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from beit_hamikdash_occlusion import VISITE

RACINE = pathlib.Path(__file__).resolve().parent
# Au-delà, le rebond d'une paroi retouchée sur sa voisine se perd dans le bruit de la carte : un seul rang de voisins.
PORTEE_IMPACT = 4.0
FACES_DE_BOITE = ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))


def signature_matiere(mat):
    if mat is None or mat.node_tree is None:
        return repr(mat and (mat.name, tuple(mat.diffuse_color)))
    parties = [mat.name]
    for noeud in sorted(mat.node_tree.nodes, key=lambda n: n.name):
        parties.append(noeud.bl_idname)
        if getattr(noeud, "image", None) is not None:
            parties.append(noeud.image.name)
        for entree in noeud.inputs:
            if entree.is_linked or not hasattr(entree, "default_value"):
                continue
            valeur = entree.default_value
            parties.append(repr(tuple(valeur) if hasattr(valeur, "__len__") else valeur))
    parties += [f"{l.from_node.name}.{l.from_socket.identifier}>{l.to_node.name}.{l.to_socket.identifier}"
                for l in mat.node_tree.links]
    return "|".join(parties)


def empreinte(obj, taille, reglages):
    """Tout ce dont la carte d'un concept dépend chez lui : maillage, dépliage, matières, et les réglages de la lumière."""
    maillage = obj.data
    empreinte_ = hashlib.sha1(reglages.encode())
    empreinte_.update(repr((taille, len(maillage.uv_layers), tuple(map(tuple, obj.matrix_world)))).encode())
    for collection, attribut, type_ in ((maillage.vertices, "co", np.float32),
                                        (maillage.loops, "vertex_index", np.int32),
                                        (maillage.polygons, "loop_total", np.int32),
                                        (maillage.polygons, "material_index", np.int32)):
        valeurs = np.empty(len(collection) * (3 if attribut == "co" else 1), dtype=type_)
        collection.foreach_get(attribut, valeurs)
        empreinte_.update(valeurs.tobytes())
    for fente in obj.material_slots:
        empreinte_.update(signature_matiere(fente.material).encode())
    return empreinte_.hexdigest()


def boite_blender(emprise):
    """L'emprise de reperes.json (glTF, Y vers le haut) en repère Blender."""
    bas, haut = emprise["min"], emprise["max"]
    return Vector((bas[0], -haut[2], bas[1])), Vector((haut[0], -bas[2], haut[1]))


class Geometrie:
    def __init__(self, obj):
        co = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
        obj.data.vertices.foreach_get("co", co)
        matrice = np.array(obj.matrix_world)
        self.sommets = co.reshape(-1, 3) @ matrice[:3, :3].T + matrice[:3, 3]
        obj.data.calc_loop_triangles()
        self.arbre = BVHTree.FromPolygons(self.sommets.tolist(), [tuple(t.vertices) for t in obj.data.loop_triangles])

    def boite(self):
        return Vector(self.sommets.min(axis=0)), Vector(self.sommets.max(axis=0))

    def touche(self, bas, haut):
        if np.all((self.sommets >= bas) & (self.sommets <= haut), axis=1).any():
            return True
        coins = [Vector((x, y, z)) for x in (bas.x, haut.x) for y in (bas.y, haut.y) for z in (bas.z, haut.z)]
        return bool(self.arbre.overlap(BVHTree.FromPolygons(coins, FACES_DE_BOITE)))


def carte_de(precedent, ident):
    return precedent["lumiere"].get(ident) or precedent["occlusion"].get(ident) or {}


class Recuisson:
    """Ce que `--recuire` refait : les concepts demandés, ceux que la scène a changés depuis `precedent` (le reperes.json servi), et leurs voisins."""

    def __init__(self, precedent, demandes, cuits):
        inconnus = demandes - cuits
        if inconnus:
            raise ValueError(f"recuisson demandée sur des concepts qui ne se cuisent pas : {sorted(inconnus)}")
        self.precedent, self.demandes, self.cuits = precedent, demandes, cuits

    def modifies(self, empreintes):
        """Tout concept, cuit ou non, dont l'empreinte a changé ou qui a disparu ; un concept cuit dont la carte manque."""
        anciennes = self.precedent.get("empreintes", {})
        return {ident for ident in empreintes.keys() | anciennes.keys() if anciennes.get(ident) != empreintes.get(ident)} | {
            ident for ident in self.cuits if not (VISITE / carte_de(self.precedent, ident).get("carte", "?")).exists()}

    def cibles(self, fusionnes, empreintes):
        """Les concepts cuits à recuire en lumière, voisins à PORTEE_IMPACT compris, avant comme après la retouche."""
        sources = {ident: "demandé" for ident in self.demandes} | {
            ident: "modifié" for ident in self.modifies(empreintes) - self.demandes}
        marge = Vector((PORTEE_IMPACT,) * 3)
        emprises = self.precedent["emprises"]
        boites = [(source, bas - marge, haut + marge) for source in sources
                  for bas, haut in ([Geometrie(fusionnes[source]).boite()] if source in fusionnes else [])
                  + ([boite_blender(emprises[source])] if source in emprises else [])]
        raisons = {ident: raison for ident, raison in sources.items() if ident in self.cuits}
        for ident in sorted(self.cuits - set(raisons)):
            geometrie = Geometrie(fusionnes[ident])
            source = next((s for s, bas, haut in boites if geometrie.touche(bas, haut)), None)
            if source is not None:
                raisons[ident] = f"voisin de {source}"
        hors_cuisson = sorted(set(sources) - self.cuits)
        if hors_cuisson:
            print(f"\n  modifiés sans carte à eux, recuits par leurs voisins : {', '.join(hors_cuisson)}")
        annoncer(raisons, self.precedent, len(self.cuits))
        return frozenset(raisons)

    def gardees(self, cibles):
        return {nature: {ident: carte for ident, carte in self.precedent[nature].items()
                         if ident in self.cuits - cibles}
                for nature in ("occlusion", "lumiere")}


def annoncer(raisons, precedent, total):
    durees = [carte_de(precedent, ident).get("secondes") for ident in raisons]
    connues = [d for d in durees if d is not None]
    inconnues = len(durees) - len(connues)
    print(f"\n  recuisson : {len(raisons)} concepts sur {total}, ~{sum(connues) / 60:.0f} min"
          + (f" (+{inconnues} sans durée connue)" if inconnues else ""))
    for ident, raison in sorted(raisons.items(), key=lambda r: (r[1].startswith("voisin"), r[0])):
        secondes = carte_de(precedent, ident).get("secondes")
        print(f"    {ident:26s} {raison:36s} {f'{secondes:4.0f} s' if secondes is not None else '   ? s'}")
    print(flush=True)


@contextlib.contextmanager
def verrou():
    """Une cuisson à la fois sur la machine, worktrees compris : le verrou vit dans le .git commun et meurt avec le processus."""
    commun = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=RACINE,
                            capture_output=True, text=True, check=True).stdout.strip()
    with open((RACINE / commun).resolve() / "cuisson.lock", "a+", encoding="utf-8") as fichier:
        try:
            fcntl.flock(fichier, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fichier.seek(0)
            raise SystemExit(f"\n  cuisson déjà en cours, rien n'est lancé : {fichier.read().strip()}\n") from None
        fichier.truncate(0)
        fichier.write(f"{RACINE} · pid {os.getpid()} · depuis {datetime.datetime.now():%H:%M} · "
                      f"{' '.join(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])}\n")
        fichier.flush()
        try:
            yield
        finally:
            fichier.truncate(0)
