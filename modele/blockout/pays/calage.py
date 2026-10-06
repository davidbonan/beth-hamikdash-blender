import array
import json
import math
from typing import NamedTuple
from mathutils import Vector, geometry

from ..primitives.parametres import AMA, MODELE, Z_HAR, m
from ..primitives.pierre import DEBORD_ASSISE, JOINT, Appareil
from ..primitives.matieres import MAT_TERRE
from ..primitives.volumes import mesh_from_pydata
from ..har_habayit import HX0, HX1, HY0, HY1
from ..bayit.kodesh_hakodashim import SHETIYA_CENTRE


# ----------------------------------------------------------------------------
# 01 — LE PAYS : Jérusalem aujourd'hui autour du Temple
#   Relief, bâtiments, murailles, esplanade et Kotel réels, tirés par
#   beit_hamikdash_pays.py dans `pays/` (OpenStreetMap, Mapzen Terrain Tiles), en mètres
#   autour du rocher du Dôme. Le calage est une décision de la scène et se prend ici,
#   après le Kodesh HaKodashim : c'est la Even HaShetiya qui l'ancre.
# ----------------------------------------------------------------------------
PAYS = "01_Pays"
PAYS_DOSSIER = MODELE / "pays"
PAYS_DONNEES = json.loads((PAYS_DOSSIER / "pays.json").read_text())
# Le rocher du Dôme est la Even HaShetiya, « שֶׁהָיְתָה שָׁם מִימוֹת נְבִיאִים רִאשׁוֹנִים » (Yoma 5:2) :
# CHOIX, l'identification courante. Le Temple garde l'est vrai, celui de la ligne de
# mire de la para (Middot 2:4) ; le Haram actuel est tourné de 6°, et son mur est passe
# alors une dizaine de mètres en dedans de l'angle nord-est du carré. ORIENTATION, en
# degrés, tourne la géographie autour du rocher.
ORIENTATION = 0.0
# L'esplanade actuelle devient Z_HAR : médiane du relief dans le Haram, 740,2 m.
ALTITUDE_HAR = 740.2
PARAPET_HAR = 4          # la crête du mur d'Hérode au-dessus du dallage, CHOIX
H_KOTEL = 19             # m : ce que le Kotel montre au-dessus de sa place
Z_PLACE_KOTEL = Z_HAR + PARAPET_HAR - H_KOTEL / AMA
# Deux niveaux depuis 1968 : l'aire de prière creusée contre le Kotel, la place haute des
# visiteurs à l'ouest ; l'écart, ramené de 2,5 m à 60 cm, est tenu par un muret d'environ
# 90 cm que coiffe depuis 1979 un parapet de pierre d'un mètre (S. Bahat, Cathedra 174, 2020).
Z_PLACE_HAUTE = Z_PLACE_KOTEL + 0.6 / AMA
PARAPET_DE_PRIERE = 1 / AMA
EPAISSEUR_HAR = 4        # le mur d'Hérode, dallage compris sous sa crête : CHOIX
# Au-dessus de la place, sept assises d'Hérode à marges ciselées de 5 à 20 cm, quatre
# omeyyades de pierres plus petites sans marges, puis dix-sept petites, mameloukes et
# après (Wikipedia, « Western Wall »). Hauteurs d'assise : CHOIX qui remplit les 19 m ;
# à 1,1 m de haut et d'épaisseur, les 2 à 8 tonnes d'une pierre d'Hérode font 1 à 3 m.
Z_KOTEL_OMEYYADE = Z_PLACE_KOTEL + 7 * 1.1 / AMA
Z_KOTEL_MAMELOUK = Z_KOTEL_OMEYYADE + 4 * 0.8 / AMA
APPAREILS_KOTEL = (
    ("Kotel_herodien", Appareil(1.1 / AMA, (2.0, 6.0), DEBORD_ASSISE, 0.02, 0.3, Z_PLACE_KOTEL), Z_KOTEL_OMEYYADE),
    ("Kotel_omeyyade", Appareil(0.8 / AMA, (1.5, 2.5), DEBORD_ASSISE, JOINT, 0.0, Z_KOTEL_OMEYYADE), Z_KOTEL_MAMELOUK),
    ("Kotel_mamelouk", Appareil((Z_HAR + PARAPET_HAR - Z_KOTEL_MAMELOUK) / 17, (1.0, 1.6), DEBORD_ASSISE, JOINT, 0.0,
                               Z_KOTEL_MAMELOUK), math.inf),
)
H_MURAILLE, EPAISSEUR_MURAILLE = 12 / AMA, 3 / AMA   # murailles de Soliman, CHOIX


