"""La carte de relief : ce qu'une matière lit au lieu d'un volume.

Une figure tissée ou gravée n'est pas un empilement de plaques : c'est une HAUTEUR en
chaque point, que le nuanceur dérive en pente. Ce fichier rasterise des contours en
hauteurs — remplir un polygone, bomber ce qu'il enferme, y creuser un sillon, fondre —
et écrit la carte. `beit_hamikdash_parokhet.py` (le motif tissé) et
`beit_hamikdash_gravures.py` (les figures des parois) le lisent tous deux.

Ligne 0 en bas, comme z. Ni scipy ni PIL : numpy seul, et bpy pour écrire le PNG que
`cwebp` compresse — l'alpha du WebP est codé à part et sans perte.
"""
import pathlib
import subprocess

import bpy
import numpy as np

RACINE = pathlib.Path(__file__).resolve().parent
SORTIE = RACINE / "visite" / "matieres"
BRUT = SORTIE / ".scans"


def remplir(contour, echelle, hauteur, largeur):
    """Masque booléen d'un polygone dans sa boîte englobante, règle pair-impair : chaque
    arête bascule le pixel où elle coupe la ligne de centres, et une somme cumulée sur
    la ligne fait le reste. Le contour a le droit d'être concave, ce qui est le cas de
    toute figure. Renvoie (tranche de lignes, tranche de colonnes, masque)."""
    points = [(u * echelle, z * echelle) for u, z in contour]
    z_bas = max(0, int(np.ceil(min(z for _, z in points) - 0.5)))
    z_haut = min(hauteur, int(np.ceil(max(z for _, z in points) - 0.5)))
    u_gauche = max(0, int(np.floor(min(u for u, _ in points) - 0.5)))
    u_droite = min(largeur, int(np.ceil(max(u for u, _ in points) + 0.5)))
    boite = np.zeros((max(0, z_haut - z_bas), max(0, u_droite - u_gauche) + 1), dtype=np.int32)
    for (u0, z0), (u1, z1) in zip(points, points[1:] + points[:1]):
        if z0 == z1:
            continue
        bas, haut = min(z0, z1), max(z0, z1)
        lignes = np.arange(max(z_bas, int(np.ceil(bas - 0.5))), min(z_haut, int(np.ceil(haut - 0.5))))
        if not len(lignes):
            continue
        croisements = u0 + (lignes + 0.5 - z0) * (u1 - u0) / (z1 - z0)
        colonnes = np.clip(np.ceil(croisements - 0.5).astype(np.int64) - u_gauche, 0, boite.shape[1] - 1)
        np.add.at(boite, (lignes - z_bas, colonnes), 1)
    dedans = (np.cumsum(boite, axis=1)[:, :-1] % 2).astype(bool)
    return slice(z_bas, z_haut), slice(u_gauche, u_droite), dedans


def flouter(carte, rayon):
    """Trois flous en boîte de `rayon` pixels : une cloche, sans dépendance."""
    for _ in range(3):
        for axe in (0, 1):
            bord = [(0, 0), (0, 0)]
            bord[axe] = (rayon, rayon)
            garni = np.pad(carte, bord, mode="edge")
            somme = np.cumsum(garni, axis=axe)
            somme = np.concatenate([np.zeros_like(np.take(somme, [0], axis=axe)), somme], axis=axe)
            n = carte.shape[axe]
            carte = (np.take(somme, np.arange(2 * rayon + 1, 2 * rayon + 1 + n), axis=axe)
                     - np.take(somme, np.arange(n), axis=axe)) / (2 * rayon + 1)
    return carte


def _eroder(masque, diagonales):
    g = np.pad(masque, 1, constant_values=False)
    erode = g[1:-1, 1:-1] & g[:-2, 1:-1] & g[2:, 1:-1] & g[1:-1, :-2] & g[1:-1, 2:]
    if diagonales:
        erode &= g[:-2, :-2] & g[:-2, 2:] & g[2:, :-2] & g[2:, 2:]
    return erode


def distance(masque, rayon):
    """Distance au bord, en pixels, plafonnée à `rayon`, pour chaque pixel du masque.
    Une érosion par pixel de rayon, en alternant les quatre et les huit voisins : un
    octogone, à 8 % du cercle près — assez pour un bombé, sans transformée exacte."""
    d = np.zeros(masque.shape, dtype=np.float32)
    courant = masque
    for k in range(rayon):
        courant = _eroder(courant, diagonales=k % 2 == 1)
        if not courant.any():
            break
        d += courant
    return d


