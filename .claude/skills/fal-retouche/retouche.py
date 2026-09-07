"""Correction ciblée d'une image déjà générée, sur fal.ai.

    python3 .claude/skills/fal-retouche/retouche.py --image renders/style/CAM_09A_debut_….png \
        --zone 38%,22%,18%,44% --instruction "la Menora a sept branches, pas neuf" --simulation

Le reste de l'image ne se regénère pas : ce qui sort du modèle est **recomposé** sur
l'original, seule la zone demandée est reprise (fondu sur les bords). Sans `--zone`,
l'image entière repasse au modèle et rien n'est recomposé.

Trois méthodes, `auto` choisit :

- `masque` — l'image entière part au modèle avec un masque alpha qui ouvre la zone.
  Réservé à `gpt2` : c'est le seul endpoint d'édition à prendre un `mask_url`. Le
  modèle voit tout le cadre et ne repeint que la zone.
- `decoupe` — seule la zone, élargie d'une marge, part au modèle, puis se recolle.
  Marche avec tous les modèles, et le modèle travaille à pleine résolution sur la
  zone : c'est le détail maximal, au prix du contexte perdu hors marge.
- `plein` — l'image entière, sans masque ni découpe. Avec une `--zone`, la sortie est
  quand même recomposée ; c'est le recours quand masque et découpe échouent.

Aucun de ces trois chemins n'a encore été mesuré l'un contre l'autre sur ce film.

`--reperes` écrit une copie quadrillée tous les 10 % pour lire les coordonnées d'une
zone avant de la demander.

ffmpeg fait le masque, la découpe et la recomposition ; la plomberie fal.ai (clé,
téléversement, file d'attente) est celle du skill `fal-video`.
"""

import argparse
import json
import os
import random
import re
import subprocess
import sys

SKILLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILLS, "fal-video"))

from fal_commun import RACINE, cle_api, genere, telecharge, televerse


# --- modèles ------------------------------------------------------------------

def images(reg):
    """L'image à corriger, puis la référence quand il y en a une."""
    return [reg["entree"]] + ([reg["reference"]] if reg["reference"] else [])


def charge_gpt(reg):
    """GPT Image 2 : ni seed ni prompt négatif, et le seul à prendre un masque."""
    charge = {
        "prompt": reg["instruction"],
        "image_urls": images(reg),
        "image_size": "auto",
        "quality": "high",
        "output_format": "png",
    }
    if reg["masque"]:
        charge["mask_url"] = reg["masque"]
    return charge


def charge_nano(reg):
    return {
        "prompt": reg["instruction"],
        "image_urls": images(reg),
        "resolution": "2K",
        "aspect_ratio": "auto",
        "output_format": "png",
        "safety_tolerance": "4",
        "seed": reg["seed"],
    }


MODELES = {
    "gpt2": {"endpoint": "openai/gpt-image-2/edit", "charge": charge_gpt, "masque": True},
    "nano-pro": {"endpoint": "fal-ai/nano-banana-pro/edit", "charge": charge_nano, "masque": False},
    "nano2": {"endpoint": "fal-ai/nano-banana-2/edit", "charge": charge_nano, "masque": False},
}

CONSIGNE = (
    "Edit this image with a single, strictly local correction. {instruction}. "
    "Everything else stays exactly as it is: same framing, same camera, same lens, "
    "same composition, same light, same colours, same materials, same grain, and every "
    "other object stays at its exact place, scale and orientation. Do not restyle, "
    "recrop, re-render or clean up the picture. Change nothing but what is asked."
)

CONSIGNE_MATIERE = (
    "Re-render this frame as a real photograph of a real place, keeping its drawing "
    "intact. {instruction}. The framing, the camera, the lens and the composition stay "
    "exactly as they are, every object keeps its exact place, scale, orientation and "
    "number, the curtain keeps its exact design, register layout, motifs and colours, "
    "and nothing is added, removed or moved: only materials, surface detail, light, "
    "atmosphere and lens character change. The four corners of the output match the "
    "four corners of the input."
)
CONSIGNES = {"detail": CONSIGNE, "matiere": CONSIGNE_MATIERE}

