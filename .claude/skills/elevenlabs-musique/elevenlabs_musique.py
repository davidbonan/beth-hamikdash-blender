"""Chant liturgique sur elevenlabs.io (Music v2.5), dans le style d'une chanson de référence.

    python3 .claude/skills/elevenlabs-musique/elevenlabs_musique.py \
        --texte .claude/skills/elevenlabs-musique/textes/pitum_haketoret_complet.txt --simulation

La recette est celle qui a donné `audio/musique/pitum_haketoret_complet_direct_translittere_accent_hebreu.mp3` :
30 s de `reference.mp3` (hors git, à fournir) conditionnent tout le morceau, une voix de garçon
d'environ 6 ans chante le texte translittéré, l'intro est instrumentale, l'outro au piano, et chaque
section varie l'arrangement sans changer de tempo ni de chanteur. Le texte, son découpage, le ton et
l'arrangement de chaque section viennent du fichier `--texte`.

Chaque mp3 sort étiqueté (ID3 v2.3 : titre, artiste, album, paroles, source), prêt pour
une bibliothèque musicale ; `--etiqueter` étiquette un mp3 déjà sorti puis retouché.

Clé API : ELEVENLABS_API_KEY, dans l'environnement ou dans le `.env` à la racine.
Bibliothèque standard et ffmpeg uniquement.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass

DOSSIER = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(os.path.dirname(os.path.dirname(DOSSIER)))
DOSSIER_SORTIE = os.path.join(RACINE, "audio", "musique")
REFERENCE = os.path.join(DOSSIER, "reference.mp3")
REFERENCES_TELEVERSEES = os.path.join(DOSSIER, "references_televersees.json")

URL_API = "https://api.elevenlabs.io/v1/music"
MODELE = "music_v2_5"
FORMAT_SORTIE = "mp3_48000_192"
FORCE_REFERENCE = "medium"
CREDITS_SECONDE = 12.5  # génération comme téléversement de référence, à la seconde
DELAI_MAX = 900         # s

STYLES_CHANT = ["emotional Jewish liturgical song", "Sephardic prayer melody"]
STYLES_VOIX = ["Hebrew vocals", "young boy soloist, about 6 years old, small innocent child voice",
               "melismatic ornaments"]
STYLE_TEMPO = "flowing moderate tempo 136 BPM"
STYLES_INSTRUMENTS = ["E-flat minor", "soft piano", "warm strings", "oud and ney accents"]
STYLES_UNITE = ["one continuous song, same melody theme throughout", "same young boy singer from start to end"]
STYLE_ACCENT = "Hebrew accent"
STYLES_REJETES = ["EDM", "trap", "heavy drums", "autotune", "English lyrics", "adult voice", "teenage voice",
                  "woman singer", "slow ballad", "genre change", "different singer", "tempo change"]
STYLES_REJETES_INTRO = ["vocals", "singing", "humming", "choir", "spoken words"]
INTRO_MS, OUTRO_MS = 10000, 8000
SECONDES_PAR_LIGNE = 6
MAX_SECTIONS, MAX_LIGNES, MAX_CARACTERES = 28, 30, 200
SECTION_MS, TOTAL_MS = (3000, 120000), 600000
FENETRE_MS = (11000, 30000)  # 10 s pile sont refusées au téléversement
CLES_ETIQUETTE = ("titre", "artiste", "source")
LETTRE_HEBRAIQUE = re.compile("[א-ת]")
GENRE = "Jewish Music"


@dataclass
class Section:
    nom: str
    duree_ms: int
    ton: str | None
    arrangement: str | None
    lignes: list[str]
    paroles: list[str]


def lis_le_chant(chemin):
    """({titre, artiste, source}, [Section]).

    `clé: valeur` avant la première section, puis en-têtes `[nom | durée s | ton | arrangement]` ; `#` commente.
    Une ligne en lettres hébraïques va aux paroles de l'étiquette, les autres sont chantées.
    """
    preambule, sections = {}, []
    with open(chemin, encoding="utf-8") as fichier:
        for numero, ligne in enumerate(fichier, 1):
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#"):
                continue
            entete = re.fullmatch(r"\[(.+)\]", ligne)
            cle_valeur = re.fullmatch(rf"({'|'.join(CLES_ETIQUETTE)})\s*:\s*(.+)", ligne)
            if entete:
                nom, duree, ton, arrangement = ([champ.strip() for champ in entete[1].split("|")] + [""] * 3)[:4]
                sections.append(Section(nom, duree, ton or None, arrangement or None, [], []))
            elif cle_valeur and not sections:
                preambule[cle_valeur[1]] = cle_valeur[2]
            elif not sections:
                raise SystemExit(f"{chemin}:{numero} : ni `clé: valeur` ({', '.join(CLES_ETIQUETTE)}) "
                                 f"ni en-tête [section]")
            elif LETTRE_HEBRAIQUE.search(ligne):
                sections[-1].paroles.append(ligne)
            else:
                sections[-1].lignes.append(ligne)
    for section in sections:
        section.duree_ms = duree_ms(section.duree_ms, section.lignes)
    return preambule, sections


def duree_ms(duree, lignes):
    secondes = float(duree.replace(",", ".")) if duree else SECONDES_PAR_LIGNE * len(lignes)
    return int(round(secondes * 1000))


def verifie(sections):
    if not 1 <= len(sections) <= MAX_SECTIONS:
        raise SystemExit(f"{len(sections)} sections : il en faut de 1 à {MAX_SECTIONS}")
    for section in sections:
        if not 1 <= len(section.nom) <= 100:
            raise SystemExit(f"Nom de section de 1 à 100 caractères : « {section.nom} »")
        if not section.lignes or len(section.lignes) > MAX_LIGNES:
            raise SystemExit(f"[{section.nom}] : {len(section.lignes)} lignes chantées (translittérées), "
                             f"il en faut de 1 à {MAX_LIGNES}")
        if not SECTION_MS[0] <= section.duree_ms <= SECTION_MS[1]:
            raise SystemExit(f"[{section.nom}] : {section.duree_ms / 1000:g} s, une section dure de 3 à 120 s")
        trop_longue = next((ligne for ligne in section.lignes if len(ligne) > MAX_CARACTERES), None)
        if trop_longue:
            raise SystemExit(f"[{section.nom}] : ligne de plus de {MAX_CARACTERES} caractères, à couper : "
                             f"{trop_longue}")
    if duree_totale_ms(sections) > TOTAL_MS:
        raise SystemExit(f"{duree_totale_ms(sections) / 1000:g} s au total : 600 s au plus")


def duree_totale_ms(sections):
    return INTRO_MS + sum(section.duree_ms for section in sections) + OUTRO_MS


def credits(duree_ms):
    return round(duree_ms / 1000 * CREDITS_SECONDE)


def plan_de_composition(sections, reference):
    conditionnement = {"conditioning_ref": reference, "condition_strength": FORCE_REFERENCE}
    morceaux = [{"text": "[Intro]\n{soft piano and strings, no vocals}", "duration_ms": INTRO_MS,
                 "positive_styles": STYLES_CHANT + STYLES_INSTRUMENTS
                 + ["instrumental intro", "instrumental only", STYLE_TEMPO],
                 "negative_styles": STYLES_REJETES_INTRO, **conditionnement}]
    for section in sections:
        morceaux.append({"text": f"[{section.nom}]\n" + "\n".join(section.lignes), "duration_ms": section.duree_ms,
                         "positive_styles": STYLES_CHANT + STYLES_VOIX + [STYLE_TEMPO] + STYLES_INSTRUMENTS
                         + STYLES_UNITE + [style for style in (section.arrangement, section.ton) if style]
                         + [STYLE_ACCENT],
                         "negative_styles": STYLES_REJETES, **conditionnement})
    morceaux.append({"text": "[Outro]\n{piano alone, fading}", "duration_ms": OUTRO_MS,
                     "positive_styles": STYLES_CHANT + STYLES_VOIX + STYLES_INSTRUMENTS
                     + ["quiet piano outro", STYLE_TEMPO, STYLE_ACCENT]})
    return {"composition_plan": {"chunks": morceaux}, "model_id": MODELE}


def cadres_id3(etiquettes, sections):
    """(identifiant, contenu) des cadres ID3 v2.3 ; texte en UTF-16, que v2.3 exige hors latin-1."""
    def texte(valeur):
        return b"\x01" + valeur.encode("utf-16")

    def avec_langue(langue, valeur):
        return b"\x01" + langue + "".encode("utf-16") + b"\0\0" + valeur.encode("utf-16")

    paroles = "\n".join(ligne for section in sections for ligne in section.paroles or section.lignes)
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


def cle_api():
    cle = os.environ.get("ELEVENLABS_API_KEY")
    if cle:
        return cle
    chemin = os.path.join(RACINE, ".env")
    if not os.path.exists(chemin):
        raise SystemExit("ELEVENLABS_API_KEY introuvable (ni environnement, ni .env)")
    with open(chemin, encoding="utf-8") as fichier:
        for ligne in fichier:
            if ligne.startswith("ELEVENLABS_API_KEY="):
                return ligne.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("ELEVENLABS_API_KEY absente du .env")


def appel(url, corps, type_contenu, cle):
    """(octets, en-têtes) de la réponse ; la génération répond le mp3 lui-même, sans file d'attente."""
    requete = urllib.request.Request(url, data=corps, method="POST",
                                     headers={"xi-api-key": cle, "Content-Type": type_contenu})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI_MAX) as reponse:
            return reponse.read(), reponse.headers
    except urllib.error.HTTPError as erreur:
        detail = erreur.read().decode("utf-8", "replace")[:800]
        raise SystemExit(f"elevenlabs.io {erreur.code} sur {url}\n{detail}") from None


