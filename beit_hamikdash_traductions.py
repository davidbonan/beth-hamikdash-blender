"""python3 beit_hamikdash_traductions.py — relève ce qu'il reste à traduire dans visite/ ; code 1 s'il en reste."""
import json
import pathlib
import re
import sys

DOSSIER = pathlib.Path(__file__).resolve().parent / "visite"
FICHIERS = ("a", "b", "c")
TRADUISIBLES = {"nom", "translit", "resume", "cotes", "sources", "note"}
HEBREU = re.compile(r"[א-ת]")


def lire(nom):
    chemin = DOSSIER / nom
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else None


def ecarts_citation(source, traduite, langue):
    if not source:
        return [] if not traduite else ["citation absente en français"]
    if HEBREU.search(source):
        return [] if traduite == source else ["citation hébraïque modifiée"]
    if not traduite:
        return ["citation non traduite"]
    if langue == "he" and not HEBREU.search(traduite):
        return ["citation française à remplacer par l'original"]
    return []


def ecarts_concept(source, traduit, langue):
    if traduit is None:
        return ["non traduit"]
    ecarts = [f"clé inattendue « {clef} »" for clef in set(traduit) - TRADUISIBLES]
    if not traduit.get("nom"):
        ecarts.append("nom manquant")
    for clef in ("resume", "note"):
        if bool(source.get(clef)) != bool(traduit.get(clef)):
            ecarts.append(f"{clef} présent d'un seul côté")
    if len(source.get("cotes", [])) != len(traduit.get("cotes", [])):
        ecarts.append(f"cotes {len(source.get('cotes', []))} ≠ {len(traduit.get('cotes', []))}")
    sources, traduites = source.get("sources", []), traduit.get("sources", [])
    if len(sources) != len(traduites):
        return ecarts + [f"sources {len(sources)} ≠ {len(traduites)}"]
    for rang, (s, t) in enumerate(zip(sources, traduites)):
        if (s["oeuvre"], s["ref"]) != (t.get("oeuvre"), t.get("ref")):
            ecarts.append(f"source {rang} : {s['oeuvre']} {s['ref']} ≠ {t.get('oeuvre')} {t.get('ref')}")
        ecarts += [f"source {rang} : {e}" for e in
                   ecarts_citation(s.get("citation", ""), t.get("citation", ""), langue)]
    return ecarts


def ecarts_contenus(langue):
    ecarts = []
    for lettre in FICHIERS:
        source = lire(f"contenu_{lettre}.json") or {}
        nom = f"contenu_{lettre}.{langue}.json"
        traduit = lire(nom) or {}
        for ident in source:
            ecarts += [f"{nom} {ident} : {e}" for e in
                       ecarts_concept(source[ident], traduit.get(ident), langue)]
        ecarts += [f"{nom} {ident} : absent du français" for ident in set(traduit) - set(source)]
    return ecarts


def ecarts_textes(textes, langue):
    concepts = lire("concepts.json")["concepts"]
    reperes = lire("reperes.json")["entrees"]
    oeuvres = {s["oeuvre"] for lettre in FICHIERS
               for c in (lire(f"contenu_{lettre}.json") or {}).values() for s in c.get("sources", [])}
    t = textes[langue]
    attendus = {
        "interface": set(textes["fr"]["interface"]),
        "zones": {c["zone"] for c in concepts},
        "entrees": {e["id"] for e in reperes} if langue != "fr" else set(),
        "oeuvres": oeuvres if langue != "fr" else set(),
    }
    ecarts = [f"textes.json {langue} : « {clef} » manquant" for clef in ("nom", "sens") if clef not in t]
    for famille, clefs in attendus.items():
        ecarts += [f"textes.json {langue}.{famille} : « {clef} » manquant"
                   for clef in sorted(clefs - set(t.get(famille, {})))]
    return ecarts


def main():
    textes = lire("textes.json")
    if textes is None:
        sys.exit("visite/textes.json introuvable")
    ecarts = []
    for langue in textes:
        ecarts += ecarts_textes(textes, langue)
        if langue != "fr":
            ecarts += ecarts_contenus(langue)
    for ecart in ecarts:
        print(ecart)
    print(f"{len(ecarts)} écart(s)" if ecarts else "traductions à jour")
    sys.exit(1 if ecarts else 0)


main()