CONSIGNE_MASQUE = " Only the transparent area of the attached mask may change."
CONSIGNE_REFERENCE = (
    " A second image is attached for reference: another frame of the same film showing "
    "the same object as it must look. Copy its design, its pattern, its colours and its "
    "materials exactly, and nothing else from it — not its framing, not its lighting, "
    "not its camera, not its objects: the corrected area keeps the place, scale, "
    "perspective and light it has in the image being edited."
)
CONSIGNE_DECOUPE = (
    " This image is a crop of a larger frame: keep its edges continuous with what "
    "surrounds them, do not add a border, a vignette or a new background."
)


# --- ffmpeg -------------------------------------------------------------------

def ffmpeg(*arguments):
    commande = ["ffmpeg", "-y", "-loglevel", "error", *arguments]
    resultat = subprocess.run(commande, capture_output=True, text=True)
    if resultat.returncode:
        raise SystemExit(f"ffmpeg a échoué :\n{' '.join(commande)}\n{resultat.stderr[:600]}")


def dimensions(chemin):
    sortie = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", chemin],
        capture_output=True, text=True)
    if sortie.returncode:
        raise SystemExit(f"Image illisible : {chemin}")
    largeur, hauteur = sortie.stdout.strip().split(",")[:2]
    return int(largeur), int(hauteur)


def zone_en_pixels(valeur, largeur, hauteur):
    """« x,y,l,h » en pixels ou en pourcentages du cadre -> quatre entiers, bornés au cadre."""
    morceaux = [m.strip() for m in valeur.replace(" ", "").split(",")]
    if len(morceaux) != 4:
        raise SystemExit(f"--zone attend x,y,largeur,hauteur — reçu : {valeur}")
    reference = (largeur, hauteur, largeur, hauteur)
    nombres = []
    for morceau, plein in zip(morceaux, reference):
        try:
            nombre = float(morceau.rstrip("%"))
        except ValueError:
            raise SystemExit(f"--zone : « {morceau} » n'est pas un nombre") from None
        nombres.append(round(nombre * plein / 100) if morceau.endswith("%") else round(nombre))
    return borne(nombres, largeur, hauteur)


def borne(zone, largeur, hauteur):
    x, y, l, h = zone
    x, y = max(0, min(x, largeur - 1)), max(0, min(y, hauteur - 1))
    l, h = max(1, min(l, largeur - x)), max(1, min(h, hauteur - y))
    return x, y, l, h


def elargie(zone, marge, largeur, hauteur):
    """La zone plus une marge proportionnelle à sa taille, de chaque côté."""
    x, y, l, h = zone
    dx, dy = round(l * marge), round(h * marge)
    return borne((x - dx, y - dy, l + 2 * dx, h + 2 * dy), largeur, hauteur)


def masque_alpha(zone, largeur, hauteur, chemin):
    """Masque d'édition d'OpenAI : opaque partout, **transparent** sur la zone à reprendre."""
    x, y, l, h = zone
    ffmpeg("-f", "lavfi", "-i", f"color=c=black:s={largeur}x{hauteur}",
           "-vf", f"format=rgba,drawbox=x={x}:y={y}:w={l}:h={h}:color=black@0.0:t=fill:replace=1",
           "-frames:v", "1", chemin)
    return chemin


def masque_fondu(zone, largeur, hauteur, fondu, chemin):
    """Masque de recomposition : blanc sur la zone, noir ailleurs, bords adoucis."""
    x, y, l, h = zone
    ffmpeg("-f", "lavfi", "-i", f"color=c=black:s={largeur}x{hauteur}",
           "-vf", f"drawbox=x={x}:y={y}:w={l}:h={h}:color=white:t=fill,gblur=sigma={fondu}",
           "-frames:v", "1", chemin)
    return chemin


def decoupe_image(source, zone, chemin):
    x, y, l, h = zone
    ffmpeg("-i", source, "-vf", f"crop={l}:{h}:{x}:{y}", "-frames:v", "1", chemin)
    return chemin


def recolle(source, morceau, zone, chemin):
    """Remet le morceau retouché à sa place dans le cadre entier, à sa taille d'origine."""
    x, y, l, h = zone
    ffmpeg("-i", source, "-i", morceau,
           "-filter_complex", f"[1:v]scale={l}:{h}[m];[0:v][m]overlay=x={x}:y={y}",
           "-frames:v", "1", chemin)
    return chemin


def recompose(origine, produit, masque, chemin):
    """L'original, sauf là où le masque est blanc : là, l'image produite."""
    largeur, hauteur = dimensions(origine)
    ffmpeg("-i", origine, "-i", produit, "-i", masque,
           "-filter_complex",
           f"[1:v]scale={largeur}:{hauteur},format=rgb24[p];"
           f"[0:v]format=rgb24[o];[2:v]format=rgb24[m];[o][p][m]maskedmerge",
           "-frames:v", "1", chemin)
    return chemin


