#!/usr/bin/env python3
"""Lecture et recherche des sources du Beit HaMikdash sur Sefaria (sans dependance)."""

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request

API = "https://www.sefaria.org/api"
UA = {"User-Agent": "avoda-mikdash-skill/1.0"}


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _post(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={**UA, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _clean(raw):
    """Aplatit un texte Sefaria (str ou listes imbriquees) en lignes lisibles."""
    if raw is None:
        return []
    if isinstance(raw, str):
        txt = re.sub(r"<[^>]+>", "", raw)
        txt = html.unescape(txt).strip()
        return [txt] if txt else []
    lines = []
    for item in raw:
        lines.extend(_clean(item))
    return lines


def _url(tref):
    return "https://www.sefaria.org/" + urllib.parse.quote(tref.replace(" ", "_"), safe=",._-:")


def cmd_ref(args):
    ref = urllib.parse.quote(args.tref.replace(" ", "_"), safe=",._-:")
    data = _get(f"{API}/v3/texts/{ref}?version=primary&version=translation&return_format=text_only")
    if "error" in data:
        sys.exit(f"Sefaria: {data['error']}")
    print(f"# {data.get('ref')}  ({data.get('heRef', '')})")
    print(_url(data.get("ref", args.tref)))
    for version in data.get("versions", []):
        lang = version.get("language")
        if args.lang != "both" and lang != args.lang:
            continue
        print(f"\n## [{lang}] {version.get('versionTitle', '')}")
        for i, line in enumerate(_clean(version.get("text")), 1):
            print(f"{i}. {line}" if len(_clean(version.get('text'))) > 1 else line)


def cmd_search(args):
    payload = {
        "query": args.query,
        "type": "text",
        "size": args.n,
        "field": "naive_lemmatizer",
    }
    if args.book:
        payload["filters"] = args.book
        payload["filter_fields"] = ["path"] * len(args.book)
    data = _post(f"{API}/search-wrapper", payload)
    hits = data.get("hits", {}).get("hits", [])
    if not hits:
        print("aucun resultat")
        return
    for hit in hits:
        tref = hit.get("_id", "").rsplit(" (", 1)[0]
        snippets = [s for group in hit.get("highlight", {}).values() for s in group]
        snippet = re.sub(r"<[^>]+>", "", " … ".join(snippets))[:300]
        print(f"- {tref}\n  {html.unescape(snippet)}\n  {_url(tref)}")


def cmd_links(args):
    ref = urllib.parse.quote(args.tref.replace(" ", "_"), safe=",._-:")
    data = _get(f"{API}/links/{ref}?with_text=0")
    seen = []
    for link in data:
        cat = link.get("category", "")
        if args.category and cat != args.category:
            continue
        tref = link.get("ref", "")
        if tref in seen:
            continue
        seen.append(tref)
        print(f"- [{cat}] {tref}  {_url(tref)}")
    if not seen:
        print("aucun lien (essayer sans --category)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ref = sub.add_parser("ref", help="lire un passage : ref \"Mishnah Middot 2:1\"")
    p_ref.add_argument("tref")
    p_ref.add_argument("--lang", choices=["he", "en", "both"], default="both")
    p_ref.set_defaults(func=cmd_ref)

    p_search = sub.add_parser("search", help="chercher une expression dans le corpus")
    p_search.add_argument("query")
    p_search.add_argument("-n", type=int, default=8)
    p_search.add_argument("--book", action="append", help="filtre chemin, ex. Mishnah/Seder Kodashim/Mishnah Middot")
    p_search.set_defaults(func=cmd_search)

    p_links = sub.add_parser("links", help="commentaires et paralleles d'un passage")
    p_links.add_argument("tref")
    p_links.add_argument("--category", help="Commentary, Talmud, Halakhah, ...")
    p_links.set_defaults(func=cmd_links)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
