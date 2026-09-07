"""Génère un plan vidéo sur fal.ai depuis la ligne de commande, sans passer par le site.

    python3 .claude/skills/fal-video/fal_video.py --plan 8
    python3 .claude/skills/fal-video/fal_video.py --plan 9 --modele kling --duree 10

Le prompt et le négatif sont lus dans `prompts_par_plan.md` : la ligne **Mouvement**
du plan (le prompt i2v ne décrit que la caméra) et le bloc NÉGATIF commun complété
par le négatif du plan. Les images de départ et de fin viennent de `renders/blockout/`.

La plomberie fal.ai et la lecture du markdown sont dans `fal_commun.py`.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fal_commun import (RACINE, bloc_commun, bloc_texte, camera_du_plan, champ, cle_api,
                        figures_du_plan,
                        numero_de_plan,
                        genere, images_du_plan, negatif_du_plan, section_plan, telecharge,
                        televerse, texte_prompts)

DOSSIER_SORTIE = os.path.join(RACINE, "renders", "video")


# --- modèles -----------------------------------------------------------------

def charge_veo(depart, fin, prompt, negatif, duree, seed):
    corps = {
        "prompt": prompt,
        "first_frame_url": depart,
        "last_frame_url": fin,
        "aspect_ratio": "16:9",
        "duration": f"{duree}s",
        "resolution": "1080p",
        "generate_audio": False,     # la bande-son est le morceau, pas du son généré
        "negative_prompt": negatif,
    }
    if seed is not None:
        corps["seed"] = seed
    return corps


def charge_veo_i2v(depart, fin, prompt, negatif, duree, seed):
    """Veo à image unique : la frame de fin n'est pas imposée.

    Une frame de fin dérivée de la frame de début (zoom géométrique) épingle tous les
    pixels et le modèle n'anime plus que l'échelle — la foule reste figée. Sans elle,
    le modèle est libre d'animer, au prix du contrôle sur le cadre final.
    """
    del fin
    corps = {
        "prompt": prompt,
        "image_url": depart,
        "aspect_ratio": "16:9",
        "duration": f"{duree}s",
        "resolution": "1080p",
        "generate_audio": False,
        "negative_prompt": negatif,
    }
    if seed is not None:
        corps["seed"] = seed
    return corps


def charge_kling(depart, fin, prompt, negatif, duree, seed):
    del negatif, seed                # non supportés par cet endpoint
    corps = {
        "prompt": prompt,
        "start_image_url": depart,
        "duration": str(duree),
    }
    if fin:
        corps["end_image_url"] = fin
    return corps


def charge_kling3(depart, fin, prompt, negatif, duree, seed):
    del seed                         # non supporté par cet endpoint
    corps = {
        "prompt": prompt,
        "start_image_url": depart,
        "duration": str(duree),
        "negative_prompt": negatif,
        "generate_audio": False,     # la bande-son est le morceau, pas du son généré
        "shot_type": "customize",
    }
    if fin:
        corps["end_image_url"] = fin
    return corps


def charge_flux3(depart, fin, prompt, negatif, duree, seed):
    del negatif, seed                # non supportés par cet endpoint
    return {
        "prompt": prompt,
        "start_image_url": depart,
        "end_image_url": fin,
        "duration": duree,
        "aspect_ratio": "16:9",
        "resolution": "1080p",
        "generate_audio": False,
    }


def charge_seedance(depart, fin, prompt, negatif, duree, seed):
    del negatif                      # non supporté par cet endpoint
    corps = {
        "prompt": prompt,
        "image_url": depart,
        "end_image_url": fin,
        "duration": str(duree),
        "resolution": "720p",
        "aspect_ratio": "16:9",
        "generate_audio": False,     # la bande-son est le morceau, pas du son généré
        "camera_fixed": False,
    }
    if seed is not None:
        corps["seed"] = seed
    return corps

def charge_seedance2(depart, fin, prompt, negatif, duree, seed):
    """Seedance 2.5 : ni seed ni prompt négatif, et 30 s d'un seul tenant.

    Le tarif est au token de sortie : 0,473 $/s en 720p, dix fois `veo-lite`.
    """
    del negatif, seed                # non supportés par cet endpoint
    corps = {
        "prompt": prompt,
        "image_url": depart,
        "duration": str(duree),
        "resolution": "720p",
        "generate_audio": False,     # la bande-son est le morceau, pas du son généré
    }
    if fin:
        corps["end_image_url"] = fin
    return corps


def charge_h3_turbo(depart, fin, prompt, negatif, duree, seed):
    """MiniMax Hailuo H3 Max Turbo : 768p au mieux, et pas de prompt négatif.

    `prompt_expansion_mode` est obligatoire : MiniMax réécrit le prompt avant de
    générer. `disabled` garde la ligne Mouvement telle qu'elle est écrite — une
    réécriture rouvrirait la porte aux inventions que le film passe son temps à fermer.
    """
    del negatif                      # non supporté par cet endpoint
    corps = {
        "prompt": prompt,
        "image_url": depart,
        "end_image_url": fin,
        "duration": duree,
        "resolution": "768P",
        "prompt_expansion_mode": "disabled",
    }
    if seed is not None:
        corps["seed"] = seed
    return corps


# Endpoints image-to-video dont la charge sait se passer d'une frame de fin.
FIN_FACULTATIVE = {"kling", "kling3", "veo-lite-i2v", "h3-turbo", "seedance2"}

MODELES = {
    "veo-lite": {
        "endpoint": "fal-ai/veo3.1/lite/first-last-frame-to-video",
        "durees": (8,),              # l'endpoint lite ne prend que 8 s
        "prix_seconde": 0.05,        # 1080p sans audio ; 0,03 en 720p
        "charge": charge_veo,
    },
    "veo-lite-i2v": {
        "endpoint": "fal-ai/veo3.1/lite/image-to-video",
        "durees": (4, 6, 8),
        "prix_seconde": 0.05,        # 1080p sans audio
        "charge": charge_veo_i2v,
    },
    "kling3": {
        "endpoint": "fal-ai/kling-video/v3/pro/image-to-video",
        "durees": tuple(range(3, 16)),
        "prix_seconde": 0.112,       # audio coupé
        "prompt_max": 2500,          # l'endpoint rejette au-delà, après téléversement
        "charge": charge_kling3,
    },
    "flux3": {
        "endpoint": "blackforestlabs/flux-3/first-last-frame-to-video",
        "durees": tuple(range(5, 21)),
        "prix_seconde": 0.29,        # 1080p ; 0,17 en 720p
        "charge": charge_flux3,
    },
    "veo": {
        "endpoint": "fal-ai/veo3.1/fast/first-last-frame-to-video",
        "durees": (4, 6, 8),
        "prix_seconde": 0.10,        # variante rapide, sans audio (720p comme 1080p)
        "charge": charge_veo,
    },
    "veo-hq": {
        "endpoint": "fal-ai/veo3.1/first-last-frame-to-video",
        "durees": (4, 6, 8),
        "prix_seconde": 0.20,        # 1080p sans audio
        "charge": charge_veo,
    },
    "kling": {
        "endpoint": "fal-ai/kling-video/o1/image-to-video",
        "durees": tuple(range(3, 11)),
        "prix_seconde": 0.112,
        "charge": charge_kling,
    },
    "h3-turbo": {
        "endpoint": "minimax/h3-max-turbo/image-to-video",
        "durees": tuple(range(5, 16)),
        "prix_seconde": 0.04,        # 768p ; 0,025 en 480p (promo de lancement à 0,01)
        "charge": charge_h3_turbo,
    },
    "seedance": {
        "endpoint": "fal-ai/bytedance/seedance/v1.5/pro/image-to-video",
        "durees": tuple(range(4, 13)),
        "prix_seconde": 0.052,       # 720p ; ~0,26 $ les 5 s
        "charge": charge_seedance,
    },
    "seedance2": {
        "endpoint": "bytedance/seedance-2.5/image-to-video",
        "durees": tuple(range(4, 31)),
        "prix_seconde": 0.473,       # 720p ; 0,2205 en 480p, 1,164 en 1080p
        "charge": charge_seedance2,
    },
}


HUIS_CLOS = ("The room is closed and holds this one man alone: no one else is anywhere in the "
             "picture, no one enters it, and no crowd, prayer shawl or second figure ever appears.")


def lit_plan(texte, plan, avec_foule=True):
    """(camera, prompt de mouvement, négatif complet) pour un plan.

    Le bloc FIGURES suit le mouvement : sans lui l'i2v rhabille les gens à sa guise
    d'une image à l'autre, et la règle de tenue ne tenait que sur la frame de départ.

    Sur un plan qui ne montre personne d'autre que son sujet, les deux blocs sont au
    contraire un danger : kling3 a peuplé le Beit Avtinas d'hommes en talith rayé qui
    entrent par le bord gauche, exactement comme les blocs FIGURES et PLACES les
    décrivent. Une consigne ne nomme que ce que la caméra voit ; `avec_foule=False`
    les remplace par l'affirmation que la pièce est vide.
    """
    section = section_plan(texte, plan)
    mouvement = champ(section, "Mouvement")
    if not mouvement:
        raise SystemExit(f"Plan {plan} : ligne **Mouvement** absente")
    if avec_foule:
        suffixe = f'{figures_du_plan(texte, section)} {bloc_commun(texte, "PLACES")}'
    else:
        suffixe = HUIS_CLOS
    return camera_du_plan(section), f'{mouvement}. {suffixe}', negatif_du_plan(texte, section)


def controle_avant_video(texte, deja_fait):
    """Positions et zones d'accès, contrôlés sur les frames avant de payer une génération.

    L'i2v amplifie la frame de départ : un objet déplacé y reste huit secondes et une
    silhouette placée dans une zone qui lui est fermée se met à y marcher.
    """
    print("\n" + bloc_texte(texte, "CONTRÔLE AVANT VIDÉO") + "\n")
    if not deja_fait:
        raise SystemExit("Contrôle non déclaré : relire les deux frames stylisées contre "
                         "ce bloc, puis relancer avec --controle-fait.")


def arguments():
    analyseur = argparse.ArgumentParser(description="Génération vidéo fal.ai en ligne de commande")
    analyseur.add_argument("--plan", type=numero_de_plan, required=True,
                           help="numéro de plan (1-15, avec la lettre pour un plan coupé : 9a)")
    analyseur.add_argument("--modele", choices=sorted(MODELES), default="veo-lite")
    analyseur.add_argument("--duree", type=int, help="secondes générées (défaut : le maximum du modèle)")
    analyseur.add_argument("--depart", help="image de première frame (défaut : renders/blockout/CAM_xx_debut.png)")
    analyseur.add_argument("--fin", help="image de dernière frame (défaut : renders/blockout/CAM_xx_fin.png)")
    analyseur.add_argument("--huis-clos", action="store_true",
                           help="plan où le sujet est seul : remplace les blocs FIGURES et PLACES "
                                "par l'affirmation que personne d'autre n'est ni n'entre dans le cadre")
    analyseur.add_argument("--sans-fin", action="store_true",
                           help="n'impose aucune frame de fin : le modèle invente le mouvement "
                                "(les endpoints image-to-video seuls)")
    analyseur.add_argument("--prompt", help="remplace la ligne **Mouvement** du plan")
    analyseur.add_argument("--seed", type=int)
    analyseur.add_argument("--sortie", default=DOSSIER_SORTIE)
    analyseur.add_argument("--controle-fait", action="store_true",
                           help="atteste le contrôle positions + zones d'accès des deux frames")
    analyseur.add_argument("--simulation", action="store_true", help="affiche la charge utile sans générer")
    return analyseur.parse_args()


def main():
    args = arguments()
    modele = MODELES[args.modele]
    duree = args.duree or max(modele["durees"])
    if duree not in modele["durees"]:
        raise SystemExit(f"--duree {duree} : {args.modele} accepte {modele['durees']}")

    texte = texte_prompts()
    camera, mouvement, negatif = lit_plan(texte, args.plan, avec_foule=not args.huis_clos)
    if args.sans_fin and args.modele not in FIN_FACULTATIVE:
        raise SystemExit(f"--sans-fin : {args.modele} impose une frame de fin ; "
                         f"modèles possibles : {', '.join(sorted(FIN_FACULTATIVE))}")
    depart, fin = images_du_plan(camera, args.depart, args.fin, avec_fin=not args.sans_fin)
    prompt = args.prompt or mouvement
    cap = modele.get("prompt_max")
    if cap and len(prompt) > cap:
        raise SystemExit(f"{args.modele} : prompt de {len(prompt)} caractères pour {cap} au plus — "
                         f"raccourcir la ligne **Mouvement** du plan {args.plan} de "
                         f"{len(prompt) - cap} caractères (le reste est le suffixe FIGURES + PLACES).")

    print(f"plan {args.plan} · {camera} · {args.modele} · {duree} s "
          f"· ~{duree * modele['prix_seconde']:.2f} $")
    print(f"  prompt  : {prompt}")
    print(f"  images  : {os.path.relpath(depart, RACINE)}"
          + (f" → {os.path.relpath(fin, RACINE)}" if fin else " → aucune frame de fin imposée"))

    if args.simulation:
        print(json.dumps(modele["charge"]("<depart>", "<fin>" if fin else None,
                                          prompt, negatif, duree, args.seed),
                         indent=2, ensure_ascii=False))
        controle_avant_video(texte, deja_fait=True)
        return

    controle_avant_video(texte, args.controle_fait)
    cle = cle_api()
    corps = modele["charge"](televerse(depart, cle), televerse(fin, cle) if fin else None,
                             prompt, negatif, duree, args.seed)
    resultat = genere(modele["endpoint"], corps, cle)

    if "video" not in resultat:
        raise SystemExit(f"Réponse sans vidéo : {json.dumps(resultat, ensure_ascii=False)[:500]}")

    horodatage = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    chemin = os.path.join(args.sortie, f"{camera}_{args.modele}_{horodatage}.mp4")
    print(telecharge(resultat["video"]["url"], chemin))


if __name__ == "__main__":
    sys.exit(main())
