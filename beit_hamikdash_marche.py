"""Où la visite passe à pied, et où elle bute — sans reconstruire la scène.

    /Applications/Blender.app/Contents/MacOS/Blender -b beit_hamikdash.blend \\
        -P beit_hamikdash_marche.py -- [--zone x0 x1 y0 y1] [--pas 0.12] [--tout]
                                       [--image renders/marche/marche.png] [--ou x y [x y ...]]

Marcher dans le modèle en éprouve la continuité, mais une marche à la main ne visite
que ce qu'on pense à essayer. Ce script rejoue la règle de marche de visite/visite.js
— MONTEE, CHUTE, GARDE, SOUS_PAS, les deux rayons de garde et le rayon de sol — sur
une grille posée sur la scène, puis relie les cases que le marcheur peut enchaîner
dans les deux sens. Il en sort les zones d'un seul tenant, et chaque frontière entre
deux zones avec la raison du refus : une marche trop haute, un vide sous le pas, une
fente qu'un pied enjamberait, ou l'objet que le rayon de garde heurte. Un sol que la
visite ne peut atteindre à pied se lit alors sans y marcher.

Le rapport ne retient que les zones où se tient un lieu de concepts.json ou une entrée
de reperes.json : le dessus d'un socle, une cuve ou un toit sont des sols aussi, mais
personne ne cherche à y aller. `--tout` les garde. `--ou` détaille des points : les
sols superposés qu'on y trouve, ce qu'ils sont et leur zone.

La zone se donne en amot, dans le repère de Blender (x vers l'est, y vers le nord) ;
par défaut, les cours, le Bayit et le 'Heil avec ses degrés — les degrés doivent être
dans la grille, sans quoi les terrasses du 'Heil paraissent coupées du monde. Le pas
de la grille vaut celui du marcheur.

Les constantes sont recopiées de visite.js : les changer d'un côté oblige à les
changer de l'autre.
"""

import colorsys
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

DOSSIER = Path(bpy.path.abspath("//"))
sys.path.insert(0, str(DOSSIER))
from beit_hamikdash_visite import COLLECTIONS  # noqa: E402

AMA = 0.48
MONTEE = AMA + 0.02
CHUTE = 0.60
GARDE = 0.06
SOUS_PAS = 0.12
HAUTEURS_GARDE = (MONTEE + 0.02, 1.55)
HAUTEUR_HOMME = 1.75        # celle des silhouettes : un creux plus bas ne se visite pas debout
PENTE_SOL = 0.25            # normale.z au-dessus : un sol, pas un mur
TRAVERSABLES = ("parokhet", "chaines_devir", "soreg")

ZONE_DEFAUT = (-215.0, 170.0, -100.0, 115.0)  # amot : cours, Bayit, 'Heil et ses degrés
Z_HAUT, Z_BAS = 60.0, -60.0                  # mètres : toits compris, roche exclue
NIVEAUX = 5                                  # sols superposés retenus par case
VOISINAGE = 3.0                              # mètres : au-delà, deux sols ne se font pas face
EPS = 1e-3
COPLANAIRE = 1e-4   # m : un rayon tiré de 60 m se pose à quelques microns du plan, en float32
CHEVEU = 0.0173             # décale un point demandé hors des diagonales des faces, où un rayon passe ou non au hasard
BAS = Vector((0.0, 0.0, -1.0))
CASES_MIN = 25                               # une zone plus petite est un rebord, pas un lieu


def arguments():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def option(args, nom, n, defaut):
    if nom not in args:
        return defaut
    k = args.index(nom)
    valeurs = args[k + 1:k + 1 + n]
    return valeurs[0] if n == 1 else valeurs


def prefixes_traversables():
    concepts = json.loads((DOSSIER / "visite" / "concepts.json").read_text())["concepts"]
    return tuple(p for c in concepts if c["id"] in TRAVERSABLES for p in c["prefixes"])


# --- la scène en un seul maillage ---------------------------------------------

def est_ferme(maille):
    """Chaque arête portée par deux faces : le volume a un dedans et un dehors."""
    if not len(maille.edges):
        return False
    aretes = np.empty(len(maille.loops), dtype=np.int64)
    maille.loops.foreach_get("edge_index", aretes)
    return bool(np.all(np.bincount(aretes, minlength=len(maille.edges)) == 2))


