"""Tisse le motif des deux Parokhot : une carte que la matière lit, pas des volumes.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_parokhet.py               # la carte
    /Applications/Blender.app/Contents/MacOS/Blender -b -P beit_hamikdash_parokhet.py -- --tisser   # le tissage

« מַעֲשֵׂה חֹשֵׁב יַעֲשֶׂה אֹתָהּ כְּרֻבִים » (Ex. 26:31) : deux grands keruvim face à face, qui
portent de leurs ailes levées une couronne, et deux lions assis entre leurs sabots —
« צִיּוּרִין שֶׁל בְּרִיּוֹת » (Rashi, ibid.). Le tout tissé dans les quatre matières, trois
laines et le lin — jamais d'or (le verset n'en liste que quatre), jamais brodé. Le
profil d'homme des keruvim est un contour sans trait (§9 de la fiche). Une figure
TISSÉE n'est pas un volume : elle bombe l'étoffe de quelques centimètres et s'en
distingue par la FACE du tissage qui la montre — « אֲרִיגָה שֶׁל שְׁתֵּי קִירוֹת » (Rashi,
ibid.), deux parois de fils dont l'une passe devant l'autre là où le dessin le veut.

La composition est un dessin validé, pas une construction : `tissages/parokhet_dessin.png`,
le rideau entier, 20 amot sur 40, fait avec gpt-image-2 (fal.ai) puis retouché
(têtes, lions). `--tisser` le fait redessiner sur fond vert, `tissages/parokhet.png`,
d'où la carte se lit ; les deux images sont la SOURCE, versionnées, parce qu'un modèle
ne rend jamais deux fois la même.

Une figure tissée est une image en couleur sur fond vert : sa couleur, en chaque
point, se ramène à la face du tissage la plus proche — le point du carré (clarté,
rougeur) dont la laine dosée lui ressemble le plus —, et sa luminance donne le
modelé, la distance au bord le bombé d'ensemble, comme pour une gravure.

Écrit `visite/matieres/parokhet_2048.webp`, une carte de 20 amot sur 40 — le rideau
entier, lu par la position de monde (y, z) : R porte la HAUTEUR du bombé, G la CLARTÉ
de la face (0 les laines sombres, 1 le lin), B sa ROUGEUR (0 tekhelet, 1 tola'at
shani), alpha le MASQUE de la figure. Deux axes de dosage plutôt qu'un index de face :
un index ne survit pas au filtrage — entre un lion clair et le fond, la moyenne des
deux textures voisines tombait sur une troisième couleur ; un dosage moyenné reste
un dosage. Et `visite/matieres/parokhet.json` : les quatre matières, les dosages des
faces et la palette qui en sort, que le blockout lit (`parokhet()`) ; la visite
(`visite/matieres.js`) porte la même palette en constantes. Le WebP est sans perte
(`beit_hamikdash_carte.py`). Demande `cwebp` sur le PATH, et FAL_AI_KEY (`.env`) pour
tisser. À relancer après toute modification du tissage, puis reconstruire.
"""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from beit_hamikdash_carte import (RACINE, SORTIE, bombe, distance, ecrire, flouter,  # noqa: E402
                                  lire_rgb, reechantillonner)

LARGEUR_PX = 2048
NOM = f"parokhet_{LARGEUR_PX}"
TISSAGES = RACINE / "tissages"
DESSIN = TISSAGES / "parokhet_dessin.png"
TISSAGE = TISSAGES / "parokhet.png"

# « אָרְכָּהּ אַרְבָּעִים אַמָּה וְרָחְבָּהּ עֶשְׂרִים אַמָּה » (Shekalim 8:5) : la carte est le rideau.
LARGEUR, HAUTEUR = 20.0, 40.0
# Le bombé se fond sur 4 cm : c'est un fil qui passe par-dessus, pas une arête.
FONDU = 0.04
# Le relief d'une figure tissée, en amot : la silhouette bombe sur RONDEUR depuis son
# bord, et la luminance, floutée de GRAIN pour ôter le grain du modèle, y ajoute le
# modelé pour PART_MODELE du tout — moins que sur une gravure : un fil couché ne creuse
# pas comme un ciseau.
RONDEUR, GRAIN, PART_MODELE = 0.45, 0.03, 0.35
# Le fond vert du modèle : ce qui n'est pas la figure. C'est la DOMINANCE du vert qui le
# reconnaît, d'au moins VERT sur le rouge et sur le bleu (valeurs du fichier) — aucune
# laine n'est verte.
VERT = 0.12

