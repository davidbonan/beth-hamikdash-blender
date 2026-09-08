"""Plomberie fal.ai partagée par les générations image et vidéo.

L'accès à fal.ai — clé, téléversement sur le CDN, file d'attente — et la résolution
des images clés d'un plan dans `renders/blockout/`.

Les prompts ne vivent pas ici : ils se donnent en ligne de commande. Le dépôt n'en
tient aucun catalogue, parce que ce qu'on demande à un modèle change à chaque essai
et qu'un fichier de prompts figé se met à mentir dès la deuxième génération.

Clé API : FAL_AI_KEY, dans l'environnement ou dans le `.env` à la racine.
Bibliothèque standard uniquement — aucune installation.
"""

import json
import mimetypes
import os
import time
import urllib.error
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DOSSIER_IMAGES = os.path.join(RACINE, "renders", "blockout")

URL_JETON = "https://rest.alpha.fal.ai/storage/auth/token?storage_type=fal-cdn-v3"
URL_FILE = "https://queue.fal.run"
INTERVALLE_SONDAGE = 5      # s ; une génération dure de 10 s (image) à 5 min (vidéo)
DELAI_MAX = 900             # s


# --- images clés --------------------------------------------------------------

def images_de_frame(camera, etiquette):
    """(rendu couleur, carte de profondeur) de la frame `debut` ou `fin` d'un plan."""
    base = os.path.join(DOSSIER_IMAGES, f"{camera}_{etiquette}")
    couleur, profondeur = base + ".png", base + "_profondeur.png"
    for chemin in (couleur, profondeur):
        if not os.path.exists(chemin):
            raise SystemExit(f"Image absente : {chemin} — l'exporter avec "
                             f"beit_hamikdash_export.py")
    return couleur, profondeur


def images_du_plan(camera, depart, fin, avec_fin=True):
    depart = depart or os.path.join(DOSSIER_IMAGES, f"{camera}_debut.png")
    fin = (fin or os.path.join(DOSSIER_IMAGES, f"{camera}_fin.png")) if avec_fin else None
    for chemin in (depart, fin):
        if chemin and not os.path.exists(chemin):
            raise SystemExit(f"Image absente : {chemin}")
    return depart, fin


# --- fal.ai -------------------------------------------------------------------

def cle_api():
    cle = os.environ.get("FAL_AI_KEY") or os.environ.get("FAL_KEY")
    if cle:
        return cle
    chemin = os.path.join(RACINE, ".env")
    if not os.path.exists(chemin):
        raise SystemExit("FAL_AI_KEY introuvable (ni environnement, ni .env)")
    with open(chemin, encoding="utf-8") as fichier:
        for ligne in fichier:
            if ligne.startswith(("FAL_AI_KEY=", "FAL_KEY=")):
                return ligne.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("FAL_AI_KEY absente du .env")


def appel(url, methode="GET", entetes=None, corps=None, brut=False):
    requete = urllib.request.Request(url, method=methode, data=corps, headers=entetes or {})
    try:
        with urllib.request.urlopen(requete, timeout=300) as reponse:
            donnees = reponse.read()
    except urllib.error.HTTPError as erreur:
        detail = erreur.read().decode("utf-8", "replace")[:800]
        raise SystemExit(f"fal.ai {erreur.code} sur {url}\n{detail}") from None
    return donnees if brut else json.loads(donnees)


def televerse(chemin, cle):
    """Met un fichier local sur le CDN fal et renvoie son URL publique.

    Le CDN refuse le téléversement si le type déclaré ne correspond pas au contenu
    (« Unsupported file format » sur un mp4 annoncé en image/png) : il se lit sur
    l'extension, il ne se suppose pas.
    """
    type_mime = mimetypes.guess_type(chemin)[0] or "application/octet-stream"
    jeton = appel(URL_JETON, "POST",
                  {"Authorization": f"Key {cle}", "Content-Type": "application/json"},
                  b"{}")
    with open(chemin, "rb") as fichier:
        octets = fichier.read()
    reponse = appel(f"{jeton['base_url']}/files/upload", "POST",
                    {"Authorization": f"Bearer {jeton['token']}", "Content-Type": type_mime},
                    octets)
    return reponse["access_url"]


def genere(endpoint, corps, cle):
    entetes = {"Authorization": f"Key {cle}", "Content-Type": "application/json"}
    file = appel(f"{URL_FILE}/{endpoint}", "POST", entetes,
                 json.dumps(corps).encode("utf-8"))
    print(f"requête {file['request_id']}", flush=True)

    debut = time.time()
    while time.time() - debut < DELAI_MAX:
        etat = appel(file["status_url"], "GET", entetes)
        if etat["status"] == "COMPLETED":
            return appel(file["response_url"], "GET", entetes)
        print(f"  {etat['status']} ({int(time.time() - debut)} s)", flush=True)
        time.sleep(INTERVALLE_SONDAGE)
    raise SystemExit(f"Toujours en cours après {DELAI_MAX} s. Le résultat reste "
                     f"récupérable : {file['response_url']}")


def telecharge(url, chemin):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "wb") as fichier:
        fichier.write(appel(url, "GET", brut=True))
    return chemin
