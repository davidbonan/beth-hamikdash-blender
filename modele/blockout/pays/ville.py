import bpy
import json
import math
from mathutils import Vector

from ..primitives.parametres import AMA, m
from ..primitives.matieres import MAT_BETON, MAT_FEUILLAGE, MAT_MAISON, MAT_MURAILLE, MAT_TRONC, MAT_VITRE
from ..primitives.volumes import alea, cyl, plage, sphere
from .calage import (EPAISSEUR_MURAILLE, ESCALIER_PLACE, H_MURAILLE, HARAM, PAYS, PAYS_DONNEES, PAYS_DOSSIER,
                     PLACE_KOTEL, _abscisses, _dans, _dans_le_carre, _direct, _distance_a_l_anneau,
                     _point_a_l_abscisse, sol_naturel, vers_scene, volumes)
from .place_du_kotel import BAIE, ETAGE, PORAT_YOSEF, REZ, _baie, _coupole, _poser


def _le_long_du_haram(trace_m):
    """Un tronçon de muraille qui suit le Haram : c'est son mur, déjà bâti."""
    proches = sum(any(math.dist(vers_scene(*p), q) < 15 for q in HARAM) or _dans(vers_scene(*p), HARAM)
                  for p in trace_m)
    return proches > 0.6 * len(trace_m)


def murailles():
    """Les murailles de Soliman, un segment par pièce, arasées à H_MURAILLE au-dessus du
    point bas de chaque segment."""
    pieces = []
    for trace in PAYS_DONNEES["murailles"]:
        if _le_long_du_haram(trace):
            continue
        points = [vers_scene(*p) for p in trace]
        for a, b in zip(points, points[1:]):
            long_ = math.dist(a, b)
            if long_ < 1e-6:
                continue
            nx = -(b[1] - a[1]) / long_ * EPAISSEUR_MURAILLE / 2
            ny = (b[0] - a[0]) / long_ * EPAISSEUR_MURAILLE / 2
            z0 = min(sol_naturel(*a), sol_naturel(*b))
            pieces.append(([(a[0] - nx, a[1] - ny), (b[0] - nx, b[1] - ny),
                            (b[0] + nx, b[1] + ny), (a[0] + nx, a[1] + ny)], [],
                           z0 - 3, z0 + H_MURAILLE))
    volumes("Murailles", pieces, PAYS, MAT_MURAILLE())


def _metres(valeur):
    try:
        return float(str(valeur).replace("m", "").strip())
    except ValueError:
        return None


def hauteur_batiment(etiquettes, cle):
    """En mètres : la hauteur OSM, sinon ses niveaux, sinon deux à trois niveaux (CHOIX)."""
    hauteur = _metres(etiquettes.get("height", ""))
    if hauteur:
        return hauteur
    niveaux = _metres(etiquettes.get("building:levels", ""))
    if niveaux:
        return 3.2 * niveaux + 1
    return 6.5 + 4 * alea(cle)


TUILE_VILLE = 1000       # amot : les bâtiments sont fondus par tuile
_AXE_ESCALIER = [_point_a_l_abscisse(ESCALIER_PLACE, s)[0]
                 for s in plage(0, _abscisses(ESCALIER_PLACE)[-1], 1)]


def _barre_l_escalier(anneau):
    return any(_dans(p, anneau) for p in _AXE_ESCALIER)


def _sol_bati(x, y, depsgraph):
    """Le dessus de ce qui est déjà bâti sous (x, y) — le relief là où il est abaissé autour
    de la place, un soutènement, la voûte de Wilson —, sinon le relief réel."""
    z = sol_naturel(x, y)
    touche, point, *_ = bpy.context.scene.ray_cast(depsgraph, Vector((m(x), m(y), m(z + 1))), Vector((0, 0, -1)))
    return min(z, point.z / AMA) if touche else z


