"""Stylise une frame clé d'un plan sur fal.ai : génération conditionnée par la profondeur.

    python3 .claude/skills/fal-video/fal_image.py --camera CAM_03_Heikhal --frame debut \
        --prompt "..."

Le prompt se donne en entier sur la ligne de commande : c'est lui qui décrit la
matière, la lumière et les gens du cadre. Les modèles d'édition (`gpt2`, `nano*`,
`seedream`, `flux2-pro`) repeignent le rendu Blender sans le recomposer ; les modèles
`depth*` génèrent depuis la carte de profondeur. Flux n'accepte aucun prompt négatif :
`--negatif` ne sert qu'aux endpoints qui en prennent un.

Deux frames d'un même plan se stylisent **à seed identique** : c'est ce qui donne à
l'i2v deux images de la même matière. Plusieurs valeurs de `--controle` génèrent
autant de variantes à seed identique, seul le poids du conditionnement changeant.

Modèles (`--modele`), mesurés sur les extérieurs pour la famille édition et sur
l'intérieur du Heikhal pour les `depth*` :

- `gpt2` — `openai/gpt-image-2/edit`, défaut : le seul des six modèles d'édition à
  laisser plane une façade plane et à ne pas recomposer le cadre. Ni seed ni prompt
  négatif : la seed ne sert qu'à nommer le fichier.

- `pro-depth` — `fal-ai/flux-pro/v1/depth`, conditionné par la carte de profondeur.
- `pro-depth-rendu` — même endpoint, mais conditionné par le rendu couleur : cet
  endpoint estime lui-même la profondeur de l'image de contrôle, et un blockout gris
  lui donne une estimation propre.
- `depth` — `fal-ai/flux-control-lora-depth` : correct à `--controle 1.0`, la
  géométrie flotte ; à 1.2 la structure tient mais le style part en granité doré ;
  à 1.5 l'image s'effondre en bruit.
- `depth-i2i` — le même avec le rendu Blender en image d'init : la sortie reste le
  blockout à peine retouché, quelle que soit la force (0,50 comme 1,00).

`preprocess_depth` est coupé sur les endpoints qui l'acceptent : l'entrée est déjà
une carte de profondeur, il ne faut pas en réestimer une par-dessus.
"""

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fal_commun import RACINE, cle_api, genere, images_de_frame, telecharge, televerse

DOSSIER_SORTIE = os.path.join(RACINE, "renders", "style")
LARGEUR, HAUTEUR = 1920, 1080


# --- modèles ------------------------------------------------------------------

UNION = "Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0"


def charge_lora(reg):
    return {
        "prompt": reg["prompt"],
        "control_lora_image_url": reg["profondeur"],
        "control_lora_strength": reg["controle"],
        "preprocess_depth": False,   # l'entrée EST la carte de profondeur
        "image_size": {"width": LARGEUR, "height": HAUTEUR},
        "num_inference_steps": reg["etapes"],
        "guidance_scale": reg["guidage"],
        "output_format": "png",
        "seed": reg["seed"],
    }


def charge_lora_i2i(reg):
    return dict(charge_lora(reg), image_url=reg["couleur"], strength=reg["force"])


def charge_pro(reg, controle):
    return {
        "prompt": reg["prompt"],
        "control_image_url": controle,
        "image_size": {"width": LARGEUR, "height": HAUTEUR},
        "num_inference_steps": reg["etapes"],
        "guidance_scale": reg["guidage"],
        "output_format": "png",
        "safety_tolerance": "4",
        "seed": reg["seed"],
    }


def charge_general(reg):
    """Seul endpoint qui prenne un prompt négatif : le bloc NÉGATIF du film sert enfin."""
    return {
        "prompt": reg["prompt"],
        "negative_prompt": reg["negatif"],
        "use_real_cfg": True,        # sans CFG classique, le négatif est ignoré
        "real_cfg_scale": 3.5,
        "controlnet_unions": [{
            "path": reg["union"],
            "controls": [{
                "control_image_url": reg["profondeur"],
                "control_mode": "depth",
                "conditioning_scale": reg["controle"],
            }],
        }],
        "image_size": {"width": LARGEUR, "height": HAUTEUR},
        "num_inference_steps": reg["etapes"],
        "guidance_scale": reg["guidage"],
        "output_format": "png",
        "seed": reg["seed"],
    }


