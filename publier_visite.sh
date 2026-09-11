#!/bin/sh
# publier_visite.sh [chemin-du-site] — recopie visite/ dans public/visite/ du site perso
set -eu

source_dir="$(cd "$(dirname "$0")" && pwd)/visite"
site="${1:-$(cd "$(dirname "$0")/.." && pwd)/davidbonan.com}"
cible="$site/public/visite"

[ -f "$site/next.config.js" ] || { echo "pas le dépôt du site : $site" >&2; exit 1; }

mkdir -p "$cible"
rsync -a --delete \
  --include='index.html' --include='apercu.jpg' --include='temple.glb' \
  --include='*.js' --include='*.json' \
  --include='matieres/' --include='matieres/*.webp' \
  --include='plans/' --include='plans/*.webp' --exclude='*' \
  "$source_dir/" "$cible/"

# Servie à /visite, sans slash final, la page résoudrait ses "./" à la racine du site.
grep -q "<base " "$cible/index.html" || \
  perl -0pi -e 's|<meta charset="utf-8">|<meta charset="utf-8">\n<base href="/visite/">|' "$cible/index.html"

echo "visite copiée dans $cible"
git -C "$site" status --short public/visite