def cle_de_reference(chemin, debut_ms, fin_ms):
    with open(chemin, "rb") as fichier:
        return f"{hashlib.sha256(fichier.read()).hexdigest()}:{debut_ms}-{fin_ms}"


def references_televersees():
    if not os.path.exists(REFERENCES_TELEVERSEES):
        return {}
    with open(REFERENCES_TELEVERSEES, encoding="utf-8") as fichier:
        return json.load(fichier)


def extrait(chemin, debut_ms, fin_ms):
    """La fenêtre de la référence, copiée sans réencodage."""
    with tempfile.TemporaryDirectory() as dossier:
        sortie = os.path.join(dossier, "reference.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-ss", str(debut_ms / 1000), "-t", str((fin_ms - debut_ms) / 1000),
                        "-i", chemin, "-c", "copy", sortie], check=True)
        with open(sortie, "rb") as fichier:
            return fichier.read()


def televerse_la_reference(chemin, debut_ms, fin_ms, cle):
    """Téléverse la fenêtre, facturée comme une génération de sa durée, et retient son song_id."""
    frontiere = uuid.uuid4().hex
    corps = (f'--{frontiere}\r\nContent-Disposition: form-data; name="file"; filename="reference.mp3"\r\n'
             f"Content-Type: audio/mpeg\r\n\r\n").encode("ascii") \
        + extrait(chemin, debut_ms, fin_ms) + f"\r\n--{frontiere}--\r\n".encode("ascii")
    reponse, _ = appel(f"{URL_API}/upload", corps, f"multipart/form-data; boundary={frontiere}", cle)
    song_id = json.loads(reponse)["song_id"]
    connues = references_televersees()
    connues[cle_de_reference(chemin, debut_ms, fin_ms)] = song_id
    with open(REFERENCES_TELEVERSEES, "w", encoding="utf-8") as fichier:
        json.dump(connues, fichier, indent=1)
    return song_id


