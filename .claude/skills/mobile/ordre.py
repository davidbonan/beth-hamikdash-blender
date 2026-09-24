#!/usr/bin/env python3
"""ordre.py '<corps de fonction async>' [--client id] [--delai s] [--port 8791] — l'exécute dans la page sondée, imprime son retour.

  ordre.py 'return __etat()'
  ordre.py '__vue("vue_mizbeach"); await new Promise(r => setTimeout(r, 4000)); return __rythme.at(-1)'
Sans --client, la page la plus récemment active.
"""
import argparse
import json
import sys
import urllib.request

arguments = argparse.ArgumentParser()
arguments.add_argument("code")
arguments.add_argument("--client")
arguments.add_argument("--delai", type=float, default=120)
arguments.add_argument("--port", type=int, default=8791)
options = arguments.parse_args()

requete = urllib.request.Request(
    f"http://127.0.0.1:{options.port}/__ordonner",
    data=json.dumps({"code": options.code, "client": options.client, "delai": options.delai}).encode(),
    headers={"Content-Type": "application/json"})
try:
    reponse = json.load(urllib.request.urlopen(requete, timeout=options.delai + 5))
except urllib.error.HTTPError as e:
    reponse = json.load(e)
if reponse.get("erreur"):
    print(reponse["erreur"], file=sys.stderr)
    sys.exit(1)
print(json.dumps(reponse.get("resultat"), ensure_ascii=False, indent=1))
