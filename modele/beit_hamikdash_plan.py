"""$BLENDER -b modele/beit_hamikdash.blend -P modele/beit_hamikdash_plan.py — dessine le plan de la visite, à plat.

Une carte comme on en lit en ville : des aplats par catégorie — esplanade, cours, bâti, sanctuaire, murs —,
pas une photographie d'en haut. Un rayon par tiers de mètre tombe à la verticale sur la scène ; ce qu'il touche
d'abord dit la catégorie, un filtre de majorité efface ce qui est plus petit qu'un pas, et chaque catégorie
devient des polygones simplifiés. Autour, la vieille ville d'OpenStreetMap (`pays/`) et ses murailles.
"""
import json
import math
import pathlib
import re
import sys
import time
from typing import NamedTuple

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

MODELE = pathlib.Path(bpy.data.filepath).resolve().parent
sys.path.insert(0, str(MODELE))
from blockout.pays.calage import PAYS_DONNEES, PAYS_DOSSIER, vers_scene  # noqa: E402
from blockout.primitives.parametres import AMA  # noqa: E402

SORTIE = MODELE.parent / "visite" / "plan.json"
EMPRISES = json.loads((MODELE.parent / "visite" / "reperes.json").read_text())["emprises"]
CONCEPTS = json.loads((MODELE.parent / "visite" / "concepts.json").read_text())["concepts"]
LIEUX = [c["id"] for c in CONCEPTS if c.get("lieu")]
PAS = 3.0                    # rayons par mètre
TOLERANCE = 0.25             # m : écart permis au contour simplifié
AIRE_MIN = 1.0               # m² : plus petit, un contour ne se dessine pas
HAUT_DU_CIEL = 400.0
PENTE_MAX = 0.25             # composante verticale de la normale au-delà de laquelle une face est un dessus ou un dessous
BAS_DU_MONDE = -200.0
# En mètres, dans le repère du glb : x vers l'est, z vers le sud. `releve` : ce que les rayons couvrent,
# le Temple et la place du Kotel ; `bornes` : jusqu'où la carte se déplace, la vieille ville autour.
RELEVE = dict(x=(-345.0, 170.0), z=(-300.0, 400.0))
BORNES = dict(x=(-420.0, 240.0), z=(-360.0, 460.0))
CACHEES = {"77_Fumee", "70_Kelim", "65_Aron", "99_Outils", "91_Lumiere", "90_Cameras", "01_Pays"}

# L'ordre de dessin, du dessous au dessus.
CATEGORIES = ["esplanade", "place", "cour", "jardin", "eau", "autel", "bati", "moderne", "sanctuaire", "mur"]
PAR_CONCEPT = {
    "esplanade_herode": "esplanade", "sol_har_habayit": "esplanade", "heil": "esplanade", "soreg": "esplanade",
    "place_kotel": "place", "pont_maghrebins": "moderne", "porat_yosef": "moderne",
    "mur_herode": "mur", "mur_har_habayit": "mur", "kotel": "mur", "arche_wilson": "mur",
    "portiques": "bati", "gezuztra": "bati", "kippa_beit_hamoked": "bati",
    "azara": "cour", "ezrat_nashim": "cour", "ezrat_israel": "cour", "quinze_marches": "cour", "doukhan": "cour",
    "douze_marches_oulam": "cour", "beit_hamitbahayim": "cour", "yam": "eau",
}
PAR_ZONE = {"mizbeach": "autel", "heikhal": "sanctuaire", "oulam": "sanctuaire", "kodesh_hakodashim": "sanctuaire", "lishkot": "bati"}
PAR_COLLECTION = {"00_HarHabayit": "esplanade", "10_EzratNashim": "cour", "20_Azara": "cour", "80_Lishkot": "bati",
                  "30_Mizbeach": "autel", "40_Ulam": "sanctuaire", "50_Heikhal": "sanctuaire", "60_KodeshHakodashim": "sanctuaire"}
# Le mobilier ne fait pas la carte : ce qu'il couvre prend la catégorie d'alentour.
MOBILIER = re.compile(r"banc|siege|pupitre|gradin|dossier|marchepied|Candelabre|Anneau|Table_|Pilier_|Escalier_Korban"
                      r"|vasque|robinet|rinceaux|netilat|Mekhona|Kiyor|poubelle|etagere")