class Relief(NamedTuple):
    x0: float
    y0: float
    pas: float
    n: int
    altitudes: array.array


def _lire_relief():
    r = PAYS_DONNEES["relief"]
    altitudes = array.array("f")
    altitudes.frombytes((PAYS_DOSSIER / "relief.f32").read_bytes())
    return Relief(r["origine"][0], r["origine"][1], r["pas"], r["n"], altitudes)


RELIEF = _lire_relief()


def vers_scene(est, nord):
    """Mètres autour du rocher → amot de la scène."""
    a = math.radians(ORIENTATION)
    x, y = est * math.cos(a) - nord * math.sin(a), est * math.sin(a) + nord * math.cos(a)
    return SHETIYA_CENTRE[0] + x / AMA, SHETIYA_CENTRE[1] + y / AMA


def depuis_scene(x, y):
    a = math.radians(ORIENTATION)
    u, v = m(x - SHETIYA_CENTRE[0]), m(y - SHETIYA_CENTRE[1])
    return u * math.cos(a) + v * math.sin(a), -u * math.sin(a) + v * math.cos(a)


def cote(altitude_m):
    return Z_HAR + (altitude_m - ALTITUDE_HAR) / AMA


def sol_naturel(x, y):
    """Cote du relief en (x, y) de la scène, interpolée, en amot ; dans la cuvette du Kotel,
    jamais plus haut que la place."""
    z = _relief_brut(x, y)
    return min(z, Z_PLACE_HAUTE) if _dans((x, y), CUVETTE_KOTEL) else z


def _relief_brut(x, y):
    est, nord = depuis_scene(x, y)
    u, v = (est - RELIEF.x0) / RELIEF.pas, (nord - RELIEF.y0) / RELIEF.pas
    i = min(max(int(u), 0), RELIEF.n - 2)
    j = min(max(int(v), 0), RELIEF.n - 2)
    fu, fv = min(max(u - i, 0), 1), min(max(v - j, 0), 1)
    z = RELIEF.altitudes
    k = j * RELIEF.n + i
    bas = z[k] * (1 - fu) + z[k + 1] * fu
    haut = z[k + RELIEF.n] * (1 - fu) + z[k + RELIEF.n + 1] * fu
    return cote(bas * (1 - fv) + haut * fv)


def _direct(anneau):
    """L'anneau dans le sens trigonométrique."""
    aire = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(anneau, anneau[1:] + anneau[:1]))
    return anneau if aire > 0 else anneau[::-1]


def _dans(p, anneau):
    x, y = p
    dedans = False
    for (x0, y0), (x1, y1) in zip(anneau, anneau[1:] + anneau[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            dedans = not dedans
    return dedans


def _fraction_sur_le_segment(p, a, b):
    ab = (b[0] - a[0], b[1] - a[1])
    long2 = ab[0] ** 2 + ab[1] ** 2
    return 0 if long2 == 0 else max(0, min(1, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / long2))


def _distance_au_segment(p, a, b):
    t = _fraction_sur_le_segment(p, a, b)
    return math.dist(p, (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))


def _distance_a_l_anneau(p, anneau):
    return min(_distance_au_segment(p, a, b) for a, b in zip(anneau, anneau[1:] + anneau[:1]))


def _distance_a_la_trace(p, trace):
    return min(_distance_au_segment(p, a, b) for a, b in zip(trace, trace[1:]))


def _abscisses(trace):
    s = [0.0]
    for a, b in zip(trace, trace[1:]):
        s.append(s[-1] + math.dist(a, b))
    return s


def _abscisse_du_plus_proche(p, trace):
    """L'abscisse curviligne, sur la trace, du point le plus proche de `p`."""
    s = _abscisses(trace)
    k = min(range(len(trace) - 1), key=lambda k: _distance_au_segment(p, trace[k], trace[k + 1]))
    return s[k] + _fraction_sur_le_segment(p, trace[k], trace[k + 1]) * (s[k + 1] - s[k])


def _point_a_l_abscisse(trace, abscisse):
    """Le point de la trace à l'abscisse donnée, et la direction de son tronçon."""
    s = _abscisses(trace)
    k = max(0, min(len(trace) - 2, next((k for k in range(len(s) - 1) if abscisse <= s[k + 1]), len(s) - 2)))
    a, b = trace[k], trace[k + 1]
    t = (abscisse - s[k]) / max(s[k + 1] - s[k], 1e-9)
    long_ = max(math.dist(a, b), 1e-9)
    return ((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])),
            ((b[0] - a[0]) / long_, (b[1] - a[1]) / long_))


