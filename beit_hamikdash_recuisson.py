"""Ce que `--recuire` refait : les concepts demandés, ceux dont la carte ne correspond plus à la scène, et leurs voisins, que leurs rebonds touchent."""
import contextlib
import datetime
import fcntl
import functools
import hashlib
import json
import os
import pathlib
import subprocess
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from beit_hamikdash_occlusion import VISITE

RACINE = pathlib.Path(__file__).resolve().parent
# Au-delà, le rebond d'une paroi retouchée sur sa voisine se perd dans le bruit de la carte : un seul rang de voisins.
PORTEE_IMPACT = 4.0
# Être à portée ne suffit pas : encore faut-il peser. Quatre mètres est une distance, pas un
# impact — une porte à 4 m du mur d'enceinte n'occupe qu'un demi-pour-cent de son hémisphère,
# et traînait pourtant ses 447 s de cuisson. La carte sort en PNG 8 bits : un échelon y vaut
# 1/255, soit 0,4 %. Sous le centième d'une borne HAUTE, aucun texel ne peut bouger. Cf. `impact`.
SEUIL_IMPACT = 0.01
# Le facteur de forme ignore ce qui s'interpose : le sol du Har HaBayit, 3,8 m sous le dallage du
# Heikhal, en prenait 100 % à travers le podium. Un voisin doit donc VOIR la retouche : un rayon au
# moins, entre ÉCHANTILLONS points de chacun, qui ne bute sur aucun autre concept.
ECHANTILLONS = 400
FACES_DE_BOITE = ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))


_HACHES_IMAGE = {}


def signature_image(image):
    """Le CONTENU du fichier, pas son nom : l'atlas des gravures garde le sien d'une taille
    à l'autre, et une tuile retaillée doit faire recuire ses porteurs."""
    chemin = pathlib.Path(bpy.path.abspath(image.filepath)) if image.filepath else None
    if chemin is None or not chemin.is_file():
        return f"{image.name}:{tuple(image.size)}:{image.is_dirty}"
    etat = chemin.stat()
    cle = (str(chemin), etat.st_size, etat.st_mtime_ns)
    if cle not in _HACHES_IMAGE:
        _HACHES_IMAGE[cle] = hashlib.sha1(chemin.read_bytes()).hexdigest()
    return _HACHES_IMAGE[cle]


# L'atlas des gravures se hache tuile par tuile, et un concept n'en signe que celles que ses
# UV visent : haché entier, retoucher le cordon du Heikhal faisait recuire toutes les portes
# à timora, jusqu'au Har HaBayit.
FICHE_GRAVURES = VISITE / "matieres" / "gravures.json"
_TUILES_HACHEES = {}


@functools.cache
def _tuiles_de_l_atlas():
    fiche = json.loads(FICHE_GRAVURES.read_text(encoding="utf-8"))
    return f"gravures_{fiche['pixels']}.webp", sorted({tuple(m["tuile"]) for m in fiche["motifs"].values()})


def tuiles_visees(obj, index_matiere, tuiles):
    """Les tuiles de l'atlas où tombe le centre UV d'au moins une face de la matière `index_matiere`."""
    maillage = obj.data
    couche = maillage.uv_layers.get("UVMap")
    if couche is None:
        return []
    uv = np.empty(len(maillage.loops) * 2, dtype=np.float32)
    couche.data.foreach_get("uv", uv)
    debuts, nombres, matieres = (np.empty(len(maillage.polygons), dtype=np.int32) for _ in range(3))
    maillage.polygons.foreach_get("loop_start", debuts)
    maillage.polygons.foreach_get("loop_total", nombres)
    maillage.polygons.foreach_get("material_index", matieres)
    faces = matieres == index_matiere
    if not faces.any():
        return []
    centres = np.add.reduceat(uv.reshape(-1, 2), debuts)[faces] / nombres[faces, None]
    return [(ou, ov, taille) for ou, ov, taille in tuiles
            if ((centres >= (ou, ov)) & (centres < (ou + taille, ov + taille))).all(axis=1).any()]


