#!/usr/bin/env python3
"""Appose sur chaque URL d'asset de dist/ l'empreinte de ce qu'elle sert.

    python3 empreintes.py dist

Une URL qui porte l'empreinte de son contenu ne peut pas être périmée : le fichier
change, l'URL change, et aucun cache — celui de Safari mobile, celui d'un proxy
d'opérateur — n'a plus rien de vieux à servir sous ce nom. Un en-tête ne suffisait
pas : `must-revalidate` demande une revalidation, il ne l'obtient pas toujours, et
rien depuis le serveur ne purge ce qu'un téléphone garde. Les pages, elles, gardent
leur URL nue : elles sont la seule porte d'entrée, et netlify.toml les tient en
max-age=0 pour que la première requête de la visite ramène toujours les bonnes.

Deux régimes, parce que les poids n'ont rien de commun :

  - les médias (.glb, .webp, .jpg…) portent chacun l'empreinte de son propre
    contenu. Retoucher un script ne fait pas retélécharger les 22 Mo de temple.glb
    et des nappes ;
  - le code et les données (.js, .css, .json) portent un cachet commun, calculé sur
    l'ensemble du site, médias compris. Ils forment un seul programme : un graphe de
    modules à moitié renouvelé — un index.html neuf sur un matieres.js d'avant — est
    pire qu'un graphe en retard. Ils pèsent ensemble moins d'un mégaoctet.

Les seuls chemins que ce script ne voit pas sont ceux que la visite construit à
l'exécution (`contenu_${f}.${code}.json`) : visite.js relit le cachet dans son propre
`import.meta.url` et l'ajoute lui-même. D'où la règle : on ne touche pas ici aux
`.json` cités depuis un `.js`.
"""
import hashlib
import re
import sys
from pathlib import Path

DOMAINE = "https://bethhamikdach.com"
MEDIAS = {".webp", ".jpg", ".jpeg", ".png", ".glb", ".ico", ".svg"}
CODE = {".js", ".css", ".json"}
PORTEURS = {".html", ".css", ".js", ".json"}

# Un chemin d'asset, sous la forme qu'il prend dans une page, une feuille, un module ou
# une donnée : absolu, relatif, ou préfixé du domaine dans une balise og:. Ce qui sort
# d'ici n'est qu'un candidat — seule la résolution sur le disque dit si c'en est un.
REFERENCE = re.compile(
    r"(?<![\w.-])((?:" + re.escape(DOMAINE) + r")?[\w@./-]*\."
    + "(?:" + "|".join(e[1:] for e in sorted(MEDIAS | CODE)) + r"))(?![-\w?])"
)


def empreinte(octets):
    return hashlib.sha256(octets).hexdigest()[:8]


def empreintes_des_medias(dist):
    return {f: empreinte(f.read_bytes())
            for f in dist.rglob("*") if f.is_file() and f.suffix in MEDIAS}


def cachet(dist, medias):
    """Le cachet du programme : tout le code, toutes les données, et l'empreinte de
    chaque média — sans quoi remplacer une nappe laisserait aux modules qui la citent
    une URL inchangée sur un contenu changé."""
    h = hashlib.sha256()
    for f in sorted(f for f in dist.rglob("*") if f.is_file() and f.suffix in CODE):
        h.update(f.relative_to(dist).as_posix().encode())
        h.update(f.read_bytes())
    for f, emp in sorted((f.relative_to(dist).as_posix(), e) for f, e in medias.items()):
        h.update(f.encode())
        h.update(emp.encode())
    return h.hexdigest()[:8]


def vise(reference, porteur, dist):
    """Le fichier de dist/ que cette référence désigne, ou None si elle désigne
    autre chose — un module de trois.js sur le CDN, un nom cité dans un commentaire."""
    chemin = reference[len(DOMAINE):] if reference.startswith(DOMAINE) else reference
    racine = dist if chemin.startswith("/") else porteur.parent
    cible = (racine / chemin.lstrip("/")).resolve()
    if not cible.is_file() or dist not in cible.parents:
        return None
    return cible


def version(cible, porteur, medias, sceau):
    if cible.suffix in MEDIAS:
        return medias[cible]
    if cible.suffix == ".json" and porteur.suffix == ".js":
        return None                       # visite.js le fait à l'exécution, via json()
    return sceau


def apposer(dist):
    dist = dist.resolve()
    medias = empreintes_des_medias(dist)
    sceau = cachet(dist, medias)

    signees = 0
    for porteur in sorted(f for f in dist.rglob("*") if f.is_file() and f.suffix in PORTEURS):
        texte = porteur.read_text(encoding="utf-8")

        def signer(m):
            nonlocal signees
            cible = vise(m.group(1), porteur, dist)
            if cible is None:
                return m.group(0)
            v = version(cible, porteur, medias, sceau)
            if v is None:
                return m.group(0)
            signees += 1
            return f"{m.group(1)}?v={v}"

        signe = REFERENCE.sub(signer, texte)
        if signe != texte:
            porteur.write_text(signe, encoding="utf-8")

    print(f"empreintes apposées : cachet {sceau}, {len(medias)} médias, {signees} URL")


if __name__ == "__main__":
    apposer(Path(sys.argv[1] if len(sys.argv) > 1 else "dist"))
