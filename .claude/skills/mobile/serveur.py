#!/usr/bin/env python3
"""serveur.py [--port 8791] [--journal fichier.jsonl] — sert la visite telle qu'elle est dans l'arbre de travail, sonde injectée.

/visite/ sert visite/, / sert site/. index.html de la visite reçoit sonde.js avant son module : la page
rapporte ses erreurs, ses pertes de contexte, son rythme d'images et sa mémoire GPU à /__journal, et
exécute ce que ordre.py lui envoie. Écoute sur 127.0.0.1 seulement : le simulateur iOS partage le
loopback du Mac. Rien n'est mis en cache : un rechargement voit toujours le code du disque.
"""
import argparse
import json
import mimetypes
import queue
import sys
import threading
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("image/webp", ".webp")

clients = {}          # id -> {"vu": t, "ua": str, "ordres": Queue}
resultats = {}        # id d'ordre -> (Event, [résultat])
verrou = threading.Lock()
journal = None


def remplacer_les_anciennes(nouvelle):
    """Une page qui démarre éteint ses aînées du même appareil : deux visites ouvertes se partagent la mémoire GPU qu'on mesure."""
    with verrou:
        fiche = clients.setdefault(nouvelle["client"], {"ordres": queue.Queue(), "ua": nouvelle["ua"], "vu": time.time()})
        fiche["debut"] = time.time()
        for cle, autre in clients.items():
            if cle != nouvelle["client"] and autre["ua"] == nouvelle["ua"] and not autre.get("eteinte"):
                autre["eteinte"] = True
                autre["ordres"].put({"id": "", "code": 'location.replace("about:blank")'})


def ecrire_journal(entree):
    if entree.get("type") == "demarrage":
        remplacer_les_anciennes(entree)
    ligne = json.dumps(entree, ensure_ascii=False)
    with verrou:
        journal.write(ligne + "\n")
        journal.flush()
    if entree.get("type") != "rythme":
        print(ligne[:400], flush=True)


class Gestionnaire(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def translate_path(self, chemin):
        chemin = urlparse(chemin).path
        if chemin.startswith("/visite/"):
            return str(RACINE / "visite" / chemin[len("/visite/"):])
        return str(RACINE / "site" / chemin.lstrip("/"))

    def repondre(self, code, corps=b"", type_="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/__sonde.js":
            return self.repondre(200, (ICI / "sonde.js").read_bytes(), "application/javascript")
        if url.path == "/__ordre":
            return self.donner_ordre(parse_qs(url.query))
        if url.path == "/__clients":
            with verrou:
                vus = {k: {"ua": v["ua"], "depuis_s": round(time.time() - v["vu"], 1)} for k, v in clients.items()}
            return self.repondre(200, json.dumps(vus).encode())
        if url.path == "/visite":
            self.send_response(301)
            self.send_header("Location", "/visite/" + (f"?{url.query}" if url.query else ""))
            self.end_headers()
            return
        if url.path in ("/visite/", "/visite/index.html"):
            page = (RACINE / "visite" / "index.html").read_bytes()
            page = page.replace(b'<script type="importmap">', b'<script src="/__sonde.js"></script>\n<script type="importmap">', 1)
            return self.repondre(200, page, "text/html; charset=utf-8")
        return super().do_GET()

    def donner_ordre(self, params):
        client = params.get("client", ["?"])[0]
        with verrou:
            fiche = clients.setdefault(client, {"ordres": queue.Queue(), "ua": ""})
            fiche["vu"] = time.time()
            fiche["ua"] = params.get("ua", [fiche["ua"]])[0]
        try:
            ordre = fiche["ordres"].get(timeout=8)
        except queue.Empty:
            return self.repondre(204)
        return self.repondre(200, json.dumps(ordre).encode())

    def do_POST(self):
        longueur = int(self.headers.get("Content-Length", 0))
        corps = json.loads(self.rfile.read(longueur) or b"{}")
        chemin = urlparse(self.path).path
        if chemin == "/__journal":
            for entree in corps if isinstance(corps, list) else [corps]:
                ecrire_journal(entree)
            return self.repondre(204)
        if chemin == "/__resultat":
            with verrou:
                attente = resultats.get(corps["id"])
            if attente:
                attente[1].append(corps)
                attente[0].set()
            return self.repondre(204)
        if chemin == "/__ordonner":
            return self.ordonner(corps)
        return self.repondre(404)

    def ordonner(self, corps):
        with verrou:
            actifs = sorted((v.get("debut", 0), k) for k, v in clients.items()
                            if time.time() - v["vu"] < 20 and not v.get("eteinte"))
            cible = corps.get("client") or (actifs[-1][1] if actifs else None)
            fiche = clients.get(cible)
        if not fiche:
            return self.repondre(404, json.dumps({"erreur": "aucune page sondée n'écoute"}).encode())
        ordre = {"id": uuid.uuid4().hex, "code": corps["code"]}
        attente = (threading.Event(), [])
        with verrou:
            resultats[ordre["id"]] = attente
        fiche["ordres"].put(ordre)
        attente[0].wait(corps.get("delai", 120))
        with verrou:
            resultats.pop(ordre["id"], None)
        reponse = attente[1][0] if attente[1] else {"erreur": "pas de réponse de la page"}
        return self.repondre(200, json.dumps(reponse, ensure_ascii=False).encode())


def main():
    global journal
    arguments = argparse.ArgumentParser()
    arguments.add_argument("--port", type=int, default=8791)
    arguments.add_argument("--journal", default=str(Path.cwd() / "journal.jsonl"))
    options = arguments.parse_args()
    journal = open(options.journal, "a", encoding="utf-8")
    serveur = ThreadingHTTPServer(("127.0.0.1", options.port), Gestionnaire)
    print(f"visite sondée sur http://localhost:{options.port}/visite/ — journal {options.journal}", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