def bombe(t):
    """Le profil d'un bombé, de t = 0 au bord à t = 1 au plein : une parabole, qui
    monte vite au bord et s'aplatit au sommet. Un quart de cercle grésillait au bord."""
    return 1.0 - (1.0 - t) ** 2


class Planche:
    """Une carte de hauteur en cours de taille, dans un repère (u, z) réel.

    `cadre` = (u0, z0, u1, z1), la fenêtre réelle que la planche couvre ; `pixels` sa
    largeur. Les hauteurs sont en unités libres, à ramener à [0, 1] par l'appelant.
    """

    def __init__(self, cadre, pixels):
        self.u0, self.z0, u1, z1 = cadre
        self.echelle = pixels / (u1 - self.u0)
        self.largeur = pixels
        self.hauteur = int(round((z1 - self.z0) * self.echelle))
        self.carte = np.zeros((self.hauteur, self.largeur), dtype=np.float32)
        self.masque = np.zeros((self.hauteur, self.largeur), dtype=bool)

    def _remplir(self, contour):
        decale = [(u - self.u0, z - self.z0) for u, z in contour]
        return remplir(decale, self.echelle, self.hauteur, self.largeur)

    def bomber(self, contour, socle, epaisseur, rondeur):
        """Pose une partie PAR-DESSUS ce qui s'y trouve : dans son contour la hauteur
        devient `socle` + `epaisseur` × bombé, le bombé montant sur `rondeur` (réel)
        depuis le bord. Ce qui était dessous est recouvert, pas additionné — une aile
        posée sur un corps est une aile, et son bord est une marche."""
        lignes, colonnes, dedans = self._remplir(contour)
        rayon = max(1, int(round(rondeur * self.echelle)))
        t = distance(dedans, rayon) / rayon
        boite = self.carte[lignes, colonnes]
        boite[dedans] = socle + epaisseur * bombe(t[dedans])
        self.masque[lignes, colonnes] |= dedans

    def graver(self, polyligne, largeur, profondeur):
        """Creuse un sillon de `largeur` le long d'une ligne brisée : chaque segment est
        un rectangle, et l'union des rectangles se fond en une gorge à profil bombé. Le
        sillon ne mord que la figure — hors d'elle il n'y a rien à creuser."""
        demi = largeur / 2
        for (u0, z0), (u1, z1) in zip(polyligne, polyligne[1:]):
            du, dz = u1 - u0, z1 - z0
            n = (du * du + dz * dz) ** 0.5
            if n < 1e-9:
                continue
            nu, nz = -dz / n * demi, du / n * demi
            au, az = du / n * demi, dz / n * demi
            rectangle = [(u0 + nu - au, z0 + nz - az), (u1 + nu + au, z1 + nz + az),
                         (u1 - nu + au, z1 - nz + az), (u0 - nu - au, z0 - nz - az)]
            lignes, colonnes, dedans = self._remplir(rectangle)
            rayon = max(1, int(round(demi * self.echelle)))
            t = distance(dedans, rayon) / rayon
            boite = self.carte[lignes, colonnes]
            creux = dedans & self.masque[lignes, colonnes]
            boite[creux] = np.maximum(boite[creux] - profondeur * bombe(t[creux]), 0.0)

    def relief(self, fondu):
        """(hauteur, masque) après un fondu de `fondu` (réel). Le fondu adoucit les
        marches ; il ne les efface pas. La hauteur garde ses unités : c'est l'appelant
        qui la ramène à [0, 1], sur toutes ses planches à la fois."""
        carte = flouter(self.carte, max(1, int(round(fondu * self.echelle))))
        return carte, self.masque.astype(np.float32)

    def silhouette(self, tolerance):
        """Le contour extérieur de tout ce qui a été posé, en coordonnées réelles,
        simplifié à `tolerance` (réel) près. Une seule figure d'un seul tenant."""
        pixels = tracer(self.masque)
        aire_masque = self.masque.sum()
        aire_polygone = abs(sum(u0 * z1 - u1 * z0 for (u0, z0), (u1, z1)
                                in zip(pixels, pixels[1:] + pixels[:1]))) / 2
        if abs(aire_polygone - aire_masque) > 0.05 * aire_masque:
            raise ValueError(f"silhouette en plusieurs morceaux ou trouée : polygone "
                             f"{aire_polygone:.0f} px² pour un masque de {aire_masque} px²")
        simple = simplifier(pixels, tolerance * self.echelle)
        return [(self.u0 + (c + 0.5) / self.echelle, self.z0 + (l + 0.5) / self.echelle)
                for c, l in simple]


