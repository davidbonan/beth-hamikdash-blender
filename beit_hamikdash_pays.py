#!/usr/bin/env python3
"""Tire le pays réel autour du Temple : relief et bâtiments de Jérusalem aujourd'hui.

    python3 beit_hamikdash_pays.py

Écrit `pays/`, que le blockout lit : la géographie seule, en mètres, dans un repère
local centré sur la Even HaShetiya (est, nord, altitude). Où le Temple se pose dans ce
repère — le calage, l'orientation, la cote de l'esplanade — est une décision de la
scène, et vit dans le blockout.

- `relief.f32` : altitudes en mètres, grille régulière, float32 little-endian, ligne par
  ligne du sud au nord ; `pays.json` en donne l'origine, le pas et la taille.
  Terrain Tiles d'AWS (Mapzen, format terrarium), zoom 15.
- `pays.json` : aussi les lieux nommés — contour du Har HaBayit actuel, le Kotel, sa
  place et ses abords (pont des Maghrébins, salles de l'arche de Wilson, escalier vers le
  quartier juif, passages vers la ville, et ce qui les meuble : robinets, contrôles, portes, clôtures, arrêt de
  bus), les murailles, le rocher.
- `batiments.json` : les emprises OSM, anneaux en mètres, avec les étiquettes qui disent
  une hauteur. Ceux du Har HaBayit sont écartés : l'esplanade est au Temple ; les
  souterrains aussi.

Données : © OpenStreetMap contributors (ODbL) ; relief, Mapzen Terrain Tiles (SRTM et
autres, voir leur attribution). ffmpeg sur le PATH pour décoder les tuiles.
"""
import json
import math
import pathlib
import struct
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

DOSSIER = pathlib.Path(__file__).with_name("pays")
TUILES = DOSSIER / ".tuiles"

# La Even HaShetiya (Yoma 5:2) est le rocher du Dôme : « Foundation Stone », node OSM 12696348577.
ROCHER = (31.7779927, 35.2354315)
DEMI_COTE = 2900          # m : le pays du blockout fait 6000 amot de demi-côté
PAS_RELIEF = 10           # m
ZOOM = 15
HARAM = 5862584           # relation OSM « Temple Mount »
KOTEL, PLACE_KOTEL = 817206833, 26492734
PONT_MAGHREBINS, SALLES_WILSON = 277508271, 499210296
ESCALIER_PLACE = (26493216, 659765488)     # du coin nord-ouest de la place vers le quartier juif
# Les passages qui quittent la place : vers la rue HaGaï, vers Batei Ma'hasse, vers la porte des Ordures.
PASSAGES_PLACE = {"hagai": 1528267326, "batei_mahase": 288016687, "porte_des_ordures": 1044731105}
ROCHER_CONTOUR = 291836699
SANS_VOLUME = {"wall", "roof", "ruins", "construction", "no"}
ABORDS_KOTEL = (-240, -300, -60, -60)      # m : ouest, sud, est, nord
# Le premier genre qui s'applique décide : un contrôle d'entrée est un contrôle, pas une porte.
GENRES_DES_ABORDS = (
    ("netilat_yadayim", "amenity", "ablution"), ("fontaine", "amenity", "drinking_water"),
    ("controle", "barrier", "checkpoint"), ("portail", "barrier", "gate"), ("entree", "entrance", None),
    ("arret_bus", "highway", "bus_stop"), ("menora", "historic", "memorial"),
    ("cloture", "barrier", "fence"), ("muret", "barrier", "wall"), ("bornes", "barrier", "bollard"),
    ("auvent", "building", "roof"), ("poubelle", "amenity", "waste_basket"),
    ("recyclage", "amenity", "recycling"), ("borne_incendie", "emergency", "fire_hydrant"),
    ("toilettes", "amenity", "toilets"), ("police", "amenity", "police"),
    ("soupe_populaire", "social_facility", "soup_kitchen"), ("voie_bus", "bus", "yes"),
)

M_PAR_DEG_LAT = 111132.954 - 559.822 * math.cos(2 * math.radians(ROCHER[0]))
M_PAR_DEG_LON = 111412.84 * math.cos(math.radians(ROCHER[0]))


def local(lat, lon):
    return ((lon - ROCHER[1]) * M_PAR_DEG_LON, (lat - ROCHER[0]) * M_PAR_DEG_LAT)


def geo(est, nord):
    return (ROCHER[0] + nord / M_PAR_DEG_LAT, ROCHER[1] + est / M_PAR_DEG_LON)