# Les quatre matières (Shekalim 8:5 ; Rashi Ex. 26:31), en linéaire : tekhelet, argaman,
# tola'at shani, lin — et les FACES du tissage, en dosage de ces quatre matières, aux
# coins d'un carré (clarté, rougeur) que la carte parcourt : le fond bleu-violet, le
# chaud cramoisi, le clair de lin, et le coin lin-cramoisi qu'un fondu atteint. Aucun
# dosage n'est pur : un rouge de tola'at seule et un lin blanc sur le violet faisaient
# un drapeau, pas une tapisserie — les teintes d'un lainage se tiennent de près.
LAINES = (("tekhelet", (0.10, 0.17, 0.48)), ("argaman", (0.40, 0.08, 0.30)),
          ("shani", (0.55, 0.08, 0.08)), ("lin", (0.86, 0.84, 0.78)))
# Le fond est de tekhelet avant tout : « תְּכֵלֶת דּוֹמֶה לַיָּם וְיָם דּוֹמֶה לָרָקִיעַ וְרָקִיעַ
# דּוֹמֶה לְכִסֵּא הַכָּבוֹד » (Menachot 43b) — c'est la couleur du Trône que le rideau du Devir
# porte, l'argaman ne fait que l'assombrir.
DOSAGES = {"fond": (0.62, 0.30, 0.08, 0.00), "chaud": (0.10, 0.35, 0.50, 0.05),
           "clair": (0.05, 0.05, 0.20, 0.70), "clair_chaud": (0.00, 0.10, 0.45, 0.45)}
JOUR = 0.75   # la laine teinte absorbe : le jour d'une étoffe lourde, sur les quatre faces
PALETTE = {face: tuple(JOUR * sum(p * rgb[k] for p, (_, rgb) in zip(parts, LAINES)) for k in range(3))
           for face, parts in DOSAGES.items()}

# Ce que l'on demande au modèle : redessiner le dessin validé tel quel, le fond seul en vert.
CONSIGNE_TISSAGE = (
    "Reproduce this woven tapestry EXACTLY — same figures, same outlines, same feather rows, same "
    "colours, same positions and sizes to the pixel, same weave texture on the figures — but replace "
    "the purple woven GROUND (every area of plain background cloth, including the background seen "
    "inside the crown's loops, between the wings and between the lions) with flat pure bright green "
    "#00FF00. The figures themselves (cherubim, wings, crown, lions, hooves) keep their colours, "
    "including their purple feathers. No border, no shadow.")


def couleur_face(clarte, rougeur):
    """La couleur linéaire d'un point du carré des faces : bilinéaire entre les coins."""
    coins = np.array([[PALETTE["fond"], PALETTE["chaud"]], [PALETTE["clair"], PALETTE["clair_chaud"]]])
    c, r = np.asarray(clarte)[..., None], np.asarray(rougeur)[..., None]
    return (1 - c) * ((1 - r) * coins[0, 0] + r * coins[0, 1]) + c * ((1 - r) * coins[1, 0] + r * coins[1, 1])


def tisser_dessin():
    """Fait redessiner le dessin validé sur fond vert par gpt-image-2 : `tissages/parokhet.png`."""
    sys.path.insert(0, str(RACINE / ".claude" / "skills" / "fal-video"))
    import fal_commun  # noqa: E402
    cle = fal_commun.cle_api()
    corps = {"prompt": CONSIGNE_TISSAGE, "image_urls": [fal_commun.televerse(str(DESSIN), cle)],
             "image_size": {"width": 1536, "height": 3072}, "quality": "high", "output_format": "png"}
    reponse = fal_commun.genere("openai/gpt-image-2/edit", corps, cle)
    fal_commun.telecharge(reponse["images"][0]["url"], str(TISSAGE))
    print(f"  tissé : {TISSAGE.relative_to(RACINE)}")


