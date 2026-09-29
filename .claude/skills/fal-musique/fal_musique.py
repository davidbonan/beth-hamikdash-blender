"""Chant liturgique sur fal.ai (ElevenLabs Music v2.5), dans le style d'une chanson de référence.

    python3 .claude/skills/fal-musique/fal_musique.py \
        --texte .claude/skills/fal-musique/textes/pitum_haketoret.txt --simulation

La recette est celle qui a donné `audio/musique/pitum_haketoret.mp3` : 30 s de
`reference.mp3` (hors git, à fournir) conditionnent tout le morceau, une voix de
garçon d'environ 6 ans, une intro et un outro au piano, et chaque section monte d'un cran en puissance. Le texte,
son découpage et le ton de chaque section viennent du fichier `--texte`.

Chaque mp3 sort étiqueté (ID3 v2.3 : titre, artiste, album, paroles, source), prêt pour
une bibliothèque musicale ; `--etiqueter` étiquette un mp3 déjà sorti puis retouché.

La plomberie fal.ai (clé, téléversement, file d'attente) est celle du skill `fal-video`.
"""

import argparse
import json
import math
import os
import re
import sys
import threading
import time

SKILLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILLS, "fal-video"))

from fal_commun import RACINE, cle_api, genere, telecharge, televerse

ENDPOINT = "elevenlabs/music/v2.5"
PRIX_MINUTE = 0.6  # $, minute entamée due
DOSSIER_SORTIE = os.path.join(RACINE, "audio", "musique")
REFERENCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference.mp3")

STYLES = ["emotional Jewish liturgical song", "Sephardic prayer melody", "Hebrew vocals",
          "young boy soloist, about 6 years old, small innocent child voice", "melismatic ornaments", "flowing moderate tempo 136 BPM",
          "E-flat minor", "soft piano", "warm strings", "oud and ney accents"]
STYLES_REJETES = ["EDM", "trap", "heavy drums", "autotune", "English lyrics", "adult voice", "teenage voice", "woman singer", "slow ballad"]
PALIERS = ["flowing, already moving", "building energy",
           "more energy and fuller sound, rhythmic qanun joins",
           "powerful, driving, rhythmic qanun and light frame drum",
           "still building, more voice power, rhythmic qanun and light frame drum",
           "peak power, most intense moment, rhythmic qanun and light frame drum"]
INTRO_MS, OUTRO_MS = 10000, 8000
SECONDES_PAR_LIGNE = 6
MAX_SECTIONS, MAX_LIGNES, MAX_CARACTERES = 28, 30, 200
SECTION_MS, TOTAL_MS = (3000, 120000), 600000
CLES_ETIQUETTE = ("titre", "artiste", "source")
CLES_ENTETE = CLES_ETIQUETTE + ("percussions",)
GENRE = "Jewish Music"


def lis_le_chant(chemin):
    """({titre, artiste, source, percussions}, [(nom, durée ms, ton ou None, lignes)]).

    `clé: valeur` avant la première section, puis en-têtes `[nom | durée s | ton]` ; `#` commente.
    """
    preambule, sections = {}, []
    with open(chemin, encoding="utf-8") as fichier:
        for numero, ligne in enumerate(fichier, 1):
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#"):
                continue
            entete = re.fullmatch(r"\[(.+)\]", ligne)
            cle_valeur = re.fullmatch(rf"({'|'.join(CLES_ENTETE)})\s*:\s*(.+)", ligne)
            if entete:
                nom, duree, ton = (entete[1].split("|") + ["", ""])[:3]
                sections.append([nom.strip(), duree.strip(), ton.strip() or None, []])
            elif cle_valeur and not sections:
                preambule[cle_valeur[1]] = cle_valeur[2]
            elif not sections:
                raise SystemExit(f"{chemin}:{numero} : ni `clé: valeur` ({', '.join(CLES_ENTETE)}) "
                                 f"ni en-tête [section]")
            else:
                sections[-1][3].append(ligne)
    return preambule, [(nom, duree_ms(duree, lignes), ton, lignes) for nom, duree, ton, lignes in sections]


def duree_ms(duree, lignes):
    secondes = float(duree.replace(",", ".")) if duree else SECONDES_PAR_LIGNE * len(lignes)
    return int(round(secondes * 1000))