def murs(depsgraph, exclus):
    """Tous les volumes que la visite exporte, sauf les étoffes, en un seul maillage monde."""
    sommets, triangles, sources, noms, fermes = [], [], [], [], []
    decalage = 0
    for objet in bpy.data.objects:
        if objet.type != "MESH" or objet.name.startswith(exclus):
            continue
        if not any(c.name in COLLECTIONS for c in objet.users_collection):
            continue
        maille = objet.evaluated_get(depsgraph).data
        maille.calc_loop_triangles()
        nv, nt = len(maille.vertices), len(maille.loop_triangles)
        if not nv or not nt:
            continue
        co = np.empty(nv * 3, dtype=np.float64)
        maille.vertices.foreach_get("co", co)
        matrice = np.array(objet.matrix_world)
        co = co.reshape(-1, 3) @ matrice[:3, :3].T + matrice[:3, 3]
        tri = np.empty(nt * 3, dtype=np.int64)
        maille.loop_triangles.foreach_get("vertices", tri)
        tri = tri.reshape(-1, 3)
        if np.linalg.det(matrice[:3, :3]) < 0:
            tri = tri[:, [0, 2, 1]]
        sommets.append(co)
        triangles.append(tri + decalage)
        sources.append(np.full(nt, len(noms), dtype=np.int32))
        noms.append(objet.name)
        fermes.append(est_ferme(maille))
        decalage += nv
    return np.vstack(sommets), np.vstack(triangles), np.concatenate(sources), noms, fermes


def arbre(sommets, triangles):
    maille = bpy.data.meshes.new("Marche")
    maille.vertices.add(len(sommets))
    maille.vertices.foreach_set("co", sommets.ravel())
    maille.loops.add(len(triangles) * 3)
    maille.loops.foreach_set("vertex_index", triangles.ravel())
    maille.polygons.add(len(triangles))
    maille.polygons.foreach_set("loop_start", np.arange(0, len(triangles) * 3, 3))
    maille.update()
    objet = bpy.data.objects.new("Marche", maille)
    bpy.context.scene.collection.objects.link(objet)
    return BVHTree.FromObject(objet, bpy.context.evaluated_depsgraph_get())


class Rayons:
    """Les rayons de three sous FrontSide : une face vue de dos ne compte pas."""

    def __init__(self, bvh, sources, fermes):
        self.bvh, self.sources, self.fermes = bvh, sources, fermes

    def premier(self, origine, direction, portee):
        depart, restant = Vector(origine), portee
        for _ in range(32):
            if restant <= 0:
                return None
            point, normale, index, distance = self.bvh.ray_cast(depart, direction, restant)
            if point is None:
                return None
            restant -= distance + EPS
            depart = point + direction * EPS
            if normale.dot(direction) < 0:
                return point, normale, index
        return None

    def paquets(self, origine, direction, portee):
        """Toutes les faces rencontrées, groupées par point d'impact.

        Le rayon ne rend qu'une face par impact ; là où deux volumes se touchent — le
        dessous d'une dalle sur le dessus du remblai — l'autre face, à la même distance,
        serait sautée. On relève donc toutes les faces qui passent par le point touché,
        une par plan et par objet : les deux triangles d'un même carré ne comptent qu'une fois.
        """
        depart, restant = Vector(origine), portee
        while restant > 0:
            point, normale, index, distance = self.bvh.ray_cast(depart, direction, restant)
            if point is None:
                break
            faces = {}
            for lieu, nrm, idx, _ in self.bvh.find_nearest_range(point, EPS):
                if abs(nrm.dot(point - lieu)) > COPLANAIRE:
                    continue
                cle = (self.sources[idx], round(nrm.x, 3), round(nrm.y, 3), round(nrm.z, 3))
                faces.setdefault(cle, (point, nrm, idx))
            yield list(faces.values()) or [(point, normale, index)]
            restant -= distance + EPS
            depart = point + direction * EPS

    def descente(self, x, y, z_bas):
        """Descend du ciel et dit, pour chaque paquet de faces, si on l'aborde et si on le quitte à l'air libre.

        Chaque volume fermé se compte à part : on est dedans après un nombre impair de ses
        faces, quel que soit le sens de ses normales. Les maillages ouverts — une flamme,
        une nappe d'eau — ne comptent pas : ils n'enferment rien.
        """
        self.dedans = set()
        for paquet in self.paquets((x, y, Z_HAUT), BAS, Z_HAUT - z_bas):
            avant = not self.dedans
            for _, _, index in paquet:
                source = self.sources[index]
                if self.fermes[source]:
                    self.dedans ^= {source}
            yield paquet, avant, not self.dedans

    def dans_un_volume(self, x, y, z):
        libre = True
        for paquet, _, apres in self.descente(x, y, z):
            if paquet[0][0].z < z:
                break
            libre = apres
        return not libre


