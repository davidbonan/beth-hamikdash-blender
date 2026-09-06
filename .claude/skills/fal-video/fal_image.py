"""Stylise une frame clé d'un plan sur fal.ai : génération conditionnée par la profondeur.

    python3 .claude/skills/fal-video/fal_image.py --plan 9 --frame debut
    python3 .claude/skills/fal-video/fal_image.py --plan 9 --frame fin --modele pro-depth --seed 90901

Le prompt est lu dans `prompts_par_plan.md` : bloc STYLE commun + ligne **Prompt** du
plan ; la force i2i par défaut est la ligne **Force** du plan. Flux n'accepte aucun
prompt négatif — le bloc NÉGATIF ne sert qu'au contrôle visuel après coup.

Plusieurs valeurs de `--controle` génèrent autant de variantes **à seed identique** :
seul le poids du conditionnement change, ce qui rend les variantes comparables.

Modèles (`--modele`), la famille édition mesurée sur les plans 1, 4 et 5, les
`depth*` sur le plan 9 :

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
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fal_commun import (DOSSIER_IMAGES, RACINE, bloc_commun, camera_du_plan, champ, cle_api,
                        numero_de_plan,
                        genere, negatif_du_plan, section_plan, telecharge, televerse,
                        texte_prompts)

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
    couleur ne porte plus rien : dans un couloir fermé comme la Stoa du plan 2, toutes
    les surfaces du blockout sont blanches et l'ambiante les met au même gris — la
    colonnade est invisible en couleur alors qu'elle est nette en profondeur.
    """
    return [reg["couleur"], reg["profondeur"]] if reg["structure"] else [reg["couleur"]]


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


# --- plan ---------------------------------------------------------------------

def force_du_plan(section, plan):
    ligne = champ(section, "Force")
    trouve = re.match(r"([0-9]+[.,][0-9]+)", ligne or "")
    if not trouve:
        raise SystemExit(f"Plan {plan} : ligne **Force** absente ou illisible")
    return float(trouve.group(1).replace(",", "."))


def lit_plan(plan, etiquette):
    """(camera, {image, edition}, négatif complet, force i2i) pour une frame d'un plan.

    `image` conditionne une génération (la profondeur porte la géométrie), `edition`
    demande à un modèle d'édition de repeindre le blockout sans rien y déplacer.

    Une frame dont le cadre ne montre plus la scène du plan (le tilt final du plan 9,
    par exemple) a sa propre ligne **Prompt fin** : décrire les kelim quand ils sont
    sortis du cadre revient à demander au modèle de les réinventer. **Édition fin** et
    **Édition finale fin** suivent la même règle — au plan 8, la façade de marbre et le
    plafond de cèdre que décrit **Édition** ont quitté le cadre à la fin.

    Un plan dont le blockout laisse du vide autour de la scène (les extérieurs :
    ciel, ville, vallée) ajoute une ligne **Édition** : sans elle, l'instruction
    « ne rien ajouter » fait repeindre ce vide en aplat de ciel.
    """
    texte = texte_prompts()
    section = section_plan(texte, plan)
    prompt = champ(section, f"Prompt {etiquette}") or champ(section, "Prompt")
    if not prompt:
        raise SystemExit(f"Plan {plan} : ligne **Prompt** absente")
    prompt = prompt.replace("STYLE +", bloc_commun(texte, "STYLE"), 1)
    # Aucun modèle d'édition ne prend de prompt négatif : les interdits passent dans
    # l'instruction, sinon le bloc NÉGATIF ne sert à rien.
    negatif = negatif_du_plan(texte, section)
    hors_scene = champ(section, f"Édition {etiquette}") or champ(section, "Édition")
    # Qui est là et où : les deux blocs valent pour tout le film, pas pour un plan.
    qui = f'{bloc_commun(texte, "FIGURES")} {bloc_commun(texte, "PLACES")}'
    # La contrainte d'un plan que le modèle lâche depuis le milieu de l'instruction
    # se remet ici, juste avant le CADRAGE, seule place où elle tient encore.
    finale = (champ(section, f"Édition finale {etiquette}")
              or champ(section, "Édition finale"))
    # CADRAGE en dernier : une contrainte de cadre placée au milieu se fait diluer.
    edition = (f'{bloc_commun(texte, "ÉDITION")} {prompt}.'
               f'{" " + hors_scene if hors_scene else ""}'
               f' {qui}'
               f' Never show any of these: {negatif}.'
               f'{" " + finale if finale else ""}'
               f' {bloc_commun(texte, "CADRAGE")}')
    prompts = {"image": f'{prompt}. {qui}', "edition": edition}
    return camera_du_plan(section), prompts, negatif, force_du_plan(section, plan)