def quadrille(source, chemin):
    """Copie quadrillée tous les 10 %, médianes marquées : de quoi lire une --zone."""
    largeur, hauteur = dimensions(source)
    ffmpeg("-i", source, "-vf",
           f"drawgrid=w={largeur / 10}:h={hauteur / 10}:t=2:color=red@0.7,"
           f"drawgrid=w={largeur / 2}:h={hauteur / 2}:t=6:color=cyan@0.9",
           "-frames:v", "1", chemin)
    return chemin


# --- sortie -------------------------------------------------------------------

def travail(dossier, nom):
    """Les fichiers de fabrication — masque, découpe, fondu — hors du dossier de rendus."""
    chemin = os.path.join(dossier, "travail")
    os.makedirs(chemin, exist_ok=True)
    return os.path.join(chemin, nom)


RETOUCHE_FINALE = re.compile(r"_retouche(\d+)_([A-Za-z0-9.\-]+)$")


def chemin_libre(dossier, base, modele):
    """Une retouche du même modèle **compte** au lieu de s'empiler.

    Une chaîne qui rempile `_retouche1_gpt2` à chaque passe dépasse les 255 octets
    de nom de fichier au bout d'une quinzaine (macOS, `OSError: File name too long`),
    et la génération est perdue après avoir été payée. Le suffixe du même modèle est
    donc absorbé — `_retouche13_gpt2` devient `_retouche14_gpt2` ; un changement de
    modèle ouvre un nouveau segment, qui garde l'historique lisible.
    """
    os.makedirs(dossier, exist_ok=True)
    depart = 1
    marque = RETOUCHE_FINALE.search(base)
    if marque and marque.group(2) == modele:
        depart = int(marque.group(1)) + 1
        base = base[: marque.start()]
    for index in range(depart, 100):
        chemin = os.path.join(dossier, f"{base}_retouche{index}_{modele}.png")
        if not os.path.exists(chemin):
            return chemin
    raise SystemExit(f"Cent retouches de {base} : nettoyer {dossier}")


def relatif(chemin):
    return os.path.relpath(chemin, RACINE) if chemin.startswith(RACINE) else chemin


# --- ligne de commande --------------------------------------------------------

def arguments():
    analyseur = argparse.ArgumentParser(description="Correction ciblée d'une image sur fal.ai")
    analyseur.add_argument("--image", required=True, help="image à retoucher")
    analyseur.add_argument("--instruction", help="la correction, en une phrase ; ce qui n'est pas nommé ne bouge pas")
    analyseur.add_argument("--reference",
                           help="frame déjà validée portant l'objet tel qu'il doit être : "
                                "sa matière est copiée, jamais son cadrage ni sa lumière")
    analyseur.add_argument("--zone", help="x,y,largeur,hauteur, en pixels ou en %% du cadre (« 38%%,22%%,18%%,44%% »)")
    analyseur.add_argument("--methode", choices=("auto", "masque", "decoupe", "plein"), default="auto")
    analyseur.add_argument("--portee", choices=sorted(CONSIGNES), default="detail",
                           help="detail : une correction locale, tout le reste figé (défaut) ; "
                                "matiere : rendu photo de toute la zone, dessin et cadrage figés")
    analyseur.add_argument("--modele", choices=sorted(MODELES), default="gpt2")
    analyseur.add_argument("--marge", type=float, default=0.25,
                           help="marge de contexte autour de la zone découpée, en part de sa taille")
    analyseur.add_argument("--fondu", type=float, default=12,
                           help="adoucissement du raccord, en pixels ; 0 = raccord net")
    analyseur.add_argument("--sans-recomposition", action="store_true",
                           help="garde la sortie du modèle telle quelle, sans la recoller sur l'original")
    analyseur.add_argument("--seed", type=int, help="nano* seulement ; ailleurs ne sert qu'à nommer")
    analyseur.add_argument("--sortie", help="dossier de sortie (défaut : celui de l'image)")
    analyseur.add_argument("--reperes", action="store_true",
                           help="écrit une copie quadrillée et s'arrête : pour lire une zone")
    analyseur.add_argument("--simulation", action="store_true",
                           help="prépare masque et découpe, affiche la charge utile, ne génère pas")
    return analyseur.parse_args()