def charge_canny(reg):
    """Contours du blockout : les kelim y sont nets, là où la profondeur les noie."""
    return {
        "prompt": reg["prompt"],
        "control_lora_image_url": reg["couleur"],
        "control_lora_strength": reg["controle"],
        "image_size": {"width": LARGEUR, "height": HAUTEUR},
        "num_inference_steps": reg["etapes"],
        "guidance_scale": reg["guidage"],
        "output_format": "png",
        "seed": reg["seed"],
    }


def images_entree(reg):
    """Les images données au modèle d'édition.

    `structure` ajoute la carte de profondeur en seconde image. Utile là où le rendu
    couleur ne porte plus rien : dans un couloir fermé comme la nef du portique sud, toutes
    les surfaces du blockout sont blanches et l'ambiante les met au même gris — la
    colonnade est invisible en couleur alors qu'elle est nette en profondeur.
    """
    images = [reg["couleur"], reg["profondeur"]] if reg["structure"] else [reg["couleur"]]
    return images + [reg["reference"]] if reg["reference"] else images


def charge_nano(reg):
    """Nano Banana : édition instruite, 2K, la géométrie du blockout est conservée telle quelle."""
    return {
        "prompt": reg["prompt"],
        "image_urls": images_entree(reg),
        "resolution": "2K",
        "aspect_ratio": "16:9",
        "output_format": "png",
        "safety_tolerance": "4",
        "seed": reg["seed"],
    }


def charge_seedream(reg):
    return {
        "prompt": reg["prompt"],
        "image_urls": images_entree(reg),
        "image_size": "auto_2K",
        "output_format": "png",
    }


def charge_flux2(reg):
    return {
        "prompt": reg["prompt"],
        "image_urls": images_entree(reg),
        "image_size": "auto",
        "output_format": "png",
        "seed": reg["seed"],
    }


def charge_gpt(reg):
    """GPT Image 2 : ni seed ni prompt négatif ; `quality` décide seule du prix."""
    return {
        "prompt": reg["prompt"],
        "image_urls": images_entree(reg),
        "image_size": "auto",
        "quality": "high",
        "output_format": "png",
    }


MODELES = {
    "nano-pro": {
        "endpoint": "fal-ai/nano-banana-pro/edit",
        "charge": charge_nano,
        "prompt": "edition",
    },
    "nano2": {
        "endpoint": "fal-ai/nano-banana-2/edit",
        "charge": charge_nano,
        "prompt": "edition",
    },
    "seedream": {
        "endpoint": "bytedance/seedream/v5/pro/edit",
        "charge": charge_seedream,
        "prompt": "edition",
    },
    "seedream-lite": {
        "endpoint": "fal-ai/bytedance/seedream/v5/lite/edit",
        "charge": charge_seedream,
        "prompt": "edition",
    },
    "gpt2": {
        "endpoint": "openai/gpt-image-2/edit",
        "charge": charge_gpt,
        "prompt": "edition",
    },
    "flux2-pro": {
        "endpoint": "fal-ai/flux-2-pro/edit",
        "charge": charge_flux2,
        "prompt": "edition",
    },
    "canny": {
        "endpoint": "fal-ai/flux-control-lora-canny",
        "charge": charge_canny,
    },
    "general-depth": {
        "endpoint": "fal-ai/flux-general",
        "charge": charge_general,
    },
    "pro-depth": {
        "endpoint": "fal-ai/flux-pro/v1/depth",
        "charge": lambda reg: charge_pro(reg, reg["profondeur"]),
    },
    "pro-depth-rendu": {
        "endpoint": "fal-ai/flux-pro/v1/depth",
        "charge": lambda reg: charge_pro(reg, reg["couleur"]),
    },
    "depth": {
        "endpoint": "fal-ai/flux-control-lora-depth",
        "charge": charge_lora,
    },
    "depth-i2i": {
        "endpoint": "fal-ai/flux-control-lora-depth/image-to-image",
        "charge": charge_lora_i2i,
    },
}


PHRASE_STRUCTURE = (
    " A second image is attached: the depth map of this very same frame, near in white"
    " and far in black. Read the geometry from it — every column, figure and edge is"
    " there — and light the scene yourself: the grey render carries the layout, not the"
    " light."
)