PHRASE_STRUCTURE = (
    " A second image is attached: the depth map of this very same frame, near in white"
    " and far in black. Read the geometry from it — every column, figure and edge is"
    " there — and light the scene yourself: the grey render carries the layout, not the"
    " light."
)


def images_de_frame(camera, etiquette):
    """(rendu couleur, carte de profondeur) de la frame `debut` ou `fin`."""
    base = os.path.join(DOSSIER_IMAGES, f"{camera}_{etiquette}")
    couleur, profondeur = base + ".png", base + "_profondeur.png"
    for chemin in (couleur, profondeur):
        if not os.path.exists(chemin):
            raise SystemExit(f"Image absente : {chemin} — lancer beit_hamikdash_export_controlnet.py")
    return couleur, profondeur


def arguments():
    analyseur = argparse.ArgumentParser(description="Stylisation d'une frame clé sur fal.ai")
    analyseur.add_argument("--plan", type=numero_de_plan, required=True,
                           help="numéro de plan (1-15, avec la lettre pour un plan coupé : 9a)")
    analyseur.add_argument("--frame", choices=("debut", "fin"), default="debut")
    analyseur.add_argument("--modele", choices=sorted(MODELES), default="gpt2")
    analyseur.add_argument("--controle", type=float, nargs="+", default=[1.0],
                           help="poids du conditionnement ; une valeur = une variante")
    analyseur.add_argument("--force", type=float, help="force i2i (défaut : ligne **Force** du plan)")
    analyseur.add_argument("--seed", type=int, help="défaut : tirée au hasard, partagée par les variantes")
    analyseur.add_argument("--etapes", type=int, default=28, help="num_inference_steps")
    analyseur.add_argument("--guidage", type=float, default=3.5, help="guidance_scale")
    analyseur.add_argument("--union", default=UNION, help="poids du ControlNet Union (general-depth)")
    analyseur.add_argument("--structure", action="store_true",
                           help="joint la carte de profondeur en seconde image (rendu couleur sans relief)")
    analyseur.add_argument("--sortie", default=DOSSIER_SORTIE)
    analyseur.add_argument("--simulation", action="store_true", help="affiche la charge utile sans générer")
    return analyseur.parse_args()


def main():
    args = arguments()
    modele = MODELES[args.modele]
    camera, prompts, negatif, force_plan = lit_plan(args.plan, args.frame)
    prompt = prompts[modele.get("prompt", "image")]
    if args.structure:
        prompt += PHRASE_STRUCTURE
    force = args.force if args.force is not None else force_plan
    seed = args.seed if args.seed is not None else random.randint(1, 2**31 - 1)
    couleur, profondeur = images_de_frame(camera, args.frame)

    print(f"plan {args.plan} · {camera} · frame {args.frame} · {args.modele} "
          f"· guidage {args.guidage} · seed {seed}")
    print(f"  couleur    : {os.path.relpath(couleur, RACINE)}")
    print(f"  profondeur : {os.path.relpath(profondeur, RACINE)}")
    print(f"  prompt     : {prompt}")

    reglages = {"prompt": prompt, "negatif": negatif, "force": force, "seed": seed,
                "etapes": args.etapes, "guidage": args.guidage,
                "couleur": "<couleur>", "profondeur": "<profondeur>", "controle": args.controle[0],
                "union": args.union, "structure": args.structure}

    if args.simulation:
        print(json.dumps(modele["charge"](reglages), indent=2, ensure_ascii=False))
        return

    cle = cle_api()
    reglages["couleur"] = televerse(couleur, cle)
    reglages["profondeur"] = televerse(profondeur, cle)
    for controle in args.controle:
        reglages["controle"] = controle
        resultat = genere(modele["endpoint"], modele["charge"](reglages), cle)
        if not resultat.get("images"):
            raise SystemExit(f"Réponse sans image : {json.dumps(resultat, ensure_ascii=False)[:400]}")
        nom = f"{camera}_{args.frame}_{args.modele}_c{controle:.2f}_g{args.guidage:g}_seed{seed}.png"
        print(telecharge(resultat["images"][0]["url"], os.path.join(args.sortie, nom)), flush=True)


if __name__ == "__main__":
    sys.exit(main())