def methode_choisie(demandee, zone, modele):
    if demandee != "auto":
        return demandee
    if not zone:
        return "plein"
    return "masque" if MODELES[modele]["masque"] else "decoupe"


def main():
    args = arguments()
    if not os.path.exists(args.image):
        raise SystemExit(f"Image absente : {args.image}")
    dossier = args.sortie or os.path.dirname(os.path.abspath(args.image))
    base = os.path.splitext(os.path.basename(args.image))[0]
    largeur, hauteur = dimensions(args.image)

    if args.reperes:
        chemin = travail(dossier, f"{base}_reperes.png")
        print(f"{relatif(quadrille(args.image, chemin))} — grille tous les 10 %, "
              f"médianes en cyan ({largeur}x{hauteur})")
        return
    if not args.instruction:
        raise SystemExit("--instruction est requise (sauf avec --reperes)")

    modele = MODELES[args.modele]
    zone = zone_en_pixels(args.zone, largeur, hauteur) if args.zone else None
    methode = methode_choisie(args.methode, zone, args.modele)
    if methode != "plein" and not zone:
        raise SystemExit(f"La méthode « {methode} » demande une --zone")
    if methode == "masque" and not modele["masque"]:
        raise SystemExit(f"{args.modele} ne prend pas de masque : --methode decoupe ou plein")
    seed = args.seed if args.seed is not None else random.randint(1, 2**31 - 1)

    if args.reference and not os.path.exists(args.reference):
        raise SystemExit(f"Référence absente : {args.reference}")

    instruction = CONSIGNES[args.portee].format(instruction=args.instruction.rstrip("."))
    if args.reference:
        instruction += CONSIGNE_REFERENCE
    entree, masque = args.image, None
    cadre = zone
    if methode == "masque":
        instruction += CONSIGNE_MASQUE
        masque = masque_alpha(zone, largeur, hauteur, travail(dossier, f"{base}_masque.png"))
    elif methode == "decoupe":
        instruction += CONSIGNE_DECOUPE
        cadre = elargie(zone, args.marge, largeur, hauteur)
        entree = decoupe_image(args.image, cadre, travail(dossier, f"{base}_decoupe.png"))

    print(f"{relatif(args.image)} · {largeur}x{hauteur} · {args.modele} · {methode} · {args.portee} · seed {seed}")
    if zone:
        print(f"  zone       : {zone[0]},{zone[1]} {zone[2]}x{zone[3]} px"
              + (f" · découpe {cadre[2]}x{cadre[3]} à {cadre[0]},{cadre[1]}" if methode == "decoupe" else ""))
    if masque:
        print(f"  masque     : {relatif(masque)}")
    if entree != args.image:
        print(f"  entrée     : {relatif(entree)}")
    if args.reference:
        print(f"  référence  : {relatif(os.path.abspath(args.reference))}")
    print(f"  instruction: {instruction}")

    reglages = {"instruction": instruction, "entree": "<entrée>", "masque": "<masque>" if masque else None,
                "reference": "<référence>" if args.reference else None, "seed": seed}
    if args.simulation:
        print(json.dumps(modele["charge"](reglages), indent=2, ensure_ascii=False))
        return

    cle = cle_api()
    reglages["entree"] = televerse(entree, cle)
    if args.reference:
        reglages["reference"] = televerse(args.reference, cle)
    if masque:
        reglages["masque"] = televerse(masque, cle)
    resultat = genere(modele["endpoint"], modele["charge"](reglages), cle)
    if not resultat.get("images"):
        raise SystemExit(f"Réponse sans image : {json.dumps(resultat, ensure_ascii=False)[:400]}")

    sortie = chemin_libre(dossier, base, args.modele)
    brut = telecharge(resultat["images"][0]["url"], sortie.replace(".png", "_brut.png"))
    if args.sans_recomposition or not zone:
        os.replace(brut, sortie)
        print(sortie, flush=True)
        return

    produit = recolle(args.image, brut, cadre, travail(dossier, f"{base}_recolle.png")) \
        if methode == "decoupe" else brut
    fondu = masque_fondu(zone, largeur, hauteur, max(args.fondu, 0.1),
                         travail(dossier, f"{base}_fondu.png"))
    recompose(args.image, produit, fondu, sortie)
    print(f"{sortie}\n  sortie brute du modèle : {relatif(brut)}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