def tire(corps, nom, cadres, cle, verrou):
    son, entetes = appel(f"{URL_API}?output_format={FORMAT_SORTIE}", json.dumps(corps).encode("utf-8"),
                         "application/json", cle)
    with verrou:
        chemin = chemin_libre(nom)
        with open(chemin, "wb") as fichier:
            fichier.write(son)
    etiquette(chemin, cadres)
    with open(os.path.splitext(chemin)[0] + ".json", "w", encoding="utf-8") as journal:
        json.dump(corps, journal, ensure_ascii=False, indent=1)
    print(f"→ {os.path.relpath(chemin, RACINE)} · song-id {entetes.get('song-id')}", flush=True)


def arguments():
    analyseur = argparse.ArgumentParser(description="Chant liturgique sur elevenlabs.io, dans le style d'une référence")
    analyseur.add_argument("--texte", required=True,
                           help="fichier texte découpé en sections [nom | durée s | ton | arrangement]")
    analyseur.add_argument("--nom", help="nom du mp3 (défaut : celui du fichier texte)")
    analyseur.add_argument("--reference", default=REFERENCE, help="chanson dont le style conditionne le morceau")
    analyseur.add_argument("--fenetre", default="50-80",
                           help="secondes de la référence prises pour le style, de 11 à 30 s (défaut 50-80)")
    analyseur.add_argument("--tirages", type=int, default=1, help="générations indépendantes, lancées en parallèle")
    analyseur.add_argument("--simulation", action="store_true", help="affiche le plan et le coût, sans rien envoyer")
    analyseur.add_argument("--etiqueter", metavar="MP3", help="étiquette ce mp3 d'après --texte, sans rien générer")
    return analyseur.parse_args()