PHRASE_REFERENCE = (
    " The last attached image is this very same Temple already painted at the same hour"
    " from another angle, and it is the reference for every material: match its stone,"
    " its gold ornaments, its curtain, its smoke, its sky, its light and the grain of its"
    " crowds exactly, so that the two pictures read as two frames of one continuous shot."
    " Take colours, textures and light from it — never its composition, which is the"
    " first image's alone."
)


def arguments():
    analyseur = argparse.ArgumentParser(description="Stylisation d'une frame clé sur fal.ai")
    analyseur.add_argument("--camera", required=True,
                           help="nom de la caméra, tel qu'il est dans cameras.json")
    analyseur.add_argument("--frame", choices=("debut", "fin"), default="debut")
    analyseur.add_argument("--prompt", required=True,
                           help="ce que le cadre doit devenir : matière, lumière, gens")
    analyseur.add_argument("--negatif", default="",
                           help="prompt négatif (general-depth seul en tient compte)")
    analyseur.add_argument("--modele", choices=sorted(MODELES), default="gpt2")
    analyseur.add_argument("--controle", type=float, nargs="+", default=[1.0],
                           help="poids du conditionnement ; une valeur = une variante")
    analyseur.add_argument("--force", type=float, default=0.85, help="force i2i (depth-i2i seul)")
    analyseur.add_argument("--seed", type=int, help="défaut : tirée au hasard, partagée par les variantes")
    analyseur.add_argument("--etapes", type=int, default=28, help="num_inference_steps")
    analyseur.add_argument("--guidage", type=float, default=3.5, help="guidance_scale")
    analyseur.add_argument("--union", default=UNION, help="poids du ControlNet Union (general-depth)")
    analyseur.add_argument("--structure", action="store_true",
                           help="joint la carte de profondeur en seconde image (rendu couleur sans relief)")
    analyseur.add_argument("--reference",
                           help="frame stylisée déjà validée d'un plan voisin, jointe en dernière image : "
                                "le modèle y prend la matière, pas la composition")
    analyseur.add_argument("--sortie", default=DOSSIER_SORTIE)
    analyseur.add_argument("--simulation", action="store_true", help="affiche la charge utile sans générer")
    return analyseur.parse_args()


def main():
    args = arguments()
    modele = MODELES[args.modele]
    prompt = args.prompt
    if args.structure:
        prompt += PHRASE_STRUCTURE
    if args.reference:
        prompt += PHRASE_REFERENCE
    seed = args.seed if args.seed is not None else random.randint(1, 2**31 - 1)
    couleur, profondeur = images_de_frame(args.camera, args.frame)

    print(f"{args.camera} · frame {args.frame} · {args.modele} "
          f"· guidage {args.guidage} · seed {seed}")
    print(f"  couleur    : {os.path.relpath(couleur, RACINE)}")
    print(f"  profondeur : {os.path.relpath(profondeur, RACINE)}")
    print(f"  prompt     : {prompt}")

    reglages = {"prompt": prompt, "negatif": args.negatif, "force": args.force, "seed": seed,
                "etapes": args.etapes, "guidage": args.guidage,
                "couleur": "<couleur>", "profondeur": "<profondeur>", "controle": args.controle[0],
                "union": args.union, "structure": args.structure,
                "reference": "<reference>" if args.reference else None}

    if args.simulation:
        print(json.dumps(modele["charge"](reglages), indent=2, ensure_ascii=False))
        return

    cle = cle_api()
    reglages["couleur"] = televerse(couleur, cle)
    reglages["profondeur"] = televerse(profondeur, cle)
    if args.reference:
        reglages["reference"] = televerse(args.reference, cle)
    for controle in args.controle:
        reglages["controle"] = controle
        resultat = genere(modele["endpoint"], modele["charge"](reglages), cle)
        if not resultat.get("images"):
            raise SystemExit(f"Réponse sans image : {json.dumps(resultat, ensure_ascii=False)[:400]}")
        nom = (f"{args.camera}_{args.frame}_{args.modele}{'_ref' if args.reference else ''}"
               f"_c{controle:.2f}_g{args.guidage:g}_seed{seed}.png")
        print(telecharge(resultat["images"][0]["url"], os.path.join(args.sortie, nom)), flush=True)


if __name__ == "__main__":
    sys.exit(main())
