#!/bin/sh
# construire_site.sh [dist] — assemble le site : les pages de site/ et la visite filtrée dans dist/visite/
set -eu

racine="$(cd "$(dirname "$0")" && pwd)"
dist="${1:-$racine/dist}"

mkdir -p "$dist/visite"
rsync -a --delete --delete-excluded --exclude='visite/' --exclude='accueil.py' --exclude='styliser_accueil.sh' --exclude='cameras_accueil.json' --exclude='.DS_Store' "$racine/site/" "$dist/"
rsync -a --delete \
  --include='index.html' --include='apercu.jpg' --include='temple.glb' --include='figures.glb' \
  --include='*.js' --include='*.json' --include='mini_*.png' \
  --include='matieres/' --include='matieres/*.webp' \
  --include='plans/' --include='plans/*.webp' --exclude='*' \
  "$racine/visite/" "$dist/visite/"

echo "site assemblé dans $dist"