def faces_de(rgb, masque, pas=32):
    """La face du tissage la plus proche de chaque couleur : le point du carré (clarté,
    rougeur), au 1/`pas`, dont la laine dosée est la moins loin, en linéaire."""
    grille = (np.arange(pas + 1) / pas)
    clarte, rougeur = np.meshgrid(grille, grille, indexing="ij")
    candidats = couleur_face(clarte, rougeur).reshape(-1, 3)
    couleurs = rgb[masque]
    choix = np.empty(len(couleurs), dtype=np.int64)
    for debut in range(0, len(couleurs), 65536):
        tranche = couleurs[debut:debut + 65536]
        ecarts = ((tranche[:, None, :] - candidats[None, :, :]) ** 2).sum(axis=2)
        choix[debut:debut + 65536] = ecarts.argmin(axis=1)
    faces = np.zeros(masque.shape + (2,), dtype=np.float32)
    faces[masque] = np.stack([clarte.ravel()[choix], rougeur.ravel()[choix]], axis=1)
    return faces


def ramener_au_lin(lineaire, masque):
    """Le tissage au jour et au blanc de la palette : ses teintes les plus claires — son
    lin, le 5 % le plus lumineux de la figure — ramenées au lin de la palette, canal par
    canal. Le modèle tisse à son propre jour, un lin doré : sans ce calage son lin
    retombait sur une face à mi-clarté, et lin, cramoisi et pourpre se fondaient en un
    même lilas."""
    luminance = lineaire[masque].mean(axis=1)
    lin = lineaire[masque][luminance >= np.percentile(luminance, 95)].mean(axis=0)
    return lineaire * (np.array(PALETTE["clair"]) / lin)


def tisser():
    """(hauteur, faces, masque) : trois cartes de LARGEUR_PX sur le double, ligne 0 en bas ;
    les faces portent (clarté, rougeur) sur leur dernier axe. Le tissage couvre le rideau
    bord à bord : il se lit bilinéaire à la taille de la carte, sans cadrage. Ses figures
    ne sont pas une seule silhouette — le vert passe entre les lions, dans les boucles de
    la couronne —, aucun trou n'est donc bouché."""
    rgb = lire_rgb(TISSAGE)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dedans = ~((g > r + VERT) & (g > b + VERT))
    # Le bord de la figure emprunte au vert : deux pixels de moins, et rien n'y touche.
    dedans = distance(dedans, 2) >= 2
    largeur, hauteur = LARGEUR_PX, LARGEUR_PX * 2
    lignes = np.clip((np.arange(hauteur) + 0.5) * rgb.shape[0] / hauteur - 0.5, 0, rgb.shape[0] - 1.001)
    colonnes = np.clip((np.arange(largeur) + 0.5) * rgb.shape[1] / largeur - 0.5, 0, rgb.shape[1] - 1.001)
    masque = reechantillonner(dedans, lignes, colonnes) > 0.5
    lineaire = np.clip(reechantillonner(rgb, lignes, colonnes), 0, 1) ** 2.2
    echelle = largeur / LARGEUR
    rayon = max(1, int(round(RONDEUR * echelle)))
    volume = bombe(distance(masque, rayon) / rayon)
    modele = flouter(lineaire.mean(axis=2), max(1, int(round(GRAIN * echelle))))
    bas, haut = modele[masque].min(), modele[masque].max()
    modele = np.clip((modele - bas) / (haut - bas), 0.0, 1.0)
    relief = np.where(masque, (1.0 - PART_MODELE) * volume + PART_MODELE * modele, 0.0)
    faces = faces_de(ramener_au_lin(lineaire, masque), masque)
    fondu = max(1, round(FONDU * echelle))
    faces = np.stack([flouter(faces[..., k], fondu) for k in range(2)], axis=-1)
    return flouter(relief, fondu), faces, masque.astype(np.float32)


def ecrire_palette():
    fiche = {"laines": [[nom, list(rgb)] for nom, rgb in LAINES], "dosages": DOSAGES, "jour": JOUR,
             "palette": {face: [round(c, 4) for c in rgb] for face, rgb in PALETTE.items()}}
    (SORTIE / "parokhet.json").write_text(json.dumps(fiche, separators=(",", ":")), encoding="utf-8")
    for face, rgb in fiche["palette"].items():
        print(f"  {face:12s} {rgb}")


ARGUMENTS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if ARGUMENTS[:1] == ["--tisser"]:
    tisser_dessin()
elif __name__ == "__main__":
    relief, faces, masque = tisser()
    ecrire(NOM, relief, masque, faces)
    ecrire_palette()