JARDIN = re.compile(r"jardin|palmier|Olivier|capriers")
MODERNE = re.compile(r"^(Aish_HaTorah|Beit_HaLiba|Fondation_du_Kotel|Arret_bus|Kotel_controle|Kotel_voiture|Kotel_falaise"
                     r"|Kotel_nord|Makhkama)")
PLACE = re.compile(r"^Kotel_(place|rampe)")
# Le soutènement de la place est la marche vers le quartier juif : la ville, pas le Temple.
VILLE = re.compile(r"^Kotel_place_soutenement")
MUR = re.compile(r"couronnement|_mur|creneaux|bandeau|parapet")

# Les coupes : sous `coupe`, un rayon parti de l'intérieur d'un mur en touche le dessous et le dit tranché.
NIVEAUX = [
    dict(id="heikhal", coupe=4.5, x=(-88.0, -33.0), z=(-27.0, 27.0), pas=6.0, dans="sanctuaire",
         lieux=["oulam", "heikhal", "kodesh_hakodashim", "taim", "mesiba", "douze_marches_oulam"]),
    dict(id="sous_terrain", coupe=-6.0, plancher=-8.0, x=(-95.0, 5.0), z=(-51.0, 44.0), pas=4.0, souterraine=True,
         lieux=["mesiba_bira", "beit_hatevila", "shit"],
         # Bâti en surface, il descend aux tunnels : vu du plan de surface, il commence au-dessus d'eux.
         acces=["beit_hamoked"]),
]


def vers_la_visite(est, nord):
    x, y = vers_scene(est, nord)
    return x * AMA, -y * AMA


def categorie(nom, collection, prefixes):
    if MOBILIER.search(nom):
        return None
    if VILLE.search(nom):
        return "ville"
    for motif, valeur in ((JARDIN, "jardin"), (MODERNE, "moderne"), (PLACE, "place")):
        if motif.search(nom):
            return valeur
    concept, zone = next(((c, z) for p, c, z in prefixes if nom.startswith(p)), (None, None))
    if MUR.search(nom) and zone not in ("heikhal", "oulam", "kodesh_hakodashim") and concept != "portiques":
        return "mur"
    if concept in PAR_CONCEPT:
        return PAR_CONCEPT[concept]
    if zone in PAR_ZONE:
        return PAR_ZONE[zone]
    if concept and concept.startswith(("lishkat", "beit_", "shaar", "portes", "porte")):
        return "bati"
    return PAR_COLLECTION.get(collection)


class Scene(NamedTuple):
    arbre: BVHTree          # tous les triangles
    dessus: BVHTree         # ceux tournés vers le haut
    dessous: BVHTree        # ceux tournés vers le bas
    categories: np.ndarray  # par triangle de `arbre`, l'indice de sa catégorie (-1 : mobilier)
    lieux: np.ndarray       # par triangle de `arbre`, l'indice de son lieu dans LIEUX (-1 : aucun)