def _plus_proche_sur_la_trace(p, trace):
    return _point_a_l_abscisse(trace, _abscisse_du_plus_proche(p, trace))[0]


def _plus_proche_sur_l_anneau(p, anneau):
    a, b = min(zip(anneau, anneau[1:] + anneau[:1]), key=lambda e: _distance_au_segment(p, *e))
    t = _fraction_sur_le_segment(p, a, b)
    return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))


def _dans_le_carre(x, y, marge=0):
    return HX0 - marge <= x <= HX1 + marge and HY0 - marge <= y <= HY1 + marge


def _anneau_scene(anneau_m):
    return _direct([vers_scene(*p) for p in anneau_m])


HARAM = _anneau_scene(PAYS_DONNEES["haram"])
PLACE_KOTEL = _anneau_scene(PAYS_DONNEES["place_kotel"])
KOTEL = [vers_scene(*p) for p in PAYS_DONNEES["kotel"]]
SALLES_WILSON = _anneau_scene(PAYS_DONNEES["salles_wilson"])
PONT_MAGHREBINS = [vers_scene(*p) for p in PAYS_DONNEES["pont_maghrebins"]]
ESCALIER_PLACE = ([_plus_proche_sur_l_anneau(vers_scene(*PAYS_DONNEES["escalier_place"][0]), PLACE_KOTEL)]
                  + [vers_scene(*p) for p in PAYS_DONNEES["escalier_place"]])
# Le relief à 30 m ne voit ni la place ni la falaise du quartier juif : il descend en pente douce
# du quartier juif au pied du Kotel, dix mètres au-dessus des dalles. La cuvette est ce qui est
# de plain-pied avec la place — la place, Beit HaLiba à l'ouest, le parc des voitures et les
# contrôles au sud jusqu'à la muraille, les fouilles sous le pont à l'est. Relevée sur le plan OSM.
CUVETTE_KOTEL = _anneau_scene([
    (-188, -149), (-184, -140), (-149, -132), (-134, -130), (-122, -127), (-123, -120), (-101, -116),
    (-91, -174), (-81, -230), (-77, -258), (-95, -300), (-112, -345), (-165, -345), (-170, -300),
    (-186, -262), (-185, -241), (-177, -233), (-172, -225), (-177, -198), (-203, -201), (-212, -153)])
PORTEE_WILSON, CLE_WILSON = 13 / AMA, 6.1 / AMA    # l'arche : portée, et sa clé au-dessus du sol d'aujourd'hui
LARGEUR_PONT, GARDE_CORPS = 3 / AMA, 1.1 / AMA
CONTREMARCHE, LARGEUR_ESCALIER = 0.16 / AMA, 3.5 / AMA