# --- la grille -----------------------------------------------------------------

def sols(rayons, x, y):
    """Les sols superposés d'une case, du plus haut au plus bas.

    Un sol n'en est un que touché à l'air libre — pas le dallage qui continue sous un mur
    ou dans la tour d'une mesiba — et sous un plafond assez haut pour s'y tenir debout : le
    remblai des cours est fait de dalles superposées qui laissent entre elles des creux
    d'une coudée. Deux faces à la même hauteur se jugent avant d'être comptées : le dessus
    d'une dalle sous le pied d'un mur est dedans, pas dessus.
    """
    niveaux, plafond = [], None
    for paquet, avant, apres in rayons.descente(x, y, Z_BAS):
        if avant:
            for point, normale, index in paquet:
                if normale.z > PENTE_SOL and (plafond is None or plafond - point.z >= HAUTEUR_HOMME) \
                        and not (niveaux and abs(niveaux[-1][0] - point.z) < EPS):
                    niveaux.append((point.z, index))
        elif apres:
            plafond = paquet[0][0].z
        if len(niveaux) == NIVEAUX:
            break
    return niveaux


def cible(niveaux, h):
    """Le sol que le rayon de solEn trouve depuis h : le plus haut sous h + MONTEE, à moins de CHUTE."""
    candidats = [n for n in niveaux if h - CHUTE - 1e-6 <= n[0] <= h + MONTEE + 1e-6]
    return max(candidats, key=lambda n: n[0]) if candidats else None


def mur(rayons, x, y, h, direction, pas):
    for hauteur in HAUTEURS_GARDE:
        touche = rayons.premier((x, y, h + hauteur), direction, pas + GARDE)
        if touche is not None:
            return touche[2]
    return None