def scene_a_plat():
    """Les triangles visibles en arbres. Deux faces qui coïncident — le dessous d'une dalle sur le dessus d'une
    autre — ne sortent d'un même arbre qu'une fois : rangées par sens, elles ne se masquent plus."""
    prefixes = sorted(((p, c["id"], c["zone"]) for c in CONCEPTS for p in c["prefixes"]), key=lambda t: -len(t[0]))
    graphe = bpy.context.evaluated_depsgraph_get()
    sommets, triangles, categories, lieux = [], [], [], []
    decalage = 0
    for collection in bpy.context.scene.collection.children:
        if collection.name in CACHEES:
            continue
        for objet in collection.all_objects:
            if objet.type != "MESH" or objet.hide_render:
                continue
            evalue = objet.evaluated_get(graphe)
            maillage = evalue.to_mesh()
            maillage.calc_loop_triangles()
            n, t = len(maillage.vertices), len(maillage.loop_triangles)
            if n and t:
                co = np.empty(n * 3, np.float32)
                maillage.vertices.foreach_get("co", co)
                monde = np.array(objet.matrix_world, np.float32)
                sommets.append(co.reshape(-1, 3) @ monde[:3, :3].T + monde[:3, 3])
                tri = np.empty(t * 3, np.int32)
                maillage.loop_triangles.foreach_get("vertices", tri)
                triangles.append(tri.reshape(-1, 3) + decalage)
                c = categorie(objet.name, collection.name, prefixes)
                categories.append(np.full(t, -1 if c is None else ([*CATEGORIES, "ville"].index(c)), np.int16))
                concept = next((c for p, c, _ in prefixes if objet.name.startswith(p)), None)
                lieux.append(np.full(t, LIEUX.index(concept) if concept in LIEUX else -1, np.int16))
                decalage += n
            evalue.to_mesh_clear()
    sommets, triangles = np.concatenate(sommets), np.concatenate(triangles)
    a, b, c = (sommets[triangles[:, k]] for k in range(3))
    normales = np.cross(b - a, c - a)
    verticale = normales[:, 2] / np.maximum(np.linalg.norm(normales, axis=1), 1e-12)
    liste = sommets.tolist()

    def arbre(choix):
        return BVHTree.FromPolygons(liste, triangles[choix].tolist(), all_triangles=True)

    return Scene(arbre(slice(None)), arbre(verticale > PENTE_MAX), arbre(verticale < -PENTE_MAX),
                 np.concatenate(categories), np.concatenate(lieux))


def releve(arbre, x, z, pas):
    """La face que chaque rayon tombé du ciel touche d'abord (-1 : rien), rangée 0 au nord."""
    nx, nz = round((x[1] - x[0]) * pas), round((z[1] - z[0]) * pas)
    faces = np.full((nz, nx), -1, np.int32)
    bas = Vector((0.0, 0.0, -1.0))
    for j in range(nz):
        zv = z[0] + (j + 0.5) / pas
        for i in range(nx):
            _, _, face, _ = arbre.ray_cast(Vector((x[0] + (i + 0.5) / pas, -zv, HAUT_DU_CIEL)), bas)
            if face is not None:
                faces[j, i] = face
    return faces


def majorite(carte, valeurs, rayon=1):
    """Chaque pixel prend la valeur la plus fréquente autour de lui (fenêtre carrée)."""
    meilleure, compte = np.full_like(carte, -2), np.zeros(carte.shape, np.int32)
    garni = np.pad(carte, rayon, constant_values=-2)
    for v in valeurs:
        s = np.pad((garni == v).astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        k = 2 * rayon + 1
        n = s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]
        plus = n > compte
        meilleure[plus], compte[plus] = v, n[plus]
    return meilleure


def voisins(masque, rayon):
    """Combien de pixels du masque dans la fenêtre carrée de chaque pixel."""
    k = 2 * rayon + 1
    s = np.pad(np.pad(masque, rayon).astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]


def fermer(masque, rayon):
    """Comble les jours plus étroits que 2 × rayon : les créneaux d'une crête font un mur d'un tenant."""
    dilate = voisins(masque, rayon) > 0
    return voisins(~dilate, rayon) == 0


def ouvrir(masque, rayon):
    """Efface ce qui est plus mince que 2 × rayon : les reliefs d'une paroi n'en sont pas l'épaisseur."""
    erode = voisins(~masque, rayon) == 0
    return voisins(erode, rayon) > 0


def combler(carte, valeurs):
    """Le mobilier prend la catégorie de ses voisins, de proche en proche."""
    for _ in range(12):
        trous = carte == -1
        if not trous.any():
            break
        carte = np.where(trous, majorite(np.where(trous, -3, carte), valeurs), carte)
    return carte


