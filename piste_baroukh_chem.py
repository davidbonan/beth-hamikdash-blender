#!/usr/bin/env python3
"""Piste transparente du « Baroukh chem kevod malkhouto leolam vaed », mot à mot.

Sort un ProRes 4444 (yuva) 1920x1080 couvrant 3:39 → 3:48 du morceau : rien que
l'hébreu au centre, chaque mot apparaissant sur son attaque chantée.

    .venv/bin/python piste_baroukh_chem.py
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from bidi.algorithm import get_display

LARGEUR, HAUTEUR = 1920, 1080
FPS = 24

POLICE = "/System/Library/Fonts/SFHebrew.ttf"
TAILLE = 118
COULEUR = (255, 238, 205, 255)
CONTOUR = (0, 0, 0, 190)
EPAISSEUR_CONTOUR = 4

CENTRE_Y = 0.46
INTERLIGNE = 46
ECART_MOTS = 44
LARGEUR_UTILE = 1620

DEBUT_PISTE, FIN_PISTE = 219.000, 228.000
FIN_PHRASE, SORTIE = 226.600, 0.800
ENTREE = 0.28


@dataclass(frozen=True)
class Mot:
    texte: str
    attaque: float
    ligne: int


PHRASE = (
    Mot("בָּרוּךְ", 221.520, 0),
    Mot("שֵׁם", 222.720, 0),
    Mot("כְּבוֹד", 223.300, 0),
    Mot("מַלְכוּתוֹ", 223.900, 0),
    Mot("לְעוֹלָם", 225.020, 1),
    Mot("וָעֶד", 226.000, 1),
)


@dataclass(frozen=True)
class Calque:
    png: Path
    debut: float
    fin: float


def police_titre(taille: int) -> ImageFont.FreeTypeFont:
    police = ImageFont.truetype(POLICE, taille)
    try:
        police.set_variation_by_name("Bold")
    except OSError:
        pass
    return police


def ajuster(police: ImageFont.FreeTypeFont) -> ImageFont.FreeTypeFont:
    taille = police.size
    while taille > 40 and max(largeur_ligne(ligne, police_titre(taille))
                              for ligne in (0, 1)) > LARGEUR_UTILE:
        taille -= 4
    return police_titre(taille)


def mots_visuels(ligne: int) -> list[Mot]:
    return list(reversed([mot for mot in PHRASE if mot.ligne == ligne]))


def largeur_ligne(ligne: int, police: ImageFont.FreeTypeFont) -> float:
    mots = mots_visuels(ligne)
    return (sum(police.getlength(get_display(mot.texte)) for mot in mots)
            + ECART_MOTS * (len(mots) - 1))


def positions(police: ImageFont.FreeTypeFont) -> dict[str, tuple[float, float]]:
    haut, bas = police.getmetrics()
    hauteur_ligne = haut + bas
    sommet = HAUTEUR * CENTRE_Y - (2 * hauteur_ligne + INTERLIGNE) / 2
    places = {}
    for ligne in (0, 1):
        x = (LARGEUR - largeur_ligne(ligne, police)) / 2
        y = sommet + ligne * (hauteur_ligne + INTERLIGNE)
        for mot in mots_visuels(ligne):
            places[mot.texte] = (x, y)
            x += police.getlength(get_display(mot.texte)) + ECART_MOTS
    return places


def ombrer(image: Image.Image) -> Image.Image:
    ombre = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ombre.putalpha(image.getchannel("A").point(lambda a: int(a * 0.55)))
    ombre = ombre.filter(ImageFilter.GaussianBlur(12))
    fond = Image.new("RGBA", image.size, (0, 0, 0, 0))
    return Image.alpha_composite(Image.alpha_composite(fond, ombre), image)


def rendre_mot(mot: Mot, place: tuple[float, float], police: ImageFont.FreeTypeFont,
               png: Path) -> None:
    image = Image.new("RGBA", (LARGEUR, HAUTEUR), (0, 0, 0, 0))
    ImageDraw.Draw(image).text(place, get_display(mot.texte), font=police, fill=COULEUR,
                               stroke_width=EPAISSEUR_CONTOUR, stroke_fill=CONTOUR)
    ombrer(image).save(png)


def graphe(calques: list[Calque]) -> str:
    etapes, courant = [], "base"
    for index, calque in enumerate(calques, start=1):
        duree = calque.fin - calque.debut
        etapes.append(
            f"[{index}:v]format=rgba"
            f",fade=t=in:st=0:d={ENTREE}:alpha=1"
            f",fade=t=out:st={duree - SORTIE:.3f}:d={SORTIE}:alpha=1"
            f",setpts=PTS-STARTPTS+{calque.debut:.3f}/TB[c{index}]"
        )
        etapes.append(
            f"[{courant}][c{index}]overlay=x=0:y=0:eof_action=pass:format=auto[v{index}]"
        )
        courant = f"v{index}"
    return ";".join(etapes) + f";[{courant}]null[sortie]"


def encoder(calques: list[Calque], duree: float, destination: Path) -> None:
    entrees = ["-f", "lavfi", "-i",
               f"color=c=black@0.0:s={LARGEUR}x{HAUTEUR}:r={FPS}:d={duree:.3f},format=rgba"]
    for calque in calques:
        entrees += ["-loop", "1", "-framerate", str(FPS),
                    "-t", f"{calque.fin - calque.debut:.3f}", "-i", str(calque.png)]
    subprocess.run(
        ["ffmpeg", "-v", "error", "-stats", "-y", *entrees,
         "-filter_complex", f"[0:v]null[base];{graphe(calques)}",
         "-map", "[sortie]", "-t", f"{duree:.3f}",
         "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
         "-vendor", "apl0", "-alpha_bits", "16", str(destination)],
        check=True,
    )


def main() -> None:
    parseur = argparse.ArgumentParser()
    parseur.add_argument("--sortie", type=Path,
                         default=Path("renders/montage/piste_baroukh_chem_0339.mov"))
    options = parseur.parse_args()

    police = ajuster(police_titre(TAILLE))
    places = positions(police)

    dossier = options.sortie.parent / "baroukh_chem_png"
    dossier.mkdir(parents=True, exist_ok=True)

    calques = []
    for index, mot in enumerate(PHRASE, start=1):
        png = dossier / f"{index:02d}.png"
        rendre_mot(mot, places[mot.texte], police, png)
        calques.append(Calque(png, mot.attaque - DEBUT_PISTE,
                              FIN_PHRASE + SORTIE - DEBUT_PISTE))

    encoder(calques, FIN_PISTE - DEBUT_PISTE, options.sortie)
    print(f"piste : {options.sortie} — à poser à {DEBUT_PISTE:.3f} s (3:39,000), "
          f"{FIN_PISTE - DEBUT_PISTE:.2f} s, police {police.size} px")


if __name__ == "__main__":
    sys.exit(main())