def main():
    args = arguments()
    etiquettes, sections = lis_le_chant(args.texte)
    verifie(sections)
    nom = args.nom or os.path.splitext(os.path.basename(args.texte))[0]
    etiquettes.setdefault("titre", nom.replace("_", " ").title())
    cadres = cadres_id3(etiquettes, sections)
    if args.etiqueter:
        etiquette(args.etiqueter, cadres)
        print(f"{args.etiqueter} étiqueté : {', '.join(f'{cle} {valeur}' for cle, valeur in etiquettes.items())}")
        return
    debut, fin = (int(float(borne) * 1000) for borne in args.fenetre.split("-"))
    if not FENETRE_MS[0] <= fin - debut <= FENETRE_MS[1]:
        raise SystemExit(f"Fenêtre {args.fenetre} : de 11 à 30 s")
    if not os.path.exists(args.reference):
        raise SystemExit(f"Référence absente : {args.reference} — fournir son propre mp3 (voir SKILL.md)")

    song_id = references_televersees().get(cle_de_reference(args.reference, debut, fin))
    cout = args.tirages * credits(duree_totale_ms(sections)) + (0 if song_id else credits(fin - debut))
    print(f"{nom} · {len(sections)} sections · {duree_totale_ms(sections) / 1000:g} s · "
          f"{args.tirages} tirage(s) · {cout} crédits"
          + ("" if song_id else f", dont {credits(fin - debut)} pour téléverser la référence"))
    reference = {"song_id": song_id or "<référence à téléverser>", "range": {"start_ms": 0, "end_ms": fin - debut}}
    if args.simulation:
        print(json.dumps(plan_de_composition(sections, reference), indent=1, ensure_ascii=False))
        print(f"étiquettes : {etiquettes}")
        return

    cle = cle_api()
    reference["song_id"] = song_id or televerse_la_reference(args.reference, debut, fin, cle)
    corps, verrou = plan_de_composition(sections, reference), threading.Lock()
    fils = [threading.Thread(target=tire, args=(corps, nom, cadres, cle, verrou)) for _ in range(args.tirages)]
    for fil in fils:
        fil.start()
    for fil in fils:
        fil.join()


if __name__ == "__main__":
    main()