def signature_tuiles(image, tuiles):
    """Le contenu des seules `tuiles` de l'image, par tuile."""
    cle = signature_image(image)
    if cle not in _TUILES_HACHEES:
        largeur, hauteur = image.size
        pixels = np.empty(largeur * hauteur * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        pixels = pixels.reshape(hauteur, largeur, 4)
        _TUILES_HACHEES[cle] = {
            (ou, ov, taille): hashlib.sha1(pixels[round(ov * hauteur):round((ov + taille) * hauteur),
                                                  round(ou * largeur):round((ou + taille) * largeur)].tobytes()).hexdigest()
            for ou, ov, taille in _tuiles_de_l_atlas()[1]}
    return ",".join(_TUILES_HACHEES[cle][tuile] for tuile in tuiles)


def signature_matiere(mat, obj, index_matiere):
    if mat is None or mat.node_tree is None:
        return repr(mat and (mat.name, tuple(mat.diffuse_color)))
    atlas, tuiles = _tuiles_de_l_atlas()
    parties = [mat.name]
    for noeud in sorted(mat.node_tree.nodes, key=lambda n: n.name):
        parties.append(noeud.bl_idname)
        image = getattr(noeud, "image", None)
        if image is not None and pathlib.Path(image.filepath).name == atlas:
            parties.append(signature_tuiles(image, tuiles_visees(obj, index_matiere, tuiles)))
        elif image is not None:
            parties.append(signature_image(image))
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
    for index, fente in enumerate(obj.material_slots):
        empreinte_.update(signature_matiere(fente.material, obj, index).encode())
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
        self.triangles = np.empty(len(obj.data.loop_triangles) * 3, dtype=np.int64)
        obj.data.loop_triangles.foreach_get("vertices", self.triangles)
        self.triangles = self.triangles.reshape(-1, 3)
        self.arbre = BVHTree.FromPolygons(self.sommets.tolist(), self.triangles.tolist())

    def boite(self):
        return Vector(self.sommets.min(axis=0)), Vector(self.sommets.max(axis=0))

    def touche(self, bas, haut):
        if np.all((self.sommets >= bas) & (self.sommets <= haut), axis=1).any():
            return True
        coins = [Vector((x, y, z)) for x in (bas.x, haut.x) for y in (bas.y, haut.y) for z in (bas.z, haut.z)]
        return bool(self.arbre.overlap(BVHTree.FromPolygons(coins, FACES_DE_BOITE)))

    def points_dans(self, bas, haut):
        """Jusqu'à ECHANTILLONS points de la surface dans la boîte, répartis sur toute la liste : les
        sommets, les centres de triangles, et une grille de la boîte ramenée à la face la plus proche —
        un dallage de cent mètres n'a ni sommet ni centre dans quatre mètres autour d'un mur."""
        bas, haut = np.maximum(np.array(bas), self.sommets.min(axis=0)), np.minimum(np.array(haut), self.sommets.max(axis=0))
        if np.any(bas > haut):
            return np.empty((0, 3))
        grille = np.stack(np.meshgrid(*(np.linspace(b, h, 7) for b, h in zip(bas, haut))), -1).reshape(-1, 3)
        projetes = [tuple(trouve[0]) for trouve in map(self.arbre.find_nearest, map(Vector, grille)) if trouve[0] is not None]
        points = np.concatenate([self.sommets, self.sommets[self.triangles].mean(axis=1), np.array(projetes).reshape(-1, 3)])
        points = points[np.all((points >= bas - 1e-4) & (points <= haut + 1e-4), axis=1)]
        return points[np.linspace(0, len(points) - 1, min(len(points), ECHANTILLONS)).astype(int)] if len(points) else points


class Obstacles:
    """Tous les concepts dans un seul arbre, chaque triangle rattaché au sien."""

    def __init__(self, geometries):
        idents = sorted(geometries)
        decalages = np.cumsum([0] + [len(geometries[i].sommets) for i in idents])
        self.proprietaires = np.concatenate([np.full(len(geometries[i].triangles), k) for k, i in enumerate(idents)])
        self.idents = idents
        self.arbre = BVHTree.FromPolygons(
            np.concatenate([geometries[i].sommets for i in idents]).tolist(),
            np.concatenate([geometries[i].triangles + d for i, d in zip(idents, decalages)]).tolist())

    def voit(self, depuis, vers, cible):
        """Un point de `depuis` voit-il un point de `vers` sans buter sur autre chose que `cible` ?"""
        for p in map(Vector, depuis):
            for q in map(Vector, vers):
                rayon = q - p
                longueur = rayon.length
                if longueur < 0.02:
                    return True
                rayon /= longueur
                _, _, index, distance = self.arbre.ray_cast(p + rayon * 0.01, rayon, longueur - 0.02)
                if index is None or self.idents[self.proprietaires[index]] == cible:
                    return True
        return False


def impact(boite, geometrie):
    """Ce qu'une retouche de `boite` peut faire, AU PLUS, à la lumière de `geometrie`.

    Le facteur de forme de la boîte vue du point le plus exposé du voisin : sa surface
    apparente sur l'hémisphère de ce point. Même si tout ce que la boîte renvoie changeait du
    tout au tout, le voisin n'en verrait pas plus que cette part — et le rebond n'est qu'une
    fraction de sa lumière. C'est donc une borne haute, jamais une estimation.
    """
    bas, haut = np.array(boite[0]), np.array(boite[1])
    ecarts = geometrie.sommets - np.clip(geometrie.sommets, bas, haut)
    distances = np.linalg.norm(ecarts, axis=1)
    plus_proche = int(distances.argmin())
    distance = float(distances[plus_proche])
    if distance < 1e-6:
        return 1.0
    cotes = haut - bas
    vue = np.abs(ecarts[plus_proche]) / distance
    apparente = (vue[0] * cotes[1] * cotes[2] + vue[1] * cotes[0] * cotes[2]
                 + vue[2] * cotes[0] * cotes[1])
    return float(min(1.0, apparente / (np.pi * distance * distance)))


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
        boites = [(source, (bas, haut)) for source in sources
                  for bas, haut in ([Geometrie(fusionnes[source]).boite()] if source in fusionnes else [])
                  + ([boite_blender(emprises[source])] if source in emprises else [])]
        raisons = {ident: raison for ident, raison in sources.items() if ident in self.cuits}
        geometries = {ident: Geometrie(obj) for ident, obj in fusionnes.items()}
        obstacles = None
        negliges, caches = {}, {}
        for ident in sorted(self.cuits - set(raisons)):
            geometrie = geometries[ident]
            parts = sorted(((impact(boite, geometrie), source, boite) for source, boite in boites
                            if geometrie.touche(boite[0] - marge, boite[1] + marge)), key=lambda p: p[0], reverse=True)
            if not parts:
                continue
            if parts[0][0] < SEUIL_IMPACT:
                negliges[ident] = parts[0][:2]
                continue
            for part, source, (bas, haut) in parts:
                if part < SEUIL_IMPACT:
                    break
                voisin = geometrie.points_dans(bas - marge, haut + marge)
                visee = geometries[source].points_dans(*geometries[source].boite()) if source in geometries else []
                # Une source disparue, ou rien à viser de part ou d'autre : la borne vaut telle quelle.
                if not len(voisin) or not len(visee):
                    raisons[ident] = f"voisin de {source} ({part * 100:.0f} %)"
                    break
                obstacles = obstacles or Obstacles(geometries)
                if obstacles.voit(voisin, visee, source):
                    raisons[ident] = f"voisin de {source} ({part * 100:.0f} %)"
                    break
                caches.setdefault(ident, set()).add(source)
        if negliges:
            print(f"\n  voisins écartés, rebond sous {SEUIL_IMPACT * 100:.0f} % : "
                  + ", ".join(f"{ident} ({part * 100:.1f} % de {source})"
                              for ident, (part, source) in sorted(negliges.items())))
        caches = {ident: sources_ for ident, sources_ in caches.items() if ident not in raisons}
        if caches:
            print("\n  voisins écartés, rien ne passe de la retouche jusqu'à eux : "
                  + ", ".join(f"{ident} (de {', '.join(sorted(s))})" for ident, s in sorted(caches.items())))
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