class Zones:
    def __init__(self, n):
        self.parent = list(range(n))

    def racine(self, a):
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def unir(self, a, b):
        ra, rb = self.racine(a), self.racine(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def nom_court(nom):
    return re.sub(r"(\.\d+|_\d+)+$", "", nom)


def plus_proche(niveaux, h):
    return min(range(len(niveaux)), key=lambda k: abs(niveaux[k][0] - h))


def passage(rayons, depuis, k, vers, x, y, direction, pas):
    """(niveau atteint, None) si le pas passe ; sinon (None, raison)."""
    h = depuis[k][0]
    but = cible(vers, h)
    if but is None:
        return None, "dénivelé"
    obstacle = mur(rayons, x, y, h, direction, pas)
    if obstacle is not None:
        return None, obstacle
    return vers.index(but), None


def analyser(rayons, noms, zone, pas):
    x0, x1, y0, y1 = (v * AMA for v in zone)
    nx, ny = int((x1 - x0) / pas) + 1, int((y1 - y0) / pas) + 1
    # Au centre des cases : une ama fait quatre cases, et une grille posée sur les bords
    # tomberait exactement sur les arêtes des volumes, où un rayon touche ou non au hasard.
    xs, ys = x0 + (np.arange(nx) + 0.5) * pas, y0 + (np.arange(ny) + 0.5) * pas
    print(f"grille {nx} × {ny} cases de {pas} m")

    debut = time.time()
    grille = {}
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            niveaux = sols(rayons, x, y)
            if niveaux:
                grille[(i, j)] = niveaux
    print(f"  sols : {len(grille)} cases posées en {time.time() - debut:.0f} s")

    debut = time.time()
    zones = Zones(nx * ny * NIVEAUX)
    noeud = lambda i, j, k: (i * ny + j) * NIVEAUX + k
    refus = []
    # Les diagonales aussi : dans une vis, deux degrés qui se suivent ne se touchent
    # parfois que par un coin de case, et le marcheur, lui, va dans tous les sens.
    voisinages = [(di, dj, Vector((di, dj, 0.0)).normalized(), pas * math.hypot(di, dj))
                  for di, dj in ((1, 0), (0, 1), (1, 1), (1, -1))]
    for (i, j), niveaux in grille.items():
        for di, dj, direction, distance in voisinages:
            voisins = grille.get((i + di, j + dj))
            if not voisins:
                continue
            xa, ya, xb, yb = xs[i], ys[j], xs[i + di], ys[j + dj]
            for k, (h, _) in enumerate(niveaux):
                if not any(abs(hv - h) <= VOISINAGE for hv, _ in voisins):
                    continue
                aller = passage(rayons, niveaux, k, voisins, xa, ya, direction, distance)
                if aller[0] is not None:
                    kb = aller[0]
                    retour = passage(rayons, voisins, kb, niveaux, xb, yb, -direction, distance)
                    if retour[0] == k:
                        zones.unir(noeud(i, j, k), noeud(i + di, j + dj, kb))
                    else:
                        refus.append((noeud(i + di, j + dj, kb), noeud(i, j, k), "sens unique", xb, yb, voisins[kb][0], h))
                    continue
                kb = plus_proche(voisins, h)
                raison, hb = aller[1], voisins[kb][0]
                # Le sol voisin qui prolonge un autre étage de la même case n'est pas une
                # frontière : c'est la cave, ou le toit, qui se poursuit sous le pas.
                if any(abs(hc - hb) <= MONTEE for kc, (hc, _) in enumerate(niveaux) if kc != k):
                    continue
                if raison == "dénivelé":
                    raison = "marche" if hb > h else "vide"
                    # Un vide d'une case suivi d'un sol à hauteur de pas : une fente, que le
                    # pied enjamberait. Le refus est rapporté vers le sol d'en face.
                    au_dela = grille.get((i + 2 * di, j + 2 * dj))
                    if raison == "vide" and au_dela and cible(au_dela, h) is not None:
                        kc = au_dela.index(cible(au_dela, h))
                        refus.append((noeud(i, j, k), noeud(i + 2 * di, j + 2 * dj, kc), "fente", xa, ya, h, au_dela[kc][0]))
                        continue
                    # Une marche dont le pied est dans un volume est le flanc d'un objet posé
                    # sur le sol voisin — une jarre, un pilier —, pas un sol à atteindre.
                    if raison == "marche" and rayons.dans_un_volume(xa, ya, hb + 0.3):
                        continue
                refus.append((noeud(i, j, k), noeud(i + di, j + dj, kb), raison, xa, ya, h, hb))
    print(f"  passages : {len(refus)} refus en {time.time() - debut:.0f} s")

    return Resultat(grille, zones, refus, noeud, xs, ys, rayons.sources, noms)


class Resultat:
    def __init__(self, grille, zones, refus, noeud, xs, ys, sources, noms):
        self.grille, self.zones, self.refus, self.noeud = grille, zones, refus, noeud
        self.xs, self.ys, self.sources, self.noms = xs, ys, sources, noms
        self.pas = xs[1] - xs[0]
        self.compter()

    def nom_face(self, index):
        return nom_court(self.noms[self.sources[index]])

    def compter(self):
        cases, bornes, hauteurs, sols = Counter(), {}, defaultdict(list), defaultdict(Counter)
        self.racine_de = {}
        for (i, j), niveaux in self.grille.items():
            for k, (h, index) in enumerate(niveaux):
                r = self.zones.racine(self.noeud(i, j, k))
                self.racine_de[self.noeud(i, j, k)] = r
                cases[r] += 1
                x, y = self.xs[i], self.ys[j]
                b = bornes.setdefault(r, [x, x, y, y])
                b[0], b[1], b[2], b[3] = min(b[0], x), max(b[1], x), min(b[2], y), max(b[3], y)
                hauteurs[r].append(h)
                sols[r][self.nom_face(index)] += 1
        self.rang = {r: n + 1 for n, (r, _) in enumerate(cases.most_common())}
        self.cases, self.bornes, self.hauteurs, self.sols = cases, bornes, hauteurs, sols

    def zone(self, noeud):
        return self.rang[self.racine_de[noeud]]

    def est_un_lieu(self, racine):
        """Assez de cases, et pas une lamelle d'une case le long d'une arête où la grille tombe."""
        b = self.bornes[racine]
        return self.cases[racine] >= CASES_MIN and b[1] - b[0] >= 0.3 and b[3] - b[2] >= 0.3

    def etages(self, x, y):
        """Les sols d'un point en mètres Blender : (hauteur, nom, zone) du plus haut au plus bas."""
        i, j = round((x - self.xs[0]) / self.pas), round((y - self.ys[0]) / self.pas)
        return [(h, self.nom_face(index), self.zone(self.noeud(i, j, k)))
                for k, (h, index) in enumerate(self.grille.get((i, j), []))]

    def frontieres(self):
        """Les refus entre deux lieux distincts, groupés par (de, vers, raison)."""
        groupes = defaultdict(list)
        for a, b, raison, x, y, ha, hb in self.refus:
            ra, rb = self.racine_de[a], self.racine_de[b]
            if ra == rb or not self.est_un_lieu(ra) or not self.est_un_lieu(rb):
                continue
            motif = raison if raison in ("marche", "vide", "fente", "sens unique") else f"garde : {self.nom_face(raison)}"
            groupes[(self.rang[ra], self.rang[rb], motif)].append((x, y, ha, hb))
        return groupes

    def entrees(self):
        """(id, zone, sol) de chaque entrée du menu « Aller à… » qui donne sa position."""
        reperes = json.loads((DOSSIER / "visite" / "reperes.json").read_text())
        for entree in reperes["entrees"]:
            if "position" not in entree:
                continue
            px, py, pz = entree["position"]
            etages = self.etages(px, -pz)
            if etages:
                h, _, zone = min(etages, key=lambda e: abs(e[0] - py))
                yield entree["id"], zone, h

    def lieux(self):
        """Pour chaque concept où l'on se tient, les sols superposés au centre de son emprise."""
        concepts = json.loads((DOSSIER / "visite" / "concepts.json").read_text())["concepts"]
        emprises = json.loads((DOSSIER / "visite" / "reperes.json").read_text())["emprises"]
        for concept in concepts:
            if not concept.get("lieu") or concept["id"] not in emprises:
                continue
            e = emprises[concept["id"]]
            x, y = (e["min"][0] + e["max"][0]) / 2, -(e["min"][2] + e["max"][2]) / 2
            yield concept["id"], x, y, self.etages(x, y)

    def zones_visitees(self):
        """Les zones où se tient une entrée ou un lieu : celles que le rapport retient."""
        zones = {zone for _, zone, _ in self.entrees()}
        for _, _, _, etages in self.lieux():
            zones.update(zone for _, _, zone in etages)
        return zones

    def decrire_zones(self, retenues):
        print("\nzones d'un seul tenant (cases, m², bornes et sols en amot, ce qu'on foule)")
        ecartees = 0
        for r, n in self.cases.most_common():
            if self.rang[r] not in retenues:
                ecartees += self.est_un_lieu(r)
                continue
            b = [v / AMA for v in self.bornes[r]]
            hs = self.hauteurs[r]
            foule = ", ".join(f"{nom} {c * 100 // n}%" for nom, c in self.sols[r].most_common(3))
            print(f"  #{self.rang[r]:<4d} {n:7d} {n * self.pas * self.pas:8.1f} m²  x {b[0]:7.1f}..{b[1]:7.1f}  y {b[2]:7.1f}..{b[3]:7.1f}"
                  f"  z {min(hs) / AMA:6.1f}..{max(hs) / AMA:6.1f}  {foule}")
        if ecartees:
            print(f"  … et {ecartees} zones sans lieu ni entrée : socles, cuves, toits, creux du remblai")

    def decrire_frontieres(self, groupes, retenues):
        print("\nfrontières refusées (de → vers : pas refusés, dénivelé moyen, un point en amot)")
        for (za, zb, motif), points in sorted(groupes.items(), key=lambda kv: -len(kv[1])):
            if za not in retenues or zb not in retenues:
                continue
            xm = sum(p[0] for p in points) / len(points) / AMA
            ym = sum(p[1] for p in points) / len(points) / AMA
            dh = sum(p[3] - p[2] for p in points) / len(points)
            print(f"  #{za:<4d} → #{zb:<4d} {len(points):6d} pas   dénivelé {dh:+6.2f} m   vers ({xm:7.1f}, {ym:7.1f})   {motif}")

    def decrire_entrees(self):
        print("\nentrées du menu « Aller à… » et leur zone")
        for ident, zone, h in self.entrees():
            print(f"  {ident:24s} zone #{zone}  sol {h / AMA:6.1f} amot")

    def decrire_lieux(self):
        print("\nlieux : les sols au centre de l'emprise, du plus haut au plus bas (amot → zone)")
        for ident, x, y, etages in self.lieux():
            colonne = "   ".join(f"{h / AMA:6.1f} → #{zone}" for h, _, zone in etages)
            print(f"  {ident:28s} ({x / AMA:7.1f}, {y / AMA:7.1f})  {colonne or 'hors grille'}")

    def decrire_points(self, points, rayons):
        """Les sols retenus au point, puis toute la colonne de faces que le rayon y traverse."""
        if not points:
            return
        print("\npoints demandés : les sols superposés (amot, ce qu'on foule, zone), puis la colonne traversée")
        for x, y in points:
            colonne = "   ".join(f"{h / AMA:6.2f} {nom} #{zone}" for h, nom, zone in self.etages(x * AMA, y * AMA))
            print(f"  ({x:7.1f}, {y:7.1f})  {colonne or 'aucun sol'}")
            for paquet, avant, apres in rayons.descente(x * AMA + CHEVEU, y * AMA + CHEVEU, Z_BAS):
                faces = ", ".join(f"{self.nom_face(index)} {'▲' if normale.z > 0 else '▼'}" for _, normale, index in paquet)
                etat = "air" if apres else "dedans : " + ", ".join(nom_court(self.noms[src]) for src in rayons.dedans)
                print(f"      {paquet[0][0].z / AMA:8.2f}  {faces}  → {etat}")

    def image(self, chemin):
        nx, ny = len(self.xs), len(self.ys)
        pixels = np.zeros((ny, nx, 4), dtype=np.float32)
        pixels[..., 3] = 1.0
        for (i, j), niveaux in self.grille.items():
            rang = self.zone(self.noeud(i, j, 0))
            teinte = (rang * 0.6180339887) % 1.0
            pixels[j, i, :3] = colorsys.hsv_to_rgb(teinte, 0.55 if rang > 1 else 0.15, 0.95 if rang > 1 else 0.85)
        image = bpy.data.images.new("marche", nx, ny, alpha=True)
        image.pixels.foreach_set(pixels.ravel())
        image.filepath_raw = str(chemin)
        image.file_format = "PNG"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        image.save()
        print(f"\nplan des zones : {chemin}")


def main():
    args = arguments()
    zone = tuple(float(v) for v in option(args, "--zone", 4, ZONE_DEFAUT))
    pas = float(option(args, "--pas", 1, SOUS_PAS))
    chemin = DOSSIER / option(args, "--image", 1, "renders/marche/marche.png")
    points = [float(v) for v in args[args.index("--ou") + 1:]] if "--ou" in args else []
    points = list(zip(points[0::2], points[1::2]))

    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = lc.name not in COLLECTIONS
    depsgraph = bpy.context.evaluated_depsgraph_get()
    debut = time.time()
    sommets, triangles, sources, noms, fermes = murs(depsgraph, prefixes_traversables())
    rayons = Rayons(arbre(sommets, triangles), sources, fermes)
    print(f"{len(noms)} volumes dont {len(noms) - sum(fermes)} ouverts, {len(triangles)} triangles, "
          f"arbre en {time.time() - debut:.0f} s")

    resultat = analyser(rayons, noms, zone, pas)
    groupes = resultat.frontieres()
    retenues = set(resultat.rang.values()) if "--tout" in args else resultat.zones_visitees()
    resultat.decrire_zones(retenues)
    resultat.decrire_frontieres(groupes, retenues)
    resultat.decrire_entrees()
    resultat.decrire_lieux()
    resultat.decrire_points(points, rayons)
    resultat.image(chemin)


if __name__ == "__main__":
    main()