def verifie(sections):
    if not 1 <= len(sections) <= MAX_SECTIONS:
        raise SystemExit(f"{len(sections)} sections : il en faut de 1 à {MAX_SECTIONS}")
    for nom, duree, _, lignes in sections:
        if not 1 <= len(nom) <= 100:
            raise SystemExit(f"Nom de section de 1 à 100 caractères : « {nom} »")
        if not lignes or len(lignes) > MAX_LIGNES:
            raise SystemExit(f"[{nom}] : {len(lignes)} lignes, il en faut de 1 à {MAX_LIGNES}")
        if not SECTION_MS[0] <= duree <= SECTION_MS[1]:
            raise SystemExit(f"[{nom}] : {duree / 1000:g} s, une section dure de 3 à 120 s")
        trop_longue = next((ligne for ligne in lignes if len(ligne) > MAX_CARACTERES), None)
        if trop_longue:
            raise SystemExit(f"[{nom}] : ligne de plus de {MAX_CARACTERES} caractères, à couper : {trop_longue}")
    if duree_totale_ms(sections) > TOTAL_MS:
        raise SystemExit(f"{duree_totale_ms(sections) / 1000:g} s au total : 600 s au plus")


def duree_totale_ms(sections):
    return INTRO_MS + sum(duree for _, duree, _, _ in sections) + OUTRO_MS


def palier(rang, nombre):
    indice = round(rang * (len(PALIERS) - 1) / (nombre - 1)) if nombre > 1 else len(PALIERS) - 1
    return f"intensity {rang + 1} of {nombre}, {PALIERS[indice]}"


def plan_de_composition(sections, reference, percussions=None):
    """`percussions` devient un style du morceau entier, et « heavy drums » cesse d'être rejeté."""
    styles = STYLES + ([percussions] if percussions else [])
    rejetes = [style for style in STYLES_REJETES if not (percussions and style == "heavy drums")]
    morceaux = [{"text": "[Intro]\n{soft piano and strings, no vocals}", "duration_ms": INTRO_MS,
                 "positive_styles": styles + ["instrumental intro"], "audio_reference": reference}]
    for rang, (nom, duree, ton, lignes) in enumerate(sections):
        morceaux.append({"text": f"[{nom}]\n" + "\n".join(lignes), "duration_ms": duree,
                         "positive_styles": styles + ([ton] if ton else [])
                         + [palier(rang, len(sections)), "keeps building in power"],
                         "negative_styles": rejetes, "audio_reference": reference})
    morceaux.append({"text": "[Outro]\n{piano alone, fading}", "duration_ms": OUTRO_MS,
                     "positive_styles": STYLES + ["quiet piano outro"]})
    return {"composition_plan": {"chunks": morceaux}, "output_format": "mp3_48000_192"}


def cadres_id3(etiquettes, sections):
    """(identifiant, contenu) des cadres ID3 v2.3 ; texte en UTF-16, que v2.3 exige hors latin-1."""
    def texte(valeur):
        return b"\x01" + valeur.encode("utf-16")

    def avec_langue(langue, valeur):
        return b"\x01" + langue + "".encode("utf-16") + b"\0\0" + valeur.encode("utf-16")

    paroles = "\n".join(ligne for *_, lignes in sections for ligne in lignes)
    cadres = [("TIT2", texte(etiquettes["titre"])), ("TALB", texte(etiquettes["titre"])),
              ("TRCK", texte("1/1")), ("TCON", texte(GENRE)), ("TYER", texte(time.strftime("%Y"))),
              ("TLAN", texte("heb")), ("USLT", avec_langue(b"heb", paroles))]
    if etiquettes.get("artiste"):
        cadres += [("TPE1", texte(etiquettes["artiste"])), ("TPE2", texte(etiquettes["artiste"]))]
    if etiquettes.get("source"):
        cadres.append(("COMM", avec_langue(b"fra", etiquettes["source"])))
    return cadres


def etiquette(chemin, cadres):
    """Remplace l'étiquette ID3v2 en tête du mp3 ; le son n'est pas touché."""
    with open(chemin, "rb") as fichier:
        octets = fichier.read()
    if octets[:3] == b"ID3":
        taille = sum((octet & 0x7F) << decalage for octet, decalage in zip(octets[6:10], (21, 14, 7, 0)))
        octets = octets[10 + taille + (10 if octets[5] & 0x10 else 0):]
    corps = b"".join(ident.encode("ascii") + len(contenu).to_bytes(4, "big") + b"\0\0" + contenu
                     for ident, contenu in cadres)
    entete = b"ID3\x03\x00\x00" + bytes((len(corps) >> decalage) & 0x7F for decalage in (21, 14, 7, 0))
    provisoire = chemin + ".etiquette"
    with open(provisoire, "wb") as fichier:
        fichier.write(entete + corps + octets)
    os.replace(provisoire, chemin)