# Les huit voisins dans l'ordre horaire, en (colonne, ligne), la ligne 0 étant en bas.
_VOISINS = ((1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1))


def tracer(masque):
    """Le bord extérieur d'un masque, pixel par pixel (colonne, ligne), par suivi de
    contour à huit voisins (Moore) : on longe le bord en gardant le dehors à sa gauche,
    et l'on s'arrête en repassant par le départ dans la même direction."""
    garni = np.pad(masque, 1, constant_values=False)
    lignes, colonnes = np.nonzero(garni)
    k = np.argmin(lignes * garni.shape[1] + colonnes)
    depart = (int(colonnes[k]), int(lignes[k]))
    # Le départ est le plus à gauche de la ligne la plus basse : son voisin ouest est
    # dehors, et c'est de là qu'on « arrive ».
    contour, courant, dehors = [depart], depart, (depart[0] - 1, depart[1])
    while True:
        i = _VOISINS.index((dehors[0] - courant[0], dehors[1] - courant[1]))
        for pas in range(1, 9):
            dc, dl = _VOISINS[(i + pas) % 8]
            suivant = (courant[0] + dc, courant[1] + dl)
            if garni[suivant[1], suivant[0]]:
                break
            dehors = suivant
        else:
            return [(depart[0] - 1, depart[1] - 1)]
        # Critère de Jacob : de retour au départ ET repartant vers le même second point.
        if courant == depart and len(contour) > 1 and suivant == contour[1]:
            if contour[-1] == depart:
                contour.pop()
            return [(c - 1, l - 1) for c, l in contour]
        contour.append(suivant)
        courant = suivant
        if len(contour) > 4 * masque.size:
            raise ValueError("suivi de contour sans fin")


def simplifier(points, tolerance):
    """Douglas-Peucker sur un contour fermé : ne garde que les sommets qui s'écartent
    de plus de `tolerance` de la corde qui les saute."""
    if len(points) < 4:
        return list(points)
    pts = np.asarray(points, dtype=np.float64)
    loin = int(np.argmax(np.sum((pts - pts[0]) ** 2, axis=1)))
    return _dp(pts[:loin + 1], tolerance)[:-1] + _dp(np.vstack([pts[loin:], pts[:1]]), tolerance)[:-1]


def _dp(pts, tolerance):
    garde = np.zeros(len(pts), dtype=bool)
    garde[0] = garde[-1] = True
    pile = [(0, len(pts) - 1)]
    while pile:
        a, b = pile.pop()
        if b - a < 2:
            continue
        corde = pts[b] - pts[a]
        n = np.hypot(*corde) or 1.0
        ecarts = np.abs((pts[a + 1:b] - pts[a]) @ np.array([-corde[1], corde[0]])) / n
        k = int(np.argmax(ecarts))
        if ecarts[k] > tolerance:
            garde[a + 1 + k] = True
            pile += [(a, a + 1 + k), (a + 1 + k, b)]
    return [tuple(p) for p in pts[garde]]


def ecrire(nom, relief, masque):
    """RGB = hauteur en gris, alpha = masque. Le PNG passe par bpy, le WebP par cwebp,
    `-exact` gardant l'alpha entier là où il vaut zéro."""
    hauteur, largeur = relief.shape
    pixels = np.empty((hauteur, largeur, 4), dtype=np.float32)
    pixels[..., 0] = pixels[..., 1] = pixels[..., 2] = relief
    pixels[..., 3] = masque
    image = bpy.data.images.new(nom, largeur, hauteur, alpha=True, is_data=True)
    image.pixels.foreach_set(pixels.ravel())
    BRUT.mkdir(parents=True, exist_ok=True)
    png = BRUT / f"{nom}.png"
    image.filepath_raw = str(png)
    image.file_format = "PNG"
    image.save()
    webp = SORTIE / f"{nom}.webp"
    subprocess.run(["cwebp", "-quiet", "-q", "90", "-m", "6", "-exact", str(png), "-o", str(webp)],
                   check=True)
    print(f"  {webp.relative_to(RACINE)} : {largeur} × {hauteur}, {webp.stat().st_size / 1e3:.0f} ko")
    return webp