def volumes(name, pieces, col, mat):
    """Un maillage de prismes : chaque pièce est (anneau, trous, z0, z1), anneaux en amot.
    Flancs et dessus ; le dessous est enterré. Le dessus est triangulé trous compris."""
    verts, faces = [], []
    for anneau, trous, z0, z1 in pieces:
        anneaux = [_direct(anneau)] + [_direct(t)[::-1] for t in trous]
        for r in anneaux:
            base = len(verts)
            n = len(r)
            verts += [(x, y, z0) for x, y in r] + [(x, y, z1) for x, y in r]
            faces += [[base + i, base + (i + 1) % n, base + n + (i + 1) % n, base + n + i]
                      for i in range(n)]
        toit = [Vector((x, y, z1)) for r in anneaux for x, y in r]
        base = len(verts)
        verts += [tuple(v) for v in toit]
        for a, b, c in geometry.tessellate_polygon([[Vector((x, y, z1)) for x, y in r] for r in anneaux]):
            pa, pb, pc = toit[a], toit[b], toit[c]
            haut = (pb - pa).cross(pc - pa).z >= 0
            faces.append([base + a, base + b, base + c] if haut else [base + a, base + c, base + b])
    return mesh_from_pydata(name, verts, faces, col, mat)


MAILLE_PAYS = PAYS_DONNEES["relief"]["pas"] * math.sqrt(2) / AMA


def _creuse_pour_la_place(p):
    """Dans la cuvette ou les salles de Wilson, ou à moins d'une maille : une maille à cheval
    sur leur bord remontait en talus au-dessus du dallage. Le soutènement, aussi épais,
    couvre ce qu'on abaisse."""
    return any(_dans(p, anneau) or _distance_a_l_anneau(p, anneau) < MAILLE_PAYS
               for anneau in (CUVETTE_KOTEL, SALLES_WILSON))


Z_HAUT_ESCALIER = sol_naturel(*ESCALIER_PLACE[-1])


def _z_escalier(abscisse):
    return Z_PLACE_HAUTE + (Z_HAUT_ESCALIER - Z_PLACE_HAUTE) * abscisse / _abscisses(ESCALIER_PLACE)[-1]


def _sol_le_long_de_l_escalier(p, z):
    """Le relief à une maille de l'escalier descend sous ses degrés, que ses murs couvrent."""
    if _distance_a_la_trace(p, ESCALIER_PLACE) >= MAILLE_PAYS:
        return z
    return min(z, _z_escalier(_abscisse_du_plus_proche(p, ESCALIER_PLACE)) - 1)


def _nappe_du_pays():
    """Le relief réel sur sa grille, abaissé sous la place du Kotel et ses abords — le relief à 30 m la
    lisse en pente, et ses dix-neuf mètres y disparaissaient. Sous l'esplanade, chaque
    nœud prend le plus bas de ses voisins du dehors : une maille à cheval sur le mur
    reste ainsi sous lui au lieu de monter en talus devant son parement."""
    n = RELIEF.n
    touches = HARAM + CUVETTE_KOTEL + SALLES_WILSON + ESCALIER_PLACE
    x_min = min(x for x, _ in touches) - 2 * MAILLE_PAYS
    x_max = max(x for x, _ in touches) + 2 * MAILLE_PAYS
    y_min = min(y for _, y in touches) - 2 * MAILLE_PAYS
    y_max = max(y for _, y in touches) + 2 * MAILLE_PAYS
    verts, dessous = [], []
    for j in range(n):
        for i in range(n):
            x, y = vers_scene(RELIEF.x0 + i * RELIEF.pas, RELIEF.y0 + j * RELIEF.pas)
            z = cote(RELIEF.altitudes[j * n + i])
            if x_min < x < x_max and y_min < y < y_max:
                if _dans((x, y), HARAM) or _dans_le_carre(x, y):
                    dessous.append(j * n + i)
                elif _creuse_pour_la_place((x, y)):
                    z = min(z, Z_PLACE_KOTEL - 1)
                else:
                    z = _sol_le_long_de_l_escalier((x, y), z)
            verts.append((x, y, z))
    enfouis = set(dessous)
    for k in dessous:
        i, j = k % n, k // n
        voisins = [verts[jj * n + ii][2] for jj in range(j - 2, j + 3) for ii in range(i - 2, i + 3)
                   if jj * n + ii not in enfouis]
        verts[k] = (*verts[k][:2], min(voisins + [Z_HAR - 1]) if voisins else Z_HAR - 8)
    faces = [[j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i]
             for j in range(n - 1) for i in range(n - 1)]
    return mesh_from_pydata("Pays_relief", verts, faces, PAYS, MAT_TERRE())