def chemin_libre(nom):
    chemin, numero = os.path.join(DOSSIER_SORTIE, f"{nom}.mp3"), 1
    while os.path.exists(chemin):
        numero += 1
        chemin = os.path.join(DOSSIER_SORTIE, f"{nom}_{numero}.mp3")
    return chemin


def tire(corps, nom, cadres, cle, verrou):
    resultat = genere(ENDPOINT, corps, cle)
    with verrou:
        chemin = chemin_libre(nom)
        open(chemin, "wb").close()
    telecharge(resultat["audio"]["url"], chemin)
    etiquette(chemin, cadres)
    with open(os.path.splitext(chemin)[0] + ".json", "w", encoding="utf-8") as journal:
        json.dump(corps, journal, ensure_ascii=False, indent=1)
    print(f"→ {os.path.relpath(chemin, RACINE)}", flush=True)


def arguments():
    analyseur = argparse.ArgumentParser(description="Chant liturgique sur fal.ai, dans le style d'une référence")
    analyseur.add_argument("--texte", required=True, help="fichier texte découpé en sections [nom | durée s | ton]")
    analyseur.add_argument("--nom", help="nom du mp3 (défaut : celui du fichier texte)")
    analyseur.add_argument("--reference", default=REFERENCE, help="chanson dont le style conditionne le morceau")
    analyseur.add_argument("--fenetre", default="50-80",
                           help="secondes de la référence prises pour le style, 30 s au plus (défaut 50-80)")
    analyseur.add_argument("--tirages", type=int, default=1, help="générations indépendantes, lancées en parallèle")
    analyseur.add_argument("--simulation", action="store_true", help="affiche le plan et le prix, sans rien envoyer")
    analyseur.add_argument("--etiqueter", metavar="MP3", help="étiquette ce mp3 d'après --texte, sans rien générer")
    return analyseur.parse_args()


def main():
    args = arguments()
    etiquettes, sections = lis_le_chant(args.texte)
    percussions = etiquettes.pop("percussions", None)
    verifie(sections)
    nom = args.nom or os.path.splitext(os.path.basename(args.texte))[0]
    etiquettes.setdefault("titre", nom.replace("_", " ").title())
    cadres = cadres_id3(etiquettes, sections)
    if args.etiqueter:
        etiquette(args.etiqueter, cadres)
        print(f"{args.etiqueter} étiqueté : {', '.join(f'{cle} {valeur}' for cle, valeur in etiquettes.items())}")
        return
    debut, fin = (int(float(borne) * 1000) for borne in args.fenetre.split("-"))
    if not 0 < fin - debut <= 30000:
        raise SystemExit(f"Fenêtre {args.fenetre} : 30 s au plus, fin après début")
    if not os.path.exists(args.reference):
        raise SystemExit(f"Référence absente : {args.reference} — fournir son propre mp3 (voir SKILL.md)")

    minutes = math.ceil(duree_totale_ms(sections) / 60000)
    print(f"{nom} · {len(sections)} sections · {duree_totale_ms(sections) / 1000:g} s · "
          f"{args.tirages} tirage(s) · {args.tirages * minutes * PRIX_MINUTE:.2f} $")
    reference = {"audio_url": "<référence>", "start_ms": debut, "end_ms": fin, "strength": "high"}
    if args.simulation:
        print(json.dumps(plan_de_composition(sections, reference, percussions), indent=1, ensure_ascii=False))
        print(f"étiquettes : {etiquettes}")
        return

    cle = cle_api()
    reference["audio_url"] = televerse(args.reference, cle)
    corps, verrou = plan_de_composition(sections, reference, percussions), threading.Lock()
    fils = [threading.Thread(target=tire, args=(corps, nom, cadres, cle, verrou)) for _ in range(args.tirages)]
    for fil in fils:
        fil.start()
    for fil in fils:
        fil.join()


if __name__ == "__main__":
    main()