def ville():
    """Les bâtiments d'OSM hors du Haram, fondus par tuile. Le pied est au point bas de ce
    qui est bâti sous l'emprise, la hauteur comptée depuis le point haut : sur le relief réel,
    le pied d'une maison au bord de la place restait au-dessus du relief abaissé."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    tuiles = {}
    for b in json.loads((PAYS_DOSSIER / "batiments.json").read_text()):
        anneau = [vers_scene(*p) for p in b["anneau"]]
        cx = sum(x for x, _ in anneau) / len(anneau)
        cy = sum(y for _, y in anneau) / len(anneau)
        if (_dans((cx, cy), HARAM) or _dans_le_carre(cx, cy, 2) or _dans((cx, cy), PLACE_KOTEL)
                or _barre_l_escalier(anneau)):
            continue
        if b["osm"] == PORAT_YOSEF:
            porat_yosef(anneau, [[vers_scene(*p) for p in t] for t in b["trous"]], min(sol_naturel(x, y) for x, y in anneau))
            continue
        sols = [_sol_bati(x, y, depsgraph) for x, y in anneau]
        h = hauteur_batiment(b["etiquettes"], b["osm"]) / AMA
        piece = (anneau, [[vers_scene(*p) for p in t] for t in b["trous"]], min(sols) - 1, max(sols) + h)
        tuiles.setdefault((math.floor(cx / TUILE_VILLE), math.floor(cy / TUILE_VILLE)), []).append(piece)
    for (i, j), pieces in sorted(tuiles.items()):
        volumes(f"Ville_{i:+d}_{j:+d}", pieces, PAYS, MAT_MAISON())
    return tuiles


def porat_yosef(anneau, trous, pied, etages=10, pas_des_coupoles=4.5 / AMA):
    """La yeshiva Porat Yosef de Moshe Safdie, au-dessus de la place : dix étages qui montent
    d'est en ouest face au Kotel, des murs de pierre autour de salles cintrées, et des coupoles
    de béton préfabriqué en série (archives Safdie, McGill). Comptés depuis son pied ; les baies
    et le pas des coupoles : CHOIX."""
    haut = pied + REZ + (etages - 1) * ETAGE
    volumes("Porat_Yosef", [(anneau, trous, pied - 1, haut)], "00_HarHabayit", MAT_MAISON())
    vitres = []
    anneau = _direct(anneau)
    for p, q in zip(anneau, anneau[1:] + anneau[:1]):
        longueur = math.dist(p, q)
        bas = max(sol_naturel(*p), sol_naturel(*q))
        for i in range(int(longueur / BAIE)):
            s = (longueur - (int(longueur / BAIE) - 1) * BAIE) / 2 + i * BAIE
            for e in range(etages):
                seuil = pied + REZ + (e - 1) * ETAGE + 0.9 / AMA if e else pied + 1 / AMA
                if seuil > bas and seuil + 2.4 / AMA < haut:
                    vitres.append(_baie(q, p, longueur - s, seuil, 1.6 / AMA, 2.2 / AMA, 0.02 / AMA))
    _poser("Porat_Yosef_baies", vitres, MAT_VITRE())
    xs, ys = [x for x, _ in anneau], [y for _, y in anneau]
    coupoles = [_coupole((x, y), haut, pas_des_coupoles * 0.4)
                for x in plage(min(xs), max(xs), pas_des_coupoles) for y in plage(min(ys), max(ys), pas_des_coupoles)
                if _dans((x, y), anneau) and _distance_a_l_anneau((x, y), anneau) > pas_des_coupoles * 0.5]
    _poser("Porat_Yosef_coupoles", coupoles, MAT_BETON())


def olivier(nom, x, y, col):
    z = sol_naturel(x, y)
    r = 1.6 + 1.4 * alea(nom, 1)
    cyl(f"{nom}_tronc", x, y, z - 0.5, z + 1.6, 0.25, col, MAT_TRONC(), verts=6)
    sphere(f"{nom}_houppier", x, y, z + 1.6 + r * 0.8, r, col, MAT_FEUILLAGE(), segs=8)


def _cases_baties(tuiles, pas=10):
    cases = set()
    for pieces in tuiles.values():
        for anneau, _, _, _ in pieces:
            xs, ys = [x for x, _ in anneau], [y for _, y in anneau]
            for i in range(math.floor(min(xs) / pas), math.floor(max(xs) / pas) + 1):
                for j in range(math.floor(min(ys) / pas), math.floor(max(ys) / pas) + 1):
                    cases.add((i, j))
    return cases
