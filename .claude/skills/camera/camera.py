"""Déclare un plan dans `cameras.json`, puis en exporte les deux images clés.

    python3 .claude/skills/camera/camera.py lister
    python3 .claude/skills/camera/camera.py ajouter --nom CAM_04_Rampe --focale 35 \
        --duree 12 --camera "-38,-62,3" "-38,-57,3" --cible "-38,-28,9"
    python3 .claude/skills/camera/camera.py rendre --nom CAM_04_Rampe
    python3 .claude/skills/camera/camera.py supprimer --nom CAM_04_Rampe

Les positions sont en **amot**, dans le repère du blockout : +X est, +Y nord, +Z haut,
origine au mur est de l'Azara sur l'axe du Heikhal, au niveau de sa cour.

`--camera` et `--cible` prennent chacun une liste de points : un seul point ne bouge
pas, deux donnent une droite, plus donnent une polyligne. `--orbite` écrit cette
polyligne pour une course circulaire.

Après une déclaration, le script relance Blender — blockout, caméras, export, puis la
mesure de recouvrement du plan. C'est cette mesure qui dit si un i2v à deux frames
peut tenir le plan : sous 40 % de couverture, le modèle invente le trajet plutôt que
de l'interpoler.
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FICHIER = os.path.join(RACINE, "cameras.json")
BLEND = os.path.join(RACINE, "beit_hamikdash.blend")
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")

SCRIPTS = ("beit_hamikdash_blockout.py", "beit_hamikdash_cameras.py",
           "beit_hamikdash_export.py", "beit_hamikdash_analyse_plans.py")
BRUIT = ("Deprecation", "use_nodes", "Read blend", "Blender quit", "Blender 5",
         "Fra:", "Saved:", "Not freed memory")


# --- cameras.json -------------------------------------------------------------

def lire():
    if not os.path.exists(FICHIER):
        return {"cameras": []}
    with open(FICHIER, encoding="utf-8") as fichier:
        return json.load(fichier)


def ecrire(fiche):
    """Un point par ligne : le fichier se relit et se corrige à la main."""
    blocs = []
    for cam in fiche["cameras"]:
        champs = [f'      "nom": {json.dumps(cam["nom"], ensure_ascii=False)}',
                  f'      "duree_s": {cam["duree_s"]:g}',
                  f'      "focale": {cam["focale"]:g}']
        for clef in ("capteur", "clip_fin"):
            if clef in cam:
                champs.append(f'      "{clef}": {cam[clef]:g}')
        for clef in ("camera", "cible"):
            points = ",\n".join("        " + json.dumps(p) for p in cam[clef])
            champs.append(f'      "{clef}": [\n{points}\n      ]')
        blocs.append("    {\n" + ",\n".join(champs) + "\n    }")
    with open(FICHIER, "w", encoding="utf-8") as fichier:
        fichier.write('{\n  "cameras": [\n' + ",\n".join(blocs) + "\n  ]\n}\n")


def trouver(fiche, nom):
    return next((c for c in fiche["cameras"] if c["nom"] == nom), None)


# --- courses ------------------------------------------------------------------

def point(valeur):
    morceaux = valeur.replace(" ", "").split(",")
    if len(morceaux) != 3:
        raise argparse.ArgumentTypeError(f"« {valeur} » : un point s'écrit x,y,z en amot")
    try:
        return [float(m) for m in morceaux]
    except ValueError:
        raise argparse.ArgumentTypeError(f"« {valeur} » : trois nombres attendus") from None


def orbite(valeur):
    """cx,cy,z,rayon,deg_debut,deg_fin -> polyligne. Angle 0 = est, positif vers le nord."""
    morceaux = valeur.replace(" ", "").split(",")
    if len(morceaux) != 6:
        raise argparse.ArgumentTypeError(
            f"« {valeur} » : --orbite s'écrit cx,cy,z,rayon,deg_debut,deg_fin")
    cx, cy, z, rayon, d0, d1 = (float(m) for m in morceaux)
    nombre = max(2, int(round(abs(d1 - d0) / 5)) + 1)
    return [[round(cx + rayon * math.cos(math.radians(a)), 1),
             round(cy + rayon * math.sin(math.radians(a)), 1), z]
            for a in (d0 + (d1 - d0) * i / (nombre - 1) for i in range(nombre))]


# --- Blender ------------------------------------------------------------------

def blender(args_scripts, planche):
    """Chaîne blockout → caméras → export → mesure dans une seule instance."""
    if not shutil.which(BLENDER) and not os.path.exists(BLENDER):
        raise SystemExit(f"Blender introuvable : {BLENDER} — donner le chemin dans $BLENDER.")
    commande = [BLENDER, "-b", BLEND]
    for script in SCRIPTS:
        commande += ["-P", os.path.join(RACINE, script)]
    commande += ["--", *(["--planche"] if planche else []), *args_scripts]

    processus = subprocess.Popen(commande, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, cwd=RACINE)
    for ligne in processus.stdout:
        if not any(mot in ligne for mot in BRUIT):
            print(ligne.rstrip(), flush=True)
    return processus.wait()


# --- commandes ----------------------------------------------------------------

def commande_lister(args):
    fiche = lire()
    if not fiche["cameras"]:
        raise SystemExit(f"Aucun plan déclaré dans {FICHIER}.")
    for cam in fiche["cameras"]:
        print(f"{cam['nom']:34s} {cam['focale']:>4g} mm  {cam['duree_s']:>4g} s  "
              f"{len(cam['camera'])} pt caméra, {len(cam['cible'])} pt cible")
    return 0


def commande_ajouter(args):
    if not args.camera and not args.orbite:
        raise SystemExit("Il faut une course de caméra : --camera, ou --orbite.")
    if args.camera and args.orbite:
        raise SystemExit("--camera et --orbite décrivent la même course : en choisir une.")

    fiche = lire()
    if trouver(fiche, args.nom) and not args.remplacer:
        raise SystemExit(f"{args.nom} existe déjà — --remplacer pour l'écraser.")
    fiche["cameras"] = [c for c in fiche["cameras"] if c["nom"] != args.nom]

    declaration = {"nom": args.nom, "duree_s": args.duree, "focale": args.focale,
                   "camera": args.orbite or args.camera, "cible": args.cible}
    if args.capteur:
        declaration["capteur"] = args.capteur
    fiche["cameras"].append(declaration)
    ecrire(fiche)
    print(f"{args.nom} déclaré dans {os.path.relpath(FICHIER, RACINE)}")
    return 0 if args.sans_rendu else blender([args.nom], args.planche)


def commande_supprimer(args):
    fiche = lire()
    if not trouver(fiche, args.nom):
        raise SystemExit(f"{args.nom} n'est pas déclaré.")
    fiche["cameras"] = [c for c in fiche["cameras"] if c["nom"] != args.nom]
    ecrire(fiche)
    print(f"{args.nom} retiré. Les images déjà rendues restent dans renders/.")
    return 0


def commande_rendre(args):
    fiche = lire()
    if args.nom and not trouver(fiche, args.nom):
        raise SystemExit(f"{args.nom} n'est pas déclaré.")
    return blender([args.nom] if args.nom else [], args.planche)


def analyseur():
    principal = argparse.ArgumentParser(description="Plans du film : déclaration et images clés")
    commandes = principal.add_subparsers(dest="commande", required=True)

    commandes.add_parser("lister", help="les plans déclarés").set_defaults(fonction=commande_lister)

    ajouter = commandes.add_parser("ajouter", help="déclarer un plan et en rendre les images clés")
    ajouter.add_argument("--nom", required=True, help="nom de la caméra, p. ex. CAM_04_Rampe")
    ajouter.add_argument("--focale", type=float, required=True, help="mm sur capteur 36 mm")
    ajouter.add_argument("--duree", type=float, required=True, help="secondes")
    ajouter.add_argument("--camera", type=point, nargs="+", metavar="x,y,z",
                         help="course de l'objectif, en amot : 1 point = fixe, 2 = droite, n = polyligne")
    ajouter.add_argument("--orbite", type=orbite, metavar="cx,cy,z,rayon,deg0,deg1",
                         help="course circulaire, à la place de --camera")
    ajouter.add_argument("--cible", type=point, nargs="+", required=True, metavar="x,y,z",
                         help="course du point visé, en amot")
    ajouter.add_argument("--capteur", type=float, help="largeur de capteur en mm (défaut 36)")
    ajouter.add_argument("--remplacer", action="store_true", help="écraser un plan du même nom")
    ajouter.add_argument("--planche", action="store_true", help="rendre en 640 x 360, sans profondeur")
    ajouter.add_argument("--sans-rendu", action="store_true", help="déclarer sans lancer Blender")
    ajouter.set_defaults(fonction=commande_ajouter)

    supprimer = commandes.add_parser("supprimer", help="retirer un plan de cameras.json")
    supprimer.add_argument("--nom", required=True)
    supprimer.set_defaults(fonction=commande_supprimer)

    rendre = commandes.add_parser("rendre", help="rebâtir la scène et rendre les images clés")
    rendre.add_argument("--nom", help="un plan seulement (défaut : tous)")
    rendre.add_argument("--planche", action="store_true", help="rendre en 640 x 360, sans profondeur")
    rendre.set_defaults(fonction=commande_rendre)
    return principal


def main():
    args = analyseur().parse_args()
    return args.fonction(args)


if __name__ == "__main__":
    sys.exit(main())