def overpass(requete, essais=4):
    corps = urllib.parse.urlencode({"data": requete}).encode()
    req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=corps,
                                 headers={"User-Agent": "avoda-beit-hamikdash/1.0"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=300))["elements"]
    except urllib.error.HTTPError as erreur:
        if essais == 1 or erreur.code not in (429, 502, 503, 504):
            raise
        time.sleep(20)
        return overpass(requete, essais - 1)


def bbox():
    (s, w), (n, e) = geo(-DEMI_COTE, -DEMI_COTE), geo(DEMI_COTE, DEMI_COTE)
    return f"{s:.6f},{w:.6f},{n:.6f},{e:.6f}"


# --- Relief ---------------------------------------------------------------

def tuile_xy(lat, lon):
    n = 2 ** ZOOM
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def tuile(tx, ty):
    """Altitudes d'une tuile terrarium, 256 × 256, en mètres."""
    png = TUILES / f"{ZOOM}_{tx}_{ty}.png"
    if not png.exists():
        url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{ZOOM}/{tx}/{ty}.png"
        png.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    rgb = subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return [rgb[i] * 256 + rgb[i + 1] + rgb[i + 2] / 256 - 32768 for i in range(0, len(rgb), 3)]


def relief():
    TUILES.mkdir(parents=True, exist_ok=True)
    cache = {}

    def altitude_pixel(px, py):
        tx, ty = px // 256, py // 256
        if (tx, ty) not in cache:
            cache[(tx, ty)] = tuile(tx, ty)
        return cache[(tx, ty)][(py % 256) * 256 + px % 256]

    def altitude(lat, lon):
        x, y = tuile_xy(lat, lon)
        x, y = x * 256 - 0.5, y * 256 - 0.5
        x0, y0 = math.floor(x), math.floor(y)
        fx, fy = x - x0, y - y0
        a, b = altitude_pixel(x0, y0), altitude_pixel(x0 + 1, y0)
        c, d = altitude_pixel(x0, y0 + 1), altitude_pixel(x0 + 1, y0 + 1)
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

    n = 2 * DEMI_COTE // PAS_RELIEF + 1
    valeurs = [altitude(*geo(-DEMI_COTE + i * PAS_RELIEF, -DEMI_COTE + j * PAS_RELIEF))
               for j in range(n) for i in range(n)]
    (DOSSIER / "relief.f32").write_bytes(struct.pack(f"<{len(valeurs)}f", *valeurs))
    return {"origine": [-DEMI_COTE, -DEMI_COTE], "pas": PAS_RELIEF, "n": n,
            "source": "Mapzen Terrain Tiles (terrarium), zoom 15"}


# --- OSM ------------------------------------------------------------------

def anneau(geometrie):
    return [[round(c, 2) for c in local(p["lat"], p["lon"])] for p in geometrie]


def souder(morceaux):
    """Les ways d'un multipolygone mis bout à bout en anneaux fermés."""
    restants = [list(m) for m in morceaux if m]
    anneaux = []
    while restants:
        courant = restants.pop(0)
        while courant[0] != courant[-1]:
            for k, m in enumerate(restants):
                if m[0] == courant[-1]:
                    courant += m[1:]
                elif m[-1] == courant[-1]:
                    courant += m[-2::-1]
                elif m[-1] == courant[0]:
                    courant = m[:-1] + courant
                elif m[0] == courant[0]:
                    courant = m[:0:-1] + courant
                else:
                    continue
                restants.pop(k)
                break
            else:
                break
        if courant[0] == courant[-1] and len(courant) >= 4:
            anneaux.append(courant)
    return anneaux


def polygones(element):
    """[(extérieur, [trous])] en mètres, anneaux ouverts."""
    if element["type"] == "way":
        g = anneau(element["geometry"])
        return [(g[:-1], [])] if len(g) >= 4 and g[0] == g[-1] else []
    exterieurs = souder(anneau(m["geometry"]) for m in element["members"]
                        if m.get("role") in ("outer", "") and "geometry" in m)
    trous = souder(anneau(m["geometry"]) for m in element["members"]
                   if m.get("role") == "inner" and "geometry" in m)
    return [(e[:-1], [t[:-1] for t in trous if dedans(t[0], e)]) for e in exterieurs]


