"""Plomberie fal.ai partagée par les générations image et vidéo.

Deux choses ici : l'accès à fal.ai (clé, téléversement sur le CDN, file d'attente)
et la lecture de `prompts_par_plan.md`, seule source des prompts du film.

Clé API : FAL_AI_KEY, dans l'environnement ou dans le `.env` à la racine.
Bibliothèque standard uniquement — aucune installation.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FICHIER_PROMPTS = os.path.join(RACINE, "prompts_par_plan.md")
DOSSIER_IMAGES = os.path.join(RACINE, "renders", "blockout")

URL_JETON = "https://rest.alpha.fal.ai/storage/auth/token?storage_type=fal-cdn-v3"
URL_FILE = "https://queue.fal.run"
INTERVALLE_SONDAGE = 5      # s ; une génération dure de 10 s (image) à 5 min (vidéo)
DELAI_MAX = 900             # s


# --- prompts_par_plan.md ------------------------------------------------------

def texte_prompts():
    with open(FICHIER_PROMPTS, encoding="utf-8") as fichier:
        return fichier.read()


PLANS = ("1", "2", "3", "4", "5", "6", "7a", "7b", "8", "9a", "9b", "10", "11", "12",
         "13a", "13b", "14a", "14b", "15")


def numero_de_plan(valeur):
    """« 9 », « 9A », « 9a » -> « 9a ». Un plan coupé en deux porte une lettre.

    Quatre plans se filment en deux prises — le tilt du 9, le panoramique du 7, la
    traversée de porte du 13, la grue du 14 : leurs deux bouts ne partagent pas assez
    d'image pour qu'un i2v les relie (beit_hamikdash_analyse_plans.py). Le numéro nu
    d'un plan coupé est refusé plutôt que deviné : « 9 » ne désigne plus rien.
    """
    demande = valeur.strip().lower()
    if demande in PLANS:
        return demande
    raise ValueError(f"plan inconnu : {valeur}. Plans : {', '.join(PLANS)}")


def section_plan(texte, plan):
    motif = rf"^## Plan {re.escape(str(plan))} — .*?(?=^## |\Z)"
    trouve = re.search(motif, texte, re.MULTILINE | re.DOTALL)
    if not trouve:
        raise SystemExit(f"Plan {plan} absent de {FICHIER_PROMPTS}")
    return trouve.group(0)


def champ(section, nom):
    trouve = re.search(rf"^\*\*{nom}\*\*\s*:\s*(.+)$", section, re.MULTILINE)
    return trouve.group(1).strip() if trouve else None


def bloc_commun(texte, nom):
    """Un bloc en citation des « Blocs communs », replié en un paragraphe.

    STYLE, FIGURES, PLACES, NÉGATIF, ÉDITION, CADRAGE. Le titre peut porter un
    commentaire après les astérisques, et le bloc s'étend sur toutes les lignes
    de citation qui suivent.
    """
    motif = rf"^\*\*{nom}\*\*.*\n((?:>.*\n)+)"
    trouve = re.search(motif, texte, re.MULTILINE)
    if not trouve:
        raise SystemExit(f"Bloc {nom} commun introuvable dans prompts_par_plan.md")
    return " ".join(l.lstrip("> ").strip() for l in trouve.group(1).splitlines())


def bloc_texte(texte, nom):
    """Un bloc des « Blocs communs » qui tient sur plusieurs lignes (liste, tableau).

    Titre compris : le bloc est affiché à l'écran, pas injecté dans un prompt.
    """
    titre = re.search(rf"^(?:\*\*|## ){nom}.*$", texte, re.MULTILINE | re.IGNORECASE)
    if not titre:
        raise SystemExit(f"Bloc {nom} introuvable dans prompts_par_plan.md")
    suite = re.search(r"^(?:\*\*|## |---)", texte[titre.end():], re.MULTILINE)
    fin = titre.end() + (suite.start() if suite else len(texte) - titre.end())
    return texte[titre.start():fin].strip()


def camera_du_plan(section):
    trouve = re.search(r"\((?:[^)]*?)(CAM_\d{2}[AB]?)", section)
    if not trouve:
        raise SystemExit("Identifiant CAM_xx absent de l'en-tête du plan")
    return trouve.group(1)


def negatif_du_plan(texte, section):
    """NÉGATIF commun + le négatif propre au plan."""
    negatif = bloc_commun(texte, "NÉGATIF")
    propre = champ(section, "Négatif")
    if propre:
        negatif += ", " + propre.replace("NÉGATIF +", "").strip(" ,")
    return negatif


def images_du_plan(camera, depart, fin):
    depart = depart or os.path.join(DOSSIER_IMAGES, f"{camera}_debut.png")
    fin = fin or os.path.join(DOSSIER_IMAGES, f"{camera}_fin.png")
    for chemin in (depart, fin):
        if not os.path.exists(chemin):
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
    """Met une image locale sur le CDN fal et renvoie son URL publique."""
    jeton = appel(URL_JETON, "POST",
                  {"Authorization": f"Key {cle}", "Content-Type": "application/json"},
                  b"{}")
    with open(chemin, "rb") as fichier:
        octets = fichier.read()
    reponse = appel(f"{jeton['base_url']}/files/upload", "POST",
                    {"Authorization": f"Bearer {jeton['token']}", "Content-Type": "image/png"},
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