# Directions (ligne, colonne), ligne vers le sud ; on longe le bord le dedans à droite.
def contours(masque):
    """Les bords d'un masque en anneaux de coins de pixels (ligne, colonne), trous compris."""
    p = np.pad(masque, 1)
    dedans = p[1:-1, 1:-1]
    suivants = {}
    largeur = masque.shape[1] + 1

    def aretes(m, de, a):
        l, c = np.nonzero(m)
        for d0, d1, a0, a1 in zip(l + de[0], c + de[1], l + a[0], c + a[1]):
            suivants.setdefault(int(d0) * largeur + int(d1), []).append(int(a0) * largeur + int(a1))

    aretes(dedans & ~p[:-2, 1:-1], (0, 0), (0, 1))     # bord nord, vers l'est
    aretes(dedans & ~p[1:-1, 2:], (0, 1), (1, 1))      # bord est, vers le sud
    aretes(dedans & ~p[2:, 1:-1], (1, 1), (1, 0))      # bord sud, vers l'ouest
    aretes(dedans & ~p[1:-1, :-2], (1, 0), (0, 0))     # bord ouest, vers le nord
    anneaux = []
    while suivants:
        depart = next(iter(suivants))
        anneau, courant, venu = [], depart, None
        while True:
            options = suivants[courant]
            if len(options) > 1 and venu is not None:
                # Deux pixels qui ne se touchent que par un coin restent séparés : on tourne à droite.
                dl, dc = venu
                droite = (courant // largeur + dc, courant % largeur - dl)
                cible = droite[0] * largeur + droite[1]
                suivant = cible if cible in options else options[0]
            else:
                suivant = options[0]
            options.remove(suivant)
            if not options:
                del suivants[courant]
            anneau.append(courant)
            venu = (suivant // largeur - courant // largeur, suivant % largeur - courant % largeur)
            courant = suivant
            if courant == depart and depart not in suivants:
                break
        anneaux.append(np.array([(v // largeur, v % largeur) for v in anneau], np.float64))
    return anneaux


def simplifier(points, tolerance):
    """Douglas-Peucker sur un anneau fermé."""
    if len(points) < 4:
        return points
    loin = int(np.argmax(((points - points[0]) ** 2).sum(1)))
    garder = np.zeros(len(points), bool)
    garder[[0, loin]] = True
    pile = [(0, loin), (loin, len(points))]
    while pile:
        a, b = pile.pop()
        if b - a < 2:
            continue
        p0, p1 = points[a], points[b % len(points)]
        milieu = points[a + 1:b]
        d = p1 - p0
        longueur = math.hypot(*d)
        ecarts = np.abs(d[0] * (milieu[:, 1] - p0[1]) - d[1] * (milieu[:, 0] - p0[0])) / longueur if longueur else \
            np.hypot(*(milieu - p0).T)
        k = int(np.argmax(ecarts))
        if ecarts[k] > tolerance:
            garder[a + 1 + k] = True
            pile += [(a, a + 1 + k), (a + 1 + k, b)]
    return points[garder]


def aire(anneau):
    l, c = anneau[:, 0], anneau[:, 1]
    return abs(np.dot(c, np.roll(l, -1)) - np.dot(l, np.roll(c, -1))) / 2


def chemin(anneaux):
    return "".join("M" + "L".join(f"{x:.1f} {z:.1f}" for x, z in a) + "Z" for a in anneaux)


def vectoriser(carte, x, z, pas, categories):
    """Une couche par catégorie, du dessous au dessus ; chacune déborde d'un pas sous celles qui la recouvrent, sans jour entre elles."""
    couches = []
    for k, nom in enumerate(categories):
        masque = carte == k
        if not masque.any():
            continue
        garni = np.pad(masque, 1)
        voisin = garni[:-2, 1:-1] | garni[2:, 1:-1] | garni[1:-1, :-2] | garni[1:-1, 2:]
        masque = masque | (voisin & (carte > k))
        anneaux = []
        for anneau in contours(masque):
            if aire(anneau) < AIRE_MIN * pas * pas:
                continue
            simple = simplifier(anneau, TOLERANCE * pas)
            anneaux.append(np.stack([x[0] + simple[:, 1] / pas, z[0] + simple[:, 0] / pas], 1))
        couches.append(dict(categorie=nom, d=chemin(anneaux)))
    return couches


def plan_de_surface(faces, categories):
    carte = np.where(faces >= 0, categories[faces], -2).astype(np.int16)   # -2 : rien, -1 : mobilier
    valeurs = range(-2, len(CATEGORIES) + 1)
    carte = combler(carte, valeurs)
    carte = majorite(majorite(carte, valeurs), valeurs)
    mur = CATEGORIES.index("mur")
    carte[fermer(carte == mur, 3) & (carte < mur) & (carte >= 0)] = mur
    # Un jour de quelques pas dans un sol (bouche, regard) n'est pas un vide de la carte.
    vide = carte == -2
    carte[vide] = majorite(carte, valeurs, rayon=4)[vide]
    carte[carte == len(CATEGORIES)] = -2               # la ville : OpenStreetMap la dessine
    return carte, vectoriser(carte, RELEVE["x"], RELEVE["z"], PAS, CATEGORIES)


def traversees(arbre, origine, direction):
    """Les cotes de toutes les faces de `arbre` que la verticale traverse depuis `origine`."""
    cotes, point = [], origine.copy()
    while True:
        touche, _, face, _ = arbre.ray_cast(point, direction)
        if face is None:
            return cotes
        cotes.append(touche.z)
        point = touche + direction * 1e-4


def airs(scene, x, y):
    """Les vides de la verticale, (sol, plafond) — l'algorithme de `solsLibres` (visite/marche.js) : un dessus franchi
    en descendant fait entrer dans la matière, un dessous en fait sortir. Un rayon seul, de la coupe, se trompait
    sur les planchers des ta'im qui entrent dans le mur du Heikhal."""
    faces = sorted([(c, 1) for c in traversees(scene.dessus, Vector((x, y, HAUT_DU_CIEL)), Vector((0.0, 0.0, -1.0)))]
                   + [(c, -1) for c in traversees(scene.dessous, Vector((x, y, BAS_DU_MONDE)), Vector((0.0, 0.0, 1.0)))],
                   reverse=True)
    vides, profondeur, plafond = [], 0, math.inf
    for cote, sens in faces:
        if sens < 0:
            profondeur = max(0, profondeur - 1)
            if profondeur == 0:
                plafond = cote
            continue
        if profondeur == 0:
            vides.append((cote, plafond))
        profondeur += 1
    return vides


def coupe_a(scene, x, z, pas, hauteur):
    """À `hauteur`, pixel par pixel : la cote du sol du vide où l'on est (NaN dans la matière), et s'il a un plafond."""
    nx, nz = round((x[1] - x[0]) * pas), round((z[1] - z[0]) * pas)
    sol = np.full((nz, nx), np.nan, np.float32)
    couvert = np.zeros((nz, nx), bool)
    for j in range(nz):
        zv = z[0] + (j + 0.5) / pas
        for i in range(nx):
            vide = next(((s, p) for s, p in airs(scene, x[0] + (i + 0.5) / pas, -zv) if s <= hauteur < p), None)
            if vide:
                sol[j, i], couvert[j, i] = vide[0], vide[1] < math.inf
    return sol, np.isnan(sol), couvert


def dans_les_lieux(lieux, x, z, pas, marge=0.5):
    """Les pixels que couvre l'emprise d'un des lieux, à `marge` près."""
    xs = x[0] + (np.arange(round((x[1] - x[0]) * pas)) + 0.5) / pas
    zs = z[0] + (np.arange(round((z[1] - z[0]) * pas)) + 0.5) / pas
    dedans = np.zeros((len(zs), len(xs)), bool)
    for lieu in lieux:
        e = EMPRISES[lieu]
        dedans |= (((zs >= e["min"][2] - marge) & (zs <= e["max"][2] + marge))[:, None]
                   & ((xs >= e["min"][0] - marge) & (xs <= e["max"][0] + marge))[None, :])
    return dedans


def points_d_etiquette(faces, lieux):
    """Pour chaque lieu vu d'en haut, où poser son nom : au large de ses bords — à mi-chemin du point le plus dégagé —,
    au plus près de son centre. Le plus dégagé seul tombait, dans l'Azara, derrière le Kodesh HaKodashim."""
    vus = np.where(faces >= 0, lieux[faces], -1)
    points = {}
    for k in np.unique(vus[vus >= 0]):
        lignes, colonnes = np.nonzero(vus == k)
        l0, c0 = lignes.min(), colonnes.min()
        # Bordé de dehors : sans lui, un lieu qui remplit son cadre ne s'éroderait jamais.
        masque = np.pad(vus[l0:lignes.max() + 1, c0:colonnes.max() + 1] == k, 1)
        l0, c0 = l0 - 1, c0 - 1
        if masque.sum() < AIRE_MIN * PAS * PAS:
            continue
        lc, cc = np.nonzero(masque)
        centre = lc.mean(), cc.mean()
        erosions = [masque]
        while (erode := voisins(~erosions[-1], 1) == 0).any():
            erosions.append(erode)
        l, c = np.nonzero(erosions[len(erosions) // 2])
        i = int(np.argmin((l - centre[0]) ** 2 + (c - centre[1]) ** 2))
        points[LIEUX[int(k)]] = [round(RELEVE["x"][0] + (c0 + c[i] + 0.5) / PAS, 1),
                                 round(RELEVE["z"][0] + (l0 + l[i] + 0.5) / PAS, 1)]
    return points


def plan_de_coupe(scene, niveau, surface):
    """Sous la coupe d'un bâtiment, ses murs tranchés et son sol ; sous terre, les seuls tunnels."""
    x, z, pas = niveau["x"], niveau["z"], niveau["pas"]
    sol, plein, couvert = coupe_a(scene, x, z, pas, niveau["coupe"])
    coupe = np.full(sol.shape, -2, np.int16)
    if niveau.get("souterraine"):
        # Sous un plafond, et dans un lieu du niveau : ni l'esplanade à ciel ouvert, ni le vide sous une dalle.
        # Le massif plein ne se dessine pas : les tunnels se lisent sur le plan de surface pâli.
        libre = ~plein & (sol > niveau["plancher"]) & couvert & dans_les_lieux(niveau["lieux"], x, z, pas)
        coupe[libre] = 0
    else:
        # Sous son toit seulement, ailleurs c'est le plan de surface ; ce qui n'y est pas mur tranché est sol.
        lignes = ((np.arange(sol.shape[0]) + 0.5) / pas + z[0] - RELEVE["z"][0]) * PAS
        colonnes = ((np.arange(sol.shape[1]) + 0.5) / pas + x[0] - RELEVE["x"][0]) * PAS
        sous_le_toit = surface[lignes.astype(int)][:, colonnes.astype(int)] == CATEGORIES.index(niveau["dans"])
        coupe[sous_le_toit] = 0
        coupe[ouvrir(plein, 2) & sous_le_toit] = 1
    coupe = majorite(coupe, (-2, 0, 1))
    return vectoriser(coupe, x, z, pas, ["sol", "mur"])


def ville():
    """Les bâtiments d'OpenStreetMap et les murailles, dans les bornes de la carte."""
    def dedans(points):
        return any(BORNES["x"][0] <= x <= BORNES["x"][1] and BORNES["z"][0] <= z <= BORNES["z"][1] for x, z in points)
    batiments = []
    for b in json.loads((PAYS_DOSSIER / "batiments.json").read_text()):
        anneau = [vers_la_visite(*p) for p in b["anneau"]]
        if dedans(anneau):
            batiments.append(anneau)
    murailles = [[vers_la_visite(*p) for p in trace] for trace in PAYS_DONNEES["murailles"]]
    murailles = [m for m in murailles if dedans(m)]
    trait = "".join("M" + "L".join(f"{x:.1f} {z:.1f}" for x, z in m) for m in murailles)
    return dict(batiments=chemin(batiments), murailles=trait)


def main():
    debut = time.time()
    scene = scene_a_plat()
    faces = releve(scene.arbre, RELEVE["x"], RELEVE["z"], PAS)
    surface, couches = plan_de_surface(faces, scene.categories)
    niveaux = []
    for niveau in NIVEAUX:
        sortie = dict(id=niveau["id"], coupe=niveau["coupe"], lieux=niveau["lieux"],
                      min=[niveau["x"][0], niveau["z"][0]], max=[niveau["x"][1], niveau["z"][1]],
                      couches=plan_de_coupe(scene, niveau, surface))
        if niveau.get("souterraine"):
            sortie.update(souterraine=True, acces=niveau["acces"])
        niveaux.append(sortie)
    plan = dict(min=[BORNES["x"][0], BORNES["z"][0]], max=[BORNES["x"][1], BORNES["z"][1]],
                ville=ville(), couches=couches, niveaux=niveaux, etiquettes=points_d_etiquette(faces, scene.lieux))
    SORTIE.write_text(json.dumps(plan, ensure_ascii=False, separators=(",", ":")))
    print(f"plan · {SORTIE.stat().st_size // 1024} Ko en {time.time() - debut:.0f} s")


main()