def dedans(p, anneau_):
    x, y = p
    c = False
    for (x0, y0), (x1, y1) in zip(anneau_, anneau_[1:] + anneau_[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def lieux():
    par_id = {(e["type"], e["id"]): e for e in overpass(
        f"[out:json][timeout:120];(relation({HARAM});way({KOTEL});way({PLACE_KOTEL});"
        f"way({ROCHER_CONTOUR});way({PONT_MAGHREBINS});way({SALLES_WILSON});"
        f"way(id:{','.join(map(str, ESCALIER_PLACE + tuple(PASSAGES_PLACE.values())))}););out geom;")}
    haram = polygones(par_id[("relation", HARAM)])
    murailles = [anneau(e["geometry"]) for e in overpass(
        f'[out:json][timeout:120];way["barrier"="city_wall"]({bbox()});out geom;')]
    return {
        "haram": max((e for e, _ in haram), key=len),
        "kotel": anneau(par_id[("way", KOTEL)]["geometry"]),
        "place_kotel": anneau(par_id[("way", PLACE_KOTEL)]["geometry"])[:-1],
        "rocher": anneau(par_id[("way", ROCHER_CONTOUR)]["geometry"])[:-1],
        "pont_maghrebins": anneau(par_id[("way", PONT_MAGHREBINS)]["geometry"]),
        "salles_wilson": anneau(par_id[("way", SALLES_WILSON)]["geometry"])[:-1],
        "escalier_place": [p for k, w in enumerate(ESCALIER_PLACE)
                           for p in anneau(par_id[("way", w)]["geometry"])[1 if k else 0:]],
        "passages_place": {nom: anneau(par_id[("way", w)]["geometry"]) for nom, w in PASSAGES_PLACE.items()},
        "murailles": murailles,
    }


def _genre(etiquettes):
    return next((genre for genre, cle, valeur in GENRES_DES_ABORDS
                 if cle in etiquettes and (valeur is None or etiquettes[cle] == valeur)), None)


def abords_du_kotel():
    """Ce qui meuble la place et ses bords : robinets, contrôles, portes, clôtures, arrêt de bus…
    Un point par nœud, une trace par way."""
    (s, w), (n, e) = geo(ABORDS_KOTEL[0], ABORDS_KOTEL[1]), geo(ABORDS_KOTEL[2], ABORDS_KOTEL[3])
    boite = f"{s:.6f},{w:.6f},{n:.6f},{e:.6f}"
    filtres = "".join(f'nw["{cle}"]({boite});' if valeur is None else f'nw["{cle}"="{valeur}"]({boite});'
                      for _, cle, valeur in GENRES_DES_ABORDS)
    sortie = []
    for el in overpass(f"[out:json][timeout:120];({filtres});out geom;"):
        genre = _genre(el["tags"])
        points = anneau(el["geometry"] if "geometry" in el else [el])
        sortie.append({"osm": f"{el['type'][0]}{el['id']}", "genre": genre, "points": points,
                       "nom": el["tags"].get("name", "")})
    return sorted(sortie, key=lambda a: a["osm"])


def batiments(haram):
    elements = overpass(f'[out:json][timeout:280];(way["building"]({bbox()});'
                        f'relation["building"]({bbox()}););out geom;')
    garde = ("building", "height", "min_height", "building:levels", "building:min_level",
             "roof:shape", "roof:height", "name", "name:en", "amenity", "religion")
    sortie = []
    for e in elements:
        t = e["tags"]
        if t.get("building") in SANS_VOLUME or t.get("layer", "0").startswith("-"):
            continue
        for exterieur, trous in polygones(e):
            if dedans(exterieur[0], haram):
                continue
            sortie.append({"osm": f"{e['type'][0]}{e['id']}",
                           "etiquettes": {k: t[k] for k in garde if k in t},
                           "anneau": exterieur, "trous": trous})
    return sortie


def main():
    DOSSIER.mkdir(exist_ok=True)
    pays = {"rocher": {"lat": ROCHER[0], "lon": ROCHER[1], "osm": "n12696348577"},
            "repere": "mètres : x vers l'est, y vers le nord depuis le rocher, z altitude",
            "relief": relief()}
    pays.update(lieux())
    pays["abords_kotel"] = abords_du_kotel()
    (DOSSIER / "pays.json").write_text(json.dumps(pays, ensure_ascii=False, indent=1))
    liste = batiments(pays["haram"])
    (DOSSIER / "batiments.json").write_text(
        json.dumps(liste, ensure_ascii=False, separators=(",", ":")))
    print(f"relief {pays['relief']['n']}², {len(liste)} bâtiments, "
          f"{len(pays['murailles'])} tronçons de muraille")


if __name__ == "__main__":
    main()
